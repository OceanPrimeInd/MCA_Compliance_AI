"""Extract statutory scope conditions from clause text — deterministically.

Why regex and not an LLM: this is a compliance product. Every exclusion decision
must be auditable and reproducible. A rule you can read beats a model call you
cannot inspect, and each match records the exact phrase it fired on so a
surveyor can check the reasoning.

Output is a SIDECAR file aligned by position with the chunks already embedded in
the .npz index. Nothing is re-embedded and no chunk is deleted, so this costs
zero API quota and cannot invalidate the existing index.

Run:
    cd backend && python -m core.ingestion.extract_conditions
"""

import json
import re
from pathlib import Path

from core.vessel import Applicability

# Inclusive upper bounds ("up to and including 15m") are stored as an exclusive
# bound nudged past the value, so a single comparison handles both forms.
EPSILON = 1e-6

# A length phrase only counts as a vessel scope condition when it is attached to
# a vessel noun. Without this guard, "a painter not less than 15 metres" and
# "a hose of at least 10 metres" are misread as vessel length limits — the most
# damaging false positive available, because it silently hides binding clauses.
VESSEL_NOUN = r"(?:vessels?|craft|boats?|ribs?)"
LEN_UNIT = r"(?:metres|meters|m)\b"
NUM = r"(\d+(?:\.\d+)?)"

LENGTH_MAX_PATTERNS = [
    rf"{VESSEL_NOUN}\s+(?:of\s+)?less than\s+{NUM}\s*{LEN_UNIT}",
    rf"{VESSEL_NOUN}\s+(?:of\s+)?under\s+{NUM}\s*{LEN_UNIT}",
    rf"{VESSEL_NOUN}\s+(?:of\s+)?below\s+{NUM}\s*{LEN_UNIT}",
    rf"less than\s+{NUM}\s*{LEN_UNIT}\s+in length",
]

LENGTH_MAX_INCLUSIVE_PATTERNS = [
    rf"{VESSEL_NOUN}\s+(?:of\s+)?up to,?\s+and including,?\s+{NUM}\s*{LEN_UNIT}",
    rf"{VESSEL_NOUN}\s+(?:of\s+)?not (?:more|greater) than\s+{NUM}\s*{LEN_UNIT}",
    rf"{VESSEL_NOUN}\s+(?:of\s+)?{NUM}\s*{LEN_UNIT}\s+(?:in length\s+)?(?:and|or)\s+(?:under|below|less)",
]

LENGTH_MIN_PATTERNS = [
    rf"{VESSEL_NOUN}\s+(?:of\s+)?{NUM}\s*{LEN_UNIT}\s+(?:in length\s+)?(?:and|or)\s+(?:over|above|more)",
    rf"{VESSEL_NOUN}\s+(?:of\s+)?not less than\s+{NUM}\s*{LEN_UNIT}",
    rf"{VESSEL_NOUN}\s+(?:of\s+)?exceeding\s+{NUM}\s*{LEN_UNIT}",
    rf"{VESSEL_NOUN}\s+(?:of\s+)?(?:at least|greater than|more than)\s+{NUM}\s*{LEN_UNIT}",
    rf"{NUM}\s*{LEN_UNIT}\s+in length and over",
]

LENGTH_RANGE_PATTERNS = [
    rf"{VESSEL_NOUN}\s+(?:of\s+)?between\s+{NUM}\s*(?:{LEN_UNIT})?\s+and\s+{NUM}\s*{LEN_UNIT}",
    rf"{VESSEL_NOUN}\s+(?:of\s+)?{NUM}\s*{LEN_UNIT}\s+(?:up )?to (?:less than\s+)?{NUM}\s*{LEN_UNIT}",
]

# Category scoping. Only explicit lists and ranges are parsed. Phrases like
# "Category 2 and above" are deliberately NOT parsed: in the SPVC the numbering
# runs from 0 (least restricted) to 6 (most restricted), so "above" is ambiguous
# between numerically higher and operationally less restricted. Guessing the
# direction would exclude binding clauses.
# The SPVC's own phrasing is "area category of operation 0 or 1" — the
# "of operation" clause sits between the noun and the digits, which is why a
# naive "category N" pattern matches nothing in this corpus.
_CAT_PREFIX = r"(?:area\s+)?categor(?:y|ies)(?:\s+of\s+operation)?"

