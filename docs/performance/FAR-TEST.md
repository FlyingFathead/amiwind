# The far test (`aw_cull`, `dbg cull`)

_Last updated with AmiWind v0.0.42-rc1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Choosing it in the game](#choosing-it-in-the-game)
- [The fog-exact test (`aw_cull 2`)](#the-fog-exact-test-aw_cull-2)
- [Detail options (`aw_cull 3` to `6`)](#detail-options-aw_cull-3-to-6)
- [Measurements](#measurements)
- [What each option visibly costs](#what-each-option-visibly-costs)
- [Counters](#counters)

<!-- contents end -->

Which brush models (placed meshes) and faces the renderer leaves out at a distance. Brush
models are 60-79 % of the 3D view on a slow 68040 in Balmora, and 40-63 % of the faces they
send come from models in the far half of the draw distance
([renderer counters](RENDERER-COUNTERS.md), `dbg rcount 3`). This page is step 1 of the
render speed plan: draw the same picture with less work first, then offer detail options
that change the picture for the maintainer to judge.

| `aw_cull` | Far test | Picture |
| --- | --- | --- |
| 0 | none | everything in the potentially visible set is drawn |
| 1 | the far plane: a world node, leaf or model whose nearest point lies more than the draw distance + 16 ahead of the eye is left out (the method since v0.0.31; menu: Full) | the reference |
| 2 | 1 plus the **fog-exact test** below | identical to 1 |
| 3 | 2 plus the size-scaled cut-off, light preset | changes: small distant models go earlier |
| **4** (default from v0.0.42) | 2 plus the size-scaled cut-off, strong preset (menu: Strong) | changes more |
| 5 | 2 plus the far detail step | changes a few pixels |
| 6 | 4 and 5 together | changes |
| 7 | debug view: the fog-exact test without its colour checks (works with `aw_fog 0`, to see what it leaves out), and the line where the fog pass's sky ray crosses the horizon marked | debug only |

## Choosing it in the game

Escape > Options > **Far detail**, the row under the fog distance: Enter, Left or Right steps
through the four settings worth choosing:

| Menu | `dbg cull` | What it draws |
| --- | --- | --- |
| Full | 1 | everything up to the fog (the picture of v0.0.41; kept by configurations saved before v0.0.42) |
| Light | 3 | small and medium distant models drop out a little sooner |
| Strong | 4 | the default: distant models drop out sooner by size; 17-27 % less 3D time at the benchmark cameras |
| Strong + small faces | 6 | Strong, and tiny faces of distant buildings left out as well |

The choice is saved with the other settings (`config.cfg`) and comes back the next time. In the
F10 console, `dbg cull 4` (or `aw_cull 4`) sets the same thing; the other values in the table
above are for testing and read "Custom" in the menu.

`dbg cull on` is 1, `dbg cull off` is 0. Every value stays selectable.

**Strong is the default from v0.0.42** (decided by the maintainer, 17 October 2026): it took 17-27 % off
the 3D view time at the five Balmora benchmark cameras on the slow 68040 preset (below). What it
costs: distant small and medium objects drop out before the fog has hidden them, for example
hanging lanterns, signs, crates and the tops of towers far down a street. Choose Full in the
menu (or `dbg cull 1`) to draw everything up to the fog again.

A fresh install starts at Strong. A saved configuration from before v0.0.42 (which never held
this setting) keeps Full, the picture that player had, until Strong is chosen in the menu; every
later choice is saved. Measurements from before 17 October 2026 were all taken at Full; compare
new ones with them at `dbg cull 1`.

## The fog-exact test (`aw_cull 2`)

A model, or one face of it, is left out only where drawing it changes no pixel. Palette fog
(`AW_FogDraw`) maps a pixel to fog level 15 when its z-buffer value (32768 / depth, as
`D_DrawZSpans` writes it) is at most `819200 / (25 x distance)`, and level 15 of the colour
table maps every colour to one colour. Something may be left out when all of this holds:

1. **Every pixel it would cover is level 15.** All its vertices (a model: all corners of its
   box) lie deeper than `32768 / (limit + 0.5)`. On a plane 1/z is affine in screen position
   and every pixel the span renderer covers lies inside the projected polygon, so no covered
   pixel is nearer than the nearest vertex.
2. **Whatever it would hide also turns into that colour.** Geometry behind it is deeper, so
   level 15 too. Sky behind it lies strictly below the horizon of the fog pass's sky ray
   (ray z < 0): there the day/night sky pass maps every colour to the full fog colour (no
   sun halo, moon, stars or glow below it). The engine checks this every frame for all 256
   colours, and checks that level 15 of the table is one colour; if either fails, nothing is
   left out. The distant land layers draw the same colour.
3. **It hides no flame drawn after the fog pass.** Static fires, guard torches and the
   player's torch are drawn after fogging with a depth test. The limit in 1 is lowered to the
   smallest z-buffer value any flame particle that can land on screen may have this frame,
   so geometry that could cover a flame is kept.

The sky ray's z is `vpn.z + u * vright.z + v * vup.z` with `u`, `v` the pixel's offsets from
the screen centre; with Quake's projection (`R_EmitEdge`) that times the view depth is linear
in the view coordinates, so 2 is also a half-space: one dot product per vertex for each of the
two tests. A model pass is tested on its box (all of it hidden: not drawn at all; partly:
its faces are tested one by one before the world-tree walk); each face costs two dot
products per vertex, and only for models that straddle the full-fog depth below the horizon.

Off with the object-silhouetting horizon (`aw_skyline_fill 1`, which marks columns from
fogged scenery), in interiors, with `aw_fog 0`, and without the day/night tables.

What it can and cannot save: the far plane already drops nodes and models past
`distance + 16`; the test removes what lies between the full-fog depth (~541 at the default
540) and the far side of the leaves that straddle the far plane, below the horizon. Models
centred beyond the fog plane mostly still show: their near halves are partly fogged and their
upper parts stand against the sky, where a fogged silhouette differs from the sky colour.

## Detail options (`aw_cull 3` to `6`)

- **Size-scaled cut-off** (3, 4): a placement whose near side (centre depth less its radius)
  lies past a share of the draw distance is left out. Light (3): radius under 32 past 50 %,
  32-128 past 75 %, larger as before. Strong (4): under 32 past 40 %, 32-128 past 60 %,
  128-512 past 85 %, 512 and over as before.
- **Far detail step** (5): for models of radius 32 and more centred in the far half, a front
  face whose largest extent covers fewer than 2 pixels at its nearest vertex is left out.

## Measurements

Far detail labels: "Full" = `aw_cull 1`, "Strong" = `aw_cull 4`. 16-17 October 2026, FS-UAE x14 cycle-exact 68040 preset (49.7 MHz, emulator-relative times),
the five Balmora benchmark cameras ([HARDWARE-BENCHMARK.md](../HARDWARE-BENCHMARK.md)), noon
held, day/night cycle off, headlamp off, NPC movers off, one engine binary for every value
(no code-layout difference between the variants), each value switched in place at the same
pose; medians of 6-8 one-second `dbg rcount` lines. View = `R_RenderView` milliseconds (the
3D view; the cycle-exact view time repeats to 0.1-0.3 ms). Pixels: a paused frame per value,
compared with `aw_cull 1`; animated water and distant movers are masked by the pixels that
differ between four `aw_cull 1` frames and three `aw_cull 2` frames of the same session.

| Camera | `aw_cull 1` view ms (front faces / fragments / BSP nodes) | 2: fog-exact | 3: size, light | 4: size, strong | 5: detail step | 6: strong + detail |
| --- | --- | --- | --- | --- | --- | --- |
| Balmora 1 | 1,530.5 (3,829 / 5,917 / 42,027) | +0.8 % (4 faces left out) | -9.6 % | -18.8 % | -4.9 % | -20.2 % |
| Balmora 2 | 1,244.9 (2,707 / 4,023 / 26,289) | **-3.2 %** (132 faces; fragments -6 %) | -14.6 % | -21.3 % | -9.0 % | -23.8 % |
| Balmora 3 | 719.5 (2,085 / 2,746 / 20,409) | +0.5 % (3 faces) | -4.7 % | -27.0 % | +1.7 % | -26.7 % |
| Balmora 4 | 1,020.3 (2,129 / 2,906 / 21,991) | +0.9 % (3 faces) | -12.3 % | -22.6 % | -3.9 % | -23.9 % |
| Balmora 5 | 869.2 (2,153 / 2,219 / 21,831) | +0.7 % (23 faces) | -1.3 % | -17.1 % | -3.6 % | -18.9 % |
| Pixels changed (outside the noise mask) | - | **0 at all five** (Balmora 3 and 5 byte-identical frames) | 0-755 | 40-4,524 | 151-333 | 213-4,814 |

- **Fog-exact (2):** the picture is identical, as designed. It finds little to leave out: the
  far plane already stops at the draw distance + 16, and the full-fog depth is ~541 at the
  default 540, so only geometry in the overhang of leaves straddling the far plane and below
  the horizon qualifies (3-132 front faces). Where it finds enough (Balmora 2) the view is
  3.2 % faster; elsewhere its per-frame checks and face tests cost 0.4-0.8 %.
- **Size-scaled cut-off (3, 4):** the largest saving, mostly from medium and large models
  (radius 32-512) in the far half, where 40-63 % of the sent faces are. Visible: distant
  houses and props drop out while still partly coloured through the fog.
- **Far detail step (5):** drops 32-636 front faces under 2 pixels across (17 % of the
  clipped faces at Balmora 1) for 151-333 changed pixels; 4-9 % faster at four cameras, 1.7 %
  slower at Balmora 3, where it found only 32 faces to drop.
- Frames for each value and camera (labelled, for the maintainer's comparison) are kept with the
  private measurement notes; they are not part of the repository.

## What each option visibly costs

Seen in the paused frames of the five cameras and in walking clips (a 360-degree turn and a
walk) at two places, compared with Full:

| Camera / route | Light (3) | Strong (4) |
| --- | --- | --- |
| Balmora 1 (street) | a few pixels of a distant building's outline | the hanging lantern over the street and the distant building outline beyond it are gone |
| Balmora 1, walking north up the street | - | the stone bridge's arches and some rooftop pieces across the river drop out well before the fog |
| Balmora 2 | almost nothing (9 pixels) | distant props and pieces of buildings across the view |
| Balmora 3 (arrival) | nothing | nothing |
| Balmora 4 | small pieces of the far bridge | the right half of the stone bridge's arches |
| Balmora 5 / walking west across open ground | a few distant pieces | distant towers and the far bridge drop out earlier |

The far detail step (5) changes 151-333 pixels per camera (small far faces); Strong + small
faces (6) is Strong plus that. Where something drops out it pops as you walk towards it,
at a distance set by its size; the near street and everything within about 40-60 % of the
draw distance are unchanged.

Measured with the v0.0.41 release image, which has the flat-sky regression
[SKY-FLAT-PALETTE-DRIFT-41](../bugs/SKY-FLAT-PALETTE-DRIFT-41.md) (no clouds). The sky pixels
are the same with Full and Strong (0 of 78,100 differ, looking 30 degrees up). The figures and
clips will be taken again on a build with the sky fixed.

**Default:** Strong (see above); Full until v0.0.41.

## Counters

`dbg rcount` prints `ft on/depth/why models/faces/size/detail`: the share of frames (percent)
the fog-exact test applied, its depth, why it was off (1 no fog or no day/night tables, 2 the
skyline fill, 3 level 15 not one colour, 4 the sky below the horizon not that colour, 5 a
flame left nothing provable), then the model passes and front faces it left out, the passes
the size cut dropped and the faces the detail step dropped.

`dbg cull` takes on/off as before; `aw_cull` is no longer in the boolean registry
(`aw_boolean.h`), so 2 to 7 are accepted (`cvar.c`).

Tests: `tests/aga_culling_test.c` (full-fog depth against the fog table for every distance,
the half-spaces against the fog pass's own sky ray for random views and eye heights, the
colour checks, flames, interiors, the presets).
