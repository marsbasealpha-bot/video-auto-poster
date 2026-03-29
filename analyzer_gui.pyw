"""
analyzer_gui.pyw - GUI front-end for the Video Analyzer.
Drag-and-drop or browse to analyze videos/images with Gemini AI.
"""
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox
import threading
import json
import ctypes

# ── Ensure project imports work ──
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)
import config

# Fix for pythonw: sys.stderr/stdout are None
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w')
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w')

# ── Theme ──
BG       = "#1a1a2e"
BG_CARD  = "#16213e"
ACCENT   = "#e94560"
ACCENT2  = "#0f3460"
FG       = "#eaeaea"
FG_DIM   = "#8892a0"
SUCCESS  = "#00d474"
WARNING  = "#f5a623"

SUPPORTED = (
    ("Video/Image Files", "*.mp4 *.avi *.mov *.mkv *.wmv *.flv *.webm *.m4v "
     "*.jpg *.jpeg *.png *.gif *.bmp *.webp"),
    ("All Files", "*.*"),
)


def _crash_log(msg):
    try:
        import datetime
        log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "crash_log.txt")
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(f"[{datetime.datetime.now():%Y-%m-%d %H:%M:%S}] ANALYZER_GUI: {msg}\n")
    except Exception:
        pass


# ── Native drag-and-drop (ctypes) ──
def _hook_drop_files(tk_window, callback):
    """Win32 native drag-and-drop via WM_DROPFILES."""
    import ctypes
    from ctypes import wintypes
    hwnd = int(tk_window.wm_frame(), 16)
    WM_DROPFILES = 0x0233
    GWL_WNDPROC = -4

    # LRESULT is 64-bit on Win64 — c_long (32-bit) breaks close/maximize
    LRESULT = ctypes.c_longlong
    WNDPROC = ctypes.WINFUNCTYPE(LRESULT, wintypes.HWND, wintypes.UINT,
                                 wintypes.WPARAM, wintypes.LPARAM)

    shell32 = ctypes.windll.shell32
    DragQueryFile = shell32.DragQueryFileW
    DragQueryFile.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_wchar_p, wintypes.UINT]
    DragQueryFile.restype  = wintypes.UINT
    DragFinish = shell32.DragFinish
    DragFinish.argtypes = [ctypes.c_void_p]
    DragFinish.restype  = None
    DragAcceptFiles = shell32.DragAcceptFiles
    DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    DragAcceptFiles.restype  = None

    user32 = ctypes.windll.user32
    CallWindowProc = user32.CallWindowProcW
    CallWindowProc.argtypes = [ctypes.c_void_p, wintypes.HWND, wintypes.UINT,
                               wintypes.WPARAM, wintypes.LPARAM]
    CallWindowProc.restype  = LRESULT

    GetWindowLongPtr = user32.GetWindowLongPtrW
    GetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int]
    GetWindowLongPtr.restype  = ctypes.c_void_p

    SetWindowLongPtr = user32.SetWindowLongPtrW
    SetWindowLongPtr.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_void_p]
    SetWindowLongPtr.restype  = ctypes.c_void_p

    old_proc = GetWindowLongPtr(hwnd, GWL_WNDPROC)

    def new_wndproc(hwnd, msg, wparam, lparam):
        if msg == WM_DROPFILES:
            try:
                hdrop = ctypes.c_void_p(wparam)
                count = DragQueryFile(hdrop, 0xFFFFFFFF, None, 0)
                files = []
                buf = ctypes.create_unicode_buffer(260)
                for i in range(count):
                    DragQueryFile(hdrop, i, buf, 260)
                    files.append(buf.value)
                DragFinish(hdrop)
                callback(files)
            except Exception:
                import traceback
                _crash_log(f"DND ERROR: {traceback.format_exc()}")
            return 0
        return CallWindowProc(old_proc, hwnd, msg, wparam, lparam)

    tk_window._wndproc_ref = WNDPROC(new_wndproc)
    DragAcceptFiles(hwnd, True)
    SetWindowLongPtr(hwnd, GWL_WNDPROC, tk_window._wndproc_ref)


