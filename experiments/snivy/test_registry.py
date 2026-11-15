import struct
import unittest

from registry import append_stats, internal_id


class RegistryTests(unittest.TestCase):
    def table(self):
        data = bytearray((i % 251 for i in range(26112)))
        for offset, value in ((0, 501), (4, 52), (16, 48),
                              (20, 501 * 52), (24, len(data))):
            struct.pack_into('>I', data, offset, value)
        return bytes(data)

    def test_independent_identity_and_reserved_gap(self):
        self.assertEqual([internal_id(i) for i in range(1, 494)], list(range(1, 494)))
        self.assertEqual(internal_id(495), 501)
        for species in (0, 494, 496, 500, 501, 65535):
            with self.assertRaises(ValueError):
                internal_id(species)

    def test_append_preserves_every_original_row_and_padding(self):
        old = self.table()
        new = append_stats(old)
        end = 48 + 501 * 52
        self.assertEqual(new[48:end], old[48:end])
        self.assertEqual(new[end + 52:], old[end:])
        self.assertEqual(struct.unpack_from('>II', new, 20), (502 * 52, len(new)))
        self.assertEqual(new[end + 30:end + 38], bytes((45, 45, 55, 63, 45, 55, 12, 12)))
        self.assertEqual(new[end + 48], 65)

    def test_rejects_other_layouts_and_duplicate_application(self):
        old = self.table()
        for data in (old[:40], old[:-1], append_stats(old)):
            with self.assertRaises(ValueError):
                append_stats(data)


if __name__ == '__main__':
    unittest.main()
