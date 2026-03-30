# Basilect Engine
A music artist similarity engine that surfaces non-obvious connections between artists based on how they talk about making music. Two artists are "basilect-connected" if their creative philosophy is similar but their genre/scene is not.
The signal is artist self-discourse: verbatim quotes from interviews, embedded and compared. No critic voice, no Claude-authored summaries.

---

## Pipeline

1. **Search** — Claude finds interview URLs per artist (see below)
2. **Scrape** — `scripts/scrape.py` fetches article text via trafilatura
3. **Extract** — Claude pulls verbatim artist quotes from scraped text (see below)
4. **Embed** — `scripts/embed.py` embeds quotes and aggregates per artist
5. **Compute** — `scripts/compute.py` builds pairwise cosine similarity matrix
6. **Discover** — `scripts/discover.py` surfaces ranked artist pairs

Steps 1–3 run **per artist**. Steps 4–6 run **globally** across all artists.

**Prototype rule: do not delegate steps 1–3 to subagents.** Run them directly in the main conversation — one artist at a time. Subagents have been unreliable (WebFetching live URLs instead of using stored text, writing invalid JSON, silently correcting verbatim quotes).

---

## Artist node schema

`data/artists/{artist_id}/sources.json`
```json
[{ "url": "...", "publication": "The Wire", "date": "2019", "title": "...", "text": "..." }]
```

`data/artists/{artist_id}/quotes.json`
```json
{
  "quotes": [{ "text": "...", "publication": "...", "url": "...", "date": "..." }],
  "corpus_meta": { "quote_count": 12, "source_count": 4, "date_range": ["2014", "2021"], "corpus_valid": true }
}
```

**corpus_valid thresholds:** ≥5 quotes, ≥3 distinct sources, ≥2 distinct years

---

## Adding a new artist

1. `search {artist}` — find interview URLs
2. `python scripts/scrape.py {artist_id}` — fetch article text
3. `extract {artist_id}` — pull quotes from scraped text
4. Check `corpus_valid` — if false, find more sources and repeat 1–3
5. Run `python scripts/embed.py` → `python scripts/compute.py` → `python scripts/discover.py` when ready (global; run as a batch)

---

## Searching for interview URLs

command: `search {artist}`

`artist_id`: lowercase, spaces to underscores, strip punctuation. E.g. "BadBadNotGood" → `badbadnotgood`, "Yung Lean" → `yung_lean`, "clipping." → `clipping`

Target ≥3 URLs (up to 6), ≤2 per publication, different years where possible. Text-based only — trafilatura can't scrape video/audio (written transcripts are fine). If temporal diversity isn't achievable, report the gap; don't fabricate dates.

**Avoid:** album reviews, news pieces, quote roundups, single-album-cycle concentration, paywalled articles.

**Pitchfork:** Anthropic's crawler is blocked — don't include Pitchfork URLs. User will add manually; trafilatura can scrape them fine from a direct URL.

Output (`date` is year only; omit if unknown):
```json
[{ "url": "...", "publication": "The Wire", "date": "2019", "title": "..." }]
```

If `sources.json` already exists, append — don't overwrite, skip duplicates. Save to `data/artists/{artist_id}/sources.json` (create dir if needed).

---

## Extracting quotes from scraped text

command: `extract {artist_id}`

Read from `sources.json` entries with a `text` field. If none, stop and report scraping hasn't run. Overwrite `quotes.json` on every extraction (always a full pass). If zero quotes, write empty quotes.json with `corpus_valid: false`.

### What to extract
Verbatim quotes where the **target artist** speaks about making music — process, philosophy, influences, or how they position themselves as a practitioner (not biographical background).

- Keep exact wording — typos, grammatical errors, transcription artifacts. Do not correct anything.
- Strip non-speech insertions: `[laughs]`, `[pause]`, `[gestures around the room]`.
- Preserve ellipses — don't use them as a split signal.
- If a quote is interrupted by a journalist interjection (e.g., narrator describing a gesture), rejoin it. Don't merge separate quotes from different parts of an article; if unclear, include both as separate entries.
- Extract all matches — don't filter by quality.

**Exclude:** interviewer questions/narrative, indirect speech (journalist paraphrase), other speakers in multi-person interviews, biographical facts without creative content, promotional fluff.

**Speaker attribution:** confirm target artist is speaking via quotation marks with attribution, speaker labels (e.g., "Bladee:", "B:"), or Q&A context. Skip if ambiguous — but this conservatism applies to *speaker identity only*.

### How to read source text
Do NOT use the Read tool on `sources.json` — embedded text fields will hit token limits. Dump to a flat file first:

```bash
python3 -c "
import json
with open('data/artists/{artist_id}/sources.json') as f:
    sources = json.load(f)
for s in sources:
    if s.get('text'):
        print(f'=== SOURCE | {s[\"publication\"]} | {s.get(\"date\",\"\")} ===')
        print(s['url'])
        print(s['text'])
        print()
" > /tmp/{artist_id}_sources.txt
```

Then read `/tmp/{artist_id}_sources.txt`. Do not WebFetch live URLs — use stored text only.

### Output format
Each quote inherits `publication`, `url`, `date` from its source (omit `date` if absent). Compute `corpus_meta`:
- `quote_count`, `source_count` (distinct URLs), `date_range` [earliest, latest] from dated sources only
- `corpus_valid`: true if all thresholds met (undated sources don't count toward the 2-year threshold)

Internal double-quotes must be escaped as `\"`:
```json
{ "text": "We were like \"I don't know if it makes sense.\" But it grew on me." }
```

Validate after writing:
```bash
python3 -c "import json; json.load(open('data/artists/{artist_id}/quotes.json')); print('valid')"
```
Fix and rewrite if invalid — do not leave a broken file.

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/scrape.py` | Fetch article text via trafilatura |
| `scripts/extract.py` | LEGACY: sentence-transformer probe (fallback only; precision issues) |
| `scripts/embed.py` | Embed quotes, aggregate per artist via median |
| `scripts/compute.py` | Pairwise cosine similarity matrix |
| `scripts/discover.py` | Surface ranked artist pairs |

---

## Known limitations
- **embed.py is global-only.** Re-embeds all artists every run. Fine for current scale (<50 artists).
- **extract.py is legacy.** Catches journalist voice and wrong speakers. Kept as fallback, not primary path.
- **Un-crawlable publications:** Interview Magazine, Clash Music. Don't add to sources.json.

---

## Deferred
- Sonic validation via MAEST (post-hoc, later phase)
- Specific influence citation extraction from same corpus
- Manual tag/genre proximity layer (removed for now, may return)
- Visualization
- Scaling beyond prototype
