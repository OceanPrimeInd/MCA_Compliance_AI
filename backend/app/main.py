from fastapi import FastAPI
from pydantic import BaseModel
from core.rag.answer import Answerer

app = FastAPI(title="MCA Compliance AI")

answerer = Answerer("data/processed/spvc_2025_index.npz")

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

@app.get("/health")
def health_check():
    return {"status": "ok", "service": "mca-compliance-ai-backend"}

@app.post("/ask", response_model=AskResponse)
def ask(request: AskRequest):
    result = answerer.ask(request.question)
    return result