"""Private-asset Blender conversion helpers; never used by the public builder."""

import argparse
import hashlib
import importlib.util
from pathlib import Path
import sys
import bpy

SOURCE_SHA256 = "42ee39d351dc05e4f509267a2ce540286b134f6e8d024b776175a4c75c5a9308"
SLOTS = {
    "idle": "NorIdle0",
    "run": "Run0",
    "damage": "DamF0",
    "faint": "Faint0",
    "move_phys": "Atk0_0",
    "move_spec": "Atk2_0",
    "tx_wink": "NorIdle0",
    "tx_sleep": "Sleep0_1",
    "tx_wakeup": "Sleep0_2",
}


def arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--workdir", type=Path, required=True)
    parser.add_argument("--berrybush", type=Path, required=True)
    parser.add_argument("--pbr-addon", type=Path, required=True)
    parser.add_argument("--preview-action", default="idle")
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1 :])
    if not (3, 3, 0) <= bpy.app.version < (3, 5, 0):
        raise RuntimeError("Requires Blender 3.3 or 3.4 for BerryBush compatibility")
    if hashlib.sha256(args.source.read_bytes()).hexdigest() != SOURCE_SHA256:
        raise ValueError(
            "This experiment was audited for the supplied Tsutarja.brres only"
        )
    args.workdir.mkdir(parents=True, exist_ok=True)
    return args


def load_brres_addon(args):
    sys.path.insert(0, str(args.berrybush))
    import berrybush

    berrybush.register()
    # No online updater or preferences lookup is required for offline processing.
    bpy.app.handlers.load_post.remove(berrybush.updater.checkLatestVer)
    return berrybush


def load_pbr_addon(args, register=True):
    spec = importlib.util.spec_from_file_location(
        "pbr_io",
        str(args.pbr_addon / "__init__.py"),
        submodule_search_locations=[str(args.pbr_addon)],
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules["pbr_io"] = module
    spec.loader.exec_module(module)
    if register:
        module.register()
    return module
