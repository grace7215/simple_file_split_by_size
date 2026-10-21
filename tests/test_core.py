import io
import os
import shutil
import tempfile
import unittest

from simple_file_split_by_size import Part, SplitResult, split_file_by_size


class TestRoundTrip(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def _concat(self, parts):
        out = bytearray()
        for p in parts:
            with open(p.path, "rb") as f:
                out.extend(f.read())
        return bytes(out)

    def test_split_exact_multiple(self):
        data = b"abcdefgh"  # 8 bytes
        path = os.path.join(self.dir, "in.bin")
        with open(path, "wb") as f:
            f.write(data)

        result = split_file_by_size(path, 4, os.path.join(self.dir, "out"))
        self.assertIsInstance(result, SplitResult)
        self.assertEqual(result.part_count, 2)
        self.assertEqual([p.index for p in result.parts], [0, 1])
        self.assertEqual([p.size for p in result.parts], [4, 4])
        self.assertEqual(self._concat(result.parts), data)

    def test_split_remainder(self):
        data = b"abcdefghij"  # 10 bytes
        path = os.path.join(self.dir, "in.bin")
        with open(path, "wb") as f:
            f.write(data)

        result = split_file_by_size(path, 4, os.path.join(self.dir, "out"))
        self.assertEqual(result.part_count, 3)
        self.assertEqual([p.size for p in result.parts], [4, 4, 2])
        self.assertEqual(self._concat(result.parts), data)

    def test_chunk_larger_than_file(self):
        data = b"hello"
        path = os.path.join(self.dir, "in.bin")
        with open(path, "wb") as f:
            f.write(data)

        result = split_file_by_size(path, 1024, os.path.join(self.dir, "out"))
        self.assertEqual(result.part_count, 1)
        self.assertEqual(result.parts[0].size, 5)
        self.assertEqual(self._concat(result.parts), data)

    def test_empty_file_yields_one_empty_part(self):
        path = os.path.join(self.dir, "empty.bin")
        with open(path, "wb"):
            pass

        result = split_file_by_size(path, 100, os.path.join(self.dir, "out"))
        self.assertEqual(result.part_count, 1)
        self.assertEqual(result.parts[0].size, 0)
        self.assertEqual(self._concat(result.parts), b"")

    def test_stream_source_not_closed(self):
        data = b"abcdefgh"
        stream = io.BytesIO(data)
        result = split_file_by_size(stream, 4, os.path.join(self.dir, "out"))
        self.assertEqual(result.part_count, 2)
        # Stream passed in must remain open and usable by the caller.
        self.assertFalse(stream.closed)
        stream.seek(0)
        self.assertEqual(stream.read(), data)

    def test_stream_source_is_consumed(self):
        data = b"0123456789"
        stream = io.BytesIO(data)
        result = split_file_by_size(stream, 3, os.path.join(self.dir, "out"))
        self.assertEqual([p.size for p in result.parts], [3, 3, 3, 1])
        self.assertEqual(self._concat(result.parts), data)

    def test_pathlike_source(self):
        data = b"abcdefgh"
        path = os.path.join(self.dir, "in.bin")
        with open(path, "wb") as f:
            f.write(data)
        # os.PathLike input (not str)
        result = split_file_by_size(path, 4, os.path.join(self.dir, "out"))
        self.assertEqual(result.part_count, 2)

    def test_filenames_zero_padded(self):
        data = bytes(range(30))
        path = os.path.join(self.dir, "in.bin")
        with open(path, "wb") as f:
            f.write(data)
        result = split_file_by_size(path, 4, os.path.join(self.dir, "p"))
        expected = [
            os.path.join(self.dir, "p.000"),
            os.path.join(self.dir, "p.001"),
            os.path.join(self.dir, "p.002"),
            os.path.join(self.dir, "p.003"),
            os.path.join(self.dir, "p.004"),
            os.path.join(self.dir, "p.005"),
            os.path.join(self.dir, "p.006"),
            os.path.join(self.dir, "p.007"),
        ]
        self.assertEqual([p.path for p in result.parts], expected)


class TestValidation(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def test_chunk_bytes_must_be_positive(self):
        path = os.path.join(self.dir, "in.bin")
        with open(path, "wb") as f:
            f.write(b"data")
        with self.assertRaises(ValueError):
            split_file_by_size(path, 0, os.path.join(self.dir, "out"))
        with self.assertRaises(ValueError):
            split_file_by_size(path, -1, os.path.join(self.dir, "out"))

    def test_chunk_bytes_must_be_int(self):
        path = os.path.join(self.dir, "in.bin")
        with open(path, "wb") as f:
            f.write(b"data")
        with self.assertRaises(TypeError):
            split_file_by_size(path, "4", os.path.join(self.dir, "out"))
        with self.assertRaises(TypeError):
            split_file_by_size(path, 4.0, os.path.join(self.dir, "out"))

    def test_bool_chunk_bytes_rejected(self):
        path = os.path.join(self.dir, "in.bin")
        with open(path, "wb") as f:
            f.write(b"data")
        # bool is a subclass of int but is not a meaningful chunk size.
        with self.assertRaises(TypeError):
            split_file_by_size(path, True, os.path.join(self.dir, "out"))


if __name__ == "__main__":
    unittest.main()
