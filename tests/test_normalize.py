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
