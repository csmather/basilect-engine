"""Embed artist discourse chunks using sentence-transformers.

Each artist's discourse_chunks are embedded individually, then aggregated
into a single artist-level vector via component-wise median.
"""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"
MODEL_NAME = "all-MiniLM-L6-v2"


def load_chunks():
    """Load artist IDs and discourse chunks from JSON files."""
    ids = []
    chunks_per_artist = []
    for path in sorted(ARTISTS_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            node = json.load(f)
        ids.append(node["id"])
        chunks_per_artist.append(node["discourse_chunks"])
    return ids, chunks_per_artist


def main():
    ids, chunks_per_artist = load_chunks()
    total_chunks = sum(len(c) for c in chunks_per_artist)
    print(f"Loaded {len(ids)} artists, {total_chunks} total chunks")

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    # Flatten all chunks for batch encoding
    all_chunks = []
    artist_boundaries = []  # (start, end) indices into all_chunks
    offset = 0
    for chunks in chunks_per_artist:
        all_chunks.extend(chunks)
        artist_boundaries.append((offset, offset + len(chunks)))
        offset += len(chunks)

    print("Encoding chunks...")
    all_embeddings = model.encode(all_chunks, show_progress_bar=True)

    # Aggregate per artist: median of chunk embeddings
    artist_embeddings = []
    for i, (start, end) in enumerate(artist_boundaries):
        chunk_vecs = all_embeddings[start:end]
        median_vec = np.median(chunk_vecs, axis=0)
        artist_embeddings.append(median_vec)
        print(f"  {ids[i]}: {end - start} chunks -> median vector")

    embeddings = np.array(artist_embeddings)

    np.save(DATA_DIR / "embeddings.npy", embeddings)
    with open(DATA_DIR / "embedding_ids.json", "w", encoding="utf-8") as f:
        json.dump(ids, f, indent=2)

    print(f"\nSaved embeddings: {embeddings.shape} to data/embeddings.npy")
    print(f"Saved artist order: {len(ids)} IDs to data/embedding_ids.json")


if __name__ == "__main__":
    main()
