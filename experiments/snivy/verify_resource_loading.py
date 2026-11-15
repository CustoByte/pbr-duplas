"""Replay the native path builder, FSYS entry lookup and texture type dispatch.

Uses private FSYS bytes; no GPU, disc I/O, model render or full battle is emulated.
"""
import argparse
import json
from pathlib import Path
import struct
from unicorn import ppc_const as ppc, UC_HOOK_CODE

from verify_pass_delivery import MenuReplay
from runtime_build import build
from catalog import append_archive, relocate
from prepare_campaign_doubles import word

GUARDS = ((0x8005D1F4, 0x8005D204, 0x8005D1FC),
          (0x8005D4A4, 0x8005D4E0, 0x8005D4AC),
          (0x8005DB8C, 0x8005DB9C, 0x8005DB94),
          (0x8005DE38, 0x8005DE70, 0x8005DE40))


def verify(capture, baseline, previous, previous_catalog, catalog, payload, assets):
    original = baseline.read_bytes()
    old = MenuReplay(capture, original, previous.read_bytes())
    new = MenuReplay(capture, original, build(original, json.loads(payload.read_text())))
    handle, buffer, toc = 0x81DA0000, 0x81DA0100, 0x81B80000
    paths = []
    # Reproduce the bad catalog from test1, then execute the fixed native path builder.
    from prepare_campaign_doubles import sha
    bad_catalog = previous_catalog.read_bytes()
    for replay, data in ((old, bad_catalog), (new, append_archive(catalog.read_bytes()))):
        replay.uc.mem_write(toc, relocate(data, toc))
        replay.put(0x80627B5C, toc)
        replay.uc.mem_write(handle, bytes(0x48))
        replay.put(handle, 0x2000)
        replay.uc.mem_write(buffer, bytes(256))
        assert replay.call(0x8024C3EC, (handle, buffer), limit=3000000) == 1
        paths.append(bytes(replay.uc.mem_read(buffer, 256)).split(b'\0', 1)[0].decode())
    assert paths == ['pkx_501.fsys.fsys', 'pkx_501.fsys'], paths
    checks = 0
    values = (0, 1, 493, 494, 495, 496, 500, 501, 502, 65535, 0xFFFFFFFF)
    for site, accept, reject in GUARDS:
        for value in values:
            outcomes = []
            for replay in (old, new):
                replay.uc.reg_write(ppc.UC_PPC_REG_4, value)
                replay.uc.reg_write(ppc.UC_PPC_REG_CR, 0)
                stop = replay.uc.hook_add(UC_HOOK_CODE, lambda uc, address, size, unused: uc.emu_stop(), begin=site + 4, end=site + 4)
                replay.uc.emu_start(site, 0x81FFFFFF, count=16)
                replay.uc.hook_del(stop)
                assert replay.uc.reg_read(ppc.UC_PPC_REG_PC) == site + 4
                # Execute exactly the existing conditional branch after the guard.
                replay.uc.emu_start(site + 4, 0x81FFFFFF, count=1)
                outcomes.append(replay.uc.reg_read(ppc.UC_PPC_REG_PC))
            if value == 501:
                assert outcomes == [reject, accept], (hex(site), outcomes)
            else:
                assert outcomes[0] == outcomes[1], (hex(site), value, outcomes)
            checks += 1
    records = []
    for name, resource in (('menu_face.fsys', 0x7BEA0C00), ('menu_pokemon.fsys', 0x6BEA0C00)):
        data = (assets / name).read_bytes()
        new.uc.mem_write(0x93000000, data)
        new.uc.mem_write(handle, bytes(0x48))
        new.put(handle + 0x20, 0x93000000)
        new.uc.mem_write(handle + 0x2E, b'\1')
        index = new.call(0x8024C794, (handle, resource), limit=1000000)
        assert index == 645, (name, index)
        entry = new.call(0x8024AA18, (handle, index))
        filetype = new.get(entry + 0x20)
        assert filetype == 6, (name, filetype)
        handler = new.call(0x8024A7EC, (filetype,))
        assert handler != 0
        assert new.call(0x8024A7EC, (14,)) != handler
        records.append(dict(archive=name, entry_index=index, filetype=filetype, native_handler_found=True, sha256=sha(data)))
    return dict(passed=True, previous_native_path=paths[0], fixed_native_path=paths[1],
                portrait_request_and_draw_guards=4, native_boundary_cases=checks,
                legacy_guard_results_preserved=True, native_fsys_texture_lookups=records,
                old_portrait_handler_type_14_differs_from_native_gtx_handler=True,
                limits=['No DVD I/O, GPU texture upload, model render or full battle',
                        'Actual Windows Dolphin retest required for summary responsiveness and battle transition'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('capture', 'baseline', 'previous', 'previous-catalog', 'catalog', 'payload', 'assets', 'report'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    result = verify(a.capture, a.baseline, a.previous, a.previous_catalog, a.catalog, a.payload, a.assets)
    a.report.write_text(json.dumps(result, indent=2) + '\n')
    print(json.dumps(result, indent=2))
