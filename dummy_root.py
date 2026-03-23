import sys
from pathlib import Path


def get_app_root() -> Path:
    """
    Returns the root directory where config files (config.json, presets.json) live.

    - Development (plain Python):  directory containing this file (project root).
    - Nuitka --onefile:            directory containing the .exe, exposed via
                                   the special ``__nuitka_binary_dir`` global.
    - PyInstaller --onefile:       ``sys._MEIPASS`` parent → use sys.executable.
    """
    # Nuitka --onefile sets this global to the real exe directory
    nuitka_dir = globals().get("__nuitka_binary_dir")
    if nuitka_dir is not None:
        return Path(nuitka_dir)

    # PyInstaller frozen bundle
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent

    # Normal Python execution
    return Path(__file__).resolve().parent
