"""Level-50 Snivy configuration for Red/Cyndy's initial Rental Pass.

Only prepares a native-constructor input. No pass or save is changed here.
"""

import struct

from sunny_park import deck_row as little_row, plan as little_plan

PASS_INDEX = 37
SLOT_INDEX = 1
EXPECTED_ORIGINAL_SPECIES = 5  # Charmeleon, not Charmander
LEVEL = 50
MOVES = (412, 137, 73, 182)  # Energy Ball, Glare, Leech Seed, Protect
EXPECTED_PP = (10, 30, 10, 10)


def deck_row():
    row = bytearray(little_row())
    # Fixed item + raw EVs; do not mark the level-50 set Little Battle eligible.
    struct.pack_into(">H", row, 2, 0x1002)
    struct.pack_into(">4H", row, 32, *MOVES)
    return bytes(row)


def plan():
    result = little_plan()
    result.update(
        tournament="Initial Red/Cyndy Rental Pass",
        level=LEVEL,
        target_pass_index=PASS_INDEX,
        target_slot_zero_based=SLOT_INDEX,
        expected_original_species=EXPECTED_ORIGINAL_SPECIES,
        preserve_monferno_pass_index=38,
        moves=["Energy Ball", "Glare", "Leech Seed", "Protect"],
        gen5_legal_sources=["TM53", "egg", "level 19", "TM17"],
        requested_change="Replace Charmeleon in the other initial Rental Pass",
        training_policy="Fixed level-50 special attacker/support set",
        expected_unboosted_stats_hp_atk_def_speed_spatk_spdef=[121, 58, 75, 126, 97, 75],
    )
    return result
