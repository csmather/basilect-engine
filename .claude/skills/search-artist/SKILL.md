---
name: search-artist
description: Find interview URLs for a music artist to add to the basilect engine
---

Search for interview URLs for the artist provided as the argument.

## artist_id normalization
Derive `artist_id` from the artist name: lowercase, spaces to underscores, strip punctuation.
- "BadBadNotGood" → `badbadnotgood`
- "Yung Lean" → `yung_lean`
- "clipping." → `clipping`

## What to find
- Interviews where the artist speaks at length in their own words about how or why they make music — not promotional context or biographical background
- Target ≥3 URLs (up to 6), ≤2 per publication, different years where possible
- Text-based only — trafilatura can't scrape video/audio (written transcripts are fine)
- If temporal diversity isn't achievable, report the gap; don't fabricate dates

## What to avoid
- Album reviews, news pieces, quote roundups
- Heavy coverage of a single album cycle across sources
- Paywalled articles
- Any URL from a blocked domain — check `data/blocked_domains.md` before including

## Output
`date` is year only; omit if unknown:
```json
[{ "url": "...", "publication": "The Wire", "date": "2019", "title": "..." }]
```

If `data/artists/{artist_id}/sources.json` already exists, append — don't overwrite, skip duplicates. Create the directory if needed.
