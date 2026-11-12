"""Experimental native actor bridge for two captured command interfaces.

Disabled at boot. A test harness must explicitly install the per-party owners
and enable automatic routing. Draft, switch filtering, battle lifecycle and
online setup remain separate, unfinished integrations.
"""
import struct

from coop_input_router import CODE, ENTRY, STATE, SOURCE_SHA, assemble, state_bytes
from prepare_campaign_doubles import file_offset, sha, word
from team_series_asm import branch, d

BRIDGE=0x8063C540
RESTORE=0x8063C200
BEGIN=0x8063C720
BEGIN_HOOK=0x8005F364
UI=0x8044DF88
REGISTRY=0x804E60F0
ACTIVE_SLOT=0x803CC838


def actor_words(layout):
    words={};labels={};fix=[];pc=BRIDGE
    def e(value):
        nonlocal pc
        words[pc]=value;pc+=4
    def org(address):
        nonlocal pc
        pc=address
    def label(name):labels[name]=pc
    def j(name,condition=None):fix.append((pc,name,condition));e(0)
    def load(reg,address):e(d(15,reg,0,(address+0x8000)>>16));e(d(14,reg,reg,address&0xFFFF))
    # This is a tail trampoline: preserve the game's caller LR and input args.
    e(0x9421FFD0);e(0x7C0802A6);e(d(36,0,1,0x34))
    for reg in range(3,7):e(d(36,reg,1,8+(reg-3)*4))
    load(8,0x8006180C);e(0x7C004000);j('action','eq')
    load(8,0x80062180);e(0x7C004000);j('outside','ne')
    load(8,0x80061C98);e(d(14,9,0,2));j('registered')
    label('action');load(8,0x80061598);e(d(14,9,0,1))
    label('registered')
    # A matching caller is insufficient: it must be the registered live UI.
    e(d(32,12,13,-0x7E1C));e(d(10,0,12,32));j('outside','ge')
    load(10,REGISTRY);e(0x7D6A6214) # add r11,r10,r12
    e(d(34,11,11,0x12C));e(d(11,0,11,0));j('outside','eq')
    e(21<<26|12<<21|12<<16|2<<11|29<<1) # slwi r12,r12,2
    e(0x7D4A6214);e(d(32,12,10,0x2C));e(0x7C0C4000);j('outside','ne')
    load(10,UI)
    e(d(40,11,10,0x6E));e(d(11,0,11,0));j('outside','ne')
    e(d(32,11,10,0xB4));e(d(32,12,7,0x1C));e(0x7C0B6000);j('blocked','ne')
    e(d(34,11,7,9));e(d(11,0,11,1));j('blocked','ne')
    # First actor modes are 1/2; second actor modes are 6/7. Corroborate
    # the mode against the UI actor field before resolving the logical party.
    e(d(40,4,10,0x64));e(d(10,0,4,1));j('blocked','gt')
    e(d(7,11,4,5));e(0x7D6B4A14) # add r11,r11,r9
    e(d(34,12,13,-0x671C));e(0x7C0B6000);j('blocked','ne')
    e(d(14,3,0,0));e(branch(pc,ACTIVE_SLOT)|1)
    load(7,STATE);e(d(10,0,3,6));j('blocked','ge')
    e(d(14,8,7,10));e(31<<26|8<<21|8<<16|3<<11|87<<1) # lbzx r8,r8,r3
    e(d(10,0,8,1));j('blocked','gt')
    e(d(38,8,7,6));e(d(14,8,0,2));e(d(38,8,7,5));j('routed')
    if pc>STATE:raise ValueError('Actor bridge exceeds its reserved gap')

    org(RESTORE)
    label('blocked');load(7,STATE);e(d(14,8,0,255));e(d(38,8,7,5))
    label('routed');e(d(14,12,0,1));j('restore')
    label('outside');e(d(14,12,0,0))
    label('restore')
    for reg in range(3,7):e(d(32,reg,1,8+(reg-3)*4))
    e(d(32,0,1,0x34));e(0x7C0803A6);e(d(14,1,1,0x30))
    load(7,STATE);e(d(11,0,12,0))
    e(0x41820000|((layout['original']-pc)&0xFFFC))
    e(branch(pc,layout['manual']))
    if pc>0x8063C300:raise ValueError('Actor bridge restore overlaps berry code')

    org(BEGIN)
    # Every native menu-open request starts a new input epoch, including a
    # repeated choice by the same owner. Args and caller LR stay unchanged.
    load(7,STATE);e(d(32,8,7,0));load(9,0x434F4F50);e(0x7C084800);j('begin_original','ne')
    e(d(34,8,7,4));e(d(11,0,8,1));j('begin_original','ne')
    e(d(34,8,7,8));e(d(11,0,8,1));j('begin_original','ne')
    e(d(32,8,7,0x10));e(d(14,8,8,1));e(d(36,8,7,0x10))
    label('begin_original');e(0x9421FFC0);e(branch(pc,BEGIN_HOOK+4))
    if pc>0x8063C800:raise ValueError('Menu-open hook exceeds arena reservation')
    cond={'eq':0x41820000,'ne':0x40820000,'ge':0x40800000,'gt':0x41810000}
    for address,name,condition in fix:
        delta=labels[name]-address
        if condition and not -0x8000<=delta<0x8000:raise ValueError('Conditional branch out of range')
        words[address]=branch(address,labels[name]) if condition is None else cond[condition]|(delta&0xFFFC)
    return words


def prepare_actor_bridge(dol):
    if sha(dol)!=SOURCE_SHA:raise ValueError('Actor prototype requires exact v0.9.1 source')
    layout={};router=assemble(BRIDGE,layout);words=actor_words(layout)
    output=bytearray(dol)
    for address,value in words.items():
        off=file_offset(dol,address)
        if word(dol,off)!=0:raise ValueError(f'Actor code overlaps base at {address:08x}')
        struct.pack_into('>I',output,off,value)
    start=file_offset(dol,CODE)
    if CODE+len(router)>BRIDGE or any(dol[start:start+len(router)]):raise ValueError('Router gap unavailable')
    output[start:start+len(router)]=router
    if any(dol[file_offset(dol,STATE):file_offset(dol,STATE)+32]):raise ValueError('State gap unavailable')
    for address,destination,expected in [(ENTRY,CODE,0x9421FFD0),(BEGIN_HOOK,BEGIN,0x9421FFC0)]:
        off=file_offset(dol,address)
        if word(dol,off)!=expected:raise ValueError('Native entry instruction mismatch')
        struct.pack_into('>I',output,off,branch(address,destination))
    return bytes(output)


def automatic_state(session,owners=(0,1,0,1,255,255),epoch=1):
    if len(owners)!=6 or any(owner not in (0,1,255) for owner in owners):raise ValueError('Invalid owner table')
    if not 0x90000000<=session<0x94000000:raise ValueError('Expected a live MEM2 battle session')
    state=bytearray(state_bytes(enabled=1,phase=2,owner=0,epoch=epoch))
    state[8:16]=bytes([1,1,*owners]);struct.pack_into('>I',state,0x1C,session)
    return bytes(state)
