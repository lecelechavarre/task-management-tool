import os
import json
import logging
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox
from tkinter.scrolledtext import ScrolledText
from todo.models import Task
from todo import storage
from todo.utils import format_duration

# ---------- Configuration ----------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TASKS_PATH = os.path.join(BASE_DIR, "tasks.json")
ARCHIVE_PATH = os.path.join(BASE_DIR, "archive.json")
FINISHED_PATH = os.path.join(BASE_DIR, "finished.json")
LOG_PATH = os.path.join(BASE_DIR, "todo.log")

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

# Modern Color scheme
APP_COLORS = {
    "bg_main": "#f8fafc",
    "bg_card": "#f8fafc",
    "bg_header": "#f8fafc",
    "text_primary": "#1e293b",
    "text_secondary": "#64748b",
    "accent": "#6366f1",
    "border": "#f8fafc",
    "hover": "#f8fafc",
    "success": "#10b981",
    "error": "#ef4444",
    "archive": "#94a3b8"
}

PRIORITY_COLORS = {
    "high": "#f43f5e",
    "medium": "#6366f1",
    "low": "#10b981",
    "done": "#64748b",
    "archived": "#94a3b8"
}

# ---------- App ----------
class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("To-Do Manager")
        
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}")
        self.root.state('zoomed')
        self.root.minsize(800, 520)

        self.style = ttk.Style(root)
        self._setup_style()

        # Load data - archive, finished, then active tasks
        self.archived_tasks = self._load_archived_tasks()
        self.finished_tasks = self._load_finished_tasks()
        self.tasks = self._load_active_tasks()
        self.timers = {}
        self.timer_labels = {}

        self._build_ui()
        self._render_tasks()
        self._render_archive()
        self._render_finished()

    def _bind_mousewheel(self, widget, canvas):
        """Bind mouse wheel events to canvas for scrolling"""
        def on_mousewheel(event):
            # For Windows and MacOS
            if event.num == 5 or event.delta < 0:
                canvas.yview_scroll(1, "units")
            elif event.num == 4 or event.delta > 0:
                canvas.yview_scroll(-1, "units")
        
        # Bind to widget and all its children
        widget.bind("<Enter>", lambda e: self._bind_wheel_to_canvas(canvas))
        widget.bind("<Leave>", lambda e: self._unbind_wheel_from_canvas(canvas))
        
    def _bind_wheel_to_canvas(self, canvas):
        """Bind wheel events when mouse enters the area"""
        # Windows/Linux
        canvas.bind_all("<MouseWheel>", lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), "units"))
        # Linux alternative
        canvas.bind_all("<Button-4>", lambda e: canvas.yview_scroll(-1, "units"))
        canvas.bind_all("<Button-5>", lambda e: canvas.yview_scroll(1, "units"))
        
    def _unbind_wheel_from_canvas(self, canvas):
        """Unbind wheel events when mouse leaves the area"""
        canvas.unbind_all("<MouseWheel>")
        canvas.unbind_all("<Button-4>")
        canvas.unbind_all("<Button-5>")

    def _load_archived_tasks(self):
        """Load archived tasks from archive file"""
        if os.path.exists(ARCHIVE_PATH):
            return storage.load_tasks(ARCHIVE_PATH)
        return []

    def _load_finished_tasks(self):
        """Load finished tasks from finished file"""
        if os.path.exists(FINISHED_PATH):
            return storage.load_tasks(FINISHED_PATH)
        return []

    def _load_active_tasks(self):
        """Load active tasks, excluding archived and finished tasks"""
        all_tasks = storage.load_tasks(TASKS_PATH)
        return [task for task in all_tasks if getattr(task, 'status', 'pending') not in ('archived', 'done')]

    def _setup_style(self):
        try:
            self.style.theme_use("clam")
        except:
            pass
        default_font = ("Segoe UI", 10)
        self.style.configure(".", font=default_font, background=APP_COLORS["bg_main"])
        self.style.configure("TFrame", background=APP_COLORS["bg_main"])
        
        # Remove borders by setting borderwidth=0
        self.style.configure("Card.TFrame",
            background=APP_COLORS["bg_card"], 
            relief="flat",  # Changed from "solid" to "flat"
            borderwidth=0)  # Changed from 1 to 0
        
        self.style.configure("Archive.TFrame",
            background=APP_COLORS["bg_card"], 
            relief="flat",  # Changed from "solid" to "flat"
            borderwidth=0)  # Changed from 1 to 0
        
        self.style.configure("Finished.TFrame",
            background=APP_COLORS["bg_card"], 
            relief="flat",  # Changed from "solid" to "flat"
            borderwidth=0)  # Changed from 1 to 0
        
        self.style.configure("Header.TLabel",
            font=("Segoe UI", 20, "bold"),
            foreground=APP_COLORS["text_primary"], background=APP_COLORS["bg_card"])
        self.style.configure("Muted.TLabel",
            font=("Segoe UI", 9),
            foreground=APP_COLORS["text_secondary"], background=APP_COLORS["bg_card"])
        self.style.configure("Archive.TLabel",
            font=("Segoe UI", 9),
            foreground=APP_COLORS["archive"], background=APP_COLORS["bg_card"])
        self.style.configure("Finished.TLabel",
            font=("Segoe UI", 9),
            foreground=APP_COLORS["success"], background=APP_COLORS["bg_card"])
        self.style.configure("TButton", font=("Segoe UI", 10),
                            padding=(12, 6), relief="flat", borderwidth=1)
        self.style.configure("Accent.TButton", font=("Segoe UI", 10, "bold"),
                            padding=(12, 6), background=APP_COLORS["accent"], foreground="white")
        self.style.configure("Success.TButton", background=APP_COLORS["success"], foreground="white")
        self.style.configure("Danger.TButton", background=APP_COLORS["error"], foreground="white")
        self.style.configure("Archive.TButton", background=APP_COLORS["archive"], foreground="white")
        self.style.configure("TEntry", fieldbackground=APP_COLORS["bg_card"], borderwidth=1, relief="solid")
        self.root.configure(bg=APP_COLORS["bg_main"])

    def _build_ui(self):
        top = ttk.Frame(self.root, padding=(12,10), style="Card.TFrame")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12,6))
        top.columnconfigure(1, weight=1)

        title = ttk.Label(top, text="To-Do Manager", style="Header.TLabel")
        title.grid(row=0, column=0, sticky="w", padx=6)

        search_frame = ttk.Frame(top)
        search_frame.grid(row=0, column=1, sticky="ew", padx=12)
        search_frame.columnconfigure(1, weight=1)
        
        search_icon = ttk.Label(search_frame, text="🔍", font=("Segoe UI", 10))
        search_icon.grid(row=0, column=0, padx=(0,8))
        
        self.search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=self.search_var,
                               font=("Segoe UI", 10))
        search_entry.grid(row=0, column=1, sticky="ew")
        self.search_var.trace_add("write", lambda *args: self._render_tasks())

        filter_frame = ttk.Frame(top)
        filter_frame.grid(row=0, column=2, sticky="e", padx=12)
        
        self.status_filter = tk.StringVar(value="all")
        status_menu = ttk.OptionMenu(filter_frame, self.status_filter, "all", 
                                   "🔄 All", "📝 Pending", "✓ Done",
                                   command=lambda _e: self._render_tasks())
        status_menu.grid(row=0, column=0, padx=6)

        self.priority_filter = tk.StringVar(value="all")
        priority_menu = ttk.OptionMenu(filter_frame, self.priority_filter, "all",
                                     "📊 All", "🔴 High", "🔵 Medium", "🟢 Low",
                                     command=lambda _e: self._render_tasks())
        priority_menu.grid(row=0, column=1, padx=6)

        sort_btn = ttk.Button(filter_frame, text="📅 Newest",
                            command=lambda: self._toggle_sort(sort_btn))
        sort_btn.grid(row=0, column=2, padx=6)

        add_button = ttk.Button(top, text="➕ New Task",
                              style="Accent.TButton",
                              command=self._open_add_window)
        add_button.grid(row=0, column=3, padx=(12,0))

        left = ttk.Frame(self.root, padding=(12,6))
        left.grid(row=1, column=0, sticky="nswe")
        right = ttk.Frame(self.root, padding=(12,6))
        right.grid(row=1, column=1, sticky="nswe")

        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        stats_card = ttk.Frame(left, style="Card.TFrame", padding=12)
        stats_card.grid(row=0, column=0, sticky="nwe", padx=12)
        stats_title = ttk.Label(stats_card, text="Overview", 
                              font=("Segoe UI", 12, "bold"))
        stats_title.grid(row=0, column=0, sticky="w")
        self.stats_label = ttk.Label(stats_card, text="", 
                                   style="Muted.TLabel")
        self.stats_label.grid(row=1, column=0, sticky="w", pady=(8,0))
        
        # Archive card
        archive_card = ttk.Frame(left, style="Archive.TFrame", padding=12)
        archive_card.grid(row=1, column=0, sticky="nwse", padx=12, pady=(12,0))
        left.rowconfigure(1, weight=0)
        
        archive_header = ttk.Frame(archive_card)
        archive_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        archive_header.columnconfigure(1, weight=1)
        
        archive_title = ttk.Label(archive_header, text="🗂️ Archive", 
                                font=("Segoe UI", 12, "bold"),
                                foreground=APP_COLORS["archive"])
        archive_title.grid(row=0, column=0, sticky="w")
        
        self.archive_count_label = ttk.Label(archive_header, text="", 
                                           style="Archive.TLabel")
        self.archive_count_label.grid(row=0, column=1, sticky="e")
        
        self.archive_frame = ttk.Frame(archive_card)
        self.archive_frame.grid(row=1, column=0, sticky="nsew", pady=(8,0))
        archive_card.rowconfigure(1, weight=1)
        
        archive_canvas_height = 150
        self.archive_canvas = tk.Canvas(self.archive_frame, 
                                      borderwidth=0, 
                                      highlightthickness=0, 
                                      bg=APP_COLORS["bg_card"],
                                      height=archive_canvas_height)
        self.archive_scroll = ttk.Scrollbar(self.archive_frame, 
                                          orient="vertical", 
                                          command=self.archive_canvas.yview)
        self.archive_list_frame = ttk.Frame(self.archive_canvas)
        
        self.archive_list_frame.bind(
            "<Configure>",
            lambda e: self.archive_canvas.configure(scrollregion=self.archive_canvas.bbox("all"))
        )
        self.archive_canvas.create_window((0,0), window=self.archive_list_frame, anchor="nw")
        self.archive_canvas.configure(yscrollcommand=self.archive_scroll.set)
        
        self.archive_canvas.grid(row=0, column=0, sticky="nsew")
        self.archive_scroll.grid(row=0, column=1, sticky="ns")
        self.archive_frame.columnconfigure(0, weight=1)
        self.archive_frame.rowconfigure(0, weight=1)

                # Bind mousewheel to archive section
        self._bind_mousewheel(self.archive_frame, self.archive_canvas)
        self._bind_mousewheel(self.archive_canvas, self.archive_canvas)

        # Finished card
        finished_card = ttk.Frame(left, style="Card.TFrame", padding=12)
        finished_card.grid(row=2, column=0, sticky="nwse", padx=12, pady=(12,0))
        left.rowconfigure(2, weight=1)
        
        finished_header = ttk.Frame(finished_card)
        finished_header.grid(row=0, column=0, sticky="ew", pady=(0, 8))
        finished_header.columnconfigure(1, weight=1)
        
        finished_title = ttk.Label(finished_header, text="✨ Finished", 
                                  font=("Segoe UI", 12, "bold"),
                                  foreground=APP_COLORS["success"])
        finished_title.grid(row=0, column=0, sticky="w")
        
        self.finished_count_label = ttk.Label(finished_header, text="", 
                                             style="Finished.TLabel")
        self.finished_count_label.grid(row=0, column=1, sticky="e")
        
        self.finished_frame = ttk.Frame(finished_card)
        self.finished_frame.grid(row=1, column=0, sticky="nsew", pady=(8,0))
        finished_card.rowconfigure(1, weight=1)
        
        finished_canvas_height = 150
        self.finished_canvas = tk.Canvas(self.finished_frame,
                                        borderwidth=0,
                                        highlightthickness=0,
                                        bg=APP_COLORS["bg_card"],
                                        height=finished_canvas_height)
        self.finished_scroll = ttk.Scrollbar(self.finished_frame,
                                            orient="vertical",
                                            command=self.finished_canvas.yview)
        self.finished_list_frame = ttk.Frame(self.finished_canvas)
        self.finished_list_frame.bind(
            "<Configure>",
            lambda e: self.finished_canvas.configure(scrollregion=self.finished_canvas.bbox("all"))
        )
        self.finished_canvas.create_window((0,0), window=self.finished_list_frame, anchor="nw")
        self.finished_canvas.configure(yscrollcommand=self.finished_scroll.set)
        self.finished_canvas.grid(row=0, column=0, sticky="nsew")
        self.finished_scroll.grid(row=0, column=1, sticky="ns")
        self.finished_frame.columnconfigure(0, weight=1)
        self.finished_frame.rowconfigure(0, weight=1)

        # Bind mousewheel to finished section
        self._bind_mousewheel(self.finished_frame, self.finished_canvas)
        self._bind_mousewheel(self.finished_canvas, self.finished_canvas)

        self._update_stats()

        self.task_canvas = tk.Canvas(right, borderwidth=0, highlightthickness=0, bg=APP_COLORS["bg_main"])
        self.task_scroll = ttk.Scrollbar(right, orient="vertical", command=self.task_canvas.yview)
        self.task_frame = ttk.Frame(self.task_canvas, style="TFrame")

        self.task_frame.bind(
            "<Configure>",
            lambda e: self.task_canvas.configure(scrollregion=self.task_canvas.bbox("all"))
        )
        self.task_canvas.create_window((0,0), window=self.task_frame, anchor="nw")
        self.task_canvas.configure(yscrollcommand=self.task_scroll.set)

        self.task_canvas.grid(row=0, column=0, sticky="nswe")
        self.task_scroll.grid(row=0, column=1, sticky="ns")

        # Bind mousewheel to main task list
        self._bind_mousewheel(right, self.task_canvas)
        self._bind_mousewheel(self.task_canvas, self.task_canvas)

        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        self.sort_newest = True

    def _render_archive(self):
        for child in self.archive_list_frame.winfo_children():
            child.destroy()
        
        if not self.archived_tasks:
            no_archive_label = ttk.Label(self.archive_list_frame, 
                                       text="No archived tasks", 
                                       style="Archive.TLabel")
            no_archive_label.pack(pady=10)
            return
        
        sorted_archive = sorted(self.archived_tasks, 
                              key=lambda t: t.created_at, 
                              reverse=True)
        
        for i, task in enumerate(sorted_archive):
            self._create_archive_item(task, i)

        self._update_stats()

    def _render_finished(self):
        for child in self.finished_list_frame.winfo_children():
            child.destroy()

        if not self.finished_tasks:
            no_finished_label = ttk.Label(self.finished_list_frame,
                                         text="No finished tasks",
                                         style="Finished.TLabel")
            no_finished_label.pack(pady=10)
            return

        sorted_finished = sorted(self.finished_tasks, key=lambda t: t.created_at, reverse=True)
        for i, task in enumerate(sorted_finished):
            self._create_finished_item(task, i)

        self._update_stats()

    def _truncate_text(self, text, max_length=40):
        if len(text) <= max_length:
            return text
        return text[:max_length-3] + "..."

    def _create_archive_item(self, task: Task, index: int):
        item_frame = ttk.Frame(self.archive_list_frame, style="Card.TFrame", padding=8)
        item_frame.pack(fill="x", padx=2, pady=2)
        
        item_frame.columnconfigure(0, weight=0, minsize=30)
        item_frame.columnconfigure(1, weight=1, minsize=100)
        item_frame.columnconfigure(2, weight=0, minsize=80)
        
        icon_label = ttk.Label(item_frame, text="🗂️", font=("Segoe UI", 10))
        icon_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        
        truncated_title = self._truncate_text(task.title, max_length=25)
        title_label = ttk.Label(item_frame, 
                              text=truncated_title, 
                              font=("Segoe UI", 10),
                              foreground=APP_COLORS["archive"],
                              cursor="hand2")
        title_label.grid(row=0, column=1, sticky="w")
        title_label.bind("<Button-1>", lambda e, t=task: self._show_archived_task_details(t))
        
        btn_frame = ttk.Frame(item_frame)
        btn_frame.grid(row=0, column=2, sticky="e")
        
        restore_btn = ttk.Button(btn_frame, text="↩", 
                               width=3,
                               style="Archive.TButton",
                               command=lambda t=task: self._restore_task(t))
        restore_btn.grid(row=0, column=0, padx=2)
        
        delete_btn = ttk.Button(btn_frame, text="🗑️", 
                              width=3,
                              style="Danger.TButton",
                              command=lambda t=task: self._permanently_delete_task(t))
        delete_btn.grid(row=0, column=1, padx=2)

    def _create_finished_item(self, task: Task, index: int):
        item_frame = ttk.Frame(self.finished_list_frame, style="Card.TFrame", padding=8)
        item_frame.pack(fill="x", padx=2, pady=2)
        
        item_frame.columnconfigure(0, weight=0, minsize=30)
        item_frame.columnconfigure(1, weight=1, minsize=100)
        item_frame.columnconfigure(2, weight=0, minsize=80)
        
        icon_label = ttk.Label(item_frame, text="✨", font=("Segoe UI", 10))
        icon_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        
        truncated_title = self._truncate_text(task.title, max_length=25)
        title_label = ttk.Label(item_frame, 
                              text=f"✓ {truncated_title}", 
                              font=("Segoe UI", 10),
                              foreground=APP_COLORS["text_secondary"],
                              cursor="hand2")
        title_label.grid(row=0, column=1, sticky="w")
        title_label.bind("<Button-1>", lambda e, t=task: self._show_finished_task_details(t))
        
        btn_frame = ttk.Frame(item_frame)
        btn_frame.grid(row=0, column=2, sticky="e")
        
        reopen_btn = ttk.Button(btn_frame, text="🔄", 
                               width=3,
                               command=lambda t=task: self._undo_done(t))
        reopen_btn.grid(row=0, column=0, padx=2)
        
        delete_btn = ttk.Button(btn_frame, text="🗑️", 
                              width=3,
                              style="Danger.TButton",
                              command=lambda t=task: self._permanently_delete_finished_task(t))
        delete_btn.grid(row=0, column=1, padx=2)

    def _show_archived_task_details(self, task: Task):
        modal = tk.Toplevel(self.root)
        modal.transient(self.root)
        modal.grab_set()
        
        window_width = 700
        window_height = 550
        header_height = 80
        
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        
        position_x = root_x + (root_width - window_width) // 2
        position_y = root_y + header_height
        
        modal.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        modal.title("Archived Task Details")
        modal.configure(bg=APP_COLORS["bg_main"])
        modal.resizable(False, False)

        container = ttk.Frame(modal, style="Card.TFrame", padding=0)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        header = tk.Frame(container, bg=APP_COLORS["archive"])
        header.pack(fill="x")
        
        header_content = tk.Frame(header, bg=header["bg"])
        header_content.pack(fill="x", padx=25, pady=20)

        status_label = tk.Label(header_content,
            text="🗂️ ARCHIVED TASK",
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 11))
        status_label.pack(anchor="w", pady=(0, 10))
        
        title_label = tk.Label(header_content,
            text=task.title,
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 24, "bold"),
            wraplength=600,
            justify="left")
        title_label.pack(fill="x", anchor="w")

        content = ttk.Frame(container, style="Card.TFrame", padding=(25, 20))
        content.pack(fill="both", expand=True)

        desc_frame = ttk.Frame(content)
        desc_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        desc_header = ttk.Label(desc_frame,
            text="📝 Description",
            font=("Segoe UI", 12, "bold"),
            foreground=APP_COLORS["text_primary"])
        desc_header.pack(anchor="w", pady=(0, 10))
        
        desc_text = ScrolledText(desc_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            height=12,
            relief="flat",
            borderwidth=1)
        desc_text.pack(fill="both", expand=True)
        desc_text.insert("1.0", task.description if task.description else "(No description provided)")
        desc_text.configure(state="disabled")

        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill="x")

        restore_btn = ttk.Button(btn_frame,
            text="↩️ Restore Task",
            style="Archive.TButton",
            command=lambda: [modal.destroy(), self._restore_task(task)])
        restore_btn.pack(side="left")

        close_btn = ttk.Button(btn_frame,
            text="Close",
            command=modal.destroy)
        close_btn.pack(side="right")

    def _show_finished_task_details(self, task: Task):
        modal = tk.Toplevel(self.root)
        modal.transient(self.root)
        modal.grab_set()
        
        window_width = 700
        window_height = 550
        header_height = 80
        
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        
        position_x = root_x + (root_width - window_width) // 2
        position_y = root_y + header_height
        
        modal.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        modal.title("Finished Task Details")
        modal.configure(bg=APP_COLORS["bg_main"])
        modal.resizable(False, False)

        container = ttk.Frame(modal, style="Card.TFrame", padding=0)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        header = tk.Frame(container, bg=APP_COLORS["success"])
        header.pack(fill="x")
        
        header_content = tk.Frame(header, bg=header["bg"])
        header_content.pack(fill="x", padx=25, pady=20)

        status_label = tk.Label(header_content,
            text="✨ FINISHED TASK",
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 11))
        status_label.pack(anchor="w", pady=(0, 10))
        
        title_label = tk.Label(header_content,
            text=task.title,
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 24, "bold"),
            wraplength=600,
            justify="left")
        title_label.pack(fill="x", anchor="w")

        content = ttk.Frame(container, style="Card.TFrame", padding=(25, 20))
        content.pack(fill="both", expand=True)

        desc_frame = ttk.Frame(content)
        desc_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        desc_header = ttk.Label(desc_frame,
            text="📝 Description",
            font=("Segoe UI", 12, "bold"),
            foreground=APP_COLORS["text_primary"])
        desc_header.pack(anchor="w", pady=(0, 10))
        
        desc_text = ScrolledText(desc_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            height=12,
            relief="flat",
            borderwidth=1)
        desc_text.pack(fill="both", expand=True)
        desc_text.insert("1.0", task.description if task.description else "(No description provided)")
        desc_text.configure(state="disabled")

        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill="x")

        reopen_btn = ttk.Button(btn_frame,
            text="🔄 Reopen Task",
            command=lambda: [modal.destroy(), self._undo_done(task)])
        reopen_btn.pack(side="left")

        delete_btn = ttk.Button(btn_frame,
            text="🗑️ Delete Permanently",
            style="Danger.TButton",
            command=lambda: [modal.destroy(), self._permanently_delete_finished_task(task)])
        delete_btn.pack(side="left", padx=8)

        close_btn = ttk.Button(btn_frame,
            text="Close",
            command=modal.destroy)
        close_btn.pack(side="right")

    def _restore_task(self, task: Task):
        self.archived_tasks = [t for t in self.archived_tasks if t.id != task.id]
        task.status = "pending"
        self.tasks.append(task)
        
        storage.save_tasks(TASKS_PATH, self.tasks)
        storage.save_tasks(ARCHIVE_PATH, self.archived_tasks)
        
        self._update_stats()
        self._render_tasks()
        self._render_archive()
        
        logging.info(f"Restored task {task.id}: {task.title}. Remaining archived: {len(self.archived_tasks)}")

    def _permanently_delete_task(self, task: Task):
        if messagebox.askyesno("Permanent Delete", 
                             f"Permanently delete task '{task.title}'?\n\nThis action cannot be undone."):
            self.archived_tasks = [t for t in self.archived_tasks if t.id != task.id]
            storage.save_tasks(ARCHIVE_PATH, self.archived_tasks)
            self._update_stats()
            self._render_archive()
            logging.info(f"Permanently deleted task {task.id}: {task.title}. Remaining archived: {len(self.archived_tasks)}")

    def _permanently_delete_finished_task(self, task: Task):
        if messagebox.askyesno("Permanent Delete", 
                             f"Permanently delete finished task '{task.title}'?\n\nThis action cannot be undone."):
            self.finished_tasks = [t for t in self.finished_tasks if t.id != task.id]
            storage.save_tasks(FINISHED_PATH, self.finished_tasks)
            self._update_stats()
            self._render_finished()
            logging.info(f"Permanently deleted finished task {task.id}: {task.title}. Remaining finished: {len(self.finished_tasks)}")

    def _archive_task(self, task: Task):
        if task.id in self.timers:
            self._stop_timer(task.id)
        
        self.tasks = [t for t in self.tasks if t.id != task.id]
        
        task.status = "archived"
        self.archived_tasks.append(task)
        
        storage.save_tasks(TASKS_PATH, self.tasks)
        storage.save_tasks(ARCHIVE_PATH, self.archived_tasks)
        
        self._render_tasks()
        self._update_stats()
        self._render_archive()
        
        logging.info(f"Archived task {task.id}: {task.title}")

    def _toggle_sort(self, btn):
        self.sort_newest = not self.sort_newest
        btn.config(text=("📅 Newest" if self.sort_newest else "📅 Oldest"))
        self._render_tasks()

    def _update_stats(self):
        total = len(self.tasks)
        pending = sum(1 for t in self.tasks if t.status != "done")
        done = len(self.finished_tasks)
        high = sum(1 for t in self.tasks if t.priority == "high" and t.status != "done")
        archived = len(self.archived_tasks)
        
        txt = f"Total: {total}   Pending: {pending}   Done: {done}   High priority: {high}"
        self.stats_label.config(text=txt)
        
        archive_txt = f"({archived} items)"
        self.archive_count_label.config(text=archive_txt)
        self.finished_count_label.config(text=f"({done} items)")

    def _render_tasks(self):
        for child in self.task_frame.winfo_children():
            child.destroy()

        q = self.search_var.get().strip().lower()
        status_f = self.status_filter.get()
        prio_f = self.priority_filter.get()

        tasks = list(self.tasks)
        if status_f != "all":
            status_map = {"🔄 All": "all", "📝 Pending": "pending", "✓ Done": "done"}
            actual_status = status_map.get(status_f, status_f)
            if actual_status != "all":
                tasks = [t for t in tasks if t.status == actual_status]
        if prio_f != "all":
            prio_map = {"📊 All": "all", "🔴 High": "high", "🔵 Medium": "medium", "🟢 Low": "low"}
            actual_prio = prio_map.get(prio_f, prio_f)
            if actual_prio != "all":
                tasks = [t for t in tasks if t.priority == actual_prio]
        if q:
            tasks = [t for t in tasks if q in t.title.lower() or q in t.description.lower()]

        tasks.sort(key=lambda t: t.created_at, reverse=self.sort_newest)

        for i, task in enumerate(tasks):
            self._create_task_card(task, i)

        self._update_stats()

    def _create_task_card(self, task: Task, index: int):
        outer_card = ttk.Frame(self.task_frame, style="Card.TFrame")
        outer_card.grid(row=index, column=0, sticky="ew", padx=12, pady=6)
        outer_card.columnconfigure(0, weight=1)

        card = ttk.Frame(outer_card, style="Card.TFrame", padding=16)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(1, weight=1)

        priority_icons = {
            "high": "🔴",
            "medium": "🔵",
            "low": "🟢",
            "done": "✓"
        }
        color_key = "done" if task.status == "done" else task.priority
        badge_color = PRIORITY_COLORS.get(color_key, "#999999")
        icon = priority_icons.get(color_key, "•")
        badge_text = f"{icon} {task.priority.title()}" if task.status != "done" else f"{icon} Completed"
        
        badge = tk.Label(card, 
            text=badge_text,
            bg=badge_color, 
            fg="white", 
            padx=10, 
            pady=4, 
            font=("Segoe UI", 9, "bold"),
            borderwidth=0,
            relief="flat"
        )
        badge.grid(row=0, column=0, rowspan=2, sticky="nsw", padx=(0,16))

        # Fixed width title label - exactly 40 characters
        title_txt = self._truncate_text(task.title, max_length=40)
        if task.status == "done":
            title_txt = "✓ " + title_txt
        
        title_lbl = ttk.Label(card, 
            text=title_txt, 
            font=("Segoe UI", 12, "bold"),
            foreground=APP_COLORS["text_primary"] if task.status != "done" else APP_COLORS["text_secondary"],
            cursor="hand2",
            width=40)
        title_lbl.grid(row=0, column=1, sticky="w")
        
        title_lbl.bind("<Button-1>", lambda e, t=task: self._show_task_details(t))

        desc_txt = task.description if task.description else "(no description)"
        desc_lbl = ttk.Label(card, text=desc_txt, style="Muted.TLabel")
        desc_lbl.grid(row=1, column=1, sticky="w")

        meta = f"Created: {task.created_at.split('T')[0]}"
        if task.due_date:
            meta += f"  •  Due: {task.due_date}"
        meta_lbl = ttk.Label(card, text=meta, style="Muted.TLabel")
        meta_lbl.grid(row=2, column=1, sticky="w", pady=(6,0))

        btn_frame = ttk.Frame(card)
        btn_frame.grid(row=0, column=2, rowspan=3, sticky="e")

        edit_btn = ttk.Button(btn_frame, text="📝 Edit", 
                            command=lambda t=task: self._open_edit_window(t))
        edit_btn.grid(row=0, column=0, padx=4, pady=2)

        if task.status != "done":
            done_btn = ttk.Button(btn_frame, text="✓ Done", 
                                style="Success.TButton",
                                command=lambda t=task: self._mark_done(t))
        else:
            done_btn = ttk.Button(btn_frame, text="🔄 Reopen",
                                command=lambda t=task: self._undo_done(t))
        done_btn.grid(row=0, column=1, padx=4, pady=2)

        archive_btn = ttk.Button(btn_frame, text="🗂️ Archive",
                               style="Archive.TButton",
                               command=lambda t=task: self._archive_task(t))
        archive_btn.grid(row=0, column=2, padx=4, pady=2)

        timer_frame = ttk.Frame(btn_frame)
        timer_frame.grid(row=1, column=0, columnspan=3, pady=(8,0))

        elapsed = task.remaining_seconds if task.remaining_seconds is not None else 0
        elapsed_lbl = ttk.Label(timer_frame, 
                              text=f"⏱ {format_duration(elapsed)}",
                              font=("Segoe UI", 9, "bold"),
                              foreground=APP_COLORS["text_secondary"])
        elapsed_lbl.grid(row=0, column=0, padx=(0,6))
        self.timer_labels[task.id] = elapsed_lbl

        if task.id not in self.timers and task.status != "done":
            self._start_timer(task)

    def _show_task_details(self, task: Task):
        modal = tk.Toplevel(self.root)
        modal.transient(self.root)
        modal.grab_set()
        
        window_width = 700
        window_height = 550
        header_height = 80
        
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        
        position_x = root_x + (root_width - window_width) // 2
        position_y = root_y + header_height
        
        modal.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        modal.title("Task Details")
        modal.configure(bg=APP_COLORS["bg_main"])
        modal.resizable(False, False)

        container = ttk.Frame(modal, style="Card.TFrame", padding=0)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        header = tk.Frame(container, bg=PRIORITY_COLORS.get("done" if task.status == "done" else task.priority, "#999999"))
        header.pack(fill="x")
        
        header_content = tk.Frame(header, bg=header["bg"])
        header_content.pack(fill="x", padx=25, pady=20)

        status_frame = tk.Frame(header_content, bg=header["bg"])
        status_frame.pack(fill="x", pady=(0, 10))
        
        status_text = "✨ COMPLETED" if task.status == "done" else f"{task.priority.upper()} PRIORITY"
        status_label = tk.Label(status_frame,
            text=status_text,
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 11))
        status_label.pack(side="left")
        
        title_label = tk.Label(header_content,
            text=task.title,
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 24, "bold"),
            wraplength=600,
            justify="left")
        title_label.pack(fill="x", anchor="w")

        content = ttk.Frame(container, style="Card.TFrame", padding=(25, 20))
        content.pack(fill="both", expand=True)

        meta_frame = ttk.Frame(content)
        meta_frame.pack(fill="x", pady=(0, 20))
        
        time_frame = ttk.Frame(meta_frame)
        time_frame.pack(side="left")
        
        if task.id in self.timers:
            time_status = "⌛ Active"
            time_color = APP_COLORS["success"]
        else:
            time_status = "⏸️ Paused" if task.status != "done" else "✨ Completed"
            time_color = APP_COLORS["text_secondary"]
        
        time_label = ttk.Label(time_frame,
            text=time_status,
            font=("Segoe UI", 10, "bold"),
            foreground=time_color)
        time_label.pack(anchor="w")
        
        elapsed_label = ttk.Label(time_frame,
            text=f"Elapsed Time: {format_duration(task.remaining_seconds)}",
            style="Muted.TLabel")
        elapsed_label.pack(anchor="w")

        dates_frame = ttk.Frame(meta_frame)
        dates_frame.pack(side="right")
        
        created_date = datetime.fromisoformat(task.created_at).strftime("%B %d, %Y at %H:%M")
        created_label = ttk.Label(dates_frame,
            text=f"📅 Created: {created_date}",
            style="Muted.TLabel")
        created_label.pack(anchor="e")
        
        if task.due_date:
            due_label = ttk.Label(dates_frame,
                text=f"🎯 Due: {task.due_date}",
                style="Muted.TLabel")
            due_label.pack(anchor="e")

        desc_frame = ttk.Frame(content)
        desc_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        desc_header = ttk.Label(desc_frame,
            text="📝 Description",
            font=("Segoe UI", 12, "bold"),
            foreground=APP_COLORS["text_primary"])
        desc_header.pack(anchor="w", pady=(0, 10))
        
        desc_text = ScrolledText(desc_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            height=8,
            relief="flat",
            borderwidth=1)
        desc_text.pack(fill="both", expand=True)
        desc_text.insert("1.0", task.description if task.description else "(No description provided)")
        desc_text.configure(state="disabled")

        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill="x")

        edit_btn = ttk.Button(btn_frame,
            text="📝 Edit Task",
            style="Accent.TButton",
            command=lambda: [modal.destroy(), self._open_edit_window(task)])
        edit_btn.pack(side="left")

        close_btn = ttk.Button(btn_frame,
            text="Close",
            command=modal.destroy)
        close_btn.pack(side="right")

    def _open_add_window(self):
        self._open_task_window()

    def _open_edit_window(self, task: Task):
        self._open_task_window(task)

    def _open_task_window(self, task: Task = None):
        win = tk.Toplevel(self.root)
        win.transient(self.root)
        win.grab_set()
        
        window_width = 700
        window_height = 600
        header_height = 80
        
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        
        position_x = root_x + (root_width - window_width) // 2
        position_y = root_y + header_height
        
        win.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        win.title("Add Task" if task is None else "Edit Task")
        win.configure(bg=APP_COLORS["bg_main"])
        win.resizable(True, True)

        container = ttk.Frame(win, style="Card.TFrame", padding=0)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        is_new = task is None
        header_color = APP_COLORS["accent"] if is_new else PRIORITY_COLORS.get(task.priority, "#999999")
        header = tk.Frame(container, bg=header_color)
        header.pack(fill="x")
        
        header_content = tk.Frame(header, bg=header["bg"])
        header_content.pack(fill="x", padx=25, pady=20)

        title_text = "✨ NEW TASK" if is_new else "📝 EDIT TASK"
        header_label = tk.Label(header_content,
            text=title_text,
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 11))
        header_label.pack(anchor="w", pady=(0, 10))

        title_var = tk.StringVar(value=task.title if task else "")
        title_entry = tk.Entry(header_content,
            textvariable=title_var,
            font=("Segoe UI", 24, "bold"),
            fg="white",
            bg=header_color,
            insertbackground="white",
            relief="flat",
            highlightthickness=0,
            width=40)
        title_entry.pack(fill="x", pady=(5, 0))
        
        content = ttk.Frame(container, style="Card.TFrame", padding=(25, 20))
        content.pack(fill="both", expand=True)
        
        priority_frame = ttk.Frame(content)
        priority_frame.pack(fill="x", pady=(0, 20))
        
        priority_label = ttk.Label(priority_frame,
            text="🎯 Priority Level",
            font=("Segoe UI", 12, "bold"),
            foreground=APP_COLORS["text_primary"])
        priority_label.pack(side="left")
        
        prio_var = tk.StringVar(value=task.priority if task else "medium")
        priority_icons = {"high": "🔴", "medium": "🔵", "low": "🟢"}
        prio_menu = ttk.OptionMenu(priority_frame, prio_var, prio_var.get(),
            *[f"{priority_icons[p]} {p.title()}" for p in ["high", "medium", "low"]])
        prio_menu.pack(side="left", padx=(10, 0))

        due_frame = ttk.Frame(content)
        due_frame.pack(fill="x", pady=(0, 20))
        
        due_label = ttk.Label(due_frame,
            text="📅 Due Date",
            font=("Segoe UI", 12, "bold"),
            foreground=APP_COLORS["text_primary"])
        due_label.pack(side="left")
        
        due_var = tk.StringVar(value=task.due_date if task and task.due_date else "")
        due_entry = ttk.Entry(due_frame, textvariable=due_var)
        due_entry.pack(side="left", padx=(10, 0))
        due_hint = ttk.Label(due_frame,
            text="Format: YYYY-MM-DD",
            style="Muted.TLabel")
        due_hint.pack(side="left", padx=(10, 0))

        desc_frame = ttk.Frame(content)
        desc_frame.pack(fill="both", expand=True, pady=(0, 10))
        
        desc_header = ttk.Label(desc_frame,
            text="📝 Description",
            font=("Segoe UI", 12, "bold"),
            foreground=APP_COLORS["text_primary"])
        desc_header.pack(anchor="w", pady=(0, 10))
        
        desc_text = ScrolledText(desc_frame,
            wrap=tk.WORD,
            font=("Segoe UI", 10),
            height=12,
            relief="flat",
            borderwidth=1)
        desc_text.pack(fill="both", expand=True)
        if task and task.description:
            desc_text.insert("1.0", task.description)

        btn_frame = ttk.Frame(content)
        btn_frame.pack(fill="x")

        cancel_btn = ttk.Button(btn_frame,
            text="Cancel",
            command=win.destroy)
        cancel_btn.pack(side="right")

        save_btn = ttk.Button(btn_frame,
            text="💾 Save Task",
            style="Accent.TButton")
        save_btn.pack(side="right", padx=(0, 10))

        def on_save():
            title_text = title_var.get().strip()
            if not title_text:
                messagebox.showwarning("Validation error", "Title is required.")
                return
            description = desc_text.get("1.0", "end").strip()
            prio_full = prio_var.get()
            prio = prio_full.split()[-1].lower()
            due = due_var.get().strip() or None

            if task is None:
                new_id = storage.get_next_id(self.tasks + self.archived_tasks + self.finished_tasks)
                start_time = datetime.now()
                new_task = Task(
                    id=new_id,
                    title=title_text,
                    description=description,
                    status="pending",
                    priority=prio,
                    created_at=start_time.isoformat(),
                    due_date=due,
                    duration_seconds=0,
                    remaining_seconds=0,
                )
                self.tasks.append(new_task)
                logging.info(f"Added task {new_task.id}: {new_task.title}")
            else:
                task.title = title_text
                task.description = description
                task.priority = prio
                task.due_date = due
                logging.info(f"Updated task {task.id}")

            storage.save_tasks(TASKS_PATH, self.tasks)
            self._render_tasks()
            win.destroy()

        save_btn.config(command=on_save)

    def _mark_done(self, task: Task):
        if task.id in self.timers:
            self._stop_timer(task.id)

        self.tasks = [t for t in self.tasks if t.id != task.id]

        task.status = "done"
        task.remaining_seconds = max(0, task.remaining_seconds or 0)
        self.finished_tasks.append(task)

        storage.save_tasks(TASKS_PATH, self.tasks)
        storage.save_tasks(FINISHED_PATH, self.finished_tasks)

        self._render_tasks()
        self._render_finished()
        self._update_stats()

        logging.info(f"Marked done task {task.id}: {task.title}")

    def _undo_done(self, task: Task):
        self.finished_tasks = [t for t in self.finished_tasks if t.id != task.id]

        task.status = "pending"
        if task.remaining_seconds == 0:
            task.remaining_seconds = task.duration_seconds
        self.tasks.append(task)

        storage.save_tasks(TASKS_PATH, self.tasks)
        storage.save_tasks(FINISHED_PATH, self.finished_tasks)

        self._render_tasks()
        self._render_finished()
        self._update_stats()

        logging.info(f"Reopened finished task {task.id}: {task.title}")

    def _delete_task(self, task: Task):
        self._archive_task(task)

    def _toggle_timer(self, task: Task):
        if task.id in self.timers:
            self._stop_timer(task.id)
            storage.save_tasks(TASKS_PATH, self.tasks)
            self._render_tasks()
        else:
            if task.status == "done":
                messagebox.showinfo("Task is done", "This task is already marked done.")
                return
            if task.remaining_seconds <= 0:
                task.remaining_seconds = task.duration_seconds
            self._start_timer(task)

    def _start_timer(self, task: Task):
        def tick():
            for t in self.tasks:
                if t.id == task.id:
                    t.remaining_seconds = int((t.remaining_seconds or 0) + 1)
                    break
            lbl = self.timer_labels.get(task.id)
            if lbl:
                lbl.config(text=f"⏱ {format_duration(task.remaining_seconds)}")
            if task.status != "done":
                after_id = self.root.after(1000, tick)
                self.timers[task.id] = after_id

        after_id = self.root.after(1000, tick)
        self.timers[task.id] = after_id
        logging.info(f"Started timer for task {task.id}")

    def _stop_timer(self, task_id: int):
        after_id = self.timers.get(task_id)
        if after_id:
            try:
                self.root.after_cancel(after_id)
            except Exception:
                pass
        if task_id in self.timers:
            del self.timers[task_id]
        logging.info(f"Stopped timer for task {task_id}")
        storage.save_tasks(TASKS_PATH, self.tasks)

    def _reset_timer(self, task: Task):
        if task.id in self.timers:
            self._stop_timer(task.id)
        task.remaining_seconds = task.duration_seconds
        storage.save_tasks(TASKS_PATH, self.tasks)
        self._render_tasks()

def main():
    root = tk.Tk()
    app = TodoApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root, app))
    root.mainloop()

def on_close(root, app: TodoApp):
    for tid in list(app.timers.keys()):
        app._stop_timer(tid)
    storage.save_tasks(TASKS_PATH, app.tasks)
    storage.save_tasks(ARCHIVE_PATH, app.archived_tasks)
    storage.save_tasks(FINISHED_PATH, app.finished_tasks)
    root.destroy()

if __name__ == "__main__":
    main()
