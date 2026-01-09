import sys
from configparser import ConfigParser
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


def _get_ini_filepath() -> Path:
    root_dir = get_root_dir()
    ini_filepath = Path(root_dir / 'configuration' / 'config.ini')
    return ini_filepath


def load_ini() -> ConfigParser:
    config_data = ConfigParser()
    ini_filepath: Path = _get_ini_filepath()
    config_data.read(str(ini_filepath))
    return config_data


def find_selection(config_data: ConfigParser, header: str, selection: str) -> str:
    return config_data.get(header, f'{selection}')


if __name__ == '__main__':
    # How to get the data in the ini file
    config_data = load_ini()
    IPAddress = find_selection(config_data, 'IPAddress', 'IPAddress')
    print(IPAddress)
