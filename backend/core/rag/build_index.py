import json
import os
import numpy as np
import requests
import time

def build_index(chunks_path: str, output_path: str):
    chunks = json.load(open(chunks_path))

    # Filter out junk: keep only chunks with real content
    chunks = [c for c in chunks if len(c["text"]) > 20]

    print(f"Embedding {len(chunks)} chunks via Cohere Free API v2...")

    api_url = "https://api.cohere.com/v2/embed"
    headers = {
        "Authorization": f"Bearer {os.environ['COHERE_API_KEY']}",
        "Content-Type": "application/json"
    }

    texts = [c["text"] for c in chunks]
    embeddings = []
    
    # Process smaller batches to respect free trial tier limits
    batch_size = 50
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i + batch_size]
        
        response = requests.post(
            api_url,
            headers=headers,
            json={
                "model": "embed-english-v3.0",
                "texts": batch,
                "input_type": "search_document",
                "embedding_types": ["float"]
            }
        )
        
        # Check HTTP status directly before trying to decode JSON
        if response.status_code != 200:
            print(f"\n--- API Error Occurred (Status Code {response.status_code}) ---")
            print(f"Raw Response: {response.text}")
            print("----------------------------------------------------\n")
            raise RuntimeError(f"Cohere API Error {response.status_code} - See details above.")
            
        data = response.json()
        embeddings.extend(data["embeddings"]["float"])
        print(f"Successfully vectorized {len(embeddings)}/{len(texts)} entries...")
        
        # Short pause to prevent hit rate limits on Free Trial accounts
        time.sleep(1.0)

    # Save embeddings + the chunks they correspond to, together
    np.savez(
        output_path,
        embeddings=np.array(embeddings),
        chunks=json.dumps(chunks),
    )
    print(f"Done. Index successfully updated at {output_path}")

if __name__ == "__main__":
    build_index(
        chunks_path="data/processed/spvc_2025_chunks.json",
        output_path="data/processed/spvc_2025_index.npz",
    )
