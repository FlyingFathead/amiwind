# Distant terrain and sky gaps

_Last updated with AmiWind v0.0.45 (19 October 2026)._

The v0.0.29-dev3 source candidate adds a separate, optional resident LAND
background pass. In the console:

```text
aw_terrain_horizon 1
aw_horizon_stats
```

Use `aw_terrain_horizon 0` to restore the previous renderer. Zero remains the
default while native visual and frame-cost acceptance is pending. The switch is
saved with the other configuration variables. The pass requires exterior fog;
turning off fog also turns off this fully fogged background.

## What it corrects

The detailed renderer stops visiting distant BSP nodes at the fog boundary.
Some discarded nodes contain opaque ground. A textured sky can therefore appear
where that ground should continue, even when its geometry is already resident.

The additional pass projects the actual upward-facing LAND polygons beyond the
detailed draw distance and paints them with the current fully fogged colour.
It uses the existing camera projection and inverse-depth buffer. Nearer terrain,
water, trees and other scenery keep their normal depth priority; overlapping
distant terrain also resolves by depth. This restores a terrain skyline from
its real geometry, including slopes and valleys, without interpreting a tree or
roof as a mountain peak or filling an entire screen column below an arbitrary
object.

The converter identifies LAND with `g<decimal material id>` textures. Only
those surfaces in the world model are eligible, and only when their effective
normal points upward. Water, sky, brush bottoms, vertical closures and placed
models are excluded. Collision, PVS, detailed draw distance, clouds and asset
files remain unchanged.

## Limits and cost

This is a **resident LAND correction**, not a whole-island distant world.
It cannot recover a mountain formed by an omitted rock mesh, terrain outside
the loaded region, or an unsupported hole in the input geometry. Those need
their own source-bound representation. The separately recorded Ashlands rock
visibility report remains open.

The pass allocates no heap memory and uses no surface-cache or edge-cache
entries. It admits at most 8,192 world faces and 64 original vertices per face.
An oversized world disables this pass; a malformed or oversized individual
face is skipped. `aw_horizon_stats` reports LAND/examined faces, projected
polygons, scan rows, written pixels, rejected faces and the world-budget flag.
Keep these limitations visible when evaluating a scene.

The new 68040 object is about 2.7 KiB of code plus 28 bytes of static counters;
temporary polygon vertices use about 1.5 KiB on the stack. These are object and
scratch sizes, not total engine memory or a frame-time guarantee.

## Verification and remaining acceptance

The actual C rasterizer passes an independent ray/plane oracle across 30 camera
and surface combinations, covering pitch, yaw, roll, viewport offsets, far
clipping and differing projection scales. Additional checks cover shared edges,
depth overlap, foreground protection, genuine gaps, material exclusions,
closure faces and malformed/budget-limited input. A no-background control fails
the same geometry oracle. Existing selected sky, night/cloud and culling tests
also pass in Linux Docker; the new module compiles for 68040/FPU.

A terrain-only comparison using the reported Bitter Coast region restores
1,645, 1,444 and 1,251 missing viewport pixels at three approximate reported
camera positions, with no false terrain coverage or nearer-depth overrides in
those samples. These are source-raster checks, not native full-scene acceptance.
The sampled pass projects 906, 711 and 599 polygons respectively. Host timing
does not establish Amiga performance.

Before enabling by default, obtain matched native OFF/ON/OFF captures at fixed
position, view angles and clock, including all three reported views. Check
nearby crossings, coastline and water, looking down, changed FOV and nighttime.
Measure actual target frame cost and counters, verify that genuine gaps remain
open, and retain the old-mode switch.

