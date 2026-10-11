import tempfile
import unittest
from pathlib import Path

from aprj_exif_fallback import _as_float, _dms_to_decimal, read_metadata_batch


class ExifFallbackTests(unittest.TestCase):
    def test_rational_pair_is_converted_safely(self):
        self.assertAlmostEqual(_as_float((3, 2)), 1.5)
        self.assertIsNone(_as_float((1, 0)))

    def test_dms_uses_south_and_west_signs(self):
        self.assertAlmostEqual(_dms_to_decimal((10, 30, 0), "S"), -10.5)
        self.assertAlmostEqual(_dms_to_decimal((100, 15, 0), "W"), -100.25)
        self.assertAlmostEqual(_dms_to_decimal((10, 0, 0), "N"), 10.0)

    def test_unreadable_photo_does_not_abort_batch(self):
        with tempfile.TemporaryDirectory() as temp:
            broken = Path(temp) / "broken.jpg"
            broken.write_text("not an image", encoding="utf-8")
            result = read_metadata_batch([broken])
            self.assertEqual(len(result), 1)
            item = next(iter(result.values()))
            self.assertEqual(item["FileName"], "broken.jpg")
            self.assertNotIn("GPSLatitude", item)


if __name__ == "__main__":
    unittest.main()
