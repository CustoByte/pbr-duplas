"""Build Snivy's native face/body atlases from locally rendered portraits."""

import math
import struct
from PIL import Image, ImageOps


def rgb5a3(r, g, b, a):
    if a >= 224:
        return 0x8000 | ((r * 31 + 127) // 255) << 10 | ((g * 31 + 127) // 255) << 5 | ((b * 31 + 127) // 255)
    return ((a * 7 + 127) // 255) << 12 | ((r * 15 + 127) // 255) << 8 | ((g * 15 + 127) // 255) << 4 | ((b * 15 + 127) // 255)


def decode_color(value):
    if value & 0x8000:
        return tuple(((value >> shift) & 31) * 255 // 31 for shift in (10, 5, 0)) + (255,)
    return tuple(((value >> shift) & 15) * 17 for shift in (8, 4, 0)) + (((value >> 12) & 7) * 255 // 7,)


def encode_gtx(image):
    image = image.convert("RGBA")
    width, height = image.size
    if (width, height) not in ((96, 96), (54, 108)):
        raise ValueError("Unexpected native face/body atlas dimensions")
    indexed = image.quantize(colors=256, method=Image.Quantize.FASTOCTREE,
                             dither=Image.Dither.NONE)
    palette = indexed.getpalette("RGBA")
    colors = [tuple(palette[i:i + 4]) for i in range(0, len(palette), 4)]
    colors.extend([(0, 0, 0, 0)] * (256 - len(colors)))
    transparent = next((i for i, rgba in enumerate(colors) if rgba[3] == 0), None)
    if transparent is None:
        raise ValueError("Expected transparent atlas background")
    pixels = indexed.load()
    raw = bytearray()
    for by in range(0, height, 4):
        for bx in range(0, width, 8):
            for y in range(by, by + 4):
                for x in range(bx, bx + 8):
                    raw.append(pixels[x, y] if x < width and y < height else transparent)
    header = bytearray(128)
    struct.pack_into(">HHIII", header, 0, width, height, 0x08010000, 1, 3)
    struct.pack_into(">I", header, 0x28, 128)
    struct.pack_into(">I", header, 0x48, 128 + len(raw))
    return bytes(header + raw + b"".join(struct.pack(">H", rgb5a3(*c)) for c in colors))


def decode_gtx(data):
    width, height = struct.unpack_from(">HH", data)
    if struct.unpack_from(">II", data, 8) != (1, 3):
        raise ValueError("Expected native C8 / RGB5A3 texture")
    start, palette_at = (struct.unpack_from(">I", data, offset)[0] for offset in (0x28, 0x48))
    length = ((width + 7) // 8) * ((height + 3) // 4) * 32
    if start != 128 or palette_at != start + length or len(data) != palette_at + 512:
        raise ValueError("Invalid native atlas lengths")
    palette = [decode_color(struct.unpack_from(">H", data, palette_at + i * 2)[0]) for i in range(256)]
    image = Image.new("RGBA", (width, height))
    pixels, at = image.load(), start
    for by in range(0, height, 4):
        for bx in range(0, width, 8):
            for y in range(by, by + 4):
                for x in range(bx, bx + 8):
                    color = palette[data[at]]
                    at += 1
                    if x < width and y < height:
                        pixels[x, y] = color
    return image


def face_tile(portrait):
    # Recreate the frame procedurally: no old Pokémon pixels are copied.
    size = 384
    face = portrait.convert("RGBA").resize((size, size), Image.Resampling.LANCZOS)
    base = Image.new("RGBA", (size, size))
    mask = Image.new("L", (size, size))
    bp, mp = base.load(), mask.load()
    for y in range(size):
        for x in range(size):
            distance = math.hypot(x + 0.5 - size / 2, y + 0.5 - size / 2)
            if distance < size * 0.485:
                shade = round(255 - 32 * y / size)
                bp[x, y] = (shade, shade, shade, 255)
            if distance < size * 0.435:
                bp[x, y] = (0, 0, 0, 255)
                mp[x, y] = 255
    face.putalpha(Image.frombytes("L", (size, size), bytes(
        min(a, b) for a, b in zip(face.getchannel("A").tobytes(), mask.tobytes()))))
    base = Image.alpha_composite(base, face)
    tile = base.resize((48, 48), Image.Resampling.LANCZOS)
    tile.putalpha(tile.getchannel("A").point(lambda a: 0 if a < 64 else 255 if a > 192 else a))
    return tile


def atlases(directory):
    faces = Image.new("RGBA", (96, 96))
    bodies = Image.new("RGBA", (54, 108))
    for row, variant in enumerate(("normal", "shiny")):
        tile = face_tile(Image.open(directory / f"face-{variant}.png"))
        faces.paste(tile, (0, row * 48))
        faces.paste(ImageOps.mirror(tile), (48, row * 48))
        body = Image.open(directory / f"body-{variant}.png").convert("RGBA")
        body.thumbnail((54, 54), Image.Resampling.LANCZOS)
        bodies.paste(body, ((54 - body.width) // 2, row * 54 + (54 - body.height) // 2))
    return faces, bodies
