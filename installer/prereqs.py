"""Prerequisite detection for Dino Themes Installer."""
from __future__ import annotations

import os
import shutil
import subprocess
import winreg
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Prereq:
    name: str
    check: Callable[[], bool]
    website: str
    github: str
    description: str
    installed: bool = field(default=False, init=False)

    def refresh(self) -> None:
        try:
            self.installed = self.check()
        except Exception:
            self.installed = False


# ── Detection helpers ────────────────────────────────────────────────────────────

def _reg_exists(hive, path: str) -> bool:
    try:
        with winreg.OpenKey(hive, path):
            return True
    except OSError:
        return False


def _any_path(*paths: str) -> bool:
    return any(os.path.exists(p) for p in paths)


def _windows_apps_has(*fragments: str) -> bool:
    wa = os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")
    try:
        entries = " ".join(os.listdir(wa)).lower()
        return any(f.lower() in entries for f in fragments)
    except OSError:
        return False


def _appx_package(*names: str) -> bool:
    """Check for installed Appx packages via PowerShell (timeout-guarded)."""
    query = " -or ".join(f"$_.Name -like '*{n}*'" for n in names)
    cmd = [
        "powershell", "-NoProfile", "-NonInteractive", "-Command",
        f"if (Get-AppxPackage | Where-Object {{ {query} }}) {{ exit 0 }} else {{ exit 1 }}",
    ]
    try:
        r = subprocess.run(cmd, capture_output=True, timeout=8, creationflags=0x08000000)
        return r.returncode == 0
    except Exception:
        return False


# ── Individual checks ────────────────────────────────────────────────────────────

def _check_powertoys() -> bool:
    for sub in (
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\PowerToys",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\PowerToys",
    ):
        if _reg_exists(winreg.HKEY_LOCAL_MACHINE, sub):
            return True
    return _any_path(
        os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\PowerToys\PowerToys.exe"),
        r"C:\Program Files\PowerToys\PowerToys.exe",
    )


def _check_explorer_patcher() -> bool:
    if _reg_exists(winreg.HKEY_CURRENT_USER, r"Software\ExplorerPatcher"):
        return True
    return _any_path(
        r"C:\Windows\dxgi.dll",
        r"C:\Program Files\ExplorerPatcher\ep_gui.exe",
    )


def _check_files_app() -> bool:
    if _windows_apps_has("FilesUWP", "files.community", "49306ateratera"):
        return True
    return _appx_package("FilesUWP", "Files")


def _check_roundedtb() -> bool:
    if _windows_apps_has("RoundedTB"):
        return True
    if _reg_exists(
        winreg.HKEY_LOCAL_MACHINE,
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\RoundedTB",
    ):
        return True
    return _any_path(os.path.expandvars(r"%LOCALAPPDATA%\RoundedTB\RoundedTB.exe"))


def _check_translucenttb() -> bool:
    if _windows_apps_has("TranslucentTB"):
        return True
    return _any_path(
        os.path.expandvars(r"%LOCALAPPDATA%\TranslucentTB\TranslucentTB.exe"),
        os.path.expandvars(r"%APPDATA%\TranslucentTB\TranslucentTB.exe"),
    )


def _check_rainmeter() -> bool:
    return _any_path(
        r"C:\Program Files\Rainmeter\Rainmeter.exe",
        r"C:\Program Files (x86)\Rainmeter\Rainmeter.exe",
    ) or shutil.which("Rainmeter") is not None


def _check_autohotkey() -> bool:
    if _any_path(
        r"C:\Program Files\AutoHotkey\AutoHotkey.exe",
        r"C:\Program Files\AutoHotkey\v2\AutoHotkey.exe",
        r"C:\Program Files\AutoHotkey\AutoHotkey64.exe",
    ):
        return True
    if _reg_exists(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\AutoHotkey"):
        return True
    return shutil.which("AutoHotkey") is not None


# ── Public prereq list ────────────────────────────────────────────────────────────

PREREQS: list[Prereq] = [
    Prereq(
        name="PowerToys",
        check=_check_powertoys,
        website="https://learn.microsoft.com/en-us/windows/powertoys/",
        github="https://github.com/microsoft/PowerToys",
        description="Windows system utilities",
    ),
    Prereq(
        name="ExplorerPatcher",
        check=_check_explorer_patcher,
        website="https://github.com/valinet/ExplorerPatcher",
        github="https://github.com/valinet/ExplorerPatcher",
        description="Taskbar & Explorer tweaks",
    ),
    Prereq(
        name="Files App",
        check=_check_files_app,
        website="https://files.community",
        github="https://github.com/files-community/Files",
        description="Modern file manager",
    ),
    Prereq(
        name="RoundedTB",
        check=_check_roundedtb,
        website="https://roundedtb.github.io",
        github="https://github.com/RoundedTB/RoundedTB",
        description="Rounded taskbar corners",
    ),
    Prereq(
        name="TranslucentTB",
        check=_check_translucenttb,
        website="https://translucenttb.github.io",
        github="https://github.com/TranslucentTB/TranslucentTB",
        description="Translucent taskbar",
    ),
    Prereq(
        name="Rainmeter",
        check=_check_rainmeter,
        website="https://www.rainmeter.net",
        github="https://github.com/rainmeter/rainmeter",
        description="Desktop widget engine",
    ),
    Prereq(
        name="AutoHotkey v2",
        check=_check_autohotkey,
        website="https://www.autohotkey.com",
        github="https://github.com/AutoHotkey/AutoHotkey",
        description="Hotkey & macro scripting",
    ),
]


def refresh_all() -> None:
    for p in PREREQS:
        p.refresh()
