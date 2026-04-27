"""Aggregate co-occurrence pairs from data/canonicalized.jsonl.

Reads:
  data/canonicalized.jsonl   (episode → sorted unique artist_ids)
  data/artist_sitemap.jsonl  (id → slug, for human-readable output)

Writes:
  <out>  (sorted by shows desc, then eps desc)

Usage:
  python derive_pairs.py                                          # top 2000, shows>=2 → data/top_pairs.jsonl
  python derive_pairs.py --min-shows 3 --top 5000 --out data/top_pairs_wide.jsonl
"""
import argparse
import json
from collections import defaultdict
from itertools import combinations
from pathlib import Path

ROOT = Path(__file__).parent
DATA = ROOT / "data"
CANONICAL_FILE = DATA / "canonicalized.jsonl"
ARTIST_SITEMAP_FILE = DATA / "artist_sitemap.jsonl"


def load_id_to_slug() -> dict[int, str]:
    out: dict[int, str] = {}
    with ARTIST_SITEMAP_FILE.open() as f:
        for line in f:
            r = json.loads(line)
            out[r["id"]] = r["slug"]
    return out


def derive(min_shows: int, top: int, out_path: Path) -> None:
    eps_counts: dict[tuple[int, int], int] = defaultdict(int)
    shows_sets: dict[tuple[int, int], set[str]] = defaultdict(set)

    with CANONICAL_FILE.open() as f:
        for line in f:
            r = json.loads(line)
            ids = r["artist_ids"]
            if len(ids) < 2:
                continue
            show = r["show_alias"]
            for a, b in combinations(ids, 2):
                key = (a, b)
                eps_counts[key] += 1
                shows_sets[key].add(show)

    print(f"distinct pairs: {len(eps_counts):,}")

    rows = []
    for key, eps in eps_counts.items():
        shows = len(shows_sets[key])
        if shows < min_shows:
            continue
        rows.append((shows, eps, key[0], key[1]))
    print(f"pairs with shows >= {min_shows}: {len(rows):,}")
    rows.sort(key=lambda r: (-r[0], -r[1]))
    rows = rows[:top]

    id_to_slug = load_id_to_slug()
    with out_path.open("w") as f:
        for shows, eps, a, b in rows:
            f.write(json.dumps({
                "a": id_to_slug.get(a, str(a)),
                "b": id_to_slug.get(b, str(b)),
                "a_id": a,
                "b_id": b,
                "eps": eps,
                "shows": shows,
            }) + "\n")
    print(f"wrote {out_path} ({len(rows):,} pairs)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--min-shows", type=int, default=2)
    p.add_argument("--top", type=int, default=2000)
    p.add_argument("--out", type=str, default="data/top_pairs.jsonl")
    args = p.parse_args()
    derive(args.min_shows, args.top, Path(args.out))


if __name__ == "__main__":
    main()
