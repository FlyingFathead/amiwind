# Horstator’s musings (3 Oct 2026): “In Hindsight: *cough* Sometimes Fog May Actually Hinder You”

Fog promises less work: hide the distant stuff, draw fewer polygons, enjoy better
performance. Yet in central Balmora, increasing the view distance to 1000 seemed
to make things run better. Apparently, telling the engine to see less isn’t
necessarily asking it to do less.

One possibility is that the shorter distance makes the engine spend more time
clipping geometry at the visibility boundary. A building comfortably inside the
view can take a simpler path than one straddling the cutoff—where polygons need
testing, splitting and bookkeeping. Rejecting something has a cost too.

Another possibility is cache behavior: if that setting affects which assets are
touched, the narrower view might cause repeated churn. But **culling doesn’t
inherently unload anything**, so we shouldn’t assume that explanation without
checking the implementation.

For now, the observation is more interesting than the diagnosis: **a longer view
appeared faster in that scene.** Fog can hide polygons from the player very
conveniently while leaving the engine room still sweating over them.

## Polygons in, polygons out

Polygon count can cost us at every stage. Loading geometry means reading it,
allocating memory and preparing its textures and collision data. Drawing it
means traversing, transforming and rasterizing it. Cutting it out can mean
testing bounds, clipping polygons and generating temporary pieces. Offloading
it means releasing or recycling resources—and perhaps loading them again
shortly afterward.

The awkward middle ground is geometry straddling a cutoff: neither comfortably
visible nor cheaply rejected. Depending on the implementation, deciding what
*not* to draw can become substantial work.

That could help explain why a longer view distance felt faster in central
Balmora. It remains a hypothesis, but the lesson is useful: **count the work
around the polygons, not just the polygons left on screen.**

## A circle is not a square, and the player can turn around

The player can turn through 360 degrees; the instantaneous camera field of view
is narrower. A residency plan must support views in every possible direction
without confusing that surrounding coverage with what is on screen this frame.

A square or rectangle around a position includes corners beyond the same-radius
circle. A triangle or fitted polygon includes a different set of nearby scenery
again. Those areas need not have equal costs: one corner can contain a dense
building complex while another is nearly empty water. Boundaries should reflect
content and measured allocations rather than a prescribed geometric pattern.

A circular footprint is an intuition, not an exact promise about the renderer.
Our far culling uses forward depth; screen-edge geometry, camera field of view,
objects straddling a boundary and collision can need additional coverage. Expand
the complete residency core for supported view directions, movement hysteresis
and collision, then validate the joins. A tight polygon with sharp corners may
require unexpectedly large expanded coverage. Turning around must not reveal
missing geometry or repeatedly load and offload the same objects.

## Investigation status

Owner's playtest observation and hypotheses, recorded 3 October 2026. Working
version: v0.0.27-rc3; exact observed playtest binary/settings are not yet bound to
a captured performance trace. Neither clipping overhead nor cache churn is an
established diagnosis. The inspected far-culling implementation performs bounds
rejection; measuring actual boundary splitting requires checking the downstream
polygon pipeline. Compare matched viewpoints and requested/effective settings.

## What the inspected code actually does

The current AW_DrawDistance clamps effective range to 540 in Balmora, Seyda Neen
and terrain maps because their converted overlap is certified for that range.
The console may retain/report a requested 1000 while effective range is 540.
Record both values, binary version/hash, position and view direction. A setting
change from a lower range to requested 1000 may therefore be a lower-to-540
comparison, not proof that this build rendered to 1000.

AW_FogDraw performs a palette/depth-buffer pass over the viewport; distance
changes rebuild a depth lookup table, not the map. AW_CullBegin/AW_NodeVisible
apply far-plane rejection with a per-frame decision cache. Neither path unloads
BSP data based on fog distance. The resident map is chosen through the separate
region/cell system. Measure culling, submitted surfaces, raster work, fog pass,
cache misses and frame time independently before attributing the result to any
one of them. Stabilize settings and exclude the adjustment frame from timings.

## Boundaries should fit content, not a prescribed shape

Square/rectangular residency cores are implementation choices, not a BSP format
requirement. Investigate arbitrary polygonal boundaries fitted to geography,
dense scenery and useful sightlines. Hexagons were only an example. A polygon
can remove expensive corner scenery from a rectangle, but a retained parent
visibility/tree payload can outweigh that saving. Compare actual converted
allocations; do not infer memory reduction from outline area alone.

Keep transition cores separate from their visibility/collision coverage. Require
complete map coverage, deterministic boundary ownership, hysteresis and sufficient
margin in all travel/view directions. Validate joins around Seyda Neen and
Balmora before installing a candidate. Avoid narrow polygon corners whose required
expanded coverage grows larger than the rectangular alternative.

## Profile the entire residency cycle

Record the outgoing scene before its peak is reset, old-scene unload and
remaining persistent state, new BSP load/temporary peak, actor restoration,
first presented frame and warmed gameplay. Include both-direction crossings,
restart/teleport and save/load. Track hunk use and gap, cache occupancy/evictions,
zone fragmentation and external Fast/Chip memory separately. A scene-spawn
snapshot alone is insufficient.

Keep the 11 MiB reference heap and existing 3 MiB non-BSP reserve plus 2 MiB
safety floor: modeled BSP loading peak must stay at or below 6 MiB. Aim newly
subdivided regions near 5 MiB as a planning target for growth, not a replacement
acceptance rule. Polygon shape does not earn a reduced reserve. Raise allowances
when matched target measurements or new content require it; do not lower them
merely to pass. See [memory allocation](MEMORY_ALLOCATION.md) and the growing
[cell continuity checklist](CELL_CHANGING.md).

## Follow-up: less visible is not automatically less work

The owner reiterated the Balmora observation during the town-memory review:
requesting a longer distance appeared faster in the emulator. Preserve that
observation while testing its explanation. A short cutoff can trade raster work
for traversal, bounds tests and clipping; fewer visible polygons alone cannot
prove a cheaper frame. “Double the work” remains an intuition, not a measured
multiplier or proof that two maps are loaded.

This frame-cost question is distinct from broad terrain/PVS retention inside one
BSP and input/resident duplication during loading. Fog and distance culling do
not inherently unload map data. Record requested **and effective** distance,
exact binary/configuration, position and camera direction. Compare frame timings
and tested/rejected/clipped/drawn counts, cache behavior and any loading activity.
The current town range clamp is 540, so a requested 1000 must not be reported as
an effective 1000 without verifying the tested implementation.

## Heap watching: somebody has to count the mushrooms

The rocks and mushrooms were behaving. Then we fixed a terrain gap, and the heap
started to give in.

What looked like “a little more ground around Seyda Neen” became considerably
more visibility data. The loader then kept two copies, presumably in case the
first one got lonely. The second copy arrived at an 11 MiB heap. Not good.

Hence the heap watcher: meticulously asking every allocation, **“Are you on the
list (or lookup table), and how long are you staying?”**

Its shift must cover the whole party: old map leaving, new map arriving, textures
settling in, actors appearing, caches rearranging the furniture. Checking memory
only after loading isn't a solution to this.

And headroom means actual spare capacity. Not "it fitted once," not "whoever's
playing has plenty of RAM," and certainly not "we put the mushrooms on another
disk."

**A second HDF, at the moment, is just a temporary swap. We bring stuff in, we take
it out. We optimize, we adjust, we adapt. That's life.**
