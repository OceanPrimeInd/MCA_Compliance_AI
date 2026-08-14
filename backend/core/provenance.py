"""Compliance Provenance Record — the accumulating evidence layer.

Every answer this engine produces is a decision a professional may later have to
defend: to a Certifying Authority, to a PI insurer, or to themselves in two
years when they cannot remember why a hull was drawn the way it was. A chat
transcript does not defend anything. A dated record of exactly which clauses
were considered, which were excluded and on what stated ground, against which
version of which code, does.

Three things follow from keeping that record, in increasing order of value:

  1. EVIDENCE. A designer can export a dated justification note naming the
     governing clause and the vessel state it was decided against.

  2. REPRODUCIBILITY. Because the vessel snapshot, corpus fingerprints and
     pipeline version are all stored, any past answer can be explained even
     after the vessel, the corpus or the engine has changed.

  3. IMPACT ANALYSIS. This is the part no competitor can copy without first
     having kept the record. When a clause changes — a new MGN, a code
     amendment — `find_affected` answers "which of this customer's past
     decisions relied on that clause?" A tool that only answers questions cannot
     do this at any price, because it never kept the evidence.

The record is append-only. Answers are never rewritten, because a compliance
record that can change retroactively is not a compliance record.
"""

import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "processed" / "provenance.db"


def _get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS provenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            asked_at TEXT NOT NULL,
            question TEXT NOT NULL,
            answer TEXT NOT NULL,

            -- Vessel state AT THE TIME OF ASKING. Snapshotted rather than
            -- referenced, because the profile can be edited later and that must
            -- not silently rewrite what a past decision was based on.
            vessel_json TEXT,

            -- What the engine actually used and rejected.
            clauses_used TEXT NOT NULL,      -- [{code_id, clause, page, scope}]
            clauses_excluded TEXT NOT NULL,  -- [{code_id, clause, page, reason}]

            -- Reproducibility: which corpora, which engine.
            corpus_fingerprints TEXT NOT NULL,
            pipeline_version TEXT NOT NULL,
            model_used TEXT,

            citations_verified INTEGER NOT NULL,
            guardrail_triggered TEXT,
            verdict_guard TEXT
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_prov_user ON provenance (user_id, asked_at)")
    return conn


def record(
    user_id: str,
    question: str,
    result: dict,
    corpus_fingerprints: dict,
    pipeline_version: str,
) -> int:
    """Append one decision to the record. Returns its id."""
    used = [
        {
            "code_id": s.get("code_id"),
            "code_name": s.get("code_name"),
            "clause": s.get("clause"),
            "page": s.get("page"),
            "scope": s.get("scope_condition"),
        }
        for s in result.get("sources", [])
    ]
    excluded = [
        {
            "code_id": f.get("code_id"),
            "code_name": f.get("code_name"),
            "clause": f.get("clause_number"),
            "page": f.get("page_number"),
            "reason": f.get("reason"),
        }
        for f in result.get("filtered_out", [])
    ]

    conn = _get_conn()
    cur = conn.execute(
        "INSERT INTO provenance (user_id, asked_at, question, answer, vessel_json, "
        "clauses_used, clauses_excluded, corpus_fingerprints, pipeline_version, "
        "model_used, citations_verified, guardrail_triggered, verdict_guard) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            user_id,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
            question,
            result.get("answer", ""),
            json.dumps(result.get("vessel")),
            json.dumps(used),
            json.dumps(excluded),
            json.dumps(corpus_fingerprints),
            pipeline_version,
            result.get("model_used"),
            int(bool(result.get("verified"))),
            result.get("guardrail_triggered"),
            json.dumps(result.get("verdict_guard")) if result.get("verdict_guard") else None,
        ),
    )
    conn.commit()
    record_id = cur.lastrowid
    conn.close()
    return record_id


