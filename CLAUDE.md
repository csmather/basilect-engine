# Basilect Engine — NTS curator-graph

A music artist similarity engine. Goal: surface non-obvious connections between musicians by mining intent-dense curatorial artifacts, starting with NTS Radio tracklists.

Two artists are basilect-connected if they recur together in the choices of curators with different scenes, biases, or eras. Curated co-occurrence (a single mind chose to put A and B in the same hour of music) is structurally different from algorithmic co-occurrence (a million low-effort playlists averaged together) and orthogonal to genre tags / collaboration graphs.

---

## Pipeline (v1 — co-occurrence only)

1. **Crawl** (`crawl.py`) — enumerate shows + episodes from master sitemap, fetch tracklists via `/api/v2`. Side phases: `shows` (per-show metadata) and `artists` (slug→id sitemap). Full corpus crawled: 86,600 episodes, 1,709 shows, 0 errors @ concurrency=10.
2. **Canonicalize** (`canonicalize.py`) — free-text artist strings → NTS integer artist IDs. Two-tier split + full-string-match-first + article-prefix fallback. 80.5% resolution on 1.5M strings.
3. **Compute** — raw unweighted co-occurrence pair counts. 11M distinct pairs across 147k artists. Top 2,000 saved to `data/top_pairs.jsonl`.
4. **Discover** — rank by `shows` (distinct curator count) primarily, `eps` (raw count) secondarily.

V1 is plain co-occurrence. No thesis-fit, no LLM scoring, no aesthetic-axis layer, no per-episode intent-density weighting — deferred.

---

## NTS API quick reference

Base: `https://www.nts.live/api/v2`. HAL-style, no auth, robots permits all (`User-Agent: * Allow: /`). Crawl politely anyway (≤1 req/s default).

| Endpoint | What it returns |
|---|---|
| `/shows` | All shows, paginated (count: 1709, default limit 12) |
| `/shows/{alias}` | Show metadata (name, description, host, genres) |
| `/shows/{alias}/episodes` | Episodes per show, paginated |
| `/shows/{alias}/episodes/{ep_alias}` | Episode metadata (description, NTS-curated genres, location, mixcloud link, moods, intensity) |
| `/shows/{alias}/episodes/{ep_alias}/tracklist` | Tracklist as separate sub-resource (`artist`, `title`, `uid`, `offset`, `duration`) |
| `/genres` | NTS curated genre taxonomy with structured IDs |
| `/mixtapes` | Themed music-only streams |
| `/collections` | Show collections |
| `/live` | Current broadcast |

**`/search` is broken** as of 2026-04-26 — returns 0 results for every query, param name, and Accept header. POST returns 403. Don't waste time on it.

**`/shows` pagination caps at offset=1008** (HTTP 422 beyond), and per-show `/episodes` lists are similarly lossy past the API window. The corpus has 1709 shows and 86,600+ episodes; you cannot reach the full corpus through pure API pagination.

**Master sitemap** (`/sitemap.xml.gz`) enumerates every show landing and every episode URL, including ones the API can't paginate to. This is the crawl frontier. Verified: even 2012-era episodes fetch 200 via the tracklist endpoint when accessed directly. (`data/master_sitemap.jsonl`.)

**Artists sitemap** (`/artists_sitemap.xml.gz`): 166,704 artist pages, sitemap-of-sitemaps pointing at 4 sub-files. Each artist URL is `/artists/{int_id}-{slug}` — the integer ID is the canonical artist key. Used as a slug→id dictionary for canonicalization (`data/artist_sitemap.jsonl`); the artist *pages* themselves are not crawled (their server-rendered React state is paginated/truncated and unreliable for prolific artists — `tracks` capped at 10, `episodesPlayedOn` empty for residents, "MORE TRACKS" button hits a non-public endpoint).

---

## Canonicalization

Tracklist responses give free-text artist strings (`"Wiki, Subjxct 5"`, `"DJ Lucas & Papo2oo4"`, `"Rhythm & Sound, Paul St. Hilaire"`). Canonical key is the **NTS integer artist ID** from the artists sitemap. ~15.3% of strings carry a multi-artist marker (corpus-validated).

