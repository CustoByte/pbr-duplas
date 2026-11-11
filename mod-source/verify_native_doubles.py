"""Execute isolated original PPC routines with Unicorn; this is NOT a Dolphin test.

Only the record-index lookup and progression-flag query are stubbed. Original
table accessors, deck availability, default-format logic and initial participant
count logic execute as PPC instructions. Rendering, AI and progression do not.
"""
import argparse
import json
import struct
from pathlib import Path

from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn import ppc_const as ppc

from prepare_campaign_doubles import read_archive, word

CONFIG = 0x80800000
TABLE = 0x80900000
OBJECT = 0x806251D4
SDA = 0x80700000
STOP = 0x80FFF000


class Native:
    def __init__(self, dol, table):
        self.uc = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
        self.uc.mem_map(0x80000000, 0x01000000)
        for count, fo, ao, so in [(7, 0, 0x48, 0x90), (11, 0x1c, 0x64, 0xac)]:
            for index in range(count):
                off, addr, size = (word(dol, base + index * 4) for base in (fo, ao, so))
                if size:
                    self.uc.mem_write(addr, dol[off:off + size])
        relocated = bytearray(table)
        struct.pack_into('>I', relocated, 16, TABLE + word(table, 16))
        self.uc.mem_write(TABLE, bytes(relocated))
        self.uc.mem_write(OBJECT, struct.pack('>I', TABLE))
        self.uc.mem_write(SDA - 0x6574, struct.pack('>I', CONFIG))
        self.record = 0
        self.flag = 0
        self.stub_record_lookup = True
        self.uc.hook_add(UC_HOOK_CODE, self.hook)

    def hook(self, uc, address, size, user_data):
        if address == 0x8008BDFC and self.stub_record_lookup:
            uc.reg_write(ppc.UC_PPC_REG_3, self.record)
            uc.reg_write(ppc.UC_PPC_REG_PC, uc.reg_read(ppc.UC_PPC_REG_LR))
        elif address == 0x801675BC:
            flag_id = uc.reg_read(ppc.UC_PPC_REG_3)
            value = self.flag.get(flag_id, self.flag.get('other', 0)) if isinstance(self.flag, dict) else self.flag
            uc.reg_write(ppc.UC_PPC_REG_3, value)
            uc.reg_write(ppc.UC_PPC_REG_PC, uc.reg_read(ppc.UC_PPC_REG_LR))

    def run(self, entry, args=(), *, record=0, format=1, colosseum=1000, flag=0,
            stub_record_lookup=True, menu_index=0, master_stage=0,
            registers=None, until=STOP, instruction_limit=2000, participants=0,
            reset_session=True):
        self.record, self.flag = record, flag
        self.stub_record_lookup = stub_record_lookup
        for index in range(32):
            self.uc.reg_write(getattr(ppc, f'UC_PPC_REG_{index}'), 0)
        self.uc.reg_write(ppc.UC_PPC_REG_CR, 0)
        self.uc.reg_write(ppc.UC_PPC_REG_1, 0x80EF0000)
        self.uc.reg_write(ppc.UC_PPC_REG_13, SDA)
        self.uc.reg_write(ppc.UC_PPC_REG_LR, STOP)
        for index, value in enumerate(args, 3):
            self.uc.reg_write(getattr(ppc, f'UC_PPC_REG_{index}'), value)
        for index, value in (registers or {}).items():
            self.uc.reg_write(getattr(ppc, f'UC_PPC_REG_{index}'), value)
        if reset_session:
            self.uc.mem_write(CONFIG, bytes(512))
            self.uc.mem_write(CONFIG + 8, struct.pack('>I', format))
            self.uc.mem_write(CONFIG + 16, struct.pack('>I', colosseum))
            self.uc.mem_write(CONFIG + 0x19, bytes([participants]))
            self.uc.mem_write(CONFIG + 0x14, bytes([menu_index]))
            self.uc.mem_write(CONFIG + 0x145, bytes([master_stage]))
        self.uc.emu_start(entry, until, count=instruction_limit)
        if self.uc.reg_read(ppc.UC_PPC_REG_PC) != until:
            raise AssertionError(f'Routine failed to reach {until:#x} within instruction limit; PC={self.uc.reg_read(ppc.UC_PPC_REG_PC):#x}')
        return self.uc.reg_read(ppc.UC_PPC_REG_3)


