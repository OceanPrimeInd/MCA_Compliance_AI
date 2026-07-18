import json
import os
import numpy as np
import requests

class Retriever:
    def __init__(self, index_path: str):
        data = np.load(index_path, allow_pickle=True)
        self.embeddings = data["embeddings"]
        self.chunks = json.loads(str(data["chunks"]))
        
        # Target the modern Cohere v2 endpoint
        self.api_url = "https://api.cohere.com/v2/embed"
        self.headers = {
            "Authorization": f"Bearer {os.environ['COHERE_API_KEY']}",
            "Content-Type": "application/json"
        }

    def _embed_query(self, text: str) -> np.ndarray:
        response = requests.post(
            self.api_url, 
            headers=self.headers, 
            json={
                "model": "embed-english-v3.0",
                "texts": [text],
                "input_type": "search_query",
                "embedding_types": ["float"]
            }
        )
        
        if response.status_code != 200:
            raise RuntimeError(f"Cohere API Error {response.status_code}: {response.text}")
            
        result = response.json()
        return np.array(result["embeddings"]["float"]).flatten()

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
