"""Enrich artist tag sets with album-level tags from Last.fm.

For each artist:
1. Fetch top N albums
2. Fetch tags for each album
3. Filter noise tags
4. Normalize via canonical synonym map
5. Merge into artist node, saving provenance in tag_sources
"""

import argparse
import json
import time
from pathlib import Path

from scripts.lastfm import fetch_top_albums, fetch_album_tags
from scripts.musicbrainz import search_artist_mbid, fetch_mb_tags
from scripts.normalize import normalize_tag, normalize_tags
from scripts.tag_filter import is_noise_tag_for_album

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"

# Minimum Last.fm tag count to include an album tag
MIN_ALBUM_TAG_COUNT = 3

# Number of top albums to fetch per artist
TOP_ALBUMS = 5

# Rate limit: seconds between API calls
RATE_LIMIT = 0.25


def enrich_artist(node: dict) -> dict:
    """Enrich a single artist node with album-level tags.

    Returns the updated node. Adds tag_sources field for provenance.
    Idempotent: skips album fetching if already enriched.
    """
    if "tag_sources" not in node:
        node["tag_sources"] = {}

    # Save original artist-level tags ONLY on first run
    if "lastfm_artist" not in node["tag_sources"]:
        node["tag_sources"]["lastfm_artist"] = list(node["tags"])

    # Skip album enrichment if already done
    if "lastfm_albums" in node["tag_sources"]:
        print(f"    [albums] Already enriched, skipping API calls")
        return node

    artist_name = node["name"]

    # Fetch top albums
    albums = fetch_top_albums(artist_name, limit=TOP_ALBUMS)
    time.sleep(RATE_LIMIT)

    album_tags_all = {}
    for album in albums:
        raw_tags = fetch_album_tags(artist_name, album)
        time.sleep(RATE_LIMIT)

        # Filter: noise tags, low-count tags
        filtered = [
            (normalize_tag(name), count)
            for name, count in raw_tags
            if count >= MIN_ALBUM_TAG_COUNT
            and not is_noise_tag_for_album(name, album)
        ]

        if filtered:
            album_tags_all[album] = [name for name, _ in filtered]

    node["tag_sources"]["lastfm_albums"] = album_tags_all

    # Rebuild tags from all sources: original artist tags + album tags
    all_tags = list(node["tag_sources"]["lastfm_artist"])
    for album, tags in album_tags_all.items():
        all_tags.extend(tags)

    node["tags"] = normalize_tags(all_tags)
    return node


def enrich_artist_mb(node: dict) -> dict:
    """Enrich a single artist node with MusicBrainz folksonomy tags.

    Idempotent: skips if already enriched.
    """
    if "tag_sources" not in node:
        node["tag_sources"] = {}

    # Skip if already enriched from MB
    if "musicbrainz" in node["tag_sources"]:
        print(f"    [MB] Already enriched, skipping API calls")
        return node

    artist_name = node["name"]

    mbid = search_artist_mbid(artist_name)
    if mbid is None:
        print(f"    [MB] No MusicBrainz match for '{artist_name}'")
        node["tag_sources"]["musicbrainz"] = []  # mark as attempted
        return node

    mb_tags = fetch_mb_tags(mbid)
    node["tag_sources"]["musicbrainz"] = mb_tags

    # Rebuild tags from ALL sources
    all_tags = list(node["tag_sources"].get("lastfm_artist", []))
    for album, tags in node["tag_sources"].get("lastfm_albums", {}).items():
        all_tags.extend(tags)
    all_tags.extend(normalize_tag(t) for t in mb_tags)

    node["tags"] = normalize_tags(all_tags)
    return node


def main():
    parser = argparse.ArgumentParser(description="Enrich artist tags")
    parser.add_argument("--musicbrainz", action="store_true",
                        help="Also fetch MusicBrainz folksonomy tags")
    args = parser.parse_args()

    paths = sorted(ARTISTS_DIR.glob("*.json"))
    print(f"Enriching tags for {len(paths)} artists...\n")

    for path in paths:
        with open(path, encoding="utf-8") as f:
            node = json.load(f)

        before = len(node["tags"])
        node = enrich_artist(node)

        if args.musicbrainz:
            node = enrich_artist_mb(node)

        after = len(node["tags"])
        new_tags = after - before

        with open(path, "w", encoding="utf-8") as f:
            json.dump(node, f, indent=2, ensure_ascii=False)

        albums_fetched = len(node.get("tag_sources", {}).get("lastfm_albums", {}))
        mb_count = len(node.get("tag_sources", {}).get("musicbrainz", []))
        sources = f"{albums_fetched} albums"
        if args.musicbrainz:
            sources += f", {mb_count} MB tags"
        print(f"  {node['id']}: {before} -> {after} tags "
              f"(+{new_tags} new from {sources})")

    print("\nDone. Run `python scripts/compute.py` to rebuild matrices.")


if __name__ == "__main__":
    main()
