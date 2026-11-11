"""Save-compatible in-memory migration of Nate's original Monferno, RPBE01.

Append a DOL text section above the original main-thread stack and reserve it
through both native MEM1 arena-low setters. Never touch a save file directly.
"""
import struct,json
from pathlib import Path
from prepare_campaign_doubles import file_offset,word,sha
from team_series_asm import d,mr,branch

V8_SHA='b15c4d6d6237062d45894fdb890c9a0efa3ee0f792ad4350aa01d0bde227b9ab'
CODE=0x8063C000
ARENA=0x8063C700
CARRY=0x8063C300
CARRY_HOOK=0x80155AE4
RESERVED_END=0x8063C800
GET=0x803DE52C
SET=0x803DECA8
PASS_BASE=0x80453184
MON_OFFSET=38*0x6EC+0x1FC+0x8C
HOOKS=(0x800E85B4,0x800E85D0,0x800E8908)

def x(op,rt,ra,rb):return 31<<26|rt<<21|ra<<16|rb<<11|op<<1

def assemble():
    words=[];labels={};pending=[]
    def emit(w):words.append(w)
    def label(n):labels[n]=CODE+4*len(words)
    def jump(n,cond=None):pending.append((len(words),n,cond));emit(0)
    def call(a):emit(branch(CODE+4*len(words),a,True))
    def getter(field):
        emit(mr(3,30));emit(d(14,4,0,field));emit(d(14,5,0,0));call(GET)
    def setter(field,value=None,register=None):
        if register is None:emit(d(14,0,0,value));register=0
        emit(d(36,register,1,8));emit(mr(3,30));emit(d(14,4,0,field));emit(d(14,5,1,8));call(SET)
    emit(d(37,1,1,-0x30));emit(0x7C0802A6);emit(d(36,0,1,0x34))
    for reg,off in [(28,0x10),(29,0x14),(30,0x18),(31,0x1C)]:emit(d(36,reg,1,off))
    emit(mr(31,3))
    emit(d(15,4,0,0x8045));emit(d(32,4,4,0x3184));emit(d(11,0,4,0));jump('done','eq')
    # Accept the Nate pass accessor or its original Monferno slot accessor.
    emit(d(15,4,4,1));emit(d(14,4,4,(38*0x6EC)&65535))
    emit(x(0,0,3,4));jump('target','eq')
    emit(d(14,4,4,0x1FC+0x8C));emit(x(0,0,3,4));jump('done','ne')
    jump('mon_ready')
    label('target');emit(d(14,4,4,0x1FC+0x8C))
    label('mon_ready');emit(mr(30,4));getter(5);emit(d(11,0,3,391));jump('done','ne')
    # PID encodes nature. Preserve its bottom 20 bits, including the PK4 block
    # order, gender threshold and ability parity. Search is bounded by 49 steps.
    emit(d(32,29,30,0));emit(d(14,28,0,25))
    label('nature_loop');emit(x(459,0,29,28));emit(x(235,0,0,28));emit(x(40,0,0,29))
    emit(d(11,0,0,3));jump('nature_ready','eq');emit(d(15,29,29,0x10));jump('nature_loop')
    label('nature_ready');emit(d(32,0,30,0));emit(x(0,0,0,29));jump('nature_done','eq');setter(0,register=29)
    label('nature_done')
    for field,value,ppfield,ppup,pp in [(6,157,None,None,None),(0x38,299,0x3C,0x40,10),(0x39,370,0x3D,0x41,5)]:
        getter(field);emit(d(11,0,3,value));jump(f'field_{field}_done','eq');setter(field,value)
        if ppfield is not None:setter(ppup,0);setter(ppfield,pp)
        label(f'field_{field}_done')
    label('done');emit(mr(3,31))
    for reg,off in [(28,0x10),(29,0x14),(30,0x18),(31,0x1C)]:emit(d(32,reg,1,off))
    emit(d(32,0,1,0x34));emit(0x7C0803A6);emit(d(14,1,1,0x30));emit(0x4E800020)
    for i,n,c in pending:
        a=CODE+4*i;target=labels[n]
        if c:
            delta=target-a
            if not -32768<=delta<=32764:raise ValueError('Conditional range')
            words[i]=({'eq':0x41820000,'ne':0x40820000}[c])|(delta&0xFFFC)
        else:words[i]=branch(a,target)
    body=b''.join(struct.pack('>I',w) for w in words)
    if len(body)>ARENA-CODE:raise ValueError('Migration exceeds reserved section')
    # Clamp both MEM1 arena-low aliases so alternate loader/debug boot paths
    # cannot put heap allocations over this added section. Default ArenaLo
    # (0x8063D2C0) is already above it; the original stack top is 0x8063B2B0.
    clamp=[d(15,4,0,0x8064),d(14,4,4,-0x3800),x(32,0,3,4),0x40800008,mr(3,4),d(36,3,13,-0x7870),0x4E800020]
    result=bytearray(0x800);result[:len(body)]=body
    result[ARENA-CODE:ARENA-CODE+len(clamp)*4]=b''.join(struct.pack('>I',w) for w in clamp)
    # The survival builder normally restores a consumed item (0) from the
    # preceding fight. Override only its held-item restore for this identity,
    # once at the next battle's construction, never on in-battle item reads.
    w=[];fix=[];lab={}
    def e(v):w.append(v)
    def l(n):lab[n]=CARRY+4*len(w)
    def j(n):fix.append((len(w),n));e(0)
    def c(a):e(branch(CARRY+4*len(w),a,True))
    def g(reg):e(mr(3,reg));e(d(14,4,0,7));e(d(14,5,0,0));c(GET)
    e(d(37,1,1,-0x30));e(0x7C0802A6);e(d(36,0,1,0x34))
    for r,o in[(28,0x10),(29,0x14),(30,0x18),(31,0x1C)]:e(d(36,r,1,o))
    e(mr(31,3));e(mr(30,5));e(d(15,29,0,0x8045));e(d(32,29,29,0x3184));e(d(11,0,29,0));j('set')
    e(d(15,29,29,1));e(d(14,29,29,MON_OFFSET&65535))
    e(d(32,3,31,0));e(d(32,4,29,0));e(x(0,0,3,4));j('set')
    e(mr(3,29));e(d(14,4,0,5));e(d(14,5,0,0));c(GET);e(d(11,0,3,391));j('set')
    g(31);e(mr(28,3));g(29);e(x(0,0,3,28));j('set')
    e(d(14,0,0,157));e(d(36,0,1,8));e(d(14,30,1,8))
    l('set');e(mr(3,31));e(d(14,4,0,6));e(mr(5,30));c(0x803DEB54)
    for r,o in[(28,0x10),(29,0x14),(30,0x18),(31,0x1C)]:e(d(32,r,1,o))
    e(d(32,0,1,0x34));e(0x7C0803A6);e(d(14,1,1,0x30));e(0x4E800020)
    for i,n in fix:
        # All fast exits are bne except the initial null-base test.
        cond=0x41820000 if i==12 else 0x40820000
        w[i]=cond|((lab[n]-(CARRY+4*i))&0xFFFC)
    if CARRY+len(w)*4>ARENA:raise ValueError('Carryover helper overlap')
    result[CARRY-CODE:CARRY-CODE+len(w)*4]=b''.join(struct.pack('>I',v) for v in w)
    return bytes(result),labels

