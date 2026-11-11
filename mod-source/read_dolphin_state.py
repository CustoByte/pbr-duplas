"""Read-only extraction of a Dolphin RPBE01 state for private debugging.

Uses the system liblz4 via ctypes. Never publishes snapshots or changes game saves.
Memory/CPU locations are corroborated by DOL signature, memory configuration,
markers and PPC SDA registers, not inferred from the filename extension.
"""
import argparse,ctypes,ctypes.util,json,struct
from pathlib import Path
from prepare_campaign_doubles import word


def decode(data):
    if len(data)<64 or data[:6]!=b'RPBE01':raise ValueError('Not an RPBE01 Dolphin state')
    cookie,length=struct.unpack_from('<II',data,24)
    if not 0<length<1024:raise ValueError('Invalid version string')
    offset=32+length
    version=data[32:offset].decode('utf-8')
    header_version,compression,reserved,size=struct.unpack_from('<HHIQ',data,offset)
    if header_version!=1 or size>512*1024*1024:raise ValueError('Unsupported state header/size')
    offset+=16
    if compression==0:
        raw=data[offset:]
        if len(raw)!=size:raise ValueError('Raw state size mismatch')
    elif compression==1:
        library=ctypes.util.find_library('lz4')
        if not library:raise ValueError('System liblz4 required')
        lib=ctypes.CDLL(library)
        lib.LZ4_decompress_safe.argtypes=[ctypes.c_void_p,ctypes.c_void_p,ctypes.c_int,ctypes.c_int]
        lib.LZ4_decompress_safe.restype=ctypes.c_int
        raw=bytearray()
        while len(raw)<size:
            count=struct.unpack_from('<i',data,offset)[0];offset+=4
            if count<=0 or offset+count>len(data):raise ValueError('Invalid LZ4 block')
            capacity=min(size-len(raw),0x7E000000)
            buffer=ctypes.create_string_buffer(capacity)
            result=lib.LZ4_decompress_safe(data[offset:offset+count],buffer,count,capacity)
            if result<=0:raise ValueError('LZ4 decode failed')
            raw.extend(buffer.raw[:result]);offset+=count
        if offset!=len(data) or len(raw)!=size:raise ValueError('State stream size mismatch')
        raw=bytes(raw)
    else:raise ValueError('Unsupported state compression')
    return raw,{'game_id':'RPBE01','dolphin_version':version,'state_version':cookie-0xBAADBABE,'decoded_bytes':size}


def extract(raw,dol):
    text_offset=word(dol,0);signature=dol[text_offset+64:text_offset+128]
    location=raw.find(signature)-0x4040
    if location<18:raise ValueError('Guest memory signature missing')
    rs,ls,fake,fs,ex,es=struct.unpack_from('<II?I?I',raw,location-18)
    if (rs,ls,fake,fs,ex,es)!=(0x2000000,0x40000,False,0,True,0x4000000):raise ValueError('Unsupported memory layout')
    marker=location+rs+ls
    if raw[marker:marker+8]!=b'B\0\0\0'*2:raise ValueError('RAM markers inconsistent')
    exram=marker+8
    if raw[exram+es:exram+es+4]!=b'B\0\0\0':raise ValueError('EXRAM marker inconsistent')
    matches=[];offset=0;needle=struct.pack('<I',0x8062D600)
    while True:
        offset=raw.find(needle,offset)
        if offset<0:break
        start=offset-52
        if start>=0 and start+136<=len(raw):
            registers=struct.unpack_from('<34I',raw,start)
            if registers[2]==0x806308E0 and 0x80000000<=registers[32]<0x80400000:
                matches.append((start,registers))
        offset+=1
    if len(matches)!=1:raise ValueError('CPU register block ambiguous')
    start,registers=matches[0]
    return raw[location:location+rs],raw[exram:exram+es],{
        'offset':start,'gpr':[f'{v:08x}' for v in registers[:32]],'pc':f'{registers[32]:08x}','npc':f'{registers[33]:08x}'}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--state',type=Path,required=True);p.add_argument('--dol',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();raw,header=decode(args.state.read_bytes());mem1,mem2,cpu=extract(raw,args.dol.read_bytes())
    args.output.mkdir(parents=True,exist_ok=False)
    for name,data in [('mem1.bin',mem1),('mem2.bin',mem2)]:args.output.joinpath(name).write_bytes(data)
    args.output.joinpath('cpu-registers.json').write_text(json.dumps(cpu,indent=2)+'\n')
    args.output.joinpath('state-header.json').write_text(json.dumps(header,indent=2)+'\n')
    print(json.dumps(header,indent=2))
