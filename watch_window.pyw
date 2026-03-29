"""
watch_window.pyw - Drag-and-drop posting window for the Video Auto-Poster.
Drop video files or use Browse to start the upload pipeline.
"""
import os
import sys
import time
import shutil
import threading
import traceback
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from datetime import datetime
from queue_manager import QueueManager
import config

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, PROJECT_DIR)

# ─── Crash log (pythonw hides console output) ────────────────────────────────
CRASH_LOG = os.path.join(PROJECT_DIR, "crash_log.txt")

def _crash_log(msg):
    """Write a timestamped message to crash_log.txt with environment diagnostics."""
    try:
        with open(CRASH_LOG, "a", encoding="utf-8") as f:
            # BEST PRACTICE: Diagnostics
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] EXE: {sys.executable}\n")
            f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
    except Exception:
        pass

def _global_except_hook(exc_type, exc_value, exc_tb):
    """Catch any unhandled exception and write to crash log."""
    tb = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))
    _crash_log(f"UNHANDLED EXCEPTION:\n{tb}")

sys.excepthook = _global_except_hook
threading.excepthook = lambda args: _crash_log(
    f"THREAD EXCEPTION ({args.thread}):\n{''.join(traceback.format_exception(args.exc_type, args.exc_value, args.exc_traceback))}"
)

# ─── Load .env config ────────────────────────────────────────────────────────
def _load_env():
    data = {}
    env_file = os.path.join(PROJECT_DIR, ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
    return data

ENV = _load_env()
WATCH_FOLDER = ENV.get("WATCH_FOLDER", r"D:\Video Auto-Poster")
ATTENTION_FOLDER = ENV.get("ATTENTION_FOLDER", "")

# ─── Colours ──────────────────────────────────────────────────────────────────
BG       = "#1a1a2e"
BG_CARD  = "#16213e"
BG_INPUT = "#0f3460"
FG       = "#e0e0e0"
FG_DIM   = "#8a8a9a"
ACCENT   = "#e94560"
SUCCESS  = "#2ecc71"
WARNING  = "#f39c12"

VIDEO_EXTS = {".mp4", ".avi", ".mov", ".mkv", ".wmv", ".flv", ".webm", ".m4v"}

# ─── Native drag-and-drop (replaces buggy 'windnd' library) ──────────────────
def _hook_drop_files(tk_window, callback):
    """Hook WM_DROPFILES on a Tkinter window using ctypes.
    
    Unlike windnd, this correctly returns 0 for WM_DROPFILES instead of
    chaining the freed drop-handle to the old window procedure (which crashes).
    """
    import ctypes
    from ctypes import wintypes
    import platform

    hwnd = tk_window.winfo_id()

    if platform.architecture()[0] == "64bit":
        GetWindowLongPtr = ctypes.windll.user32.GetWindowLongPtrA
        SetWindowLongPtr = ctypes.windll.user32.SetWindowLongPtrA
        LONG_PTR = ctypes.c_int64
    else:
        GetWindowLongPtr = ctypes.windll.user32.GetWindowLongW
        SetWindowLongPtr = ctypes.windll.user32.SetWindowLongW
        LONG_PTR = ctypes.c_long

    WNDPROC = ctypes.WINFUNCTYPE(LONG_PTR, wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM)
    GWL_WNDPROC = -4
    WM_DROPFILES = 0x0233

    DragQueryFile = ctypes.windll.shell32.DragQueryFileW
    DragQueryFile.argtypes = [ctypes.c_void_p, wintypes.UINT, ctypes.c_wchar_p, wintypes.UINT]
    DragQueryFile.restype = wintypes.UINT

    DragFinish = ctypes.windll.shell32.DragFinish
    DragFinish.argtypes = [ctypes.c_void_p]
    DragFinish.restype = None

    DragAcceptFiles = ctypes.windll.shell32.DragAcceptFiles
    DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]
    DragAcceptFiles.restype = None

    CallWindowProc = ctypes.windll.user32.CallWindowProcW

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
                # Call the Python callback
                callback(files)
            except Exception:
                _crash_log(f"DND WNDPROC ERROR: {traceback.format_exc()}")
            return 0  # Handled — do NOT chain to old proc with freed handle
        return CallWindowProc(old_proc, hwnd, msg, wparam, lparam)

    # Must keep a reference to prevent garbage collection
    tk_window._wndproc_ref = WNDPROC(new_wndproc)
    DragAcceptFiles(hwnd, True)
    SetWindowLongPtr(hwnd, GWL_WNDPROC, tk_window._wndproc_ref)


