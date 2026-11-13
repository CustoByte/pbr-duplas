"""Append a resource registration without changing existing FSYS identities.

This edits the on-disk catalog only. It does not install a model or modify an
ISO. Runtime relocation is kept separate from the on-disk relative pointers.
"""

import struct

SNIVY_ARCHIVE_ID = 0x2000
SNIVY_ARCHIVE_NAME = "pkx_501.fsys"


def entries(data):
    if len(data) < 32 or data[:4] != b"GLLA":
        raise ValueError("Invalid FSYS catalog header")
    count = struct.unpack_from(">I", data, 8)[0]
    start = struct.unpack_from(">I", data, 16)[0]
    if start < 32 or count > (len(data) - start) // 16:
        raise ValueError("Catalog table is outside the file")
    result, ids, names = [], set(), set()
    for index in range(count):
        offset = start + index * 16
        identity, name_offset, cache, flags = struct.unpack_from(">4I", data, offset)
        if not 32 <= name_offset < start:
            raise ValueError("Catalog name pointer is outside the name area")
        end = data.find(b"\0", name_offset, start)
        if end < 0:
            raise ValueError("Unterminated catalog name")
        try:
            name = data[name_offset:end].decode("ascii")
        except UnicodeDecodeError as error:
            raise ValueError("Non-ASCII archive name") from error
        if not name or identity in ids or name in names:
            raise ValueError("Empty or duplicate catalog identity/name")
        ids.add(identity)
        names.add(name)
        result.append((identity, name, name_offset, cache, flags))
    return start, result


def append_archive(data, identity=SNIVY_ARCHIVE_ID, name=SNIVY_ARCHIVE_NAME):
    start, old = entries(data)
    if not 0 < identity <= 0xFFFFFFFF or any(r[0] == identity for r in old):
        raise ValueError("Archive ID is invalid or already registered")
    if (
        not name.endswith(".fsys") or not name.isascii()
        or any(c in name for c in ("/", "\\", "\0"))
        or any(r[1] == name for r in old)
    ):
        raise ValueError("Archive name is invalid or already registered")
    name_offset = len(data)
    output = bytearray(data + name.encode("ascii") + b"\0")
    output.extend(bytes((-len(output)) % 32))
    new_start = len(output)
    output.extend(data[start:start + len(old) * 16])
    output.extend(struct.pack(">4I", identity, name_offset, 0, 0))
    output.extend(bytes((-len(output)) % 32))
    struct.pack_into(">I", output, 8, len(old) + 1)
    struct.pack_into(">I", output, 16, new_start)
    _, registered = entries(output)
    if registered[:-1] != old:
        raise AssertionError("Existing archive registrations changed")
    return bytes(output)


def relocate(data, base):
    """Apply only the name relocation and flag reset used by native loadToc."""
    start, rows = entries(data)
    output = bytearray(data)
    for index, (_, _, name_offset, _, _) in enumerate(rows):
        struct.pack_into(">I", output, start + index * 16 + 4, base + name_offset)
        struct.pack_into(">I", output, start + index * 16 + 12, 0)
    return bytes(output)
