"""Fetch top tags for an artist from the Last.fm API."""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

API_KEY = os.getenv("LASTFM_API_KEY")
BASE_URL = "http://ws.audioscrobbler.com/2.0/"


def fetch_top_tags(artist_name: str) -> list[str]:
    """Fetch top tags for an artist. Returns a list of lowercase tag strings."""
    resp = requests.get(BASE_URL, params={
        "method": "artist.getTopTags",
        "artist": artist_name,
        "api_key": API_KEY,
        "format": "json",
    })
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        print(f"Last.fm error for '{artist_name}': {data['message']}")
        return []

    tags_raw = data.get("toptags", {}).get("tag", [])
    # Keep tags with non-trivial weight (>0)
    return [t["name"].lower() for t in tags_raw if int(t.get("count", 0)) > 0]


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/lastfm.py <artist name>")
        sys.exit(1)

    artist_name = " ".join(sys.argv[1:])
    tags = fetch_top_tags(artist_name)

    if tags:
        print(f"{artist_name}: {len(tags)} tags")
        print(json.dumps(tags, indent=2))
    else:
        print(f"No tags found for '{artist_name}'.")


if __name__ == "__main__":
    main()
