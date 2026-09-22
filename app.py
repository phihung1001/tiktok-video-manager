import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import math
from datetime import datetime
from pathlib import Path
from automation.engine import AutomationEngine
from automation.state import load_config, save_config
from automation.license import LicenseManager, device_id
from automation.paths import LOGS

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("TikTok Video Manager — Selenium")
        self.geometry("1120x820")
        self.minsize(980, 700)
        self.engine = None
        self.error_photo = None
        self.error_photo_path = None
        self.error_photo_window = None
        self.error_photo_original = None
        self.error_photo_zoom = 1.0
        self.error_photo_canvas = None
        self.error_photo_zoom_label = None
        self.session_started_at = None
        self.session_log_lines = []
        self.session_stats = {"success": 0, "error": 0, "invalid": 0, "info": 0}
        self.session_log_path = None
        self.cfg = load_config()
        self.language = tk.StringVar(value=self.cfg.get("language", "vi"))
        self.theme = tk.StringVar(value=self.cfg.get("theme", "light"))

        self.folder = tk.StringVar(value=self.cfg.get("folder", ""))
        self.account = tk.StringVar(value=self.cfg.get("account_name", "HT88 - Thời trang nam"))
        self.account_mode = tk.StringVar(value=self.cfg.get("account_mode", "name"))
        self.product = tk.StringVar(value=self.cfg.get("product_name", ""))
        self.product_mode = tk.StringVar(value=self.cfg.get("product_mode", "name"))
        self.license_key = tk.StringVar(value=self.cfg.get("license_key", ""))
        self.diagnostic_mode = tk.BooleanVar(value=self.cfg.get("diagnostic_mode", False))
        self.public_profile = tk.BooleanVar(value=self.cfg.get("public_profile", False))
        rules = self.cfg.get("video_rules", {})
        self.max_file_size = tk.StringVar(value=str(rules.get("max_file_size_mb", self.cfg.get("max_file_size_mb", 500))))
        self.min_duration = tk.StringVar(value=str(rules.get("min_duration_seconds", 5)))
        self.max_duration = tk.StringVar(value=str(rules.get("max_duration_seconds", 600)))
        self.aspect_tolerance = tk.StringVar(value=str(rules.get("aspect_tolerance", 0.005)))
        self.batch_size = tk.StringVar(value=str(self.cfg.get("batch_size", 50)))
        self.upload_timeout = tk.StringVar(value=str(self.cfg.get("upload_timeout_seconds", 900)))
        self.status = tk.StringVar(value=f"✦ {self._t('ready')}")
        self.counter = tk.StringVar(value="0 / 0")
        self._build()

    TRANSLATIONS = {
        "vi": {
            "subtitle": "Tự động hóa nội dung video trong Seller Center", "session": "PHIÊN UPLOAD",
            "folder": "Thư mục video", "choose_folder": "Chọn thư mục", "account": "Tài khoản TikTok", "account_name_mode": "Tên", "account_id_mode": "ID",
            "product": "Sản phẩm (không bắt buộc)", "product_name_mode": "Tên", "product_id_mode": "ID", "description": "Mô tả mặc định",
            "public": "Hiển thị trên hồ sơ TikTok công khai", "rules": "QUY TẮC VIDEO",
            "max_size": "Dung lượng tối đa (MB)", "min": "Tối thiểu (giây)", "max": "Tối đa (giây)",
            "tolerance": "Sai số tỷ lệ", "batch": "Video / batch", "start": "BẮT ĐẦU PHIÊN",
            "upload_timeout": "Timeout upload/xác thực (giây)",
            "pause": "Tạm dừng", "resume": "Tiếp tục", "stop": "Dừng", "progress": "TIẾN TRÌNH",
            "journal": "Nhật ký phiên làm việc", "clear": "Xóa log", "ready": "Sẵn sàng",
            "running": "Đang chạy", "stopped": "Đã dừng", "done": "Hoàn tất", "theme": "Theme",
            "language": "Ngôn ngữ", "light": "Sáng", "dark": "Tối", "vietnamese": "Tiếng Việt",
            "english": "English", "license_key": "License key", "error_screenshot": "ẢNH LỖI GẦN NHẤT", "no_screenshot": "Chưa có ảnh lỗi",
            "view_large": "Xem ảnh lớn", "fit_window": "Vừa cửa sổ", "screenshot_ready": "Ảnh lỗi đã được hiển thị trên màn hình tool",
        },
        "en": {
            "subtitle": "Automate video content in Seller Center", "session": "UPLOAD SESSION",
            "folder": "Video folder", "choose_folder": "Choose folder", "account": "TikTok account", "account_name_mode": "Name", "account_id_mode": "ID",
            "product": "Product (optional)", "product_name_mode": "Name", "product_id_mode": "ID", "description": "Default description",
            "public": "Show on public TikTok profile", "rules": "VIDEO RULES",
            "max_size": "Max size (MB)", "min": "Minimum (seconds)", "max": "Maximum (seconds)",
            "tolerance": "Aspect tolerance", "batch": "Videos / batch", "start": "START SESSION",
            "upload_timeout": "Upload/validation timeout (seconds)",
            "pause": "Pause", "resume": "Resume", "stop": "Stop", "progress": "PROGRESS",
            "journal": "Session activity", "clear": "Clear log", "ready": "Ready",
            "running": "Running", "stopped": "Stopped", "done": "Completed", "theme": "Theme",
            "language": "Language", "light": "Light", "dark": "Dark", "vietnamese": "Tiếng Việt",
            "english": "English", "license_key": "License key", "error_screenshot": "LATEST ERROR SCREENSHOT", "no_screenshot": "No error screenshot",
            "view_large": "View larger", "fit_window": "Fit window", "screenshot_ready": "Error screenshot displayed in the tool",
        },
    }

    def _t(self, key):
        return self.TRANSLATIONS[self.language.get()].get(key, key)

    def _rebuild_ui(self):
        description = self.description.get("1.0", "end") if hasattr(self, "description") else ""
        log_content = self.log.get("1.0", "end") if hasattr(self, "log") else ""
        for child in self.winfo_children():
            child.destroy()
        self._build()
        self.description.delete("1.0", "end")
        self.description.insert("1.0", description)
        if log_content.strip():
            self.log["state"] = "normal"
            self.log.insert("1.0", log_content)
            self.log["state"] = "disabled"
        if self.session_log_lines and self.session_started_at:
            self.export_log_btn.configure(state="normal")

    def _change_language(self, *_):
        save_config({"language": self.language.get(), "theme": self.theme.get()})
        self._rebuild_ui()

    def _change_theme(self, *_):
        save_config({"language": self.language.get(), "theme": self.theme.get()})
        self._rebuild_ui()

    def _build(self):
        self._configure_styles()
        self.configure(bg="#f3f6f8" if self.theme.get() == "light" else "#101820")

        outer = ttk.Frame(self, padding=(24, 20), style="App.TFrame")
        outer.pack(fill="both", expand=True)

        header = ttk.Frame(outer, style="App.TFrame")
        header.pack(fill="x", pady=(0, 18))
        title_group = ttk.Frame(header, style="App.TFrame")
        title_group.pack(side="left")
        ttk.Label(title_group, text="TikTok Video Manager", style="Title.TLabel").pack(anchor="w")
        ttk.Label(title_group, text=self._t("subtitle"), style="Subtitle.TLabel").pack(anchor="w", pady=(3, 0))
        controls = ttk.Frame(header, style="App.TFrame")
        controls.pack(side="right", padx=(12, 12))
        ttk.Label(controls, text=self._t("language"), style="Subtitle.TLabel").grid(row=0, column=0, padx=4)
        self._choice_switch(controls, self.language, (("VI", "vi"), ("EN", "en")), self._change_language).grid(row=0, column=1, padx=4)
        ttk.Label(controls, text=self._t("theme"), style="Subtitle.TLabel").grid(row=0, column=2, padx=4)
        self._choice_switch(controls, self.theme, (("Sáng", "light"), ("Tối", "dark")), self._change_theme).grid(row=0, column=3, padx=4)
        self.status_label = ttk.Label(header, textvariable=self.status, style="StatusReady.TLabel")
        self.status_label.pack(side="right", anchor="n", ipadx=12, ipady=6)
        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=(0, 16))

        form = ttk.LabelFrame(outer, text=f"  {self._t('session')}  ", padding=(16, 12), style="Card.TLabelframe")
        form.pack(fill="x", pady=(0, 12))
        form.columnconfigure(0, weight=1)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text=self._t("folder"), style="Field.TLabel").grid(row=0, column=0, columnspan=2, sticky="w")
        ttk.Entry(form, textvariable=self.folder, style="Input.TEntry").grid(row=1, column=0, sticky="ew", padx=(0, 8), pady=(5, 12))
        ttk.Button(form, text=self._t("choose_folder"), command=self.choose_folder, style="Secondary.TButton").grid(row=1, column=1, sticky="ew", pady=(5, 12))

        ttk.Label(form, text=self._t("account"), style="Field.TLabel").grid(row=2, column=0, sticky="w", padx=(0, 8))
        ttk.Label(form, text=self._t("product"), style="Field.TLabel").grid(row=2, column=1, sticky="w")
        account_controls = ttk.Frame(form, style="Card.TFrame")
        account_controls.grid(row=3, column=0, sticky="ew", padx=(0, 8), pady=(5, 12))
        account_controls.columnconfigure(0, weight=1)
        ttk.Entry(account_controls, textvariable=self.account, style="Input.TEntry").grid(row=0, column=0, sticky="ew", padx=(0, 6))
        account_mode_box = ttk.Frame(account_controls, style="Card.TFrame")
        account_mode_box.grid(row=0, column=1, sticky="e")
        self._mode_switch(account_mode_box, self.account_mode)
        product_controls = ttk.Frame(form, style="Card.TFrame")
        product_controls.grid(row=3, column=1, sticky="ew", pady=(5, 12))
        product_controls.columnconfigure(0, weight=1)
        ttk.Entry(product_controls, textvariable=self.product, style="Input.TEntry").grid(row=0, column=0, sticky="ew", padx=(0, 6))
        product_mode_box = ttk.Frame(product_controls, style="Card.TFrame")
        product_mode_box.grid(row=0, column=1, sticky="e")
        self._mode_switch(product_mode_box, self.product_mode)

        ttk.Checkbutton(
            form,
            text="Ghi log chi tiết" if self.language.get() == "vi" else "Detailed logging",
            variable=self.diagnostic_mode,
            style="Clean.TCheckbutton"
        ).grid(row=9, column=0, columnspan=2, sticky="w", pady=(8, 0))

        ttk.Label(form, text=self._t("description"), style="Field.TLabel").grid(row=4, column=0, columnspan=2, sticky="w")
        dark = self.theme.get() == "dark"
        self.description = tk.Text(form, height=3, wrap="word", relief="flat", bd=0, padx=10, pady=8, bg="#223442" if dark else "#ffffff", fg="#e7eef4" if dark else "#17202a", insertbackground="#e7eef4" if dark else "#17202a", font=("Segoe UI", 10))
        self.description.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(5, 10))
        self.description.insert("1.0", self.cfg.get("description", ""))

        ttk.Checkbutton(
            form, text=self._t("public"),
            variable=self.public_profile, style="Clean.TCheckbutton"
        ).grid(row=6, column=0, columnspan=2, sticky="w", pady=(0, 2))
        ttk.Label(form, text=self._t("license_key"), style="Field.TLabel").grid(row=7, column=0, columnspan=2, sticky="w", pady=(8, 0))
        ttk.Entry(form, textvariable=self.license_key, style="Input.TEntry", show="*").grid(row=8, column=0, columnspan=2, sticky="ew", pady=(5, 0))

        rules_box = ttk.LabelFrame(outer, text=f"  {self._t('rules')}  ", padding=(12, 10), style="Card.TLabelframe")
        rules_box.pack(fill="x", pady=(0, 12))
        fields = [
            (self._t("max_size"), self.max_file_size), (self._t("min"), self.min_duration),
            (self._t("max"), self.max_duration), (self._t("tolerance"), self.aspect_tolerance),
            (self._t("batch"), self.batch_size), (self._t("upload_timeout"), self.upload_timeout),
        ]
        for column, (label, variable) in enumerate(fields):
            rules_box.columnconfigure(column, weight=1)
            ttk.Label(rules_box, text=label, style="Field.TLabel").grid(row=0, column=column, sticky="w", padx=4)
            ttk.Entry(rules_box, textvariable=variable, style="Input.TEntry", width=14).grid(row=1, column=column, sticky="ew", padx=4, pady=(5, 0))

        buttons = ttk.Frame(outer, style="App.TFrame")
        buttons.pack(fill="x", pady=(0, 14))
        self.start_btn = ttk.Button(buttons, text=self._t("start"), command=self.start, style="Accent.TButton")
        self.pause_btn = ttk.Button(buttons, text=self._t("pause"), command=self.pause, style="Secondary.TButton", state="disabled")
        self.resume_btn = ttk.Button(buttons, text=self._t("resume"), command=self.resume, style="Secondary.TButton", state="disabled")
        self.stop_btn = ttk.Button(buttons, text=self._t("stop"), command=self.stop, style="Danger.TButton", state="disabled")
        self.start_btn.pack(side="left", expand=True, fill="x", padx=(0, 8))
        self.pause_btn.pack(side="left", padx=4)
        self.resume_btn.pack(side="left", padx=4)
        self.stop_btn.pack(side="left", padx=(4, 0))

        progress_box = ttk.LabelFrame(outer, text=f"  {self._t('progress')}  ", padding=(16, 12), style="Card.TLabelframe")
        progress_box.pack(fill="both", expand=True)
        head = ttk.Frame(progress_box, style="Card.TFrame")
        head.pack(fill="x")
        ttk.Label(head, text=self._t("journal"), style="Section.TLabel").pack(side="left")
        self.export_log_btn = ttk.Button(
            head,
            text="Xuất log phiên" if self.language.get() == "vi" else "Export session log",
            command=self.export_log,
            state="disabled",
            style="Secondary.TButton",
        )
        self.export_log_btn.pack(side="right", padx=(10, 0))
        ttk.Button(head, text=self._t("clear"), command=self.clear_log, style="Secondary.TButton").pack(side="right", padx=(10, 0))
        ttk.Label(head, textvariable=self.counter, style="Counter.TLabel").pack(side="right")
        self.progress = ttk.Progressbar(progress_box, maximum=100, style="Accent.Horizontal.TProgressbar")
        self.progress.pack(fill="x", pady=(10, 12))

        log_frame = ttk.Frame(progress_box, style="Card.TFrame")
        log_frame.pack(fill="both", expand=True)
        preview_box = ttk.LabelFrame(log_frame, text=f"  {self._t('error_screenshot')}  ", padding=(8, 8), style="Card.TLabelframe")
        preview_box.pack(side="right", fill="y", padx=(10, 0))
        self.error_preview = ttk.Label(preview_box, text=self._t("no_screenshot"), anchor="center", justify="center", width=30, style="Subtitle.TLabel")
        self.error_preview.pack(fill="both", expand=True, padx=4, pady=4)
        self.view_photo_btn = ttk.Button(preview_box, text=self._t("view_large"), command=self._view_error_photo, state="disabled", style="Secondary.TButton")
        self.view_photo_btn.pack(fill="x", pady=(6, 0))

        self.log = tk.Text(log_frame, height=12, state="disabled", wrap="word", relief="flat", bd=0, padx=14, pady=12, bg="#111c29", fg="#d9e3ec", insertbackground="#ffffff", font=("Cascadia Mono", 10))
        self.log.tag_configure("SESSION", foreground="#78d5ff", font=("Cascadia Mono", 10, "bold"))
        self.log.tag_configure("OK", foreground="#7ee2a8")
        self.log.tag_configure("INFO", foreground="#d9e3ec")
        self.log.tag_configure("WARN", foreground="#ffd37a")
        self.log.tag_configure("ERROR", foreground="#ff8f8f")
        self.log.tag_configure("SUMMARY", foreground="#bda8ff", font=("Cascadia Mono", 10, "bold"))
        self.log.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(log_frame, orient="vertical", command=self.log.yview)
        scrollbar.pack(side="right", fill="y")
        self.log.configure(yscrollcommand=scrollbar.set)

    def _configure_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        dark = self.theme.get() == "dark"
        background = "#101820" if dark else "#f3f6f8"
        card = "#182633" if dark else "#ffffff"
        foreground = "#e7eef4" if dark else "#17202a"
        muted = "#a9b9c5" if dark else "#526170"
        border = "#304554" if dark else "#d7e0e8"
        input_bg = "#223442" if dark else "#ffffff"
        style.configure("App.TFrame", background=background)
        style.configure("Card.TFrame", background=card)
        style.configure("Card.TLabelframe", background=card, bordercolor=border, relief="solid", borderwidth=1)
        style.configure("Card.TLabelframe.Label", background=card, foreground=muted, font=("Segoe UI", 9, "bold"))
        style.configure("Title.TLabel", background=background, foreground=foreground, font=("Segoe UI", 24, "bold"))
        style.configure("Subtitle.TLabel", background=background, foreground=muted, font=("Segoe UI", 10))
        style.configure("StatusReady.TLabel", background="#214b3a" if dark else "#e7f5ee", foreground="#8ee0b3" if dark else "#1d7a4d", font=("Segoe UI", 10, "bold"), padding=(16, 8), borderwidth=1, relief="solid")
        style.configure("StatusRunning.TLabel", background="#123e50" if dark else "#e6f6fb", foreground="#78d5ff" if dark else "#087ea4", font=("Segoe UI", 10, "bold"), padding=(16, 8), borderwidth=1, relief="solid")
        style.configure("StatusDone.TLabel", background="#3d315c" if dark else "#f0ebff", foreground="#d2c2ff" if dark else "#6346b5", font=("Segoe UI", 10, "bold"), padding=(16, 8), borderwidth=1, relief="solid")
        style.configure("StatusWarning.TLabel", background="#513d22" if dark else "#fff5df", foreground="#ffd37a" if dark else "#986b00", font=("Segoe UI", 10, "bold"), padding=(16, 8), borderwidth=1, relief="solid")
        style.configure("Field.TLabel", background=card, foreground=muted, font=("Segoe UI", 9, "bold"))
        style.configure("Section.TLabel", background=card, foreground=foreground, font=("Segoe UI", 11, "bold"))
        style.configure("Counter.TLabel", background=card, foreground="#159ac5" if not dark else "#65c6ed", font=("Segoe UI", 10, "bold"))
        style.configure("Input.TEntry", padding=(9, 7), fieldbackground=input_bg, foreground=foreground, bordercolor=border, lightcolor=border, darkcolor=border)
        style.configure("App.TCombobox", padding=(6, 5), fieldbackground=input_bg, background=input_bg, foreground=foreground, bordercolor=border, lightcolor=border, darkcolor=border, arrowcolor=foreground)
        style.map("App.TCombobox", fieldbackground=[("readonly", input_bg), ("focus", input_bg)], foreground=[("readonly", foreground)], selectbackground=[("readonly", input_bg)], selectforeground=[("readonly", foreground)])
        mode_bg = "#223442" if dark else "#edf2f5"
        mode_active = "#087ea4" if dark else "#159ac5"
        mode_active_hover = "#066783" if dark else "#087ea4"
        style.configure("Mode.TRadiobutton", padding=(11, 6), background=mode_bg, foreground=foreground, borderwidth=0, relief="flat", font=("Segoe UI", 9, "bold"))
        style.map("Mode.TRadiobutton", background=[("selected", mode_active), ("active", mode_active_hover)], foreground=[("selected", "#ffffff"), ("active", "#ffffff")])
        style.configure("Clean.TCheckbutton", background=card, foreground=foreground, font=("Segoe UI", 9))
        style.configure("Accent.TButton", padding=(16, 11), background="#087ea4", foreground="#ffffff", font=("Segoe UI", 10, "bold"), borderwidth=0)
        style.map("Accent.TButton", background=[("active", "#066783"), ("disabled", "#a8c5d0")])
        style.configure("Secondary.TButton", padding=(12, 9), background="#2b3d4b" if dark else "#e9eef2", foreground=foreground, font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("Secondary.TButton", background=[("active", "#385365" if dark else "#d8e2e9"), ("disabled", "#263743" if dark else "#eef2f4")])
        style.configure("Danger.TButton", padding=(12, 9), background="#512b2d" if dark else "#f9e8e7", foreground="#ffaaa7" if dark else "#b23a35", font=("Segoe UI", 9, "bold"), borderwidth=0)
        style.map("Danger.TButton", background=[("active", "#68383a" if dark else "#f3d3d1"), ("disabled", "#382528" if dark else "#f5eeee")])
        style.configure("Accent.Horizontal.TProgressbar", troughcolor="#30424e" if dark else "#e6edf2", background="#22a7d5", bordercolor="#30424e" if dark else "#e6edf2", lightcolor="#22a7d5", darkcolor="#22a7d5", thickness=8)

    def _choice_switch(self, parent, variable, choices, callback):
        dark = self.theme.get() == "dark"
        frame = tk.Frame(parent, bg="#101820" if dark else "#f3f6f8", highlightthickness=0)
        buttons = []
        normal_bg = "#223442" if dark else "#edf2f5"
        normal_fg = "#e7eef4" if dark else "#526170"
        selected_bg = "#087ea4" if dark else "#159ac5"

        def refresh():
            for button, value in buttons:
                selected = variable.get() == value
                button.configure(
                    bg=selected_bg if selected else normal_bg,
                    fg="#ffffff" if selected else normal_fg,
                    activebackground="#066783" if selected else ("#304c5d" if dark else "#d8e5eb"),
                    activeforeground="#ffffff" if selected else normal_fg,
                )

        for label, value in choices:
            button = tk.Button(
                frame,
                text=label,
                command=lambda selected=value: (variable.set(selected), callback()),
                relief="flat",
                bd=0,
                padx=9,
                pady=4,
                cursor="hand2",
                font=("Segoe UI", 9, "bold"),
                highlightthickness=0,
            )
            button.pack(side="left")
            buttons.append((button, value))
        refresh()
        return frame

    def _mode_switch(self, parent, variable):
        dark = self.theme.get() == "dark"
        buttons = []
        normal_bg = "#223442" if dark else "#edf2f5"
        normal_fg = "#e7eef4" if dark else "#526170"
        selected_bg = "#087ea4" if dark else "#159ac5"

        def refresh(*_):
            for button, value in buttons:
                selected = variable.get() == value
                button.configure(
                    bg=selected_bg if selected else normal_bg,
                    fg="#ffffff" if selected else normal_fg,
                    activebackground="#066783" if selected else ("#304c5d" if dark else "#d8e5eb"),
                    activeforeground="#ffffff" if selected else normal_fg,
                )

        for label, value in (("Tên", "name"), ("ID", "id")):
            button = tk.Button(
                parent,
                text=label,
                command=lambda selected=value: variable.set(selected),
                relief="flat",
                bd=0,
                padx=12,
                pady=5,
                cursor="hand2",
                font=("Segoe UI", 9, "bold"),
                highlightthickness=0,
            )
            button.pack(side="left")
            buttons.append((button, value))
        variable.trace_add("write", refresh)
        refresh()

    def choose_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.folder.set(folder)

    def clear_log(self):
        self.log["state"] = "normal"
        self.log.delete("1.0", "end")
        self.log["state"] = "disabled"

    def export_log(self):
        if not self.session_log_lines:
            messagebox.showinfo("Log", "Chưa có log của phiên để xuất.")
            return
        started = self.session_started_at or datetime.now()
        target = filedialog.asksaveasfilename(
            title="Lưu log phiên",
            defaultextension=".txt",
            initialfile=f"session-log-{started.strftime('%Y%m%d-%H%M%S')}.txt",
            filetypes=(("Log text", "*.txt"), ("All files", "*.*")),
        )
        if not target:
            return
        try:
            Path(target).write_text("\n".join(self.session_log_lines) + "\n", encoding="utf-8")
            self._log("INFO", f"Đã xuất log phiên: {Path(target).name}", record=False)
        except OSError as error:
            messagebox.showerror("Log", f"Không thể xuất log: {error}")

    def _write_session_log(self):
        if not self.session_log_lines or not self.session_started_at:
            return
        try:
            LOGS.mkdir(parents=True, exist_ok=True)
            self.session_log_path = LOGS / f"session-{self.session_started_at.strftime('%Y%m%d-%H%M%S')}.txt"
            self.session_log_path.write_text("\n".join(self.session_log_lines) + "\n", encoding="utf-8")
        except OSError:
            self.session_log_path = None

    def start(self):
        folder = self.folder.get().strip()
        account = self.account.get().strip()
        license_config = dict(self.cfg)
        license_config["license_key"] = self.license_key.get().strip()
        if license_config.get("license_server_url"):
            license_status = LicenseManager(license_config).validate(
                license_config.get("license_key", ""), device_id()
            )
            if not license_status.valid:
                messagebox.showerror("License", license_status.message)
                return
        if not folder or not Path(folder).is_dir():
            messagebox.showerror("Lỗi", "Hãy chọn thư mục video hợp lệ.")
            return
        if not account:
            messagebox.showerror("Lỗi", "Hãy nhập tài khoản TikTok.")
            return

        try:
            max_file_size = float(self.max_file_size.get())
            min_duration = float(self.min_duration.get())
            max_duration = float(self.max_duration.get())
            aspect_tolerance = float(self.aspect_tolerance.get())
            batch_size = int(self.batch_size.get())
            upload_timeout = int(self.upload_timeout.get())
        except ValueError:
            messagebox.showerror("Lỗi", "Các quy tắc video phải là số hợp lệ.")
            return
        if max_file_size <= 0 or min_duration < 0 or max_duration <= min_duration:
            messagebox.showerror("Lỗi", "Kiểm tra dung lượng và khoảng thời lượng video.")
            return
        if not 0 < aspect_tolerance <= 1 or not 1 <= batch_size <= 50 or upload_timeout < 30:
            messagebox.showerror("Lỗi", "Sai số tỷ lệ phải trong (0, 1], batch từ 1 đến 50 và timeout tối thiểu 30 giây.")
            return

        config = {
            "folder": folder,
            "account_name": account,
            "account_mode": self.account_mode.get(),
            "product_name": self.product.get().strip(),
            "product_mode": self.product_mode.get(),
            "diagnostic_mode": self.diagnostic_mode.get(),
            "description": self.description.get("1.0", "end").strip(),
            "public_profile": self.public_profile.get(),
            "license_key": self.license_key.get().strip(),
            "batch_size": batch_size,
            "upload_timeout_seconds": upload_timeout,
            "video_rules": {
                "max_file_size_mb": max_file_size,
                "min_duration_seconds": min_duration,
                "max_duration_seconds": max_duration,
                "aspect_tolerance": aspect_tolerance,
            },
        }
        save_config(config)
        self._set_running(True)
        self.clear_log()
        self.error_photo = None
        self.error_photo_path = None
        self.error_photo_original = None
        self.error_preview.configure(image="", text=self._t("no_screenshot"))
        self.error_preview.image = None
        self.view_photo_btn.configure(state="disabled")
        self.progress["value"] = 0
        self.counter.set("0 / 0")
        self.session_started_at = datetime.now()
        self.session_log_lines = []
        self.session_stats = {"success": 0, "error": 0, "invalid": 0, "info": 0}
        self.session_log_path = None
        self.export_log_btn.configure(state="disabled")
        self._log("SESSION", "Bắt đầu phiên automation")
        self._log("INFO", f"Thư mục: {Path(folder).name}")
        self._log("INFO", "Đang kiểm tra video và chuẩn bị hàng đợi")

        self.engine = AutomationEngine(config, self.emit)
        threading.Thread(target=self._run_engine, daemon=True).start()

    def _run_engine(self):
        try:
            self.engine.run()
        except Exception as e:
            self.emit({"type":"error", "message":str(e)})
        finally:
            self.after(0, lambda: self._set_running(False))

    def pause(self):
        if self.engine:
            self.engine.pause()
            self._set_status("Paused" if self.language.get() == "en" else "Đã tạm dừng")
            self.pause_btn["state"] = "disabled"
            self.resume_btn["state"] = "normal"

    def resume(self):
        if self.engine:
            self.engine.resume()
            self._set_status(self._t("running"))
            self.pause_btn["state"] = "normal"
            self.resume_btn["state"] = "disabled"

    def stop(self):
        if self.engine:
            self.engine.stop()
            self._set_status("Stopping..." if self.language.get() == "en" else "Đang dừng...")

    def _set_running(self, running):
        self.start_btn["state"] = "disabled" if running else "normal"
        self.pause_btn["state"] = "normal" if running else "disabled"
        self.resume_btn["state"] = "disabled"
        self.stop_btn["state"] = "normal" if running else "disabled"
        self._set_status(self._t("running") if running else self._t("ready"))

    def _set_status(self, text):
        lowered = text.lower()
        if any(word in lowered for word in ("chạy", "running")):
            icon, style = "●", "StatusRunning.TLabel"
        elif any(word in lowered for word in ("hoàn tất", "completed")):
            icon, style = "✓", "StatusDone.TLabel"
        elif any(word in lowered for word in ("dừng", "dừng", "paused", "stopping")):
            icon, style = "!", "StatusWarning.TLabel"
        else:
            icon, style = "✦", "StatusReady.TLabel"
        self.status.set(f"{icon} {text}")
        if hasattr(self, "status_label"):
            self.status_label.configure(style=style)

    def emit(self, event):
        self.after(0, lambda: self._handle_event(event))

    def _handle_event(self, e):
        t = e.get("type")
        if t == "scan":
            self.counter.set(f"0 / {e['total']}")
        elif t == "progress":
            self.progress["value"] = e["percent"]
            self.counter.set(f"{e['done']} / {e['total']}")
        elif t == "result":
            status = e.get("status", "info").lower()
            level = "WARN" if status == "invalid" else "ERROR" if status == "error" else "OK" if status == "success" else "INFO"
            self.session_stats[status] = self.session_stats.get(status, 0) + 1
            self._log(level, f"{e['file']} — {e['message']}")
            return
        elif t == "info":
            self._log("INFO", e["message"])
        elif t == "error":
            self._log("ERROR", e["message"])
        elif t == "screenshot":
            self._show_error_photo(e.get("path"), e.get("message", self._t("screenshot_ready")))
        elif t == "finished":
            self._set_status(self._t("stopped") if e.get("stopped") else self._t("done"))
            self._log("WARN" if e.get("stopped") else "INFO", "Phiên đã dừng theo yêu cầu người dùng" if e.get("stopped") else "Đã xử lý xong hàng đợi")
            self._log("SUMMARY", "Tổng kết: thành công {success}, lỗi {error}, bỏ qua {invalid}".format(**self.session_stats))
            self._write_session_log()
            self.export_log_btn.configure(state="normal" if self.session_log_lines else "disabled")
            return

    def _log(self, level, msg, record=True):
        line = f"{datetime.now().strftime('%H:%M:%S')}  [{level}]  {msg}"
        self.log["state"] = "normal"
        tag = level if level in {"SESSION", "OK", "INFO", "WARN", "ERROR", "SUMMARY"} else "INFO"
        self.log.insert("end", line + "\n", tag)
        self.log.see("end")
        self.log["state"] = "disabled"
        if record:
            self.session_log_lines.append(line)

    def _show_error_photo(self, path, caption):
        if not path or not Path(path).is_file():
            return
        try:
            image = tk.PhotoImage(file=path)
            factor = max(1, math.ceil(image.width() / 320), math.ceil(image.height() / 220))
            preview = image.subsample(factor, factor) if factor > 1 else image
            self.error_photo = image
            self.error_photo_path = path
            self.error_preview.configure(image=preview, text="")
            self.error_preview.image = preview
            self.view_photo_btn.configure(state="normal")
            self._log("ERROR", f"{caption}: {Path(path).name}")
        except tk.TclError as error:
            self._log("ERROR", f"Không thể hiển thị ảnh lỗi: {error}")

    def _view_error_photo(self):
        if not self.error_photo_path or not Path(self.error_photo_path).is_file():
            return
        if self.error_photo_window and self.error_photo_window.winfo_exists():
            self.error_photo_window.lift()
            return
        window = tk.Toplevel(self)
        window.title(self._t("error_screenshot"))
        window.geometry("1200x800")
        window.minsize(700, 500)
        window.configure(bg="#101820" if self.theme.get() == "dark" else "#f3f6f8")
        toolbar = ttk.Frame(window, style="App.TFrame")
        toolbar.pack(fill="x", padx=10, pady=(10, 4))
        ttk.Button(toolbar, text="−", width=4, command=lambda: self._zoom_error_photo(0.8)).pack(side="left")
        ttk.Button(toolbar, text="+", width=4, command=lambda: self._zoom_error_photo(1.25)).pack(side="left", padx=(4, 0))
        ttk.Button(toolbar, text="100%", command=lambda: self._set_error_photo_zoom(1.0)).pack(side="left", padx=(10, 0))
        ttk.Button(toolbar, text=self._t("fit_window"), command=self._fit_error_photo).pack(side="left", padx=(4, 0))
        self.error_photo_zoom_label = ttk.Label(toolbar, text="100%", style="Subtitle.TLabel")
        self.error_photo_zoom_label.pack(side="right")

        viewer = ttk.Frame(window, style="App.TFrame")
        viewer.pack(fill="both", expand=True, padx=10, pady=(4, 10))
        viewer.rowconfigure(0, weight=1)
        viewer.columnconfigure(0, weight=1)
        canvas = tk.Canvas(viewer, highlightthickness=0, bg="#101820" if self.theme.get() == "dark" else "#dfe7ec")
        canvas.grid(row=0, column=0, sticky="nsew")
        x_scroll = ttk.Scrollbar(viewer, orient="horizontal", command=canvas.xview)
        y_scroll = ttk.Scrollbar(viewer, orient="vertical", command=canvas.yview)
        x_scroll.grid(row=1, column=0, sticky="ew")
        y_scroll.grid(row=0, column=1, sticky="ns")
        canvas.configure(xscrollcommand=x_scroll.set, yscrollcommand=y_scroll.set)
        self.error_photo_window = window
        self.error_photo_canvas = canvas
        self.error_photo_original = tk.PhotoImage(file=self.error_photo_path)
        window.update_idletasks()
        self._fit_error_photo()

    def _render_error_photo(self):
        if not self.error_photo_canvas or not self.error_photo_original:
            return
        image = self.error_photo_original
        if self.error_photo_zoom < 1:
            denominator = max(1, round(1 / self.error_photo_zoom))
            displayed = image.subsample(denominator, denominator)
        elif self.error_photo_zoom == 1:
            displayed = image
        else:
            factor = max(1, round(self.error_photo_zoom))
            displayed = image.zoom(factor, factor)
        self.error_photo_canvas.delete("all")
        self.error_photo_canvas.create_image(0, 0, image=displayed, anchor="nw")
        self.error_photo_canvas.image = displayed
        self.error_photo_canvas.configure(scrollregion=(0, 0, displayed.width(), displayed.height()))
        if self.error_photo_zoom_label:
            self.error_photo_zoom_label.configure(text=f"{round(self.error_photo_zoom * 100)}% — {image.width()}×{image.height()} px")

    def _set_error_photo_zoom(self, zoom):
        self.error_photo_zoom = max(0.25, min(4.0, zoom))
        self._render_error_photo()

    def _zoom_error_photo(self, multiplier):
        if multiplier > 1:
            self._set_error_photo_zoom(min(4.0, max(2.0, math.ceil(self.error_photo_zoom) + 1 if self.error_photo_zoom >= 2 else 2.0)))
        else:
            self._set_error_photo_zoom(max(0.25, math.floor(self.error_photo_zoom) - 1 if self.error_photo_zoom > 1 else 0.5))

    def _fit_error_photo(self):
        if not self.error_photo_original or not self.error_photo_canvas:
            return
        width = max(1, self.error_photo_canvas.winfo_width())
        height = max(1, self.error_photo_canvas.winfo_height())
        image = self.error_photo_original
        self._set_error_photo_zoom(min(width / image.width(), height / image.height(), 1.0))

if __name__ == "__main__":
    App().mainloop()
