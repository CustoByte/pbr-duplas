"""Compose verified Snivy code stages; no files installed, no updater changes."""

import base64
import struct
from pathlib import Path

from names import patch_dol as name_dol
from species_guards import patch_dol as guards_dol, BASE as SECTION_BASE, SITES
from prepare_campaign_doubles import file_offset, word, sha
from team_series_asm import branch, d

PAYLOAD_BASE, RESERVED_END = 0x80648000, 0x8064C000
AI_CODE, AI_ROW, AI_HOOK = 0x80646500, 0x80646600, 0x8039D068
CAMERA_ROW, CAMERA_POSITION, CAMERA_SCALE = 0x80646640, 0x80646680, 0x806466E0
VOICE_ROW, VOICE_CODE = 0x80646660, 0x80646780


def row_bridge(code_address, hook, row_address, voice=False):
    # Legacy calls execute the original first instruction and resume normally.
    # The new species gets a blank prediction row, like native unknown/default
    # entries, instead of reading past the original 499-row prediction table.
    words = [d(37, 1, 1, -0x20), d(36, 0, 1, 8), d(11, 0, 4, 501), 0]
    if voice:
        words.append(d(32, 0, 13, -0x696C))
    else:
        words.extend((d(15, 0, 0, 0x8062), d(24, 0, 0, 0x51E8)))
    words.append(0x7C030040)
    second_branch = len(words)
    words.extend((0, d(15, 3, 0, row_address >> 16), d(24, 3, 3, row_address & 65535),
                  d(32, 0, 1, 8), d(14, 1, 1, 0x20), d(11, 0, 4, 0), 0x4E800020))
    legacy = code_address + len(words) * 4
    for index in (3, second_branch):
        words[index] = 0x40820000 | ((legacy - (code_address + index * 4)) & 0xFFFC)
    words.extend((d(32, 0, 1, 8), d(14, 1, 1, 0x20), 0x80630000,
                  branch(legacy + 12, hook + 4)))
    return b"".join(struct.pack(">I", w) for w in words)


