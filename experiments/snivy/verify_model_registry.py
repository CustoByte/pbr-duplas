"""Replay species -> model row -> FSYS catalog and native action/node getters.

This proves data dispatch only. It does not open/load/render either SDR variant.
"""

import argparse
import json
from pathlib import Path
import struct

from prepare_campaign_doubles import read_archive, sha
from verify_coop_draft import DraftReplay
from pkx_reference import scene_inventory
from catalog import append_archive, relocate, SNIVY_ARCHIVE_ID, SNIVY_ARCHIVE_NAME
from registry import RESOURCE as STATS_RESOURCE, append_stats
from sunny_park import stats_row
from model_registry import RESOURCE, MODEL_INDEX, NORMAL_ID, SHINY_ID, NODE_ROLES, ACTION_ROLES, build_row, append_model, bind_stats_row


def verify(capture, dol_path, common_path, catalog_path, sdr_path):
    dol, common, catalog, sdr = (p.read_bytes() for p in (dol_path, common_path, catalog_path, sdr_path))
    if sha(dol) != "da02a1232240e139ec14a26ee8b4c2818c56f3c2907f5c2391bd81e2dc0842f6":
        raise ValueError("Requires unchanged published test13 DOL")
    if sha(common) != "a3667703d2bf2e6733c6d40e4709869982f98e45b9ad029a9f7d7d9fec883d57":
        raise ValueError("Requires unchanged published test13 common.fsys")
    if sha(catalog) != "da886839e93a719a04833795f2407417cccded696d7e92e49087065dbf3ee26e":
        raise ValueError("Requires the supplied original catalog")
    resources = dict(read_archive(common))
    scene = scene_inventory(sdr)
    row = build_row(scene)
    table = append_model(resources[RESOURCE], row)
    new_catalog = append_archive(catalog)
    stats = bind_stats_row(stats_row(21775))
    stats_table = append_stats(resources[STATS_RESOURCE], stats)
    h = DraftReplay(capture, dol)
    model_reference, stats_reference, catalog_reference = 0x80625174, 0x80625184, 0x80627B5C
    originals = {p: h.get(p) for p in (model_reference, stats_reference, catalog_reference)}
    model_rows = h.get(originals[model_reference] + 16)
    assert bytes(h.uc.mem_read(model_rows, 670 * 72)) == resources[RESOURCE][48:48 + 670 * 72]
    before_models = [h.call(0x80395CC0, (model_reference, i)) for i in range(670)]
    assert before_models == [model_rows + i * 72 for i in range(670)]
    before_indices = [h.call(0x80396B74, (stats_reference, i)) for i in range(501)]

    def register(reference, source, target, object_address, rows_address):
        old_object = originals[reference]
        obj = bytearray(h.uc.mem_read(old_object, 48))
        count, stride = struct.unpack_from(">II", target)
        rows = target[48:48 + count * stride]
        for offset, value in ((0, count), (8, rows_address), (16, rows_address),
                              (20, len(rows)), (24, rows_address + len(rows))):
            struct.pack_into(">I", obj, offset, value)
        old_count, old_stride = struct.unpack_from(">II", source)
        old_length = old_count * old_stride
        assert rows[:old_length] == source[48:48 + old_length]
        h.uc.mem_write(object_address, bytes(obj))
        h.uc.mem_write(rows_address, rows)
        h.put(reference, object_address)

    register(model_reference, resources[RESOURCE], table, 0x81B20000, 0x81B40000)
    register(stats_reference, resources[STATS_RESOURCE], stats_table, 0x81B22000, 0x81810000)
    catalog_base = 0x81B60000
    h.uc.mem_write(catalog_base, relocate(new_catalog, catalog_base))
    h.put(catalog_reference, catalog_base)
    node_cases, action_cases = [], []
    try:
        assert [h.call(0x80396B74, (stats_reference, i)) for i in range(501)] == before_indices
        for index in range(670):
            pointer = h.call(0x80395CC0, (model_reference, index))
            assert bytes(h.uc.mem_read(pointer, 72)) == resources[RESOURCE][48 + index * 72:48 + (index + 1) * 72]
        assert h.call(0x80396B74, (stats_reference, 501)) == MODEL_INDEX
        assert h.call(0x80395CF4, (model_reference,)) == 671
        for getter, expected in ((0x80395D10, 501), (0x80395D44, 0),
                                  (0x80395D78, 1), (0x80395DB0, 0),
                                  (0x80395E90, SNIVY_ARCHIVE_ID),
                                  (0x80395EC4, NORMAL_ID), (0x80395EF8, SHINY_ID)):
            assert h.call(getter, (model_reference, MODEL_INDEX)) == expected
            h.abi()
        nodes = {n["index"]: n["name"] for n in scene["nodes"]}
        for field, (role, expected) in enumerate(NODE_ROLES):
            index = h.call(0x80395DE8, (model_reference, MODEL_INDEX, field))
            assert nodes[index] == expected
            node_cases.append(dict(role=role, node=expected, index=index))
        for field, (role, expected) in enumerate(ACTION_ROLES):
            index = h.call(0x80395E3C, (model_reference, MODEL_INDEX, field))
            assert scene["actions"][index]["name"] == expected
            action_cases.append(dict(role=role, action=expected, index=index))
        assert h.call(0x80395DE8, (model_reference, MODEL_INDEX, 25)) == 0
        assert h.call(0x80395E3C, (model_reference, MODEL_INDEX, 22)) == 0
        archive_id = h.call(0x80395E90, (model_reference, MODEL_INDEX))
        entry = h.call(0x8024C32C, (archive_id,))
        assert entry != 0 and h.get(entry) == SNIVY_ARCHIVE_ID
        name_pointer = h.get(entry + 4)
        assert bytes(h.uc.mem_read(name_pointer, len(SNIVY_ARCHIVE_NAME) + 1)) == SNIVY_ARCHIVE_NAME.encode() + b"\0"
    finally:
        for reference, pointer in originals.items():
            h.put(reference, pointer)
    assert [h.call(0x80395CC0, (model_reference, i)) for i in range(670)] == before_models
    assert [h.call(0x80396B74, (stats_reference, i)) for i in range(501)] == before_indices
    return dict(
        kind="offline native model dispatch and attachment/animation table lookup",
        passed=True, original_model_rows_preserved=670,
        original_species_model_indices_preserved=501,
        new_model_index=MODEL_INDEX, snivy_internal_id=501,
        fsys_id=f"{SNIVY_ARCHIVE_ID:08x}", archive_name=SNIVY_ARCHIVE_NAME,
        reserved_normal_resource=f"{NORMAL_ID:08x}", reserved_shiny_resource=f"{SHINY_ID:08x}",
        catalog_chain_verified=True, restored_original_pointers=True,
        node_roles=node_cases, action_roles=action_cases,
        converted_scene_nodes=len(scene["nodes"]), converted_scene_actions=len(scene["actions"]),
        sdr_sha256=sha(sdr), source_models_sha256=sha(resources[RESOURCE]),
        target_models_sha256=sha(table), model_row_hex=row.hex(),
        playable=False, published_in_updater=False,
        limits=["No actual FSYS or SDR loading/rendering",
                "Shiny resource ID reserved; shiny variant not built in this step",
                "Camera, run speed, effect positions and action semantics need in-game calibration",
                "No global eligibility, pass migration, icons or save/load test"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "dol", "common", "catalog", "sdr", "report"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.capture, args.dol, args.common, args.catalog, args.sdr)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
