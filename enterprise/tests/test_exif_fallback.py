import tempfile
import unittest
from pathlib import Path

import piexif
from PIL import Image

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

    def test_reads_gps_from_real_exif_jpeg(self):
        with tempfile.TemporaryDirectory() as temp:
            photo = Path(temp) / "gps.jpg"
            image = Image.new("RGB", (8, 8), "white")
            gps = {
                piexif.GPSIFD.GPSLatitudeRef: "S",
                piexif.GPSIFD.GPSLatitude: [(0, 1), (30, 1), (0, 1)],
                piexif.GPSIFD.GPSLongitudeRef: "E",
                piexif.GPSIFD.GPSLongitude: [(101, 1), (15, 1), (0, 1)],
                piexif.GPSIFD.GPSImgDirectionRef: "T",
                piexif.GPSIFD.GPSImgDirection: (90, 1),
            }
            exif_bytes = piexif.dump({"0th": {}, "Exif": {}, "GPS": gps, "1st": {}, "thumbnail": None})
            image.save(photo, "JPEG", exif=exif_bytes)
            result = read_metadata_batch([photo])
            item = next(iter(result.values()))
            self.assertAlmostEqual(item["GPSLatitude"], -0.5, places=5)
            self.assertAlmostEqual(item["GPSLongitude"], 101.25, places=5)
            self.assertAlmostEqual(item["GPSImgDirection"], 90.0)


if __name__ == "__main__":
    unittest.main()
