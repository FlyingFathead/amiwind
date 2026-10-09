# CHIM ideas and held-back work

Every idea around [CHIM](README.md) that is not simply "done": what is
planned, what is designed, what has a prototype, and what was measured and
then dropped. Each item links to the document or bug that holds the detail.
The status is honest and nothing here is a promise. Items that were measured
and dropped stay on this page with the reason, so nobody spends a night
measuring them again.

<!-- contents start -->
## Contents

- [Modular NPCs](#modular-npcs)
- [NPC pathfinding](#npc-pathfinding)
- [The distant view: far terrain and mold shells](#the-distant-view-far-terrain-and-mold-shells)
- [M3: Vivec on CHIM](#m3-vivec-on-chim)
- [M4: the open world](#m4-the-open-world)
  - [The frame grid](#the-frame-grid)
  - [The memory estimator](#the-memory-estimator)
  - [The density planner, and why frame cuts do not lower the peak](#the-density-planner-and-why-frame-cuts-do-not-lower-the-peak)
- [Memory](#memory)
- [Build speed](#build-speed)
- [Texture effects: a bug turned into an effect](#texture-effects-a-bug-turned-into-an-effect)
- [The slow-accelerator reality](#the-slow-accelerator-reality)
- [Island-wide audits (mechanism classes)](#island-wide-audits-mechanism-classes)
- [Also held back](#also-held-back)
- [Measured and dropped](#measured-and-dropped)

<!-- contents end -->

| Status | Meaning |
| --- | --- |
| planned | decided or requested; no design yet |
| designed | written down with its data layout, budgets and gates; no code |
| prototyped | code exists (a debug command, a tool or a branch), not yet a finished feature |
| in source | implemented and gated on a development branch, not yet in a release |
| measured and dropped | tried or counted; not worth it, for the reason given |

All figures come from the owner's own game data and builder output, as
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

## The distant view: far terrain and mold shells

**Status: release blocker for v0.0.33; designed, a first layer is being
prototyped.** Tracked as [CHIM-FAR-TERRAIN-33](../bugs/CHIM-FAR-TERRAIN-33.md).

CHIM draws full-detail chunks inside the ring only, so beyond the view
distance there is only fog and sky: valleys look empty and Vivec cannot be
seen from the world. The legacy region maps drew these views much better.

- **Reference look.** v0.0.32's horizon, the HORSTATOR APPROVED method
  (`aw_skyline_fill 0`), and its sky veil. Every CHIM change to the distant
  view is A/B-checked against v0.0.32 at the same poses (the owner's poses and
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
- **Vis.** Canton bodies and the Temple are the first big closed masses CHIM
  meets: real occluders that hide whole streets. Visibility rows and
  placements per view are measured, and the counters may not get worse than
  the legacy preview.

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
- **The 2 MiB Hunk-gap rule. Status: kept (owner decision).** The engine's
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
- **Other open memory items:** the zone size itself (a 7,680 KiB interim
  zone vs a bank size the builder writes per world, owner decision pending,
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
| Longest work first | in source on a branch | Worker pools hand out the largest items first from measured cost history, so no stage ends on one core while the rest wait ([parallel build](../PARALLEL_BUILD.md)). |

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
| NPC parts as follower entities | About 19 entity setups per actor per frame; see [Modular NPCs](#modular-npcs) |
| A legacy and CHIM hybrid build | Dismissed: builds are pure CHIM; the legacy builder stays selectable on its own |
| Town occluders and hints on legacy region maps | Negligible benefit with the current partitioning; town occlusion deferred pending a better approach ([TOWN-VIS-OCCLUSION-31](../bugs/TOWN-VIS-OCCLUSION-31.md)) |
| Appending building faces to the world model | At most 5 % less face work, and it breaks the face-list limits ([town visibility](../performance/TOWN-VISIBILITY.md)) |
| A compiled terrain standing hull for regular ground | It broke a Balmora stair walk; the compiled hull is used for irregular ground only ([CHIM-SEYDA-MEMORY-33](../bugs/CHIM-SEYDA-MEMORY-33.md)) |
| Smaller frame-world slots (256 KiB) | Outgrown, unstable across reruns ([CHIM engine](ENGINE.md#not-yet-done)) |
