"""Fetch MusicBrainz genres for all artists and update their nodes.

For artists where auto-search is unreliable, MBIDs are hardcoded.
Run this script to populate/refresh the genres and mbid fields.
"""

import io
import json
import sys
import time
from pathlib import Path

import requests

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

BASE_URL = "https://musicbrainz.org/ws/2"
HEADERS = {"User-Agent": "basilect-engine/0.1 (https://github.com/basilect-engine)"}
ARTISTS_DIR = Path(__file__).resolve().parent.parent / "data" / "artists"

_last_req = 0.0


def mb_get(url, params):
    global _last_req
    elapsed = time.time() - _last_req
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    r = requests.get(url, params=params, headers=HEADERS)
    _last_req = time.time()
    r.raise_for_status()
    return r.json()


def search_mbid(name, limit=5):
    data = mb_get(f"{BASE_URL}/artist/", {"query": f"artist:{name}", "fmt": "json", "limit": limit})
    return data.get("artists", [])


def fetch_genres(mbid):
    data = mb_get(f"{BASE_URL}/artist/{mbid}", {"inc": "genres", "fmt": "json"})
    return [g["name"].lower() for g in data.get("genres", []) if int(g.get("count", 0)) > 0]


# Hardcoded MBIDs for artists with disambiguation issues
KNOWN_MBIDS = {
    "alex_g":       "18c8c840-3a7f-4649-9eb6-5ad91d3d4e1a",  # Alex G (Giannascoli)
    "danny_brown":  "960afc67-9c21-46dd-9c7f-ff2b509e3150",  # Danny Brown (US rapper)
    "faye_webster": "ce4a1c08-6912-423f-bf6c-97ce69f5e89f",  # Faye Webster
    "fishmans":     "f24a55f9-e784-4f4e-b399-e81dc7583735",  # Fishmans (Japanese band)
    "the_garden":   "c8e4b7db-c6e5-4a16-8bf5-b14a98dc3714",  # The Garden (US duo)
}


def main():
    for path in sorted(ARTISTS_DIR.glob("*.json")):
        slug = path.stem
        with open(path, encoding="utf-8") as f:
            node = json.load(f)
        name = node["name"]

        # Get MBID
        if slug in KNOWN_MBIDS:
            mbid = KNOWN_MBIDS[slug]
            print(f"{name}: using known MBID {mbid}")
        else:
            candidates = search_mbid(name)
            if not candidates:
                print(f"{name}: NO MB RESULTS — skipping genres")
                continue
            top = candidates[0]
            mbid = top["id"]
            disambig = top.get("disambiguation", "")
            label = f" ({disambig})" if disambig else ""
            print(f"{name}: matched '{top['name']}{label}' [{mbid}]")

        # Fetch genres
        genres = fetch_genres(mbid)

        if genres:
            print(f"  {len(genres)} genres: {genres}")
        else:
            print(f"  No MB genres — keeping existing: {node.get('genres', [])}")
            genres = node.get("genres", [])

        node["mbid"] = mbid
        node["genres"] = genres

        with open(path, "w", encoding="utf-8") as f:
            json.dump(node, f, indent=2, ensure_ascii=False)

    print("\nDone.")


if __name__ == "__main__":
    main()