See [the bug journal](journals/BUG_JOURNAL-v0.0.29.md#land-horizon-gaps-29-sky-visible-through-distant-resident-ground-open)
and [the separate horizon study](history/plans/PLAN-v0.0.29.md#distant-terrain-topology-and-occlusion-study).

## Horizon draw methods (v0.0.32)

| Setting | Method | Status |
| --- | --- | --- |
| `aw_skyline_fill 0` (default, from the game config) | Land-outline horizon: far scenery ends at the fog distance and the sky stays sky, as before the skyline fill (v0.0.30). | Default. |
| `aw_skyline_fill 1` (`dbg skyline fill 1`) | Object silhouetting: in each screen column, sky below far scenery at fog level 12 or more takes the fog colour (added in v0.0.31-dev5, on in v0.0.31). | Experimental and buggy (sprites need their shapes from the alpha channel); tested but subpar results; kept for future improvement. |
| `aw_terrain_horizon 1` | The resident LAND pass described above. | Opt-in, unchanged. |

The subpar result of the silhouetting: far trees near the fog distance turn the sky below them into
solid fog-colour columns, for example a canopy-shaped block behind Seyda Neen's town wall and a wall
of spikes to the north-west of the town. A saved configuration from before this default is reset
once by `aw_horizon_migrate` (run from `quake.rc` after `config.cfg`); a later explicit choice
stays. Details: [HORIZON-FLORA-SPRITES-32](bugs/HORIZON-FLORA-SPRITES-32.md).

## Horizon ponderings: the island cut-out (19 October 2026)

Distant views still break up where tall things meet the sky: Vivec's cantons and the bridges between them,
mountainsides ([HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md),
[VIVEC-DISTANT-BRIDGES-32](bugs/VIVEC-DISTANT-BRIDGES-32.md)). Balmora's low roofs on flat ground hold up well.
The direction the maintainer set: compute the distant silhouette as cheaply as possible from one far model of the
whole island, the topography with every building and tree baked in as a cut-out, built once by the builder. Three
cheap forms, measured against today's horizon at the same poses before any becomes the default:

- a horizon profile per cell: the highest elevation angle of all distant geometry in a few hundred directions,
  filled per screen column in fog colour (the cheapest; no parallax inside a cell, which is not visible that far);
- a coarse height grid of the island (for each point the highest thing standing there), drawn as flat fog-coloured
  spans beyond the CHIM frames, with no seams of its own;
- low-poly shells (mold shells, collision hulls) for the few shapes a height grid cannot show, such as arches and
  bridges.

Refined the same day: the height grid is for the terrain only; buildings, towers and bridges get their silhouette
shells, vegetation keeps its sprites (and possibly the angle impostors). Every change from a far form to the near
one overlaps, with hysteresis, and an object made of several placements (a bridge) switches as one group, so a
transition never leaves a hole. The fog rule hides the moment of the switch; it does not replace the far
geometry: both are needed.

The far shell is drawn in one colour, the fog's, with no texture and no lighting: only its outline and its depth
matter, so the sky can never show through it. Quake already has that drawing path: `D_DrawSolidSurface`
(`d_edge.c`, behind `r_drawflat` and the clear colour) fills a surface's spans with one colour through the same edge
list, so the shell hides correctly behind nearer geometry and costs no surface cache. The bridge and hillside
breakup is fixed on its own as correctness bugs; the shell does not merely hide them.

Implementation notes for the far shell:

- Its own surface class: one palette index (the fog colour) through `D_DrawSolidSurface`, but with its real depth
  gradients written to the z-buffer, unlike the background branch (which assigns background depth) and unlike
  `r_drawflat` (which turns every surface flat). No texture sampling, no surface cache, the normal edge and surface
  visibility, no conversion work beyond the pixels already drawn.
- Built by the converter as one coherent model of the world, not object by object: a bridge stays connected
  across cell borders and detail changes, and real openings (under a bridge, an arch) stay open.
- Resident before the detail it stands in for: the far shell is loaded first and the near geometry replaces it,
  never the other way round.
- The one open cost: the shell's extra edges against the texture and visibility work it saves, measured on the
  68040 and 68060 profiles before it becomes a default.

The full note is in the [CHIM ideas](chim/IDEAS.md#the-distant-view-far-terrain-and-mold-shells).
