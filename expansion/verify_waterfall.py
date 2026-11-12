"""Replay Waterfall rotation/scoring natively; outcomes/HP/UI are fixtures.

This is not a rendered battle or an Explosion/Self-Destruct combat test.
"""
import argparse,itertools,json,struct
from pathlib import Path
from prepare_campaign_doubles import read_archive,word,sha
from verify_series import SeriesNative,MANAGER,SOURCE,SDA2
from verify_native_doubles import CONFIG

class Team(SeriesNative):
    def seed(self,history,hp=(50,50),missing_flags=False):
        super().seed(history,hp,missing_flags)
        for side in (0,1):
            for slot in range(6):
                source=SOURCE+side*0x1000+slot*0x8C
                self.uc.mem_write(source,bytes([0x20+slot+side*16])*0x88+b'\0\0\x80\0')
    def process_floor(self,floor):
        self.run(0x80076B1C,registers={2:SDA2,29:0,30:0},colosseum=floor,
                 until=0x8007712C,instruction_limit=100000)
        base=(CONFIG+0x648,CONFIG+0x1420)
        return {'phase':self.uc.mem_read(CONFIG+0x18,1)[0],
                'count':self.uc.mem_read(CONFIG+0x19,1)[0],
                'manager_state':word(self.uc.mem_read(MANAGER+12,4),0),
                'outcome':self.uc.mem_read(MANAGER+0x52A,1)[0],
                'callbacks':self.callbacks,
                'payloads':[[bytes(self.uc.mem_read(b+i*0x8C,0x88)) for i in range(6)] for b in base],
                'presence':[[self.uc.mem_read(b+i*0x8C+0x8A,1)[0] for i in range(6)] for b in base]}

def verify(original,base,changed,common_before,common_after):
    old=read_archive(common_before);new=read_archive(common_after)
    assert len(old)==len(new)
    assert [x for i,x in enumerate(old) if i!=11]==[x for i,x in enumerate(new) if i!=11]
    a,b=old[11][1],new[11][1];allowed={48+r*92+f for r in (8,9,10) for f in (0x4D,0x4E)}
    assert {i for i,(x,y) in enumerate(zip(a,b)) if x!=y}==allowed
    native,previous,test=(Team(dol,b) for dol in (original,base,changed))
    cases=nonwater=0
    for length in (1,2,3):
        for history in itertools.product((0,1,2),repeat=length):
            if length==3 and (history[:2]==(0,0) or history[:2]==(1,1)):continue
            for hp in ((50,50),(75,25),(25,75)):
                for h in (native,test):h.seed(history,hp)
                wanted=native.process_floor(1002);actual=test.process_floor(1002)
                assert actual==wanted,(history,hp,{k:v for k,v in actual.items() if k not in ('payloads','presence')}, {k:v for k,v in wanted.items() if k not in ('payloads','presence')})
                assert actual['count']==2
                expected_pair=0 if actual['manager_state']==4 else length*2
                if expected_pair<6:
                    for side in (0,1):
                        assert actual['payloads'][side][:2]==[bytes([0x20+expected_pair+i+side*16])*0x88 for i in (0,1)]
                cases+=1
    for floor in range(1000,1010):
        if floor==1002:continue
        for history in ((0,),(1,),(0,1),(1,0),(0,0),(1,1),(0,1,0)):
            for h in (previous,test):h.seed(history)
            assert test.process_floor(floor)==previous.process_floor(floor),(floor,history)
            nonwater+=1
    menu=0
    for floor in range(1000,1010):
        expected=6 if floor==1002 else 4
        test.run(0x8008C254,colosseum=floor,format=1)
        assert test.uc.mem_read(CONFIG+0x19,1)[0]==expected,(floor,'initial')
        assert test.run(0x80641340,colosseum=floor)==expected
        menu+=2
    return {'status':'passed','native_waterfall_series_cases':cases,'other_floor_comparisons':nonwater,
            'menu_and_required_size_cases':menu,'changed_common_bytes':len(allowed),
            'output_dol_sha256':sha(changed),'output_common_sha256':sha(common_after),
            'source_model':'Original native pair rotation and scoring; six distinct synthetic snapshots',
            'stubs':['Synthetic battle outcomes','Synthetic HP values','Terminal UI callback and progression flags'],
            'limits':['No rendered Dolphin battle, save/reward execution or real move damage engine',
                      'Explosion, Self-Destruct and multi-target combat still require real game tests'],
            'dolphin_tested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('original','base','changed','common-before','common-after','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.original.read_bytes(),a.base.read_bytes(),a.changed.read_bytes(),a.common_before.read_bytes(),a.common_after.read_bytes())
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
