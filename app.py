import os
import queue
import threading
import time
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from tkinterdnd2 import DND_FILES, TkinterDnD

# Import modular config and engine components
from config import load_settings, save_settings, load_history, save_history
from engine import ConversionJob, ConverterEngine

# --- THE STUNNING STITCH-INSPIRED TKINTER UI ---
class MediaConvertApp(TkinterDnD.Tk):
    def __init__(self):
        super().__init__()
        self.title("All in One Media Converter")
        self.geometry("520x660")
        self.resizable(False, False)
        
        # Color Palette - PREMIUM MODERN DARK MODE
        self.bg_color = "#0B0F19"
        self.card_bg = "#111827"
        self.indigo = "#6366F1"
        self.indigo_hover = "#4F46E5"
        self.border_color = "#1F2937"
        self.text_main = "#F9FAFB"
        self.text_sub = "#9CA3AF"
        self.green = "#10B981"
        self.light_indigo = "#1E1B4B"
        
        # Load user data
        self.settings = load_settings()
        self.history = load_history()
        
        # Queue system
        self.queue = queue.Queue()
        self.queue_list = []
        self.is_converting = False
        self.converter = ConverterEngine(self.settings)
        self.settings_window = None
        self.recent_window = None
        
        self.configure(bg=self.bg_color)
        self.setup_styles()
        self.build_ui()
        
        # Register for DnD
        self.drop_target_register(DND_FILES)
        self.dnd_bind('<<Drop>>', self.handle_dnd_drop)
        self.dnd_bind('<<DragEnter>>', lambda e: self.animate_dnd_border(True))
        self.dnd_bind('<<DragLeave>>', lambda e: self.animate_dnd_border(False))
        
        # Intercept Exit Event to Warm User
        self.protocol("WM_DELETE_WINDOW", self.on_exit)

        # Smooth dynamic progress animation loop
        self.displayed_progress = {}
        self.animate_progress()

    def on_mousewheel(self, event):
        if hasattr(self, 'queue_canvas') and self.queue_canvas.winfo_exists():
            canvas_height = self.queue_canvas.winfo_height()
            frame_height = self.queue_scroll_frame.winfo_height()
            if frame_height > canvas_height:
                self.queue_canvas.yview_scroll(int(-1*(event.delta/120)), "units")

    def bind_mousewheel_recursive(self, widget, callback):
        widget.bind("<MouseWheel>", callback)
        for child in widget.winfo_children():
            self.bind_mousewheel_recursive(child, callback)

    def center_window(self, target_window, width, height):
        # Reliable OS-agnostic coordinate centering calculation
        self.update_idletasks()
        parent_x = self.winfo_x()
        parent_y = self.winfo_y()
        parent_w = self.winfo_width()
        parent_h = self.winfo_height()
        x = parent_x + (parent_w - width) // 2
        y = parent_y + (parent_h - height) // 2
        target_window.geometry(f"{width}x{height}+{x}+{y}")

    def create_icon_button(self, parent, text, icon, fg, command, side=tk.RIGHT, padx=0):
        btn_frame = tk.Frame(parent, bg=self.bg_color, cursor="hand2")
        btn_frame.pack(side=side, padx=padx)
        
        icon_lbl = tk.Label(btn_frame, text=icon, font=("Segoe MDL2 Assets", 8, "bold"), fg=fg, bg=self.bg_color)
        icon_lbl.pack(side=tk.RIGHT, padx=(4, 0))
        
        text_lbl = tk.Label(btn_frame, text=text, font=("Segoe UI Semibold", 8), fg=fg, bg=self.bg_color)
        text_lbl.pack(side=tk.RIGHT)
        
        def on_enter(e):
            if fg == self.indigo:
                hover_fg = "#818CF8"
            elif fg == "red":
                hover_fg = "#F87171"
            elif fg == self.text_sub:
                hover_fg = self.text_main
            else:
                hover_fg = fg
            icon_lbl.configure(fg=hover_fg)
            text_lbl.configure(fg=hover_fg)
            
        def on_leave(e):
            icon_lbl.configure(fg=fg)
            text_lbl.configure(fg=fg)
            
        btn_frame.bind("<Enter>", on_enter)
        btn_frame.bind("<Leave>", on_leave)
        
        btn_frame.bind("<Button-1>", lambda e: command())
        icon_lbl.bind("<Button-1>", lambda e: command())
        text_lbl.bind("<Button-1>", lambda e: command())
        
        return btn_frame

    def setup_styles(self):
        style = ttk.Style(self)
        style.theme_use('clam')
        
        # Modern Flat Popdown listbox configuration
        self.option_add("*TCombobox*Listbox.background", self.card_bg)
        self.option_add("*TCombobox*Listbox.foreground", self.text_main)
        self.option_add("*TCombobox*Listbox.selectBackground", self.light_indigo)
        self.option_add("*TCombobox*Listbox.selectForeground", self.indigo)
        self.option_add("*TCombobox*Listbox.font", ("Segoe UI Semibold", 10))
        self.option_add("*TCombobox*Listbox.relief", "flat")
        self.option_add("*TCombobox*Listbox.borderWidth", "0")

        # Flat custom combobox style
        style.configure("TCombobox", 
                        fieldbackground=self.card_bg, 
                        background=self.card_bg, 
                        bordercolor=self.border_color,
                        lightcolor=self.border_color, 
                        darkcolor=self.border_color, 
                        arrowcolor=self.indigo,
                        foreground=self.text_main, 
                        padding=6,
                        relief="flat",
                        font=("Segoe UI Semibold", 10))
        
        style.map("TCombobox",
                  fieldbackground=[("readonly", self.card_bg), ("active", self.light_indigo)],
                  foreground=[("readonly", self.text_main)],
                  bordercolor=[("focus", self.indigo), ("active", self.border_color)])
        
        # Scrollbar styling
        style.configure("Vertical.TScrollbar",
                        background=self.border_color,
                        troughcolor=self.bg_color,
                        bordercolor=self.bg_color,
                        arrowcolor=self.text_sub)
                        
        # Spinbox styling
        style.configure("TSpinbox",
                        fieldbackground=self.card_bg,
                        background=self.card_bg,
                        foreground=self.text_main,
                        bordercolor=self.border_color,
                        lightcolor=self.border_color,
                        darkcolor=self.border_color,
                        arrowcolor=self.text_main)

    def build_ui(self):
        # --- HEADER SECTION ---
        header_frame = tk.Frame(self, bg=self.bg_color, padx=25, pady=20)
        header_frame.pack(fill=tk.X)
        
        logo_label = tk.Label(header_frame, text="All in One Media Converter", font=("Segoe UI Semibold", 18), fg=self.indigo, bg=self.bg_color)
        logo_label.pack(side=tk.LEFT, anchor=tk.W)
        
        # Gear / Settings Button using Google MDL2 Assets
        self.gear_icon = tk.Label(header_frame, text="\uE713", font=("Segoe MDL2 Assets", 13), fg=self.text_sub, bg=self.bg_color, cursor="hand2")
        self.gear_icon.pack(side=tk.RIGHT, padx=5)
        self.gear_icon.bind("<Button-1>", lambda e: self.open_settings())
        self.gear_icon.bind("<Enter>", lambda e: self.gear_icon.configure(fg=self.indigo))
        self.gear_icon.bind("<Leave>", lambda e: self.gear_icon.configure(fg=self.text_sub))
        
        # Recent Button matching Stitch UI using Google MDL2 Assets Icon
        recent_btn = tk.Frame(header_frame, bg=self.light_indigo, cursor="hand2", padx=12, pady=5)
        recent_btn.pack(side=tk.RIGHT, padx=10)
        
        recent_text = tk.Label(recent_btn, text="\uE81C  RECENT", font=("Segoe MDL2 Assets", 9, "bold"), fg=self.indigo, bg=self.light_indigo)
        recent_text.pack()
        
        def on_recent_hover(enter):
            bg = "#2C2A69" if enter else self.light_indigo
            recent_btn.configure(bg=bg)
            recent_text.configure(bg=bg)
            
        recent_btn.bind("<Enter>", lambda e: on_recent_hover(True))
        recent_btn.bind("<Leave>", lambda e: on_recent_hover(False))
        recent_btn.bind("<Button-1>", lambda e: self.open_recent())
        recent_text.bind("<Button-1>", lambda e: self.open_recent())

        subtitle_label = tk.Label(self, text="A media transcoding app by JannersLSR", font=("Segoe UI", 10), fg=self.text_sub, bg=self.bg_color)
        subtitle_label.place(x=25, y=52)

        # Separator line
        sep = tk.Frame(self, height=1, bg=self.border_color)
        sep.pack(fill=tk.X, padx=25, pady=(5, 10))

        # --- FORMAT SELECTION ROW ---
        format_frame = tk.Frame(self, bg=self.bg_color, padx=35, pady=5)
        format_frame.pack(fill=tk.X)

        tgt_lbl = tk.Label(format_frame, text="TARGET FORMAT", font=("Segoe UI Bold", 8), fg=self.text_sub, bg=self.bg_color)
        tgt_lbl.pack(anchor=tk.W, pady=(0, 5))
        
        # Deep Indigo custom Dropdown to perfectly match target format style
        self.tgt_combo = ttk.Combobox(format_frame, values=["MP4", "WEBM", "GIF", "MOV", "WEBP"], state="readonly")
        self.tgt_combo.set("MP4")
        self.tgt_combo.pack(fill=tk.X, ipady=4)
        
        # Apply special styling options to target combo for distinct premium feel
        self.tgt_combo.bind("<<ComboboxSelected>>", lambda e: (self.on_target_change(e), self.tgt_combo.selection_clear()))
        self.tgt_combo.bind("<FocusIn>", lambda e: self.tgt_combo.selection_clear())

        # --- CENTRAL DRAG & DROP ZONE / QUEUE VIEW ---
        self.center_container = tk.Frame(self, bg=self.bg_color, padx=25, pady=15)
        self.center_container.pack(fill=tk.BOTH, expand=True)
        
        # We will dynamically toggle between DND empty state & Queue active state
        self.show_dnd_state()

        # --- BOTTOM STATUS BAR ---
        self.bottom_bar = tk.Frame(self, bg=self.bg_color, height=40, borderwidth=1, relief=tk.FLAT)
        self.bottom_bar.pack(fill=tk.X, side=tk.BOTTOM)
        
        bottom_sep = tk.Frame(self.bottom_bar, height=1, bg=self.border_color)
        bottom_sep.pack(fill=tk.X, side=tk.TOP)
        
        bottom_pad = tk.Frame(self.bottom_bar, bg=self.bg_color, padx=25, pady=8)
        bottom_pad.pack(fill=tk.BOTH, expand=True)

        self.version_label = tk.Label(bottom_pad, text="VERSION 1.0.0", font=("Segoe UI Semibold", 8), fg=self.text_sub, bg=self.bg_color)
        self.version_label.pack(side=tk.LEFT)

        self.engine_dot = tk.Label(bottom_pad, text="● ENGINE READY", font=("Segoe UI Bold", 8), fg=self.green, bg=self.bg_color)
        self.engine_dot.pack(side=tk.RIGHT)
        
        if not self.converter.ffmpeg_available or not self.converter.magick_available:
            missing = []
            if not self.converter.ffmpeg_available: missing.append("FFmpeg")
            if not self.converter.magick_available: missing.append("ImageMagick")
            self.engine_dot.configure(text=f"● MISSING {', '.join(missing)}", fg="red")

    def show_dnd_state(self):
        # Clear container
        for widget in self.center_container.winfo_children():
            widget.destroy()

        # DND Dotted Canvas
        self.dnd_canvas = tk.Canvas(self.center_container, bg=self.card_bg, highlightthickness=0, bd=0, cursor="hand2")
        self.dnd_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Click action inside the box
        self.dnd_canvas.bind("<Button-1>", lambda e: self.select_files_dialog())
        
        self.draw_dnd_dotted_rect()
        self.center_container.update()
        
        # Draw Icon and Text inside Canvas dynamically
        w, h = 470, 370 # Canvas expected dimensions
        
        # Draw Google-Style Upload Document Icon via Segoe MDL2 Assets
        self.dnd_canvas.create_rectangle(210, 80, 260, 140, fill=self.light_indigo, outline="", width=0, tags="icon_bg")
        self.dnd_canvas.create_oval(200, 70, 270, 140, fill=self.light_indigo, outline="", tags="icon_bg")
        self.dnd_canvas.create_text(235, 105, text="\uE8E5", font=("Segoe MDL2 Assets", 34), fill=self.indigo, tags="icon")

        self.dnd_canvas.create_text(235, 175, text="Drag and drop files here", font=("Segoe UI Semibold", 14), fill=self.text_main, tags="text")
        self.dnd_canvas.create_text(235, 205, text="Maximum file size: 2GB per file", font=("Segoe UI", 9), fill=self.text_sub, tags="subtext")

        # + ADD FILES button inside the canvas as a window object
        add_btn = tk.Frame(self.dnd_canvas, bg=self.indigo, cursor="hand2", padx=25, pady=8)
        add_btn_lbl = tk.Label(add_btn, text="+ ADD FILES", font=("Segoe UI Bold", 9), fg="#FFFFFF", bg=self.indigo)
        add_btn_lbl.pack()
        
        def on_add_hover(enter):
            bg = self.indigo_hover if enter else self.indigo
            add_btn.configure(bg=bg)
            add_btn_lbl.configure(bg=bg)
            
        add_btn.bind("<Enter>", lambda e: on_add_hover(True))
        add_btn.bind("<Leave>", lambda e: on_add_hover(False))
        add_btn.bind("<Button-1>", lambda e: self.select_files_dialog())
        add_btn_lbl.bind("<Button-1>", lambda e: self.select_files_dialog())

        self.dnd_canvas.create_window(235, 265, window=add_btn, anchor=tk.CENTER, tags="btn")
        
        # Redraw triggers on resize
        self.dnd_canvas.bind("<Configure>", lambda e: self.draw_dnd_dotted_rect())

    def draw_dnd_dotted_rect(self, active=False):
        if not hasattr(self, 'dnd_canvas') or not self.dnd_canvas.winfo_exists():
            return
        
        self.dnd_canvas.delete("border")
        w = self.dnd_canvas.winfo_width()
        h = self.dnd_canvas.winfo_height()
        if w < 10 or h < 10:
            return
        
        border_col = self.indigo if active else self.border_color
        # Draw beautiful simulated dotted line border
        self.dnd_canvas.create_rectangle(4, 4, w-4, h-4, outline=border_col, width=2, dash=(6, 4), tags="border")

    def animate_dnd_border(self, active):
        self.draw_dnd_dotted_rect(active)

    def show_queue_state(self):
        # Clear container
        for widget in self.center_container.winfo_children():
            widget.destroy()

        # Queue layout frame
        queue_frame = tk.Frame(self.center_container, bg=self.bg_color)
        queue_frame.pack(fill=tk.BOTH, expand=True)

        # Header of queue
        header_bar = tk.Frame(queue_frame, bg=self.bg_color)
        header_bar.pack(fill=tk.X, pady=(0, 10))
        
        count_lbl = tk.Label(header_bar, text=f"QUEUE ({len(self.queue_list)} FILES)", font=("Segoe UI Bold", 9), fg=self.text_sub, bg=self.bg_color)
        count_lbl.pack(side=tk.LEFT)
        
        clear_btn = tk.Label(header_bar, text="Clear All", font=("Segoe UI Semibold", 9), fg=self.indigo, bg=self.bg_color, cursor="hand2")
        clear_btn.pack(side=tk.RIGHT)
        clear_btn.bind("<Button-1>", lambda e: self.clear_queue())

        # Scrollable Canvas for files
        canvas_container = tk.Frame(queue_frame, bg=self.card_bg, borderwidth=1, relief=tk.FLAT)
        canvas_container.pack(fill=tk.BOTH, expand=True)
        
        # Border outline using canvas
        self.queue_canvas = tk.Canvas(canvas_container, bg=self.card_bg, highlightthickness=0, bd=0)
        self.queue_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        scrollbar = ttk.Scrollbar(canvas_container, orient="vertical", command=self.queue_canvas.yview, style="Vertical.TScrollbar")
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.queue_canvas.configure(yscrollcommand=scrollbar.set)
        self.queue_scroll_frame = tk.Frame(self.queue_canvas, bg=self.card_bg)
        
        # Self-scrolling binder
        self.scroll_window = self.queue_canvas.create_window((0, 0), window=self.queue_scroll_frame, anchor="nw", width=420)
        
        def update_scrollregion(e):
            self.queue_canvas.configure(scrollregion=self.queue_canvas.bbox("all"))
            
        self.queue_scroll_frame.bind("<Configure>", update_scrollregion)
        self.queue_canvas.bind("<Configure>", lambda e: self.queue_canvas.itemconfig(self.scroll_window, width=e.width))

        # Local non-polluting bindings using class methods
        self.queue_canvas.bind("<MouseWheel>", self.on_mousewheel)
        self.queue_scroll_frame.bind("<MouseWheel>", self.on_mousewheel)
        
        # Ensure scroll view starts fully reset at the top
        self.queue_canvas.yview_moveto(0)

        # Render list entries - REVERSED order so newer items list upwards!
        self.queue_widgets = {}
        for index, job in enumerate(reversed(self.queue_list)):
            self.render_queue_item(job, index)

        # Control Row at bottom of list
        control_bar = tk.Frame(queue_frame, bg=self.bg_color, pady=10)
        control_bar.pack(fill=tk.X)

        add_more_lbl = tk.Label(control_bar, text="+ Add More Files", font=("Segoe UI Semibold", 9), fg=self.indigo, bg=self.bg_color, cursor="hand2")
        add_more_lbl.pack(side=tk.LEFT)
        add_more_lbl.bind("<Button-1>", lambda e: self.select_files_dialog())

        if self.is_converting:
            self.action_btn = tk.Frame(control_bar, bg=self.border_color, padx=20, pady=8)
            self.action_btn_lbl = tk.Label(self.action_btn, text="CONVERTING...", font=("Segoe UI Bold", 9), fg=self.text_sub, bg=self.border_color)
            self.action_btn_lbl.pack()
            self.action_btn.pack(side=tk.RIGHT)
        else:
            self.action_btn = tk.Frame(control_bar, bg=self.indigo, cursor="hand2", padx=20, pady=8)
            self.action_btn_lbl = tk.Label(self.action_btn, text="CONVERT ALL", font=("Segoe UI Bold", 9), fg="#FFFFFF", bg=self.indigo)
            self.action_btn_lbl.pack()
            self.action_btn.pack(side=tk.RIGHT)
            
            def on_action_hover(enter):
                bg = self.indigo_hover if enter else self.indigo
                self.action_btn.configure(bg=bg)
                self.action_btn_lbl.configure(bg=bg)
                
            self.action_btn.bind("<Enter>", lambda e: on_action_hover(True))
            self.action_btn.bind("<Leave>", lambda e: on_action_hover(False))
            self.action_btn.bind("<Button-1>", lambda e: self.start_batch_conversion())
            self.action_btn_lbl.bind("<Button-1>", lambda e: self.start_batch_conversion())

    def render_queue_item(self, job: ConversionJob, index):
        item_frame = tk.Frame(self.queue_scroll_frame, bg=self.bg_color, borderwidth=1, relief=tk.FLAT, pady=8, padx=10)
        item_frame.pack(fill=tk.X, pady=4, padx=5)
        
        # Rounded border simulated
        sep = tk.Frame(item_frame, height=1, bg=self.border_color)
        
        # Content frame
        info_frame = tk.Frame(item_frame, bg=self.bg_color)
        info_frame.pack(fill=tk.X)
        
        # Filename
        name_lbl = tk.Label(info_frame, text=job.file_path.name, font=("Segoe UI Semibold", 9), fg=self.text_main, bg=self.bg_color, anchor=tk.W)
        name_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Size & Format Label
        size_mb = os.path.getsize(job.file_path) / (1024 * 1024)
        meta_txt = f"{size_mb:.1f} MB  •  {job.src_format.upper()} → {job.target_format.upper()}"
        meta_lbl = tk.Label(info_frame, text=meta_txt, font=("Segoe UI", 8), fg=self.text_sub, bg=self.bg_color)
        meta_lbl.pack(side=tk.RIGHT, padx=5)

        # Status text
        status_lbl = tk.Label(item_frame, text=job.status, font=("Segoe UI Bold", 8), fg=self.indigo, bg=self.bg_color)
        status_lbl.pack(anchor=tk.E, pady=(2, 2))
        
        if job.status == "Completed":
            status_lbl.configure(fg=self.green)
        elif job.status == "Failed":
            status_lbl.configure(fg="red")
        elif job.status == "Cancelled":
            status_lbl.configure(fg="orange")

        # Custom canvas progress bar - visual sliding progress is handled in animate_progress loop!
        prog_canvas = tk.Canvas(item_frame, height=4, bg=self.border_color, highlightthickness=0, bd=0)
        prog_canvas.pack(fill=tk.X, pady=(2, 5))
        prog_canvas.bind("<Configure>", lambda e, j=job: self.on_progress_canvas_resize(e, j))

        # Action links row using native Google Assets Icons
        links_frame = tk.Frame(item_frame, bg=self.bg_color)
        links_frame.pack(fill=tk.X)
        
        self.queue_widgets[job] = {
            "status_lbl": status_lbl,
            "prog_canvas": prog_canvas,
            "links_frame": links_frame,
            "item_frame": item_frame,
            "last_rendered_status": job.status
        }
        self.bind_mousewheel_recursive(item_frame, self.on_mousewheel)
        
        # Render the action links row using the unified refresh function
        self.refresh_links_row(job)

    # --- DRAG & DROP & CLICK HANDLERS ---
    def handle_dnd_drop(self, event):
        files = self.tk.splitlist(event.data)
        self.animate_dnd_border(False)
        self.add_files_to_queue(files)

    def select_files_dialog(self):
        files = filedialog.askopenfilenames(
            title="Select Media Files",
            filetypes=[("Media Files", "*.mp4 *.webm *.gif *.mov *.webp"), ("All Files", "*.*")]
        )
        if files:
            self.add_files_to_queue(files)

    def on_target_change(self, event):
        target = self.tgt_combo.get()
        for job in self.queue_list:
            if job.status in ["Pending", "Cancelled"]:
                job.target_format = target.lower()
        if len(self.queue_list) > 0:
            self.show_queue_state()

    def add_files_to_queue(self, paths):
        target = self.tgt_combo.get()
        
        valid_extensions = [".mp4", ".webm", ".gif", ".mov", ".webp"]
        added_any = False
        
        for path in paths:
            p = Path(path)
            if not p.is_file():
                continue
                
            ext = p.suffix.lower()
            if ext not in valid_extensions:
                continue
            
            if any(j.file_path == p and j.status == "Pending" for j in self.queue_list):
                continue
                
            job = ConversionJob(p, ext[1:].upper(), target)
            self.queue_list.append(job)
            added_any = True
            
        if added_any:
            self.show_queue_state()

    def remove_from_queue(self, job):
        if job.status in ["Converting", "Pending"] and self.is_converting:
            self.cancel_job(job)
        if job in self.queue_list:
            self.queue_list.remove(job)
        self.displayed_progress.pop(job, None)
        if len(self.queue_list) == 0:
            self.show_dnd_state()
        else:
            self.show_queue_state()

    def clear_queue(self):
        if self.is_converting:
            return
        self.queue_list.clear()
        self.displayed_progress.clear()
        self.show_dnd_state()

    # --- BATCH CONVERSION THREADING PIPELINE ---
    def start_batch_conversion(self):
        if self.is_converting or len(self.queue_list) == 0:
            return
            
        self.is_converting = True
        self.tgt_combo.configure(state="disabled") # Disable target format dropdown during conversion!
        self.action_btn.configure(bg=self.border_color)
        self.action_btn_lbl.configure(bg=self.border_color, fg=self.text_sub, text="CONVERTING...")
        self.engine_dot.configure(text="● ENGINE ACTIVE", fg=self.indigo)
        
        while not self.queue.empty():
            try: self.queue.get_nowait()
            except queue.Empty: break
            
        for job in self.queue_list:
            if job.status == "Pending" or job.status == "Cancelled":
                job.status = "Pending"
                job.progress = 0.0
                job.cancelled = False
                job.process = None
                self.queue.put(job)
                if job in self.queue_widgets:
                    self.refresh_links_row(job)
                    self.queue_widgets[job]["last_rendered_status"] = "Pending"
                
        # Start background worker thread
        self.worker_thread = threading.Thread(target=self.batch_worker_run, daemon=True)
        self.worker_thread.start()

    def batch_worker_run(self):
        output_dir = self.settings.get("default_output_dir", "")
        if output_dir and not os.path.exists(output_dir):
            try: os.makedirs(output_dir)
            except Exception: output_dir = ""

        while not self.queue.empty():
            job = self.queue.get()
            if job.cancelled:
                self.queue.task_done()
                continue
            
            def update_cb(j):
                self.after(0, lambda: self.update_job_ui(j))

            self.converter.convert(job, output_dir=output_dir if output_dir else None, on_progress=update_cb)
            
            if job.status == "Completed":
                hist_item = {
                    "filename": job.file_path.name,
                    "src": job.src_format.upper(),
                    "dest": job.target_format.upper(),
                    "out_path": str(job.dest_path),
                    "time": int(time.time())
                }
                self.history.append(hist_item)
                save_history(self.history)

            self.queue.task_done()
            
        self.after(0, self.on_batch_complete)

    def cancel_job(self, job):
        job.cancelled = True
        if job.process:
            try:
                job.process.kill()
                job.process.wait()
            except Exception:
                pass
        job.status = "Cancelled"
        job.progress = 0.0
        self.update_job_ui(job)

    def retry_job(self, job):
        job.status = "Pending"
        job.progress = 0.0
        job.cancelled = False
        job.process = None
        self.displayed_progress[job] = 0.0
        self.show_queue_state()
        if not self.is_converting:
            self.start_batch_conversion()

    def update_job_ui(self, job):
        if job not in self.queue_widgets:
            return
        
        w_dict = self.queue_widgets[job]
        
        # Update text status
        w_dict["status_lbl"].configure(text=job.status)
        if job.status == "Completed":
            w_dict["status_lbl"].configure(text="Completed", fg=self.green)
            if w_dict.get("last_rendered_status") != "Completed":
                self.refresh_links_row(job)
                w_dict["last_rendered_status"] = "Completed"
        elif job.status == "Failed":
            w_dict["status_lbl"].configure(text="Failed", fg="red")
            if w_dict.get("last_rendered_status") != "Failed":
                self.refresh_links_row(job)
                w_dict["last_rendered_status"] = "Failed"
        elif job.status == "Cancelled":
            w_dict["status_lbl"].configure(text="Cancelled", fg="orange")
            if w_dict.get("last_rendered_status") != "Cancelled":
                self.refresh_links_row(job)
                w_dict["last_rendered_status"] = "Cancelled"
        elif job.status == "Converting":
            w_dict["status_lbl"].configure(text=f"Converting ({int(job.progress*100)}%)", fg=self.indigo)
            if w_dict.get("last_rendered_status") != "Converting":
                self.refresh_links_row(job)
                w_dict["last_rendered_status"] = "Converting"

    def refresh_links_row(self, job):
        w_dict = self.queue_widgets[job]
        for w in w_dict["links_frame"].winfo_children():
            w.destroy()
            
        if job.status == "Completed":
            self.create_icon_button(w_dict["links_frame"], "Folder", "\uE8B7", self.indigo, lambda: os.startfile(job.dest_path.parent), side=tk.LEFT)
            self.create_icon_button(w_dict["links_frame"], "Play", "\uE768", self.indigo, lambda: os.startfile(job.dest_path), side=tk.LEFT, padx=10)
            
        elif job.status == "Failed":
            msg = job.error_msg[:45] + ("..." if len(job.error_msg) > 45 else "")
            err_lbl = tk.Label(w_dict["links_frame"], text=f"Error: {msg}", font=("Segoe UI Italic", 8), fg="red", bg=self.bg_color, cursor="hand2")
            err_lbl.pack(side=tk.LEFT)
            err_lbl.bind("<Button-1>", lambda e: messagebox.showerror("Conversion Failed", job.error_msg))

        elif job.status == "Cancelled":
            self.create_icon_button(w_dict["links_frame"], "Retry", "\uE72C", self.indigo, lambda: self.retry_job(job), side=tk.LEFT)

        elif (job.status == "Pending" or job.status == "Converting") and self.is_converting:
            self.create_icon_button(w_dict["links_frame"], "Cancel", None, "red", lambda: self.cancel_job(job), side=tk.LEFT)

        elif job.status == "Pending" and not self.is_converting:
            self.create_icon_button(w_dict["links_frame"], "Remove", None, self.text_sub, lambda: self.remove_from_queue(job), side=tk.RIGHT)

    def on_batch_complete(self):
        self.is_converting = False
        self.tgt_combo.configure(state="readonly") # Re-enable dropdown!
        self.engine_dot.configure(text="● ENGINE READY", fg=self.green)
        self.show_queue_state()

    # --- SMOOTH SLIDING PROGRESS INDICATOR LOOP ---
    def animate_progress(self):
        step = 0.06 # Smoothness/speed of sliding
        for job in self.queue_list:
            if job not in self.displayed_progress:
                self.displayed_progress[job] = 0.0
            
            curr = self.displayed_progress[job]
            target = job.progress
            
            # Smoothly transition current value to target
            if curr < target:
                new_val = min(curr + step, target)
                self.displayed_progress[job] = new_val
                self.update_progress_bar_ui(job, new_val)
            elif curr > target:
                self.displayed_progress[job] = target
                self.displayed_progress[job] = target
                self.update_progress_bar_ui(job, target)
            else:
                self.update_progress_bar_ui(job, curr)
                
        # 30ms (~33 FPS) periodic call
        self.after(30, self.animate_progress)

    def update_progress_bar_ui(self, job, val):
        if job not in self.queue_widgets:
            return
        w_dict = self.queue_widgets[job]
        canvas = w_dict["prog_canvas"]
        if not canvas.winfo_exists():
            return
        
        w_width = w_dict.get("canvas_width", canvas.winfo_width())
        if w_width <= 1:
            w_width = 400
            
        canvas.delete("prog")
        
        # Color schemes based on job state
        if job.status == "Completed":
            color = self.green
        elif job.status == "Failed":
            color = "red"
        elif job.status == "Cancelled":
            color = "orange"
        elif job.status == "Converting":
            color = self.indigo
        else:
            color = self.text_sub
            
        canvas.create_rectangle(0, 0, int(w_width * val), 4, fill=color, outline="", tags="prog")

    def on_progress_canvas_resize(self, event, job):
        if job not in self.queue_widgets:
            return
        self.queue_widgets[job]["canvas_width"] = event.width
        self.update_progress_bar_ui(job, self.displayed_progress.get(job, 0.0))

    # --- ADVANCED CONFIG SETTINGS DIALOG ---
    def open_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
            self.settings_window.focus_force()
            return
            
        dialog = tk.Toplevel(self)
        self.settings_window = dialog
        dialog.title("Settings")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self)
        
        self.center_window(dialog, 400, 370)

        # Pack save button FIRST to prevent clipping!
        def save_and_close():
            self.settings["default_output_dir"] = folder_var.get()
            self.settings["overwrite_existing"] = overwrite_var.get()
            self.settings["video_crf"] = crf_var.get()
            self.settings["gif_fps"] = fps_var.get()
            self.settings["gif_width"] = width_var.get()
            save_settings(self.settings)
            dialog.destroy()

        save_btn = tk.Button(dialog, text="SAVE CONFIG", command=save_and_close, font=("Segoe UI Bold", 9), fg="#FFFFFF", bg=self.indigo, activebackground=self.indigo_hover, activeforeground="#FFFFFF", bd=0, pady=8)
        save_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=25, pady=15)
        
        # Native Title inside frame rather than custom header
        title_frame = tk.Frame(dialog, bg=self.bg_color, padx=25, pady=12)
        title_frame.pack(fill=tk.X)
        tk.Label(title_frame, text="Advanced Transcode Settings", font=("Segoe UI Semibold", 12), fg=self.indigo, bg=self.bg_color).pack(side=tk.LEFT)

        form = tk.Frame(dialog, bg=self.bg_color, padx=25)
        form.pack(fill=tk.BOTH, expand=True)

        # Output Folder Option
        tk.Label(form, text="Default Output Folder:", font=("Segoe UI Semibold", 9), fg=self.text_main, bg=self.bg_color).pack(anchor=tk.W)
        folder_row = tk.Frame(form, bg=self.bg_color)
        folder_row.pack(fill=tk.X, pady=(2, 10))
        
        folder_var = tk.StringVar(value=self.settings.get("default_output_dir", ""))
        folder_entry = tk.Entry(folder_row, textvariable=folder_var, font=("Segoe UI", 9), bd=1, relief=tk.SOLID, bg=self.card_bg, fg=self.text_main, insertbackground=self.text_main)
        folder_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=3)
        
        def browse_folder():
            folder = filedialog.askdirectory()
            if folder:
                folder_var.set(folder)
                
        browse_btn = tk.Button(folder_row, text="...", font=("Segoe UI", 8), command=browse_folder, bg=self.border_color, bd=0, activebackground=self.border_color, fg=self.text_main)
        browse_btn.pack(side=tk.RIGHT, padx=(5, 0), ipady=1)

        # Overwrite toggle
        overwrite_var = tk.BooleanVar(value=self.settings.get("overwrite_existing", True))
        overwrite_cb = tk.Checkbutton(form, text="Overwrite existing files", variable=overwrite_var, font=("Segoe UI", 9), fg=self.text_main, bg=self.bg_color, activebackground=self.bg_color, activeforeground=self.text_main, selectcolor=self.card_bg)
        overwrite_cb.pack(anchor=tk.W, pady=5)

        # Separator line
        tk.Frame(form, height=1, bg=self.border_color).pack(fill=tk.X, pady=10)

        # Video CRF (Quality) Setting
        tk.Label(form, text="Video Quality (CRF: 0=best, 51=worst):", font=("Segoe UI Semibold", 9), fg=self.text_main, bg=self.bg_color).pack(anchor=tk.W)
        crf_var = tk.StringVar(value=self.settings.get("video_crf", "23"))
        crf_spin = ttk.Spinbox(form, from_=0, to=51, textvariable=crf_var, width=10, style="TSpinbox")
        crf_spin.pack(anchor=tk.W, pady=(2, 10))

        # Animated GIF Scale & Frame Rate Setting
        tk.Label(form, text="GIF FPS / Output Scale Width (px):", font=("Segoe UI Semibold", 9), fg=self.text_main, bg=self.bg_color).pack(anchor=tk.W)
        gif_row = tk.Frame(form, bg=self.bg_color)
        gif_row.pack(fill=tk.X, pady=(2, 10))
        
        fps_var = tk.StringVar(value=self.settings.get("gif_fps", "15"))
        fps_spin = ttk.Spinbox(gif_row, from_=1, to=60, textvariable=fps_var, width=8, style="TSpinbox")
        fps_spin.pack(side=tk.LEFT)
        
        width_var = tk.StringVar(value=self.settings.get("gif_width", "480"))
        width_spin = ttk.Spinbox(gif_row, from_=100, to=1920, textvariable=width_var, width=12, style="TSpinbox")
        width_spin.pack(side=tk.LEFT, padx=10)

    # --- RECENT LOG HISTORICAL DIALOG ---
    def open_recent(self):
        if self.recent_window and self.recent_window.winfo_exists():
            self.recent_window.lift()
            self.recent_window.focus_force()
            return
            
        dialog = tk.Toplevel(self)
        self.recent_window = dialog
        dialog.title("Recent Transcodes")
        dialog.configure(bg=self.bg_color)
        dialog.transient(self)
        
        self.center_window(dialog, 400, 420)

        # Pack clear history button FIRST to prevent clipping completely!
        def clear_history():
            self.history.clear()
            save_history(self.history)
            dialog.destroy()
            self.open_recent()

        clear_h_btn = tk.Button(dialog, text="CLEAR HISTORY", command=clear_history, font=("Segoe UI Bold", 9), fg=self.text_sub, bg=self.border_color, activebackground=self.border_color, activeforeground=self.text_main, bd=0, pady=8)
        clear_h_btn.pack(side=tk.BOTTOM, fill=tk.X, padx=20, pady=15)
        
        # Native Title inside frame rather than custom header
        title_frame = tk.Frame(dialog, bg=self.bg_color, padx=20, pady=12)
        title_frame.pack(fill=tk.X)
        tk.Label(title_frame, text="Recent Transcodes", font=("Segoe UI Semibold", 12), fg=self.indigo, bg=self.bg_color).pack(side=tk.LEFT)

        # List Container
        list_frame = tk.Frame(dialog, bg=self.card_bg, borderwidth=1, relief=tk.FLAT)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 5))
        
        r_canvas = tk.Canvas(list_frame, bg=self.card_bg, highlightthickness=0)
        r_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        r_scroll = ttk.Scrollbar(list_frame, orient="vertical", command=r_canvas.yview, style="Vertical.TScrollbar")
        r_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        r_canvas.configure(yscrollcommand=r_scroll.set)
        r_scroll_frame = tk.Frame(r_canvas, bg=self.card_bg)
        
        r_window = r_canvas.create_window((0, 0), window=r_scroll_frame, anchor="nw", width=340)
        r_scroll_frame.bind("<Configure>", lambda e: r_canvas.configure(scrollregion=r_canvas.bbox("all")))
        r_canvas.bind("<Configure>", lambda e: r_canvas.itemconfig(r_window, width=e.width))

        if len(self.history) == 0:
            tk.Label(r_scroll_frame, text="No recent conversions found.", font=("Segoe UI Italic", 9), fg=self.text_sub, bg=self.card_bg, pady=20).pack()
        else:
            for item in reversed(self.history):
                item_row = tk.Frame(r_scroll_frame, bg=self.bg_color, pady=8, padx=10, borderwidth=1, relief=tk.FLAT)
                item_row.pack(fill=tk.X, pady=3, padx=2)
                
                file_lbl = tk.Label(item_row, text=item["filename"], font=("Segoe UI Semibold", 9), fg=self.text_main, bg=self.bg_color, anchor=tk.W)
                file_lbl.pack(fill=tk.X)
                
                meta_lbl = tk.Label(item_row, text=f"{item['src']} → {item['dest']}", font=("Segoe UI Bold", 8), fg=self.indigo, bg=self.bg_color)
                meta_lbl.pack(side=tk.LEFT, pady=2)
                
                out_path = Path(item["out_path"])
                if out_path.exists():
                    self.create_icon_button(item_row, "Folder", "\uE8B7", self.indigo, lambda p=out_path: os.startfile(p.parent), side=tk.RIGHT, padx=5)
                    self.create_icon_button(item_row, "Play", "\uE768", self.indigo, lambda p=out_path: os.startfile(p), side=tk.RIGHT, padx=5)
                else:
                    missing_lbl = tk.Label(item_row, text="File moved or deleted", font=("Segoe UI Italic", 8), fg=self.text_sub, bg=self.bg_color)
                    missing_lbl.pack(side=tk.RIGHT)

    def on_exit(self):
        if self.is_converting:
            if messagebox.askyesno("Exit Converter", "Conversions are currently in progress. Exiting will cancel all active operations. Exit anyway?"):
                # Terminate any running process
                for job in self.queue_list:
                    if job.status in ["Converting", "Pending"]:
                        job.cancelled = True
                        if job.process:
                            try:
                                job.process.kill()
                                job.process.wait()
                            except Exception:
                                pass
                self.destroy()
        else:
            self.destroy()

if __name__ == "__main__":
    app = MediaConvertApp()
    app.mainloop()
