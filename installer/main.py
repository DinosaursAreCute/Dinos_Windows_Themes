"""Dino Themes Installer — GUI + silent CLI."""
from __future__ import annotations

import argparse
import os
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from clone import clone_repo, get_latest_release_info, is_already_installed
from prereqs import PREREQS, Prereq, refresh_all

BG = "#111415"
PANEL = "#181C1E"
PANEL_DARK = "#0E1112"
PANEL_ALT = "#1C2124"
ACCENT = "#C44B8E"
ACCENT_HI = "#E8719A"
TEXT = "#E8E8E8"
TEXT_DIM = "#7A7A8A"
GREEN = "#4CAF88"
RED = "#E05555"
WARNING_COL = "#E8A020"
BORDER = "#252B2E"

FONT_TITLE = ("Segoe UI Variable", 22, "bold")
FONT_BODY = ("Segoe UI Variable", 12)
FONT_SMALL = ("Segoe UI Variable", 11)
FONT_BOLD = ("Segoe UI Variable", 13, "bold")
FONT_MONO = ("Consolas", 11)

VERSION = "v1.1"


def resource_path(rel: str) -> str:
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).parent))
    return str(base / rel)


def load_logo(size: int = 64) -> ctk.CTkImage | None:
    for cand in (resource_path("assets/dino_themes.png"), resource_path("assets/logo.png"), resource_path("assets/logo.ico")):
        try:
            img = Image.open(cand).convert("RGBA")
            return ctk.CTkImage(img, size=(size, size))
        except Exception:
            pass
    return None


def is_windows_11() -> bool:
    if os.name != "nt":
        return False
    try:
        return sys.getwindowsversion().build >= 22000
    except Exception:
        return False


def run_theme_apply_script(dest: str, options: dict, log_cb=None) -> None:
    script_path = Path(dest) / "install.ps1"
    if not script_path.exists():
        raise FileNotFoundError(f"install.ps1 not found in {dest}")

    cmd = [
        "powershell",
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script_path),
    ]

    if options.get("apply_explorerpatcher"):
        cmd.append("-ApplyExplorerPatcher")
    if options.get("autostart"):
        cmd.append("-EnableAutoStart")
    if options.get("interlude87"):
        cmd.append("-SetInterlude87Wallpaper")
    if options.get("backup_configs"):
        cmd.append("-BackupCurrentConfigs")
    if options.get("set_accent_color"):
        cmd.append("-SetAccentColor")

    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        creationflags=0x08000000,
    )
    assert proc.stdout is not None
    for line in proc.stdout:
        line = line.rstrip()
        if line and log_cb:
            log_cb(line)
    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"Theme apply script failed with exit code {proc.returncode}")


