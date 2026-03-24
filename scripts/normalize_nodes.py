"""Apply tag normalization to all existing artist nodes."""

import json
from pathlib import Path

from scripts.normalize import normalize_tags

ARTISTS_DIR = Path(__file__).resolve().parent.parent / "data" / "artists"


def normalize_node(path: Path) -> dict:
    """Load a node, normalize its tags, return the updated node."""
    with open(path, encoding="utf-8") as f:
        node = json.load(f)
    original = node["tags"]
    normalized = normalize_tags(original)
    node["tags"] = normalized
    return node, original, normalized


def main():
    paths = sorted(ARTISTS_DIR.glob("*.json"))
    print(f"Normalizing tags for {len(paths)} artists...\n")

    changes = 0
    for path in paths:
        node, original, normalized = normalize_node(path)
        if original != normalized:
            changes += 1
            removed = len(original) - len(normalized)
            print(f"  {node['id']}: {len(original)} -> {len(normalized)} tags "
                  f"({removed} duplicates removed)")
            with open(path, "w", encoding="utf-8") as f:
                json.dump(node, f, indent=2, ensure_ascii=False)
        else:
            print(f"  {node['id']}: no changes")

    print(f"\n{changes} artists updated.")


if __name__ == "__main__":
    main()