def build(dol, payload):
    body = base64.b64decode(payload["payload_base64"], validate=True)
    if payload["address"] != PAYLOAD_BASE or sha(body) != payload["payload_sha256"]:
        raise ValueError("Invalid delivery payload address/digest")
    if payload["source_sha256"] != sha(Path(__file__).with_name("pass_delivery.c").read_bytes()):
        raise ValueError("Delivery payload does not match current source")
    if PAYLOAD_BASE + len(body) > RESERVED_END:
        raise ValueError("Delivery code exceeds reservation")
    for symbol in ("snivy_accessor", "snivy_carry"):
        if not PAYLOAD_BASE <= payload["symbols"][symbol] < PAYLOAD_BASE + len(body):
            raise ValueError("Delivery symbol is outside payload")
    named = name_dol(dol, 21775)
    guarded, _ = guards_dol(named)
    output = bytearray(guarded)
    offset, size = word(output, 24), word(output, 0xA8)
    if offset + size != len(output):
        raise ValueError("Guard section is not the last file section")
    new_size = RESERVED_END - SECTION_BASE
    output.extend(bytes(new_size - size))
    struct.pack_into(">I", output, 0xA8, new_size)
    output[offset + PAYLOAD_BASE - SECTION_BASE:offset + PAYLOAD_BASE - SECTION_BASE + len(body)] = body
    # Early species checks also cover voice/narrator banks with fixed original
    # resources. Do not admit 501 into those banks merely because it is a valid
    # model species. Only the audited menu presence checks are activated here.
    for site in SITES:
        if site < 0x80030000:
            at = file_offset(dol, site)
            output[at:at + 4] = dol[at:at + 4]
    bridge = row_bridge(AI_CODE, AI_HOOK, AI_ROW)
    output[offset + AI_CODE - SECTION_BASE:offset + AI_CODE - SECTION_BASE + len(bridge)] = bridge
    row = bytearray(44)
    row[42] = 1
    output[offset + AI_ROW - SECTION_BASE:offset + AI_ROW - SECTION_BASE + 44] = row
    if word(dol, file_offset(dol, AI_HOOK)) != 0x80630000:
        raise ValueError("Unexpected original AI prediction getter")
    struct.pack_into(">I", output, file_offset(dol, AI_HOOK), branch(AI_HOOK, AI_CODE))
    # Snivy has no supplied cry/narrator recording. Silence is deliberate:
    # preserve the original sound banks, never index a missing bank or borrow
    # another Pokémon's identity. Other move/impact sounds remain native.
    for n, (site, failure) in enumerate(((0x80026F40, 0x80026F74),
                                        (0x80026FCC, 0x80026FEC),
                                        (0x80027098, 0x800270B8))):
        address = 0x80646700 + n * 20
        original = word(dol, file_offset(dol, site))
        words = ((original & 0xFFFF0000) | 501, 0x40820008,
                 branch(address + 8, failure), original, branch(address + 16, site + 4))
        code = b"".join(struct.pack(">I", w) for w in words)
        output[offset + address - SECTION_BASE:offset + address - SECTION_BASE + len(code)] = code
        struct.pack_into(">I", output, file_offset(dol, site), branch(site, address))
    voice = row_bridge(VOICE_CODE, 0x803987E4, VOICE_ROW, voice=True)
    output[offset + VOICE_CODE - SECTION_BASE:offset + VOICE_CODE - SECTION_BASE + len(voice)] = voice
    if word(dol, file_offset(dol, 0x803987E4)) != 0x80630000:
        raise ValueError("Unexpected native narrator table getter")
    struct.pack_into(">I", output, file_offset(dol, 0x803987E4), branch(0x803987E4, VOICE_CODE))
    # The original summary camera has a fixed 495-entry array and clamps new
    # species to Egg. Give 501 its own small-biped camera entry instead, keeping
    # every original array byte and every legacy lookup unchanged.
    camera_row = struct.pack(">4f", -5.5, -3.0, 0.0, 0.54)
    output[offset + CAMERA_ROW - SECTION_BASE:offset + CAMERA_ROW - SECTION_BASE + 16] = camera_row
    position = [d(11, 0, 0, 501), 0x40820028,
                d(15, 3, 0, 0x8064), d(24, 3, 3, 0x6640),
                d(48, 0, 3, 0), d(52, 0, 4, 0), d(48, 0, 3, 4), d(52, 0, 4, 4),
                d(48, 0, 3, 8), d(52, 0, 4, 8), 0x4E800020,
                d(10, 0, 0, 495), branch(CAMERA_POSITION + 12 * 4, 0x80104DB0)]
    scale = [d(11, 0, 0, 501), 0x40820010,
             d(15, 3, 0, 0x8064), d(24, 3, 3, 0x6640),
             branch(CAMERA_SCALE + 4 * 4, 0x80104EC0),
             d(10, 0, 0, 495), branch(CAMERA_SCALE + 6 * 4, 0x80104EA8)]
    for hook, address, words in ((0x80104DAC, CAMERA_POSITION, position), (0x80104EA4, CAMERA_SCALE, scale)):
        if word(dol, file_offset(dol, hook)) != d(10, 0, 0, 495):
            raise ValueError("Unexpected original summary camera clamp")
        body_code = b"".join(struct.pack(">I", w) for w in words)
        output[offset + address - SECTION_BASE:offset + address - SECTION_BASE + len(body_code)] = body_code
        struct.pack_into(">I", output, file_offset(dol, hook), branch(hook, address))
    for hook in (0x800E85B4, 0x800E85D0, 0x800E8908):
        if word(dol, file_offset(dol, hook)) != branch(hook, 0x8063C000):
            raise ValueError("Existing Monferno accessor hook differs")
        struct.pack_into(">I", output, file_offset(dol, hook), branch(hook, payload["symbols"]["snivy_accessor"]))
    if word(dol, file_offset(dol, 0x80155AE4)) != branch(0x80155AE4, 0x8063C300, True):
        raise ValueError("Existing between-battles item hook differs")
    struct.pack_into(">I", output, file_offset(dol, 0x80155AE4), branch(0x80155AE4, payload["symbols"]["snivy_carry"], True))
    # 8064c000 = lis 8065 + signed addi c000. Retain the original clamp body.
    struct.pack_into(">I", output, file_offset(dol, 0x8063C700), d(15, 4, 0, 0x8065))
    struct.pack_into(">I", output, file_offset(dol, 0x8063C704), d(14, 4, 4, -0x4000))
    return bytes(output)
