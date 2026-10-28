# v0.0.45 working plan: crossings, then every interior

_Last updated with AmiWind v0.0.45 (20 October 2026)._

<!-- contents start -->
## Contents

- [1. Cell crossings](#1-cell-crossings)
- [2. Bugs from the v0.0.43 playtests](#2-bugs-from-the-v0043-playtests)
- [3. Every interior of the base game](#3-every-interior-of-the-base-game)
- [4. After the interiors](#4-after-the-interiors)

<!-- contents end -->

The step-by-step checklist behind the [roadmap's road after v0.0.44](../../ROADMAP.md#the-road-after-v0044-19-october-2026).
Written 19 October 2026 from the maintainer's decisions of that day. A step is ticked only with its evidence (a
commit, a gate, a build run, a measurement or a clip); a step that turns out wrong is struck through with the reason,
never deleted. Every speed change is an A/B/C run with the profiler and kept only when it wins; every builder change
comes with a test and a gate; every failure found becomes a bug page.

## 1. Cell crossings

[CHIM-CROSSING-SLUGGISH-43](../../bugs/CHIM-CROSSING-SLUGGISH-43.md): crossing between CHIM cells pauses the game, worst at
corners, even with 128 MB of RAM. The design, the measurements and the order of work: [Cell crossings](../../chim/CELL_CROSSINGS.md).

Two selectable methods (maintainer, 19 October 2026): type 0 "AmiQuake", today's level change, stays as an option,
and type 1 "CHIM", one continuous world that streams the next frame in place, becomes the default once it measures
better. Nothing is deleted: Quake's networking and multiplayer code stay in the codebase. The outdoor switch carries
no multiplayer requirement (the Vivec Arena duel idea concerns the indoor Arena, an ordinary level); real doors,
travel and interiors stay level changes in both methods.

Every step below is an A/B on the same route, image, memory size and cache state, at 16 and 128 MB, with a repeated
A run as drift control, and is kept only when it wins.

### 1a. What v0.0.45 ships

- [x] 1.1 A fixed route with edge and corner crossings, scripted; crossing time per section at 16 MB and at 128 MB:
  the A of every comparison. The route is `tools/crossing_route.py` (edges, diagonal corners and corner loops in a
  light area and at the Balmora frame; one boot per image and memory size, each leg three times; method and
  limits: [Crossing baseline](../../performance/CROSSING_BASELINE.md)). Quiet-host baseline 20 October 2026 on the
  v0.0.44 image, median ready time: 128 MB light edge 293 ms, light corner 367, Balmora edge 650, Balmora corner
  822; 16 MB 448, 537, 665, 879 (table and causes:
  [Cell crossings](../../chim/CELL_CROSSINGS.md#what-a-crossing-costs-today)). The route flies above the fogged ground, so
  its approach frames are light; a walking route on the ground is still to come.

Order (maintainer, 19 October 2026): measure the level change part by part first (1.6); of the type 0 quick wins
only A, and only if the measurement shows a large share, at most one evening; then straight to the type 1 sandbox
(1.9). Type 1, the outdoors as one running world, is the target; type 0 stays selectable.
- [x] 1.2 The prefetch into spare RAM (branch `v0.0.43-prefetch`, measured about 450 ms down to about 230 ms per
  crossing at 128 MB): merged 19 October 2026 (1557f6c) and in the v0.0.45 build. On the route, 20 October 2026,
  v0.0.45 against v0.0.44 at 128 MB: light edge 293 to 123 ms, light corner 367 to 123, Balmora edge 650 to 201,
  Balmora corner 822 to 223 (about a third, more than the "roughly halves" of the v0.0.45 notes); the longest
  frame of a light crossing about 200 to 260 ms down to about 65. At 16 MB 1 to 7 % faster.
- [x] 1.3 RAM past 16 MB as a frame cache and a heap that grows with RAM
  ([ENGINE-HEAP-FIXED-SIZE-43](../../bugs/ENGINE-HEAP-FIXED-SIZE-43.md)): merged with 1.2; on the same measurement the heap
  is 24 MiB with 128 MB (11 MiB on v0.0.44 and with 16 MB), the CHIM cache 82 MiB.
- [ ] 1.4 Loading spread over many rendered frames before the border, no blocking read at the crossing. The v0.0.45
  prefetch reads a slice per rendered frame; what still blocks at the crossing is the level change (1.6 onwards).
- [ ] 1.5 Corners: all three other frames queued, the one ahead first; hysteresis so a border is never loaded twice.
  In the v0.0.45 prefetch (the 2x2 block at the nearest corner, the frame ahead first, a margin past the midline);
  checked on the route with 1.2.

### 1b. The level change, part by part (type 0, v0.0.46)

- [x] 1.6 The level change split into its parts on the route: the reconnection handshake (each step), clearing the
  old level, loading the game scripts, reading the frame map, starting the CHIM world, the renderer's new-map work and
  priming the chunk ring. A small buffered timeline with the host frame number of each event (server shut down and
  started, client model and sound lists, each reconnection reply queued and processed, the first real presentation of
  the new world) separates work from waiting between host frames: elapsed time is not all processor time. The end
  point is a frame of the new world actually shown, timed before any audit or logging work (today
  `aw_stream.c` `AW_StreamPresented` runs a heap audit before it takes the time).
  Done 20 October 2026 with a timing build of the v0.0.45 engine on the v0.0.45 image (table:
  [The level change, part by part](../../chim/CELL_CROSSINGS.md#the-level-change-part-by-part)). Four host frames from the
  border to the first frame shown: 155 ms (light edge) and 305 ms (Balmora corner) with 128 MB, 540 and 906 ms with
  16 MB. The largest parts: with 128 MB the chunk ring (38 to 54 ms), the CHIM start of the frame (21 to 28) and the
  heap audit lines (17 to 21), in a town the entity spawn (96); with 16 MB the CHIM start of the frame (199 to 335,
  the world index decoded again) and the chunk ring (95 to 231), in a town also the entity spawn (231) and the client
  model list (92). Waiting between host frames is about 17 ms at the best and 1 to 4 ms otherwise.
- [ ] 1.6b The worst rendered frame over the whole approach and crossing, and the longest piece of loading work that
  cannot be interrupted today (one model decoded, one terrain chunk grafted: the budgets allow one unit over). A
  change that only moves the pause a few metres before the border does not count as a win; a piece longer than the
  allowance starts earlier, is prepared apart or becomes resumable.
- [ ] 1.7 The quick wins, one at a time, each kept only when it wins and the Arena, doors and saves still work:
  - [ ] A. the reconnection replies that are already waiting processed during loading, a bounded number, instead of
    one per host frame (same handlers and message order, no physics steps added to move them along, and client
    time, entity relinking and effects advanced once per host frame: the whole client read step advances them, so
    only the waiting replies are exchanged); kept only if 1.6 shows real waiting. Not started: 1.6 measured about
    17 ms of waiting at the best (one frame of the 72 Hz cap), 1 to 4 ms otherwise, not worth an evening ahead of
    the items below;
  - [ ] A2. no heap audit lines during a crossing (one summary line, or development builds only): 17 to 21 ms at every
    memory size (measured 20 October 2026);
  - [ ] A3. the 11 to 12 ms spent in the console command buffer in the handshake's second frame, found and removed
    if it is not needed there;
  - [ ] B. the game scripts kept loaded when unchanged;
  - [ ] C. the decoded world index kept with 16 MB too, if the memory gate allows it (the largest part with 16 MB:
    the CHIM start of the frame, 199 to 335 ms, measured 20 October 2026);
  - [ ] D. the frame's entity text read once, not twice more, when sky and lighting settings are the same;
  - [ ] E. no double stop of all sounds and no loading screen draw for a crossing;
  - [ ] F. the chunks of the neighbouring frame that are still in reach kept.

### 1c. Type 1 "CHIM": one continuous world

- [x] 1.8 The method switch: type 0 and type 1 selectable; type 0 stays the default until type 1 wins on the route.
  A setting of its own (or an explicit migration): today's saved `aw_cell_change_method` 1 means the current method
  and 2 the read-ahead experiment, so a saved 1 must never turn into type 1.
  Done 20 October 2026 (branch `v0.0.46-stream-type1`, 951c1e83): `chim crossing 0|1`, a `chim` subcommand that
  is never saved; 0, the default, is type 0 unchanged.
- [ ] 1.9 Near and far together in the sandbox ([one system](../../chim/CELL_CROSSINGS.md#near-and-far-as-one-system-upcoming-direction)):
  streamed detail near, the far shell beyond, one handover distance tied to the fog, the shell split along the
  streamed chunks, one priority queue and one memory budget; a chunk held back on purpose shows its silhouette.
  A sandbox of four light frames around one corner, at a fixed origin: the four frames' chunks in one
  composite world (one owner per physical chunk, so shared terrain margins are never loaded twice); the game logic,
  display, player and clock kept running; a model and sound set that fits today's lists. The player's logical cell is
  kept apart from the running session and the coordinate origin; after a seamless crossing the terrain, the doors and
  harvesting all work, checked in each of the four frames. Coordinate conversion uses the current origin; doors and
  nearby objects keep the area they belong to; the remembered harvest region carries its area too (two catalogues
  can use the same index). The check: cross the seam, pick a plant, use a door in the incoming area, come back
  outside and read the world-map position.
  20 October 2026, first part: the window of four region frames at a fixed origin, one owner per physical chunk,
  each object drawn once, the session, player and clock running through the crossing (branch
  `v0.0.46-stream-type1`; engine tests on a six-frame test world). Measured on the release image's four cells
  2,-7 / 3,-7 / 2,-6 / 3,-6 instead of a MiniWind build: the builder refuses `--chim-regions` in a MiniWind and a
  MiniWind leaves out the terrain-region stage the region directory comes from, so a region sandbox needs its own
  MiniWind scope first. Not yet: the doors and plants of a frame entered by streaming, and the far shell.
- [ ] 1.10 Repeated loading and unloading in the sandbox with a person, an object across a seam and changed object
  state: memory and list use stay within a bounded range (entity data reclaimed without a level reset).
- [ ] 1.11 Late data: bytes read, data decoded, and collision and objects installed and safe are three different
  states; being in RAM is not ready to walk on. Collision the player still needs is kept while the incoming side is
  prepared; if needed collision is missing, a defined short stall, counted and timed, never walking through absent
  ground. Tested with delayed reads, little memory, a diagonal corner crossing and an immediate turn back. At a corner
  one bounded active neighbourhood, not four whole frames of geometry and people.
- [ ] 1.12 A rebase forced in the sandbox: collision, camera, effects, saving and loading all hold.
- [ ] 1.13 Edges and the corner measured for the longest single rendered frame and the memory peak, beside the median
  crossing, at 16 and 128 MB; the same standing views and walking route in both methods with frame time, active
  actors and drawn geometry, so a smooth crossing is not bought with neighbours that keep thinking and drawing.
  20 October 2026, the light legs (ai-c1, ai-l1, ai-e1; [table](../../chim/CELL_CROSSINGS.md#the-type-1-prototype-measured-20-october-2026)):
  worst frame after a crossing 83 to 42 ms at 128 MB, 373 to 66 ms at 16 MB; the approach's worst frame the same at
  128 MB and 66 to 80 ms at 16 MB; zone locked peak +7 % at 16 MB; standing views 0.00 and 0.16 % of pixels apart.
  Corrected 20 October 2026: not a like-for-like comparison, because type 1 creates no entities in the frames it joins
  and type 0 does; these figures do not show the speed of a complete crossing. To be repeated with both methods doing
  the same work on frames with people. Towns, actors and drawn geometry still to measure.
- [ ] 1.14 The whole island on type 1, type 0 kept as an option; crossings between towns and the open world may stay
  type 0 at first (town frames are not cell-aligned).

## 2. Bugs from the v0.0.43 playtests

- [ ] 2.1 [CHIM-ROCKS-OPEN-SHELLS-43](../../bugs/CHIM-ROCKS-OPEN-SHELLS-43.md): an island-wide open-edge sweep of rock meshes
  against their source, OpenMW A/B, face winding and rotation checked. 19 October: sweep, winding and rotation done
  (`tools/rock_shell_audit.py`, no converter cause); the in-game orbit and the OpenMW A/B at reference 476548 remain.
- [ ] 2.2 [CHIM-VIVEC-DOCK-WALKWAY-43](../../bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md): the fix on its branch, verified in a few-frame
  build.
- [ ] 2.3 The other open playtest bugs: Daedric ruin pillars, the muckspunge seam, blocky roads, the Seyda Neen to
  Balmora load hang, the Ebonheart dragon pedestal.
- [ ] 2.4 Builder: [BUILD-CHIM-SERIAL-SECTIONS-44](../../bugs/BUILD-CHIM-SERIAL-SECTIONS-44.md) and
  [BUILD-IMAGE-STAIR-WALK-CORES-43](../../bugs/BUILD-IMAGE-STAIR-WALK-CORES-43.md): every pool follows the live allowance.

## 3. Every interior of the base game

Measured 19 October 2026 on the v0.0.43-dev3 build. The base game (Morrowind, Tribunal and Bloodmoon) has 1,328
interior cells: 1,134 on Vvardenfell (8 of them developer test cells), 98 on Solstheim and 96 in Mournhold. On
Vvardenfell, 176 rooms are converted and reachable (Balmora 42, Seyda Neen 14, two tombs, Vivec 118), 23 are converted
but cut off behind left-out hub rooms, 8 are left out (Vivec, over the model limits) and 919 are not converted yet,
about 420 of them caves, tombs, ruins and shipwrecks in the wilderness. Of the doors from outdoors, 746 show
"Interior unavailable" and 11 show no prompt at all.

- [ ] 3.1 Interiors on CHIM, then convert (decided for the project, 19 October 2026): rooms average about 2 MB, so about 950 more rooms would add about 2 GB to an
  image of 3.62 GB against the 4 GiB limit. Rooms store each mesh and texture once and reference them, as CHIM does
  outdoors, or get a per-room size budget, before the big batches.
  Everything already converted is reused, never made again: a mesh or texture the outdoors or another room already
  has in the store is placed by reference, by its SHA-256, and only the pieces no room or cell has yet are converted.
- [ ] 3.1b Interiors modular (maintainer, 19 October 2026): Morrowind builds its rooms from shared kits (Hlaalu,
  Redoran, Telvanni, Imperial, Dwemer, caves, tombs); each kit piece is converted once and every room places it
  by reference, with its doors as working entities (rotate or slide with their sounds, from the DOOR records;
  [AW-20260928-10](../../bugs/AW-20260928-10.md)) and its plants as sprites, so a new room costs its placement list.
- [ ] 3.2 The interior progress tracker: one row per interior (name, town or region, its outdoor doors, state, size,
  last build), fed after every build like the cell tracker, shown in the Toolkit and as counts in the docs.
- [ ] 3.3 The entrance audit, island-wide: every load door checked against the build; a door to a room left out on
  purpose names the reason.
- [ ] 3.4 The room list made from the game's door graph instead of hand lists (today: Balmora, Seyda Neen, Vivec).
- [ ] 3.5 The 11 doors with no prompt (near Seyda Neen, three Pelagiad houses, Wolverine Hall): cause found and fixed.
- [ ] 3.6 Vivec's left-out rooms through the [over-limit procedure](../../INTERIOR_SECTIONS.md): the four Waistworks and Plaza
  hubs and the Prison Keep first (28 rooms reachable again), then the rest.
- [ ] 3.7 Conversion batches, towns first (Ald-ruhn 56, Sadrith Mora 31, Caldera 20, Gnisis 20, ...), then the
  wilderness; each batch measured for build time, image size and memory.
- [ ] 3.8 Solstheim and Mournhold, planned once Vvardenfell's rooms are in.
  Mournhold (maintainer, 19 October 2026): its five open districts are interior cells flagged to behave like exteriors
  (Godsreach, Great Bazaar, Plaza Brindisi Dorom, Royal Palace: Courtyard, Temple Courtyard; cell flags 0x87,
  region "Mournhold Region"), so they need the region's sky, weather and fog, read from the game data as outdoors
  ([SKY-REDMOUNTAIN-BLUE-44](../../bugs/SKY-REDMOUNTAIN-BLUE-44.md) is the same missing piece). Each is one huge cell, a
  whole district, so each is planned as the Vivec Arena Pit was: the over-limit procedure from the start (sprites,
  per-mesh recipes, sections cut at gates and archways, recentring), measured against the memory and frame budget.

## 4. After the interiors

The [roadmap](../../ROADMAP.md#the-road-after-v0044-19-october-2026) order: object and container state, NPC placement,
then MWScript compiled by the builder. Each gets its own checklist when it starts.
