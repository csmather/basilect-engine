"""Compare median vs mean vs max pooling on cached Qwen3 quote vectors.

Loads data/quote_embeddings.npy (pure encoding, no pool applied) and re-pools
per artist for each method. Then reports:
  1. Pairwise rank-overlap between methods (Jaccard@10, Spearman over 300 pairs).
  2. Diagnostic pairs — danny_brown↔earl_sweatshirt (suspected false positive
     from median-collapse), bjork↔sophie, clairo↔kate_bush — score + rank
     under each method.
  3. Per-method spread stats (std, sparsity correlation).
"""

import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"
TOP_K = 10
DIAGNOSTIC_PAIRS = [
    ("danny_brown", "earl_sweatshirt"),
    ("bjork", "sophie"),
    ("clairo", "kate_bush"),
    ("bladee", "danny_brown"),
    ("burial", "danny_brown"),
]


def pool_artists(quote_emb, quote_index, ids, method):
    by_artist = {aid: [] for aid in ids}
    for row, meta in enumerate(quote_index):
        by_artist[meta["artist_id"]].append(row)
    fn = {"median": np.median, "mean": np.mean, "max": np.max}[method]
    return np.array([fn(quote_emb[by_artist[aid]], axis=0) for aid in ids])


def adjust(sim, counts):
    n = sim.shape[0]
    upper = np.triu_indices(n, k=1)
    raw = sim[upper]
    log_min = np.log(np.minimum(counts[upper[0]], counts[upper[1]]))
    slope, intercept = np.polyfit(log_min, raw, 1)
    median_log = float(np.median(log_min))
    baseline = slope * median_log + intercept
    log_min_full = np.log(np.minimum.outer(counts, counts))
    sim_adj = sim - (slope * log_min_full + intercept) + baseline
    np.fill_diagonal(sim_adj, 1.0)
    return sim_adj, float(slope)


def top_k(sim, k):
    n = sim.shape[0]
    out = []
    for i in range(n):
        scores = sim[i].copy()
        scores[i] = -np.inf
        out.append([int(x) for x in np.argsort(-scores)[:k]])
    return out


def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


def pair_stats(sim, ids, a, b):
    """Return (score, rank-of-b-in-a's-neighbors, rank-of-a-in-b's-neighbors)."""
    i, j = ids.index(a), ids.index(b)
    score = float(sim[i, j])
    n = sim.shape[0]
    row_i = sim[i].copy()
    row_i[i] = -np.inf
    rank_b = int(np.sum(row_i > sim[i, j])) + 1
    row_j = sim[j].copy()
    row_j[j] = -np.inf
    rank_a = int(np.sum(row_j > sim[j, i])) + 1
    return score, rank_b, rank_a, n - 1


def main():
    ids = json.loads((DATA_DIR / "embedding_ids.json").read_text(encoding="utf-8"))
    quote_emb = np.load(DATA_DIR / "quote_embeddings.npy")
    quote_index = json.loads((DATA_DIR / "quote_index.json").read_text(encoding="utf-8"))
    counts = np.array([sum(1 for q in quote_index if q["artist_id"] == aid) for aid in ids])
    n = len(ids)
    upper = np.triu_indices(n, k=1)

    print(f"{n} artists, {quote_emb.shape[0]} quotes, encoder dim={quote_emb.shape[1]}\n")

    methods = ["median", "mean", "max"]
    sims_raw, sims_adj, slopes = {}, {}, {}
    for m in methods:
        artist_emb = pool_artists(quote_emb, quote_index, ids, m)
        sim = cosine_similarity(artist_emb)
        sims_raw[m] = sim
        sim_adj, slope = adjust(sim, counts)
        sims_adj[m] = sim_adj
        slopes[m] = slope

    print("=== Per-method spread (adjusted similarity, upper triangle) ===")
    print(f"  {'method':<8}  {'mean':>7s}  {'std':>7s}  {'min':>7s}  {'max':>7s}  {'slope':>7s}")
    for m in methods:
        s = sims_adj[m][upper]
        print(f"  {m:<8}  {s.mean():+.3f}  {s.std():.3f}  {s.min():+.3f}  {s.max():+.3f}  {slopes[m]:+.4f}")

    print("\n=== Pairwise rank-overlap between methods (adjusted) ===")
    for a in methods:
        for b in methods:
            if a >= b:
                continue
            rho, _ = spearmanr(sims_adj[a][upper], sims_adj[b][upper])
            top_a = top_k(sims_adj[a], TOP_K)
            top_b = top_k(sims_adj[b], TOP_K)
            jac = np.mean([jaccard(top_a[i], top_b[i]) for i in range(n)])
            print(f"  {a:<6} vs {b:<6}: Spearman ρ={float(rho):+.3f}  mean Jaccard@{TOP_K}={jac:.3f}")  # type: ignore[arg-type]

    print(f"\n=== Diagnostic pairs (adjusted score, rank in each artist's neighbors) ===")
    print(f"  Format: score [rank_of_B_in_A's_top / rank_of_A_in_B's_top]  (out of {n - 1})\n")
    print(f"  {'pair':<38s}  {'median':>22s}  {'mean':>22s}  {'max':>22s}")
    for a, b in DIAGNOSTIC_PAIRS:
        cells = []
        for m in methods:
            score, rank_b, rank_a, _ = pair_stats(sims_adj[m], ids, a, b)
            cells.append(f"{score:+.3f} [{rank_b:>2d}/{rank_a:>2d}]")
        print(f"  {a + ' ↔ ' + b:<38s}  {cells[0]:>22s}  {cells[1]:>22s}  {cells[2]:>22s}")

    print(f"\n=== Top-{TOP_K} for each diagnostic anchor under each pool ===")
    for anchor in {p[0] for p in DIAGNOSTIC_PAIRS} | {p[1] for p in DIAGNOSTIC_PAIRS}:
        i = ids.index(anchor)
        print(f"\n  {anchor}  ({counts[i]} quotes)")
        for m in methods:
            top = top_k(sims_adj[m], TOP_K)[i]
            row = "  ".join(f"{ids[k]}({sims_adj[m][i, k]:+.2f})" for k in top[:5])
            print(f"    {m:<7s} → {row}")

    out = {
        "ids": ids,
        "counts": counts.tolist(),
        "spread": {
            m: {
                "mean": float(sims_adj[m][upper].mean()),
                "std": float(sims_adj[m][upper].std()),
                "slope": slopes[m],
            }
            for m in methods
        },
        "diagnostic_pairs": [
            {
                "a": a, "b": b,
                **{m: {
                    "score": pair_stats(sims_adj[m], ids, a, b)[0],
                    "rank_b_in_a": pair_stats(sims_adj[m], ids, a, b)[1],
                    "rank_a_in_b": pair_stats(sims_adj[m], ids, a, b)[2],
                } for m in methods},
            }
            for a, b in DIAGNOSTIC_PAIRS
        ],
    }
    out_path = DATA_DIR / "pooling_comparison.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
