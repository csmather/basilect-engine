# Basilect Engine
A music artist similarity engine that surfaces non-obvious connections between artists based on how they talk about making music. Two artists are "basilect-connected" if their creative philosophy is similar but their genre/scene is not.
The signal is artist self-discourse: verbatim quotes from interviews, embedded and compared. No critic voice, no Claude-authored summaries.

---

## Pipeline

1. **Search** — Claude finds interview URLs per artist (see below)
2. **Scrape** — `scripts/scrape.py` fetches article text via trafilatura
3. **Extract** — Claude pulls verbatim artist quotes from scraped text (see below)
4. **Embed** — `scripts/embed.py` embeds quotes and aggregates per artist
5. **Compute** — `scripts/compute.py` builds raw + count-adjusted similarity matrices
6. **Discover** — `scripts/discover.py` surfaces ranked artist pairs (ranked on adjusted score)

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

`corpus_valid` is a data-quality flag, not a usability flag. An artist failing it isn't excluded from the pipeline — it just means the source metadata is thin (often missing dates that weren't in the scraped articles).

---

## Adding a new artist

1. `/search-artist {artist}` — find interview URLs
2. `python scripts/scrape.py {artist_id}` — fetch article text
3. `/extract-artist {artist_id}` — pull quotes from scraped text
4. Check `corpus_valid`
5. `/run-pipeline` when ready — runs embed → compute → discover globally

---

## Searching for interview URLs

command: `/search-artist {artist}`

Full instructions: `.claude/skills/search-artist/SKILL.md`

`artist_id`: lowercase, spaces to underscores, strip punctuation; e.g. "Artist Name!"->"artist_name"

---

## Extracting quotes from scraped text

command: `/extract-artist {artist_id}`

Full instructions: `.claude/skills/extract-artist/SKILL.md`

---

## Scripts

| Script | Purpose |
|---|---|
| `scripts/scrape.py` | Fetch article text via trafilatura |
| `scripts/extract.py` | LEGACY: sentence-transformer probe (fallback only; precision issues) |
| `scripts/embed.py` | Embed quotes, aggregate per artist via median |
| `scripts/compute.py` | Raw cosine + count-adjusted similarity matrix (sparsity-artifact correction, fit in `data/similarity_fit.json`) |
| `scripts/discover.py` | Surface ranked artist pairs — ranked on adjusted, raw kept as `score_raw` |
| `scripts/diagnose.py` | D-phase audit (sparsity / stability / spread) → `data/diagnostics.html` |

---

## Known limitations
- **embed.py is global-only.** Re-embeds all artists every run. Fine for current scale (<50 artists).
- **extract.py is legacy.** Sentence-transformer probe has precision issues (catches journalist voice, wrong speakers). Kept as fallback, not primary path.
- **Un-crawlable domains:** See `data/blocked_domains.md`.

---

## Deferred
- Sonic validation via MAEST (post-hoc, later phase)
- Specific influence citation extraction from same corpus
- Manual tag/genre proximity layer (removed for now, may return)
- Visualization
- Scaling beyond prototype

---

## Meta
`docs/TODO.md` is MY kanban/todo list for status + goals at a glance.
`docs/NOTES.md` is YOUR scratchpad for details, state, and reference.

## Working notes (carried from prior sessions)

**Dead / pre-internet artists.** Flag deceased or pre-web artists at the start of `/search-artist` before running. Their interviews are audio, scanned print, or paywalled — not trafilatura-scrapeable. Burned a full search on Coltrane learning this.

**Extraction runs in the main conversation.** Use the bash dump pattern in CLAUDE.md, no subagents. Same model as claude.ai; bad batches were subagent failures (live WebFetch, mangled JSON, silently rewritten quotes), not model quality.

**The Motegi Clause.** A quote counts as self-discourse iff the speaker is inside the creative collective. Keep: target artist first-person, bandmate first-person speaking as the band (even about other members). Drop: external-collaborator third-person prose, even when relaying the artist's words (precedent: Shing02 on Nujabes was excluded). One question — is the speaker inside the collective? Yes keep, no drop.

**No quote-count minimum.** Underground artists with thin corpora are the core use case. Sparsity bias is corrected in `compute.py` via `log(min(count_i, count_j))` residualization → `similarity_adjusted.npy`; never via exclusion. If score quality issues arise, propose encoder/aggregation/CI fixes — don't re-raise exclusion. `corpus_valid` is metadata-completeness, not a gate.

**Fork at `~/projects/baseng-fork`** (`tangyraccoon/basilect-engine`, branch `v5`) has 672 scraped artists. Raw `sources.json` is clean trafilatura — reusable to skip the slow scrape step. Fork `quotes.json` is ~25% polluted (Haiku at scale, no review) — re-extract with main pipeline if cherry-picking, never copy. Never copy `critic_quotes.json`, `influences.json`, `tags.json`, fork `corpus_meta`. Fork `quotes.json` schema lacks `url`.
