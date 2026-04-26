# TODO

Kanban. Keep short.

## Now — v1 NTS co-occurrence pipeline

Plain co-occurrence first. No thesis-fit, no LLM scoring. Goal: a working ranked-pairs output from crawled NTS data.

- [ ] Brainstorm v1 scope and design before building. Open questions:
  - **Crawl direction**: episode-first (~60–80k fetches, full corpus, natural for co-occurrence) vs artist-first (~200k fetches, gives Discogs IDs as bonus). Probably episode-first with a backfill artist-pass for canonicalization.
  - **Co-occurrence weighting**: per-episode intent-density (compilation/resident/guest weighting), per-artist normalization (frequent-collaborator dampening so prolific cross-genre journeymen don't dominate)
  - **Storage**: SQLite for relational shape (episodes, tracks, artists, co-occurrences) probably right; revisit
  - **Scope cut for v1**: which shows to include? All 1709, or filter to higher-intent-density show types first?
- [ ] Stand up crawler: episode-first, polite rate (≤1 req/s), resumable (state checkpointing)
- [ ] Discogs URL extraction → canonical artist keys
- [ ] Co-occurrence matrix + ranking → `discoveries.json`

## Later

- [ ] Thesis-fit layer (LLM reads episode description, scores artist fit) — v2 enrichment
- [ ] Other curator substrates if NTS validates: Discogs compilations, Bandcamp Daily mixes, RA "In Residence", artist self-curation (year-end lists, guest mixes)
- [ ] Aesthetic-axis projection as eventual ranking layer; curator-graph becomes one evidence stream

## Parked (far-off, see CLAUDE.md)

- Discourse axis revival — would feed axis layer alongside curator-graph; the `discourse` branch has the prior pipeline, validated 25-artist corpus, A-investigation findings
- Sampling lineage (WhoSampled, Spotify-acquired Nov 2025, access risk)
- Listening-trajectory geometry from Last.fm scrobble sequences
- Audio→LLM-listening as input to axis layer (frontier multimodal, expensive per call)

## Rejected

- Collaborative filtering / play-count-based similarity
- Genre supervision in ranking (GATSY 2024)
- Claude-authored prose summaries, curated tag vocabularies
- NTS `/search` endpoint (broken as of 2026-04-26 — empty results for every query, every param, every Accept header)

## Bugs

(none yet)

## Done

(empty — fresh start)
