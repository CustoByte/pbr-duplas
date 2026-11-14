import io
import struct
from types import SimpleNamespace
import unittest
from sdr_track_storage import writer


class TrackStorageTests(unittest.TestCase):
    def test_identical_arrays_shared_but_headers_independent(self):
        file = SimpleNamespace(file=io.BytesIO())
        write = writer(30)
        keys = [(0, 1.25), (1, -0.0), (2, 3.5)]
        end = write(file, 0, keys, 1)
        end2 = write(file, end, keys, 1)
        data = file.file.getvalue()
        self.assertEqual(end2, end + 32)
        for offset in (0, 16):
            self.assertEqual(struct.unpack_from('>I', data, offset), struct.unpack_from('>I', data, end + offset))
        first_values = struct.unpack_from('>I', data, 0)[0]
        self.assertEqual(data[first_values:first_values + 12], b''.join(struct.pack('>f', 0.0 if v == 0 else v) for _, v in keys))
        time_data = struct.unpack_from('>I', data, 16)[0]
        self.assertEqual(data[time_data:time_data + 36], b''.join(struct.pack('>HHIf', 0, i, 0, t / 30) for i, (t, _) in enumerate(keys)))
        file.file.seek(end + 24)
        file.file.write(bytes(4))
        self.assertNotEqual(file.file.getvalue()[24:28], file.file.getvalue()[end + 24:end + 28])

    def test_rounding_and_repeated_samples_keep_source_rate(self):
        file = SimpleNamespace(file=io.BytesIO())
        keys = [(0, 1.00000001), (1, 1.00000002), (2, 1.25)]
        writer(30)(file, 0, keys, 1)
        data = file.file.getvalue()
        self.assertEqual(struct.unpack_from('>H', data, 8)[0], 2)
        time_at = struct.unpack_from('>I', data, 16)[0]
        self.assertAlmostEqual(struct.unpack_from('>f', data, time_at + 20)[0], 2 / 30)


if __name__ == '__main__':
    unittest.main()
