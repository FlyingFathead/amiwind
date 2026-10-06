# Distant terrain and sky gaps

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

See [the bug journal](BUG_JOURNAL.md#land-horizon-gaps-29-sky-visible-through-distant-resident-ground-open)
and [the separate horizon study](PLAN-v0.0.29.md#distant-terrain-topology-and-occlusion-study).
