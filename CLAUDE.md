# Basilect Engine — CLAUDE.md

This file provides guidance to Claude Code when working in this repository.

## What This Is

A curated graph of artist nodes and connection edges that maps how artists connect beneath the surface. The graph grows with every artist researched and every connection established, accumulating enough density to generate connections the curator hasn't made yet.

The core theory: music has a shared language hidden beneath surface-level genre and sonic differences. Two artists can be sonically miles apart but intentionally, philosophically in the same room. Algorithms analyze texture and energy. This engine reasons about intent and meaning.

## Why LLM Reasoning Over a Curated Graph

Spotify-style systems work on audio features — BPM, warmth, density. That catches surface similarity. It misses the shared sensibility between a Japanese library music composer and a New York jazz rap producer, or the emotional architecture overlap between Radiohead and Fishmans. Those connections live in language — interviews, critical writing, liner notes, how artists describe what they're doing. LLM reasoning over accumulated context is better suited to this dimension than audio embeddings.

The priority hierarchy for what makes a basilect connection:

1. **Intentional/philosophical** — the artist's approach, sensibility, what they're trying to do
2. **Textural** — sonic surface, grain, density, space
3. **Emotional** — how the music moves through feeling over time
4. **Structural/compositional** — use of space, repetition, how elements enter and exit

---

## Curation Principles

These define what a valid connection looks like. Apply them when reasoning about candidates, evaluating paths, or generating new connections.

### What a basilect connection is

A connection is valid when two artists share intentional or philosophical DNA despite surface-level differences. The goal is "same room, different door" — not artists who sound alike, but artists who are _doing_ something alike.

### What makes a connection worth adding

- It should reward curiosity, not confirm what the algorithm already shows. If Spotify or Last.fm would surface this pairing, it's probably not a basilect connection — it's a similarity connection.
- Don't reach for obscurity for its own sake. The connection should feel like something a listener _would_ value but _wouldn't_ have found.
- Value sonic DNA, but value "same room, different door" higher — shared sensibility, emotional architecture, or production philosophy across different eras, scenes, or countries.
- Cross-cultural and cross-era links are high value. Geographic and temporal range signals that the connection operates on a deeper dimension than scene proximity.
- Genre labels are low priority. Vibes, texture, feeling, and compositional approach matter more than categorical genre fit.

### Blindspots

Data (Last.fm, listening patterns, critical writing) clusters within scenes and cultures. The real discoveries often live outside the main cluster — artists from other countries, other eras, adjacent scenes that share intent but not audience. Flag these proactively. When researching a new artist, always ask: who's doing something philosophically similar in a completely different context?

### Epistemic honesty

You cannot hear the music. Sonic judgments are based on contextual knowledge — genre tags, critical descriptions, scene associations, production lineage. Be transparent when a candidate is obscure enough that you're uncertain about the actual sound. Flag it as **"going off context"** so the curator can prioritize checking by ear.

---

## Data Model

### Artist Node

Three layers: **sources** (raw evidence), **profiles** (synthesized for reasoning), and **metadata** (confidence, coverage).

```json
{
  "id": "nujabes",
  "name": "Nujabes",
  "country": "JP",
  "era": "1990s-2000s",
  "tags": ["jazz rap", "lo-fi", "instrumental hip hop", "japanese"],

  "sonic_profile": {
    "texture": "warm, dusty, sample-based",
    "density": "medium — space between elements is intentional",
    "energy": "introspective, unhurried"
  },

  "philosophical_profile": "Treats hip hop production as a meditative form. The loop isn't repetition — it's stillness. Draws from jazz not for genre signaling but for a shared philosophy of restraint and space. The sadness in the music is never melodramatic.",

  "sources": [
    {
      "url": "https://example.com/nujabes-interview-2003",
      "type": "interview",
      "summary": "Discusses his approach to sampling as finding stillness in motion.",
      "fetched": "2026-03-22"
    }
  ],

  "confidence": "high",
  "notes": ""
}
```

**Source types**: `interview`, `review`, `liner_notes`, `artist_statement`, `critical_essay`, `documentary`, `biography`, `curator_note`

**Confidence levels**:

- `high` — 3+ quality sources, philosophical profile is well-grounded
- `medium` — 1-2 sources, profile is reasonable but could be deeper
- `low` — primarily inferred from tags/scene context, limited primary sources
- `stub` — name and tags only, needs research before use in connections

