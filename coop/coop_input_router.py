"""Experimental input primitive; disabled at boot, no battle-phase integration.

Routes logical pad 0 only for explicitly authorized choice epochs. No network
socket, no AI takeover, no automatic actor/party mapping is implemented here.
"""
import struct
from prepare_campaign_doubles import file_offset,word,sha
from team_series_asm import branch,d,mr

SOURCE_SHA='10913e96306bd0f8ef85f07c1d95d73ca90cbe923added8b513809640163fe96'
ENTRY=0x8005B5EC
CODE=0x8063C400
STATE=0x8063C6C0
MAGIC=0x434F4F50

def assemble():
    w=[];labels={};patch=[]
    def e(v):w.append(v)
    def label(n):labels[n]=CODE+4*len(w)
    def j(n,c=None):patch.append((len(w),n,c));e(0)
    e(d(15,7,0,0x8064));e(d(14,7,7,-0x3940))
    e(d(32,8,7,0));e(d(15,9,0,0x434F));e(d(24,9,9,0x4F50));e(0x7C084800);j('original','ne')
    e(d(34,8,7,4));e(d(11,0,8,1));j('original','ne')
    e(d(34,8,7,5));e(d(11,0,8,0));j('original','eq');e(d(10,0,8,5));j('blocked','gt')
    e(d(11,0,4,0));j('original','ne');e(d(11,0,5,0));j('original','ne')
    e(29<<26|3<<21|0x2000);j('original','ne') # Don't mask device-probe queries.
    e(d(34,8,7,6));e(d(10,0,8,1));j('blocked','gt')
    e(d(32,9,7,0x10));e(d(32,10,7,0x14));e(0x7C095000);j('epoch_ready','eq')
    e(d(36,9,7,0x14));e(d(14,10,0,1));e(d(38,10,7,7))
    label('epoch_ready');e(d(32,10,13,-0x5B60));e(d(11,0,10,0));j('disconnect','eq')
    e(d(32,11,10,4));e(0x7C085840);j('disconnect','ge') # cmplw r8,r11
    e(d(7,11,8,0x928));e(0x7D4A5A14);e(d(14,10,10,0x38))
    e(d(32,11,10,0x3C));e(d(11,0,11,0));j('disconnect','ne')
    e(d(32,11,10,0x40));e(d(11,0,11,0));j('disconnect','le')
    e(d(34,11,10,0xA1));e(d(11,0,11,0));j('disconnect','ne')
    e(d(34,11,7,7));e(d(11,0,11,0));j('route','eq')
    e(d(32,11,10,0x20));e(21<<26|11<<21|11<<16|17<<6|15<<1);e(d(11,0,11,0));j('blocked','ne')
    e(d(14,11,0,0));e(d(38,11,7,7));j('blocked')
    label('route');e(mr(4,8));e(mr(5,8));j('original')
    label('disconnect');e(d(14,11,0,1));e(d(38,11,7,7))
    label('blocked');e(d(14,3,0,0));e(0x4E800020)
    label('original');e(0x9421FFD0);e(branch(CODE+4*len(w),ENTRY+4))
    conditions={'eq':0x41820000,'ne':0x40820000,'gt':0x41810000,'ge':0x40800000,'le':0x40810000}
    for i,n,c in patch:
        a=CODE+4*i;delta=labels[n]-a
        w[i]=branch(a,labels[n]) if c is None else conditions[c]|(delta&0xFFFC)
    data=b''.join(struct.pack('>I',v) for v in w)
    if CODE+len(data)>STATE:raise ValueError('Input router exceeds owned section gap')
    return data

def prepare_router(dol):
    if sha(dol)!=SOURCE_SHA:raise ValueError('Coop primitive requires exact v0.9.1 source')
    output=bytearray(dol);code=assemble()
    start=file_offset(dol,CODE);state=file_offset(dol,STATE)
    if any(dol[start:state+0x20]):raise ValueError('Coop primitive overlaps existing code/data')
    off=file_offset(dol,ENTRY)
    if word(dol,off)!=0x9421FFD0:raise ValueError('Input entry instruction mismatch')
    output[start:start+len(code)]=code;struct.pack_into('>I',output,off,branch(ENTRY,CODE))
    return bytes(output)

def state_bytes(enabled=0,phase=0,owner=0,epoch=0):
    # last_epoch starts different from epoch, so first use requires release.
    return struct.pack('>I4B8xII8x',MAGIC,enabled,phase,owner,1,epoch,(epoch-1)&0xFFFFFFFF)
