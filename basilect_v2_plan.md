# Basilect Engine v2 — Prototype Plan

## Repo Strategy

Previous work preserved on `v1-manual-graph` branch. Main is clean. Build from scratch.

---

## Goal

A small-scale prototype that can:
1. Autonomously build artist nodes from real data (Last.fm tags + web-sourced discourse profiles)
2. Compute two independent similarity scores for all pairs: tag proximity (Jaccard) and discourse similarity (cosine of embedded profiles)
3. Surface pairs where discourse similarity is high but tag proximity is low
4. Output those pairs for human evaluation (listening + judgment)

No curation layer. No manual connection authoring. No approval gates during node building. The engine runs, you evaluate the output.

---

## Node Schema

```json
{
  "id": "brian_eno",
  "name": "Brian Eno",
  "country": "GB",
  "tags": ["ambient", "electronic", "experimental", "art rock", "british", "producer"],
  "discourse_profile": "Music as environment rather than event. Eno's central idea is that music doesn't need to demand attention — it should work at the periphery...",
  "sources": [
    { "url": "https://...", "type": "interview", "fetched": "2026-03-25" },
    { "url": "https://...", "type": "critical_essay", "fetched": "2026-03-25" }
  ],
  "confidence": "high"
}
```

**That's the whole node.** Tags from Last.fm API. Discourse profile synthesized from web sources. Sources are breadcrumbs (url, type, date) — no summaries stored. Embeddings computed separately and stored in numpy files, not in the node JSON.

---

## Pipeline

### Phase 1: Build Nodes (~2 weeks for 40 artists)

For each artist, Claude Code runs:

1. **Gather tags** — Last.fm `artist.getTopTags` API call. Store tag names with non-zero weight (~10 per artist — the API's weight distribution is steep).
2. **Research discourse** — web search for interviews, critical writing, liner notes. Fetch 2-4 quality sources. Extract relevant discourse signals into scratch notes (not persisted). Write the discourse profile from accumulated notes.
3. **Write node** — assemble the JSON and save to `data/artists/{slug}.json`.

**Artist selection strategy for prototype:**
- 4-5 clusters of 6-8 artists each
- Clusters should be genre-distinct (e.g., Japanese ambient, Brazilian jazz, UK electronic, jazz rap, Italian film/library)
- Within each cluster, include 1-2 artists that plausibly bridge to another cluster
- Total: ~35-40 artists

### Phase 2: Compute Embeddings

```bash
python scripts/embed.py
```

Reads all discourse profiles, embeds them via sentence-transformers (`all-MiniLM-L6-v2`), saves to `data/embeddings.npy` + `data/embedding_ids.json`.

### Phase 3: Compute Pairwise Scores

```bash
python scripts/compute.py
```

For all N×N pairs:
- **Discourse similarity (Φ_sim):** cosine similarity of discourse profile embeddings
- **Tag proximity (P_prox):** Jaccard similarity of tag sets (1 - Jaccard distance)

Saves both matrices to `data/`.

### Phase 4: Surface Discoveries

```bash
python scripts/discover.py
```

Outputs three ranked lists:
- **Basilect discoveries:** high Φ_sim, low P_prox — the signature output
- **Deep scene connections:** high Φ_sim, high P_prox — proximity confirmed by discourse
- **Surface-only connections:** low Φ_sim, high P_prox — similar tags, different intent

### Phase 5: Orthogonality Test

```bash
python scripts/stats.py
```

Pearson and Spearman correlation between Φ_sim and P_prox across all pairs. If r < 0.3, the two layers are measuring substantially different things and the engine is surfacing a real signal. If r > 0.6, the discourse profiles may just be restating genre info in prose.

**This is the first real milestone.** Everything downstream depends on it.

### Phase 6: Evaluate by Ear

Look at the top basilect discoveries. Listen. Judge:
- Does this connection hold up sonically?
- Would a curious listener find this rewarding?
- Is this something an algorithm would have surfaced?

Curation re-enters here as judgment on output, not input to the process.

---

## File Structure

```
basilect-engine/
  CLAUDE.md
  requirements.txt

  scripts/
    lastfm.py             # fetch tags from Last.fm API
    embed.py              # embed all discourse profiles
    compute.py            # pairwise Φ_sim and P_prox matrices
    discover.py           # surface ranked pair lists
    stats.py              # orthogonality test, distribution stats

  data/
    artists/              # one .json per artist node
    embeddings.npy        # discourse profile embeddings (computed)
    embedding_ids.json    # artist ID order for embedding matrix
    discourse_sim.npy     # pairwise cosine similarity (computed)
    tag_prox.npy          # pairwise tag Jaccard similarity (computed)
```

---

## Dependencies

```
sentence-transformers
numpy
scipy
scikit-learn
requests
```

`torch` comes in as a dependency of sentence-transformers. Everything else is lightweight.

---

## What's Deferred

- Curation layer (approve/reject/feedback) — after prototype proves the signal exists
- Tag embeddings for smarter proximity — only if Jaccard proves too crude after orthogonality test
- Visualization — after the data is worth looking at
- Video pipeline integration — after discoveries are validated
- Scaling beyond ~40 artists — after schema and pipeline are proven
- Formal evaluation — not the goal; listen and judge
