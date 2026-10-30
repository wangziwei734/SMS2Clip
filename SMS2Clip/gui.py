"""Tkinter desktop application for the SMS2Clip bridge."""

from __future__ import annotations

import argparse
import ctypes
import os
import secrets
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path
import tkinter as tk
from tkinter import messagebox, ttk

from .config import Config
from .extractor import extract_verification_code
from .history import HistoryStore
from .i18n import LANG_EN, LANG_ZH, normalize_language, tr
from .ntfy_client import publish_message
from .paths import default_config_path, is_frozen, resource_path
from .single_instance import ManagerInstance
from .runtime import (
    build_service_command,
    build_service_environment,
    pid_file_path,
    process_is_running,
    read_pid,
    terminate_process,
)
from .startup import (
    build_startup_command,
    disable_startup,
    enable_startup,
    get_startup_mode,
)

try:
    import pystray
    from PIL import Image, ImageTk
except ImportError:  # pragma: no cover - the packaged build includes pystray
    pystray = None
    Image = None
    ImageTk = None

try:
    import qrcode
except ImportError:  # pragma: no cover - the packaged build includes qrcode
    qrcode = None

APP_NAME = "SMS2Clip"
ICLOUD_SHORTCUT_URL = (
    "https://www.icloud.com/shortcuts/2e72a660dec84fd9b8c7abd92d42043f"
)
BG = "#F3F5F7"
CARD = "#FFFFFF"
NAVY = "#101828"
TEAL = "#0F766E"
TEAL_DARK = "#0B5F59"
GREEN = "#12B76A"
GREEN_BG = "#D1FADF"
GREEN_TEXT = "#027A48"
RED = "#D92D20"
RED_BG = "#FEE4E2"
RED_TEXT = "#B42318"
AMBER_BG = "#FEF0C7"
AMBER_TEXT = "#B54708"
MUTED = "#667085"
BORDER = "#E4E7EC"
SOFT = "#F9FAFB"


def gui_executable() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve()
    candidate = Path(sys.executable).with_name("pythonw.exe")
    return candidate if candidate.exists() else Path(sys.executable).resolve()


def _set_dpi_awareness() -> None:
    if sys.platform != "win32":
        return
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


