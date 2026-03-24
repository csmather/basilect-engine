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
