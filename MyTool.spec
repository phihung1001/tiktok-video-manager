# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_submodules

# Selenium imports Chrome WebDriver modules dynamically. PyInstaller's static
# analysis can otherwise omit selenium.webdriver.chrome.webdriver from the exe.
selenium_hiddenimports = collect_submodules('selenium.webdriver')

# This Python installation has Tcl/Tk files, but PyInstaller's automatic
# tkinter hook cannot validate them. Bundle the runtime explicitly so the
# one-file executable can create the Tkinter GUI.
tcl_root = os.path.join(sys.prefix, 'tcl')
tcl_datas = [
    (os.path.join(tcl_root, 'tcl8.6'), 'tcl/tcl8.6'),
    (os.path.join(tcl_root, 'tk8.6'), 'tcl/tk8.6'),
]
tcl_binaries = [
    (os.path.join(sys.prefix, 'DLLs', 'tcl86t.dll'), '.'),
    (os.path.join(sys.prefix, 'DLLs', 'tk86t.dll'), '.'),
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=tcl_binaries,
    datas=tcl_datas,
    hiddenimports=selenium_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MyTool',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
