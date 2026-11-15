"""Compile only mod-owned pass delivery code with the pinned PPC toolchain."""

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import subprocess

BASE, LIMIT = 0x80648000, 0x8064C000


def build(source, output, toolchain):
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = str(toolchain / "usr/lib/x86_64-linux-gnu")
    prefix = str(toolchain / "usr/bin/powerpc-linux-gnu-")
    def run(*args):
        return subprocess.check_output([str(x) for x in args], env=env, text=True)
    version = run(prefix + "gcc-14", "-dumpfullversion").strip()
    if version != "14.2.0":
        raise ValueError("Requires GCC 14.2.0")
    script = output / "delivery.ld"
    script.write_text(f"SECTIONS {{ . = {BASE}; .payload : {{ *(.text*) *(.rodata*) *(.data*) *(.bss*) }} /DISCARD/ : {{ *(.eh_frame*) *(.comment*) *(.note*) }} }}")
    obj, elf, binary = (output / name for name in ("delivery.o", "delivery.elf", "delivery.bin"))
    flags = ["-mcpu=750", "-m32", "-mbig-endian", "-msoft-float", "-mno-altivec", "-msdata=none", "-O2",
             "-ffreestanding", "-fno-builtin", "-fno-pic", "-fno-pie", "-fno-stack-protector",
             "-fno-asynchronous-unwind-tables", "-fno-unwind-tables", "-fno-tree-loop-distribute-patterns",
             "-Wall", "-Wextra", "-Werror"]
    run(prefix + "gcc-14", *flags, "-c", source, "-o", obj)
    run(prefix + "ld", "-m", "elf32ppc", "--build-id=none", "--no-undefined", "-T", script, "-o", elf, obj)
    run(prefix + "objcopy", "-O", "binary", "--only-section=.payload", elf, binary)
    data = binary.read_bytes()
    if BASE + len(data) > LIMIT:
        raise ValueError("Delivery code exceeds reservation")
    symbols = {}
    for line in run(prefix + "nm", "-n", elf).splitlines():
        parts = line.split()
        if len(parts) == 3 and parts[1] in ("T", "D", "B", "R", "t", "b", "r"):
            symbols[parts[2]] = int(parts[0], 16)
    report = dict(compiler=version, address=BASE, bytes=len(data), symbols=symbols,
                  source_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
                  payload_sha256=hashlib.sha256(data).hexdigest(),
                  payload_base64=base64.b64encode(data).decode())
    (output / "pass-payload.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    for name in ("source", "output", "toolchain"):
        p.add_argument("--" + name, type=Path, required=True)
    args = p.parse_args()
    result = build(args.source, args.output, args.toolchain)
    print(json.dumps({k: v for k, v in result.items() if k != "payload_base64"}, indent=2))
