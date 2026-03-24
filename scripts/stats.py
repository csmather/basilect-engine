"""Orthogonality test and distribution stats for the engine."""

import json
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"


def load_data():
    """Load artist IDs and both similarity matrices."""
    with open(DATA_DIR / "embedding_ids.json", encoding="utf-8") as f:
        ids = json.load(f)
    discourse_sim = np.load(DATA_DIR / "discourse_sim.npy")
    tag_prox = np.load(DATA_DIR / "tag_prox.npy")
    return ids, discourse_sim, tag_prox


def node_stats(ids):
    """Compute basic node statistics."""
    tag_counts = []
    confidence_dist = {"high": 0, "medium": 0, "low": 0}
    for artist_id in ids:
        path = ARTISTS_DIR / f"{artist_id}.json"
        with open(path, encoding="utf-8") as f:
            node = json.load(f)
        tag_counts.append(len(node["tags"]))
        conf = node.get("confidence", "unknown")
        confidence_dist[conf] = confidence_dist.get(conf, 0) + 1
    return tag_counts, confidence_dist


def main():
    ids, discourse_sim, tag_prox = load_data()
    n = len(ids)
    upper = np.triu_indices(n, k=1)
    d_scores = discourse_sim[upper]
    t_scores = tag_prox[upper]
    num_pairs = len(d_scores)

    # Node stats
    tag_counts, confidence_dist = node_stats(ids)
    print("NODE STATS")
    print(f"  Artists: {n}")
    print(f"  Avg tags/node: {np.mean(tag_counts):.1f} "
          f"(min {min(tag_counts)}, max {max(tag_counts)})")
    print(f"  Confidence: {confidence_dist}")

    # Distribution stats
    print(f"\nDISTRIBUTION STATS ({num_pairs} pairs)")
    print(f"  Discourse similarity (Φ_sim):")
    print(f"    mean={d_scores.mean():.3f}  std={d_scores.std():.3f}  "
          f"min={d_scores.min():.3f}  max={d_scores.max():.3f}")
    print(f"    quartiles: {np.percentile(d_scores, [25, 50, 75])}")
    print(f"  Tag proximity (P_prox):")
    print(f"    mean={t_scores.mean():.3f}  std={t_scores.std():.3f}  "
          f"min={t_scores.min():.3f}  max={t_scores.max():.3f}")
    print(f"    quartiles: {np.percentile(t_scores, [25, 50, 75])}")

    # Orthogonality test
    pearson_r, pearson_p = sp_stats.pearsonr(d_scores, t_scores)
    spearman_r, spearman_p = sp_stats.spearmanr(d_scores, t_scores)
    print(f"\nORTHOGONALITY TEST")
    print(f"  Pearson:  r={pearson_r:.3f}  (p={pearson_p:.4f})")
    print(f"  Spearman: r={spearman_r:.3f}  (p={spearman_p:.4f})")
    if abs(pearson_r) < 0.3:
        print(f"  → The two layers are measuring substantially different things.")
    elif abs(pearson_r) < 0.6:
        print(f"  → Moderate correlation — some overlap, but the layers carry "
              f"independent signal.")
    else:
        print(f"  → High correlation — discourse profiles may be restating genre "
              f"info in prose.")


if __name__ == "__main__":
    main()
