# APRJ Next — Panduan Penggunaan dan Pemeliharaan

Dokumen ini adalah panduan kerja untuk aplikasi di folder `enterprise`. Nama entry point resmi adalah `aprj_main.py`; jangan menjalankan file compatibility lama.

## Visualisasi Peta Online

Tab **Integrasi Online** menyediakan dua alur visualisasi:
- **Visualisasikan Hasil Aplikasi**: menampilkan titik foto, titik STA, dan geometri ruas dari berkas jalan yang dipilih.
- **Impor Data untuk Peta**: membaca geometri garis KML/KMZ/GeoJSON/JSON atau titik dari CSV yang memiliki kolom `latitude/longitude` (juga `lat/lon`).
- **Kontrol layer peta**: gunakan panel layer di kanan atas untuk menyalakan/mematikan **Ruas jalan**, **Titik foto**, **Titik STA**, dan **Skor/kondisi**. Layer skor/kondisi akan berisi fitur yang memiliki atribut kondisi/skor; warna marker adalah indikasi visual sederhana berdasarkan teks/nilai atribut, bukan hasil penilaian resmi.

Aplikasi menghasilkan HTML lokal dan membukanya pada browser. Basemap Leaflet/OpenStreetMap dan pustaka peta dimuat dari internet; tanpa internet, peta dasar mungkin tidak tampil. Berkas foto dan data sumber tidak diunggah otomatis, tetapi koordinat dan atribut yang dipetakan dapat terlihat pada browser lokal. Periksa ketentuan penggunaan OpenStreetMap sebelum penggunaan produksi.

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
- ExifTool lokal adalah pembaca metadata utama. Jika tidak tersedia saat menjalankan source, pembacaan EXIF dasar memakai Pillow sebagai fallback; format/tag khusus mungkin hanya terbaca dengan ExifTool.
- PostgreSQL hanya diperlukan untuk fungsi online; survei lokal tidak mensyaratkan server PostgreSQL.

Daftar dependency Python langsung berada di `requirements.txt`; dependency untuk proses build berada di `requirements-build.txt`.

## 3. Membangun aplikasi

1. Unduh/checkout repository dan buka folder `enterprise`.
2. Pastikan `bin\\exiftool.exe` tersedia. Script akan mencoba menyalinnya dari `C:\\Tools\\ExifTool` bila ditemukan.
3. Jalankan `build_portable.bat`. Script memeriksa sintaks dan menjalankan tes regresi sebelum pemaketan.
4. Jika build selesai, buka `dist\\APRJ_Next\\APRJ_Next.exe`.
5. Uji aplikasi terlebih dahulu di komputer pembangun, lalu salin seluruh folder `dist\\APRJ_Next` ke komputer lain dan lakukan smoke test kembali.

Build script menjalankan pemeriksaan sintaks dan `unittest` sebelum pemaketan PyInstaller. Tes otomatis hanya mencakup fungsi yang diuji; itu **bukan** pengganti pengujian GUI, uji portable di komputer lain, atau validasi akurasi.

## 3A. Menyiapkan AI untuk training pertama

Jalankan `prepare_ai_training.bat` dari folder `enterprise` untuk membuat/menggunakan
`.venv`, memasang dependensi runtime, mengunduh dan memvalidasi bobot dasar ResNet-18,
serta menyiapkan folder model. Panduan rinci tersedia di `PERSIAPAN_AI_SURVEI.txt`.

Script ini tidak mengunduh checkpoint kondisi jalan yang sudah terlatih karena
checkpoint seperti itu harus dihasilkan dari foto dan label survei APRJ yang valid.
Setelah mengimpor dan memvalidasi dataset, pilih **Latih ulang dari awal** untuk
training pertama. Checkpoint yang dipakai inferensi adalah
`survey_ai\\models\\survey_multi_task_model.pth`; bobot ImageNet di folder
`pretrained` merupakan file yang berbeda.

## 4. Alur penggunaan utama

### A. Survei Jalan

1. Buka aplikasi dan pilih tab **Survei Jalan**.
2. Pilih/muat folder atau foto sesuai kontrol pada antarmuka.
3. Tinjau foto dan lengkapi data survei secara manual.
4. **MODE AI: ON/OFF** mengendalikan prediksi otomatis saat foto dimuat atau berpindah.
5. **POP-UP AI: ON** meminta konfirmasi sebelum saran prediksi diterapkan. **POP-UP AI: OFF** melewati dialog konfirmasi dan menerapkan saran ke form langsung. Preferensi disimpan di `config/survey_session.json`; default untuk sesi lama adalah ON. Toggle ini tidak menonaktifkan popup error/diagnostik.
6. Saran AI tetap harus ditinjau. Penilaian tidak dianggap sebagai hasil final otomatis; simpan dan verifikasi catatan survei.
7. Gunakan ekspor Excel untuk membuat salinan kerja atau bahan impor AI.

