"""Verify native Trade exchange and Rental Pass copy without substituting either.

Species are constructed by the actual opponent Pokemon constructor. Selection
marks model an already-confirmed, eligible trade. This does NOT exercise the
eligibility UI, campaign completion commit, NAND save, or save/load lifecycle.
"""
import argparse,itertools,json
from pathlib import Path
from prepare_campaign_doubles import sha,file_offset
from verify_sets import verify as construct

UI=0x81A10000;SESSION=0x81A20000;PASS=0x81A40000
STRIDE=0x8C;PAYLOAD=0x88;SDA=0x8062D600

def verify(capture,dol,deck,policy,original):
    # Check this test is exercising the original routines, not a replacement
    # that made the fixture succeed by accepting everything.
    for start,end in ((0x80131EB8,0x8013200C),(0x800CD764,0x800CD8A8)):
        assert dol[file_offset(dol,start):file_offset(dol,end)]==original[file_offset(original,start):file_offset(original,end)]
    counts={'exchanges':0,'species':0,'pass_copies':0};baseline=[None]
    def observer(h,mon,species):
        if baseline[0] is None:baseline[0]=bytes(h.uc.mem_read(h.session+0x44C,0x6EC))
        original_ui=h.get(SDA-0x7D78)
        h.uc.mem_write(UI,bytes(0x2000));h.put(UI+0x14C,SESSION);h.put(SDA-0x7D78,UI)
        incoming=bytes(h.uc.mem_read(mon,PAYLOAD))
        combinations=itertools.product(range(6),repeat=2) if species in (251,489,491,492,493) else ((species%6,(species//6)%6),)
        for player,opponent in combinations:
            h.uc.mem_write(SESSION+0x44C,baseline[0]);h.uc.mem_write(SESSION+0x1224,baseline[0])
            a=SESSION+0x648+player*STRIDE;b=SESSION+0x1420+opponent*STRIDE
            h.uc.mem_write(b,incoming)
            before_a=[bytes(h.uc.mem_read(SESSION+0x648+i*STRIDE,PAYLOAD)) for i in range(6)]
            before_b=[bytes(h.uc.mem_read(SESSION+0x1420+i*STRIDE,PAYLOAD)) for i in range(6)]
            h.uc.mem_write(UI+0x97C,bytes(24))
            # Native side 0 chooses the enemy, side 1 chooses the player.
            h.uc.mem_write(UI+0x97C+opponent,b'\1');h.uc.mem_write(UI+0x988+player,b'\1')
            h.call(0x80131EB8);h.abi()
            after_a=[bytes(h.uc.mem_read(SESSION+0x648+i*STRIDE,PAYLOAD)) for i in range(6)]
            after_b=[bytes(h.uc.mem_read(SESSION+0x1420+i*STRIDE,PAYLOAD)) for i in range(6)]
            wanted_a=before_a[:];wanted_b=before_b[:]
            wanted_a[player]=before_b[opponent];wanted_b[opponent]=before_a[player]
            assert after_a==wanted_a and after_b==wanted_b,(species,player,opponent)
            assert h.call(0x803DE52C,(a,5,0))==species
            counts['exchanges']+=1
        h.uc.mem_write(PASS,bytes(0x6EC))
        h.call(0x800CD764,(PASS,SESSION+0x44C));h.abi()
        for slot in range(6):
            assert bytes(h.uc.mem_read(PASS+0x1FC+slot*STRIDE,PAYLOAD))==after_a[slot]
        assert h.call(0x803DE52C,(PASS+0x1FC+player*STRIDE,5,0))==species
        counts['pass_copies']+=1;counts['species']+=1
        h.put(SDA-0x7D78,original_ui)
    construction=construct(capture,dol,deck,policy,constructed=observer)
    assert counts=={'exchanges':668,'species':493,'pass_copies':493},counts
    return {'status':'passed-native-exchange-and-pass-copy-fixtures',**counts,
            'native_exchange':'80131eb8','native_pass_copy':'800cd764',
            'pokemon_payload_bytes_compared':136,'untouched_team_members_checked':True,
            'new_species_all36_slot_pairings':True,'native_routines_unchanged':True,
            'construction':construction,'dol_sha256':sha(dol),'deck_sha256':sha(deck),
            'fixture':'Trade already confirmed; one selected slot per side',
            'limits':['Does not establish Trade UI eligibility or native unlock behavior',
                      'Pass copy in memory is not permanent save storage validation',
                      'No real battle, tournament completion, NAND write or save/load'],
            'dolphin_tested':False,'trade_save_tested':False}

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    for n in ('capture','dol','deck','policy','original','output'):p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args();r=verify(a.capture,a.dol.read_bytes(),a.deck.read_bytes(),json.loads(a.policy.read_text()),a.original.read_bytes())
    a.output.write_text(json.dumps(r,indent=2)+'\n');print(json.dumps({k:v for k,v in r.items() if k!='construction'},indent=2))
