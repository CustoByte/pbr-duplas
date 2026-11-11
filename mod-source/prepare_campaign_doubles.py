"""Prepare internal, unintegrated campaign edits for RPBE01 revision 0.

Outputs are internal development files, NOT a packaged playable mod or ISO.
Source files are opened read-only; exact hashes gate version-specific edits.
"""
import argparse
import hashlib
import json
import struct
import zlib
from pathlib import Path

from inspect_fsys import decompress
from team_series_asm import assemble as assemble_team_series, branch, NOP
from lzss_encode import encode as encode_lzss

DOL_SHA256 = 'ecb89c86f2eca30151561d9ee86a2ff260b2b2b3c9b4eb9429e04368392a2af9'
COMMON_SHA256 = '75ba89e3bb859ac32ad655517e001928e7bf9ad655c675584256dd2a21393b36'
DECK_SHA256 = 'c1a478be1ca447a47fe3efb2064de07bc3dffe883f52a180b403dab7469ddfdc'
CAMPAIGN_RECORDS = tuple(range(39))  # 0 fallback; 1..38 returned by 0x8008BDFC.
# 0x8008C254 seeds participant count in the campaign menu, including two overrides.
COUNT_LITERALS = {0x8008C28C: 5, 0x8008C2A8: 6, 0x8008C2D0: 6, 0x8008C2F4: 3}
# Each call obtains record 0..38 via 0x8008BDFC and passes the campaign state.
# Keep non-campaign preview calls to the shared constructor unchanged.
CAMPAIGN_FORMAT_LOADS = {
    0x80082ECC: 0x80DC0008,  # lwz r6,8(r28)
    0x800836D0: 0x80D90008,  # lwz r6,8(r25)
    0x8008406C: 0x80D90008,
    0x80083148: 0x80D90008,
}
# Campaign rules loader: override only the returned required-party-size value;
# the remaining level/species/item clauses still use their original getters.
CAMPAIGN_REQUIRED_SIZE = {0x8008B7F0: 0x4830FD01}
# Native battle marshalling has additional per-encounter caps after selection.
SPECIAL_PARTY_LIMITS = {
    0x801733D4: (0x3A800002, 0x3A800004),  # mode 3 / phase 1: li r20,2 -> 4
    0x80173304: (0x38030001, 0x38000004),  # progressive opponent, doubles: force four
}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def word(data, offset):
    return struct.unpack_from('>I', data, offset)[0]


def read_archive(data):
    if data[:4] != b'FSYS' or word(data, 0x20) != len(data):
        raise ValueError('Invalid archive')
    result = []
    table = word(data, word(data, 0x18))
    for index in range(word(data, 12)):
        header = word(data, table + index * 4)
        identifier = word(data, header)
        offset, expanded, stored = (word(data, header + o) for o in (4, 8, 0x14))
        if offset + stored > len(data):
            raise ValueError('Entry outside archive')
        payload = decompress(data[offset:offset + stored], expanded)
        if data[offset:offset + 4] == b'LZSS' and word(data, offset + 12) != zlib.crc32(payload):
            raise ValueError('LZSS decoded CRC-32 mismatch')
        result.append((identifier, payload))
    return result


def replace_archive_resource(archive, identifier, payload):
    """Replace inside the original compressed slot; preserve archive size/offsets."""
    entries = read_archive(archive)
    if sum(key == identifier for key, _ in entries) != 1:
        raise ValueError('Replacement ID not unique')
    if archive[-32:] != bytes(28) + b'FSYS':
        raise ValueError('Unexpected archive footer')
    pointer_table = word(archive, word(archive, 0x18))
    packed = encode_lzss(payload)
    output = bytearray(archive)
    for index, (key, _) in enumerate(entries):
        if key != identifier:
            continue
        header = word(archive, pointer_table + index * 4)
        offset, stored = word(archive, header + 4), word(archive, header + 0x14)
        if len(packed) > stored:
            raise ValueError('Compressed replacement exceeds original slot; archive relayout refused')
        output[offset:offset + stored] = packed + bytes(stored - len(packed))
        struct.pack_into('>I', output, header + 8, len(payload))
        struct.pack_into('>I', output, header + 0x14, len(packed))
    decoded = read_archive(bytes(output))
    for (old_id, old), (new_id, new) in zip(entries, decoded):
        if old_id != new_id or new != (payload if old_id == identifier else old):
            raise AssertionError('Resource replacement changed unrelated decoded data')
    return bytes(output)


