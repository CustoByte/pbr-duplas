"""Replay native coupon accessors and shop purchases with captured game data.

Shop rows/prices are fixtures; the getter, setter, balance check and inventory
grant execute real PPC. No GPU, shop menu or NAND save/load is exercised.
"""
import argparse, json
from pathlib import Path
from prepare_campaign_doubles import file_offset, sha
from unlimited_coupons import GET, SET, MAXIMUM, prepare
from verify_coop_draft import DraftReplay


def verify(capture, source):
    changed, report = prepare(source)
    old = DraftReplay(capture, source)
    new = DraftReplay(capture, changed)
    table = 0x80625174 + 0x44
    count = old.call(0x8039A214, (table,))
    assert 8 < count < 10000
    for key in range(count):
        expected = old.call(GET, (key,))
        actual = new.call(GET, (key,))
        assert actual == (MAXIMUM if key == 8 else expected), key
        new.abi()
    # Maximum substitution is restricted to coupons, including profile-init writes.
    write_cases = 0
    for mode in (0, 1):
        for key in (0, 7, 8, 9, 14, 25, 61, count - 1):
            for value in (0, 1, 100, MAXIMUM, 0xFFFFFFFF):
                a = DraftReplay(capture, source)
                b = DraftReplay(capture, changed)
                a.call(SET, (key, MAXIMUM if key == 8 else value, mode))
                b.call(SET, (key, value, mode))
                b.abi()
                for base, size in ((0x80000000, 0x1800000), (0x90000000, 0x4000000)):
                    # Compare data only: code and call stacks differ legitimately.
                    # Native save bitfield storage is in MEM2 in this capture.
                    if base == 0x90000000:
                        assert bytes(a.uc.mem_read(base, size)) == bytes(b.uc.mem_read(base, size)), (key, value, mode)
                write_cases += 1
    # A pre-existing empty balance cannot buy in stock; it can in this mod.
    # Use real shop 801420d8, including unmodified inventory grant 800ebdf4.
    purchases = 0
    for avatar in (0, 1, 5, 9):
        for price in (1, 500, 5000, 50000, 100000, MAXIMUM):
            a = DraftReplay(capture, source)
            b = DraftReplay(capture, changed)
            ui = 0x81A90000
            for h in (a, b):
                h.uc.mem_write(ui, bytes(0x800))
                h.put(0x8062D600 - 0x6360, ui)
                h.put(ui + 0x54, price)
                h.call(SET, (8, 0, 1))
            assert a.call(0x801420D8, (avatar, 0), limit=3000000) == 0
            for _ in range(3):
                assert b.call(0x801420D8, (avatar, 0), limit=3000000) == 1
                assert b.call(GET, (8,)) == MAXIMUM
                b.abi()
                purchases += 1
            # Inventory and all other saved data match the same native purchase
            # made with enough coupons in the unmodified game.
            a.call(SET, (8, MAXIMUM, 1))
            assert a.call(0x801420D8, (avatar, 0), limit=3000000) == 1
            a.call(SET, (8, MAXIMUM, 1))
            profile = a.call(0x801641E8)
            assert profile == b.call(0x801641E8)
            assert bytes(a.uc.mem_read(profile, 0x13000)) == bytes(b.uc.mem_read(profile, 0x13000))
    # Ensure the only executable changes are the two small accessor bridges.
    allowed = set()
    for start, end in report['changed_address_ranges']:
        begin = file_offset(source, int(start, 16))
        allowed.update(range(begin, begin + int(end, 16) - int(start, 16)))
    assert len(source) == len(changed)
    assert all(x == y or i in allowed for i, (x, y) in enumerate(zip(source, changed)))
    return {**report, 'status': 'passed-native-coupon-and-shop-fixtures',
            'properties_compared': count, 'native_write_cases': write_cases,
            'successful_native_purchases': purchases,
            'native_inventory_grant_executed': True,
            'unrelated_save_properties_unchanged': True,
            'limits': ['Synthetic shop rows; no real menu rendering or item unlock test',
                       'No Dolphin playthrough or NAND save/load'],
            'dol_sha256': sha(changed)}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('capture', 'source', 'output'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    result = verify(a.capture, a.source.read_bytes())
    a.output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
