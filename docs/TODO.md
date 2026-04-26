# TODO

Kanban. Keep short. Details live in `NOTES.md`.

## Now — curated-playlist / curator-graph signal (new branch)
The intent-dense flip side of CF: NTS shows, dublab, RA In Residence, niche YouTube curator playlists, compilation albums (Light in the Attic, Mr. Bongo, Soul Jazz, Music From Memory), Bandcamp Daily mixes, artist guest mixes / year-end lists / "sounds I love" features. Each artifact = tracklist + free-text thesis (show description, DJ bio, liner-note essay). N is in the thousands, not millions; intent density per artifact is high; fully LLM/NLP-tractable; not CF.

- [ ] Brainstorm to nail this down before building. Open questions: which curator universe to start with (NTS vs compilations vs artist self-curation each have different scrape difficulty + thesis density); co-presence-as-evidence vs thesis-fit-as-evidence (separate signals from same data); artist-name resolution across messy tracklists (likely MusicBrainz IDs as canonical); how this integrates with the eventual aesthetic-axis layer (additional evidence stream into shared axes vs separate similarity matrix that ensembles in)

## Next — aesthetic-axis projection + extraction cleanup (deferred from prior Now)
- [ ] Aesthetic-axis projection: pick 5–8 poles musicians actually argue about (spontaneity↔deliberation, inwardness↔communication, reverence↔iconoclasm, maximalism↔minimalism, studio-as-instrument↔studio-as-documentation, genre-committed↔indifferent, etc.). LLM scores each artist on each axis with quote-grounded justification + confidence. Similarity becomes geometric in this low-D interpretable space. Replaces mean-pooled cosine as the primary scoring path. May need refinement / more dimensions to capture minutiae. **Eventually: same axes, multiple evidence streams** (quotes + curator-graph thesis fits + later audio LLM-listening + lyrics).
- [ ] Tighten `.claude/skills/extract-artist/SKILL.md` — drop pure interjections, reactive fragments, single-clause non-content quotes (the kind that drag artists toward register-match neighbors)
- [ ] Re-extract `danny_brown` first — most concentrated case of register-match suspicion (73 quotes, 30% under 30 words, top neighbors include 1 likely false positive)
- [ ] Port `state.json` checkpointing from fork
- [ ] Port `pathfind.py` from fork (Dijkstra similarity chains)

## Later
- [ ] B: corpus expansion — podcasts (Broken Record, Song Exploder, Tetragrammaton), yt-dlp auto-captions. Also helps test whether n=25 register-effect generalizes
- [ ] Re-extract / re-scrape other heavy-corpus artists once the tightened skill is settled
- [ ] C: CLAP/MuQ-MuLan audio embeddings as diagnostic channel (never re-ranker)
- [ ] Play with Nomic Atlas for data exploration
- [ ] Far-off / multimodal: full multi-evidence fusion across discourse + curator-graph + audio LLM-listening + lyrics, all feeding the shared aesthetic-axis layer. Right structurally; not chasing soon, focus is one substrate at a time

## Parked (need more explanation before touching)
- Retrieval-based LLM judgment over top-K quote pairs — natural follow-on to aesthetic-axis projection if axis-based scoring needs sharpening. Cosine for retrieval, LLM judgment for ranking. Re-uses cached `quote_embeddings.npy` + `explain.py` infra. Needs refinement on judgment prompt + how to aggregate per-pair judgments to artist-pair score before pursuing.
- Collaboration-graph orthogonality re-ranker — would operationalize "invisible to collab graph, visible to discourse" as the product framing. Deferred: at current scale (n=25, plausibly to n~500) the smell-test on personal music knowledge is sufficient; pulling MusicBrainz/Last.fm related-artist data isn't worth the lift yet.
- Audio→LLM-listening as input to aesthetic-axis layer — feed raw audio to a frontier multimodal model (Claude/Gemini multimodal, native audio) and have it produce critic-level decomposition (named harmonic moves, mix decisions, structural choices, allusion-spotting). Different signal from CLAP cosine: LLM extracts named musical facts using all music theory + music writing in pretraining; CLAP only pattern-matches in caption-distribution space. Cost-per-call non-trivial, only matters once axis layer is solid.
- Listening-trajectory geometry from Last.fm scrobble sequences — sequence-model timestamped scrobble streams, embed each artist by its position in the listener-discovery topology. Catches "gateway dependency" connections (artists discovered at similar points in personal taste evolution) that static playlist co-occurrence flattens. Distinct from SASRec/BERT4Rec next-track prediction.
- Sampling / cover lineage with LLM-read source taste — what an artist samples is a strong aesthetic-stance signal independent of scene (Madlib obscure Brazilian funk, Daft Punk obscure French film soundtracks). LLM reads sample annotations to characterize source-material taste in plain language. WhoSampled is the obvious data source but Spotify acquired November 2025 and almost certainly powers their DNA feature — access trajectory uncertain, may need alternative data.
- Late-interaction / max-of-pairs aggregation — appealing on theory grounds, but rewrite cost is high and small-n results don't yet justify
- Mean-center before cosine — tested via `compare_pooling.py`; mean ≈ median (ρ=0.989), no meaningful reorganization
- BM25 as sparse second-opinion layer

