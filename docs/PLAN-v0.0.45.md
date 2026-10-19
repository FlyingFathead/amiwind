# v0.0.45 working plan: crossings, then every interior

_Last updated with AmiWind v0.0.45 (19 October 2026)._

The step-by-step checklist behind the [roadmap's road after v0.0.44](ROADMAP.md#the-road-after-v0044-19-october-2026).
Written 19 October 2026 from the maintainer's decisions of that day. A step is ticked only with its evidence (a
commit, a gate, a build run, a measurement or a clip); a step that turns out wrong is struck through with the reason,
never deleted. Every speed change is an A/B/C run with the profiler and kept only when it wins; every builder change
comes with a test and a gate; every failure found becomes a bug page.

## 1. Cell crossings

[CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md): crossing between CHIM cells pauses the game, worst at
corners, even with 128 MB of RAM. The design, the measurements and the order of work: [Cell crossings](chim/CELL_CROSSINGS.md).

Two selectable methods (maintainer, 19 October 2026): type 0 "AmiQuake", today's level change, stays as an option,
and type 1 "CHIM", one continuous world that streams the next frame in place, becomes the default once it measures
better. Nothing is deleted: Quake's networking and multiplayer code stay in the codebase. The outdoor switch carries
no multiplayer requirement (the Vivec Arena duel idea concerns the indoor Arena, an ordinary level); real doors,
travel and interiors stay level changes in both methods.

Every step below is an A/B on the same route, image, memory size and cache state, at 16 and 128 MB, with a repeated
A run as drift control, and is kept only when it wins.

### 1a. What v0.0.45 ships

- [ ] 1.1 A fixed route with edge and corner crossings, scripted; crossing time per section at 16 MB and at 128 MB:
  the A of every comparison. First baseline 19 October 2026 on the v0.0.44 image (busy host, 128 MB): light edge
  about 320 ms, light corner about 360 ms, Balmora edge about 680 ms, Balmora corner about 880 ms; about 220 to 260 ms
  of each is the level change itself, the same at 16 and 128 MB. A quiet-host rerun with the v0.0.45 image follows
  the release build.
- [ ] 1.2 The prefetch into spare RAM (branch `v0.0.43-prefetch`, measured about 450 ms down to about 230 ms per
  crossing at 128 MB): merged 19 October 2026 (1557f6c) and in the v0.0.45 build; ticked after the route measurement
  with the v0.0.45 image.
- [ ] 1.3 RAM past 16 MB as a frame cache and a heap that grows with RAM
  ([ENGINE-HEAP-FIXED-SIZE-43](bugs/ENGINE-HEAP-FIXED-SIZE-43.md)): merged with 1.2; ticked with the same measurement.
- [ ] 1.4 Loading spread over many rendered frames before the border, no blocking read at the crossing. The v0.0.45
  prefetch reads a slice per rendered frame; what still blocks at the crossing is the level change (1.6 onwards).
- [ ] 1.5 Corners: all three other frames queued, the one ahead first; hysteresis so a border is never loaded twice.
  In the v0.0.45 prefetch (the 2x2 block at the nearest corner, the frame ahead first, a margin past the midline);
  checked on the route with 1.2.

### 1b. The level change, part by part (type 0, v0.0.46)

- [ ] 1.6 The level change split into its parts on the route: the reconnection handshake (each step), clearing the
  old level, loading the game scripts, reading the frame map, starting the CHIM world, the renderer's new-map work and
  priming the chunk ring. A small buffered timeline with the host frame number of each event (server shut down and
  started, client model and sound lists, each reconnection reply queued and processed, the first real presentation of
  the new world) separates work from waiting between host frames: elapsed time is not all processor time. The end
  point is a frame of the new world actually shown, timed before any audit or logging work (today
  `aw_stream.c` `AW_StreamPresented` runs a heap audit before it takes the time).
- [ ] 1.6b The worst rendered frame over the whole approach and crossing, and the longest piece of loading work that
  cannot be interrupted today (one model decoded, one terrain chunk grafted: the budgets allow one unit over). A
  change that only moves the pause a few metres before the border does not count as a win; a piece longer than the
  allowance starts earlier, is prepared apart or becomes resumable.
- [ ] 1.7 The quick wins, one at a time, each kept only when it wins and the Arena, doors and saves still work:
  - [ ] A. the reconnection replies that are already waiting processed during loading, a bounded number, instead of
    one per host frame (same handlers and message order, no physics steps added to move them along, and client
    time, entity relinking and effects advanced once per host frame: the whole client read step advances them, so
    only the waiting replies are exchanged); kept only if 1.6 shows real waiting;
  - [ ] B. the game scripts kept loaded when unchanged;
  - [ ] C. the decoded world index kept with 16 MB too, if the memory gate allows it;
  - [ ] D. the frame's entity text read once, not twice more, when sky and lighting settings are the same;
  - [ ] E. no double stop of all sounds and no loading screen draw for a crossing;
  - [ ] F. the chunks of the neighbouring frame that are still in reach kept.

