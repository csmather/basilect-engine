# Basilect Engine — NTS curator-graph

A music artist similarity engine. Goal: surface non-obvious connections between musicians by mining intent-dense curatorial artifacts, starting with NTS Radio tracklists.

Two artists are basilect-connected if they recur together in the choices of curators with different scenes, biases, or eras. Curated co-occurrence (a single mind chose to put A and B in the same hour of music) is structurally different from algorithmic co-occurrence (a million low-effort playlists averaged together) and orthogonal to genre tags / collaboration graphs.

---

## Pipeline (v1 — co-occurrence only)

1. **Crawl** — enumerate NTS shows → episodes → tracklists via `/api/v2`
2. **Canonicalize** — resolve artists via Discogs URLs in NTS artist payloads
3. **Compute** — co-occurrence matrix, weighted by per-episode intent-density
4. **Discover** — rank artist pairs

V1 is plain co-occurrence. No thesis-fit, no LLM scoring, no aesthetic-axis layer — those are far-off.

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

**Artists sitemap**: `/artists_sitemap.xml.gz` is a sitemap-of-sitemaps pointing at 4 sub-files (~50k URLs each, ~200k artist pages). Each artist URL is `/artists/{int_id}-{slug}` — the integer ID is required. Each artist page server-renders a React state into `<script id="react-state">window._REACT_STATE_ = {...}</script>` containing:

- `id`, `name`, `slug`, `biography`
- `tracks` — every track of theirs played on NTS, each with `title`, `artistNames`, `releaseLabels`, `releaseYear`, **`discogsUrl`**
- `totalTracks`
- `residentShowLinks`, `specialShowLinks`, `episodes`, **`episodesPlayedOn`** ← the reverse-lookup search would have given us, computed and cached server-side

---

## Canonicalization

NTS payloads include Discogs URLs in track entries. **Use Discogs IDs as the canonical artist key.** No need for MusicBrainz resolution — NTS has done the work, and Discogs IDs are arguably the cleaner identifier for our purposes anyway.

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
