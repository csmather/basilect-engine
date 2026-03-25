"""Fetch genres for an artist from the MusicBrainz API."""

import json
import sys
import time

import requests

BASE_URL = "https://musicbrainz.org/ws/2"
HEADERS = {"User-Agent": "basilect-engine/0.1 (https://github.com/basilect-engine)"}

# Module-level rate limiter: MB API allows max 1 request per second
_last_request_time = 0.0


def _rate_limited_get(url: str, params: dict) -> requests.Response:
    """GET with rate limiting — ensures at least 1.1s between requests."""
    global _last_request_time
    elapsed = time.time() - _last_request_time
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)
    resp = requests.get(url, params=params, headers=HEADERS)
    _last_request_time = time.time()
    resp.raise_for_status()
    return resp


def search_artist(artist_name: str, limit: int = 5) -> list[dict]:
    """Search MusicBrainz for an artist by name. Returns a list of candidates."""
    resp = _rate_limited_get(
        f"{BASE_URL}/artist/",
        params={"query": f"artist:{artist_name}", "fmt": "json", "limit": limit},
    )
    return resp.json().get("artists", [])


def fetch_genres_by_mbid(mbid: str) -> list[str]:
    """Fetch genres for an artist by MBID. Returns lowercase genre names."""
    resp = _rate_limited_get(
        f"{BASE_URL}/artist/{mbid}",
        params={"inc": "genres", "fmt": "json"},
    )
    data = resp.json()
    return [
        g["name"].lower()
        for g in data.get("genres", [])
        if int(g.get("count", 0)) > 0
    ]


def fetch_genres(artist_name: str, mbid: str | None = None) -> list[str]:
    """Fetch genres for an artist. If mbid is provided, use it directly.
    Otherwise search by name and use the top result."""
    if mbid:
        print(f"Using MBID: {mbid}")
        return fetch_genres_by_mbid(mbid)

    candidates = search_artist(artist_name)
    if not candidates:
        print(f"No MusicBrainz results for '{artist_name}'.")
        return []

    # Show top results for disambiguation
    print(f"Search results for '{artist_name}':")
    for i, c in enumerate(candidates[:5]):
        disambig = c.get("disambiguation", "")
        label = f" ({disambig})" if disambig else ""
        print(f"  {i + 1}. {c['name']}{label}  [score={c.get('score', '?')}  mbid={c['id']}]")

    # Use top result
    top = candidates[0]
    print(f"Using: {top['name']} ({top['id']})")
    return fetch_genres_by_mbid(top["id"])


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/musicbrainz.py <artist name> [--mbid <MBID>]")
        sys.exit(1)

    args = sys.argv[1:]
    mbid = None
    if "--mbid" in args:
        idx = args.index("--mbid")
        mbid = args[idx + 1]
        args = args[:idx] + args[idx + 2:]

    artist_name = " ".join(args)
    genres = fetch_genres(artist_name, mbid=mbid)

    if genres:
        print(f"\n{artist_name}: {len(genres)} genres")
        print(json.dumps(genres, indent=2))
    else:
        print(f"\nNo genres found for '{artist_name}'.")


if __name__ == "__main__":
    main()
