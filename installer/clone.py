"""Repository clone / download workflow."""
from __future__ import annotations

import os
import json
import shutil
import stat
import subprocess
import tempfile
import threading
import time
import urllib.request
import zipfile
from pathlib import Path
from typing import Callable

REPO_ZIP_URL   = "https://github.com/DinosaursAreCute/Dinos_Windows_Themes/archive/refs/heads/main.zip"
REPO_CLONE_URL = "https://github.com/DinosaursAreCute/Dinos_Windows_Themes.git"
REPO_API_LATEST_RELEASE = "https://api.github.com/repos/DinosaursAreCute/Dinos_Windows_Themes/releases/latest"
MARKER_FILE    = ".dino_themes_install"

ProgressCB = Callable[[str, float], None]  # (message, 0-1 fraction; -1 = indeterminate)


def clone_repo(
    dest: str,
    overwrite: bool = False,
    source_mode: str = "stable",
    progress_cb: ProgressCB | None = None,
    cancel_event: threading.Event | None = None,
) -> None:
    """Clone or download the theme repo into *dest*.

    Raises:
        FileExistsError  – dest is non-empty and overwrite=False
        InterruptedError – cancel_event was set
        RuntimeError     – git / network failure
    """
    dest_path = Path(dest)

    if dest_path.exists() and any(dest_path.iterdir()):
        if not overwrite:
            raise FileExistsError(
                f"'{dest}' already exists and is not empty.\n"
                "Choose a different directory or allow overwrite."
            )
        # Never wipe an existing git working tree unless it was created by this installer.
        if (dest_path / ".git").exists() and not (dest_path / MARKER_FILE).exists():
            raise RuntimeError(
                "Destination appears to be an existing git repository.\n"
                "Please choose a different install folder (for example: C:\\DinoThemes)."
            )
        _safe_remove_tree(dest_path)

    dest_path.mkdir(parents=True, exist_ok=True)

    release_info = None
    if source_mode == "stable":
        release_info = get_latest_release_info()
        if release_info and release_info.get("tag"):
            _report(progress_cb, f"Using latest release {release_info['tag']}", 0.02)
        else:
            _report(progress_cb, "Latest release not found, falling back to main branch.", 0.02)

    if shutil.which("git") and source_mode == "beta":
        _git_clone(dest, progress_cb, cancel_event, branch="main")
    elif shutil.which("git") and source_mode == "stable" and release_info and release_info.get("tag"):
        _git_clone(dest, progress_cb, cancel_event, branch=release_info["tag"])
    else:
        zip_url = REPO_ZIP_URL
        if source_mode == "stable" and release_info and release_info.get("zipball_url"):
            zip_url = release_info["zipball_url"]
        _zip_download(dest, progress_cb, cancel_event, zip_url=zip_url)

    (dest_path / MARKER_FILE).touch()


def is_already_installed(dest: str) -> bool:
    return (Path(dest) / MARKER_FILE).exists()


def get_latest_release_info() -> dict | None:
    """Return {'tag', 'name', 'zipball_url'} or None."""
    req = urllib.request.Request(
        REPO_API_LATEST_RELEASE,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "DinoThemesInstaller",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except Exception:
        return None

    tag = data.get("tag_name")
    name = data.get("name") or tag
    zipball_url = data.get("zipball_url")
    if not tag or not zipball_url:
        return None
    return {"tag": tag, "name": name, "zipball_url": zipball_url}


# ── git path ─────────────────────────────────────────────────────────────────────

def _git_clone(dest: str, cb: ProgressCB | None, cancel: threading.Event | None, branch: str) -> None:
    _report(cb, f"Cloning repository via git ({branch})…", 0.05)
    cmd = ["git", "clone", "--depth", "1", "--branch", branch, REPO_CLONE_URL, dest]
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=0x08000000,  # CREATE_NO_WINDOW
    )
    if proc.stdout is None:
        raise RuntimeError("Unable to read git output stream.")
    for line in proc.stdout:
        if cancel and cancel.is_set():
            proc.terminate()
            raise InterruptedError("Installation cancelled.")
        stripped = line.strip()
        if stripped:
            _report(cb, stripped, -1)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"git clone failed (exit {proc.returncode}).")
    _report(cb, "Clone complete.", 1.0)


# ── zip download path ────────────────────────────────────────────────────────────

def _zip_download(dest: str, cb: ProgressCB | None, cancel: threading.Event | None, zip_url: str) -> None:
    _report(cb, "Downloading repository archive…", 0.05)

    with tempfile.TemporaryDirectory() as tmp:
        zip_path = os.path.join(tmp, "repo.zip")

        # Stream download
        req = urllib.request.Request(
            zip_url,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "DinoThemesInstaller",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            total = int(resp.headers.get("Content-Length", 0) or 0)
            downloaded = 0
            chunk = 65536
            with open(zip_path, "wb") as fh:
                while True:
                    if cancel and cancel.is_set():
                        raise InterruptedError("Installation cancelled.")
                    data = resp.read(chunk)
                    if not data:
                        break
                    fh.write(data)
                    downloaded += len(data)
                    if total:
                        pct = 0.1 + 0.5 * (downloaded / total)
                        _report(cb, f"Downloading… {downloaded // 1024} / {total // 1024} KB", pct)

        _report(cb, "Extracting archive…", 0.65)

        with zipfile.ZipFile(zip_path) as zf:
            members = zf.namelist()
            n = len(members)
            for i, member in enumerate(members):
                if cancel and cancel.is_set():
                    raise InterruptedError("Installation cancelled.")
                # Strip top-level folder (e.g. Dinos_Windows_Themes-main/)
                parts = member.split("/", 1)
                rel = parts[1] if len(parts) > 1 else ""
                if not rel:
                    continue
                target = Path(dest) / rel
                if member.endswith("/"):
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        shutil.copyfileobj(src, dst)
                if i % 20 == 0:
                    _report(cb, f"Extracting… ({i}/{n} files)", 0.65 + 0.3 * (i / max(n, 1)))

    _report(cb, "Download and extraction complete.", 1.0)


def _report(cb: ProgressCB | None, msg: str, pct: float) -> None:
    if cb:
        cb(msg, pct)


def _safe_remove_tree(path: Path) -> None:
    """Best-effort recursive delete for Windows (readonly files, transient locks)."""

    def _on_rm_error(func, p, exc_info):  # noqa: ANN001
        try:
            os.chmod(p, stat.S_IWRITE)
            func(p)
        except Exception:
            # Let outer retry logic handle persistent locks.
            pass

    last_err: Exception | None = None
    for _ in range(5):
        try:
            shutil.rmtree(path, onerror=_on_rm_error)
            return
        except PermissionError as exc:
            last_err = exc
            time.sleep(0.3)
        except OSError as exc:
            last_err = exc
            time.sleep(0.3)

    if last_err is not None:
        raise RuntimeError(
            f"Could not remove '{path}'. Close any apps using that folder and try again.\n"
            f"Details: {last_err}"
        ) from last_err
