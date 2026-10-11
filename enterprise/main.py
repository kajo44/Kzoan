# -*- coding: utf-8 -*-
"""
Skrip Utama (Entry Point) untuk Menjalankan Aplikasi APRJ & PKRMS.
"""

import tkinter as tk
import core
from frontend import RoadSurveyAppFrontend

if __name__ == "__main__":
    core.initialize_portable_dirs()
    root = tk.Tk()
    app = RoadSurveyAppFrontend(root)
    root.mainloop()