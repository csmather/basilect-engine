---
name: extract-artist
description: Extract verbatim artist quotes from scraped sources for a given artist_id
---

Extract quotes for the artist_id provided as the argument.

## How to read source text
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

Then read `/tmp/{artist_id}_sources.txt`. If no sources have a `text` field, stop and report that scraping hasn't run yet.

Do not WebFetch live URLs — use stored text only.

## What to extract
Verbatim quotes where the **target artist** speaks about making music — process, philosophy, influences, or how they position themselves as a practitioner making choices (not biographical background).

- Keep exact wording — typos, grammatical errors, transcription artifacts. Do not correct anything.
- Strip non-speech insertions: `[laughs]`, `[pause]`, `[gestures around the room]`.
- Preserve ellipses — don't use them as a split signal.
- If a quote is interrupted by a journalist interjection, rejoin it. Don't merge separate quotes from different parts of an article; if unclear, include both as separate entries.
- Extract all matches — don't filter by quality.

**Exclude:** interviewer questions/narrative, indirect speech (journalist paraphrase), other speakers in multi-person interviews, biographical facts without creative content, promotional fluff.

**Speaker attribution:** confirm target artist is speaking via quotation marks with attribution, speaker labels (e.g., "Bladee:", "B:"), or Q&A context. Skip if ambiguous — but this conservatism applies to *speaker identity only*.

## Output format
Overwrite `data/artists/{artist_id}/quotes.json` on every run (always a full pass). If zero quotes found, write an empty quotes.json with `corpus_valid: false`.

Each quote inherits `publication`, `url`, `date` from its source (omit `date` if absent from source). Compute `corpus_meta`:
- `quote_count`: total quotes extracted
- `source_count`: distinct source URLs that contributed quotes
- `date_range`: [earliest year, latest year] from dated sources only — undated sources excluded from range and don't count toward the ≥2 years threshold
- `corpus_valid`: true if all three thresholds met (≥5 quotes, ≥3 distinct sources, ≥2 distinct years)

Internal double-quotes must be escaped as `\"`:
```json
{ "text": "We were like \"I don't know if it makes sense.\" But it grew on me." }
```

Validate after writing:
```bash
python3 -c "import json; json.load(open('data/artists/{artist_id}/quotes.json')); print('valid')"
```
Fix and rewrite if invalid — do not leave a broken file.
