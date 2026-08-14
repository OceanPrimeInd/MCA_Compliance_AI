"""Evaluation harness for the compliance engine.

Four categories. A, B and C follow Dave's baseline plan; D is new and is the one
that measures the context layer itself.

  A — must answer confidently with a correct clause citation
  B — must refuse, clearly out of scope (tax, immigration, weather)
  C — must refuse for a subtler reason: sounds in scope, not in the ingested Code
  D — must answer DIFFERENTLY for different vessels

Why D can be scored without a maritime lawyer
---------------------------------------------
A and C need someone who knows the Code to state the right clause. D does not.
It asks one question against two vessels that sit on opposite sides of a
statutory threshold and checks mechanical properties of the result:

  1. LEAKAGE (hard failure): did the answer cite a clause that the applicability
     filter had already excluded for that vessel? This must be zero. It is the
     honest version of "hallucination rate" for this system — a real clause,
     correctly quoted, that cannot bind the vessel it was given for.

  2. DISCRIMINATION: did the two vessels actually receive different clause sets?
     If a question about a length-dependent requirement returns identical
     clauses for an 11m and an 18.5m vessel, the layer did nothing.

Both are computed from the engine's own output, so the number is measured rather
than asserted.

Run:
    cd backend && python -m evals.runner
    cd backend && python -m evals.runner --category D --out evals/results
"""

import argparse
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import yaml

from core.corpus import CorpusRegistry
from core.rag.answer import Answerer
from core.vessel import VesselProfile

EVAL_DIR = Path(__file__).resolve().parent
SUITES_DIR = EVAL_DIR / "suites"
DEFAULT_OUT = EVAL_DIR / "results"

CITATION_PATTERN = re.compile(
    r"(?:Clause|Section|Table)[/\s]*(?:Section\s*)?([0-9]+[A-Z]?(?:\.[0-9]+)*)",
    re.IGNORECASE,
)

REFUSAL_MARKERS = (
    "could not find",
    "not covered",
    "no comparable extract",
    "check with the mca",
    "certifying authority directly",
    "not found",
    "outside the scope",
    "does not address",
)


def cited_clauses(answer_text: str) -> set:
    return set(CITATION_PATTERN.findall(answer_text or ""))


def looks_like_refusal(answer_text: str) -> bool:
    lowered = (answer_text or "").lower()
    return any(m in lowered for m in REFUSAL_MARKERS)


def load_suite(category: str | None) -> list:
    cases = []
    for path in sorted(SUITES_DIR.glob("*.yaml")):
        payload = yaml.safe_load(open(path))
        for case in payload.get("cases", []):
            case.setdefault("category", payload.get("category"))
            case["_source"] = path.name
            if category is None or case["category"].upper() == category.upper():
                cases.append(case)
    return cases


def profile_from(spec: dict) -> VesselProfile:
    return VesselProfile(
        vessel_type=spec.get("vessel_type", "workboat"),
        length_overall=float(spec["length_overall"]),
        area_category=int(spec["area_category"]),
        hull_material=spec.get("hull_material", "GRP"),
        passenger_count=int(spec.get("passenger_count", 0)),
    )


def run_abc(answerer: Answerer, case: dict) -> dict:
    """Categories A, B and C — one question, optional vessel."""
    vessel = profile_from(case["vessel"]) if case.get("vessel") else None
    started = time.time()
    result = answerer.ask(case["question"], vessel=vessel)
    elapsed = time.time() - started

    answer = result["answer"]
    cited = cited_clauses(answer)
    refused = looks_like_refusal(answer)
    category = case["category"].upper()

    excluded = {str(f["clause_number"]) for f in result.get("filtered_out", [])}
    leaked = sorted(cited & excluded)

    if category == "A":
        accepted = {str(c) for c in case.get("accepted_citations", [])}
        if accepted:
            passed = bool(cited & accepted) and not refused
            detail = (
                f"cited {sorted(cited) or '—'}, accepted {sorted(accepted)}"
                if not passed
                else f"cited {sorted(cited & accepted)}"
            )
        else:
            # No verified clause list yet — the weakest an A case can be checked
            # at. Records that a confident, cited answer came back, and flags
            # that a domain reviewer still has to confirm the clause is right.
            passed = bool(cited) and not refused
            detail = f"cited {sorted(cited) or '—'} [NEEDS REVIEWER: no accepted_citations set]"
    else:  # B and C must refuse
        passed = refused
        detail = "refused" if refused else f"ANSWERED instead of refusing; cited {sorted(cited)}"

    if leaked:
        passed = False
        detail += f" | LEAKED excluded clauses {leaked}"

    return {
        "id": case["id"],
        "category": category,
        "question": case["question"],
        "passed": passed,
        "detail": detail,
        "leaked": leaked,
        "elapsed": round(elapsed, 2),
        "from_cache": result.get("from_cache"),
        "answer": answer,
    }


