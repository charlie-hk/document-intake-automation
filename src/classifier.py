"""Rule-based document classifier.

Reads config/classification_rules.json and matches a document's text
content against each type's keyword list. The first type with a keyword
hit wins; if nothing matches, the document falls through to "other".

Note: this is intentionally simple (no AI/ML step). It's meant to be a
first pass that a smarter classifier could later sit behind.
"""

import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config", "classification_rules.json")


def load_rules(config_path=CONFIG_PATH):
    with open(config_path, "r", encoding="utf-8") as f:
        return json.load(f)


def classify(text, rules=None):
    """Return the document type (str) whose keyword list matches the text.

    Falls back to "other" if no type matches, or if a type has no
    keywords configured at all (an empty keyword list can never match).
    """
    if rules is None:
        rules = load_rules()

    text_lower = text.lower()

    for doc_type, spec in rules.items():
        if doc_type == "other":
            continue
        keywords = spec.get("keywords", [])
        for kw in keywords:
            if kw.lower() in text_lower:
                return doc_type

    return "other"
