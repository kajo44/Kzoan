# -*- coding: utf-8 -*-
"""Map matching foto ber-GPS ke geometri ruas dan STA.

Semua jarak dihitung dalam meter pada proyeksi lokal untuk setiap segmen.
Hasil tetap merupakan kandidat dan harus diperiksa pada peta/foto sumber.
"""
from __future__ import annotations

import csv
import json
import math
import os
import re
import shutil
import subprocess
import zipfile
import xml.etree.ElementTree as ET
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from aprj_geospasial import load_road_segments, EARTH_RADIUS_M

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".tif", ".tiff", ".png", ".bmp", ".webp"}
GRID_DEG = 0.002


def _safe_name(value):
    value = re.sub(r'[<>:"/\\\\|?*\\x00-\\x1f]+', "_", str(value or "").strip())
    value = re.sub(r"\s+", " ", value).strip(" .")
    return (value or "Tanpa_Nama")[:100]


def _parse_time(value):
    if not value:
        return None
    text = str(value).strip()
    for fmt in ("%Y:%m:%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S%z",
                "%Y-%m-%dT%H:%M:%S", "%Y:%m:%d %H:%M:%S.%f"):
        try:
            return datetime.strptime(text, fmt).replace(tzinfo=None)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return None


def _distance_m(a_lat, a_lon, b_lat, b_lon):
    p1, p2 = math.radians(a_lat), math.radians(b_lat)
    dp, dl = math.radians(b_lat-a_lat), math.radians(b_lon-a_lon)
    q = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2 * EARTH_RADIUS_M * math.asin(min(1.0, math.sqrt(q)))


def _bearing(lat1, lon1, lat2, lon2):
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2-lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1)*math.sin(p2) - math.sin(p1)*math.cos(p2)*math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _angle_diff(a, b):
    return abs((float(a) - float(b) + 180.0) % 360.0 - 180.0)


def _cell(lon, lat):
    return math.floor(lon / GRID_DEG), math.floor(lat / GRID_DEG)


def _project_to_segment(lon, lat, a, b):
    """Kaki tegak lokal pada segmen; mengembalikan jarak, fraksi, koordinat, arah."""
    lat0 = math.radians(lat)
    sx = math.cos(lat0) * 111320.0
    sy = 110574.0
    ax, ay = (a[0]-lon)*sx, (a[1]-lat)*sy
    bx, by = (b[0]-lon)*sx, (b[1]-lat)*sy
    vx, vy = bx-ax, by-ay
    denom = vx*vx + vy*vy
    t = 0.0 if denom <= 1e-12 else max(0.0, min(1.0, -(ax*vx+ay*vy)/denom))
    px, py = ax+t*vx, ay+t*vy
    plon = lon + px/sx if sx else lon
    plat = lat + py/sy
    return math.hypot(px, py), t, plon, plat, _bearing(a[1], a[0], b[1], b[0])


def _point_at_distance(coords, target_m):
    """Koordinat lon/lat pada jarak kumulatif dari vertex pertama."""
    remaining = max(0.0, float(target_m))
    for a, b in zip(coords, coords[1:]):
        length = _distance_m(a[1], a[0], b[1], b[0])
        if remaining <= length or (a, b) == (coords[-2], coords[-1]):
            fraction = 0.0 if length <= 0 else min(1.0, remaining / length)
            return (a[0] + (b[0]-a[0])*fraction, a[1] + (b[1]-a[1])*fraction)
        remaining -= length
    return coords[-1]


