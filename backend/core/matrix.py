"""Structured Regulatory Matrix — deterministic lookup for multi-variable tables.

The problem this solves: PDF extraction flattens tables. A row/column matrix
mapping vessel length against area category arrives as a run of values with no
recoverable headers, so the answer layer can only name the table and decline.
That is safe but unsatisfying, and it fails on exactly the questions
practitioners ask most (life-saving appliances, radio, firefighting).

The fix is to hold those specific tables as structured JSON and resolve them
deterministically — no retrieval, no model, no inference.

THE VERIFICATION GATE
---------------------
Every row carries `verified_by` and `verified_on`. A row without both is
IGNORED at load time and never reaches an answer. This is not ceremony: a
transcription error here produces a fabricated statutory requirement delivered
with an authoritative citation, which is worse than any hallucination the
retrieval path can produce, because it looks exactly like ground truth.

Whoever transcribes a table must be able to check it against the published Code.
The engine will not take their word for it implicitly — it requires the claim to
be recorded.
"""

import json
from dataclasses import dataclass
from pathlib import Path

from core.vessel import VesselProfile

MATRIX_DIR = Path(__file__).resolve().parents[1] / "data" / "matrices"


@dataclass(frozen=True)
class MatrixRow:
    """One resolved requirement, valid for a bounded set of vessel states."""

    requirements: dict
    clause: str
    page: int | None
    length_min: float | None
    length_max: float | None
    categories: frozenset | None
    passengers_min: int | None
    passengers_max: int | None
    verified_by: str
    verified_on: str

    def matches(self, vessel: VesselProfile) -> bool:
        loa = vessel.length_overall
        if self.length_min is not None and loa < self.length_min:
            return False
        if self.length_max is not None and loa >= self.length_max:
            return False
        if self.categories is not None and vessel.area_category not in self.categories:
            return False
        if self.passengers_min is not None and vessel.passenger_count < self.passengers_min:
            return False
        if self.passengers_max is not None and vessel.passenger_count > self.passengers_max:
            return False
        return True

    def describe_scope(self) -> str:
        parts = []
        if self.length_min is not None and self.length_max is not None:
            parts.append(f"{self.length_min}m to under {self.length_max}m")
        elif self.length_min is not None:
            parts.append(f"{self.length_min}m and over")
        elif self.length_max is not None:
            parts.append(f"under {self.length_max}m")
        if self.categories is not None:
            parts.append("Category " + ", ".join(str(c) for c in sorted(self.categories)))
        if self.passengers_min is not None:
            parts.append(f"{self.passengers_min}+ passengers")
        if self.passengers_max is not None:
            parts.append(f"up to {self.passengers_max} passengers")
        return "; ".join(parts) if parts else "all vessels"


@dataclass(frozen=True)
class Matrix:
    matrix_id: str
    code_id: str
    code_name: str
    title: str
    table_reference: str
    topic_keywords: tuple
    rows: tuple

    def resolve(self, vessel: VesselProfile) -> MatrixRow | None:
        """The single row governing this vessel, or None.

        Rows are expected to partition the vessel space. If more than one
        matches, the first is returned and the overlap is reported by
        `validate()` — an ambiguous table is a transcription bug, not a
        judgement call for the engine to make at query time.
        """
        for row in self.rows:
            if row.matches(vessel):
                return row
        return None

    def validate(self) -> list[str]:
        """Overlapping scopes, checked at load rather than discovered in an answer."""
        problems = []
        for i, a in enumerate(self.rows):
            for b in self.rows[i + 1 :]:
                if _overlaps(a, b):
                    problems.append(
                        f"{self.matrix_id}: rows '{a.describe_scope()}' and "
                        f"'{b.describe_scope()}' overlap — a vessel could match both"
                    )
        return problems


def _interval_overlaps(a_min, a_max, b_min, b_max) -> bool:
    lo_a, hi_a = (a_min if a_min is not None else float("-inf")), (
        a_max if a_max is not None else float("inf")
    )
    lo_b, hi_b = (b_min if b_min is not None else float("-inf")), (
        b_max if b_max is not None else float("inf")
    )
    return lo_a < hi_b and lo_b < hi_a


def _overlaps(a: MatrixRow, b: MatrixRow) -> bool:
    if not _interval_overlaps(a.length_min, a.length_max, b.length_min, b.length_max):
        return False
    if a.categories is not None and b.categories is not None and not (a.categories & b.categories):
        return False
    if not _interval_overlaps(
        a.passengers_min, a.passengers_max, b.passengers_min, b.passengers_max
    ):
        return False
    return True


