import os
import sys
from pathlib import Path

try:
    import win32com.client
    import winreg
except ImportError:
    print("[ERROR] Library pywin32 belum terinstall.")
    print("        Jalankan: python -m pip install pywin32")
    sys.exit(1)


def get_desktop_path() -> Path:
    """
    Dapatkan path Desktop yang benar, termasuk jika Desktop
    dipindah ke OneDrive (sinkronisasi OneDrive).
    Menggunakan Windows Shell API agar selalu akurat.
    """
    shell = win32com.client.Dispatch("WScript.Shell")
    # SpecialFolders("Desktop") selalu mengembalikan path Desktop yang aktual
    desktop = shell.SpecialFolders("Desktop")
    return Path(desktop)


def create_desktop_shortcut():
    project_dir = Path(__file__).parent.resolve()
    target_bat  = project_dir / "run_cctv_recorder.bat"
    icon_file   = project_dir / "cctv_icon.ico"

    desktop_dir   = get_desktop_path()
    shortcut_path = desktop_dir / "CCTV ZIQVA.lnk"

    print(f"     Desktop terdeteksi : {desktop_dir}")
    print(f"     Shortcut target    : {shortcut_path}")

    shell    = win32com.client.Dispatch("WScript.Shell")
    shortcut = shell.CreateShortCut(str(shortcut_path))
    shortcut.TargetPath      = str(target_bat)
    shortcut.WorkingDirectory = str(project_dir)
    shortcut.IconLocation    = str(icon_file) if icon_file.exists() else ""
    shortcut.Description     = "CCTV ZIQVA - Global Stream & Auto Recorder (by team ziqva.com)"
    shortcut.Save()

    print(f"[OK] Shortcut berhasil dibuat: {shortcut_path}")


if __name__ == "__main__":
    create_desktop_shortcut()
