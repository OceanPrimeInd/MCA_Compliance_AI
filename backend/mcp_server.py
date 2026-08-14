"""Maritime Compliance Context Protocol — MCP server.

This is the surface the pitch describes: any agent, surveyor tool or insurance
engine can query UK maritime statute through a protocol, with physical vessel
state enforced at the data layer before an LLM ever sees a clause.

It deliberately exposes the LAYER, not just the chatbot. `resolve_applicability`
returns structured scope decisions with no model call at all — a consuming agent
can use its own LLM and still get deterministic, auditable filtering. That is
what makes this infrastructure rather than a hosted assistant.

Transport is stdio, so it drops into Claude Desktop, Cursor, or any MCP client:

    {
      "mcpServers": {
        "oceangrc": {
          "command": "/absolute/path/to/venv/bin/python",
          "args": ["-m", "mcp_server"],
          "cwd": "/absolute/path/to/backend"
        }
      }
    }

Requires:  pip install "mcp[cli]"
Run:       cd backend && python -m mcp_server
"""

import json

from core.corpus import CorpusRegistry
from core.matrix import MatrixRegistry
from core.rag.answer import Answerer
from core.vessel import Applicability, VesselProfile

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover
    raise SystemExit(
        'The MCP SDK is not installed. Run:  pip install "mcp[cli]"\n'
        "It is intentionally not a hard dependency of the API server — the REST "
        "app runs without it."
    )

mcp = FastMCP("oceangrc")

_registry = CorpusRegistry()
_matrices = MatrixRegistry()
_answerer = Answerer(_registry, matrices=_matrices)


def _vessel(
    length_overall: float,
    area_category: int,
    vessel_type: str = "workboat",
    hull_material: str = "GRP",
    passenger_count: int = 0,
) -> VesselProfile:
    return VesselProfile(
        vessel_type=vessel_type,
        length_overall=length_overall,
        area_category=area_category,
        hull_material=hull_material,
        passenger_count=passenger_count,
    )


@mcp.tool()
def list_codes() -> str:
    """List the UK MCA regulatory codes this server can answer against."""
    return json.dumps(_registry.catalogue(), indent=2)


@mcp.tool()
def resolve_applicability(
    length_overall: float,
    area_category: int,
    question: str,
    vessel_type: str = "workboat",
    hull_material: str = "GRP",
    passenger_count: int = 0,
    top_k: int = 8,
) -> str:
    """Return the clauses that CAN bind this vessel, and those that cannot — no LLM.

    This is the context layer on its own. Use it when you want to run your own
    model over the clause text but still need scope enforced deterministically.
    Every exclusion carries the reason it was made, so the decision is auditable.

    Args:
        length_overall: Length overall in metres.
        area_category: Area category of operation, 0 (unlimited) to 6 (smooth waters).
        question: What you are looking for — used for retrieval only.
        vessel_type: workboat, pilot boat, commercial rib, sport or pleasure.
        hull_material: GRP, Aluminium, Steel, Timber, Composite.
        passenger_count: Number of passengers carried.
        top_k: Maximum in-scope clauses to return.
    """
    vessel = _vessel(
        length_overall, area_category, vessel_type, hull_material, passenger_count
    )
    outcome = _registry.search(question, top_k=top_k, vessel=vessel)

    return json.dumps(
        {
            "vessel": vessel.to_dict(),
            "codes_searched": outcome["codes_searched"],
            "filtering_active": outcome["filtering_active"],
            "binding_clauses": [
                {
                    "code": r.get("code_name"),
                    "clause": r["clause_number"],
                    "page": r["page_number"],
                    "section": r.get("section_title"),
                    "scope_condition": r["scope_condition"],
                    "scope_evidence": r.get("scope_evidence", []),
                    "relevance": round(r["score"], 4),
                    "text": r["text"],
                }
                for r in outcome["results"]
            ],
            "excluded_clauses": [
                {
                    "code": f.get("code_name"),
                    "clause": f["clause_number"],
                    "page": f["page_number"],
                    "excluded_because": f["reason"],
                }
                for f in outcome["filtered_out"]
            ],
        },
        indent=2,
    )


@mcp.tool()
def check_clause_applies(
    clause_scope_length_min: float | None = None,
    clause_scope_length_max: float | None = None,
    clause_scope_categories: list[int] | None = None,
    length_overall: float = 0,
    area_category: int = 0,
    passenger_count: int = 0,
) -> str:
    """Test a scope condition against a vessel state. Pure predicate, no retrieval.

    For consumers that hold their own regulatory data and want only the
    applicability decision.
    """
    applicability = Applicability(
        length_min=clause_scope_length_min,
        length_max=clause_scope_length_max,
        categories=frozenset(clause_scope_categories)
        if clause_scope_categories is not None
        else None,
    )
    vessel = _vessel(length_overall, area_category, passenger_count=passenger_count)
    conflict = applicability.conflicts_with(vessel)

    return json.dumps(
        {
            "applies": conflict is None,
            "reason": conflict or "no scope conflict — the clause can bind this vessel",
            "scope": applicability.describe_scope(),
        },
        indent=2,
    )


@mcp.tool()
def ask_compliance(
    question: str,
    length_overall: float,
    area_category: int,
    vessel_type: str = "workboat",
    hull_material: str = "GRP",
    passenger_count: int = 0,
    code_ids: list[str] | None = None,
) -> str:
    """Full answer for a vessel: verdict, statutory anchor, verbatim extract.

    Out-of-scope clauses are removed before generation, so the answer cannot cite
    a requirement that does not bind this vessel.
    """
    vessel = _vessel(
        length_overall, area_category, vessel_type, hull_material, passenger_count
    )
    result = _answerer.ask(question, vessel=vessel, code_ids=code_ids)

    return json.dumps(
        {
            "answer": result["answer"],
            "citations_verified": result["verified"],
            "codes_searched": result.get("codes_searched", []),
            "clauses_excluded": len(result.get("filtered_out", [])),
            "matrix_lookups": result.get("matrix_hits", []),
        },
        indent=2,
    )


@mcp.tool()
def compare_codes(
    question: str,
    code_ids: list[str],
    length_overall: float,
    area_category: int,
    vessel_type: str = "workboat",
    hull_material: str = "GRP",
    passenger_count: int = 0,
) -> str:
    """What differs between two codes for one vessel.

    e.g. code_ids ["spvc_2025", "wbc3"] — the question a single-code tool cannot
    answer, because it needs both corpora retrieved separately and compared.
    """
    vessel = _vessel(
        length_overall, area_category, vessel_type, hull_material, passenger_count
    )
    result = _answerer.compare(question, code_ids, vessel=vessel)

    return json.dumps(
        {
            "answer": result["answer"],
            "codes_compared": result["codes_compared"],
            "citations_verified": result["verified"],
        },
        indent=2,
    )


if __name__ == "__main__":
    mcp.run()
