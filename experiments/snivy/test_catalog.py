import struct
import unittest

from catalog import append_archive, entries, relocate


class CatalogTests(unittest.TestCase):
    def source(self):
        data = bytearray(128)
        data[:4] = b"GLLA"
        struct.pack_into(">I", data, 8, 2)
        struct.pack_into(">I", data, 16, 64)
        data[32:38] = b"a\0\0\0\0\0"
        data[40:46] = b"b\0\0\0\0\0"
        struct.pack_into(">4I", data, 64, 7, 32, 123, 8)
        struct.pack_into(">4I", data, 80, 9, 40, 456, 16)
        return bytes(data)

    def test_preserves_all_existing_records_and_unrelated_bytes(self):
        old = self.source()
        new = append_archive(old)
        start, rows = entries(new)
        self.assertEqual(rows[:-1], entries(old)[1])
        self.assertEqual(rows[-1][:2], (0x2000, "pkx_501"))
        self.assertEqual(new[start:start + 32], old[64:96])
        restored = bytearray(new[:len(old)])
        restored[8:12] = old[8:12]
        restored[16:20] = old[16:20]
        self.assertEqual(restored, old)

    def test_runtime_relocation_does_not_change_disk_bytes_or_size_cache(self):
        disk = append_archive(self.source())
        start, rows = entries(disk)
        runtime = relocate(disk, 0x81000000)
        for i, (_, _, name, cache, _) in enumerate(rows):
            self.assertEqual(struct.unpack_from(">3I", runtime, start + 16 * i + 4),
                             (0x81000000 + name, cache, 0))
        self.assertEqual(entries(disk)[1], rows)

    def test_rejects_collisions_and_duplicate_application(self):
        old = self.source()
        for identity, name in ((7, "c"), (11, "a"), (0, "x"),
                               (11, "../x"), (11, "x\0"), (11, "pkx_501.fsys")):
            with self.assertRaises(ValueError):
                append_archive(old, identity, name)
        with self.assertRaises(ValueError):
            append_archive(append_archive(old))

    def test_rejects_invalid_count_pointer_and_missing_terminator(self):
        old = self.source()
        malformed = [old[:20], b"BAD!" + old[4:]]
        for field, value in ((8, 1000), (16, 129), (68, 31), (68, 64)):
            data = bytearray(old)
            struct.pack_into(">I", data, field, value)
            malformed.append(bytes(data))
        data = bytearray(old)
        data[32:64] = b"X" * 32
        malformed.append(bytes(data))
        for data in malformed:
            with self.assertRaises(ValueError):
                entries(data)


if __name__ == "__main__":
    unittest.main()
