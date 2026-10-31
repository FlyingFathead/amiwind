# CHIM ideas and held-back work

_Last updated with AmiWind v0.0.54-dev1 (28 October 2026)._

<!-- contents start -->
## Contents

- [Modular NPCs](#modular-npcs)
- [NPC pathfinding](#npc-pathfinding)
- [The Ghostfence as a Quake turbulent surface](#the-ghostfence-as-a-quake-turbulent-surface)
- [Angle impostors for heavy plants and rocks](#angle-impostors-for-heavy-plants-and-rocks)
- [The distant view: far terrain and mold shells](#the-distant-view-far-terrain-and-mold-shells)
- [M3: Vivec on CHIM](#m3-vivec-on-chim)
  - [M3 preflight (10 October 2026)](#m3-preflight-10-october-2026)
- [M4: the open world](#m4-the-open-world)
  - [The frame grid](#the-frame-grid)
  - [The memory estimator](#the-memory-estimator)
  - [The density planner, and why frame cuts do not lower the peak](#the-density-planner-and-why-frame-cuts-do-not-lower-the-peak)
- [Memory](#memory)
- [Build speed](#build-speed)
- [Texture effects: a bug turned into an effect](#texture-effects-a-bug-turned-into-an-effect)
- [The slow-accelerator reality](#the-slow-accelerator-reality)
- [Island-wide audits (mechanism classes)](#island-wide-audits-mechanism-classes)
- [Collision from what the game already knows](#collision-from-what-the-game-already-knows)
  - [Terrain collision from heights (measured prototype, 21 October 2026)](#terrain-collision-from-heights-measured-prototype-21-october-2026)
- [The Arena Pit's upper tiers as backdrop panels](#the-arena-pits-upper-tiers-as-backdrop-panels)
- [Also held back](#also-held-back)
- [Measured and dropped](#measured-and-dropped)

<!-- contents end -->

Every idea around [CHIM](README.md) that is not simply "done": what is
planned, what is designed, what has a prototype, and what was measured and
then dropped. Each item links to the document or bug that holds the detail.
The status is honest and nothing here is a promise. Items that were measured
and dropped stay on this page with the reason, so nobody spends a night
measuring them again.

| Status | Meaning |
| --- | --- |
| planned | decided or requested; no design yet |
| designed | written down with its data layout, budgets and gates; no code |
| prototyped | code exists (a debug command, a tool or a branch), not yet a finished feature |
| in source | implemented and gated on a development branch, not yet in a release |
| measured and dropped | tried or counted; not worth it, for the reason given |

All figures come from the maintainer's own game data and builder output, as
aggregates. Emulator frame times are relative until a real accelerated Amiga
has been measured ([hardware benchmark](../HARDWARE-BENCHMARK.md)).

## Modular NPCs

**Status: designed and measured; composition prototyped.** CHIM top priority
together with the map. Design: [Modular NPCs](../MODULAR_NPCS.md), tracked as
[NPC-BAKED-WHOLE-DUPLICATION-33](../bugs/NPC-BAKED-WHOLE-DUPLICATION-33.md).

Today every NPC appearance is baked into one complete model. The 2,675
humanoid NPC records resolve to about 3,500 appearances, yet those are made
of only 1,726 distinct body parts (942 mesh files), each used about 39 times.
Baking whole processes about 12.3 million source triangles; the distinct
parts hold about 0.4 million. The same "stored once" rule as the world:

- **Parts library and recipes.** Each part converted once (at a few quota
  levels), plus one small recipe per appearance. A part baked alone and
  concatenated with the others gives exactly the whole model (byte-identical
  at unit scale, tested in the prototype).
- **The NPC gallery from parts.** The longest stage of a full build
  (about half an hour) is expected to drop to a few minutes.
- **Load-time merge (method A, recommended).** The engine composes one
  ordinary Quake alias model per appearance when it loads, so the renderer is
  unchanged.
- **Equipment and looting.** Worn items per actor, kept through streaming
  and saves; changing or looting equipment recomposes the model, so an actor
  you strip actually looks stripped ([equipment roadmap](../CHARACTER_EQUIPMENT_ROADMAP.md)).
  Planned (stage 4).
- **Measured and dropped:** attaching parts as follower entities (method B)
  costs about 19 entity setups per actor per frame, too much for the slow
  68040 target.
- The baked whole-actor method stays in the builder, selectable, for
  comparison and as a fallback.

## NPC pathfinding

**Status: designed and measured; a follower test is prototyped.** Design:
[NPC pathfinding](../NPC_PATHFINDING.md) (how Morrowind, OpenMW and Quake do
it) and [CHIM NPC pathfinding](CHIM_NPC_PATHFINDING.md) (the graph in the
world format, budgets, gates).

Morrowind stores a small path grid per cell, but only about 10 % of exterior
cells have one, and most outdoor spawn points stand where there is none. So
the plan is a ladder that starts with plain Quake movement; each step runs
only when the cheaper one failed:

1. **Quake chase with stair climbing.** NPCs step with the player's own step
   physics (8.5 units up, a 46 degree slope), driven by Quake's chase order of
   directions. Every staircase that passes the stair gate is then climbable by
   NPCs too.
2. **Stuck check and local ping.** When progress stalls (less than half the
   expected progress over about 1.5 s): a fan of short hull traces to find an
   open direction, then, if that fails, a tiny flood fill (about 8 x 8 step
   cells). Only when stuck, only near the player.
3. **A* on a local patch.** When the player is out of sight or the NPC is
   kited: an A* search on the walkable graph covering the NPC and the player
   (a few hundred units), with a fixed node budget per frame; back to direct
   chase on line of sight. The graph comes from Morrowind's path grids where
   they exist and from the builder's own generator on CHIM collision
   elsewhere, stored per sector and streamed with the chunks.
4. **The unreachable switch.** If the patch has no path (the player on a rock
   or a ledge), the NPC changes behaviour (ranged attack, back off, wait at a
   sensible spot) instead of grinding into a wall: the classic "stand on a
   rock" trick stops working.

**Companions.** `dbg companion` is a prototype follower (on a development
branch, not saved): pick any NPC with the crosshair, or spawn a test one, and
it follows you with the player's step physics, pings around obstacles and
falls back to the small flood fill after repeated failed detours; at most two
traces per think and 48 bytes of state per follower. It is the test bed for
steps 1 and 2.

**Followers through doors.** Designed: at a load door the engine collects
the actors following you (OpenMW's rules: a follow package aimed at you,
nearby, not fighting you), carries a compact record (about 64 bytes each,
proposed limit 4) across the map change next to Quake's spawn parameters, and
places them behind you at the door's arrival point on standing ground. Hostile
pursuers stop at load doors, as in Morrowind
([traversal rules](../NPC_CELL_TRAVERSAL.md)).

## The Ghostfence as a Quake turbulent surface

**Status: the default of a build from v0.0.47-dev1 (`--chim-uv-scroll off` for the still texture; in game `dbg ghostfence on/off`), 21 October 2026 ([GHOSTFENCE-NO-ANIMATION-46](../bugs/GHOSTFENCE-NO-ANIMATION-46.md)); the flickering light style is not done. Idea: the maintainer, 16 October 2026, with the Red Mountain region.** The Ghostfence and the Ghostgate show an
upright, shimmering curtain between the pylons, like electricity and water at once. Quake already draws exactly
this kind of surface: a texture whose name starts with `*` is drawn turbulent (`D_DrawTurbulent`, the warp that
ripples water, slime, lava and the upright teleporter fields), and our lava already uses it. Plan: the fence's
energy texture converted as a turbulent `*` texture on the fence walls, its glow given a flickering light style
(Quake's animated light patterns) for the electric pulse; A/B against the original at the same pose. No new
engine feature: the existing mechanism, mapped onto the Morrowind data.

**Lit from afar (maintainer, 18 October 2026: yes).** The curtain uses fullbright colours, like Quake's lava and
teleporter colours, which ignore lightmaps and the night, so it reads as a shining wall across the rim of Red
Mountain from far away, through the fog as well. Its cost at a distance is measured with the far-terrain layer.

## Angle impostors for heavy plants and rocks

**Status: idea (maintainer, 19 October 2026), to measure before building.** Some meshes cost a lot every frame for
how they look from a distance: emperor parasols, giant mushrooms, big Bitter Coast trees. Quake's own sprite
renderer already draws our distant tree sprites and the interior plant sprites: z-buffered, so a sprite still
disappears behind a building, with transparent texels skipped so it keeps its outline. An angle impostor goes one
step further: the builder renders a heavy mesh from 8 directions once and stores the 8 views as one Quake sprite
with a frame group; the engine shows the view closest to the player's direction, so the object still turns as the
player walks around it, at the cost of one sprite. Near the player the real mesh stays.

What decides it is the pixels drawn, not the polygon count: a large sprite covering many screen pixels can cost
more than a few small polygons. The A/B per mesh type, at the same poses: spans and pixels drawn (`dbg rcount`) and
frame time with the mesh, with an upright sprite and with the 8-view impostor, plus the memory of 8 views against
the mesh. Hardware sprites are no option here: the chipset knows no depth, so they suit the HUD, the crosshair and
the pointer, not objects in the world.

**Distant silhouettes (maintainer, 19 October 2026).** The same path as a far ring for buildings, rocks and big
plants: past a set distance the engine draws the object's sprite instead of its mesh, so it keeps its outline
against the sky and the fog, as the distant trees already do. Two things to measure with it: the light (a sprite
rendered in daylight needs the fog colour and the night tint applied when it is drawn, as the distant trees get
them now) and the pixels (only the far ring, where a sprite covers few pixels). It belongs with the distance layers
below: far terrain and mold shells.

## The distant view: far terrain and mold shells

**Status: release blocker for v0.0.33; designed, a first layer is being
prototyped.** Tracked as [CHIM-FAR-TERRAIN-33](../bugs/CHIM-FAR-TERRAIN-33.md).

CHIM draws full-detail chunks inside the ring only, so beyond the view
distance there is only fog and sky: valleys look empty and Vivec cannot be
seen from the world. The legacy region maps drew these views much better.

- **Reference look.** v0.0.32's horizon, the HORSTATOR APPROVED method
  (`aw_skyline_fill 0`), and its sky veil. Every CHIM change to the distant
  view is A/B-checked against v0.0.32 at the same poses (the maintainer's poses and
  the release gallery poses) and must not look worse. The skyline fill stays
  selectable as an experimental alternative.
- **Far terrain.** A resident, low-detail layer of the land for the frame and
  beyond its edge, made from the same height samples as the chunk terrain,
  stored once, paid for from the same memory budget, drawn beyond the ring
  the way the approved horizon draws land at the fog plane.
- **Mold shells later.** Closed low-poly shells for landmarks such as Vivec's
  cantons, so they stand on the horizon without their full cost. The shell
  tool exists and was measured on Balmora; the engine switch is designed
  ([distant shells](../DISTANT_SHELLS.md)).
- **The island cut-out (maintainer, 19 October 2026: the target for
  [HORIZON-HOLES-31](../bugs/HORIZON-HOLES-31.md) and
  [VIVEC-DISTANT-BRIDGES-32](../bugs/VIVEC-DISTANT-BRIDGES-32.md)).** Distant views break up where tall
  things meet the sky: Vivec's cantons and bridges, mountainsides; Balmora's low roofs on flat ground hold up.
  One far model of the whole island, the topography with every building and tree baked in as a cut-out, built
  once by the builder and streamed by region like the far terrain. The simplest form is a coarse height grid
  (for each point the highest thing standing there: ground, roof, canopy, canton top) drawn as flat fog-coloured
  spans beyond the frames: no seams of its own, so far geometry never breaks. Cheaper still for the far skyline:
  a horizon profile per cell (the highest elevation angle of all distant geometry in a few hundred directions,
  a few hundred bytes), one fill per screen column. A height grid cannot show an arch, so a bridge seen from far
  becomes a band down to the water; for those few objects the low-poly shells (mold shells, collision hulls)
  sit on top. A/B against today at the same poses (the Vivec bridges, Balmora across the river at sunset).
- **Solid at every distance: the order. Proposed 19 October 2026.** The maintainer's examples: Vivec's walkways
  cut in the middle at a distance, Balmora's walls, hillsides and the Ghostfence, which should all stay solid.
  Cheapest first: (1) the fog rule, no cut before the fog is opaque (settings and a builder check, no new drawing
  code); (2) long structures (walkways, town walls, the Ghostfence) cut as one piece at one distance, so they fade
  together instead of losing their middle; (3) the far shell in flat fog colour, measured in the sandbox, designed
  with the streaming as [one system](CELL_CROSSINGS.md#near-and-far-as-one-system-upcoming-direction); (4) if the
  68040 cannot afford (3), the horizon profile above (one fill per screen column, a few hundred bytes per cell)
  for what lies far behind the fog, with the shells only for the few arches. 20 October 2026: (1) and (2) in
  source, off until the in-game A/B (`dbg fog rule`, `dbg cut groups`: switches in `aw_cull`;
  [CHIM-BRIDGE-POP-PIECES-44](../bugs/CHIM-BRIDGE-POP-PIECES-44.md)).
- **No artificial clamps.** The CHIM view distance follows the ring and the
  memory budget, with any remaining limit measured and stated.

## M3: Vivec on CHIM

**Status: stage A in progress, stage B designed.** Design: [world
format, "Planned: all of Vivec (M3) and the open world (M4)"](WORLD_FORMAT.md#planned-all-of-vivec-m3-and-the-open-world-m4).

- **Stage A, the Arena canton first.** The existing Arena area as one frame
  (12 x 12 chunks, no format change). Canton bodies that reach into the frame
  are stored and drawn whole, so the straight cut of the legacy preview
  ([VIVEC-ARENA-FRAME-EDGE-32](../bugs/VIVEC-ARENA-FRAME-EDGE-32.md)) goes
  away. Parity with the v0.0.32 preview, each a build gate: residents stand on
  the frame's own collision ([VIVEC-ARENA-ACTORS-32](../bugs/VIVEC-ARENA-ACTORS-32.md)),
  the arrival point is a standing spot, the closed frame edge says "Area
  unavailable", doors and `dbg tp` names work. The gates and the engine's
  closed edge are in source.
- **Stage B, all of Vivec in one frame.** Every canton, the Temple, the
  Foreign Quarter, the bridges and the waistworks exteriors, seen from the
  open world and later joined to it. 39 x 43 chunks give 195 sector files,
  more than a classic FFS directory block holds, so **format 0.6** puts
  sectors in one folder per sector row; nothing else in the format changes.
  One city frame does not fit the engine's coordinate range
  ([CHIM-FRAME-COORD-RANGE-33](../bugs/CHIM-FRAME-COORD-RANGE-33.md)): the
  frame layout is an open decision (see the preflight below).
- **Vis.** Canton bodies and the Temple are the first big closed masses CHIM
  meets: real occluders that hide whole streets. Visibility rows and
  placements per view are measured, and the counters may not get worse than
  the legacy preview.

### M3 preflight (10 October 2026)

**Status: measured without a build; nothing of Vivec is in a v0.0.36 build yet.**
The Arena is still withdrawn from images, and every Vivec memory figure below
comes from CHIM builds of 9 October, so the first step is to measure again on
the current builder.

- **The city.** The union of the eight district frames is 36 cells
  (39 x 43 chunks), 15 of them Vivec's own; about 4,200 placed objects with
  233 distinct meshes and 1.0 million placed source triangles, 1,159 flora
  placements, 32 NPCs and 118 doors in the Vivec cells, 144 interiors listed
  in the district settings. The district frames overlap in 16 of 28 pairs,
  so one world cannot hold them as they are: stage B needs merged frames.
- **Large models.** 18 meshes (26 placements) are wider than the 512-unit cut:
  the canton bodies (about 1,780 units), the High Fane quarters (1,414), the
  Temple pool water (1,369), the Ministry of Truth (915), four more Temple
  district meshes (728-933), and also 24 wide trees and 31 parasols, which an
  area-wide cut would tile too (to measure, or keep flora whole).
- **Memory, one hotspot.** With the cut, five district frames fit the
  6,242,304-byte chunk room (3.71-5.72 MB); the Temple, St. Delyn and
  St. Olms frames are 1.5-2.0 MB over, all at the north end of the Temple
  plaza (the two Vivec statues, the Ministry of Truth, the High Fane). The
  'vivec-deep' detail budget fits the Temple frame with 20,016 bytes to spare
  (0.3 %). The load ring is over the room in 5 of 7 measured frames.
- **Stairs.** The Temple's palace steps and the High Fane quarters' flights
  ([VIVEC-TEMPLE-STAIRS-33](../bugs/VIVEC-TEMPLE-STAIRS-33.md)) are the only
  failing flights in the district frames; the other five frames pass
  (2,665-3,793 steps and ramps each).
- **Frame layout.** One city frame is 96 x 608 units past the engine's
  coordinate bound; of two frames, the north one is 96 units over on each
  side; three frames fit
  ([CHIM-FRAME-COORD-RANGE-33](../bugs/CHIM-FRAME-COORD-RANGE-33.md)). This
  section is the one Vivec frame plan
  ([DOCS-VIVEC-FRAME-PLAN-36](../bugs/DOCS-VIVEC-FRAME-PLAN-36.md)). Maintainer
  decision (10 October 2026): widen the coordinates first, as a measured
  spike (in source behind the engine switch `AW_EXP_WIDECOORD`, off by
  default), then one city frame; the Arena returns to default builds after
  its stage A playtest; 'vivec-deep' becomes the Vivec default after the A/B
  shots and its seam audit; flora stays out of the cut until measured.
- **Tools.** The memory predictor reads Vivec 28-54 % low
  ([CHIM-PREDICT-VIVEC-LOW-36](../bugs/CHIM-PREDICT-VIVEC-LOW-36.md)), so
  Vivec memory is decided by built heap gates only; the seam audit does not
  cover the detail budgets yet
  ([CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36](../bugs/CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36.md)).

- **Measured on the 9 October Temple world** ('vivec-deep', cut on):
  collision is 6.2 % of the model bytes; 30.7 % of the placed faces lie
  wholly below the water plane (kelp, seabed rocks, waterspouts); at the
  memory peak 80 % of the ring's model bytes belong to placements more than
  300 units away, so a coarse distance level is the largest lever measured;
  inside the ring the chunk visibility culls almost nothing (99.9 % of the
  ring visible on average). One city frame would hold 69 actors (600 allowed)
  and 118 teleport doors (128 rows in the door bank). The placements sent
  from one view position (all directions, before the view frustum) hold up
  to 37,112 faces, against 12,288 surfaces the renderer draws per frame
  ([RENDER-SURFACE-OVERFLOW-SILENT-36](../bugs/RENDER-SURFACE-OVERFLOW-SILENT-36.md)).

Steps, each gated before the next:

1. Stage A preflight (seconds): the area check with Balmora and Seyda Neen,
   the town table's hand-over rules and the reuse plan, without a build.
2. The cut as an Arena area setting (512 units), so Balmora and Seyda Neen
   keep their models whole, flora kept whole; a test for it (in source,
   10 October 2026).
3. A build with the Arena as a CHIM-native town (requested as a MiniWind
   build through the build server, `aw request --kind miniwind`) and every
   gate on its frame:
   validation, heap (active, load, largest block), stair walk, hull chains,
   residents on the frame's collision, the arrival point, the closed edge,
   doors and `dbg tp`, far terrain, sky-bank texels, seams.
4. A MiniWind sandbox at the Arena: A/B against the v0.0.32 preview (as a
   labelled regression test) and OpenMW at fixed poses, headlamp pairs,
   renderer counters, the five v0.0.32-dev3 findings at their poses.
5. Stage B: the wide-coordinate measurements (sign-on size, bytes and time
   per frame, narrow against wide), then one city frame (1,596 chunks, 182
   sector files in format 0.6 rows), 'vivec-deep' with its seam audit, the
   Temple district first.

## M4: the open world

**Status: designed.** Same design section as M3.

### The frame grid

The island is about 42 x 46 cells, more than the coordinate range of Quake's
node bounds, so the open world cannot be one frame. Frames become a fixed grid
of 3 x 3 cells anchored on Balmora's frame; towns become the content of the
frames that hold their cells, and Seyda Neen and Vivec are re-cut onto the
grid. The engine keeps up to four frames resident and shifts the origin when
you cross a frame edge, with no map load ([frame re-centring plan](ENGINE.md#frame-re-centring-plan-not-implemented)).
Format 0.6 adds an owner-frame field so a placement can reach into a
neighbour's chunks. The first slice is Balmora with the grid frames east and
west of it: crossing with no stop, standing across frame edges, the memory
ring at a frame corner, and disk bytes against the legacy world maps of the
same cells.

### The memory estimator

**Status: prototyped** (`tools/chim/predict.py`, a draft). It predicts,
before anything is built, how many bytes the engine's memory zone must hold
at any position on the island:

- the distinct models of the placements in the ring (each model counted
  once, so this grows more slowly than the placement count), the terrain per
  chunk, a catalogue entry per placement and the models' textures;
- for two ring radii: the active ring (view distance plus hysteresis, what
  the heap gate checks) and the load ring (plus the prefetch margin), which
  is what a moving player really holds, because a chunk is released only
  past the load radius;
- coefficients fitted on built worlds with the heap gate's own block sizes,
  checked by leaving one town out: about plus or minus 20 % at the load
  radius on towns like the ones it was fitted on, about 40 % on a town type
  it has not seen; the active-radius figure runs low and is not compared with
  the gate;
- a second opinion from placed face counts, which sees single huge meshes
  (cantons) that a placement count misses; when the two disagree by more than
  a quarter, the place is built and measured;
- a fragmentation check: a ring is safe only when the largest free piece left
  after loading fits the largest model it still needs (one measurement so
  far; the engine's own zone simulator will replace it).

Blind spots, written down: placements that reach into chunks other than
their own, terrain whose collision cost depends on slope and water, and
everything outside the zone (interiors, actors, sounds). Over the whole
island it flags a handful of dense town cells as over budget at the load
radius; the Vivec Arena cell fits by both opinions. The heap gate on a built
world always has the final word.

### The density planner, and why frame cuts do not lower the peak

**Status: planned.** The polycount heatmap of the world metrics
([polygon heatmap](../POLYGON_HEATMAP.md), [world estimate](../WORLD_ESTIMATE.md))
and the estimator order the work: the densest and riskiest cells first, and
cells flagged before a build is spent on them.

Moving where frames meet does **not** help a dense place: the ring is centred
on the player, so the memory peak at a position is the same wherever the
frame edges are. Dense places fit only by spending less there: simpler models
at a distance, a measured and stated view budget per frame, or a larger zone.

## Memory

Detail: [CHIM engine, "Memory"](ENGINE.md#memory) and the heap gate in the
[world format](WORLD_FORMAT.md#the-heap-gate-05).

- **Load radius, not just view radius. Status: measured.** A chunk is
  activated within the active radius (636 units: view 540 plus hysteresis
  96) and released only past the load radius (892: plus the prefetch margin
  256). On Balmora the load ring peaks at about 7.66 MB against 6.24 MB of
  chunk room, at 661 of 9,216 positions. The heap gate reports the active
  ring, the load ring and the largest single block, and follows the engine's
  stated policy (`tools/engine_limits.py`) instead of keeping its own copy.
- **Full rotation in the placement record. Status: decided for the project, next after the cell crossings (19
  October 2026); first measured 16 October 2026.** Island-wide on the v0.0.45 world: 33,426 stored models made
  from only 1,400 distinct meshes, 26,477 of them tilted variants (550 MB), and 91 % of the 713 MB of model data
  copies beyond one per mesh (barnacles alone in 2,022 variants;
  [CHIM-TILT-VARIANTS-SPLIT-33](../bugs/CHIM-TILT-VARIANTS-SPLIT-33.md)); up to about 650 MB of the 1.32 GB CHIM
  world, less what collision copies keep. Engine side: drawing a turned model is Quake's own path
  (`R_RotateBmodel`) and costs one change of view per model, not per vertex; uniform scale is added to the same
  transform; collision is the open part (below). Selectable storage: mode 0 a baked copy per tilt and scale
  (today, kept), mode 1 one shared model with rotation and scale in the placement record; a separate setting for
  collision; mode 1 the default once smaller and no slower on the 68040 and 68060 profiles. The interiors need the
  same mechanism, so it comes before them ([roadmap](../ROADMAP.md)). It starts with a study of the engine's turned
  models (drawing and collision as they are, CHIM's yaw-only placements) and of what scale needs, which Quake lacks,
  before any code. From 16 October: a placement
  record holds a position and a yaw, so every tilted or scaled placement of a mesh is baked into a model of
  its own. Morrowind tilts and scales a lot (Telvanni roots, kelp, shells, barnacles): in the 13 cells left
  out of v0.0.41-dev4, 854 of 1,586 stored models are tilted copies, 20.6 of 41.5 MB. With the rotation in
  the placement (one drawn model per mesh and scale) they need 836 models and 17 MB less (41 %); with scale
  too, 427 models and 23.8 MB less (57 %). The renderer already draws a brush model at any rotation
  (`R_RotateBmodel` uses all three angles), so drawing costs what it does now. Collision is the hard part:
  the player's box is axis-aligned, so a tilted model keeps a small tilted collision hull of its own, and
  scale needs renderer support. A world-format step (minor version) and an engine change; measured before
  adopting on the cells over the memory budget. A builder-only table that merges near-identical tilts
  saves little: 0.6 % exact (two placements share a model only when they differ by a world yaw, because
  Morrowind applies its Z rotation first), 2 % with tilts snapped to 2 degrees.
- **The same building blocks everywhere. Status: direction (19 October 2026).** One stored model per mesh, placed
  by reference at any angle and size, is the rule for every kind of content, not only outdoor scenery: people
  from a shared library of body parts with a recipe per person (3,500 baked people use only 942 part meshes, about
  72 uses each; [Modular NPCs](#modular-npcs)), and interiors from Morrowind's own kit pieces (halls, walls,
  stairs per house style), so a room becomes mostly a list of placements instead of about 2 MB of copies.
- **Rewriting the upper half of the world streaming. Status: direction (19 October 2026).** What works today is
  the chunk streaming inside a frame (reading chunks, the cache, grafting them into one world). What has to go is
  the layer above it: frames as separate maps with a level change between them
  ([Cell crossings](CELL_CROSSINGS.md)). The continuous world replaces that layer, near detail and the far shell
  are designed together, and shared models change what a chunk holds. Whether the chunk layer itself is rewritten
  too is decided by the 2x2 sandbox: if it cannot hold a window of several frames cleanly, it is.
- **Fragmentation. Status: in source on a branch.** The zone never moves a
  block, so a ring that fits by the sum can still find no piece large enough
  for a house model once locked blocks split the room (at a dense Balmora
  pose the largest free piece was 211 KB, the houses 258-292 KB). The repair:
  small blocks from the zone's high end and large ones from the low end, as
  Quake's Hunk keeps two ends; a loading chunk keeps what it has and releases
  farther chunks instead of evicting its own models; a chunk can be activated
  without a model that has no room yet. A zone walk gate runs the engine's
  own zone code over a walk through every frame and fails when a step leaves
  the player without ground
  ([CHIM-CHUNK-LOAD-FAIL-33](../bugs/CHIM-CHUNK-LOAD-FAIL-33.md)).
- **The 2 MiB Hunk-gap rule. Status: kept (project decision).** The engine's
  heap audit keeps at least 2 MiB of the map heap free at the load peak. The
  CHIM zone is taken from that heap when a CHIM map starts, so the zone may
  only be as large as the rule allows: measured, Balmora's map allows the
  default 6,864 KiB, Seyda Neen's 5,888 KiB, because its frame map carries
  all of the town's actors and flora sprites at once
  ([CHIM-SEYDA-HUNK-GAP-33](../bugs/CHIM-SEYDA-HUNK-GAP-33.md),
  [CHIM-ZONE-BUDGET-33](../bugs/CHIM-ZONE-BUDGET-33.md)). Two levers are
  tested, in this order, before any larger zone:
  - **Sprite statics streamed with chunks. Status: planned (first).** Seyda
    Neen's flora sprites are ordinary Quake static entities in the frame map
    today; streaming them with their chunks takes them out of the map's
    fixed cost, followed by a memory check over the whole map.
  - **A 12 MiB heap across the whole game. Status: planned.** Fast RAM has
    room for one more MiB at the 16 MB baseline on both towns, untried.
- **`--heap-mb`: "you do you". Status: planned.** A builder option like
  `--jobs`: the map heap in MiB, exact, default 11; beyond the safe profile it
  prints one loud warning and runs anyway, never refused; every gate uses the
  build's own value.
- **Static entities as a stated budget. Status: planned.** Measure what
  raising the static-entity limit costs (bytes per entity, heap headroom) and
  make it a measured budget instead of a fixed clamp.
- **Shared texture mappings. Status: measured and dropped.** Texture mappings
  (texinfo) are about 40 of a face's bytes, so sharing them looked like a big
  win. The builder already stores each mapping once per model; Morrowind's
  UVs give almost every triangle its own mapping. An exact world-wide table
  saves 1.4-4.6 % of the mappings of Balmora and Seyda Neen (under 1 % of the
  ring's bytes) and about 10 % in the Vivec Arena: not worth a format change.
  Rounding mappings changes the pixels and saves little. Unmeasured
  leftover: dropping one decoded field that can be computed when needed
  (about 9 % of the mappings, same pixels).
- **Other open memory items:** the zone size itself (the engine's 6,864 KiB
  zone less the 2 x 384 KiB frame-world pool, which the heap gate reads from
  the engine source, vs a zone the builder writes per world,
  [CHIM-ZONE-BUDGET-33](../bugs/CHIM-ZONE-BUDGET-33.md)); pack directories
  that would grow to about 400 KB island-wide if kept whole
  ([CHIM-PACK-DIRS-33](../bugs/CHIM-PACK-DIRS-33.md)); collision data read
  only for chunks near the player; resumable decoders for hard per-frame
  read bounds ([CHIM-READ-BUDGET-33](../bugs/CHIM-READ-BUDGET-33.md)). The
  optional cache bank (`-chimcache`, extra Fast RAM where shared models
  survive map changes) is in source.

## Build speed

Development must not wait on the builder; release candidates and finals are
always built from scratch and refuse every shortcut below.
Guide: [CHIM build guide](build_guide/README.md).

| Idea | Status | What it does |
| --- | --- | --- |
| Stage cache | in source (stage fingerprints on a branch) | `--reuse-from RUN` reuses an earlier run's unchanged stages; each stage's fingerprint covers its command, the code it can reach, the game inputs, tools, environment and the stages it depends on, independent of folder paths ([build profile](../BUILD_PROFILE.md)). The world terrain keeps a per-map cache across development builds. |
| Prerendered store | prototyped | Finished stage outputs (CHIM worlds, interiors, region maps) kept by version and area across runs and reused by fingerprint, every file verified while copying; a failed build stores nothing; releases write but never read. |
| Leaving content out | in source on a branch | `--exclude` groups (video, music, voice, NPC gallery, interiors, harvest), each with its own option; dressing, clutter and flora are never left out; the image and receipts say "quick test build" ([quick test builds](build_guide/QUICK_TEST_BUILDS.md)). |
| Only what an area references | in source on a branch | `--exclude-unreferenced` builds only the content the built area references. |
| MiniWind | in source on a branch | The MiniWind playtester build: Balmora on CHIM with its interiors, booting straight into Balmora, development versions only, labelled as a partial-area test ([MiniWind playtester build](../MINIWIND_PLAYTESTER.md)). |
| MiniWind presets | planned | `--miniwind-preset NAME` for repeatable small builds of a chosen spot (the Vivec Arena pit as the worked example). |
| Start straight in the game | designed | `--direct-to-game-map` with an area, `interior:<cell id>`, `cell:X,Y` or `pos:X,Y,Z@HEADING`, plus `--quick-character`, skipping the intro. |
| Incremental image | planned | Rewrite only the image files a change reaches, instead of assembling the whole image again. |
| Longest work first | in source on a branch | Worker pools hand out the largest items first from measured cost history, so no stage ends on one core while the rest wait ([parallel build](../history/superseded/PARALLEL_BUILD.md)). |

## Texture effects: a bug turned into an effect

**Status: in source.** [CHIM texture effects](TEXTURE_EFFECTS.md),
[CHIM-TEXTURE-SPECKS-33](../bugs/CHIM-TEXTURE-SPECKS-33.md).

The first CHIM worlds showed bright single-texel specks: CHIM textures had
skipped the image step that keeps texels off the palette entries the sky
repaints, so a few texels turned into sky colours. The fix sends every CHIM
texture through the same palette translation, and the validator refuses
sky-bank texels. The look itself was liked, so it was kept on purpose: a
`.chimfx` effect file can add specks of chosen colours to chosen textures,
byte-identical in every build, off unless selected. The shipped example is
`autumn_glitter_leaves`: orange and cream specks that glow at dusk.

## The slow-accelerator reality

Where a slow frame goes, part by part, and how the speed work adds up and is
calibrated on real machines: [where a slow frame goes](../performance/SLOW-FRAME-BREAKDOWN.md).

**Status: measured; the breakdown is in progress.** Measured in FS-UAE on
Balmora on CHIM (relative numbers, busy host): the normal JIT preset runs
20-25 frames per second, but an A1200 with a 68040 at about 50 MHz (the slow
accelerator preset, cycle-exact) runs **about 0.8-0.9 frames per second**,
about a second for every frame in town; a chunk crossing adds up to about
0.3 s on top. At half that clock it is 0.4-0.5. Streaming is not the main
cost: the town itself is (the preset is described in the
[FS-UAE guide](../FS-UAE-PLAYTESTING.md), section "Slow accelerator preset").

The plan:

- **Find where the second goes.** One sweep at the benchmark cameras with
  one thing changed per variant (entities off, world only, smaller view,
  coarser mip level, shorter draw distance, fog off), plus a drift rerun.
- **Spend less per view.** Model faces dominate every Balmora view
  ([CHIM-VIEW-FACES-33](../bugs/CHIM-VIEW-FACES-33.md)); the levers are
  distance detail (simpler distant models, mold shells), cheaper per-model
  work and the visibility counters.
- **Budget new features against it.** NPC pathfinding, far terrain and
  modular NPCs are costed on the cycle-exact preset, not on the JIT.
- **One real number.** A frame and disk measurement on a real accelerated
  A1200 ([hardware benchmark](../HARDWARE-BENCHMARK.md)); until then every
  emulator figure stays relative ([BENCH-JIT-PROFILE-32](../bugs/BENCH-JIT-PROFILE-32.md)).
  The first one arrived on 16 October 2026: a tester's A4000 with a 68060 at
  100 MHz ran an earlier build at about 0.2 frames per second, about 0.1 above
  his own emulator runs
  ([CHIM-SLOWCPU-FRAMETIME-33](../bugs/CHIM-SLOWCPU-FRAMETIME-33.md)). Next: the
  same build indoors and outdoors with the console counters, and whether the
  68060 support library was installed.

Two directions follow from what the frame is spent on (16 October 2026), each
measured before it is built:

- **Detail by distance and size.** The far cut-off at the fog distance already
  exists: nothing past the fog is drawn. What is missing is detail that falls
  away before it. Small objects (cups, plants, clutter) drop out well before the
  fog, large buildings stay to the fog edge; past a set distance a block of
  scenery becomes one merged, simplified shape per chunk; meshes get simpler in
  the last stretch before the fog. A counter of drawn models and faces per
  distance band and size class decides which of these pays first.
- **Scenery that is not drawn as brush models.** Quake's brush models are made
  for a few doors and lifts: each one is set up and its polygons clipped against
  the world on its own, and at Morrowind's density that is most of a slow frame.
  Large static scenery can become part of each chunk's own world geometry (drawn
  front to back and culled with the world, at the price of storing it per
  placement instead of once), small props can be drawn the way Quake draws items
  and monsters (no world clipping), and clutter as sprites, as flora already is.
  Brush models stay for doors and moving parts. Each option is compared at the
  same views (frame time, counters, memory, disk), and the current method stays
  selectable.

An independent review of the renderer (16 October 2026) sharpened the order.
The brush-model share is two costs of similar size, walking each model's tree
and emitting its polygon pieces; baking scenery into the world removes only the
first, and the 16-bit limits of the chunk pool stand in its way. Even with
brush models at zero, a slow frame keeps 400-700 ms (edge scan, the fog pass,
the server frame, the screen copy), and a Balmora view sends about 13,500 faces
where Quake was designed around 800 surfaces. So the plan is:

1. Measure first: the frame with entities and fog off, the walk and the emit
   timed apart, faces per distance band and size, leaves touched per placement,
   small props drawn as items against brush models, and one real 68060 run.
2. Fewer faces in view: the size-scaled cut-off and the heaviest models.
3. A coarser terrain drawing tree, so most props sit in one leaf, which is
   Quake's cheap path.
4. The fog pass folded into drawing, and a lighter server frame.
5. A 68060 build without the floating-point instructions that trap on that
   processor.
6. A larger surface cache from extra memory, and the window size as a player
   option (the full AGA picture stays the default).
7. Hand-written 68k code for the measured hottest loops.
8. Scenery baked into the world last outdoors; interiors (sealed rooms whose
   every mesh is a separate model today) are the clean case for it.

**Next measured experiment: town clutter as items (30 October 2026, not built).**
Central Ald'ruhn, facing west (aw_aim 180) from the town spawn (local -79 230 603),
is the slowest of its four headings on the Raspberry Pi 4B (7 fps against 9-13), and
the size-scaled cut-off gains nothing there (aw_cull 1: 7.1, 4: 7.2, 4 plus the fog
rule: 6.5 fps). The view is not one heavy model: a market stall a few hundred units
away (urns, baskets, an overhang) plus a long street of Redoran houses. The renderer
counters (dbg rcount 3, FS-UAE with JIT, 32 MB Fast, v0.0.57-dev4) show the brush
models doing the extra work:

| Heading | Brush models drawn | Brush-model faces tested | Spans | Brush models (us) | Scan (us) | Frame, renderer (us) |
|---|---|---|---|---|---|---|
| 0 (east) | 9 | 2,914 | 3,151 | 4,879 | 2,145 | 9,866 |
| 90 | 10 | 2,692 | 1,919 | 3,908 | 1,477 | 8,580 |
| 180 (west) | 22 | 5,671 | 7,587 | 8,409 | 4,928 | 15,044 |
| 270 | 8 | 3,205 | 3,636 | 5,413 | 2,632 | 11,355 |

Mesh reduction of the stall's models gains little (most of their faces sit on
locked rims). The experiment: draw small town props (urns, baskets, crates, sacks)
as items, with no world clipping, and compare this view like for like (fps on the
Pi, the counters above, memory).

The first measurements of that plan (16 October 2026) are written up in
[where a slow frame goes](../performance/SLOW-FRAME-BREAKDOWN.md).

A faster processor alone (PiStorm-class) or a graphics-card screen does not
change this order: at 0.2 frames per second the 3D work, not the screen, is the
limit ([comparisons](../COMPARISONS.md)).

## Island-wide audits (mechanism classes)

**Status: rule adopted; each audit's status below.** A geometry or collision
bug usually has a cause that repeats wherever the same converter path runs.
So every finding: (1) names its mechanism, (2) sweeps every mesh or cell that
goes through the same path, island-wide, ranked by the placements affected,
(3) is fixed once in the shared converter, (4) keeps the sweep as a builder
gate. Each CHIM frame sweep (M3, M4) runs all known audits on its cells before
the build counts, ordered by the polycount heatmap and the estimator.

| Mechanism class | Audit | Status |
| --- | --- | --- |
| Seam tears | Mesh reduction tore seams between material sections, leaving open hulls (the silt strider showed sky through its body); boundary-locked reduction, and a seam-tear audit as a builder gate ([MESH-LOD-OPEN-SEAMS-33](../bugs/MESH-LOD-OPEN-SEAMS-33.md)) | in source on a branch |
| Stair walk | One stair rule in the shared collision layer (authored collision where the convex proxy invents too-steep faces) and a walk test of every flight on every CHIM world ([stair rules](../STAIR_RULES.md), [COLLISION-STAIR-SLOPE-32](../bugs/COLLISION-STAIR-SLOPE-32.md)) | in source |
| Hull bevels | Exact terrain standing hulls, with a seam check at every chunk border in the validator ([CHIM-TERRAIN-HULL-BEVELS-33](../bugs/CHIM-TERRAIN-HULL-BEVELS-33.md)) | in source |
| Sky-bank texels | The validator refuses texels on the sky's palette entries ([CHIM-TEXTURE-SPECKS-33](../bugs/CHIM-TEXTURE-SPECKS-33.md)) | in source |
| Hidden faces | Placed-model faces buried under the terrain, which the legacy maps culled ([CHIM-HIDDEN-FACES-33](../bugs/CHIM-HIDDEN-FACES-33.md)) | open |
| Memory fit | The strict heap gate (active ring, load ring, largest block) and the zone walk gate on every frame | in source (zone walk gate on a branch) |

## Collision from what the game already knows

**Status: decided as a direction, 20 October 2026; not started.** The stair walk above was the right safety net
while the converter guessed at collision, but it walks every step of the island to rediscover what the game data
already says: a mesh's own collision node (or its drawn mesh), and the original movement rules for the highest
step, the steepest walkable slope and the player's size (the original game, OpenMW's movement code and the GMSTs).
The second method builds collision from those, walkable by construction: a plate per tread or an invisible ramp
under a flight, steps still drawn as steps, and only the surfaces the player stands on kept exact. Its check is
arithmetic (standing surface against the drawn one, step heights against the limit); the walk becomes a sample. The
first method stays selectable and unchanged, with its stair gate, and the walk results it has already recorded are
kept as the reference for the comparison. Both are compared on the same frames (memory, build time, the walk
sample, clips at stairs, docks and ladders), and the new one must first give the same result at every place where
a stair or collision bug was fixed. A collision simplifier (plates, merged coplanar pieces) replaces the visual
mesh optimizer for this; the visual optimizer moves vertices of steps and made merged meshes larger before.
See the [roadmap](../ROADMAP.md) and [BUILD-STAIR-WALK-BRUTE-FORCE-46](../bugs/BUILD-STAIR-WALK-BRUTE-FORCE-46.md).

### Terrain collision from heights (measured prototype, 21 October 2026)

**Status: design and host measurement only; no engine or builder change, no default change.** Today every terrain
record stores qbsp's standing hull: the union of the tile prisms already moved out by the player's box, as planes and
clipnodes. The alternative traces the player's box against the ground itself: each ground polygon of the chunk (the
render faces that are not water) is a prism down to the chunk floor, and the engine's exact box-against-convex trace
(the placed-model collision method, a Minkowski sum with every bevel) sweeps the box against the prisms whose box
meets the move, the way a heightfield shape works in other engines. The walkable rules (step 34, slope 46 degrees)
are then read from the hit normal, as today.

Measured on the v0.0.46 world, every tenth terrain record (9,736 records, 200 moves each inside the chunk: random
moves, drops, walks at foot height, step-downs), against the stored hull traced by the engine's own trace code:

| Records | Moves | Same end (0.05), same hit, same start state | Different start state | Hit against miss | End apart 0.05 or more |
| --- | ---: | ---: | ---: | ---: | ---: |
| generated (0.11) | 1,667,800 | 99.979 % | 41 | 5 | 303 |
| other, not lava | 268,200 | 99.979 % | 3 | 1 | 51 |
| lava beds | 11,200 | 80.2 % | 935 | 113 | 1,174 |

What does not agree, by kind: (1) lava beds: the stored hull keeps the lava volume solid up to the lava surface,
and the prototype makes no lava prisms yet (it skips the lava surface like water), so lava needs its own flat prisms
before this can replace the stored hull there; (2) moves that end within a fraction of a unit (median 0.11) of the
stored end, mostly grazing moves along a slope, where the stored planes are rounded and the prism planes are not;
(3) a hit exactly on the crease between two ground polygons, where the two methods report the other polygon's normal
(103 moves, and 10 more where the two normals fall on either side of the walkable slope limit); (4) a start exactly on or inside the surface,
where the stored hull calls the whole move solid and the prisms let it slide out, or the reverse (44); (5) a few
moves the stored hull stops on a bevel or underside plane that the prisms do not have (6).

Cost per move: 33.6 clipnode visits with the stored hull against 36.3 prism plane tests (generated chunks; 36.9
against 53.7 on the converter's triangles; each is two dot products), 2.8 prisms per move with a box lookup; the
prisms are moved out once when the chunk joins (about 10,800 floating-point operations, 118 planes held per chunk).
Bytes it would remove from a 0.11 world: the clipnode payload (55.7 MB) and the planes only the hull uses (about
78 MB of the 98.0 MB plane payload) of the 83,236 generated records, and up to 42.7 MB more in the others before
packing, about 176 MB of the 298.5 MB of terrain records. It would ship as an option with an A/B against the stored
hull, never as a silent replacement.

## The Arena Pit's upper tiers as backdrop panels

Status: planned (an idea of the maintainer, 28 October 2026; nothing built). Detail and the measured context:
[PERF-ARENA-PIT-SLOW-48](../bugs/PERF-ARENA-PIT-SLOW-48.md).

The cost in the Vivec Arena Pit is not only the pit but everything above it. Racing games of the first 3D console
generation drew the roadside landscape as a picture on a few flat planes, and the stands and balcony of the Pit can be
treated the same way: the player is held on the pit floor and always sees them from about the same place, from below
and at a distance, so the parallax is small.

Measured context (v0.0.54-dev1, JIT, FPU, maximum CPU, 32 MB Fast): the bowl is one placement of 15,760 faces that is
always in view (rooms get no fog, far cut or detail step). Its brush faces take 14.7 to 24.4 ms of a 23.0 to 43.9 ms
view, and the frame takes 25 to 38 ms.

The plan:

- Render the upper tiers (the band from height 64 to 160, 9,349 of the bowl's small faces) from the centre of the pit
  floor at 8 to 16 headings. The shots are taken from the real room in the emulator, so the original lighting is baked
  in.
- Cut the shots into textures on a ring of 8 to 16 large quads at the stands' radius.
- The pit wall, the floor and all collision stay real geometry.
- It is room-only: the Pit is its own room (vai000) behind a load door, so the outdoor world is not re-keyed.
- Cost: about 128 KB at 8 bits for 16 panels of 128 by 64.
- The stands are empty in the original, so the panels are still pictures with nothing to animate, which suits the method.

Open: how the panel seams look at the turn of the head, and whether the pit wall's top edge hides the join.

This is type 3 of the setting `aw_vivec_arena_pit_type`: 0 the bowl whole, 1 tiles (the default), 2 tiles and the room
detail budget, 3 the backdrop panels. Types 0 to 2 are done; the image stores the room once per type and the door loads
the chosen one. The first A/B of type 1 against the whole bowl cut the frame time by 7 to 11 ms on the pit floor and by
7 ms on the upper level, with the same surfaces drawn.

Two more ideas for the same room, each with what it would buy:

- **A lossless mesh optimizer pass on the bowl.** 4,289 of its faces are under 4 square units. Merging neighbouring
  coplanar faces into fewer, larger polygons keeps the picture identical and cuts the per-face cost of the software
  renderer, which the detail budget (type 2) does by lowering detail instead.
- **Symmetry.** If the bowl is rotationally symmetric, one stored sector placed several times saves model memory and
  load time, not frame time. Being checked by geometry.

A far cut bounded by the original's fog would not help: the Pit's fog starts beyond the room (see the
[bug page](../bugs/PERF-ARENA-PIT-SLOW-48.md#a-finding-the-originals-fog-cannot-bound-a-far-cut-here)).

## Also held back

Not in the first CHIM releases, written down so they are not lost:

- **Shared interior props** with per-placement lighting (the streamer
  design's options B and C), which would remove the per-map model limit
  indoors ([world streamer](../WORLD_STREAMER.md)). Planned.
- **Run-time scale and tilt** (one model per mesh instead of a variant per
  scale and tilt): most model bytes island-wide, but hulls stay per variant.
  Designed as an open decision; measure with the engine first.
- **Terrain as a heightfield generated at load** instead of stored faces,
  once its 68040 cost is measured. Planned.
- **Quake's `vis` on the stitched frame world**, with occluder brushes, if
  sampled visibility rows show popping. Designed as an open decision.
- **Animated textures shared between models**, today drawn as their first
  frame ([CHIM-ANIM-TEXTURES-33](../bugs/CHIM-ANIM-TEXTURES-33.md)). Open.
- **Hollow house shells** let the chunk visibility rows see through
  buildings ([CHIM-PVS-HOLLOW-33](../bugs/CHIM-PVS-HOLLOW-33.md)). Open.
- **A RAM-expansion settings screen** and **player-versus-player** in the
  Arena: ideas, not started.

## Measured and dropped

The short list, so nobody redoes them:

| Idea | Why it was dropped |
| --- | --- |
| Sharing texture mappings across models | Saves under 1 % of the ring's bytes in Balmora and Seyda Neen; see [Memory](#memory) |
| Rounding texture mappings | Changes the pixels; saves little |
| Cutting large models by chunk for the Telvanni towns | At 1,024 units no change; at 512 units five of six frames grew by up to 411 KB, Sadrith Mora gained 48 KB (16 October 2026); the pieces carry their own collision and records |
| Merging near-identical tilted variants in the builder | 0.6 % exact, 2.1 % snapped to 2 degrees, and snapping moves objects; see full rotation in [Memory](#memory) |
| The mesh optimizer on every mesh | Made Hla Oad's frames 1.5 MB larger (merged flora polygons become triangles); per-mesh recipes instead ([CHIMport](CHIMPORT.md#when-a-cell-does-not-fit-the-memory-budget)) |
| NPC parts as follower entities | About 19 entity setups per actor per frame; see [Modular NPCs](#modular-npcs) |
| A legacy and CHIM hybrid build | Dismissed: builds are pure CHIM; the legacy builder stays selectable on its own |
| Town occluders and hints on legacy region maps | Negligible benefit with the current partitioning; town occlusion deferred pending a better approach ([TOWN-VIS-OCCLUSION-31](../bugs/TOWN-VIS-OCCLUSION-31.md)) |
| Appending building faces to the world model | At most 5 % less face work, and it breaks the face-list limits ([town visibility](../performance/TOWN-VISIBILITY.md)) |
| A compiled terrain standing hull for regular ground | It broke a Balmora stair walk; the compiled hull is used for irregular ground only ([CHIM-SEYDA-MEMORY-33](../bugs/CHIM-SEYDA-MEMORY-33.md)) |
| Smaller frame-world slots (256 KiB) | Outgrown, unstable across reruns ([CHIM engine](ENGINE.md#not-yet-done)) |
