# Basilect Engine — CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## What This Is

A dual-layer artist knowledge graph that measures two independent dimensions of artist relatedness:

1. **Tag proximity** — genre, style, and scene overlap derived from Last.fm tags. This is the conventional layer: what a genre-matching system would see.
2. **Discourse similarity** — what artists say about what they're doing, what critics identify as their intent, how they describe their relationship to sound. Extracted from interviews, critical writing, and liner notes, then embedded for semantic comparison.

The hypothesis: the most rewarding music discoveries happen when two artists are far apart on tag proximity but close together on discourse similarity. The engine surfaces those pairs.

## How It Works

1. Artist nodes are built individually — tags from Last.fm, discourse profiles from web research.
2. Discourse profiles are embedded via sentence-transformers.
3. Pairwise scores are computed for all artist pairs: tag Jaccard (proximity) and cosine similarity of embeddings (discourse).
4. Pairs are ranked and surfaced. The human curator evaluates by ear.

**Connections are computed, not authored.** There are no edge files. There is no `connect` command. The engine does not decide which artists are related — it computes two scores and the curator interprets the output.

---

## Node Schema

```json
{
  "id": "artist_slug",
  "name": "Artist Name",
  "country": "XX",
  "tags": ["tag1", "tag2", "tag3", ...],
  "discourse_profile": "...",
  "sources": [
    { "url": "https://...", "type": "interview", "fetched": "YYYY-MM-DD" },
    { "url": "https://...", "type": "critical_essay", "fetched": "YYYY-MM-DD" }
  ],
  "confidence": "high"
}
```

