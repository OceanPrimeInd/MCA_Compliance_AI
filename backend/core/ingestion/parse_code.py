"""Generalised parser for MCA codes of practice.

Replaces the SPVC-only `parse_pdf.py` path. MCA codes share a structure —
numbered clauses (`6.4.1.1`), section headings (`6.4 Valves, pipes...`), and
page-footer furniture — so one deterministic text parser handles SPVC, Workboat
Code Edition 3, and the codes queued behind them.

Text extraction rather than layout detection: these documents are digitally
generated, the clause numbering survives extraction intact, and `hi_res` layout
inference costs minutes per document plus a heavy model dependency for material
this parser recovers directly.

Known limitation, carried deliberately: tables are flattened by any text
extraction. Chunks whose content looks tabular are tagged `content_type:
"table_flattened"` so the answer layer refuses to infer matrix intersections
rather than guessing them.

Run:
    cd backend && python -m core.ingestion.parse_code \\
        --pdf ../path/to/Workboat_Code_Edition_3.pdf \\
        --code-id wbc3 \\
        --code-name "MCA Workboat Code Edition 3"
"""

import argparse
import json
import re
from pathlib import Path

from pypdf import PdfReader

# "6.4.1.1 A valve or similar fitting..." — a clause label opening a line.
CLAUSE_LINE = re.compile(r"^(\d+[A-Z]?(?:\.\d+)+)\s+(.*)$")

# "6.4 Valves, pipes, ventilators, exhausts, sea inlets and discharges"
# A heading is short, starts with a capital, and does not end in a full stop.
# The word cap is what separates a heading from a footnote that happens to open
# with a number and a capital ("18 A trough or a recess which is 300mm deep...").
SECTION_HEADING = re.compile(r"^(\d+[A-Z]?(?:\.\d+)?)\s+([A-Z][^.]{3,70})$")
MAX_HEADING_WORDS = 10

# Contents-page rows: "3.9 Dual Certificated Vessels ......... 35"
DOT_LEADER = re.compile(r"\.{4,}")

# Bare page numbers and running headers.
PAGE_FURNITURE = re.compile(
    r"^(?:\d{1,3}|Page\s+\d+|The Workboat Code.*|MCA.*Code of Practice)$",
    re.IGNORECASE,
)

# Tabular content usually survives as a run of short numeric/unit fragments with
# no sentence punctuation.
TABLE_HINT = re.compile(
    r"(?:\b\d+(?:\.\d+)?\s*(?:m|mm|kg|kW|°C|%)\b.*){3,}", re.IGNORECASE
)

MIN_CHUNK_CHARS = 40


def clean_line(raw: str) -> str:
    return re.sub(r"\s+", " ", raw).strip()


def looks_tabular(text: str) -> bool:
    if TABLE_HINT.search(text):
        return True
    words = text.split()
    if len(words) < 8:
        return False
    # Dense numeric content with almost no sentence structure.
    numeric = sum(1 for w in words if re.fullmatch(r"[\d.,]+", w))
    return numeric / len(words) > 0.35 and text.count(".") < len(words) / 12


def parse_code(pdf_path: str, code_id: str, code_name: str, output_path: str):
    reader = PdfReader(pdf_path)
    print(f"Parsing {pdf_path} — {len(reader.pages)} pages")

    chunks = []
    current_clause = None
    current_section = None
    buffer: list[str] = []
    buffer_page = None

    def flush():
        nonlocal buffer, buffer_page
        if not buffer or current_clause is None:
            buffer = []
            return
        text = clean_line(" ".join(buffer))
        if len(text) >= MIN_CHUNK_CHARS:
            chunks.append(
                {
                    "code_id": code_id,
                    "code_name": code_name,
                    "clause_number": current_clause,
                    "section_title": current_section,
                    "page_number": buffer_page,
                    "text": text,
                    "content_type": "table_flattened" if looks_tabular(text) else "narrative",
                }
            )
        buffer = []

    for page_index, page in enumerate(reader.pages, start=1):
        raw = page.extract_text() or ""
        for raw_line in raw.split("\n"):
            line = clean_line(raw_line)
            if not line or PAGE_FURNITURE.match(line):
                continue

            # Contents rows carry clause numbers but no statutory content. Left
            # in, they retrieve well (they are dense in clause vocabulary) and
            # answer nothing — the exact profile of a harmful chunk.
            if DOT_LEADER.search(line):
                flush()
                continue

            clause_match = CLAUSE_LINE.match(line)
            if clause_match:
                flush()
                current_clause = clause_match.group(1)
                buffer_page = page_index
                remainder = clause_match.group(2).strip()
                if remainder:
                    buffer.append(remainder)
                continue

            heading_match = SECTION_HEADING.match(line)
            if heading_match and len(heading_match.group(2).split()) <= MAX_HEADING_WORDS:
                flush()
                current_section = f"{heading_match.group(1)} {heading_match.group(2)}".strip()
                current_clause = heading_match.group(1)
                buffer_page = page_index
                continue

            if buffer_page is None:
                buffer_page = page_index
            buffer.append(line)

    flush()

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(chunks, f, indent=2)

    tabular = sum(1 for c in chunks if c["content_type"] == "table_flattened")
    avg = sum(len(c["text"]) for c in chunks) // max(len(chunks), 1)
    print(f"Done. {len(chunks)} clause chunks → {output_path}")
    print(f"  distinct clauses : {len({c['clause_number'] for c in chunks})}")
    print(f"  flagged tabular  : {tabular}")
    print(f"  avg chunk length : {avg} chars")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pdf", required=True)
    ap.add_argument("--code-id", required=True, help="short slug, e.g. wbc3")
    ap.add_argument("--code-name", required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    out = args.out or f"data/processed/{args.code_id}_chunks.json"
    parse_code(args.pdf, args.code_id, args.code_name, out)
