"""Local RGB5A3 palette variant; all non-texture SDR bytes remain unchanged."""

import colorsys
import struct

from pkx_reference import scene_inventory


def prepare(data):
    scene = scene_inventory(data)
    output = bytearray(data)
    changed, ranges = 0, []
    for texture in scene["textures"]:
        if texture["encoding"] != 0x90:
            raise ValueError("Expected audited RGB5A3 Snivy textures")
        start, size = texture["data_offset"], texture["data_size"]
        ranges.append((start, start + size))
        for at in range(start, start + size, 2):
            word = struct.unpack_from(">H", data, at)[0]
            opaque = bool(word & 0x8000)
            shifts, maximum = ((10, 5, 0), 31) if opaque else ((8, 4, 0), 15)
            rgb = tuple(((word >> shift) & maximum) / maximum for shift in shifts)
            h, s, v = colorsys.rgb_to_hsv(*rgb)
            if not (0.16 <= h <= 0.50 and s > 0.15):
                continue
            rgb = colorsys.hsv_to_rgb(h + 0.07, s, v)
            value = word & (0x8000 if opaque else 0xF000)
            for channel, shift in zip(rgb, shifts):
                value |= round(channel * maximum) << shift
            if value != word:
                struct.pack_into(">H", output, at, value)
                changed += 1
    if not changed:
        raise ValueError("No eligible green pixels found")
    cursor = 0
    for start, end in sorted(ranges):
        assert output[cursor:start] == data[cursor:start]
        cursor = end
    assert output[cursor:] == data[cursor:]
    target_scene = scene_inventory(output)
    assert {k: v for k, v in target_scene.items() if k != "sha256"} == {
        k: v for k, v in scene.items() if k != "sha256"}
    return bytes(output), dict(changed_texture_pixels=changed, alpha_bits_preserved=True,
                               geometry_actions_and_metadata_preserved=True,
                               color_policy="green hue +0.07; other hues preserved",
                               visually_matched_to_official_art=False)