class DinoInstaller(ctk.CTk):
    def __init__(self) -> None:
        super().__init__(fg_color=BG)
        self.title("Dino Themes Installer")
        self.geometry("860x760")
        self.resizable(False, False)

        icon = resource_path("assets/icon.ico")
        if os.path.exists(icon):
            try:
                self.iconbitmap(icon)
            except Exception:
                pass

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("dark-blue")

        self._cancel_event = threading.Event()
        self._install_dir = ctk.StringVar(value=str(Path.home() / "DinoThemes"))
        self._release_text = ctk.StringVar(value="Checking latest release...")

        self._is_win11 = is_windows_11()
        self._install_supported = self._is_win11

        self._opt_beta = ctk.BooleanVar(value=False)
        self._opt_apply_theme = ctk.BooleanVar(value=True)
        self._opt_apply_explorerpatcher = ctk.BooleanVar(value=False)
        self._opt_autostart = ctk.BooleanVar(value=False)
        self._opt_interlude87 = ctk.BooleanVar(value=False)
        self._opt_backup_configs = ctk.BooleanVar(value=True)
        self._opt_set_accent = ctk.BooleanVar(value=False)

        self._build_header()
        self._build_body()
        self._build_footer()
        self._show_page("setup")
        self._async_check_prereqs()
        threading.Thread(target=self._fetch_release_text, daemon=True).start()

    def _build_header(self) -> None:
        hdr = ctk.CTkFrame(self, fg_color=PANEL_DARK, corner_radius=0, height=88)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)

        logo = load_logo(56)
        if logo:
            ctk.CTkLabel(hdr, image=logo, text="").pack(side="left", padx=(22, 10), pady=14)

        text_col = ctk.CTkFrame(hdr, fg_color="transparent")
        text_col.pack(side="left", pady=14)
        ctk.CTkLabel(text_col, text="Dino Themes", font=FONT_TITLE, text_color=ACCENT_HI).pack(anchor="w")
        ctk.CTkLabel(text_col, text="Windows 11 Theme Installer", font=FONT_SMALL, text_color=TEXT_DIM).pack(anchor="w")

        ctk.CTkLabel(hdr, text=VERSION, font=FONT_SMALL, text_color=TEXT_DIM, fg_color=PANEL, corner_radius=5, padx=8, pady=2).pack(side="right", padx=20)

    def _build_body(self) -> None:
        self._body = ctk.CTkFrame(self, fg_color="transparent")
        self._body.pack(fill="both", expand=True)

        self._setup_frame = ctk.CTkFrame(self._body, fg_color="transparent")
        self._progress_frame = ctk.CTkFrame(self._body, fg_color="transparent")
        self._done_frame = ctk.CTkFrame(self._body, fg_color="transparent")

        self._build_setup_page()
        self._build_progress_page()
        self._build_done_page()

    def _show_page(self, name: str) -> None:
        for f in (self._setup_frame, self._progress_frame, self._done_frame):
            f.pack_forget()
        {"setup": self._setup_frame, "progress": self._progress_frame, "done": self._done_frame}[name].pack(
            fill="both", expand=True, padx=20, pady=(14, 0)
        )

    def _build_setup_page(self) -> None:
        p = self._setup_frame
        setup_scroll = ctk.CTkScrollableFrame(p, fg_color="transparent", corner_radius=0)
        setup_scroll.pack(fill="both", expand=True)
        content = setup_scroll

        hrow = ctk.CTkFrame(content, fg_color="transparent")
        hrow.pack(fill="x")
        ctk.CTkLabel(hrow, text="Prerequisites", font=FONT_BOLD, text_color=TEXT).pack(side="left")
        self._summary_lbl = ctk.CTkLabel(hrow, text="", font=FONT_SMALL, text_color=TEXT_DIM)
        self._summary_lbl.pack(side="left", padx=(10, 0))
        self._refresh_btn = ctk.CTkButton(
            hrow,
            text="↻  Refresh",
            width=96,
            height=28,
            fg_color=PANEL,
            hover_color=PANEL_ALT,
            text_color=ACCENT,
            font=FONT_SMALL,
            corner_radius=6,
            border_width=1,
            border_color=BORDER,
            command=self._on_refresh,
        )
        self._refresh_btn.pack(side="right")

        card = ctk.CTkFrame(content, fg_color=PANEL, corner_radius=10, border_width=1, border_color=BORDER)
        card.pack(fill="x", pady=(8, 0))
        self._prereq_rows: list[dict] = []
        for i, prereq in enumerate(PREREQS):
            self._prereq_rows.append(_make_prereq_row(card, prereq, i, last=(i == len(PREREQS) - 1)))

        ctk.CTkLabel(content, text="Install Source", font=FONT_BOLD, text_color=TEXT).pack(anchor="w", pady=(14, 0))
        source_card = ctk.CTkFrame(content, fg_color=PANEL, corner_radius=10, border_width=1, border_color=BORDER)
        source_card.pack(fill="x", pady=(6, 0))

        ctk.CTkSwitch(
            source_card,
            text="Beta (install from main branch)",
            variable=self._opt_beta,
            progress_color=ACCENT,
            button_color=ACCENT_HI,
            text_color=TEXT,
            command=self._update_source_labels,
        ).pack(anchor="w", padx=12, pady=(10, 4))

        self._release_lbl = ctk.CTkLabel(source_card, textvariable=self._release_text, font=FONT_SMALL, text_color=TEXT_DIM)
        self._release_lbl.pack(anchor="w", padx=12, pady=(0, 10))

        ctk.CTkLabel(content, text="Install Options", font=FONT_BOLD, text_color=TEXT).pack(anchor="w", pady=(14, 0))
        opt_card = ctk.CTkFrame(content, fg_color=PANEL, corner_radius=10, border_width=1, border_color=BORDER)
        opt_card.pack(fill="x", pady=(6, 0))

        self._add_option_switch(opt_card, "Apply theme setup after download", self._opt_apply_theme)
        self._add_option_switch(opt_card, "Apply ExplorerPatcher profile (auto backup in ExplorerPatcher backup folder)", self._opt_apply_explorerpatcher)
        self._add_option_switch(opt_card, "Create startup shortcut (AutoHotkey autostart)", self._opt_autostart)
        self._add_option_switch(opt_card, "Set wallpaper to interlude_87", self._opt_interlude87)
        self._add_option_switch(opt_card, "Backup current configs (PowerToys/Rainmeter/Files/etc)", self._opt_backup_configs)
        self._add_option_switch(opt_card, "Set Windows accent color to RGB(50,67,50)", self._opt_set_accent)

        ctk.CTkLabel(content, text="Install Location", font=FONT_BOLD, text_color=TEXT).pack(anchor="w", pady=(14, 0))
        dir_row = ctk.CTkFrame(content, fg_color="transparent")
        dir_row.pack(fill="x", pady=(6, 0))
        self._dir_entry = ctk.CTkEntry(dir_row, textvariable=self._install_dir, font=FONT_BODY, height=36, corner_radius=6, fg_color=PANEL, border_color=BORDER, text_color=TEXT)
        self._dir_entry.pack(side="left", fill="x", expand=True)
        ctk.CTkButton(dir_row, text="📁", width=44, height=36, fg_color=PANEL, hover_color=PANEL_ALT, text_color=TEXT, font=("Segoe UI", 14), corner_radius=6, command=self._browse_dir).pack(side="left", padx=(6, 0))

    def _add_option_switch(self, parent: ctk.CTkFrame, label: str, variable: ctk.BooleanVar) -> None:
        ctk.CTkSwitch(
            parent,
            text=label,
            variable=variable,
            progress_color=ACCENT,
            button_color=ACCENT_HI,
            text_color=TEXT,
        ).pack(anchor="w", padx=12, pady=6)

    def _build_progress_page(self) -> None:
        p = self._progress_frame
        ctk.CTkLabel(p, text="Installing...", font=FONT_BOLD, text_color=TEXT).pack(anchor="w")
        self._progress_bar = ctk.CTkProgressBar(p, height=8, corner_radius=4, progress_color=ACCENT, fg_color=PANEL)
        self._progress_bar.pack(fill="x", pady=(10, 0))
        self._progress_bar.set(0)
        self._pct_lbl = ctk.CTkLabel(p, text="0%", font=FONT_SMALL, text_color=TEXT_DIM)
        self._pct_lbl.pack(anchor="e", pady=(2, 0))
        self._log_box = ctk.CTkTextbox(p, height=320, fg_color=PANEL_DARK, text_color=TEXT_DIM, font=FONT_MONO, corner_radius=8, border_width=1, border_color=BORDER)
        self._log_box.pack(fill="both", expand=True, pady=(8, 0))
        self._log_box.configure(state="disabled")

    def _build_done_page(self) -> None:
        p = self._done_frame
        ctk.CTkLabel(p, text="✓", font=("Segoe UI", 64), text_color=GREEN).pack(pady=(40, 4))
        ctk.CTkLabel(p, text="Dino Themes installed!", font=FONT_TITLE, text_color=TEXT).pack()
        ctk.CTkLabel(
            p,
            text="Install completed with your selected options.",
            font=FONT_BODY,
            text_color=TEXT_DIM,
            justify="center",
        ).pack(pady=(12, 0))

    def _build_footer(self) -> None:
        ctk.CTkFrame(self, fg_color=BORDER, height=1, corner_radius=0).pack(fill="x", side="bottom")
        footer = ctk.CTkFrame(self, fg_color=PANEL_DARK, corner_radius=0, height=64)
        footer.pack(fill="x", side="bottom")
        footer.pack_propagate(False)

        self._warning_lbl = ctk.CTkLabel(footer, text="", font=FONT_SMALL, text_color=WARNING_COL, wraplength=540, justify="left", anchor="w")
        self._warning_lbl.pack(side="left", padx=(20, 0), fill="x", expand=True)

        self._btn_frame = ctk.CTkFrame(footer, fg_color="transparent")
        self._btn_frame.pack(side="right", padx=(0, 20))
        self._continue_btn = ctk.CTkButton(self._btn_frame, text="Continue Anyway", width=140, height=36, fg_color="transparent", hover_color="#2A1820", text_color=WARNING_COL, font=FONT_BODY, border_width=1, border_color=WARNING_COL, corner_radius=6, command=self._on_install)
        self._install_btn = ctk.CTkButton(self._btn_frame, text="⬇  Install", width=120, height=36, fg_color=ACCENT, hover_color=ACCENT_HI, text_color="#FFFFFF", font=FONT_BOLD, corner_radius=6, command=self._on_install)
        self._cancel_btn = ctk.CTkButton(self._btn_frame, text="✕  Cancel", width=110, height=36, fg_color=PANEL, hover_color="#3A1515", text_color=TEXT_DIM, font=FONT_BODY, corner_radius=6, command=self._on_cancel)
        self._done_btn = ctk.CTkButton(self._btn_frame, text="Close  ✓", width=110, height=36, fg_color=GREEN, hover_color="#3DBF77", text_color="#FFFFFF", font=FONT_BOLD, corner_radius=6, command=self.destroy)
        self._set_footer_state("checking")

        if not self._is_win11:
            self._warning_lbl.configure(text="Windows 11 only. This installer is disabled on non-Windows 11 systems.", text_color=RED)
            self._set_footer_state("unsupported")

    def _set_footer_state(self, state: str) -> None:
        for btn in (self._continue_btn, self._install_btn, self._cancel_btn, self._done_btn):
            btn.pack_forget()
        if state == "checking":
            self._install_btn.configure(state="disabled")
            self._install_btn.pack(side="left", padx=(8, 0))
        elif state == "ready":
            self._install_btn.configure(state="normal")
            self._install_btn.pack(side="left", padx=(8, 0))
        elif state == "warn":
            self._install_btn.configure(state="normal")
            self._continue_btn.pack(side="left", padx=(8, 0))
            self._install_btn.pack(side="left", padx=(8, 0))
        elif state == "installing":
            self._cancel_btn.pack(side="left", padx=(8, 0))
        elif state == "done":
            self._done_btn.pack(side="left", padx=(8, 0))
        elif state == "error":
            self._install_btn.configure(state="normal")
            self._install_btn.pack(side="left", padx=(8, 0))
        elif state == "unsupported":
            self._install_btn.configure(state="disabled")
            self._install_btn.pack(side="left", padx=(8, 0))

    def _fetch_release_text(self) -> None:
        info = get_latest_release_info()
        if info:
            self.after(0, lambda: self._release_text.set(f"Stable mode installs latest release: {info['tag']}"))
        else:
            self.after(0, lambda: self._release_text.set("Stable mode uses latest release when available; fallback is main."))

    def _update_source_labels(self) -> None:
        if self._opt_beta.get():
            self._release_lbl.configure(text_color=WARNING_COL)
            self._release_text.set("Beta mode: installs from main branch (latest commits).")
        else:
            self._release_lbl.configure(text_color=TEXT_DIM)
            threading.Thread(target=self._fetch_release_text, daemon=True).start()

    def _async_check_prereqs(self) -> None:
        self._refresh_btn.configure(state="disabled", text="Checking...")
        for row in self._prereq_rows:
            row["dot"].configure(text_color=TEXT_DIM)
            row["status_var"].set("Checking...")
            row["status_lbl"].configure(text_color=TEXT_DIM)
        if self._install_supported:
            self._set_footer_state("checking")
        threading.Thread(target=self._run_check_prereqs, daemon=True).start()

    def _run_check_prereqs(self) -> None:
        refresh_all()
        self.after(0, self._apply_prereq_results)

    def _apply_prereq_results(self) -> None:
        installed_count = 0
        for prereq, row in zip(PREREQS, self._prereq_rows):
            if prereq.installed:
                installed_count += 1
                row["dot"].configure(text_color=GREEN)
                row["status_var"].set("✓  Installed")
                row["status_lbl"].configure(text_color=GREEN)
            else:
                row["dot"].configure(text_color=RED)
                row["status_var"].set("✗  Not found")
                row["status_lbl"].configure(text_color=RED)

        total = len(PREREQS)
        colour = GREEN if installed_count == total else (WARNING_COL if installed_count >= total - 2 else RED)
        self._summary_lbl.configure(text=f"{installed_count}/{total} installed", text_color=colour)
        self._refresh_btn.configure(state="normal", text="↻  Refresh")

        if not self._is_win11:
            return

        missing = [p.name for p in PREREQS if not p.installed]
        if not missing:
            self._warning_lbl.configure(text="All prerequisites installed. Ready to go!", text_color=GREEN)
            self._set_footer_state("ready")
        else:
            self._warning_lbl.configure(
                text=f"⚠ Missing: {', '.join(missing)}. Continue is allowed (links are provided above).",
                text_color=WARNING_COL,
            )
            self._set_footer_state("warn")

    def _on_refresh(self) -> None:
        self._summary_lbl.configure(text="")
        if self._is_win11:
            self._warning_lbl.configure(text="")
        self._async_check_prereqs()

    def _browse_dir(self) -> None:
        chosen = filedialog.askdirectory(title="Choose Install Location", initialdir=self._install_dir.get())
        if chosen:
            self._install_dir.set(chosen)

    def _collect_options(self) -> dict:
        return {
            "source_mode": "beta" if self._opt_beta.get() else "stable",
            "apply_theme": self._opt_apply_theme.get(),
            "apply_explorerpatcher": self._opt_apply_explorerpatcher.get(),
            "autostart": self._opt_autostart.get(),
            "interlude87": self._opt_interlude87.get(),
            "backup_configs": self._opt_backup_configs.get(),
            "set_accent_color": self._opt_set_accent.get(),
        }

    def _on_install(self) -> None:
        if not self._is_win11:
            self._warning_lbl.configure(text="Windows 11 only. Install blocked.", text_color=RED)
            return

        dest = self._install_dir.get().strip()
        if not dest:
            self._warning_lbl.configure(text="Please choose an install directory.", text_color=RED)
            return

        overwrite = False
        dest_path = Path(dest)
        if dest_path.exists():
            if (dest_path / ".git").exists() and not is_already_installed(dest):
                self._warning_lbl.configure(
                    text="Selected folder is an existing git repository. Choose a different install location.",
                    text_color=RED,
                )
                return
            if is_already_installed(dest):
                if not messagebox.askyesno("Reinstall?", f"Dino Themes is already installed in:\n{dest}\n\nReinstall?", parent=self):
                    return
                overwrite = True
            elif any(dest_path.iterdir()):
                if not messagebox.askyesno("Directory not empty", f"'{dest}' already contains files.\nOverwrite them?", parent=self):
                    return
                overwrite = True

        self._cancel_event.clear()
        self._show_page("progress")
        self._set_footer_state("installing")
        self._warning_lbl.configure(text="Installation in progress...", text_color=TEXT_DIM)
        self._log_append("Starting installation...")

        options = self._collect_options()
        threading.Thread(target=self._run_install, args=(dest, overwrite, options), daemon=True).start()

    def _run_install(self, dest: str, overwrite: bool, options: dict) -> None:
        def cb(msg: str, pct: float) -> None:
            self.after(0, lambda m=msg, p=pct: self._update_progress(m, p))

        try:
            clone_repo(
                dest,
                overwrite=overwrite,
                source_mode=options["source_mode"],
                progress_cb=cb,
                cancel_event=self._cancel_event,
            )
            if options.get("apply_theme"):
                cb("Applying theme setup with selected options...", 0.92)
                run_theme_apply_script(dest, options, log_cb=lambda line: cb(line, -1))
            self.after(0, self._on_install_done)
        except InterruptedError:
            self.after(0, lambda: self._on_install_error("Installation cancelled."))
        except Exception as exc:
            self.after(0, lambda e=str(exc): self._on_install_error(e))

    def _update_progress(self, msg: str, pct: float) -> None:
        if pct >= 0:
            self._progress_bar.set(min(max(pct, 0), 1))
            self._pct_lbl.configure(text=f"{int(min(max(pct, 0), 1) * 100)}%")
        if msg:
            self._log_append(msg)

    def _log_append(self, text: str) -> None:
        self._log_box.configure(state="normal")
        self._log_box.insert("end", f"> {text}\n")
        self._log_box.see("end")
        self._log_box.configure(state="disabled")

    def _on_install_done(self) -> None:
        self._progress_bar.set(1.0)
        self._pct_lbl.configure(text="100%")
        self._log_append("Done!")
        self._show_page("done")
        self._warning_lbl.configure(text="Dino Themes installed successfully.", text_color=GREEN)
        self._set_footer_state("done")

    def _on_install_error(self, msg: str) -> None:
        self._progress_bar.set(0)
        self._log_append(f"Error: {msg}")
        self._warning_lbl.configure(text=f"✗ {msg}", text_color=RED)
        self._set_footer_state("error")

    def _on_cancel(self) -> None:
        self._cancel_event.set()
        self._log_append("Cancelling, please wait...")
        self._cancel_btn.configure(state="disabled")


