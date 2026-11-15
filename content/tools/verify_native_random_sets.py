"""Offline PPC sampler + original game stat recalculation on private cloned RAM.

No CPU encounter hook is installed. Four new base-stat rows are substituted in
one existing-species row in the fixture; this does not install the new Pokemon.
"""
import argparse
import ctypes
import json
import os
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [str(ROOT/'content/tools'), str(ROOT/'content/tests'), str(ROOT/'mod-source'),
               str(ROOT/'expansion'), str(ROOT/'experiments/snivy'),
               str(ROOT/'experiments/mega_lucario'), '/workspace/pbr-coop']
from generate_rules import generate, DEFAULT
from test_random_sets import SharedSet, expected_stats
from verify_integration import register, MenuReplay
from prepare_campaign_doubles import sha

BASE = 0x81780000
RESULT = 0x81de4000
NATIVE_ORDER = [0, 1, 2, 5, 3, 4]


def verify(args):
    args.work.mkdir(parents=True, exist_ok=True)
    generate(DEFAULT, args.work)
    data = json.loads(DEFAULT.read_text())
    source = ROOT/'content/tools/random_sets.c'
    env = os.environ.copy()
    env['LD_LIBRARY_PATH'] = str(args.toolchain/'usr/lib/x86_64-linux-gnu')
    prefix = str(args.toolchain/'usr/bin/powerpc-linux-gnu-')
    def run(*cmd):
        return subprocess.check_output(list(map(str, cmd)), env=env, text=True)
    assert run(prefix+'gcc-14', '-dumpfullversion').strip() == '14.2.0'
    obj, elf, binary = [args.work/name for name in ('random.o', 'random.elf', 'random.bin')]
    script = args.work/'random.ld'
    script.write_text(f'SECTIONS {{ . = {BASE}; .payload : {{ *(.text*) *(.rodata*) *(.data*) *(.bss*) }} /DISCARD/ : {{ *(.eh_frame*) *(.comment*) *(.note*) }} }}')
    run(prefix+'gcc-14', '-mcpu=750', '-m32', '-mbig-endian', '-msoft-float', '-msdata=none',
        '-O2', '-ffreestanding', '-fno-builtin', '-fno-pic', '-fno-pie', '-fno-stack-protector',
        '-fno-asynchronous-unwind-tables', '-fno-unwind-tables', '-Wall', '-Wextra', '-Werror',
        '-I', args.work, '-c', source, '-o', obj)
    run(prefix+'ld', '-m', 'elf32ppc', '--build-id=none', '--no-undefined', '-T', script, '-o', elf, obj)
    run(prefix+'objcopy', '-O', 'binary', '--only-section=.payload', elf, binary)
    symbols = {p[2]: int(p[0], 16) for line in run(prefix+'nm', '-n', elf).splitlines() if len(p := line.split()) == 3}
    payload = binary.read_bytes()
    assert BASE + len(payload) < 0x81800000
    host = args.work/'random.so'
    subprocess.run(['gcc', '-O2', '-shared', '-fPIC', '-I', str(args.work), str(source), '-o', str(host)], check=True)
    lib = ctypes.CDLL(str(host))
    lib.shared_generate.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_uint32, ctypes.POINTER(SharedSet)]
    h = MenuReplay(args.capture, args.original.read_bytes(), args.dol.read_bytes())
    register(h, *((args.integrated/name).read_bytes() for name in ('common.fsys', 'mes_common.fsys', 'GSfsys.toc')))
    original_base = h.get(0x80453184)
    passes = bytes(h.uc.mem_read(original_base, 159*0x6ec))
    clone = 0x81d00000
    h.uc.mem_write(clone, passes)
    h.put(0x80453184, clone)
    h.call(0x800e8594, (37,), limit=10000000)
    mon = clone + 37*0x6ec + 0x1fc
    original_record = bytes(h.uc.mem_read(mon, 140))
    h.uc.mem_write(BASE, payload)
    row = h.get(h.get(0x80625184)+16) + 502*52
    scratch, boxed, party = 0x81de1000, 0x81d92000, 0x81d90000
    def get(pointer, field):
        return h.call(0x803de52c, (pointer, field, 0))
    def set_field(pointer, field, value):
        h.put(scratch, value)
        h.call(0x803deca8, (pointer, field, scratch))
    cases = []
    for profile, entry in enumerate(data['entries']):
        base = [entry['base_stats'][name] for name in data['stat_order']]
        h.uc.mem_write(row+30, bytes(base[i] for i in NATIVE_ORDER))
        for seed in (0, 1, 2, 42, 1234, 98765, 0x80000000, 0xffffffff):
            expected = SharedSet()
            assert lib.shared_generate(profile, seed, 50, ctypes.byref(expected)) == 1
            h.uc.mem_write(RESULT, bytes(ctypes.sizeof(expected)))
            assert h.call(symbols['shared_generate'], (profile, seed, 50, RESULT), limit=3000000) == 1
            raw = bytes(h.uc.mem_read(RESULT, 44))
            assert struct.unpack_from('>I', raw)[0] == expected.state
            assert list(struct.unpack_from('>4H', raw, 4)) == list(expected.moves)
            assert list(struct.unpack_from('>6H', raw, 12)) == list(expected.stats)
            assert list(raw[24:28]) == list(expected.pp)
            assert list(raw[28:34]) == list(expected.ivs)
            assert list(raw[34:40]) == list(expected.evs)
            assert raw[40] == expected.nature
            h.uc.mem_write(boxed, original_record)
            pid = get(boxed, 0)
            for step in range(25):
                candidate = (pid + step*0x100000) & 0xffffffff
                if candidate % 25 == expected.nature:
                    break
            else:
                raise AssertionError('Could not assign nature without changing PK4 block order')
            set_field(boxed, 0, candidate)
            ot = get(boxed, 7)
            if ((candidate ^ (candidate >> 16) ^ ot ^ (ot >> 16)) & 65535) < 8:
                set_field(boxed, 7, ot ^ 0x80000)
            for native, canonical in enumerate(NATIVE_ORDER):
                set_field(boxed, 0x46+native, expected.ivs[canonical])
                set_field(boxed, 0xd+native, expected.evs[canonical])
            h.uc.mem_write(party, bytes(0xa4))
            h.call(0x803dfd78, (boxed, party), limit=3000000)
            native_stats = [h.call(0x803e100c, (party, field, 0)) for field in range(163, 169)]
            assert native_stats == [expected.stats[i] for i in NATIVE_ORDER], (entry['key'], seed, native_stats, list(expected.stats))
            cases.append(dict(key=entry['key'], seed=seed, stats=list(expected.stats), nature=expected.nature,
                              ivs=list(expected.ivs), evs=list(expected.evs), moves=list(expected.moves)))
    assert bytes(h.uc.mem_read(original_base, len(passes))) == passes
    return dict(passed=True, kind='isolated PPC sampler + native PK4 setters and party stat calculation',
                cases=len(cases), six_stat_comparisons=len(cases)*6, sample_sets=cases[:2],
                source_sha256=sha(source.read_bytes()), rules_sha256=sha(DEFAULT.read_bytes()),
                compiled_rules_header_sha256=sha((args.work/'battle_rules.h').read_bytes()),
                payload_sha256=sha(payload), dol_sha256=sha(args.dol.read_bytes()),
                fixture_stat_row_replaced=True, fixture_species_alias=502, no_new_species_installed=True,
                original_capture_passes_preserved=True, optional_shiny_bonus_excluded=True,
                npc_generation_hook_installed=False, animated_battle_verified=False, results=cases)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('capture', 'original', 'integrated', 'dol', 'toolchain', 'work', 'output'):
        parser.add_argument('--'+key, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args)
    args.output.write_text(json.dumps(result, indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='results'}, indent=2))
