import os
import re
from pathlib import Path
from dotenv import load_dotenv
from groq import Groq
from core.rag.retrieve import Retriever
from core.rag import cache

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env", override=True)

SYSTEM_PROMPT = """You are a compliance assistant for the UK MCA Sport or Pleasure Vessel Code (SPVC), 2025 edition.

You will be given a question and a set of retrieved clauses from the Code. Follow these rules strictly:

1. Answer ONLY using the retrieved clauses provided below. Do not use any outside knowledge of maritime regulations.
2. Every claim in your answer must cite the exact clause number and page number it came from, in the format (Clause X.X.X, p.XX).
3. If the retrieved clauses do not actually relate to the topic of the question, say clearly: "I could not find a clause in the SPVC that directly addresses this — please check with the MCA or a Certifying Authority directly." Do not guess or invent information beyond what is written. HOWEVER: if the retrieved clauses clearly relate to the topic being asked about — even if the question is phrased differently from the clause text — you must use them to answer. Do not refuse just because the wording doesn't match exactly.
4. If multiple clauses are relevant, cite each one separately rather than blending them into an unattributed summary.
5. Keep answers concise and practical — surveyors and operators need the citation more than lengthy explanation.
"""

LOW_CONFIDENCE_THRESHOLD = 0.45
CACHE_SIMILARITY_THRESHOLD = 0.92
CLAUSE_CITATION_PATTERN = re.compile(r'Clause\s+([0-9]+[A-Z]?(?:\.[0-9]+)*)', re.IGNORECASE)

class Answerer:
    def __init__(self, index_path: str, model: str = "llama-3.3-70b-versatile"):
        self.retriever = Retriever(index_path)
        self.client = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = model

    def _verify_citations(self, answer_text: str, sources: list) -> bool:
        cited = set(CLAUSE_CITATION_PATTERN.findall(answer_text))
        retrieved = {s["clause"] for s in sources if s.get("clause")}
        return cited.issubset(retrieved) if cited else True

    def ask(self, question: str, top_k: int = 5):
        query_embedding = self.retriever.model.encode([question])[0]

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

        response = self.client.chat.completions.create(
            model=self.model,
            max_tokens=1000,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Retrieved clauses:\n\n{context}\n\nQuestion: {question}"},
            ],
        )
        answer_text = response.choices[0].message.content

        verified = self._verify_citations(answer_text, sources)
        cache.store(question, query_embedding, answer_text, sources, verified=verified)

        return {
            "answer": answer_text,
            "sources": sources,
            "verified": verified,
            "from_cache": False,
            "guardrail_triggered": None if verified else "unverified_citation",
        }


if __name__ == "__main__":
    answerer = Answerer("data/processed/spvc_2025_index.npz")
    test_question = "Do I need a kill cord on my rigid inflatable boat?"
    result = answerer.ask(test_question)
    print(result)