Jangan menganggap data tersimpan sebelum operasi simpan berhasil. Pertahankan salinan cadangan database dan file sumber.

### B. Rekayasa AI

1. Siapkan file Excel hasil survei dengan sheet dan kolom yang dikenali aplikasi; path foto sumber harus dapat diakses ketika impor.
2. Gunakan **Pilih Export Excel**, periksa pratinjau, lalu **Konfirmasi Impor**.
3. Proses impor menyimpan referensi jalur foto sumber, hash SHA-256, dan label ke manifest; foto tidak disalin atau dipindahkan.
4. Pastikan folder foto sumber tetap tersedia dan tidak dipindahkan selama training. Tombol **Validasi Dataset** membantu memeriksa foto yang hilang.
5. Pilih mode training yang tersedia, perangkat, epoch, dan batch size yang sesuai kemampuan komputer.
6. Mulai training dan tunggu status selesai; hindari menutup aplikasi saat proses berlangsung.
7. Periksa kesiapan checkpoint, lalu jalankan prediksi pada foto terpilih.
8. Gunakan **CLEAN — Bersihkan Cache** pada tab Rekayasa AI untuk membersihkan cache/berkas sementara yang dikenal. CLEAN tidak dimaksudkan untuk menghapus database survei, foto sumber, dataset, checkpoint, atau hasil training.
9. Gunakan **Ekspor Hasil Proses (Excel)** untuk membuat satu workbook dengan lembar Ringkasan, Survei Jalan, Geospasial STA, dan Map Matching sesuai hasil yang tersedia. Diagnostik Map Matching yang diekspor adalah hasil proses terakhir di sesi aplikasi.
10. Verifikasi hasil prediksi dan ekspor. Prediksi bukan hasil survei resmi otomatis.

Manifest baru menggunakan `source_path` untuk foto sumber. Record lama yang masih memakai `image_path` tetap didukung. Jika foto sumber hilang, aplikasi dapat memakai salinan lama yang memang sudah tercatat sebagai fallback; foto baru tidak disalin saat impor. Tombol **Relokasi Dataset** dapat mencari foto yang hilang pada folder baru secara rekursif, mencocokkan SHA-256, lalu memperbarui `source_path` tanpa menyalin, memindahkan, atau menghapus file. Path yang masih valid tidak diubah. Hash yang ditemukan pada beberapa file dianggap ambigu dan tidak dipakai untuk relokasi otomatis. Relokasi memerlukan SHA-256 pada manifest; record lama tanpa hash harus diimpor ulang dari Excel atau diperbaiki secara manual.

Training baru menggunakan backbone ResNet-18 dengan bobot pretrained ImageNet yang disiapkan saat build dan dibundel lokal; aplikasi tidak mengunduh bobot saat runtime. Bobot ImageNet adalah fitur visual umum, bukan model yang telah dilatih khusus untuk kondisi jalan. Kepala klasifikasi/regresi APRJ tetap harus dilatih menggunakan label survei yang relevan. Kualitas bergantung pada mutu dan representativitas label. Estimasi lebar dari foto tidak boleh dianggap ukuran resmi tanpa kalibrasi dan verifikasi lapangan.

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
- **Foto tidak punya koordinat** — pastikan foto menyimpan GPS EXIF. Jika ExifTool tidak tersedia, Pillow mencoba membaca tag EXIF dasar; format/tag yang tidak didukung dapat memerlukan ExifTool.
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
| `aprj_exif_fallback.py` | Fallback EXIF dasar berbasis Pillow jika ExifTool tidak tersedia |
| `requirements.txt` | Dependency runtime |
| `requirements-build.txt` | Dependency runtime + PyInstaller |
| `build_portable.bat` | Build portable Windows |
| `tests\\` | Tes regresi otomatis |

## 8. Status validasi

- Pemeriksaan sintaks Python dan tes regresi otomatis: **lulus** pada GitHub Actions untuk commit `8d3804074004a6f766de5e7c38edfdc09b6c6cbb`. [Lihat hasil CI](https://github.com/kajo44/Kzoan/actions/runs/38797687356).
- Fitur POP-UP AI ON/OFF sudah masuk ke source; perilaku GUI perlu diuji langsung pada Windows dengan model/checkpoint yang tersedia.
- Build PyInstaller ONEDIR pada Windows, training AI nyata, koneksi PostgreSQL, ekspor menggunakan data operasional, beban jutaan foto, dan akurasi lapangan **belum dibuktikan oleh CI ini**.

Sebelum penggunaan operasional, jalankan smoke test pada dataset kecil yang hasilnya dapat diverifikasi manual. Periksa kedua keadaan POP-UP AI, simpan/pulihkan sesi, file Excel yang dihasilkan, serta startup paket portable pada Windows bersih. Naikkan skala secara bertahap dan catat error yang muncul.
