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
