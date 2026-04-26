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

**Current status (2026-04-25):** D complete; A investigation cycle complete (encoder swap + rank-overlap + pooling + length-filter). **Bottleneck has moved to extraction**, not encoding/aggregation.

- **D (diagnostics)** — DONE. Findings: D2 stability passed (Jaccard@10=0.799); D1 sparsity artifact confirmed (ρ=+0.617) and corrected in-pipeline via `compute.py`'s `log(min_count)` adjustment rather than via a quote-count minimum (keeps underground artists in — they're the point); D3 compression still present but wider floor than before, motivating A.
- **A.1 — encoder swap done, surprising result.** Qwen3-Embedding-4B (bf16, 2560-dim) replaced MiniLM-L6-v2 (384-dim). Expected: wider spread proving MiniLM was the bottleneck. Got: *tighter* spread. Raw std 0.078→0.047, adjusted std 0.068→0.036; mean shifted up 0.706→0.822 (raw), 0.700→0.817 (adjusted). Stability *improved* (Jaccard@10 0.799→0.873) and sparsity correlation *worsened* (ρ 0.617→0.756, p=1.3e-5). MiniLM vectors preserved at `data/embeddings_minilm.npy`. The "MiniLM compression is the ceiling" reading from the old D3 was wrong: a richer model produces *more* clustering on a creative-process-themed corpus, not less.
- **A.2 — rank-overlap analysis (`compare_encoders.py`).** Spearman ρ=+0.716 adj, Jaccard@10=0.569 adj over 300 pairs between MiniLM and Qwen3. ~40% top-10 turnover. Encoder swap is **reorganizing**, not just rescaling. Output: `data/encoder_comparison.json`.
- **A.3 — pooling probe (`compare_pooling.py`).** Loaded cached per-quote vectors and re-pooled three ways. Mean ≈ median (Spearman ρ=+0.989, Jaccard@10=0.907) — they agree on essentially everything. Max collapses (std drops to 0.008, all pairs land in [0.899, 0.945]; per-dim max in 2560-d almost certainly fires *somewhere* across 30+ quotes, so every artist's vector looks alike). The "median-pool collapse in high-d" hypothesis is **not confirmed** — central-tendency operators land in the same place, neither dominates the other. Aggregation is not the bottleneck. Output: `data/pooling_comparison.json`.
- **A.4 — quote-length filter probe (`probe_quote_length.py`).** Drop quotes < N words before pooling. Only T=30 meaningfully reorganizes danny_brown's neighborhood (rappers → producers/process artists, e.g. nujabes/skrillex/arthur_verocai promoted), but at heavy cost: real pair bladee↔danny falls from rank 4 to rank 10, clairo↔kate_bush degrades 1/2 → 3/4. Uniform length cutoff is too coarse — it dings burial's substantive 13-word lines while preserving danny's longer-but-tonally-loaded ones. Even longer rapper quotes encode register strongly enough to keep the "Detroit MC" cluster intact at T=15.
- **A.5 — explain.py shipped.** Loads cached per-quote vectors (no re-encoding) and prints top-K quote pairs with text + the artist-pair raw/adjusted score in header. Used for manual review of 5 most-promoted Qwen3 pairs (`bjork↔sophie`, `burial↔danny_brown`, `danny_brown↔earl_sweatshirt`, `bladee↔danny_brown`, `danny_brown↔kate_bush`, `clairo↔kate_bush`): 4 real, 1 false positive (danny↔earl matched on shared profanity/short-emphatic register, not creative philosophy).
- **What the investigation actually proved (n=25 caveat):** Qwen3 encodes register strongly at the per-quote level — short reactive quotes ("This shit is fire!") embed with measurable rapper-energy direction. Pooling can't separate it (mean = median = same problem; max = worse). Length-filtering can partially fix it but only at aggressive cutoffs that also delete real signal. **The lever is upstream — extraction quality.** This is suggestive, not definitive: 25 artists is a small sample, and the danny_brown register effect could be specific to him + his corpus mix or a more general Qwen3 property. Corpus expansion (B) would help disambiguate.
- **B (corpus expansion via podcasts)** is now also a methodology check, not just a data-volume play: more artists with high quote counts (esp. non-rapper) would test whether the register-effect generalizes.
- **C (audio orthogonality)** last because: adding signals prematurely is exactly what the fork got wrong. Pure audio via CLAP as a diagnostic ("is this pair actually genre-far?") — never a re-ranker. Also partially addresses the "orthogonality between similarity axes" gap the research doc flags.

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

- **Encoder is now `Qwen3-Embedding-4B`** (bf16, 2560-dim, 32K context, last-token pooling, no prompt prefix for symmetric document embedding). Loaded from `models/Qwen3-Embedding-4B/` via sentence-transformers. Default attention (sdpa); flash-attn 2 not installed but encoding is ~12s for 802 quotes anyway. `embed.py` and `diagnose.py` both updated. `embed.py` also writes per-quote vectors to `data/quote_embeddings.npy` + `data/quote_index.json` for downstream tools (`explain.py`, `compare_pooling.py`, `probe_quote_length.py`) to consume without re-encoding.
- Spread is *tighter* than MiniLM, not wider. Don't re-derive the old "compression motivates encoder swap" conclusion from MiniLM-era stats; the encoder swap is done and the new encoder is more compressed.
- **Median-pool collapse hypothesis: probed and not confirmed.** `compare_pooling.py` shows mean ≈ median (Spearman ρ=+0.989, Jaccard@10=0.907) on Qwen3 embeddings — the two central-tendency operators land in the same place in 2560-d. Max collapses much harder (per-dim max in high-d picks up *something* in nearly every dimension). Don't reach for a pooling change to fix specific bad pairings; it won't.
- **Register-encoding quirk (n=25 — suggestive only):** Qwen3 appears to encode linguistic register (cadence, vocab, profanity, short emphatic delivery) strongly enough at the per-quote level to drive false-positive artist pairings when artists share that register. Smoking gun: `danny_brown ↔ earl_sweatshirt` ranked #1/#2 on shared "rapper energy" rather than creative-process semantics — confirmed via `explain.py`. Pooling alternatives don't fix it (A.3); uniform quote-length filtering only helps at T=30, with collateral damage to real pairs (A.4). Productive lever is extraction-side filtering (drop pure interjections, reactive fragments). May not generalize beyond n=25; corpus expansion will test.
- Data sparsity STILL drives rankings — under Qwen3-4B the correlation is stronger (ρ=+0.756, p=1.3e-5) than under MiniLM (ρ=+0.617, p=0.001). The `compute.py` log(min_count) adjustment still applies; refits on every run. Adjusted scores are what `discover.py` ranks on; raw is kept alongside as `score_raw`. Note: `corpus_valid=False` still tracks metadata completeness (missing source dates), not usability — thin-corpus artists stay in the pipeline and get count-adjusted.
