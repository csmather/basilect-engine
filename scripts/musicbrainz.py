"""Fetch folksonomy tags from MusicBrainz."""

import time

import requests

BASE_URL = "https://musicbrainz.org/ws/2"
HEADERS = {
    "User-Agent": "BasilectEngine/0.1 (https://github.com/basilect-engine)",
    "Accept": "application/json",
}

# MusicBrainz rate limit: 1 req/sec
RATE_LIMIT = 1.1


def search_artist_mbid(artist_name: str) -> str | None:
    """Search MusicBrainz for an artist, return their MBID or None."""
    time.sleep(RATE_LIMIT)
    resp = requests.get(f"{BASE_URL}/artist", params={
        "query": f'artist:"{artist_name}"',
        "limit": 1,
        "fmt": "json",
    }, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    artists = data.get("artists", [])
    if not artists:
        return None

    # Return the top match
    return artists[0].get("id")


def fetch_mb_tags(mbid: str) -> list[str]:
    """Fetch folksonomy tags for an artist by MBID. Returns lowercase tag names."""
    time.sleep(RATE_LIMIT)
    resp = requests.get(f"{BASE_URL}/artist/{mbid}", params={
        "inc": "tags",
        "fmt": "json",
    }, headers=HEADERS)
    resp.raise_for_status()
    data = resp.json()

    tags = data.get("tags", [])
    # MusicBrainz tags have a "count" (votes). Keep tags with count >= 1.
    return [t["name"].lower() for t in tags if t.get("count", 0) >= 1]
