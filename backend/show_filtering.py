"""Show the context layer working, with no LLM call at all.

This is the fastest way to test the core claim and the best thing to put in
front of a technical reviewer. It uses only Cohere embeddings and the
deterministic applicability filter — no generation, so it costs nothing against
the Gemini quota and the result is identical every time you run it.

Usage:
    cd backend
    ../venv/bin/python show_filtering.py
    ../venv/bin/python show_filtering.py "how many liferafts are required?"
    ../venv/bin/python show_filtering.py "what bilge pumping is required?" --length 13 --category 4
"""

import argparse

from core.corpus import CorpusRegistry
from core.vessel import VesselProfile

DEFAULT_QUESTION = "What watertight subdivision or collision bulkhead is required?"


def show(registry, question, label, vessel, top_k):
    outcome = registry.search(question, top_k=top_k, vessel=vessel)

    print(f"\n{'=' * 74}")
    print(f"{label}  —  {vessel.describe()}")
    print("=" * 74)

    print(f"\n  KEPT — these can bind this vessel ({len(outcome['results'])})")
    for r in outcome["results"]:
        code = (r.get("code_name") or "").replace("MCA ", "")[:22]
        print(f"    {r['clause_number']:<12} p.{r['page_number']:<5} {code:<24} {r['scope_condition'][:44]}")

    print(f"\n  DROPPED — these cannot bind this vessel ({len(outcome['filtered_out'])})")
    if not outcome["filtered_out"]:
        print("    (none — no retrieved clause conflicted with this vessel)")
    for f in outcome["filtered_out"]:
        print(f"    {f['clause_number']:<12} p.{f['page_number']:<5} {f['reason'][:62]}")

    return {r["clause_number"] for r in outcome["results"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("question", nargs="?", default=DEFAULT_QUESTION)
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--length", type=float, default=None, help="override vessel A length")
    ap.add_argument("--category", type=int, default=None, help="override vessel A category")
    args = ap.parse_args()

    small = VesselProfile(
        "workboat",
        args.length if args.length is not None else 11.0,
        args.category if args.category is not None else 2,
        "GRP",
        8,
    )
    large = VesselProfile("workboat", 18.5, 0, "Aluminium", 30)

    registry = CorpusRegistry()
    print(f'\nQUESTION:  "{args.question}"')

    a = show(registry, args.question, "VESSEL A", small, args.top_k)
    b = show(registry, args.question, "VESSEL B", large, args.top_k)

    print(f"\n{'=' * 74}")
    print("VERDICT")
    print("=" * 74)
    if a == b:
        print("  Identical clause sets — the filter did NOT discriminate here.")
        print("  Expected when neither vessel conflicts with any retrieved clause:")
        print("  most clauses in these codes apply to every vessel in scope.")
    else:
        print(f"  Only vessel A:  {sorted(a - b) or '—'}")
        print(f"  Only vessel B:  {sorted(b - a) or '—'}")
        print("\n  Same question. Same corpus. Different binding clauses.")
        print("  That difference is the product.")
    print()


if __name__ == "__main__":
    main()
