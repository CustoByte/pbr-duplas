"""Create a private SDR variant using names observed in actual native USA models.

Only four name pointers plus appended strings change. Curve IDs, geometry,
materials and all original bytes outside those pointers remain intact. This
prepares core name lookup; it does not register a species or bind battle events.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import struct

RENAMES = {"idle": "wait", "faint": "down", "move_phys": "tackle", "move_spec": "kime"}
REFERENCE_NATIVE = {
    "wait",
    "run",
    "damage",
    "down",
    "tackle",
    "punch",
    "kime",
    "kime_a",
    "mamoru",
    "kime_phy",
    "tx_wink",
    "tx_sleep",
    "tx_wakeup",
}


def adapt(source):
    def read(offset, size):
        if offset < 0 or offset + size > len(source):
            raise ValueError("SDR reference outside file")
        return source[offset : offset + size]

    def u32(offset):
        return struct.unpack(">I", read(offset, 4))[0]

    def u16(offset):
        return struct.unpack(">H", read(offset, 2))[0]

    if read(0, 4) != b"\x01\x00\x00\x04" or u16(24) != 1:
        raise ValueError("Expected experimental single-object SDR version 4")
    obj = u32(u32(8))
    count, table = u16(obj + 8), u32(obj + 12)
    if count != 9:
        raise ValueError("Expected nine prototype actions")
    result = bytearray(source)
    before_names, changed = [], []
    for index in range(count):
        row = table + 48 * index
        read(row, 48)
        pointer = u32(row)
        name = read(pointer, 64).split(b"\0", 1)[0].decode("ascii")
        length = struct.unpack(">f", read(row + 12, 4))[0]
        if not math.isfinite(length) or length <= 0:
            raise ValueError("Missing animation duration")
        before_names.append(name)
        if name in RENAMES:
            result.extend(bytes((-len(result)) % 4))
            new_pointer = len(result)
            result.extend(RENAMES[name].encode("ascii") + b"\0")
            struct.pack_into(">I", result, row, new_pointer)
            changed.append(row)
    if set(RENAMES) - set(before_names) or len(set(before_names)) != count:
        raise ValueError("Unexpected or duplicate prototype names")
    # Exact preservation beyond the four intentional pointer changes.
    check = bytearray(result[: len(source)])
    for row in changed:
        check[row : row + 4] = source[row : row + 4]
    assert bytes(check) == source
    after_names = [RENAMES.get(name, name) for name in before_names]
    return bytes(result), dict(
        before_sha256=hashlib.sha256(source).hexdigest(),
        after_sha256=hashlib.sha256(result).hexdigest(),
        actions=after_names,
        renamed=RENAMES,
        curve_indices_preserved=True,
        missing_native_actions=sorted(REFERENCE_NATIVE - set(after_names)),
        event_binding_verified=False,
        playable=False,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument("--report", required=True, type=Path)
    args = parser.parse_args()
    if args.source.resolve() == args.destination.resolve():
        raise ValueError("Preserve the original prototype SDR")
    data, report = adapt(args.source.read_bytes())
    args.destination.write_bytes(data)
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
