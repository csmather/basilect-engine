# TODO

Kanban. Keep short. Details live in `NOTES.md`.

## Now
(empty — D complete, count-adjustment shipped; ready for A)

## Done
- 2026-04-23: D-phase audit (`scripts/diagnose.py` → `data/diagnostics.html`). Findings: D1 Spearman(quote_count, mean_sim) ρ=+0.617 (p=0.001) — sparsity artifact confirmed. D2 mean Jaccard@10=0.799 under 20% dropout — rankings stable. D3 raw spread mean=0.706 std=0.078; MiniLM compression persists but wider floor than old 0.70–0.85 band.
- 2026-04-23: Count-adjustment wired into pipeline. `compute.py` fits `score ~ log(min_count)` across all pairs, emits `similarity.npy` (raw) + `similarity_adjusted.npy` + `similarity_fit.json`. `discover.py` ranks on adjusted; raw kept as `score_raw` in `discoveries.json`. Underground-to-underground pairs are the beneficiaries.
- 2026-04-23: Validation pass on borrowed 11 — 507→382 quotes, 125 drops (24.5% pollution). Catastrophic wrong-source errors in burial/sophie/danny_brown/kate_bush; minor reporter-paraphrase + external-prose drops elsewhere.
- 2026-04-23: Control audit on original 14 — 0/70 sampled drops, baseline confirmed clean.
- 2026-04-23: `corpus_meta` recomputed on all 25 with 4-digit-year regex; old fork date-parser bugs resolved. Many artists flag invalid on year-count due to missing source dates, not quote quality (`corpus_valid` = data-quality flag, not usability flag — noted in CLAUDE.md).
- 2026-04-23: Motegi clause codified in memory — inside-collective voice only; all external voices out (including relayed quotes via collaborators, per prior Nujabes/Shing02 decision).

## Next — A (methodology upgrade, if D passes)
- [ ] Swap embedding model — `BAAI/bge-large-en-v1.5` or `nomic-embed-text-v1.5` local on 5070; Voyage-3 as API alt
- [ ] Port `state.json` checkpointing from fork
- [ ] Port `explain.py` from fork (top-K quote pairs driving each score)
- [ ] Port `pathfind.py` from fork (Dijkstra similarity chains)

## Later
- [ ] B: corpus expansion — podcasts (Broken Record, Song Exploder, Tetragrammaton), yt-dlp auto-captions
- [ ] C: CLAP/MuQ-MuLan audio embeddings as diagnostic channel (never re-ranker)
- [ ] Play with Nomic Atlas for data exploration

## Parked (need more explanation before touching)
- Mean-center before cosine — already tested other aggregations, stuck with median
- Late-interaction / max-of-pairs aggregation — scale concern unclear
- BM25 as sparse second-opinion layer

## Rejected / out of scope
- Automated genre-distance re-ranking (GATSY 2024 confirms: genre supervision hurts)
- Critic-discourse signal, curated tag vocab, Claude-authored summaries
- Vector DB, Flask app, dashboard infra

## Bugs
(none open — all three prior bugs resolved by validation pass + meta recompute on 2026-04-23)
