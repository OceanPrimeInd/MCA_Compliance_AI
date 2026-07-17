import json
import numpy as np
from sentence_transformers import SentenceTransformer

class Retriever:
    def __init__(self, index_path: str):
        data = np.load(index_path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.chunks = json.loads(str(data["chunks"]))
        self.model = SentenceTransformer("all-MiniLM-L6-v2")

    def search(self, query: str, top_k: int = 5):
        query_embedding = self.model.encode([query])[0]
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        similarities = (self.embeddings @ query_embedding) / norms

        pool_size = min(top_k * 4, len(similarities))
        candidate_indices = np.argsort(similarities)[::-1][:pool_size]

        seen_clauses = set()
        results = []
        for idx in candidate_indices:
            chunk = self.chunks[idx]
            clause = chunk.get("clause_number")
            if clause in seen_clauses:
                continue
            seen_clauses.add(clause)
            results.append({
                "score": float(similarities[idx]),
                "clause_number": clause,
                "page_number": chunk.get("page_number"),
                "text": chunk["text"],
            })
            if len(results) >= top_k:
                break
        return results