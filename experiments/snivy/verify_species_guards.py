"""Execute every selective species bridge and the real menu presence check."""

import argparse
import json
from pathlib import Path
from unicorn import ppc_const as ppc

from names import patch_dol as name_dol
from species_guards import patch_dol
from prepare_campaign_doubles import sha
from verify_coop_draft import DraftReplay


def verify(capture, dol_path):
    source = name_dol(dol_path.read_bytes(), 21775)
    target, bridges = patch_dol(source)
    old, new = DraftReplay(capture, source), DraftReplay(capture, target)
    values = (0, 1, 492, 493, 494, 495, 496, 497, 498, 499, 500, 501, 502,
              600, 601, 65535, 0x80000000, 0xFFFFFFFF)
    checked = 0
    for bridge in bridges:
        site, reg = int(bridge["site"], 16), bridge["register"]
        for value in values:
            for overflow in (0, 0x80000000):
                states = []
                for h in (old, new):
                    for i in range(32):
                        h.uc.reg_write(getattr(ppc, f"UC_PPC_REG_{i}"), 0x10000000 + i * 0x10101)
                    h.uc.reg_write(getattr(ppc, f"UC_PPC_REG_{reg}"),
                                   bridge["old_limit"] if h is old and value == 501 else value)
                    h.uc.reg_write(ppc.UC_PPC_REG_CR, 0xA5F03C96)
                    h.uc.reg_write(ppc.UC_PPC_REG_XER, overflow)
                    h.uc.reg_write(ppc.UC_PPC_REG_CTR, 0x76543210)
                    h.uc.reg_write(ppc.UC_PPC_REG_LR, 0x81F10000)
                    gprs = [h.uc.reg_read(getattr(ppc, f"UC_PPC_REG_{i}")) for i in range(32)]
                    h.uc.emu_start(site, site + 4, count=32)
                    assert h.uc.reg_read(ppc.UC_PPC_REG_PC) == site + 4
                    assert [h.uc.reg_read(getattr(ppc, f"UC_PPC_REG_{i}")) for i in range(32)] == gprs
                    assert h.uc.reg_read(ppc.UC_PPC_REG_CTR) == 0x76543210
                    assert h.uc.reg_read(ppc.UC_PPC_REG_LR) == 0x81F10000
                    assert h.uc.reg_read(ppc.UC_PPC_REG_XER) == overflow
                    states.append(h.uc.reg_read(ppc.UC_PPC_REG_CR))
                assert states[0] == states[1], (bridge, value, states)
                checked += 1
    # Presence-only fixture: clone an existing valid box, then change species
    # through the native setter. This is NOT the player's pass migration.
    def presence(h):
        rental = h.call(0x800E8594, (37,))
        box, value_address = 0x81D10000, 0x81D11000
        h.uc.mem_write(box, bytes(h.uc.mem_read(rental + 0x1FC + 0x8C, 0x8C)))
        before = h.call(0x80058C34, (box,))
        h.put(value_address, 501)
        h.call(0x803DECA8, (box, 5, value_address))
        assert h.call(0x803DE52C, (box, 5, 0)) == 501
        return before, h.call(0x80058C34, (box,))
    original, patched = presence(old), presence(new)
    assert original == (1, 0) and patched == (1, 1), (original, patched)
    for setter in (0x8026EABC, 0x8026EACC):
        assert new.call(setter, (0x80640000,)) == 0x80647200
        assert new.call(setter, (0x80650000,)) == 0x80650000
    return dict(
        kind="offline native selective species guards and menu presence predicate",
        passed=True, bridges=bridges, native_compare_cases=checked,
        all_gprs_lr_ctr_xer_preserved=True,
        all_other_species_values_keep_original_comparison=True,
        egg_and_alternate_form_indices_not_shifted=True,
        original_menu_presence_for_snivy=original[1], patched_menu_presence_for_snivy=patched[1],
        source_dol_sha256=sha(source), target_dol_sha256=sha(target),
        limits=["Known audited guards only; not a proof that every species-dependent path is complete",
                "No Little Battle validation, player pass delivery or actual gameplay",
                "No table registration or model loading in this proof"],
        playable=False, published_in_updater=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("capture", "dol", "report"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = verify(args.capture, args.dol)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "bridges"}, indent=2))
