"""Requested level-5 set and staging data. Never installed by the release build.

The roster substitution is deliberately not performed until acquisition, model
lookup, non-contiguous identity and persistence are integrated and verified.
"""

import struct

from registry import INTERNAL_ID

MOVES = (33, 43, 345, 182)  # Tackle, Leer, Magical Leaf, Protect
NATURE = 10  # Timid
ABILITY = 65  # Overgrow (no Gen5-only Contrary)
ITEM = 157  # Lum Berry
LEVEL = 5
EVS = (4, 0, 0, 252, 252, 0)  # HP/Atk/Def/Spe/SpA/SpD


def stats_row():
    row = bytearray(52)
    # Gen4 TM17 Protect compatibility; remaining learnset work is separate.
    struct.pack_into(">I", row, 0, 1 << 16)
    struct.pack_into(">HH", row, 20, 6, 81)  # 0.6 m, 8.1 kg
    # Names/model references remain unresolved and are not copied from Grotle.
    row[30:36] = bytes((45, 45, 55, 63, 45, 55))
    row[36:40] = bytes((12, 12, 45, 62))
    struct.pack_into(">H", row, 40, 0x0100)  # one Speed EV yield
    row[42:52] = bytes((31, 20, 70, 3, 5, 7, ABILITY, 0, 0, 6))
    return bytes(row)


def deck_row():
    row = bytearray(56)
    # A fixed-configuration Little Battle constructor fixture, not a live pool.
    struct.pack_into(">4H", row, 0, 0, 0x1402, 1, INTERNAL_ID)
    row[8:14] = bytes((12, 12, 4, 0, NATURE, 0))
    row[16:22] = bytes((31,) * 6)
    struct.pack_into(">H", row, 22, sum(EVS))
    row[24:30] = bytes(EVS)
    struct.pack_into(">4H", row, 32, *MOVES)
    struct.pack_into(">4H", row, 40, *((ITEM,) * 4))
    return bytes(row)


def plan():
    return dict(
        tournament="Sunny Park — Little Battle",
        level=LEVEL,
        national_id=495,
        provisional_internal_id=INTERNAL_ID,
        nature="Timid",
        ability="Overgrow",
        item="Lum Berry",
        moves=["Tackle", "Leer", "Magical Leaf", "Protect"],
        gen5_legal_sources=["level 1", "level 4", "egg", "TM"],
        ivs=[31] * 6,
        ev_order="HP/Atk/Def/Speed/SpAtk/SpDef",
        evs=list(EVS),
        original_species_replaced=False,
        requested_change="one player-usable roster slot, restricted to Little Battle",
        live_player_slot_selected=False,
        playable=False,
        ready_to_publish=False,
    )