class MapMatchingEngine:
    def __init__(self, app_root):
        self.app_root = Path(app_root)
        self.exiftool = self._find_exiftool()
        self.last_results = []
        self.last_root = ""
        self.last_road_file = ""
        self.last_interval = 100

    def _find_exiftool(self):
        for p in (
            self.app_root / "bin" / "exiftool.exe",
            self.app_root / "bin" / "exiftool",
            self.app_root / "_internal" / "bin" / "exiftool.exe",
            self.app_root / "_internal" / "bin" / "exiftool",
        ):
            if p.is_file():
                return p
        raise FileNotFoundError("ExifTool tidak ditemukan. Pastikan bin\\\\exiftool.exe ikut dalam folder aplikasi.")

    def _read_batch(self, paths):
        command = [
            str(self.exiftool), "-json", "-n", "-GPSLatitude", "-GPSLongitude",
            "-GPSImgDirection", "-GPSImgDirectionRef", "-DateTimeOriginal", "-CreateDate",
            "-FileName", "-Directory", "--",
        ] + [str(p) for p in paths]
        completed = subprocess.run(command, capture_output=True, text=True, encoding="utf-8",
                                   errors="replace", timeout=240, check=False)
        if completed.returncode not in (0, 1):
            raise RuntimeError(f"ExifTool gagal (kode {completed.returncode}): {completed.stderr[:800]}")
        try:
            items = json.loads(completed.stdout or "[]")
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Respons EXIF bukan JSON valid: {exc}") from exc
        rows = []
        for item in items if isinstance(items, list) else []:
            try:
                path = str(Path(item.get("SourceFile", "")).resolve())
            except OSError:
                path = str(item.get("SourceFile", ""))
            lat, lon = item.get("GPSLatitude"), item.get("GPSLongitude")
            if lat is not None and lon is not None:
                try:
                    lat, lon = float(lat), float(lon)
                    if not (math.isfinite(lat) and math.isfinite(lon) and -90 <= lat <= 90 and -180 <= lon <= 180):
                        lat = lon = None
                except (TypeError, ValueError):
                    lat = lon = None
            else:
                lat = lon = None
            heading = item.get("GPSImgDirection")
            try:
                heading = float(heading) % 360.0 if heading is not None else None
                if heading is not None and not math.isfinite(heading):
                    heading = None
            except (TypeError, ValueError):
                heading = None
            taken = _parse_time(item.get("DateTimeOriginal") or item.get("CreateDate"))
            rows.append({
                "photo_path": path, "photo_name": Path(path).name,
                "source_folder": str(Path(path).parent), "latitude": lat, "longitude": lon,
                "taken_at": taken, "taken_at_text": taken.isoformat(sep=" ") if taken else "",
                "camera_heading_deg": heading, "heading_ref": item.get("GPSImgDirectionRef", ""),
                "file_size_bytes": self._safe_stat_size(path),
                "match_status": "Belum dicocokkan",
            })
        return rows

    @staticmethod
    def _safe_stat_size(path):
        try:
            return Path(path).stat().st_size
        except OSError:
            return None

    def _index_photos(self, root, progress=None, cancel_event=None, batch_size=150):
        root = Path(root)
        if not root.is_dir():
            raise NotADirectoryError(f"Folder foto tidak ditemukan: {root}")
        rows, batch, scanned = [], [], 0
        for path in root.rglob("*"):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Proses dibatalkan.")
            try:
                if not path.is_file() or path.suffix.lower() not in IMAGE_EXTENSIONS:
                    continue
            except OSError:
                continue
            batch.append(path)
            if len(batch) >= batch_size:
                new = self._read_batch(batch)
                rows.extend(new)
                scanned += len(batch)
                if progress:
                    progress("index", scanned, len(rows), f"Memindai metadata foto: {scanned} file.")
                batch = []
        if batch:
            rows.extend(self._read_batch(batch))
            scanned += len(batch)
            if progress:
                progress("index", scanned, len(rows), f"Pemindaian metadata selesai: {scanned} file.")
        return rows, scanned

    def _prepare_segments(self, roads, progress=None):
        segments, grid = [], defaultdict(list)
        road_id_counts = defaultdict(int)
        for road_id, road_name, coords in roads:
            road_id_counts[str(road_id)] += 1
            unique_road_id = str(road_id) if road_id_counts[str(road_id)] == 1 else f"{road_id}__{road_id_counts[str(road_id)]}"
            cumulative = 0.0
            for idx, (a, b) in enumerate(zip(coords, coords[1:])):
                length = _distance_m(a[1], a[0], b[1], b[0])
                if length <= 0.01:
                    continue
                seg = {
                    "road_id": unique_road_id, "road_name": str(road_name),
                    "a": a, "b": b, "road_coords": coords, "seg_index": idx, "offset_m": cumulative,
                    "length_m": length, "bearing_deg": _bearing(a[1], a[0], b[1], b[0]),
                }
                seg_index = len(segments)
                segments.append(seg)
                steps = max(1, int(math.ceil(length / 100.0)))
                for n in range(steps + 1):
                    f = n / steps
                    lon = a[0] + (b[0]-a[0])*f
                    lat = a[1] + (b[1]-a[1])*f
                    grid[_cell(lon, lat)].append(seg_index)
                cumulative += length
            if progress:
                progress("roads", len(segments), len(roads), f"Menyiapkan indeks geometri: {len(segments)} segmen.")
        return segments, grid

    def run(self, photo_root, road_file, interval_m=100, radius_m=100,
            max_speed_kmh=40, heading_tolerance_deg=65, max_time_gap_s=10,
            use_heading=True, use_speed=True, progress=None, cancel_event=None):
        interval_m, radius_m = int(interval_m), float(radius_m)
        max_speed_kmh, heading_tolerance_deg = float(max_speed_kmh), float(heading_tolerance_deg)
        max_time_gap_s = float(max_time_gap_s)
        if interval_m < 1: raise ValueError("Interval STA minimal 1 meter.")
        if not 1 <= radius_m <= 5000: raise ValueError("Radius pencocokan harus 1–5000 meter.")
        if not 1 <= max_speed_kmh <= 160: raise ValueError("Kecepatan maksimum harus 1–160 km/jam.")
        if not 1 <= heading_tolerance_deg <= 180: raise ValueError("Toleransi arah harus 1–180 derajat.")
        if not 1 <= max_time_gap_s <= 300: raise ValueError("Rentang waktu harus 1–300 detik.")
        roads = load_road_segments(road_file)
        segments, grid = self._prepare_segments(roads, progress)
        photos, scanned = self._index_photos(photo_root, progress, cancel_event)
        gps_photos = [p for p in photos if p["latitude"] is not None and p["longitude"] is not None]
        no_gps = []
        for photo in photos:
            if photo["latitude"] is None or photo["longitude"] is None:
                row = dict(photo)
                row.update({"road_id": "", "road_name": "", "sta_m": None, "sta_km": None,
                            "sta_latitude": None, "sta_longitude": None, "distance_m": None,
                            "road_bearing_deg": None, "heading_difference_deg": None,
                            "match_status": "Tidak ada koordinat GPS"})
                no_gps.append(row)
        gps_photos.sort(key=lambda p: (p["taken_at"] is None, p["taken_at"] or datetime.max, p["photo_path"].casefold()))

        # Kecepatan antar-foto berurutan hanya dinilai bila kedua waktu tersedia dan
        # selisih waktu kecil; gap besar tidak boleh ditafsirkan sebagai kecepatan pasti.
        for i, photo in enumerate(gps_photos):
            photo["speed_from_prev_kmh"] = None
            photo["time_gap_prev_s"] = None
            if i == 0:
                continue
            prev = gps_photos[i-1]
            if photo["taken_at"] and prev["taken_at"] and photo["source_folder"] == prev["source_folder"]:
                dt = (photo["taken_at"] - prev["taken_at"]).total_seconds()
                if 0 < dt <= max_time_gap_s:
                    dist = _distance_m(prev["latitude"], prev["longitude"], photo["latitude"], photo["longitude"])
                    photo["time_gap_prev_s"] = dt
                    photo["speed_from_prev_kmh"] = dist / dt * 3.6

        # Candidate matching photo -> segment, then collapse to nearest STA interval.
        best_by_station = {}
        results = []
        radius_cells = max(1, int(math.ceil(radius_m / (GRID_DEG * 110000))) + 1)
        for i, photo in enumerate(gps_photos):
            if cancel_event and cancel_event.is_set():
                raise InterruptedError("Proses dibatalkan.")
            lon, lat = photo["longitude"], photo["latitude"]
            cx, cy = _cell(lon, lat)
            candidates = set()
            for dx in range(-radius_cells, radius_cells+1):
                for dy in range(-radius_cells, radius_cells+1):
                    candidates.update(grid.get((cx+dx, cy+dy), ()))
            scored = []
            speed = photo["speed_from_prev_kmh"]
            speed_bad = bool(use_speed and speed is not None and speed > max_speed_kmh)
            for seg_idx in candidates:
                seg = segments[seg_idx]
                distance, fraction, plon, plat, bearing = _project_to_segment(lon, lat, seg["a"], seg["b"])
                if distance > radius_m:
                    continue
                heading_diff = None
                if photo["camera_heading_deg"] is not None:
                    heading_diff = _angle_diff(photo["camera_heading_deg"], bearing)
                if use_heading and heading_diff is not None and heading_diff > heading_tolerance_deg:
                    continue
                # STA along the digitized line, from its first vertex toward its last.
                sta_exact = seg["offset_m"] + fraction * seg["length_m"]
                sta_bucket = int(math.floor(sta_exact / interval_m) * interval_m)
                sta_lon, sta_lat = _point_at_distance(seg["road_coords"], sta_bucket)
                score = distance + ((heading_diff or 0.0) / 180.0) * min(radius_m, 50.0)
                scored.append((score, distance, heading_diff, seg, sta_exact, sta_bucket, sta_lon, sta_lat, bearing))
            result = dict(photo)
            result.update({
                "road_id": "", "road_name": "", "sta_m": None, "sta_km": None,
                "sta_latitude": None, "sta_longitude": None, "distance_m": None,
                "road_bearing_deg": None, "heading_difference_deg": None,
                "match_status": "Tidak ada ruas dalam radius",
            })
            if speed_bad:
                result["match_status"] = f"Ditolak: kecepatan antar-foto {speed:.1f} km/jam melebihi batas"
            elif scored:
                scored.sort(key=lambda x: (x[0], x[1]))
                score, distance, hdiff, seg, sta_exact, sta_bucket, plon, plat, bearing = scored[0]
                result.update({
                    "road_id": seg["road_id"], "road_name": seg["road_name"],
                    "sta_m": sta_bucket, "sta_km": sta_bucket / 1000.0,
                    "sta_latitude": plat, "sta_longitude": plon,
                    "distance_m": distance, "road_bearing_deg": bearing,
                    "heading_difference_deg": hdiff,
                    "projected_sta_m": sta_exact,
                    "match_status": "Cocok - perlu verifikasi",
                })
                key = (seg["road_id"], sta_bucket)
                previous = best_by_station.get(key)
                rank = (score, distance, result["photo_path"].casefold())
                if previous is None or rank < previous[0]:
                    best_by_station[key] = (rank, result)
            results.append(result)
            if progress and (i+1) % 100 == 0:
                progress("match", i+1, len(gps_photos), f"Mencocokkan foto ber-GPS: {i+1}/{len(gps_photos)}.")

        chosen = []
        for _, row in best_by_station.values():
            row["match_status"] = "Cocok - perlu verifikasi"
            chosen.append(row)
        chosen.sort(key=lambda r: (r["road_name"].casefold(), r["sta_m"] if r["sta_m"] is not None else -1))
        # Retain unmatched/filtered photos in CSV for diagnostics, but mark duplicates as not selected.
        chosen_paths = {r["photo_path"] for r in chosen}
        for row in results:
            if row["match_status"] == "Cocok - perlu verifikasi" and row["photo_path"] not in chosen_paths:
                row["match_status"] = "Kandidat tidak terpilih: STA sudah memiliki foto lebih baik"
        self.last_results = chosen
        self.last_diagnostics = results + no_gps
        self.last_root = str(Path(photo_root).resolve())
        self.last_road_file = str(Path(road_file).resolve())
        self.last_interval = interval_m
        if progress:
            progress("done", len(chosen), len(results),
                     f"Selesai: {scanned} foto dipindai, {len(gps_photos)} memiliki GPS, {len(chosen)} foto terpilih pada STA.")
        return chosen, results, scanned, len(gps_photos)

    def export_csv(self, destination, include_diagnostics=True):
        rows = self.last_diagnostics if include_diagnostics else self.last_results
        fields = [
            "photo_name", "photo_path", "source_folder", "file_size_bytes", "taken_at_text",
            "latitude", "longitude", "camera_heading_deg", "road_id", "road_name",
            "projected_sta_m", "sta_m", "sta_km", "sta_latitude", "sta_longitude",
            "distance_m", "road_bearing_deg", "heading_difference_deg",
            "speed_from_prev_kmh", "time_gap_prev_s", "match_status",
        ]
        with open(destination, "w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
            writer.writeheader()
            for row in rows:
                writer.writerow({k: row.get(k, "") for k in fields})
        return len(rows)

    def export_sta_kml(self, destination):
        ns = "http://www.opengis.net/kml/2.2"
        ET.register_namespace("", ns)
        root = ET.Element(f"{{{ns}}}kml")
        doc = ET.SubElement(root, f"{{{ns}}}Document")
        ET.SubElement(doc, f"{{{ns}}}name").text = "Hasil Map Matching STA"
        for row in self.last_results:
            if row.get("sta_latitude") is None or row.get("sta_longitude") is None:
                continue
            pm = ET.SubElement(doc, f"{{{ns}}}Placemark")
            ET.SubElement(pm, f"{{{ns}}}name").text = f'{row.get("road_name","")} STA {row.get("sta_m")} m'
            desc = ET.SubElement(pm, f"{{{ns}}}description")
            desc.text = (f'Foto: {row.get("photo_name","")}\nJarak: {row.get("distance_m",0):.1f} m'
                         f'\nWaktu: {row.get("taken_at_text","")}\nStatus: {row.get("match_status","")}')
            ext = ET.SubElement(pm, f"{{{ns}}}ExtendedData")
            for key in ("road_id", "road_name", "sta_m", "sta_km", "photo_name", "photo_path",
                        "distance_m", "camera_heading_deg", "heading_difference_deg", "taken_at_text", "match_status"):
                data = ET.SubElement(ext, f"{{{ns}}}Data", name=key)
                ET.SubElement(data, f"{{{ns}}}value").text = str(row.get(key, "") or "")
            point = ET.SubElement(pm, f"{{{ns}}}Point")
            ET.SubElement(point, f"{{{ns}}}coordinates").text = f'{row["sta_longitude"]:.8f},{row["sta_latitude"]:.8f},0'
        ET.ElementTree(root).write(destination, encoding="utf-8", xml_declaration=True)
        return len(self.last_results)

    def copy_matched_photos(self, destination, organize_by="road"):
        destination = Path(destination)
        destination.mkdir(parents=True, exist_ok=True)
        copied, errors = 0, []
        for row in self.last_results:
            source = Path(row["photo_path"])
            if not source.is_file():
                errors.append(f"Foto hilang: {source}")
                continue
            road_dir = _safe_name(row.get("road_name") or row.get("road_id"))
            if organize_by == "sta":
                sta = int(row.get("sta_m") or 0)
                low = (sta // self.last_interval) * self.last_interval
                high = low + self.last_interval
                subfolder = Path(road_dir) / f"STA_{low:06d}_{high:06d}m"
            else:
                subfolder = Path(road_dir)
            target_dir = destination / subfolder
            try:
                target_dir.mkdir(parents=True, exist_ok=True)
                target = target_dir / source.name
                if target.exists():
                    target = target_dir / f"{source.stem}_{abs(hash(str(source))) & 0xffffffff:08x}{source.suffix}"
                shutil.copy2(source, target)
                copied += 1
            except OSError as exc:
                errors.append(f"{source.name}: {exc}")
        return copied, errors

    def create_photo_kmz(self, folder_path, output_file=None):
        """Buat KMZ titik foto GPS; foto asli hanya disalin ke arsip, tidak diubah."""
        folder = Path(folder_path)
        if not folder.is_dir():
            raise NotADirectoryError(f"Folder foto tidak ditemukan: {folder}")
        if output_file is None:
            output_file = folder / f"{_safe_name(folder.name)}_photos.kmz"
        output_file = Path(output_file)
        exif_rows, _ = self._index_photos(folder)
        ns = "http://www.opengis.net/kml/2.2"
        ET.register_namespace("", ns)
        root = ET.Element(f"{{{ns}}}kml")
        doc = ET.SubElement(root, f"{{{ns}}}Document")
        ET.SubElement(doc, f"{{{ns}}}name").text = folder.name
        log_lines = []
        used_names = set()
        with zipfile.ZipFile(output_file, "w", zipfile.ZIP_DEFLATED) as archive:
            for row in exif_rows:
                path = Path(row["photo_path"])
                lat, lon = row.get("latitude"), row.get("longitude")
                if lat is None or lon is None:
                    log_lines.append(f"[NO GPS] {path}")
                    continue
                member = path.name
                if member in used_names:
                    member = f"{path.parent.name}_{member}"
                used_names.add(member)
                pm = ET.SubElement(doc, f"{{{ns}}}Placemark")
                ET.SubElement(pm, f"{{{ns}}}name").text = path.name
                description = ET.SubElement(pm, f"{{{ns}}}description")
                description.text = f'<a href="{member}"><img src="{member}" width="200"/></a>'
                point = ET.SubElement(pm, f"{{{ns}}}Point")
                ET.SubElement(point, f"{{{ns}}}coordinates").text = f"{lon},{lat},0"
                try:
                    archive.write(path, member)
                    log_lines.append(f"[OK] {path.name} -> {lat},{lon}")
                except OSError as exc:
                    log_lines.append(f"[ERROR] {path}: {exc}")
        # Add KML after XML tree is complete. ElementTree safely escapes text and attributes.
            archive.writestr("doc.kml", ET.tostring(root, encoding="utf-8", xml_declaration=True))
        log_path = folder / "map_matching_kmz_log.txt"
        with open(log_path, "a", encoding="utf-8") as handle:
            handle.write(f"\n=== Eksekusi {datetime.now().isoformat(timespec='seconds')} ===\n")
            handle.write("\n".join(log_lines) + "\n")
        return str(output_file), len([line for line in log_lines if line.startswith("[OK]")]), str(log_path)
