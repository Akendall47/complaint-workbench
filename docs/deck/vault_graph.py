"""Draw the research vault as a graph for the deck: one dot per note, one line per [[link]], coloured by folder.
A plain force layout with a fixed seed, so the picture is the same every run. Run: uv run python docs/deck/vault_graph.py"""
import re
from pathlib import Path

import numpy as np

VAULT = Path(__file__).resolve().parents[2] / "vault"
OUT = Path(__file__).parent / "vault-graph.svg"
COLOUR = {"research": "#c34756", "concepts": "#224d74", "decisions": "#3e8778", "features": "#e5b922", "maps": "#587da8", "": "#1a272e"}  # Ankura palette

notes = {p.stem: p.parent.name if p.parent != VAULT else "" for p in VAULT.rglob("*.md") if ".obsidian" not in p.parts}
names = sorted(notes)
index = {n: i for i, n in enumerate(names)}
edges = set()
for p in VAULT.rglob("*.md"):
    if ".obsidian" in p.parts:
        continue
    for target in re.findall(r"\[\[([^\]|#]+)", p.read_text(encoding="utf-8")):
        if target in index and target != p.stem:
            edges.add(tuple(sorted((index[p.stem], index[target]))))
edges = np.array(sorted(edges))

# Fruchterman-Reingold: linked notes pull together, all notes push apart.
rng = np.random.default_rng(7)
n = len(names)
pos = rng.uniform(-1, 1, (n, 2))
k = 1.6 / np.sqrt(n)
for step in range(400):
    delta = pos[:, None, :] - pos[None, :, :]
    dist = np.linalg.norm(delta, axis=2) + 1e-6
    force = (delta / dist[..., None] * (k * k / dist)[..., None]).sum(axis=1)
    d = pos[edges[:, 0]] - pos[edges[:, 1]]
    dl = np.linalg.norm(d, axis=1)[:, None] + 1e-6
    pull = d / dl * (dl * dl / k)
    np.add.at(force, edges[:, 0], -pull)
    np.add.at(force, edges[:, 1], pull)
    force -= pos * 0.02  # a weak pull to the centre keeps loose notes on the page
    t = 0.1 * (1 - step / 400) + 0.002
    length = np.linalg.norm(force, axis=1)[:, None] + 1e-6
    pos += force / length * np.minimum(length, t)

W, H, M = 900, 760, 40
lo, hi = pos.min(axis=0), pos.max(axis=0)
xy = M + (pos - lo) / (hi - lo) * [W - 2 * M, H - 2 * M]
degree = np.bincount(edges.ravel(), minlength=n)
lines = "".join(f'<line x1="{xy[a][0]:.1f}" y1="{xy[a][1]:.1f}" x2="{xy[b][0]:.1f}" y2="{xy[b][1]:.1f}"/>' for a, b in edges)
dots = "".join(f'<circle cx="{xy[i][0]:.1f}" cy="{xy[i][1]:.1f}" r="{3 + 1.6 * np.sqrt(degree[i]):.1f}" fill="{COLOUR[notes[nm]]}"><title>{nm}</title></circle>'
               for i, nm in enumerate(names))
OUT.write_text(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img" aria-label="The research vault: {n} notes and {len(edges)} links">'
               f'<g stroke="#c9c9d6" stroke-width="0.8" stroke-opacity="0.7">{lines}</g><g stroke="white" stroke-width="1.2">{dots}</g></svg>', encoding="utf-8")
print(f"{n} notes, {len(edges)} links, wrote {OUT.name}")