def _row_to_dict(row) -> dict:
    return {
        "id": row[0],
        "asked_at": row[1],
        "question": row[2],
        "answer": row[3],
        "vessel": json.loads(row[4]) if row[4] else None,
        "clauses_used": json.loads(row[5]),
        "clauses_excluded": json.loads(row[6]),
        "corpus_fingerprints": json.loads(row[7]),
        "pipeline_version": row[8],
        "model_used": row[9],
        "citations_verified": bool(row[10]),
        "guardrail_triggered": row[11],
        "verdict_guard": json.loads(row[12]) if row[12] else None,
    }


_SELECT = (
    "SELECT id, asked_at, question, answer, vessel_json, clauses_used, "
    "clauses_excluded, corpus_fingerprints, pipeline_version, model_used, "
    "citations_verified, guardrail_triggered, verdict_guard FROM provenance"
)


def list_records(user_id: str, limit: int = 50, offset: int = 0) -> list:
    conn = _get_conn()
    rows = conn.execute(
        f"{_SELECT} WHERE user_id = ? ORDER BY asked_at DESC LIMIT ? OFFSET ?",
        (user_id, limit, offset),
    ).fetchall()
    conn.close()
    return [_row_to_dict(r) for r in rows]


def get_record(user_id: str, record_id: int) -> dict | None:
    conn = _get_conn()
    row = conn.execute(
        f"{_SELECT} WHERE user_id = ? AND id = ?", (user_id, record_id)
    ).fetchone()
    conn.close()
    return _row_to_dict(row) if row else None


def find_affected(user_id: str, code_id: str, clauses: list) -> list:
    """Past decisions that relied on any of `clauses` in `code_id`.

    The feature the record exists for. When an MGN amends clause 8.3.2, a
    customer needs to know which of their past design decisions rested on it —
    not to re-read the whole Code. A product without a stored record cannot
    answer this, however good its retrieval is.

    Matching is done in Python rather than SQL because clauses_used is JSON;
    at per-user volumes this is a scan over tens to hundreds of rows, and
    keeping it simple beats a schema that would need migrating later.
    """
    wanted = {str(c) for c in clauses}

    affected = []
    for rec in list_records(user_id, limit=10_000):
        hits = [
            u
            for u in rec["clauses_used"]
            if str(u.get("clause")) in wanted and (not code_id or u.get("code_id") == code_id)
        ]
        if hits:
            affected.append(
                {
                    "id": rec["id"],
                    "asked_at": rec["asked_at"],
                    "question": rec["question"],
                    "vessel": rec["vessel"],
                    "affected_clauses": hits,
                }
            )
    return affected


