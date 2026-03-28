# Discourse Upgrade Plan

**Date:** 2026-03-25 (revised)
**Starting from:** v2 baseline with MusicBrainz genre proximity
**Archived:** v3 overcomplicated implementation at `archive/v3` branch

---

## Diagnosis (from Codex cross-test)

V3 over-invested in proximity (album tags, MusicBrainz tags, soft Jaccard, synonym maps) when proximity is just the control axis. Meanwhile discourse — the novel axis — stayed coarse: one long paragraph per artist, single-shot MiniLM embedding.

Proximity is now settled: plain Jaccard on MusicBrainz genres.

**All new complexity goes to discourse.**

---

## Plan

### 1. Chunk discourse profiles into atomic claims

**Problem:** A single long paragraph gets averaged into one embedding vector. Specific philosophical positions get diluted by surrounding context. Two artists who share one precise idea but differ everywhere else look moderately similar instead of strikingly similar on that one dimension.

**Change:** Split each discourse profile into discrete claim-level chunks before embedding. Each chunk should be one idea: a quote, a stated intent, a critic's observation about approach.

- Store chunks as a list in the artist node JSON: `"discourse_chunks": [...]`
- Keep the full `discourse_profile` paragraph for human reading
- Chunks are the embedding input; profile is the display output

**How to chunk:** Simple sentence/clause splitting, with each chunk being a self-contained claim. Not ML-based chunking — just break on natural boundaries. A profile of 4-8 sentences should yield 4-8 chunks.

### 2. Embed chunks, aggregate robustly

**Problem:** Single vector per artist loses the shape of the distribution. Trimmed mean or median of chunk embeddings is more robust to one outlier sentence pulling the whole profile toward a generic cluster.

**Change in `embed.py`:**
- Embed all chunks per artist (not the whole profile)
- Store per-chunk embeddings
- Compute artist-level vector as **median** of chunk embeddings (not mean — median is more robust to outlier chunks)

**Change in `compute.py`:**
- Discourse similarity still = cosine of artist-level vectors
- Optional: also compute max chunk-to-chunk similarity per pair (captures "these two artists share one very specific idea" even if their overall profiles diverge)

### 3. Stability testing

**Problem:** With n=20 and 190 pairs, median thresholding is noisy. No way to tell if a pipeline change actually improved results vs. just shuffled the noise.

**Approach:** Stability testing, not accuracy testing. This is an exploratory tool — there is no ground truth for "correct" connections. Do not hand-label expected outputs.

Add `scripts/stability.py`:
- Snapshot ranked pair lists before and after a pipeline change
- Report: how many of the top-N pairs are shared between runs?
- Report: what's the average rank displacement for pairs across runs?
- Flag artists that dominate top rankings (suggests generically written profiles)

### 4. Test embedding model sensitivity

**After** chunks + stability testing are in place:
- Snapshot current rankings (whole-profile MiniLM)
- Run with chunked embeddings → compare stability
- Optionally swap to a larger model (e.g., `all-mpnet-base-v2`) → compare stability

Don't swap models until you can measure the difference.

---

## What this plan does NOT do

- Touch proximity. It's a control variable. Plain Jaccard stays.
- Scale the artist set. Stay at 20 until the pipeline is validated.
- Add visualization or UI. Downstream of validation.
- Hand-label expected outputs or introduce a curation step.

---

## Execution order

1. **Chunk profiles** — update node schema, write chunks for all 20 artists
2. **Update embed.py** — chunk-level embedding + median aggregation
3. **Write stability.py** — ranking comparison across pipeline configs
4. **Snapshot pre-chunk rankings** — baseline for comparison
5. **Re-run pipeline** — embed → compute → discover
6. **Compare** — are chunked rankings stable and meaningfully different from whole-profile?
7. **Model swap test** — only if step 6 shows the pipeline is stable

Each step is independently testable. No step depends on a later step.

---

## Success criteria

- Stability script exists and produces repeatable comparison metrics
- Chunked discourse embeddings produce stable rankings
- Orthogonality test still shows r < 0.3 (discourse and proximity remain independent axes)
- No new complexity in the proximity pipeline
