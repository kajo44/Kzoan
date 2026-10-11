import json
import tempfile
import unittest
from pathlib import Path

import piexif
from PIL import Image

from aprj_geospasial import (
    GeospatialStore,
    _distance_m,
    _station_points,
    load_road_segments,
)


class GeospatialModuleTests(unittest.TestCase):
    def test_station_points_start_at_zero_and_increase_by_interval(self):
        coords = [(100.0, 0.0), (100.002, 0.0)]
        stations = list(_station_points(coords, 100))
        self.assertGreaterEqual(len(stations), 2)
        self.assertEqual(stations[0][0], 0)
        self.assertEqual(stations[1][0], 100)
        self.assertTrue(all(stations[i][0] < stations[i + 1][0] for i in range(len(stations) - 1)))

    def test_distance_same_point_is_zero(self):
        self.assertAlmostEqual(_distance_m(-0.5, 100.0, -0.5, 100.0), 0.0)

    def test_load_geojson_linestring(self):
        with tempfile.TemporaryDirectory() as temp:
            source = Path(temp) / "roads.geojson"
            source.write_text(json.dumps({
                "type": "FeatureCollection",
                "features": [{
                    "type": "Feature",
                    "properties": {"road_code": "R-01", "road_name": "Jalan Contoh"},
                    "geometry": {"type": "LineString", "coordinates": [[100.0, -0.5], [100.001, -0.5]]},
                }],
            }), encoding="utf-8")
            segments = load_road_segments(source)
            self.assertEqual(len(segments), 1)
            self.assertEqual(segments[0][0], "R-01")
            self.assertEqual(segments[0][1], "Jalan Contoh")
            self.assertEqual(len(segments[0][2]), 2)

    def test_store_persists_job_and_results_separately(self):
        with tempfile.TemporaryDirectory() as temp:
            store = GeospatialStore(Path(temp) / "geo.sqlite3")
            job_id = store.create_job("roads.kml", "photos", 100, 50)
            store.save_matches(job_id, [
                (job_id, "R-01", "Jalan Contoh", 0, -0.5, 100.0,
                 None, None, None, None, "Tidak ada kandidat dalam radius")
            ])
            rows = store.get_matches(job_id)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0][0], "R-01")
            self.assertIsNone(rows[0][5])

    def test_photo_index_uses_pillow_when_exiftool_missing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "photos"
            root.mkdir()
            photo = root / "gps.jpg"
            image = Image.new("RGB", (8, 8), "white")
            gps = {
                piexif.GPSIFD.GPSLatitudeRef: "S",
                piexif.GPSIFD.GPSLatitude: [(0, 1), (30, 1), (0, 1)],
                piexif.GPSIFD.GPSLongitudeRef: "E",
                piexif.GPSIFD.GPSLongitude: [(101, 1), (15, 1), (0, 1)],
            }
            image.save(photo, "JPEG", exif=piexif.dump({
                "0th": {}, "Exif": {}, "GPS": gps, "1st": {}, "thumbnail": None,
            }))
            engine = GeospatialEngine(Path(temp))
            self.assertIsNone(engine.exiftool_path())
            engine.index_photos(root, batch_size=1)
            self.assertEqual(engine.store.photo_count(), 1)
            with engine.store.connect() as conn:
                row = conn.execute(
                    "SELECT latitude, longitude FROM photo_index WHERE path = ?",
                    (str(photo.resolve()),),
                ).fetchone()
            self.assertAlmostEqual(row[0], -0.5, places=5)
            self.assertAlmostEqual(row[1], 101.25, places=5)


if __name__ == "__main__":
    unittest.main()
