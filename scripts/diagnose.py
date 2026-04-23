"""D-phase diagnostics: signal-vs-noise audit of the current pipeline.

Runs three diagnostics in-memory (does NOT overwrite canonical embeddings):
  D1  rank-vs-quote-count correlation (sparsity artifact check)
  D2  bootstrap stability: drop 20% of quotes per artist, N=20 reruns,
      Jaccard@10 overlap vs canonical top-10
  D3  score-distribution spread of all pairwise similarities

Emits a single self-contained HTML file at data/diagnostics.html.
"""

import json
from pathlib import Path

import numpy as np
from scipy.stats import spearmanr
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
ARTISTS_DIR = DATA_DIR / "artists"
OUT_PATH = DATA_DIR / "diagnostics.html"
MODEL_NAME = "all-MiniLM-L6-v2"
N_BOOTSTRAP = 20
DROP_FRAC = 0.20
TOP_K = 10
RNG_SEED = 1


def load_quotes():
    ids, quotes, meta = [], [], []
    for path in sorted(ARTISTS_DIR.glob("*/quotes.json")):
        node = json.loads(path.read_text(encoding="utf-8"))
        texts = [q["text"] for q in node["quotes"]]
        if not texts:
            continue
        ids.append(path.parent.name)
        quotes.append(texts)
        meta.append(node.get("corpus_meta", {}))
    return ids, quotes, meta


def median_pool(quote_embs_list):
    return np.array([np.median(v, axis=0) for v in quote_embs_list])


def top_k_neighbors(sim, k):
    n = sim.shape[0]
    result = []
    for i in range(n):
        scores = sim[i].copy()
        scores[i] = -np.inf
        idx = np.argsort(-scores)[:k]
        result.append(set(idx.tolist()))
    return result


def jaccard(a, b):
    return len(a & b) / len(a | b) if (a | b) else 0.0


