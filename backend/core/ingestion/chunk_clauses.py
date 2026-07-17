import json
import re
from pathlib import Path

# Matches clause numbers like "3.5.1", "12A.4.3.1", "27B.2.10", or sub-items like ".1", ".2"
CLAUSE_PATTERN = re.compile(r'^\.?(\d+[A-Z]?)(\.\d+)*\.?$')

def is_page_furniture(el, prev_page_num_seen):
    """Filters out footer page numbers and single-letter table debris."""
    text = el["text"].strip()
    if el["category"] in ("Footer", "Header") and text.isdigit():
        return True
    # Bare single digits/letters that are almost certainly OCR debris from tables
    if el["category"] == "UncategorizedText" and len(text) <= 2 and not CLAUSE_PATTERN.match(text):
        return True
    return False

def chunk_clauses(parsed_path: str, output_path: str):
    elements = json.load(open(parsed_path))

    chunks = []
    current_section_title = None   # e.g. "Machinery, Propulsion and Fuel Systems"
    current_clause_number = None   # e.g. "8.9.2.1"
    last_valid_clause_number = None   # tracks the most recent real clause number seen, for inheritance
    buffer_text = []
    buffer_page = None

    def flush():
        nonlocal buffer_text, buffer_page, current_clause_number
        if buffer_text:
            # If this chunk never got its own clause label, inherit the last real one seen
            clause_to_use = current_clause_number or last_valid_clause_number
            chunks.append({
                "clause_number": clause_to_use,
                "section_title": current_section_title,
                "page_number": buffer_page,
                "text": " ".join(buffer_text).strip(),
            })
        buffer_text = []

    for el in elements:
        text = el["text"].strip()
        cat = el["category"]

        if not text or is_page_furniture(el, None):
            continue

        if cat == "Title":
            flush()
            current_section_title = text
            current_clause_number = None
            continue

        if cat in ("Table", "Image", "Formula", "FigureCaption"):
            # Keep tables/formulas as their own standalone chunk, tagged clearly
            flush()
            chunks.append({
                "clause_number": current_clause_number or last_valid_clause_number,
                "section_title": current_section_title,
                "page_number": el["page_number"],
                "text": text,
                "content_type": cat.lower(),
            })
            continue

        # Detect a standalone clause number label (often split from its text)
        if CLAUSE_PATTERN.match(text) and len(text) <= 12:
            flush()
            current_clause_number = text.lstrip(".")
            last_valid_clause_number = current_clause_number
            buffer_page = el["page_number"]
            continue

        # Detect clause number embedded at start of the text itself, e.g. "3.5.1 It is the responsibility..."
        embedded = re.match(r'^(\d+[A-Z]?(\.\d+)+)\s+(.*)', text)
        if embedded:
            flush()
            current_clause_number = embedded.group(1)
            last_valid_clause_number = current_clause_number
            buffer_page = el["page_number"]
            buffer_text.append(embedded.group(3))
            continue

        # Otherwise, regular narrative/list content — attach to current clause
        if buffer_page is None:
            buffer_page = el["page_number"]
        buffer_text.append(text)

    flush()

    # Drop empty/near-empty chunks (leftover junk)
    chunks = [c for c in chunks if len(c["text"]) > 10]

    # Drop any chunk that still has no clause number even after inheritance —
    # this guarantees nothing uncitable ever reaches the model
    chunks = [c for c in chunks if c["clause_number"] is not None]

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(chunks, f, indent=2)

    print(f"Done. {len(chunks)} clause-level chunks → {output_path}")

if __name__ == "__main__":
    chunk_clauses(
        parsed_path="data/processed/spvc_2025_parsed.json",
        output_path="data/processed/spvc_2025_chunks.json",
    )