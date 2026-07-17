import json
import numpy as np
from sentence_transformers import SentenceTransformer
from pathlib import Path

def build_index(chunks_path: str, output_path: str):
    chunks = json.load(open(chunks_path))

    # Filter out junk: keep only chunks with real content
    chunks = [c for c in chunks if len(c["text"]) > 20]

    print(f"Embedding {len(chunks)} chunks... this takes a few minutes on CPU.")

    model = SentenceTransformer("all-MiniLM-L6-v2")  # small, fast, runs on CPU, no GPU needed
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, batch_size=32)

    # Save embeddings + the chunks they correspond to, together
    np.savez(
        output_path,
        embeddings=embeddings,
        chunks=json.dumps(chunks),  # store chunks as JSON string alongside the vectors
    )
    print(f"Done. Index saved to {output_path}")

if __name__ == "__main__":
    build_index(
        chunks_path="data/processed/spvc_2025_chunks.json",
        output_path="data/processed/spvc_2025_index.npz",
    )