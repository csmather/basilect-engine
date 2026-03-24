"""Compute pairwise discourse similarity and tag proximity matrices."""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

from scripts.tag_similarity import soft_jaccard_matrix

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"


def load_embeddings():
    """Load precomputed embeddings and their ID order."""
    embeddings = np.load(DATA_DIR / "embeddings.npy")
    with open(DATA_DIR / "embedding_ids.json", encoding="utf-8") as f:
        ids = json.load(f)
    return ids, embeddings


def load_tags(ids):
    """Load tag sets for each artist, in embedding ID order."""
    tag_sets = []
    for artist_id in ids:
        path = ARTISTS_DIR / f"{artist_id}.json"
        with open(path, encoding="utf-8") as f:
            node = json.load(f)
        tag_sets.append(set(node["tags"]))
    return tag_sets


def jaccard_matrix(tag_sets):
    """Compute pairwise Jaccard similarity for a list of tag sets."""
    n = len(tag_sets)
    matrix = np.zeros((n, n))
    for i in range(n):
        matrix[i, i] = 1.0
        for j in range(i + 1, n):
            intersection = len(tag_sets[i] & tag_sets[j])
            union = len(tag_sets[i] | tag_sets[j])
            sim = intersection / union if union > 0 else 0.0
            matrix[i, j] = sim
            matrix[j, i] = sim
    return matrix


def main():
    ids, embeddings = load_embeddings()
    print(f"Loaded {len(ids)} embeddings ({embeddings.shape})")

    # Discourse similarity: cosine of embedded profiles
    discourse_sim = cosine_similarity(embeddings)
    np.save(DATA_DIR / "discourse_sim.npy", discourse_sim)
    print(f"Saved discourse similarity matrix: {discourse_sim.shape}")

    # Tag proximity: both hard and soft Jaccard
    tag_sets = load_tags(ids)

    # Hard Jaccard (original)
    tag_prox_hard = jaccard_matrix(tag_sets)
    np.save(DATA_DIR / "tag_prox_hard.npy", tag_prox_hard)
    print(f"Saved hard Jaccard matrix: {tag_prox_hard.shape}")

    # Soft Jaccard (new primary)
    tag_prox = soft_jaccard_matrix(tag_sets)
    np.save(DATA_DIR / "tag_prox.npy", tag_prox)
    print(f"Saved soft Jaccard matrix: {tag_prox.shape}")

    # Quick summary
    n = len(ids)
    num_pairs = n * (n - 1) // 2
    upper = np.triu_indices(n, k=1)
    print(f"\n{num_pairs} unique pairs")
    print(f"Discourse sim  — mean: {discourse_sim[upper].mean():.3f}, "
          f"std: {discourse_sim[upper].std():.3f}")
    print(f"Tag prox (hard)— mean: {tag_prox_hard[upper].mean():.3f}, "
          f"std: {tag_prox_hard[upper].std():.3f}")
    print(f"Tag prox (soft)— mean: {tag_prox[upper].mean():.3f}, "
          f"std: {tag_prox[upper].std():.3f}")


if __name__ == "__main__":
    main()
