"""Add Portuguese tilde letters using existing native font strokes.

Preserves every original glyph bitmap and metrics. Adds four sorted records
per font; no font-size or advance changes. Glyph data is packed 4-bit intensity.
"""
import struct

PAIRS={'ã':'â','õ':'ô','Ã':'Â','Õ':'Ô'}

def blocks(data):
    count=struct.unpack_from('>I',data,0)[0]//4
    offsets=list(struct.unpack_from('>'+str(count)+'I',data))
    assert offsets[0]==count*4 and offsets==sorted(offsets)
    return [data[a:b] for a,b in zip(offsets,offsets[1:]+[len(data)])]

def records(block):
    assert block[:4]==b'FONT'
    n=struct.unpack_from('>H',block,4)[0]
    return {struct.unpack_from('>H',block,8+10*i)[0]:block[8+10*i:18+10*i] for i in range(n)}

def bitmap(block,record):
    width,top,bottom=record[2:5];stride=(width+1)//2
    at=struct.unpack_from('>I',record,6)[0]
    return block[at:at+stride*(bottom-top+1)]

def unpack_pixels(record,data):
    w=record[2];stride=(w+1)//2
    return [[((data[y*stride+x//2]>>(4 if x%2==0 else 0))&15) for x in range(w)] for y in range(record[4]-record[3]+1)]

def pack_pixels(rows):
    return bytes((r[x]<<4)|(r[x+1] if x+1<len(r) else 0) for r in rows for x in range(0,len(r),2))

def extend_block(block):
    rs=records(block);added=[]
    for target,source in PAIRS.items():
        assert ord(target) not in rs
        base=rs[ord('a' if target.lower()=='ã' else 'o') if target.islower() else ord('A' if target=='Ã' else 'O')]
        base_pixels=unpack_pixels(base,bitmap(block,base))
        ink_top=next((y for y,row in enumerate(base_pixels) if any(n>=8 for n in row)),0)
        actual_top=base[3]+ink_top
        top=max(0,actual_top-5)
        accent_rows=actual_top-top
        if accent_rows<2:raise ValueError('No room above native letter body')
        template=bytearray(base);template[3]=top
        pixels=[[0]*base[2] for _ in range(base[4]-top+1)]
        for y,row in enumerate(base_pixels):
            at=base[3]-top+y
            if at>=0:pixels[at]=row[:]
        tilde=unpack_pixels(rs[ord('~')],bitmap(block,rs[ord('~')]))
        ink=[y for y,row in enumerate(tilde) if any(n>=8 for n in row)]
        tilde=tilde[min(ink):max(ink)+1]
        aw=min(len(tilde[0]),len(pixels[0]));ah=min(len(tilde),accent_rows-1)
        left=(len(pixels[0])-aw)//2
        for y in range(ah):
            for x in range(aw):pixels[y][left+x]=tilde[y*len(tilde)//ah][x*len(tilde[0])//aw]
        glyph=pack_pixels(pixels);added.append((ord(target),template,glyph))
    shift=10*len(added);out=bytearray(block[:8]);struct.pack_into('>H',out,4,len(rs)+len(added))
    all_records={c:bytearray(r) for c,r in rs.items()}
    for r in all_records.values():struct.pack_into('>I',r,6,struct.unpack_from('>I',r,6)[0]+shift)
    payload=bytearray(block[8+len(rs)*10:]);end=len(block)+shift
    for c,template,glyph in added:
        r=bytearray(template);struct.pack_into('>H',r,0,c);struct.pack_into('>I',r,6,end)
        all_records[c]=r;payload.extend(glyph);end+=len(glyph)
    for c,r in sorted(all_records.items()):out.extend(r)
    out.extend(payload)
    # Byte-exact preservation of every existing glyph and its dimensions.
    actual=records(out)
    for c,r in rs.items():
        assert r[:6]==actual[c][:6] and bitmap(block,r)==bitmap(out,actual[c])
    out.extend(bytes((-len(out))%4))
    return bytes(out)

def prepare(data):
    original=blocks(data);parts=[extend_block(b) for b in original]
    at=len(parts)*4;out=bytearray()
    for p in parts:out.extend(struct.pack('>I',at));at+=len(p)
    out.extend(b''.join(parts));assert len(blocks(out))==len(original)
    return bytes(out),{'fonts':len(parts),'added_letters':list(PAIRS),'original_bitmaps_preserved':True,'font_size_unchanged':True}
