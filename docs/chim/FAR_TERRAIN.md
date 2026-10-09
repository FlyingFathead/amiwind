# CHIM far terrain: the distant view

Status: CHIM 0.1.0, first version (Balmora and Seyda Neen frames). Tracked as
[CHIM-FAR-TERRAIN-33](../bugs/CHIM-FAR-TERRAIN-33.md), a v0.0.33 release
blocker: the CHIM distant view must look at least as good as v0.0.32's, the
HORSTATOR APPROVED horizon.

<!-- contents start -->
## Contents

- [The problem](#the-problem)
- [How the legacy builder and engine draw the distance (v0.0.32)](#how-the-legacy-builder-and-engine-draw-the-distance-v0032)
- [Why CHIM lost it](#why-chim-lost-it)
- [The CHIM far layer](#the-chim-far-layer)
- [Data: the far terrain sidecar](#data-the-far-terrain-sidecar)
- [Engine: drawing it](#engine-drawing-it)
- [Memory](#memory)
- [Vis and counters](#vis-and-counters)
- [Cost](#cost)
- [Settings](#settings)
- [Measured](#measured)
- [Later: object silhouettes and landmark shells](#later-object-silhouettes-and-landmark-shells)
- [Tests](#tests)

<!-- contents end -->

## The problem

On a CHIM map the ground ends where the chunk ring ends. Past it there was
nothing: the background (sky) filled the screen down to the bottom of the
valley, fully fogged, so valleys looked empty and the land outline that
v0.0.32 drew against the sky was gone. The owner rated v0.0.32's distant
views 4 to 5 out of 5 in many places.

## How the legacy builder and engine draw the distance (v0.0.32)

There is no separate distant-world pass in v0.0.32. The horizon comes from
four ordinary pieces:

1. **Region maps with overlap.** Every town region map (and every open-world
   `vf` map) holds its core plus 896 units of its neighbours on every side
   (`config/<town>.json`: core 768, overlap 896; `tools/adaptive_town_regions.py`
   requires overlap >= sqrt(2) x 540 + 96 + 32, about 892). The terrain is a
   uniform 128-unit grid of brushes (every fourth LAND sample), the same
   resolution in the overlap as in the core. So in every direction there is
   real ground at least to the fog distance (540) and beyond it.
2. **The far plane.** `aw_cull` (aw_fog.c) keeps a BSP node when the nearest
   corner of its box lies in front of the plane `distance + 16` ahead of the
   eye (`AW_NodeVisible`); models likewise (`AW_ModelVisible`). A node that
   straddles the plane is drawn whole, so terrain faces reach a little past
   the fog distance.
3. **Palette fog.** `AW_FogDraw` remaps every drawn pixel after rasterising,
   by Quake's inverse-depth z-buffer: level 1 at 0.44 x the distance, full fog
   colour (level 15) at the distance. Ground at and past the far plane is
   therefore drawn in the full fog colour: the land outline.
4. **The sky.** Quake's background surface (`SURF_DRAWBACKGROUND`) fills every
   pixel no polygon covers with the software sky, marked with the reserved
   depth -32768. `AW_FogDraw` regrades those pixels by ray direction
   (gradient, sunset glow, sun halo, stars; `R_DayNightSkyPixel`), and the
   lowest band of the sky is the same fog colour, so the fogged land outline
   meets a sky that fades into it.

`aw_skyline_fill` only changes a branch of that fog pass: `0` (the default,
the HORSTATOR APPROVED look) leaves the sky below fogged far scenery as sky;
`1` (object silhouetting, experimental and buggy, kept) paints it in the fog
colour. `aw_terrain_horizon 1` (off by default) adds the resident LAND faces
of the world model beyond the far plane, in the fog colour, depth tested
(`aw_horizon.c`, [DISTANT_TERRAIN.md](../DISTANT_TERRAIN.md)).

Quake mechanisms: the BSP world and its node boxes, the z-buffer the span
renderer writes (`D_DrawZSpans`), the background surface and the sky scans
(`D_DrawSkyScans8`). Cost: the overlap is paid in disk and memory (every
exterior object is stored about 9.8 times, WORLD-REGION-DUPLICATION-31); the
draw itself costs the terrain faces at the far plane and the fog pass over
the viewport (two table lookups per geometry pixel, a ray step per sky
pixel). Memory for fog and sky: about 100 KB of tables; nothing per map.

## Why CHIM lost it

A CHIM frame map's world is the frame world (`chim_graft.c`): only the chunks
of the active ring (the view distance plus the hysteresis) are grafted into
it. Beyond them the frame grid is empty leaves, and past the frame's edge
there is no data at all. Chunk terrain leaves are 128 units wide, so even the
node-straddling margin of the legacy far plane is small. The far plane, the
fog and the sky work exactly as before; only the ground they had to work on
is missing. (Chunks that a zone without room could not load,
CHIM-CHUNK-LOAD-FAIL-33, made holes nearer than that; that is a separate
bug.)

## The CHIM far layer

The equivalent of the legacy overlap, stored once and small: a coarse
heightfield of the frame's land and a margin beyond its edges, resident for
the whole map, drawn by the engine past the fog plane in the full fog
colour, depth tested, after the fog pass. It is the same picture the region
maps' overlap made (fully fogged ground meeting the sky), produced from data
that is a few kilobytes instead of a second copy of every neighbour.

Why this is enough for the HORSTATOR APPROVED look: beyond the fog plane
every surface is drawn in one colour, so the far layer needs no texture, no
lighting, no BSP and no collision; only the outline of the land matters, and
the outline is the heights.

Hidden where a real chunk is resident: the layer is drawn only beyond the
fog plane, and only where the depth buffer holds sky or something farther.
Nearer than the fog plane the resident chunks are never touched; beyond it
a chunk's ground and the layer are the same full fog colour, and the nearer
one wins the depth test. Nothing has to be switched per chunk.

## Data: the far terrain sidecar

Built by the CHIM builder (`tools/chim/far.py`, a step of
`tools/chim/build.py`; on by default, `--no-far-terrain` is a debugging
opt-out) from `Morrowind.esm`'s LAND records, the same samples the chunk
terrain uses (`mwad.audit.decode_heights`):

- one height every 512 Morrowind units (every fourth LAND sample, 128 local
  units, the converter's terrain step), exact at the samples;
- over the frame plus one cell on every side (5 x 5 cells for a 3 x 3 frame:
  81 x 81 samples), snapped to the cell grid; one cell is more than the
  default depth (896 local units, under half a cell) reaches past any point of
  the frame;
- the water level where the ground lies below it, or where a cell has no LAND
  (the sea is drawn as flat land at the water level, as the fogged water of a
  region map was);
- object stamps (version 2): the drawn boxes of the frame's large placements
  (at least 64 local units wide both ways and 64 above the ground: houses,
  towers, big rocks; never flora) as a separate list of raised samples, so
  the engine can leave them out;
- big-endian 16-bit local heights after a 40-byte header (`CHFL`, version,
  frame cell, world position of the first sample, step, scale, size, block,
  stamp count, CRC-32). Balmora: 81 x 81 samples and 1,719 stamps from 1,473
  placements, 23,476 bytes; Seyda Neen: 75 x 75 samples and 829 stamps,
  16,264 bytes.

The image step (`build_aga.py`, `chim_frame_maps`) copies each frame's layer
beside its frame map as `maps/<frame map>.far`, like a Quake `.lit` file next
to its map, after checking its frame cell. Seyda Neen's intro docks and
courtyard frame maps get their frame's layer too. The sidecar is not part of
the CHIM world: `chim/world.cwi` does not list it, it has its own version, and
it changes neither the world format nor the disk-layout gate. An engine
without far terrain ignores it; a frame map without one draws no far land.
The specification is in [WORLD_FORMAT.md](WORLD_FORMAT.md#far-terrain-sidecar).

## Engine: drawing it

- `chim/chim_far.c` reads the sidecar at map start (after the frame world),
  checks its header, size, frame cell and CRC, converts the heights to native
  shorts, applies the object stamps when `chim_far_objects` is 1, and
  computes each block's lowest and highest height. A file that fails any
  check is refused with a reason (`chim` prints it) and nothing is drawn.
- `AW_FogDraw` (aw_fog.c) calls the hook `aw_chim_far_draw` after the fog pass,
  with the same full fog colour and distance as the LAND pass; NULL on legacy
  data, so the legacy engine is unchanged.
- `AW_HorizonGrid` (aw_horizon.c) draws the grid with the LAND pass's own
  scan routine (`polygon`: inverse-depth test against the z-buffer, pixel
  centres as `D_DrawZSpans`), after clipping each triangle at the fog plane
  and at the reach (`chim_far_reach`, default 896: the legacy overlap depth),
  as the LAND pass clips its faces. Per block of 16 x 16 quads (a cell) it
  rejects whole blocks that lie nearer than the fog plane, beyond the reach,
  or outside one side of the view (eight corners against the four planes
  through the eye and the viewport edges); then each quad is two triangles
  (corners 0-1-2 and 0-2-3, as the converter's tiles), skipped when all three
  corners are nearer than the fog plane or beyond the reach, or when it faces
  away from the eye (a heightfield seen from above is closed: a ray meets a
  facing triangle first).

Quake mechanisms: none for terrain level of detail. Reused: the z-buffer and
fog pass, the background sky, and AmiWind's distant-LAND rasterizer; the data
follows Quake's `.lit` sidecar convention.

## Memory

The heights and block bounds live in the low Hunk, allocated at map start
right after the CHIM zone (as efrag pages and every other per-map Quake
allocation) and given back with the Hunk at the next map change: Balmora
81 x 81 x 2 + 25 x 4 = 13,222 bytes, Seyda Neen 75 x 75 x 2 + 25 x 4 = 11,350
bytes. The stamp list (Balmora 10,316 bytes) is read above them only while
it is applied, and the Hunk goes back to its mark at once. The layer is
outside the CHIM zone, so the chunk ring's heap gate is unchanged; it takes
those bytes from the 2 MiB Hunk gap that `chim_reserve_kib` protects (the
engine refuses the layer, with a line, rather than go below that reserve).
Code: about 3 KiB; static data: one 17 x 17 vertex block (3.5 KiB).

## Vis and counters

The far layer is not world geometry: it adds no node, leaf, surface, efrag
or entity, so the PVS, `R_MarkLeaves`, the entity counters (entities sent,
faces clipped, BSP nodes per face) and `MAX_VISEDICTS` are unchanged (the
`bm`, `bf`, `e` and `pl` fields of `dbg rcount` are identical with
`chim_far` 1 and 0 at every A/B pose). It is drawn only past the fog plane,
where the BSP draws nothing. Its own counters are in `chim` (last frame:
blocks drawn of total and why the others were culled, triangles, triangles
facing away, polygons, pixels, microseconds; stamps applied) and at the end of
the `dbg rcount` line on a CHIM map: `far drawn/blocks tr triangles px pixels
fus worst-us` (`far off` with `chim_far 0` or no layer).

## Cost

Per frame: 25 block tests (8 corners against 5 planes each), the vertices of
the blocks that pass (289 per block, three dot products each) and the
triangles of those blocks that reach past the fog plane and stay within the
reach, then the pixels of the land outline band. Measured on the slow FS-UAE
preset (68040, cycle-exact, multiplier 14 = 49.7 MHz; emulated time, relative
until a hardware number exists), 40 seconds of counters each, same session,
with the object stamps on (the run predates their default of off; at the
bridge pose the default without them draws 214 triangles and 3,571 pixels in
the standard profile, fewer pixels than measured here):

| Pose | chim_far 0: frame | reach 896, objects on: far draw | reach 0 (whole layer): far draw |
| --- | ---: | ---: | ---: |
| Owner's bridge pose, 19:54, looking west | 0.96 s | 43.7 ms (166 triangles, 8,549 pixels) | 228.6 ms (2,342 triangles, 29,591 pixels) |
| East bank (HORIZON-HOLES-31 position), looking west | 1.50 s | 30.6 ms (191 triangles, 209 pixels) | 193.8 ms (2,149 triangles, 5,392 pixels) |

So the default depth costs 3 to 5 % of a slow-preset frame there; the whole layer
13 to 24 %, which is one reason the default stops at the legacy depth.
Standard-profile (JIT) timings on the busy host are not comparable and are not
quoted.

## Settings

- `chim_far` (default 1): 0 draws no far land, the first CHIM method, kept
  for A/B tests.
- `chim_far_reach` (default 896): the forward depth, in local units, beyond
  which nothing is drawn; 896 is the legacy region overlap, so the outline is
  as deep as v0.0.32's; 0 draws the whole layer (the land up to a cell past
  the frame: much more land than v0.0.32 showed, high ridges cover the low
  sky and the sun at sunset).
- `chim_far_objects` (default 0, read at map start): 1 raises the object
  stamps into the layer. Experimental: on a 128-unit grid a house becomes a
  steep peak or tent, not the boxy outline the legacy overlap drew, so it is
  off until object silhouettes have their own shapes (see below).
- `chim_far_cull` (default 1): 0 tests every block (exactness checks).
- `chim_terrain_floor` (default 1): the layer is also the terrain floor
  (CHIM-GRAFT-REPACK-EMPTY-33, second layer). It is the one copy of the
  frame's ground that is never streamed, so it is still there when the frame
  world loses its chunks. With noclip off, a walking or free-falling body
  whose feet are below the lowest height at its X/Y, with nothing of the
  world below it, is lifted onto the ground surface with one console line
  (`Terrain floor: ... lifted onto it`); the player is then held on that
  surface while the world has no ground under it. The world's own ground
  always wins, however low.
  The surface is the chunk terrain's own tile triangles through the same
  samples; the lowest height is the quad's lowest corner less 64 units, or,
  where a corner lies at the water level (the layer keeps the water surface
  there, not the bed), the lowest terrain point of the chunk (from the
  frame's chunk table) less 64. Noclip and flight never use it; applied
  object stamps turn it off. 0: no floor (the previous behaviour).

The legacy horizon methods are untouched: `aw_skyline_fill 0` stays the
default and `aw_terrain_horizon` stays as it was.

## Measured

FS-UAE, standard play profile, A/B/C/D in separate sessions from the same
images, headlamp off (look evidence) and on (near geometry), at fixed poses:
the owner's bridge frames (global -17541 -15916, 19:54 and 19:58), the east
bank of HORIZON-HOLES-31 (18:00), the town centre looking north and south
(13:00), the west at 19:30 and a raised view south-west (16:00). None of the
ten release gallery poses is in Balmora or Seyda Neen (all ten are at the
Vivec Arena, and their poses were not recorded), so they are not part of this
A/B; Seyda Neen has no CHIM image yet. Variants: A the v0.0.32 release image;
B CHIM Preview 1 (as the owner played it); C the far layer (default), CHIM
before on the same engine (`chim_far 0`), the whole layer, legacy region maps
in the same image (`chim_towns 0`, with and without entities), and a rerun of
the first pose (drift control: identical counters). Frames and counters are
on the bug page.

What the A/B shows:

- At the owner's bridge pose v0.0.32 itself shows no ground in that band
  either: past the fog distance the valley is sky in every variant. What
  v0.0.32 had and CHIM did not is the fogged land outline at the horizon; the
  far layer at the default depth draws it, continuous instead of the
  node-by-node fragments of the legacy far plane.
- Much of v0.0.32's horizon at the east-bank pose is buildings: with
  `r_drawentities 0` the legacy view keeps only scattered terrain fragments.
  Those houses stand between the CHIM ring and the legacy overlap depth;
  CHIM does not draw them (CHIM-FAR-OBJECTS-33). The ground layer does not
  replace them; object stamps in the heightfield make peaks, not houses.

## Later: object silhouettes and landmark shells

Objects beyond the chunk ring need their own shapes, drawn by the same
rasterizer in the fog colour: each large model converted once to a few dozen
triangles (the distant shell prototype, `tools/mold_shell.py`,
[DISTANT_SHELLS.md](../DISTANT_SHELLS.md)) and placed by reference from the
frame's placements, sprite trees by their alpha mask (never rectangles:
HORIZON-FLORA-SPRITES-32), and landmarks that stand above the land outline
(Vivec's cantons, Red Mountain's crater rim) the same way. The ground layer
comes first because it fixes every direction at once.

## Tests

- `tests/test_chim_far.py`: the builder (area and snapping, exact LAND samples
  including the neighbour cell's edge and the water level, object stamps for
  large boxes only, file round trip for versions 1 and 2, CRC, size and stamp
  order refusals, LAND read from a synthetic master, determinism); the image
  step's sidecar check; the engine contract (fog hook after the fog pass,
  defaults, map start and end, Makefile); native: the grid rasterizer against
  an independent ray/plane oracle on planar and valley heightfields from 18
  cameras, block culling equal to no culling pixel for pixel, the reach,
  nearer foreground kept, precomputed bounds, a view from below, and invalid
  grids; the loader on files the builder's writer made, refusing a damaged,
  foreign-frame, short or missing file and the Hunk reserve; stamps applied
  only with `chim_far_objects` 1 and their Hunk given back.
- `tests/test_chim_far.py` (terrain floor): the surface equals the tile
  triangles at about a thousand points, the lowest height on land and water
  (chunk and frame lowest), nothing outside the layer, when off, on a legacy
  map, with object stamps or after the map; `tests/aga_walk_test.c`: walking,
  a cliff and a jump are unchanged with the floor on; a player whose world is
  emptied is lifted once with one console line, then stands, walks uphill and
  jumps on the terrain; the world coming back ends the hold; the world's own
  ground 100 units below the layer's is never lifted from; noclip and
  flight pass below; an actor's trial step never uses it; a free-falling body
  is lifted; with the floor off the fall has no end.
- `tests/test_chim_engine_native.py` (`far`): the frame map's layer loads at
  map start into the low Hunk, reaches the fog hook with the frame-local
  origin, and goes with the map; without one nothing is drawn.
