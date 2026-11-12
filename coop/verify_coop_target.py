"""Replay native command/move/target UIs with attacker-owned input.

Uses private battle RAM, seeded controller caches and explicit widget animation
completion. Native menu opening, callback registration, target eligibility,
cursor, confirmation/cancel and target result execute unchanged in PPC.
No rendering, damage engine, hardware polling or NetPlay is simulated.
"""
import argparse,json,struct
from pathlib import Path
from coop_actor_bridge import UI,REGISTRY
from coop_input_router import STATE
from prepare_campaign_doubles import sha
from verify_coop_capture import verify_loaded_text
from verify_coop_switch import SwitchReplay,VALUE

CALLBACKS=(0x80060EEC,0x80061598,0x80061C98)
READY=(3,12,18)

class TargetReplay(SwitchReplay):
    def widget_done(self,family):
        widget=int.from_bytes(self.uc.mem_read(0x803FC7E8+family*2,2),'big',signed=True)
        assert 0<=widget<int.from_bytes(self.uc.mem_read(REGISTRY,2),'big')
        # Native 802585f4 reads this animation-completion field. The animation
        # engine is not executed; only this explicit fixture advances it.
        self.uc.mem_write(self.get(REGISTRY+8)+widget*0xC0+0x12,b'\0\3')

    def open_choice(self,family,position,code=14,enabled=True,target_hp=None):
        self.enable();self.uc.mem_write(STATE+4,bytes([int(enabled)]));self.seed(0,0)
        mode=family+5*position if family else 4*position
        self.call(0x8005F320,(0,mode,code,0))
        self.callback=self.get(REGISTRY+0x2C+4*self.get(0x806257E4))
        assert self.callback==CALLBACKS[family]
        self.call(self.callback)
        if target_hp is not None:
            assert family==2
            for bit,offset in enumerate((4,0x1C,8,0x20)):
                mon=self.get(UI+offset)
                hp=self.call(0x803E100C,(mon,0xA3,0)) if target_hp&(1<<bit) else 0
                self.put(VALUE,hp);self.call(0x803DEB54,(mon,0xA2,VALUE))
        self.widget_done(family);self.call(self.callback)
        assert self.state()==READY[family],(family,position,self.state())
        self.abi()

    def state(self):return int.from_bytes(self.uc.mem_read(0x80626ED4,2),'big')
    def snapshot(self):
        return (bytes(self.uc.mem_read(UI+0x64,0x50)),bytes(self.uc.mem_read(0x80626ED0,0x18)))
    def tick(self,p0=0,p1=0):
        self.seed(p0,p1);self.reads.clear()
        for off in (-0x6768,-0x6764,-0x6760):self.put(0x8062D600+off,0)
        self.call(self.callback);self.abi()
    def finish_target(self):
        assert self.state()==19
        for _ in range(2):self.widget_done(2);self.call(self.callback);self.abi()
        assert self.state()==21
        return int.from_bytes(self.uc.mem_read(0x80626EE0,2),'big')


