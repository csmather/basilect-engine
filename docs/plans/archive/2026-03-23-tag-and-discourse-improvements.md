# Tag Layer & Discourse Layer Improvements

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the binary Jaccard problem by enriching and normalizing the tag layer, then improve discourse quality and pipeline integrity.

**Architecture:** Tag enrichment pulls from Last.fm album tags and MusicBrainz folksonomy, normalizes through a canonical form map, and merges into existing artist nodes. A soft Jaccard variant gives partial credit for related tags. Discourse profiles get a quality checklist. Pipeline gets consistency checks.

**Tech Stack:** Python, Last.fm API, MusicBrainz API, sentence-transformers, numpy, scipy, scikit-learn

---

## Context

Read `CLAUDE.md` for full project documentation. Key points for this plan:

- 20 artist nodes in `data/artists/*.json`, each with ~10 Last.fm tags and a prose discourse profile
- Two similarity layers: tag proximity (Jaccard on tag sets) and discourse similarity (cosine on embedded profiles)
- Current tag median is 0.053 — nearly binary. All basilect discoveries have tag=0.0
- Last.fm `tag.getSimilar` endpoint is dead (returns empty). Do NOT use it.
- Spotify genres endpoint is deprecated and too sparse. Do NOT use it.
- Last.fm `album.getTopTags` works well and surfaces subgenre/bridge tags not present at artist level
- MusicBrainz folksonomy tags are a good supplementary source
- The `.env` file has `LASTFM_API_KEY` (actively used) and Spotify keys (unused, ignore)
- All scripts are in `scripts/`, all data in `data/`, artist nodes in `data/artists/`
- Python scripts use `pathlib` for paths. Project runs on Windows.

### Current node schema

```json
{
  "id": "artist_slug",
  "name": "Artist Name",
  "country": "XX",
  "tags": ["tag1", "tag2", "tag3"],
  "discourse_profile": "...",
  "sources": [{"url": "...", "type": "...", "fetched": "..."}],
  "confidence": "high"
}
```

### Known tag problems (why we're doing this)

1. Within-artist duplicates: Danny Brown has both "hip-hop" AND "hip hop", both "experimental hip-hop" AND "experimental hip hop" (4 slots for 2 concepts). Six artists have this.
2. ~10 tags per artist is a ceiling — album-level tags surface subgenres (e.g., "jazz rap", "psychedelic folk") that don't appear at artist level.
3. Related tags get zero Jaccard credit: "jazz" and "jazz fusion" are treated as completely different.
4. Tag median 0.053 means the layer is nearly binary: zero overlap or some overlap, no gradient.

---

## Phase 1: Tag Normalization

### Task 1: Build the normalization module

**Files:**
- Create: `scripts/normalize.py`
- Test: `tests/test_normalize.py`

This module canonicalizes tags so that "hip hop", "hip-hop", and "Hip-Hop" all become one canonical form. It also deduplicates within an artist's tag list.

- [ ] **Step 1: Set up Python package structure and create test file**

The project has no package configuration. Tests import from `scripts.*`, which requires Python to resolve `scripts` as a package. Create `__init__.py` files and a root `conftest.py`:

```bash
mkdir -p tests
touch scripts/__init__.py
touch tests/__init__.py
```

Create `conftest.py` in the project root (ensures imports work regardless of how pytest is invoked):

```python
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
```

Also add `pytest` to `requirements.txt`:

```bash
echo "pytest" >> requirements.txt
```

Now write `tests/test_normalize.py`:

```python
"""Tests for tag normalization."""

from scripts.normalize import normalize_tag, normalize_tags


def test_hyphen_vs_space():
    assert normalize_tag("hip hop") == "hip-hop"
    assert normalize_tag("hip-hop") == "hip-hop"


def test_casing():
    assert normalize_tag("Hip-Hop") == "hip-hop"
    assert normalize_tag("Neo-Psychedelia") == "neo-psychedelia"
    assert normalize_tag("Avant-Garde") == "avant-garde"


def test_known_synonyms():
    assert normalize_tag("electronica") == "electronic"
    assert normalize_tag("experimental hip hop") == "experimental hip-hop"
    assert normalize_tag("hardcore hip hop") == "hardcore hip-hop"


def test_normalize_tags_deduplicates():
    tags = ["hip-hop", "hip hop", "rap", "Hip-Hop"]
    result = normalize_tags(tags)
    assert result.count("hip-hop") == 1
    assert "rap" in result


def test_normalize_tags_preserves_order():
    tags = ["rock", "indie", "folk"]
    result = normalize_tags(tags)
    assert result == ["rock", "indie", "folk"]


def test_normalize_tags_removes_dupes_keeps_first():
    tags = ["hip-hop", "rap", "hip hop", "trap"]
    result = normalize_tags(tags)
    assert result == ["hip-hop", "rap", "trap"]
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
cd C:\Users\mathe\projects\basilect-engine
python -m pytest tests/test_normalize.py -v
```

