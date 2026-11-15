"""Replay an already-delivered test.1 rental through the balance update."""
import json,sys
from pathlib import Path
from verify_integration import MenuReplay,register

def verify(capture,original,previous,current):
 old=MenuReplay(capture,original.read_bytes(),(previous/'main.dol').read_bytes())
 register(old,*[(previous/n).read_bytes() for n in ('common.fsys','mes_common.fsys','GSfsys.toc')])
 old.call(0x800e8594,(37,),limit=10000000);base=old.get(0x80453184);passes=bytes(old.uc.mem_read(base,159*0x6ec))
 h=MenuReplay(capture,original.read_bytes(),(current/'main.dol').read_bytes());register(h,*[(current/n).read_bytes() for n in ('common.fsys','mes_common.fsys','GSfsys.toc')])
 clone=0x81d00000;h.put(0x80453184,clone);mon=clone+37*0x6ec+0x1fc+2*140;scratch=0x81de0000
 def reset():h.uc.mem_write(clone,passes)
 def get(field):return h.call(0x803de52c,(mon,field,0))
 def set_value(field,value):h.put(scratch,value);h.call(0x803deca8,(mon,field,scratch))
 def deliver():h.call(0x800e8594,(37,),limit=10000000)
 def training():return ([get(f) for f in range(0x46,0x4c)],[get(f) for f in range(0xD,0x13)])
 reset();assert training()==([31]*6,[4,0,0,252,252,0])
 pid,ot=get(0),get(7);before=bytes(h.uc.mem_read(clone,len(passes)));deliver();after=bytes(h.uc.mem_read(clone,len(passes)))
 assert training()==([20]*6,[0]*6) and get(0)==pid and get(7)==ot
 offset=mon-clone;assert before[:offset]==after[:offset] and before[offset+140:]==after[offset+140:]
 dest=0x81d90000;h.uc.mem_write(dest,bytes(164));h.call(0x803dfd78,(mon,dest),limit=3000000)
 stats=[h.call(0x803e100c,(dest,f,0)) for f in range(163,169)];assert stats==[148,107,93,115,150,110]
 assert h.call(0x80058c34,(mon,))==1 and h.call(0x80058e8c,(mon,))==0
 deliver();assert bytes(h.uc.mem_read(clone,len(passes)))==after
 # A nickname, legal alternate move and held item do not block the stat migration.
 reset();custom=bytes.fromhex('012b012c012dffff')+b'\xff\xff'*7;h.uc.mem_write(scratch,custom);h.call(0x803deca8,(mon,116,scratch));set_value(0x36,126);set_value(6,157);deliver()
 assert training()==([20]*6,[0]*6) and get(0x36)==126 and get(6)==157
 h.call(0x803de52c,(mon,116,scratch));assert bytes(h.uc.mem_read(scratch,22))==custom
 # Preserve deliberately edited training; repeating delivery never resets it.
 reset();set_value(0x46,25);before=bytes(h.uc.mem_read(mon,140));deliver();assert bytes(h.uc.mem_read(mon,140))==before
 reset();set_value(0xD,8);before=bytes(h.uc.mem_read(mon,140));deliver();assert bytes(h.uc.mem_read(mon,140))==before
 return dict(passed=True,already_delivered_preset_migrated=True,ivs=[20]*6,evs=[0]*6,stats_hp_atk_def_speed_spatk_spdef=stats,pid_and_trainer_preserved=True,nickname_moves_item_preserved=True,user_edited_training_preserved=True,other_five_slots_and_all_other_passes_preserved=True,idempotent=True,gameplay_verified=False,save_file_written=False)
if __name__=='__main__':
 c,o,p,n,out=map(Path,sys.argv[1:]);r=verify(c,o,p,n);out.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
