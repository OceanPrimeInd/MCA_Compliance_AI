import os
import uuid
from datetime import datetime, timezone

import jwt
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from jwt import PyJWKClient
from pydantic import BaseModel, Field

from core import provenance, usage, vessel_store
from core.corpus import CorpusRegistry
from core.rag.answer import Answerer
from core.rag.cache import PIPELINE_VERSION
from core.vessel import VESSEL_TYPES, VesselProfile

app = FastAPI(title="OceanGRC Compliance Engine")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://www.oceangrc.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

registry = CorpusRegistry()
answerer = Answerer(registry)

SUPABASE_URL = os.environ["VITE_SUPABASE_URL"]
JWKS_URL = f"{SUPABASE_URL}/auth/v1/.well-known/jwks.json"
jwks_client = PyJWKClient(JWKS_URL)


def get_current_user_id(authorization: str = Header(...)) -> str:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token, signing_key.key, algorithms=["ES256", "RS256"], audience="authenticated"
        )
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]


class VesselProfileRequest(BaseModel):
    vessel_type: str = Field(..., description=f"One of: {', '.join(VESSEL_TYPES)}")
    length_overall: float = Field(..., gt=0, le=100, description="LOA in metres")
    area_category: int = Field(..., ge=0, le=6)
    hull_material: str
    passenger_count: int = Field(..., ge=0, le=500)


class VesselProfileResponse(BaseModel):
    vessel_type: str
    length_overall: float
    area_category: int
    hull_material: str
    passenger_count: int


class DemoRequest(BaseModel):
    question: str
    vessel_key: str = Field(..., description="Preset key from GET /demo/vessels")


class AskRequest(BaseModel):
    question: str
    code_ids: list[str] | None = Field(
        default=None, description="Restrict to these codes. Omit to search all available."
    )


class CompareRequest(BaseModel):
    question: str
    code_ids: list[str] = Field(..., min_length=2, description="Two or more codes to compare.")


class Source(BaseModel):
    clause: str | None
    page: int | None
    score: float
    text: str
    scope_condition: str | None = None
    content_type: str | None = None
    clause_reliable: bool = True
    code_id: str | None = None
    code_name: str | None = None


class FilteredClause(BaseModel):
    clause_number: str | None
    page_number: int | None
    reason: str
    score: float
    code_id: str | None = None
    code_name: str | None = None


class CompareResponse(BaseModel):
    answer: str
    sources: list[Source]
    filtered_out: list[FilteredClause]
    verified: bool
    from_cache: bool
    vessel: VesselProfileResponse | None
    codes_compared: list[str]
    remaining_this_month: int


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    filtered_out: list[FilteredClause]
    verified: bool
    from_cache: bool
    guardrail_triggered: str | None
    filtering_active: bool
    vessel: VesselProfileResponse | None
    codes_searched: list[str] = []
    matrix_hits: list[dict] = []
    verdict: dict | None = None
    verdict_guard: dict | None = None
    model_used: str | None = None
    record_id: int | None = None
    remaining_this_month: int


@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "oceangrc-compliance-engine"}


@app.put("/vessel", response_model=VesselProfileResponse)
def set_vessel(request: VesselProfileRequest, user_id: str = Depends(get_current_user_id)):
    """Lock in the verified vessel attributes. Captured once, applied to every question."""
    try:
        profile = VesselProfile(
            vessel_type=request.vessel_type,
            length_overall=request.length_overall,
            area_category=request.area_category,
            hull_material=request.hull_material,
            passenger_count=request.passenger_count,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    vessel_store.save_profile(user_id, profile)
    return profile.to_dict()


@app.get("/vessel", response_model=VesselProfileResponse | None)
def get_vessel(user_id: str = Depends(get_current_user_id)):
    profile = vessel_store.get_profile(user_id)
    return profile.to_dict() if profile else None


@app.delete("/vessel")
def clear_vessel(user_id: str = Depends(get_current_user_id)):
    deleted = vessel_store.delete_profile(user_id)
    return {"deleted": deleted}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, user_id: str = Depends(get_current_user_id)):
    allowed, remaining = usage.check_and_increment(user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="You've reached this month's beta usage limit. Thanks for testing — more capacity coming soon.",
        )

    # The user identity now reaches the answer engine. Previously it stopped at
    # the usage counter, which is why every answer was vessel-agnostic.
    vessel = vessel_store.get_profile(user_id)

    try:
        result = answerer.ask(request.question, vessel=vessel, code_ids=request.code_ids)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    # Append to the compliance record. Cached answers are recorded too — the
    # user still relied on the determination, and a gap in the record is
    # indistinguishable from a decision never made.
    result["record_id"] = provenance.record(
        user_id=user_id,
        question=request.question,
        result=result,
        corpus_fingerprints=registry.fingerprints,
        pipeline_version=PIPELINE_VERSION,
    )

    result["remaining_this_month"] = remaining
    return result


# ── Public demo ────────────────────────────────────────────────────────────
#
# Un-gated so a naval architect can forward a link and a partner can try it
# without signing up. Kept safe by construction rather than by auth:
#   - vessels are PRESETS only, never free-form, so this cannot be used as an
#     open compliance API for arbitrary vessels
#   - a shared monthly budget caps total spend regardless of traffic
#   - answers are cached per (preset, question), so repeat traffic on the same
#     demo questions costs nothing

