import os
import jwt
from jwt import PyJWKClient
from fastapi import FastAPI, Header, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.rag.answer import Answerer
from core import usage

app = FastAPI(title="MCA Compliance AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://www.oceangrc.com",
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

answerer = Answerer("data/processed/spvc_2025_index.npz")

SUPABASE_URL = os.environ["SUPABASE_URL"]
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

class AskRequest(BaseModel):
    question: str


class Source(BaseModel):
    clause: str | None
    page: int | None
    score: float
    text: str


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    verified: bool
    from_cache: bool
    guardrail_triggered: str | None
    remaining_this_month: int


@app.get("/")
@app.get("/health")
def health_check():
    return {"status": "ok", "service": "mca-compliance-ai-backend"}


@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest, user_id: str = Depends(get_current_user_id)):
    allowed, remaining = usage.check_and_increment(user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="You've reached this month's beta usage limit. Thanks for testing — more capacity coming soon.",
        )
    result = answerer.ask(request.question)
    result["remaining_this_month"] = remaining
    return result