def main():
    ids, quotes, meta = load_quotes()
    n = len(ids)
    counts = np.array([len(q) for q in quotes])
    total = int(counts.sum())
    print(f"Loaded {n} artists, {total} quotes")

    print(f"Loading {MODEL_NAME}...")
    model = SentenceTransformer(MODEL_NAME)

    flat = []
    bounds = []
    off = 0
    for qs in quotes:
        flat.extend(qs)
        bounds.append((off, off + len(qs)))
        off += len(qs)

    print("Encoding all quotes once...")
    quote_embs = model.encode(flat, show_progress_bar=True, convert_to_numpy=True)
    per_artist = [quote_embs[a:b] for (a, b) in bounds]

    # Canonical embeddings + similarity
    artist_vecs = median_pool(per_artist)
    sim = cosine_similarity(artist_vecs)

    # --- D3: score-distribution spread ---
    upper = np.triu_indices(n, k=1)
    pair_scores = sim[upper]

    # Adjusted scores: linear fit of score ~ log(min corpus depth), then
    # residual + prediction-at-median-depth. Puts every pair on the scale
    # of "what would this score be if both artists had a median corpus?"
    pair_min_count = np.minimum(counts[upper[0]], counts[upper[1]])
    log_min = np.log(pair_min_count)
    slope, intercept = np.polyfit(log_min, pair_scores, 1)
    predicted = slope * log_min + intercept
    median_log = float(np.median(log_min))
    baseline = slope * median_log + intercept
    adjusted_scores = pair_scores - predicted + baseline

    def dist_stats(arr):
        return {
            "scores": arr.tolist(),
            "mean": float(arr.mean()),
            "std": float(arr.std()),
            "min": float(arr.min()),
            "max": float(arr.max()),
            "p05": float(np.percentile(arr, 5)),
            "p95": float(np.percentile(arr, 95)),
            "iqr": float(np.percentile(arr, 75) - np.percentile(arr, 25)),
        }

    d3 = {
        "raw": dist_stats(pair_scores),
        "adjusted": dist_stats(adjusted_scores),
        "fit": {
            "slope": float(slope),
            "intercept": float(intercept),
            "median_log_min_count": median_log,
            "baseline": float(baseline),
        },
    }

    # --- D1: rank vs quote count ---
    # mean similarity across each artist's n-1 pairs (diagonal masked)
    mask = ~np.eye(n, dtype=bool)
    mean_sim_per_artist = (sim * mask).sum(axis=1) / (n - 1)

    # mean global rank: build pair ranking, for each artist take mean rank of pairs involving it
    pairs = []
    for i in range(n):
        for j in range(i + 1, n):
            pairs.append((i, j, sim[i, j]))
    pairs.sort(key=lambda p: -p[2])
    ranks = {}
    for r, (i, j, _) in enumerate(pairs, start=1):
        ranks.setdefault(i, []).append(r)
        ranks.setdefault(j, []).append(r)
    mean_rank_per_artist = np.array([np.mean(ranks[i]) for i in range(n)])

    rho_sim, p_sim = spearmanr(counts, mean_sim_per_artist)  # type: ignore[misc]
    rho_rank, p_rank = spearmanr(counts, mean_rank_per_artist)  # type: ignore[misc]
    d1 = {
        "ids": ids,
        "quote_counts": counts.tolist(),
        "mean_sim": mean_sim_per_artist.tolist(),
        "mean_rank": mean_rank_per_artist.tolist(),
        "corpus_valid": [bool(m.get("corpus_valid", False)) for m in meta],
        "spearman_sim": {"rho": float(rho_sim), "p": float(p_sim)},  # type: ignore[arg-type]
        "spearman_rank": {"rho": float(rho_rank), "p": float(p_rank)},  # type: ignore[arg-type]
    }

    # --- D2: bootstrap stability ---
    canonical_top = top_k_neighbors(sim, TOP_K)
    rng = np.random.default_rng(RNG_SEED)
    per_artist_jaccards = [[] for _ in range(n)]
    global_jaccards_per_run = []

    print(f"\nRunning {N_BOOTSTRAP} bootstrap iterations (drop {int(DROP_FRAC * 100)}%)...")
    for _ in range(N_BOOTSTRAP):
        dropped = []
        for vecs in per_artist:
            k = len(vecs)
            keep_n = max(1, int(round(k * (1 - DROP_FRAC))))
            idx = rng.choice(k, size=keep_n, replace=False)
            dropped.append(vecs[idx])
        vecs_b = median_pool(dropped)
        sim_b = cosine_similarity(vecs_b)
        top_b = top_k_neighbors(sim_b, TOP_K)
        js = []
        for i in range(n):
            j = jaccard(canonical_top[i], top_b[i])
            per_artist_jaccards[i].append(j)
            js.append(j)
        global_jaccards_per_run.append(float(np.mean(js)))

    per_artist_mean_jaccard = [float(np.mean(x)) for x in per_artist_jaccards]
    per_artist_std_jaccard = [float(np.std(x)) for x in per_artist_jaccards]
    order = np.argsort(per_artist_mean_jaccard)  # least-stable first
    d2 = {
        "ids": ids,
        "quote_counts": counts.tolist(),
        "mean_jaccard": per_artist_mean_jaccard,
        "std_jaccard": per_artist_std_jaccard,
        "sort_order": order.tolist(),
        "global_mean": float(np.mean(per_artist_mean_jaccard)),
        "global_median": float(np.median(per_artist_mean_jaccard)),
        "per_run_mean": global_jaccards_per_run,
        "n_bootstrap": N_BOOTSTRAP,
        "drop_frac": DROP_FRAC,
        "top_k": TOP_K,
    }

    payload = {
        "n_artists": n,
        "n_quotes": total,
        "model": MODEL_NAME,
        "d1": d1,
        "d2": d2,
        "d3": d3,
    }

    html = render_html(payload)
    OUT_PATH.write_text(html, encoding="utf-8")
    print(f"\nWrote {OUT_PATH}")
    print(f"\nSummary:")
    print(f"  D1 Spearman(count, mean_sim)  rho={float(rho_sim):+.3f} p={float(p_sim):.3g}")  # type: ignore[arg-type]
    print(f"  D1 Spearman(count, mean_rank) rho={float(rho_rank):+.3f} p={float(p_rank):.3g}")  # type: ignore[arg-type]
    print(f"  D2 global mean Jaccard@{TOP_K} = {d2['global_mean']:.3f}")
    r, a = d3["raw"], d3["adjusted"]
    print(f"  D3 raw      : mean={r['mean']:.3f} std={r['std']:.3f} range=[{r['min']:.3f}, {r['max']:.3f}]")
    print(f"  D3 adjusted : mean={a['mean']:.3f} std={a['std']:.3f} range=[{a['min']:.3f}, {a['max']:.3f}]")
    print(f"  D3 fit slope={d3['fit']['slope']:+.4f} (score vs log(min count))")


