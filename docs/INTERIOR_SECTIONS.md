# Interior sections

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

<!-- contents start -->
## Contents

- [Interiors over a limit: the order](#interiors-over-a-limit-the-order)
- [Measured fallback after subdivision — 6 October 2026](#measured-fallback-after-subdivision--6-october-2026)
- [Trying cuts in the 3D Map Inspector](#trying-cuts-in-the-3d-map-inspector)

<!-- contents end -->

An interior that does not fit its limits is split or lightened, never just left out. This page holds the
order of the repairs, how sections are cut and how cuts are tried in the inspector.

## Interiors over a limit: the order

A converted interior is a Quake map with three hard limits: 220 placed models of its own (inline models,
INTERIOR-INLINE-LIMIT-31), the room heap budget (VIVEC-HEAP-31) and the coordinate range of +-4,096 units
(INTERIOR-COORDS-31). The builder lists every room it leaves out with the limit it missed (for Vivec:
`chim-rooms-vivec_city/rooms.json`, key `excluded`). Repairs, in this order, each one measured before the
next:

1. **Numerous decorative meshes become sprites.** Potted plants and similar small scenery drawn as sprites
   are no inline models; the room gets fewer models, less memory and a faster frame. The sprite keeps the
   plant's outline (the sprite shape rule of the world flora).
2. **The heaviest meshes are reduced, mesh by mesh.** A per-mesh recipe (`config/visual-recipes.json`) or
   the mesh optimizer, as an A/B against the room's current build: the optimizer can make merged meshes
   larger, so only a measured gain is kept. Collision keeps the original mesh.
3. **Sub-cell cuts at hallways and doorways.** The room is split into sections where the player walks
   through a narrow passage anyway: doorway and hallway pieces and the narrow points of the walkable floor.
   Each section has its own limits; every original object stays in exactly one section
   (`tools/prepare_interior_sections.py`). Planned for v0.0.42: the builder proposes the cuts and scores
   each side against the limits; the proposal is reviewed in the inspector's divider (below).
4. **Recentring** for a room whose coordinates pass +-4,096.

### What the builder does today (v0.0.42)

- **Before any step: same-lit placements share one model.** A lit room bakes light into every placed object,
  so each one used to be a model of its own. A placement that no light can reach (every light farther than
  its reach from the object's bounding sphere plus the farthest lightmap sample) is lit by the room's ambient
  alone on every sample, so equal placements of the same mesh share one model; what is drawn does not change
  (`prepare_mesh_bsp.unlit_placement`, `tests/test_shared_ambient.py` checks every sample). Earlier rule:
  `AMIWIND_SHARED_AMBIENT=off`. Rooms with light zones never share.
- **Step 1, plants as sprites,** in every converted interior (from v0.0.43-dev3, the default by decision for
  the project, 18 October 2026; [INTERIOR-MORAG-TONG-FPS-43](bugs/INTERIOR-MORAG-TONG-FPS-43.md), which also
  ranks the meshes that draw the most faces after it and the step that fits each): a converted room is one vis leaf, so every
  plant mesh in view is drawn every frame. The room converter draws its nonsolid static plants (an NC/NCO
  marker or ground vegetation without an authored collision node) and its static trees as sprites
  (`tools/interior_plants.py`); a tree that is solid in the original keeps its collision as a collision-only
  model, so the trunk still blocks the player. Logs keep their meshes. Measured on the v0.0.43-dev2 interiors:
  nonsolid plants 397 placements, 78,502 faces in 74 rooms; trees 10 placements, 8,121 faces in 6 rooms.
  `AMIWIND_INTERIOR_PLANTS=plants` keeps the trees as meshes; `over-limit` is the v0.0.42 rule (sprites only for
  a room still over its model limit, converted again). A sprite keeps the plant's outline from its alpha; since
  sprites are not lit by the renderer, each one is shaded with the room's colormap at the light its
  placement gets, one sprite file per plant mesh and light step. A sprite file counts as one model slot.
  Harvestable plants (containers) and plants you can bump into keep their mesh. The receipt
  (`conversion.json` `plant_sprites`, `limit_steps`) lists every plant and what it became. Every plant a mesh:
  `AMIWIND_INTERIOR_PLANTS=meshes` (a room over its model limit fails as before). A room over its heap budget, which the room
  converter cannot see (the heap is estimated in the image step), asks for plant sprites in its town config row:
  `"plants": "sprites"` (Vivec, Hlaalu Underworks).
- **Step 3, cut proposal:** `tools/propose_interior_cuts.py ROOM_FOLDER ... --out proposal.json` reads
  converted rooms and proposes vertical cuts through doorway and hallway pieces, with the model slots of each
  side (by the converter's own sharing rule) and the placements a cut would cross. A proposal is reviewed in
  the inspector's divider before any section is built; no cut is applied by the builder.
- **Step 4, recentring:** a room row in the town config can carry `"recentre": [x, y, z]` (original units).
  The converter subtracts it from every position of the room, its lights and its arrivals, and every door bank
  that leads into the room subtracts it from the arrival (`town_interiors.room_offsets`, `recentre_cell`).

### On CHIM rooms (v0.0.48)

From v0.0.48 a room can be a CHIM room instead ([Interiors on CHIM](chim/INTERIOR_STORE.md)): its meshes and
textures are stored once in the shared interior store and the room map holds only the room's own entities. The
limits change, the order above does not:

- **The 220 inline models and the +-4,096 coordinate range no longer bind a CHIM room:** placements are records on
  the store (up to 60,416 linked per room, read from the engine), not models of the map.
- **The limit that binds is the room's own set** (its models and textures on the store, loaded) against what the
  machine gives a room. A room map has no frame world, so it has the whole CHIM zone (6,864 KiB less the 32 KiB
  loading buffer); and models and textures go first into the automatic cache banks of the spare Fast RAM. On the
  32 MB minimum machine that is one 8 MiB bank (measured), so a room holds about 14.7 MiB, one model at most 8 MiB.
  On the 16 MB baseline it is the zone alone, about 6.7 MiB. The numbers are read from the engine on every run
  ([the door graph](chim/DOOR_GRAPH.md#chim-room-limits)).
- **The same repairs, in the same order, measured the same way:** plants as sprites (a sprite is far smaller than its
  mesh), then the heaviest meshes reduced by recipe or the mesh optimizer ([mesh methods](chim/MESH_METHODS.md),
  only a measured gain kept, collision on the original), then cuts at hallways and doorways, which split a room's
  set into sections that each fit; then a larger zone where the fast RAM allows it.
- **Water and lava** are not limits: they reuse the room map's liquid brushes (the room's waterline, each lava pool).
- **Lighter collision is a repair too.** A model's collision can be lighter than its visible mesh without changing
  what you see: the game's own authored collision mesh (`RootCollisionNode`, in 84 % of the interior kit NIFs) instead
  of the visible triangles cut the estimated collision cost of the Balmora rooms by 54 % and of the Seyda Neen exterior
  by 79 % ([collision meshes](COLLISION_MESHES.md#cost-of-using-the-authored-collision); converted rooms still use it
  for `i/` models only, COLLISION-RCN-SCOPE-32). Large models over 16 pieces get compiled or routed hulls instead of
  one long chain (COLLISION-HULL-CHAINS-33). Exact collision plates for everything are not affordable (6.9 times the
  cost on the Balmora rooms). Every collision change is checked by walking it: stairs, doorways, tilted props.
- **A single model over one image's limits is cut, not its room.** When one model's collision needs more clipnodes,
  point nodes, vertices or texture mappings than one model image numbers (65,520 clipnodes), lighter collision is
  tried first. If that does not fit without changing the collision, the model is stored as tiles of its own frame:
  the large-model cut's tiles, at the room's grain, halved until each tile fits. Every collision piece and face goes
  whole to one tile, so nothing drawn or solid changes and nothing needs a walk check. The builder does this on its
  own for any room or frame, and the receipt names the model (`over_budget_tiles`). First case: Akulakhan's Chamber
  (below).
- How a hard room is approached as a whole: [the method](chim/INTERIOR_STORE.md#when-a-room-is-hard-the-method).

#### What worked for the 27 rooms over the size limit (23 October 2026)

**Step 0, before any repair: check the estimate against a measurement.** The 27 rooms were set aside by an estimate,
not a measurement, and the estimate was wrong in two ways
([CHIM-ROOM-ESTIMATE-48](bugs/CHIM-ROOM-ESTIMATE-48.md)):

- **The budget.** It was the zone less the two frame-world pool blocks (5.95 MiB), the 16 MB figure of a frame map.
  A room has no frame world, so it has the whole zone; and on the 32 MB minimum its models and textures use the
  8 MiB cache bank too.
- **The bytes.** They were the BSP29 bytes on disk. Loaded, a model's faces, planes and texture mappings take the
  engine's larger structures. On the 43 Balmora CHIM rooms the disk figure was 17 % under the measured need, against
  the zone each room map actually took (`chim-room-heap.json` of the Balmora CHIM rooms sandbox: the Temple needs
  4.10 MB of its 7.03 MB zone). The estimate now counts the loaded structures from the same mesh census (target
  sizes from the compiler): 9 % over the measured need in all; per room the measured need is 0.82 to 1.03 times the
  estimate.

With both corrected, **all 27 rooms fit the 32 MB minimum**: the largest set is 10.2 MiB (Assemanu) against 14.7 MiB,
and the Vivec Arena Pit, which works at 16 MB today, is 3.8 MiB. No mesh was reduced and no room was cut. Mesh repairs
are measured gains only, and with no room over its limit at 32 MB none was made.

**Still to watch:**

- **One model over one image: Akulakhan's Chamber (done, 23 October 2026).** The cave shell (`in_akulacave00`) has as
  its authored collision the whole cave (6,532 triangles). The room profile keeps it as 6,281 plates with exact
  bevels, a standing hull of 162,975 clipnodes, where one model image holds 65,520. The method's steps, in order:
  lighter collision alone does not fit (approximate bevels 69,713, and the qbsp union fails to compile); the mesh
  optimizer reduces only what is drawn; so the cut. The part over the limit is one model, not the room's references,
  so the cut is of the model: it is stored as tiles of its own frame (78 at grain 256). Every plate and face goes
  whole to one tile, so nothing drawn or solid changes, and each tile is its own image. The builder does this for any
  model over an image's budgets ([CHIM-ROOM-CLIPNODE-BUDGET-48](bugs/CHIM-ROOM-CLIPNODE-BUDGET-48.md)). The room
  needs 10.1 MiB: it fits the 32 MB minimum (14.7 MiB), with no 7.6 MiB single block any more, but not the 16 MB zone.
- **The 16 MB baseline.** 72 of the 1,328 rooms need more than the zone alone (the 27 among them). They load on the 32 MB minimum.
  On 16 MB, or with Options > Extra RAM off, they do not load. Their heaviest meshes are cave shells (`in_lavacave`,
  `in_moldcave`, `in_pycave`) and the corpse containers (`contain_corpse10`, `_20`). Those are the targets if rooms
  should load at 16 MB.

**Sections for CHIM rooms (a proposal; not needed by any room at 32 MB).** A CHIM room loads whole: one room record,
one room map, every model locked until the next map. The smallest way to split a room's set is two room records and
two room maps with a door between them: the cut is a doorway or hallway (`tools/propose_interior_cuts.py` proposes
them on converted rooms), each side becomes its own room with its own set, and the seam is an invisible load
trigger in the passage, like a load door. It needs no engine change. A room that streams its sections in one map
(both sets resident near the seam) would need the engine to load and free models inside a room, which CHIM rooms
do not do today.

## Measured fallback after subdivision — 6 October 2026

Divide oversized interiors at natural doorways, corridors and cave bends first.
If a section still exceeds its memory/frame budget, use the polycount inspector
and allocation profile to identify the responsible objects. Selective lower-poly
variants of large decorative, non-pickable mushrooms or other costly scenery
are an approved fallback. Preserve silhouette, closed seams, UV/material
boundaries, collision and original placement. The wireframe is see-through;
density colours alone do not establish visible per-frame cost. Measure again
after conversion and on the Amiga before admission.

## Trying cuts in the 3D Map Inspector

The inspector's sub-cell divider draws candidate cuts through the converted
room, counts faces, placements, lightmap bytes and an estimated heap share for
each side, and exports the cuts as a section plan in the
`tools/prepare_interior_sections.py` format with the receipt fields left
`PENDING`. `tools/region_cuts.py plan` turns any section plan into an overlay
for review. See
[sub-cell cuts](POLYCOUNT_INSPECTOR.md#build-020-sub-cell-cuts-and-divider).
