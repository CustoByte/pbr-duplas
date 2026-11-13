"""Checked inventory of the supplied native Pokémon package; no asset export."""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

from prepare_campaign_doubles import read_archive

REFERENCE_SHA = "ce02a053b41bc806391bf3bb4606faffcae3edc7b974120959d25f488f75afb8"
ORDER = (
    "wait",
    "run",
    "damage",
    "down",
    "tackle",
    "kime",
    "kime_a",
    "tx_wink",
    "tx_sleep",
    "tx_wakeup",
    "mamoru",
    "kime_phy",
)


def scene_inventory(data):
    def read(offset, length):
        if offset < 0 or length < 0 or offset + length > len(data):
            raise ValueError("SDR reference outside resource")
        return data[offset : offset + length]

    def u32(offset):
        return struct.unpack(">I", read(offset, 4))[0]

    def u16(offset):
        return struct.unpack(">H", read(offset, 2))[0]

    def string(offset):
        end = data.find(b"\0", offset)
        if offset < 0 or end < offset or end - offset > 256:
            raise ValueError("Invalid SDR string")
        return read(offset, end - offset).decode("ascii")

    if read(0, 4) != b"\x01\x00\x00\x04" or u16(24) != 1:
        raise ValueError("Unexpected native scene version or object count")
    obj = u32(u32(8))
    count, table = u16(obj + 8), u32(obj + 12)
    if not 1 <= count <= 128:
        raise ValueError("Invalid action count")
    actions = []
    for index in range(count):
        at = table + index * 48
        row = read(at, 48)
        start, end, length = struct.unpack_from(">fff", row, 4)
        if (
            not all(math.isfinite(v) for v in (start, end, length))
            or not 0 <= start <= end <= length
            or length <= 0
        ):
            raise ValueError("Invalid native action markers")
        actions.append(
            dict(
                index=index,
                name=string(u32(at)),
                start=start,
                end=end,
                length=length,
                flags=list(row[40:44]),
                bone_filter_count=u16(at + 24),
                material_filter_count=u16(at + 26),
            )
        )
    nodes, seen = [], set()

    def walk(at):
        if not at:
            return
        if at in seen or len(seen) >= u16(obj + 6):
            raise ValueError("Cyclic or oversized node tree")
        seen.add(at)
        read(at, 48)
        nodes.append(dict(index=u16(at + 8), type=u32(at), name=string(u32(at + 4))))
        walk(u32(at + 36))
        walk(u32(at + 40))

    walk(u32(obj + 16))
    if len(nodes) != u16(obj + 6) or len({n["index"] for n in nodes}) != len(nodes):
        raise ValueError("Node count/index mismatch")
    textures = []
    for index in range(u16(26)):
        at = u32(u32(12) + index * 4)
        pixels, size = at + u32(at + 40), u32(at + 76)
        read(pixels, size)
        textures.append(
            dict(
                index=index,
                width=u16(at),
                height=u16(at + 2),
                encoding=u32(at + 8),
                wrap_s=u32(at + 16), wrap_t=u32(at + 20),
                data_offset=pixels,
                data_size=size,
            )
        )
    return dict(
        object_name=string(u32(obj)),
        actions=actions,
        nodes=nodes,
        textures=textures,
        sha256=hashlib.sha256(data).hexdigest(),
    )


def inspect_package(data):
    if hashlib.sha256(data).hexdigest() != REFERENCE_SHA:
        raise ValueError("Requires the supplied unmodified pkx_388.fsys")
    resources = read_archive(data)
    if [key for key, _ in resources] != [0x1B7B0400, 0x1FDD0400]:
        raise ValueError("Unexpected native resource IDs")
    scenes = [scene_inventory(payload) for _, payload in resources]
    for scene in scenes:
        if (
            scene["object_name"] != "hayashigame"
            or tuple(a["name"] for a in scene["actions"]) != ORDER
        ):
            raise ValueError("Native reference contract differs")
    a, b = [payload for _, payload in resources]
    ranges = [
        (t["data_offset"], t["data_offset"] + t["data_size"])
        for t in scenes[0]["textures"]
    ]
    if len(a) != len(b):
        raise ValueError("Variant sizes differ")
    differences = [i for i, (x, y) in enumerate(zip(a, b)) if x != y]
    outside = sum(not any(lo <= i < hi for lo, hi in ranges) for i in differences)
    return dict(
        source_sha256=REFERENCE_SHA,
        resources=[
            dict(resource_id=f"{key:08x}", **scene)
            for (key, _), scene in zip(resources, scenes)
        ],
        differing_bytes=len(differences),
        differences_outside_texture_data=outside,
        variants_have_same_actions=scenes[0]["actions"] == scenes[1]["actions"],
        modified_original=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = inspect_package(args.source.read_bytes())
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "resources"}, indent=2))
