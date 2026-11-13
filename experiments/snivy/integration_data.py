"""Assemble independent data registrations without overwriting old species."""

import json
from pathlib import Path
import struct

from names import append_name, MAP_RESOURCE, MESSAGE_RESOURCE
from registry import append_stats, RESOURCE as STATS_RESOURCE
from sunny_park import stats_row
from model_registry import build_row, append_model, bind_stats_row, RESOURCE as MODEL_RESOURCE
from icon_registry import prepare as icon_tables
from pkx_reference import scene_inventory

EVOLUTION_RESOURCE, LEVELUP_RESOURCE = 0x00820200, 0x12A90200


def append_fixed(table, stride, row):
    if len(table) < 48 or struct.unpack_from(">II", table) != (501, stride):
        raise ValueError("Unexpected original per-species table")
    if struct.unpack_from(">I", table, 16)[0] != 48 or struct.unpack_from(">I", table, 28)[0] != 0:
        raise ValueError("Unsupported offsets or embedded relocations")
    end = 48 + 501 * stride
    if len(row) != stride or end > len(table):
        raise ValueError("Unexpected per-species row length")
    if struct.unpack_from(">II", table, 20) != (501 * stride, len(table)):
        raise ValueError("Unexpected original table lengths")
    output = bytearray(table[:end] + row + table[end:])
    struct.pack_into(">I", output, 0, 502)
    struct.pack_into(">II", output, 20, 502 * stride, len(output))
    assert output[48:end] == table[48:end] and output[end + stride:] == table[end:]
    return bytes(output)


def prepare(common_resources, messages, normal_sdr):
    new_map, new_messages, name_id = append_name(common_resources[MAP_RESOURCE], messages)
    if name_id != 21775:
        raise ValueError("This runtime build requires audited global name ID 21775")
    replacements = icon_tables(common_resources)
    row = bytearray(bind_stats_row(stats_row(name_id)))
    # Shared native TM17 Protect and TM53 Energy Ball; no invented Gen5 moves.
    value = struct.unpack_from(">I", row, 4)[0] | (1 << 20)
    struct.pack_into(">I", row, 4, value)
    replacements[STATS_RESOURCE] = append_stats(common_resources[STATS_RESOURCE], bytes(row))
    replacements[MODEL_RESOURCE] = append_model(common_resources[MODEL_RESOURCE], build_row(scene_inventory(normal_sdr)))
    replacements[MAP_RESOURCE] = new_map
    # Evolution capability is recorded in the native face/NFE flag. No fake
    # Servine/Serperior target or self-evolution is invented for this first step.
    replacements[EVOLUTION_RESOURCE] = append_fixed(common_resources[EVOLUTION_RESOURCE], 42, bytes(42))
    learnset = json.loads(Path(__file__).with_name("supported-learnset.json").read_text())["supported_native_levelup"]
    if len(learnset) > 20:
        raise ValueError("Native level-up record capacity exceeded")
    levels = bytearray(80)
    for index, entry in enumerate(learnset):
        if not 1 <= entry["move_id"] <= 467 or not 1 <= entry["level"] <= 100:
            raise ValueError("Unsupported move or level")
        struct.pack_into(">HBB", levels, index * 4, entry["move_id"], entry["level"], 0)
    replacements[LEVELUP_RESOURCE] = append_fixed(common_resources[LEVELUP_RESOURCE], 80, bytes(levels))
    return replacements, new_messages