def _make_prereq_row(parent: ctk.CTkFrame, prereq: Prereq, idx: int, last: bool) -> dict:
    bg = PANEL if idx % 2 == 0 else PANEL_ALT
    row = ctk.CTkFrame(parent, fg_color=bg, corner_radius=0, height=44)
    row.pack(fill="x")
    row.pack_propagate(False)
    if not last:
        ctk.CTkFrame(row, fg_color=BORDER, height=1, corner_radius=0).pack(side="bottom", fill="x")

    dot = ctk.CTkLabel(row, text="●", text_color=TEXT_DIM, font=("Segoe UI", 14), width=22)
    dot.pack(side="left", padx=(14, 0))
    ctk.CTkLabel(row, text=prereq.name, font=("Segoe UI Variable", 12, "bold"), text_color=TEXT, width=140, anchor="w").pack(side="left", padx=(8, 0))
    ctk.CTkLabel(row, text=prereq.description, font=FONT_SMALL, text_color=TEXT_DIM, width=158, anchor="w").pack(side="left", padx=(4, 0))

    status_var = ctk.StringVar(value="-")
    status_lbl = ctk.CTkLabel(row, textvariable=status_var, font=FONT_SMALL, text_color=TEXT_DIM, width=108, anchor="w")
    status_lbl.pack(side="left", padx=(4, 0))

    links = ctk.CTkFrame(row, fg_color="transparent")
    links.pack(side="right", padx=(0, 12))
    ctk.CTkButton(
        links,
        text="↗ Website",
        width=80,
        height=26,
        fg_color="transparent",
        hover_color=PANEL_ALT,
        text_color=ACCENT,
        font=FONT_SMALL,
        border_width=1,
        border_color=BORDER,
        corner_radius=5,
        command=lambda u=prereq.website: webbrowser.open(u),
    ).pack(side="left", padx=(0, 5))
    ctk.CTkButton(
        links,
        text="⑂ GitHub",
        width=76,
        height=26,
        fg_color="transparent",
        hover_color=PANEL_ALT,
        text_color=TEXT_DIM,
        font=FONT_SMALL,
        border_width=1,
        border_color=BORDER,
        corner_radius=5,
        command=lambda u=prereq.github: webbrowser.open(u),
    ).pack(side="left")
    return {"dot": dot, "status_var": status_var, "status_lbl": status_lbl}


