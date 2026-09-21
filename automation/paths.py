import os
import shutil
from pathlib import Path

APP_NAME = "TikTokVideoManager"
PROJECT_ROOT = Path(__file__).resolve().parents[1]


def data_root():
    appdata = os.environ.get("APPDATA")
    if appdata:
        return Path(appdata) / APP_NAME
    return Path.home() / ".config" / APP_NAME


DATA_ROOT = data_root()
CONFIG = DATA_ROOT / "config.json"
STATE = DATA_ROOT / "state.json"
LOGS = DATA_ROOT / "logs"
BROWSER_PROFILE = DATA_ROOT / "browser-profile"


def ensure_data_root():
    DATA_ROOT.mkdir(parents=True, exist_ok=True)
    LOGS.mkdir(parents=True, exist_ok=True)
    _migrate_legacy_files()


def _migrate_legacy_files():
    """Import settings/state once without deleting the old portable files."""
    for name, target in (("config.json", CONFIG), ("state.json", STATE)):
        source = PROJECT_ROOT / name
        if source.is_file() and not target.exists():
            try:
                shutil.copy2(source, target)
            except OSError:
                pass
