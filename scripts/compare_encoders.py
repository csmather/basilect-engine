"""Compare top-K rank overlap between two encoders.

Loads MiniLM baseline (data/embeddings_minilm.npy) and the current encoder
(data/embeddings.npy), computes per-artist top-K neighbors from each, and
reports Jaccard@K + Spearman over all pairs. Both raw cosine and
count-adjusted similarity are reported (adjustment refits per encoder,
matching compute.py).
"""

import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"
TOP_K = 10


def load_counts(ids):
    counts = []
    for artist_id in ids:
        node = json.loads((ARTISTS_DIR / artist_id / "quotes.json").read_text(encoding="utf-8"))
        counts.append(len(node["quotes"]))
    return np.array(counts)


def adjust(sim, counts):
    """Same residualize + recenter as compute.py — per encoder fit."""
    n = sim.shape[0]
    upper = np.triu_indices(n, k=1)
    raw_scores = sim[upper]
    log_min = np.log(np.minimum(counts[upper[0]], counts[upper[1]]))
    slope, intercept = np.polyfit(log_min, raw_scores, 1)
    median_log = float(np.median(log_min))
    baseline = slope * median_log + intercept
    log_min_full = np.log(np.minimum.outer(counts, counts))
    sim_adj = sim - (slope * log_min_full + intercept) + baseline
    np.fill_diagonal(sim_adj, 1.0)
    return sim_adj, float(slope), float(baseline)


def top_k(sim, k):
    n = sim.shape[0]
    out = []
    for i in range(n):
        scores = sim[i].copy()
        scores[i] = -np.inf
        idx = np.argsort(-scores)[:k]
        out.append([int(x) for x in idx])
    return out


def jaccard(a, b):
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if (sa | sb) else 0.0


def main():
    ids = json.loads((DATA_DIR / "embedding_ids.json").read_text(encoding="utf-8"))
    emb_mini = np.load(DATA_DIR / "embeddings_minilm.npy")
    emb_qwen = np.load(DATA_DIR / "embeddings.npy")
    counts = load_counts(ids)
    n = len(ids)

    if emb_mini.shape[0] != n or emb_qwen.shape[0] != n:
        raise SystemExit(
            f"Row count mismatch: ids={n}, MiniLM={emb_mini.shape[0]}, Qwen3={emb_qwen.shape[0]}"
        )

    print(f"Comparing encoders on {n} artists")
    print(f"  MiniLM : {emb_mini.shape}")
    print(f"  Qwen3  : {emb_qwen.shape}")

    sim_m = cosine_similarity(emb_mini)
    sim_q = cosine_similarity(emb_qwen)
    sim_m_adj, slope_m, _ = adjust(sim_m, counts)
    sim_q_adj, slope_q, _ = adjust(sim_q, counts)

    upper = np.triu_indices(n, k=1)
    rho_raw, p_raw = spearmanr(sim_m[upper], sim_q[upper])  # type: ignore[misc]
    rho_adj, p_adj = spearmanr(sim_m_adj[upper], sim_q_adj[upper])  # type: ignore[misc]

    top_m_raw = top_k(sim_m, TOP_K)
    top_q_raw = top_k(sim_q, TOP_K)
    top_m_adj = top_k(sim_m_adj, TOP_K)
    top_q_adj = top_k(sim_q_adj, TOP_K)

    j_raw = [jaccard(top_m_raw[i], top_q_raw[i]) for i in range(n)]
    j_adj = [jaccard(top_m_adj[i], top_q_adj[i]) for i in range(n)]

    print()
    print(f"=== Aggregate (top-{TOP_K}) ===")
    print(f"Pairwise Spearman over {len(upper[0])} pairs (1.0 = identical ordering):")
    print(f"  raw      : ρ={float(rho_raw):+.3f}  p={float(p_raw):.3g}")  # type: ignore[arg-type]
    print(f"  adjusted : ρ={float(rho_adj):+.3f}  p={float(p_adj):.3g}")  # type: ignore[arg-type]
    print(f"Per-artist Jaccard@{TOP_K} (1.0 = same top-10):")
    print(f"  raw      : mean={np.mean(j_raw):.3f}  median={np.median(j_raw):.3f}")
    print(f"  adjusted : mean={np.mean(j_adj):.3f}  median={np.median(j_adj):.3f}")
    print(f"Sparsity-fit slopes (score ~ log(min_count)):")
    print(f"  MiniLM   : slope={slope_m:+.4f}")
    print(f"  Qwen3    : slope={slope_q:+.4f}")

    order = list(np.argsort(j_adj))
    print()
    print(f"=== Per-artist top-{TOP_K} (sorted by adjusted Jaccard, lowest = most shifted) ===")
    print(f"  '=' marks an artist that appears in BOTH encoders' top-{TOP_K} for this row.")
    for i in order:
        print(f"\n  {ids[i]:<22}  J_raw={j_raw[i]:.2f}  J_adj={j_adj[i]:.2f}  ({counts[i]} quotes)")
        ml = [ids[k] for k in top_m_adj[i]]
        ql = [ids[k] for k in top_q_adj[i]]
        ml_set, ql_set = set(ml), set(ql)
        for r in range(TOP_K):
            mark_m = "=" if ml[r] in ql_set else " "
            mark_q = "=" if ql[r] in ml_set else " "
            print(f"    {r + 1:2d}.  MiniLM {mark_m} {ml[r]:<22}  |  Qwen3 {mark_q} {ql[r]}")

    out = {
        "top_k": TOP_K,
        "ids": ids,
        "counts": counts.tolist(),
        "spearman_raw": {"rho": float(rho_raw), "p": float(p_raw)},  # type: ignore[arg-type]
        "spearman_adj": {"rho": float(rho_adj), "p": float(p_adj)},  # type: ignore[arg-type]
        "jaccard_raw": j_raw,
        "jaccard_adj": j_adj,
        "fit_slopes": {"minilm": slope_m, "qwen3": slope_q},
        "top_minilm_raw": top_m_raw,
        "top_qwen_raw": top_q_raw,
        "top_minilm_adj": top_m_adj,
        "top_qwen_adj": top_q_adj,
    }
    out_path = DATA_DIR / "encoder_comparison.json"
    out_path.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\nSaved {out_path}")


if __name__ == "__main__":
    main()
