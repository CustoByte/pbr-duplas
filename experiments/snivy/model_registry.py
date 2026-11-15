"""Build independent model-table bindings from the converted Snivy's indices.

No Grotle node/action byte indices are copied. Resource IDs are reservations;
this does not claim either SDR has been installed or the shiny is finished.
"""

import struct

from catalog import SNIVY_ARCHIVE_ID
from pkx_reference import ORDER

RESOURCE = 0x00800200
MODEL_INDEX = 670
NORMAL_ID = 0x73EA0400
SHINY_ID = 0x63EA0400

# Field order is the native 72-byte RPBE01 model row, not skeleton order.
NODE_ROLES = (
    ("damage_1", "ef_damage"), ("mouth", "ef_mouth"),
    ("left_eye", "ef_leye"), ("right_eye", "ef_reye"),
    ("root_1", "PBR_StaticRoot"), ("left_arm", "ef_lfhand"),
    ("right_arm", "ef_rfhand"), ("left_foot", "ef_lffoot"),
    ("right_foot", "ef_rffoot"), ("center", "ef_o"),
    ("control_all_move_1", "ct_all_move"), ("head", "ef_head"),
    ("right_hand", "ef_rfhand"), ("right_foot_2", "ef_rffoot"),
    ("root_2", "PBR_StaticRoot"), ("root_3", "PBR_StaticRoot"),
    ("root_4", "PBR_StaticRoot"), ("root_5", "PBR_StaticRoot"),
    ("root_6", "PBR_StaticRoot"), ("damage_2", "ef_damage"),
    ("direct_set", "direct_set"), ("control_bust", "ct_bust"),
    ("control_bust_move", "ct_bust_move"), ("control_all", "ct_all"),
    ("control_all_move_2", "ct_all_move"),
)
ACTION_ROLES = (
    ("battle_idle", "wait"), ("special_move", "kime"),
    ("physical_move", "tackle"), ("punch_1", "kime_phy"),
    ("kick", "kime_phy"), ("fly", "wait"), ("dive", "wait"),
    ("punch_2", "tackle"), ("damage", "damage"), ("faint", "down"),
    ("hover", "wait"), ("unknown_idle_2", "kime_a"),
    ("unknown_idle_3", "mamoru"), ("unknown_idle_4", "wait"),
    ("unknown_idle_5", "wait"), ("unknown_idle_6", "wait"),
    ("status", "wait"), ("run", "run"), ("summary_idle", "wait"),
    ("blink", "tx_wink"), ("sleep", "tx_sleep"), ("wake", "tx_wakeup"),
)


def build_row(scene):
    if scene["object_name"] != "SnivyExport":
        raise ValueError("Expected an independent converted Snivy scene")
    nodes = {node["name"]: node["index"] for node in scene["nodes"]}
    actions = {action["name"]: action["index"] for action in scene["actions"]}
    if len(nodes) != len(scene["nodes"]) or len(actions) != len(scene["actions"]):
        raise ValueError("Ambiguous node or action names")
    if len(set(nodes.values())) != len(nodes) or sorted(actions.values()) != list(range(len(actions))):
        raise ValueError("Duplicate or invalid node/action indices")
    if tuple(actions) != ORDER:
        raise ValueError("Unexpected native-reference action order")
    required_nodes = {name for _, name in NODE_ROLES}
    if required_nodes - nodes.keys():
        raise ValueError(f"Missing effect/control nodes: {sorted(required_nodes - nodes.keys())}")
    if any(not 0 <= index <= 255 for index in nodes.values()):
        raise ValueError("Model row node indices exceed uint8")
    row = bytearray(72)
    # Provisional small-model class and run speed, comparable to Treecko.
    # These are not a claim of camera/stride calibration in the live game.
    row[0] = 0x30
    struct.pack_into(">III f H", row, 4, SNIVY_ARCHIVE_ID, NORMAL_ID, SHINY_ID, 18.0, 501)
    row[25:50] = bytes(nodes[name] for _, name in NODE_ROLES)
    row[50:72] = bytes(actions[name] for _, name in ACTION_ROLES)
    return bytes(row)


def append_model(table, row):
    if len(table) != 48288 or struct.unpack_from(">II", table) != (670, 72):
        raise ValueError("Requires audited original model table")
    if struct.unpack_from(">III", table, 16) != (48, 670 * 72, len(table)):
        raise ValueError("Unexpected model table lengths")
    if not isinstance(row, bytes) or len(row) != 72:
        raise ValueError("Expected a complete native model row")
    if struct.unpack_from(">III", row, 4) != (SNIVY_ARCHIVE_ID, NORMAL_ID, SHINY_ID) or struct.unpack_from(">H", row, 20)[0] != 501:
        raise ValueError("Expected independent Snivy model identities")
    old_rows = [table[48 + i * 72:48 + (i + 1) * 72] for i in range(670)]
    if any(struct.unpack_from(">H", r, 20)[0] == 501 for r in old_rows):
        raise ValueError("Species is already registered")
    old_ids = {struct.unpack_from(">I", r, offset)[0] for r in old_rows for offset in (8, 12)}
    if NORMAL_ID in old_ids or SHINY_ID in old_ids:
        raise ValueError("Reserved model resource IDs collide with existing models")
    output = bytearray(table + row)
    struct.pack_into(">I", output, 0, 671)
    struct.pack_into(">II", output, 20, 671 * 72, len(output))
    assert output[48:len(table)] == table[48:]
    return bytes(output)


def bind_stats_row(row):
    """Attach a fresh, independent stats row to the newly appended model row."""
    if not isinstance(row, bytes) or len(row) != 52:
        raise ValueError("Expected a complete native stats row")
    if struct.unpack_from(">H", row, 28)[0] != 0:
        raise ValueError("Stats row already has a model binding")
    output = bytearray(row)
    struct.pack_into(">H", output, 28, MODEL_INDEX)
    return bytes(output)
