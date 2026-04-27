# NOTES — NTS curator-graph

Working scratchpad. Active design notes and empirical observations. Stable architectural facts live in CLAUDE.md; kanban in TODO.md.

---

## Current pipeline state

```
crawl.py master       → data/master_sitemap.jsonl   (88,310 rows: 1,710 shows + 86,600 episodes)
crawl.py shows        → data/shows.jsonl            (1,709 per-show metadata rows)
crawl.py tracklists   → data/tracklists.jsonl       (86,600 rows, full corpus, 0 errors @ c=10)
crawl.py artists      → data/artist_sitemap.jsonl   (166,704 slug→id rows for canonicalization)

canonicalize.py       → data/canonicalized.jsonl    (86,600 rows: episode → sorted unique artist_ids)
                      → data/unresolved.jsonl       (210,570 distinct unresolved fragments, frequency-ranked)
                      → data/top_pairs.jsonl        (top 2,000 pairs by raw episode co-occurrence)
```

Implementation is sync by default, threaded with `--concurrency N` (effective rate ≈ N/sleep req/s). Full crawl ran clean at concurrency=10.

## Empirical findings on the NTS API

These are the surprises that shaped the implementation:

- **`/shows` paginates only to offset=1008** (HTTP 422 beyond). 1,709 shows total but the API can't surface ~700 of them via pagination. Per-show `/episodes` is similarly lossy for prolific shows (`the-do-you-breakfast-show` has 2,005 episodes). **Workaround**: the master sitemap (`/sitemap.xml.gz`) enumerates everything, including 2012-era episodes that fetch 200 via tracklist when accessed directly.
- **Server hard-caps page size at 12** regardless of requested `limit`. Confirmed up to limit=1000.
- **Artist-page React state (`window._REACT_STATE_`) is paginated/truncated server-side.** `tracks` is capped at 10. `episodesPlayedOn` is empty for prolific residents (Loraine James totalTracks=89 → episodesPlayedOn=0). The "MORE TRACKS" button hits a non-public endpoint inside the minified JS bundle. This is why we crawl tracklists, not artist pages, for play history.
- **No `/api/v2/artists/*` endpoint exists** — every variant returns 400.
- **`residentShowLinks` / `specialShowLinks`** on artist pages use camelCase (`showAlias`/`showName`) inside the array even though sibling fields use snake_case. Field is also empty for some actual residents (Moxie has none despite a long-running Wednesday show). Don't trust as ground truth for curator attribution.
- Tracklist endpoint extra fields not in the CLAUDE.md API table: `offset_estimate`, `duration_estimate` (sibling to `offset`/`duration`).
- **Master sitemap stores aliases as URL-encoded** (extracted from `<loc>` URLs verbatim). Non-ASCII slugs like `coucou-chloé` appear as `coucou-chlo%C3%A9`. Passing the %-encoded form straight to `requests` double-encodes over the wire and 404s. `load_*_from_master` now URL-decodes at read time. Scale: 1 show alias and 145 episode aliases affected.
- **Sitemap also has 1 dup**: `guests` appears twice as a show entry. `load_shows_from_master` dedupes.

## Empirical observations on data quality

- **Episode metadata partially inherits from show metadata.** Most show-level fields (location, moods, intensity, frequency) carry down unchanged. `genres` differs — episodes often pin a more specific subgenre. Twist: 65% of shows have empty show-level `genres` and 58% empty `moods`; for those, episode-level metadata is the *only* genre signal. Affects whether episode-level crawl is worth the 5h cost (deferred).
- **Multi-artist marker rate ≈15.3%** on the full corpus (29,267 / 190,779 strings, 10k sample). `,` 11.5%, ` & ` 3.9%, ft/feat 0.9%, ` x ` 0.5%.
- **Empty-tracklist rate**: 11.4% on the full corpus (9,889 / 86,600). Episodes NTS staff never tracklisted.
- **Same `uid` appears multiple times in the same episode** sometimes — DJs reprise tracks within a set. Real signal, not bug.

## Canonicalization (v1)

Pipeline (`canonicalize.py`):
1. Skip placeholders (`Unknown Artist`, `Excerpt`, `.`, ...).
2. Try full-string slug match against `artist_sitemap.jsonl` (catches "Tyler, the Creator", "Earth, Wind & Fire" without splitting).
3. Comma split, then per fragment: try slug match; fall back to sub-delimiter split (`&`, `ft`, `x`) only if comma-fragment didn't resolve.
4. Article-prefix fallback: `the-x ↔ x`.

Why two-tier (comma first, sub-delimiters only as fallback)? `,` is a hard collaborator boundary. `&`/`ft`/`x` appear inside band names (`Rhythm & Sound`, `Earth, Wind & Fire`). One-tier splitting on `&` would shred `"Rhythm & Sound, Paul St. Hilaire"` into `[Rhythm, Sound, Paul St. Hilaire]` — false-pair-of-the-decade. Caught the first time we ranked the corpus.

**Resolution rate (full corpus, 1.5M strings):** 80.5% resolve to ≥1 NTS artist ID (68.0% full-string + 9.3% clean split + 3.2% partial split). 19.5% fully unresolved.

