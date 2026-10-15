"""Duplicate detection for incoming documents.

Intent: before filing a document, check whether a file with the same
*content* (not just the same name) has already been processed, so the
same invoice/contract/report doesn't get filed twice under two different
filenames (e.g. "invoice_042.txt" and "invoice_042_copy.txt").

Current state: only an exact-name guard exists. Content-hash comparison
against previously processed files was never wired up.
"""

import os


def _already_processed_names(processed_root):
    seen = set()
    if not os.path.isdir(processed_root):
        return seen
    for _, _, files in os.walk(processed_root):
        seen.update(files)
    return seen


def is_duplicate(file_path, processed_root):
    """Return True if this file should be treated as a duplicate.

    TODO: this only guards against re-processing a file with the exact
    same name. It does not hash file contents, so a copy saved under a
    different filename (e.g. "invoice_042_copy.txt") is NOT caught and
    will be filed again under its own name.
    """
    filename = os.path.basename(file_path)
    return filename in _already_processed_names(processed_root)