def _load_row(raw: dict, matrix_id: str) -> MatrixRow | None:
    verified_by = (raw.get("verified_by") or "").strip()
    verified_on = (raw.get("verified_on") or "").strip()
    if not verified_by or not verified_on:
        print(
            f"[matrix] {matrix_id}: skipping unverified row "
            f"'{raw.get('scope_label', raw.get('clause', '?'))}' — set verified_by and "
            f"verified_on once the values are checked against the published Code."
        )
        return None

    cats = raw.get("categories")
    return MatrixRow(
        requirements=raw["requirements"],
        clause=raw["clause"],
        page=raw.get("page"),
        length_min=raw.get("length_min"),
        length_max=raw.get("length_max"),
        categories=frozenset(cats) if cats is not None else None,
        passengers_min=raw.get("passengers_min"),
        passengers_max=raw.get("passengers_max"),
        verified_by=verified_by,
        verified_on=verified_on,
    )


class MatrixRegistry:
    """Loads every verified matrix from data/matrices/."""

    def __init__(self, matrix_dir: Path = MATRIX_DIR):
        self.matrices: list[Matrix] = []
        self.skipped: list[str] = []

        if not matrix_dir.exists():
            return

        for path in sorted(matrix_dir.glob("*.json")):
            payload = json.load(open(path))
            rows = tuple(
                r for r in (_load_row(x, payload["matrix_id"]) for x in payload["rows"]) if r
            )
            if not rows:
                self.skipped.append(payload["matrix_id"])
                print(f"[matrix] {payload['matrix_id']}: no verified rows — matrix inactive")
                continue

            matrix = Matrix(
                matrix_id=payload["matrix_id"],
                code_id=payload["code_id"],
                code_name=payload["code_name"],
                title=payload["title"],
                table_reference=payload["table_reference"],
                topic_keywords=tuple(k.lower() for k in payload["topic_keywords"]),
                rows=rows,
            )
            for problem in matrix.validate():
                print(f"[matrix] WARNING {problem}")

            self.matrices.append(matrix)
            print(f"[matrix] {matrix.matrix_id}: {len(rows)} verified rows")

    def find(self, question: str, code_ids: list[str] | None = None) -> list[Matrix]:
        """Matrices whose topic keywords appear in the question."""
        q = question.lower()
        return [
            m
            for m in self.matrices
            if (not code_ids or m.code_id in code_ids)
            and any(k in q for k in m.topic_keywords)
        ]

    def resolve_for(self, question: str, vessel: VesselProfile, code_ids=None) -> list[dict]:
        """Deterministic answers for every matrix this question touches."""
        if vessel is None:
            return []

        resolved = []
        for matrix in self.find(question, code_ids):
            row = matrix.resolve(vessel)
            if row is None:
                continue
            resolved.append(
                {
                    "matrix_id": matrix.matrix_id,
                    "title": matrix.title,
                    "code_name": matrix.code_name,
                    "table_reference": matrix.table_reference,
                    "clause": row.clause,
                    "page": row.page,
                    "scope": row.describe_scope(),
                    "requirements": row.requirements,
                    "verified_by": row.verified_by,
                    "verified_on": row.verified_on,
                }
            )
        return resolved


def format_for_prompt(resolved: list[dict]) -> str:
    """Render resolved rows as authoritative structured context."""
    if not resolved:
        return ""

    blocks = []
    for r in resolved:
        values = "\n".join(f"  - {k}: {v}" for k, v in r["requirements"].items())
        blocks.append(
            f"[STRUCTURED MATRIX — {r['code_name']}, {r['table_reference']}, "
            f"Clause {r['clause']}, p.{r['page']}]\n"
            f"  Applies to: {r['scope']}\n"
            f"  Resolved values for THIS vessel:\n{values}\n"
            f"  (Transcribed and verified by {r['verified_by']} on {r['verified_on']}.)"
        )

    return (
        "\n\n[AUTHORITATIVE STRUCTURED LOOKUP]\n"
        "These values were resolved deterministically from a verified transcription "
        "of the table, not from retrieved text. The intersection has ALREADY been "
        "traced for this vessel — state these values directly and cite the table "
        "reference. Do NOT mark these REQUIRES VISUAL CONFIRMATION.\n\n"
        + "\n\n".join(blocks)
    )
