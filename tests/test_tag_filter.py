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