Expected: ImportError or ModuleNotFoundError (normalize.py doesn't exist yet).

- [ ] **Step 3: Implement normalize.py**

Create `scripts/normalize.py`:

```python
"""Tag normalization: canonical forms, synonym resolution, deduplication."""

# Canonical synonym map: maps variant -> canonical form.
# Applied AFTER lowercasing. Add entries as new variants are discovered.
SYNONYMS = {
    "hip hop": "hip-hop",
    "hiphop": "hip-hop",
    "electronica": "electronic",
    "experimental hip hop": "experimental hip-hop",
    "hardcore hip hop": "hardcore hip-hop",
    "abstract hip hop": "abstract hip-hop",
    "west coast hip hop": "west coast hip-hop",
}


def normalize_tag(tag: str) -> str:
    """Normalize a single tag: lowercase, apply synonym map."""
    tag = tag.strip().lower()
    return SYNONYMS.get(tag, tag)


def normalize_tags(tags: list[str]) -> list[str]:
    """Normalize and deduplicate a list of tags, preserving first-seen order."""
    seen = set()
    result = []
    for tag in tags:
        canonical = normalize_tag(tag)
        if canonical not in seen:
            seen.add(canonical)
            result.append(canonical)
    return result
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_normalize.py -v
```

Expected: All 6 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/normalize.py tests/test_normalize.py
git commit -m "feat: add tag normalization module with synonym map and dedup"
```

---

### Task 2: Apply normalization to all existing artist nodes

**Files:**
- Create: `scripts/normalize_nodes.py`
- Modify: `data/artists/*.json` (all 20 files)

- [ ] **Step 1: Write the normalization script**

Create `scripts/normalize_nodes.py`:

```python
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
```

- [ ] **Step 2: Run it**

```bash
python scripts/normalize_nodes.py
```

Expected: Several artists updated (at minimum: danny_brown, badbadnotgood, bladee, nujabes, yung_lean, earl_sweatshirt — all have "hip-hop"/"hip hop" duplicates).

- [ ] **Step 3: Verify a known case**

Read `data/artists/danny_brown.json` and confirm:
- "hip-hop" and "hip hop" collapsed to one entry
- "experimental hip-hop" and "experimental hip hop" collapsed to one entry
- "hardcore hip-hop" and "hardcore hip hop" collapsed to one entry
- Total tags reduced from 10 to ~7

- [ ] **Step 4: Commit**

```bash
git add scripts/normalize_nodes.py data/artists/
git commit -m "fix: normalize tags across all 20 artist nodes, remove duplicates"
```

---

## Phase 2: Album Tag Enrichment

### Task 3: Add album tag fetching to lastfm.py

**Files:**
- Modify: `scripts/lastfm.py`
- Test: `tests/test_lastfm.py`

Add functions to fetch top albums and album-level tags. These supplement the existing `fetch_top_tags` function.

- [ ] **Step 1: Write integration tests**

Create `tests/test_lastfm.py`:

```python
"""Integration tests for Last.fm API functions (require API key)."""

import os
import pytest
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# Skip all tests if no API key
pytestmark = pytest.mark.skipif(
    not os.getenv("LASTFM_API_KEY"),
    reason="LASTFM_API_KEY not set"
)

from scripts.lastfm import fetch_top_tags, fetch_top_albums, fetch_album_tags


def test_fetch_top_tags_returns_list():
    tags = fetch_top_tags("Radiohead")
    assert isinstance(tags, list)
    assert len(tags) > 0
    assert all(isinstance(t, str) for t in tags)


def test_fetch_top_albums_returns_list():
    albums = fetch_top_albums("Radiohead", limit=3)
    assert isinstance(albums, list)
    assert len(albums) > 0
    assert len(albums) <= 3
    assert all(isinstance(a, str) for a in albums)


def test_fetch_album_tags_returns_list_with_counts():
    tags = fetch_album_tags("Radiohead", "OK Computer")
    assert isinstance(tags, list)
    assert len(tags) > 0
    # Each entry is (tag_name, count)
    assert all(isinstance(t, tuple) and len(t) == 2 for t in tags)
    assert all(isinstance(t[0], str) and isinstance(t[1], int) for t in tags)


def test_fetch_album_tags_unknown_album():
    tags = fetch_album_tags("Radiohead", "This Album Does Not Exist 12345")
    assert tags == []
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_lastfm.py -v
```

Expected: ImportError on `fetch_top_albums` and `fetch_album_tags` (not yet defined).

- [ ] **Step 3: Add the new functions to lastfm.py**

Add to `scripts/lastfm.py`, below the existing `fetch_top_tags` function:

```python
def fetch_top_albums(artist_name: str, limit: int = 5) -> list[str]:
    """Fetch top album names for an artist. Returns a list of album title strings."""
    resp = requests.get(BASE_URL, params={
        "method": "artist.getTopAlbums",
        "artist": artist_name,
        "api_key": API_KEY,
        "format": "json",
        "limit": limit,
    })
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        print(f"Last.fm error fetching albums for '{artist_name}': {data['message']}")
        return []

    albums = data.get("topalbums", {}).get("album", [])
    # Filter out "(null)" or empty names that Last.fm sometimes returns
    return [a["name"] for a in albums if a.get("name") and a["name"] != "(null)"]


def fetch_album_tags(artist_name: str, album_name: str) -> list[tuple[str, int]]:
    """Fetch top tags for a specific album. Returns list of (tag_name, count) tuples."""
    resp = requests.get(BASE_URL, params={
        "method": "album.getTopTags",
        "artist": artist_name,
        "album": album_name,
        "api_key": API_KEY,
        "format": "json",
    })
    resp.raise_for_status()
    data = resp.json()

    if "error" in data:
        return []

    tags_raw = data.get("toptags", {}).get("tag", [])
    return [(t["name"].lower(), int(t.get("count", 0))) for t in tags_raw if int(t.get("count", 0)) > 0]
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_lastfm.py -v
```

Expected: All 4 tests pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/lastfm.py tests/test_lastfm.py
git commit -m "feat: add album tag and top albums fetching to lastfm.py"
```

---

### Task 4: Build the album tag enrichment script

**Files:**
- Create: `scripts/enrich_tags.py`
- Create: `scripts/tag_filter.py`
- Test: `tests/test_tag_filter.py`

This script fetches album-level tags for each artist's top albums, filters noise, normalizes, and merges into the artist node. It saves the original artist-level tags in a `tag_sources` field for provenance.

- [ ] **Step 1: Write tag filter tests**

Create `tests/test_tag_filter.py`:

```python
"""Tests for album tag noise filtering."""

from scripts.tag_filter import is_noise_tag


def test_year_tags():
    assert is_noise_tag("2009") is True
    assert is_noise_tag("1982") is True
    assert is_noise_tag("00s") is True
    assert is_noise_tag("70s") is True
    assert is_noise_tag("best of 2009") is True


def test_gibberish():
    assert is_noise_tag("dbdbdbdbdbdbdbdbdbdbdb") is True
    assert is_noise_tag("4444266662") is True
    assert is_noise_tag("GUSIC") is True  # short all-caps, not a known acronym


def test_known_acronyms_pass():
    assert is_noise_tag("EDM") is False
    assert is_noise_tag("IDM") is False
    assert is_noise_tag("RNB") is False


def test_meta_tags():
    assert is_noise_tag("geotagged") is True
    assert is_noise_tag("venues") is True
    assert is_noise_tag("places") is True
    assert is_noise_tag("vinyl") is True
    assert is_noise_tag("albums i own") is True


def test_valid_tags_pass():
    assert is_noise_tag("jazz rap") is False
    assert is_noise_tag("experimental hip-hop") is False
    assert is_noise_tag("neo-psychedelia") is False
    assert is_noise_tag("psychedelic folk") is False
    assert is_noise_tag("glitch hop") is False
    assert is_noise_tag("atmospheric") is False
    assert is_noise_tag("drumless") is False
    assert is_noise_tag("japanese") is False
    assert is_noise_tag("american") is False
    assert is_noise_tag("80s") is True  # decade tags are noise


def test_album_name_match():
    from scripts.tag_filter import is_noise_tag_for_album
    assert is_noise_tag_for_album("merriweather post pavilion",
                                   album_name="Merriweather Post Pavilion") is True
    assert is_noise_tag_for_album("jazz rap",
                                   album_name="Merriweather Post Pavilion") is False
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_tag_filter.py -v
```

- [ ] **Step 3: Implement tag_filter.py**

Create `scripts/tag_filter.py`:

```python
"""Filter noise tags from album-level Last.fm data."""

import re

# Explicit blocklist for known noise tags
BLOCKLIST = {
    "geotagged", "venues", "places", "vinyl", "albums i own",
    "favorite albums", "favourites", "favourite", "favorites",
    "seen live", "check out", "spotify", "bandcamp",
    "under 2000 listeners", "fixme",
}

# Pattern: pure digits, year-like (4 digits), decade shorthand (70s, 00s),
# "best of YYYY", strings with mostly repeated chars
YEAR_RE = re.compile(r"^\d{4}$")
DECADE_RE = re.compile(r"^\d{2}s$")
BEST_OF_RE = re.compile(r"^best of \d{4}$")
PURE_DIGITS_RE = re.compile(r"^\d+$")
REPEATED_CHARS_RE = re.compile(r"(.)\1{4,}")  # 5+ repeated chars


def is_noise_tag(tag: str) -> bool:
    """Return True if tag is noise (year, gibberish, meta-tag, etc.)."""
    t = tag.strip().lower()

    if t in BLOCKLIST:
        return True

    if YEAR_RE.match(t) or DECADE_RE.match(t):
        return True

    if BEST_OF_RE.match(t) or PURE_DIGITS_RE.match(t):
        return True

    # Gibberish detection: repeated characters or very short all-caps
    if REPEATED_CHARS_RE.search(t):
        return True

    # All caps, short, and NOT a known acronym — likely vandal tag (e.g., "GUSIC")
    KNOWN_ACRONYMS = {"EDM", "IDM", "RNB", "R&B", "DNB", "DnB", "DJ", "MC", "UK", "US"}
    if tag.isupper() and len(tag) <= 8 and " " not in tag and tag not in KNOWN_ACRONYMS:
        return True

    return False


def is_noise_tag_for_album(tag: str, album_name: str) -> bool:
    """Return True if tag is noise, including album-name-as-tag check."""
    if is_noise_tag(tag):
        return True
    # Tag that matches the album name is not a genre descriptor
    if tag.strip().lower() == album_name.strip().lower():
        return True
    return False
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_tag_filter.py -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/tag_filter.py tests/test_tag_filter.py
git commit -m "feat: add tag noise filter for album-level Last.fm tags"
```

- [ ] **Step 6: Write the enrichment script**

Create `scripts/enrich_tags.py`:

```python
"""Enrich artist tag sets with album-level tags from Last.fm.

For each artist:
1. Fetch top N albums
2. Fetch tags for each album
3. Filter noise tags
4. Normalize via canonical synonym map
5. Merge into artist node, saving provenance in tag_sources
"""

import json
import time
from pathlib import Path

from scripts.lastfm import fetch_top_albums, fetch_album_tags
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


def main():
    paths = sorted(ARTISTS_DIR.glob("*.json"))
    print(f"Enriching tags for {len(paths)} artists...\n")

    for path in paths:
        with open(path, encoding="utf-8") as f:
            node = json.load(f)

        before = len(node["tags"])
        node = enrich_artist(node)
        after = len(node["tags"])
        new_tags = after - before

        with open(path, "w", encoding="utf-8") as f:
            json.dump(node, f, indent=2, ensure_ascii=False)

        albums_fetched = len(node.get("tag_sources", {}).get("lastfm_albums", {}))
        print(f"  {node['id']}: {before} -> {after} tags "
              f"(+{new_tags} new from {albums_fetched} albums)")

    print("\nDone. Run `python scripts/compute.py` to rebuild matrices.")


if __name__ == "__main__":
    main()
```

- [ ] **Step 7: Run the enrichment script**

```bash
python scripts/enrich_tags.py
```

Expected: Each artist gains several new tags from album-level data. Watch for:
- Earl Sweatshirt gaining "jazz rap", "abstract hip-hop", "glitch hop"
- Animal Collective gaining "psychedelic folk", "avant-folk", "psychedelic pop"
- Most artists gaining 3-10 new tags

This will take ~2-3 minutes (20 artists * ~6 API calls each * 0.25s rate limit).

- [ ] **Step 8: Spot-check a couple of enriched nodes**

Read `data/artists/earl_sweatshirt.json` and `data/artists/animal_collective.json`. Verify:
- `tags` array is longer and includes album-level subgenres
- `tag_sources.lastfm_artist` contains the original tags
- `tag_sources.lastfm_albums` has per-album tag data
- No obvious noise/vandal tags made it through

- [ ] **Step 9: Commit**

```bash
git add scripts/enrich_tags.py data/artists/
git commit -m "feat: enrich all artist tags with album-level Last.fm data"
```

---

## Phase 3: MusicBrainz Enrichment

### Task 5: Build MusicBrainz tag fetcher

**Files:**
- Create: `scripts/musicbrainz.py`
- Test: `tests/test_musicbrainz.py`

MusicBrainz has a free API (no key needed) with folksonomy tags. Rate limit is 1 request per second. The flow: search for artist by name -> get MBID -> fetch tags.

- [ ] **Step 1: Write integration tests**

Create `tests/test_musicbrainz.py`:

```python
"""Integration tests for MusicBrainz tag fetching."""

import pytest
from scripts.musicbrainz import search_artist_mbid, fetch_mb_tags


def test_search_known_artist():
    mbid = search_artist_mbid("Radiohead")
    assert mbid is not None
    assert isinstance(mbid, str)
    assert len(mbid) == 36  # UUID format


def test_search_unknown_artist():
    mbid = search_artist_mbid("zzzzzz_nonexistent_artist_12345")
    assert mbid is None


def test_fetch_tags_for_known_artist():
    mbid = search_artist_mbid("Radiohead")
    tags = fetch_mb_tags(mbid)
    assert isinstance(tags, list)
    assert len(tags) > 0
    assert all(isinstance(t, str) for t in tags)
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_musicbrainz.py -v
```

- [ ] **Step 3: Implement musicbrainz.py**

Create `scripts/musicbrainz.py`:

```python
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
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_musicbrainz.py -v
```

Note: These tests hit the live MusicBrainz API. They'll take ~3s due to rate limiting.

- [ ] **Step 5: Commit**

```bash
git add scripts/musicbrainz.py tests/test_musicbrainz.py
git commit -m "feat: add MusicBrainz folksonomy tag fetcher"
```

---

### Task 6: Integrate MusicBrainz into the enrichment pipeline

**Files:**
- Modify: `scripts/enrich_tags.py`

Add a `--musicbrainz` flag to the enrichment script that also pulls MB tags and merges them.

- [ ] **Step 1: Add MB enrichment to enrich_tags.py**

Add these imports at the top of `scripts/enrich_tags.py`:

```python
import argparse
from scripts.musicbrainz import search_artist_mbid, fetch_mb_tags
```

Add a new function:

```python
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
```

Update `main()` to accept a `--musicbrainz` flag:

```python
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
```

- [ ] **Step 2: Run with MusicBrainz**

```bash
python scripts/enrich_tags.py --musicbrainz
```

This will take ~4-5 minutes (20 artists * MB rate limit of 1.1s + album API calls).

- [ ] **Step 3: Spot-check enriched nodes**

Verify a couple of artist files now have `tag_sources.musicbrainz` populated and that new MB tags appear in the `tags` array.

- [ ] **Step 4: Commit**

```bash
git add scripts/enrich_tags.py data/artists/
git commit -m "feat: integrate MusicBrainz folksonomy tags into enrichment pipeline"
```

---

## Phase 4: Soft Jaccard

### Task 7: Implement tag-family partial credit in compute.py

**Files:**
- Create: `scripts/tag_similarity.py`
- Test: `tests/test_tag_similarity.py`
- Modify: `scripts/compute.py`

After enrichment, many cross-genre pairs will gain direct tag matches (e.g., "jazz rap" appears for both Earl Sweatshirt and Nujabes). But we still want partial credit for related tags that share a root: "jazz" and "jazz fusion" are clearly related even if they're not identical.

The approach: compute pairwise tag similarity using word overlap between tag strings, then use the best-match score in a soft Jaccard formula.

- [ ] **Step 1: Write tests**

Create `tests/test_tag_similarity.py`:

```python
"""Tests for soft tag similarity."""

from scripts.tag_similarity import tag_pair_similarity, soft_jaccard


def test_identical_tags():
    assert tag_pair_similarity("jazz", "jazz") == 1.0


def test_superset_tags():
    # "jazz fusion" contains "jazz" — should be high similarity
    sim = tag_pair_similarity("jazz", "jazz fusion")
    assert sim > 0.5


def test_unrelated_tags():
    sim = tag_pair_similarity("jazz", "dubstep")
    assert sim == 0.0


def test_partial_overlap():
    sim = tag_pair_similarity("experimental hip-hop", "experimental rock")
    assert 0.0 < sim < 1.0  # share "experimental"


def test_soft_jaccard_identical_sets():
    a = {"rock", "indie", "folk"}
    b = {"rock", "indie", "folk"}
    assert soft_jaccard(a, b) == 1.0


def test_soft_jaccard_disjoint_sets():
    a = {"jazz", "bebop"}
    b = {"dubstep", "edm"}
    assert soft_jaccard(a, b) == 0.0


def test_soft_jaccard_partial_credit():
    a = {"jazz", "jazz fusion"}
    b = {"jazz rap", "hip-hop"}
    score = soft_jaccard(a, b)
    # Should be > 0 because "jazz" and "jazz rap" share a word
    assert score > 0.0


def test_soft_jaccard_exceeds_hard_jaccard():
    a = {"jazz", "experimental"}
    b = {"jazz fusion", "experimental rock"}
    hard = len(a & b) / len(a | b)  # 0.0 — no exact matches
    soft = soft_jaccard(a, b)
    assert soft > hard
```

- [ ] **Step 2: Run tests, verify they fail**

```bash
python -m pytest tests/test_tag_similarity.py -v
```

- [ ] **Step 3: Implement tag_similarity.py**

Create `scripts/tag_similarity.py`:

```python
"""Soft tag similarity using word overlap between tag strings.

Two tags are similar if they share words. "jazz" and "jazz fusion" share
the word "jazz", so they get partial credit. This creates gradient where
standard Jaccard sees binary match/no-match.
"""

import numpy as np


def tag_pair_similarity(tag_a: str, tag_b: str) -> float:
    """Compute similarity between two tag strings using word overlap.

    Returns Jaccard similarity of the word sets within the tag strings.
    "jazz" vs "jazz fusion" -> {"jazz"} & {"jazz", "fusion"} -> 1/2 = 0.5
    """
    words_a = set(tag_a.lower().replace("-", " ").split())
    words_b = set(tag_b.lower().replace("-", " ").split())
    intersection = len(words_a & words_b)
    union = len(words_a | words_b)
    if union == 0:
        return 0.0
    return intersection / union


def soft_jaccard(tags_a: set[str], tags_b: set[str]) -> float:
    """Compute soft Jaccard similarity between two tag sets.

    For each tag in A, find its best match in B. For each tag in B, find
    its best match in A. Average all best-match scores, normalized.

    Falls back to standard Jaccard when tags match exactly.
    Returns 0.0 for empty sets.
    """
    if not tags_a or not tags_b:
        return 0.0

    list_a = list(tags_a)
    list_b = list(tags_b)

    # Best match for each tag in A against all tags in B
    scores_a = []
    for ta in list_a:
        best = max(tag_pair_similarity(ta, tb) for tb in list_b)
        scores_a.append(best)

    # Best match for each tag in B against all tags in A
    scores_b = []
    for tb in list_b:
        best = max(tag_pair_similarity(tb, ta) for ta in list_a)
        scores_b.append(best)

    # Average of all best-match scores, normalized by total tags
    total = sum(scores_a) + sum(scores_b)
    return total / (len(list_a) + len(list_b))


def soft_jaccard_matrix(tag_sets: list[set[str]]) -> np.ndarray:
    """Compute pairwise soft Jaccard similarity matrix."""
    n = len(tag_sets)
    matrix = np.zeros((n, n))
    for i in range(n):
        matrix[i, i] = 1.0
        for j in range(i + 1, n):
            sim = soft_jaccard(tag_sets[i], tag_sets[j])
            matrix[i, j] = sim
            matrix[j, i] = sim
    return matrix
```

- [ ] **Step 4: Run tests, verify they pass**

```bash
python -m pytest tests/test_tag_similarity.py -v
```

- [ ] **Step 5: Commit**

```bash
git add scripts/tag_similarity.py tests/test_tag_similarity.py
git commit -m "feat: add soft Jaccard with word-overlap tag similarity"
```

---

### Task 8: Update compute.py to output both Jaccard variants

**Files:**
- Modify: `scripts/compute.py`

Keep the original (hard) Jaccard for comparison, add soft Jaccard as the new primary tag proximity measure.

- [ ] **Step 1: Update compute.py**

Replace the `main()` function in `scripts/compute.py`:

```python
from scripts.tag_similarity import soft_jaccard_matrix


def main():
    ids, embeddings = load_embeddings()
    print(f"Loaded {len(ids)} embeddings ({embeddings.shape})")

    # Discourse similarity: cosine of embedded profiles
    discourse_sim = cosine_similarity(embeddings)
    np.save(DATA_DIR / "discourse_sim.npy", discourse_sim)
    print(f"Saved discourse similarity matrix: {discourse_sim.shape}")

    # Tag proximity: both hard and soft Jaccard
    tag_sets = load_tags(ids)

    # Hard Jaccard (original)
    tag_prox_hard = jaccard_matrix(tag_sets)
    np.save(DATA_DIR / "tag_prox_hard.npy", tag_prox_hard)
    print(f"Saved hard Jaccard matrix: {tag_prox_hard.shape}")

    # Soft Jaccard (new primary)
    tag_prox = soft_jaccard_matrix(tag_sets)
    np.save(DATA_DIR / "tag_prox.npy", tag_prox)
    print(f"Saved soft Jaccard matrix: {tag_prox.shape}")

    # Quick summary
    n = len(ids)
    num_pairs = n * (n - 1) // 2
    upper = np.triu_indices(n, k=1)
    print(f"\n{num_pairs} unique pairs")
    print(f"Discourse sim  — mean: {discourse_sim[upper].mean():.3f}, "
          f"std: {discourse_sim[upper].std():.3f}")
    print(f"Tag prox (hard)— mean: {tag_prox_hard[upper].mean():.3f}, "
          f"std: {tag_prox_hard[upper].std():.3f}")
    print(f"Tag prox (soft)— mean: {tag_prox[upper].mean():.3f}, "
          f"std: {tag_prox[upper].std():.3f}")
```

- [ ] **Step 2: Run the updated pipeline**

```bash
python scripts/compute.py
```

Expected: Three matrices saved. The soft Jaccard should show a higher mean and wider spread than hard Jaccard.

- [ ] **Step 3: Commit**

```bash
git add scripts/compute.py
git commit -m "feat: compute both hard and soft Jaccard in compute.py"
```

---

## Phase 5: Pipeline Fixes

### Task 9: Save baseline before re-running discovery

**Files:**
- Create: `data/baseline/` directory

Save the current stats and discoveries so we can compare before/after.

- [ ] **Step 1: Save current results as baseline**

```bash
mkdir -p data/baseline
cp data/stats.json data/baseline/stats_v1.json
cp data/discoveries.json data/baseline/discoveries_v1.json
cp data/tag_prox.npy data/baseline/tag_prox_v1.npy
```

- [ ] **Step 2: Commit baseline**

```bash
git add data/baseline/
git commit -m "chore: save v1 baseline results for comparison"
```

---

### Task 10: Fix discover.py — add fourth quadrant, improve threshold handling

**Files:**
- Modify: `scripts/discover.py`

The current discover.py drops the fourth quadrant (low discourse, low tag). Add it. Also, surface pair counts per quadrant so the distribution is visible.

- [ ] **Step 1: Update discover.py**

Replace the entire `main()` function in `scripts/discover.py` with:

```python
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

    # Unrelated: low discourse, low tag
    unrelated = [p for p in pairs if p["discourse"] < d_median and p["tag"] < t_median]
    unrelated.sort(key=lambda p: p["discourse"] + p["tag"])

    # Quadrant distribution
    print(f"\nQuadrant distribution:")
    print(f"  Basilect discoveries (high D, low T): {len(basilect)}")
    print(f"  Deep scene (high D, high T):          {len(deep)}")
    print(f"  Surface only (low D, high T):         {len(surface)}")
    print(f"  Unrelated (low D, low T):             {len(unrelated)}")

    print_list("BASILECT DISCOVERIES (high discourse, low tag)", basilect, names)
    print_list("DEEP SCENE CONNECTIONS (high discourse, high tag)", deep, names)
    print_list("SURFACE-ONLY CONNECTIONS (low discourse, high tag)", surface, names)
    print_list("UNRELATED (low discourse, low tag)", unrelated, names)

    # Save structured output
    output = {
        "num_pairs": len(pairs),
        "thresholds": {"discourse_median": d_median, "tag_median": t_median},
        "basilect": basilect,
        "deep_scene": deep,
        "surface_only": surface,
        "unrelated": unrelated,
    }
    out_path = DATA_DIR / "discoveries.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {out_path}")
```

- [ ] **Step 2: Run discover.py**

```bash
python scripts/discover.py
```

Expected: Four categories now printed. Check that all pairs sum to the total. The quadrant distribution should be more balanced than before (because enriched tags push more pairs above the tag median).

- [ ] **Step 3: Commit**

```bash
git add scripts/discover.py
git commit -m "fix: add fourth quadrant (unrelated) to discover.py output"
```

---

### Task 11: Update stats.py with richer diagnostics

**Files:**
- Modify: `scripts/stats.py`

Add: tag count stats post-enrichment, distribution comparison between hard and soft Jaccard, and a zero-overlap count.

- [ ] **Step 1: Update stats.py**

Replace the `load_data()` function:

```python
def load_data():
    """Load artist IDs and all similarity matrices."""
    with open(DATA_DIR / "embedding_ids.json", encoding="utf-8") as f:
        ids = json.load(f)
    discourse_sim = np.load(DATA_DIR / "discourse_sim.npy")
    tag_prox = np.load(DATA_DIR / "tag_prox.npy")

    tag_prox_hard_path = DATA_DIR / "tag_prox_hard.npy"
    tag_prox_hard = np.load(tag_prox_hard_path) if tag_prox_hard_path.exists() else None

    return ids, discourse_sim, tag_prox, tag_prox_hard
```

Replace the entire `main()` function:

```python
def main():
    ids, discourse_sim, tag_prox, tag_prox_hard = load_data()
    n = len(ids)
    upper = np.triu_indices(n, k=1)
    d_scores = discourse_sim[upper]
    t_scores = tag_prox[upper]
    num_pairs = len(d_scores)

    # Node stats
    tag_counts, confidence_dist = node_stats(ids)
    print("NODE STATS")
    print(f"  Artists: {n}")
    print(f"  Avg tags/node: {np.mean(tag_counts):.1f} "
          f"(min {min(tag_counts)}, max {max(tag_counts)})")
    print(f"  Confidence: {confidence_dist}")

    # Distribution stats
    print(f"\nDISTRIBUTION STATS ({num_pairs} pairs)")
    print(f"  Discourse similarity (D_sim):")
    print(f"    mean={d_scores.mean():.3f}  std={d_scores.std():.3f}  "
          f"min={d_scores.min():.3f}  max={d_scores.max():.3f}")
    print(f"    quartiles: {np.percentile(d_scores, [25, 50, 75])}")

    # Tag proximity (soft Jaccard — primary)
    print(f"  Tag proximity — soft Jaccard (primary):")
    print(f"    mean={t_scores.mean():.3f}  std={t_scores.std():.3f}  "
          f"min={t_scores.min():.3f}  max={t_scores.max():.3f}")
    print(f"    quartiles: {np.percentile(t_scores, [25, 50, 75])}")
    zero_pairs = int(np.sum(t_scores == 0.0))
    print(f"    Zero-overlap pairs: {zero_pairs} / {num_pairs} "
          f"({100 * zero_pairs / num_pairs:.1f}%)")

    # Tag proximity (hard Jaccard — comparison)
    tag_prox_hard_stats = None
    if tag_prox_hard is not None:
        t_hard = tag_prox_hard[upper]
        print(f"  Tag proximity — hard Jaccard (comparison):")
        print(f"    mean={t_hard.mean():.3f}  std={t_hard.std():.3f}  "
              f"min={t_hard.min():.3f}  max={t_hard.max():.3f}")
        hard_zeros = int(np.sum(t_hard == 0.0))
        print(f"    Zero-overlap pairs: {hard_zeros} / {num_pairs} "
              f"({100 * hard_zeros / num_pairs:.1f}%)")
        tag_prox_hard_stats = {
            "mean": round(float(t_hard.mean()), 3),
            "std": round(float(t_hard.std()), 3),
            "min": round(float(t_hard.min()), 3),
            "max": round(float(t_hard.max()), 3),
            "zero_pairs": hard_zeros,
        }

    # Orthogonality test
    pearson_r, pearson_p = sp_stats.pearsonr(d_scores, t_scores)
    spearman_r, spearman_p = sp_stats.spearmanr(d_scores, t_scores)
    print(f"\nORTHOGONALITY TEST")
    print(f"  Pearson:  r={pearson_r:.3f}  (p={pearson_p:.4f})")
    print(f"  Spearman: r={spearman_r:.3f}  (p={spearman_p:.4f})")
    if abs(pearson_r) < 0.3:
        verdict = "orthogonal"
        print(f"  >> The two layers are measuring substantially different things.")
    elif abs(pearson_r) < 0.6:
        verdict = "moderate"
        print(f"  >> Moderate correlation -- some overlap, but the layers carry "
              f"independent signal.")
    else:
        verdict = "correlated"
        print(f"  >> High correlation -- discourse profiles may be restating genre "
              f"info in prose.")

    # Save structured output
    output = {
        "nodes": {
            "count": n,
            "avg_tags": round(float(np.mean(tag_counts)), 1),
            "min_tags": min(tag_counts),
            "max_tags": max(tag_counts),
            "confidence": confidence_dist,
        },
        "distribution": {
            "discourse_sim": {
                "mean": round(float(d_scores.mean()), 3),
                "std": round(float(d_scores.std()), 3),
                "min": round(float(d_scores.min()), 3),
                "max": round(float(d_scores.max()), 3),
            },
            "tag_prox": {
                "mean": round(float(t_scores.mean()), 3),
                "std": round(float(t_scores.std()), 3),
                "min": round(float(t_scores.min()), 3),
                "max": round(float(t_scores.max()), 3),
                "zero_pairs": zero_pairs,
            },
        },
        "orthogonality": {
            "pearson_r": round(pearson_r, 3),
            "pearson_p": round(pearson_p, 4),
            "spearman_r": round(spearman_r, 3),
            "spearman_p": round(spearman_p, 4),
            "verdict": verdict,
        },
    }
    if tag_prox_hard_stats:
        output["distribution"]["tag_prox_hard"] = tag_prox_hard_stats

    out_path = DATA_DIR / "stats.json"
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2)
    print(f"\nSaved to {out_path}")
```

- [ ] **Step 2: Run stats**

```bash
python scripts/stats.py
```

Compare with baseline: key metrics are whether the tag distribution spread improved and whether zero-overlap pairs decreased.

- [ ] **Step 3: Commit**

```bash
git add scripts/stats.py data/stats.json
git commit -m "feat: add enriched tag diagnostics to stats.py"
```

---

## Phase 6: Re-run Full Pipeline & Evaluate

### Task 12: Full pipeline run and comparison

- [ ] **Step 1: Re-embed (optional — only if discourse profiles changed)**

If no discourse profiles were modified, skip this. The embeddings are unchanged.

If you want to upgrade the embedding model while you're here, change `MODEL_NAME` in `scripts/embed.py` from `"all-MiniLM-L6-v2"` to `"all-mpnet-base-v2"` (768-dim, better paragraph encoding). Then:

```bash
python scripts/embed.py
```

- [ ] **Step 2: Recompute matrices**

```bash
python scripts/compute.py
```

- [ ] **Step 3: Run discovery**

```bash
python scripts/discover.py
```

- [ ] **Step 4: Run stats**

```bash
python scripts/stats.py
```

- [ ] **Step 5: Compare with baseline**

Key questions to answer:
1. Did the tag proximity distribution spread? (Compare std, min, max, quartiles)
2. How many zero-overlap pairs remain? (Should be significantly fewer)
3. Did the orthogonality hold? (Pearson/Spearman should still be < 0.3)
4. Do the top basilect discoveries still make musical sense?
5. Did any obviously wrong pairs move into the top rankings?
6. How does the quadrant distribution compare? (Should be more balanced)

Print a comparison:

```bash
python -c "
import json
with open('data/baseline/stats_v1.json') as f: v1 = json.load(f)
with open('data/stats.json') as f: v2 = json.load(f)
print('Tag proximity comparison:')
print(f'  v1: mean={v1[\"distribution\"][\"tag_prox\"][\"mean\"]}, std={v1[\"distribution\"][\"tag_prox\"][\"std\"]}')
print(f'  v2: mean={v2[\"distribution\"][\"tag_prox\"][\"mean\"]}, std={v2[\"distribution\"][\"tag_prox\"][\"std\"]}')
print(f'Orthogonality:')
print(f'  v1: pearson={v1[\"orthogonality\"][\"pearson_r\"]}, verdict={v1[\"orthogonality\"][\"verdict\"]}')
print(f'  v2: pearson={v2[\"orthogonality\"][\"pearson_r\"]}, verdict={v2[\"orthogonality\"][\"verdict\"]}')
"
```

- [ ] **Step 6: Commit results**

```bash
git add data/
git commit -m "results: v2 pipeline run with enriched tags and soft Jaccard"
```

---

## Phase 7: Discourse Quality Bar

### Task 13: Update CLAUDE.md with discourse profile checklist

**Files:**
- Modify: `CLAUDE.md`

This is a writing-process change, not code. Add a quality checklist to the discourse profile writing instructions.

- [ ] **Step 1: Add checklist to CLAUDE.md**

In the "Step 3: Write the discourse profile" section, after the existing writing rules, add:

```markdown
**Quality checklist (every profile should have):**

- [ ] At least one direct quote or near-quote from the artist (grounds the profile in primary material)
- [ ] At least one named specific: a technique, a reference point, a collaborator, or a work that illustrates the philosophy (prevents generic abstraction)
- [ ] At least one contrastive statement: what the artist rejects, avoids, or defines themselves against (contrastive details discriminate better than affirmative descriptions in embedding space)
- [ ] No sentences that could describe a different artist equally well (if a sentence works for anyone, it works for no one)
```

- [ ] **Step 2: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: add discourse profile quality checklist to CLAUDE.md"
```

---

## Phase 8: Consistency & Safety

### Task 14: Add pipeline consistency check

**Files:**
- Create: `scripts/check_pipeline.py`

A simple script that verifies all pipeline artifacts are in sync: same artist set in nodes, embeddings, and matrices.

- [ ] **Step 1: Write the check script**

Create `scripts/check_pipeline.py`:

```python
"""Verify pipeline artifact consistency."""

import json
import sys
from pathlib import Path

import numpy as np

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"


def main():
    errors = []

    # 1. Artist nodes on disk
    node_ids = sorted(p.stem for p in ARTISTS_DIR.glob("*.json"))

    # 2. Embedding IDs
    emb_ids_path = DATA_DIR / "embedding_ids.json"
    if not emb_ids_path.exists():
        errors.append("Missing embedding_ids.json — run embed.py")
    else:
        with open(emb_ids_path, encoding="utf-8") as f:
            emb_ids = json.load(f)
        if emb_ids != node_ids:
            missing = set(node_ids) - set(emb_ids)
            extra = set(emb_ids) - set(node_ids)
            if missing:
                errors.append(f"Artists on disk but not embedded: {missing}")
            if extra:
                errors.append(f"Embedded but no node file: {extra}")

    # 3. Matrix dimensions
    for name in ["discourse_sim.npy", "tag_prox.npy"]:
        path = DATA_DIR / name
        if not path.exists():
            errors.append(f"Missing {name} — run compute.py")
        else:
            matrix = np.load(path)
            expected = len(node_ids)
            if matrix.shape != (expected, expected):
                errors.append(f"{name} is {matrix.shape}, expected ({expected}, {expected}) — run compute.py")

    # 4. Embeddings shape
    emb_path = DATA_DIR / "embeddings.npy"
    if emb_path.exists():
        emb = np.load(emb_path)
        if emb.shape[0] != len(node_ids):
            errors.append(f"embeddings.npy has {emb.shape[0]} rows, expected {len(node_ids)} — run embed.py")

    if errors:
        print("PIPELINE INCONSISTENCY DETECTED:")
        for e in errors:
            print(f"  - {e}")
        sys.exit(1)
    else:
        print(f"Pipeline consistent: {len(node_ids)} artists, all artifacts in sync.")
        sys.exit(0)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Run it**

```bash
python scripts/check_pipeline.py
```

Expected: "Pipeline consistent: 20 artists, all artifacts in sync."

- [ ] **Step 3: Commit**

```bash
git add scripts/check_pipeline.py
git commit -m "feat: add pipeline consistency check script"
```

---

## Task Dependency Order

```
Task 1  (normalize module)
  └─> Task 2  (apply to nodes)
        └─> Task 9  (save baseline) — do this BEFORE enrichment
              └─> Task 3  (album tag fetching)
                    └─> Task 4  (enrichment script + filter)
                          └─> Task 5  (MusicBrainz fetcher)
                                └─> Task 6  (MB integration)
                                      └─> Task 7  (soft Jaccard)
                                            └─> Task 8  (compute.py update)
                                                  └─> Task 10 (discover.py fix)
                                                        └─> Task 11 (stats.py update)
                                                              └─> Task 12 (full pipeline run)

Task 13 (CLAUDE.md update) — independent, do anytime
Task 14 (consistency check) — independent, do anytime
```

**Critical path:** Tasks 1 → 2 → 9 → 3 → 4 → 5 → 6 → 7 → 8 → 10 → 11 → 12

**Important:** Save the baseline (Task 9) AFTER normalizing existing nodes (Task 2) but BEFORE enrichment (Task 4). Note: the baseline `tag_prox.npy` and `stats.json` are from the original v1 pipeline run (pre-normalization tags), since normalization only changes the JSON node files — it does not re-run compute. This means the final comparison in Task 12 shows the full delta from original v1 state to enriched + soft Jaccard.

---

## What This Plan Does NOT Cover

- **Adding new artists beyond the current 20.** Do that after validating the improved pipeline.
- **Embedding model swap.** Noted as optional in Task 12. The current model works; a swap is a one-line change if you want to try it.
- **Faceted discourse extraction** (separating process/intent/tradition into separate embeddings). That's a v3 design decision — evaluate whether the quality checklist alone improves the discourse layer enough first.
- **Visualization.** The numbers are the priority right now.
