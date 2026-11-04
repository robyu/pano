import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import mask


class DecodeTests(unittest.TestCase):
    def test_lsb_is_leftmost(self):
        grid = mask.decode([1 << 0] + [0] * 17)
        self.assertEqual(grid[0][0], 1)
        self.assertEqual(grid[0][1], 0)

    def test_last_column_is_bit_21(self):
        grid = mask.decode([1 << 21] + [0] * 17)
        self.assertEqual(grid[0][21], 1)
        self.assertEqual(grid[0][20], 0)

    def test_full_and_empty(self):
        self.assertEqual(mask.decode([mask.FULL_ROW] * 18), mask.full())
        self.assertEqual(mask.decode([0] * 18), mask.clear())

    def test_wrong_row_count(self):
        with self.assertRaises(mask.MaskError):
            mask.decode([0] * 17)

    def test_out_of_range(self):
        with self.assertRaises(mask.MaskError):
            mask.decode([mask.FULL_ROW + 1] + [0] * 17)
        with self.assertRaises(mask.MaskError):
            mask.decode([-1] + [0] * 17)


class EncodeTests(unittest.TestCase):
    def test_round_trip(self):
        values = [mask.FULL_ROW, 0, 1, 1 << 21] + [0] * 14
        self.assertEqual(mask.encode(mask.decode(values)), values)

    def test_encode_known_cam01_rows(self):
        values = [4194303, 4194303, 4194291, 4194291, 4194291, 4194289,
                  4194289, 4194288, 4194288, 4194288, 4194288, 4194288,
                  4194288, 4194288, 4194288, 4194288, 4194288, 4194288]
        self.assertEqual(mask.encode(mask.decode(values)), values)

    def test_invalid_shape(self):
        with self.assertRaises(mask.MaskError):
            mask.encode([[0] * 22] * 17)
        with self.assertRaises(mask.MaskError):
            mask.encode([[0] * 21] * 18)

    def test_invalid_cell(self):
        rows = mask.clear()
        rows[4][5] = 2
        with self.assertRaises(mask.MaskError):
            mask.encode(rows)


class HelperTests(unittest.TestCase):
    def test_revision_is_stable(self):
        rows = mask.decode([1, 2, 4] + [0] * 15)
        self.assertEqual(mask.revision(rows), mask.revision(rows))
        self.assertEqual(
            mask.revision(rows),
            mask.revision_from_regions(mask.encode(rows)),
        )

    def test_revision_changes(self):
        rows = mask.clear()
        before = mask.revision(rows)
        rows[0][0] = 1
        self.assertNotEqual(before, mask.revision(rows))

    def test_invert_clear_count(self):
        rows = mask.clear()
        self.assertEqual(mask.count(rows), 0)
        self.assertEqual(mask.count(mask.invert(rows)), 18 * 22)
        self.assertEqual(mask.ascii(rows).splitlines()[0], "." * 22)
        self.assertEqual(mask.ascii(mask.full()).splitlines()[0], "#" * 22)


if __name__ == "__main__":
    unittest.main()
