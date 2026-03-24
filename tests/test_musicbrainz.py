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
