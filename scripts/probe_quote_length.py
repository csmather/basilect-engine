"""Probe whether short quotes are dragging artist vectors toward register-match.

Loads cached quote vectors, then for each length threshold T, drops quotes
with fewer than T words before median-pooling. Reports:
  1. How many quotes survive per artist (esp. danny_brown).
  2. Diagnostic pairs' rank under each threshold.
  3. Top-5 neighbors for the implicated anchors (danny_brown, earl_sweatshirt).
"""

import json
from pathlib import Path

import numpy as np
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"
THRESHOLDS = [0, 10, 15, 30]
DIAGNOSTIC_PAIRS = [
    ("danny_brown", "earl_sweatshirt"),
    ("bjork", "sophie"),
    ("clairo", "kate_bush"),
    ("bladee", "danny_brown"),
    ("burial", "danny_brown"),
]
ANCHORS = ["danny_brown", "earl_sweatshirt", "bladee", "burial"]


def load():
    ids = json.loads((DATA_DIR / "embedding_ids.json").read_text(encoding="utf-8"))
    quote_emb = np.load(DATA_DIR / "quote_embeddings.npy")
    quote_index = json.loads((DATA_DIR / "quote_index.json").read_text(encoding="utf-8"))
    # Pull quote text in cached row order
    texts_by_artist = {}
    for aid in ids:
        node = json.loads((ARTISTS_DIR / aid / "quotes.json").read_text(encoding="utf-8"))
        texts_by_artist[aid] = [q["text"] for q in node["quotes"]]
    word_counts = np.array([
        len(texts_by_artist[r["artist_id"]][r["quote_idx"]].split())
        for r in quote_index
    ])
    return ids, quote_emb, quote_index, word_counts


def pool_with_threshold(quote_emb, quote_index, ids, word_counts, threshold):
    rows_by_artist = {aid: [] for aid in ids}
    for row, meta in enumerate(quote_index):
        if word_counts[row] >= threshold:
            rows_by_artist[meta["artist_id"]].append(row)
    artist_emb, kept = [], {}
    for aid in ids:
        rows = rows_by_artist[aid]
        kept[aid] = len(rows)
        # If everything was filtered out, fall back to all quotes (no realistic
        # threshold should hit this, but guard against div-by-zero on tiny corpora)
        if not rows:
            rows = [r for r, m in enumerate(quote_index) if m["artist_id"] == aid]
        artist_emb.append(np.median(quote_emb[rows], axis=0))
    return np.array(artist_emb), kept


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
    return sim_adj


def pair_ranks(sim, ids, a, b):
    i, j = ids.index(a), ids.index(b)
    row_i = sim[i].copy(); row_i[i] = -np.inf
    row_j = sim[j].copy(); row_j[j] = -np.inf
    rank_b = int(np.sum(row_i > sim[i, j])) + 1
    rank_a = int(np.sum(row_j > sim[j, i])) + 1
    return float(sim[i, j]), rank_b, rank_a


def top_n_for(sim, ids, anchor, n=5):
    i = ids.index(anchor)
    row = sim[i].copy(); row[i] = -np.inf
    top = np.argsort(-row)[:n]
    return [(ids[k], float(sim[i, k])) for k in top]


def main():
    ids, quote_emb, quote_index, word_counts = load()
    n = len(ids)

    print(f"{n} artists, {quote_emb.shape[0]} quotes total\n")

    # Length distribution snapshot for the implicated anchors
    print("=== Word-count distribution per anchor ===")
    print(f"  {'artist':<22s}  {'n':>4s}  {'min':>4s}  {'p25':>4s}  {'med':>4s}  {'p75':>4s}  {'max':>5s}  {'<10':>5s}  {'<15':>5s}  {'<30':>5s}")
    for aid in ANCHORS:
        rows = [r for r, m in enumerate(quote_index) if m["artist_id"] == aid]
        wc = word_counts[rows]
        lt10 = int(np.sum(wc < 10))
        lt15 = int(np.sum(wc < 15))
        lt30 = int(np.sum(wc < 30))
        print(f"  {aid:<22s}  {len(wc):>4d}  {wc.min():>4d}  {int(np.percentile(wc, 25)):>4d}  "
              f"{int(np.median(wc)):>4d}  {int(np.percentile(wc, 75)):>4d}  {wc.max():>5d}  "
              f"{lt10:>5d}  {lt15:>5d}  {lt30:>5d}")

    # Per-threshold pool + diagnostic table
    sims = {}
    kept_all = {}
    for t in THRESHOLDS:
        artist_emb, kept = pool_with_threshold(quote_emb, quote_index, ids, word_counts, t)
        kept_all[t] = kept
        counts = np.array([kept[aid] if kept[aid] > 0 else 1 for aid in ids])
        sim = cosine_similarity(artist_emb)
        sims[t] = adjust(sim, counts)

    print(f"\n=== Quotes kept per anchor at each threshold ===")
    header = "  ".join(f"T={t:>2d}" for t in THRESHOLDS)
    print(f"  {'artist':<22s}  " + header)
    for aid in ANCHORS:
        row = "  ".join(f"{kept_all[t][aid]:>4d}" for t in THRESHOLDS)
        print(f"  {aid:<22s}  {row}")

    print(f"\n=== Diagnostic pair ranks at each threshold (rank_B_in_A's_top / rank_A_in_B's_top) ===")
    header = "  ".join(f"{'T=' + str(t):>14s}" for t in THRESHOLDS)
    print(f"  {'pair':<38s}  " + header)
    for a, b in DIAGNOSTIC_PAIRS:
        cells = []
        for t in THRESHOLDS:
            score, rb, ra = pair_ranks(sims[t], ids, a, b)
            cells.append(f"{score:+.3f}[{rb:>2d}/{ra:>2d}]")
        row = "  ".join(f"{c:>14s}" for c in cells)
        print(f"  {a + ' ↔ ' + b:<38s}  {row}")

    print(f"\n=== Top-5 neighbors for danny_brown / earl_sweatshirt at each threshold ===")
    for anchor in ["danny_brown", "earl_sweatshirt"]:
        print(f"\n  {anchor}")
        for t in THRESHOLDS:
            top = top_n_for(sims[t], ids, anchor, n=5)
            row = "  ".join(f"{name}({s:+.2f})" for name, s in top)
            print(f"    T={t:>2d} (kept={kept_all[t][anchor]:>3d}) → {row}")


if __name__ == "__main__":
    main()
