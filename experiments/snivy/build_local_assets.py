"""Build PRIVATE model/portrait FSYS files from the player's own game inputs.

This is an asset preparation stage, NOT an installer, ISO builder or release.
It never opens a save and never changes the updater feed.
"""

import argparse
import json
from pathlib import Path

from icon_textures import atlases, encode_gtx, decode_gtx
from shiny_variant import prepare as shiny_variant
from resource_packages import model_package, append_resource
from icon_registry import FACE_ID, BODY_ID
from pkx_reference import inspect_package
from verify_native_asset import verify as verify_asset
from prepare_campaign_doubles import read_archive, sha


def build(workdir, reference, face_archive, body_archive, output):
    original_face, original_body = face_archive.read_bytes(), body_archive.read_bytes()
    if sha(original_face) != "05f0037c6cecf8a4e958d616a71c6c30af6d1d4dc37f4615d3051afff1f53e9a":
        raise ValueError("Requires audited original menu_face.fsys")
    if sha(original_body) != "8c39595a3b6176b709475674e143266f093bf657ff0bd025ddf6dea1cd1fbdad":
        raise ValueError("Requires audited original menu_pokemon.fsys")
    source = reference.read_bytes()
    contract = inspect_package(source)
    normal = (workdir / "snivy-experimental.sdr").read_bytes()
    if len(normal) > 3 * 1024 * 1024:
        raise ValueError("Converted model exceeds the audited 3 MiB memory budget")
    expected_uv = json.loads((workdir / "expected-uv.json").read_text())
    native_asset = verify_asset(normal, contract, expected_uv)
    roundtrip = json.loads((workdir / "roundtrip-report.json").read_text())
    if not roundtrip.get("passed") or roundtrip.get("sdr_sha256") != sha(normal):
        raise ValueError("Requires matching passed geometry/texture roundtrip report")
    shiny, shiny_report = shiny_variant(normal)
    faces, bodies = atlases(workdir / "portraits")
    face_texture, body_texture = encode_gtx(faces), encode_gtx(bodies)
    files = {
        "pkx_501.fsys": model_package(source, normal, shiny),
        "menu_face.fsys": append_resource(original_face, FACE_ID, face_texture, "snivy-face.gtx"),
        "menu_pokemon.fsys": append_resource(original_body, BODY_ID, body_texture, "snivy-body.gtx"),
    }
    report = dict(
        kind="private local graphics preparation, not an installable game update",
        protected_resources_bundled_in_public_project=False,
        original_face_entries_preserved=len(read_archive(original_face)),
        original_body_entries_preserved=len(read_archive(original_body)),
        native_asset_validation=native_asset,
        shiny_variant=shiny_report,
        outputs={name: dict(bytes=len(data), sha256=sha(data)) for name, data in files.items()},
        source_sha256={"pkx_388.fsys": sha(source), "menu_face.fsys": sha(original_face),
                       "menu_pokemon.fsys": sha(original_body), "normal_sdr": sha(normal)},
        playable=False, ready_to_publish=False, updater_changed=False,
        remaining=["Integrated common/DOL build", "Safe pass delivery and persistence",
                   "Full Little Battle eligibility", "AI species-dependent structures",
                   "In-game effects/animation/memory validation", "Local conversion integration in updater"],
    )
    output.mkdir(parents=True, exist_ok=False)
    for name, data in files.items():
        (output / name).write_bytes(data)
    decode_gtx(face_texture).save(output / "face-atlas-preview.png")
    decode_gtx(body_texture).save(output / "body-atlas-preview.png")
    (output / "local-assets-report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("workdir", "reference", "face-archive", "body-archive", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    report = build(args.workdir, args.reference, args.face_archive, args.body_archive, args.output)
    print(json.dumps(report, indent=2))
