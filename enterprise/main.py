# -*- coding: utf-8 -*-
"""Entry point aplikasi APRJ/PKRMS."""
import tkinter as tk
import core
from frontend import RoadSurveyAppFrontend


def main():
    core.initialize_portable_dirs()
    root = tk.Tk()
    try:
        RoadSurveyAppFrontend(root)
        root.mainloop()
    except Exception as exc:
        core.log_application_error("Startup aplikasi", type(exc), exc, exc.__traceback__)
        try:
            from tkinter import messagebox
            messagebox.showerror("APRJ/PKRMS gagal dijalankan", f"{exc}\n\nPeriksa logs/application_errors.log.")
        except Exception:
            pass
        raise


if __name__ == "__main__":
    main()
