"""Native Windows/Mac/Linux desktop GUI for the document intake pipeline.

Built with tkinter + ttkbootstrap for a modern, themed look (ttkbootstrap
is the only extra dependency; tkinter itself ships with standard Python).
Calls the real pipeline in intake.py directly — nothing here is simulated.

Usage:
    pip install ttkbootstrap
    python gui_desktop.py
"""

import csv
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

import ttkbootstrap as ttk
from ttkbootstrap.constants import BOTH, END, LEFT, RIGHT, X, Y

from intake import (
    BASE_DIR,
    INBOX_DIR,
    LOG_PATH,
    OPEN_ITEMS_NOTICE,
    PROCESSED_DIR,
    process_inbox,
)
from src.classifier import CONFIG_PATH, load_rules

THEME = "flatly"  # a clean, modern light theme; try "darkly" for dark mode

# --- Developer credit, with a tamper check -----------------------------
# This isn't real protection (anyone editing this .py file can edit this
# block too), but it stops the credit line from being silently dropped or
# swapped by a casual find-and-replace: if DEVELOPER_CREDIT doesn't match
# DEVELOPER_CREDIT_SHA256, the app refuses to start rather than running on
# quietly under someone else's name.
DEVELOPER_CREDIT = "Ali Amini"
DEVELOPER_CREDIT_SHA256 = "ca02607170653c6140dc96f858ecd9eeec69ff9623b27c960c8a63fdde271bd9"


def verify_developer_credit():
    actual = hashlib.sha256(DEVELOPER_CREDIT.encode("utf-8")).hexdigest()
    if actual != DEVELOPER_CREDIT_SHA256:
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "Document Intake Automation",
            "Developer credit has been modified or removed.\n\n"
            "This copy of Document Intake Automation will not run until the "
            "DEVELOPER_CREDIT constant in gui_desktop.py matches its "
            "original value (Ali Amini).",
        )
        sys.exit(1)


def open_in_default_app(path, *fallback_paths):
    """Open a file with whatever application the OS has associated with it
    (Notepad for .txt on a stock Windows install, etc.). If path doesn't
    exist, tries fallback_paths in order before giving up (useful for a
    "failed" row, where the file may still be sitting in the inbox rather
    than wherever it was destined for)."""
    for candidate in (path, *fallback_paths):
        if os.path.exists(candidate):
            path = candidate
            break
    else:
        messagebox.showerror("Document Intake", f"File not found:\n{path}")
        return
    try:
        if sys.platform.startswith("win"):
            os.startfile(path)  # noqa: S606 (Windows-only API, by design)
        elif sys.platform == "darwin":
            subprocess.run(["open", path], check=False)
        else:
            subprocess.run(["xdg-open", path], check=False)
    except OSError as e:
        messagebox.showerror("Document Intake", f"Couldn't open {os.path.basename(path)}:\n{e}")


