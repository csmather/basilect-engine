# Notes

Working reference for basilect. State, rationale, context. Actionable items live in `TODO.md`.

---

## Corpus state (2026-04-23, post-validation)

**25 artists total: 14 original + 11 borrowed from fork. Borrowed pruned; meta recomputed.**

**Original 14** (0/70 control-sample drops, quality confirmed):
animal_collective, arthur_verocai, astrid_sonne, badbadnotgood, bill_evans, bladee, boy_harsher, clairo, fishmans, nujabes, radiohead, skrillex, tame_impala, yung_lean

**Borrowed 11** (post-prune counts, was 507→382 total, 24.5% pollution):
danny_brown (73q, was 99), sophie (51q, was 90), arca (58q, unchanged), joanna_newsom (54q, was 56), burial (13q, was 48), brian_eno (32q, was 35), earl_sweatshirt (30q, was 34), bjork (23q, was 26), kate_bush (15q, was 22), kaija_saariaho (15q, was 20), frank_ocean (18q, was 19)

**Validation pass findings (2026-04-23):**
Pollution was concentrated in 4 artists with catastrophic wrong-source errors:
- **burial**: idx 0-34 were a different Berlin-based composer entirely (record "Idol" about the Hypogeum) — 73% pollution
- **sophie**: idx 17-55 were two wrong Sophies — a pop singer on a Sting tour, then Sophie Muller the music video director — 43% pollution
- **danny_brown**: idx 0-25 were Wikipedia article summary prose, not interview quotes — 26% pollution
- **kate_bush**: idx 11-16 were a Kate Bush tribute-show performer at Harrogate Theatre — 32% pollution

Minor pollution in the others: reporter paraphrase ("Bjork said that…"), fragments, external-collaborator third-person (Mälkki on Saariaho). All dropped per the Motegi clause (see memory).

**Post-prune schema/metadata:**
- Schema still `{text, publication, date}` — `url` field not backfilled (non-blocking).
- `corpus_meta` recomputed with robust 4-digit-year regex. 12/25 artists now flag `corpus_valid=False`, almost entirely due to missing source dates in scraped articles (not a parser bug). `corpus_valid` is a data-quality flag, not a usability flag — failing artists still go through the pipeline.

---

## Plan direction rationale

Priority: **D → A → B → C**

- **D (diagnostics) first** because: output currently reads as noisy, some pairs land well, but we don't know if that's signal or artifact. Before any rescrape / re-extract / model swap, confirm the engine has signal above noise. Fits the "stability not accuracy" validation frame.
- **A (methodology upgrade) second** because: assuming D shows signal, the next highest-leverage change is model + aggregation + interpretability, not more data. The `all-MiniLM-L6-v2` encoder is a 2021-era 384-dim model; 12GB VRAM on the 5070 supports far better.
- **B (corpus expansion via podcasts) third** because: interview text is a bounded well (<10 good long-form pieces per artist). Podcasts = same signal type, much more volume. But only after methodology is solid — don't pump new data into an unvalidated pipeline.
- **C (audio orthogonality) last** because: adding signals prematurely is exactly what the fork got wrong. Pure audio via CLAP as a diagnostic ("is this pair actually genre-far?") — never a re-ranker. Also partially addresses the "orthogonality between similarity axes" gap the research doc flags.

---

## What was learned from the fork (tangyraccoon/basilect-engine, v5)

**Worth stealing** (queued in TODO):
- `state.json` per-artist checkpoints — resume-safe pipeline
- `pathfind.py` — Dijkstra over `(1 - similarity)` for similarity chains + alternate paths
- `explain.py` — for any pair, surface top-K quote pairs driving the score

**What to avoid** (confirmed by seeing it fail at scale):
- Multi-signal linear blend with hand-tuned weights (`0.4*quote + 0.2*critic + 0.2*influence + 0.2*tag`)
- Curated tag vocabulary (DIY, analog, multi_instrumental, etc.) — hand-labeling dressed up as LLM output
- Claude-authored theme summaries (`taste_profile.py --explain` uses Sonnet to write prose)
- Haiku-only extraction at scale without human review — polluted corpora with critic prose
- Dead-artist / pre-internet gap not flagged (`2pac/quotes.json` empty in fork)
- Scope creep: 36KB Flask server, 92KB SPA, 41KB monitor, 4 batch orchestrators, 24KB 7-phase 20k-artist plan before the 14-artist version was validated

**Fork infra worth considering later:** Haiku + Message Batches API for extraction (~50% discount, ~$0.007–$0.04/artist claimed). Only after extraction quality is validated on small scale.

---

## Research-landscape context

Full bibliography with verifiable URLs: `docs/research/bibliography.md`. Full deep-research doc: `docs/research/mapping_musicsim_landscape.md` (LLM-generated lit review, citations are real but numeric claims should be spot-checked).

Key takeaways:
- **Artist self-discourse as similarity signal = genuine white space.** No published precedent. This is basilect's core novelty.
- **Closest precedent: Badillo-Goicoechea 2025 (HDSR)** — 22k-artist graph from critic namedrops, Dijkstra/max-flow for bridge-artist discovery. Basilect is the mirror (self-discourse, not critic-discourse). Complementary.
- **GATSY 2024** — genre supervision hurts artist-similarity performance. External validation for rejecting the genre-distance layer.
- **"Orthogonality between similarity axes" is an acknowledged-open gap since Ellis/Whitman 2002.** A future C-phase diagnostic (audio vs. self-discourse similarity) would be a lightweight contribution to that gap.
- **Untapped adjacent corpora** beyond interviews: podcasts, liner notes, RateYourMusic enthusiast lists. Podcasts are the natural next lever (B phase).

---

## Tooling notes

- **Embedding model candidates** (12GB VRAM, 5070): `BAAI/bge-large-en-v1.5` (1024-dim, ~1.3GB), `nomic-embed-text-v1.5` (768-dim, strong long-context), `mixedbread-ai/mxbai-embed-large-v1`. API alternative: Voyage-3-large / Cohere embed-v3 (pennies at 25-artist scale).
- **Nomic Atlas** — cheap way to explore quote-level clusters in 2D without building viz infra. Worth trying.
- **Visualization** — Claude-generated stats/viz on demand is currently fine. No need for standalone tooling yet.
- **Long-term** — standalone webapp to run basilect on its own. Far off.

---

## Known quirks

- `all-MiniLM-L6-v2` (current encoder) is 384-dim, 2021-era, generic NLI training. Likely a major source of score compression (0.70–0.85 band).
- Median-pooling over 30+ quotes per artist may smear signal toward a generic "interview discourse" centroid. Unconfirmed — D will help clarify.
- Data sparsity may be partly driving current rankings: invalid-corpus artists (nujabes, arthur_verocai, bill_evans) cluster at the bottom of `discoveries.json`, which could be semantic OR could be a function of having fewer quotes. Rank-vs-quote-count correlation check will tell us. Note: most post-recompute `corpus_valid=False` flags are driven by missing source dates rather than quote scarcity — the flag tracks metadata completeness, not usability.
