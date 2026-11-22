# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller specification for building Windows standalone EXE."""

from PyInstaller.utils.hooks import collect_data_files

ctk_datas = collect_data_files("customtkinter")

hidden_imports = [
    "pynput.keyboard._win32",
    "pynput.mouse._win32",
    "pygetwindow",
    "pyautogui",
    "pyperclip",
    "PIL._tkinter_finder",
]

a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=ctk_datas,
    hiddenimports=hidden_imports,
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
    name="SonOyuncuAutoMessageBot",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