def file_offset(dol, address):
    for count, fo, ao, so in [(7, 0, 0x48, 0x90), (11, 0x1c, 0x64, 0xac)]:
        for index in range(count):
            offset, start, size = (word(dol, base + index * 4) for base in (fo, ao, so))
            if start <= address and address + 4 <= start + size:
                return offset + address - start
    raise ValueError(f'Address outside DOL: {address:#x}')


def convert_table(source, deck_entries):
    count, stride, start = word(source, 0), word(source, 4), word(source, 16)
    if (count, stride, start) != (51, 92, 48) or start + count * stride > len(source):
        raise ValueError('Unexpected colosseum table layout')
    pools = dict(deck_entries)
    counterparts = {}
    for index in CAMPAIGN_RECORDS:
        row = start + index * stride
        for single, double in [(32, 40), (36, 44)]:
            a, b = word(source, row + single), word(source, row + double)
            if a and b:
                if a in counterparts and counterparts[a] != b:
                    raise ValueError('Ambiguous singles/doubles deck correspondence')
                counterparts[a] = b
    changed = bytearray(source)
    records = []
    for index in CAMPAIGN_RECORDS:
        base = start + index * stride
        original = source[base:base + stride]
        row = bytearray(original)
        filled = []
        for single, double in [(32, 40), (36, 44)]:
            a, b = word(row, single), word(row, double)
            if a and not b:
                if a not in counterparts:
                    raise ValueError(f'No documented counterpart for deck {a:08x}')
                b = counterparts[a]
                struct.pack_into('>I', row, double, b)
                filled.append({'slot': double, 'from_single': f'{a:08x}', 'double': f'{b:08x}'})
            if b:
                payload = pools.get(b)
                if payload is None or payload[:4] != b'DCKP' or word(payload, 8) < 4:
                    raise ValueError(f'Doubles pool absent or too small: {b:08x}')
        if not (word(row, 40) or word(row, 44)):
            raise ValueError(f'Campaign record {index} has no doubles pool')
        # Native getters 0x8039BDA4 / 0x8008BBB8 select doubles by slot availability.
        row[32:40] = bytes(8)
        # Native getter 0x8039BB04 reads this pair; format 1 uses index 1 (doubles).
        row[0x4D:0x4F] = bytes([4, 4])
        changed[base:base + stride] = row
        records.append({'index': index, 'filled_decks': filled,
                        'changed_offsets': [o for o in range(stride) if row[o] != original[o]],
                        'before_sha256': sha(original), 'after_sha256': sha(row)})
    allowed = {start + i * stride + field for i in CAMPAIGN_RECORDS
               for field in (*range(32, 48), 0x4D, 0x4E)}
    if any(i not in allowed for i, (a, b) in enumerate(zip(source, changed)) if a != b):
        raise AssertionError('Unrelated table data changed')
    return bytes(changed), records


