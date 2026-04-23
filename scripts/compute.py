"""Compute pairwise cosine similarity from artist embeddings.

Also emits a count-adjusted similarity matrix that removes the
sparsity artifact measured in D1 (quote-count correlates positively
with raw similarity). Adjustment is a linear fit of score on
log(min pair count), residualized and recentered at the median depth.
"""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"


def load_counts(ids):
    counts = []
    for artist_id in ids:
        node = json.loads((ARTISTS_DIR / artist_id / "quotes.json").read_text(encoding="utf-8"))
        counts.append(len(node["quotes"]))
    return np.array(counts)


def main():
    embeddings = np.load(DATA_DIR / "embeddings.npy")
    ids = json.loads((DATA_DIR / "embedding_ids.json").read_text(encoding="utf-8"))
    counts = load_counts(ids)
    print(f"Loaded {len(ids)} embeddings ({embeddings.shape})")

    sim = cosine_similarity(embeddings)
    np.save(DATA_DIR / "similarity.npy", sim)

    n = len(ids)
    upper = np.triu_indices(n, k=1)
    raw_scores = sim[upper]

    log_min = np.log(np.minimum(counts[upper[0]], counts[upper[1]]))
    slope, intercept = np.polyfit(log_min, raw_scores, 1)
    median_log = float(np.median(log_min))
    baseline = slope * median_log + intercept

    # Build full adjusted matrix (symmetric, diagonal = 1.0)
    log_min_full = np.log(np.minimum.outer(counts, counts))
    sim_adj = sim - (slope * log_min_full + intercept) + baseline
    np.fill_diagonal(sim_adj, 1.0)
    np.save(DATA_DIR / "similarity_adjusted.npy", sim_adj)

    fit = {
        "slope": float(slope),
        "intercept": float(intercept),
        "baseline": float(baseline),
        "median_log_min_count": median_log,
        "median_min_count": float(np.exp(median_log)),
        "predictor": "log(min(count_i, count_j))",
    }
    (DATA_DIR / "similarity_fit.json").write_text(json.dumps(fit, indent=2), encoding="utf-8")

    adj_scores = sim_adj[upper]
    print(f"Saved similarity.npy            (raw cosine)          {sim.shape}")
    print(f"Saved similarity_adjusted.npy   (count-corrected)     {sim_adj.shape}")
    print(f"Saved similarity_fit.json       slope={slope:+.4f} intercept={intercept:+.4f} "
          f"median_min_count≈{np.exp(median_log):.0f}")
    print(f"\n{len(raw_scores)} pairs")
    print(f"  raw      — mean: {raw_scores.mean():.3f}, std: {raw_scores.std():.3f}, "
          f"range: [{raw_scores.min():.3f}, {raw_scores.max():.3f}]")
    print(f"  adjusted — mean: {adj_scores.mean():.3f}, std: {adj_scores.std():.3f}, "
          f"range: [{adj_scores.min():.3f}, {adj_scores.max():.3f}]")


if __name__ == "__main__":
    main()
