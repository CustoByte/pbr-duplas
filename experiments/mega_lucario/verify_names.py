"""Native regression for expanded display names and deferred party checksums.

Inputs are private captures/builds. Allocation uses MenuReplay's scratch fixture;
this verifies native getters, not rendering or a complete Dolphin battle.
"""
import json
import sys
from pathlib import Path
from verify_integration import register, MenuReplay
from prepare_campaign_doubles import sha

FULL = bytes.fromhex('0137012f0131012b01de0136013f012d012b013c01330139ffff')
MARKER = bytes.fromhex('013701ae0136013f012d012b013c01330139ffffffff')


def verify(capture, original, integrated, fixed):
    old, candidate = original.read_bytes(), fixed.read_bytes()
    h = MenuReplay(capture, old, candidate)
    register(h, *( (integrated / name).read_bytes() for name in
                  ('common.fsys', 'mes_common.fsys', 'GSfsys.toc')))
    original_base = h.get(0x80453184)
    passes = bytes(h.uc.mem_read(original_base, 159 * 0x6ec))
    clone = 0x81d00000
    h.uc.mem_write(clone, passes)
    h.put(0x80453184, clone)
    h.call(0x800e8594, (37,), limit=10000000)
    mega = clone + 37 * 0x6ec + 0x1fc
    record = bytes(h.uc.mem_read(mega, 0x8c))
    raw = 0x81de0000
    h.call(0x803de52c, (mega, 116, raw))
    assert bytes(h.uc.mem_read(raw, 22)) == MARKER
    names = []
    for slot, length in ((0, 12), (1, 5), (2, 9)):
        mon = mega + slot * 0x8c
        before = bytes(h.uc.mem_read(mon, 0x8c))
        dest = h.call(0x803e2604, (11, 0))
        assert bytes(h.uc.mem_read(dest, 2)) == b'\x00\x10'
        fence = dest + 42  # capacity 16: two header halfwords, magic, 17 glyphs
        h.uc.mem_write(fence, b'CANARY!!')
        h.call(0x803de52c, (mon, 118, dest))
        assert int.from_bytes(h.uc.mem_read(dest + 2, 2), 'big') == length
        assert bytes(h.uc.mem_read(fence, 8)) == b'CANARY!!'
        assert bytes(h.uc.mem_read(mon, 0x8c)) == before
        if slot == 0:
            assert bytes(h.uc.mem_read(dest + 8, 26)) == FULL
        names.append(dict(slot=slot, length=length, capacity=16, canary_untouched=True))
    # A player's own nickname must not be replaced by the species display name.
    custom = bytes.fromhex('012b012c012dffff') + b'\xff\xff' * 7
    h.uc.mem_write(raw, custom)
    h.call(0x803deca8, (mega, 116, raw))
    dest = h.call(0x803e2604, (11, 0))
    h.call(0x803de52c, (mega, 118, dest))
    assert bytes(h.uc.mem_read(dest + 2, 2)) == b'\x00\x03'
    assert bytes(h.uc.mem_read(dest + 8, 8)) == custom[:8]
    # Repair an already-delivered Mega whose original constructor left it empty.
    h.uc.mem_write(raw, bytes(22))
    h.call(0x803deca8, (mega, 116, raw))
    h.call(0x800e8594, (37,), limit=10000000)
    assert bytes(h.uc.mem_read(mega, 0x8c)) == record
    assert bytes(h.uc.mem_read(original_base, len(passes))) == passes
    # Exercise a valid battle-party condition: lock with a deferred checksum.
    # The published boxed getter incorrectly flags this valid party record.
    lock_results = []
    scratch = 0x81de1000
    for label, executable in (('published', (integrated / 'main.dol').read_bytes()),
                              ('fixed', candidate)):
        vm = MenuReplay(capture, old, executable)
        vm.uc.mem_write(scratch, record + bytes(24))
        vm.uc.mem_write(scratch + 4, b'\x80\x00\x00\x00')
        before = bytes(vm.uc.mem_read(scratch, 0xa4))
        vm.call(0x803df700, (scratch,), limit=3000000)
        after = bytes(vm.uc.mem_read(scratch, 0xa4))
        if label == 'fixed':
            assert after == before
        else:
            assert after[4:6] == b'\xa0\x00'
        lock_results.append(dict(build=label, flags=after[4:6].hex(), unchanged=after == before))
    metrics = h.call(0x8024fbbc, (0x8048062c, 21776, 1, 0), limit=3000000)
    assert metrics >> 16 == 25 and metrics & 65535 == 120
    return dict(passed=True, names=names, full_name='MEGA LUCARIO',
                native_font_width=120, native_font_height=25,
                serialized_record_bytes=140, custom_nickname_preserved=True,
                existing_empty_name_repaired=True, original_passes_preserved=True,
                deferred_checksum_regression=lock_results,
                dol_sha256=sha(candidate), gameplay_verified=False,
                reported_invalid_read_reproduced=False)


def verify_user_capture(capture, published, fixed):
    """Use the actual user's registered tables, without replacing their data."""
    h = MenuReplay(capture, published.read_bytes(), fixed.read_bytes())
    base = h.get(0x80453184)
    before = bytes(h.uc.mem_read(base, 159 * 0x6ec))
    clone = 0x81d00000
    h.uc.mem_write(clone, before)
    h.put(0x80453184, clone)
    mon = clone + 37 * 0x6ec + 0x1fc
    assert h.call(0x803de52c, (mon, 5, 0)) == 502
    h.call(0x800e8594, (37,), limit=10000000)
    dest = h.call(0x803e2604, (11, 0))
    h.call(0x803de52c, (mon, 118, dest))
    assert bytes(h.uc.mem_read(dest + 8, 26)) == FULL
    assert bytes(h.uc.mem_read(base, len(before))) == before
    return dict(native_name_verified=True, registered_tables_replaced=False,
                original_memory_untouched=True,
                captured_executable_sections_verified=h.checked_sections,
                battle_invalid_read_reproduced=False)


if __name__ == '__main__':
    capture, original, integrated, fixed, output = map(Path, sys.argv[1:6])
    result = verify(capture, original, integrated, fixed)
    if len(sys.argv) == 7:
        result['user_capture'] = verify_user_capture(Path(sys.argv[6]), integrated / 'main.dol', fixed)
    output.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
