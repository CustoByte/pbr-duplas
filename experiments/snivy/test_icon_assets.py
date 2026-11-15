import struct
import unittest
from PIL import Image

from icon_textures import encode_gtx, decode_gtx, face_tile
from icon_registry import extend_table
from resource_packages import append_resource
from prepare_campaign_doubles import read_archive, word


class IconAssetTests(unittest.TestCase):
    def test_c8_tiling_palette_and_non_block_aligned_body_width(self):
        for size in ((96, 96), (54, 108)):
            image = Image.new("RGBA", size)
            for y in range(size[1]):
                for x in range(size[0]):
                    if x % 5:
                        image.putpixel((x, y), ((248, 0, 0, 255) if y % 2 else (0, 248, 0, 255)))
            data = encode_gtx(image)
            decoded = decode_gtx(data)
            self.assertEqual(decoded.size, size)
            for xy in ((0, 0), (1, 0), (1, 1), (size[0] - 1, size[1] - 1)):
                expected, actual = image.getpixel(xy), decoded.getpixel(xy)
                self.assertLessEqual(max(abs(a - b) for a, b in zip(expected, actual)), 8)
            self.assertEqual(len(data), 9856 if size == (96, 96) else 6688)

    def test_face_has_transparent_corners_and_visible_white_frame(self):
        image = Image.new("RGBA", (384, 384), (16, 180, 80, 255))
        tile = face_tile(image)
        self.assertEqual(tile.getpixel((0, 0))[3], 0)
        self.assertGreater(min(tile.getpixel((24, 1))[:3]), 200)
        self.assertEqual(tile.getpixel((24, 24))[:3], (16, 180, 80))

    def test_mapping_append_preserves_rows_and_padding(self):
        source = bytearray(48 + 2 * 8 + 12)
        for offset, value in ((0, 2), (4, 8), (16, 48), (20, 16), (24, len(source))):
            struct.pack_into(">I", source, offset, value)
        source[48:] = bytes(range(28))
        result = extend_table(bytes(source), 2, 8, [bytes(8)])
        self.assertEqual(result[48:64], source[48:64])
        self.assertEqual(result[72:], source[64:])
        with self.assertRaises(ValueError):
            extend_table(bytes(source), 2, 8, [bytes(7)])

    def archive(self):
        data = bytearray(0x160)
        data[:4] = b"FSYS"
        for offset, value in ((4, 0x251), (12, 2), (24, 0x40), (28, 0x160),
                              (0x40, 0x60), (0x44, 0x70), (0x48, 0x160),
                              (0x60, 0x80), (0x64, 0xF0)):
            struct.pack_into(">I", data, offset, value)
        for index, payload in enumerate((b"first local fixture", b"second local fixture")):
            header, at = 0x80 + 112 * index, len(data)
            data.extend(payload)
            data.extend(bytes((-len(data)) % 32))
            for offset, value in ((0, index + 1), (4, at), (8, len(payload)),
                                  (12, 0x80000000), (20, len(payload)), (0x20, 6)):
                struct.pack_into(">I", data, header + offset, value)
        data.extend(bytes(28) + b"FSYS")
        struct.pack_into(">I", data, 32, len(data))
        return bytes(data)

    def test_archive_append_preserves_payloads_and_keeps_metadata_before_data(self):
        original = self.archive()
        payload = b"new locally generated texture " * 100
        result = append_resource(original, 0x7BEA0C00, payload, "snivy-face.gtx")
        self.assertEqual(read_archive(result), read_archive(original) + [(0x7BEA0C00, payload)])
        table = word(result, word(result, 24))
        new_header = word(result, table + 8)
        self.assertEqual(word(result, new_header + 0x20), 6)
        self.assertLess(new_header + 112, word(result, 28))
        self.assertLess(table + 12, word(result, 28))
        with self.assertRaises(ValueError):
            append_resource(result, 0x7BEA0C00, payload, "snivy-face.gtx")


if __name__ == "__main__":
    unittest.main()