class DocumentIntakeApp(ttk.Window):
    def __init__(self):
        super().__init__(title="Document Intake Automation", themename=THEME, size=(1020, 680))
        self.minsize(900, 560)

        self._build_header()
        self._build_notice()

        self.notebook = ttk.Notebook(self, bootstyle="primary")
        self.notebook.pack(fill=BOTH, expand=True, padx=18, pady=(0, 18))

        self.dashboard_tab = DashboardTab(self.notebook, self)
        self.inbox_tab = InboxTab(self.notebook, self)
        self.rules_tab = RulesTab(self.notebook, self)
        self.log_tab = LogTab(self.notebook, self)

        self.notebook.add(self.dashboard_tab, text="  Dashboard  ")
        self.notebook.add(self.inbox_tab, text="  Inbox  ")
        self.notebook.add(self.rules_tab, text="  Rules  ")
        self.notebook.add(self.log_tab, text="  Log  ")

        self.refresh_all()

    def _build_header(self):
        header = ttk.Frame(self, padding=(18, 18, 18, 8))
        header.pack(fill=X)

        title_box = ttk.Frame(header)
        title_box.pack(side=LEFT)
        title_row = ttk.Frame(title_box)
        title_row.pack(anchor="w")
        ttk.Label(title_row, text="Document Intake Automation",
                  font=("Segoe UI", 18, "bold")).pack(side=LEFT)
        ttk.Label(title_row, text=f"  by {DEVELOPER_CREDIT}", bootstyle="secondary",
                  font=("Segoe UI", 9)).pack(side=LEFT, anchor="s", pady=(0, 3))
        ttk.Label(title_box, text="Document intake  →  classify  →  dedupe  →  file  →  log",
                  bootstyle="secondary").pack(anchor="w")

        btn_box = ttk.Frame(header)
        btn_box.pack(side=RIGHT)
        ttk.Button(btn_box, text="▶  Run Pipeline", bootstyle="primary",
                   command=self.run_pipeline).pack(side=LEFT, padx=4)
        ttk.Button(btn_box, text="⟲  Reset Demo", bootstyle="secondary-outline",
                   command=self.reset_demo).pack(side=LEFT, padx=4)

    def _build_notice(self):
        box = ttk.Frame(self, bootstyle="warning", padding=14)
        box.pack(fill=X, padx=18, pady=(0, 14))
        ttk.Label(box, text="KNOWN OPEN ITEMS", bootstyle="inverse-warning",
                  font=("Segoe UI", 8, "bold")).pack(anchor="w")
        ttk.Label(box, text=OPEN_ITEMS_NOTICE, bootstyle="inverse-warning",
                  wraplength=960, justify="left").pack(anchor="w", pady=(4, 0))

    def run_pipeline(self):
        results = process_inbox(verbose=False)
        if not results:
            messagebox.showinfo("Document Intake", "Inbox is empty, nothing to process.")
        self.refresh_all()

    def reset_demo(self):
        if os.path.isdir(PROCESSED_DIR):
            for folder in os.listdir(PROCESSED_DIR):
                full = os.path.join(PROCESSED_DIR, folder)
                if not os.path.isdir(full):
                    continue
                for filename in os.listdir(full):
                    src = os.path.join(full, filename)
                    if os.path.isfile(src):
                        shutil.move(src, os.path.join(INBOX_DIR, filename))
        if os.path.exists(LOG_PATH):
            os.remove(LOG_PATH)
        self.refresh_all()

    def refresh_all(self):
        self.dashboard_tab.refresh()
        self.inbox_tab.refresh()
        self.rules_tab.refresh()
        self.log_tab.refresh()


class DashboardTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app

        self.stats_frame = ttk.Frame(self)
        self.stats_frame.pack(fill=X, pady=(0, 16))

        ttk.Label(self, text="Last run", font=("Segoe UI", 12, "bold")).pack(
            anchor="w", pady=(0, 6)
        )

        columns = ("file", "type", "destination", "status")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=12,
                                  bootstyle="primary")
        for col, label, width in [
            ("file", "File", 260), ("type", "Type", 110),
            ("destination", "Destination", 220), ("status", "Status", 150),
        ]:
            self.tree.heading(col, text=label)
            self.tree.column(col, width=width, anchor="w")
        self.tree.pack(fill=BOTH, expand=True)
        self.tree.tag_configure("processed", foreground="#198754")
        self.tree.tag_configure("failed", foreground="#dc3545")
        self.tree.tag_configure("skipped_duplicate", foreground="#b08900")
        self.tree.bind("<Double-1>", self.open_selected)

        ttk.Label(self, text="Double-click a row to open that file.",
                  bootstyle="secondary", font=("Segoe UI", 8)).pack(anchor="w", pady=(6, 0))

    def open_selected(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        filename, _doc_type, destination, _status = self.tree.item(selected[0])["values"]
        if destination and destination not in ("-",):
            path = os.path.join(PROCESSED_DIR, destination)
        else:
            path = os.path.join(INBOX_DIR, filename)
        open_in_default_app(path, os.path.join(INBOX_DIR, filename))

    def _stat_tile(self, parent, value, label, style="primary"):
        tile = ttk.Frame(parent, bootstyle=style, padding=14)
        ttk.Label(tile, text=str(value), bootstyle=f"inverse-{style}",
                  font=("Segoe UI", 22, "bold")).pack(anchor="w")
        ttk.Label(tile, text=label, bootstyle=f"inverse-{style}",
                  font=("Segoe UI", 9)).pack(anchor="w")
        return tile

    def refresh(self):
        for widget in self.stats_frame.winfo_children():
            widget.destroy()

        inbox_count = sum(
            1 for f in os.listdir(INBOX_DIR) if os.path.isfile(os.path.join(INBOX_DIR, f))
        ) if os.path.isdir(INBOX_DIR) else 0

        processed_counts = {}
        if os.path.isdir(PROCESSED_DIR):
            for folder in sorted(os.listdir(PROCESSED_DIR)):
                full = os.path.join(PROCESSED_DIR, folder)
                if os.path.isdir(full):
                    processed_counts[folder] = sum(
                        1 for f in os.listdir(full) if os.path.isfile(os.path.join(full, f))
                    )

        needs_review = 0
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, newline="", encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    if row.get("status") in ("skipped_duplicate", "failed"):
                        needs_review += 1

        tiles = [
            (inbox_count, "waiting in inbox", "primary"),
            (needs_review, "needs manual review",
             "danger" if needs_review else "secondary"),
        ]
        tiles += [(c, f"filed · {k}", "success") for k, c in processed_counts.items()]
        for value, label, style in tiles:
            self._stat_tile(self.stats_frame, value, label, style).pack(
                side=LEFT, padx=(0, 10), fill=Y
            )

        for row in self.tree.get_children():
            self.tree.delete(row)
        # Read the tail of the log (rather than caching the last in-process
        # run) so the dashboard also reflects runs made from the CLI while
        # the GUI happens to be open.
        if os.path.exists(LOG_PATH):
            with open(LOG_PATH, newline="", encoding="utf-8") as f:
                rows = list(csv.DictReader(f))
            for row in rows[-20:]:
                dest = row.get("destination", "")
                if dest.startswith(PROCESSED_DIR):
                    dest = dest[len(PROCESSED_DIR):].lstrip(os.sep)
                status = row.get("status", "")
                self.tree.insert("", END, values=(
                    row.get("source_file", ""), row.get("doc_type", ""), dest, status,
                ), tags=(status,))


class InboxTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, pady=(0, 10))
        ttk.Button(toolbar, text="＋ Add File...", bootstyle="primary",
                   command=self.add_file).pack(side=LEFT)
        ttk.Button(toolbar, text="✕ Remove Selected", bootstyle="danger-outline",
                   command=self.remove_selected).pack(side=LEFT, padx=6)

        columns = ("file", "size")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16,
                                  bootstyle="primary")
        self.tree.heading("file", text="File")
        self.tree.heading("size", text="Size (bytes)")
        self.tree.column("file", width=620, anchor="w")
        self.tree.column("size", width=140, anchor="e")
        self.tree.pack(fill=BOTH, expand=True)
        self.tree.bind("<Double-1>", self.open_selected)

        ttk.Label(self, text="Double-click a row to open that file.",
                  bootstyle="secondary", font=("Segoe UI", 8)).pack(anchor="w", pady=(6, 0))

    def open_selected(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        filename = self.tree.item(selected[0])["values"][0]
        open_in_default_app(os.path.join(INBOX_DIR, filename))

    def add_file(self):
        path = filedialog.askopenfilename(title="Add file to inbox")
        if not path:
            return
        dest = os.path.join(INBOX_DIR, os.path.basename(path))
        if os.path.exists(dest):
            messagebox.showwarning("Document Intake", f"{os.path.basename(path)} is already in the inbox.")
            return
        shutil.copy2(path, dest)
        self.app.refresh_all()

    def remove_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        filename = self.tree.item(selected[0])["values"][0]
        path = os.path.join(INBOX_DIR, filename)
        if os.path.exists(path):
            os.remove(path)
        self.app.refresh_all()

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not os.path.isdir(INBOX_DIR):
            return
        for filename in sorted(os.listdir(INBOX_DIR)):
            full = os.path.join(INBOX_DIR, filename)
            if os.path.isfile(full):
                self.tree.insert("", END, values=(filename, os.path.getsize(full)))


class RulesTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, pady=(0, 10))
        ttk.Button(toolbar, text="✎ Edit Keywords...", bootstyle="primary",
                   command=self.edit_keywords).pack(side=LEFT)
        ttk.Button(toolbar, text="💾 Save Changes", bootstyle="success",
                   command=self.save_rules).pack(side=LEFT, padx=6)

        columns = ("type", "folder", "keywords")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16,
                                  bootstyle="primary")
        self.tree.heading("type", text="Document Type")
        self.tree.heading("folder", text="Files Into")
        self.tree.heading("keywords", text="Keywords")
        self.tree.column("type", width=160, anchor="w")
        self.tree.column("folder", width=160, anchor="w")
        self.tree.column("keywords", width=580, anchor="w")
        self.tree.pack(fill=BOTH, expand=True)
        self.tree.bind("<Double-1>", lambda e: self.edit_keywords())

        self.rules = {}

    def edit_keywords(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showinfo("Document Intake", "Select a document type first.")
            return
        doc_type = self.tree.item(selected[0])["values"][0]
        current = ", ".join(self.rules.get(doc_type, {}).get("keywords", []))
        new_value = simpledialog.askstring(
            "Edit Keywords",
            f'Comma-separated keywords for "{doc_type}":',
            initialvalue=current,
        )
        if new_value is None:
            return
        keywords = [k.strip() for k in new_value.split(",") if k.strip()]
        self.rules.setdefault(doc_type, {})["keywords"] = keywords
        self._render()

    def save_rules(self):
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(self.rules, f, indent=2)
        messagebox.showinfo("Document Intake", "Classification rules saved.")

    def refresh(self):
        self.rules = load_rules()
        self._render()

    def _render(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        for doc_type, spec in self.rules.items():
            self.tree.insert("", END, values=(
                doc_type, spec.get("folder", ""), ", ".join(spec.get("keywords", [])),
            ))


class LogTab(ttk.Frame):
    def __init__(self, parent, app):
        super().__init__(parent, padding=16)
        self.app = app

        toolbar = ttk.Frame(self)
        toolbar.pack(fill=X, pady=(0, 10))
        ttk.Button(toolbar, text="⟲ Refresh", bootstyle="secondary-outline",
                   command=self.refresh).pack(side=LEFT)
        ttk.Label(toolbar, text="Filter by status:").pack(side=LEFT, padx=(16, 6))
        self.filter_var = tk.StringVar(value="all")
        filter_menu = ttk.Combobox(
            toolbar, textvariable=self.filter_var, state="readonly",
            values=["all", "processed", "failed", "skipped_duplicate"], width=18,
            bootstyle="primary",
        )
        filter_menu.pack(side=LEFT)
        filter_menu.bind("<<ComboboxSelected>>", lambda e: self.refresh())

        columns = ("timestamp", "source", "type", "destination", "status", "note")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=16,
                                  bootstyle="primary")
        widths = {"timestamp": 170, "source": 180, "type": 90, "destination": 220,
                  "status": 130, "note": 160}
        for col in columns:
            self.tree.heading(col, text=col.replace("_", " ").title())
            self.tree.column(col, width=widths[col], anchor="w")
        self.tree.pack(fill=BOTH, expand=True)
        self.tree.bind("<Double-1>", self.open_selected)

        ttk.Label(self, text="Double-click a row to open that file.",
                  bootstyle="secondary", font=("Segoe UI", 8)).pack(anchor="w", pady=(6, 0))

    def open_selected(self, _event=None):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])["values"]
        _timestamp, source, _doc_type, destination, status, _note = values
        if status == "processed" and destination:
            path = os.path.join(PROCESSED_DIR, destination)
        else:
            path = os.path.join(INBOX_DIR, source)
        open_in_default_app(path, os.path.join(PROCESSED_DIR, destination or ""),
                             os.path.join(INBOX_DIR, source))

    def refresh(self):
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not os.path.exists(LOG_PATH):
            return
        with open(LOG_PATH, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        wanted = self.filter_var.get()
        for row in reversed(rows):
            if wanted != "all" and row.get("status") != wanted:
                continue
            dest = row.get("destination", "")
            if dest.startswith(PROCESSED_DIR):
                dest = dest[len(PROCESSED_DIR):].lstrip(os.sep)
            self.tree.insert("", END, values=(
                row.get("timestamp_utc", ""), row.get("source_file", ""),
                row.get("doc_type", ""), dest, row.get("status", ""), row.get("note", ""),
            ))


if __name__ == "__main__":
    verify_developer_credit()
    app = DocumentIntakeApp()
    app.mainloop()
