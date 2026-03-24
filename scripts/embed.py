"""Embed all artist discourse profiles using sentence-transformers."""

import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"
MODEL_NAME = "all-MiniLM-L6-v2"


def load_profiles():
    """Load artist IDs and discourse profiles from JSON files."""
    ids = []
    profiles = []
    for path in sorted(ARTISTS_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            node = json.load(f)
        ids.append(node["id"])
        profiles.append(node["discourse_profile"])
    return ids, profiles


def main():
    ids, profiles = load_profiles()
    print(f"Loaded {len(ids)} artist profiles")

    print(f"Loading model: {MODEL_NAME}")
    model = SentenceTransformer(MODEL_NAME)

    print("Encoding profiles...")
    embeddings = model.encode(profiles, show_progress_bar=True)

    np.save(DATA_DIR / "embeddings.npy", embeddings)
    with open(DATA_DIR / "embedding_ids.json", "w", encoding="utf-8") as f:
        json.dump(ids, f, indent=2)

    print(f"Saved embeddings: {embeddings.shape} to data/embeddings.npy")
    print(f"Saved artist order: {len(ids)} IDs to data/embedding_ids.json")


if __name__ == "__main__":
    main()
