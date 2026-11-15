"""Restore native Waterfall pair rotation without overwriting shiny/VM helpers.

Requires the user's original USA rev0 DOL plus exact experimental coop base.
Original native blocks are read locally and relocated, never bundled in source.
Only Waterfall (floor 1002) changes to six picks/three independent pairs.
"""
import argparse,json,struct
from pathlib import Path
from prepare_campaign_doubles import sha,word,file_offset,read_archive,replace_archive_resource,DOL_SHA256
from team_series_asm import d,branch
from lzss_encode import encode

BASE_SHAS={'c9a1b12b0c950b3475f3a645cf4cbdf7fdeb9b7653b1a4e19546bdda4ace933a','10913e96306bd0f8ef85f07c1d95d73ca90cbe923added8b513809640163fe96'}
START=0x80641000
END=0x80642000
PAIR=START
TERMINAL=START+0x180
GATE_PAIR=START+0x280
GATE_TERMINAL=START+0x2C0
GATE_COUNT=START+0x300
REQUIRED=START+0x340
MARSHAL=START+0x380


def relocated_block(original,start,end,target):
    out={}
    for old in range(start,end,4):
        raw=word(original,file_offset(original,old));new=target+old-start
        opcode=raw>>26
        if opcode==18 and not raw&2:
            delta=raw&0x3FFFFFC
            if delta&0x2000000:delta-=0x4000000
            destination=old+delta
            if start<=destination<=end:destination=target+destination-start
            raw=branch(new,destination,bool(raw&1))
        elif opcode==16 and not raw&2:
            delta=raw&0xFFFC
            if delta&0x8000:delta-=0x10000
            destination=old+delta
            if start<=destination<=end:destination=target+destination-start
            jump=destination-new
            if not -32768<=jump<32768:
                raise ValueError('External conditional branch cannot be relocated')
            raw=(raw&0xFFFF0003)|(jump&0xFFFC)
        out[new]=raw
    return out


