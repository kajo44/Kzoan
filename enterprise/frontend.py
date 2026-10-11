# -*- coding: utf-8 -*-
"""
Modul Frontend: Antarmuka Grafis Tkinter Terpadu (APRJ & PKRMS).
Menyediakan survei jalan lengkap, canvas interaktif smooth zoom/pan, Mode AI Otomatis, dan manajemen tab.
"""

import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from PIL import Image, ImageTk
import openpyxl

import core
import database
import ai_model
import pkrms_utils


class RoadSurveyAppFrontend:
    def __init__(self, root):
        self.root = root
        self.root.title(f"{core.APP_NAME} - Aplikasi Survei Jalan Terpadu & PKRMS")
        self.root.geometry("1350x780")
        self.root.configure(bg="#eaf2f8")

        core.initialize_portable_dirs()

        self.photo_folder = ""
        self.photo_list = []
        self.current_photo_idx = -1
        self.survey_data = {}
        self.ai_latest_prediction = {}

        self.original_image = None
        self.zoom_scale = 1.0
        self.img_canvas_obj = None

        self.options_config = {
            "bahu_kiri_tipe": ["Tidak Ada", "Beton", "Aspal", "Lapen", "Batu Kali", "Kerikil", "Tanah"],
            "bahu_kiri_kondisi": ["Tidak Ada", "Baik/Rata", "Bekas roda", "Erosi"],
            "bahu_kanan_tipe": ["Tidak Ada", "Beton", "Aspal", "Lapen", "Batu Kali", "Kerikil", "Tanah"],
            "bahu_kanan_kondisi": ["Tidak Ada", "Baik/Rata", "Bekas roda", "Erosi"],
            "drainase_kiri_tipe": ["Tidak Ada", "Tak perlu", "Tanah", "Pasang Batu Terbuka", "Pasang Batu Tertutup"],
            "drainase_kiri_kondisi": ["Tidak Ada", "Tersumbat", "Bersih", "Diperlukan Pasangan", "Diperlukan Drainase", "Erosi"],
            "drainase_kanan_tipe": ["Tidak Ada", "Tak perlu", "Tanah", "Pasang Batu Terbuka", "Pasang Batu Tertutup"],
            "drainase_kanan_kondisi": ["Tidak Ada", "Tersumbat", "Bersih", "Diperlukan Pasangan", "Diperlukan Drainase", "Erosi"],
            "perkerasan_tipe": ["Aspal", "Beton", "Blok Beton", "Lapen", "Batu Kali", "Kerikil", "Tanah"],
            "perkerasan_kondisi": ["BAIK", "SEDANG", "RUSAK RINGAN", "RUSAK BERAT"],
        }
        self.buttons_ref = {}

        self.var_lebar_bahu_kiri = tk.StringVar(value="0")
        self.var_lebar_drainase_kiri = tk.StringVar(value="0")
        self.var_lebar_bahu_kanan = tk.StringVar(value="0")
        self.var_lebar_drainase_kanan = tk.StringVar(value="0")
        self.var_lebar_perkerasan = tk.StringVar(value="0")
        self.current_selections = {key: "" for key in self.options_config.keys()}

        self.build_main_ui()

    def build_main_ui(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True)

        self.survey_tab = tk.Frame(self.notebook, bg="#eaf2f8")
        self.notebook.add(self.survey_tab, text="Survei & Penilaian Jalan")
        self.build_survey_tab_content()

        self.ai_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.ai_tab, text="Rekayasa & Pelatihan AI")
        self.build_ai_tab_content()

        self.online_tab = ttk.Frame(self.notebook, padding=12)
        self.notebook.add(self.online_tab, text="Koneksi Online, Drive, & Peta")
        self.build_online_tab_content()

    def build_survey_tab_content(self):
        top_frame = tk.Frame(self.survey_tab, bg="#1f4e78", bd=1, relief=tk.RAISED)
        top_frame.pack(fill=tk.X, side=tk.TOP, padx=8, pady=5)

        tk.Label(top_frame, text="Folder Foto:", bg="#1f4e78", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5, pady=5)
        self.ent_path = tk.Entry(top_frame, width=40, font=("Arial", 10))
        self.ent_path.pack(side=tk.LEFT, padx=5, pady=5, fill=tk.X, expand=True)

        tk.Button(top_frame, text="PILIH", bg="#3498db", fg="white", font=("Arial", 9, "bold"), command=self.pilih_folder).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(top_frame, text="MUAT", bg="#2ecc71", fg="white", font=("Arial", 9, "bold"), command=self.muat_foto).pack(side=tk.LEFT, padx=3, pady=5)
        tk.Button(top_frame, text="PREVIEW", bg="#f1c40f", fg="black", font=("Arial", 9, "bold"), command=self.tampilkan_preview_popup).pack(side=tk.RIGHT, padx=5, pady=5)
        tk.Button(top_frame, text="EKSPORT", bg="#e67e22", fg="white", font=("Arial", 9, "bold"), command=self.eksport_ke_excel).pack(side=tk.RIGHT, padx=5, pady=5)

        main_layout = tk.Frame(self.survey_tab, bg="#eaf2f8")
        main_layout.pack(fill=tk.BOTH, expand=True, padx=8, pady=5)

        row_top_panels = tk.Frame(main_layout, bg="#eaf2f8")
        row_top_panels.pack(fill=tk.BOTH, expand=True)
        row_top_panels.columnconfigure(0, weight=2)
        row_top_panels.columnconfigure(1, weight=12)
        row_top_panels.columnconfigure(2, weight=2)
        row_top_panels.rowconfigure(0, weight=1)

        def make_scroll_panel(parent, column):
            outer = tk.Frame(parent, bg="#eaf2f8", bd=1, relief=tk.GROOVE)
            outer.grid(row=0, column=column, sticky="nsew", padx=3, pady=3)
            canvas = tk.Canvas(outer, borderwidth=0, background="#f5f6fa", highlightthickness=0)
            scrollbar = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
            content = tk.Frame(canvas, bg="#f5f6fa")
            content.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
            window_id = canvas.create_window((0, 0), window=content, anchor="nw")
            canvas.bind("<Configure>", lambda e: canvas.itemconfigure(window_id, width=e.width))
            canvas.configure(yscrollcommand=scrollbar.set)
            canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            return content

        self.root.bind("<Left>", lambda event: self.foto_sebelumnya())
        self.root.bind("<Right>", lambda event: self.simpan_dan_selanjutnya())
        self.root.bind("<Control-r>", lambda event: self.reset_penilaian())

        # Kolom Kiri
        left_column = make_scroll_panel(row_top_panels, 0)
        tk.Label(left_column, text="KIRI - BAHU JALAN", bg="#7f8c8d", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, padx=2, pady=4)
        f_lebar_bk = tk.Frame(left_column, bg="#f5f6fa")
        f_lebar_bk.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(f_lebar_bk, text="LEBAR (m):", bg="#f5f6fa", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        tk.Entry(f_lebar_bk, textvariable=self.var_lebar_bahu_kiri, width=10, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        f_matrix_bk = tk.Frame(left_column, bg="#f5f6fa")
        f_matrix_bk.pack(fill=tk.X, padx=2, pady=2)
        f_matrix_bk.columnconfigure(0, weight=1); f_matrix_bk.columnconfigure(1, weight=1)
        self.create_side_matrix(f_matrix_bk, "TIPE", "bahu_kiri_tipe", 0)
        self.create_side_matrix(f_matrix_bk, "KONDISI", "bahu_kiri_kondisi", 1)

        tk.Label(left_column, text="KIRI - DRAINASE", bg="#7f8c8d", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, padx=2, pady=(12, 4))
        f_lebar_dk = tk.Frame(left_column, bg="#f5f6fa")
        f_lebar_dk.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(f_lebar_dk, text="LEBAR (m):", bg="#f5f6fa", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        tk.Entry(f_lebar_dk, textvariable=self.var_lebar_drainase_kiri, width=10, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        f_matrix_dk = tk.Frame(left_column, bg="#f5f6fa")
        f_matrix_dk.pack(fill=tk.X, padx=2, pady=2)
        f_matrix_dk.columnconfigure(0, weight=1); f_matrix_dk.columnconfigure(1, weight=1)
        self.create_side_matrix(f_matrix_dk, "TIPE", "drainase_kiri_tipe", 0)
        self.create_side_matrix(f_matrix_dk, "KONDISI", "drainase_kiri_kondisi", 1)

        # Kolom Tengah (Canvas & AI Control Panel)
        center_column = tk.Frame(row_top_panels, bg="#ffffff", bd=1, relief=tk.SOLID)
        center_column.grid(row=0, column=1, sticky="nsew", padx=3, pady=3)
        center_column.rowconfigure(0, weight=0); center_column.rowconfigure(1, weight=0); center_column.rowconfigure(2, weight=1); center_column.columnconfigure(0, weight=1)

        photo_toolbar = tk.Frame(center_column, bg="#34495e")
        photo_toolbar.grid(row=0, column=0, sticky="ew")
        self.lbl_photo_info = tk.Label(photo_toolbar, text="Foto: 0 / 0 | -", bg="#34495e", fg="white", font=("Arial", 9, "bold"))
        self.lbl_photo_info.pack(side=tk.LEFT, padx=10, pady=5)

        tk.Button(photo_toolbar, text=" ⛶ ", bg="#95a5a6", fg="white", font=("Arial", 8, "bold"), command=self.zoom_fit).pack(side=tk.RIGHT, padx=3, pady=5)
        tk.Button(photo_toolbar, text=" - ", bg="#e74c3c", fg="white", font=("Arial", 8, "bold"), command=self.zoom_out).pack(side=tk.RIGHT, padx=3, pady=5)
        tk.Button(photo_toolbar, text=" + ", bg="#2ecc71", fg="white", font=("Arial", 8, "bold"), command=self.zoom_in).pack(side=tk.RIGHT, padx=3, pady=5)

        # Panel Kontrol AI di Tab Survei
        ai_control_panel = tk.Frame(center_column, bg="#d4efdf", bd=1, relief=tk.SOLID)
        ai_control_panel.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        
        tk.Button(
            ai_control_panel, text="🤖 PREDIKSI OTOMATIS (AI)", 
            bg="#27ae60", fg="white", font=("Arial", 8, "bold"),
            command=self.jalankan_prediksi_ai_single
        ).pack(side=tk.LEFT, padx=5, pady=3)
        
        self.lbl_ai_prediction_status = tk.Label(
            ai_control_panel, text="Status AI: Belum diprediksi", 
            bg="#d4efdf", fg="#145a32", font=("Arial", 8, "bold")
        )
        self.lbl_ai_prediction_status.pack(side=tk.LEFT, padx=5, pady=3)
        
        tk.Button(
            ai_control_panel, text="Terapkan Hasil AI", 
            bg="#f39c12", fg="white", font=("Arial", 8, "bold"),
            command=self.terapkan_hasil_ai
        ).pack(side=tk.RIGHT, padx=5, pady=3)

        canvas_container = tk.Frame(center_column, bg="grey")
        canvas_container.grid(row=2, column=0, sticky="nsew")
        canvas_container.rowconfigure(0, weight=1); canvas_container.columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(canvas_container, bg="#2f3640", highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")
        self.canvas.bind("<ButtonPress-1>", lambda e: self.canvas.scan_mark(e.x, e.y))
        self.canvas.bind("<B1-Motion>", lambda e: self.canvas.scan_dragto(e.x, e.y, gain=1))
        self.canvas.bind("<MouseWheel>", self.zoom_mouse_scroll)

        # Kolom Kanan
        right_column = make_scroll_panel(row_top_panels, 2)
        tk.Label(right_column, text="KANAN - BAHU JALAN", bg="#7f8c8d", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, padx=2, pady=4)
        f_lebar_bkr = tk.Frame(right_column, bg="#f5f6fa")
        f_lebar_bkr.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(f_lebar_bkr, text="LEBAR (m):", bg="#f5f6fa", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        tk.Entry(f_lebar_bkr, textvariable=self.var_lebar_bahu_kanan, width=10, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        f_matrix_bkr = tk.Frame(right_column, bg="#f5f6fa")
        f_matrix_bkr.pack(fill=tk.X, padx=2, pady=2)
        f_matrix_bkr.columnconfigure(0, weight=1); f_matrix_bkr.columnconfigure(1, weight=1)
        self.create_side_matrix(f_matrix_bkr, "TIPE", "bahu_kanan_tipe", 0)
        self.create_side_matrix(f_matrix_bkr, "KONDISI", "bahu_kanan_kondisi", 1)

        tk.Label(right_column, text="KANAN - DRAINASE", bg="#7f8c8d", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X, padx=2, pady=(12, 4))
        f_lebar_dkr = tk.Frame(right_column, bg="#f5f6fa")
        f_lebar_dkr.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(f_lebar_dkr, text="LEBAR (m):", bg="#f5f6fa", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        tk.Entry(f_lebar_dkr, textvariable=self.var_lebar_drainase_kanan, width=10, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        f_matrix_dkr = tk.Frame(right_column, bg="#f5f6fa")
        f_matrix_dkr.pack(fill=tk.X, padx=2, pady=2)
        f_matrix_dkr.columnconfigure(0, weight=1); f_matrix_dkr.columnconfigure(1, weight=1)
        self.create_side_matrix(f_matrix_dkr, "TIPE", "drainase_kanan_tipe", 0)
        self.create_side_matrix(f_matrix_dkr, "KONDISI", "drainase_kanan_kondisi", 1)

        # Panel Bawah
        row_bottom_master = tk.Frame(main_layout, bg="#eaf2f8")
        row_bottom_master.pack(fill=tk.X, side=tk.BOTTOM, pady=(8, 2))

        frame_buttons_left = tk.Frame(row_bottom_master, bg="#eaf2f8")
        frame_buttons_left.pack(side=tk.LEFT, fill=tk.Y, padx=5)
        tk.Button(frame_buttons_left, text="RESET", bg="#e74c3c", fg="white", font=("Arial", 8, "bold"), command=self.reset_penilaian).pack(fill=tk.X, pady=2)
        tk.Button(frame_buttons_left, text="LEWATI", bg="#95a5a6", fg="white", font=("Arial", 8, "bold"), command=self.lewati_tanpa_simpan).pack(fill=tk.X, pady=2)

        row_bottom_perkerasan = tk.Frame(row_bottom_master, bg="#eaf2f8", bd=1, relief=tk.GROOVE)
        row_bottom_perkerasan.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        tk.Label(row_bottom_perkerasan, text="PERKERASAN UTAMA", bg="#1976d2", fg="white", font=("Arial", 9, "bold")).pack(fill=tk.X)

        f_lp = tk.Frame(row_bottom_perkerasan, bg="#eaf2f8")
        f_lp.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(f_lp, text="LEBAR PERKERASAN (m):", bg="#eaf2f8", font=("Arial", 9, "bold")).pack(side=tk.LEFT)
        tk.Entry(f_lp, textvariable=self.var_lebar_perkerasan, width=15, font=("Arial", 10)).pack(side=tk.LEFT, padx=5)

        self.create_perkerasan_buttons(row_bottom_perkerasan, "TIPE PERKERASAN", "perkerasan_tipe")
        self.create_perkerasan_buttons(row_bottom_perkerasan, "KONDISI PERKERASAN", "perkerasan_kondisi")

        frame_buttons_right = tk.Frame(row_bottom_master, bg="#eaf2f8")
        frame_buttons_right.pack(side=tk.RIGHT, fill=tk.Y, padx=5)
        tk.Button(frame_buttons_right, text="SEBELUMNYA", bg="#7f8c8d", fg="white", font=("Arial", 8, "bold"), command=self.foto_sebelumnya).pack(fill=tk.X, pady=2)
        tk.Button(frame_buttons_right, text="SIMPAN & LANJUT", bg="#27ae60", fg="white", font=("Arial", 8, "bold"), command=self.simpan_dan_selanjutnya).pack(fill=tk.X, pady=2)

    def build_ai_tab_content(self):
        self.ai_tab.columnconfigure(0, weight=1); self.ai_tab.rowconfigure(2, weight=1)
        ttk.Label(self.ai_tab, text="Rekayasa & Pelatihan AI Multi-Task Survei Jalan", font=("Segoe UI", 15, "bold")).grid(row=0, column=0, sticky="w", pady=(0, 4))
        ttk.Label(self.ai_tab, text="Kelola dataset terkonfirmasi manusia dan latih model AI secara lokal.").grid(row=1, column=0, sticky="w", pady=(0, 10))

        dataset_frame = ttk.LabelFrame(self.ai_tab, text="Dataset Terkonfirmasi")
        dataset_frame.grid(row=2, column=0, sticky="nsew", pady=5)
        dataset_frame.columnconfigure(0, weight=1); dataset_frame.rowconfigure(0, weight=1)

        columns = ("photo", "source", "categories", "widths", "state")
        self.ai_dataset_tree = ttk.Treeview(dataset_frame, columns=columns, show="headings", height=8)
        for key, heading, width in (("photo", "Foto", 180), ("source", "Path Dataset", 380), ("categories", "Kategori", 90), ("widths", "Lebar", 90), ("state", "Status", 130)):
            self.ai_dataset_tree.heading(key, text=heading)
            self.ai_dataset_tree.column(key, width=width, anchor="w")
        self.ai_dataset_tree.grid(row=0, column=0, sticky="nsew")

    def build_online_tab_content(self):
        ttk.Label(self.online_tab, text="Koneksi Cloud, Google Drive, & Google Colab Training", font=("Segoe UI", 15, "bold")).pack(anchor="w", pady=(0, 5))
        
        drive_frame = ttk.LabelFrame(self.online_tab, text="Integrasi Google Drive & Training di Google Colab", padding=10)
        drive_frame.pack(fill=tk.X, pady=5)
        tk.Button(drive_frame, text="Generate Skrip Training Google Colab (.py)", bg="#8e44ad", fg="white", font=("Arial", 9, "bold"), command=self.export_colab_script).pack(anchor="w", pady=5)

        db_frame = ttk.LabelFrame(self.online_tab, text="Koneksi PostgreSQL Database", padding=10)
        db_frame.pack(fill=tk.X, pady=5)
        tk.Label(db_frame, text="Host:").grid(row=0, column=0, sticky="w", padx=3)
        self.db_host = tk.Entry(db_frame, width=15)
        self.db_host.insert(0, "localhost")
        self.db_host.grid(row=0, column=1, padx=3)
        tk.Button(db_frame, text="Test & Sinkron ke PostgreSQL", bg="#2980b9", fg="white", command=self.sync_postgres).grid(row=0, column=6, padx=10)

    # --- Metode Prediksi AI Otomatis ---
    def jalankan_prediksi_ai_single(self):
        """Memeriksa kesiapan inferensi; tidak mengarang hasil tanpa model terlatih."""
        if self.original_image is None:
            messagebox.showwarning("Perhatian", "Belum ada foto yang dimuat di canvas!")
            return

        self.ai_latest_prediction = {}
        if not ai_model.TORCH_AVAILABLE:
            self.lbl_ai_prediction_status.configure(text="Status AI: PyTorch belum terpasang.")
            messagebox.showwarning(
                "AI belum tersedia",
                "PyTorch belum terpasang. Pasang dependensi AI lalu bangun ulang aplikasi."
            )
            return

        model_path = core.SURVEY_AI_MODELS / "survey_multi_task_model.pth"
        if not model_path.is_file():
            self.lbl_ai_prediction_status.configure(text="Status AI: Model terlatih belum tersedia.")
            messagebox.showinfo(
                "Model AI belum tersedia",
                "Belum ditemukan model terlatih di:\n"
                f"{model_path}\n\n"
                "Aplikasi tidak akan menampilkan prediksi palsu. "
                "Latih/siapkan model yang kompatibel sebelum menjalankan inferensi."
            )
            return

        self.lbl_ai_prediction_status.configure(
            text="Status AI: Berkas model ada, loader inferensi belum diimplementasikan."
        )
        messagebox.showwarning(
            "Inferensi belum terhubung",
            "Berkas model ditemukan, tetapi loader dan pemetaan output model "
            "belum diimplementasikan. Tidak ada hasil prediksi yang diterapkan."
        )

    def terapkan_hasil_ai(self):
        """Menerapkan hasil prediksi AI ke form penilaian aktif."""
        if hasattr(self, 'ai_latest_prediction') and self.ai_latest_prediction:
            for key, val in self.ai_latest_prediction.items():
                if key in self.options_config and val in self.options_config[key]:
                    self.select_option_trigger(key, val)
            messagebox.showinfo("Sukses", "Hasil prediksi AI berhasil diterapkan ke form survei!")
        else:
            messagebox.showwarning("Perhatian", "Belum ada data prediksi AI. Jalankan 'Prediksi Otomatis' terlebih dahulu.")

    def create_side_matrix(self, parent_grid, title_label, key_data, col_target):
        f_container = tk.Frame(parent_grid, bg="#f5f6fa")
        f_container.grid(row=0, column=col_target, sticky="nsew", padx=2, pady=1)
        tk.Label(f_container, text=f"{title_label}:", bg="#f5f6fa", font=("Arial", 8, "bold"), fg="#2c3e50").pack(anchor="w", padx=1)
        options = self.options_config[key_data]
        self.buttons_ref[key_data] = {}
        for opt in options:
            btn = tk.Button(f_container, text=opt, font=("Arial", 7, "bold"), bg="#ffffff", fg="#2c3e50", relief=tk.RAISED, bd=1, command=lambda k=key_data, o=opt: self.select_option_trigger(k, o))
            btn.pack(fill=tk.X, padx=1, pady=1)
            self.buttons_ref[key_data][opt] = btn

    def create_perkerasan_buttons(self, parent_frame, title_label, key_data):
        f_container = tk.Frame(parent_frame, bg="#eaf2f8")
        f_container.pack(fill=tk.X, padx=5, pady=1)
        tk.Label(f_container, text=f"{title_label}:", bg="#eaf2f8", fg="#1f4e79", font=("Arial", 8, "bold")).pack(side=tk.LEFT, padx=2)
        f_buttons = tk.Frame(f_container, bg="#eaf2f8")
        f_buttons.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        options = self.options_config[key_data]
        self.buttons_ref[key_data] = {}
        for col, opt in enumerate(options):
            btn = tk.Button(f_buttons, text=opt, font=("Arial", 7, "bold"), bg="#ffffff", fg="#203040", relief=tk.RAISED, bd=1, command=lambda k=key_data, o=opt: self.select_option_trigger(k, o))
            btn.grid(row=0, column=col, sticky="ew", padx=1)
            f_buttons.columnconfigure(col, weight=1)
            self.buttons_ref[key_data][opt] = btn

    def select_option_trigger(self, key_data, selected_value):
        for opt, btn in self.buttons_ref[key_data].items():
            btn.configure(bg="#ffffff", fg="#203040", relief=tk.RAISED)
        self.current_selections[key_data] = selected_value
        self.buttons_ref[key_data][selected_value].configure(bg="#00b894", fg="white", relief=tk.SUNKEN)

    def pilih_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.ent_path.delete(0, tk.END)
            self.ent_path.insert(0, folder)
            self.photo_folder = folder

    def muat_foto(self):
        folder = self.ent_path.get().strip()
        if not folder or not os.path.exists(folder):
            messagebox.showerror("Error", "Path folder foto tidak valid!")
            return
        self.photo_folder = folder
        valid_exts = tuple(core.IMAGE_EXTENSIONS)
        self.photo_list = [f for f in os.listdir(folder) if f.lower().endswith(valid_exts)]
        self.photo_list.sort()
        if not self.photo_list:
            messagebox.showwarning("Informasi", "Tidak ditemukan file foto gambar di folder tersebut.")
            return
        self.current_photo_idx = 0
        self.tampilkan_foto_dan_load_data()

    def tampilkan_foto_dan_load_data(self):
        if not self.photo_list or self.current_photo_idx < 0:
            return
        filename = self.photo_list[self.current_photo_idx]
        full_path = os.path.join(self.photo_folder, filename)
        try:
            self.original_image = Image.open(full_path)
            self.zoom_fit()
        except Exception as e:
            core.log_application_error("Muat Foto Canvas", type(e), e, e.__traceback__)
            return
        self.lbl_photo_info.configure(text=f"Foto: {self.current_photo_idx + 1} / {len(self.photo_list)} | {filename}")
        self.lbl_ai_prediction_status.configure(text="Status AI: Belum diprediksi")
        self.ai_latest_prediction = {}
        if filename in self.survey_data:
            self.load_saved_fields(self.survey_data[filename])

    def render_canvas_image(self):
        if self.original_image is None:
            return
        w, h = self.original_image.size
        new_w = int(w * self.zoom_scale)
        new_h = int(h * self.zoom_scale)
        if new_w <= 0 or new_h <= 0:
            return
        resized = self.original_image.resize((new_w, new_h), Image.Resampling.LANCZOS)
        self.tk_photo = ImageTk.PhotoImage(resized)
        self.canvas.delete("all")
        c_w = max(700, self.canvas.winfo_width())
        c_h = max(500, self.canvas.winfo_height())
        pos_x = max(0, (c_w - new_w) // 2)
        pos_y = max(0, (c_h - new_h) // 2)
        self.img_canvas_obj = self.canvas.create_image(pos_x, pos_y, anchor="nw", image=self.tk_photo)
        self.canvas.config(scrollregion=(0, 0, max(c_w, new_w), max(c_h, new_h)))

    def zoom_in(self):
        if self.original_image:
            self.zoom_scale *= 1.2
            self.render_canvas_image()

    def zoom_out(self):
        if self.original_image:
            self.zoom_scale /= 1.2
            self.render_canvas_image()

    def zoom_fit(self):
        if self.original_image is None:
            return
        self.root.update_idletasks()
        c_w = max(700, self.canvas.winfo_width())
        c_h = max(500, self.canvas.winfo_height())
        img_w, img_h = self.original_image.size
        self.zoom_scale = min(c_w / img_w, c_h / img_h) * 0.95
        self.render_canvas_image()

    def zoom_mouse_scroll(self, event):
        if self.original_image is None:
            return
        if event.delta > 0 or getattr(event, "num", 0) == 4:
            self.zoom_scale *= 1.15
        else:
            self.zoom_scale /= 1.15
        self.zoom_scale = max(0.1, min(self.zoom_scale, 15.0))
        self.render_canvas_image()

    def load_saved_fields(self, data):
        self.var_lebar_bahu_kiri.set(data.get("lebar_bahu_kiri", "0"))
        self.var_lebar_drainase_kiri.set(data.get("lebar_drainase_kiri", "0"))
        self.var_lebar_bahu_kanan.set(data.get("lebar_bahu_kanan", "0"))
        self.var_lebar_drainase_kanan.set(data.get("lebar_drainase_kanan", "0"))
        self.var_lebar_perkerasan.set(data.get("lebar_perkerasan", "0"))
        for key in self.options_config.keys():
            val = data.get(key, "")
            if val in self.options_config[key]:
                self.select_option_trigger(key, val)

    def simpan_dan_selanjutnya(self):
        if not self.photo_list or self.current_photo_idx < 0:
            return
        filename = self.photo_list[self.current_photo_idx]
        current_data = {
            "folder": self.photo_folder,
            "lebar_bahu_kiri": self.var_lebar_bahu_kiri.get(),
            "lebar_drainase_kiri": self.var_lebar_drainase_kiri.get(),
            "lebar_bahu_kanan": self.var_lebar_bahu_kanan.get(),
            "lebar_drainase_kanan": self.var_lebar_drainase_kanan.get(),
            "lebar_perkerasan": self.var_lebar_perkerasan.get(),
        }
        current_data.update(self.current_selections)
        self.survey_data[filename] = current_data
        if self.current_photo_idx < len(self.photo_list) - 1:
            self.current_photo_idx += 1
            self.tampilkan_foto_dan_load_data()
        else:
            messagebox.showinfo("Selesai", "Semua foto dalam folder telah dievaluasi!")

    def foto_sebelumnya(self):
        if self.current_photo_idx > 0:
            self.current_photo_idx -= 1
            self.tampilkan_foto_dan_load_data()

    def lewati_tanpa_simpan(self):
        if self.current_photo_idx < len(self.photo_list) - 1:
            self.current_photo_idx += 1
            self.tampilkan_foto_dan_load_data()

    def reset_penilaian(self):
        self.var_lebar_bahu_kiri.set("0")
        self.var_lebar_drainase_kiri.set("0")
        self.var_lebar_bahu_kanan.set("0")
        self.var_lebar_drainase_kanan.set("0")
        self.var_lebar_perkerasan.set("0")
        for key in self.options_config.keys():
            self.current_selections[key] = ""
            for opt, btn in self.buttons_ref[key].items():
                btn.configure(bg="#ffffff", fg="#203040", relief=tk.RAISED)

    def tampilkan_preview_popup(self):
        popup = tk.Toplevel(self.root)
        popup.title("Preview Data Survei")
        popup.geometry("950x450")
        tree = ttk.Treeview(popup, columns=("foto", "l_perkerasan", "t_perkerasan", "k_perkerasan"), show="headings")
        tree.heading("foto", text="Nama Foto")
        tree.heading("l_perkerasan", text="Lebar Perkerasan")
        tree.heading("t_perkerasan", text="Tipe Perkerasan")
        tree.heading("k_perkerasan", text="Kondisi")
        tree.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        for fn, d in self.survey_data.items():
            tree.insert("", tk.END, values=(fn, d.get("lebar_perkerasan", "-"), d.get("perkerasan_tipe", "-"), d.get("perkerasan_kondisi", "-")))

    def eksport_ke_excel(self):
        if not self.survey_data:
            messagebox.showwarning("Perhatian", "Belum ada data survei untuk dieksport.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")])
        if not path:
            return
        try:
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Hasil Survei Jalan"
            ws.append(["Nama File Foto", "Lebar Perkerasan", "Tipe Perkerasan", "Kondisi Perkerasan"])
            for fn, d in self.survey_data.items():
                ws.append([fn, d.get("lebar_perkerasan"), d.get("perkerasan_tipe"), d.get("perkerasan_kondisi")])
            wb.save(path)
            messagebox.showinfo("Sukses", f"File berhasil disimpan di:\n{path}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def sync_postgres(self):
        manager = database.DatabaseManager(host=self.db_host.get())
        success, msg = manager.test_connection()
        if success:
            _, sync_msg = manager.sync_to_postgres(self.survey_data)
            messagebox.showinfo("PostgreSQL", sync_msg)
        else:
            messagebox.showerror("Koneksi Gagal", msg)

    def export_colab_script(self):
        path = filedialog.asksaveasfilename(defaultextension=".py", initialfile="train_colab_aprj.py", filetypes=[("Python Files", "*.py")])
        if path:
            _, msg = ai_model.GoogleDriveColabManager.generate_colab_training_notebook(path)
            messagebox.showinfo("Google Colab Exporter", f"{msg}\nDisimpan di: {path}")


if __name__ == "__main__":
    # Blok opsional agar frontend.py dapat diuji secara mandiri jika diperlukan
    root = tk.Tk()
    app = RoadSurveyAppFrontend(root)
    root.mainloop()