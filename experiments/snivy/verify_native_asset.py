"""Check native-profile action metadata, attachment names and serialized UV curves.

Offline SDR validation, not native game execution or event synchronization.
"""

import argparse
import json
import math
from pathlib import Path
import struct

from native_graphics_profile import ANCHORS
from pkx_reference import inspect_package, scene_inventory


def verify(data, reference, expected_uv):
    actual = scene_inventory(data)
    template = reference["resources"][0]
    if actual["object_name"] != "SnivyExport":
        raise ValueError("Expected independent Snivy object")
    if [a["name"] for a in actual["actions"]] != [
        a["name"] for a in template["actions"]
    ]:
        raise ValueError("Native action order differs")
    for target, source in zip(actual["actions"], template["actions"]):
        if target["flags"] != source["flags"]:
            raise ValueError("Native body/material flags differ")
        for field in ("start", "end"):
            if not math.isclose(
                target[field] / target["length"],
                source[field] / source["length"],
                abs_tol=1e-6,
            ):
                raise ValueError("Reference timing fraction differs")
    names = {node["name"] for node in actual["nodes"]}
    if set(ANCHORS) - names:
        raise ValueError("Missing effect/control attachment names")

    def read(offset, size):
        if offset < 0 or offset + size > len(data):
            raise ValueError("Material reference outside SDR")
        return data[offset : offset + size]

    def u32(offset):
        return struct.unpack(">I", read(offset, 4))[0]

    def u16(offset):
        return struct.unpack(">H", read(offset, 2))[0]

    def string(offset):
        end = data.find(b"\0", offset)
        if end < offset or end - offset > 256:
            raise ValueError("Invalid material name")
        return read(offset, end - offset).decode("ascii")

    curves = {}
    for material_index in range(u16(30)):
        material = u32(u32(20) + 4 * material_index)
        material_name = string(u32(material))
        link = u32(material + 132)
        seen = set()
        while link:
            if link in seen or len(seen) >= len(actual["actions"]):
                raise ValueError("Cyclic material action chain")
            seen.add(link)
            action_index, channels = u16(link), u16(link + 2)
            if action_index >= len(actual["actions"]) or channels != 4:
                raise ValueError("Invalid material channels")
            name = actual["actions"][action_index]["name"]
            for i in range(channels):
                channel = u32(link + 4) + i * 16
                component, axis, dtype, exponent = (
                    data[channel + 1],
                    data[channel + 2],
                    data[channel + 6],
                    data[channel + 7],
                )
                if (
                    component not in (20, 22)
                    or axis not in (1, 2)
                    or (dtype, exponent) != (0, 0)
                ):
                    raise ValueError("Unexpected UV curve encoding")
                track = u32(channel + 8)
                value_count, key_count = u16(track + 8), u16(track + 20)
                values, keys = u32(track), u32(track + 16)
                points = []
                for key in range(key_count):
                    at = keys + key * 12
                    interpolation, index = u16(at), u16(at + 2)
                    if interpolation != 0 or index >= value_count:
                        raise ValueError("Unexpected material key")
                    points.append(
                        (
                            struct.unpack(">f", read(at + 8, 4))[0],
                            struct.unpack(">f", read(values + 4 * index, 4))[0],
                        )
                    )
                if not points:
                    raise ValueError("Missing material keyframes")
                curves[name, material_name, component, axis] = points
            link = u32(link + 12)
    max_error, samples = 0, 0
    for action, frames in expected_uv.items():
        for frame, materials in frames.items():
            for material, components in materials.items():
                for component, code in (("translation", 20), ("scale", 22)):
                    for axis, target in enumerate(components[component], start=1):
                        points = curves[action, material, code, axis]
                        prior = [
                            value
                            for time, value in points
                            if time <= int(frame) / 30 + 1e-6
                        ]
                        if not prior:
                            raise ValueError("No UV key at requested time")
                        max_error = max(max_error, abs(prior[-1] - target))
                        samples += 1
    if max_error > 1e-6:
        raise ValueError("UV serialization regression")
    wink = expected_uv["tx_wink"]
    if (
        wink["0"]["Snivy_Eye"] == wink["1"]["Snivy_Eye"]
        or wink["0"]["Snivy_Eye"] != wink["4"]["Snivy_Eye"]
    ):
        raise ValueError("Blink must close and reopen the source eyes")
    return dict(
        kind="offline native-profile asset validation",
        passed=True,
        actions=len(actual["actions"]),
        nodes=len(actual["nodes"]),
        effect_control_attachments=len(ANCHORS),
        uv_scalar_samples=samples,
        max_uv_error=max_error,
        blink_changes_and_restores_uv=True,
        reference_metadata_matched=True,
        sdr_sha256=actual["sha256"],
        native_game_tested=False,
        effects_positions_calibrated=False,
        event_synchronization_verified=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sdr", type=Path, required=True)
    parser.add_argument("--reference", type=Path, required=True)
    parser.add_argument("--uv", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = verify(
        args.sdr.read_bytes(),
        inspect_package(args.reference.read_bytes()),
        json.loads(args.uv.read_text()),
    )
    args.report.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))
