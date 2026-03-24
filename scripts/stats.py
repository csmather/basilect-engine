"""Orthogonality test and distribution stats for the engine."""

import json
from pathlib import Path

import numpy as np
from scipy import stats as sp_stats

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"


def load_data():
    """Load artist IDs and all similarity matrices."""
    with open(DATA_DIR / "embedding_ids.json", encoding="utf-8") as f:
        ids = json.load(f)
    discourse_sim = np.load(DATA_DIR / "discourse_sim.npy")
    tag_prox = np.load(DATA_DIR / "tag_prox.npy")

    tag_prox_hard_path = DATA_DIR / "tag_prox_hard.npy"
    tag_prox_hard = np.load(tag_prox_hard_path) if tag_prox_hard_path.exists() else None

    return ids, discourse_sim, tag_prox, tag_prox_hard


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
    ids, discourse_sim, tag_prox, tag_prox_hard = load_data()
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
    print(f"  Discourse similarity (D_sim):")
    print(f"    mean={d_scores.mean():.3f}  std={d_scores.std():.3f}  "
          f"min={d_scores.min():.3f}  max={d_scores.max():.3f}")
    print(f"    quartiles: {np.percentile(d_scores, [25, 50, 75])}")

    # Tag proximity (soft Jaccard — primary)
    print(f"  Tag proximity — soft Jaccard (primary):")
    print(f"    mean={t_scores.mean():.3f}  std={t_scores.std():.3f}  "
          f"min={t_scores.min():.3f}  max={t_scores.max():.3f}")
    print(f"    quartiles: {np.percentile(t_scores, [25, 50, 75])}")
    zero_pairs = int(np.sum(t_scores == 0.0))
    print(f"    Zero-overlap pairs: {zero_pairs} / {num_pairs} "
          f"({100 * zero_pairs / num_pairs:.1f}%)")

    # Tag proximity (hard Jaccard — comparison)
    tag_prox_hard_stats = None
    if tag_prox_hard is not None:
        t_hard = tag_prox_hard[upper]
        print(f"  Tag proximity — hard Jaccard (comparison):")
        print(f"    mean={t_hard.mean():.3f}  std={t_hard.std():.3f}  "
              f"min={t_hard.min():.3f}  max={t_hard.max():.3f}")
        hard_zeros = int(np.sum(t_hard == 0.0))
        print(f"    Zero-overlap pairs: {hard_zeros} / {num_pairs} "
              f"({100 * hard_zeros / num_pairs:.1f}%)")
        tag_prox_hard_stats = {
            "mean": round(float(t_hard.mean()), 3),
            "std": round(float(t_hard.std()), 3),
            "min": round(float(t_hard.min()), 3),
            "max": round(float(t_hard.max()), 3),
            "zero_pairs": hard_zeros,
        }

    # Orthogonality test
    pearson_r, pearson_p = sp_stats.pearsonr(d_scores, t_scores)
    spearman_r, spearman_p = sp_stats.spearmanr(d_scores, t_scores)
    print(f"\nORTHOGONALITY TEST")
    print(f"  Pearson:  r={pearson_r:.3f}  (p={pearson_p:.4f})")
    print(f"  Spearman: r={spearman_r:.3f}  (p={spearman_p:.4f})")
    if abs(pearson_r) < 0.3:
        verdict = "orthogonal"
        print(f"  >> The two layers are measuring substantially different things.")
    elif abs(pearson_r) < 0.6:
        verdict = "moderate"
        print(f"  >> Moderate correlation -- some overlap, but the layers carry "
              f"independent signal.")
    else:
        verdict = "correlated"
        print(f"  >> High correlation -- discourse profiles may be restating genre "
              f"info in prose.")

    # Save structured output
    output = {
        "nodes": {
            "count": n,
            "avg_tags": round(float(np.mean(tag_counts)), 1),
            "min_tags": min(tag_counts),
            "max_tags": max(tag_counts),
            "confidence": confidence_dist,
        },
        "distribution": {
            "discourse_sim": {
                "mean": round(float(d_scores.mean()), 3),
                "std": round(float(d_scores.std()), 3),
                "min": round(float(d_scores.min()), 3),
                "max": round(float(d_scores.max()), 3),
            },
            "tag_prox": {
                "mean": round(float(t_scores.mean()), 3),
                "std": round(float(t_scores.std()), 3),
                "min": round(float(t_scores.min()), 3),
                "max": round(float(t_scores.max()), 3),
                "zero_pairs": zero_pairs,
            },
        },
        "orthogonality": {
            "pearson_r": round(pearson_r, 3),
            "pearson_p": round(pearson_p, 4),
            "spearman_r": round(spearman_r, 3),
            "spearman_p": round(spearman_p, 4),
            "verdict": verdict,
        },
    }
    if tag_prox_hard_stats:
        output["distribution"]["tag_prox_hard"] = tag_prox_hard_stats

    out_path = DATA_DIR / "stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
