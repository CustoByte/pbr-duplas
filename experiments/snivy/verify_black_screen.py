"""Reproduce the actual captured allocation failure and complete native loading.

The only platform fixture skips OS cache-maintenance syscalls because Unicorn
memory is coherent. Allocation, resource registration, SDR relocation and the
waiting routine execute unchanged. No GPU rendering or full battle is claimed.
"""
import argparse
import json
from pathlib import Path
from unicorn import UC_HOOK_CODE, ppc_const as ppc
from verify_vm_wait import Replay
from prepare_campaign_doubles import word, sha
from runtime_build import build
from prepare_campaign_doubles import file_offset


def verify(capture, baseline, current, payload, compact):
    memory = (capture / 'mem1.bin').read_bytes()
    dol = current.read_bytes()
    sections = []
    for i in range(7):
        off, address, size = (word(dol, field + i * 4) for field in (0, 0x48, 0x90))
        if not size:
            continue
        expected, actual = dol[off:off + size], memory[address - 0x80000000:address - 0x80000000 + size]
        # Existing translation formatter writes temporary status text into its
        # own reserved buffer. Executable instructions must still match.
        differences = [address + j for j, (a, b) in enumerate(zip(expected, actual)) if a != b]
        assert all(0x80643FE4 <= a < 0x80644004 for a in differences), (i, differences[:8])
        sections.append(i)
    h = Replay(capture)
    handle = 0x80BBE1A8
    assert h.get(handle) == 0x2000 and h.get(handle + 0x14) == 12
    assert h.call(0x801E00FC, (0x2000, 0x63EA0400)) == 0
    old_size = 0x7C7468
    assert h.call(0x80008CC8, (0x2000, 0x63EA0400, old_size), limit=3000000) == 0
    data = compact.read_bytes()
    assert len(data) < 3 * 1024 * 1024
    at = h.call(0x80008CC8, (0x2000, 0x63EA0400, len(data)), limit=3000000)
    assert at != 0
    h.uc.mem_write(at, data)
    cache_syscalls = (0x8026F024, 0x8026F054, 0x8026F084)
    for address in cache_syscalls:
        h.uc.hook_add(UC_HOOK_CODE, lambda u, a, size, unused: u.reg_write(ppc.UC_PPC_REG_PC, a + 4), begin=address, end=address)
    assert h.call(0x80008D80, (0x2000, 0x63EA0400, len(data)), limit=30000000) == at
    assert h.call(0x801E00FC, (0x2000, 0x63EA0400)) == at
    references = h.call(0x80039254, (0x2000, 0x63EA0400), limit=1000000)
    assert references > 0
    target = build(baseline.read_bytes(), json.loads(payload.read_text()))
    # Execute the actual BL hook and selective summary bridge, stopping before
    # the unchanged native look-at setter (no model/GPU fixture required).
    for i in range(7):
        off, address, size = (word(target, field + i * 4) for field in (0, 0x48, 0x90))
        if size:
            h.uc.mem_write(address, target[off:off + size])
    stop = h.uc.hook_add(UC_HOOK_CODE, lambda u, a, s, d: u.emu_stop(), begin=0x8003AE58, end=0x8003AE58)
    import struct
    for species in (1, 493, 494, 495, 500, 501, 502):
        model, vector = 0x81D80000, 0x81D81000
        h.uc.mem_write(model + 0x510, struct.pack('>H', species))
        h.uc.mem_write(vector, struct.pack('>3f', 7, 0, 20))
        h.uc.reg_write(ppc.UC_PPC_REG_2, 0x806308E0)
        h.uc.reg_write(ppc.UC_PPC_REG_3, model)
        h.uc.reg_write(ppc.UC_PPC_REG_4, vector)
        h.uc.emu_start(0x80104740, 0x81FFF000, count=20)
        assert h.uc.reg_read(ppc.UC_PPC_REG_PC) == 0x8003AE58
        assert h.uc.reg_read(ppc.UC_PPC_REG_LR) == 0x80104744
        assert struct.unpack('>3f', h.uc.mem_read(vector, 12)) == ((-3., 0., 20.) if species == 501 else (7., 0., 20.))
    h.uc.hook_del(stop)
    return dict(passed=True, kind='native replay of supplied black-screen state',
                identical_executable_sections_except_known_status_buffer=sections,
                capture_dolphin=json.loads((capture / 'state-header.json').read_text())['dolphin_version'],
                fsys_file_read_finished_but_resource_missing=True,
                old_unpacked_bytes=old_size, original_allocation_failed=True,
                compact_unpacked_bytes=len(data), compact_sha256=sha(data),
                reduction_percent=round(100 * (1 - len(data) / old_size), 2),
                native_compact_allocation_succeeded=True, native_scene_relocation_succeeded=True,
                native_resource_ready=True, captured_wait_routine_returned=True,
                summary_orientation_only_changes_snivy=True, summary_orientation_boundary_cases=7,
                cache_maintenance_syscalls_skipped=[f'{a:08x}' for a in cache_syscalls],
                limits=['No native allocation, resource, parser or waiting routine is substituted',
                        'Not an actual Dolphin battle, GPU render or save/load test'])


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('capture', 'baseline', 'current', 'payload', 'compact', 'report'):
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    r = verify(a.capture, a.baseline, a.current, a.payload, a.compact)
    a.report.write_text(json.dumps(r, indent=2) + '\n')
    print(json.dumps(r, indent=2))
