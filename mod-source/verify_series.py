"""Exercise the doubles best-of-three result block with synthetic result/HP data.

Scoring branches, floating-point HP tie-break, phase changes, roster copies and
slot cleanup execute in PPC. Rendering callback and decoded-HP getters are stubs.
This does not execute the battle or write a save.
"""
import argparse
import itertools
import json
import struct
from pathlib import Path

from unicorn import ppc_const as ppc

from prepare_campaign_doubles import read_archive, word
from verify_native_doubles import Native, CONFIG, SDA

MANAGER = 0x80D00000
SOURCE = 0x80D10000
SDA2 = 0x806308E0


class SeriesNative(Native):
    def __init__(self, dol, table):
        super().__init__(dol, table)
        self.history = ()
        self.hp = (50, 50)
        self.missing_flags = False
        self.callbacks = 0
        self.inject_history = True
        self.uc.mem_write(SDA - 0x7E08, struct.pack('>I', MANAGER))
        self.uc.reg_write(ppc.UC_PPC_REG_MSR, 0x2000)  # Enable native FP instructions.

    def hook(self, uc, address, size, data):
        super().hook(uc, address, size, data)
        if address == 0x80076B1C and self.inject_history:
            uc.mem_write(CONFIG + 0x18, bytes([len(self.history)]))
            uc.mem_write(CONFIG + 0x80, bytes(self.history))
        if address == 0x80258AA4:
            self.callbacks += 1
            uc.reg_write(ppc.UC_PPC_REG_3, 0)
            uc.reg_write(ppc.UC_PPC_REG_PC, uc.reg_read(ppc.UC_PPC_REG_LR))
        elif address == 0x803E100C:
            pointer = uc.reg_read(ppc.UC_PPC_REG_3)
            field = uc.reg_read(ppc.UC_PPC_REG_4)
            side = 0 if pointer < CONFIG + 0x61B8 else 1
            base = CONFIG + (0x5760 if side == 0 else 0x61B8)
            slot = (pointer - base) // 0xDC
            if not 0 <= slot < 6 or field not in (0xA2, 0xA3):
                raise AssertionError('Unexpected HP getter invocation')
            value = (self.hp[side] if field == 0xA2 else 100) if slot < 4 else 0
            uc.reg_write(ppc.UC_PPC_REG_3, value)
            uc.reg_write(ppc.UC_PPC_REG_PC, uc.reg_read(ppc.UC_PPC_REG_LR))

    def seed(self, history, hp=(50, 50), missing_flags=False):
        self.history, self.hp, self.missing_flags = history, hp, missing_flags
        self.callbacks = 0
        self.uc.mem_write(MANAGER, bytes(0x600))
        self.uc.mem_write(MANAGER + 0x30, struct.pack('>I', CONFIG))
        self.uc.mem_write(MANAGER + 0xC, struct.pack('>I', 2))
        for side in (0, 1):
            target_base = CONFIG + (0x648 if side == 0 else 0x1420)
            for slot in range(6):
                source = SOURCE + side * 0x1000 + slot * 0x8C
                payload = bytes([0x20 + slot + side * 16]) * 0x88 if slot < 4 else bytes(0x88)
                uc_data = payload + b'\x00\x00' + bytes([0x80 if slot < 4 else 0]) + b'\x00'
                self.uc.mem_write(source, uc_data)
                self.uc.mem_write(MANAGER + (0x538 if side == 0 else 0x550) + slot * 4,
                                  struct.pack('>I', source))
                self.uc.mem_write(target_base + slot * 0x8C, b'\xEE' * 0x88)
                self.uc.mem_write(target_base + slot * 0x8C + 0x8A,
                                  bytes([0x15 if missing_flags else 0x95]))
        # Native integer-to-double conversion scratch words from the caller frame.
        for offset in (0x18, 0x20):
            self.uc.mem_write(0x80EF0000 + offset, struct.pack('>I', 0x43300000))

    def process(self):
        self.run(0x80076B1C, registers={2: SDA2, 29: 0, 30: 0},
                 until=0x8007712C, instruction_limit=100000)
        result = {'phase': bytes(self.uc.mem_read(CONFIG + 0x18, 1))[0],
                  'scan_count': bytes(self.uc.mem_read(CONFIG + 0x19, 1))[0],
                  'manager_state': word(self.uc.mem_read(MANAGER + 0xC, 4), 0),
                  'outcome_flag': bytes(self.uc.mem_read(MANAGER + 0x52A, 1))[0],
                  'callbacks': self.callbacks}
        return result

    def check_rosters(self):
        for side in (0, 1):
            base = CONFIG + (0x648 if side == 0 else 0x1420)
            for slot in range(6):
                pointer = base + slot * 0x8C
                data = bytes(self.uc.mem_read(pointer, 0x88))
                flags = bytes(self.uc.mem_read(pointer + 0x8A, 1))[0]
                expected = bytes([0x20 + slot + side * 16]) * 0x88 if slot < 4 else bytes(0x88)
                if data != expected or bool(flags & 0x80) != (slot < 4) or flags & 0x7F != 0x15:
                    raise AssertionError(f'Incorrect restoration/cleanup side={side} slot={slot}')


