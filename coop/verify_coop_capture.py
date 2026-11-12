"""Check a private command-screen capture against the exact coop base.

The report contains verification results only. Never copy private RAM or the
source savestate into the public repository. This does not identify an actor
or prove a complete Dolphin/NetPlay session works.
"""
import argparse
import json
import struct
from pathlib import Path

from coop_input_router import SOURCE_SHA, prepare_router
from prepare_campaign_doubles import sha
from verify_coop_input import verify


def verify_loaded_text(dol, mem1):
    if sha(dol) != SOURCE_SHA:
        raise ValueError('Expected the unmodified v0.9.1 coop base')
    if len(mem1) != 0x2000000:
        raise ValueError('Expected a complete 32 MiB MEM1 bank')
    sections = []
    for i in range(7):
        offset, address, size = (
            struct.unpack_from('>I', dol, base + i * 4)[0]
            for base in (0, 0x48, 0x90)
        )
        if not size:
            continue
        relative = address - 0x80000000
        if relative < 0 or relative + size > len(mem1) or offset + size > len(dol):
            raise ValueError('Executable section is outside the available banks')
        if dol[offset:offset + size] != mem1[relative:relative + size]:
            raise ValueError(f'Loaded executable differs in text section {i}')
        sections.append({'index': i, 'bytes': size, 'status': 'identical'})
    if not sections:
        raise ValueError('No executable sections found')
    return sections


def capture_report(source, diagnostics):
    header = json.loads((diagnostics / 'state-header.json').read_text())
    if header.get('game_id') != 'RPBE01':
        raise ValueError('Expected an RPBE01 capture')
    sections = verify_loaded_text(source, (diagnostics / 'mem1.bin').read_bytes())
    if (diagnostics / 'mem2.bin').stat().st_size != 0x4000000:
        raise ValueError('Expected a complete 64 MiB MEM2 bank')
    router = verify(source, prepare_router(source), diagnostics)
    return {
        'capture': {k: header[k] for k in ('game_id', 'dolphin_version', 'state_version')},
        'base_dol_sha256': sha(source),
        'loaded_executable_sections': sections,
        'loaded_executable_bytes': sum(s['bytes'] for s in sections),
        'input_router_replay': router,
        'actor_detection_integrated': False,
        'playable_coop': False,
        'privacy': 'No savestate, RAM, roster, trainer identity or save data included',
    }


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--diagnostics', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = capture_report(args.source.read_bytes(), args.diagnostics)
    args.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))
