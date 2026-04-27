"""Render data/top_pairs.jsonl as an interactive force-directed graph.

Usage: python visualize.py
Output: data/graph.html (open in a browser).

Layout pipeline:
  1. spring_layout (Fruchterman-Reingold) for initial topology-respecting positions
  2. iterative overlap removal so no two node disks intersect (planets + moons feel)
  3. physics disabled in vis.js so panning/zooming is cheap
"""

import json
import math
from pathlib import Path

import networkx as nx
import numpy as np
from pyvis.network import Network
from scipy.spatial import cKDTree

DATA = Path("data/top_pairs.jsonl")
OUT = Path("data/graph.html")

pairs = [json.loads(line) for line in DATA.open()]

G = nx.Graph()
for p in pairs:
    G.add_edge(p["a"], p["b"], shows=p["shows"], eps=p["eps"])

nodes = list(G.nodes)
sizes = np.array([6.0 + G.degree(n) * 1.4 for n in nodes])

print(f"laying out {len(nodes)} nodes...")
pos = nx.spring_layout(G, weight=None, iterations=120, seed=7, k=0.25)
SCALE = 12000
coords = np.array([[pos[n][0] * SCALE, pos[n][1] * SCALE] for n in nodes])


def remove_overlaps(coords, radii, padding=3.0, max_iter=2000, step=0.5):
    """Iteratively push apart overlapping disks. Uses cKDTree.query_pairs to
    only consider candidate pairs each iteration (cheap when overlaps are sparse).
    """
    coords = coords.copy()
    search_radius = 2 * radii.max() + padding
    n_over = 0
    for it in range(max_iter):
        tree = cKDTree(coords)
        pairs = tree.query_pairs(search_radius, output_type="ndarray")
        if len(pairs) == 0:
            print(f"  no overlaps after {it} iterations")
            return coords
        i, j = pairs[:, 0], pairs[:, 1]
        diff = coords[j] - coords[i]
        dist = np.linalg.norm(diff, axis=-1)
        min_dist = radii[i] + radii[j] + padding
        mask = (dist < min_dist) & (dist > 0)
        n_over = int(mask.sum())
        if n_over == 0:
            print(f"  no overlaps after {it} iterations")
            return coords
        i, j, diff, dist, min_dist = i[mask], j[mask], diff[mask], dist[mask], min_dist[mask]
        unit = diff / dist[:, None]
        push = unit * ((min_dist - dist) * step * 0.5)[:, None]
        np.add.at(coords, j, push)
        np.add.at(coords, i, -push)
    print(f"  overlap removal stopped at max_iter={max_iter} ({n_over} pairs still overlap)")
    return coords


coords = remove_overlaps(coords, sizes, padding=3.0, max_iter=2000, step=0.5)

for i, n in enumerate(nodes):
    G.nodes[n]["x"] = float(coords[i][0])
    G.nodes[n]["y"] = float(coords[i][1])
    G.nodes[n]["size"] = float(sizes[i])
    G.nodes[n]["title"] = f"{n}\ndegree: {G.degree(n)}"


def _mix(c1, c2, f):
    return tuple(c1[i] + (c2[i] - c1[i]) * f for i in range(4))


def _fmt(c):
    return f"rgba({int(c[0])},{int(c[1])},{int(c[2])},{c[3]:.2f})"


HEATMAP_STOPS = [
    (0.00, (35, 60, 110, 0.10)),
    (0.30, (70, 130, 170, 0.22)),
    (0.60, (255, 240, 160, 0.55)),
    (1.00, (155, 25, 30, 0.95)),
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
    d["color"] = {"color": heatmap(t), "highlight": "rgba(255,255,255,0.7)"}

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