def render_html(p):
    data_json = json.dumps(p)
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>basilect diagnostics — n={p['n_artists']}</title>
<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.1/dist/chart.umd.min.js"></script>
<style>
  :root {{
    --bg: #0f1115; --panel: #171a21; --fg: #e6e6e6; --dim: #8a8f98;
    --accent: #6ea8fe; --warn: #f1b55b; --ok: #7fd6a0; --bad: #e56b6b;
    --border: #262a33;
  }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; padding: 24px 32px; font: 14px/1.5 ui-sans-serif, system-ui, sans-serif;
         background: var(--bg); color: var(--fg); }}
  h1 {{ margin: 0 0 4px; font-size: 22px; font-weight: 600; }}
  h2 {{ margin: 0 0 12px; font-size: 16px; font-weight: 600; color: var(--accent); }}
  .sub {{ color: var(--dim); margin-bottom: 24px; font-size: 13px; }}
  .grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }}
  .panel {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px;
            padding: 18px; }}
  .panel.full {{ grid-column: 1 / -1; }}
  .stats {{ display: flex; flex-wrap: wrap; gap: 16px 28px; font-size: 13px; color: var(--dim);
            margin-bottom: 14px; }}
  .stats b {{ color: var(--fg); font-weight: 600; }}
  .verdict {{ font-size: 13px; color: var(--dim); margin-top: 12px; padding-top: 12px;
              border-top: 1px dashed var(--border); }}
  .verdict b {{ color: var(--fg); }}
  canvas {{ background: transparent; }}
  code {{ background: #0a0c10; padding: 1px 6px; border-radius: 3px; color: var(--warn); }}
</style>
</head>
<body>
<h1>basilect — D-phase diagnostics</h1>
<div class="sub">n={p['n_artists']} artists, {p['n_quotes']} quotes · encoder: <code>{p['model']}</code></div>

<div class="grid">

  <div class="panel full">
    <h2>D3 — Score distribution spread (raw)</h2>
    <div class="stats" id="d3-stats"></div>
    <canvas id="d3" height="120"></canvas>
    <div class="verdict" id="d3-verdict"></div>
  </div>

  <div class="panel full">
    <h2>D3 — Score distribution spread (count-adjusted)</h2>
    <div class="stats" id="d3adj-stats"></div>
    <canvas id="d3adj" height="120"></canvas>
    <div class="verdict" id="d3adj-verdict"></div>
  </div>

  <div class="panel">
    <h2>D1 — Rank vs. quote count</h2>
    <div class="stats" id="d1-stats"></div>
    <canvas id="d1" height="220"></canvas>
    <div class="verdict" id="d1-verdict"></div>
  </div>

  <div class="panel">
    <h2>D2 — Bootstrap stability (Jaccard@{p['d2']['top_k']})</h2>
    <div class="stats" id="d2-stats"></div>
    <canvas id="d2" height="220"></canvas>
    <div class="verdict" id="d2-verdict"></div>
  </div>

</div>

<script>
const DATA = {data_json};

function fmt(x, d=3) {{ return x.toFixed(d); }}
function pct(x) {{ return (100*x).toFixed(1) + '%'; }}

// ---- D3: histograms of pair scores (raw + count-adjusted) ----
(function() {{
  const raw = DATA.d3.raw, adj = DATA.d3.adjusted;
  // Shared x-axis range so both histograms are visually comparable.
  const lo = Math.min(raw.min, adj.min);
  const hi = Math.max(raw.max, adj.max);
  const pad = (hi - lo) * 0.02 || 0.01;
  const axisMin = lo - pad, axisMax = hi + pad;
  const bins = 30;
  const width = (axisMax - axisMin) / bins;
  const labels = Array.from({{length: bins}}, (_, i) => (axisMin + (i + 0.5) * width).toFixed(2));

  function histogram(scores) {{
    const counts = new Array(bins).fill(0);
    for (const s of scores) {{
      let b = Math.floor((s - axisMin) / width);
      if (b < 0) b = 0;
      if (b >= bins) b = bins - 1;
      counts[b]++;
    }}
    return counts;
  }}

  function renderHist(canvasId, scores, color) {{
    new Chart(document.getElementById(canvasId), {{
      type: 'bar',
      data: {{ labels, datasets: [{{ label: 'pair count',
                data: histogram(scores), backgroundColor: color }}] }},
      options: {{
        plugins: {{ legend: {{ display: false }} }},
        scales: {{
          x: {{ title: {{ display: true, text: 'cosine similarity',
                         color: '#8a8f98' }}, ticks: {{ color: '#8a8f98' }}, grid: {{ color: '#262a33' }} }},
          y: {{ title: {{ display: true, text: 'pairs', color: '#8a8f98' }},
                ticks: {{ color: '#8a8f98' }}, grid: {{ color: '#262a33' }} }}
        }}
      }}
    }});
  }}

  function statsLine(d) {{
    return `<span>mean <b>${{fmt(d.mean)}}</b></span>` +
           `<span>std <b>${{fmt(d.std)}}</b></span>` +
           `<span>range <b>[${{fmt(d.min)}}, ${{fmt(d.max)}}]</b></span>` +
           `<span>p5–p95 <b>[${{fmt(d.p05)}}, ${{fmt(d.p95)}}]</b></span>` +
           `<span>IQR <b>${{fmt(d.iqr)}}</b></span>`;
  }}

  renderHist('d3', raw.scores, '#6ea8fe');
  renderHist('d3adj', adj.scores, '#b38cff');

  document.getElementById('d3-stats').innerHTML = statsLine(raw);
  document.getElementById('d3adj-stats').innerHTML = statsLine(adj);

  const oldBand = (raw.min >= 0.70 && raw.max <= 0.85);
  const narrow = (raw.p95 - raw.p05) < 0.15;
  document.getElementById('d3-verdict').innerHTML =
    `<b>Verdict:</b> ${{oldBand ? 'old 0.70–0.85 compression still holds.' :
      'no longer in the old 0.70–0.85 band.'}} ` +
    `${{narrow ? 'p5–p95 spread &lt; 0.15 — still compressed; MiniLM encoder is a likely bottleneck.'
               : 'p5–p95 spread ≥ 0.15 — scores are more spread than before.'}}`;

  const fit = DATA.d3.fit;
  const stdDelta = adj.std - raw.std;
  const iqrDelta = adj.iqr - raw.iqr;
  const baselineCount = Math.exp(fit.median_log_min_count).toFixed(0);
  const deltaDirection = stdDelta > 0 ? 'wider' : 'tighter';
  document.getElementById('d3adj-verdict').innerHTML =
    `<b>Fit:</b> score ≈ ${{fmt(fit.slope)}}·log(min_count) + ${{fmt(fit.intercept)}} — ` +
    `baselined at median depth (≈${{baselineCount}} quotes). ` +
    `<b>After adjustment:</b> std ${{stdDelta >= 0 ? '+' : ''}}${{fmt(stdDelta)}}, ` +
    `IQR ${{iqrDelta >= 0 ? '+' : ''}}${{fmt(iqrDelta)}} — distribution is ${{deltaDirection}} than raw. ` +
    `Adjusted scores answer: "what would this pair score if both artists had ≈${{baselineCount}} quotes?"`;
}})();

// ---- D1: rank vs quote count ----
(function() {{
  const d = DATA.d1;
  const points = d.ids.map((id, i) => ({{
    x: d.quote_counts[i], y: d.mean_sim[i], id,
    valid: d.corpus_valid[i]
  }}));
  const validPts = points.filter(p => p.valid);
  const invalidPts = points.filter(p => !p.valid);
  new Chart(document.getElementById('d1'), {{
    type: 'scatter',
    data: {{ datasets: [
      {{ label: 'corpus_valid', data: validPts, backgroundColor: '#7fd6a0',
         pointRadius: 5 }},
      {{ label: 'corpus_invalid', data: invalidPts, backgroundColor: '#f1b55b',
         pointRadius: 5 }}
    ]}},
    options: {{
      plugins: {{
        legend: {{ labels: {{ color: '#e6e6e6' }} }},
        tooltip: {{ callbacks: {{ label: c => `${{c.raw.id}} — ${{c.raw.x}} quotes, mean_sim=${{fmt(c.raw.y)}}` }} }}
      }},
      scales: {{
        x: {{ title: {{ display: true, text: 'quote count', color: '#8a8f98' }},
              ticks: {{ color: '#8a8f98' }}, grid: {{ color: '#262a33' }} }},
        y: {{ title: {{ display: true, text: 'mean similarity (to other 24)', color: '#8a8f98' }},
              ticks: {{ color: '#8a8f98' }}, grid: {{ color: '#262a33' }} }}
      }}
    }}
  }});
  const rho = d.spearman_sim.rho, pval = d.spearman_sim.p;
  const rhoR = d.spearman_rank.rho, pR = d.spearman_rank.p;
  document.getElementById('d1-stats').innerHTML =
    `<span>Spearman(count, mean_sim) ρ=<b>${{fmt(rho)}}</b> p=<b>${{pval.toExponential(1)}}</b></span>` +
    `<span>Spearman(count, mean_rank) ρ=<b>${{fmt(rhoR)}}</b> p=<b>${{pR.toExponential(1)}}</b></span>`;
  const strong = Math.abs(rho) >= 0.5 && pval < 0.05;
  const weak = Math.abs(rho) < 0.3 || pval > 0.1;
  let msg;
  if (strong) msg = `ρ=${{fmt(rho)}} — <b>strong sparsity artifact</b>: quote count materially drives similarity rankings.`;
  else if (weak) msg = `ρ=${{fmt(rho)}} — <b>no meaningful sparsity artifact</b>: rankings are not driven by quote count.`;
  else msg = `ρ=${{fmt(rho)}} — weak-to-moderate correlation; treat as partial artifact, not disqualifying.`;
  document.getElementById('d1-verdict').innerHTML = `<b>Verdict:</b> ${{msg}}`;
}})();

// ---- D2: bootstrap stability ----
(function() {{
  const d = DATA.d2;
  const order = d.sort_order;
  const labels = order.map(i => d.ids[i]);
  const means = order.map(i => d.mean_jaccard[i]);
  const stds = order.map(i => d.std_jaccard[i]);
  const counts = order.map(i => d.quote_counts[i]);
  new Chart(document.getElementById('d2'), {{
    type: 'bar',
    data: {{ labels, datasets: [{{
      label: `mean Jaccard@${{d.top_k}} over ${{d.n_bootstrap}} runs (drop ${{(d.drop_frac*100)|0}}%)`,
      data: means,
      backgroundColor: means.map(m => m >= 0.7 ? '#7fd6a0' : (m >= 0.5 ? '#f1b55b' : '#e56b6b'))
    }}]}},
    options: {{
      indexAxis: 'y',
      plugins: {{
        legend: {{ labels: {{ color: '#e6e6e6' }} }},
        tooltip: {{ callbacks: {{ label: c => {{
          const i = c.dataIndex;
          return `mean=${{fmt(means[i])}} ±${{fmt(stds[i])}}  (${{counts[i]}} quotes)`;
        }} }} }}
      }},
      scales: {{
        x: {{ min: 0, max: 1, title: {{ display: true, text: 'Jaccard@10 (1.0 = identical top-10)', color: '#8a8f98' }},
              ticks: {{ color: '#8a8f98' }}, grid: {{ color: '#262a33' }} }},
        y: {{ ticks: {{ color: '#8a8f98' }}, grid: {{ color: '#262a33' }} }}
      }}
    }}
  }});
  document.getElementById('d2-stats').innerHTML =
    `<span>global mean <b>${{fmt(d.global_mean)}}</b></span>` +
    `<span>global median <b>${{fmt(d.global_median)}}</b></span>` +
    `<span>bootstrap runs <b>${{d.n_bootstrap}}</b></span>` +
    `<span>drop <b>${{pct(d.drop_frac)}}</b></span>`;
  const g = d.global_mean;
  let msg;
  if (g >= 0.75) msg = `global mean Jaccard@${{d.top_k}} = ${{fmt(g)}} — <b>rankings are stable</b>: ~${{pct(g)}} top-10 overlap survives a 20% quote dropout.`;
  else if (g >= 0.55) msg = `global mean Jaccard@${{d.top_k}} = ${{fmt(g)}} — <b>moderately stable</b>: signal persists but edges are noisy.`;
  else msg = `global mean Jaccard@${{d.top_k}} = ${{fmt(g)}} — <b>fragile</b>: top-10 rearranges badly under 20% dropout.`;
  document.getElementById('d2-verdict').innerHTML = `<b>Verdict:</b> ${{msg}} Least-stable artists at top of chart.`;
}})();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
