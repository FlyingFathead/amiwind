"""Prepare a small 33x33 height lattice and a four-plane native HUD."""
import json
import math
from pathlib import Path
from mwad.paths import ensure_external


def prepare_walk(area, out, data_files=None):
    from PIL import Image, ImageDraw, ImageFont
    area = ensure_external(area, "terrain area")
    out = ensure_external(out, "terrain build")
    grids = json.loads((area / "terrain-source.json").read_text())
    cells = {tuple(g["cell"]): g["heights"] for g in grids}
    expected = {(x, y) for y in range(-10, -7) for x in range(-3, 0)}
    if len(grids) != 9 or set(cells) != expected:
        raise ValueError("Walking experiment requires the default nine-cell Seyda Neen export")
    heightmap = [[0] * 193 for _ in range(193)]
    for (x, y), heights in cells.items():
        if len(heights) != 65 or any(len(row) != 65 for row in heights):
            raise ValueError("Invalid terrain height grid")
        for iy, row in enumerate(heights):
            for ix, h in enumerate(row):
                if not isinstance(h, (int, float)) or not math.isfinite(h):
                    raise ValueError("Terrain heights must be finite numbers")
                heightmap[(y + 10) * 64 + iy][(x + 3) * 64 + ix] = h
    lines = ["        section walk_geometry,data", "walk_vertices:"]
    for y in range(33):
        for x in range(33):
            h = round(max(0, heightmap[y * 6][x * 6]) / 16)
            if not 0 <= h <= 1024:
                raise ValueError("Height exceeds this bounded renderer's arithmetic range")
            lines.append(f"        dc.w {x * 48},{y * 48},{h}")
    fine_heights = []
    fine_colours = []
    for y in range(97):
        for x in range(97):
            source_h = heightmap[y * 2][x * 2]
            h = round(max(0, source_h) / 16)
            if not 0 <= h <= 1024:
                raise ValueError("Height exceeds this bounded renderer's arithmetic range")
            fine_heights.append(h)
            # Analytical colours, not original texture pixels.
            dx = heightmap[y * 2][min(192, x * 2 + 2)] - heightmap[y * 2][max(0, x * 2 - 2)]
            dy = heightmap[min(192, y * 2 + 2)][x * 2] - heightmap[max(0, y * 2 - 2)][x * 2]
            colour = 1 if source_h <= 0 else 5 if abs(dx) + abs(dy) > 180 else 3 if dx - dy < -20 else 2
            fine_colours.append(colour)
    palette = [0x678, 0x345, 0x565, 0x786, 0x677, 0x887, 0x678, 0xdc9]
    colour_bake = {"scope": "Analytical colours for synthetic/standalone terrain tests"}
    if data_files is not None:
        from bake_terrain import bake_colours
        fine_colours, palette, colour_bake = bake_colours(data_files, area, grids, heightmap, out)
    palette += [0x222,0x432,0x554,0x764,0x986,0xba8,0x675,0x998]
    lines += ["solid_palette:", "        dc.w " + ",".join(map(str, palette))]
    for name, values, directive in [("solid_heights", fine_heights, "dc.w"),
                                     ("solid_colours", fine_colours, "dc.b")]:
        lines += ["        even", name + ":"]
        for start in range(0, len(values), 16):
            lines.append("        " + directive + " " + ",".join(map(str, values[start:start+16])))
    maximum = max(fine_heights)
    bias = maximum + 9
    depths = list(range(16, 240, 8))
    lines += [f"SOLID_DELTA_BIAS equ {bias}", "        even", "solid_rows:"]
    for start in range(0, 97, 16):
        lines.append("        dc.w " + ",".join(str(y * 97) for y in range(start, min(97, start + 16))))
    lines += ["solid_depths:"]
    for depth in depths:
        reciprocal = round(128 * 256 / depth)
        lines += [f"        dc.w {depth},{reciprocal}", f"        dc.l solid_projection_{depth}"]
    for depth in depths:
        reciprocal = round(128 * 256 / depth)
        values = [(delta * reciprocal) >> 8 for delta in range(-bias, maximum - 8)]
        lines.append(f"solid_projection_{depth}:")
        for start in range(0, len(values), 16):
            lines.append("        dc.w " + ",".join(map(str, values[start:start+16])))
    lines += ["town_inks:"]
    for colour in range(16):
        values = [sum((mask if colour & (1 << p) else 0) << (8*p) for p in range(4)) for mask in (0xf0,0x0f)]
        lines.append("        dc.l " + ",".join(str(v) for v in values))
    lines += ["walk_sines:"]
    for start in range(0, 256, 16):
        values = [round(math.sin(i * math.tau / 256) * 256) for i in range(start, start + 16)]
        lines.append("        dc.w " + ",".join(map(str, values)))
    lines += ["        section walk_ui,data_c", "walk_hud:", '        incbin "converted/walk-hud.planes"']
    (out / "walking-assets.i").write_text("\n".join(lines) + "\n", encoding="ascii")
    image = Image.new("1", (320, 200), 0)
    draw = ImageDraw.Draw(image)
    font = ImageFont.load_default()
    draw.text((6, 5), "AMIWIND / SEYDA NEEN", font=font, fill=1)
    draw.text((6, 18), "006 / F6-F7 song / F8 battle", font=font, fill=1)
    draw.text((6, 178), "WASD: move   Mouse: look", font=font, fill=1)
    draw.text((6, 189), "Shift: run   Tab: view   Esc: exit", font=font, fill=1)
    raw = image.tobytes()
    if len(raw) != 8000:
        raise ValueError("Unexpected one-plane image size")
    (out / "converted/walk-hud.planes").write_bytes(raw * 4)
    return {"vertices": 1089, "grid": [33, 33], "spacing_world_units": 768,
            "camera_bounds_world_units": [512, 24064], "water": "heights below zero clamped to zero",
            "solid_grid": [97, 97], "solid_spacing_world_units": 256,
            "solid_columns": 80, "solid_depth_samples_default": 10,
            "fog_presets_world_units": [{"key": key, "band_start": base * 8, "opaque": base * 12}
                                         for key, base in [(1, 128), (2, 192), (3, 320)]],
            "camera_start_world_units": [-11200, -71504], "default_preset": "dense",
            "projection_lookup_bytes": len(depths) * (maximum * 2 + 1) * 2,
            "colour_bake": colour_bake,
            "scope": "Heightfield plus external town bake; conservative building footprints"}