- **id**: lowercase slug, underscores for spaces. e.g. `brian_eno`, `badbadnotgood`.
- **tags**: from Last.fm `artist.getTopTags`. Include all tags with non-zero weight — typically ~10 per artist (the API's weight distribution drops off steeply). Lowercase, as returned by the API.
- **discourse_profile**: synthesized from source research. See writing instructions below.
- **sources**: breadcrumbs only — url, type, fetch date. No summaries stored.
- **confidence**: `high` (3+ quality sources, profile well-grounded), `medium` (1-2 sources, reasonable but thin), `low` (inferred from context, limited primary material).

---

## Commands

### `add [artist]`

Build a new artist node. Three steps:

**Step 1: Gather tags**

Call the Last.fm API:

```
http://ws.audioscrobbler.com/2.0/?method=artist.getTopTags&artist=ARTIST_NAME&api_key=API_KEY&format=json
```

The API key is stored in `.env` as `LASTFM_API_KEY`. Use `scripts/lastfm.py` to fetch.

Extract tag names. Keep all tags with non-zero weight (the API returns a weight 0-100, but the distribution drops off steeply — expect ~10 usable tags per artist). Store as a flat list of lowercase strings.

If the artist isn't found on Last.fm, note it and proceed — tags can be manually assigned from genre knowledge, but flag the node's proximity data as incomplete.

**Step 2: Research discourse**

Search for and read source material about the artist's intent, philosophy, and approach. The goal is to understand what the artist is _trying to do_ — not what they sound like, not their biography, not their discography.

**Source priority** (highest to lowest):

1. **Artist's own words** — interviews, liner notes, artist statements. These ground the profile in intent, not inference.
2. **Longform critical writing** — essays or reviews that analyze approach and philosophy, not just rate the music.
3. **Scene/label/compilation context** — curatorial framing that positions the artist within a tradition.
4. **Biography and review pages** — useful for facts, weak for discourse.

**Search strategy:**

- Lead with queries targeting the artist's own words: `[artist] interview`, `[artist] "in their own words"`, `[artist] approach philosophy`.
- Follow with queries targeting specific works.
- At least one query **must** be exploratory — a lesser-known work, a label, a scene, a collaborator, a compilation that might surface context your training data doesn't emphasize. This is not optional.
- For non-anglophone artists, target English-language specialty publications (Bandcamp Daily, The Wire, Japan Times, Vinyl Factory, Red Bull Music Academy) and search for translated interviews. English-language material will be thinner — if confidence lands at `medium`, say why honestly rather than padding the profile with inference.
- If your findings are unexpected compared to your training data, you're probably doing a good job.

**Source reading workflow:**

- Fetch a source → extract the relevant discourse signals into scratch notes → move on to the next source.
- If a fetch fails (403, empty page, TLS error), search for an alternative source rather than falling back on search result summaries. Search snippets are leads, not sources.
- Do NOT store source summaries as persistent data. The discourse profile is the output; the source list is the receipt.
- Working notes are context-management tools, not data.

**Minimum sources for confidence levels:**

- `high`: at least 1 primary source (interview/artist statement) + 1 critical source
- `medium`: at least 2 sources of any tier
- `low`: fewer than 2 usable sources — flag what's missing and move on honestly

**Step 3: Write the discourse profile**

Synthesize the source material into a prose paragraph (3-8 sentences) that captures:

- What the artist says they're trying to do
- What critics identify as their distinctive approach or philosophy
- How they describe their relationship to genre, tradition, sound, or composition
- Any explicit self-positioning ("I wanted the music to recede into the room")

**Writing rules:**

- **Write what the sources say.** Do not synthesize a thesis beyond what's grounded in the material. If an artist hasn't articulated a clear philosophy in interviews, say that — don't invent one.
- **Discourse, not description.** "Treats hip-hop production as a meditative form" is discourse. "Warm, dusty, sample-based beats" is description. The profile should be primarily the former. Sonic description is fine as supporting context, but the core of the profile is intent and approach.
- **Don't write for connection-making.** The profile should faithfully represent this artist's discourse, not frame it in terms that might match other artists in the graph. If two artists genuinely share vocabulary, the embeddings will catch it. Don't force it.
- **Flag uncertainty.** If the profile relies substantially on inference rather than source material, say so. "Going off context — no primary interview material found" is better than a confident-sounding profile built on guesses.
- **No genre hand-holding.** Don't explain what ambient music is. Don't contextualize jazz rap for a lay reader. Write for someone who knows music.

**Step 4: Assemble and save**

Write the node JSON to `data/artists/{slug}.json`. Confirm the file was written.

### `batch [list of artists]`

Run `add` for each artist in sequence. Research and save one at a time — don't batch research across artists. Each artist should be fully written to disk before starting the next.

### `embed`

Run `python scripts/embed.py`. Embeds all discourse profiles and saves to `data/embeddings.npy` + `data/embedding_ids.json`.

### `compute`

Run `python scripts/compute.py`. Computes pairwise discourse similarity (cosine) and tag proximity (Jaccard) for all artist pairs. Saves matrices to `data/`.

### `discover`

Run `python scripts/discover.py`. Outputs ranked pair lists:

- Basilect discoveries (high discourse sim, low tag proximity)
- Deep scene connections (high discourse sim, high tag proximity)
- Surface-only connections (low discourse sim, high tag proximity)

### `stats`

Run `python scripts/stats.py`. Outputs:

- Node count, average tags per node, confidence distribution
- Orthogonality test: Pearson and Spearman correlation between Φ_sim and P_prox
- Distribution stats for both similarity measures

---

## What This Engine Does NOT Do

- **It does not decide which artists are connected.** It computes scores. The curator interprets.
- **It does not hear music.** All discourse claims are mediated by language — what artists say, what critics write. Flag when you're uncertain about actual sound.
- **It does not curate.** There are no curation principles, no "what makes a good connection" guidelines. The engine builds nodes and runs math. Curation happens downstream, by a human, with ears.
- **It does not author connection reasoning.** v1 wrote paragraphs explaining why two artists were related. v2 produces numbers. If a pair scores high, the curator can read both profiles and decide if the connection is real.

---

## Platform Note

This project runs on Windows. File paths use Windows conventions. Python scripts should use forward slashes or `pathlib` for cross-platform compatibility.

The Last.fm API key is stored in `.env` and loaded via `python-dotenv` or read directly. Do not commit the API key.