def verify(original_dol, common, changed_dol):
    table = read_archive(common)[11][1]
    baseline = SeriesNative(original_dol, table)
    current = SeriesNative(changed_dol, table)
    histories, ties, early, source_checks = 0, 0, 0, 0
    for length in (1, 2, 3):
        for history in itertools.product((0, 1, 2), repeat=length):
            if length == 3 and (history[:2].count(0) == 2 or history[:2].count(1) == 2):
                continue  # Already finished after two wins.
            for hp in ((50, 50), (75, 25), (25, 75)):
                wins, losses = history.count(0), history.count(1)
                terminal = length == 3 or wins == 2 or losses == 2
                expected_flag = 0
                if terminal:
                    expected_flag = 1 if wins > losses else (2 if losses > wins else
                                    (1 if hp[0] > hp[1] else (2 if hp[1] > hp[0] else 3)))
                for missing in (False, True):
                    current.seed(history, hp, missing)
                    source = bytes(current.uc.mem_read(SOURCE, 0x2000))
                    result = current.process()
                    if result['scan_count'] != 4 or result['phase'] != (1 if terminal else length + 1):
                        raise AssertionError(f'Invalid series continuation: {history} {result}')
                    if result['manager_state'] != (4 if terminal else 3) or result['callbacks'] != int(terminal):
                        raise AssertionError('Manager transition/callback count mismatch')
                    if result['outcome_flag'] != expected_flag:
                        raise AssertionError(f'Unexpected winner: {history} {hp} {result}')
                    current.check_rosters()
                    if source != bytes(current.uc.mem_read(SOURCE, 0x2000)):
                        raise AssertionError('Restoration modified source snapshots')
                    histories += 1
                    source_checks += 1
                    ties += int(terminal and wins == losses)
                    early += int(length == 2 and terminal)
    baseline.seed((0,))
    before = baseline.process()
    if before['scan_count'] != 2:
        raise AssertionError('Original pair cleanup not reproduced')
    # Verify the native result accessor's stable protocol without changing its code.
    accessor_cases = 0
    for flag, expected in ((1, 0), (2, 1), (3, 2)):
        current.uc.mem_write(MANAGER + 0xC, struct.pack('>I', 5))
        current.uc.mem_write(MANAGER + 0x52A, bytes([flag]))
        if current.run(0x80075394, reset_session=False) != expected:
            raise AssertionError('Result accessor protocol changed')
        accessor_cases += 1
    return {'status': 'passed', 'series_state_cases': histories,
            'early_finish_cases': early, 'HP_tiebreak_cases': ties,
            'source_snapshot_checks': source_checks, 'result_accessor_cases': accessor_cases,
            'original_cleanup_count': before['scan_count'], 'changed_cleanup_count': 4,
            'policy': 'Best of three, two wins; same selected quartet restored between encounters',
            'stubs': ['rendering callback 0x80258AA4', 'decoded HP/max-HP attributes 0x803E100C'],
            'limits': ['Injected result history and HP, no actual battle',
                       'No outer event-loop, tournament advancement, save or rewards test']}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('original-dol', 'original-common', 'work'):
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    report = verify(args.original_dol.read_bytes(), args.original_common.read_bytes(),
                    (args.work / 'main.dol').read_bytes())
    (args.work / 'series-verification.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))
