"""Surface top-K quote pairs driving an artist-pair similarity score.

Usage:
    python scripts/explain.py {artist_a} {artist_b} [--top K] [--json]

Loads cached per-quote vectors written by embed.py — no re-encoding.
Header reports the artist-pair raw + adjusted cosine from compute.py
output so the per-quote pairs can be read in context of the aggregate.
"""

import argparse
import json
import textwrap
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"


def load_pair_vectors(artist_a, artist_b):
    """Return (vecs_a, vecs_b, quotes_a, quotes_b)."""
    quote_index = json.loads((DATA_DIR / "quote_index.json").read_text(encoding="utf-8"))
    quote_emb = np.load(DATA_DIR / "quote_embeddings.npy")

    rows_a = [i for i, r in enumerate(quote_index) if r["artist_id"] == artist_a]
    rows_b = [i for i, r in enumerate(quote_index) if r["artist_id"] == artist_b]
    if not rows_a or not rows_b:
        missing = [a for a, rows in [(artist_a, rows_a), (artist_b, rows_b)] if not rows]
        raise SystemExit(f"No cached quote vectors for: {', '.join(missing)}")

    quotes_a = json.loads((ARTISTS_DIR / artist_a / "quotes.json").read_text(encoding="utf-8"))["quotes"]
    quotes_b = json.loads((ARTISTS_DIR / artist_b / "quotes.json").read_text(encoding="utf-8"))["quotes"]
    return quote_emb[rows_a], quote_emb[rows_b], quotes_a, quotes_b


def pair_scores(artist_a, artist_b):
    """Return (raw, adjusted) artist-pair cosine from compute.py output, or (None, None)."""
    ids_path = DATA_DIR / "embedding_ids.json"
    raw_path = DATA_DIR / "similarity.npy"
    adj_path = DATA_DIR / "similarity_adjusted.npy"
    if not (ids_path.exists() and raw_path.exists() and adj_path.exists()):
        return None, None
    ids = json.loads(ids_path.read_text(encoding="utf-8"))
    if artist_a not in ids or artist_b not in ids:
        return None, None
    i, j = ids.index(artist_a), ids.index(artist_b)
    return float(np.load(raw_path)[i, j]), float(np.load(adj_path)[i, j])


def cosine(a, b):
    a_norm = a / (np.linalg.norm(a, axis=1, keepdims=True) + 1e-12)
    b_norm = b / (np.linalg.norm(b, axis=1, keepdims=True) + 1e-12)
    return a_norm @ b_norm.T


def top_k_pairs(sim, k):
    flat = np.argsort(sim.ravel())[::-1][:k]
    n_b = sim.shape[1]
    return [(int(idx // n_b), int(idx % n_b), float(sim.ravel()[idx])) for idx in flat]


def fmt_quote(q, width=80, indent="      "):
    text = q.get("text", "")
    wrapped = textwrap.fill(text, width=width, initial_indent=indent, subsequent_indent=indent)
    meta_parts = [q.get("publication") or "?", q.get("date") or "?"]
    return wrapped, " · ".join(meta_parts)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("artist_a")
    parser.add_argument("artist_b")
    parser.add_argument("--top", type=int, default=5)
    parser.add_argument("--json", action="store_true", dest="as_json")
    args = parser.parse_args()

    vecs_a, vecs_b, quotes_a, quotes_b = load_pair_vectors(args.artist_a, args.artist_b)
    sim = cosine(vecs_a, vecs_b)
    pairs = top_k_pairs(sim, args.top)
    raw, adj = pair_scores(args.artist_a, args.artist_b)

    if args.as_json:
        out = {
            "a": args.artist_a,
            "b": args.artist_b,
            "artist_pair_raw": raw,
            "artist_pair_adjusted": adj,
            "top_k": args.top,
            "quote_pairs": [
                {
                    "similarity": s,
                    "quote_a": quotes_a[i],
                    "quote_b": quotes_b[j],
                }
                for i, j, s in pairs
            ],
        }
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    print(f"\n{args.artist_a}  ↔  {args.artist_b}")
    if raw is not None and adj is not None:
        print(f"  artist-pair cosine : raw={raw:+.3f}  adjusted={adj:+.3f}")
    print(f"  cartesian quote-pair grid : {sim.shape[0]} × {sim.shape[1]} = {sim.size} pairs")
    print(f"  showing top {args.top}\n")

    for rank, (i, j, s) in enumerate(pairs, 1):
        qa, qa_meta = fmt_quote(quotes_a[i])
        qb, qb_meta = fmt_quote(quotes_b[j])
        print(f"  #{rank}  sim={s:+.3f}")
        print(f"    [{args.artist_a}] ({qa_meta})")
        print(qa)
        print(f"    [{args.artist_b}] ({qb_meta})")
        print(qb)
        print()


if __name__ == "__main__":
    main()
