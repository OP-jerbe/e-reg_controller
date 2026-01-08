import sys
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path


def get_app_version() -> str:
    try:
        return version('e_reg_controller')
    except PackageNotFoundError:
        return 'development-build'


def get_root_dir() -> Path:
    """
    Get the root directory of the __main__ file.

    Returns [str]:
        Path object
    """
    if getattr(sys, 'frozen', False):  # Check if running from the PyInstaller EXE
        return Path(getattr(sys, '_MEIPASS', '.'))
    else:  # Running in a normal Python environment
        return Path(__file__).resolve().parents[1]
