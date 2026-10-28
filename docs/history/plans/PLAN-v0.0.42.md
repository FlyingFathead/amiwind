# v0.0.42 working plan: Things Are Starting To Look Pretty Khuul

_Last updated with AmiWind v0.0.42 (17 October 2026)._

<!-- contents start -->
## Contents

- [1. Tools first](#1-tools-first)
  - [1.0 Reuse keys that cover exactly their inputs](#10-reuse-keys-that-cover-exactly-their-inputs)
  - [1.0b The stair gate: walk each flight once, keep every pass, ship the known results](#10b-the-stair-gate-walk-each-flight-once-keep-every-pass-ship-the-known-results)
  - [1.0c Nothing quietly disappears from the world](#10c-nothing-quietly-disappears-from-the-world)
  - [1.1 The builder explains a memory overrun](#11-the-builder-explains-a-memory-overrun)
  - [1.2 `dbg cam orbit`, the inspection camera (planned)](#12-dbg-cam-orbit-the-inspection-camera-planned)
  - [1.2b `dbg cam flyingcam`, the island fly-over (planned)](#12b-dbg-cam-flyingcam-the-island-fly-over-planned)
  - [1.2c `dbg cam pancam`, `dbg cam steadicam` and `dbg cam cranecam`, shots on request (planned)](#12c-dbg-cam-pancam-dbg-cam-steadicam-and-dbg-cam-cranecam-shots-on-request-planned)
  - [1.3 The remaining cells, by weight](#13-the-remaining-cells-by-weight)
  - [1.3b Every cached result says when and with what it was made](#13b-every-cached-result-says-when-and-with-what-it-was-made)
  - [1.4 Reuse the building blocks and simplify collision (maintainer, 16 October 2026)](#14-reuse-the-building-blocks-and-simplify-collision-maintainer-16-october-2026)
- [2. Complete Vivec (the city)](#2-complete-vivec-the-city)
  - [2.1 Interiors (14 of 144 rooms left out on 16 October)](#21-interiors-14-of-144-rooms-left-out-on-16-october)
  - [2.2 Vivec himself](#22-vivec-himself)
  - [2.3 The city frame and the visible defects](#23-the-city-frame-and-the-visible-defects)
  - [2.4 The Vivec bug review](#24-the-vivec-bug-review)
- [3. CHIMport by weight](#3-chimport-by-weight)
  - [3.1 Before the batches](#31-before-the-batches)
  - [3.2 The easy batch](#32-the-easy-batch)
  - [3.3 The heavier cells, lightest first, each group measured again first](#33-the-heavier-cells-lightest-first-each-group-measured-again-first)
- [4. Effects (with the regions they belong to)](#4-effects-with-the-regions-they-belong-to)
- [5. Release](#5-release)

<!-- contents end -->

The step-by-step checklist behind the [roadmap's v0.0.42 items](../../ROADMAP.md#v0042-complete-vivec-the-city-16-october-2026).
Written 16 October 2026 from the maintainer's decisions of that day. A step is ticked only with its evidence (a commit,
a gate, a build run, a measurement or a clip); a step that turns out wrong is struck through with the reason,
never deleted. Every measurement is taken with the current builder; every builder change comes with a test and a
gate; every failure found becomes a bug page.

Order: tools first (they make the rest faster), then Vivec, then the CHIMport batches by weight.
Project decision, 17 October 2026: once the builder fixes are in, v0.0.42-dev1 is pushed and the easy CHIMport
batch (3.2) follows straight after it; the batch is prepared while the builder work finishes. Vivec work runs
alongside.

## 1. Tools first

Maintainer, 16 October 2026: release v0.0.41 first, then build things better, starting with the builder itself.

### 1.0 Reuse keys that cover exactly their inputs

- [ ] Each stage's key covers exactly the code and data it uses ([BUILD-REUSE-KEYS-TOO-BROAD-35](../../bugs/BUILD-REUSE-KEYS-TOO-BROAD-35.md)):
  a change to a shared module reruns only the stages that use the changed code (16 October: a collision change in
  `mesh_geometry.py` reran the Balmora interiors stage).
- [ ] Early stages use the cores they are given (BUILD-IDLE-STAGES-33).
- [ ] The CHIM stage's final checks over every frame run on one worker pool kept for the whole step, largest
  frame first, so no batch waits on its slowest frame and no workers are started per batch (16 October, dev5:
  20-24 of 24 cores, dropping to 4-8 every 1-3 minutes; hundreds of workers living about 0.2 s, about 15 % of the
  CPU spent on process overhead). Measured over the 46 minutes of the stage with progress samples: world
  conversion 17.7 cores on average (under 12 cores a fifth of the time), validation 10.3 (on 1 core more than half
  of its 6 minutes: the whole-world cross-checks), the heap gate 2.9, the zone walk dropping to 1 core between
  frames; about 340 core-minutes left idle. Each of these single-core stretches is split into units and run on
  the pool.
- [ ] The same checks print one progress line per frame (frame, area, count done of total): dev5's step printed
  nothing for over 24 minutes.
- [ ] The build's ETA scales with the work, not only with past wall time: each stage's estimate from its unit
  counts (frames, cells, models, maps) and the per-unit cost history (`build_costs.py`), corrected while it runs
  from units done of total. 16 October, dev5: the CHIM stage was estimated at 43 minutes from earlier builds and
  took over 85 (726 frames against 604, two whole regions added); the ETA said 23 minutes left at 12:40 and still
  25 minutes at 13:07.

### 1.0b The stair gate: walk each flight once, keep every pass, ship the known results

The stair walk is one of the slowest gates (8 min 52 s, 2.67 million steps and ramps in v0.0.41-dev5) and the one
that stopped dev5 after 1 h 35 min. Maintainer, 16 October 2026: "so that we don't have this stairway march for aeons".

- [x] Each flight walked once, in the frame that owns it, plus the margin the engine lets a player stand in before
  it switches map; border copies reuse that result ([BUILD-STAIR-WALK-BORDER-COPIES-41](../../bugs/BUILD-STAIR-WALK-BORDER-COPIES-41.md)).
  Measured: walked steps against distinct steps, before and after, same failures found.
  Evidence: branch v0.0.42-stairs ccdc07f and the option-history commit after it, gate 2601. v0.0.41 world: 2,672,454 steps and ramps (3.07 per place) ->
  853,398 (1.11 per place). Vos-edge world: the copy failure gone (13.6 s -> 8.0 s); with Vos on CHIM the failure is
  found once, in Vos's own frame, same rows (15.6 s -> 9.0 s). An area walk is derived from an unchanged whole-frame
  walk without walking. Found on the way: [STAIR-FLIGHT-CORE-SPLIT-41](../../bugs/STAIR-FLIGHT-CORE-SPLIT-41.md),
  [STAIR-DETECT-POSITION-41](../../bugs/STAIR-DETECT-POSITION-41.md).
- [x] A pass is a pass: a frame or flight walk that passed is kept with its SHA-256 key and provenance (timestamp,
  AmiWind and CHIM versions, commit, run) and reused while the key is unchanged, whatever else the build did; the
  key covers the walker and the stair rule, not the compilers that made the collision (their output is in the key
  already) ([BUILD-STAIR-PASS-NOT-KEPT-41](../../bugs/BUILD-STAIR-PASS-NOT-KEPT-41.md)).
  Evidence: 2c0ca25 (merged in 9ecea71, line gate 2544); checked again with the walk areas (ccdc07f): the frame walk
  key is what the walk reads plus the walker (stair_task or stair_task_in) and the stair rule; release candidates
  and finals keep the check mark by design.
- [x] Known-good stair records in the public repository (maintainer, 16 October 2026): for every flight, its place
  (cell, model, reference number, position), how it behaves (passed, covered, untestable, with the rise and the
  headroom) and the SHA-256 of exactly what the walk read. A build from the same game data makes the same
  collision, so its hashes match and the walk is skipped; only a flight whose hash differs (a changed converter or
  other game data) is walked. Hashes and coordinates only, no game data. The stair gate stays the development
  check; a release build checks the records, and a full walk runs in the nightly reference build. A full walk
  stays one builder option away for anyone who wants it (maintainer: "if you WANT to run the staircase tests, you CAN"),
  e.g. `--stair-walk full` ignoring every stored and shipped record. For anyone building the game from their own
  data the walk is a developer and debugging tool, off by default (maintainer, 16 October 2026): a build whose
  collision hashes match the shipped records skips it; a flight whose hash differs is reported (it means a
  different converter or different game data) and walked only on request.
  Design written (docs/BUILD_PROFILE.md "Known-good stair records"): one row per frame (key, walker, rule, outcome,
  counts, rows SHA-256, flight steps with place and behaviour), proposed `--stair-walk-cache records|cached|full`
  (`--stair-walk` already names the walk's scope).
  Built on branch v0.0.42-stairs2 (8da2b42, merged with the line in 6a2ef9d; gate 2680): `config/stair-records/v0.0.41-chim.json`
  from a full walk of the v0.0.41 final world with the v0.0.42 walker (726 frames, all passed, 1,233 flight steps,
  498,667 bytes); `--stair-walk-cache records` is the default without `--developer-mode`. Measured on that world:
  records mode walks 0 of 726 frames (84 s, frame keys only; the full walk took 32 min); a frame whose walk area was
  moved by one unit is named and not walked. Left: the nightly reference build writes the file again with each walker
  change (by hand until then); legacy maps have no shipped records yet (walked as with cached).
- [x] The stair gate runs first on the frames that changed, before the rest of the CHIM checks, so a stair
  failure stops a build in minutes, not at its end.
  Evidence: ccdc07f and the option-history commit after it, gate 2601: `tools/chim_build.py --gate-order stairs-first` (default; right after the
  validation, before the statistics, heap gate and zone walk; `stairs-last` keeps the earlier order). Still after
  the world conversion: walking each frame as soon as it is converted is the next step.
- [ ] A general collision rule instead of a list of mesh names: a convex piece whose underside sits more than a unit
  below an authored downward-facing surface becomes that mesh's authored plates
  ([CHIM-VOS-TEMPLE-WALKWAY-41](../../bugs/CHIM-VOS-TEMPLE-WALKWAY-41.md)); swept island-wide with the stair gate and the
  heap gate.
  Built and measured, kept EXPERIMENTAL (branch v0.0.42-stairs2, `--collision-underside rule|split|whole`; the name
  list stays the default): on every exterior mesh the rule changes 162-240 meshes for +3.6 % to +33 % standing clip
  nodes, and on a Vos test world the walkway step still starts in solid; only the whole-mesh form passes the step,
  and it doubles the clip nodes and fails the heap gate (7.21 of 6.24 MB). Table on the bug page. Next: find the
  temple piece that closes the walkway and make the rule about that piece.
- [x] Flight marks found on the core plus a margin and steps found the same way at any position (one walker change,
  so every frame walked once more): [STAIR-FLIGHT-CORE-SPLIT-41](../../bugs/STAIR-FLIGHT-CORE-SPLIT-41.md) 39 -> 0 flight
  marks lost on the v0.0.41 world; [STAIR-DETECT-POSITION-41](../../bugs/STAIR-DETECT-POSITION-41.md) 107 -> 63 places
  found only in a copy (rest open). Evidence: branch v0.0.42-stairs2, gate 2680; full walk of the v0.0.41 world:
  726 frames passed.

### 1.0c Nothing quietly disappears from the world

The entity tracker already compares every cell and category (NPCs, creatures, containers, doors, lights,
harvestable plants, flora) with a baseline, and it caught the harvest loss
([HARVEST-CHIM-REGION-LOSS-41](../../bugs/HARVEST-CHIM-REGION-LOSS-41.md)); the loss was let through with a free-text
reason. Maintainer, 16 October 2026: a disparity checker that recognises when the world suddenly loses things, without
delaying the build.

- [ ] Early: the same per-cell comparison right after the world stages, from reference counts the builder already
  has (seconds), not only at the image step at the end.
- [ ] Strict: a loss can be accepted only by naming a registered tracker ID per cell and category; the accepted loss
  is listed in the release notes; refused for release candidates and finals unless the tracker entry says the loss
  is intended.
- [ ] Current: the baseline moves to the latest published release's image (today it is v0.0.31), so every build is
  compared with what players had last.
- [ ] Visible: per-cell gains and losses in the build summary and in the CHIM Progress Tracker.

### 1.1 The builder explains a memory overrun

- [ ] Split each frame's memory peak by source: the frame's own objects, border copies from CHIM neighbours,
  border copies from classic neighbours. A model used by the frame's own objects counts as its own.
- [ ] Split it by kind: drawn faces, collision (planes, clipnodes and nodes no longer counted as drawn), terrain,
  textures.
- [ ] Per top model: the heavy part (planes, clipnodes or faces), tilted copies of the same mesh, collision
  fallbacks with their reasons, whether a recipe covers it.
- [ ] A one-line hint per cause, pointing at the CHIMport procedure.
- [ ] Output in four places: the heap gate's error, the build log, the heap report (data), the master builder's
  summary line; a warning on frames over 90 % whose classic-neighbour share is large.
- [ ] The Polycount inspector shows the same overview next to its heatmap.
- [ ] Tests on a fixture frame; checked against the 16 October hand analyses (Ashurnibibi, Sadrith Mora (18,4)).

### 1.2 `dbg cam orbit`, the inspection camera (planned)

- [ ] Engine: orbit the entity under the crosshair, a world position, an original reference number or a camera mark;
  built on the engine's existing idle vanity camera (`aw_view.c`, which today orbits only the player) retargeted to
  the chosen entity, and Quake's chase camera (`chase.c`). All planned camera modes live under `dbg cam` (maintainer, 16 October
  2026), so none is mistaken for a spell or a game command.
- [ ] While orbiting: debug HUD, noclip and god mode on; mouse wheel for distance; speed in degrees per second,
  + and - while orbiting, 0 holds still; right click or Esc restores every setting as it was.
- [ ] The photo variant (planned as `dbg cam orbit photo`): no HUD, no interface, full screen.
- [ ] Debug help entries and docs; the debug-help coverage test passes.
- [ ] Headless FS-UAE: a console exec file runs one orbit; ffmpeg records exactly one orbit (mp4 with game audio,
  under 20 MB); the clip is sent to the maintainer.
- [ ] Works in a full build and in a MiniWind sandbox; one test clip of each.

### 1.2b `dbg cam flyingcam`, the island fly-over (planned)

- [ ] Smooth, steady motion like a drone or steadicam shot (maintainer, 16 October 2026): head bob and view sway off
  for the whole flight by default but switchable on and off (e.g. `bob on`), eased turns and climbs, no camera shake;
  the same for `dbg cam orbit` (planned).
- [ ] Engine: a camera path that spirals over the island from the coast inwards (the CHIMport ring order) at a
  set speed and height above the ground, and eases to a stop over the highest terrain point, on Red Mountain.
- [ ] The path made by the builder from the land records (ring order, ground height along the way, the highest
  point found, not typed in) and stored with the world; the engine only follows it.
- [ ] The tracking shot, planned as `dbg cam flyingcam mountain`: starts at eye height, climbs on the way in, past
  the Ghostfence's height, and settles on the summit of Red Mountain (heights taken from the land records and
  the Ghostfence's placed pieces, not typed in).
- [ ] Noclip and god mode on by default for the whole flight; speed and height settable; switches `hud on` /
  `nohud` (the debug HUD) and `photomode` (full screen, no player stats interface, no crosshair), for both
  both fly-overs (planned); Esc restores every setting as it was.
- [ ] While flying: per-cell frame time, memory and load hitches logged (cell, time, bytes), a streaming test over
  every CHIM cell in one pass.
- [ ] Headless FS-UAE: one full fly-over recorded (mp4 with game audio), plus the per-cell log; debug help entry
  and docs; the debug-help coverage test passes.
- [ ] On the test list (maintainer, 16 October 2026): one fly-over of every release candidate in headless FS-UAE,
  and, as the island fills with CHIM cells, the whole-island performance check: per-cell frame time, memory and
  load hitches compared with the previous release's fly-over, a slower or heavier cell named in the report; the
  fixed benchmark cameras in [HARDWARE-BENCHMARK.md](../../HARDWARE-BENCHMARK.md) stay as the quick check.

### 1.2c `dbg cam pancam`, `dbg cam steadicam` and `dbg cam cranecam`, shots on request (planned)

Maintainer, 16 October 2026: cameras for video postcards, promotional clips, gif animations, inspection and frame-rate
counting, so a shot of any place can be taken and sent on request.

Every planned camera mode (`dbg cam orbit`, `dbg cam flyingcam`, `dbg cam pancam`, `dbg cam steadicam`, `dbg cam cranecam`) is detached from
the world (maintainer, 16 October 2026): the player is not there for the game while a shot runs. No collision and no
damage (noclip and god mode), no enemy notices or attacks (Quake's `notarget`, extended to every enemy awareness check), no
doors, triggers, pick-ups or scripts fire, no dialogue starts, and the game state is left exactly as it was when
the shot ends.

- [ ] `dbg cam pancam` (planned): a pan across a location, left or right, at a set speed, from the current position or
  given coordinates; `hud on` / `nohud` and `photomode` (full screen) switches.
- [ ] `dbg cam steadicam` (planned): the camera glides at a set height above the ground (player height by default),
  steady, no head bob, with its own `photomode` switch.
- [ ] `dbg cam cranecam` (planned, maintainer, 16 October 2026): the camera rises or lowers straight up or down from the
  current position at a set speed and stays there; or a sequence: up, hold for x seconds, down, hold for y seconds,
  repeated or once (heights, speeds and hold times settable); smooth, no head bob, with the same `hud on` / `nohud`
  and `photomode` switches. Useful for town reveals and for frame-time counts at different heights over one spot.
- [ ] `dbg cam mark NAME`, `dbg cam recall NAME` and `dbg cam list` (planned, maintainer, 16 October 2026; under `dbg cam`
  so they are not mistaken for the Mark and Recall spells): a named shot saved and restored
  exactly (map or cell, position, heading and pitch, time of day, headlamp, fog distance), detached from the world
  like the camera modes. Marks live in a file: public ones in the repository (the benchmark cameras, bug-evidence
  spots), private ones in the save folder. The camera modes, speed measurements, bug pages and A/B screenshots name
  marks instead of repeating coordinates (planned `dbg cam orbit NAME`).
- [ ] All of them in headless FS-UAE: one exec file per shot, recorded as an mp4 or gif, with the frame-time log of
  the run.

### 1.3 The remaining cells, by weight

- [ ] A table generated from the tracker after every build: cell, place, region, memory headroom, placed faces,
  status; lightest first; in the CHIMport guide.
  17 October 2026: `tools/chim_weight_table.py` writes it (both weights, the build and date of every figure, towns
  kept whole, classes as data in `config/chim-weight-classes.json`, proposed and waiting for the maintainer); the guide
  section and [CELL_WEIGHTS.md](../../chim/CELL_WEIGHTS.md) are generated. Still to do: run it after every build.

### 1.3b Every cached result says when and with what it was made

- [ ] One provenance writer for every cache entry and stage record: creation timestamp (ISO with zone), AmiWind
  version, CHIM version, source commit, run, converter hash ([BUILD-CACHE-PROVENANCE-41](../../bugs/BUILD-CACHE-PROVENANCE-41.md)).
- [ ] A test fails a cache entry without them.
- [ ] Using it (maintainer, 16 October 2026): a query tool over the provenance, for glitches and regression smoke checks.
  "Which build made this cell, mesh or map, from which inputs, with which versions and converter?"; "what changed
  between these two builds, and which code changed it?" (units with a new input or converter, reused units shown
  as reused); before a release, every unit changed since the previous release listed with its cause, unexpected
  changes flagged before anyone plays the build; a bug's "introduced in" filled from the records.

### 1.4 Reuse the building blocks and simplify collision (maintainer, 16 October 2026)

- [ ] Recipes per kit family, applied island-wide: one measured treatment of each Telvanni, Hlaalu, Redoran,
  Velothi, Dwemer and Daedric piece used in every town and ruin (as the everywhere recipe does for the
  streetlight), instead of one recipe per town.
- [ ] Collision counted as its own factor in every cell and model report (it was about three quarters of
  Ashurnibibi's ruins and about 95 % of the large Telvanni root).
- [ ] Authored collision shapes used where a mesh has one (cheaper than collision from the visible mesh); measured.
- [ ] Coarser convex pieces per mesh where no walkable surface depends on them (`collision_tolerance`).
- [ ] For town architecture, where the step-height rule keeps the authored surfaces: walkable surfaces exact,
  only what cannot be stood on simplified; the stair walk and the walkability audits decide.

## 2. Complete Vivec (the city)

### 2.1 Interiors (14 of 144 rooms left out on 16 October)

- [x] Same-lit placements share one model (`shared_ambient`): today every lit placement is its own inline model.
  Measure the 14 rooms' counts before and after. Done 16 October 2026 (gate 2641): an unlit placement shares
  its model (`AMIWIND_SHARED_AMBIENT=off` keeps the earlier rule); Hlaalu Underworks 225 -> 191, St. Delyn
  Storage 249 -> 204, St. Olms Temple 230 -> 205, Prison Keep 254 -> 230, Telvanni Plaza 267 -> 249; rooms full
  of lanterns gain little (Foreign Quarter Lower Waistworks, the Waistworks rooms: 0).
- [x] Plants as sprites: non-harvestable plants first (fixes Foreign Quarter Lower Waistworks, Hlaalu Underworks,
  Telvanni Plaza, Telvanni Waistworks by count); harvestable ones keep their pick (adds Redoran Waistworks and
  St. Olms Waistworks). Done for nonsolid static plants (16 October 2026, `tools/interior_plants.py`): a room over
  its model limit gets them by itself, Hlaalu Underworks by its config row (heap). In: Foreign Quarter Lower
  Waistworks (213 slots), Hlaalu Underworks (145). Harvestable plants keep their mesh (no Vivec room has a pick
  catalogue yet), so Telvanni Plaza (222, 101 harvestable meshes) and the Waistworks rooms stay over.
- [ ] Per-mesh reduction as an A/B for the rooms over memory (not needed on 16 October 2026: measured against the
  v0.0.41 image's own heap profiles every room fits its heap after the steps above; INTERIOR-EXCLUDE-STALE-41): St. Delyn Underworks (964 bytes over), Telvanni
  Tower (chairs, tapestries, two large trees), Hlaalu Underworks (769 KB over: the corpse mesh, sewer pillars,
  vines), Telvanni Plaza.
- [ ] Sections cut at hallways and doorways for what is still over 220 models: the builder proposes cuts at
  doorway and hallway pieces and floor narrowings, scores each side, the maintainer reviews in the inspector's
  divider; `tools/prepare_interior_sections.py` builds them inside the build. Expected: No Name Club, Prison
  Keep, St. Delyn Storage, St. Olms Temple, Guild of Mages.
  16 October 2026: `tools/propose_interior_cuts.py` proposes the cuts (sides counted by the converter's own
  sharing rule) for the seven rooms still over: Telvanni Plaza 222, St. Olms Waistworks 223, Prison Keep 230,
  Telvanni Waistworks 231, Redoran Waistworks 233, Guild of Mages 248, No Name Club 262 model slots. Waiting for
  the maintainer's review in the inspector; no cut is built before it. (St. Delyn Storage and St. Olms Temple fit
  after same-lit sharing.)
- [x] Redoran Temple Shrine recentred (coordinates reach 4,156). Done 16 October 2026: `"recentre"` in the room's
  config row, 4,156 -> 1,212; Arena Waistworks (listed as vci000, 4,671 -> 1,602) the same way.
- [ ] All 144 rooms in the build; 0 doors "unavailable" (63 today).

### 2.2 Vivec himself

- [ ] The resident stage takes listed creatures (`INTERIOR-CREATURES-MISSING-41`): Vivec (CREA `vivec_god`) first.
- [ ] His model posed on his own skeleton at the authored crossed-leg idle, the height the animation gives him
  kept; classed as levitating, so the ground check and the engine's floor snap leave him floating.
- [ ] Every reference the resident stage leaves out is listed with its reason.
- [ ] A/B with OpenMW at the same position; an orbit clip for the maintainer.

### 2.3 The city frame and the visible defects

- [ ] The city frame owns only the city's cells, on whole-cell borders (`CHIM-VIVEC-FRAME-WIDE-41`); the three
  residents grounded without a waiver.
- [ ] The two banner-draped giant mushroom caps closed (`MESH-VIVEC-CAP-GAP-38`).
- [ ] The Hlaalu Ordinator's appearance (`NPC-ORDINATOR-APPEARANCE-39`).

### 2.4 The Vivec bug review

- [ ] Close the 14 entries fixed but left open, each with its evidence.
- [ ] Close the 5 entries replaced by the whole-city frame, each with what replaced it.
- [ ] The 10 entries that need an in-game look: one orbit clip or still each, then fixed or closed.
- [ ] The 13 still-real entries fixed or scheduled with a reason.

## 3. CHIMport by weight

### 3.1 Before the batches

- [ ] Seabed cells (land records entirely under water) planned and converted as their own cells
  (`CHIMPORT-OCEAN-LAND-41`, 98 cells); the ocean statuses corrected.
  17 October 2026: planned. All 98 are LAND records without height data and nothing placed; the tracker no
  longer takes an open-ocean result for them; they are converted in the re-measure run below.
- [ ] Measure all candidates again with the current builder (one CHIMport run); feed the tracker; publish the
  reference.
  17 October 2026: needed: every headroom figure of the easy candidates comes from the v0.0.36-v0.0.40 builders
  ([TRACKER-RELEASE-HEADROOM-MISSING-42](../../bugs/TRACKER-RELEASE-HEADROOM-MISSING-42.md)); the run waits for a quiet
  machine.
  17 October 2026: done: one CHIMport run with the current builder (3aa9743) over the 611 cells not on CHIM
  (26 minutes on 12 threads): 607 converted, 4 stopped on unclassified NPCs
  ([CHIM-ACTOR-GROUNDING-POLICY-36](../../bugs/CHIM-ACTOR-GROUNDING-POLICY-36.md), decided for the project the same day:
  ground by the OpenMW drop-to-ground rule; the four cells measured again and passing); all 98 seabed cells empty sea
  ([CHIMPORT-SEABED-NO-ISLAND-42](../../bugs/CHIMPORT-SEABED-NO-ISLAND-42.md) fixed on the way); tracker fed and the
  reference published. Classes now: featherweight 161, lightweight 326, middleweight 15, heavyweight 1, over or
  failing 18 (14 hull policy pending, 4 stair walk), seabed 98.

### 3.2 The easy batch

- [ ] Every converted cell with all audits passing and comfortable headroom, whole regions where possible
  (16 October: 459 cells with at least 2 MB).
  17 October 2026, provisional (older builders' figures): 479 cells in the two easy classes (the 459 of 16 October
  plus 20 lava cells measured on 16 October); 316 in the batch once towns are kept whole and the lava group waits
  for its method (357 with the lava cells as ordinary cells); no region is whole yet.
- [ ] CHIM-stage precheck of the batch; one build; the tracker and the build list updated.
  17 October 2026: batch 1 (v0.0.42-dev2) = the dev1 cells + 499 easy cells (401 land, 19 of the 24 lava cells
  as ordinary cells, the other 5 waiting with Erabenimsun Camp, Dagoth Ur and Suran; 98 seabed); 9 pocket openers
  left out with their pocket named (cells wholly inside a town frame no longer open a pocket:
  [CHIM-REGION-POCKET-TOWN-CELLS-42](../../bugs/CHIM-REGION-POCKET-TOWN-CELLS-42.md)); 1,252 cells in the list; region
  doors get their door table ([CHIM-REGION-DOORS-NO-PROMPT-42](../../bugs/CHIM-REGION-DOORS-NO-PROMPT-42.md)).
  The first final build stopped on the 98 heightless seabed cells
  ([CHIM-REGION-SEABED-NO-HEIGHTS-42](../../bugs/CHIM-REGION-SEABED-NO-HEIGHTS-42.md)): v0.0.42 builds 1,154 cells
  (1,115 region frames) without them; they join after that repair.

### 3.3 The heavier cells, lightest first, each group measured again first

- [ ] The inland lava group (24 cells): all three options measured and kept selectable (ordinary cells, the lava
  stored once as a shared piece, smaller lava groups); the default is picked by the project. Decided 17 October
  2026: ordinary cells, joining the easy batch if they pass the re-measure run with the current builder; the weight
  classes confirmed as proposed. Measured 16 October 2026 as
  ordinary region cells, each built on its own: all 24 fit (28-60 % of the budget for most; the tightest, (9,1)
  94 % and (8,1) 92 %, beside the Dwemer ruin by the lava pools); stair walk passed (15,411 steps and ramps).
- [ ] Settlements and heavy spots with 1-2 MB headroom (Zergonipal, Bal Isra, Zainab Camp, Dren Plantation,
  Erabenimsun Camp, Urshilaku Camp and eight more).
- [ ] Tight cells under 1 MB (Suran, Vos, three Red Mountain cells, one in Sheogorad).
- [ ] Over budget: Tel Vos, and cells in Sheogorad, Red Mountain and the Grazelands, through the over-budget
  procedure.
- [ ] Failing other audits: Ald-ruhn, Maar Gan and two more.
- [ ] Caldera and its neighbour, never converted.

## 4. Effects (with the regions they belong to)

- [ ] The Ghostfence and Ghostgate curtain as a Quake turbulent (`*`) texture, its glow on a flickering light style.
- [ ] Intense lava smoke plumes: overlapping animated smoke sprites per pool; a few particle embers close by.
- [ ] Each effect A/B'd against the original at the same pose, headlamp off.

## 5. Release

- [ ] The release guard on the candidate; one gate; a full build; boot smoke; the playtest package and source ZIP
  published; README and gallery updated from the finished build; the Linux kit.