CATEGORY_LIST_PATTERN = re.compile(
    _CAT_PREFIX + r"\s+((?:\d\s*(?:,|or|and|to|-|–)?\s*)+)",
    re.IGNORECASE,
)
CATEGORY_RANGE_PATTERN = re.compile(
    _CAT_PREFIX + r"\s+(\d)\s*(?:to|-|–)\s*(\d)",
    re.IGNORECASE,
)

PASSENGER_MIN_PATTERNS = [
    r"more than\s+(\d+)\s+passengers",
    r"carrying\s+(?:more than|over)\s+(\d+)\s+passengers",
    r"in excess of\s+(\d+)\s+passengers",
]

PASSENGER_MAX_PATTERNS = [
    r"(?:up to,?\s+and including,?|not more than|no more than|fewer than or equal to)\s+(\d+)\s+passengers",
    r"(\d+)\s+(?:or fewer|or less)\s+passengers",
    r"carrying\s+up to\s+(\d+)\s+passengers",
]


def _first_match(patterns, text):
    """Return (value, matched_phrase) for the first pattern that fires."""
    for pat in patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            return float(m.group(1)), m.group(0).strip()
    return None, None


# A category mention only restricts scope when it sits in a scoping
# construction. Plain prose referring to categories ("vessels in categories 3
# and 4 typically...") must not become a filter, because a false category
# restriction silently hides binding clauses — the worst failure available here.
SCOPING_CONTEXT = re.compile(
    r"(?:applies?\s+(?:only\s+)?to|applicable to|application|restricted to|"
    r"certificated for|intended to operate in|operating in|operate in|"
    r"for (?:a )?vessels?[^.]{0,40}\bin\b|when operating in)",
    re.IGNORECASE,
)

# The Code's own scoping idiom. Self-evidently a restriction wherever it appears.
STRONG_CATEGORY_IDIOM = re.compile(r"categor(?:y|ies)\s+of\s+operation", re.IGNORECASE)


def _category_match_is_scoping(text: str, match: re.Match) -> bool:
    if STRONG_CATEGORY_IDIOM.search(match.group(0)):
        return True
    window = text[max(0, match.start() - 90) : match.start()]
    return bool(SCOPING_CONTEXT.search(window))


def _parse_categories(text):
    """Return (frozenset_of_categories, evidence_phrase) or (None, None)."""
    m = CATEGORY_RANGE_PATTERN.search(text)
    if m and _category_match_is_scoping(text, m):
        lo, hi = int(m.group(1)), int(m.group(2))
        if lo <= hi:
            return frozenset(range(lo, hi + 1)), m.group(0).strip()

    m = CATEGORY_LIST_PATTERN.search(text)
    if m and _category_match_is_scoping(text, m):
        digits = re.findall(r"\d", m.group(1))
        cats = {int(d) for d in digits if 0 <= int(d) <= 6}
        if cats:
            return frozenset(cats), m.group(0).strip()
    return None, None


