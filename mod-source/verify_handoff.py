"""Verify selection packing and isolated native battle-party marshalling.

Native copies, loops, caps and final party append run as PowerPC instructions.
Pokemon decoding/validity, AI choice, allocation and name-registration use
explicit synthetic stand-ins. This does not execute a battle or its result flow.
"""
import argparse
import itertools
import json
import struct
from pathlib import Path

from unicorn import ppc_const as ppc

from prepare_campaign_doubles import read_archive, word
from verify_native_doubles import Native, CONFIG, SDA

UI = 0x80B00000
CTX = 0x80A00000
ENGINE = 0x80A10000
SCRATCH = 0x80A20000
TEAM = 0x80A30000
HEAP = 0x80C00000
ORDERS = 0x804765F0


class HandoffNative(Native):
    def __init__(self, dol, table):
        super().__init__(dol, table)
        self.mode = 0
        self.phase = 0
        self.ai = 0
        self.round = 1
        self.side = 0
        self.ai_counts = []
        self.uc.mem_write(SDA - 0x7D38, struct.pack('>I', UI))
        self.uc.mem_write(UI + 0xD8, struct.pack('>I', CONFIG))
        self.uc.mem_write(CTX + 4, struct.pack('>I', ENGINE))
        self.uc.mem_write(CTX + 8, struct.pack('>I', SCRATCH))
        for side in (0, 1):
            self.uc.mem_write(ENGINE + 4 + side * 4, struct.pack('>I', TEAM + side * 0x1000))
            self.uc.mem_write(ENGINE + 0xD8 + side * 4, struct.pack('>I', 0x80A50000 + side * 0x1000))

    def hook(self, uc, address, size, data):
        super().hook(uc, address, size, data)
        if address == 0x80173188:
            uc.mem_write(CONFIG + 0x14, bytes([self.mode]))
            uc.mem_write(CONFIG + 0x18, bytes([self.phase]))
            uc.mem_write(CONFIG + 0x1B, bytes([self.ai]))
            uc.mem_write(CONFIG + 0x16, struct.pack('>H', self.round))
        result = None
        if address in (0x803DD6A4, 0x803E2254, 0x801DFAE4):
            result = 0  # Name registration or freeing the temporary packed party.
        elif address == 0x801DF9A4:
            if uc.reg_read(ppc.UC_PPC_REG_3) > 0x10000:
                raise AssertionError('Unexpected allocation size')
            result = HEAP
        elif address == 0x801C6390:
            result = 0  # Enable the observed native opponent-selection branch.
        elif address == 0x80182DE8:
            party = uc.reg_read(ppc.UC_PPC_REG_3)
            output = uc.reg_read(ppc.UC_PPC_REG_4)
            count = uc.reg_read(ppc.UC_PPC_REG_5)
            self.ai_counts.append(count)
            valid = [i for i in range(6) if bytes(uc.mem_read(party + i * 0x8C + 0x286, 1))[0] & 0x80]
            order = valid[:count]
            uc.mem_write(output, bytes(order + [0xFF] * (6 - len(order))))
            result = 0
        elif address == 0x803DFD78:
            source = uc.reg_read(ppc.UC_PPC_REG_3)
            target = uc.reg_read(ppc.UC_PPC_REG_4)
            # Preserve a marker through a synthetic decoder. Native append is NOT stubbed.
            marker = bytes(uc.mem_read(source, 4))
            uc.mem_write(target, marker + bytes(0xA0))
            result = 1
        elif address == 0x803E100C:
            result = 1  # The synthetic decoded marker represents a present Pokemon.
        if result is not None:
            uc.reg_write(ppc.UC_PPC_REG_3, result)
            uc.reg_write(ppc.UC_PPC_REG_PC, uc.reg_read(ppc.UC_PPC_REG_LR))

    def seed(self, orders):
        for side, order in enumerate(orders):
            ready = CONFIG + (0x44C if side == 0 else 0x1224)
            pool = CONFIG + (0x1FFC if side == 0 else 0x2DD4)
            self.uc.mem_write(ready, bytes(0x6EC))
            self.uc.mem_write(pool, bytes(0x6EC))
            self.uc.mem_write(ready + 4, struct.pack('>H', 0x41))
            ranks = [0] * 6
            for rank, slot in enumerate(order, 1):
                ranks[slot] = rank
            self.uc.mem_write(UI + (0xDC if side == 0 else 0xE8), bytes(ranks))
            for slot in range(6):
                marker = 0xAB000000 + side * 0x100 + slot
                self.uc.mem_write(pool + slot * 0x8C + 0x1FC, struct.pack('>I', marker) + bytes([slot + 1]) * 0x84)
                self.uc.mem_write(pool + slot * 0x8C + 0x286, b'\x80')

    def pack(self):
        self.run(0x8015A1C4, instruction_limit=100000, participants=4)
        return bytes(self.uc.mem_read(CONFIG + 0x19, 1))[0]

    def packed_markers(self, side):
        base = CONFIG + (0x44C if side == 0 else 0x1224)
        return [word(self.uc.mem_read(base + i * 0x8C + 0x1FC, 4), 0)
                for i in range(6) if bytes(self.uc.mem_read(base + i * 0x8C + 0x286, 1))[0] & 0x80]

    def transfer(self, side, *, mode=0, phase=0, ai=0, round=1):
        self.mode, self.phase, self.ai, self.round, self.side = mode, phase, ai, round, side
        self.ai_counts = []
        self.uc.mem_write(CONFIG + 8, struct.pack('>I', 1))
        self.uc.mem_write(CONFIG + 16, struct.pack('>I', 1007 if mode == 11 else 1002))
        self.uc.mem_write(TEAM + side * 0x1000, struct.pack('>II', 6, 0) + bytes(6 * 0xA4))
        registers = {15: CTX, 19: side, 29: CONFIG, 25: side * 4,
                     24: side * 0x2C, 23: ORDERS + side * 6, 14: 0, 30: 2}
        self.run(0x80173188, registers=registers, reset_session=False,
                 until=0x80173468, instruction_limit=100000)
        base = TEAM + side * 0x1000
        count = word(self.uc.mem_read(base + 4, 4), 0)
        return [word(self.uc.mem_read(base + 8 + i * 0xA4, 4), 0) for i in range(count)]