### 1c. Type 1 "CHIM": one continuous world

- [ ] 1.8 The method switch: type 0 and type 1 selectable; type 0 stays the default until type 1 wins on the route.
  A setting of its own (or an explicit migration): today's saved `aw_cell_change_method` 1 means the current method
  and 2 the read-ahead experiment, so a saved 1 must never turn into type 1.
- [ ] 1.9 A sandbox of four light frames around one corner, at a fixed origin: the four frames' chunks in one
  composite world (one owner per physical chunk, so shared terrain margins are never loaded twice); the game logic,
  display, player and clock kept running; a model and sound set that fits today's lists. The player's logical cell is
  kept apart from the running session and the coordinate origin; after a seamless crossing the terrain, the doors and
  harvesting all work, checked in each of the four frames. Coordinate conversion uses the current origin; doors and
  nearby objects keep the area they belong to; the remembered harvest region carries its area too (two catalogues
  can use the same index). The check: cross the seam, pick a plant, use a door in the incoming area, come back
  outside and read the world-map position.
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
- [ ] 1.14 The whole island on type 1, type 0 kept as an option; crossings between towns and the open world may stay
  type 0 at first (town frames are not cell-aligned).

## 2. Bugs from the v0.0.43 playtests

- [ ] 2.1 [CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md): an island-wide open-edge sweep of rock meshes
  against their source, OpenMW A/B, face winding and rotation checked. 19 October: sweep, winding and rotation done
  (`tools/rock_shell_audit.py`, no converter cause); the in-game orbit and the OpenMW A/B at reference 476548 remain.
- [ ] 2.2 [CHIM-VIVEC-DOCK-WALKWAY-43](bugs/CHIM-VIVEC-DOCK-WALKWAY-43.md): the fix on its branch, verified in a few-frame
  build.
- [ ] 2.3 The other open playtest bugs: Daedric ruin pillars, the muckspunge seam, blocky roads, the Seyda Neen to
  Balmora load hang, the Ebonheart dragon pedestal.
- [ ] 2.4 Builder: [BUILD-CHIM-SERIAL-SECTIONS-44](bugs/BUILD-CHIM-SERIAL-SECTIONS-44.md) and
  [BUILD-IMAGE-STAIR-WALK-CORES-43](bugs/BUILD-IMAGE-STAIR-WALK-CORES-43.md): every pool follows the live allowance.

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
  [AW-20260928-10](bugs/AW-20260928-10.md)) and its plants as sprites, so a new room costs its placement list.
- [ ] 3.2 The interior progress tracker: one row per interior (name, town or region, its outdoor doors, state, size,
  last build), fed after every build like the cell tracker, shown in the Toolkit and as counts in the docs.
- [ ] 3.3 The entrance audit, island-wide: every load door checked against the build; a door to a room left out on
  purpose names the reason.
- [ ] 3.4 The room list made from the game's door graph instead of hand lists (today: Balmora, Seyda Neen, Vivec).
- [ ] 3.5 The 11 doors with no prompt (near Seyda Neen, three Pelagiad houses, Wolverine Hall): cause found and fixed.
- [ ] 3.6 Vivec's left-out rooms through the [over-limit procedure](INTERIOR_SECTIONS.md): the four Waistworks and Plaza
  hubs and the Prison Keep first (28 rooms reachable again), then the rest.
- [ ] 3.7 Conversion batches, towns first (Ald-ruhn 56, Sadrith Mora 31, Caldera 20, Gnisis 20, ...), then the
  wilderness; each batch measured for build time, image size and memory.
- [ ] 3.8 Solstheim and Mournhold, planned once Vvardenfell's rooms are in.
  Mournhold (maintainer, 19 October 2026): its five open districts are interior cells flagged to behave like exteriors
  (Godsreach, Great Bazaar, Plaza Brindisi Dorom, Royal Palace: Courtyard, Temple Courtyard; cell flags 0x87,
  region "Mournhold Region"), so they need the region's sky, weather and fog, read from the game data as outdoors
  ([SKY-REDMOUNTAIN-BLUE-44](bugs/SKY-REDMOUNTAIN-BLUE-44.md) is the same missing piece). Each is one huge cell, a
  whole district, so each is planned as the Vivec Arena Pit was: the over-limit procedure from the start (sprites,
  per-mesh recipes, sections cut at gates and archways, recentring), measured against the memory and frame budget.

## 4. After the interiors

The [roadmap](ROADMAP.md#the-road-after-v0044-19-october-2026) order: object and container state, NPC placement,
then MWScript compiled by the builder. Each gets its own checklist when it starts.