def verify(source,changed,captures):
    counts={name:0 for name in ('disabled_native_callback_comparisons','owned_callback_comparisons',
        'wrong_player_blocked','release_barrier_cases','target_result_comparisons','target_profile_initializations',
        'survivor_native_reorder_cases','invalid_binding_cases','native_main_dialog_calls',
        'ally_target_owned_by_attacker_cases','fainted_target_mask_cases')}
    for capture in captures:
        verify_loaded_text(source,(capture/'mem1.bin').read_bytes())
        native=TargetReplay(capture,source);test=TargetReplay(capture,changed)
        for family in range(3):
            for position in (0,1):
                for event in (0,1,2,4,8,0x800,0x400):
                    for h in (native,test):h.mapping((0,1));h.health(15);h.open_choice(family,position,enabled=False)
                    native.tick(event);test.tick(event)
                    assert native.snapshot()==test.snapshot(),('disabled',family,position,event)
                    assert native.reads==test.reads
                    counts['disabled_native_callback_comparisons']+=1
                for topology in ('normal','reverse','p1_survives','p2_survives'):
                    for h in (native,test):
                        h.mapping((0,1));h.health(15)
                        if topology in ('p1_survives','p2_survives'):
                            owner=int(topology=='p2_survives');h.health(10 if owner else 5)
                            client,member=(0,3) if owner else (2,2)
                            h.call(0x803C96D4,(h.ctx,h.data,client,member))
                        elif topology=='reverse':h.mapping((1,0))
                    member=test.call(0x803CC838,(0,position));owner=member%2
                    for event in (1,2,4,8,0x800,0x400):
                        native.open_choice(family,position,enabled=False);test.open_choice(family,position)
                        before=test.snapshot()
                        test.tick(event if owner==0 else 0,event if owner==1 else 0)
                        assert test.snapshot()==before and not test.reads
                        counts['release_barrier_cases']+=1
                        native.tick();test.tick()
                        assert test.snapshot()==native.snapshot()
                        assert test.uc.mem_read(STATE+5,2)==bytes((3 if family==2 else 2,owner)),(family,position,topology,event,test.uc.mem_read(STATE+5,2).hex(),test.reads)
                        before=test.snapshot()
                        test.tick(event if owner==1 else 0,event if owner==0 else 0)
                        assert test.snapshot()==before
                        assert all(read[2]==owner for read in test.reads)
                        counts['wrong_player_blocked']+=1
                        test.tick(event if owner==0 else 0,event if owner==1 else 0);native.tick(event)
                        assert test.snapshot()==native.snapshot(),('routed',family,position,topology,event)
                        assert test.reads and test.reads[-1][2]==owner
                        assert [r[:2] for r in test.reads]==[r[:2] for r in native.reads]
                        counts['owned_callback_comparisons']+=1
                        if topology.endswith('survives'):counts['survivor_native_reorder_cases']+=1
        # Native target profiles, including multi-target bitmasks, retain their
        # original UI setup/result. Numeric profiles are game values, not a
        # claim that every move/ability combination has been exercised.
        for position in (0,1):
            for code in (1,4,5,10,11,14,15,0x25,0x8A,0x9B,0xCE,0xFF):
                for h in (native,test):h.health(15);h.mapping((0,1));h.open_choice(2,position,code,h is test)
                native.tick();test.tick();assert native.snapshot()==test.snapshot()
                counts['target_profile_initializations']+=1
                for direction in (0,1,2,4,8):
                    for h in (native,test):h.open_choice(2,position,code,h is test)
                    native.tick();test.tick()
                    if direction:
                        native.tick(direction);test.tick(direction if position==0 else 0,direction if position==1 else 0)
                    native.tick(0x800);test.tick(0x800 if position==0 else 0,0x800 if position==1 else 0)
                    assert test.snapshot()==native.snapshot()
                    assert test.state()==19
                    assert test.finish_target()==native.finish_target()
                    counts['target_result_comparisons']+=1
        for position,button,expected in ((0,3,4),(1,1,1)):
            for h in (native,test):
                h.health(15);h.mapping((0,1));h.open_choice(2,position,15,h is test)
                h.uc.mem_write(0x80626ED8,bytes([button]));h.tick()
            native.tick(0x800)
            test.tick(0x800 if position==0 else 0,0x800 if position==1 else 0)
            assert test.finish_target()==native.finish_target()==expected
            assert test.uc.mem_read(STATE+5,2)==bytes((3,position))
            counts['ally_target_owned_by_attacker_cases']+=1
        for position in (0,1):
            for mask in range(1,16):
                if not mask&(1<<(2*position)):continue
                for code in (15,255):
                    for h in (native,test):
                        h.health(15);h.mapping((0,1));h.open_choice(2,position,code,h is test,target_hp=mask)
                    native.tick();test.tick();native.tick(0x800)
                    test.tick(0x800 if position==0 else 0,0x800 if position==1 else 0)
                    assert test.snapshot()==native.snapshot(),('hp',position,mask,code,
                        test.snapshot(),native.snapshot())
                    result=test.finish_target();assert result==native.finish_target()
                    assert result and not result&~mask,(position,mask,code,result)
                    counts['fainted_target_mask_cases']+=1
        # Registered commands with stale ownership/session/actor must fail closed.
        for family in range(3):
            for corrupt in ('session','table','owner','actor','mode','dead_attacker'):
                test.health(15);test.mapping((0,1));test.open_choice(family,0)
                if corrupt=='session':test.put(STATE+0x1C,test.session+4)
                if corrupt=='table':test.uc.mem_write(STATE+9,b'\0')
                if corrupt=='owner':test.uc.mem_write(STATE+10,b'\xff')
                if corrupt=='actor':test.uc.mem_write(UI+0x64,b'\0\2')
                if corrupt=='mode':test.uc.mem_write(0x80626EE4,b'\x08')
                if corrupt=='dead_attacker':test.health(14)
                before=test.snapshot();test.tick(0x800,0x800)
                assert test.snapshot()==before and not test.reads,(family,corrupt)
                counts['invalid_binding_cases']+=1
        # Both branches of main-command input and its native yes/no dialog use
        # the same actor-owned scope. Execute real BL sites with native cursor.
        for position,flags,callsite in ((0,0,0x80061114),(1,0,0x80061138),(1,1,0x80061150),(1,0,0x80061438)):
            test.health(15);test.mapping((0,1));test.open_choice(0,position)
            args=(flags,2 if callsite==0x80061438 else 1,0,1)
            test.seed(0,0);test.event(callsite,args,(callsite+4,))
            test.seed(0x800 if position==0 else 0,0x800 if position==1 else 0)
            test.reads.clear();test.event(callsite,args,(callsite+4,))
            assert test.reads[-1][2]==position
            counts['native_main_dialog_calls']+=1
        test.intact_switch()
        print(f'{capture.name}: native command/move/target checks passed',flush=True)
    return {'status':'passed',**counts,'prototype_sha256':sha(changed),'enabled_at_boot':False,
        'native_callbacks':{'command':'80060eec','moves':'80061598','targets':'80061c98'},
        'native_target_eligibility':'80063a40','target_owner':'Attacker logical party owner; target ownership does not transfer input',
        'input_cursor_target_getter_or_callback_stubs':[],
        'audio_and_psq_exceptions':'Same narrow feedback stubs and four context PSQ skips as verify_coop_draft',
        'fixtures':['Owner tables and button/connection caches','Native widget animation-complete field',
                    'Native HP setter and mapping fixtures/native reorder; no damage engine'],
        'limits':['No rendered UI, physical controllers, complete battle or NetPlay',
                  'Native numeric target profiles tested; not every move/ability interaction',
                  'Secondary summary callback, special tournament screens, owner indicator and end-battle lifecycle remain unfinished'],
        'private_data_published':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('source','changed','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--captures',type=Path,nargs=2,required=True)
    a=p.parse_args();report=verify(a.source.read_bytes(),a.changed.read_bytes(),a.captures)
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
