APRJ - APLIKASI SURVEI JALAN PORTABLE
=====================================

BUILD
-----
1. Gunakan Windows 10/11 64-bit.
2. Instal Python 3.11 64-bit dari python.org dan pastikan Tcl/Tk ikut terpasang.
3. Buka folder enterprise, lalu jalankan build_portable.bat.
4. Hasil build berada di dist\APRJ\APRJ.exe.
5. Untuk memindahkan aplikasi, salin seluruh folder dist\APRJ, bukan hanya EXE.
6. Build script memasang PyTorch CPU. GPU CUDA hanya dapat digunakan pada lingkungan
   yang memang mempunyai instalasi PyTorch/CUDA yang cocok; paket portable ini CPU.

ANTARMUKA TERPADU
-----------------
- Survei Jalan: pemuatan foto, penilaian manual, navigasi, preview, penyimpanan
  SQLite lokal, dan ekspor Excel.
- Rekayasa AI: impor hasil survei Excel, dataset berlabel, training lokal, penyimpanan
  checkpoint, pemeriksaan checkpoint, dan prediksi foto untuk ditinjau petugas.
- PKRMS: template Excel, ekspor catatan survei, audit foto, audit dataset
  klasifikasi lama, dan ekspor rekap dataset klasifikasi.
- Integrasi Online: ekspor skrip awal Google Colab, uji koneksi PostgreSQL,
  dan sinkronisasi catatan survei ke PostgreSQL.
- Entry point build adalah main.py yang memanggil APRJ_v2.py.

ALUR TRAINING AI
----------------
1. Jalankan APRJ.exe dan buka tab Rekayasa AI.
2. Klik "Pilih Export Excel", lalu pilih file hasil survei yang mempunyai sheet
   "Hasil Survei Jalan" dan path foto sumber masih bisa diakses.
3. Periksa pratinjau, lalu klik "Konfirmasi Impor". Foto disalin ke
   survey_ai\dataset\images dan label disimpan di survey_ai\dataset\labels.json.
4. Pastikan label hasil survei benar. Label yang kosong tidak diperlakukan sebagai
   label kelas. Untuk melatih satu tugas klasifikasi, dataset harus mempunyai minimal
   dua kelas label yang berbeda untuk tugas tersebut.
5. Atur device, batch, dan epoch, lalu klik "Mulai Training". Training berjalan di
   thread terpisah; jangan tutup aplikasi sebelum selesai.
6. Checkpoint disimpan sebagai survey_ai\models\survey_multi_task_model.pth.
   Ringkasan dan riwayat training disimpan pada survey_ai\training_runs.
7. Klik "Periksa Kesiapan Model", lalu pilih foto pada tab Survei Jalan dan klik
   "Prediksi Foto Aktif". Tinjau saran dan konfirmasi sebelum hasil diterapkan ke form.
   Simpan hasil survei secara manual setelah verifikasi manusia.

BATASAN DAN VALIDASI
--------------------
- Training lokal memakai CNN kecil yang diinisialisasi dari awal, bukan model pretrained.
  Karena itu, kualitas prediksi sangat bergantung pada jumlah, variasi, dan ketepatan
  label. Training yang berhasil selesai tidak otomatis berarti model akurat.
- Foto dan label yang diimpor harus berpasangan dengan benar. Foto sumber harus tersedia
  ketika impor Excel dilakukan. Periksa duplikasi, label kosong/salah, dan ketimpangan kelas.
- Metrik training/validasi bukan sertifikasi akurasi lapangan. Uji model pada foto terpisah
  yang tidak digunakan untuk training sebelum dipakai dalam pekerjaan survei.
- Prediksi lebar perkerasan/bahu/drainase adalah estimasi visual. Foto biasa tidak memberi
  skala fisik yang andal tanpa kalibrasi, referensi ukuran, atau metode pengukuran tambahan.
  Jangan gunakan estimasi lebar sebagai ukuran resmi tanpa verifikasi.
- Probabilitas/confidence model bukan jaminan benar. Semua prediksi harus diperiksa petugas.
- Ekspor Colab tetap berupa skrip awal, bukan pipeline training Colab lengkap.
- PostgreSQL memerlukan server yang dapat dijangkau, kredensial yang benar, dan driver.
- Template PKRMS adalah struktur kerja; kesesuaian dengan skema resmi harus diverifikasi.
- build_portable.bat menjalankan pemeriksaan sintaks, bukan pengujian GUI/runtime penuh.
  Build Windows dan performa training belum dikonfirmasi di lingkungan pengembang.
- Folder aplikasi harus dapat ditulis, misalnya C:\Tools\APRJ. Data AI disimpan di
  folder survey_ai di samping executable.