The philosophical profile is the ceiling for reasoning quality. A thin profile produces thin connections. When confidence is `low` or `stub`, flag it — don't reason over it as if it's solid.

### Connection Edge

```json
{
  "from": "nujabes",
  "to": "rei_harakami",
  "type": "basilect",
  "strength": "strong",
  "confidence": "medium",
  "dimensions": ["intentional", "emotional"],
  "reasoning": "Both operate in a Japanese tradition of introspective electronic/instrumental music where restraint is the primary tool. Harakami's synthesizers occupy the same emotional register as Nujabes' samples — unhurried, melancholic without being sentimental. Different sonic surfaces, same philosophical approach to space and feeling.",
  "cross_cultural": false,
  "cross_era": false,
  "discovered_by": "manual"
}
```

**Connection types**:

- `basilect` — full philosophical/intentional connection. The real thing.
- `sonic` — primarily textural/surface similarity. Weaker signal, but worth tracking.
- `lineage` — direct influence (one artist shaped the other). Useful context, not the same as a basilect connection.

**Dimensions** — tag which layers the connection operates on: `intentional`, `textural`, `emotional`, `structural`. Enables queries like "show me all cross-cultural connections that are primarily intentional."

**discovered_by** — `manual` (established by the curator, either from personal knowledge or confirmed by ear) or `engine` (suggested by graph reasoning, pending approval).

**Edge strength** vs **edge confidence** — these measure different things:

- `strength` is curatorial: "if this connection is real, how good is it?" A strong connection is one that rewards a curious listener. This is a judgment about the connection's value, not its certainty.
- `confidence` is epistemic: "how sure are we this connection is actually valid?" Constrained by the weakest node it touches — you can't have high confidence on an edge between two medium-confidence profiles.
  - `high` — both nodes are well-sourced, the reasoning is grounded in specific evidence
  - `medium` — at least one node has gaps, or the reasoning relies partly on inference
  - `low` — speculative, going off context, or both nodes are thin
  - A `strong` / `low` edge means "this would be a great connection if it holds up — prioritize ear-checking"

---

## Project Structure

```
basilect-engine/
  CLAUDE.md                   # This file
  data/
    artists/                  # One .json per artist node
    connections/              # One .json per connection edge
    graph_summary.md          # Auto-generated readable overview of current graph state
  README.md
```

`graph_summary.md` is regenerated by the `status` command. It's a human-readable snapshot: node count, edge count, cluster overview, stub/low-confidence nodes that need sourcing, and isolated nodes with few connections.

---

## Commands

All commands run interactively through Claude Code on your Pro plan. No API calls, no external scripts.

### `add artist [name]`

Research and add a new artist to the graph.

1. Search for interviews, critical writing, and reviews
2. Collect 2-5 quality sources — prioritize interviews and longform criticism over listicles and aggregator pages
3. Draft the sonic and philosophical profiles from the source material
4. Assign a confidence level based on source quality and coverage
5. Write the node JSON to `data/artists/[slug].json`
6. Present the draft for review before saving

Don't generate philosophical profiles from thin air. If sources are sparse, write what you can, set confidence to `low` or `stub`, and flag what's missing. A honest stub is better than a confident hallucination.

#### Source strategy

Search for what you don't already know, not for confirmation of what you do. Your training data gives you a starting impression of most artists — the goal of source research is to challenge, deepen, or correct that impression, not validate it.

**Source value hierarchy** (highest to lowest):

1. Artist's own words — interviews, liner notes, artist statements. These ground the philosophical profile in intent, not inference.
2. Longform critical writing — reviews or essays that analyze specific works with textual detail, not just star ratings.
3. Scene/compilation/label context — curatorial framing from labels, compilation liner notes, or scene retrospectives that position the artist within a tradition.
4. General reviews and biography pages — useful for facts and tags, weak for philosophical profiling.

**Search discipline:**

- Lead with queries targeting the artist's own words: `[artist] interview`, `[artist] "in their own words"`, `[artist] liner notes`.
- Follow with queries targeting specific works you're less familiar with — not the album you'd name from memory, but a deeper cut, a collaboration, a side project. This is where genuine discovery happens.
- At least one query per artist should be exploratory — a label, a scene, a collaborator, a compilation — something that might surface context your training data doesn't emphasize.
- If all your sources say roughly what you expected, you haven't searched well enough.