def prepare(dol, common, deck):
    for label, data, expected in [('main.dol', dol, DOL_SHA256),
                                  ('common.fsys', common, COMMON_SHA256),
                                  ('deck.fsys', deck, DECK_SHA256)]:
        if sha(data) != expected:
            raise ValueError(f'Unsupported or already modified {label}')
    common_entries = read_archive(common)
    identifier, table = common_entries[11]
    if identifier != 0x1D9C0200:
        raise ValueError('Unexpected colosseum resource')
    new_table, records = convert_table(table, read_archive(deck))
    new_dol = bytearray(dol)
    edits = []
    for address, old_count in COUNT_LITERALS.items():
        offset = file_offset(dol, address)
        before, after = 0x38000000 | old_count, 0x38000004  # li r0, N
        if word(dol, offset) != before:
            raise ValueError('Native instruction mismatch')
        struct.pack_into('>I', new_dol, offset, after)
        edits.append({'address': f'{address:08x}', 'file_offset': offset,
                      'before': f'{before:08x}', 'after': f'{after:08x}',
                      'purpose': 'initial_participant_count'})
    for address, before in CAMPAIGN_FORMAT_LOADS.items():
        offset = file_offset(dol, address)
        after = 0x38C00001  # li r6,1: native doubles enum
        if word(dol, offset) != before:
            raise ValueError('Campaign format argument instruction mismatch')
        struct.pack_into('>I', new_dol, offset, after)
        edits.append({'address': f'{address:08x}', 'file_offset': offset,
                      'before': f'{before:08x}', 'after': f'{after:08x}',
                      'purpose': 'force_campaign_constructor_doubles'})
    for address, before in CAMPAIGN_REQUIRED_SIZE.items():
        offset = file_offset(dol, address)
        after = 0x38600004  # li r3,4; the existing sth writes session +0x90
        if word(dol, offset) != before:
            raise ValueError('Campaign selection-rule getter instruction mismatch')
        struct.pack_into('>I', new_dol, offset, after)
        edits.append({'address': f'{address:08x}', 'file_offset': offset,
                      'before': f'{before:08x}', 'after': f'{after:08x}',
                      'purpose': 'require_exactly_four_in_campaign_selection'})
    for address, (before, after) in SPECIAL_PARTY_LIMITS.items():
        offset = file_offset(dol, address)
        if word(dol, offset) != before:
            raise ValueError('Special encounter party-limit instruction mismatch')
        struct.pack_into('>I', new_dol, offset, after)
        edits.append({'address': f'{address:08x}', 'file_offset': offset,
                      'before': f'{before:08x}', 'after': f'{after:08x}',
                      'purpose': 'four_participants_in_special_encounter_marshalling'})
    # The real freeze snapshot contains a fresh maincallback task with stale
    # wait-type 2 / index 0x8A. Preserve allocated VM stack pointers on reuse.
    helper = 0x80077060
    series_words = assemble_team_series()
    helper_words = {helper: 0x909F017C, helper + 4: 0x909F016C,
                    helper + 8: 0x909F0170, helper + 12: 0x4E800020}
    if any(series_words[a] != NOP for a in helper_words):
        raise ValueError('VM wait initializer overlaps series restoration code')
    series_words.update(helper_words)
    for address, before, after in [(0x8022DF50, 0x38A00144, 0x38A00178),
                                   (0x8022E1C8, 0x909F017C, branch(0x8022E1C8, helper, True))]:
        offset = file_offset(dol, address)
        if word(dol, offset) != before:
            raise ValueError('VM initializer instruction mismatch')
        struct.pack_into('>I', new_dol, offset, after)
        edits.append({'address': f'{address:08x}', 'file_offset': offset,
                      'before': f'{before:08x}', 'after': f'{after:08x}',
                      'purpose': 'initialize_vm_wait_state'})
    for address, after in sorted(series_words.items()):
        offset = file_offset(dol, address)
        before = word(dol, offset)
        if before == after:
            continue
        struct.pack_into('>I', new_dol, offset, after)
        edits.append({'address': f'{address:08x}', 'file_offset': offset,
                      'before': f'{before:08x}', 'after': f'{after:08x}',
                      'purpose': 'initialize_vm_wait_state' if address in helper_words else 'restore_same_four_between_best_of_three_encounters'})
    audit = {'status': 'experimental_unintegrated', 'runtime_tested': False,
             'scope': 'Campaign table records 0..38; fallback plus primary/rematch/master variants',
             'not_completed': ['in-game verification of each special rule',
                               'full campaign progression tests', 'coop'],
             'colosseum_resource_id': f'{identifier:08x}', 'records': records,
             'native_edits': edits,
             'source_sha256': {'main.dol': sha(dol), 'common.fsys': sha(common), 'deck.fsys': sha(deck)},
             'output_sha256': {'main.dol': sha(new_dol), 'colosseum-table.bin': sha(new_table)}}
    return bytes(new_dol), new_table, audit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['dol', 'common', 'deck', 'output']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    output_dol, table, audit = prepare(args.dol.read_bytes(), args.common.read_bytes(), args.deck.read_bytes())
    output_common = replace_archive_resource(args.common.read_bytes(), 0x1D9C0200, table)
    audit['output_sha256']['common.fsys'] = sha(output_common)
    audit['resource_roundtrip_verified'] = True
    # Refuse to overwrite an existing workspace, including a source directory.
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / 'main.dol').write_bytes(output_dol)
    (args.output / 'colosseum-table.bin').write_bytes(table)
    (args.output / 'common.fsys').write_bytes(output_common)
    (args.output / 'audit.json').write_text(json.dumps(audit, indent=2))
    print('Prepared campaign records, native doubles arguments and exact-four selection; FSYS roundtrip passed, no gameplay test.')


if __name__ == '__main__':
    main()
