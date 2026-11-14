"""Native six-member packing and two-member Waterfall battle handoff.

The marker decoder, validity getter, name registration, scratch allocation and
AI selector are explicit fixtures inherited from verify_handoff. Actual packing,
copy, participant limit and party append execute natively; no real combat.
"""
import argparse,itertools,json,struct
from pathlib import Path
from unicorn import ppc_const as ppc
from prepare_campaign_doubles import read_archive,sha
from verify_handoff import HandoffNative
from verify_native_doubles import CONFIG,Native

def verify(dol,common):
    h=HandoffNative(dol,read_archive(common)[11][1]);packing=transfers=gates=0
    for order in itertools.permutations(range(6)):
        orders=(order,tuple(reversed(order)));h.seed(orders)
        assert h.pack()==6
        for side in (0,1):
            expected=[0xAB000000+side*0x100+i for i in orders[side]]
            assert h.packed_markers(side)==expected
            actual=h.transfer(side,mode=3,phase=1)
            assert actual==expected[:2],(orders,side,actual,expected[:2])
            packing+=1;transfers+=1
    # Use a separate emulator so prior full-loop translations do not share the
    # stop address with this isolated branch probe.
    h=Native(dol,read_archive(common)[11][1])
    for floor in range(1000,1010):
        for format in (1,4):
            h.run(0x801733D4,colosseum=floor,registers={0:format,20:6},until=0x801733D8)
            assert h.uc.reg_read(ppc.UC_PPC_REG_0)==format
            assert h.uc.reg_read(ppc.UC_PPC_REG_20)==(2 if floor==1002 else 4)
            gates+=1
    return {'status':'passed-native-packing-and-waterfall-party-limit',
            'six_member_orderings':720,'side_specific_packing_checks':packing,
            'native_two_member_battle_party_appends':transfers,'floor_and_format_gate_checks':gates,
            'no_third_pokemon_appended':True,'dol_sha256':sha(dol),'common_sha256':sha(common),
            'stubs':['Marker Pokemon decoder and validity getter','Name registration',
                     'Temporary allocation/free','Opponent-selection fixture (disabled in tested AI=0 cases)'],
            'limits':['Subsequent-pair rotation and scoring tested separately in verify_waterfall',
                      'No rendered battle, live switch UI, damage, Explosion or save/reward execution'],
            'dolphin_tested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('dol','common','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.dol.read_bytes(),a.common.read_bytes())
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps(r,indent=2))
