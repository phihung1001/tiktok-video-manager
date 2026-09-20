import os
import shutil
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

def create_driver(root: Path):
    profile = root / "browser-profile"
    profile.mkdir(exist_ok=True)

    options = Options()
    options.add_argument(f"--user-data-dir={profile}")
    options.add_argument("--start-maximized")
    options.add_argument("--disable-notifications")
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