def prepare_build(dol):
    if sha(dol)!=V8_SHA:raise ValueError('Monferno migration requires exact v8 DOL')
    payload,labels=assemble();out=bytearray(dol)
    if any(word(dol,b+8) for b in(0,0x48,0x90)):raise ValueError('Text slot 2 occupied')
    for count,fo,ao,so in[(7,0,0x48,0x90),(11,0x1C,0x64,0xAC)]:
        for i in range(count):
            a,s=word(dol,ao+4*i),word(dol,so+4*i)
            if s and a<RESERVED_END and CODE<a+s:raise ValueError('New section overlaps existing section')
    if word(dol,0xD8)+word(dol,0xDC)>CODE:raise ValueError('New section overlaps BSS')
    edits=[]
    for a in HOOKS:
        off=file_offset(dol,a)
        if word(dol,off)!=0x4E800020:raise ValueError('Accessor return mismatch')
        w=branch(a,CODE);struct.pack_into('>I',out,off,w);edits.append(hex(a))
    for a in(0x8026EABC,0x8026EACC):
        off=file_offset(dol,a)
        if word(dol,off)!=0x906D8790:raise ValueError('Arena setter mismatch')
        struct.pack_into('>I',out,off,branch(a,ARENA));edits.append(hex(a))
    off=file_offset(dol,CARRY_HOOK)
    if word(dol,off)!=branch(CARRY_HOOK,0x803DEB54,True):raise ValueError('Carryover setter call mismatch')
    struct.pack_into('>I',out,off,branch(CARRY_HOOK,CARRY,True));edits.append(hex(CARRY_HOOK))
    offset=(len(out)+31)&~31;out+=bytes(offset-len(out));out+=payload
    for base,value in[(0,offset),(0x48,CODE),(0x90,len(payload))]:struct.pack_into('>I',out,base+8,value)
    return bytes(out),{'status':'experimental','source_sha256':sha(dol),'main_dol_sha256':sha(out),
        'nature':'Adamant','moves':['Fire Punch','Mach Punch','Blaze Kick','Close Combat'],'item':'Lum Berry',
        'scope':'Nate rental pass 38, slot 1 (zero-based), species 391 only',
        'new_text_section':{'address':hex(CODE),'size':len(payload),'reserved_end':hex(RESERVED_END)},'hook_addresses':edits,
        'save_file_directly_modified':False,'runtime_tested_in_dolphin':False}

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args()
    new,report=prepare_build(a.source.read_bytes());a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'main.dol').write_bytes(new);(a.output/'monferno-audit.json').write_text(json.dumps(report,indent=2)+'\n')
