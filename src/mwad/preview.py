#!/usr/bin/env python3
"""Make a technical terrain preview, not an Amiga-rendered screenshot."""
import argparse
import json
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LightSource, LinearSegmentedColormap


def preview(area, output):
    from .paths import ensure_external
    area = ensure_external(area, "area data")
    output = ensure_external(output, "preview output")
    if output.exists():
        raise ValueError("Preview output already exists; choose a new name")
    output.parent.mkdir(parents=True, exist_ok=True)
    grids = json.loads((area / "terrain-source.json").read_text())
    audit = json.loads((area / "audit.json").read_text())
    placements = json.loads((area / "placements.json").read_text())
    xmin, ymin = np.min([g["cell"] for g in grids], axis=0)
    xmax, ymax = np.max([g["cell"] for g in grids], axis=0)
    h = np.full(((ymax - ymin + 1) * 64 + 1, (xmax - xmin + 1) * 64 + 1), np.nan)
    for g in grids:
        x, y = g["cell"]
        x0, y0 = (x - xmin) * 64, (y - ymin) * 64
        h[y0:y0 + 65, x0:x0 + 65] = g["heights"]
    x = xmin + np.arange(h.shape[1]) / 64
    y = ymin + np.arange(h.shape[0]) / 64
    xx, yy = np.meshgrid(x, y)
    cmap = LinearSegmentedColormap.from_list("land", ["#59776c", "#a7ad79", "#dbc89e"])
    rgb = LightSource(azdeg=310, altdeg=50).shade(np.maximum(h, 0), cmap=cmap, dx=128, dy=128,
                                               vert_exag=1, blend_mode="soft")
    rgb[h < 0] = [0.14, 0.28, 0.35, 1]
    fig = plt.figure(figsize=(14, 7), facecolor="#f4f2eb")
    ax = fig.add_axes([.065, .16, .4, .65])
    ax.imshow(rgb, origin="lower", extent=(x[0], x[-1], y[0], y[-1]))
    ax.contour(xx, yy, h, levels=[0], colors=["#dfe9d4"], linewidths=.8)
    for cx in np.arange(xmin, xmax + 1.01, .25):
        ax.axvline(cx, color="white", lw=.4, alpha=.28)
    for cy in np.arange(ymin, ymax + 1.01, .25):
        ax.axhline(cy, color="white", lw=.4, alpha=.28)
    npc = [r for r in placements if r.get("type") == "NPC_"]
    ax.scatter([r["position"][0]/8192 for r in npc], [r["position"][1]/8192 for r in npc],
               c="#ffd58a", s=18, edgecolors="#413a29", linewidths=.5, label="NPC placements", zorder=5)
    for c in audit["area"]["cells"]:
        if c["name"] == "Seyda Neen":
            ax.text(c["x"]+.5, c["y"]+.87, "Seyda Neen", ha="center", fontsize=9,
                    color="white", bbox={"facecolor":"#193239", "alpha":.8, "edgecolor":"none", "pad":3})
    ax.set(xlabel="Exterior cell X", ylabel="Exterior cell Y / north",
           title=f"Decoded terrain · {audit['area']['chunks']} streaming chunks")
    ax.legend(loc="lower left", fontsize=9)
    ax2 = fig.add_axes([.49, .14, .47, .69], projection="3d")
    step = 4
    hh = np.maximum(h[::step, ::step], 0)
    ax2.plot_surface(xx[::step, ::step], yy[::step, ::step], hh / 8192,
                     rstride=1, cstride=1, facecolors=rgb[::step, ::step], edgecolor="#253b36",
                     linewidth=.22, antialiased=True, shade=False)
    ax2.view_init(elev=36, azim=-118)
    ax2.set_box_aspect((1, 1, .25))
    ax2.set_axis_off()
    ax2.set_title("Coarse terrain study · sample stride 4", pad=2)
    fig.text(.065, .92, "SEYDA NEEN / FIRST DATA EXTRACTION", fontsize=20, weight="bold", color="#16353b")
    fig.text(.065, .865, "Actual Morrowind heights and NPC positions. Analytical colours; sea clamped to zero in the 3D view.", fontsize=10, color="#4e5f61")
    fig.text(.065, .065, "PC-generated inspection view. Buildings, trees, texture baking and the Amiga renderer are not included.", fontsize=10, color="#4e5f61")
    fig.savefig(output, dpi=160, facecolor=fig.get_facecolor())
    plt.close(fig)


