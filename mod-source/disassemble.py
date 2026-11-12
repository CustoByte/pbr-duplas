"""Dump a verified-address range from the supplied DOL (development utility)."""
import argparse
import struct
from pathlib import Path
from capstone import Cs, CS_ARCH_PPC, CS_MODE_32, CS_MODE_BIG_ENDIAN


def sections(data):
    for count, fo, ao, so in [(7, 0, 0x48, 0x90), (11, 0x1c, 0x64, 0xac)]:
        for index in range(count):
            off, addr, size = (struct.unpack_from('>I', data, base + 4 * index)[0] for base in (fo, ao, so))
            if size:
                yield off, addr, size


def dump(data, start, end):
    for off, addr, size in sections(data):
        if addr <= start < end <= addr + size:
            begin = off + start - addr
            md = Cs(CS_ARCH_PPC, CS_MODE_32 | CS_MODE_BIG_ENDIAN)
            lines = []
            for relative in range(0, end - start, 4):
                raw = data[begin + relative:begin + relative + 4]
                decoded = list(md.disasm(raw, start + relative))
                if decoded:
                    i = decoded[0]
                    lines.append(f'{i.address:08x}: {i.mnemonic:8} {i.op_str}')
                else:
                    lines.append(f'{start + relative:08x}: .long    0x{raw.hex()}  # undecoded')
            return '\n'.join(lines)
    raise ValueError('Range outside one DOL section')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('dol', type=Path)
    p.add_argument('start', type=lambda x: int(x, 0))
    p.add_argument('end', type=lambda x: int(x, 0))
    p.add_argument('--output', type=Path)
    args = p.parse_args()
    text = dump(args.dol.read_bytes(), args.start, args.end)
    if args.output:
        args.output.write_text(text + '\n')
    else:
        print(text)
