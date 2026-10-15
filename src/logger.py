"""Append-only CSV logging for the intake pipeline."""

import csv
import os
from datetime import datetime, timezone

LOG_HEADER = ["timestamp_utc", "source_file", "doc_type", "destination", "status", "note"]


def log_event(log_path, source_file, doc_type, destination, status, note=""):
    is_new = not os.path.exists(log_path)
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(LOG_HEADER)
        writer.writerow([
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            source_file,
            doc_type,
            destination,
            status,
            note,
        ])