def summary(user_id: str) -> dict:
    """Headline counts for the record view."""
    conn = _get_conn()
    row = conn.execute(
        "SELECT COUNT(*), MIN(asked_at), MAX(asked_at), "
        "SUM(CASE WHEN citations_verified = 0 THEN 1 ELSE 0 END) "
        "FROM provenance WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    conn.close()

    total = row[0] or 0
    return {
        "decisions_recorded": total,
        "first_recorded": row[1],
        "last_recorded": row[2],
        "unverified_citations": row[3] or 0,
    }


_MD_HEADING = re.compile(r"^\s*#{1,6}\s*(.+?)\s*$")
_MD_BOLD = re.compile(r"\*\*(.+?)\*\*")
_MD_ITALIC = re.compile(r"(?<![*\w])\*([^*\n]+)\*(?![*\w])")
_MD_CODE = re.compile(r"`([^`]+)`")
_VERDICT_LINE = re.compile(
    r"^\s*VERDICT:\s*(\w+)\s*[—\-–]\s*(.+?)\s*$", re.IGNORECASE | re.MULTILINE
)
# Decorative emoji the model puts in section headings. Fine on screen, wrong in
# a document that may be printed, filed, or read by a Certifying Authority.
_HEADING_EMOJI = re.compile(r"[✀-➿-\U0001F000-\U0001FAFF☀-⛿]️?")


def _plain_text(markdown: str) -> str:
    """Flatten the model's markdown into text fit for a formal document.

    The design note exists to be pasted into a design justification file, a
    Word document, or a Certifying Authority's own form. Markdown syntax
    surviving into that context reads as a system defect, whatever the content
    underneath says.
    """
    lines = []
    for raw in (markdown or "").split("\n"):
        line = raw.rstrip()

        heading = _MD_HEADING.match(line)
        if heading:
            text = _HEADING_EMOJI.sub("", heading.group(1)).strip()
            lines.append("")
            lines.append(text.upper())
            lines.append("-" * len(text))
            continue

        if line.lstrip().startswith(">"):
            line = "    " + line.lstrip().lstrip(">").strip()

        line = _MD_BOLD.sub(r"\1", line)
        line = _MD_ITALIC.sub(r"\1", line)
        line = _MD_CODE.sub(r"\1", line)
        line = re.sub(r"^(\s*)[-*]\s+", r"\1  - ", line)
        lines.append(line)

    # Collapse the runs of blank lines the heading rule introduces.
    out, blank = [], False
    for line in lines:
        if not line.strip():
            if blank:
                continue
            blank = True
        else:
            blank = False
        out.append(line)
    return "\n".join(out).strip()


def export_design_note(record: dict) -> str:
    """A dated, attributable block a designer can paste into a justification file.

    Deliberately plain text: it has to survive being pasted into Word, a PDF, an
    email, or a Certifying Authority's own form.
    """
    vessel = record.get("vessel") or {}
    vessel_line = (
        f"{vessel.get('length_overall')}m {vessel.get('vessel_type')}, "
        f"{vessel.get('hull_material')} hull, Area Category "
        f"{vessel.get('area_category')}, {vessel.get('passenger_count')} passenger(s)"
        if vessel
        else "No vessel profile set — answer is general, not vessel-specific."
    )

    used = "\n".join(
        f"  - {u.get('code_name') or u.get('code_id')} — Clause {u.get('clause')}, "
        f"p.{u.get('page')}"
        + (f"  [scope: {u['scope']}]" if u.get("scope") else "")
        for u in record["clauses_used"]
    ) or "  (none)"

    excluded = "\n".join(
        f"  - Clause {e.get('clause')}, p.{e.get('page')} — excluded: {e.get('reason')}"
        for e in record["clauses_excluded"]
    ) or "  (none)"

    fingerprints = "\n".join(
        f"  - {code}: {fp}" for code, fp in (record["corpus_fingerprints"] or {}).items()
    ) or "  (not recorded)"

    raw_answer = record.get("answer", "")
    verdict_match = _VERDICT_LINE.search(raw_answer)
    if verdict_match:
        verdict = f"{verdict_match.group(1).replace('_', ' ').upper()} — {verdict_match.group(2)}"
        body = _plain_text(raw_answer[: verdict_match.start()] + raw_answer[verdict_match.end() :])
    else:
        verdict = "Not stated"
        body = _plain_text(raw_answer)

    guard = record.get("verdict_guard")
    guard_block = (
        f"\n\n  SAFETY DOWNGRADE — originally stated as "
        f"{guard['downgraded_from'].replace('_', ' ')}.\n  {guard['reason']}"
        if guard
        else ""
    )

    return f"""COMPLIANCE DESIGN NOTE
Record #{record['id']} — generated by OceanGRC
Decision recorded: {record['asked_at']} (UTC)

VESSEL AS ASSESSED
{vessel_line}

QUESTION
{record['question']}

VERDICT
{verdict}{guard_block}

DETERMINATION
{body}

CLAUSES RELIED UPON
{used}

CLAUSES EXCLUDED AS NOT APPLICABLE
{excluded}

REPRODUCIBILITY
  Corpus versions at time of decision:
{fingerprints}
  Engine version: {record['pipeline_version']}
  Generation model: {record.get('model_used') or 'not recorded'}
  Citations machine-verified against retrieved text: {'yes' if record['citations_verified'] else 'NO — verify manually'}

This record states which provisions were considered and which were excluded, on
what stated ground, against the corpus versions listed. It is a record of the
assessment performed. It is not a certificate, and it does not replace the
determination of the MCA or a Certifying Authority.
"""
