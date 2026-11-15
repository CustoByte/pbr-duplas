import struct
import unittest

from names import append_name, name_thunk, patch_dol
from sunny_park import stats_row
from translation.messages import encoded, read_messages, write_messages


class NameRegistrationTests(unittest.TestCase):
    def sources(self):
        # Three GLOBAL IDs, but only two rows in the common MESG resource.
        mapping = struct.pack(">II6H", 4, 3, 1, 1, 2, 5, 1, 2)
        header = b"MESG" + struct.pack(">I", 2) + bytes(8)
        rows = [encoded("{F001}{F101}A"), encoded("{F001}{F101}B")]
        return mapping, write_messages(header, rows)

    def test_appends_global_id_and_local_index_separately(self):
        mapping, messages = self.sources()
        new_map, new_messages, global_id = append_name(mapping, messages)
        self.assertEqual(global_id, 4)
        self.assertEqual(struct.unpack_from(">HH", new_map, len(new_map) - 4), (1, 3))
        self.assertEqual(new_map[8:-4], mapping[8:])
        self.assertEqual(read_messages(new_messages)[1][:-1], read_messages(messages)[1])
        self.assertEqual(read_messages(new_messages)[1][-1], encoded("{F001}{F101}SNIVY"))
        self.assertEqual(struct.unpack_from(">HH", stats_row(global_id), 24), (4, 4))

    def test_rejects_duplicate_and_corrupted_map(self):
        mapping, messages = self.sources()
        new_map, new_messages, _ = append_name(mapping, messages)
        with self.assertRaises(ValueError):
            append_name(new_map, new_messages)
        for data in (mapping[:4], mapping[:-1], struct.pack(">II", 8, 3) + mapping[8:]):
            with self.assertRaises(ValueError):
                append_name(data, messages)

    def test_rejects_truncating_ids_and_unrecognized_executable(self):
        for value in (0, -1, 32768, 65536):
            with self.assertRaises(ValueError):
                name_thunk(value)
        for value in (0, -1, 65536):
            with self.assertRaises(ValueError):
                stats_row(value)
        with self.assertRaises(ValueError):
            patch_dol(bytes(512), 4)


if __name__ == "__main__":
    unittest.main()
