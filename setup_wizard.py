"""
setup_wizard.py - Interactive GUI setup wizard for the Video Auto-Poster.
Uses tkinter to guide the user through credential and configuration setup.
Run: python setup_wizard.py
"""
import os
import sys
import shutil
import webbrowser
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ─── Paths ───────────────────────────────────────────────────────────────────
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_FILE = os.path.join(PROJECT_DIR, ".env")

# ─── Helpers ─────────────────────────────────────────────────────────────────

def load_env() -> dict:
    """Read current .env into a dict."""
    data = {}
    if os.path.exists(ENV_FILE):
        with open(ENV_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, val = line.split("=", 1)
                    data[key.strip()] = val.strip()
    return data


def save_env(data: dict):
    """Write dict back to .env with section headers."""
    sections = [
        ("# ─── Folders ──────────────────────────────────────────────────────────────────", [
            "WATCH_FOLDER", "PROCESSED_FOLDER"
        ]),
        ("# ─── FFmpeg ───────────────────────────────────────────────────────────────────", [
            "FFMPEG_PATH"
        ]),
        ("# ─── Platform Toggles ────────────────────────────────────────────────────────", [
            "ENABLE_YOUTUBE", "ENABLE_TIKTOK", "ENABLE_INSTAGRAM", "ENABLE_X",
            "ENABLE_RUMBLE", "ENABLE_TRUTHSOCIAL"
        ]),
        ("# ─── AI Automation (Gemini) ───────────────────────────────────────────────────", [
            "GEMINI_API_KEY"
        ]),
        ("# ─── YouTube ─────────────────────────────────────────────────────────────────", [
            "YOUTUBE_CLIENT_SECRET", "YOUTUBE_TOKEN_FILE"
        ]),
        ("# ─── TikTok ──────────────────────────────────────────────────────────────────", [
            "TIKTOK_SESSION_FILE"
        ]),
        ("# ─── Instagram ───────────────────────────────────────────────────────────────", [
            "INSTAGRAM_USERNAME", "INSTAGRAM_PASSWORD", "INSTAGRAM_SESSION_FILE"
        ]),
        ("# ─── X (Twitter) ─────────────────────────────────────────────────────────────", [
            "X_USERNAME", "X_PASSWORD", "X_SESSION_FILE"
        ]),
        ("# ─── Rumble ───────────────────────────────────────────────────────────────────", [
            "RUMBLE_USERNAME", "RUMBLE_PASSWORD", "RUMBLE_SESSION_FILE"
        ]),
        ("# ─── Truth Social ────────────────────────────────────────────────────────────", [
            "TRUTHSOCIAL_USERNAME", "TRUTHSOCIAL_PASSWORD", "TRUTHSOCIAL_SESSION_FILE"
        ]),
        ("# ─── Default Post Metadata ────────────────────────────────────────────────────", [
            "DEFAULT_TITLE", "DEFAULT_HASHTAGS", "DEFAULT_DESCRIPTION"
        ]),
    ]
    lines = []
    written_keys = set()
    for header, keys in sections:
        lines.append(header)
        for k in keys:
            if k in data:
                lines.append(f"{k}={data[k]}")
                written_keys.add(k)
        lines.append("")
    # Write any remaining keys not in known sections
    for k, v in data.items():
        if k not in written_keys:
            lines.append(f"{k}={v}")

    with open(ENV_FILE, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


# ─── Colours ─────────────────────────────────────────────────────────────────
BG          = "#1a1a2e"
BG_CARD     = "#16213e"
BG_INPUT    = "#0f3460"
FG          = "#e0e0e0"
FG_DIM      = "#8a8a9a"
ACCENT      = "#e94560"
ACCENT_HOVER = "#ff6b81"
SUCCESS     = "#2ecc71"
FONT_TITLE  = ("Segoe UI", 16, "bold")
FONT_HEAD   = ("Segoe UI", 12, "bold")
FONT_BODY   = ("Segoe UI", 10)
FONT_SMALL  = ("Segoe UI", 9)
FONT_BTN    = ("Segoe UI", 10, "bold")


class SetupWizard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Auto-Poster  ·  Setup Wizard")
        self.configure(bg=BG)
        self.resizable(True, True)

        # Centre on screen
        w, h = 640, 620
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # ── Enable clipboard shortcuts (Ctrl+C/V/X/A) ──
        self.bind_all("<Control-a>", lambda e: e.widget.select_range(0, "end") if isinstance(e.widget, tk.Entry) else None)
        self.bind_all("<Control-A>", lambda e: e.widget.select_range(0, "end") if isinstance(e.widget, tk.Entry) else None)
        self.bind_all("<Control-c>", lambda e: self._clipboard_copy(e))
        self.bind_all("<Control-v>", lambda e: self._clipboard_paste(e))
        self.bind_all("<Control-x>", lambda e: self._clipboard_cut(e))

        # ── Right-click context menu for all Entry widgets ──
        self._ctx_menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=FG,
                                  activebackground=ACCENT, activeforeground="white",
                                  font=FONT_SMALL, relief="flat", bd=1)
        self._ctx_menu.add_command(label="✂  Cut        Ctrl+X")
        self._ctx_menu.add_command(label="📋 Copy      Ctrl+C")
        self._ctx_menu.add_command(label="📌 Paste     Ctrl+V")
        self._ctx_menu.add_separator()
        self._ctx_menu.add_command(label="🔘 Select All  Ctrl+A")
        self.bind_all("<Button-3>", self._show_context_menu)

        self.env = load_env()

        # ── Title bar ──
        title_frame = tk.Frame(self, bg=ACCENT, height=50)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(
            title_frame, text="⚡ Video Auto-Poster Setup", font=FONT_TITLE,
            bg=ACCENT, fg="white", anchor="w", padx=20
        ).pack(fill="both", expand=True)

        # ── Notebook (tabbed pages) ──
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", background=BG_CARD, foreground=FG,
                        font=FONT_BODY, padding=[14, 6])
        style.map("TNotebook.Tab",
                  background=[("selected", ACCENT)],
                  foreground=[("selected", "white")])
        style.configure("TFrame", background=BG)

        self.notebook = ttk.Notebook(self)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(10, 0))

        # Create tabs
        self._create_general_tab()
        self._create_gemini_tab()
        self._create_youtube_tab()
        self._create_tiktok_tab()
        self._create_instagram_tab()
        self._create_x_tab()
        self._create_rumble_tab()
        self._create_truthsocial_tab()
        self._create_metadata_tab()

        # ── Bottom bar ──
        bottom = tk.Frame(self, bg=BG, height=56)
        bottom.pack(fill="x", padx=10, pady=10)

        save_btn = tk.Button(
            bottom, text="💾  Save Configuration", font=FONT_BTN,
            bg=SUCCESS, fg="white", activebackground="#27ae60",
            activeforeground="white", relief="flat", padx=20, pady=8,
            cursor="hand2", command=self._save
        )
        save_btn.pack(side="right")

        cancel_btn = tk.Button(
            bottom, text="Cancel", font=FONT_BODY,
            bg=BG_CARD, fg=FG_DIM, activebackground=BG_INPUT,
            activeforeground=FG, relief="flat", padx=16, pady=8,
            cursor="hand2", command=self.destroy
        )
        cancel_btn.pack(side="right", padx=(0, 10))

    # ─── Tab Helpers ─────────────────────────────────────────────────────────

    def _make_tab(self, title: str) -> tk.Frame:
        frame = tk.Frame(self.notebook, bg=BG, padx=16, pady=12)
        self.notebook.add(frame, text=f"  {title}  ")
        return frame

    def _label(self, parent, text, font=FONT_BODY, fg=FG, **kw):
        lbl = tk.Label(parent, text=text, font=font, bg=BG, fg=fg, anchor="w", **kw)
        lbl.pack(fill="x", pady=(8, 2))
        return lbl

    def _entry(self, parent, key, show=None, width=50):
        var = tk.StringVar(value=self.env.get(key, ""))
        entry = tk.Entry(
            parent, textvariable=var, font=FONT_BODY, width=width,
            bg=BG_INPUT, fg=FG, insertbackground=FG, relief="flat",
            highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BG_CARD
        )
        if show:
            entry.config(show=show)
        entry.pack(fill="x", pady=(0, 4), ipady=4)
        setattr(self, f"var_{key}", var)
        return entry

    def _file_row(self, parent, key, filetypes=(("JSON", "*.json"), ("All", "*.*"))):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=(0, 4))
        var = tk.StringVar(value=self.env.get(key, ""))
        entry = tk.Entry(
            row, textvariable=var, font=FONT_BODY, width=40,
            bg=BG_INPUT, fg=FG, insertbackground=FG, relief="flat",
            highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BG_CARD
        )
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        btn = tk.Button(
            row, text="Browse…", font=FONT_SMALL, bg=BG_CARD, fg=FG,
            activebackground=ACCENT, activeforeground="white",
            relief="flat", padx=10, cursor="hand2",
            command=lambda: self._browse(var, filetypes)
        )
        btn.pack(side="left", padx=(6, 0))
        setattr(self, f"var_{key}", var)
        return row

    def _toggle(self, parent, key, label_text):
        var = tk.BooleanVar(value=self.env.get(key, "true").lower() == "true")
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", pady=3)
        cb = tk.Checkbutton(
            row, text=label_text, variable=var, font=FONT_BODY,
            bg=BG, fg=FG, selectcolor=BG_INPUT,
            activebackground=BG, activeforeground=FG, anchor="w"
        )
        cb.pack(side="left")
        setattr(self, f"var_{key}", var)
        return row

    def _hint(self, parent, text):
        tk.Label(parent, text=text, font=FONT_SMALL, bg=BG, fg=FG_DIM,
                 anchor="w", wraplength=560, justify="left").pack(fill="x", pady=(0, 6))

    def _link(self, parent, text, url):
        """Create a clickable hyperlink label that opens the URL in a browser."""
        link = tk.Label(
            parent, text=f"🔗 {text}", font=("Segoe UI", 9, "underline"),
            bg=BG, fg=ACCENT, cursor="hand2", anchor="w"
        )
        link.pack(fill="x", pady=(0, 6))
        link.bind("<Button-1>", lambda e: webbrowser.open(url))
        link.bind("<Enter>", lambda e: link.config(fg=ACCENT_HOVER))
        link.bind("<Leave>", lambda e: link.config(fg=ACCENT))
        return link

    def _clipboard_copy(self, event):
        """Copy selected text to clipboard."""
        widget = event.widget
        if isinstance(widget, tk.Entry):
            try:
                if widget.selection_present():
                    self.clipboard_clear()
                    self.clipboard_append(widget.selection_get())
            except tk.TclError:
                pass
        return "break"

    def _clipboard_paste(self, event):
        """Paste text from clipboard."""
        widget = event.widget
        if isinstance(widget, tk.Entry):
            try:
                text = self.clipboard_get()
                if widget.selection_present():
                    widget.delete("sel.first", "sel.last")
                widget.insert("insert", text)
            except tk.TclError:
                pass
        return "break"

    def _clipboard_cut(self, event):
        """Cut selected text to clipboard."""
        widget = event.widget
        if isinstance(widget, tk.Entry):
            try:
                if widget.selection_present():
                    self.clipboard_clear()
                    self.clipboard_append(widget.selection_get())
                    widget.delete("sel.first", "sel.last")
            except tk.TclError:
                pass
        return "break"

    def _show_context_menu(self, event):
        """Show right-click context menu on Entry widgets."""
        widget = event.widget
        if not isinstance(widget, tk.Entry):
            return
        # Focus the widget so clipboard operations work on it
        widget.focus_set()
        # Update menu commands to target this specific widget
        self._ctx_menu.entryconfigure(0, command=lambda: self._ctx_cut(widget))
        self._ctx_menu.entryconfigure(1, command=lambda: self._ctx_copy(widget))
        self._ctx_menu.entryconfigure(2, command=lambda: self._ctx_paste(widget))
        self._ctx_menu.entryconfigure(4, command=lambda: widget.select_range(0, "end"))
        try:
            self._ctx_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self._ctx_menu.grab_release()

    def _ctx_cut(self, widget):
        try:
            if widget.selection_present():
                self.clipboard_clear()
                self.clipboard_append(widget.selection_get())
                widget.delete("sel.first", "sel.last")
        except tk.TclError:
            pass

    def _ctx_copy(self, widget):
        try:
            if widget.selection_present():
                self.clipboard_clear()
                self.clipboard_append(widget.selection_get())
        except tk.TclError:
            pass

    def _ctx_paste(self, widget):
        try:
            text = self.clipboard_get()
            if widget.selection_present():
                widget.delete("sel.first", "sel.last")
            widget.insert("insert", text)
        except tk.TclError:
            pass

    def _browse(self, var, filetypes):
        path = filedialog.askopenfilename(filetypes=filetypes)
        if path:
            var.set(path)

    def _browse_folder(self, var):
        path = filedialog.askdirectory()
        if path:
            var.set(path)

    # ─── Tabs ────────────────────────────────────────────────────────────────

    def _create_general_tab(self):
        tab = self._make_tab("⚙ General")
        self._label(tab, "Watch Folder (videos dropped here trigger uploads)", font=FONT_HEAD)

        row = tk.Frame(tab, bg=BG)
        row.pack(fill="x", pady=(0, 4))
        var_wf = tk.StringVar(value=self.env.get("WATCH_FOLDER", ""))
        entry = tk.Entry(row, textvariable=var_wf, font=FONT_BODY, width=40,
                         bg=BG_INPUT, fg=FG, insertbackground=FG, relief="flat",
                         highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BG_CARD)
        entry.pack(side="left", fill="x", expand=True, ipady=4)
        btn = tk.Button(row, text="Browse…", font=FONT_SMALL, bg=BG_CARD, fg=FG,
                        activebackground=ACCENT, activeforeground="white",
                        relief="flat", padx=10, cursor="hand2",
                        command=lambda: self._browse_folder(var_wf))
        btn.pack(side="left", padx=(6, 0))
        self.var_WATCH_FOLDER = var_wf

        self._label(tab, "Processed Folder (completed videos moved here)")
        row2 = tk.Frame(tab, bg=BG)
        row2.pack(fill="x", pady=(0, 4))
        var_pf = tk.StringVar(value=self.env.get("PROCESSED_FOLDER", ""))
        entry2 = tk.Entry(row2, textvariable=var_pf, font=FONT_BODY, width=40,
                          bg=BG_INPUT, fg=FG, insertbackground=FG, relief="flat",
                          highlightthickness=1, highlightcolor=ACCENT, highlightbackground=BG_CARD)
        entry2.pack(side="left", fill="x", expand=True, ipady=4)
        btn2 = tk.Button(row2, text="Browse…", font=FONT_SMALL, bg=BG_CARD, fg=FG,
                         activebackground=ACCENT, activeforeground="white",
                         relief="flat", padx=10, cursor="hand2",
                         command=lambda: self._browse_folder(var_pf))
        btn2.pack(side="left", padx=(6, 0))
        self.var_PROCESSED_FOLDER = var_pf

        self._label(tab, "FFmpeg Path")
        self._entry(tab, "FFMPEG_PATH")
        self._hint(tab, 'Leave as "ffmpeg" if it\'s on your system PATH.')

        self._label(tab, "Enabled Platforms", font=FONT_HEAD)
        self._toggle(tab, "ENABLE_YOUTUBE", "YouTube Shorts")
        self._toggle(tab, "ENABLE_TIKTOK", "TikTok")
        self._toggle(tab, "ENABLE_INSTAGRAM", "Instagram Reels")
        self._toggle(tab, "ENABLE_X", "X (Twitter)")
        self._toggle(tab, "ENABLE_RUMBLE", "Rumble")
        self._toggle(tab, "ENABLE_TRUTHSOCIAL", "Truth Social")

    def _create_gemini_tab(self):
        tab = self._make_tab("🤖 Gemini AI")
        self._label(tab, "Gemini API Key", font=FONT_HEAD)
        self._hint(tab, "Used for AI-powered video analysis, title generation, and thumbnail creation.")
        self._link(tab, "Get your API key from Google AI Studio", "https://aistudio.google.com/apikey")
        self._entry(tab, "GEMINI_API_KEY", show="•")
        self._hint(tab, "Without this key, the system uses generic mock titles and descriptions.")

    def _create_youtube_tab(self):
        tab = self._make_tab("▶ YouTube")
        self._label(tab, "YouTube Setup", font=FONT_HEAD)
        self._hint(tab,
            "1. Go to Google Cloud Console → APIs & Services → Credentials\n"
            "2. Create an OAuth 2.0 Client ID (Desktop application)\n"
            "3. Download the client_secret.json file\n"
            "4. Select it below"
        )
        self._link(tab, "Open Google Cloud Console — Credentials",
                   "https://console.cloud.google.com/apis/credentials")
        self._label(tab, "Client Secret File (client_secret.json)")
        self._file_row(tab, "YOUTUBE_CLIENT_SECRET")
        self._label(tab, "Token File (auto-generated after first login)")
        self._entry(tab, "YOUTUBE_TOKEN_FILE")

    def _create_tiktok_tab(self):
        tab = self._make_tab("♪ TikTok")
        self._label(tab, "TikTok Setup", font=FONT_HEAD)
        self._hint(tab,
            "TikTok uses browser cookies for authentication:\n"
            "1. Install the 'Get cookies.txt LOCALLY' Chrome extension\n"
            "2. Log into TikTok in Chrome\n"
            "3. Use the extension to export cookies to a .txt file\n"
            "4. Select that file below"
        )
        self._link(tab, "Get 'cookies.txt LOCALLY' Chrome Extension",
                   "https://github.com/kairi003/Get-cookies.txt-LOCALLY")
        self._link(tab, "Open TikTok (log in first)",
                   "https://www.tiktok.com")
        self._label(tab, "TikTok Cookies / Session File")
        self._file_row(tab, "TIKTOK_SESSION_FILE",
                        filetypes=(("Text/JSON", "*.txt;*.json"), ("All", "*.*")))

    def _create_instagram_tab(self):
        tab = self._make_tab("📸 Instagram")
        self._label(tab, "Instagram Credentials", font=FONT_HEAD)
        self._hint(tab,
            "Your Instagram username and password are used for the Private API login.\n"
            "A session file will be saved after the first successful login to avoid re-authentication."
        )
        self._label(tab, "Username")
        self._entry(tab, "INSTAGRAM_USERNAME")
        self._label(tab, "Password")
        self._entry(tab, "INSTAGRAM_PASSWORD", show="•")
        self._label(tab, "Session File (auto-saved)")
        self._entry(tab, "INSTAGRAM_SESSION_FILE")

    def _create_x_tab(self):
        tab = self._make_tab("𝕏 X")
        self._label(tab, "X (Twitter) Setup", font=FONT_HEAD)
        self._hint(tab,
            "X uses a Playwright browser session for uploading.\n"
            "To create a session file:\n"
            "1. Run: python -c \"from playwright.sync_api import sync_playwright; ...\"\n"
            "   (or use the login helper script below)\n"
            "2. Log in manually in the browser that opens\n"
            "3. The session is saved to x_session.json"
        )
        self._label(tab, "Username")
        self._entry(tab, "X_USERNAME")
        self._label(tab, "Password")
        self._entry(tab, "X_PASSWORD", show="•")
        self._label(tab, "Session File")
        self._file_row(tab, "X_SESSION_FILE")

        # Login helper button
        login_btn = tk.Button(
            tab, text="🔐  Launch X Login Helper", font=FONT_BTN,
            bg=BG_CARD, fg=ACCENT, activebackground=ACCENT,
            activeforeground="white", relief="flat", padx=16, pady=6,
            cursor="hand2", command=self._launch_x_login
        )
        login_btn.pack(pady=(12, 0))

    def _create_rumble_tab(self):
        tab = self._make_tab("🟢 Rumble")
        self._label(tab, "Rumble Setup", font=FONT_HEAD)
        self._hint(tab,
            "Rumble uses browser automation for uploading.\n"
            "Enter your Rumble account credentials below.\n"
            "A session file will be saved after the first login."
        )
        self._link(tab, "Open Rumble (log in first)",
                   "https://rumble.com")
        self._label(tab, "Username")
        self._entry(tab, "RUMBLE_USERNAME")
        self._label(tab, "Password")
        self._entry(tab, "RUMBLE_PASSWORD", show="•")
        self._label(tab, "Session File")
        self._file_row(tab, "RUMBLE_SESSION_FILE")

    def _create_truthsocial_tab(self):
        tab = self._make_tab("🇺🇸 Truth")
        self._label(tab, "Truth Social Setup", font=FONT_HEAD)
        self._hint(tab,
            "Truth Social uses browser automation for posting.\n"
            "Enter your Truth Social account credentials below.\n"
            "A session file will be saved after the first login."
        )
        self._link(tab, "Open Truth Social (log in first)",
                   "https://truthsocial.com")
        self._label(tab, "Username / Email")
        self._entry(tab, "TRUTHSOCIAL_USERNAME")
        self._label(tab, "Password")
        self._entry(tab, "TRUTHSOCIAL_PASSWORD", show="•")
        self._label(tab, "Session File")
        self._file_row(tab, "TRUTHSOCIAL_SESSION_FILE")

    def _create_metadata_tab(self):
        tab = self._make_tab("📝 Defaults")
        self._label(tab, "Default Post Metadata", font=FONT_HEAD)
        self._hint(tab, "Used when AI analysis is unavailable or fails.")
        self._label(tab, "Default Title")
        self._entry(tab, "DEFAULT_TITLE")
        self._label(tab, "Default Hashtags")
        self._entry(tab, "DEFAULT_HASHTAGS")
        self._label(tab, "Default Description")
        self._entry(tab, "DEFAULT_DESCRIPTION")

    # ─── Actions ─────────────────────────────────────────────────────────────

    def _launch_x_login(self):
        """Open a Playwright browser for manual X login and save the session."""
        session_path = self.var_X_SESSION_FILE.get() or "x_session.json"
        try:
            from playwright.sync_api import sync_playwright
            messagebox.showinfo(
                "X Login",
                "A browser window will open.\n\n"
                "1. Log into your X (Twitter) account\n"
                "2. Once logged in, CLOSE the browser window\n"
                "3. Your session will be saved automatically",
                parent=self
            )
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=False)
                context = browser.new_context()
                page = context.new_page()
                page.goto("https://x.com/login")
                # Wait for user to log in and close
                try:
                    page.wait_for_url("https://x.com/home", timeout=300_000)
                    context.storage_state(path=session_path)
                    messagebox.showinfo("Success", f"Session saved to: {session_path}", parent=self)
                except Exception:
                    # User closed browser or timeout
                    try:
                        context.storage_state(path=session_path)
                        messagebox.showinfo("Session Saved",
                                            f"Session saved to: {session_path}\n(even if login was partial)",
                                            parent=self)
                    except Exception:
                        messagebox.showwarning("Warning", "Could not save session.", parent=self)
                browser.close()
        except ImportError:
            messagebox.showerror("Error", "Playwright is not installed.\nRun: pip install playwright", parent=self)
        except Exception as e:
            messagebox.showerror("Error", f"Failed to launch browser:\n{e}", parent=self)

    def _save(self):
        """Collect all values and write to .env."""
        # Collect all var_ attributes
        for attr in dir(self):
            if attr.startswith("var_"):
                key = attr[4:]  # strip "var_"
                widget_var = getattr(self, attr)
                if isinstance(widget_var, tk.BooleanVar):
                    self.env[key] = "true" if widget_var.get() else "false"
                else:
                    self.env[key] = widget_var.get()

        # Copy YouTube client secret to project dir if it's an external path
        yt_secret = self.env.get("YOUTUBE_CLIENT_SECRET", "")
        if yt_secret and os.path.isabs(yt_secret) and os.path.exists(yt_secret):
            dest = os.path.join(PROJECT_DIR, "client_secret.json")
            if yt_secret != dest:
                shutil.copy2(yt_secret, dest)
                self.env["YOUTUBE_CLIENT_SECRET"] = "client_secret.json"

        save_env(self.env)

        # Summary of what's configured
        platforms = []
        if self.env.get("ENABLE_YOUTUBE", "").lower() == "true":
            platforms.append("YouTube")
        if self.env.get("ENABLE_TIKTOK", "").lower() == "true":
            platforms.append("TikTok")
        if self.env.get("ENABLE_INSTAGRAM", "").lower() == "true":
            platforms.append("Instagram")
        if self.env.get("ENABLE_X", "").lower() == "true":
            platforms.append("X")
        if self.env.get("ENABLE_RUMBLE", "").lower() == "true":
            platforms.append("Rumble")
        if self.env.get("ENABLE_TRUTHSOCIAL", "").lower() == "true":
            platforms.append("Truth Social")

        messagebox.showinfo(
            "Saved",
            f"Configuration saved to .env\n\n"
            f"Enabled platforms: {', '.join(platforms) if platforms else 'None'}\n"
            f"Watch folder: {self.env.get('WATCH_FOLDER', 'N/A')}\n\n"
            f"Run 'python main.py' to start the auto-poster.",
            parent=self
        )


if __name__ == "__main__":
    app = SetupWizard()
    app.mainloop()
