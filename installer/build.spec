# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller build spec for Dino Themes Installer.

Run from the installer/ directory:
    python make_assets.py   # generate assets/ first
    pyinstaller build.spec
"""
import os

block_cipher = None

# ── Conditional assets ────────────────────────────────────────────────────────────
datas = []
if os.path.exists("assets/dino_themes.png"):
    datas.append(("assets/dino_themes.png", "assets"))
if os.path.exists("assets/icon.ico"):
    datas.append(("assets/icon.ico", "assets"))

icon_path = "assets/icon.ico" if os.path.exists("assets/icon.ico") else None
ver_file  = "version_info.txt" if os.path.exists("version_info.txt") else None

# ── Analysis ──────────────────────────────────────────────────────────────────────
a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "PIL._tkinter_finder",
        "customtkinter",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="DinoThemesInstaller",
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
    icon=icon_path,
    version=ver_file,
    uac_admin=False,
)
