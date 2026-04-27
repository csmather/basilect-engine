"""Render data/top_pairs.jsonl as an interactive force-directed graph.

Usage: python visualize.py
Output: data/graph.html (open in a browser).

Layout is computed once via networkx.spring_layout, then physics is disabled
in vis.js so panning/zooming is cheap.
"""

import json
import math
from pathlib import Path

import networkx as nx
from pyvis.network import Network

DATA = Path("data/top_pairs.jsonl")
OUT = Path("data/graph.html")

pairs = [json.loads(line) for line in DATA.open()]

G = nx.Graph()
for p in pairs:
    G.add_edge(
        p["a"],
        p["b"],
        shows=p["shows"],
        eps=p["eps"],
    )

print(f"laying out {G.number_of_nodes()} nodes...")
pos = nx.spring_layout(G, weight=None, iterations=100, seed=7, k=0.12)
SCALE = 4500
for node, (x, y) in pos.items():
    G.nodes[node]["x"] = x * SCALE
    G.nodes[node]["y"] = y * SCALE
    deg = G.degree(node)
    G.nodes[node]["size"] = 6 + deg * 1.4
    G.nodes[node]["title"] = f"{node}\ndegree: {deg}"


def _mix(c1, c2, f):
    return tuple(c1[i] + (c2[i] - c1[i]) * f for i in range(4))


def _fmt(c):
    return f"rgba({int(c[0])},{int(c[1])},{int(c[2])},{c[3]:.2f})"


# cold (rare pairs) → hot (high-curator-recurrence pairs)
HEATMAP_STOPS = [
    (0.00, (40, 70, 130, 0.12)),
    (0.35, (90, 140, 180, 0.22)),
    (0.65, (220, 160, 70, 0.50)),
    (1.00, (255, 80, 70, 0.90)),
]


def heatmap(t):
    t = max(0.0, min(1.0, t))
    for i in range(len(HEATMAP_STOPS) - 1):
        a, b = HEATMAP_STOPS[i], HEATMAP_STOPS[i + 1]
        if t <= b[0]:
            f = (t - a[0]) / (b[0] - a[0]) if b[0] > a[0] else 0.0
            return _fmt(_mix(a[1], b[1], f))
    return _fmt(HEATMAP_STOPS[-1][1])


shows_vals = [d["shows"] for _, _, d in G.edges(data=True)]
log_min = math.log(max(1, min(shows_vals)))
log_max = math.log(max(shows_vals))
log_span = log_max - log_min or 1.0

for u, v, d in G.edges(data=True):
    t = (math.log(max(1, d["shows"])) - log_min) / log_span
    d["title"] = f"{u} ↔ {v}\nshows: {d['shows']}  eps: {d['eps']}"
    d["width"] = 0.025
    d["color"] = {
        "color": heatmap(t),
        "highlight": "rgba(255,255,255,0.7)",
    }

net = Network(
    height="100vh",
    width="100%",
    bgcolor="#0f1115",
    font_color="#e6e6e6",
    notebook=False,
    cdn_resources="remote",
)
net.from_nx(G)
net.set_options("""
{
  "physics": {"enabled": false},
  "edges": {
    "width": 0.025,
    "smooth": {"enabled": false},
    "scaling": {"min": 0.025, "max": 0.025}
  },
  "interaction": {"hover": true, "tooltipDelay": 120}
}
""")
net.write_html(str(OUT), notebook=False, open_browser=False)
print(f"wrote {OUT}  (nodes={G.number_of_nodes()}, edges={G.number_of_edges()})")
