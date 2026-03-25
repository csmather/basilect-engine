"""Compare two discovery outputs to measure ranking stability.

Usage:
    python scripts/stability.py data/discoveries_baseline.json data/discoveries.json
"""

import json
import sys
from pathlib import Path


def load_rankings(path: str) -> dict:
    """Load a discoveries JSON file."""
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def pair_key(pair: dict) -> tuple:
    """Canonical key for a pair (sorted so order doesn't matter)."""
    return tuple(sorted((pair["a"], pair["b"])))


def compare_list(name: str, list_a: list, list_b: list, top_n: int = 15):
    """Compare two ranked lists and report overlap and displacement."""
    keys_a = [pair_key(p) for p in list_a[:top_n]]
    keys_b = [pair_key(p) for p in list_b[:top_n]]

    overlap = set(keys_a) & set(keys_b)
    overlap_pct = len(overlap) / top_n * 100 if top_n > 0 else 0

    # Average rank displacement for shared pairs
    displacements = []
    rank_b = {k: i for i, k in enumerate(keys_b)}
    for i, k in enumerate(keys_a):
        if k in rank_b:
            displacements.append(abs(i - rank_b[k]))

    avg_disp = sum(displacements) / len(displacements) if displacements else float("nan")

    print(f"\n  {name} (top {top_n}):")
    print(f"    Overlap: {len(overlap)}/{top_n} ({overlap_pct:.0f}%)")
    print(f"    Avg rank displacement: {avg_disp:.1f}")

    # Show what moved in/out
    entered = set(keys_b[:top_n]) - set(keys_a[:top_n])
    exited = set(keys_a[:top_n]) - set(keys_b[:top_n])
    if entered:
        print(f"    Entered top {top_n}: {[' x '.join(k) for k in entered]}")
    if exited:
        print(f"    Exited top {top_n}: {[' x '.join(k) for k in exited]}")

    return overlap_pct, avg_disp


def artist_frequency(pairs: list, top_n: int = 15) -> dict:
    """Count how often each artist appears in top-N pairs."""
    counts = {}
    for p in pairs[:top_n]:
        for key in ("a", "b"):
            artist = p[key]
            counts[artist] = counts.get(artist, 0) + 1
    return counts


def flag_dominant_artists(name: str, pairs: list, top_n: int = 15):
    """Flag artists that appear in more than 40% of top-N pairs."""
    freq = artist_frequency(pairs, top_n)
    threshold = top_n * 0.4
    dominant = {k: v for k, v in freq.items() if v >= threshold}
    if dominant:
        print(f"    Dominant artists: {dominant}")


def main():
    if len(sys.argv) < 3:
        print("Usage: python scripts/stability.py <baseline.json> <new.json>")
        sys.exit(1)

    path_a, path_b = sys.argv[1], sys.argv[2]
    a = load_rankings(path_a)
    b = load_rankings(path_b)

    print(f"Comparing: {path_a} vs {path_b}")
    print(f"Pairs: {a['num_pairs']} vs {b['num_pairs']}")

    for category in ("basilect", "deep_scene", "surface_only", "unrelated"):
        if category in a and category in b:
            compare_list(category, a[category], b[category])
            flag_dominant_artists(category, b[category])


if __name__ == "__main__":
    main()
