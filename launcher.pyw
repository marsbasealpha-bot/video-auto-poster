"""
launcher.pyw - GUI launcher for the Video Auto-Poster.
Replaces the console menu with a clickable dark-themed window.
Double-click the desktop shortcut to open this.
"""
import os
import sys
import subprocess
import tkinter as tk

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_PYTHON = os.path.join(PROJECT_DIR, "venv", "Scripts", "python.exe")
PYTHONW = os.path.join(PROJECT_DIR, "venv", "Scripts", "pythonw.exe")

# Use venv python if available, else system python
PYTHON = VENV_PYTHON if os.path.exists(VENV_PYTHON) else sys.executable
PW = PYTHONW if os.path.exists(PYTHONW) else PYTHON

# ─── Colours (matching setup_wizard.py) ──────────────────────────────────────
BG          = "#1a1a2e"
BG_CARD     = "#16213e"
BG_INPUT    = "#0f3460"
FG          = "#e0e0e0"
FG_DIM      = "#8a8a9a"
ACCENT      = "#e94560"
ACCENT_HOVER = "#ff6b81"
SUCCESS     = "#2ecc71"


class Launcher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video Auto-Poster")
        self.configure(bg=BG)
        self.resizable(True, True)

        # Centre on screen
        w, h = 380, 360
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

        # ── Title bar ──
        title_frame = tk.Frame(self, bg=ACCENT, height=50)
        title_frame.pack(fill="x")
        title_frame.pack_propagate(False)
        tk.Label(
            title_frame, text="⚡ Video Auto-Poster",
            font=("Segoe UI", 16, "bold"),
            bg=ACCENT, fg="white", anchor="w", padx=20
        ).pack(fill="both", expand=True)

        # ── Subtitle ──
        tk.Label(
            self, text="Select an option to get started",
            font=("Segoe UI", 10), bg=BG, fg=FG_DIM
        ).pack(pady=(16, 12))

        # ── Option Buttons ──
        buttons = [
            ("1", "▶  Start Auto-Poster",   "Launch the drag & drop posting window",   SUCCESS,   self._start_poster),
            ("2", "⚙  Open Setup Wizard",   "Configure credentials & folders",         BG_INPUT,  self._open_wizard),
            ("3", "🧪  Run Tests",           "Verify system components",                BG_INPUT,  self._run_tests),
            ("Q", "✖  Quit",                "Close this launcher",                     "#c0392b", self._quit),
        ]

        for key, label, hint, color, cmd in buttons:
            btn_frame = tk.Frame(self, bg=BG)
            btn_frame.pack(fill="x", padx=30, pady=4)

            btn = tk.Frame(btn_frame, bg=BG_CARD, cursor="hand2",
                           highlightthickness=1, highlightbackground=BG_INPUT)
            btn.pack(fill="x")

            # Key badge
            badge = tk.Label(
                btn, text=key, font=("Consolas", 12, "bold"),
                bg=color, fg="white", width=3, height=1
            )
            badge.pack(side="left", padx=(0, 0))

            # Text area
            text_frame = tk.Frame(btn, bg=BG_CARD)
            text_frame.pack(side="left", fill="both", expand=True, padx=10, pady=6)

            title_lbl = tk.Label(
                text_frame, text=label, font=("Segoe UI", 11, "bold"),
                bg=BG_CARD, fg=FG, anchor="w"
            )
            title_lbl.pack(fill="x")

            hint_lbl = tk.Label(
                text_frame, text=hint, font=("Segoe UI", 8),
                bg=BG_CARD, fg=FG_DIM, anchor="w"
            )
            hint_lbl.pack(fill="x")

            # Hover effects + click binding on all child widgets
            for widget in (btn, badge, text_frame, title_lbl, hint_lbl):
                widget.bind("<Enter>", lambda e, b=btn, t=title_lbl: (
                    b.config(bg=BG_INPUT),
                    t.config(bg=BG_INPUT, fg="white"),
                    e.widget.master.config(bg=BG_INPUT) if hasattr(e.widget, 'master') else None
                ))
                widget.bind("<Leave>", lambda e, b=btn, t=title_lbl, tf=text_frame, hl=hint_lbl: (
                    b.config(bg=BG_CARD),
                    t.config(bg=BG_CARD, fg=FG),
                    tf.config(bg=BG_CARD),
                    hl.config(bg=BG_CARD)
                ))
                widget.bind("<Button-1>", lambda e, c=cmd: c())
                widget.config(cursor="hand2")

        # ── Keyboard shortcuts ──
        self.bind("1", lambda e: self._start_poster())
        self.bind("2", lambda e: self._open_wizard())
        self.bind("3", lambda e: self._run_tests())
        self.bind("q", lambda e: self._quit())
        self.bind("Q", lambda e: self._quit())
        self.bind("<Escape>", lambda e: self._quit())

    def _start_poster(self):
        """Launch the watch folder monitor window."""
        subprocess.Popen(
            [PW, os.path.join(PROJECT_DIR, "watch_window.pyw")],
            cwd=PROJECT_DIR
        )
        self.destroy()

    def _open_wizard(self):
        """Open the setup wizard (no console)."""
        subprocess.Popen(
            [PW, os.path.join(PROJECT_DIR, "setup_wizard.py")],
            cwd=PROJECT_DIR
        )
        self.destroy()

    def _run_tests(self):
        """Run tests in a new console window and keep it open."""
        subprocess.Popen(
            ["cmd", "/k", PYTHON, os.path.join(PROJECT_DIR, "test_system.py")],
            cwd=PROJECT_DIR,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        self.destroy()

    def _quit(self):
        self.destroy()


if __name__ == "__main__":
    app = Launcher()
    app.mainloop()