## Rejected / out of scope
- Automated genre-distance re-ranking (GATSY 2024 confirms: genre supervision hurts)
- Critic-discourse signal, curated tag vocab, Claude-authored summaries
- Vector DB, Flask app, dashboard infra

## Bugs
(none open — all three prior bugs resolved by validation pass + meta recompute on 2026-04-23)

## Done
- 2026-04-25: A investigation cycle complete. Three diagnostics on n=25:
  - **Rank-overlap (MiniLM vs Qwen3)** via `compare_encoders.py`: Spearman ρ=+0.716 adj, Jaccard@10=0.569 adj over 300 pairs. ~40% top-10 turnover — encoder swap is reorganizing, not just rescaling. Output: `data/encoder_comparison.json`.
  - **Pooling (median/mean/max)** via `compare_pooling.py`: mean ≈ median (ρ=+0.989, Jaccard@10=0.907). Max collapses (std=0.008, all pairs in [0.899, 0.945]). Aggregation is not the bottleneck. Output: `data/pooling_comparison.json`.
  - **Quote-length filter** via `probe_quote_length.py`: only T=30 reorganizes danny_brown's neighborhood (rappers → producers/process artists), at heavy cost — real pair bladee↔danny drops rank 4→10. Uniform length cutoff too coarse.
  - Manual review of 5 most-promoted Qwen3 pairs via `explain.py`: 4 real (bjork↔sophie, bladee↔danny, clairo↔kate_bush, danny↔kate_bush), 1 register-match false positive (danny↔earl). All findings on n=25; treat as suggestive not definitive. Pivot: extraction quality is the next lever, not aggregation.
- 2026-04-25: `explain.py` shipped — loads cached per-quote vectors, prints top-K quote pairs with text + raw/adjusted artist-pair score in header. `embed.py` now also writes `data/quote_embeddings.npy` + `data/quote_index.json` so explain runs without re-encoding.
- 2026-04-25: Encoder swap to Qwen3-Embedding-4B (bf16, local). Spread *tightened* not widened — std 0.078→0.047 raw, 0.068→0.036 adjusted. Stability up (Jaccard@10 0.799→0.873). Sparsity correlation up (ρ 0.617→0.756). Compression hypothesis from NOTES.md:88 reversed; new investigation queued. Diagnostics overlay in `data/diagnostics.html`; MiniLM baseline kept at `data/diagnostics_baseline.json` and `data/embeddings_minilm.npy`.
- 2026-04-23: Validation pass on borrowed 11 — 507→382 quotes, 125 drops (24.5% pollution). Catastrophic wrong-source errors in burial/sophie/danny_brown/kate_bush; minor reporter-paraphrase + external-prose drops elsewhere.
- 2026-04-23: Control audit on original 14 — 0/70 sampled drops, baseline confirmed clean.
- 2026-04-23: `corpus_meta` recomputed on all 25 with 4-digit-year regex; old fork date-parser bugs resolved. Many artists flag invalid on year-count due to missing source dates, not quote quality (`corpus_valid` = data-quality flag, not usability flag — noted in CLAUDE.md).
- 2026-04-23: Motegi clause codified in memory — inside-collective voice only; all external voices out (including relayed quotes via collaborators, per prior Nujabes/Shing02 decision).
