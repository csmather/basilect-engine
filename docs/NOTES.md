# NOTES — NTS curator-graph

Scratchpad. Active design notes; not a spec. Things harden out of here into CLAUDE.md or TODO.md.

---

## Crawl direction: artist-first (decided 2026-04-26)

Forks considered:
- **Episode-first** — walk shows → episodes → tracklists. Co-occurrence falls out directly. Free-text artist string per track, often multi-artist (`"Wiki, Subjxct 5"`, `"DJ Lucas & Papo2oo4"`). **No `discogsUrl` and no artist ID** in tracklist payload (confirmed via curl). Canonicalization is unsolvable cleanly without `/search` (broken since 2026-04-26).
- **Artist-first** — walk `artists_sitemap*.xml.gz` → ~200k artist pages → `window._REACT_STATE_` → `state.artist`. Hands you canonical NTS `id`, `episodesPlayedOn` already aggregated, `tracks` with per-track `discogsUrl` (release, not artist). Co-occurrence is a one-line invert.

Picked artist-first. Same order-of-magnitude cost (~200k vs ~50–100k requests), but artist-first solves canonicalization for free instead of leaving an unsolvable name-resolution problem downstream.

## Why not Discogs as canonical key (yet)

`discogsUrl` on artist pages points to a Discogs **release**, not artist. Resolving release→artist is one extra Discogs API hop per track. Premature for v1: NTS's own integer `id` is stable, in the URL, and the natural inverse of the sitemap. Discogs only matters when we want to join external evidence streams; for the v1 graph, NTS ID is sufficient. Keep the `discogsUrl` field around (cheap), defer resolution.

## Curator/host data — already in the crawl

NTS doesn't expose host/DJ as a structured field on shows or episodes (it's encoded in the show name like "100 Elements w/ YL"). But artist pages carry `residentShowLinks` and `specialShowLinks` — when an artist hosts/guests a show, it's on their page. So curator info is the *dual* of appearance info, harvested in the same crawl. Post-crawl, we build `show_alias → curator_artist_id` from residency/special links. Until then, `show_alias` itself is a fine proxy for "this curatorial mind" in co-occurrence weighting.

## Trimmed artist payload (per row in data/artists.jsonl)

```
{
  id, name, slug, biography, totalTracks,
  tracks:            [{ title, artistNames, releaseLabels, releaseYear, discogsUrl }],
  episodesPlayedOn:  [{ episode_alias, show_alias, broadcast }],
  residentShowLinks: [{ show_alias, name }],
  specialShowLinks:  [{ show_alias, name }]
}
```

Dropped: media URLs, description_html, mixcloud links, audio_sources, brand, full genre/mood objects. Saves ~95% on disk and keeps the file `jq`-able. Re-crawlable cheaply if we want a richer field later.

## Pipeline mechanics

- **Storage**: `data/artists.jsonl` (append-only) + `data/sitemap.jsonl` (cached after first walk) + `data/errors.jsonl` (one per failed page). Migrate to SQLite once shape stabilizes.
- **Rate**: 1 req/s default, configurable. Robots permits all; politeness anyway.
- **Resume**: scan existing `artists.jsonl` for IDs, skip those on re-run. No separate state file.
- **User-Agent**: `basilect-research/0.1 (matherscottc@gmail.com)` — honest contact for traffic ops.
- **Concurrency**: sync for v1. Add async only if 1 req/s feels limiting at scale.

## Open questions for after the crawl

- Co-occurrence weighting: per-episode intent-density (resident vs guest vs special), per-artist normalization (dampen prolific cross-genre journeymen so they don't dominate)
- Episode metadata for weighting: do we need to crawl `/shows/{a}/episodes/{e}` to get genres/moods/intensity per episode for diagnostic spot-checks? Or is that deferrable?
- Show-set scope: filter to higher-intent-density shows for v1 ranking, or use the full corpus and let weighting handle it?

## Reference: what we learned looking at ribenamaplesyrup/nts-scraper

Dead since March 2023. Pre-`/api/v2`, pre-`_REACT_STATE_` extraction — used Selenium + BeautifulSoup. Their similarity proxy is **shared record labels between shows**, not artist co-occurrence. Independently hit our canonicalization wall (had to visit artist pages anyway to get Discogs URLs, but didn't resolve to artist IDs — only release.labels[0].url). Confirms our direction without anything to copy. Different graph entirely (label-mediated show network ≠ episode-level artist co-occurrence).
