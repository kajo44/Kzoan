# APRJ Next — Panduan Penggunaan dan Pemeliharaan

Dokumen ini adalah panduan kerja untuk aplikasi di folder `enterprise`. Nama entry point resmi adalah `aprj_main.py`; jangan menjalankan file compatibility lama.

## 1. Ringkasan aplikasi

APRJ Next menggabungkan lima area kerja:

- **Survei Jalan** — memuat foto, mengisi/meninjau atribut survei, menyimpan catatan lokal, dan mengekspor Excel.
- **Rekayasa AI** — mengimpor dataset berlabel, melatih model lokal, memeriksa checkpoint, dan menjalankan prediksi untuk ditinjau petugas.
- **Map Matching** — pencocokan foto ber-GPS ke ruas/STA, parameter jarak-arah-waktu-kecepatan, ekspor KML/CSV, KMZ titik foto, dan penyalinan foto terpilih.
- **Integrasi Online** — fitur terkait Google Colab dan sinkronisasi PostgreSQL jika server serta kredensial tersedia.
- **Metadata Foto** — salin EXIF antarfolder, ekspor metadata EXIF/GPS ke Excel/CSV, dan tulis koordinat GPS dari Excel/CSV ke JPG/JPEG.

SQLite lokal tetap menjadi penyimpanan lokal. PostgreSQL merupakan integrasi online terpisah. Prediksi AI dan kandidat geospasial harus diverifikasi manusia sebelum dijadikan data resmi.

## 2. Persyaratan sistem

### Untuk membangun aplikasi di Windows

- Windows 10/11 64-bit.
- Python 3.11 64-bit dengan Python Launcher (`py`) dan Tcl/Tk.
- Koneksi internet saat menginstal dependency Python.
- Ruang disk yang memadai; PyTorch CPU membuat paket hasil build cukup besar.
- ExifTool Windows tersedia di `enterprise\\bin\\exiftool.exe`. Jika distribusinya memerlukan `exiftool_files`, sertakan folder tersebut.

### Untuk menjalankan hasil portable

- Salin **seluruh** folder `dist\\APRJ_Next`, bukan hanya EXE.
- Pastikan folder aplikasi dapat ditulisi oleh pengguna karena database, log, model, dan hasil disimpan di folder aplikasi.
- Modul Geospasial Jalan memerlukan ExifTool di folder `bin` pada lokasi aplikasi yang sesuai.
- PostgreSQL hanya diperlukan untuk fungsi online; survei lokal tidak mensyaratkan server PostgreSQL.

Daftar dependency Python langsung berada di `requirements.txt`; dependency untuk proses build berada di `requirements-build.txt`.

## 3. Membangun aplikasi

1. Unduh/checkout repository dan buka folder `enterprise`.
2. Pastikan `bin\\exiftool.exe` tersedia. Script akan mencoba menyalinnya dari `C:\\Tools\\ExifTool` bila ditemukan.
3. Jalankan `build_portable.bat`.
4. Jika build selesai, buka `dist\\APRJ_Next\\APRJ_Next.exe`.
5. Uji aplikasi terlebih dahulu di komputer pembangun, lalu salin seluruh folder `dist\\APRJ_Next` ke komputer lain dan lakukan smoke test kembali.

Build script melakukan pemeriksaan sintaks dan pemaketan PyInstaller. Itu **bukan** pengganti pengujian GUI, uji portable di komputer lain, atau validasi akurasi.

## 4. Alur penggunaan utama

### A. Survei Jalan

1. Buka aplikasi dan pilih tab **Survei Jalan**.
2. Pilih/muat folder atau foto sesuai kontrol pada antarmuka.
3. Tinjau foto dan lengkapi data survei secara manual.
4. Simpan catatan dan uji pembukaan kembali sebelum memproses banyak data.
5. Gunakan ekspor Excel untuk membuat salinan kerja atau bahan impor AI.

Jangan menganggap data tersimpan sebelum operasi simpan berhasil. Pertahankan salinan cadangan database dan file sumber.

### B. Rekayasa AI

1. Siapkan file Excel hasil survei dengan sheet dan kolom yang dikenali aplikasi; path foto sumber harus dapat diakses ketika impor.
2. Gunakan **Pilih Export Excel**, periksa pratinjau, lalu **Konfirmasi Impor**.
3. Proses impor menyimpan referensi jalur foto sumber, hash SHA-256, dan label ke manifest; foto tidak disalin atau dipindahkan.
4. Pastikan folder foto sumber tetap tersedia dan tidak dipindahkan selama training. Tombol **Validasi Dataset** membantu memeriksa foto yang hilang.
5. Pilih mode training yang tersedia, perangkat, epoch, dan batch size yang sesuai kemampuan komputer.
6. Mulai training dan tunggu status selesai; hindari menutup aplikasi saat proses berlangsung.
7. Periksa kesiapan checkpoint, lalu jalankan prediksi pada foto terpilih.
8. Verifikasi hasil prediksi dan terapkan secara manual. Prediksi bukan hasil survei resmi otomatis.

