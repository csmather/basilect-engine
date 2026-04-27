# TODO

Kanban. Keep short.

## Now — explore the v1 corpus

Pipeline shipped end-to-end (crawl → canonicalize → rank). 86,600 episodes, 11M pairs, top 2,000 in `data/top_pairs.jsonl`. Before refining anything, sit with the data.

- [ ] Data analysis + visualization. Load `top_pairs.jsonl` and `canonicalized.jsonl` in a notebook. Things worth looking at: pair-rank distribution, per-artist degree distribution, show-recurrence histogram, scene clusters via simple graph layout, sanity-check pairs at various rank tiers (top-10, 100, 1000, 10000), genre-diversity of co-occurring pairs (using `shows.jsonl` show-level genres as diagnostic).

## Next — dedicated session

- [ ] Canonicalization refinement. Hand-curated NTS-dupes merge table (j-dilla/jay-dee, dj-spinn/spinn, d-angelo/dangelo, d-angelo/the-vanguard band-name pages). Special-character normalization (`A$AP Rocky` → `asap-rocky`, abbreviations like `M.I.A.`). Possibly an article/punctuation-tolerant fuzzy fallback. Worth a focused session because it touches the unresolved-fragment review (210k distinct fragments in `unresolved.jsonl`) and the dupes table needs a manual eye on top-N pairs.

## Later

- [ ] Co-occurrence weighting: per-episode intent-density (compilation/themed mix vs grab-bag resident set), per-artist normalization (dampen prolific journeymen — Drake/Future/Thug cluster inflates). Open question pre-implementation.
- [ ] Storage migration to SQLite. The 11M-pair counter sits in RAM fine for v1 but interactive querying would benefit from indexed storage.
- [ ] Episode-level metadata enrichment (`/api/v2/shows/{a}/episodes/{ea}` × 86k ≈ 5 hr). Becomes load-bearing for the ~65% of shows with empty show-level `genres`. Hold until a concrete use case (time-windowed analyses, per-episode thesis scoring, or genre-diversity diagnostic).
- [ ] Thesis-fit layer (LLM reads episode/show description, scores artist fit) — v2 enrichment.
- [ ] Other curator substrates if NTS validates: Discogs compilations, Bandcamp Daily mixes, RA "In Residence", artist self-curation (year-end lists, guest mixes).
- [ ] Aesthetic-axis projection as eventual ranking layer; curator-graph becomes one evidence stream.

## Parked (far-off, see CLAUDE.md)

- Discourse axis revival — would feed axis layer alongside curator-graph; the `discourse` branch has the prior pipeline, validated 25-artist corpus, A-investigation findings.
- Sampling lineage (WhoSampled, Spotify-acquired Nov 2025, access risk).
- Listening-trajectory geometry from Last.fm scrobble sequences.
- Audio→LLM-listening as input to axis layer (frontier multimodal, expensive per call).

## Rejected

- Collaborative filtering / play-count-based similarity.
- Genre supervision in ranking (GATSY 2024).
- Claude-authored prose summaries, curated tag vocabularies.
- NTS `/search` endpoint (broken as of 2026-04-26 — empty results for every query, every param, every Accept header).
- Artist-first crawl (artist React state is paginated/truncated server-side; can't get full play history without reverse-engineering the load-more endpoint inside the JS bundle).
- Discogs-as-canonical-key for v1 (`discogsUrl` is per-release, not per-artist; resolution needs extra hops we don't pay yet).

## Bugs

(none open)

## Done

- Master sitemap walker (`crawl.py master`) — enumerates 1,710 shows + 86,600 episodes from `https://www.nts.live/sitemap.xml.gz`. Bypasses the `/shows` offset=1008 cap.
- Artists sitemap walker (`crawl.py artists`) — 166,704 artists into `data/artist_sitemap.jsonl` for canonicalization.
- Tracklist crawler (`crawl.py tracklists`) — full corpus (86,600 episodes, 0 errors @ concurrency=10).
- Show metadata crawler (`crawl.py shows`) — 1,709 shows into `data/shows.jsonl`. Full coverage verified.
- Canonicalization (`canonicalize.py`) — two-tier comma/sub-delimiter splitter + article-prefix fallback. 80.5% resolution on 1.5M strings. Outputs `canonicalized.jsonl`, `unresolved.jsonl`, `top_pairs.jsonl`.