def verify(original_dol, original_common, changed_dol, changed_common):
    original = HandoffNative(original_dol, read_archive(original_common)[11][1])
    changed = HandoffNative(changed_dol, read_archive(changed_common)[11][1])
    packing_cases = 0
    handoff_cases = 0
    for order in itertools.permutations(range(6), 4):
        orders = (order, tuple(reversed(order)))
        changed.seed(orders)
        pool_snapshots = [bytes(changed.uc.mem_read(CONFIG + base, 0x6EC))
                          for base in (0x1FFC, 0x2DD4)]
        if changed.pack() != 6:
            raise AssertionError('Full-roster packing behavior was unexpectedly changed')
        for base, snapshot in zip((0x1FFC, 0x2DD4), pool_snapshots):
            if bytes(changed.uc.mem_read(CONFIG + base, 0x6EC)) != snapshot:
                raise AssertionError('Selection packing modified the source party')
        for side in (0, 1):
            expected = [0xAB000000 + side * 0x100 + i for i in orders[side]]
            if changed.packed_markers(side) != expected:
                raise AssertionError('Native packing lost or reordered a selected Pokemon')
            if changed.transfer(side) != expected:
                raise AssertionError('Native append did not receive the four selected markers')
            packing_cases += 1
            handoff_cases += 1
    # Reproduce and fix the pair-only special encounter using the same packed input.
    baseline_special_sizes = []
    for native in (original, changed):
        native.seed(((0, 2, 4, 5), (5, 3, 1, 0)))
        native.pack()
        sizes = [len(native.transfer(side, mode=3, phase=1)) for side in (0, 1)]
        baseline_special_sizes.append(sizes)
    if baseline_special_sizes != [[2, 2], [4, 4]]:
        raise AssertionError(f'Special pair cap not reproduced/fixed: {baseline_special_sizes}')
    progressive = []
    for round in (1, 9, 10, 29, 30, 39, 40, 49):
        values = []
        for native in (original, changed):
            # AI can have six candidates even though the player picked four.
            # Verify the cap itself rather than relying on missing candidates.
            native.seed(((0, 1, 2, 3), (5, 4, 3, 2, 1, 0)))
            native.pack()
            values.append(len(native.transfer(1, mode=11, ai=1, round=round)))
        expected_before = 2 if round < 10 else (3 if round < 30 else (4 if round < 40 else 5))
        if values[0] != expected_before or values[1] != 4:
            raise AssertionError('Progressive encounter did not populate four opponents')
        progressive.append({'round': round, 'before': values[0], 'after': values[1]})
    return {'status': 'passed', 'native_packing_cases': packing_cases,
            'native_party_append_cases': handoff_cases,
            'special_pair_cap_before_after': baseline_special_sizes,
            'progressive_opponent_sizes': progressive,
            'native_party_append_routine': '0x803E1EC0 (executes without a stub)',
            'stubs': ['name registration', 'temporary allocation/free',
                      'AI order selection (first valid candidates)',
                      'Pokemon decoding and decoded-presence predicate',
                      'opponent-selection enable query'],
            'limits': ['Does not validate Pokemon decoding or AI quality',
                       'No rendering, battle, outcome, survival state or progression test']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('original-dol', 'original-common', 'work'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.original_dol.read_bytes(), args.original_common.read_bytes(),
                    (args.work / 'main.dol').read_bytes(), (args.work / 'common.fsys').read_bytes())
    (args.work / 'handoff-verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