Resolution flow (`canonicalize.py`):
1. Skip placeholders (`Unknown Artist`, `Excerpt`, ...).
2. **Full-string slug match first.** Catches names with internal commas/&'s like "Tyler, the Creator" or "Earth, Wind & Fire" without false-splitting.
3. **Two-tier split** if step 2 misses: comma is a hard collaborator boundary; `&`/`ft`/`x` are inside-band-name fallbacks. Try each comma-fragment as a full match before falling back to sub-delimiter splitting on it. (One-tier `&`-splitting falsely shreds "Rhythm & Sound, Paul St. Hilaire" into [Rhythm, Sound, Paul St. Hilaire] — caught and fixed during first ranking pass.)
4. **Article-prefix fallback** (`the-x ↔ x`) on individual fragment lookups.

Slugify: NFKD-strip non-ASCII, lowercase, replace non-alphanumerics with hyphens. NTS slugs are pure ASCII (verified: 0/166,704 have non-ASCII).

Resolution rate on full corpus (1.5M strings): 80.5% (68% full + 9.3% clean split + 3.2% partial). Unresolved 19.5% breaks down into tracklist staff notes ("Excerpt"), shorthand references ("Eno", "Janet"), special-character mismatches ("A$AP Rocky" → `a-ap-rocky`, NTS uses `asap-rocky`), and small artists not on NTS.

**NTS-data dupes** (same human, two artist pages — not our bug, NTS's): visible at the top of co-occurrence ranking. Examples: `j-dilla ↔ jay-dee`, `dj-spinn ↔ spinn`, `d-angelo ↔ dangelo`, `d-angelo ↔ the-vanguard` (band-name page split). Cleanup is a hand-curated merge table — deferred.

**Collaborator-pair pattern** (calibration): some top-ranked pairs are duos / frequent collaborators (Sam Gendel↔Sam Wilkes, Dean Blunt↔Joanne Robertson, Madlib↔Freddie Gibbs). Treat as expected, not noise — same pattern as music-map.com surfacing aliases/partners adjacent to the center artist. Cross-curator validation still holds; just don't claim these as *non-obvious* discoveries.

Discogs IDs are deferred. The `discogsUrl` field on artist-page tracks points to a Discogs *release*, not artist; resolution to a Discogs artist ID requires extra API hops. Discogs joins matter only when joining external evidence streams later.

---

## Carry-forward priors (binding)

These commitments survive from the prior direction (`discourse` branch / `self-discourse` tag) and still apply:

- **No collaborative filtering.** Goal is to surface what CF misses, not compete with Spotify's signal.
- **No genre supervision in scoring or ranking.** GATSY 2024 demonstrated genre signals hurt artist similarity. NTS-curated genre tags are useful for diagnostic spot-checks ("is this co-occurrence pair genre-far?"), never for filtering or weighting.
- **No Claude-authored summaries / curated tag vocabulary.** Hand-labeling dressed up as LLM output isn't the point.
- **Intent-density, not algorithmic-mass.** A single NTS show curated by a real person with a written thesis is the right substrate; Spotify's million-playlist average is not. Same data type, very different signal density per artifact.
- **No curation layer on outputs.** Surface ranked pairs; don't editorialize the connections.

---

## Far-off (not chasing soon)

- **Aesthetic-axis projection** (5–8 poles musicians argue about; LLM scores artists per axis with evidence). Eventually replaces plain co-occurrence ranking; would be fed by multiple evidence streams.
- **Multi-evidence streams into the axis layer**: NTS curator-graph + artist self-discourse (the prior direction, on the `discourse` branch) + lyrics + LLM-listening to audio.
- **Other curator substrates** if NTS works: Discogs compilations, Bandcamp Daily mixes, RA "In Residence", artist self-curation (year-end lists, guest mixes).
- **Sampling lineage** (WhoSampled-derived; Spotify acquired Nov 2025, access trajectory uncertain).
- **Listening-trajectory geometry** from Last.fm scrobble sequences.

---

## Prior direction (deprecated)

The prior architecture mined artist self-discourse from interview corpora — extract verbatim quotes per artist, embed, median-pool, cosine. Frozen at tag `self-discourse` (branch `discourse`). Worked on n=25 with manually validated quote corpora; pivoted to curator-graph on 2026-04-26 because (a) self-discourse signal is partial and survivor-biased toward talkative anglophone artists, (b) embeddings encoded register strongly enough at the per-quote level to drive false positives that tracked scene rather than aesthetic. The full investigation lives in the `discourse` branch's `docs/NOTES.md`.

The music-similarity research landscape that frames both directions: `docs/research/`.
