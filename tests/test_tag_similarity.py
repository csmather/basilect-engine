"""Tests for soft tag similarity."""

from scripts.tag_similarity import tag_pair_similarity, soft_jaccard


def test_identical_tags():
    assert tag_pair_similarity("jazz", "jazz") == 1.0


def test_superset_tags():
    # "jazz fusion" contains "jazz" — should be high similarity
    sim = tag_pair_similarity("jazz", "jazz fusion")
    assert sim >= 0.5


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
