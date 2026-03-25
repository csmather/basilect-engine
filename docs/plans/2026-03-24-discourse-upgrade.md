# Discourse Upgrade Plan

**Date:** 2026-03-24
**Starting from:** v2 baseline (20 artists, plain Jaccard proximity, MiniLM whole-profile embedding)
**Archived:** v3 overcomplicated implementation at `archive/v3` branch

---

## Diagnosis (from Codex cross-test)

V3 over-invested in proximity (album tags, MusicBrainz tags, soft Jaccard, synonym maps) when proximity is just the control axis. Meanwhile discourse — the novel axis — stayed coarse: one long paragraph per artist, single-shot MiniLM embedding.

V2's proximity is already right: plain Jaccard on ~10 Last.fm artist tags. Leave it alone.

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

### 3. Add a small eval harness

**Problem:** With n=20 and 190 pairs, median thresholding is noisy. No way to tell if a pipeline change actually improved results vs. just shuffled the noise.

**Change:** Create `data/eval_pairs.json` — a hand-labeled set of ~30 pairs with expected quadrant assignments:
- ~10 pairs expected basilect (high discourse, low tag)
- ~10 pairs expected deep scene (high discourse, high tag)
- ~10 pairs expected surface-only (low discourse, high tag)

Add `scripts/eval.py`:
- Load eval pairs and computed matrices
- Report how many pairs land in their expected quadrant
- Report ranking stability: does the pair's relative position hold across runs / model swaps?

This is the ground truth the project currently lacks. Without it, every change is vibes.

### 4. Test embedding model sensitivity

**After** chunks + eval harness are in place:
- Run eval with `all-MiniLM-L6-v2` (current)
- Run eval with one larger model (e.g., `all-mpnet-base-v2`)
- Compare eval scores

Don't swap models until you can measure the difference. The eval harness has to come first.

---

## What this plan does NOT do

- Touch proximity. It's a control variable. Plain Jaccard stays.
- Add tag enrichment, album tags, MusicBrainz, soft Jaccard, synonym maps. That's what v3 did. It was wrong.
- Scale the artist set. Stay at 20 until the pipeline is validated.
- Add visualization, curation layers, or UI. Downstream of validation.

---

## Execution order

1. **Chunk profiles** — update node schema, write chunks for all 20 artists
2. **Update embed.py** — chunk-level embedding + median aggregation
3. **Build eval pairs** — hand-label ~30 pairs from current results + listening
4. **Write eval.py** — quadrant accuracy + ranking stability
5. **Re-run pipeline** — embed → compute → discover → eval
6. **Compare** — do chunked embeddings score better on eval than whole-profile?
7. **Model swap test** — only if step 6 shows the pipeline is eval-stable

Each step is independently testable. No step depends on a later step.

---

## Success criteria

- Eval harness exists and produces a repeatable score
- Chunked discourse embeddings score >= whole-profile on eval (or we learn why not)
- Orthogonality test still shows r < 0.3 (discourse and proximity remain independent axes)
- No new complexity in the proximity pipeline
