"""Apply the mod's compiled shiny code to the exact verified Full493 solo DOL."""
import argparse,base64,json,struct
from pathlib import Path
from prepare_campaign_doubles import sha,word,file_offset
from team_series_asm import d,mr,branch
from monferno_build import x
BASE=0x80642000;END=0x80646000
BONUS_BRIDGE=BASE;ENCOUNTER_BRIDGE=BASE+0x80
LOOKUP_BRIDGE=BASE+0x100;UI_BRIDGES=BASE+0x180
BOSS_BRIDGE=BASE+0x1C0
MEWTWO_GATE=0x80641400
UI_CALLS={0x80101A38:0,0x80101B5C:1,0x80101C80:2,0x80101DA4:3,0x80101EC8:4,0x80101FEC:5}
SOURCE_SHA='a45fc7d800730630ad955dca74b40a41488dd8e7e328d9d8322ff752e7b0d6d9'

def prepare(dol,manifest=None):
    manifest=manifest or json.loads(Path(__file__).with_name('shiny-payload.json').read_text())
    if sha(dol)!=SOURCE_SHA:raise ValueError('Exact verified solo Full493/Waterfall DOL required')
    payload=base64.b64decode(manifest['payload_base64'],validate=True)
    if sha(payload)!=manifest['payload_sha256']:raise ValueError('Shiny payload checksum mismatch')
    if sha(Path(__file__).with_name('tournament_shiny.c').read_bytes())!=manifest['source_sha256']:raise ValueError('Shiny C source/payload mismatch; rebuild')
    for name,digest in manifest.get('inputs_sha256',{}).items():
        if sha(Path(__file__).with_name(name).read_bytes())!=digest:raise ValueError('Payload input mismatch: '+name)
    if manifest['address']!=BASE+0x200 or manifest['address']+len(payload)>END:raise ValueError('Payload address/length mismatch')
    if any(word(dol,b+20) for b in (0,0x48,0x90)):raise ValueError('DOL text slot 5 is occupied')
    code=bytearray(END-BASE);at=manifest['address']-BASE;code[at:at+len(payload)]=payload
    def bridge(at,func,args,tail):
        seq=[d(37,1,1,-0x20),0x7c0802a6,d(36,0,1,0x24),*args]
        seq+=[branch(at+len(seq)*4,func,True),d(32,0,1,0x24),0x7c0803a6,d(14,1,1,0x20),*tail]
        for i,v in enumerate(seq):struct.pack_into('>I',code,at-BASE+4*i,v)
        return at+4*len(seq)
    stop=bridge(BONUS_BRIDGE,manifest['symbols']['shiny_bonus'],
                [mr(3,15),d(14,4,1,0x3c)],[d(32,0,1,0x20)])
    struct.pack_into('>I',code,stop-BASE,branch(stop,0x803de3cc))
    stop=bridge(ENCOUNTER_BRIDGE,manifest['symbols']['encounter_shiny'],
                [mr(3,24),mr(4,25)],[mr(3,30)])
    struct.pack_into('>I',code,stop-BASE,branch(stop,0x8017e21c))
    # Resolve only the six private numeric message IDs; all normal lookups
    # retain the displaced native comparison and continue into its routine.
    strings=manifest['symbols']['shiny_ui_strings']
    seq=[d(15,11,0,0x7fff),x(40,11,11,4),d(10,0,11,6),0x40800020,
         d(7,3,11,64),d(15,11,0,(strings+0x8000)>>16),d(14,11,11,strings&65535),
         x(266,3,3,11),0x4e800020,d(10,0,4,1)]
    seq.append(branch(LOOKUP_BRIDGE+len(seq)*4,0x8024fb38))
    # bge must target the displaced original cmplwi, not the final branch.
    seq[3]=0x40800000|((LOOKUP_BRIDGE+9*4-(LOOKUP_BRIDGE+3*4))&65535)
    for i,v in enumerate(seq):struct.pack_into('>I',code,LOOKUP_BRIDGE-BASE+4*i,v)
    for field in range(6):
        at=UI_BRIDGES+field*8
        struct.pack_into('>II',code,at-BASE,d(14,9,0,field),branch(at+4,manifest['symbols']['shiny_ui_draw']))
    # Native CPU dispatch has completed either fixed or variable team creation.
    seq=[d(37,1,1,-0x20),0x7c0802a6,d(36,0,1,0x24),d(36,3,1,8),d(11,0,3,0),0x41820010,
         mr(3,27),mr(4,30),branch(BOSS_BRIDGE+32,manifest['symbols']['tournament_roster'],True),
         d(32,3,1,8),d(32,0,1,0x24),0x7c0803a6,d(14,1,1,0x20),d(14,11,1,0x20),
         branch(BOSS_BRIDGE+56,0x8017f478)]
    for i,v in enumerate(seq):struct.pack_into('>I',code,BOSS_BRIDGE-BASE+4*i,v)
    out=bytearray(dol);offset=(len(out)+31)&~31;out.extend(bytes(offset-len(out)));out.extend(code)
    for b,v in ((0,offset),(0x48,BASE),(0x90,len(code))):struct.pack_into('>I',out,b+20,v)
    for a,before,after in ((0x803de3c8,d(32,0,1,0x20),branch(0x803de3c8,BONUS_BRIDGE)),
                           (0x8017e218,mr(3,30),branch(0x8017e218,ENCOUNTER_BRIDGE)),
                           (0x8063c704,d(14,4,4,0x2000),d(14,4,4,0x6000))):
        pos=file_offset(out,a)
        if word(out,pos)!=before:raise ValueError(f'Hook mismatch at {a:08x}')
        struct.pack_into('>I',out,pos,after)
    for a,field in UI_CALLS.items():
        pos=file_offset(out,a)
        if word(out,pos)!=branch(a,0x80254c6c,True):raise ValueError(f'Status draw mismatch at {a:08x}')
        struct.pack_into('>I',out,pos,branch(a,UI_BRIDGES+field*8,True))
    # Rank filter: exclude Mewtwo from every variable Gateway pool below rank 8.
    gate=[d(40,11,4,6),d(11,0,11,150),0x40820020,d(32,11,3,0x7c),d(10,0,11,4),0x41810014,
          d(11,0,5,7),0x4182000c,d(14,3,0,0),0x4e800020,d(37,1,1,-0x20),branch(MEWTWO_GATE+44,0x8017c568)]
    for i,v in enumerate(gate):
        pos=file_offset(out,MEWTWO_GATE+4*i)
        if word(out,pos)!=0:raise ValueError('Mewtwo filter overlaps existing Waterfall code')
        struct.pack_into('>I',out,pos,v)
    for a,before,after in ((0x8017f474,d(14,11,1,0x20),branch(0x8017f474,BOSS_BRIDGE)),
                           (0x8017c564,d(37,1,1,-0x20),branch(0x8017c564,MEWTWO_GATE))):
        pos=file_offset(out,a)
        if word(out,pos)!=before:raise ValueError(f'Boss hook mismatch: {a:08x}')
        struct.pack_into('>I',out,pos,after)
    pos=file_offset(out,0x8024fb34)
    if word(out,pos)!=d(10,0,4,1):raise ValueError('Message lookup prologue mismatch')
    struct.pack_into('>I',out,pos,branch(0x8024fb34,LOOKUP_BRIDGE))
    return bytes(out),{'status':'implemented-awaiting-native-and-Dolphin-validation',
        'source_dol_sha256':sha(dol),'output_dol_sha256':sha(out),
        'chance_basis_points_by_rank':[300+(200*i)//7 for i in range(8)],
        'survival_maximum_native_tier':6,'masters_difficulty_source':'Original set index, records 31..38',
        'roll':'Per generated CPU Pokemon, native LCG with unbiased rejection sampling',
        'bonus':'floor(highest actual recalculated stat * 110 / 100), one stat only',
        'boss_rules':'Ranks 6/7 replace weakest BST member with a distinct legendary; rank 8 shiny Mewtwo; Little Battle excluded',
        'gateway_mewtwo':'Rank 8 only, variable legal Gen 4 coverage sets; no immediate set repeat within session',
        'hp_included':True,'status_bonus_text':'base (+bonus), compact if needed; native measured font/bounds; narrow layouts keep original effective value; HP shows current/base (+bonus)','tie_order':['HP','Attack','Defense','SpAttack','SpDefense','Speed'],
        'bonus_recalculation_idempotent':True,'shiny_pid_preserves_nature_and_gender':True,
        'unown_letter_preserved':True,'shiny_identity_method':'Preserve PID/public trainer ID/name; update hidden secret ID with native PK4 setter',
        'existing_rental_shiny_appearance_preserved':True,'direct_save_file_writes':False,
        'dolphin_tested':False,'payload_sha256':manifest['payload_sha256'],'reserved_end':f'{END:08x}'}
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dol','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();out,r=prepare(a.dol.read_bytes());a.output.mkdir(parents=True,exist_ok=True)
    (a.output/'main.dol').write_bytes(out);(a.output/'shiny-build.json').write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