def run_silent(args: argparse.Namespace) -> int:
    if not is_windows_11():
        print("ERROR: Windows 11 only.")
        return 2

    dest = args.dest or str(Path.home() / "DinoThemes")
    options = {
        "source_mode": "beta" if args.beta else "stable",
        "apply_theme": args.apply_theme,
        "apply_explorerpatcher": args.apply_explorerpatcher,
        "autostart": args.autostart,
        "interlude87": args.interlude87,
        "backup_configs": args.backup_configs,
        "set_accent_color": args.set_accent_color,
    }

    def cb(msg: str, pct: float) -> None:
        if pct >= 0:
            print(f"[{int(min(max(pct, 0), 1) * 100):3d}%] {msg}")
        else:
            print(msg)

    overwrite = args.yes
    try:
        clone_repo(dest, overwrite=overwrite, source_mode=options["source_mode"], progress_cb=cb)
        if options["apply_theme"]:
            cb("Applying theme setup with selected options...", -1)
            run_theme_apply_script(dest, options, log_cb=print)
        print("Installation complete.")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}")
        return 1


def build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Dino Themes installer")
    p.add_argument("--silent", action="store_true", help="Run without GUI")
    p.add_argument("--dest", help="Install directory")
    p.add_argument("--yes", action="store_true", help="Overwrite existing destination in silent mode")
    p.add_argument("--beta", action="store_true", help="Install from main branch (beta)")
    p.add_argument("--apply-theme", action="store_true", default=True, help="Apply theme setup after download")
    p.add_argument("--no-apply-theme", dest="apply_theme", action="store_false", help="Skip theme setup script")
    p.add_argument("--apply-explorerpatcher", action="store_true", help="Apply ExplorerPatcher profile")
    p.add_argument("--autostart", action="store_true", help="Create AutoHotkey startup shortcut")
    p.add_argument("--interlude87", action="store_true", help="Set wallpaper to interlude_87")
    p.add_argument("--backup-configs", action="store_true", default=True, help="Backup current app configs")
    p.add_argument("--no-backup-configs", dest="backup_configs", action="store_false", help="Skip backup")
    p.add_argument("--set-accent-color", action="store_true", help="Set Windows accent RGB(50,67,50)")
    return p


def main() -> None:
    parser = build_arg_parser()
    args = parser.parse_args()
    if args.silent:
        raise SystemExit(run_silent(args))
    app = DinoInstaller()
    app.mainloop()


if __name__ == "__main__":
    main()
