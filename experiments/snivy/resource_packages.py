"""Private FSYS outputs using only local game inputs and converted resources."""

import struct

from prepare_campaign_doubles import read_archive, word
from lzss_encode import encode
from encounter_expansion import rebuild_archive
from model_registry import NORMAL_ID, SHINY_ID
from pkx_reference import inspect_package


def append_resource(archive, identity, payload, name):
    before = read_archive(archive)
    if identity in {key for key, _ in before}:
        raise ValueError("Resource ID is already registered")
    if not name.isascii() or any(c in name for c in ("\0", "/", "\\")):
        raise ValueError("Invalid resource name")
    if archive[-32:] != bytes(28) + b"FSYS":
        raise ValueError("Unexpected FSYS footer")
    metadata = word(archive, 24)
    table = word(archive, metadata)
    headers = [word(archive, table + i * 4) for i in range(len(before))]
    first = min(word(archive, header + 4) for header in headers)
    if word(archive, 28) != first or word(archive, metadata + 8) != first:
        raise ValueError("Unsupported FSYS metadata/data split")
    # The native loader reads metadata up to first-data offset. Keep ALL new
    # headers, names and pointer tables inside that prefix, not after payloads.
    output = bytearray(archive[:first])
    name_at = len(output)
    output.extend(name.encode() + b"\0")
    output.extend(bytes((-len(output)) % 16))
    new_header = len(output)
    record = bytearray(archive[headers[0]:headers[0] + 112])
    if len(record) != 112:
        raise ValueError("Truncated native resource header")
    for offset, value in ((0, identity), (8, len(payload)), (0x10, 0),
                          (0x18, 0), (0x1C, 0), (0x24, name_at)):
        struct.pack_into(">I", record, offset, value)
    # +0x20 is the native file-handler type (GTX=6), not name length.
    # Preserve the audited texture handler from the original record.
    output.extend(record)
    output.extend(bytes((-len(output)) % 16))
    new_table = len(output)
    output.extend(struct.pack(">" + "I" * (len(headers) + 1), *headers, new_header))
    output.extend(bytes((-len(output)) % 32))
    new_first = len(output)
    struct.pack_into(">I", output, metadata, new_table)
    struct.pack_into(">I", output, metadata + 8, new_first)
    struct.pack_into(">I", output, 28, new_first)
    struct.pack_into(">I", output, 12, len(before) + 1)
    for header in headers:
        output.extend(bytes((-len(output)) % 32))
        at = len(output)
        old_at, size = word(archive, header + 4), word(archive, header + 0x14)
        output.extend(archive[old_at:old_at + size])
        struct.pack_into(">I", output, header + 4, at)
    output.extend(bytes((-len(output)) % 32))
    at = len(output)
    packed = encode(payload)
    output.extend(packed)
    struct.pack_into(">I", output, new_header + 4, at)
    struct.pack_into(">I", output, new_header + 0x14, len(packed))
    output.extend(bytes((-len(output)) % 32))
    output.extend(bytes(28) + b"FSYS")
    struct.pack_into(">I", output, 32, len(output))
    assert read_archive(output) == before + [(identity, payload)]
    return bytes(output)


def model_package(reference, normal, shiny):
    inspect_package(reference)  # Exact supplied native package/version gate.
    originals = read_archive(reference)
    output = bytearray(rebuild_archive(reference, {
        originals[0][0]: normal, originals[1][0]: shiny,
    }))
    table = word(output, word(output, 24))
    for index, identity in enumerate((NORMAL_ID, SHINY_ID)):
        struct.pack_into(">I", output, word(output, table + 4 * index), identity)
    assert read_archive(output) == [(NORMAL_ID, normal), (SHINY_ID, shiny)]
    return bytes(output)
