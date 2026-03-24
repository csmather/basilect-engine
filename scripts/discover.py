"""Surface ranked pair lists from precomputed similarity matrices."""

import json
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"


def load_data():
    """Load artist IDs and both similarity matrices."""
    with open(DATA_DIR / "embedding_ids.json", encoding="utf-8") as f:
        ids = json.load(f)
    discourse_sim = np.load(DATA_DIR / "discourse_sim.npy")
    tag_prox = np.load(DATA_DIR / "tag_prox.npy")
    return ids, discourse_sim, tag_prox


def load_names(ids):
    """Load display names for artist IDs."""
    names = {}
    for artist_id in ids:
        path = DATA_DIR / "artists" / f"{artist_id}.json"
        with open(path, encoding="utf-8") as f:
            node = json.load(f)
        names[artist_id] = node["name"]
    return names


def get_pairs(ids, discourse_sim, tag_prox):
    """Extract all unique pairs with both scores."""
    n = len(ids)
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append({
                "a": ids[i],
                "b": ids[j],
                "discourse": float(discourse_sim[i, j]),
                "tag": float(tag_prox[i, j]),
            })
    return pairs


def print_list(title, pairs, names, limit=15):
    """Print a ranked list of pairs."""
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")
    for rank, p in enumerate(pairs[:limit], 1):
        name_a = names[p["a"]]
        name_b = names[p["b"]]
        print(f"  {rank:2d}. {name_a} × {name_b}")
        print(f"      discourse: {p['discourse']:.3f}  |  tag: {p['tag']:.3f}")
    if len(pairs) > limit:
        print(f"  ... and {len(pairs) - limit} more pairs")


def main():
    ids, discourse_sim, tag_prox = load_data()
    names = load_names(ids)
    pairs = get_pairs(ids, discourse_sim, tag_prox)

    # Compute thresholds from distribution
    d_scores = [p["discourse"] for p in pairs]
    t_scores = [p["tag"] for p in pairs]
    d_median = float(np.median(d_scores))
    t_median = float(np.median(t_scores))

    print(f"Pairs: {len(pairs)}")
    print(f"Discourse sim median: {d_median:.3f}")
    print(f"Tag proximity median: {t_median:.3f}")

    # Basilect discoveries: high discourse, low tag
    basilect = [p for p in pairs if p["discourse"] >= d_median and p["tag"] < t_median]
    basilect.sort(key=lambda p: p["discourse"] - p["tag"], reverse=True)

    # Deep scene connections: high discourse, high tag
    deep = [p for p in pairs if p["discourse"] >= d_median and p["tag"] >= t_median]
    deep.sort(key=lambda p: p["discourse"] + p["tag"], reverse=True)

    # Surface-only: low discourse, high tag
    surface = [p for p in pairs if p["discourse"] < d_median and p["tag"] >= t_median]
    surface.sort(key=lambda p: p["tag"] - p["discourse"], reverse=True)

    print_list("BASILECT DISCOVERIES (high discourse, low tag)", basilect, names)
    print_list("DEEP SCENE CONNECTIONS (high discourse, high tag)", deep, names)
    print_list("SURFACE-ONLY CONNECTIONS (low discourse, high tag)", surface, names)

    # Save structured output
    output = {
        "num_pairs": len(pairs),
        "thresholds": {"discourse_median": d_median, "tag_median": t_median},
        "basilect": basilect,
        "deep_scene": deep,
        "surface_only": surface,
    }
    out_path = DATA_DIR / "discoveries.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {out_path}")


if __name__ == "__main__":
    main()
