"""Compose a disabled cooperative draft prototype on the exact v0.9.1 base.

Own freestanding code occupies an extended, arena-reserved DOL text section.
No user saves or original Pokemon data are included in the payload.
"""
import argparse,json,struct
from pathlib import Path

from coop_actor_bridge import BRIDGE,prepare_actor_bridge
from coop_input_router import CODE,STATE,assemble
from disassemble import sections
from prepare_campaign_doubles import file_offset,sha,word
from team_series_asm import branch,d,mr

BASE=0x8063C000
END=0x8063F000
PAYLOAD=0x8063D400
DRAFT=0x8063EB00
STUBS=0x8063EA00
CHOOSE_ADAPTER=0x8063EA20
PACK_ADAPTER=0x8063EA28
INPUT_ADAPTER=0x8063EA80
HOOKS={0x80159B6C:('coop_reset',0x8063EA00),
       0x80159DB8:('choose_adapter',0x8063EA08),
       0x8015A1C4:('pack_adapter',0x8063EA10),
       0x80156364:('coop_cleanup',0x8063EA18),
       0x801722BC:('coop_validate_switch',0x8063EB50)}

def stub_words(symbols,layout,source):
    words={};labels={};fix=[];pc=STUBS
    def e(v):
        nonlocal pc
        if pc in words:raise ValueError('Stub overlap')
        words[pc]=v;pc+=4
    def label(n):labels[n]=pc
    def j(n,c=None):fix.append((pc,n,c));e(0)
    def load(reg,value):e(d(15,reg,0,(value+0x8000)>>16));e(d(14,reg,reg,value&0xFFFF))
    for address,(_,stub) in HOOKS.items():
        pc=stub;e(word(source,file_offset(source,address)));e(branch(pc,address+4))
    pc=CHOOSE_ADAPTER;e(0x7CE802A6);e(branch(pc,symbols['coop_choose'])) # mflr r7
    pc=PACK_ADAPTER
    e(0x9421FFE0);e(0x7C0802A6);e(d(36,0,1,0x24));e(branch(pc,symbols['coop_pack'],True))
    e(d(32,0,1,0x24));e(0x7C0803A6);e(d(14,1,1,0x20));e(d(11,0,3,0));j('return','ne')
    # Native callers otherwise leave the selection screen even after failure.
    for caller in (0x8015748C,0x80156C40):
        load(12,caller);e(0x7C006000);j('selection_exit','eq')
    label('return');e(0x4E800020)
    label('selection_exit');e(branch(pc,0x80157B58))
    if pc>INPUT_ADAPTER:raise ValueError('Packing adapter overlaps input adapter')
    pc=INPUT_ADAPTER
    e(0x9421FFD0);e(0x7C0802A6);e(d(36,0,1,0x34))
    for reg in range(3,7):e(d(36,reg,1,8+(reg-3)*4))
    e(mr(3,0));e(branch(pc,symbols['coop_input_scope'],True));e(mr(12,3))
    for reg in range(3,7):e(d(32,reg,1,8+(reg-3)*4))
    e(d(32,0,1,0x34));e(0x7C0803A6);e(d(14,1,1,0x30));load(7,STATE)
    e(d(11,0,12,0));e(0x41820000|((BRIDGE-pc)&0xFFFC));e(branch(pc,layout['manual']))
    if pc>DRAFT:raise ValueError('Input adapter overlaps draft state')
    pc=0x8063EB40;load(7,STATE);e(branch(pc,layout['manual']))
    for a,n,c in fix:
        delta=labels[n]-a
        if c and not -0x8000<=delta<0x8000:raise ValueError('Conditional branch range')
        words[a]=branch(a,labels[n]) if c is None else {'eq':0x41820000,'ne':0x40820000}[c]|(delta&0xFFFC)
    return words

def prepare_draft(source,payload,manifest):
    actor=prepare_actor_bridge(source)
    if manifest['address']!=PAYLOAD or manifest['bytes']!=len(payload) or manifest['payload_sha256']!=sha(payload):
        raise ValueError('Draft payload manifest mismatch')
    symbols=manifest['symbols']
    for name in ('coop_reset','coop_choose','coop_pack','coop_cleanup','coop_input_scope',
                 'coop_party_read','coop_validate_switch'):
        if not PAYLOAD<=symbols[name]<PAYLOAD+len(payload):raise ValueError('Symbol outside payload')
    if PAYLOAD+len(payload)>STUBS:raise ValueError('Payload overlaps stubs')
    offset=word(actor,8)
    if word(actor,0x50)!=BASE or word(actor,0x98)!=0x800 or offset+0x800!=len(actor):
        raise ValueError('Unexpected source text section layout')
    # The captured SDK EXPHeap header lives at 0x8063C800. A separate text
    # section keeps that gap out of the DOL image. Raising ArenaLo below also
    # moves heap creation above the new section when booting this prototype.
    if any(word(actor,header+12) for header in (0,0x48,0x90)):
        raise ValueError('DOL text slot 3 is occupied')
    for _,address,size in sections(actor):
        if address<END and PAYLOAD<address+size:raise ValueError('New section overlaps existing DOL')
    offset=(len(actor)+31)&~31
    out=bytearray(actor)+bytes(offset-len(actor))+bytes(END-PAYLOAD)
    for header,value in ((0,offset),(0x48,PAYLOAD),(0x90,END-PAYLOAD)):
        struct.pack_into('>I',out,header+12,value)
    def put(address,value):struct.pack_into('>I',out,file_offset(out,address),value)
    out[file_offset(out,PAYLOAD):file_offset(out,PAYLOAD)+len(payload)]=payload
    layout={};router=assemble(INPUT_ADAPTER,layout)
    out[file_offset(out,CODE):file_offset(out,CODE)+len(router)]=router
    for address,value in stub_words(symbols,layout,source).items():put(address,value)
    for address,(name,_) in HOOKS.items():
        target={'choose_adapter':CHOOSE_ADAPTER,'pack_adapter':PACK_ADAPTER}.get(name,symbols.get(name))
        put(address,branch(address,target))
    if word(source,file_offset(source,0x80063240))!=branch(0x80063240,0x8005B5EC,True):
        raise ValueError('Native party input call mismatch')
    put(0x80063240,branch(0x80063240,symbols['coop_party_read'],True))
    # Both arena-low aliases already use this clamp; raise its minimum to
    # include the new payload, adapters and state before any heap allocation.
    if word(actor,file_offset(actor,0x8063C704))!=d(14,4,4,-0x3800):raise ValueError('Arena clamp mismatch')
    put(0x8063C704,d(14,4,4,-0x1000))
    if any(out[file_offset(out,DRAFT):file_offset(out,DRAFT)+32]):raise ValueError('Draft must boot disabled')
    return bytes(out)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('source','payload','manifest','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args()
    result=prepare_draft(args.source.read_bytes(),args.payload.read_bytes(),json.loads(args.manifest.read_text()))
    args.output.write_bytes(result)
    print(json.dumps({'status':'development-only','bytes':len(result),'sha256':sha(result),
                      'reserved_end':f'{END:08x}','enabled_at_boot':False},indent=2))
