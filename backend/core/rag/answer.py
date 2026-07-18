import os
import re
import json
from pathlib import Path
from dotenv import load_dotenv
import requests
from core.rag.retrieve import Retriever
from core.rag import cache

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

SYSTEM_PROMPT = """You are a compliance assistant for the UK MCA Sport or Pleasure Vessel Code (SPVC), 2025 edition.

You will be given a question and a set of retrieved clauses from the Code. Follow these rules strictly:

1. Answer ONLY using the retrieved clauses provided below. Do not use any outside knowledge of maritime regulations.
2. Every claim in your answer must cite the exact clause number and page number it came from, in the format (Clause X.X.X, p.XX).
3. If the retrieved clauses do not actually relate to the topic of the question, say clearly: "I could not find a clause in the SPVC that directly addresses this — please check with the MCA or a Certifying Authority directly." Do not guess or invent information beyond what is written.
4. If multiple clauses are relevant, cite each one separately rather than blending them into an unattributed summary.
5. Keep answers concise and practical — surveyors and operators need the citation more than lengthy explanation.
"""

LOW_CONFIDENCE_THRESHOLD = 0.45
CACHE_SIMILARITY_THRESHOLD = 0.92
CLAUSE_CITATION_PATTERN = re.compile(r'Clause\s+([0-9]+[A-Z]?(?:\.[0-9]+)*)', re.IGNORECASE)

class Answerer:
    # command-r-08-2024 is Cohere's production text generation model
    def __init__(self, index_path: str, model: str = "command-r-08-2024"):
        self.retriever = Retriever(index_path)
        self.model = model   # <-- add this line

        # Pull your single key from environment variables
        self.api_key = os.getenv("COHERE_API_KEY")
        if not self.api_key:
            raise ValueError("CRITICAL ERROR: 'COHERE_API_KEY' environment variable is missing on Render!")

        self.api_url = "https://api.cohere.com/v2/chat"

    def _verify_citations(self, answer_text: str, sources: list) -> bool:
        cited = set(CLAUSE_CITATION_PATTERN.findall(answer_text))
        retrieved = {s["clause"] for s in sources if s.get("clause")}
        return cited.issubset(retrieved) if cited else True

    def ask(self, question: str, top_k: int = 5):
        query_embedding = self.retriever._embed_query(question)

        cached = cache.find_similar(query_embedding, threshold=CACHE_SIMILARITY_THRESHOLD)
        if cached:
            return {
                "answer": cached["answer"],
                "sources": cached["sources"],
                "verified": cached["verified"],
                "from_cache": True,
                "guardrail_triggered": None,
            }

        results = self.retriever.search(question, top_k=top_k)
        sources = [
            {"clause": r["clause_number"], "page": r["page_number"], "score": r["score"], "text": r["text"]}
            for r in results
        ]
        top_score = results[0]["score"] if results else 0

        if top_score < LOW_CONFIDENCE_THRESHOLD:
            answer = "I could not find a clause in the SPVC that directly addresses this — please check with the MCA or a Certifying Authority directly."
            cache.store(question, query_embedding, answer, sources, verified=True)
            return {
                "answer": answer,
                "sources": sources,
                "verified": True,
                "from_cache": False,
                "guardrail_triggered": "low_retrieval_confidence",
            }

        context = "\n\n".join([
            f"[Clause {r['clause_number']}, Page {r['page_number']}]\n{r['text']}"
            for r in results
        ])

        # Call Cohere v2 Chat API natively via HTTP
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        response = requests.post(
            self.api_url,
            headers=headers,
            json={
                "model": self.model,
                "messages": [
                    {"role": "user", "content": f"{SYSTEM_PROMPT}\n\nRetrieved clauses:\n\n{context}\n\nQuestion: {question}"}
                ]
            }
        )

        if response.status_code != 200:
            raise RuntimeError(f"Cohere Chat API Error {response.status_code}: {response.text}")

        response_data = response.json()
        
        # Correctly parses text chunks out of the Cohere v2 block format structure
        answer_text = ""
        for content_block in response_data["message"]["content"]:
            if content_block["type"] == "text":
                answer_text += content_block["text"]

        verified = self._verify_citations(answer_text, sources)
        cache.store(question, query_embedding, answer_text, sources, verified=verified)

        return {
            "answer": answer_text,
            "sources": sources,
            "verified": verified,
            "from_cache": False,
            "guardrail_triggered": None,
        }
