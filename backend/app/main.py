import os
import jwt
from fastapi import FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from core.rag.answer import Answerer
from core import usage

app = FastAPI(title="Compliance AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "https://www.oceangrc.com"
    ],
    allow_methods=["*"],
    allow_headers=["*"],
)

answerer = Answerer("data/processed/spvc_2025_index.npz")

SUPABASE_JWT_SECRET = os.environ["SUPABASE_JWT_SECRET"]

def get_current_user_id(authorization: str = Header(...)) -> str:
    """Verifies the Supabase-issued JWT sent by the frontend and returns the user's id."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ")
    try:
        payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    return payload["sub"]  # this is the Supabase user id

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
def ask(request: AskRequest, user_id: str = get_current_user_id):
    allowed, remaining = usage.check_and_increment(user_id)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="You've reached this month's beta usage limit. Thanks for testing — more capacity coming soon.",
        )
    result = answerer.ask(request.question)
    result["remaining_this_month"] = remaining
    return result