def prepare(source,original,common):
    if sha(common)!='08ccff086b981be6babcb659905f2612cbd0844acc6300b0279d3e4bb22c4297':raise ValueError('Unsupported base common archive')
    if sha(source) not in BASE_SHAS or sha(original)!=DOL_SHA256:raise ValueError('Unsupported base/original DOL')
    if any(word(source,b+16) for b in (0,0x48,0x90)):raise ValueError('DOL text slot 4 occupied')
    out=bytearray(source)+bytes(END-START)
    for header,value in ((0,len(source)),(0x48,START),(0x90,END-START)):struct.pack_into('>I',out,header+16,value)
    words={}
    def put(address,value):struct.pack_into('>I',out,file_offset(out,address),value)
    # No lookup table in these original blocks: only relative branches/CTR loops.
    words.update(relocated_block(original,0x80076F08,0x8007707C,PAIR))
    words[PAIR+0x174]=branch(PAIR+0x174,0x8007707C)
    words.update(relocated_block(original,0x80076E24,0x80076ED8,TERMINAL))
    words[TERMINAL+0xB4]=branch(TERMINAL+0xB4,0x80076ED8)
    # Branch on floor without destroying incoming phase r0 or format r0.
    def gate(at,waterfall,ordinary):
        seq=[d(32,11,3,0x30),d(32,11,11,0x10),d(11,0,11,1002),
             0x41820000|((waterfall-(at+12))&0xFFFC)]
        seq+=ordinary
        for i,v in enumerate(seq):words[at+4*i]=v
    gate(GATE_PAIR,PAIR,[branch(GATE_PAIR+16,0x80076F20,True),branch(GATE_PAIR+20,0x8007707C)])
    # Terminal entry does not yet have r3=manager; load the original SDA global.
    words[GATE_TERMINAL]=d(32,3,13,-0x7E08)
    gate(GATE_TERMINAL+4,TERMINAL,[branch(GATE_TERMINAL+20,0x80076F20,True),branch(GATE_TERMINAL+24,0x80076ED8)])
    gate(GATE_COUNT,GATE_COUNT+32,[d(14,0,0,4),d(14,29,0,4),branch(GATE_COUNT+24,0x800770A8)])
    words[GATE_COUNT+32]=d(14,0,0,2);words[GATE_COUNT+36]=d(14,29,0,2);words[GATE_COUNT+40]=branch(GATE_COUNT+40,0x800770A8)
    for at,targetreg,normal,special,ret in ((REQUIRED,3,4,6,None),(MARSHAL,20,4,2,0x801733D8)):
        words[at]=d(32,11,13,-0x6574);words[at+4]=d(32,11,11,0x10);words[at+8]=d(11,0,11,1002)
        words[at+12]=d(14,targetreg,0,normal);words[at+16]=0x4082000C
        words[at+20]=d(14,targetreg,0,special)
        words[at+24]=branch(at+24,ret) if ret else 0x4E800020
        # The bne goes to the same return instruction; no second path/state.
        words[at+16]=0x40820008
    for a,v in words.items():put(a,v)
    for a,t,link in ((0x80076F08,GATE_PAIR,False),(0x80076E24,GATE_TERMINAL,False),
                     (0x800770A0,GATE_COUNT,False),(0x8008B7F0,REQUIRED,True),(0x801733D4,MARSHAL,False)):
        put(a,branch(a,t,link))
    put(0x8008C2A8,d(14,0,0,6)) # Waterfall-only original doubles menu branch.
    if word(source,file_offset(source,0x8063C704)) not in (d(14,4,4,0x1000),d(14,4,4,-0x3800)):raise ValueError('Arena clamp mismatch')
    put(0x8063C704,d(14,4,4,0x2000))
    entries=read_archive(common);identifier,table=entries[11];changed=bytearray(table)
    for record in (8,9,10):
        at=48+92*record
        if changed[at+0x4D:at+0x4F]!=b'\4\4':raise ValueError('Unexpected Waterfall table count')
        changed[at+0x4D:at+0x4F]=b'\6\6'
    # The prior patch shortened the stored length while keeping the original
    # physical slot. Permit its verified zero padding, never another resource.
    normalized=bytearray(common)
    pointers=word(common,word(common,0x18))
    headers=[word(common,pointers+4*i) for i in range(word(common,12))]
    header=headers[11];offset=word(common,header+4);stored=word(common,header+0x14)
    limit=min([word(common,h+4) for h in headers if word(common,h+4)>offset]+[len(common)-32])
    if any(common[offset+stored:limit]):raise ValueError('Nonzero bytes in resource padding')
    packed=encode(bytes(changed))
    if len(packed)>limit-offset:raise ValueError('Recompressed table exceeds verified physical slot')
    normalized[offset:limit]=packed+bytes(limit-offset-len(packed))
    struct.pack_into('>I',normalized,header+8,len(changed))
    struct.pack_into('>I',normalized,header+0x14,len(packed))
    common_out=bytes(normalized)
    after=read_archive(common_out)
    assert [(key,data) for key,data in after if key!=identifier]==[(key,data) for key,data in entries if key!=identifier]
    assert after[11][1]==bytes(changed)
    return bytes(out),common_out,{'status':'implemented-awaiting-native-and-Dolphin-validation',
        'scope_floor':1002,'waterfall_records':[8,9,10],'selected_count':6,'pair_count':2,
        'original_dol_sha256':sha(original),'source_dol_sha256':sha(source),'output_dol_sha256':sha(out),
        'output_common_sha256':sha(common_out),'reserved_end':f'{END:08x}',
        'original_blocks_read_from_user_copy':True,'other_floor_quartet_restoration_retained':True,
        'shiny_vm_helpers_not_overwritten':True,'dolphin_tested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('source','original','common','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();dol,common,report=prepare(a.source.read_bytes(),a.original.read_bytes(),a.common.read_bytes())
    a.output.mkdir(parents=True,exist_ok=True);(a.output/'main.dol').write_bytes(dol);(a.output/'common.fsys').write_bytes(common)
    (a.output/'waterfall.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
