"""Apply small, pinned experimental-tool adaptations to private research clones.

No game data is changed. BerryBush is GPL-3.0-or-later; changes below disable
only GPU allocation during headless import. The PBR exporter changes preserve
float32 animation values instead of its lossy short/fuzzy-key approximation.
"""

import argparse
from pathlib import Path
import subprocess


def revision(root, expected):
    actual = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    if actual != expected:
        raise ValueError(f"Unexpected tool revision in {root}: {actual}")


def replace(path, replacements):
    source = path.read_text()
    for before, after in replacements:
        if before == after:
            raise ValueError("Empty adaptation")
        if before not in source:
            if after in source:
                continue
            raise ValueError(f"Expected tool source not found: {path}: {before}")
        if source.count(before) != 1:
            raise ValueError(f"Ambiguous adaptation: {path}")
        source = source.replace(before, after)
    path.write_text(source)


def prepare(berrybush, pbr):
    revision(berrybush, "5ff000f7362a3b18cc55e871fc3e1f645eb5e206")
    revision(pbr, "ed18e4fd606bf66b670c71c2484bf9fc86ea5b7d")
    replace(
        berrybush / "berrybush/blender/shaders.py",
        [
            (
                "BRRES_SHADER = compileBrresShader()",
                "BRRES_SHADER = None if bpy.app.background else compileBrresShader()",
            ),
            (
                "POSTPROCESS_SHADER = compilePostprocessShader()",
                "POSTPROCESS_SHADER = None if bpy.app.background else compilePostprocessShader()",
            ),
        ],
    )
    replace(
        berrybush / "berrybush/blender/render.py",
        [
            (
                "EMPTY_UBO = gpu.types.GPUUniformBuf(_EMPTY_UBO_BYTES)",
                "EMPTY_UBO = None if bpy.app.background else gpu.types.GPUUniformBuf(_EMPTY_UBO_BYTES)",
            ),
        ],
    )
    replace(
        pbr / "exporter/exporter.py",
        [
            ("rel_tol=1e-05, abs_tol=0.001", "rel_tol=1e-08, abs_tol=1e-08"),
            (
                "file.write('uchar', 0x8, entryAddr, offset=0x6)",
                "file.write('uchar', 0x0, entryAddr, offset=0x6)",
            ),
            ("exp = min(14, math.ceil(15 - math.log(umax, 2)) - 1)", "exp = 0"),
            ("(numFrames * 2 + 3) // 4 * 4", "numFrames * 4"),
            (
                "scaled = round(kf[1] * scale)\n        file.write('short', scaled, 0, whence='current')",
                "file.write('float', kf[1], 0, whence='current')",
            ),
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--berrybush", type=Path, required=True)
    parser.add_argument("--pbr-addon", type=Path, required=True)
    args = parser.parse_args()
    prepare(args.berrybush, args.pbr_addon)
    print("Pinned graphics tools prepared; no game assets changed.")