class AnalyzerGUI(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(f"Video Analyzer - {PROJECT_DIR}")
        self.configure(bg=BG)
        self.resizable(True, True)

        w, h = 500, 780
        screen_w = self.winfo_screenwidth()
        x = (screen_w - w) // 2
        y = 20
        self.geometry(f"{w}x{h}+{x}+{y}")

        # Ensure inbox and analyzed folders exist
        for folder in (config.ANALYZER_INBOX, config.ANALYZED_FOLDER):
            os.makedirs(folder, exist_ok=True)

        self._build_ui()

        # Hook drag-and-drop
        self.after(100, self._setup_dnd)

    def _setup_dnd(self):
        try:
            _hook_drop_files(self, self._on_drop)
        except Exception as e:
            _crash_log(f"DND hook failed: {e}")

    def _build_ui(self):
        # ── Header ──
        hdr = tk.Frame(self, bg=ACCENT, height=44)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="Video Analyzer", font=("Segoe UI", 13, "bold"),
            bg=ACCENT, fg="white", anchor="w", padx=14
        ).pack(fill="both", expand=True)

        # ── Drop / Browse Zone ──
        drop_frame = tk.Frame(self, bg=BG, padx=10, pady=6, height=100)
        drop_frame.pack(fill="x")
        drop_frame.pack_propagate(False)

        self.drop_zone = tk.Frame(
            drop_frame, bg=BG_CARD, cursor="hand2",
            highlightthickness=2, highlightbackground=FG_DIM, highlightcolor=ACCENT
        )
        self.drop_zone.pack(fill="both", expand=True, padx=2, pady=2)

        self.drop_label = tk.Label(
            self.drop_zone,
            text="Drop a video/image here\nor click to browse",
            font=("Segoe UI", 10), bg=BG_CARD, fg=FG_DIM, justify="center"
        )
        self.drop_label.pack(expand=True)
        self.drop_zone.bind("<Button-1>", lambda e: self._browse())
        self.drop_label.bind("<Button-1>", lambda e: self._browse())

        # ── Status ──
        self.status_var = tk.StringVar(value="Ready")
        status_bar = tk.Label(
            self, textvariable=self.status_var, font=("Segoe UI", 9),
            bg=ACCENT2, fg=FG, anchor="w", padx=10, pady=4
        )
        status_bar.pack(fill="x")

        # ── Results Frame ──
        results_frame = tk.Frame(self, bg=BG, padx=10, pady=6)
        results_frame.pack(fill="both", expand=True)

        # Field labels and values
        self.fields = {}
        field_defs = [
            ("Hook/Filename", 1),
            ("Title", 1),
            ("Description", 2),
            ("Transcript", 4),
            ("Hashtags", 2),
            ("Mentions", 1),
            ("Thumbnail Prompt", 3),
            ("Output Folder", 1),
        ]

        for label_text, height in field_defs:
            lbl = tk.Label(
                results_frame, text=label_text + ":",
                font=("Segoe UI", 9, "bold"), bg=BG, fg=ACCENT, anchor="w"
            )
            lbl.pack(fill="x", pady=(6, 0))

            txt = tk.Text(
                results_frame, font=("Consolas", 9), bg=BG_CARD, fg=FG,
                relief="flat", height=height, wrap="word", state="disabled",
                highlightthickness=1, highlightbackground=ACCENT2,
                insertbackground=FG
            )
            txt.pack(fill="x", pady=(0, 2))
            self.fields[label_text] = txt

        # ── Buttons ──
        btn_frame = tk.Frame(self, bg=BG, padx=10, pady=8)
        btn_frame.pack(fill="x")

        self.analyze_btn = tk.Button(
            btn_frame, text="Analyze", font=("Segoe UI", 10, "bold"),
            bg=ACCENT, fg="white", activebackground="#c0392b", activeforeground="white",
            relief="flat", padx=20, pady=6, state="disabled",
            command=self._run_analysis
        )
        self.analyze_btn.pack(side="left", padx=(0, 8))

        self.open_folder_btn = tk.Button(
            btn_frame, text="Open Output", font=("Segoe UI", 9),
            bg=ACCENT2, fg=FG, activebackground="#1a4a7a", activeforeground="white",
            relief="flat", padx=14, pady=6, state="disabled",
            command=self._open_folder
        )
        self.open_folder_btn.pack(side="left", padx=(0, 8))

        self.open_inbox_btn = tk.Button(
            btn_frame, text="Open Inbox", font=("Segoe UI", 9),
            bg=ACCENT2, fg=FG, activebackground="#1a4a7a", activeforeground="white",
            relief="flat", padx=14, pady=6,
            command=self._open_inbox
        )
        self.open_inbox_btn.pack(side="left")

        self.selected_file = None
        self.output_folder = None

    def _browse(self):
        path = filedialog.askopenfilename(
            title="Select a video or image",
            initialdir=config.ANALYZER_INBOX,
            filetypes=SUPPORTED
        )
        if path:
            self._set_file(path)

    def _on_drop(self, files):
        if files:
            self._set_file(files[0])

    def _set_file(self, path):
        self.selected_file = path
        name = os.path.basename(path)
        self.drop_label.configure(text=name, fg=FG)
        self.status_var.set(f"Selected: {name}")
        self.analyze_btn.configure(state="normal")
        # Clear previous results
        for txt in self.fields.values():
            txt.configure(state="normal")
            txt.delete("1.0", "end")
            txt.configure(state="disabled")

    def _run_analysis(self):
        if not self.selected_file:
            return
        self.analyze_btn.configure(state="disabled")
        self.status_var.set("Analyzing... please wait")
        self.drop_label.configure(fg=WARNING)

        thread = threading.Thread(target=self._analyze_worker, daemon=True)
        thread.start()

    def _analyze_worker(self):
        try:
            from analyzer import analyze_media
            result = analyze_media(self.selected_file)

            self.output_folder = result.get("output_folder")

            def update_ui():
                mapping = {
                    "Hook/Filename": result.get("hook", ""),
                    "Title": result.get("title", ""),
                    "Description": result.get("description", ""),
                    "Transcript": result.get("transcript", ""),
                    "Hashtags": result.get("hashtags", ""),
                    "Mentions": result.get("mentions", ""),
                    "Thumbnail Prompt": result.get("thumbnail_prompt", ""),
                    "Output Folder": result.get("output_folder", ""),
                }
                for key, val in mapping.items():
                    txt = self.fields[key]
                    txt.configure(state="normal")
                    txt.delete("1.0", "end")
                    txt.insert("1.0", str(val))
                    txt.configure(state="disabled")

                self.status_var.set("Analysis complete!")
                self.drop_label.configure(text="Done! Drop another file or browse", fg=SUCCESS)
                self.analyze_btn.configure(state="normal")
                self.open_folder_btn.configure(state="normal")
                self.selected_file = None

            self.after(0, update_ui)

        except Exception as e:
            import traceback
            _crash_log(f"Analysis failed: {traceback.format_exc()}")
            error_msg = str(e)

            def show_error():
                self.status_var.set(f"Error: {error_msg[:80]}")
                self.drop_label.configure(fg=ACCENT)
                self.analyze_btn.configure(state="normal")
                messagebox.showerror("Analysis Error", f"Failed to analyze file:\n\n{error_msg[:300]}")

            self.after(0, show_error)

    def _open_folder(self):
        if self.output_folder and os.path.isdir(self.output_folder):
            os.startfile(self.output_folder)

    def _open_inbox(self):
        inbox = config.ANALYZER_INBOX
        if os.path.isdir(inbox):
            os.startfile(inbox)


if __name__ == "__main__":
    app = AnalyzerGUI()
    app.mainloop()