DEMO_VESSELS = {
    "small": VesselProfile(
        vessel_type="workboat",
        length_overall=11.0,
        area_category=2,
        hull_material="GRP",
        passenger_count=8,
    ),
    "large": VesselProfile(
        vessel_type="workboat",
        length_overall=18.5,
        area_category=0,
        hull_material="Aluminium",
        passenger_count=30,
    ),
}

DEMO_LABELS = {"small": "11m · Category 2 · 8 pax", "large": "18.5m · Category 0 · 30 pax"}


@app.get("/demo/vessels")
def demo_vessels():
    return {
        "vessels": [
            {"key": k, "label": DEMO_LABELS[k], **v.to_dict()} for k, v in DEMO_VESSELS.items()
        ],
        "suggested_questions": [
            "What watertight subdivision or collision bulkhead is required?",
            "What bilge pumping arrangements are required?",
            "What navigation lights are required?",
            "How often must the vessel be surveyed?",
        ],
        "remaining_today": usage.demo_remaining(),
    }


@app.post("/demo/ask")
def demo_ask(request: DemoRequest):
    vessel = DEMO_VESSELS.get(request.vessel_key)
    if vessel is None:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown vessel_key. Choose one of: {', '.join(DEMO_VESSELS)}",
        )

    if len(request.question) > 300:
        raise HTTPException(status_code=400, detail="Question too long for the demo (300 chars).")

    allowed, remaining = usage.check_and_increment_demo()
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="The public demo has reached today's shared limit. "
            "Sign up for a free account to keep asking.",
        )

    result = answerer.ask(request.question, vessel=vessel)
    return {
        "answer": result["answer"],
        "sources": result["sources"],
        "filtered_out": result["filtered_out"],
        "verified": result["verified"],
        "from_cache": result["from_cache"],
        "vessel": result["vessel"],
        "vessel_label": DEMO_LABELS[request.vessel_key],
        "codes_searched": result.get("codes_searched", []),
        "verdict": result.get("verdict"),
        "verdict_guard": result.get("verdict_guard"),
        "model_used": result.get("model_used"),
        # Execution provenance. The demo is stateless — nothing is persisted for
        # an anonymous visitor — so this identifies the run and pins the exact
        # corpus and engine that produced it, without implying a stored record.
        # Signed-in determinations DO persist; those carry a record_id instead.
        "execution": {
            "execution_id": uuid.uuid4().hex[:16],
            "executed_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "corpus_fingerprints": registry.fingerprints,
            "pipeline_version": PIPELINE_VERSION,
            "persisted": False,
        },
        "remaining_today": remaining,
    }


@app.get("/codes")
def list_codes():
    """Which regulatory codes this deployment can answer against."""
    return {"codes": registry.catalogue()}


@app.post("/compare", response_model=CompareResponse)
def compare(request: CompareRequest, user_id: str = Depends(get_current_user_id)):
    """One question, several codes, side by side.

    The feature a single-code competitor cannot ship: "this 11m Category 2
    vessel — what changes under Workboat Code Edition 3 rather than SPVC?"
    """
    allowed, remaining = usage.check_and_increment(user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="You've reached this month's beta usage limit. Thanks for testing — more capacity coming soon.",
        )

    vessel = vessel_store.get_profile(user_id)

    try:
        result = answerer.compare(request.question, request.code_ids, vessel=vessel)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    result["remaining_this_month"] = remaining
    return result


# ── Compliance provenance ──────────────────────────────────────────────────


class ImpactRequest(BaseModel):
    code_id: str | None = Field(default=None, description="Restrict to one code.")
    clauses: list[str] = Field(..., min_length=1, description="Clause numbers that changed.")


@app.get("/provenance")
def list_provenance(
    limit: int = 50, offset: int = 0, user_id: str = Depends(get_current_user_id)
):
    """Every determination made for this user, newest first."""
    return {
        "summary": provenance.summary(user_id),
        "records": provenance.list_records(user_id, limit=limit, offset=offset),
    }


@app.get("/provenance/{record_id}")
def get_provenance(record_id: int, user_id: str = Depends(get_current_user_id)):
    record = provenance.get_record(user_id, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No such record for this account.")
    return record


@app.get("/provenance/{record_id}/design-note")
def provenance_design_note(record_id: int, user_id: str = Depends(get_current_user_id)):
    """Dated, attributable text for a design justification file."""
    record = provenance.get_record(user_id, record_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No such record for this account.")
    return {"record_id": record_id, "design_note": provenance.export_design_note(record)}


@app.post("/provenance/impact")
def provenance_impact(request: ImpactRequest, user_id: str = Depends(get_current_user_id)):
    """Which past determinations relied on clauses that have now changed.

    The question a product without a stored record cannot answer at any price:
    an MGN amends clause 8.3.2 — which of my past design decisions are stale?
    """
    affected = provenance.find_affected(user_id, request.code_id, request.clauses)
    return {
        "queried_clauses": request.clauses,
        "code_id": request.code_id,
        "affected_count": len(affected),
        "affected": affected,
    }
