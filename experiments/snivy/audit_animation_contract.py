"""Inspect actual USA capture animation tables and shared Poké Ball script names.

Read-only. Names establish a native reference contract, not battle-event bindings
for the experimental Snivy. No PAL addresses are used or game files modified.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import struct

from prepare_campaign_doubles import read_archive


class Memory:
    def __init__(self, capture):
        self.regions = [
            (base, (capture / name).read_bytes())
            for base, name in ((0x80000000, "mem1.bin"), (0x90000000, "mem2.bin"))
        ]

    def read(self, address, size):
        for base, data in self.regions:
            if base <= address and address + size <= base + len(data):
                return data[address - base : address - base + size]
        raise ValueError(f"Unmapped reference: {address:08x}")

    def string(self, address):
        data = self.read(address, 64)
        end = data.find(b"\0")
        if end < 1:
            raise ValueError("Invalid native name")
        return data[:end].decode("ascii")

    def references(self, value):
        needle = struct.pack(">I", value)
        for base, data in self.regions:
            start = 0
            while (start := data.find(needle, start)) >= 0:
                if not start % 4:
                    yield base + start
                start += 1

    def object(self, name):
        candidates = []
        for base, data in self.regions:
            start = 0
            needle = name.encode() + b"\0"
            while (start := data.find(needle, start)) >= 0:
                for address in self.references(base + start):
                    try:
                        header = self.read(address, 28)
                        nodes, count = struct.unpack_from(">HH", header, 6)
                        table, root = struct.unpack_from(">II", header, 12)
                        if not (1 <= nodes <= 1024 and 1 <= count <= 100):
                            continue
                        self.read(root, 48)
                        actions = []
                        for index in range(count):
                            row = self.read(table + index * 48, 48)
                            action_name = self.string(struct.unpack_from(">I", row)[0])
                            length = struct.unpack_from(">f", row, 12)[0]
                            if not math.isfinite(length) or length <= 0:
                                raise ValueError("Invalid native animation duration")
                            if not re.fullmatch(r"[a-zA-Z0-9_]+", action_name):
                                raise ValueError("Invalid animation name")
                            actions.append(
                                dict(
                                    index=index,
                                    name=action_name,
                                    seconds=length,
                                    flags=row[40:44].hex(),
                                )
                            )
                        candidates.append(
                            dict(
                                name=name,
                                object_address=f"{address:08x}",
                                nodes=nodes,
                                actions=actions,
                            )
                        )
                    except (ValueError, UnicodeDecodeError, struct.error):
                        pass
                start += 1
        if len(candidates) != 1:
            raise ValueError(
                f"Expected one native object for {name}, got {len(candidates)}"
            )
        return candidates[0]


def audit(capture, fight_common, current_report):
    memory = Memory(capture)
    references = [
        memory.object(name) for name in ("moukazaru", "hikozaru", "hayashigame")
    ]
    native = sorted({a["name"] for obj in references for a in obj["actions"]})
    current = sorted(current_report["conversion"]["candidate_mapping"])
    data = fight_common.read_bytes()
    script = dict(read_archive(data))[0x024D1200]
    names = sorted(
        {
            match.group()[:-1].decode("ascii")
            for match in re.finditer(rb"[a-zA-Z_][a-zA-Z0-9_]{3,}\x00", script)
            if b"ball" in match.group().lower()
        }
    )
    return dict(
        kind="Native USA captured model tables and shared script inventory; no Snivy integration",
        capture_hashes={
            name: hashlib.sha256((capture / name).read_bytes()).hexdigest()
            for name in ("mem1.bin", "mem2.bin")
        },
        reference_models=references,
        native_names=native,
        prototype_names=current,
        missing_native_names=sorted(set(native) - set(current)),
        fight_common_sha256=hashlib.sha256(data).hexdigest(),
        shared_ball_script_resource="024d1200",
        shared_ball_script_names=names,
        ball_event_execution_verified=False,
        snivy_native_binding_verified=False,
        required_runtime_tests=[
            "continuous idle through command selection",
            "physical/special/status/Protect dispatch and return to idle",
            "damage, faint and forced replacement",
            "send-out, recall, switching and Poké Ball effects",
            "sleep/wakeup/blink with independent material channels",
            "simultaneous double battle actors and event completion",
        ],
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--capture", type=Path, required=True)
    parser.add_argument("--fight-common", type=Path, required=True)
    parser.add_argument("--current-report", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    report = audit(
        args.capture, args.fight_common, json.loads(args.current_report.read_text())
    )
    args.report.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {
                key: report[key]
                for key in (
                    "native_names",
                    "missing_native_names",
                    "shared_ball_script_names",
                )
            },
            indent=2,
        )
    )