**Minimum for confidence levels:**

- `high` requires at least one primary source (interview/artist statement) + one critical source
- `medium` requires at least two sources of any quality tier
- `low` or `stub` means you found fewer than two usable sources — flag what's missing and move on honestly

### `seed`

Bulk-add a cluster of connected artists from a natural language description. The curator describes the artists and the through-line connecting them:

> _"Brian Eno connects to Hiroshi Yoshimura, Yoshio Ojima, Midori Hirano, and Midori Takada. The through-line is Japanese ambient / kankyō ongaku — artists who share Eno's philosophy of music as environment but filtered through a distinctly Japanese sensibility of restraint and negative space."_

The command:

1. Runs `add artist` for each artist not already in the graph (source research, profile drafting, confidence assignment)
2. Generates connection edges between the named artists using the curator's description + the researched profiles to write proper reasoning and dimensions
3. Presents the full batch (all nodes + all edges) for review before writing anything to disk
4. Updates `graph_summary.md`

This is the fastest way to build initial density. Describe a cluster, review the output, approve.

### `connect [artist] [artist]`

Manually add a connection between two existing nodes. The curator describes the connection, Claude drafts the edge JSON with reasoning and dimensions. For one-off connections, scene relationships, lineage, or connections known from personal knowledge.

### `suggest [artist]`

The core reasoning command. Given an artist (in the graph or new):

1. Load the full graph context
2. If the artist is in the graph: find all existing connections, then reason about potential connections to other nodes — prioritize paths through shared philosophical dimensions over tag/genre overlap
3. If the artist is new: draft a quick profile from available knowledge, then find the most promising connection candidates in the existing graph
4. Flag blindspots — scenes, eras, or cultures that the current graph doesn't cover but that might contain strong connections
5. For each suggested connection, indicate confidence level and whether you're going off context

**Output format:**

```
## [Artist Name] — Suggestion Report

**In the graph**: [yes/no, and if yes: current connections, cluster membership]

**Strongest candidates** (ranked):
1. **[Artist]** — [connection type], [dimensions]
   - Why: [reasoning]
   - Confidence: [high/medium/going off context]

**Blindspots**: [scenes, eras, cultures worth exploring that the graph doesn't cover yet]

**Graph notes**: [anything about the current graph topology that's relevant — isolated clusters, missing bridges, thin profiles that limit reasoning]
```

### `scan gaps`

Batch analysis of the full graph:

1. Find all two-hop paths that don't have a direct edge — rank by philosophical overlap potential
2. Identify clusters and name them (the engine should notice when a group of densely connected artists forms a scene)
3. Flag isolated nodes (few connections) and thin profiles (low confidence) that are limiting the graph's reasoning power
4. Suggest the highest-value artists to add next — not random, but artists who would create bridges between existing clusters or fill known blindspots
5. Update `graph_summary.md`
6. Surface high-strength / low-confidence edges as priority ear-checks — these are the connections most worth validating

### `status`

Regenerate `graph_summary.md` and print a quick overview: node count, edge count, confidence distribution, cluster summary, top priorities for graph improvement.

---

## How Claude Code Should Work Here

**Do:**

- Reason about connections using the philosophical dimension first, then texture, emotion, structure
- Search for and synthesize source material when building profiles
- Flag uncertainty — "going off context" is always better than a confident guess
- Proactively surface blindspots in the graph's cultural and temporal coverage
- Track your own confidence in each suggestion

**Don't:**

- Default to Last.fm-style reasoning ("fans of X also listen to Y") — that's audience overlap, not a basilect connection
- Generate philosophical profiles without source material — ask for more or mark as stub
- Treat genre tags as the primary signal for connections
- Add anything to the graph without the curator's approval — suggestions only, they decide
- Overweight connections between artists who are already in the same scene/era/country — those are easy and usually already known

---

## Tools

- **WebSearch / WebFetch** — for source research during artist profiling. WebSearch for discovery, WebFetch for reading full pages.
- **Filesystem** — read/write JSON files in `data/`. All graph state lives on disk.

No external API calls. No database. The graph is JSON files that Claude Code reads into context and reasons over directly.

---

## Platform Note

This project runs on Windows. File paths use Windows conventions.