Manifest baru menggunakan `source_path` untuk foto sumber. Record lama yang masih memakai `image_path` tetap didukung. Jika foto sumber hilang, aplikasi dapat memakai salinan lama yang memang sudah tercatat sebagai fallback; foto baru tidak disalin saat impor. Tombol **Relokasi Dataset** dapat mencari foto yang hilang pada folder baru secara rekursif, mencocokkan SHA-256, lalu memperbarui `source_path` tanpa menyalin, memindahkan, atau menghapus file. Path yang masih valid tidak diubah. Hash yang ditemukan pada beberapa file dianggap ambigu dan tidak dipakai untuk relokasi otomatis. Relokasi memerlukan SHA-256 pada manifest; record lama tanpa hash harus diimpor ulang dari Excel atau diperbaiki secara manual.

Model yang ada adalah CNN yang dilatih dari awal, bukan model pretrained. Kualitasnya bergantung pada mutu dan representativitas label. Estimasi lebar dari foto tidak boleh dianggap ukuran resmi tanpa kalibrasi dan verifikasi lapangan.

### C. Map Matching

1. Buka tab **Map Matching**.
2. Pilih folder root foto. Pemindaian mencakup subfolder secara rekursif; foto sumber tidak dipindah atau diubah.
3. Pilih geometri ruas berformat KML, KMZ, GeoJSON, atau JSON yang berisi garis `LineString`/`MultiLineString`. File KMZ foto yang hanya berisi `Point` bukan geometri ruas yang dapat dipakai untuk mencocokkan STA.
4. Atur interval STA (default 100 m), radius pencocokan, batas kecepatan (default 40 km/jam), toleransi arah kamera, dan rentang waktu untuk pemeriksaan kecepatan antar-foto.
5. Jalankan batch. ExifTool membaca koordinat GPS, arah kamera, waktu foto, dan metadata dasar dalam batch. Indeks geometri mempersempit kandidat sebelum perhitungan jarak.
6. Sistem membentuk hingga delapan kandidat ruas per foto. Bila opsi **HMM/Viterbi** aktif, sistem memilih urutan kandidat per folder sumber berdasarkan kecocokan GPS/heading dan konsistensi jarak antarproyeksi; bila nonaktif, baseline memilih kandidat lokal terbaik. Setelah itu dipilih satu foto terbaik per ruas dan bucket STA.
7. Ekspor **CSV Lengkap** untuk mencakup foto yang cocok, tidak cocok, tanpa GPS, atau tidak terpilih karena kandidat STA lain lebih baik. Kolom mencakup nama/path foto, waktu, GPS, heading, ruas, STA, jarak, selisih arah, kecepatan, dan status.
8. Ekspor **STA KML** untuk meninjau titik STA hasil pada perangkat GIS. Tombol **Buat KMZ Foto GPS** membuat arsip KMZ berisi placemark titik foto, thumbnail/link ke foto, file foto, dan log.
9. Gunakan **Salin Foto Terpilih** untuk menyalin (bukan memindahkan) foto ke folder output, disusun per ruas atau per ruas dan interval STA.

**Batas interpretasi dan akurasi:**

- Arah ruas ditentukan oleh urutan vertex pada geometri: arah kamera dibandingkan dengan arah lokal dari vertex awal menuju vertex akhir. Bila garis digitasi terbalik terhadap arah perjalanan, hasil dapat ditolak oleh filter heading. Periksa arah digitasi atau nonaktifkan filter arah untuk pengujian.
- Foto tanpa GPS tidak dapat dicocokkan secara spasial. Foto tanpa heading EXIF masih dapat dipertimbangkan, tetapi arah kamera tidak dapat diverifikasi.
- Batas kecepatan dihitung dari jarak GPS dan selisih waktu antar-foto berurutan dalam folder sumber yang sama, hanya jika kedua timestamp ada dan jedanya tidak melebihi jendela waktu. GPS yang berisik atau timestamp salah dapat menghasilkan penolakan yang keliru.
- HMM/Viterbi memakai emisi jarak GPS dan heading serta transisi berdasarkan selisih antara perpindahan GPS dan jarak antartitik proyeksi. Skala emisi awal (σ = 20 m dan σ arah = 45°) adalah nilai heuristik, belum dikalibrasi pada data lapangan. Kolom `hmm_log_score` merupakan skor log kumulatif, bukan persentase keyakinan. File geometri tanpa topologi jaringan tidak dapat memastikan konektivitas ruas; karena itu transisi ini pendekatan geometris, bukan perutean jaringan penuh. Baseline lokal tetap tersedia sebagai pembanding.
- Semua status hasil adalah kandidat untuk verifikasi manusia. Uji dengan ruas dan foto yang sudah diketahui benar sebelum dipakai sebagai data resmi atau diproses pada skala jutaan foto.

### E. Metadata Foto