def extract(text: str) -> Applicability:
    """Parse scope conditions out of one clause's text."""
    evidence = []
    length_min = length_max = None

    # Ranges first — they set both bounds and would otherwise be half-matched.
    for pat in LENGTH_RANGE_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            lo, hi = float(m.group(1)), float(m.group(2))
            if lo < hi:
                length_min, length_max = lo, hi
                evidence.append(m.group(0).strip())
            break

    if length_max is None:
        val, phrase = _first_match(LENGTH_MAX_PATTERNS, text)
        if val is not None:
            length_max = val
            evidence.append(phrase)

    if length_max is None:
        val, phrase = _first_match(LENGTH_MAX_INCLUSIVE_PATTERNS, text)
        if val is not None:
            length_max = val + EPSILON
            evidence.append(phrase)

    if length_min is None:
        val, phrase = _first_match(LENGTH_MIN_PATTERNS, text)
        if val is not None:
            length_min = val
            evidence.append(phrase)

    # A parse that produces an empty interval is a misparse, not a real scope.
    if length_min is not None and length_max is not None and length_min >= length_max:
        length_min = length_max = None
        evidence.append("[discarded contradictory length parse]")

    categories, cat_phrase = _parse_categories(text)
    if cat_phrase:
        evidence.append(cat_phrase)

    pax_min, pax_phrase = _first_match(PASSENGER_MIN_PATTERNS, text)
    pax_max, pax_max_phrase = _first_match(PASSENGER_MAX_PATTERNS, text)

    # A chunk stating both "more than 12 passengers" and "up to 12 passengers"
    # is describing the scope of two different regimes, not one scope. Same
    # reasoning as the contradictory-length guard: an impossible interval is a
    # misparse, and acting on it would exclude a clause that binds everyone.
    if pax_min is not None and pax_max is not None and (pax_min + 1) > pax_max:
        pax_min = pax_max = None
        evidence.append("[discarded contradictory passenger parse]")
    else:
        if pax_phrase:
            evidence.append(pax_phrase)
        if pax_max_phrase:
            evidence.append(pax_max_phrase)

    return Applicability(
        length_min=length_min,
        length_max=length_max,
        categories=categories,
        # "more than 12 passengers" binds at 13.
        passengers_min=int(pax_min) + 1 if pax_min is not None else None,
        passengers_max=int(pax_max) if pax_max is not None else None,
        vessel_types=None,  # see note in build_sidecar()
        evidence=tuple(evidence),
    )


def is_toc_debris(chunk: dict) -> bool:
    """Table-of-contents pages parsed as content. Never useful, always noisy."""
    text = chunk.get("text", "")
    if "......" in text or "…" * 3 in text:
        return True
    if chunk.get("section_title") == "Contents":
        return True
    return False


def has_suspect_clause_number(chunk: dict) -> bool:
    """Clause numbers the chunker clearly got wrong (e.g. 1500, 262).

    The SPVC's top-level sections do not reach three digits, so a bare integer of
    that size is a page number that inherited a clause label.

    These chunks are FLAGGED, never dropped. They are concentrated in the
    Definitions section — "Critical equipment means...", "Design category
    means..." — which is exactly the material the prompt requires be quoted
    verbatim rather than paraphrased. Excluding them would make it impossible to
    answer a definition question correctly. The answer layer cites them by page
    and section instead of by clause.
    """
    clause = chunk.get("clause_number")
    return bool(clause and re.fullmatch(r"\d{3,}", str(clause)))


def clause_ancestors(clause: str):
    """'5.6.3.1' -> ['5.6.3', '5.6', '5'], nearest parent first.

    Scope conditions in the SPVC are usually stated once on a parent clause and
    left implicit in its children, so a child chunk read in isolation looks
    unconstrained when it is not.
    """
    if not clause or not re.fullmatch(r"\d+[A-Z]?(?:\.\d+)*", str(clause)):
        return []
    parts = str(clause).split(".")
    # Stop at depth 2. A bare top-level section ("1", "7") is a container whose
    # chunk text is long narrative prose; any condition parsed from it is far
    # more likely incidental than scoping, and inheriting it would wrongly
    # constrain every clause in the section.
    return [".".join(parts[:i]) for i in range(len(parts) - 1, 1, -1)]


def inherit(child: Applicability, parent: Applicability) -> Applicability:
    """Fill unset axes of `child` from `parent`. Never overrides or contradicts."""
    return Applicability(
        length_min=child.length_min if child.length_min is not None else parent.length_min,
        length_max=child.length_max if child.length_max is not None else parent.length_max,
        categories=child.categories if child.categories is not None else parent.categories,
        passengers_min=(
            child.passengers_min if child.passengers_min is not None else parent.passengers_min
        ),
        passengers_max=(
            child.passengers_max if child.passengers_max is not None else parent.passengers_max
        ),
        vessel_types=child.vessel_types if child.vessel_types is not None else parent.vessel_types,
        evidence=tuple(child.evidence)
        + tuple(f"[inherited] {e}" for e in parent.evidence if e not in child.evidence),
    )