def run_d(answerer: Answerer, case: dict) -> dict:
    """Category D — same question, two vessels, must differ and must not leak."""
    va, vb = profile_from(case["vessel_a"]), profile_from(case["vessel_b"])

    started = time.time()
    ra = answerer.ask(case["question"], vessel=va)
    rb = answerer.ask(case["question"], vessel=vb)
    elapsed = time.time() - started

    def clause_set(r):
        return {str(s["clause"]) for s in r["sources"] if s.get("clause")}

    def excluded_set(r):
        return {str(f["clause_number"]) for f in r.get("filtered_out", [])}

    a_clauses, b_clauses = clause_set(ra), clause_set(rb)
    a_excluded, b_excluded = excluded_set(ra), excluded_set(rb)

    leak_a = sorted(cited_clauses(ra["answer"]) & a_excluded)
    leak_b = sorted(cited_clauses(rb["answer"]) & b_excluded)
    leaked = leak_a + leak_b

    discriminated = a_clauses != b_clauses or a_excluded != b_excluded
    passed = discriminated and not leaked

    detail = []
    if not discriminated:
        detail.append("NO DISCRIMINATION — identical clause sets for both vessels")
    else:
        only_a = sorted(a_clauses - b_clauses)
        only_b = sorted(b_clauses - a_clauses)
        detail.append(
            f"A-only {only_a or '—'} | B-only {only_b or '—'} | "
            f"excluded A:{len(a_excluded)} B:{len(b_excluded)}"
        )
    if leaked:
        detail.append(f"LEAKED excluded clauses {leaked}")

    return {
        "id": case["id"],
        "category": "D",
        "question": case["question"],
        "passed": passed,
        "discriminated": discriminated,
        "detail": " | ".join(detail),
        "leaked": leaked,
        "elapsed": round(elapsed, 2),
        "vessel_a": va.describe(),
        "vessel_b": vb.describe(),
        "answer_a": ra["answer"],
        "answer_b": rb["answer"],
    }


def summarise(results: list) -> dict:
    by_cat = {}
    for r in results:
        c = by_cat.setdefault(r["category"], {"total": 0, "passed": 0})
        c["total"] += 1
        c["passed"] += 1 if r["passed"] else 0

    d = [r for r in results if r["category"] == "D"]
    total_leaks = sum(len(r.get("leaked", [])) for r in results)

    return {
        "by_category": by_cat,
        "total": len(results),
        "passed": sum(1 for r in results if r["passed"]),
        "leakage_incidents": total_leaks,
        "leakage_rate": round(
            100 * sum(1 for r in results if r.get("leaked")) / max(len(results), 1), 1
        ),
        "discrimination_rate": round(
            100 * sum(1 for r in d if r.get("discriminated")) / max(len(d), 1), 1
        )
        if d
        else None,
    }


def write_report(results: list, summary: dict, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")

    (out_dir / f"run-{stamp}.json").write_text(
        json.dumps({"summary": summary, "results": results}, indent=2)
    )

    lines = [
        f"# Eval run — {datetime.now(timezone.utc).isoformat(timespec='seconds')}",
        "",
        f"**{summary['passed']}/{summary['total']} passed**",
        "",
        "| Category | Passed | Total | Rate |",
        "|---|---|---|---|",
    ]
    for cat in sorted(summary["by_category"]):
        c = summary["by_category"][cat]
        lines.append(
            f"| {cat} | {c['passed']} | {c['total']} | {round(100 * c['passed'] / c['total'])}% |"
        )

    lines += [
        "",
        "## Context layer metrics",
        "",
        f"- **Excluded-clause leakage: {summary['leakage_rate']}%** "
        f"({summary['leakage_incidents']} incidents) — answers citing a clause the "
        f"applicability filter had already excluded for that vessel. Target: 0%.",
    ]
    if summary["discrimination_rate"] is not None:
        lines.append(
            f"- **Applicability discrimination: {summary['discrimination_rate']}%** — "
            f"Category D questions where two vessels on opposite sides of a statutory "
            f"threshold received materially different clause sets."
        )

    lines += ["", "## Failures", ""]
    failures = [r for r in results if not r["passed"]]
    if not failures:
        lines.append("None.")
    for r in failures:
        lines.append(f"- **{r['id']}** ({r['category']}) — {r['detail']}")
        lines.append(f"  - _{r['question']}_")

    path = out_dir / f"run-{stamp}.md"
    path.write_text("\n".join(lines))
    return path


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--category", default=None, help="A, B, C or D. Omit for all.")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    cases = load_suite(args.category)
    if not cases:
        print(f"No cases found in {SUITES_DIR}")
        return

    print(f"Running {len(cases)} case(s)…\n")
    answerer = Answerer(CorpusRegistry())

    results = []
    for case in cases:
        runner = run_d if case["category"].upper() == "D" else run_abc
        try:
            r = runner(answerer, case)
        except Exception as exc:  # a crash is a failure, not a stopped run
            r = {
                "id": case["id"],
                "category": case["category"].upper(),
                "question": case["question"],
                "passed": False,
                "detail": f"ERROR {type(exc).__name__}: {exc}",
                "leaked": [],
                "elapsed": 0,
            }
        results.append(r)
        print(f"  [{'PASS' if r['passed'] else 'FAIL'}] {r['id']:<10} {r['detail'][:96]}")

    summary = summarise(results)
    report = write_report(results, summary, Path(args.out))

    print(f"\n{summary['passed']}/{summary['total']} passed")
    print(f"Excluded-clause leakage : {summary['leakage_rate']}%")
    if summary["discrimination_rate"] is not None:
        print(f"Applicability discrimination: {summary['discrimination_rate']}%")
    print(f"\nReport → {report}")


if __name__ == "__main__":
    main()
