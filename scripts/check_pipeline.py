"""Verify pipeline artifact consistency."""

import json
import sys
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"


def main():
    errors = []

    # 1. Artist nodes on disk
    node_ids = sorted(p.stem for p in ARTISTS_DIR.glob("*.json"))

    # 2. Embedding IDs
    emb_ids_path = DATA_DIR / "embedding_ids.json"
    if not emb_ids_path.exists():
        errors.append("Missing embedding_ids.json — run embed.py")
    else:
        with open(emb_ids_path, encoding="utf-8") as f:
            emb_ids = json.load(f)
        if emb_ids != node_ids:
            missing = set(node_ids) - set(emb_ids)
            extra = set(emb_ids) - set(node_ids)
            if missing:
                errors.append(f"Artists on disk but not embedded: {missing}")
            if extra:
                errors.append(f"Embedded but no node file: {extra}")

    # 3. Matrix dimensions
    for name in ["discourse_sim.npy", "tag_prox.npy"]:
        path = DATA_DIR / name
        if not path.exists():
            errors.append(f"Missing {name} — run compute.py")
        else:
            matrix = np.load(path)
            expected = len(node_ids)
            if matrix.shape != (expected, expected):
                errors.append(f"{name} is {matrix.shape}, expected ({expected}, {expected}) — run compute.py")

    # 4. Embeddings shape
    emb_path = DATA_DIR / "embeddings.npy"
    if emb_path.exists():
        emb = np.load(emb_path)
        if emb.shape[0] != len(node_ids):
            errors.append(f"embeddings.npy has {emb.shape[0]} rows, expected {len(node_ids)} — run embed.py")

    if errors:
        print("PIPELINE INCONSISTENCY DETECTED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"Pipeline consistent: {len(node_ids)} artists, all artifacts in sync.")
        sys.exit(0)


if __name__ == "__main__":
    main()