def load_chunks(source_path: str) -> list:
    """Load the chunk list, preferring the .npz index over the .json source.

    Alignment matters more than convenience here. `build_index` drops chunks
    below a length threshold, so the JSON source and the embedded index can hold
    different numbers of chunks. A sidecar built from the JSON would then be
    offset against the index, and every applicability decision would be attached
    to the wrong clause. Reading from the index makes that impossible.
    """
    if source_path.endswith(".npz"):
        import numpy as np

        data = np.load(source_path, allow_pickle=True)
        return json.loads(str(data["chunks"]))
    return json.load(open(source_path))


def build_sidecar(chunks_path: str, output_path: str):
    chunks = load_chunks(chunks_path)

    stats = {
        "total": len(chunks),
        "excluded_toc": 0,
        "flagged_unreliable_clause": 0,
        "own_conditions": 0,
        "gained_by_inheritance": 0,
        "with_length": 0,
        "with_category": 0,
        "with_passengers": 0,
        "unconstrained": 0,
    }

    # Pass 1 — parse each chunk's own text.
    own = []
    for chunk in chunks:
        excluded = is_toc_debris(chunk)
        if excluded:
            stats["excluded_toc"] += 1
        own.append(Applicability() if excluded else extract(chunk.get("text", "")))

    # Pass 2 — build the clause -> conditions map used for inheritance. Where
    # several chunks share a clause number, merge what each of them found.
    by_clause: dict[str, Applicability] = {}
    for chunk, app in zip(chunks, own):
        clause = chunk.get("clause_number")
        if not clause or app.is_unconstrained():
            continue
        key = str(clause)
        by_clause[key] = inherit(app, by_clause[key]) if key in by_clause else app

    # Pass 3 — walk each chunk's ancestors, nearest first, filling unset axes.
    records = []
    for chunk, app in zip(chunks, own):
        excluded = is_toc_debris(chunk)
        reason = "table_of_contents" if excluded else None

        had_own = not app.is_unconstrained()
        if had_own:
            stats["own_conditions"] += 1

        if not excluded:
            for ancestor in clause_ancestors(chunk.get("clause_number")):
                if ancestor in by_clause:
                    app = inherit(app, by_clause[ancestor])
            if not had_own and not app.is_unconstrained():
                stats["gained_by_inheritance"] += 1

        clause_reliable = not has_suspect_clause_number(chunk)
        if not clause_reliable:
            stats["flagged_unreliable_clause"] += 1

        if app.length_min is not None or app.length_max is not None:
            stats["with_length"] += 1
        if app.categories is not None:
            stats["with_category"] += 1
        if app.passengers_min is not None or app.passengers_max is not None:
            stats["with_passengers"] += 1
        if app.is_unconstrained() and not excluded:
            stats["unconstrained"] += 1

        records.append(
            {
                "clause_number": chunk.get("clause_number"),
                "page_number": chunk.get("page_number"),
                "excluded": excluded,
                "exclude_reason": reason,
                "clause_reliable": clause_reliable,
                "applicability": app.to_dict(),
            }
        )

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump({"stats": stats, "records": records}, f, indent=2)

    print(f"Wrote {len(records)} applicability records → {output_path}")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(
        "\nNote: vessel_type is never inferred. Clauses mention vessel types "
        "incidentally far more often than they scope by them, and a wrong type "
        "exclusion hides a binding clause. Type filtering is left to the model."
    )


if __name__ == "__main__":
    import argparse

    ap = argparse.ArgumentParser(description="Extract statutory scope conditions.")
    ap.add_argument(
        "--chunks",
        default="data/processed/spvc_2025_index.npz",
        help="source of chunks. Pass the .npz index wherever one exists — it "
        "guarantees the sidecar aligns with what was actually embedded.",
    )
    ap.add_argument(
        "--out",
        default=None,
        help="sidecar path; defaults to <name>_applicability.json alongside the input",
    )
    args = ap.parse_args()

    out = args.out or re.sub(r"_(chunks\.json|index\.npz)$", "_applicability.json", args.chunks)
    build_sidecar(chunks_path=args.chunks, output_path=out)
