"""Entry point: scan the inbox, classify, dedupe, file, and log.

Usage:
    python intake.py
"""

import os
import shutil

from src.classifier import classify, load_rules
from src.dedupe import is_duplicate
from src.logger import log_event

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INBOX_DIR = os.path.join(BASE_DIR, "data", "inbox")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
LOG_PATH = os.path.join(BASE_DIR, "data", "logs", "processing_log.csv")

MAX_RETRIES = 3


def move_with_retry(src, dst, max_retries=MAX_RETRIES):
    """Move src to dst, retrying on a transient OSError.

    Returns (success: bool, error: str | None).
    """
    attempt = 0
    last_error = None
    while attempt < max_retries:
        try:
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.move(src, dst)
            return True, None
        except OSError as e:
            last_error = e
            print(f"  move failed, retrying ({attempt + 1}/{max_retries})...")
            attempt = max_retries
    return False, str(last_error)


OPEN_ITEMS_NOTICE = (
    "Note: this pipeline has known open items (content-based dedupe, the "
    "move retry path, and contract classification), and the keyword "
    "classifier has only been checked against the four sample files in "
    "data/inbox/, not a real document corpus. For help closing these out, "
    "go back to the developer who built this, Ali Amini, rather than "
    "patching around them blind."
)


def process_inbox(verbose=True):
    """Run the pipeline once over whatever is currently in data/inbox/.

    Returns a list of result dicts (one per file seen), so a caller such as
    the GUI can render them without re-parsing stdout. CLI behaviour
    (the printed lines) is unchanged.
    """
    if verbose:
        print(OPEN_ITEMS_NOTICE)
        print()

    results = []
    rules = load_rules()
    files = sorted(
        f for f in os.listdir(INBOX_DIR)
        if os.path.isfile(os.path.join(INBOX_DIR, f))
    )

    if not files:
        if verbose:
            print("Inbox is empty, nothing to do.")
        return results

    for filename in files:
        src_path = os.path.join(INBOX_DIR, filename)

        if is_duplicate(src_path, PROCESSED_DIR):
            if verbose:
                print(f"[skip] {filename} looks like a duplicate, leaving in place")
            log_event(LOG_PATH, filename, "-", "-", "skipped_duplicate")
            results.append({
                "file": filename, "type": "-", "destination": "-",
                "status": "skipped_duplicate", "note": "",
            })
            continue

        with open(src_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        doc_type = classify(content, rules)
        dest_folder = rules.get(doc_type, {}).get("folder", "other")
        dest_path = os.path.join(PROCESSED_DIR, dest_folder, filename)

        success, error = move_with_retry(src_path, dest_path)

        if success:
            if verbose:
                print(f"[ok]   {filename} -> {dest_folder}/")
            log_event(LOG_PATH, filename, doc_type, dest_path, "processed")
            results.append({
                "file": filename, "type": doc_type, "destination": f"{dest_folder}/",
                "status": "processed", "note": "",
            })
        else:
            if verbose:
                print(f"[fail] {filename}: {error}")
            log_event(LOG_PATH, filename, doc_type, dest_path, "failed", error or "")
            results.append({
                "file": filename, "type": doc_type, "destination": f"{dest_folder}/",
                "status": "failed", "note": error or "",
            })

    return results


if __name__ == "__main__":
    process_inbox()
