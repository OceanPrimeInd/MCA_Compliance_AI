import json
import time
from pathlib import Path

import numpy as np
import requests

from core.env import require
from core.vessel import Applicability, VesselProfile


class Retriever:
    """Vessel-aware retrieval.

    Retrieval happens in two passes. First a wide semantic sweep, then the
    applicability filter, then top-k. Filtering AFTER scoring but BEFORE
    truncation is what makes the context layer real: a clause that cannot bind
    the vessel never occupies one of the k slots handed to the model, so the
    model is never in a position to cite it.
    """

    # Widened from the original 4x. Once out-of-scope clauses are dropped, a
    # narrow pool can be exhausted before top_k applicable results are found.
    CANDIDATE_MULTIPLIER = 12

    def __init__(self, index_path: str, applicability_path: str | None = None):
        data = np.load(index_path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.chunks = json.loads(str(data["chunks"]))

        self.applicability = self._load_applicability(index_path, applicability_path)

        self.api_url = "https://api.cohere.com/v2/embed"
        self.headers = {
            "Authorization": f"Bearer {require('COHERE_API_KEY')}",
            "Content-Type": "application/json",
        }

    def _load_applicability(self, index_path: str, applicability_path: str | None):
        """Sidecar records aligned by position with self.chunks.

        Absent or misaligned sidecar degrades to unfiltered retrieval rather
        than failing. Silently filtering on stale metadata would be far worse
        than not filtering at all.
        """
        if applicability_path is None:
            applicability_path = str(index_path).replace("_index.npz", "_applicability.json")

        path = Path(applicability_path)
        if not path.exists():
            print(f"[retriever] No applicability sidecar at {path} — filtering disabled.")
            return None

        payload = json.load(open(path))
        records = payload["records"]

        if len(records) != len(self.chunks):
            print(
                f"[retriever] Sidecar length {len(records)} != index length "
                f"{len(self.chunks)} — filtering disabled. Re-run "
                f"core.ingestion.extract_conditions against the chunk file used "
                f"to build this index."
            )
            return None

        return [
            {
                "excluded": r["excluded"],
                "exclude_reason": r["exclude_reason"],
                # False where the chunker's clause number is page furniture
                # (mostly the Definitions section). The chunk is still served —
                # the answer layer cites it by page and section instead.
                "clause_reliable": r.get("clause_reliable", True),
                "applicability": Applicability.from_dict(r["applicability"]),
            }
            for r in records
        ]

    # The Cohere trial tier rate-limits aggressively. A burst — an eval run, or
    # several users at once — hits 429 and would otherwise surface as a failed
    # answer rather than a slow one.
    MAX_RETRIES = 5
    BACKOFF_BASE_SECONDS = 2.0

    def _embed_query(self, text: str) -> np.ndarray:
        last_error = None

        for attempt in range(self.MAX_RETRIES):
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json={
                    "model": "embed-english-v3.0",
                    "texts": [text],
                    "input_type": "search_query",
                    "embedding_types": ["float"],
                },
                timeout=30,
            )

            if response.status_code == 200:
                result = response.json()
                return np.array(result["embeddings"]["float"]).flatten()

            # 429 (rate limit) and 5xx are transient; anything else is a real
            # error and retrying only wastes trial quota.
            if response.status_code != 429 and response.status_code < 500:
                raise RuntimeError(
                    f"Cohere API Error {response.status_code}: {response.text}"
                )

            last_error = f"{response.status_code}: {response.text[:200]}"
            if attempt < self.MAX_RETRIES - 1:
                time.sleep(self.BACKOFF_BASE_SECONDS * (2**attempt))

        raise RuntimeError(
            f"Cohere API still failing after {self.MAX_RETRIES} attempts — {last_error}"
        )

    def search(self, query: str, top_k: int = 5, vessel: VesselProfile | None = None):
        """Return up to top_k clauses that can bind `vessel`.

        Also returns what was filtered out and why, so the answer layer can be
        transparent about it rather than silently narrowing the corpus.
        """
        query_embedding = self._embed_query(query)

        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        if np.isclose(norms, 0).any():
            return {"results": [], "filtered_out": [], "filtering_active": False}

        similarities = (self.embeddings @ query_embedding) / norms

        pool_size = min(top_k * self.CANDIDATE_MULTIPLIER, len(similarities))
        candidate_indices = np.argsort(similarities)[::-1][:pool_size]

        filtering_active = self.applicability is not None

        seen_clauses = set()
        results = []
        filtered_out = []

        for idx in candidate_indices:
            chunk = self.chunks[idx]
            clause = chunk.get("clause_number")

            if clause in seen_clauses:
                continue

            meta = self.applicability[idx] if filtering_active else None

            # Corpus hygiene: ToC debris and unresolvable clause numbers are
            # dropped for every vessel, with no explanation surfaced — they are
            # parser artefacts, not statutory content.
            if meta and meta["excluded"]:
                continue

            app = meta["applicability"] if meta else Applicability()
            conflict = app.conflicts_with(vessel) if (meta and vessel) else None

            if conflict:
                filtered_out.append(
                    {
                        "clause_number": clause,
                        "page_number": chunk.get("page_number"),
                        "reason": conflict,
                        "score": float(similarities[idx]),
                    }
                )
                seen_clauses.add(clause)
                continue

            seen_clauses.add(clause)
            results.append(
                {
                    "score": float(similarities[idx]),
                    "clause_number": clause,
                    "section_title": chunk.get("section_title"),
                    "page_number": chunk.get("page_number"),
                    "text": chunk["text"],
                    "content_type": chunk.get("content_type", "narrative"),
                    "clause_reliable": meta["clause_reliable"] if meta else True,
                    "scope_condition": app.describe_scope(),
                    "scope_evidence": list(app.evidence),
                }
            )

            if len(results) >= top_k:
                break

        return {
            "results": results,
            "filtered_out": filtered_out,
            "filtering_active": filtering_active and vessel is not None,
        }
