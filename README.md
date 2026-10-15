# Document Intake Automation

![Document Intake Automation](assets/cover.png)

A lightweight document intake pipeline: it watches an inbox folder, classifies
each incoming file by type (invoice, contract, report, other), renames it
according to a fixed naming convention, files it into the right processed
subfolder, and logs every action to a CSV log for audit purposes.

This project is deliberately structured the way a small business's "first
automation pass" usually looks: the core pipeline works end to end, but a
few pieces were never finished. Treat it as a stand-in for a real client
handoff — the kind where you're asked to audit what's there, say what's
solid, and complete or repair the rest.

## Architecture

```
inbox/  --->  classifier.py  --->  dedupe.py  --->  intake.py (rename + file + log)  --->  processed/<type>/
                                                              |
                                                              v
                                                      logs/processing_log.csv
```

- `src/classifier.py` — rule-based classification using keyword lists from
  `config/classification_rules.json`. No ML/AI step yet; keyword matching only.
- `src/dedupe.py` — meant to stop the same document being filed twice under
  different names.
- `src/logger.py` — appends one row per processed file to the CSV log
  (timestamp, source name, destination, type, status).
- `intake.py` — the entry point. Scans `data/inbox/`, runs each file through
  classification, dedupe, then moves and logs it.

## Running it

**Command line:**

```bash
python intake.py
```

Drop files into `data/inbox/` first. Processed files land in
`data/processed/<type>/` and every action is appended to
`data/logs/processing_log.csv`.

**Desktop GUI (Windows/Mac/Linux, no browser):**

```bash
pip install -r requirements.txt
python gui_desktop.py
```

Native `tkinter` window, themed with `ttkbootstrap` (the one extra
dependency) for a modern look instead of stock tkinter's default styling.
This is the one to use for a real office tool, not just a demo:

- **Dashboard** — Run Pipeline / Reset Demo, stat tiles (including a
  "needs manual review" count pulled from failed/skipped entries), and the
  last run's results.
- **Inbox** — add a file via a native file picker or remove one, without
  touching the filesystem by hand.
- **Rules** — double-click a document type to edit its keyword list and
  save it back to `config/classification_rules.json`, so classification
  rules can be adjusted by whoever owns the intake process, not only by a
  developer.
- **Log** — the full processing history, filterable by status.

**Web GUI (browser-based alternative):**

```bash
pip install -r requirements.txt
python gui_app.py
```

Then open `http://127.0.0.1:5000`. A lighter, read-mostly view of the same
pipeline (Run Pipeline / Reset Demo, stat cards, last-run table, log
table) for when a browser-accessible view is preferred over a native
window. It does not include inbox management or rules editing.

Both GUIs call the exact same `process_inbox()` function the CLI uses —
neither is a simulation.

## Configuration

Classification is entirely config-driven — see
`config/classification_rules.json`. Add a document type by adding a new key
with its keyword list; no code changes needed for a new type, only for new
*matching logic* (e.g. moving past plain keyword matching).

## Classification Rules

TODO: document the keyword list behind each type and why those words were
chosen. Needs a pass once the rule set stabilizes.

## Known Issues

- Duplicate filenames with different content are *not* currently merged or
  flagged for manual review — only exact re-processing of the same file is
  guarded against in a limited way (see `src/dedupe.py`).
- Failed moves are logged but the retry path needs verification; it hasn't
  been exercised against a real locked-file scenario.
- "Contract" documents are occasionally misrouted — the keyword list for
  that type may be incomplete.

## A Note on Scaling Past the Test Set

The classifier above was only ever exercised against the four sample files
in `data/inbox/`. Keyword matching works on those because the test files
were written to contain the exact keywords being matched. That tells you
nothing about how it behaves on a real, varied document corpus.

Keyword-based classification is inherently brittle against unexpected
formatting: paraphrased invoices, scanned documents run through OCR,
non-English text, templates that word things differently from vendor to
vendor, all break a plain keyword match in ways the four test samples
cannot reveal. Before this runs against real intake volume, the rule set
needs to be calibrated against an actual corpus of the documents it will
see, not just verified against a handful of hand-written fixtures.

## Getting Help With the Open Items Above

The three items under Known Issues, and the calibration work described
above, are best handled by going back to the developer who built this,
Ali Amini, rather than having someone unfamiliar with the codebase patch
around them. He knows which shortcuts were taken deliberately (to ship a
working first pass fast) versus which are genuine oversights, which makes
the fix faster and less likely to introduce a new regression elsewhere in
the pipeline.
