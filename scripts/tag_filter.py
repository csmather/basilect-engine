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

    # Gibberish detection: consecutive repeated chars, or alternating pattern (low unique chars)
    if REPEATED_CHARS_RE.search(t):
        return True
    if len(t) >= 8 and len(set(t.replace(" ", "").replace("-", ""))) <= 3:
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
