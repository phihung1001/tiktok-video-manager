import os
import shutil
from datetime import datetime
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .paths import BROWSER_PROFILE, DATA_ROOT, ensure_data_root

def _profile_is_locked(profile: Path):
    return any((profile / name).exists() for name in (
        "SingletonLock", "SingletonCookie", "SingletonSocket"
    ))

def _session_profile(root: Path):
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    profile = root / f"browser-profile-session-{stamp}"
    profile.mkdir(parents=True, exist_ok=False)
    return profile

def create_driver(root: Path):
    ensure_data_root()
    profile = BROWSER_PROFILE
    profile.mkdir(parents=True, exist_ok=True)
    if _profile_is_locked(profile):
        profile = _session_profile(DATA_ROOT)

    options = Options()
    options.add_argument(f"--user-data-dir={profile}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
    options.add_argument("--no-first-run")
    options.add_argument("--no-default-browser-check")
    options.add_experimental_option("excludeSwitches", ["enable-logging"])

    # Ignore an old chromedriver in PATH and let Selenium Manager match Chrome.
    original_path = os.environ.get("PATH", "")
    path_driver = shutil.which("chromedriver")
    if path_driver:
        driver_dir = os.path.normcase(os.path.abspath(os.path.dirname(path_driver)))
        os.environ["PATH"] = os.pathsep.join(
            entry for entry in original_path.split(os.pathsep)
            if os.path.normcase(os.path.abspath(entry)) != driver_dir
        )
    try:
        driver = webdriver.Chrome(options=options)
    finally:
        os.environ["PATH"] = original_path
    driver.set_page_load_timeout(60)
    return driver
