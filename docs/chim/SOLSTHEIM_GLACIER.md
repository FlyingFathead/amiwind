# Solstheim's glacier: how it is approached

_Last updated with AmiWind v0.0.68-dev7 (22 November 2026)._

This page is reference material: why the glacier corner of Solstheim did not fit, what was measured, which ways of
making it fit were tried, the way chosen, and the rules every way has to pass. The other 135 of Solstheim's 144 open
terrain cells are in the build since v0.0.68-dev3; the glacier cell (-26,26) and its eight neighbouring cells go in
together or not at all, and since v0.0.68-dev8 they are in, built with method `E`
([the way chosen](#the-way-chosen-method-e)).

## The way chosen: method E

Method `E` (the sets below: `C` and `D` together) is the shipped default for the listed ice models, decided for the
project on 22 November 2026: `config/mesh-method-sets.json` names it as its `default`, and the Solstheim build module
builds with it whenever a build names no set (`--chim-mesh-method-set baseline` still builds today's methods, for a
comparison). Only the module's own world stage re-keys for it; the base world's stages and stored units are the same.

The nine cells were converted again as one set, each in the shape a build installs it with the other eight as frames of
its world, with set `E` (a CHIM import of 22 November 2026, 15 cells in 156 seconds, most units taken from the shared
pool), and every one of them passes every check, the 32 MB memory check among them. The tracker reference calls them
finished, so the module takes them as it takes every finished cell. The active ring's peak per cell, against the
32 MB limit of 13,582,336 bytes:

| Cell | Peak (bytes) | | Cell | Peak (bytes) | | Cell | Peak (bytes) |
| --- | ---: | --- | --- | ---: | --- | --- | ---: |
| -27,25 | 7,521,808 | | -26,25 | 11,975,024 | | -25,25 | 9,710,192 |
| -27,26 | 12,473,472 | | -26,26 | 13,191,424 | | -25,26 | 11,074,368 |
| -27,27 | 9,433,760 | | -26,27 | 11,190,544 | | -25,27 | 8,347,024 |

Measured on the test images of 21 November 2026, `E` against today's methods: the nine cells' store 51,663,984 bytes
against 92,618,372 (the shard copies 20.9 MB against 48.3 MB); open edges the same as the original (shard 0, iceberg
330, collapsed iceberg 204); 3 of the shard's 1,298 drawn faces shift by about 49 texels (0.097 % of its area), every
other face by at most 0.2 texel; no walkable spot lost and none raised by more than 8 game units, and 218 spots of the
shard's walkable grid (0.075 %) where today's collision stood above the drawn ice now stand on the ice.

## Why the glacier corner is hard

- **One model placed many times.** The glacier and the ice around it are built from one iceberg shard model
  (`bm_ex_iceberg_shard01`), placed 54 times around the glacier, each placement tilted and scaled differently, and two
  large iceberg models (`bm_ex_iceberg`, `bm_ex_iceberg_collapsed`).
- **Tilt and scale are baked.** The engine stores a model once and turns it around the vertical axis while the game
  runs, but a placement's tilt and scale are built into the model when the world is converted. So every differently
  tilted or scaled placement becomes a stored copy of its own: 54 copies of the shard.
- **Collision is the drawn mesh.** In the original game the collision of these models is the mesh itself, one convex
  piece per triangle (about 1,770 for the shard). The engine keeps two collision structures for a placed model: one for
  point traces (weapon and spell hits, projectiles, line of sight, the camera, the aim) and one for the player's
  standing box. A shard copy comes to about 0.9 MB: about 240 KB drawn, about 250 KB for point traces and 230 to
  590 KB for standing, by its scale.
- **The memory mark.** At 32 MB of Fast RAM the models of the cells around the player (the active ring) must fit in
  about 13.6 MB. Standing at the glacier, 21 shard copies are in range: about 19 MB on their own.

Nothing in Vvardenfell places one large mesh at so many different tilts in one place, which is why this first shows
on Solstheim.

## What v0.0.68-dev3 already does

- The collision of the shard copies is compiled in the larger map format where the classic one runs out of node
  numbers, and every copy now compiles ([CHIM-COLLISION-UNION-FALLBACK-41](../bugs/CHIM-COLLISION-UNION-FALLBACK-41.md)).
- The two large icebergs get a compiled collision per tile instead of their pieces' own chains.
- A neighbour's model pieces that lie outside a frame are left out of it only where their own cell has a frame
  ([CHIM-FRAME-EDGE-CLAMPS-OUTSIDE-TILES-68](../bugs/CHIM-FRAME-EDGE-CLAMPS-OUTSIDE-TILES-68.md)).

With these, the nine cells' memory peaks fell from 33 to 46 MB to 14 to 24 MB. All nine are still over the mark
([SOL-ICE-CELLS-RING-OVER-68](../bugs/SOL-ICE-CELLS-RING-OVER-68.md),
[COLLISION-ICEBERG-CLIPNODE-BUDGET-67](../bugs/COLLISION-ICEBERG-CLIPNODE-BUDGET-67.md)). What is left is mostly the
shard copies: 48 to 80 % of each peak.

## The ways being tried

Measured so far, on the nine cells as converted:

- **The shard as tiles.** A copy is only two or three tiles, so most of it is still in range: not enough on its own.
- **A lighter drawn mesh alone.** At most about 240 KB a copy can be saved, and almost every face of the shard has its
  own texture mapping: not enough on its own.
- **A simpler collision shape alone** (one convex hull per copy, or one per tile). Eight of the nine fit, the glacier
  cell itself does not; with a lighter drawn mesh as well all nine fit, but where the player stands on the ice moves
  (7 to 29 game units typically, up to about 700 beside the tall spikes).

Being measured:

- **Uniform shards.** Each placement's tilt and scale snapped to a small shared set, so placements share stored copies
  (the texture and the collision ride the shape as drawn).
- **Shards merged into the cell.** The overlapping shards of a cell compiled into one solid piece of ice, the faces
  hidden between them removed.
- **The mesh reducer on the collision** of the shard and of the two icebergs, keeping the walkable faces exact, also
  together with uniform shards.

Kept as the last resort: a run-time tilt and scale for placed models. It is an engine change, it would touch every
collision trace, and its cost on a 68040 has not been measured.

## Comparing the ways

Each way is meant to become a builder option for the listed ice models, so the same nine cells can be built with
each one and compared side by side. This page will carry the comparison: a table and a chart of each way's memory peak
per cell, open edges, texture checks and footing change, and pictures and short panning videos of the glacier made the
same way for every option. Until those exist, the numbers above are the measured state.

How a way is chosen for a build: the builder option `--chim-mesh-method-set NAME` names a set of
`config/mesh-method-sets.json` (the set `baseline` is today's methods, and leaving the option out is the same). It
reaches only Solstheim's stages, the module's world stage and the `--chim-sol-test` stages, whose own runners install
the set for the meshes it lists; the base world's command, key and output are the same with any set. For pictures of a
way that does not fit yet, `--chim-sol-test-look-only` lets the test stage report its memory check instead of stopping,
and marks the test store as not fitting 32 MB: such images are for looking only, in sessions with more Fast RAM, and a
release candidate or final refuses the option. A `--chim-sol-test` image is itself a test build: its Solstheim is only
the named cells, so the Solstheim build module is left out of it (the plan says so, and so do the build's record and
the image's record of the test store). The first-minute check that every finished cell of a selected expansion is
built accepts that only for such a test image on a development version; a release candidate or final refuses the
option. A CHIM import measures a set with `tools/chimport.py run
--mesh-method-set NAME` (the master builder's `chimport-region` request takes it as `mesh_method_set`); the set is part
of each cell's key and recorded in its result.

The sets so far:

- **`C`: the collision with exact footing**, on the shard and both icebergs (`tools/chim/collision_exact.py`). For
  every placed copy, after its tilt and scale: the pieces of every face the player can stand on there are kept as
  they are; the other faces become convex pieces, and each of those is tested against today's collision top on a grid
  of 8 game units over the walkable surface: where it would rise more than 8 game units over it, it is split, and a
  piece too small to split goes back to today's own pieces; a walkable spot that would end up lower than both
  today's collision and the drawn ice gets today's pieces there back. So nothing is lost where the player stands and
  nothing rises over it by more than 8 game units, measured on that grid for every copy; where today's collision
  stood above the drawn ice, the player now stands on the ice, and those spots are counted apart (each copy's figures
  are written beside the converted cell, `mesh-method-set.json`). The drawn meshes are not touched. The icebergs stay stored as
  tiles of their own frame, as today.
- **`D`: the shard's drawn mesh simplified with its seams locked** (the hand-made "conservative" kind of
  [method 2](MESH_METHODS.md#method-2-hand-made-meshes): every border vertex, texture seam and extreme kept, about
  half the triangles); its collision stays the source mesh's.
- **`E`: `C` and `D` together.** It is the way measured first.

Every method's mesh and variant units are keyed as their own unit kinds, so no stored unit of any other mesh, and no
stage of the base world, is built again for a set.

## The rules a way must pass

In this order of importance:

1. **No seams or holes.** The meshes stay stitched together: no open seams, no gaps or cracks between pieces or tiles,
   and the result has no more open edges than the original. This matters most: a lower face count is fine, a gaping
   hole is not.
2. **Textures intact.** Nothing stretched, swimming, misaligned or seamed on the ice.
3. **Looks like the original** at close range, shown in before and after pictures.
4. **Collision usable.** The player walks where the ice is drawn, does not fall through it and does not stand on air
   beyond a small measured tolerance.
5. **Fits the 32 MB mark** in all nine cells.

And always: every shard stays in the game; a way applies only to the listed ice models, and Vvardenfell's models and
their stored build results stay the same; the nine cells go into the build together or not at all.
