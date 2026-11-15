"""Native species-name dispatch and global text lookup for appended Snivy.

No archive loader, UI rendering, GPU or save runs in this replay.
"""

import argparse
import json
from pathlib import Path
import struct
from unicorn import ppc_const as ppc

from prepare_campaign_doubles import read_archive, sha
from translation.messages import read_messages, readable
from verify_coop_draft import DraftReplay
from verify_vm_wait import STOP
from names import append_name, patch_dol, MAP_RESOURCE, MESSAGE_RESOURCE, NAME_HOOK
from registry import append_stats, RESOURCE
from sunny_park import stats_row


def verify(capture, dol_path, common_path, messages_path):
    dol, common, archive = (p.read_bytes() for p in (dol_path, common_path, messages_path))
    if sha(common) != "a3667703d2bf2e6733c6d40e4709869982f98e45b9ad029a9f7d7d9fec883d57":
        raise ValueError("Requires exact published test13 common.fsys")
    resources = dict(read_archive(common))
    source_map = resources[MAP_RESOURCE]
    source_messages = dict(read_archive(archive))[MESSAGE_RESOURCE]
    new_map, new_messages, global_id = append_name(source_map, source_messages)
    patched = patch_dol(dol, global_id)
    old = DraftReplay(capture, dol)
    h = DraftReplay(capture, patched)
    name_lookup = 0x803E3458
    # Selector 2 is species; selector 0 is the item-name category.
    before = [old.call(name_lookup, (2, species)) for species in range(501)]
    after = [h.call(name_lookup, (2, species)) for species in range(501)]
    assert before == after == [species + 10 for species in range(501)]
    assert h.call(name_lookup, (2, 501)) == global_id
    h.abi()
    # Bind the same ID into the appended stats row and exercise its getter.
    stats_pointer = 0x80625184
    original_stats = h.get(stats_pointer)
    original_name_results = [h.call(0x80396B0C, (stats_pointer, s)) for s in range(501)]
    table = append_stats(resources[RESOURCE], stats_row(global_id))
    object_address, rows_address = 0x81B20000, 0x81810000
    obj = bytearray(h.uc.mem_read(original_stats, 48))
    stats_rows = table[48:48 + 502 * 52]
    for offset, value in ((0, 502), (8, rows_address), (16, rows_address),
                          (20, len(stats_rows)), (24, rows_address + len(stats_rows))):
        struct.pack_into(">I", obj, offset, value)
    h.uc.mem_write(object_address, bytes(obj))
    h.uc.mem_write(rows_address, stats_rows)
    h.put(stats_pointer, object_address)
    try:
        assert [h.call(0x80396B0C, (stats_pointer, s)) for s in range(501)] == original_name_results
        assert h.call(0x80396B0C, (stats_pointer, 501)) == global_id
    finally:
        h.put(stats_pointer, original_stats)
    # Preserve the old fallback even for unsupported IDs; this hook alone does
    # not relax species eligibility or make indices 502+ valid Pokémon.
    for species in (502, 600, 601, 65535):
        assert h.call(name_lookup, (2, species)) == old.call(name_lookup, (2, species))
    category_cases = 0
    for category in (0, 1, 3, 4, 5, 6, 7, 8, 9, 10):
        for value in (0, 1, 493, 494, 495, 500, 501, 502, 65535):
            assert h.call(name_lookup, (category, value)) == old.call(name_lookup, (category, value))
            category_cases += 1
    # Exercise the replacement of a single addi with live caller state. The
    # ordinary harness resets CR/r0, which alone would miss preservation bugs.
    abi_cases = 0
    for species in (0, 493, 494, 495, 496, 500, 501, 502, 65535):
        h.call(name_lookup, (2, species))
        for register, value in ((ppc.UC_PPC_REG_0, 0xDEADBEEF),
                                (ppc.UC_PPC_REG_CR, 0xA5F03C96),
                                (ppc.UC_PPC_REG_CTR, 0x13579)):
            h.uc.reg_write(register, value)
        h.uc.emu_start(NAME_HOOK, STOP, count=100)
        assert h.uc.reg_read(ppc.UC_PPC_REG_PC) == STOP
        assert h.uc.reg_read(ppc.UC_PPC_REG_3) == (global_id if species == 501 else species + 10)
        assert h.uc.reg_read(ppc.UC_PPC_REG_0) == 0xDEADBEEF
        assert h.uc.reg_read(ppc.UC_PPC_REG_CR) == 0xA5F03C96
        assert h.uc.reg_read(ppc.UC_PPC_REG_CTR) == 0x13579
        assert h.uc.reg_read(ppc.UC_PPC_REG_1) == 0x81F00000
        assert h.uc.reg_read(ppc.UC_PPC_REG_4) == species
        abi_cases += 1
    context, mes_address, map_address = 0x8048062C, 0x92C00000, 0x92E00000
    pointers = {offset: h.get(context + offset) for offset in (0xD34, 0xD38, 0x64F34)}
    count = pointers[0xD34]
    assert count + 1 == global_id
    assert bytes(h.uc.mem_read(pointers[0xD38], count * 4)) == source_map[8:]
    h.uc.mem_write(mes_address, new_messages)
    h.uc.mem_write(map_address, new_map)
    h.put(context + 0xD34, global_id)
    h.put(context + 0xD38, map_address + 8)
    h.put(context + 0x64F34, mes_address)
    _, rows = read_messages(new_messages)
    checked = 0
    try:
        for index in range(global_id):
            table, local = struct.unpack_from(">HH", new_map, 8 + index * 4)
            if table != 1:
                continue
            row = rows[local - 1]
            pointer = h.call(0x8024FB34, (context, index + 1))
            assert bytes(h.uc.mem_read(pointer, len(row))) == row
            checked += 1
        assert readable(rows[-1]) == "{F001}{F101}SNIVY"
        dimensions = h.call(0x8024FBBC, (context, global_id, 1, 0), limit=3000000)
        width, height = dimensions & 65535, dimensions >> 16
        assert 0 < width <= 150 and height == 25, (width, height)
        h.abi()
    finally:
        for offset, value in pointers.items():
            h.put(context + offset, value)
    # Check both arena aliases after reserving the added executable section.
    for setter in (0x8026EABC, 0x8026EACC):
        assert h.call(setter, (0x80640000,)) == 0x80646200
        assert h.call(setter, (0x80650000,)) == 0x80650000
    return dict(
        kind="offline native species name dispatch, global lookup and font metrics",
        passed=True, original_species_name_results_preserved=501,
        original_stats_name_results_preserved=501,
        stats_name_binding_verified=True,
        original_global_map_entries_preserved=count,
        original_common_messages_preserved=len(rows) - 1,
        native_common_message_lookups=checked,
        other_message_category_results_preserved=category_cases,
        seeded_caller_state_preservation_cases=abi_cases,
        snivy_internal_id=501, snivy_global_name_id=global_id,
        snivy_local_message_index_one_based=len(rows),
        snivy_name="SNIVY", width=width, height=height,
        memory_arena_aliases_verified=2,
        source_dol_sha256=sha(dol), target_dol_sha256=sha(patched),
        source_map_sha256=sha(source_map), target_map_sha256=sha(new_map),
        source_messages_sha256=sha(source_messages), target_messages_sha256=sha(new_messages),
        playable=False, published_in_updater=False,
        limits=["Scratch registration only; no real FSYS loading",
                "No icons, pass delivery, model dispatch or save integration",
                "Font metrics do not prove layout in the actual game UI"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "dol", "common", "messages", "report"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.capture, args.dol, args.common, args.messages)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
