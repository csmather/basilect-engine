---

kanban-plugin: basic

---

## Now

- [ ] **Aesthetic-axis projection** (post-A pivot) — pick 5–8 poles musicians actually argue about (spontaneity↔deliberation, inwardness↔communication, reverence↔iconoclasm, maximalism↔minimalism, studio-as-instrument↔studio-as-documentation, genre-committed↔indifferent, etc.). LLM scores each artist on each axis with quote-grounded justification + confidence. Similarity becomes geometric in this low-D interpretable space. Replaces mean-pooled cosine as primary scoring path. May need refinement / more dimensions to capture minutiae.
- [ ] **Tighten `extract-artist` SKILL.md** — drop pure interjections, reactive fragments, single-clause non-content quotes (the kind that drag artists toward register-match neighbors)
- [ ] **Re-extract `danny_brown` first** — most concentrated case of register-match suspicion (73 quotes, 30% under 30 words, top neighbors include 1 likely false positive)
- [ ] Port `state.json` checkpointing from fork
- [ ] Port `pathfind.py` from fork (Dijkstra similarity chains)


## Later

- [ ] **B: corpus expansion** — podcasts (Broken Record, Song Exploder, Tetragrammaton), yt-dlp auto-captions. Also helps test whether n=25 register-effect generalizes
- [ ] Re-extract / re-scrape other heavy-corpus artists once tightened skill is settled
- [ ] **C: CLAP/MuQ-MuLan audio embeddings** as diagnostic channel (never re-ranker)
- [ ] Play with Nomic Atlas for data exploration


## Parked

- [ ] **Retrieval-based LLM judgment** over top-K quote pairs — natural follow-on to aesthetic-axis projection if axis-based scoring needs sharpening. Cosine for retrieval, LLM judgment for ranking. Re-uses cached `quote_embeddings.npy` + `explain.py` infra. Needs refinement on judgment prompt + how to aggregate per-pair judgments to artist-pair score before pursuing.
- [ ] **Collaboration-graph orthogonality re-ranker** — would operationalize "invisible to collab graph, visible to discourse" as the product framing. Deferred: at current scale (n=25, plausibly to n~500) the smell-test on personal music knowledge is sufficient; pulling MusicBrainz/Last.fm related-artist data isn't worth the lift yet.
- [ ] **Late-interaction / max-of-pairs aggregation** — appealing on theory grounds, but rewrite cost is high and small-n results don't yet justify
- [ ] **Mean-center before cosine** — tested via `compare_pooling.py`; mean ≈ median (ρ=0.989), no meaningful reorganization
- [ ] **BM25 as sparse second-opinion layer**


## Rejected

- [ ] Automated genre-distance re-ranking (GATSY 2024 confirms: genre supervision hurts)
- [ ] Critic-discourse signal, curated tag vocab, Claude-authored summaries
- [ ] Vector DB, Flask app, dashboard infra


## Bugs

- [ ] (none open — all three prior bugs resolved by validation pass + meta recompute on 2026-04-23)


## Done

**Complete**

- [x] **2026-04-25: A investigation cycle complete.** Three diagnostics on n=25:<br>• Rank-overlap (MiniLM vs Qwen3) via `compare_encoders.py`: Spearman ρ=+0.716 adj, Jaccard@10=0.569 adj over 300 pairs. ~40% top-10 turnover — encoder swap is reorganizing, not just rescaling. Output: `data/encoder_comparison.json`.<br>• Pooling (median/mean/max) via `compare_pooling.py`: mean ≈ median (ρ=+0.989, Jaccard@10=0.907). Max collapses (std=0.008, all pairs in [0.899, 0.945]). Aggregation is not the bottleneck. Output: `data/pooling_comparison.json`.<br>• Quote-length filter via `probe_quote_length.py`: only T=30 reorganizes danny_brown's neighborhood (rappers → producers/process artists), at heavy cost — real pair bladee↔danny drops rank 4→10. Uniform length cutoff too coarse.<br>• Manual review of 5 most-promoted Qwen3 pairs via `explain.py`: 4 real (bjork↔sophie, bladee↔danny, clairo↔kate_bush, danny↔kate_bush), 1 register-match false positive (danny↔earl). All findings on n=25; treat as suggestive not definitive. Pivot: extraction quality is the next lever, not aggregation.
- [x] **2026-04-25: `explain.py` shipped** — loads cached per-quote vectors, prints top-K quote pairs with text + raw/adjusted artist-pair score in header. `embed.py` now also writes `data/quote_embeddings.npy` + `data/quote_index.json` so explain runs without re-encoding.
- [x] **2026-04-25: Encoder swap to Qwen3-Embedding-4B** (bf16, local). Spread *tightened* not widened — std 0.078→0.047 raw, 0.068→0.036 adjusted. Stability up (Jaccard@10 0.799→0.873). Sparsity correlation up (ρ 0.617→0.756). Compression hypothesis from NOTES.md:88 reversed; new investigation queued. Diagnostics overlay in `data/diagnostics.html`; MiniLM baseline kept at `data/diagnostics_baseline.json` and `data/embeddings_minilm.npy`.
- [x] **2026-04-23: Validation pass on borrowed 11** — 507→382 quotes, 125 drops (24.5% pollution). Catastrophic wrong-source errors in burial/sophie/danny_brown/kate_bush; minor reporter-paraphrase + external-prose drops elsewhere.
- [x] **2026-04-23: Control audit on original 14** — 0/70 sampled drops, baseline confirmed clean.
- [x] **2026-04-23: `corpus_meta` recomputed** on all 25 with 4-digit-year regex; old fork date-parser bugs resolved. Many artists flag invalid on year-count due to missing source dates, not quote quality (`corpus_valid` = data-quality flag, not usability flag — noted in CLAUDE.md).
- [x] **2026-04-23: Motegi clause codified in memory** — inside-collective voice only; all external voices out (including relayed quotes via collaborators, per prior Nujabes/Shing02 decision).




%% kanban:settings
```
{"kanban-plugin":"basic"}
```
%%