class WatchWindow(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("⚡ Video Auto-Poster")
        self.configure(bg=BG)
        self.resizable(True, True)
        self.attributes("-topmost", True)

        # Position top-right
        w, h = 420, 560
        screen_w = self.winfo_screenwidth()
        x = screen_w - w - 20
        y = 40
        self.geometry(f"{w}x{h}+{x}+{y}")

        self.qm = QueueManager()
        self.is_processing = False

        # ── Header ──
        hdr = tk.Frame(self, bg=ACCENT, height=40)
        hdr.pack(fill="x")
        hdr.pack_propagate(False)
        tk.Label(
            hdr, text="⚡ Video Auto-Poster", font=("Segoe UI", 12, "bold"),
            bg=ACCENT, fg="white", anchor="w", padx=14
        ).pack(fill="both", expand=True)

        # ── Reservoir Root ──
        path_frame = tk.Frame(self, bg=BG_CARD)
        path_frame.pack(fill="x", padx=8, pady=(8, 0))
        tk.Label(
            path_frame, text="📁 Reservoir Root:", font=("Segoe UI", 8),
            bg=BG_CARD, fg=FG_DIM, anchor="w"
        ).pack(fill="x", padx=8, pady=(4, 0))
        root_lbl = tk.Label(
            path_frame, text=WATCH_FOLDER, font=("Consolas", 8),
            bg=BG_CARD, fg=ACCENT, anchor="w", cursor="hand2", wraplength=380
        )
        root_lbl.pack(fill="x", padx=8, pady=(0, 4))
        root_lbl.bind("<Button-1>", lambda e: os.startfile(WATCH_FOLDER) if os.path.isdir(WATCH_FOLDER) else None)

        # ══════════════════════════════════════════════════════════════════════
        # ── DRAG & DROP ZONE ──
        # ══════════════════════════════════════════════════════════════════════
        self.drop_frame = tk.Frame(self, bg=BG, padx=8, pady=4, height=120)
        self.drop_frame.pack(fill="x")
        self.drop_frame.pack_propagate(False)

        self.drop_zone = tk.Frame(
            self.drop_frame, bg=BG_CARD, cursor="hand2",
            highlightthickness=2, highlightbackground=FG_DIM, highlightcolor=ACCENT
        )
        self.drop_zone.pack(fill="both", expand=True, padx=2, pady=2)

        # Dashed border effect
        self.drop_canvas = tk.Canvas(
            self.drop_zone, bg=BG_CARD, highlightthickness=0, bd=0
        )
        self.drop_canvas.pack(fill="both", expand=True)

        # Draw drop zone content
        self.drop_canvas.bind("<Configure>", self._draw_drop_zone)
        self.drop_canvas.bind("<Button-1>", lambda e: self._browse_files())

        # Enable drag-and-drop (native implementation)
        try:
            _hook_drop_files(self, self._on_drop)
            _crash_log("Drag-and-drop hooked successfully")
        except Exception as e:
            _crash_log(f"Failed to hook drag-and-drop: {e}")

        # ── Reservoir Portal (Queue List) ──
        queue_frame = tk.Frame(self, bg=BG)
        queue_frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        tk.Label(
            queue_frame, text="📅 Reservoir Portal:", font=("Segoe UI", 9, "bold"),
            bg=BG, fg=FG, anchor="w"
        ).pack(fill="x", padx=4, pady=(4, 0))

        # --- Pilot Console (Stage Gate Toggles) ---
        gate_frame = tk.Frame(queue_frame, bg=BG)
        gate_frame.pack(fill="x", padx=4, pady=(0, 4))
        
        self.meta_var = tk.BooleanVar(value=config.CONFIRM_METADATA)
        tk.Checkbutton(
            gate_frame, text="Metadata Gate", variable=self.meta_var,
            font=("Segoe UI", 8), bg=BG, fg=FG, activebackground=BG, 
            selectcolor=BG_INPUT, command=self._save_gate_settings
        ).pack(side="left")

        self.caps_var = tk.BooleanVar(value=config.CONFIRM_CAPTIONS)
        tk.Checkbutton(
            gate_frame, text="Caption Gate", variable=self.caps_var,
            font=("Segoe UI", 8), bg=BG, fg=FG, activebackground=BG,
            selectcolor=BG_INPUT, command=self._save_gate_settings
        ).pack(side="left", padx=10)

        self.final_var = tk.BooleanVar(value=config.CONFIRM_FINAL)
        tk.Checkbutton(
            gate_frame, text="Final Gate", variable=self.final_var,
            font=("Segoe UI", 8), bg=BG, fg=FG, activebackground=BG,
            selectcolor=BG_INPUT, command=self._save_gate_settings
        ).pack(side="left")

        # Use a Treeview for more detailed portal view
        style = ttk.Style()
        style.theme_use("default")
        style.configure("Treeview", 
            background=BG_CARD, foreground=FG, fieldbackground=BG_CARD, 
            borderwidth=0, font=("Segoe UI", 9), rowheight=28
        )
        style.map("Treeview", background=[('selected', ACCENT)])
        style.configure("Treeview.Heading", background=BG_INPUT, foreground=FG, borderwidth=0)

        self.portal = ttk.Treeview(queue_frame, columns=("Status", "Platforms", "ETA"), show="headings", height=8)
        self.portal.heading("Status", text="Status")
        self.portal.heading("Platforms", text="Destinations")
        self.portal.heading("ETA", text="Launch ETA")
        self.portal.column("Status", width=100, anchor="center")
        self.portal.column("Platforms", width=100, anchor="center")
        self.portal.column("ETA", width=150, anchor="w")
        self.portal.pack(fill="both", expand=True, padx=2, pady=2)
        
        self.portal.bind("<Double-1>", self._on_item_double_click)
        self.portal.bind("<Button-3>", self._on_item_right_click) # Right-click

        # ── Activity Log ──
        log_frame = tk.Frame(self, bg=BG)
        log_frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        tk.Label(
            log_frame, text="📝 Activity:", font=("Segoe UI", 8, "bold"),
            bg=BG, fg=FG_DIM, anchor="w"
        ).pack(fill="x", padx=4)

        self.log_text = tk.Text(
            log_frame, font=("Consolas", 8), bg=BG_CARD, fg=FG,
            relief="flat", height=4, wrap="word", state="disabled",
            highlightthickness=1, highlightbackground=BG_INPUT
        )
        self.log_text.pack(fill="both", expand=False, padx=2, pady=2)
        self.log_text.tag_configure("error", foreground=ACCENT)
        self.log_text.tag_configure("success", foreground=SUCCESS)
        self.log_text.tag_configure("info", foreground=FG_DIM)
        self.log_text.tag_configure("warning", foreground=WARNING)

        # ── Bottom Buttons ──
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=8, pady=(0, 8))

        browse_btn = tk.Button(
            btn_frame, text="📂 Browse Files", font=("Segoe UI", 9, "bold"),
            bg=BG_INPUT, fg="white", activebackground=ACCENT,
            activeforeground="white", relief="flat", padx=14, pady=5,
            cursor="hand2", command=self._browse_files
        )
        browse_btn.pack(side="left")

        open_btn = tk.Button(
            btn_frame, text="📁 Open Folder", font=("Segoe UI", 9),
            bg=BG_CARD, fg=FG, activebackground=ACCENT,
            activeforeground="white", relief="flat", padx=10, pady=5,
            cursor="hand2",
            command=lambda: os.startfile(WATCH_FOLDER) if os.path.isdir(WATCH_FOLDER) else None
        )
        open_btn.pack(side="left", padx=(6, 0))

        setup_btn = tk.Button(
            btn_frame, text="⚙️ Setup", font=("Segoe UI", 9),
            bg=BG_CARD, fg=FG, activebackground=ACCENT,
            activeforeground="white", relief="flat", padx=10, pady=5,
            cursor="hand2", command=self._run_setup_wizard
        )
        setup_btn.pack(side="left", padx=(6, 0))

        processed_btn = tk.Button(
            btn_frame, text="✅ Processed", font=("Segoe UI", 9),
            bg=BG_CARD, fg=FG, activebackground=SUCCESS,
            activeforeground="white", relief="flat", padx=10, pady=5,
            cursor="hand2",
            command=lambda: os.startfile(config.PROCESSED_FOLDER) if os.path.isdir(config.PROCESSED_FOLDER) else None
        )
        processed_btn.pack(side="left", padx=(6, 0))

        stop_btn = tk.Button(
            btn_frame, text="✖ Close", font=("Segoe UI", 9),
            bg="#c0392b", fg="white", activebackground=ACCENT,
            activeforeground="white", relief="flat", padx=10, pady=5,
            cursor="hand2", command=self._stop
        )
        stop_btn.pack(side="right")

        # ── Status bar ──
        self.status_var = tk.StringVar(value="● Ready — Drop videos or click Browse")
        tk.Label(
            self, textvariable=self.status_var, font=("Segoe UI", 8),
            bg=BG_INPUT, fg=SUCCESS, anchor="w", padx=10, pady=3
        ).pack(fill="x", side="bottom")

        self.protocol("WM_DELETE_WINDOW", self._stop)

        self._log("Auto-Poster ready", "info")
        self._log("Drag & drop enabled — drop video files here", "info")

        # Start watching the folder too
        self._poll_folder()

    def _draw_drop_zone(self, event=None):
        """Draw the drop zone visual."""
        c = self.drop_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()

        if w < 10 or h < 10:
            return

        # Dashed border rectangle
        dash = (8, 4)
        pad = 10
        c.create_rectangle(
            pad, pad, w - pad, h - pad,
            outline=FG_DIM, width=2, dash=dash
        )

        # Center icon and text
        cy = h // 2
        c.create_text(
            w // 2, cy - 25,
            text="🎬", font=("Segoe UI", 28),
            fill=FG
        )
        c.create_text(
            w // 2, cy + 15,
            text="Drag & Drop Videos Here",
            font=("Segoe UI", 12, "bold"), fill=FG
        )
        c.create_text(
            w // 2, cy + 38,
            text="or click to Browse",
            font=("Segoe UI", 9), fill=FG_DIM
        )
        c.create_text(
            w // 2, cy + 58,
            text=".mp4  .mov  .avi  .mkv  .webm",
            font=("Consolas", 8), fill=FG_DIM
        )

    def _on_drop(self, files):
        """Handle files dropped onto the window."""
        try:
            _crash_log(f"DROP received: {len(files)} file(s)")
            self._handle_dropped_files(files)
        except Exception as e:
            _crash_log(f"DROP ERROR: {traceback.format_exc()}")

    def _handle_dropped_files(self, files):
        """Process dropped files on the main thread."""
        try:
            _crash_log(f"_handle_dropped_files START: {len(files)} file(s)")
            added = 0
            for path in files:
                try:
                    path = str(path).strip().strip('"').strip("'")
                    _crash_log(f"  Path: {path}")

                    self._log(f"Dropped: {os.path.basename(path)}", "info")

                    if not os.path.exists(path):
                        self._log(f"File not found: {path}", "error")
                        _crash_log(f"  File not found, skipping")
                        continue

                    ext = os.path.splitext(path)[1].lower()
                    _crash_log(f"  Extension: {ext}")
                    if ext in VIDEO_EXTS:
                        self._add_to_queue(path)
                        added += 1
                        _crash_log(f"  Added to queue")
                    else:
                        self._log(f"Skipped non-video: {os.path.basename(path)}", "warning")
                        _crash_log(f"  Skipped non-video")
                except Exception as e:
                    _crash_log(f"  ITEM ERROR: {traceback.format_exc()}")
                    self._log(f"Drop error: {e}", "error")

            _crash_log(f"_handle_dropped_files: {added} added")
            if added > 0:
                self._log(f"Added {added} video(s) to queue", "success")
                self._process_queue()
            _crash_log(f"_handle_dropped_files END")
        except Exception as e:
            _crash_log(f"_handle_dropped_files FATAL: {traceback.format_exc()}")

    def _browse_files(self):
        """Open file browser to select videos to add to reservoir."""
        files = filedialog.askopenfilenames(
            title="Select Video Files for Reservoir",
            filetypes=[
                ("Video Files", "*.mp4 *.mov *.avi *.mkv *.wmv *.flv *.webm *.m4v"),
                ("All Files", "*.*")
            ]
        )
        if files:
            self._handle_dropped_files(files)

    def _add_to_queue(self, path):
        """Full ingestion pipeline: move to reservoir, analyze, and queue."""
        name = os.path.basename(path)
        dest = os.path.join(WATCH_FOLDER, name)
        
        def ingest_worker():
            try:
                # 1. Copy to internal reservoir
                os.makedirs(WATCH_FOLDER, exist_ok=True)
                if os.path.exists(dest):
                    base, ext = os.path.splitext(name)
                    final_dest = os.path.join(WATCH_FOLDER, f"{base}_{int(time.time())}{ext}")
                else:
                    final_dest = dest
                
                self._log(f"Ingesting: {name}...", "info")
                shutil.copy2(path, final_dest)
                
                # 2. Analyze immediately
                self.after(0, lambda: self._log(f"Analyzing {name} (Gemini)...", "info"))
                from analyzer import analyze_media
                result = analyze_media(final_dest)
                
                analyzed_path = result.get("output_path")
                if not analyzed_path:
                    self.after(0, lambda: self._log(f"Analysis failed for {name}", "error"))
                    return

                # 3. Add to Persistent Queue as PRIORITY
                self.qm.add_to_queue(analyzed_path, priority=True)
                
                self.after(0, lambda n=name: self._log(f"🔥 Added to Priority Queue: {n}", "success"))
                
            except Exception as e:
                # CRITICAL: Log the FULL traceback so we can see the exact line
                full_tb = traceback.format_exc()
                _crash_log(f"INGEST WORKER ERROR:\n{full_tb}")
                self.after(0, lambda e=e: self._log(f"Ingestion failed: {e}", "error"))
                self.after(0, lambda e=e: self._show_error(f"Failed to process video:\n{e}"))

        threading.Thread(target=ingest_worker, daemon=True).start()

    def _process_queue(self):
        """No longer used locally - the SchedulerService handles this."""
        pass

    def _poll_folder(self):
        """Sync with the persistent queue periodically."""
        try:
            queue = self.qm.load_queue()
            
            # Clear current portal items
            for item in self.portal.get_children():
                self.portal.delete(item)
            
            # Rebuild list from queue
            for item in queue:
                current_status = item.get("status", "queued")
                stage = item.get("current_stage", "analysis")
                platforms = item.get("platforms", "ALL")
                
                # Visual Indicator Mapping
                icons = {
                    "analysis": "🔍 Analysis",
                    "captioning": "💅 Captions",
                    "rendering": "🎬 Render",
                    "uploading": "🚀 Upload"
                }
                icon = icons.get(stage, "🛠️ Logic")
                
                if current_status == "pending":
                    display_status = f"⏳ WAITING: {stage.upper()}"
                elif current_status == "processing":
                    display_status = f"🔄 {icon}"
                elif current_status == "posted":
                    display_status = "✅ POSTED"
                elif current_status == "failed":
                    display_status = "❌ FAILED"
                else:
                    display_status = f"🛒 {icon}"
                
                # Format ETA
                sched_ts = item.get("scheduled_at")
                if sched_ts:
                    diff = sched_ts - time.time()
                    if diff < 60:
                        eta = "🔥 SOON / NOW"
                    else:
                        eta = datetime.fromtimestamp(sched_ts).strftime("%H:%M")
                else:
                    eta = "---"
                    
                self.portal.insert("", "end", text=item['filename'], values=(display_status, platforms, eta))
            
            count = len([i for i in queue if i['status'] == 'queued'])
            self.status_var.set(f"● {count} video(s) in reservoir backlog")
            
        except Exception as e:
            _crash_log(f"POLL ERROR: {e}")
            
        self.after(3000, self._poll_folder)

    def _show_error(self, msg):
        """Show an error popup."""
        self.attributes("-topmost", False)
        messagebox.showerror("⚠ Posting Failed", msg, parent=self)
        self.attributes("-topmost", True)

    def _log(self, message, tag="info"):
        """Add a timestamped line to the activity log."""
        self.log_text.config(state="normal")
        ts = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {message}\n", tag)
        self.log_text.see("end")
        self.log_text.config(state="disabled")

    def _run_setup_wizard(self):
        """Launches the setup wizard in a separate process."""
        try:
            import subprocess
            subprocess.Popen([sys.executable, os.path.join(PROJECT_DIR, "setup_wizard.py")])
            self._log("Setup Wizard launched", "info")
        except Exception as e:
            self._log(f"Failed to launch Setup: {e}", "error")

    def _save_gate_settings(self):
        """Update config based on UI toggles."""
        config.CONFIRM_METADATA = self.meta_var.get()
        config.CONFIRM_CAPTIONS = self.caps_var.get()
        config.CONFIRM_FINAL = self.final_var.get()
        self._log(f"Gates updated - Meta: {config.CONFIRM_METADATA}, Caps: {config.CONFIRM_CAPTIONS}, Final: {config.CONFIRM_FINAL}", "info")

    def _on_item_double_click(self, event):
        """Handle double-click on a reservoir item."""
        selected = self.portal.selection()
        if not selected: return
        item_text = self.portal.item(selected[0], "text")
        self._open_control_center(item_text)

    def _on_item_right_click(self, event):
        """Show context menu on right-click."""
        selected = self.portal.identify_row(event.y)
        if selected:
            self.portal.selection_set(selected)
            menu = tk.Menu(self, tearoff=0, bg=BG_CARD, fg=FG)
            menu.add_command(label="✅ Approve Next Stage", command=lambda: self._approve_item(selected))
            menu.add_command(label="✍️ Alter / Refine (AI)", command=lambda: self._alter_item(selected))
            menu.add_separator()
            menu.add_command(label="🔄 Restart Stage", command=lambda: self._restart_item(selected))
            menu.add_command(label="🗑️ Delete from Queue", command=lambda: self._delete_item(selected))
            menu.post(event.x_root, event.y_root)

    def _open_control_center(self, filename):
        """Open a popup to review metadata and approve/alter."""
        queue = self.qm.load_queue()
        item = next((i for i in queue if i['filename'] == filename), None)
        if not item: return

        top = tk.Toplevel(self)
        top.title(f"🎮 Pilot Control: {filename}")
        top.geometry("450x550")
        top.configure(bg=BG)
        top.attributes("-topmost", True)

        # Load Metadata
        meta_path = os.path.join(os.path.dirname(item['path']), "metadata.json")
        title, tags = "Loading...", "Loading..."
        if os.path.exists(meta_path):
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
                title = meta.get("title", "")
                tags = meta.get("hashtags", "")

        # UI
        tk.Label(top, text="📝 Current Metadata", font=("Segoe UI", 10, "bold"), bg=BG, fg=FG).pack(pady=10)
        
        tk.Label(top, text="Title:", bg=BG, fg=FG_DIM).pack(anchor="w", padx=20)
        title_ent = tk.Entry(top, bg=BG_INPUT, fg=FG, insertbackground=FG, relief="flat")
        title_ent.pack(fill="x", padx=20, pady=2)
        title_ent.insert(0, title)

        tk.Label(top, text="Hashtags:", bg=BG, fg=FG_DIM).pack(anchor="w", padx=20, pady=(10, 0))
        tags_ent = tk.Entry(top, bg=BG_INPUT, fg=FG, insertbackground=FG, relief="flat")
        tags_ent.pack(fill="x", padx=20, pady=2)
        tags_ent.insert(0, tags)

        # Action Buttons
        btn_frame = tk.Frame(top, bg=BG)
        btn_frame.pack(fill="x", pady=20, padx=20)

        def save_and_approve():
            # Update metadata json
            if os.path.exists(meta_path):
                with open(meta_path, "r", encoding="utf-8") as f: meta = json.load(f)
                meta['title'] = title_ent.get()
                meta['hashtags'] = tags_ent.get()
                with open(meta_path, "w", encoding="utf-8") as f: json.dump(meta, f, indent=2)
            self.qm.mark_stage_approved(filename)
            self._log(f"Approved stage for {filename}", "success")
            top.destroy()

        def request_alter():
            feedback = tk.simpledialog.askstring("Refine AI", "What should the AI improve or change?")
            if feedback:
                # 1. Log Global Lesson
                from feedback_engine import log_lesson
                log_lesson(feedback, title, stage=item['current_stage'])
                
                # 2. Store specific feedback in local metadata for immediate retry
                if os.path.exists(meta_path):
                    with open(meta_path, "r", encoding="utf-8") as f: meta = json.load(f)
                    meta['latest_feedback'] = feedback
                    with open(meta_path, "w", encoding="utf-8") as f: json.dump(meta, f, indent=2)
                
                # 3. Restart stage to let AI try again with lesson
                self.qm.update_stage(filename, "analysis", "queued") # Reset to analysis to pick up lesson
                self._log(f"Requested AI Refinement: {feedback}", "info")
                top.destroy()

        tk.Button(btn_frame, text="✅ Approve & Next", bg=SUCCESS, fg="white", relief="flat", padx=10, command=save_and_approve).pack(side="left", expand=True, fill="x")
        tk.Button(btn_frame, text="✍️ Alter (Lessons)", bg=WARNING, fg="white", relief="flat", padx=10, command=request_alter).pack(side="left", expand=True, fill="x", padx=10)
        tk.Button(btn_frame, text="🗑️ Delete", bg=ACCENT, fg="white", relief="flat", padx=10, command=lambda: [self._delete_item_by_name(filename), top.destroy()]).pack(side="left", expand=True, fill="x")

    def _approve_item(self, tree_id):
        filename = self.portal.item(tree_id, "text")
        self.qm.mark_stage_approved(filename)
        self._log(f"Approved {filename}", "success")

    def _alter_item(self, tree_id):
        filename = self.portal.item(tree_id, "text")
        self._open_control_center(filename)

    def _restart_item(self, tree_id):
        filename = self.portal.item(tree_id, "text")
        self.qm.update_stage(filename, "analysis", "queued")
        self._log(f"Restarting pipeline for {filename}", "info")

    def _delete_item_by_name(self, filename):
        queue = self.qm.load_queue()
        new_queue = [i for i in queue if i['filename'] != filename]
        self.qm.save_queue(new_queue)
        self._log(f"Deleted {filename} from reservoir", "warning")

    def _delete_item(self, tree_id):
        filename = self.portal.item(tree_id, "text")
        self._delete_item_by_name(filename)

    def _stop(self):
        self.destroy()


if __name__ == "__main__":
    try:
        os.makedirs(WATCH_FOLDER, exist_ok=True)
        _crash_log("=== Window starting ===")
        app = WatchWindow()
        app.mainloop()
    except Exception:
        _crash_log(f"FATAL:\n{traceback.format_exc()}")
