import json
import os
import numpy as np
from huggingface_hub import InferenceClient

class Retriever:
    def __init__(self, index_path: str):
        data = np.load(index_path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.chunks = json.loads(str(data["chunks"]))
        # REMOVED provider="hf-inference"
        self.client = InferenceClient(api_key=os.environ["HF_TOKEN"])

    def _embed_query(self, text: str) -> np.ndarray:
        # CHANGED to a reliably supported serverless embedding model
        result = self.client.feature_extraction(text, model="BAAI/bge-small-en-v1.5")
        return np.array(result).flatten()

    def search(self, query: str, top_k: int = 5):
        query_embedding = self._embed_query(query)
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
