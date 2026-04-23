"""Surface ranked artist pairs by quote similarity.

Ranks on count-adjusted similarity (score); raw cosine is kept as
score_raw for transparency. See compute.py for the adjustment.
"""

import json
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def main():
    ids = json.loads((DATA_DIR / "embedding_ids.json").read_text(encoding="utf-8"))
    sim_raw = np.load(DATA_DIR / "similarity.npy")
    sim_adj = np.load(DATA_DIR / "similarity_adjusted.npy")

    n = len(ids)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append({
                "a": ids[i],
                "b": ids[j],
                "score": float(sim_adj[i, j]),
                "score_raw": float(sim_raw[i, j]),
            })

    pairs.sort(key=lambda p: p["score"], reverse=True)

    print(f"\n{'=' * 60}")
    print(f"  ARTIST SIMILARITY RANKING — {len(pairs)} pairs (adjusted)")
    print(f"{'=' * 60}")
    for rank, p in enumerate(pairs, 1):
        delta = p["score"] - p["score_raw"]
        arrow = "↑" if delta > 0 else ("↓" if delta < 0 else " ")
        print(f"  {rank:3d}. {p['a']:<20} × {p['b']:<20}  "
              f"{p['score']:.3f}  (raw {p['score_raw']:.3f} {arrow}{abs(delta):.3f})")

    out_path = DATA_DIR / "discoveries.json"
    out_path.write_text(json.dumps(pairs, indent=2), encoding="utf-8")
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