def verify(original_dol, original_common, changed_dol, changed_table):
    table = read_archive(original_common)[11][1]
    original = Native(original_dol, table)
    changed = Native(changed_dol, changed_table)
    checks = 0
    resolved_records = set()
    resolver_cases = 0
    for floor in range(1000, 1010):
        for menu_index in range(14):
            for unlocked in (0, 1):
                for cleared in (0, 1):
                    for master_stage in range(8):
                        result = original.run(0x8008BDFC, colosseum=floor,
                                              menu_index=menu_index, master_stage=master_stage,
                                              flag={0x39: unlocked, 'other': cleared},
                                              stub_record_lookup=False)
                        resolved_records.add(result)
                        resolver_cases += 1
    if resolved_records != set(range(39)):
        raise AssertionError(f'Unexpected campaign record range: {sorted(resolved_records)}')
    baseline_formats = {'1': 0, '2': 0}
    for record in range(39):
        base = word(table, 16) + record * word(table, 4)
        old_format = 2 if word(table, base + 32) or word(table, base + 36) else 1
        for native, expected in [(original, old_format), (changed, 1)]:
            native.run(0x8008BBB8, record=record)
            result = word(native.uc.mem_read(CONFIG + 8, 4), 0)
            if result != expected:
                raise AssertionError(f'Default format mismatch for record {record}')
            checks += 1
        baseline_formats[str(old_format)] += 1
        for index in (0, 1):
            result = changed.run(0x8039BB04, (OBJECT, record, index))
            if result != 4:
                raise AssertionError(f'Participant count mismatch for record {record}')
            checks += 1
        if changed.run(0x8008BC40, record=record) != 0:
            raise AssertionError(f'Singles/doubles format toggle still available for record {record}')
        checks += 1
    original_counts = set()
    for colosseum in range(1000, 1010):
        for format in (1, 2):
            for flag in (0, 1):
                original.run(0x8008C254, colosseum=colosseum, format=format, flag=flag)
                original_counts.add(bytes(original.uc.mem_read(CONFIG + 0x19, 1))[0])
                changed.run(0x8008C254, colosseum=colosseum, format=format, flag=flag)
                if bytes(changed.uc.mem_read(CONFIG + 0x19, 1))[0] != 4:
                    raise AssertionError('Menu participant count override survived')
                checks += 1
    campaign_entry_checks = 0
    for begin, end, base_reg in [(0x80082ECC, 0x80082EE4, 28),
                                 (0x800836D0, 0x800836EC, 25),
                                 (0x8008406C, 0x80084084, 25),
                                 (0x80083148, 0x80083168, 25)]:
        for saved_format in (0, 1, 2, 3):
            for native, expected in [(original, saved_format), (changed, 1)]:
                native.run(begin, format=saved_format, registers={base_reg: CONFIG}, until=end)
                if native.uc.reg_read(ppc.UC_PPC_REG_6) != expected:
                    raise AssertionError('Campaign entry did not force the native doubles argument')
                campaign_entry_checks += 1
    constructor_prefix_checks = 0
    for record in range(39):
        for boss in (0, 1):
            for stale_count in (0, 3, 4, 5, 6):
                changed.run(0x8017F57C, (0x80A00000, record, 1, 1, 0, 0, boss, CONFIG),
                            record=record, format=2, participants=stale_count,
                            until=0x8017F6FC, instruction_limit=5000)
                if word(changed.uc.mem_read(CONFIG + 8, 4), 0) != 1:
                    raise AssertionError('Constructor failed to replace stale singles state')
                if bytes(changed.uc.mem_read(CONFIG + 0x19, 1))[0] != 4:
                    raise AssertionError('Constructor failed to propagate four participants')
                constructor_prefix_checks += 1
    return {'status': 'passed', 'native_scenarios_checked': checks,
            'campaign_record_resolver_scenarios': resolver_cases,
            'campaign_constructor_argument_checks': campaign_entry_checks,
            'constructor_prefix_checks': constructor_prefix_checks,
            'campaign_records_observed': sorted(resolved_records),
            'records_checked': 39, 'baseline_default_formats': baseline_formats,
            'baseline_initial_participant_counts': sorted(original_counts),
            'changed_initial_participant_count': 4,
            'stubs': ['record index lookup 0x8008BDFC', 'progression flag query 0x801675BC'],
            'limitations': ['Does not execute full game', 'No graphics or AI',
                            'No special-rule or campaign-progression validation']}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['original-dol', 'original-common', 'work']:
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.original_dol.read_bytes(), args.original_common.read_bytes(),
                    (args.work / 'main.dol').read_bytes(),
                    (args.work / 'colosseum-table.bin').read_bytes())
    if (args.work / 'common.fsys').exists():
        integrated = read_archive((args.work / 'common.fsys').read_bytes())[11][1]
        if integrated != (args.work / 'colosseum-table.bin').read_bytes():
            raise AssertionError('Working FSYS does not contain the tested table')
        result['working_fsys_contains_verified_table'] = True
    (args.work / 'native-verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))
