import json
import os
import numpy as np
from huggingface_hub import InferenceClient

class Retriever:
    def __init__(self, index_path: str):
        data = np.load(index_path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.chunks = json.loads(str(data["chunks"]))
        self.client = InferenceClient(api_key=os.environ["HF_TOKEN"])

    def _embed_query(self, text: str) -> np.ndarray:
        # Uses the generic post method to directly hit the model feature extraction API
        # This completely bypasses version restrictions and router provider overrides
        response = self.client.post(
            json={"inputs": [text]},
            model="sentence-transformers/all-MiniLM-L6-v2"
        )
        # Parse the JSON byte array returned by the API
        result = json.loads(response.decode("utf-8"))
        
        # Hugging Face returns a nested list [[0.1, 0.2, ...]] for batching
        return np.array(result[0]).flatten()

    def search(self, query: str, top_k: int = 5):
        query_embedding = self._embed_query(query)
        norms = np.linalg.norm(self.embeddings, axis=1) * np.linalg.norm(query_embedding)
        
        if np.isclose(norms, 0).any():
            return []
            
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