Unresolved breakdown (top categories from `unresolved.jsonl`):
- Tracklist staff notes (`Excerpt`, `In Heaven Everything Is Fine`, `Recorded By...`).
- Shorthand references (`Eno`, `Janet`, `Beach Boys`) — irreducible without context.
- Special-character mismatches (`A$AP Rocky` → `a-ap-rocky`; NTS uses `asap-rocky`).
- Genuinely-not-on-NTS small artists.

**NTS-data dupes visible at the top of co-occurrence ranking** (same human, two artist pages — not our bug, NTS's):
- `j-dilla ↔ jay-dee` (85 curators)
- `dj-rashad ↔ spinn` (58) vs `dj-rashad ↔ dj-spinn` (86) — DJ Spinn has two pages
- `d-angelo ↔ the-vanguard` (61) — D'Angelo and his band as separate sequential IDs
- `d-angelo ↔ dangelo` — apostrophe-spelling variants

Hand-curated dupes-merge table would clean these. Deferred until the canonicalization-refinement pass.

## Top co-occurrence pairs (v1, plain unweighted)

`data/top_pairs.jsonl`. Top by curator (show) recurrence:

```
103 shows  alice-coltrane ↔ pharoah-sanders   (spiritual jazz canon)
 87 shows  madlib ↔ freddie-gibbs              (collab pair, validates cross-curator)
 86 shows  dj-rashad ↔ dj-spinn                (footwork)
 86 shows  patrice-rushen ↔ f-byron-clark
 85 shows  future ↔ young-thug                 (modern rap gravity)
 82 shows  oliver-coates ↔ mica-levi           (modern composition)
 80 shows  brian-eno ↔ daniel-lanois           (ambient)
 72 shows  dean-blunt ↔ joanne-robertson       (Hype Williams orbit)
 68 shows  holger-czukay ↔ jah-wobble          (krautrock × dub)
 66 shows  milton-nascimento ↔ lo-borges       (Clube da Esquina)
```

**Calibration on collaborator pairs.** Some top pairs are duo/collaborator clusters (Sam Gendel↔Sam Wilkes, Dean Blunt↔Joanne Robertson, Madlib↔Freddie Gibbs). Treat as expected, not noise — same pattern as music-map.com surfacing aliases/partners next to the center artist. The cross-curator dimension still validates the connection; we just don't claim it's a *non-obvious* discovery for these pairs.

## Curator/host attribution

NTS doesn't expose a structured host field on shows or episodes. Host is encoded in the show name by convention (`"100 Elements w/ YL"`).

For v1 co-occurrence, **`show_alias` IS the curator key** — one show alias = one curatorial voice. No mapping to artist IDs needed in the algorithm. If we ever want a human-readable host name for output display, it's a 5-line post-process on the show `name` string. Not crawl work.

## Why not Discogs as canonical key (yet)

`discogsUrl` on artist-page tracks points to a Discogs *release*, not artist. Resolving release→artist is one extra Discogs API hop per track. NTS's own integer ID is stable, in the URL, and the natural inverse of the artists sitemap. Discogs joins matter only when we eventually pull external evidence streams — premature for v1.

## Design forks already resolved

- **Crawl direction**: started artist-first → pivoted to episode-first via master sitemap. Reason: artist React state is paginated/truncated; episode-first is full-coverage and the artists sitemap solves canonicalization for free.
- **Canonical artist key**: NTS integer ID, not Discogs.
- **Curator attribution depth**: just `show_alias`. No name/ID resolution.
- **Storage**: JSONL append-only for now. SQLite migration once shape stabilizes.
- **Pagination workaround**: master sitemap as crawl frontier, not `/api/v2/shows` pagination.
- **Concurrency**: ThreadPoolExecutor + shared `requests.Session`. Defaults to sync (concurrency=1); scale tested at 5.

## Open questions (deferred)

- **Co-occurrence weighting**: per-episode intent-density (compilation/series vs recurring resident vs guest), per-artist normalization (dampen prolific journeymen — the Drake/Future/Thug cluster naturally inflates).
- **Show-set scope**: filter to higher-intent-density show types for v1, or use the full corpus?
- **Episode metadata trigger**: load-bearing for the 65%-of-shows-with-empty-show-genres question. Crawl when genre is needed for diagnostic spot-checks, time-windowed analyses, or per-episode thesis text.

## Reference: ribenamaplesyrup/nts-scraper

Dead since March 2023. Pre-`/api/v2`, pre-`_REACT_STATE_`. Selenium + BeautifulSoup. Their similarity proxy is shared record labels between shows, not artist co-occurrence — different graph entirely. Independently hit our canonicalization wall (had to visit artist pages for Discogs URLs, but didn't resolve artist identity — only `release.labels[0].url`). Confirms our direction without anything to copy.

## Orphaned data files

- `data/artists.jsonl` — 100 trimmed rows from the abandoned artist-first sample. Different shape from anything the new crawler produces. Safe to delete.
- `data/diagnostics.html` — old artist-page HTML diagnostic from the pre-pivot phase. Safe to delete.
