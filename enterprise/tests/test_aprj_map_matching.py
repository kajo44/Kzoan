import math
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from aprj_map_matching import (
    MapMatchingEngine,
    _angle_diff,
    _point_at_distance,
    _project_to_segment,
    _safe_name,
    _viterbi_decode,
)


class MapMatchingGeometryTests(unittest.TestCase):
    def test_angle_difference_wraps_at_north(self):
        self.assertAlmostEqual(_angle_diff(359, 1), 2.0)
        self.assertAlmostEqual(_angle_diff(10, 350), 20.0)

    def test_projection_finds_nearby_point_on_line(self):
        distance, fraction, lon, lat, bearing = _project_to_segment(
            0.0005, 0.0001, (0.0, 0.0), (0.001, 0.0)
        )
        self.assertAlmostEqual(fraction, 0.5, places=3)
        self.assertAlmostEqual(lon, 0.0005, places=6)
        self.assertAlmostEqual(lat, 0.0, places=6)
        self.assertGreater(distance, 10.0)
        self.assertLess(distance, 12.0)
        self.assertAlmostEqual(bearing, 90.0, delta=0.1)

    def test_station_interpolation_uses_cumulative_distance(self):
        coords = [(0.0, 0.0), (0.001, 0.0), (0.002, 0.0)]
        lon, lat = _point_at_distance(coords, 111.2)
        self.assertAlmostEqual(lat, 0.0, places=7)
        self.assertAlmostEqual(lon, 0.001, delta=0.00002)

    def test_viterbi_decodes_complete_candidate_sequence(self):
        candidates = [
            [
                {"distance_m": 2, "heading_difference_deg": 0, "projected_latitude": 0, "projected_longitude": 0.0000, "road_id": "A"},
                {"distance_m": 5, "heading_difference_deg": 0, "projected_latitude": 0.001, "projected_longitude": 0.0000, "road_id": "B"},
            ],
            [
                {"distance_m": 1, "heading_difference_deg": 0, "projected_latitude": 0, "projected_longitude": 0.0010, "road_id": "A"},
                {"distance_m": 4, "heading_difference_deg": 0, "projected_latitude": 0.001, "projected_longitude": 0.0010, "road_id": "B"},
            ],
            [
                {"distance_m": 2, "heading_difference_deg": 0, "projected_latitude": 0, "projected_longitude": 0.0020, "road_id": "A"},
                {"distance_m": 5, "heading_difference_deg": 0, "projected_latitude": 0.001, "projected_longitude": 0.0020, "road_id": "B"},
            ],
        ]
        path, scores = _viterbi_decode(candidates, [(0, 0), (0, 0.001), (0, 0.002)])
        self.assertEqual(len(path), 3)
        self.assertTrue(all(index is not None for index in path))
        self.assertTrue(all(score is not None for score in scores))
        self.assertEqual([candidates[i][path[i]]["road_id"] for i in range(3)], ["A", "A", "A"])

    def test_safe_name_removes_path_separators(self):
        value = _safe_name(r"Road/Name: Segment*1")
        self.assertNotIn("/", value)
        self.assertNotIn(":", value)
        self.assertNotIn("*", value)

    def test_sta_kml_exports_station_point_and_attributes(self):
        engine = MapMatchingEngine.__new__(MapMatchingEngine)
        engine.last_results = [{
            "road_id": "R-1", "road_name": "Ruas Utama", "sta_m": 100, "sta_km": 0.1,
            "sta_latitude": -0.5, "sta_longitude": 101.2, "photo_name": "IMG_001.jpg",
            "photo_path": r"C:\foto\IMG_001.jpg", "distance_m": 4.2,
            "camera_heading_deg": 90, "heading_difference_deg": 5,
            "taken_at_text": "2026-01-01 10:00:00", "match_status": "Cocok - perlu verifikasi",
        }]
        with tempfile.TemporaryDirectory() as folder:
            output = Path(folder) / "stations.kml"
            count = engine.export_sta_kml(output)
            root = ET.parse(output).getroot()
            self.assertEqual(count, 1)
            coords = [node.text for node in root.iter() if node.tag.endswith("coordinates")]
            self.assertEqual(coords, ["101.20000000,-0.50000000,0"])
            names = [node.text for node in root.iter() if node.tag.endswith("name")]
            self.assertTrue(any("STA 100 m" in name for name in names))


if __name__ == "__main__":
    unittest.main()
