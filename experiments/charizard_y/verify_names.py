"""Native dynamic names, nickname bounds and party checksum regression."""
import json,sys
from pathlib import Path
from verify_integration import MenuReplay,register
from prepare_campaign_doubles import sha

def verify(capture,original,integrated):
 h=MenuReplay(capture,original.read_bytes(),(integrated/'main.dol').read_bytes())
 register(h,*[(integrated/n).read_bytes() for n in ('common.fsys','mes_common.fsys','GSfsys.toc')])
 base=h.get(0x80453184);data=bytes(h.uc.mem_read(base,159*0x6ec));clone=0x81d00000;h.uc.mem_write(clone,data);h.put(0x80453184,clone)
 h.call(0x800e8594,(37,),limit=10000000);records=[]
 for slot,name in [(0,'MEGA LUCARIO'),(1,'SNIVY'),(2,'MEGA CHARIZARD Y')]:
  mon=clone+37*0x6ec+0x1fc+slot*140;before=bytes(h.uc.mem_read(mon,140))
  dest=h.call(0x803e2604,(11,0));capacity=int.from_bytes(h.uc.mem_read(dest,2),'big');assert capacity==24
  fence=dest+8+25*2;h.uc.mem_write(fence,b'CANARY!!');h.call(0x803de52c,(mon,118,dest))
  assert bytes(h.uc.mem_read(fence,8))==b'CANARY!!' and bytes(h.uc.mem_read(mon,140))==before
  length=int.from_bytes(h.uc.mem_read(dest+2,2),'big')
  expected=b''.join((0x1de if c==' ' else 0x12b+ord(c)-65).to_bytes(2,'big') for c in name)+b'\xff\xff'
  assert length==len(name) and bytes(h.uc.mem_read(dest+8,len(expected)))==expected
  party=0x81dd0000;h.uc.mem_write(party,before+bytes(24));h.uc.mem_write(party+4,b'\x80\0\0\0');locked=bytes(h.uc.mem_read(party,164));h.call(0x803df700,(party,));assert slot==1 or bytes(h.uc.mem_read(party,164))==locked,(slot,bytes(h.uc.mem_read(party+4,4)).hex())
  records.append(dict(slot=slot,name=name,length=length,capacity=capacity,canary_untouched=True,deferred_checksum_preserved=None if slot==1 else True))
 mon=clone+37*0x6ec+0x1fc+2*140;scratch=0x81de0000;custom=bytes.fromhex('012b012c012dffff')+b'\xff\xff'*7;h.uc.mem_write(scratch,custom);h.call(0x803deca8,(mon,116,scratch));h.call(0x800e8594,(37,),limit=10000000)
 dest=h.call(0x803e2604,(11,0));h.call(0x803de52c,(mon,118,dest));assert bytes(h.uc.mem_read(dest+8,8))==custom[:8]
 metrics=h.call(0x8024fbbc,(0x8048062c,21777,1,0),limit=3000000)
 return dict(passed=True,records=records,custom_nickname_preserved=True,native_font_width=metrics&65535,native_font_height=metrics>>16,serialized_record_bytes=140,gameplay_verified=False,dol_sha256=sha((integrated/'main.dol').read_bytes()))
if __name__=='__main__':
 c,o,i,out=map(Path,sys.argv[1:]);r=verify(c,o,i);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
