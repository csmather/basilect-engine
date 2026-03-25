# Basilect Engine — CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## What This Is

A dual-layer artist knowledge graph that measures two independent dimensions of artist relatedness:

1. **Genre proximity** — genre and style overlap derived from MusicBrainz genres. This is the control layer: what a conventional genre-matching system would see.
2. **Discourse similarity** — what artists say about what they're doing, what critics identify as their intent, how they describe their relationship to sound. Extracted from interviews, critical writing, and liner notes, then embedded for semantic comparison.

The hypothesis: the most rewarding music discoveries happen when two artists are far apart on genre proximity but close together on discourse similarity. The engine surfaces those pairs.

## How It Works

1. Artist nodes are built individually — genres from MusicBrainz, discourse profiles from web research.
2. Discourse profiles are embedded via sentence-transformers.
3. Pairwise scores are computed for all artist pairs: genre Jaccard (proximity) and cosine similarity of embeddings (discourse).
4. Pairs are ranked and surfaced for exploration.

**Connections are computed, not authored.** There are no edge files. There is no `connect` command. The engine does not decide which artists are related — it computes two scores and the output is exploratory.

---

## Node Schema

```json
{
  "id": "artist_slug",
  "name": "Artist Name",
  "mbid": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "country": "XX",
  "genres": ["genre1", "genre2", "genre3"],
  "discourse_profile": "...",
  "sources": [
    { "url": "https://...", "type": "interview", "fetched": "YYYY-MM-DD" },
    { "url": "https://...", "type": "critical_essay", "fetched": "YYYY-MM-DD" }
  ],
  "confidence": "high"
}
```

- **id**: lowercase slug, underscores for spaces. e.g. `brian_eno`, `badbadnotgood`.
- **mbid**: MusicBrainz artist ID. Used for direct genre lookups — bypasses search disambiguation. Can be provided at add time or confirmed from search results.
- **genres**: from MusicBrainz `inc=genres` lookup. Community-voted, controlled vocabulary. Lowercase. If an artist has zero MB genres, manually assign 3-5 genres.
- **discourse_profile**: synthesized from source research. See writing instructions below.
- **sources**: breadcrumbs only — url, type, fetch date. No summaries stored.
- **confidence**: `high` (3+ quality sources, profile well-grounded), `medium` (1-2 sources, reasonable but thin), `low` (inferred from context, limited primary material).

---

## Commands

### `add [artist]`

Build a new artist node. Steps:

**Step 1: Gather genres**

Use `scripts/musicbrainz.py` to fetch genres from MusicBrainz.

If an MBID is provided (recommended — avoids disambiguation errors):
```
python scripts/musicbrainz.py "Artist Name" --mbid <MBID>
```

If no MBID is provided, the script searches by name and shows candidates:
```
python scripts/musicbrainz.py "Artist Name"
```

The script hits the MusicBrainz API directly (`inc=genres`) and returns the curated genre list. Store as a flat list of lowercase strings. Store the MBID in the node.

If the artist has zero MusicBrainz genres, manually assign 3-5 genres based on genre knowledge. Note this in the node.

**Rate limit:** MusicBrainz requires max 1 request per second. The script handles this.

**Step 2: Research discourse**

Search for and read source material about the artist's intent, philosophy, and approach. The goal is to understand what the artist is _trying to do_ — not what they sound like, not their biography, not their discography.

**Source priority** (highest to lowest):

1. **Artist's own words** — interviews, liner notes, artist statements. These ground the profile in intent, not inference.
2. **Longform critical writing** — essays or reviews that analyze approach and philosophy, not just rate the music.
3. **Scene/label/compilation context** — framing that positions the artist within a tradition.
4. **Biography and review pages** — useful for facts, weak for discourse.

**Search strategy:**

- Lead with queries targeting the artist's own words: `[artist] interview`, `[artist] "in their own words"`, `[artist] approach philosophy`.
- Follow with queries targeting specific works.
- At least one query **must** be exploratory — a lesser-known work, a label, a scene, a collaborator, a compilation that might surface context your training data doesn't emphasize. This is not optional.
- For non-anglophone artists, target English-language specialty publications (Bandcamp Daily, The Wire, Japan Times, Vinyl Factory, Red Bull Music Academy) and search for translated interviews. English-language material will be thinner — if confidence lands at `medium`, say why honestly rather than padding the profile with inference.
- If your findings are unexpected compared to your training data, you're probably doing a good job.
- **Flag when the exploratory search changed the profile.** If the exploratory query surfaced material that shifted your understanding of the artist — a collaboration, a scene connection, a lesser-known work that reframes their intent — note it briefly in the discourse profile or as a comment during the add. If the exploratory search only confirmed what you already knew, that's fine, but the distinction matters for evaluating whether the search strategy is actually working.

**Source reading workflow:**

- Fetch a source → extract the relevant discourse signals into scratch notes → move on to the next source.
- If a fetch fails (403, empty page, TLS error), search for an alternative source rather than falling back on search result summaries. Search snippets are leads, not sources. **A 200 response with no extractable text counts as a failed fetch** — many sites return full HTML/CSS/JS blobs with no readable content. Don't treat these as sourced; move on and find an alternative.
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

Run `python scripts/compute.py`. Computes pairwise discourse similarity (cosine) and genre proximity (Jaccard) for all artist pairs. Saves matrices to `data/`.

### `discover`

Run `python scripts/discover.py`. Outputs ranked pair lists:

- Basilect discoveries (high discourse sim, low genre proximity)
- Deep scene connections (high discourse sim, high genre proximity)
- Surface-only connections (low discourse sim, high genre proximity)
- Unrelated (low discourse sim, low genre proximity)

### `stats`

Run `python scripts/stats.py`. Outputs:

- Node count, average genres per node, confidence distribution
- Orthogonality test: Pearson and Spearman correlation between discourse sim and genre proximity
- Distribution stats for both similarity measures

---

## What This Engine Does NOT Do

- **It does not decide which artists are connected.** It computes scores. The output is exploratory, not prescriptive.
- **It does not hear music.** All discourse claims are mediated by language — what artists say, what critics write. Flag when you're uncertain about actual sound.
- **It does not curate.** There are no curation principles, no "what makes a good connection" guidelines. The engine builds nodes and runs math.
- **It does not author connection reasoning.** v1 wrote paragraphs explaining why two artists were related. v2 produces numbers. If a pair scores high, both profiles can be read to understand why.

## Evaluation Philosophy

This is an exploratory tool. There is no ground truth for "correct" artist connections — the engine surfaces patterns for interpretation, not answers to validate.

**Evaluation is stability testing, not accuracy testing:**

- Do the top-ranked pairs stay roughly the same across pipeline changes? (If the whole list shuffles, the signal is noise)
- Does a given change (chunking, model swap) produce meaningfully different rankings, or just minor reordering?
- Are certain artists dominating the top of every list? (Suggests generically written profiles, not real connections)

**Do not hand-label expected outputs.** That bakes assumptions into the test and defeats the purpose of exploration. Measure whether the pipeline is stable and whether the two axes remain orthogonal.

---

## Platform Note

This project runs on Windows. File paths use Windows conventions. Python scripts should use forward slashes or `pathlib` for cross-platform compatibility.
