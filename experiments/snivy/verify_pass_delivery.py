"""Execute delivery on a private clone of the supplied menu state's pass data.

Native constructors, PK4 getters, ownership setters and Little Battle validator
run unchanged. Allocation/free use explicit bounded scratch fixtures. No NAND,
save file, GPU or actual Dolphin gameplay is exercised.
"""

import argparse
import json
from pathlib import Path
import struct

from unicorn import Uc, UC_ARCH_PPC, UC_MODE_32, UC_MODE_BIG_ENDIAN, UC_HOOK_CODE
from unicorn import ppc_const as ppc

from verify_vm_wait import Replay
from prepare_campaign_doubles import read_archive, word, sha
from integration_data import prepare
from names import MESSAGE_RESOURCE
from catalog import append_archive, relocate
from runtime_build import build


class MenuReplay(Replay):
    def __init__(self, capture, original_dol, changed_dol):
        self.uc = Uc(UC_ARCH_PPC, UC_MODE_32 | UC_MODE_BIG_ENDIAN)
        memory = (capture / "mem1.bin").read_bytes()
        self.checked_sections = []
        for i in range(7):
            off, address, size = (word(original_dol, base + i * 4) for base in (0, 0x48, 0x90))
            if size:
                if memory[address - 0x80000000:address - 0x80000000 + size] != original_dol[off:off + size]:
                    raise ValueError("Capture executable differs from test13")
                self.checked_sections.append(i)
        for name, base in (("mem1.bin", 0x80000000), ("mem2.bin", 0x90000000)):
            data = (capture / name).read_bytes()
            self.uc.mem_map(base, len(data))
            self.uc.mem_write(base, data)
        for i in range(7):
            off, address, size = (word(changed_dol, base + i * 4) for base in (0, 0x48, 0x90))
            if size:
                self.uc.mem_write(address, changed_dol[off:off + size])
        self.uc.reg_write(ppc.UC_PPC_REG_MSR, 0x2000)
        self.next_allocation = 0x81C00000
        self.allocations = []
        def allocation(u, address, size, unused):
            result = 0
            if address in (0x801728E4, 0x801DF6B4):
                count = u.reg_read(ppc.UC_PPC_REG_4 if address == 0x801728E4 else ppc.UC_PPC_REG_3)
                if not 0 < count <= 0x20000:
                    raise AssertionError(f"Unexpected scratch allocation: {count}")
                result = self.next_allocation
                self.next_allocation += (count + 31) & ~31
                assert self.next_allocation < 0x81C80000
                u.mem_write(result, bytes(count))
                self.allocations.append(count)
            u.reg_write(ppc.UC_PPC_REG_3, result)
            u.reg_write(ppc.UC_PPC_REG_PC, u.reg_read(ppc.UC_PPC_REG_LR))
        for address in (0x801728E4, 0x801DF6B4, 0x80172A14, 0x801DF6FC):
            self.uc.hook_add(UC_HOOK_CODE, allocation, begin=address, end=address)


def register(h, replacements, source_messages, catalog):
    references = {0x00810200: 0x80625184, 0x00800200: 0x80625174,
                  0x007D0200: 0x80625178, 0x16410200: 0x806251C0,
                  0x1D9D0200: 0x806251D8, 0x00820200: 0x80625188,
                  0x12A90200: 0x806251BC}
    for slot, (resource, reference) in enumerate(references.items()):
        table = replacements[resource]
        count, stride = struct.unpack_from(">II", table)
        obj = bytearray(h.uc.mem_read(h.get(reference), 48))
        object_at, data_at = 0x81B00000 + slot * 0x100, 0x81810000 + slot * 0x10000
        rows = table[48:48 + count * stride]
        for offset, value in ((0, count), (8, data_at), (16, data_at),
                              (20, len(rows)), (24, data_at + len(rows))):
            struct.pack_into(">I", obj, offset, value)
        h.uc.mem_write(object_at, bytes(obj))
        h.uc.mem_write(data_at, rows)
        h.put(reference, object_at)
    context = 0x8048062C
    h.uc.mem_write(0x92C00000, source_messages)
    h.uc.mem_write(0x92E00000, replacements[0x008B0000])
    h.put(context + 0x64F34, 0x92C00000)
    h.put(context + 0xD34, 21775)
    h.put(context + 0xD38, 0x92E00008)
    h.uc.mem_write(0x81B80000, relocate(append_archive(catalog), 0x81B80000))
    h.put(0x80627B5C, 0x81B80000)


