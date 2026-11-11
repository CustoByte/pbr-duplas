"""Greedy Okumura LZSS encoder, 4096-byte zero ring, initial cursor 0xFEE."""
from collections import defaultdict,deque
import struct,zlib


def encode(payload):
    virtual=bytes(4096)+payload
    candidates=defaultdict(deque)
    for index in range(4094): candidates[virtual[index:index+3]].append(index)
    cursor=4096;tokens=[]
    while cursor<len(virtual):
        best_length,best_index=0,0
        key=virtual[cursor:cursor+3]
        choices=candidates[key]
        while choices and choices[0]<cursor-4096: choices.popleft()
        if len(key)==3:
            limit=min(18,len(virtual)-cursor)
            for index in reversed(choices):
                length=0
                while length<limit and virtual[index+length]==virtual[cursor+length]:length+=1
                if length>best_length:best_length,best_index=length,index
                if length==limit:break
        if best_length>=3:
            offset=(0xFEE+best_index)&4095
            tokens.append((False,bytes((offset&255,((offset>>4)&0xF0)|(best_length-3)))))
            advance=best_length
        else:
            tokens.append((True,virtual[cursor:cursor+1]));advance=1
        for index in range(cursor,cursor+advance):
            if index+3<=len(virtual):candidates[virtual[index:index+3]].append(index)
        cursor+=advance
    stream=bytearray()
    for start in range(0,len(tokens),8):
        group=tokens[start:start+8]
        stream.append(sum(int(literal)<<bit for bit,(literal,_) in enumerate(group)))
        for _,data in group:stream.extend(data)
    return struct.pack('>4sIII',b'LZSS',len(payload),16+len(stream),zlib.crc32(payload))+stream
