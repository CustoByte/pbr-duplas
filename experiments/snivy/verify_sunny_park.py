"""Construct the requested Snivy through the native USA constructor and read it.

Only table registration and scratch allocation/free are fixtures. No Pokémon,
move, nature, ability, EXP or item getter is stubbed. No save file is modified.
"""

import argparse
import json
from pathlib import Path
import struct

from unicorn import UC_HOOK_CODE
from unicorn import ppc_const as ppc

from prepare_campaign_doubles import read_archive, sha
from verify_coop_draft import DraftReplay
from registry import RESOURCE, append_stats
from sunny_park import (
    plan,
    stats_row,
    deck_row,
    MOVES,
    EVS,
    NATIVE_IV_MIN_RANGE,
    NATIVE_EV_BUDGETS,
)


def verify(capture, dol_path, common_path, rank=None, level=5):
    if level not in (5, 50) or (level == 50 and rank is not None):
        raise ValueError("Use level 5 with optional rank, or fixed level 50")
    moves, pp = MOVES, (35, 30, 20, 10)
    row = deck_row(rank)
    requested = plan(rank)
    if level == 50:
        import starter_pass
        row, requested = starter_pass.deck_row(), starter_pass.plan()
        moves, pp = starter_pass.MOVES, starter_pass.EXPECTED_PP
    dol, common = dol_path.read_bytes(), common_path.read_bytes()
    if (
        sha(dol) != "da02a1232240e139ec14a26ee8b4c2818c56f3c2907f5c2391bd81e2dc0842f6"
        or sha(common)
        != "a3667703d2bf2e6733c6d40e4709869982f98e45b9ad029a9f7d7d9fec883d57"
    ):
        raise ValueError("Requires unchanged published test13 baseline")
    table = dict(read_archive(common))[RESOURCE]
    expanded = append_stats(table, stats_row())
    h = DraftReplay(capture, dol)
    reference = 0x80625184
    old = h.get(reference)
    obj = bytearray(h.uc.mem_read(old, 48))
    object_address, rows_address = 0x81B20000, 0x81810000
    rows = expanded[48 : 48 + 502 * 52]
    for offset, value in (
        (0, 502),
        (8, rows_address),
        (16, rows_address),
        (20, len(rows)),
        (24, rows_address + len(rows)),
    ):
        struct.pack_into(">I", obj, offset, value)
    h.uc.mem_write(object_address, bytes(obj))
    h.uc.mem_write(rows_address, rows)
    h.put(reference, object_address)
    ctx, party, trainer, row_address, dest = (
        0x81B00000,
        0x81B05000,
        0x81B06000,
        0x81800000,
        0x81D10000,
    )
    h.uc.mem_write(ctx, bytes(0x10000))
    h.put(ctx + 0x10, 7 if rank is None else rank - 1)
    h.put(ctx + 0x14, 6)
    h.put(ctx + 0x6C, level)
    h.put(ctx + 0x60, trainer)
    h.put(party + 0x28, 0x13572468)
    h.uc.mem_write(party + 0xC, b"\1" if rank is None else b"\0")
    h.put(party + 0x10, 7 if rank is None else rank - 1)
    h.uc.mem_write(row_address, row)
    heap = [0x81C00000]
    allocations = []

    def allocate(u, address, size, data):
        result = 0
        if address in (0x801728E4, 0x801DF6B4):
            count = u.reg_read(
                ppc.UC_PPC_REG_4 if address == 0x801728E4 else ppc.UC_PPC_REG_3
            )
            if not 0 < count < 65536:
                raise AssertionError("Unexpected allocation")
            result = heap[0]
            heap[0] += (count + 31) & ~31
            assert heap[0] < 0x81C10000
            allocations.append(count)
        u.reg_write(ppc.UC_PPC_REG_3, result)
        u.reg_write(ppc.UC_PPC_REG_PC, u.reg_read(ppc.UC_PPC_REG_LR))

    for address in (0x801728E4, 0x801DF6B4, 0x80172A14, 0x801DF6FC):
        h.uc.hook_add(UC_HOOK_CODE, allocate, begin=address, end=address)
    h.uc.mem_write(dest, bytes(0xA4))
    h.call(0x8017D750, (ctx, dest, row_address, party, 255), limit=3000000)
    h.abi()
    get = lambda field: h.call(0x803DE52C, (dest, field, 0))
    result = dict(
        species=get(5),
        held_item=get(6),
        ability=get(10),
        pid=get(0),
        moves=[get(i) for i in range(0x36, 0x3A)],
        pp=[get(i) for i in range(0x3A, 0x3E)],
        ivs=[get(i) for i in range(0x46, 0x4C)],
        evs=[get(i) for i in range(0xD, 0x13)],
        experience=get(8),
    )
    assert (
        result["species"] == 501
        and result["held_item"] == 157
        and result["ability"] == 65
    ), result
    assert result["pid"] % 25 == 10 and result["moves"] == list(moves), result
    assert result["pp"] == list(pp), result
    if rank is None:
        assert result["ivs"] == [31] * 6 and result["evs"] == list(EVS), result
    else:
        low, span = NATIVE_IV_MIN_RANGE[rank - 1]
        assert all(low <= v < low + span for v in result["ivs"]), result
        assert (
            all(v <= 252 for v in result["evs"])
            and sum(result["evs"]) <= NATIVE_EV_BUDGETS[rank - 1]
        ), result
    assert result["experience"] == h.call(0x803DF14C, (501, level)), result
    if level == 5:
        assert result["experience"] == 135, result
    party_dest = 0x81D12000
    h.uc.mem_write(party_dest, bytes(0xA4))
    h.call(0x803DFD78, (dest, party_dest), limit=3000000)
    party_get = lambda field: h.call(0x803E100C, (party_dest, field, 0))
    result["level"] = party_get(160)
    result["stats_hp_atk_def_speed_spatk_spdef"] = [
        party_get(field) for field in range(163, 169)
    ]
    result["species_or_egg"] = get(173)
    base = (45, 45, 55, 63, 45, 55)
    expected = [
        ((2 * b + iv + ev // 4) * level) // 100 + (level + 10 if i == 0 else 5)
        for i, (b, iv, ev) in enumerate(zip(base, result["ivs"], result["evs"]))
    ]
    expected[1] = expected[1] * 90 // 100
    expected[3] = expected[3] * 110 // 100
    assert (
        result["level"] == level
        and result["stats_hp_atk_def_speed_spatk_spdef"] == expected
    ), result
    assert result["species_or_egg"] == 501, result
    copied = 0x81D11000
    h.uc.mem_write(copied, bytes(h.uc.mem_read(party_dest, 0xA4)))
    assert h.call(0x803DE52C, (copied, 5, 0)) == 501
    assert h.call(0x803DE52C, (copied, 6, 0)) == 157
    assert h.call(0x803E100C, (copied, 160, 0)) == level
    h.put(reference, old)
    return dict(
        kind=f"native offline level-{level} constructor proof",
        passed=True,
        requested_set=requested,
        readback=result,
        allocation_sizes=sorted(set(allocations)),
        limits=[
            "No model dispatch or render",
            "No Little Battle player eligibility test",
            "No roster migration, real save/load or Dolphin battle",
            "Name/model registry fields remain unresolved",
        ],
        released=False,
        tested_rank=rank,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "dol", "common", "report"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--rank", type=int, choices=range(1, 9))
    parser.add_argument("--level", type=int, choices=(5, 50), default=5)
    args = parser.parse_args()
    result = verify(args.capture, args.dol, args.common, args.rank, args.level)
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