def verify(capture, dol_path, common_path, messages_path, catalog_path, sdr_path, payload_path):
    dol, common, messages, catalog, sdr = (p.read_bytes() for p in (dol_path, common_path, messages_path, catalog_path, sdr_path))
    payload = json.loads(payload_path.read_text())
    changed = build(dol, payload)
    replacements, new_messages = prepare(dict(read_archive(common)), dict(read_archive(messages))[MESSAGE_RESOURCE], sdr)
    h = MenuReplay(capture, dol, changed)
    original_base = h.get(0x80453184)
    original_passes = bytes(h.uc.mem_read(original_base, 159 * 0x6EC))
    clone = 0x81D00000
    h.uc.mem_write(clone, original_passes)
    h.put(0x80453184, clone)
    before_personal = h.call(0x800E7CE8, (7, 0))
    # Before registration, readiness guard must not modify a player's passes.
    h.call(0x800E8594, (0,))
    assert bytes(h.uc.mem_read(clone, len(original_passes))) == original_passes
    register(h, replacements, new_messages, catalog)
    h.call(0x800E8594, (0,), limit=10000000)
    delivered = bytes(h.uc.mem_read(clone, len(original_passes)))
    changed_slots = [i for i in range(159) if delivered[i * 0x6EC:(i + 1) * 0x6EC] != original_passes[i * 0x6EC:(i + 1) * 0x6EC]]
    assert changed_slots == [0, 37], changed_slots
    assert h.call(0x800E7CE8, (7, 0)) == before_personal + 1
    assert h.call(0x800E7CE8, (2, 0)) == 0 and h.call(0x800E7CE8, (4, 0)) == 1
    records = []
    for pass_index, slot in [(0, i) for i in range(6)] + [(37, 1)]:
        mon = clone + pass_index * 0x6EC + 0x1FC + slot * 0x8C
        get = lambda field: h.call(0x803DE52C, (mon, field, 0))
        result = dict(pass_index=pass_index, slot=slot, species=get(5), level=get(160),
                      moves=[get(f) for f in range(0x36, 0x3A)],
                      pp=[get(f) for f in range(0x3A, 0x3E)],
                      ability=get(10), item=get(6), nature=get(0) % 25,
                      ivs=[get(f) for f in range(0x46, 0x4C)], evs=[get(f) for f in range(0xD, 0x13)],
                      presence=h.call(0x80058C34, (mon,)), illegal=h.call(0x80058E8C, (mon,)))
        if result['species'] == 501:
            party_dest = 0x81D90000
            h.uc.mem_write(party_dest, bytes(0xA4))
            h.call(0x803DFD78, (mon, party_dest), limit=3000000)
            result['stats_hp_atk_def_speed_spatk_spdef'] = [h.call(0x803E100C, (party_dest, field, 0)) for field in range(163, 169)]
        records.append(result)
    assert [r["species"] for r in records[:6]] == [501, 4, 7, 387, 390, 393], records
    assert all(r["level"] == 5 and r["presence"] == 1 and r["illegal"] == 0 for r in records[:6]), records
    assert records[6]["species"] == 501 and records[6]["level"] == 50 and records[6]["item"] == 157
    assert records[0]['ivs'] == [15] * 6 and records[0]['evs'] == [0] * 6, records[0]
    assert records[0]['stats_hp_atk_def_speed_spatk_spdef'] == [20, 9, 11, 13, 10, 11], records[0]
    assert records[6]['ivs'] == [31] * 6 and records[6]['evs'] == [4, 0, 0, 252, 252, 0], records[6]
    assert records[6]['stats_hp_atk_def_speed_spatk_spdef'] == [121, 58, 75, 138, 97, 75], records[6]
    # Native campaign pass eligibility, using actual Little Battle mode 7.
    session = h.call(0x8011F458)
    h.put(session + 0xC, 0)
    h.uc.mem_write(session + 0x14, b"\7")
    h.uc.mem_write(session + 0x19, b"\4")
    little = h.call(0x8008EE00, (), limit=10000000)
    assert little == 0, ("Native Little validator found no eligible pass", records)
    after_validation = bytes(h.uc.mem_read(clone, len(original_passes)))
    h.call(0x800E8594, (0,), limit=10000000)
    assert bytes(h.uc.mem_read(clone, len(original_passes))) == after_validation
    # Preserve customized/occupied personal slots and a player-modified rental.
    # Work only on the private clone and restore the proven delivery afterwards.
    for i in range(37):
        h.uc.mem_write(clone + i * 0x6EC, original_passes[i * 0x6EC:(i + 1) * 0x6EC])
        h.uc.mem_write(clone + i * 0x6EC, b"X")
    custom_before = bytes(h.uc.mem_read(clone, len(original_passes)))
    h.call(0x800E8594, (0,), limit=10000000)
    assert bytes(h.uc.mem_read(clone, len(original_passes))) == custom_before
    h.uc.mem_write(clone, after_validation)
    # Consumption is native and remains consumed until the explicit carry hook.
    party = 0x81D80000
    source = clone + 0x1FC
    h.uc.mem_write(party, bytes(h.uc.mem_read(source, 0x8C)))
    value = 0x81D81000
    h.put(value, 0)
    h.call(0x803DECA8, (party, 6, value))
    assert h.call(0x803DE52C, (party, 6, 0)) == 0
    h.call(payload["symbols"]["snivy_carry"], (party, 6, value), limit=10000000)
    assert h.call(0x803DE52C, (party, 6, 0)) == 157
    # If the player removes the source Berry, do not force it back.
    h.call(0x803DECA8, (source, 6, value))
    h.call(0x803DECA8, (party, 6, value))
    h.call(payload["symbols"]["snivy_carry"], (party, 6, value), limit=10000000)
    assert h.call(0x803DE52C, (party, 6, 0)) == 0
    h.uc.mem_write(clone, after_validation)
    # Guard against reads beyond fixed legacy prediction/narrator tables.
    for reference, getter, count, row_at in (
        (0x806251E8, 0x8039D068, 499, 0x80646600),
        (0x80626C94, 0x803987E4, 494, 0x80646660),
    ):
        baseline = MenuReplay(capture, dol, dol)
        argument = h.get(reference) if getter == 0x803987E4 else reference
        for species_id in range(count):
            assert h.call(getter, (argument, species_id)) == baseline.call(getter, (argument, species_id))
        assert h.call(getter, (argument, 501)) == row_at
    assert bytes(h.uc.mem_read(original_base, len(original_passes))) == original_passes
    return dict(
        kind="native delivery on private cloned pass memory; no NAND or actual UI render",
        passed=True, capture_header=json.loads((capture / "state-header.json").read_text()),
        executable_text_sections_identical=h.checked_sections,
        readiness_gate_preserved_old_passes=True, changed_pass_indices=changed_slots,
        original_user_pass_memory_untouched=True, native_personal_count_increased_by=1,
        native_personal_category=0, native_ownership_verified=True,
        native_little_validator_result=little, repeated_delivery_idempotent=True,
        customized_empty_slots_preserved=True, lum_consumption_and_restore_verified=True,
        removed_source_berry_respected=True, legacy_prediction_and_narrator_rows_verified=993,
        generated_pokemon=records, source_dol_sha256=sha(dol), target_dol_sha256=sha(changed),
        scratch_allocation_sizes=sorted(set(h.allocations)),
        playable_release=False, updater_changed=False,
        limits=["Native game routines run offline with explicit scratch allocation/free fixtures",
                "No actual menu frame, filesystem model load, battle sequence or save/load in Dolphin"],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "dol", "common", "messages", "catalog", "sdr", "payload", "report"):
        parser.add_argument("--" + name, type=Path, required=True)
    a = parser.parse_args()
    result = verify(a.capture, a.dol, a.common, a.messages, a.catalog, a.sdr, a.payload)
    a.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