class SMS2ClipApp(tk.Tk):
    def __init__(self, config_path: Path, minimized: bool = False) -> None:
        super().__init__()
        self.config_path = config_path.resolve()
        self.minimized = minimized
        self.settings: Config | None = None
        self.language = LANG_ZH
        self.auto_copy_code = True
        self.startup_mode = get_startup_mode()
        self.tray_icon = None
        self.child_process: subprocess.Popen | None = None
        self._status_kind = "stopped"
        self._status_job = None
        self._log_job = None
        self._history_job = None
        self._log_signature: tuple[int, int] | None = None
        self._history_signature: tuple[int, int] | None = None
        self._history_records: list[dict] = []
        self.history_store = HistoryStore(self.config_path.parent / "history.json")
        self._advanced_username = ""
        self._advanced_password = ""
        self._advanced_since = ""
        self._advanced_gap = "350"

        self.title(APP_NAME)
        self.geometry("920x740")
        self.minsize(900, 700)
        self.configure(bg=BG)
        self.option_add("*Font", "微软雅黑 10")
        icon = resource_path("assets/sms2clip.ico")
        if icon.exists():
            try:
                self.iconbitmap(str(icon))
            except tk.TclError:
                pass

        self.server_var = tk.StringVar(value="https://ntfy.sh")
        self.topic_var = tk.StringVar()
        self.token_var = tk.StringVar()
        self.publish_url_var = tk.StringVar()
        self.startup_mode_var = tk.StringVar()
        self.startup_hint_var = tk.StringVar()
        self.auto_copy_code_var = tk.BooleanVar(value=True)
        self.status_title_var = tk.StringVar(value=self._t("status.stopped"))
        self.status_detail_var = tk.StringVar(value=self._t("status.stopped_detail"))
        self.test_input: tk.Text | None = None
        self.test_result_var = tk.StringVar(value=self._t("test.no_result"))
        self.log_text: tk.Text | None = None
        self.history_tree: ttk.Treeview | None = None
        self.history_detail: tk.Text | None = None
        self.history_copy_button: ttk.Button | None = None
        self.history_count_var = tk.StringVar()
        self.history_status_var = tk.StringVar()

        self._build_styles()
        self._load_config()
        self._build_ui()
        self._fit_window()
        self._update_publish_url()
        self._refresh_history(force=True)
        self._start_tray()

        self.server_var.trace_add("write", lambda *_: self._update_publish_url())
        self.topic_var.trace_add("write", lambda *_: self._update_publish_url())

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(500, self._poll_status)
        self.after(1000, self._poll_log)
        self.after(1200, self._poll_history)
        self.after(600, self._auto_start_if_needed)
        if minimized:
            self.after(250, self._hide_to_tray)

    def _fit_window(self) -> None:
        self.update_idletasks()
        current_width = max(self.winfo_width(), 920)
        current_height = max(self.winfo_height(), 740)
        required_width = max(current_width, self.winfo_reqwidth() + 20)
        required_height = max(current_height, self.winfo_reqheight() + 20)
        width = min(required_width, max(900, self.winfo_screenwidth() - 80))
        height = min(required_height, max(700, self.winfo_screenheight() - 60))
        self.geometry(f"{width}x{height}")

    def _build_styles(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure(
            "Primary.TButton",
            background=TEAL,
            foreground="#FFFFFF",
            borderwidth=0,
            focusthickness=0,
            padding=(16, 8),
            font=("微软雅黑", 10, "bold"),
        )
        style.map(
            "Primary.TButton",
            background=[("active", TEAL_DARK), ("disabled", "#98A2B3")],
            foreground=[("disabled", "#F2F4F7")],
        )
        style.configure(
            "Secondary.TButton",
            background=CARD,
            foreground=NAVY,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            borderwidth=1,
            relief="solid",
            padding=(12, 7),
            font=("微软雅黑", 10),
        )
        style.map(
            "Secondary.TButton",
            background=[("active", "#F2F4F7"), ("disabled", "#F9FAFB")],
            foreground=[("disabled", "#98A2B3")],
        )
        style.configure(
            "Header.TButton",
            background="#1D2939",
            foreground="#FFFFFF",
            bordercolor="#344054",
            lightcolor="#344054",
            darkcolor="#344054",
            borderwidth=1,
            padding=(12, 6),
            font=("微软雅黑", 9),
        )
        style.map(
            "Header.TButton",
            background=[("active", "#344054"), ("disabled", "#1D2939")],
        )
        style.configure(
            "Danger.TButton",
            background=RED_BG,
            foreground=RED_TEXT,
            bordercolor="#FECDCA",
            lightcolor="#FECDCA",
            darkcolor="#FECDCA",
            borderwidth=1,
            padding=(12, 7),
            font=("微软雅黑", 10),
        )
        style.map(
            "Danger.TButton",
            background=[("active", "#FEE4E2"), ("disabled", "#F9FAFB")],
            foreground=[("disabled", "#98A2B3")],
        )
        style.configure(
            "Field.TEntry",
            fieldbackground=SOFT,
            foreground=NAVY,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=8,
        )
        style.map(
            "Field.TEntry",
            fieldbackground=[("readonly", "#F2F4F7")],
            foreground=[("readonly", MUTED)],
        )
        style.configure(
            "Field.TCombobox",
            fieldbackground=SOFT,
            foreground=NAVY,
            background=CARD,
            bordercolor=BORDER,
            lightcolor=BORDER,
            darkcolor=BORDER,
            padding=7,
        )
        style.map(
            "Field.TCombobox",
            fieldbackground=[("readonly", SOFT)],
            foreground=[("readonly", NAVY)],
        )
        style.configure(
            "TCheckbutton",
            background=CARD,
            foreground=NAVY,
            font=("微软雅黑", 10),
        )
        style.map("TCheckbutton", background=[("active", CARD)])
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure(
            "TNotebook.Tab",
            background="#E4E7EC",
            foreground=MUTED,
            padding=(16, 7),
            font=("微软雅黑", 9, "bold"),
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", CARD), ("active", "#EAECF0")],
            foreground=[("selected", TEAL)],
        )
        style.configure(
            "History.Treeview",
            background=CARD,
            fieldbackground=CARD,
            foreground=NAVY,
            borderwidth=0,
            rowheight=30,
            font=("微软雅黑", 9),
        )
        style.configure(
            "History.Treeview.Heading",
            background=SOFT,
            foreground=NAVY,
            font=("微软雅黑", 9, "bold"),
        )
        style.map(
            "History.Treeview",
            background=[("selected", TEAL)],
            foreground=[("selected", "#FFFFFF")],
        )

    def _card(self, parent: tk.Misc) -> tk.Frame:
        return tk.Frame(
            parent,
            bg=CARD,
            bd=0,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=BORDER,
        )

    def _card_title(self, parent: tk.Misc, title: str, subtitle: str = "") -> None:
        tk.Label(
            parent,
            text=title,
            bg=CARD,
            fg=NAVY,
            font=("微软雅黑", 13, "bold"),
            anchor="w",
        ).pack(fill="x")
        if subtitle:
            tk.Label(
                parent,
                text=subtitle,
                bg=CARD,
                fg=MUTED,
                font=("微软雅黑", 9),
                anchor="w",
                justify="left",
                wraplength=260,
            ).pack(fill="x", pady=(4, 0))

    def _field(
        self,
        parent: tk.Misc,
        row: int,
        label: str,
        variable: tk.StringVar,
        *,
        show: str | None = None,
    ) -> ttk.Entry:
        tk.Label(
            parent,
            text=label,
            bg=CARD,
            fg=NAVY,
            font=("微软雅黑", 9, "bold"),
            anchor="w",
        ).grid(row=row, column=0, sticky="w", pady=(10, 4))
        entry = ttk.Entry(
            parent,
            textvariable=variable,
            style="Field.TEntry",
            show=show or "",
        )
        entry.grid(row=row + 1, column=0, sticky="ew", pady=(0, 0))
        return entry

    def _t(self, key: str, **values: object) -> str:
        return tr(self.language, key, **values)

    def _toggle_language(self) -> None:
        self.language = LANG_EN if self.language == LANG_ZH else LANG_ZH
        saved = True
        if self.config_path.exists():
            try:
                self._save_settings()
            except Exception:
                saved = False
        self._rebuild_ui()
        if saved:
            self._restart_service_if_running()

    def _rebuild_ui(self) -> None:
        selected = 0
        if hasattr(self, "notebook"):
            try:
                selected = self.notebook.index(self.notebook.select())
            except tk.TclError:
                selected = 0
        for child in self.winfo_children():
            child.destroy()
        self._build_ui()
        self._fit_window()
        self._update_publish_url()
        if hasattr(self, "notebook") and selected:
            self.notebook.select(selected)
        self._log_signature = None
        self._history_signature = None
        self._refresh_history(force=True)
        self._update_status()
        self._update_tray_menu()

    def _build_tray_menu(self):
        if pystray is None:
            return None
        return pystray.Menu(
            pystray.MenuItem(
                self._t("tray.open"),
                lambda icon, item: self.after(0, self._show_window),
                default=True,
            ),
            pystray.MenuItem(
                self._t("tray.start"),
                lambda icon, item: self.after(0, self._start_service),
            ),
            pystray.MenuItem(
                self._t("tray.stop"),
                lambda icon, item: self.after(0, self._stop_service),
            ),
            pystray.Menu.SEPARATOR,
            pystray.MenuItem(
                self._t("tray.exit"),
                lambda icon, item: self.after(0, self._exit_app),
            ),
        )

    def _start_tray(self) -> None:
        if pystray is None or Image is None:
            return
        icon_path = resource_path("assets/sms2clip.png")
        if not icon_path.exists():
            return
        try:
            image = Image.open(icon_path).convert("RGBA")
            self.tray_icon = pystray.Icon(
                "sms2clip",
                image,
                self._t("tray.tooltip"),
                self._build_tray_menu(),
            )
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
        except Exception:
            self.tray_icon = None

    def _update_tray_menu(self) -> None:
        if self.tray_icon is None:
            return
        try:
            self.tray_icon.menu = self._build_tray_menu()
            self.tray_icon.title = self._t("tray.tooltip")
            self.tray_icon.update_menu()
        except Exception:
            pass

    def _show_window(self) -> None:
        self.deiconify()
        self.lift()
        self.focus_force()
        self.attributes("-topmost", True)
        self.after(200, lambda: self.attributes("-topmost", False))

    def _hide_to_tray(self) -> None:
        if self.tray_icon is not None:
            self.withdraw()
        else:
            self.iconify()

    def _exit_app(self) -> None:
        if self.startup_mode != "service":
            self._stop_service()
        if self.tray_icon is not None:
            try:
                self.tray_icon.stop()
            except Exception:
                pass
            self.tray_icon = None
        self.destroy()

    def _build_ui(self) -> None:
        header = tk.Frame(self, bg=NAVY, height=108)
        header.pack(fill="x")
        header.pack_propagate(False)

        header_inner = tk.Frame(header, bg=NAVY)
        header_inner.pack(fill="both", expand=True, padx=28, pady=14)
        title_box = tk.Frame(header_inner, bg=NAVY)
        title_box.pack(side="left", fill="y")
        tk.Label(
            title_box,
            text=APP_NAME,
            bg=NAVY,
            fg="#FFFFFF",
            font=("微软雅黑", 22, "bold"),
            anchor="w",
        ).pack(anchor="w")
        tk.Label(
            title_box,
            text=self._t("app.subtitle"),
            bg=NAVY,
            fg="#D0D5DD",
            font=("微软雅黑", 10),
            anchor="w",
        ).pack(anchor="w", pady=(5, 0))

        header_right = tk.Frame(header_inner, bg=NAVY)
        header_right.pack(side="right", fill="y")
        self.status_pill = tk.Label(
            header_right,
            text=self._t("status.stopped"),
            bg="#344054",
            fg="#D0D5DD",
            padx=14,
            pady=5,
            font=("微软雅黑", 9, "bold"),
        )
        self.status_pill.pack(side="top", anchor="e")
        header_actions = tk.Frame(header_right, bg=NAVY)
        header_actions.pack(side="top", anchor="e", pady=(6, 0))
        ttk.Button(
            header_actions,
            text=self._t("button.help"),
            style="Header.TButton",
            command=self._open_help,
        ).pack(side="left")
        ttk.Button(
            header_actions,
            text=self._t("button.shortcut"),
            style="Header.TButton",
            command=self._open_shortcut_qr,
        ).pack(side="left", padx=(6, 0))
        language_key = (
            "button.language_to_en"
            if self.language == LANG_ZH
            else "button.language_to_zh"
        )
        ttk.Button(
            header_actions,
            text=self._t(language_key),
            style="Header.TButton",
            command=self._toggle_language,
        ).pack(side="left", padx=(6, 0))

        notebook = ttk.Notebook(self)
        notebook.pack(fill="both", expand=True, padx=18, pady=(12, 14))
        self.notebook = notebook
        connection_tab = tk.Frame(notebook, bg=BG)
        tools_tab = tk.Frame(notebook, bg=BG)
        history_tab = tk.Frame(notebook, bg=BG)
        notebook.add(connection_tab, text=f"  {self._t('tab.connection')}  ")
        notebook.add(tools_tab, text=f"  {self._t('tab.tools')}  ")
        notebook.add(history_tab, text=f"  {self._t('tab.history')}  ")
        content_viewport = tk.Frame(connection_tab, bg=BG)
        content_viewport.pack(fill="both", expand=True)
        content_viewport.grid_rowconfigure(0, weight=1)
        content_viewport.grid_columnconfigure(0, weight=1)
        self.connection_canvas = tk.Canvas(
            content_viewport,
            bg=BG,
            bd=0,
            highlightthickness=0,
        )
        self.connection_canvas.grid(row=0, column=0, sticky="nsew")
        self.connection_scrollbar = ttk.Scrollbar(
            content_viewport,
            orient="vertical",
            command=self.connection_canvas.yview,
        )
        self.connection_scrollbar.grid(row=0, column=1, sticky="ns", padx=(0, 4))
        self.connection_scrollbar.grid_remove()
        self.connection_canvas.configure(yscrollcommand=self.connection_scrollbar.set)

        content = tk.Frame(self.connection_canvas, bg=BG)
        content_window = self.connection_canvas.create_window(
            (10, 10), window=content, anchor="nw"
        )
        content.bind(
            "<Configure>",
            lambda _event: self._update_connection_scrollbar(),
        )

        def resize_content(event) -> None:
            self.connection_canvas.itemconfigure(
                content_window, width=max(1, event.width - 20)
            )
            self._update_connection_scrollbar()

        self.connection_canvas.bind("<Configure>", resize_content)
        content.grid_columnconfigure(0, weight=1, uniform="main")
        content.grid_columnconfigure(1, weight=1, uniform="main")
        content.grid_rowconfigure(0, weight=1)

        settings_card = self._card(content)
        settings_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        settings_inner = tk.Frame(settings_card, bg=CARD)
        settings_inner.pack(fill="both", expand=True, padx=16, pady=14)
        self._card_title(
            settings_inner,
            self._t("settings.title"),
            self._t("settings.subtitle"),
        )

        self.settings_toggle_button = ttk.Button(
            settings_inner,
            text=self._t("settings.show"),
            style="Secondary.TButton",
            command=self._toggle_connection_settings,
        )
        self.settings_toggle_button.pack(anchor="w", pady=(14, 0))
        self.settings_hidden_hint_label = tk.Label(
            settings_inner,
            text=self._t("settings.hidden_hint"),
            bg="#F0FDF9",
            fg="#0F766E",
            font=("微软雅黑", 9),
            justify="left",
            anchor="w",
            wraplength=420,
            padx=10,
            pady=8,
        )
        self.settings_hidden_hint_label.pack(fill="x", pady=(12, 0))

        self.connection_settings_content = tk.Frame(settings_inner, bg=CARD)
        form = tk.Frame(self.connection_settings_content, bg=CARD)
        form.pack(fill="x", pady=(2, 0))
        form.grid_columnconfigure(0, weight=1)
        self._field(form, 0, self._t("field.server"), self.server_var)

        tk.Label(
            form,
            text=self._t("field.topic"),
            bg=CARD,
            fg=NAVY,
            font=("微软雅黑", 9, "bold"),
            anchor="w",
        ).grid(row=2, column=0, sticky="w", pady=(10, 4))
        topic_row = tk.Frame(form, bg=CARD)
        topic_row.grid(row=3, column=0, sticky="ew")
        topic_row.grid_columnconfigure(0, weight=1)
        ttk.Entry(
            topic_row,
            textvariable=self.topic_var,
            style="Field.TEntry",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Button(
            topic_row,
            text=self._t("button.regenerate"),
            style="Secondary.TButton",
            command=self._regenerate_topic,
        ).grid(row=0, column=1, padx=(8, 0))

        self._field(form, 4, self._t("field.token"), self.token_var, show="•")

        tk.Label(
            form,
            text=self._t("field.publish_url"),
            bg=CARD,
            fg=NAVY,
            font=("微软雅黑", 9, "bold"),
            anchor="w",
        ).grid(row=6, column=0, sticky="w", pady=(10, 4))
        url_row = tk.Frame(form, bg=CARD)
        url_row.grid(row=7, column=0, sticky="ew")
        url_row.grid_columnconfigure(0, weight=1)
        ttk.Entry(
            url_row,
            textvariable=self.publish_url_var,
            style="Field.TEntry",
            state="readonly",
        ).grid(row=0, column=0, sticky="ew")
        ttk.Button(
            url_row,
            text=self._t("button.copy"),
            style="Secondary.TButton",
            command=self._copy_publish_url,
        ).grid(row=0, column=1, padx=(8, 0))

        hint = tk.Label(
            self.connection_settings_content,
            text=self._t("hint.security"),
            bg="#F0FDF9",
            fg="#0F766E",
            font=("微软雅黑", 9),
            justify="left",
            anchor="w",
            wraplength=420,
            padx=10,
            pady=8,
        )
        hint.pack(fill="x", pady=(12, 0))
        connection_actions = tk.Frame(self.connection_settings_content, bg=CARD)
        connection_actions.pack(anchor="w", pady=(10, 0))
        ttk.Button(
            connection_actions,
            text=self._t("button.save_connection"),
            style="Primary.TButton",
            command=self._save_connection_settings,
        ).pack(side="left")
        ttk.Button(
            connection_actions,
            text=self._t("button.advanced"),
            style="Secondary.TButton",
            command=self._open_advanced,
        ).pack(side="left", padx=(8, 0))
        self._bind_connection_mousewheel(self.connection_settings_content)

        actions_card = self._card(content)
        actions_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        actions_inner = tk.Frame(actions_card, bg=CARD)
        actions_inner.pack(fill="both", expand=True, padx=16, pady=14)
        self._card_title(
            actions_inner, self._t("status.title"), self._t("status.subtitle")
        )

        status_box = tk.Frame(
            actions_inner,
            bg=SOFT,
            highlightthickness=1,
            highlightbackground=BORDER,
        )
        status_box.pack(fill="x", pady=(14, 0))
        self.status_title_label = tk.Label(
            status_box,
            textvariable=self.status_title_var,
            bg=SOFT,
            fg=NAVY,
            font=("微软雅黑", 17, "bold"),
            anchor="w",
        )
        self.status_title_label.pack(fill="x", padx=16, pady=(12, 2))
        self.status_detail_label = tk.Label(
            status_box,
            textvariable=self.status_detail_var,
            bg=SOFT,
            fg=MUTED,
            font=("微软雅黑", 9),
            anchor="w",
            justify="left",
            wraplength=340,
        )
        self.status_detail_label.pack(fill="x", padx=16, pady=(0, 12))

        ttk.Checkbutton(
            actions_inner,
            text=self._t("checkbox.auto_copy_code"),
            variable=self.auto_copy_code_var,
            command=self._on_auto_copy_change,
        ).pack(anchor="w", pady=(14, 0))

        self.start_button = ttk.Button(
            actions_inner,
            text=self._t("button.start"),
            style="Primary.TButton",
            command=self._start_service,
        )
        self.start_button.pack(fill="x", pady=(14, 0))
        self.stop_button = ttk.Button(
            actions_inner,
            text=self._t("button.stop"),
            style="Danger.TButton",
            command=self._stop_service,
            state="disabled",
        )
        self.stop_button.pack(fill="x", pady=(6, 0))
        ttk.Button(
            actions_inner,
            text=self._t("button.test_sms"),
            style="Secondary.TButton",
            command=self._send_test,
        ).pack(fill="x", pady=(6, 0))

        ttk.Separator(actions_inner, orient="horizontal").pack(fill="x", pady=14)
        tk.Label(
            actions_inner,
            text=self._t("label.startup_mode"),
            bg=CARD,
            fg=NAVY,
            font=("微软雅黑", 9, "bold"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))
        self.startup_mode_combo = ttk.Combobox(
            actions_inner,
            textvariable=self.startup_mode_var,
            values=self._startup_mode_labels(),
            state="readonly",
            style="Field.TCombobox",
        )
        self.startup_mode_combo.pack(fill="x")
        self.startup_mode_combo.bind(
            "<<ComboboxSelected>>", self._on_startup_mode_change
        )
        self.startup_mode_var.set(self._startup_mode_label(self.startup_mode))
        self.startup_hint_var.set(self._startup_hint(self.startup_mode))
        tk.Label(
            actions_inner,
            textvariable=self.startup_hint_var,
            bg=CARD,
            fg=MUTED,
            font=("微软雅黑", 8),
            anchor="w",
            justify="left",
            wraplength=380,
        ).pack(fill="x", pady=(4, 0))
        ttk.Button(
            actions_inner,
            text=self._t("button.open_log"),
            style="Secondary.TButton",
            command=self._open_log,
        ).pack(fill="x", pady=(12, 0))
        ttk.Button(
            actions_inner,
            text=self._t("button.clipboard_settings"),
            style="Secondary.TButton",
            command=self._open_clipboard_settings,
        ).pack(fill="x", pady=(6, 0))
        ttk.Button(
            actions_inner,
            text=self._t("button.config_folder"),
            style="Secondary.TButton",
            command=self._open_config_folder,
        ).pack(fill="x", pady=(6, 0))

        bottom = tk.Frame(tools_tab, bg=BG)
        bottom.pack(fill="both", expand=True, padx=12, pady=12)
        bottom.grid_columnconfigure(0, weight=1, uniform="bottom")
        bottom.grid_columnconfigure(1, weight=1, uniform="bottom")
        bottom.grid_rowconfigure(0, weight=1)

        test_card = self._card(bottom)
        test_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        test_inner = tk.Frame(test_card, bg=CARD)
        test_inner.pack(fill="both", expand=True, padx=16, pady=14)
        self._card_title(test_inner, self._t("test.title"), self._t("test.subtitle"))
        self.test_input = tk.Text(
            test_inner,
            height=5,
            width=40,
            bg=SOFT,
            fg=NAVY,
            insertbackground=NAVY,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=TEAL,
            padx=10,
            pady=8,
            font=("微软雅黑", 10),
            wrap="word",
        )
        self.test_input.pack(fill="both", expand=True, pady=(14, 8))
        self.test_input.insert("1.0", self._t("test.placeholder"))
        test_actions = tk.Frame(test_inner, bg=CARD)
        test_actions.pack(fill="x")
        ttk.Button(
            test_actions,
            text=self._t("button.recognize"),
            style="Primary.TButton",
            command=self._recognize_test,
        ).pack(side="left")
        tk.Label(
            test_actions,
            textvariable=self.test_result_var,
            bg=CARD,
            fg=MUTED,
            font=("微软雅黑", 9),
            anchor="w",
        ).pack(side="left", padx=(12, 0))

        log_card = self._card(bottom)
        log_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        log_inner = tk.Frame(log_card, bg=CARD)
        log_inner.pack(fill="both", expand=True, padx=16, pady=14)
        self._card_title(log_inner, self._t("log.title"), self._t("log.subtitle"))
        log_frame = tk.Frame(log_inner, bg=CARD)
        log_frame.pack(fill="both", expand=True, pady=(14, 0))
        log_frame.grid_rowconfigure(0, weight=1)
        log_frame.grid_columnconfigure(0, weight=1)
        self.log_text = tk.Text(
            log_frame,
            height=6,
            width=40,
            bg=SOFT,
            fg="#344054",
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=TEAL,
            padx=10,
            pady=8,
            font=("Consolas", 9),
            wrap="word",
            state="disabled",
        )
        self.log_text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_text.configure(yscrollcommand=scrollbar.set)

        self._build_history_tab(history_tab)

    def _build_history_tab(self, parent: tk.Misc) -> None:
        content = tk.Frame(parent, bg=BG)
        content.pack(fill="both", expand=True, padx=10, pady=10)
        content.grid_columnconfigure(0, weight=3, uniform="history")
        content.grid_columnconfigure(1, weight=5, uniform="history")
        content.grid_rowconfigure(0, weight=1)

        list_card = self._card(content)
        list_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        list_inner = tk.Frame(list_card, bg=CARD)
        list_inner.pack(fill="both", expand=True, padx=16, pady=14)
        self._card_title(
            list_inner,
            self._t("history.title"),
            self._t("history.subtitle"),
        )

        list_actions = tk.Frame(list_inner, bg=CARD)
        list_actions.pack(fill="x", pady=(12, 8))
        tk.Label(
            list_actions,
            textvariable=self.history_count_var,
            bg=CARD,
            fg=MUTED,
            font=("微软雅黑", 9),
            anchor="w",
        ).pack(side="left")
        ttk.Button(
            list_actions,
            text=self._t("button.clear_history"),
            style="Secondary.TButton",
            command=self._clear_history,
        ).pack(side="right")

        tree_frame = tk.Frame(list_inner, bg=CARD)
        tree_frame.pack(fill="both", expand=True)
        tree_frame.grid_rowconfigure(0, weight=1)
        tree_frame.grid_columnconfigure(0, weight=1)
        self.history_tree = ttk.Treeview(
            tree_frame,
            columns=("time", "message"),
            show="headings",
            style="History.Treeview",
            selectmode="browse",
        )
        self.history_tree.heading("time", text=self._t("history.time"))
        self.history_tree.heading("message", text=self._t("history.message"))
        self.history_tree.column("time", width=150, minwidth=145, stretch=False)
        self.history_tree.column("message", width=220, minwidth=120, stretch=True)
        self.history_tree.grid(row=0, column=0, sticky="nsew")
        history_scrollbar = ttk.Scrollbar(
            tree_frame, orient="vertical", command=self.history_tree.yview
        )
        history_scrollbar.grid(row=0, column=1, sticky="ns")
        self.history_tree.configure(yscrollcommand=history_scrollbar.set)
        self.history_tree.bind("<<TreeviewSelect>>", self._on_history_select)

        detail_card = self._card(content)
        detail_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        detail_inner = tk.Frame(detail_card, bg=CARD)
        detail_inner.pack(fill="both", expand=True, padx=16, pady=14)
        self._card_title(
            detail_inner,
            self._t("history.detail_title"),
            self._t("history.detail_subtitle"),
        )

        detail_frame = tk.Frame(detail_inner, bg=CARD)
        detail_frame.pack(fill="both", expand=True, pady=(14, 10))
        detail_frame.grid_rowconfigure(0, weight=1)
        detail_frame.grid_columnconfigure(0, weight=1)
        self.history_detail = tk.Text(
            detail_frame,
            width=40,
            height=10,
            bg=SOFT,
            fg=NAVY,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=TEAL,
            padx=12,
            pady=10,
            font=("微软雅黑", 10),
            wrap="word",
            state="disabled",
        )
        self.history_detail.grid(row=0, column=0, sticky="nsew")
        detail_scrollbar = ttk.Scrollbar(
            detail_frame, orient="vertical", command=self.history_detail.yview
        )
        detail_scrollbar.grid(row=0, column=1, sticky="ns")
        self.history_detail.configure(yscrollcommand=detail_scrollbar.set)

        footer = tk.Frame(detail_inner, bg=CARD)
        footer.pack(fill="x")
        tk.Label(
            footer,
            textvariable=self.history_status_var,
            bg=CARD,
            fg=MUTED,
            font=("微软雅黑", 9),
            anchor="w",
        ).pack(side="left", fill="x", expand=True)
        self.history_copy_button = ttk.Button(
            footer,
            text=self._t("history.copy_code"),
            style="Primary.TButton",
            state="disabled",
            command=self._copy_history_code,
        )
        self.history_copy_button.pack(side="right")

    def _load_config(self) -> None:
        if not self.config_path.exists():
            self.topic_var.set(secrets.token_urlsafe(12))
            self._set_status("stopped", self._t("status.no_config"))
            return
        try:
            self.settings = Config.load(self.config_path)
            self.language = normalize_language(self.settings.language)
            self.auto_copy_code = self.settings.auto_copy_code
            self.auto_copy_code_var.set(self.auto_copy_code)
        except Exception as exc:
            messagebox.showerror(
                self._t("dialog.config_read_error"), f"{self.config_path}\n\n{exc}"
            )
            self.topic_var.set(secrets.token_urlsafe(12))
            return
        self.server_var.set(self.settings.server)
        self.topic_var.set(self.settings.topic)
        self.token_var.set(self.settings.token or "")
        self._advanced_username = self.settings.username or ""
        self._advanced_password = self.settings.password or ""
        self._advanced_since = self.settings.since
        self._advanced_gap = str(self.settings.clipboard_gap_ms)

    def _save_settings(self) -> Config:
        server = self.server_var.get().strip().rstrip("/")
        topic = self.topic_var.get().strip()
        if not server.startswith(("https://", "http://")):
            raise ValueError(self._t("error.server_prefix"))
        if not topic:
            raise ValueError(self._t("error.topic_empty"))
        try:
            gap = int(self._advanced_gap)
        except ValueError as exc:
            raise ValueError(self._t("error.gap_integer")) from exc
        if gap < 0:
            raise ValueError(self._t("error.gap_negative"))

        config = Config(
            server=server,
            topic=topic,
            token=self.token_var.get().strip() or None,
            username=self._advanced_username.strip() or None,
            password=self._advanced_password or None,
            since=self._advanced_since,
            clipboard_gap_ms=gap,
            state_file=self.config_path.parent / "state.json",
            log_file=self.config_path.parent / "logs" / "sms2clip.log",
            reconnect_min_seconds=1,
            reconnect_max_seconds=60,
            language=self.language,
            auto_copy_code=self.auto_copy_code_var.get(),
        )
        config.save(self.config_path)
        self.settings = config
        return config

    def _restart_service_if_running(self) -> bool:
        if not self._service_pid():
            return False
        self.status_detail_var.set(self._t("status.listener_restarting"))
        self._stop_service()
        self.after(500, self._start_service)
        return True

    def _save_connection_settings(self) -> None:
        try:
            self._save_settings()
        except Exception as exc:
            messagebox.showerror(self._t("dialog.config_error"), str(exc))
            return
        if not self._restart_service_if_running():
            self.status_detail_var.set(self._t("status.connection_saved"))

    def _on_auto_copy_change(self) -> None:
        self.auto_copy_code = bool(self.auto_copy_code_var.get())
        if self.config_path.exists():
            try:
                self._save_settings()
            except Exception as exc:
                messagebox.showerror(self._t("dialog.config_error"), str(exc))

        if not self._restart_service_if_running():
            self.status_detail_var.set(self._t("status.auto_copy_updated"))

    def _update_connection_scrollbar(self) -> None:
        bbox = self.connection_canvas.bbox("all")
        if bbox is None:
            return
        self.connection_canvas.configure(scrollregion=bbox)
        content_height = bbox[3] - bbox[1]
        if content_height > self.connection_canvas.winfo_height() + 1:
            self.connection_scrollbar.grid()
        else:
            self.connection_scrollbar.grid_remove()

    def _bind_connection_mousewheel(self, widget: tk.Misc) -> None:
        widget.bind("<MouseWheel>", self._on_connection_mousewheel, add="+")
        for child in widget.winfo_children():
            self._bind_connection_mousewheel(child)

    def _on_connection_mousewheel(self, event) -> str:
        if not self.connection_settings_content.winfo_manager():
            return "break"
        direction = -1 if event.delta > 0 else 1
        self.connection_canvas.yview_scroll(direction, "units")
        return "break"

    def _toggle_connection_settings(self) -> None:
        if self.connection_settings_content.winfo_manager():
            self.connection_settings_content.pack_forget()
            self.settings_hidden_hint_label.pack(fill="x", pady=(12, 0))
            self.settings_toggle_button.configure(text=self._t("settings.show"))
        else:
            self.settings_hidden_hint_label.pack_forget()
            self.connection_settings_content.pack(
                fill="both", expand=True, pady=(12, 0)
            )
            self.connection_canvas.yview_moveto(0)
            self.settings_toggle_button.configure(text=self._t("settings.hide"))
        self.after_idle(self._update_connection_scrollbar)

    def _update_publish_url(self) -> None:
        server = self.server_var.get().strip().rstrip("/")
        topic = self.topic_var.get().strip()
        self.publish_url_var.set(f"{server}/{topic}" if server and topic else "")

    def _regenerate_topic(self) -> None:
        self.topic_var.set(secrets.token_urlsafe(12))

    def _copy_publish_url(self) -> None:
        url = self.publish_url_var.get().strip()
        if not url:
            return
        self.clipboard_clear()
        self.clipboard_append(url)
        self.update()
        self.status_detail_var.set(self._t("status.copied_url"))

    def _open_advanced(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(self._t("advanced.title"))
        dialog.geometry("480x400")
        dialog.configure(bg=CARD)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=self._t("advanced.title"),
            bg=CARD,
            fg=NAVY,
            font=("微软雅黑", 15, "bold"),
        ).pack(anchor="w", padx=24, pady=(22, 4))
        tk.Label(
            dialog,
            text=self._t("advanced.subtitle"),
            bg=CARD,
            fg=MUTED,
            font=("微软雅黑", 9),
            justify="left",
            wraplength=420,
        ).pack(anchor="w", padx=24)

        form = tk.Frame(dialog, bg=CARD)
        form.pack(fill="x", padx=24, pady=16)
        form.grid_columnconfigure(0, weight=1)

        username_var = tk.StringVar(value=self._advanced_username)
        password_var = tk.StringVar(value=self._advanced_password)
        since_var = tk.StringVar(value=self._advanced_since)
        gap_var = tk.StringVar(value=self._advanced_gap)

        for row, (label, variable, show) in enumerate(
            [
                (self._t("advanced.username"), username_var, ""),
                (self._t("advanced.password"), password_var, "•"),
                (self._t("advanced.since"), since_var, ""),
                (self._t("advanced.gap"), gap_var, ""),
            ]
        ):
            tk.Label(
                form,
                text=label,
                bg=CARD,
                fg=NAVY,
                font=("微软雅黑", 9, "bold"),
                anchor="w",
                justify="left",
                wraplength=420,
            ).grid(row=row * 2, column=0, sticky="w", pady=(8, 4))
            ttk.Entry(
                form,
                textvariable=variable,
                style="Field.TEntry",
                show=show,
            ).grid(row=row * 2 + 1, column=0, sticky="ew")

        def save_advanced() -> None:
            self._advanced_username = username_var.get().strip()
            self._advanced_password = password_var.get()
            self._advanced_since = since_var.get().strip()
            self._advanced_gap = gap_var.get().strip() or "350"
            dialog.destroy()
            self.status_detail_var.set(self._t("status.advanced_updated"))

        ttk.Button(
            dialog,
            text=self._t("button.save"),
            style="Primary.TButton",
            command=save_advanced,
        ).pack(side="right", padx=24, pady=16)

    def _service_pid(self) -> int | None:
        pid_path = pid_file_path(self.config_path)
        pid = read_pid(pid_path)
        if pid and process_is_running(pid):
            return pid
        if pid_path.exists():
            try:
                pid_path.unlink()
            except OSError:
                pass
        return None

    def _set_status(self, kind: str, detail: str) -> None:
        self._status_kind = kind
        if kind == "running":
            title, pill_bg, pill_fg = self._t("status.running"), GREEN_BG, GREEN_TEXT
        elif kind == "starting":
            title, pill_bg, pill_fg = self._t("status.starting"), AMBER_BG, AMBER_TEXT
        elif kind == "error":
            title, pill_bg, pill_fg = self._t("status.error"), RED_BG, RED_TEXT
        else:
            title, pill_bg, pill_fg = self._t("status.stopped"), "#EAECF0", "#475467"
        self.status_title_var.set(title)
        self.status_detail_var.set(detail)
        if hasattr(self, "status_pill"):
            self.status_pill.configure(text=title, bg=pill_bg, fg=pill_fg)
        if hasattr(self, "status_title_label"):
            self.status_title_label.configure(fg=pill_fg)

    def _update_status(self) -> None:
        pid = self._service_pid()
        if pid:
            self._set_status("running", self._t("status.running_detail", pid=pid))
            if hasattr(self, "start_button"):
                self.start_button.configure(state="disabled")
                self.stop_button.configure(state="normal")
        else:
            if self.config_path.exists():
                self._set_status("stopped", self._t("status.stopped_detail"))
            if hasattr(self, "start_button"):
                self.start_button.configure(state="normal")
                self.stop_button.configure(state="disabled")

    def _poll_status(self) -> None:
        self._update_status()
        self._status_job = self.after(1000, self._poll_status)

    def _history_preview(self, text: str) -> str:
        normalized = " ".join(text.split())
        return f"{normalized[:80]}…" if len(normalized) > 80 else normalized

    def _selected_history_record(self) -> dict | None:
        if self.history_tree is None:
            return None
        selection = self.history_tree.selection()
        if not selection:
            return None
        try:
            index = int(selection[0])
        except (TypeError, ValueError):
            return None
        if 0 <= index < len(self._history_records):
            return self._history_records[index]
        return None

    def _refresh_history(self, force: bool = False) -> None:
        if self.history_tree is None or self.history_detail is None:
            return
        try:
            stat = self.history_store.path.stat()
            signature = (stat.st_mtime_ns, stat.st_size)
        except OSError:
            signature = None
        if not force and signature == self._history_signature:
            return
        self._history_signature = signature

        selected = self._selected_history_record()
        selected_key = None
        if selected is not None:
            selected_key = (
                selected.get("id", ""),
                selected.get("received_at", ""),
                selected.get("text", ""),
            )

        self._history_records = self.history_store.load()
        self.history_tree.delete(*self.history_tree.get_children())
        target_iid = None
        for index, record in enumerate(self._history_records):
            code = str(record.get("code") or "")
            prefix = f"[{code}] " if code else ""
            preview = prefix + self._history_preview(str(record.get("text", "")))
            iid = str(index)
            self.history_tree.insert(
                "",
                "end",
                iid=iid,
                values=(str(record.get("received_at", ""))[:16], preview),
            )
            record_key = (
                record.get("id", ""),
                record.get("received_at", ""),
                record.get("text", ""),
            )
            if selected_key is not None and record_key == selected_key:
                target_iid = iid

        self.history_count_var.set(
            self._t("history.count", count=len(self._history_records))
        )
        if self._history_records:
            if target_iid is None:
                target_iid = "0"
            self.history_tree.selection_set(target_iid)
            self.history_tree.focus(target_iid)
            self.history_tree.see(target_iid)
            self._on_history_select()
        else:
            self._set_history_detail(self._t("history.empty"))
            self.history_status_var.set("")
            if self.history_copy_button is not None:
                self.history_copy_button.configure(state="disabled")

    def _set_history_detail(self, text: str) -> None:
        if self.history_detail is None:
            return
        self.history_detail.configure(state="normal")
        self.history_detail.delete("1.0", "end")
        self.history_detail.insert("1.0", text)
        self.history_detail.configure(state="disabled")

    def _on_history_select(self, event=None) -> None:
        record = self._selected_history_record()
        if record is None:
            return
        self._set_history_detail(str(record.get("text", "")))
        code = str(record.get("code") or "")
        if code:
            self.history_status_var.set(self._t("history.code_found", code=code))
            if self.history_copy_button is not None:
                self.history_copy_button.configure(state="normal")
        else:
            self.history_status_var.set(self._t("history.no_code"))
            if self.history_copy_button is not None:
                self.history_copy_button.configure(state="disabled")

    def _copy_history_code(self) -> None:
        record = self._selected_history_record()
        if record is None:
            return
        code = str(record.get("code") or "")
        if not code:
            return
        self.clipboard_clear()
        self.clipboard_append(code)
        self.update_idletasks()
        self.history_status_var.set(self._t("history.copied", code=code))

    def _clear_history(self) -> None:
        if not self._history_records:
            return
        if not messagebox.askyesno(
            self._t("dialog.clear_history_title"),
            self._t("dialog.clear_history_body"),
        ):
            return
        try:
            self.history_store.clear()
        except OSError as exc:
            messagebox.showerror(self._t("dialog.config_error"), str(exc))
            return
        self._history_signature = None
        self._refresh_history(force=True)

    def _poll_history(self) -> None:
        self._refresh_history()
        self._history_job = self.after(1500, self._poll_history)

    def _poll_log(self) -> None:
        log_path = self.config_path.parent / "logs" / "sms2clip.log"
        if log_path.exists() and self.log_text is not None:
            try:
                stat = log_path.stat()
                signature = (stat.st_mtime_ns, stat.st_size)
                if signature != self._log_signature:
                    self._log_signature = signature
                    content = log_path.read_text(encoding="utf-8", errors="replace")[
                        -12000:
                    ]
                    self.log_text.configure(state="normal")
                    self.log_text.delete("1.0", "end")
                    self.log_text.insert("end", content)
                    self.log_text.see("end")
                    self.log_text.configure(state="disabled")
            except OSError:
                pass
        self._log_job = self.after(1500, self._poll_log)

    def _start_service(self) -> None:
        if self._service_pid():
            self._update_status()
            return
        try:
            self._save_settings()
        except Exception as exc:
            messagebox.showerror(self._t("dialog.start_error"), str(exc))
            return
        self._set_status("starting", self._t("status.starting_detail"))
        self.update_idletasks()
        command = build_service_command(
            self.config_path,
            frozen=is_frozen(),
            executable=gui_executable(),
        )
        try:
            process = subprocess.Popen(
                command,
                cwd=str(self.config_path.parent),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                env=build_service_environment(),
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except Exception as exc:
            self._set_status("error", f"{self._t('dialog.start_error')}: {exc}")
            messagebox.showerror(self._t("dialog.start_error"), str(exc))
            return
        pid_file_path(self.config_path).write_text(str(process.pid), encoding="ascii")
        self.child_process = process
        self.after(700, self._update_status)

    def _stop_service(self) -> None:
        pid = self._service_pid()
        if pid:
            terminate_process(pid)
        pid_path = pid_file_path(self.config_path)
        if pid_path.exists():
            try:
                pid_path.unlink()
            except OSError:
                pass
        self.child_process = None
        self.after(400, self._update_status)

    def _send_test(self) -> None:
        try:
            config = self._save_settings()
        except Exception as exc:
            messagebox.showerror(self._t("dialog.config_error"), str(exc))
            return
        if not self._service_pid():
            if not messagebox.askyesno(
                self._t("dialog.test_requires_listen_title"),
                self._t("dialog.test_requires_listen_body"),
            ):
                return
            self._start_service()
            self.after(1200, lambda: self._publish_test_message(config))
            return
        self._publish_test_message(config)

    def _publish_test_message(self, config: Config) -> None:
        def worker() -> None:
            try:
                publish_message(
                    server=config.server,
                    topic=config.topic,
                    message=self._t("test.placeholder"),
                    title="SMS",
                    token=config.token,
                    username=config.username,
                    password=config.password,
                )
            except Exception as exc:
                error_message = str(exc)
                self.after(
                    0,
                    lambda message=error_message: messagebox.showerror(
                        self._t("dialog.test_failed"), message
                    ),
                )
                return
            self.after(
                0,
                lambda: messagebox.showinfo(
                    self._t("dialog.test_sent_title"),
                    self._t("dialog.test_sent_body"),
                ),
            )

        threading.Thread(target=worker, daemon=True).start()

    def _recognize_test(self) -> None:
        if self.test_input is None:
            return
        text = self.test_input.get("1.0", "end").strip()
        code = extract_verification_code(text)
        if code:
            self.test_result_var.set(self._t("test.result", code=code))
        else:
            self.test_result_var.set(self._t("test.not_found"))

    def _startup_mode_labels(self) -> list[str]:
        return [
            self._t("startup.manual"),
            self._t("startup.manager"),
            self._t("startup.service"),
        ]

    def _startup_mode_label(self, mode: str) -> str:
        key = {
            "manager": "startup.manager",
            "service": "startup.service",
        }.get(mode, "startup.manual")
        return self._t(key)

    def _startup_mode_from_label(self, label: str) -> str:
        if label == self._t("startup.service"):
            return "service"
        if label == self._t("startup.manager"):
            return "manager"
        return "manual"

    def _startup_hint(self, mode: str) -> str:
        key = {
            "manager": "startup.hint_manager",
            "service": "startup.hint_service",
        }.get(mode, "startup.hint_manual")
        return self._t(key)

    def _on_startup_mode_change(self, event=None) -> None:
        selected = self._startup_mode_from_label(self.startup_mode_var.get())
        previous = self.startup_mode
        if selected == "service" and previous != "service":
            if not messagebox.askyesno(
                self._t("dialog.silent_mode_title"),
                self._t("dialog.silent_mode_body"),
            ):
                self.startup_mode_var.set(self._startup_mode_label(previous))
                self.startup_hint_var.set(self._startup_hint(previous))
                return
        try:
            if selected == "manual":
                disable_startup()
            else:
                self._save_settings()
                command = build_startup_command(
                    frozen=is_frozen(),
                    executable=gui_executable(),
                    config_path=self.config_path,
                    mode=selected,
                )
                enable_startup(command)
            self.startup_mode = selected
            self.startup_hint_var.set(self._startup_hint(selected))
            self.status_detail_var.set(self._t(f"status.startup_{selected}"))
            if selected == "service":
                if not self._service_pid():
                    self._start_service()
                if self._service_pid():
                    self.after(100, self._exit_app)
        except Exception as exc:
            self.startup_mode_var.set(self._startup_mode_label(previous))
            self.startup_hint_var.set(self._startup_hint(previous))
            messagebox.showerror(self._t("dialog.autostart_error"), str(exc))

    def _open_log(self) -> None:
        log_path = self.config_path.parent / "logs" / "sms2clip.log"
        if not log_path.exists():
            messagebox.showinfo(
                self._t("dialog.no_log_title"), self._t("dialog.no_log_body")
            )
            return
        os.startfile(str(log_path))

    def _open_clipboard_settings(self) -> None:
        try:
            os.startfile("ms-settings:clipboard")
        except OSError as exc:
            messagebox.showerror(self._t("dialog.open_settings_error"), str(exc))

    def _open_config_folder(self) -> None:
        os.startfile(str(self.config_path.parent))

    def _open_shortcut_qr(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(self._t("shortcut.title"))
        dialog.geometry("520x700")
        dialog.configure(bg=CARD)
        dialog.transient(self)
        dialog.grab_set()

        tk.Label(
            dialog,
            text=self._t("shortcut.title"),
            bg=CARD,
            fg=NAVY,
            font=("微软雅黑", 15, "bold"),
        ).pack(anchor="w", padx=24, pady=(22, 4))
        tk.Label(
            dialog,
            text=self._t("shortcut.instructions"),
            bg=CARD,
            fg=MUTED,
            font=("微软雅黑", 8),
            justify="left",
            anchor="w",
            wraplength=420,
        ).pack(fill="x", padx=24, pady=(0, 6))
        ttk.Button(
            dialog,
            text=self._t("shortcut.copy_topic"),
            style="Secondary.TButton",
            command=self._copy_topic,
        ).pack(anchor="w", padx=24, pady=(0, 6))

        if qrcode is not None and ImageTk is not None:
            qr_image = qrcode.make(ICLOUD_SHORTCUT_URL).resize((240, 240))
            self._shortcut_qr_photo = ImageTk.PhotoImage(qr_image)
            tk.Label(dialog, image=self._shortcut_qr_photo, bg=CARD).pack(pady=8)
        else:
            tk.Label(
                dialog,
                text=ICLOUD_SHORTCUT_URL,
                bg=SOFT,
                fg=NAVY,
                font=("Consolas", 9),
                wraplength=400,
                padx=12,
                pady=12,
            ).pack(fill="x", padx=24, pady=12)

        tk.Label(
            dialog,
            text=self._t("shortcut.credit"),
            bg=CARD,
            fg=MUTED,
            font=("微软雅黑", 8),
            wraplength=420,
        ).pack(padx=24, pady=(4, 12))

        actions = tk.Frame(dialog, bg=CARD)
        actions.pack(fill="x", padx=24, pady=(0, 20))
        ttk.Button(
            actions,
            text=self._t("shortcut.copy"),
            style="Primary.TButton",
            command=self._copy_shortcut_link,
        ).pack(side="left")
        ttk.Button(
            actions,
            text=self._t("shortcut.open"),
            style="Secondary.TButton",
            command=self._open_shortcut_link,
        ).pack(side="left", padx=(8, 0))
        ttk.Button(
            actions,
            text=self._t("shortcut.close"),
            style="Secondary.TButton",
            command=dialog.destroy,
        ).pack(side="right")

    def _copy_topic(self) -> None:
        topic = self.topic_var.get().strip()
        if not topic:
            return
        self.clipboard_clear()
        self.clipboard_append(topic)
        self.update()
        self.status_detail_var.set(self._t("shortcut.topic_copied"))

    def _copy_shortcut_link(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(ICLOUD_SHORTCUT_URL)
        self.update()
        self.status_detail_var.set(self._t("shortcut.copied"))

    def _open_shortcut_link(self) -> None:
        webbrowser.open(ICLOUD_SHORTCUT_URL)

    def _open_help(self) -> None:
        dialog = tk.Toplevel(self)
        dialog.title(self._t("help.title"))
        dialog.geometry("640x620")
        dialog.configure(bg=CARD)
        dialog.transient(self)
        text_frame = tk.Frame(dialog, bg=CARD)
        text_frame.pack(fill="both", expand=True)
        text = tk.Text(
            text_frame,
            bg=CARD,
            fg=NAVY,
            relief="flat",
            wrap="word",
            padx=22,
            pady=18,
            font=("微软雅黑", 10),
        )
        text.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(text_frame, orient="vertical", command=text.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text.configure(yscrollcommand=scrollbar.set)
        text_frame.grid_rowconfigure(0, weight=1)
        text_frame.grid_columnconfigure(0, weight=1)
        text.insert("1.0", self._t("help.body"))
        text.configure(state="disabled")
        ttk.Button(
            dialog,
            text=self._t("button.ok"),
            style="Primary.TButton",
            command=dialog.destroy,
        ).pack(pady=(0, 18))

    def _auto_start_if_needed(self) -> None:
        if not self._service_pid():
            self._start_service()

    def destroy(self) -> None:
        for job in (self._status_job, self._log_job, self._history_job):
            if job:
                try:
                    self.after_cancel(job)
                except tk.TclError:
                    pass
        self._status_job = None
        self._log_job = None
        self._history_job = None
        super().destroy()

    def _on_close(self) -> None:
        if self.tray_icon is not None:
            self._hide_to_tray()
            return
        self._exit_app()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=APP_NAME)
    parser.add_argument("--config", default=str(default_config_path()))
    parser.add_argument("--minimized", action="store_true")
    args = parser.parse_args(argv)

    instance = ManagerInstance()
    if instance.already_running:
        instance.signal_existing()
        instance.close()
        return 0

    _set_dpi_awareness()
    app = SMS2ClipApp(Path(args.config), minimized=args.minimized)

    def activate_existing() -> None:
        try:
            app.after(0, app._show_window)
        except Exception:
            pass

    instance.wait_for_activation(activate_existing)
    try:
        app.mainloop()
    finally:
        instance.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