1. Buka tab **Metadata Foto**.
2. **Salin metadata EXIF** mencocokkan nama file JPG/JPEG yang sama pada dua folder. Tanpa opsi timpa, aplikasi membuat salinan berakhiran `_with_meta`; dengan opsi timpa, file tujuan yang cocok akan diganti setelah pemrosesan sementara berhasil.
3. **Ekspor metadata** membuat file Excel atau CSV berisi nama dan path foto, koordinat GPS desimal bila tersedia, serta tag EXIF/GPS yang dapat dibaca. Foto tanpa EXIF atau yang gagal dibaca tetap dicatat dengan kolom `MetadataError`.
4. **Impor GPS** membaca kolom `Filename`, `Latitude`, dan `Longitude` dari Excel/CSV lalu menulis koordinat ke foto JPG/JPEG yang namanya cocok. Nilai koordinat divalidasi sebelum ditulis.

Fitur ini bekerja pada file JPG/JPEG langsung di folder yang dipilih (tidak menelusuri subfolder). Penulisan metadata mengubah file foto tujuan; simpan cadangan data penting sebelum operasi timpa/impor. Impor saat ini menulis koordinat GPS, bukan seluruh kolom EXIF dari spreadsheet. Tag EXIF yang berupa data biner/rasional kompleks dapat ditampilkan sebagai representasi teks, bukan selalu sebagai nilai terurai secara semantik.

### D. Integrasi Online

1. Gunakan hanya jika server PostgreSQL dapat dijangkau.
2. Uji koneksi terlebih dahulu.
3. Jangan menulis password ke source code, dokumen publik, atau log.
4. Uji sinkronisasi dengan data contoh dan pastikan kegagalan jaringan tidak menghilangkan data lokal.

## 5. Data, lokasi, dan pembersihan

Lokasi utama saat aplikasi berjalan dari source:

- `data\\survey.sqlite3` — database survei.
- `data\\geospatial.sqlite3` — indeks dan hasil geospasial.
- `survey_ai\\dataset\\` — gambar/label dataset AI.
- `survey_ai\\models\\` — checkpoint model.
- `survey_ai\\training_runs\\` — ringkasan dan riwayat training.
- `logs\\` — log aplikasi.

Pada paket frozen, folder data ditentukan relatif terhadap lokasi executable. Sebelum memindahkan atau membersihkan folder aplikasi, tutup aplikasi dan buat cadangan database, dataset, checkpoint, serta hasil ekspor.

Fitur **CLEAN** ditujukan untuk cache yang dikenali; jangan menggunakannya sebagai pengganti pencadangan. Database, dataset, model, dan hasil pemetaan tidak boleh dihapus sebagai cache.

## 6. Troubleshooting

- **Build gagal karena ExifTool** — tempatkan file Windows `exiftool.exe` di `enterprise\\bin`; sertakan `exiftool_files` bila distribusi Anda memerlukannya.
- **Python tidak ditemukan** — instal Python 3.11 64-bit dan aktifkan Python Launcher serta Tcl/Tk.
- **Build gagal saat pip install** — periksa koneksi, ruang disk, dan versi Python; baca pesan error sebelum mengulang.
- **Aplikasi tidak dapat menyimpan** — pastikan folder aplikasi dapat ditulisi dan periksa `logs\\application_errors.log`.
- **AI tidak siap/prediksi gagal** — periksa checkpoint, label, jumlah kelas, dan kompatibilitas model.
- **Foto tidak punya koordinat** — pastikan metadata GPS tersedia dan dapat dibaca ExifTool.
- **Tidak ada kandidat foto** — cek radius, koordinat KML/GeoJSON, metadata GPS, dan apakah jalur foto yang dipilih benar.
- **Ekspor tidak cocok dengan template resmi** — cocokkan kolom terhadap template resmi yang berlaku; jangan menganggap format bantu otomatis memenuhi semua ketentuan.

## 7. Struktur modul inti

| File | Tanggung jawab |
|---|---|
| `aprj_main.py` | Entry point resmi |
| `aprj_ui.py` | Antarmuka dan alur aplikasi |
| `aprj_core.py` | Konstanta dan path aplikasi |
| `aprj_database.py` | Sinkronisasi PostgreSQL |
| `aprj_ai_model.py` | Definisi arsitektur model |
| `aprj_training_engine.py` | Training dan inferensi |
| `aprj_pkrms.py` | Utilitas audit/ekspor PKRMS |
| `aprj_geospasial.py` | Indeks GPS, geometri, STA, pencocokan, CSV |
| `requirements.txt` | Dependency runtime |
| `requirements-build.txt` | Dependency runtime + PyInstaller |
| `build_portable.bat` | Build portable Windows |
| `tests\\` | Tes regresi otomatis |

## 8. Status validasi

Tes unit dan pemeriksaan sintaks melalui GitHub Actions tidak membuktikan seluruh GUI, build Windows, training AI, PostgreSQL, skala jutaan foto, atau akurasi lapangan telah teruji. Sebelum penggunaan operasional, lakukan smoke test pada dataset kecil yang hasilnya dapat diverifikasi manual, lalu tingkatkan skala secara bertahap.
