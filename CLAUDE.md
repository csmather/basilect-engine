# Basilect Engine

A music artist similarity engine that surfaces non-obvious connections 
between artists based on how they talk about making music. Two artists 
are "basilect-connected" if their creative philosophy is similar but 
their genre/scene is not.

The signal is artist self-discourse: verbatim quotes from interviews, 
embedded and compared. No critic voice, no Claude-authored summaries.

---

## Pipeline

1. **Search** — Claude finds interview URLs per artist (see below)
2. **Scrape** — trafilatura extracts clean article text from URLs
3. **Extract** — sentence-transformer probe pulls relevant quotes
4. **Embed** — quotes embedded and aggregated per artist
5. **Compute** — pairwise cosine similarity across artists
6. **Discover** — surface high-similarity, low-proximity pairs

---

## Artist node schema

`data/artists/{artist_id}/quotes.json`
```json
{
  "quotes": [
    { "text": "...", "publication": "...", "url": "...", "date": "..." }
  ],
  "corpus_meta": {
    "quote_count": 12,
    "source_count": 4,
    "date_range": ["2014", "2021"],
    "corpus_valid": true
  }
}
```

### corpus_valid thresholds
- ≥5 quotes
- ≥3 distinct sources
- ≥2 distinct years

---

## Adding a new artist

1. Run the search step to get URLs (see below)
2. Run `scripts/scrape.py` to fetch article text
3. Run `scripts/extract.py` to pull quotes into the node
4. Check `corpus_valid` — if false, find more sources
5. Run `scripts/embed.py` → `compute.py` → `discover.py`

---

## Searching for interview URLs

command: `search artist`
Claude's only role in the pipeline is finding interview URLs.

### What to find
- Long-form interviews where the artist speaks extensively
- Covers creative process, philosophy, influences, or intent
- 2–6 URLs per artist
- Different publications and different years where possible

### What to avoid
- Album reviews, news pieces, quote roundups
- Heavy coverage of a single album cycle across sources
- Paywalled articles

### Output format
```json
[
  {
    "url": "https://...",
    "publication": "The Wire",
    "date": "2019",
    "title": "..."
  }
]
```

Save results to `data/artists/{artist_id}/sources.json` (create dir if needed). This is what `scrape.py` reads from.

### What Claude does NOT do
- Judge quote quality or relevance (the pipeline handles this)
- Summarize or paraphrase anything
- Write any content that goes into artist nodes

## Quote extraction probe

The probe string used in `scripts/extract.py` to score sentences:

`"musician describing their creative process, philosophy, and approach to making music"`

Threshold: 0.3 (cosine similarity). Minimum sentence length: 8 words.

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/scrape.py` | Fetch article text via trafilatura |
| `scripts/extract.py` | Pull quotes via sentence-transformer probe |
| `scripts/embed.py` | Embed quotes, aggregate per artist |
| `scripts/compute.py` | Pairwise cosine similarity matrix |
| `scripts/discover.py` | Surface high-sim low-proximity pairs |
| `scripts/stats.py` | Corpus health + orthogonality stats |

---

## Deferred

- Sonic validation via MAEST (post-hoc, later phase)
- Influence citation extraction from same corpus
- Scaling beyond 20 artists
- Visualization
