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
LOG_PATH = os.path.join(BASE_DIR, "todo.log")

logging.basicConfig(filename=LOG_PATH, level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")

# Modern Color scheme
APP_COLORS = {
    "bg_main": "#f8fafc",       # Light cool gray background
    "bg_card": "#ffffff",       # Pure white cards
    "bg_header": "#ffffff",     # White header
    "text_primary": "#1e293b",  # Slate gray for primary text
    "text_secondary": "#64748b", # Cool gray for secondary text
    "accent": "#6366f1",        # Indigo for accent
    "border": "#e2e8f0",        # Soft gray for borders
    "hover": "#eef2ff",         # Light indigo for hover states
    "success": "#10b981",       # Emerald for success states
    "error": "#ef4444",         # Red for dangerous actions
    "archive": "#94a3b8"        # Slate for archived items
}

# Modern priority colors with softer tones
PRIORITY_COLORS = {
    "high": "#f43f5e",    # Rose red
    "medium": "#6366f1",  # Indigo
    "low": "#10b981",     # Emerald
    "done": "#64748b",    # Slate
    "archived": "#94a3b8" # Slate for archived
}

# ---------- App ----------
class TodoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("To-Do Manager")
        
        # Set window to full screen
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        self.root.geometry(f"{screen_width}x{screen_height}")
        self.root.state('zoomed')  # This maximizes the window on Windows
        self.root.minsize(800, 520)

        # style
        self.style = ttk.Style(root)
        self._setup_style()

        # data - Load archive first, then filter out archived tasks from main tasks
        self.archived_tasks = self._load_archived_tasks()
        self.tasks = self._load_active_tasks()
        self.timers = {}  # task_id -> after_id
        self.timer_labels = {}  # task_id -> label widget to update

        # UI layout
        self._build_ui()
        self._render_tasks()
        # Render archive after UI is fully built
        self._render_archive()

    def _load_archived_tasks(self):
        """Load archived tasks from archive file"""
        if os.path.exists(ARCHIVE_PATH):
            return storage.load_tasks(ARCHIVE_PATH)
        return []

    def _load_active_tasks(self):
        """Load active tasks, excluding any that are marked as archived"""
        all_tasks = storage.load_tasks(TASKS_PATH)
        # Only return tasks that are not archived
        return [task for task in all_tasks if getattr(task, 'status', 'pending') != 'archived']

    def _setup_style(self):
        # Use a clean theme if available
        try:
            self.style.theme_use("clam")
        except:
            pass
        
        # Configure default styles with modern font
        default_font = ("Segoe UI", 10)
        self.style.configure(".", 
            font=default_font,
            background=APP_COLORS["bg_main"]
        )
        
        # Frame styles
        self.style.configure("TFrame", background=APP_COLORS["bg_main"])
        
        # Modern card style with subtle border
        self.style.configure("Card.TFrame",
            background=APP_COLORS["bg_card"],
            relief="solid",
            borderwidth=1,
            bordercolor=APP_COLORS["border"]
        )
        
        # Archive card style
        self.style.configure("Archive.TFrame",
            background=APP_COLORS["bg_card"],
            relief="solid",
            borderwidth=1,
            bordercolor=APP_COLORS["archive"]
        )
        
        # Header styles with larger, bolder text
        self.style.configure("Header.TLabel", 
            font=("Segoe UI", 20, "bold"),
            foreground=APP_COLORS["text_primary"],
            background=APP_COLORS["bg_card"]
        )
        
        # Text styles
        self.style.configure("Muted.TLabel", 
            font=("Segoe UI", 9),
            foreground=APP_COLORS["text_secondary"],
            background=APP_COLORS["bg_card"]
        )
        
        # Archive text style
        self.style.configure("Archive.TLabel", 
            font=("Segoe UI", 9),
            foreground=APP_COLORS["archive"],
            background=APP_COLORS["bg_card"]
        )
        
        # Modern button styles
        self.style.configure("TButton", 
            font=("Segoe UI", 10),
            padding=(12, 6),
            relief="flat",
            borderwidth=1
        )
        
        # Accent button style
        self.style.configure("Accent.TButton", 
            font=("Segoe UI", 10, "bold"),
            padding=(12, 6),
            background=APP_COLORS["accent"],
            foreground="white"
        )
        
        # Success button style
        self.style.configure("Success.TButton", 
            background=APP_COLORS["success"],
            foreground="white"
        )
        
        # Danger button style
        self.style.configure("Danger.TButton", 
            background=APP_COLORS["error"],
            foreground="white"
        )
        
        # Archive button style
        self.style.configure("Archive.TButton", 
            background=APP_COLORS["archive"],
            foreground="white"
        )
        
        # Entry styles
        self.style.configure("TEntry", 
            fieldbackground=APP_COLORS["bg_card"],
            borderwidth=1,
            relief="solid"
        )
        
        # Header entry style with transparent background
        self.style.configure("Header.TEntry",
            fieldbackground=APP_COLORS["accent"],  # Will be overridden by tk entry widget
            foreground="white",
            insertcolor="white",  # Cursor color
            borderwidth=0,
            relief="flat"
        )
        
        # Configure root background
        self.root.configure(bg=APP_COLORS["bg_main"])

    def _build_ui(self):
        # top frame: title + search/filter
        top = ttk.Frame(self.root, padding=(12,10), style="Card.TFrame")
        top.grid(row=0, column=0, columnspan=2, sticky="ew", padx=12, pady=(12,6))
        top.columnconfigure(1, weight=1)

        title = ttk.Label(top, text="To-Do Manager", style="Header.TLabel")
        title.grid(row=0, column=0, sticky="w", padx=6)

        # Modern search with icon
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

        # Modern filter controls
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

        # Modern add button
        add_button = ttk.Button(top, text="➕ New Task",
                              style="Accent.TButton",
                              command=self._open_add_window)
        add_button.grid(row=0, column=3, padx=(12,0))

        # main frames
        left = ttk.Frame(self.root, padding=(12,6))
        left.grid(row=1, column=0, sticky="nswe")
        right = ttk.Frame(self.root, padding=(12,6))
        right.grid(row=1, column=1, sticky="nswe")

        # grid config to be responsive
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        # left: info / quick stats
        stats_card = ttk.Frame(left, style="Card.TFrame", padding=12)
        stats_card.grid(row=0, column=0, sticky="nwe", padx=12)
        stats_title = ttk.Label(stats_card, text="Overview", 
                              font=("Segoe UI", 12, "bold"))
        stats_title.grid(row=0, column=0, sticky="w")
        self.stats_label = ttk.Label(stats_card, text="", 
                                   style="Muted.TLabel")
        self.stats_label.grid(row=1, column=0, sticky="w", pady=(8,0))
        
        # Archive section below stats
        archive_card = ttk.Frame(left, style="Archive.TFrame", padding=12)
        archive_card.grid(row=1, column=0, sticky="nwse", padx=12, pady=(12,0))
        left.rowconfigure(1, weight=1)  # Make archive section expandable
        
        # Archive header
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
        
        # Archive list (always visible)
        self.archive_frame = ttk.Frame(archive_card)
        self.archive_frame.grid(row=1, column=0, sticky="nsew", pady=(8,0))
        archive_card.rowconfigure(1, weight=1)
        
        # Archive canvas for scrolling
        self.archive_canvas = tk.Canvas(self.archive_frame, 
                                      borderwidth=0, 
                                      highlightthickness=0, 
                                      bg=APP_COLORS["bg_card"],
                                      height=200)  # Fixed height
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

        self._update_stats()

        # right: tasks list (scrollable)
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

        right.columnconfigure(0, weight=1)
        right.rowconfigure(0, weight=1)

        # internal state
        self.sort_newest = True

    def _render_archive(self):
        # Clear previous archive items
        for child in self.archive_list_frame.winfo_children():
            child.destroy()
        
        if not self.archived_tasks:
            no_archive_label = ttk.Label(self.archive_list_frame, 
                                       text="No archived tasks", 
                                       style="Archive.TLabel")
            no_archive_label.pack(pady=20)
            return
        
        # Sort archived tasks by deletion date (most recent first)
        sorted_archive = sorted(self.archived_tasks, 
                              key=lambda t: t.created_at, 
                              reverse=True)
        
        for i, task in enumerate(sorted_archive):
            self._create_archive_item(task, i)

    def _create_archive_item(self, task: Task, index: int):
        item_frame = ttk.Frame(self.archive_list_frame, style="Card.TFrame", padding=8)
        item_frame.pack(fill="x", padx=2, pady=2)
        item_frame.columnconfigure(1, weight=1)
        
        # Archive icon
        icon_label = ttk.Label(item_frame, text="🗂️", font=("Segoe UI", 10))
        icon_label.grid(row=0, column=0, sticky="w", padx=(0, 8))
        
        # Task title (clickable)
        title_label = ttk.Label(item_frame, 
                              text=task.title, 
                              font=("Segoe UI", 10),
                              foreground=APP_COLORS["archive"],
                              cursor="hand2")
        title_label.grid(row=0, column=1, sticky="w")
        title_label.bind("<Button-1>", lambda e, t=task: self._show_archived_task_details(t))
        
        # Action buttons
        btn_frame = ttk.Frame(item_frame)
        btn_frame.grid(row=0, column=2, sticky="e")
        
        restore_btn = ttk.Button(btn_frame, text="↩", 
                               style="Archive.TButton",
                               command=lambda t=task: self._restore_task(t))
        restore_btn.grid(row=0, column=0, padx=2)
        
        delete_btn = ttk.Button(btn_frame, text="🗑️", 
                              style="Danger.TButton",
                              command=lambda t=task: self._permanently_delete_task(t))
        delete_btn.grid(row=0, column=1, padx=2)

    def _show_archived_task_details(self, task: Task):
        # Similar to _show_task_details but with archive styling
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

        # Archive header
        header = tk.Frame(container, bg=APP_COLORS["archive"])
        header.pack(fill="x")
        
        header_content = tk.Frame(header, bg=header["bg"])
        header_content.pack(fill="x", padx=25, pady=20)

        status_label = tk.Label(header_content,
            text="🗂️ ARCHIVED TASK",
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 11))
        status_label.pack(side="left", pady=(0, 10))
        
        title_label = tk.Label(header_content,
            text=task.title,
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 24, "bold"),
            wraplength=600)
        title_label.pack(fill="x", anchor="w")

        # Content area (same as regular task details)
        content = ttk.Frame(container, style="Card.TFrame", padding=(25, 20))
        content.pack(fill="both", expand=True)

        # Description section
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
            height=15,
            relief="flat",
            borderwidth=1)
        desc_text.pack(fill="both", expand=True)
        desc_text.insert("1.0", task.description if task.description else "(No description provided)")
        desc_text.configure(state="disabled")

        # Action buttons
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

    def _restore_task(self, task: Task):
        # Remove from archive
        self.archived_tasks = [t for t in self.archived_tasks if t.id != task.id]
        # Add back to active tasks
        task.status = "pending"  # Reset status
        self.tasks.append(task)
        
        # Save both files
        storage.save_tasks(TASKS_PATH, self.tasks)
        storage.save_tasks(ARCHIVE_PATH, self.archived_tasks)
        
        self._update_stats()
        self._render_tasks()
        self._render_archive()
        
        logging.info(f"Restored task {task.id}: {task.title}")

    def _permanently_delete_task(self, task: Task):
        if messagebox.askyesno("Permanent Delete", 
                             f"Permanently delete task '{task.title}'?\n\nThis action cannot be undone."):
            self.archived_tasks = [t for t in self.archived_tasks if t.id != task.id]
            storage.save_tasks(ARCHIVE_PATH, self.archived_tasks)
            
            self._update_stats()
            self._render_archive()
            
            logging.info(f"Permanently deleted task {task.id}: {task.title}")

    def _archive_task(self, task: Task):
        # Stop timer if running
        if task.id in self.timers:
            self._stop_timer(task.id)
        
        # Remove from active tasks
        self.tasks = [t for t in self.tasks if t.id != task.id]
        
        # Add to archive
        task.status = "archived"  # Mark as archived
        self.archived_tasks.append(task)
        
        # Save both files
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
        done = total - pending
        high = sum(1 for t in self.tasks if t.priority == "high" and t.status != "done")
        archived = len(self.archived_tasks)
        
        txt = f"Total: {total}   Pending: {pending}   Done: {done}   High priority: {high}"
        self.stats_label.config(text=txt)
        
        # Update archive count
        archive_txt = f"({archived} items)"
        self.archive_count_label.config(text=archive_txt)

    def _render_tasks(self):
        # clear previous cards
        for child in self.task_frame.winfo_children():
            child.destroy()

        # prepare filtered+searched list
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
        # Create outer card frame for shadow effect
        outer_card = ttk.Frame(self.task_frame, style="Card.TFrame")
        outer_card.grid(row=index, column=0, sticky="ew", padx=12, pady=6)
        outer_card.columnconfigure(0, weight=1)

        # Inner card with padding
        card = ttk.Frame(outer_card, style="Card.TFrame", padding=16)
        card.grid(row=0, column=0, sticky="ew")
        card.columnconfigure(1, weight=1)

        # Priority badge with friendly icons
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

        # Title with status icon - made clickable
        title_txt = task.title
        if task.status == "done":
            title_txt = "✓ " + title_txt
        title_lbl = ttk.Label(card, 
            text=title_txt, 
            font=("Segoe UI", 12, "bold"),
            foreground=APP_COLORS["text_primary"] if task.status != "done" else APP_COLORS["text_secondary"],
            cursor="hand2")  # Change cursor to hand when hovering
        title_lbl.grid(row=0, column=1, sticky="w")
        
        # Bind click event to show task details
        title_lbl.bind("<Button-1>", lambda e, t=task: self._show_task_details(t))

        # desc and meta
        desc_txt = task.description if task.description else "(no description)"
        desc_lbl = ttk.Label(card, text=desc_txt, style="Muted.TLabel")
        desc_lbl.grid(row=1, column=1, sticky="w")

        meta = f"Created: {task.created_at.split('T')[0]}"
        if task.due_date:
            meta += f"  •  Due: {task.due_date}"
        meta_lbl = ttk.Label(card, text=meta, style="Muted.TLabel")
        meta_lbl.grid(row=2, column=1, sticky="w", pady=(6,0))

        # right-side buttons with modern styling
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

        # Archive button instead of direct delete
        archive_btn = ttk.Button(btn_frame, text="🗂️ Archive",
                               style="Archive.TButton",
                               command=lambda t=task: self._archive_task(t))
        archive_btn.grid(row=0, column=2, padx=4, pady=2)

        # Modern timer display
        timer_frame = ttk.Frame(btn_frame)
        timer_frame.grid(row=1, column=0, columnspan=3, pady=(8,0))

        # Elapsed time label with friendly icon
        elapsed = task.remaining_seconds if task.remaining_seconds is not None else 0
        elapsed_lbl = ttk.Label(timer_frame, 
                              text=f"⏱ {format_duration(elapsed)}",
                              font=("Segoe UI", 9, "bold"),
                              foreground=APP_COLORS["text_secondary"])
        elapsed_lbl.grid(row=0, column=0, padx=(0,6))
        self.timer_labels[task.id] = elapsed_lbl

        # Start timer automatically if not running and task is not done
        if task.id not in self.timers and task.status != "done":
            self._start_timer(task)

    def _show_task_details(self, task: Task):
        # Create modal window
        modal = tk.Toplevel(self.root)
        modal.transient(self.root)
        modal.grab_set()
        
        # Calculate position to center the modal below the header
        window_width = 700
        window_height = 550
        header_height = 80  # Height of the "To-Do Manager" header and search bar
        
        # Get the main window's position and dimensions
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width

        ()
        
        # Calculate position to center horizontally and place below header
        position_x = root_x + (root_width - window_width) // 2
        position_y = root_y + header_height
        
        modal.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        
        # Configure modal
        modal.title("Task Details")
        modal.configure(bg=APP_COLORS["bg_main"])
        modal.resizable(False, False)

        # Create main container with modern styling
        container = ttk.Frame(modal, style="Card.TFrame", padding=0)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Header section with gradient-like effect
        header = tk.Frame(container, bg=PRIORITY_COLORS.get("done" if task.status == "done" else task.priority, "#999999"))
        header.pack(fill="x")
        
        header_content = tk.Frame(header, bg=header["bg"])
        header_content.pack(fill="x", padx=25, pady=20)

        # Status indicator and title
        status_frame = tk.Frame(header_content, bg=header["bg"])
        status_frame.pack(fill="x", pady=(0, 10))
        
        status_text = "✨ COMPLETED" if task.status == "done" else f"{task.priority.upper()} PRIORITY"
        status_label = tk.Label(status_frame,
            text=status_text,
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 11))
        status_label.pack(side="left")
        
        # Title in header
        title_label = tk.Label(header_content,
            text=task.title,
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 24, "bold"),
            wraplength=600)
        title_label.pack(fill="x", anchor="w")

        # Content area
        content = ttk.Frame(container, style="Card.TFrame", padding=(25, 20))
        content.pack(fill="both", expand=True)

        # Task metadata section
        meta_frame = ttk.Frame(content)
        meta_frame.pack(fill="x", pady=(0, 20))
        
        # Time information
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

        # Dates information
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

        # Description section
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
            height=10,
            relief="flat",
            borderwidth=1)
        desc_text.pack(fill="both", expand=True)
        desc_text.insert("1.0", task.description if task.description else "(No description provided)")
        desc_text.configure(state="disabled")

        # Action buttons
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

    # ---------- CRUD actions ----------
    def _open_add_window(self):
        self._open_task_window()

    def _open_edit_window(self, task: Task):
        self._open_task_window(task)

    def _open_task_window(self, task: Task = None):
        # Create modal window
        win = tk.Toplevel(self.root)
        win.transient(self.root)
        win.grab_set()
        
        # Calculate position to center the modal below the header
        window_width = 700
        window_height = 600
        header_height = 80  # Height of the "To-Do Manager" header and search bar
        
        # Get the main window's position and dimensions
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        
        # Calculate position to center horizontally and place below header
        position_x = root_x + (root_width - window_width) // 2
        position_y = root_y + header_height
        
        win.geometry(f"{window_width}x{window_height}+{position_x}+{position_y}")
        win.title("Add Task" if task is None else "Edit Task")
        win.configure(bg=APP_COLORS["bg_main"])
        win.resizable(True, True)

        # Create main container with modern styling
        container = ttk.Frame(win, style="Card.TFrame", padding=0)
        container.pack(fill="both", expand=True, padx=20, pady=20)

        # Header section with gradient-like effect
        is_new = task is None
        header_color = APP_COLORS["accent"] if is_new else PRIORITY_COLORS.get(task.priority, "#999999")
        header = tk.Frame(container, bg=header_color)
        header.pack(fill="x")
        
        header_content = tk.Frame(header, bg=header["bg"])
        header_content.pack(fill="x", padx=25, pady=20)

        # Header title
        title_text = "✨ NEW TASK" if is_new else "📝 EDIT TASK"
        header_label = tk.Label(header_content,
            text=title_text,
            bg=header["bg"],
            fg="white",
            font=("Segoe UI", 11))
        header_label.pack(anchor="w", pady=(0, 10))

        # Title Entry with transparent background
        title_var = tk.StringVar(value=task.title if task else "")
        title_entry = tk.Entry(header_content,
            textvariable=title_var,
            font=("Segoe UI", 24, "bold"),
            fg="white",
            bg=header_color,  # Match header background
            insertbackground="white",  # Cursor color
            relief="flat",
            highlightthickness=0)  # Remove focus border
        title_entry.pack(fill="x", pady=(5, 0))
        
        # Content area
        content = ttk.Frame(container, style="Card.TFrame", padding=(25, 20))
        content.pack(fill="both", expand=True)
        
        # Priority section
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

        # Due date section
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

        # Description section
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

        # Action buttons
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
            # Extract priority level from the menu selection (remove emoji)
            prio_full = prio_var.get()
            prio = prio_full.split()[-1].lower()
            due = due_var.get().strip() or None

            if task is None:
                # add new
                new_id = storage.get_next_id(self.tasks)
                start_time = datetime.now()
                new_task = Task(
                    id=new_id,
                    title=title_text,
                    description=description,
                    status="pending",
                    priority=prio,
                    created_at=start_time.isoformat(),
                    due_date=due,
                    duration_seconds=0,  # Duration will be counted up automatically
                    remaining_seconds=0,  # Will be used to track elapsed time
                )
                self.tasks.append(new_task)
                logging.info(f"Added task {new_task.id}: {new_task.title}")
            else:
                # update existing
                task.title = title_text
                task.description = description
                task.priority = prio
                task.due_date = due
                # Keep the existing elapsed time (remaining_seconds) when editing
                logging.info(f"Updated task {task.id}")

            storage.save_tasks(TASKS_PATH, self.tasks)
            self._render_tasks()
            win.destroy()

        save_btn.config(command=on_save)

    def _mark_done(self, task: Task):
        task.status = "done"
        task.remaining_seconds = 0
        # stop timer if running
        if task.id in self.timers:
            self._stop_timer(task.id)
        storage.save_tasks(TASKS_PATH, self.tasks)
        self._render_tasks()

    def _undo_done(self, task: Task):
        task.status = "pending"
        # restore remaining to duration if zero
        if task.remaining_seconds == 0:
            task.remaining_seconds = task.duration_seconds
        storage.save_tasks(TASKS_PATH, self.tasks)
        self._render_tasks()

    def _delete_task(self, task: Task):
        # This method is now replaced by _archive_task but kept for compatibility
        self._archive_task(task)

    # ---------- Timer controls ----------
    def _toggle_timer(self, task: Task):
        if task.id in self.timers:
            # pause
            self._stop_timer(task.id)
            storage.save_tasks(TASKS_PATH, self.tasks)
            self._render_tasks()
        else:
            # start
            # if already done, do nothing
            if task.status == "done":
                messagebox.showinfo("Task is done", "This task is already marked done.")
                return
            if task.remaining_seconds <= 0:
                task.remaining_seconds = task.duration_seconds
            self._start_timer(task)

    def _start_timer(self, task: Task):
        def tick():
            # increment elapsed time
            for t in self.tasks:
                if t.id == task.id:
                    t.remaining_seconds = int(t.remaining_seconds + 1)
                    break
            # update label
            lbl = self.timer_labels.get(task.id)
            if lbl:
                lbl.config(text=f"⏱ {format_duration(task.remaining_seconds)}")
            # schedule next tick if task is not done
            if task.status != "done":
                after_id = self.root.after(1000, tick)
                self.timers[task.id] = after_id

        # start first tick
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
        # persist current remaining seconds
        storage.save_tasks(TASKS_PATH, self.tasks)

    def _reset_timer(self, task: Task):
        # stop if running
        if task.id in self.timers:
            self._stop_timer(task.id)
        task.remaining_seconds = task.duration_seconds
        storage.save_tasks(TASKS_PATH, self.tasks)
        self._render_tasks()

# ---------- Run ----------
def main():
    root = tk.Tk()
    app = TodoApp(root)
    root.protocol("WM_DELETE_WINDOW", lambda: on_close(root, app))
    root.mainloop()

def on_close(root, app: TodoApp):
    # stop timers and persist
    for tid in list(app.timers.keys()):
        app._stop_timer(tid)
    storage.save_tasks(TASKS_PATH, app.tasks)
    # Also save archive on close
    storage.save_tasks(ARCHIVE_PATH, app.archived_tasks)
    root.destroy()

if __name__ == "__main__":
    main()
