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
