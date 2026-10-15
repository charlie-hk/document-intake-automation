"""Local web GUI for the document intake pipeline.

This wraps the real pipeline in intake.py: pressing "Run Pipeline" in the
browser calls the exact same process_inbox() function the CLI uses, so
whatever it does (including its known open items) shows up here too.

Usage:
    pip install flask
    python gui_app.py
    then open http://127.0.0.1:5000 in a browser
"""

import csv
import os
import shutil

from flask import Flask, redirect, render_template, url_for

from intake import (
    INBOX_DIR,
    LOG_PATH,
    OPEN_ITEMS_NOTICE,
    PROCESSED_DIR,
    process_inbox,
)

app = Flask(__name__)

# Keeps the results of the most recent run in memory so the page can show
# them after a redirect (no database needed for a tool this size).
LAST_RUN = {"results": None}


def count_inbox():
    if not os.path.isdir(INBOX_DIR):
        return 0
    return sum(
        1 for f in os.listdir(INBOX_DIR)
        if os.path.isfile(os.path.join(INBOX_DIR, f))
    )


def count_processed():
    counts = {}
    if not os.path.isdir(PROCESSED_DIR):
        return counts
    for folder in sorted(os.listdir(PROCESSED_DIR)):
        full = os.path.join(PROCESSED_DIR, folder)
        if os.path.isdir(full):
            counts[folder] = sum(
                1 for f in os.listdir(full) if os.path.isfile(os.path.join(full, f))
            )
    return counts


def read_log_tail(n=10):
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    for row in rows:
        dest = row.get("destination", "")
        if dest.startswith(PROCESSED_DIR):
            row["destination"] = dest[len(PROCESSED_DIR):].lstrip(os.sep)
    return rows[-n:]


@app.route("/")
def index():
    return render_template(
        "index.html",
        notice=OPEN_ITEMS_NOTICE,
        inbox_count=count_inbox(),
        processed_counts=count_processed(),
        log_rows=read_log_tail(),
        last_results=LAST_RUN["results"],
    )


@app.route("/run", methods=["POST"])
def run_pipeline():
    LAST_RUN["results"] = process_inbox(verbose=False)
    return redirect(url_for("index"))


@app.route("/reset", methods=["POST"])
def reset_demo():
    """Move everything back into data/inbox/ and clear the log, so the demo
    can be run again from a clean state."""
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
    LAST_RUN["results"] = None
    return redirect(url_for("index"))


if __name__ == "__main__":
    app.run(debug=True, port=5000)
