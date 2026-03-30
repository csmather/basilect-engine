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

---

## Artist node schema

`data/artists/{artist_id}/sources.json` — interview URLs and scraped text
```json
[{ "url": "https://...", "publication": "The Wire", "date": "2019", "title": "...", "text": "..." }]
```

`data/artists/{artist_id}/quotes.json` — extracted quotes and corpus metadata
```json
{
  "quotes": [{ "text": "...", "publication": "...", "url": "...", "date": "..." }],
  "corpus_meta": { "quote_count": 12, "source_count": 4, "date_range": ["2014", "2021"], "corpus_valid": true }
}
```

### corpus_valid thresholds
- ≥5 quotes, ≥3 distinct sources, ≥2 distinct years

---

## Adding a new artist

1. `search {artist}` — find interview URLs
2. `python scripts/scrape.py {artist_id}` — fetch article text
3. `extract {artist_id}` — pull quotes from scraped text
4. Check `corpus_valid` — if false, find more sources and repeat 1–3
5. Run `python scripts/embed.py` → `python scripts/compute.py` → `python scripts/discover.py` when ready (global; run as a batch, not per artist)

---

## Searching for interview URLs

command: `search {artist}`

`artist_id` is derived from the artist name: lowercase, spaces to underscores, strip punctuation. E.g. "BadBadNotGood" → `badbadnotgood`, "Yung Lean" → `yung_lean`, "clipping." → `clipping`

### What to find
- Interviews where the artist speaks at length in their own words about how or why they make music — not promotional context or biographical background
- Target ≥3 URLs (minimum to satisfy corpus_valid downstream); up to 6
- No more than 2 URLs from the same publication
- Different years where possible; if temporal diversity isn't achievable, report the gap to the user in the response only — do not fabricate dates
- Text-based articles only; exclude video and audio-only sources (trafilatura cannot scrape them — written transcripts of audio interviews are fine)
### What to avoid
- Album reviews, news pieces, quote roundups
- Heavy coverage of a single album cycle across sources
- Paywalled articles

### Output format
```json
[{ "url": "https://...", "publication": "The Wire", "date": "2019", "title": "..." }]
```

`date` is year only (e.g. `"2019"`). If the year is unknown, omit the field.

If `sources.json` already exists, append new entries — do not overwrite existing ones, and skip any URLs already present in the file.
Save to `data/artists/{artist_id}/sources.json` (create dir if needed).

### Known limitation: Pitchfork
Anthropic's crawler is blocked by Pitchfork. Do not include Pitchfork URLs in output — even if they appear in search results. Trafilatura can scrape them fine given a direct URL; the user will manually add Pitchfork URLs to sources.json when appropriate.

---

## Extracting quotes from scraped text

command: `extract {artist_id}`

Read scraped text from `data/artists/{artist_id}/sources.json` (entries with a `text` field). If no entries have a `text` field, stop and report that scraping has not been run yet. Extract verbatim quotes; overwrite `data/artists/{artist_id}/quotes.json` (re-extraction is always a full pass over all sources). If extraction yields zero quotes, write an empty quotes.json with `corpus_valid: false` and report the result.

### What to extract
Verbatim quotes where the **target artist** speaks about making music — process, philosophy, influences, or how they position themselves relative to genre, scene, or tradition as a practitioner making choices (not biographical background).

If a quote is split by a journalist interjection — meaning a non-speech description inserted mid-quote (e.g., narrator describing a pause or gesture) — rejoin it into one statement. Do not merge separate quotes from different parts of an article — if it's unclear whether two fragments are one interrupted quote or two distinct ones, include both as separate entries.

Keep the artist's exact wording — including typos, grammatical errors, and transcription artifacts. Do not silently "correct" anything. Strip non-speech editorial insertions like `[laughs]`, `[pause]`, `[gestures around the room]`. Preserve ellipses as-is — do not use them as a split signal. Extract all quotes that match — do not filter by perceived quality.

### What to exclude
- **Interviewer/journalist questions or narrative** — not spoken by the artist
- **Indirect speech** — journalist paraphrase of artist statements (e.g., "He said texture mattered more than melody")
- **Other speakers** — in multi-person interviews, only the target artist
- **Biographical facts without creative content** — tour dates, sales figures, personal life
- **Promotional fluff** — generic hype about upcoming releases

### Speaker attribution
Many articles mix artist quotes with journalist prose. Use context clues to confirm the target artist is speaking:
- Direct quotes in quotation marks attributed to the artist
- Dialogue with speaker labels (e.g., "Bladee:", "B:")
- First-person statements in Q&A format following a question

If it's ambiguous who's speaking, skip it. This conservatism applies to speaker identity only — don't use it as a reason to filter content.

### How to read source text
Do NOT use the Read tool directly on `sources.json` — the embedded text fields are long and will hit token limits. Instead, use Bash to dump the text to a flat file first, then read that file:

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

Then read `/tmp/{artist_id}_sources.txt`. Do not use WebFetch to re-fetch live URLs — use only the stored text.

### Output format
Write `data/artists/{artist_id}/quotes.json` with the schema above. Each quote inherits `publication`, `url`, and `date` from its source entry. If a source has no `date`, omit that field from the quote.

Compute `corpus_meta` (thresholds: ≥5 quotes, ≥3 distinct sources, ≥2 distinct years):
- `quote_count`: total quotes extracted
- `source_count`: distinct source URLs that contributed quotes
- `date_range`: [earliest year, latest year] derived from source publication dates — sources with no date are excluded from the range and do not count toward the ≥2 years threshold
- `corpus_valid`: true if all three thresholds are met

### JSON safety
Quote text often contains double-quote characters. These MUST be escaped as `\"` in the JSON output or the file will be invalid. Example:

```json
{ "text": "We were like \"I don't know if it makes sense.\" But it grew on me." }
```

After writing quotes.json, always validate with:
```bash
python3 -c "import json; json.load(open('data/artists/{artist_id}/quotes.json')); print('valid')"
```

If validation fails, fix the escaping and rewrite — do not leave an invalid file.

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/scrape.py` | Fetch article text via trafilatura |
| `scripts/extract.py` | LEGACY: sentence-transformer probe extraction (fallback only) |
| `scripts/embed.py` | Embed quotes, aggregate per artist via median |
| `scripts/compute.py` | Pairwise cosine similarity matrix |
| `scripts/discover.py` | Surface ranked artist pairs |

---

## Known limitations
- **embed.py is global-only.** Re-embeds all artists every run. Fine for current scale (<50 artists); incremental mode deferred.
- **extract.py is legacy.** Sentence-transformer probe has precision issues (catches journalist voice, wrong speakers). Kept as fallback, NOT primary extraction path.
- **Un-crawlable publications (trafilatura returns no text):** Interview Magazine, Clash Music. Do not include these in sources.json going forward.
## Deferred
- Full list of known un-crawlable URLs
- Sonic validation via MAEST (post-hoc, later phase)
- Specific influence citation extraction from same corpus
- Manual tag/genre proximity layer (removed for now, may return)
- Visualization
- Scaling beyond prototype
