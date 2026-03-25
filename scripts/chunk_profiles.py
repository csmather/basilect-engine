"""Split discourse profiles into atomic claim chunks for all artists."""

import json
import re
from pathlib import Path

ARTISTS_DIR = Path(__file__).resolve().parent.parent / "data" / "artists"

# Split on sentence-ending punctuation followed by whitespace and a new sentence.
# Handles regular quotes, curly quotes, and apostrophes at sentence boundaries.
SPLIT_PATTERN = re.compile(
    r'(?<=[.?!"\u201d\u2019])\s+(?=[A-Z"\u201c])'
)


def chunk_profile(profile: str) -> list[str]:
    """Split a discourse profile into sentence-level chunks."""
    chunks = SPLIT_PATTERN.split(profile)
    return [c.strip() for c in chunks if c.strip()]


def main():
    for path in sorted(ARTISTS_DIR.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            node = json.load(f)

        chunks = chunk_profile(node["discourse_profile"])
        node["discourse_chunks"] = chunks

        with open(path, "w", encoding="utf-8") as f:
            json.dump(node, f, indent=2, ensure_ascii=False)

        print(f"  {node['name']}: {len(chunks)} chunks")


if __name__ == "__main__":
    main()
