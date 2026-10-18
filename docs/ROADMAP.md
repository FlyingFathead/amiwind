# Roadmap and implementation options

[CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md) — 15 October 2026, v0.0.41-dev1: full-build preparation rejected five explicitly selected ocean routing cells absent from the original CELL/LAND inventory, before legacy compilation. The source checklist now records additional ocean routing cells separately and allows their absence only before routing rows are appended. Final classification/stage verification still requires every row and CHIM routing flags; undeclared or unselected missing cells are rejected. All 98 targeted checks across five modules pass, including three new ocean checklist regressions. Exact production conversion, native ocean behavior, image/package and delivery checks remain pending; coverage states are unchanged.

<!-- contents start -->
## Contents

- [Next: the outdoors complete, then every entrance and every interior, 18 October 2026](#next-the-outdoors-complete-then-every-entrance-and-every-interior-18-october-2026)
- [Near future: the baseline stays, extra RAM becomes speed, 16 October 2026](#near-future-the-baseline-stays-extra-ram-becomes-speed-16-october-2026)
- [Near future: one game for the 68040 and the 68060, 16 October 2026](#near-future-one-game-for-the-68040-and-the-68060-16-october-2026)
- [Goal: every exterior on CHIM, 16 October 2026](#goal-every-exterior-on-chim-16-october-2026)
- [v0.0.42: Complete Vivec (the city), 16 October 2026](#v0042-complete-vivec-the-city-16-october-2026)
- [Effects to investigate: Quake machinery first, 16 October 2026](#effects-to-investigate-quake-machinery-first-16-october-2026)
- [v0.0.41 "More Fixes" and v0.0.42, 16 October 2026](#v0041-more-fixes-and-v0042-16-october-2026)
- [v0.0.41 candidate - visibility aprons, 15 October 2026](#v0041-candidate---visibility-aprons-15-october-2026)
- [v0.0.41 candidate - window support, 15 October 2026](#v0041-candidate---window-support-15-october-2026)
- [v0.0.41 candidate - lava coverage, 15 October 2026](#v0041-candidate---lava-coverage-15-october-2026)
- [Compiled apron selection, 15 October 2026](#compiled-apron-selection-15-october-2026)
- [Paired boundary validation, 15 October 2026](#paired-boundary-validation-15-october-2026)
- [Owner apron follow-up, 15 October 2026](#owner-apron-follow-up-15-october-2026)
- [Combined-world gate update, 15 October 2026](#combined-world-gate-update-15-october-2026)
- [v0.0.41-dev1: ring3 feasibility after v0.0.40 delivery](#v0041-dev1-ring3-feasibility-after-v0040-delivery)
- [v0.0.40 release scope - 15 October 2026](#v0040-release-scope---15-october-2026)
- [v0.0.40-dev1 gameplay priority, 14 October 2026](#v0040-dev1-gameplay-priority-14-october-2026)
- [Additional RC1 inspection findings, 13 October 2026](#additional-rc1-inspection-findings-13-october-2026)
- [Release hold and RC2 request, 13 October 2026](#release-hold-and-rc2-request-13-october-2026)
- [v0.0.39 - Cell By Cell, Piece By Piece](#v0039---cell-by-cell-piece-by-piece)
- [Movement presets and all eight attributes, 13 October 2026](#movement-presets-and-all-eight-attributes-13-october-2026)
- [v0.0.40 - Unfinished work and new features](#v0040---unfinished-work-and-new-features)
- [v0.0.38 - Lava Is All You Need (And A Hint Of Tel Uvirith)](#v0038---lava-is-all-you-need-and-a-hint-of-tel-uvirith)
- [v0.0.37 - Proofreading the Cantons (fix release)](#v0037---proofreading-the-cantons-fix-release)
- [v0.0.36 - 36 Lessons of Vivec's Cantons (And Vvardenfell Shorelines) (released)](#v0036---36-lessons-of-vivecs-cantons-and-vvardenfell-shorelines-released)
- [v0.0.35 - CHIMporting It All: Gathering Up The Loose Branches From The Seashore (released)](#v0035---chimporting-it-all-gathering-up-the-loose-branches-from-the-seashore-released)
  - [Next: build system](#next-build-system)
  - [Build pipeline speed (very near term, after Vivec)](#build-pipeline-speed-very-near-term-after-vivec)
  - [Perf, profiler and optimizer (future)](#perf-profiler-and-optimizer-future)
  - [Next: CHIMport region by region, coast first](#next-chimport-region-by-region-coast-first)
  - [Gameplay](#gameplay)
  - [CHIM maps become their own format (approved 10 October 2026)](#chim-maps-become-their-own-format-approved-10-october-2026)
  - [Tiny squeezes: memory that stays resident](#tiny-squeezes-memory-that-stays-resident)
  - [Roadmap horizon: one partition with CHIM](#roadmap-horizon-one-partition-with-chim)
- [v0.0.34 - CHIM: Tightening the Bolts (released)](#v0034---chim-tightening-the-bolts-released)
- [v0.0.33 - Towards CHIM: Replacing the Engine Block (released)](#v0033---towards-chim-replacing-the-engine-block-released)
- [v0.0.32 - Last Stop on the Old Line: Window-Shopping in Vivec (released)](#v0032---last-stop-on-the-old-line-window-shopping-in-vivec-released)
  - [Decided: a world streamer with no duplicated assets - the whole game on one hard file](#decided-a-world-streamer-with-no-duplicated-assets---the-whole-game-on-one-hard-file)
  - [Near future: fires and lava across the world](#near-future-fires-and-lava-across-the-world)
- [Planned: heap size matched to the host machine, 7 October 2026](#planned-heap-size-matched-to-the-host-machine-7-october-2026)
  - [The cache plan: extra RAM spent on not doing work twice (16 October 2026)](#the-cache-plan-extra-ram-spent-on-not-doing-work-twice-16-october-2026)
- [Other ideas and wildcards](#other-ideas-and-wildcards)
  - [Sky fading into the horizon](#sky-fading-into-the-horizon)
  - [Sea skirt: the sea runs to the horizon](#sea-skirt-the-sea-runs-to-the-horizon)
  - [Weather: ash storms and blight winds](#weather-ash-storms-and-blight-winds)
  - [Long-term possibility: a reusable Amiga game engine](#long-term-possibility-a-reusable-amiga-game-engine)
  - [Long-term possibility: an RTG display path](#long-term-possibility-an-rtg-display-path)
  - [Long-term possibility: Lua scripting](#long-term-possibility-lua-scripting)
  - [From Quake Arena to Vivec Arena: two-Amiga 1v1 duels](#from-quake-arena-to-vivec-arena-two-amiga-1v1-duels)
- [Older history](#older-history)

<!-- contents end -->

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: whole-world metadata binding failed because tutorial barrel reference 172851 lacked its original CELL, while the original audit records [-2,-9]. A narrow source correction restores only that missing field before capture, rejecting nonempty wrong cells and every other identity/transform mismatch. Fifty focused Seyda/ownership checks pass, including three new semantic regressions. The preceding 4,247-test full-suite pass remains historical; the repaired world is pending. The prepared Linux source kit is held and undelivered. Native, image/package and playtest acceptance remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1 image integration follow-up: added Seyda dependency numbers and model digests are checked against the world-index-bound source manifest before source-carrier static parity includes them. Frames without supplements retain prior behavior. The focused ownership/apron module now passes 33 checks, including five new semantic regressions and missing/rebound-model rejection. The issue remains OPEN; exact world rebuild, held-boundary/native and image/package checks remain pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: a source repair supplements only missing Seyda apron dependencies using the included original-cell owner's exact compiled mesh and textures, preserving original identity and unique ownership while translating frame-local origins. It targets rock reference 251397 and shell reference 461804; 32 focused ownership/apron checks pass. The rebuilt world and held boundary/native checks remain pending. Separately, independent normal interior/actor/UI conversion completed 2,451 files with unchanged source and inputs; it is not image, native or package acceptance. CHIM coverage states are unchanged. Earlier full-suite and world results remain bound to their preceding source; changed apron acceptance is pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: exact source validation completed 4,242 tests (4,236 passed, three Windows-only skips and three Census expected failures), with zero failures/errors; the matching engine compiled. The completed 369-frame world passed structural/source, modeled heap, host zone-walk and scoped stair gates. Of 547 boundary comparisons, 544 measured agreement and three remain held (237, 241, 242). Of 36 sampled models, 22 have matching face counts and unique face correspondence; 14 differ in collision-only versus visual representation and require payload/sprite/native review. These measurements do not establish visual severity or universal equivalence. Native captures, independent interior conversion, image assembly/readback and package acceptance remain pending; coverage states are unchanged. Stair evidence retains 15,348 advisory findings despite zero blocking failures.

15 October 2026: active preparation now targets v0.0.41-dev1. The planned final release title is **v0.0.41: Collisions And Boundaries**. Earlier source snapshots, checks and findings retain their recorded version identities; they do not establish acceptance of this development candidate. Matching source validation, completed image assembly/readback, native checks, packaging and delivery remain separate gates. See the [current development candidate](RELEASE-v0.0.41-dev1.md).

[BUILD-INVENTORY-PALETTE-41](bugs/BUILD-INVENTORY-PALETTE-41.md) — 15 October 2026, v0.0.41 source candidate: image assembly prepares inventory before the sky palette pass, which rejected current AWIC icons and AWI2/AWST metadata as unknown images. The source repair validates each inventory format at its exact path, remaps only icon pixels and preserves metadata bytes. Scoped evidence contains 15 passing palette checks and 2 passing inventory-asset checks on matching unchanged source. Actual image assembly, native verification, packaging and shipment remain pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41 source candidate: the 941 world stopped at the unchanged ownership guard because ten explicitly deferred Seyda references reappeared through a named-town apron. The candidate applies the existing exact owner dispositions to named and regional neighbours alike. All ten original deferred IDs are verified and 38 focused checks pass. Fresh affected-world conversion and renewed boundary/memory checks remain pending; no coverage, native, package or maintainer acceptance is promoted.

[CHIM-MODEL-ARENA-RESERVE-41](bugs/CHIM-MODEL-ARENA-RESERVE-41.md) — 15 October 2026: exact allocation and predecessor-world checks remain separately recorded. The later 941 world stopped at its ownership guard because named aprons bypassed ten existing deferred-owner dispositions. The source-only disposition repair passes 38 focused checks; fresh world, boundary/model review and native/package acceptance remain pending.

[CHIM-RECIPE-APRON-SCOPE-41](bugs/CHIM-RECIPE-APRON-SCOPE-41.md) — 15 October 2026, v0.0.41 candidate: recipe repair converted all four affected frames with structural PASS. Three still failed the unchanged memory gate (peaks 6,957,632; 6,939,952; 6,644,768 bytes for (10,0), (10,1), (9,2)); (11,0) passed at 5,875,568 bytes. The separate placed-model reserve repair passes all four on identical world bytes. A complete successor world and recipe/model/sprite equivalence and native checks remain pending.

15 October 2026: exact-source validation completed 4,231 tests: 4,225 passed, three Windows-only skips and three tracked Census expected failures. The 71 focused tests and original-data readback across nine frame positions passed, consistently hiding 33 of 158 original references at stronghold state 6 while preserving unknown scripts. All 243 player resources are reusable after exact producer, input and file verification. Complete combined-world conversion, native comparison, packaging and shipment remain pending; coverage counts are unchanged.

## Next: the outdoors complete, then every entrance and every interior, 18 October 2026

**v0.0.43 (in progress): every exterior cell of Vvardenfell on CHIM.** After v0.0.43-dev2 the cells still classic
are the ones held by the stair walk (Ald-ruhn, Maar Gan, Suran and one rope bridge cell, with the town cells
around them), eight Balmora border cells and fourteen open-sea cells; the last two are fixed, the stair fix is
in the shared converter. v0.0.43-dev3 is meant to be the first build with the whole outdoors on CHIM
([progress tracker](chim/PROGRESS_TRACKER.md#current-state-18-october-2026)).

**v0.0.44, the next step, decided for the project on 18 October 2026: entrances and interiors.**

1. **An entrance audit, island-wide.** From the game data, every load door (outside to inside, inside to
   inside, inside to outside) is checked against the build: the destination interior is converted and in the
   image, the door shows its prompt, the player arrives standing inside the room and not in a wall, and a door
   leads back near the entrance. Doors to rooms left out on purpose are named with the reason. It is a data
   check, not a walk through every door.
2. **An interior progress tracker,** the interior twin of the exterior cell tracker: one row per interior cell
   with its entrances, whether it is converted and in which build, its limits (inline models, room memory,
   coordinate range), its audits (stairs, lighting, actors, harvestables) and a status colour with the reason
   for anything left out. It is shown in the Toolkit, linked from the doors on the exterior map, published as a
   reference with every build, and fed after every build like the cell tracker.
3. **Missing interiors become conversion batches,** through the interior procedure
   ([interiors over a limit](INTERIOR_SECTIONS.md)): numerous decorative meshes as sprites, per-mesh recipes,
   sections cut at hallways and doorways. Vivec's rooms left out so far come first.

**After the interiors and the fixes that come with them: the game logic.** With the world and its rooms in
place, the work turns to what happens in it: an interpreter for MWScript, the game's own script language, that
runs the original scripts from the game data; dialogue conditions and quests; NPC and creature behaviour; combat, magic,
inventory and services. As everywhere else, the original game's records and behaviour are the reference for what
it should do, OpenMW the readable reference for how it fits together, and AmiQuake's machinery (QuakeC, entities,
the server loop) the means, measured for its cost on the 68040 and 68060.

**MWScript compiled at build time, decided for the project on 18 October 2026.** The Amiga does not interpret the
game's script text while it plays. The builder parses every script once into compact bytecode (or QuakeC), folds
constants, drops dead branches, and turns the scripts that run on every frame into cheap event checks. Behaviour
stays identical, quirks included: some of the original scripts depend on odd timing and corner cases, and quests
rely on them, so each optimization is checked side by side against the original game (and OpenMW) before it is
kept. Optimized, never changed. The one exception is the original's known script and engine bugs that OpenMW
fixes: AmiWind takes the same fixes, written in its own code and each named with the OpenMW issue or change it
follows, so a player sees the behaviour OpenMW players see. These fixes are on by default.

## Near future: the baseline stays, extra RAM becomes speed, 16 October 2026

The game keeps working on the current memory setup (the reference configuration and its budgets decide every
gate), and uses more RAM as caches when a machine has it: a larger surface cache, resident streamed chunks,
prefetch, visited interiors kept, read caching. Details: [the cache plan](#the-cache-plan-extra-ram-spent-on-not-doing-work-twice-16-october-2026).

## Near future: one game for the 68040 and the 68060, 16 October 2026

Project decision, 16 October 2026: one game binary that recognises the machine at start-up.
The 68060 plan, its rules and steps: [AmiWind on the 68060](68060.md).

- [ ] The engine reads the CPU and FPU type at start-up (the system's attention flags) and picks its 68040 or its
  68060-tuned version of each hot routine (span drawing, edge clipping, the surface cache builder) once, through
  a function pointer. The 68040 path stays the baseline; the 68060 path is our own measured code, pixel-identical
  at the same poses, and avoids the instructions the 68060 emulates in software.
- [ ] The CPU support library (`68040.library` or `68060.library`, the user's own, never shipped by us) either set
  when building or dropped into the game disk's library folder afterwards; the boot script loads the one
  matching the CPU. Default folder when building: `amiga-libs` next to the Morrowind `Data Files` folder, used
  when present; `--amiga-libs DIR` chooses another. The hardware guide keeps the
  [compatibility roadmap](REAL_HARDWARE.md#compatibility-roadmap).
- [ ] If the CPU needs a library that is not there, the game says so in plain words (which file, where to put it)
  instead of crashing on the first emulated instruction.

## Goal: every exterior on CHIM, 16 October 2026

Project decision, 16 October 2026: everything above ground (and the sea around it) is CHIM; interiors are each a
Quake map or CHIM, whichever suits the room. When every exterior cell is CHIM, the classic region maps leave the
game: no edges between CHIM and classic cells, no border copies of classic objects in CHIM frames, no object
stored many times over, one world format outdoors. The classic region builder stays in the code, selectable for
A/B regression tests, but no build ships it. The path: v0.0.41 (rings 0 to 4 with the Bitter Coast and Azura's
Coast whole), the batch import of the easy cells in v0.0.42, the remaining cells by weight, the seabed cells and
the open sea, then Solstheim ([v0.0.42 working plan](PLAN-v0.0.42.md)).

## v0.0.42: Complete Vivec (the city), 16 October 2026

Project decision, 16 October 2026: v0.0.41 ships the first regional build (More Fixes, Fewer Planes
(A Telvanni Root Story)); v0.0.42 completes the city of Vivec.

The step-by-step checklist, with what counts as done for each step, is the
[v0.0.42 working plan](PLAN-v0.0.42.md).

- [ ] `dbg orbit` (planned): an inspection camera that orbits the object under the crosshair, a world position or an
  original reference number, with the debug HUD, noclip and god mode on; mouse wheel for distance; orbit speed
  settable (a number of degrees per second, and + / - while orbiting, 0 to hold still); right click or Esc
  restores everything. A photo variant, planned as `dbg orbit photo`, hides the HUD and all interface for
  full-screen promo clips. Built on Quake's chase camera; the test harness records one orbit as a short clip.
- [ ] The stair gate only where something changed: each flight walked once, a pass kept by the SHA-256 of what it
  read, and known-good stair records (place, behaviour, hash; no game data) shipped in the repository so a build
  from unchanged data skips the walk ([plan 1.0b](PLAN-v0.0.42.md#10b-the-stair-gate-walk-each-flight-once-keep-every-pass-ship-the-known-results)).
- [ ] `dbg flyingcam` (planned): a fly-over camera that spirals across the whole island at a set speed and
  height above the ground, from the coast inwards like the CHIMport's own ring order, and slows to a stop over
  the highest terrain point, on Red Mountain (found from the land records). Flown in noclip and god mode by default;
  speed and height settable; `hud on` / `nohud` for the debug HUD; `photomode` for full screen without the
  player's stats interface; Esc ends it and restores every setting. Uses: a streaming and frame-time run over
  every CHIM cell (memory, load hitches, missing or broken cells seen in one pass) and a promo clip.
  A tracking-shot variant, planned as `dbg flyingcam mountain`, starts at eye height, climbs past the top of the
  Ghostfence and comes to rest on the summit of Red Mountain. Both fly smooth, steadicam-like shots: head bob and
  view sway off by default. Both go on the test list: a fly-over of every
  release candidate, and, as more of the island is on CHIM, the whole-island performance check against the
  previous release's fly-over.
- [ ] Seabed cells (land records entirely under water) planned and converted as their own CHIM cells
  ([CHIMPORT-OCEAN-LAND-41](bugs/CHIMPORT-OCEAN-LAND-41.md)); interior creatures placed, the demigod Vivec first
  ([INTERIOR-CREATURES-MISSING-41](bugs/INTERIOR-CREATURES-MISSING-41.md)).
- [ ] Every Vivec interior in the build. Today 14 of 144 rooms are left out: 11 over the 220 placed-model limit,
  4 over the room memory budget (one by 964 bytes), 1 past the coordinate range. In order: numerous plants as
  sprites, per-mesh reduction measured as an A/B, sections cut at hallways and doorways, recentring
  ([Interior sections](INTERIOR_SECTIONS.md#interiors-over-a-limit-the-order)).
- [ ] Vivec himself in his palace: the demigod floats above the floor, meditating in the lotus position, as in the
  original (his own idle pose and hover height; the actor ground check accepts a floating actor where the
  original places one).
- [ ] The city frame owns only the city's cells, on whole-cell borders
  ([CHIM-VIVEC-FRAME-WIDE-41](bugs/CHIM-VIVEC-FRAME-WIDE-41.md)); the two banner-draped giant mushroom caps closed
  ([MESH-VIVEC-CAP-GAP-38](bugs/MESH-VIVEC-CAP-GAP-38.md)).
- [ ] The open Vivec entries of the bug register reviewed: each one still real, fixed, or replaced by the whole-city
  frame, with evidence; the still-real ones fixed or scheduled.
- [ ] Vivec's interior plants that cost frame time drawn as sprites, measured in game.
- [ ] The batch import of the easy cells (maintainer, 16 October 2026), once Vivec is done: every converted cell with all
  audits passing and comfortable memory headroom joins CHIM in one step, whole regions where possible. Measured
  16 October: 524 such cells outside v0.0.41, 459 of them with at least 2 MB of headroom (Ashlands 157, Molag Amur
  91, West Gash 77, Ascadian Isles 58, Sheogorad 53, Grazelands 53, Red Mountain 35). Every CHIM edge removed is a
  frame that no longer carries copies of a classic neighbour's objects, and every classic region map retired is
  one of the old, overlapping maps gone. Order by weight (maintainer, 16 October 2026): the lightest cells first, then
  the heavier, the heaviest last, each step measured again with the current builder (CHIMport) and prechecked in
  the CHIM stage before one build. Converting the light cells first turns the heavy cells' classic neighbours into
  CHIM, which removes the border copies that push them over; the heaviest then go through the over-budget
  procedure.
- [ ] The builder names the neighbour overlap (maintainer, 16 October 2026): each frame's memory peak split into its own
  objects, border copies from CHIM neighbours and border copies from classic neighbours (a model used by the
  frame's own objects counts as its own). The heap gate's failure message, the heap report and the master
  builder's over-budget summary say how much of a peak is classic-neighbour overlap and from which cells, and warn
  on tight frames (over 90 %) where that share is large: those neighbours go first in the light-to-heavy order.
- [ ] An automatic cause overview for every frame over the budget or tight (maintainer, 16 October 2026: "show it in the
  logs or errors ... what exactly caused the heap excess"): in the log, the error, the heap report and the master
  builder's summary, the peak by kind (drawn, collision, terrain, textures; collision planes and nodes no longer
  counted as drawn), by source (own cell, classic and CHIM neighbours), the top models with their heavy part
  (planes, clipnodes or faces), tilted copies per mesh, collision fallbacks with their reasons, which top meshes a
  recipe covers, and a one-line hint per cause pointing at the CHIMport procedure. The Polycount inspector shows
  the same overview next to its heatmap.
- [ ] The remaining cells, by weight: a table generated from the tracker after every build (cell, place, region,
  memory headroom, placed faces, status), lightest first, in the CHIMport guide. Measured 16 October, after
  v0.0.41 and the easy batch 54 Vvardenfell cells would remain: the inland lava group (24 cells, light but one
  shared lava frame group with 175 KB headroom); settlements and heavy spots with 1-2 MB headroom (Zergonipal,
  Bal Isra, Zainab Camp, Dren Plantation, Erabenimsun Camp, Urshilaku Camp and eight more); tight cells under
  1 MB (Suran, Vos, three Red Mountain cells, one in Sheogorad); four over budget (Tel Vos 57 KB, cells in
  Sheogorad, Red Mountain and the Grazelands); four failing other audits (Ald-ruhn, Maar Gan and two more); and
  Caldera, never converted. Each group is worked through in that order, measured again first.
- [ ] The inland lava group as ordinary region cells, with the lava stored once: the lava surface a shared,
  content-keyed piece every lava cell references (as the shared ocean chunk and CHIM's terrain references), so
  no lava is stored twice on disk or in memory (maintainer, 16 October 2026: avoid duplicates). Measured first: each
  of the 24 cells built on its own against the memory budget. The other options stay open and selectable, as
  every method does: smaller lava frame groups split along natural breaks, the shared lava surface on its own,
  and ordinary cells with each cell's own lava; all three are measured, the default is the maintainer's choice.

## Effects to investigate: Quake machinery first, 16 October 2026

Maintainer request, 16 October 2026: future effects start from what AmiQuake already draws, mapped onto the Morrowind
data, before any new engine feature ([IDEAS](chim/IDEAS.md#the-ghostfence-as-a-quake-turbulent-surface)).

- [ ] The Ghostfence and the Ghostgate: the upright shimmering curtain between the pylons (electricity and water
  at once) as a Quake turbulent surface. Textures named with a leading `*` are drawn by the warp that ripples
  water, slime, lava and Quake's upright teleporter fields; our lava already uses it. The fence's energy texture
  becomes such a texture on the fence walls, with no new engine feature.
- [ ] The electric pulse: a flickering light style (Quake's animated light patterns) on the fence's glow, so the
  light around it pulses like the original's shimmer.
- [ ] Smoke plumes rising from the lava pools (maintainer, 16 October 2026: "they can be massive, use AmiQuake cheap
  ones"): large animated Quake sprites over the pools the build already records. A sprite is one camera-facing
  picture, so a massive plume costs what a small one does (one quad, a few frames), with its outline kept like the
  tree sprites. The plumes can be intense: two or three overlapping, nearly opaque smoke sprites per pool at
  different sizes and animation phases give a thick, churning column for the cost of three quads. Quake's
  particles (`pt_fire`, 1-4 pixel squares) only as a few embers close by; a plume of particles would cost
  hundreds per frame.
- [ ] Each effect A/B'd against the original at the same pose, headlamp off, before it is adopted.

## v0.0.41 "More Fixes" and v0.0.42, 16 October 2026

v0.0.41 is a fix release, published once rings 0, 1 and 2 are complete. v0.0.42 brings rings 3 and 4
(149 and 138 cells, all converted) to CHIM. Planned:

- [ ] Builder: chim stage key only its own inputs; stair walks and units reused by hash; every worker used
  ([BUILD-REUSE-KEYS-TOO-BROAD-35](bugs/BUILD-REUSE-KEYS-TOO-BROAD-35.md)). Lava regions measured against the
  storage budget before a build.
- [ ] Town frames own only the town's cells, on whole-cell borders, Vivec first
  ([CHIM-VIVEC-FRAME-WIDE-41](bugs/CHIM-VIVEC-FRAME-WIDE-41.md)); closed giant mushroom caps in towns
  ([MESH-VIVEC-CAP-GAP-38](bugs/MESH-VIVEC-CAP-GAP-38.md)).
- [ ] Mesh optimizer threshold measured (50 to 400 faces); a Dwemer ruin by the lava pools (cells 8,0, 9,2).
- [ ] Interior map: each original interior cell, our maps and their format (BSP29 or CHIM), built or excluded
  with the reason, doors that reach it; exterior entrances first. Shown in the tracker's Interiors table.
- [ ] Planar merge and the mesh optimizer for interiors; the 14 excluded Vivec rooms measured again; a CHIM interior
  trial; the Arena Pit's polycount reduced.
- [ ] Inventory: the original posture per weapon type (A/B with the original game), the title plaque, picked
  mushrooms shown. A stats screen on O. A separate switch for combat speech gating.
- [ ] Quest journal indices as a small table, with a `dbg journal QUEST INDEX` command.
- [ ] Toolkit: a settlement list from your own game files. Done: the polycount inspector opens a build's world
  from its address (`toolkit_serve.py --chim-world`).
- [ ] Full rotation and scale in the CHIM placement record: one drawn model per mesh, collision kept per tilt;
  41-57 % less model data in the cells over budget ([IDEAS](chim/IDEAS.md#memory)).
- [ ] Telvanni towns (Vos, Sadrith Mora) fit with per-mesh recipes
  ([CHIMport](chim/CHIMPORT.md#when-a-cell-does-not-fit-the-memory-budget)).
- [ ] Whole-region CHIM for the lava regions; revisit Seyda Neen, Balmora and Vivec optimizations.
- [ ] Tracker: inclusion by release with a percentage, label fixes, world data size per build.
- [ ] Bug tracker: an "introduced in" commit for regressions; bugs filed from one validated input file.

## v0.0.41 candidate - visibility aprons, 15 October 2026

[CHIM-VISIBILITY-APRON-SCOPE-41](bugs/CHIM-VISIBILITY-APRON-SCOPE-41.md) - The combined world stopped at Tel Uvirith, original cell (10, 1), because
its approved fixed stronghold snapshot required a source radius of zero.
Regional frames now audit neighbouring cells for separate aprons. The repair
keeps visibility snapshots bound to each original cell across all frames that
audit it. Unknown scripts and unaudited references remain visible. Runtime
quest progression is still deferred; complete conversion and native/package
acceptance remain pending. Coverage counts are unchanged.

## v0.0.41 candidate - window support, 15 October 2026

[CHIM-WINDOW-TOWER-SUPPORT-41](bugs/CHIM-WINDOW-TOWER-SUPPORT-41.md) - The combined v0.0.41 world build stopped while mounting four Nordic windows
from original cell (7, 22) into the adjacent frame apron. Their supporting
thatched tower was present, but the facade search accepted only model names
containing "house". Exact source triangles support all four windows under the
existing distance and outward-normal checks.

The candidate recognizes the original thatched-tower model in both local and
neighbouring facade searches. It keeps original reference ownership, geometry,
collision, mounting range and clearance. Arbitrary props are still rejected.
The failing build is preserved; complete conversion, native comparison and
fresh package readback remain pending. Coverage counts are not promoted.


15 October 2026, v0.0.41 candidate: 50 focused lava/polygon/terrain checks
and 47 emulator preset/launcher checks pass. Both original failing chunks pass
coverage against the unchanged cached geometry. Full combined-world, exact
source suite, native, package and shipment checks remain pending.

## v0.0.41 candidate - lava coverage, 15 October 2026

[CHIM-LAVA-DUPLICATE-VERTEX-40](bugs/CHIM-LAVA-DUPLICATE-VERTEX-40.md) - The v0.0.40 combined-world build stopped on two chunks in cell (2, -2).
Readback of the exact cached units found five affected coverage samples:
each has one lava surface and lava contents (-5) at the required depth.
A tiny edge collapses to identical adjacent vertices when the chunk is
translated into float32 frame coordinates. The polygon test mistook this
zero-length edge for a boundary through every sample.

The v0.0.41 candidate skips only exactly identical adjacent XY vertices.
It preserves edge ambiguity, outside rejection and empty/degenerate rejection;
no geometry, collision, pool height, tolerance or engine format is changed.
Full-world validation, native checks, fresh package readback and delivery
remain separate and pending. No coverage count is promoted.

## Compiled apron selection, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The full combined conversion found a conservative
source box overlapping an apron although the compiled rock footprint ends
0.83 game units outside it. The selection now records and excludes only external
references whose compiled pieces all miss that apron. Owned originals, reaching
pieces and missing-piece failures remain protected. The original reference and
compiled boxes remain in the source receipt. All 68 focused checks pass.
The preceding source passed 4,218 tests: 4,212 passed, three Windows checks
skipped and three tracked Census cases were expected failures. The later source
requires its own full suite and combined validation. Native, package and shipment
acceptance remain pending; no converted or accepted coverage count is promoted.

[Canonical report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).

## Paired boundary validation, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The latest v0.0.40 paired conversion passes structural, heap, zone-walk and
stair validation. The 3,836 tested steps and ramps pass; 610 advisory results
remain recorded. Across 2,816 paired positions, full-static support states agree
and the maximum supported-height difference is 0.000077 game units. Terrain,
water and common standing-hull controls agree. The complete 369-frame successor
is being built from the same converter source; its acceptance remains pending.
The exact source full suite is running. Native gameplay, other boundary segments,
fresh package readback and shipment remain separate unfinished gates.

[Canonical report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).

Release preparation, 15 October 2026: all 369 combined candidate frames pass
conversion and structural, heap, zone-walk and stair validation. A later
combined ownership failure keeps the candidate held; corrected compiled-world,
native and package acceptance remain pending. Complete rings 0, 1 and 2, original
references, actors, horizons and visual/collision seams remain release gates.
See [release preparation](RELEASE-v0.0.40.md) and
[the static seam report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).

## Owner apron follow-up, 15 October 2026

The source owner check found twelve additional references in the sampled
regional apron: four placements of the fourth kelp mesh, four objects already
deferred by Seyda, and four nonsolid grasses represented by existing sprites.
The successor retains all four original kelp models. Regional aprons now honor
the included town's exact declared deferrals; nonsolid grasses retain the same
hash-verified sprite bytes and original transforms instead of duplicate meshes.
Unrecorded missing owners, changed original identities and corrupt sprite assets
still fail. The existing ownership validator is unchanged. Forty-seven focused
checks pass, including serialized ownership and sprite corruption controls.

The earlier authored-collision source passed 4,213 tests: 4,207 passed, three
Windows-only checks skipped, and three tracked Census expected failures. This
does not certify the later source. Combined conversion, native seams, gameplay,
fresh packaging and delivery remain pending; no coverage acceptance is promoted.

[Canonical report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).


## Combined-world gate update, 15 October 2026

All 369 frames in the combined candidate passed conversion, structural,
heap, zone-walk and stair validation on 15 October 2026. This establishes a
conversion result for that exact source, not native or packaged acceptance.
The initial comparison measured six of 547 original-cell boundary segments:
five agreed, while southern Seyda between (-2,-12) and (-2,-11) had 477
full-static support disagreements. Later scoped results are recorded below;
the remaining 541 segments are unmeasured.

The regional scenery apron first reduced the southern Seyda comparison from
477 to 69 support-status disagreements. Original reference 463188 had identical
63 rendered faces but 40 collision hit-presence disagreements in 588 rays:
the regional path retained the authored RootCollisionNode while the legacy
Seyda carrier omitted it. A CHIM-only supplement verifies the original NIF and
visual hashes, preserves carrier bytes and appends the original authored hulls.

The corrected Seyda frame now compiles with zero structural failures and passes
heap and zone-walk checks. Compared with the repaired regional frame, the same
boundary has zero full-static support-status disagreements across 2,816 samples
(5,632 queries); terrain and water controls also agree. Its complete stair gate
is unfinished: the parallel run exceeded its memory limit and was stopped by
out-of-memory termination. A passing boundary sample is not a complete stair,
combined-world, native or package pass.

The combined attempt then stopped at ownership validation before packing:
original kelp references, including 463098, were omitted from the Seyda frame.
These references are present in the original source carrier and absent from the
existing flora sprite receipt; a legacy dressing filter removed them. The next
source correction retains only the three known original kelp meshes 01/02/03,
binds additions to the original scenery index and leaves unrelated deferred
dressing unchanged. All 43 focused Seyda, town and ownership checks pass.
Compiled verification of this later correction, native checks and packaging
remain pending. The earlier source's running full suite does not certify it.
[Static seam](bugs/CHIM-FRAME-STATIC-SEAM-40.md) and
[boundary ownership](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).


## v0.0.41-dev1: ring3 feasibility after v0.0.40 delivery

Current work remains v0.0.40; no v0.0.41 version switch has begun.
Begin this expansion after the v0.0.40 playtest and matching source are delivered.
The 15 October tracker identifies 149 Vvardenfell ring3 cells. Seventeen already
lie within the current town ownership cores; none is an existing regional core.
The provisional extension therefore needs 132 regional frames: 129 currently
eligible by offline status and three held cells. Retaining the current frames
would give 501 frames before pocket and routing reconciliation. These are
feasibility counts, not new converted, native-checked or packaged coverage.

| Held ring3 cell | Retained failed checks |
| --- | --- |
| Ald Velothi (-11,15) | Hull-chain limit and memory fit; headroom -280,976 bytes |
| Ald Daedroth (11,20) | Hull-chain limit and memory fit; headroom -206,256 bytes |
| Tel Mora (13,14) | Memory fit; headroom -2,641,936 bytes |

Reassess those older per-cell findings on the next pinned source. Keep all holds
explicit; excluding a cell must also pass the enclosed-pocket check. Reuse the
existing original-cell selection, ownership/dependency records, palette, source
archives, compiled hulls, shared terrain and far horizon layer. Preserve separate
aprons and exclude replaced legacy terrain/scenery from compilation and payloads.
Resolve the current static seam before extending its boundary checks inward.

Across these 149 cells the original-reference accounting includes 8,430 statics,
4,511 flora, 63 activators, 1,308 containers, 62 doors, 16 items and 318 lights.
It separately defers 37 NPCs, 455 creature references and 280 meshless lights.
Flora placements do not by themselves establish their runtime conversion policy.
Retain original reference types, dependency copies and all unimplemented gameplay.
Solstheim is outside this ring3 scope. Revalidate compiled contact, memory,
stairs, horizons and both sides of each handover before native and package gates.

## v0.0.40 release scope - 15 October 2026

**v0.0.40: Rings 0, 1 and 2 of Vvardenfell in Full CHIM** is the selected title. Rings 0-2
are the complete planned CHIM conversion scope; other exterior cells retain the
legacy route except already converted CHIM towns. Door-entered interiors remain
independent. All 336 ring cells appear in the 435-cell spatial plan; that plan
is not a package manifest. The combined 369-frame world, preserved horizons,
original references, deferred features and adjacent visual/collision seams must
pass their gates before release. The combined conversion has passed; the later
source repair needs its own checks and compiled boundary verification. See
[coverage](chim/CELL_TRACKER.md) and
[ownership](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).

Public gameplay images must be actual AmiWind captures. Original-game reference
images remain private; the previous exception is removed and the export
regression passes. See [public image selection](bugs/PUBLIC-REFERENCE-SCREENSHOT-40.md).


Earlier source checkpoint, 15 October 2026: boundary ownership repair passed
37 focused checks and the source contract for all 369 frames. Combined-world
readback, split-model/sprite dependencies, seams, native gameplay and full
package gates remain pending. Converted, audited, native-checked and packaged
coverage retain their previous receipts.
[Ownership repair](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).


Scoped combat follow-up, 14 October 2026: Khajiit female physical ready movement
and stationary/strafe punches are positive controls. Keep the reported
[movement](bugs/PLAYER-READY-MOVEMENT-39.md) and
[attack](bugs/PLAYER-PUNCH-THIRDPERSON-39.md) cases open. Next acceptance work
must resolve the failing character/context and compare motion with the original;
these controls do not establish hit/damage or gait quality. Preserve the
[Seyda allocation retry](bugs/CHIM-CHUNK-LOAD-FAIL-33.md) separately from cell
conversion, inclusion and visual/collision coverage.

15 October 2026 terrain follow-up: original-spacing diamond topology and two
local LAND-detail repairs are integrated. Source coordinates and affected edges
agree; the dreamer contact issue remains open. The complete source gate now
passes with explicit skips and expected failures. Original ray measurements
are distinguished from rendered/contact triangles. Complete the original
foot-pose comparison, compiled contact and native cell/chunk
crossings before accepting rings 0-2 or packaging dev2. Existing conversion and
package counts remain separate and unchanged.
[Diagonals](bugs/CHIM-TERRAIN-DIAGONAL-40.md),
[contact](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).


- BUILD-PLAYER-BODY-BUDGET-FALLBACK-39 — 15 October 2026, v0.0.40-dev2:
  continue past reduced animation fits to seek full action sampling under
  unchanged geometry and memory guards. The canonical Argonian diagnostic
  fits122 frames; production and native verification remain pending.
  [Report](bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md).


v0.0.40-dev2 candidate preparation, 15 October 2026: the animation correction
passes 115 shared converter checks. Regenerated assets, full release gates and
shipment remain pending. [Candidate notes](RELEASE-v0.0.40-dev2.md).


Animation follow-up, 15 October 2026: the
[rotating-offset converter correction](bugs/NPC-ANIMATION-OFFSET-40.md)
has nine focused checks. Rebuild affected player bodies and compare gait,
limb shape, ready movement and combat before the next v0.0.40-dev2 inspection
candidate. Keep original-asset, native, packaging and shipment gates separate.
CHIM cell ownership and coverage are unchanged by this converter work.



Original gait reference, 14 October2026: Nord male/Barbarian/Steed controls now
cover physical lowered/ready W and Shift+W. Correct camera-eye/actor labels
before measuring movement. Resolve the measured eye-height residual and compare
actual speed/phase with current and v0.0.38 motion before closing
[gait](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md) or
[ready movement](bugs/PLAYER-READY-MOVEMENT-39.md). Head and scene differences
remain explicit; reference evidence is not repaired-game acceptance.


Nord gait follow-up, 14 October2026: physical ready walking and running have a
scoped positive control, with changing limb poses in retained original frames.
Complete the matched original and historical v0.0.38 motion comparison before
accepting [gait quality](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md). Keep the
[reported ready-movement failure](bugs/PLAYER-READY-MOVEMENT-39.md) and
[terrain allocation retries](bugs/CHIM-CHUNK-LOAD-FAIL-33.md) open; initial
blocked-endpoint controls are excluded and no cell coverage is promoted.


## v0.0.40-dev1 gameplay priority, 14 October 2026

The unreleased dev2 documentation rotates selected older journal entries before
adding further findings; keep the existing size guards and preserve archive
links in the next source export. [Tracker maintenance](bugs/TRACKER-REGISTER-SIZE-33.md).

Selected actual item lookup/icons and physical sword/shield equip are observed in native diagnostics. The exact later target/FPU and full suite pass; actual Nord steel-weapon/shield blocking credits two incoming blocks. Normal HUD Guard text is absent with target names retained, and live no-dice health/fatigue readouts are correct. Selected legacy Argonian held/released shield and fists-readied movement are scoped positive controls; closer pose, anatomy, jump/death, matched gait and all-appearance acceptance remain pending. [Catalogue](bugs/INVENTORY-CATALOG-LOOKUP-40.md), [blocking](bugs/COMBAT-BLOCKING-36.md), [HUD](bugs/HUD-STATS-29.md).

The selected dev1 body payload retains the previously packaged 122-frame
Argonian male and matching tags alongside nineteen current bodies, preserving
hit/death/jump sampling. Its legacy block holds a sample about 67 ms before the
authored hit, and current anatomy/quality limits remain open. Selected-payload native held/released shield and movement are observed;
closer pose, anatomy and jump/death checks remain pending. Do not infer
complete Argonian acceptance from Nord controls. [Body fitting](bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md).

The bounded dev1 gameplay inspection candidate is delivered. Continue dev2.
Dev2's primary objective is CHIM mapping for rings 0, 1 and 2, with separate
conversion, audit, native, packaging and acceptance records. The inventory
requirements below remain planned follow-up work.

CHIM static-mesh performance remains a measured dev2 audit even in already
mapped areas. Playtesting reports occasional exterior Dwemer FPS drops; exact
site/build/cause and measurements remain unknown, with no reproduced repair.
After selecting an exact scene, profile static meshes, visibility, transforms,
clipping, surface-cache/overdraw, server/collision and streaming costs separately.
Compare fixed pose and route with warp off and controlled settings, then preserve
original geometry/gameplay through matched OpenMW and native before/after checks.
Mapping alone does not establish an FPS budget, and an optimizer is not assumed
to fix the report. Rings 0, 1 and 2 remain dev2's primary objective.
[CHIM-VIEW-FACES-33](bugs/CHIM-VIEW-FACES-33.md).


Plan compact lookup tables for all original item identities, properties and
effects, with explicit support states and bounded on-demand resources. Preserve
original typed effect, enchantment/charge, equip/use and save semantics; do not
substitute default values for unsupported records. Current basic AWI2 rows and
ten selected asset pairs are incomplete: actual picked Luminous Russula resolves
name/count/weight/value but has no converted icon/model or admitted action.
Keep authoritative carried IDs, counts, condition and equipped state reliable.
Quest logic must query actual AW_ITEM inventory, not a hot-swap list or the UI's
visible rows. A bounded hotbar/equipped asset cache may stay resident for fast
use; other descriptors, icons and models load on demand. Full-catalogue lookup
coverage does not require full-catalogue residency. This is a cache plan, not
an implemented optimization or measured speed/memory saving.

Original UI textures must be derived from the locally supplied owned game
during conversion and excluded from public source. The fixed right-hand corner
must mirror the left border pattern, with no movable-window or resize control.
Interim authored placeholders do not establish original artwork parity.

Require original golden title/tab frames and font, with no movable-window
top-right corner decoration in the full-screen modal. Add actual carried-weight/
capacity and Armor-rating readouts from game state, plus a mouse-operable
vertical scrollbar on the right and keyboard navigation. These readouts and
visual refinements remain planned. The dev2 scrollbar source follow-up below
has focused automated checks; native acceptance remains pending.

Reserve an inset, readable bottom control/status area in inventory, with
enough vertical margin and wrapping to keep hints away from the screen edge and
item details. A new supplied image confirms crowded bottom hints; its exact
running binary is unverified. This spacing refinement and the original-style UI
features above remain planned, with actual native/reference checks required.
[UI-INVENTORY-LAYOUT-40](bugs/UI-INVENTORY-LAYOUT-40.md).

14 October post-dev1 source follow-up: inset inventory status/control rows and
literal Inventory heading pass executable bounds/actions and map/journal
checks. Target/native visual comparison, original plaque/artwork/pose and the
remaining inventory requirements stay pending; delivered dev1 is unchanged.

Add a persistent View option for item list versus icon grid, reusing the same
actual carried selection, category/filter/sort, equip/use/drop admission and
keyboard/mouse actions. Persisting a view must not duplicate inventory state
or change item ownership. This list/grid option remains planned follow-up.

Plan E or a double-click on the actual selected carried item to open its
context actions: equip/unequip, consume/use and read books or papers as the item
supports. Share the existing action admission and authoritative ownership state;
unsupported effects or reading paths must be labelled unavailable rather than
simulated. These expanded shortcuts/use/read actions are planned, not dev1
implementation.

Equipped items also require a thin golden outline. Dedicated original inventory
poses, the original inset black name plaque and camera parity remain planned;
none of these additions is implemented by this roadmap update.

The inventory title must read the literal "Inventory" in the original inset
black plaque/golden border. The planned attributes/stats panel uses the actual
player name as its header. Keep title content distinct from player identity;
these refinements remain planned and must follow the supplied original UI.

The planned dev2 [inventory follow-up](INVENTORY.md#next-inventory-pass-v0040-dev2-14-october-2026)
requires the actual race/sex/head/hair/clothing/equipment appearance, full original
item icons and original equip/use/drop, ownership, save and effect rules.
Drag-to-character equip/use, category/value/weight/item-stat sorting and filters,
a black full-screen paused backdrop, original golden borders, the original inset black
title plaque within the gold top border reading "Inventory" and a readable F10 console-font hover-detail variant remain
required. The preview posture still needs original-reference refinement; neither
that posture nor the inset plaque is implemented by this plan. The dedicated
original inventory pose (fixed time zero), rather than a rotated live idle,
remains required; selected male-Nord modal pause evidence is scoped. Minimize RAM
through compact item lookup tables (LUTs), on-demand disk
assets and measured cache/preview choices. Give inventory preparation an explicit
master-builder phase, monitor build/runtime performance, and keep the producer,
consumer and public source export synchronized. Plan a controlled MiniWind
`--inventory-test` scene with explicitly tracked original test items. The linked
inventory page owns the detailed requirements and verification gates. These
additions and the planned ring/town/seam expansion are not included in dev1.

Reconcile the three experimental quick-character expected failures under
[TEST-CENSUS-CONTRACTS-40](bugs/TEST-CENSUS-CONTRACTS-40.md): meaningful source
routing checks, supported debug aliases and direct-start documentation. Keep
these open contracts separate from native menu/gameplay acceptance; remove each
decorator only after its replacement passes. This follows the urgent physical
combat and inventory gates.


Spell follow-up: magicka use, shield effects, destruction types and player
casting animations remain required gameplay work. Inspect existing AmiQuake
projectile movement/collision, damage, particles and lighting before designing
new effects; compare spell costs, eligibility, delivery and effects against the
original. Reusable projectile machinery is not complete spell-system parity.
No spell implementation is included in this roadmap update.

The v0.0.40 exterior target is CHIM coverage of rings 0, 1 and 2, with every failed, held, partial or excluded cell explicit. The shipped v0.0.40-dev1 gameplay inspection candidate omitted the town-boundary/seam expansion; dev2 requires the approved original-cell ownership and full rings 0, 1 and 2. For each included CHIM maintainer, exclude its replaced legacy BSP29 map before compilation and from the final payload. Preserve independently selected interior formats and required nonduplicate dependencies; conversion/audit alone does not prove runtime inclusion. Adjacent-cell acceptance must cover shared border heights/coordinates, water and surface continuity, collision crossings in both directions, and unique edge-object ownership.

Keep a per-reference entrance ledger for converted CHIM cells: original location/type/destination, visible geometry, activation bank, configured target, actual packaged destination and native entry/return states. Reuse the existing unavailable-interior handler for registered entrances with deferred destinations. Actual interior implementation follows in the next pass. Resolve the six partial town overlaps in dev2 through the approved original-cell-aligned town ownership and complete reference-band conversion, with separate terrain aprons.

Ring 0 needs five runtime core owners and a compatible shared ocean terrain path before inclusion. Preserve four original deferred LEVC references. Plan outward grid-aligned CHIM town frames at Vivec x=1..6, y=-14..-9 and Seyda Neen x=-3..0, y=-11..-8; audit overlap ownership and boundaries before conversion. No frame expansion or new native coverage is implemented by this plan.

Movement parity: use the [source speed study](MOVEMENT_SPEED_STUDY.md) and [PLAYER-MOVEMENT-STATS-PARITY-39](bugs/PLAYER-MOVEMENT-STATS-PARITY-39.md). Next quantify forward walk/run/level-swim in matched scenes with effective stats, load/effects, race/sex, original race-speed setting and simulation time recorded. Then verify direction, readied states and save/load. Keep faithful gameplay and convenient fast debug policy distinct; no tuning or proposed maximum-stat option is implemented by the study.

The inventory's current safe placement boundary is plain BSP. Active CHIM,
captured scenery and restricted story contexts refuse drops and retain the
item; full-game CHIM/scenery placement is required next under
[UI-INVENTORY-INTEGRATION-40](bugs/UI-INVENTORY-INTEGRATION-40.md). Keep the
distinct limits visible: 32 carried IDs, 32 persistent ground records and 16
distinct new inventory model precaches per loaded level. Repeated models reuse
a slot and scene changes reset that cache. Expanding the model limit requires
explicit table-budget validation. Target compilation and selected native lookup,
physical equip and first-person RMB raising are observed. The repaired complete
suite, full native modal, third-person block pose, plain-BSP transfer/save/load
and CHIM-refusal gates remain pending.


Maintainer-published v0.0.39 source is commit
`751e1efa6b28e7fc58453fc81c73100715b88195`; the maintainer reports the same gameplay
in inspected RC2 and final. The current bounded priority is the renewed
[physical-LMB punch](bugs/PLAYER-PUNCH-THIRDPERSON-39.md),
[ready-state inability to move](bugs/PLAYER-READY-MOVEMENT-39.md),
[both-view blocking presentation](bugs/COMBAT-BLOCKING-36.md) and
[sinking/upright swim body](bugs/WATER-GAMEPLAY-PARITY-38.md) failures.

For punch acceptance captures, drain diagnostic commands before physical input
and avoid a wait/readout burst ahead of that input. A later state-2-only capture
is inconclusive because its wait/readout burst can defer physical LMB execution;
exact guest timing and Preview-specific suppression are unproven. Keep original footage and actual
state transitions with event timing. This is a measurement correction, not a
gameplay fix. [Punch record](bugs/PLAYER-PUNCH-THIRDPERSON-39.md).

Reproduce maintainer input/state first, repair the diagnosed paths, then check the
exact target and package with ordinary physical input, matched original views
and maintainer inspection. A successful Nord ready-movement or input/damage control
is scoped evidence; it does not accept the maintainer failure. Preserve good ready
posture, original shield eligibility and earlier historical receipts.

The requested `dbg characterchange` testing command is implemented in source:
it reuses the existing pier race/gender/head/hair appearance menu by default;
`all` selects the full quick-character page sequence. Two focused C/console
checks pass. Native Nord-male to Orc-female menu/confirmation/reopen and exact
engine readback pass. Story-registration restrictions remain in place. Package
and maintainer acceptance remain pending; it is a diagnostic aid,
with no gameplay repair claimed.
The new source race-testing shortcut dbg set race/playerrace accepts a strict
zero-based loaded ID or normalized race name, with no-value/list output for
IDs/names/current selection. The refined contract preserves stats/level/current
health, gender/name/class/birth and equipment while changing only validated
race/head/hair and live eye height. It reuses the existing character builder on
a temporary copy, without reapplying racial stats. A same-race request preserves
head/hair; another race selects its first valid gender-compatible pair.
Invalid/context-restricted changes are refused. Fourteen final focused checks
pass; new target/native/package verification remains pending, with no gameplay
repair inferred.
[Contract](CHARACTER_CREATION.md#diagnostic-race-shortcut-14-october-2026).
The complete candidate gate rejects a direct resident registration at270 versus
269commands (+32B). Reuse existing on-demand AWDC1 dbg routing without raising
the budget. Twenty focused actual character/console/catalogue/registry checks
pass after correction; new target/full-gate/native/package remain pending under
[ENGINE-RESIDENT-REGISTRY-GROWTH-36](bugs/ENGINE-RESIDENT-REGISTRY-GROWTH-36.md).

CHIM remains 360 whole cells plus six excluded partial overlaps; no new cell
coverage is established by this follow-up.

## Additional RC1 inspection findings, 13 October 2026

Vivec mushroom seams and missing swimming remain open. The maintainer also reports
coarse Nord/Khajiit third-person gait and an Ordinator appearance mismatch.
Five original screenshots were inspected and retained privately. No new cell
conversion, native coverage or packaged coverage follows from these reports.

- [MESH-VIVEC-CAP-GAP-38](bugs/MESH-VIVEC-CAP-GAP-38.md): Vivec giant mushroom cap has a visible opening.
- [NPC-ORDINATOR-APPEARANCE-39](bugs/NPC-ORDINATOR-APPEARANCE-39.md): Vivec Hlaalu Ordinator has an unhelmeted Fargoth-like appearance.
- [PLAYER-MOVEMENT-FRAME-SKIP-39](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation.
- [WATER-GAMEPLAY-PARITY-38](bugs/WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification.

## Release hold and RC2 request, 13 October 2026

Post-pin evidence, 14 October: exact RC2 package/readback and scoped Nord
punch/torch/water inspection passed; inspection artifacts were finalized at
2026-10-13T22:15:44Z. Final source packaging was authorized on 14 October; individual gameplay acceptance remains separate. Leg/seam,
fast-gait, actor/equipment, memory/streaming and wider gameplay acceptance remain
open in the [register](BUGS.md#fix-index). This continuation records observations
after the immutable RC2 source/package pin; it does not rewrite those artifacts.

The [spear-resident candidate](bugs/NPC-SPEAR-ATTACK-REGRESSION-39.md) now selects the authored attack from equipped weapon type; affected asset/native/package checks are pending.

RC2 update, 14 October: [third-person torch](bugs/PLAYER-TORCH-THIRDPERSON-38.md) has scoped native holding/movement evidence. All 20 [swim companions](bugs/WATER-GAMEPLAY-PARITY-38.md) are built and select in water; inherited idle sinking is repaired in source with target/reference checks pending. RC2 package/readback and scoped water checks have passed. Final packaging is authorized; CHIM coverage and individual maintainer acceptance are unchanged.

The maintainer stopped final preparation after RC1 playtest reports. RC2 must
address the third-person punch animation, reported Nord leg shape, recurring
NPC chase animation and guard spear-attack regression before final delivery.
Earlier RC1 release approval does not clear these newly reported blockers.
The canonical reports and corrected fatigue observation are linked below.

All 20 candidate body model/layout pairs now pass offline binary checks within
the unchanged 512 KiB limit, superseding the earlier incomplete bake set.
Possible knee/calf section gaps remain under
[PLAYER-BODY-LEG-SHAPE-39](bugs/PLAYER-BODY-LEG-SHAPE-39.md); numeric fitting does
not establish visible seams, gait, punch, memory or maintainer acceptance. Complete RC2 package readback and scoped native checks passed; wider visual acceptance remains open.

- [PLAYER-PUNCH-THIRDPERSON-39](bugs/PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation.
- [PLAYER-BODY-LEG-SHAPE-39](bugs/PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1.
- [NPC-SPEAR-ATTACK-REGRESSION-39](bugs/NPC-SPEAR-ATTACK-REGRESSION-39.md): Seyda Neen guard spear attack animation is missing in first-person view.
- [COMBAT-FATIGUE-HEALTH-DAMAGE-39](bugs/COMBAT-FATIGUE-HEALTH-DAMAGE-39.md): Clarify Eldafire bare-fist fatigue damage versus armed guard health damage.
- [NPC-NO-RUN-ANIM-35](bugs/NPC-NO-RUN-ANIM-35.md): Companions and hostile NPCs walk but never run, and the walk looks wrong: release residents had only idle frames.
- [ANIMKIT-COVERAGE-35](bugs/ANIMKIT-COVERAGE-35.md): NPCs that move or fight have no walk, run or attack animation: Fargoth and other Seyda Neen villagers glitch toward the player.

## v0.0.39 - Cell By Cell, Piece By Piece

v0.0.39 keeps the implemented RC1 scope: safer automatic checkpoints and death
UI, third-person jump and bare-hand ready/draw/lower source work, body budget
fallback, current help, sound cancellation and exclusive exterior ownership.
The maintainer initially approved RC1 on 13 October 2026, then stopped final
preparation and requested RC2 after the additional playtest reports above.
On 14 October the maintainer authorized the final release package from RC2.
Exact-source checks, image readback, native acceptance and publication remain
separate gates; only the agreed repair/diagnostic scope enters RC2.

The README map uses the sanitized 13 October 2026 reference snapshot.
Converted, audited, native-checked and packaged coverage remain separate;
planned or converted cells do not count as included. The [bug register](BUGS.md#fix-index)
retains all unresolved findings.

## Movement presets and all eight attributes, 13 October 2026

The maintainer requests faithful normal-game movement using original Speed, Athletics,
encumbrance and running-fatigue rules. Keep convenient fast, less strict debug
builds distinct: this report does not authorize silently slowing the current
debug preset. A proposed maxstats option would accept on/off, true/false and1/0.
The requested future maxstats/godmode speed extension would provide maximum debug
walking/running while enabled; disabling both would restore normal effective
values without destroying real character stats. These movement extensions are
not implemented; the existing godmode immunity toggle is separate. See
[PLAYER-MOVEMENT-STATS-PARITY-39](bugs/PLAYER-MOVEMENT-STATS-PARITY-39.md).
Movement and the [speed-linked body animation](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md)
need separate original/native comparisons and actual baked pose checks.

All eight attributes must eventually have their original gameplay effects:
Strength, Intelligence, Willpower, Agility, Speed, Endurance, Personality and Luck.
Require matched original shield-block balance/stagger/knockdown/recovery checks,
including return to control and distinct incoming weapon cases. A successful
block or raised shield alone does not establish those reactions. The applicable
original rule/formula still needs audit; this requirement adds no implementation
or native acceptance. See [COMBAT-BLOCKING-36](bugs/COMBAT-BLOCKING-36.md).

Maintain a mechanics matrix with original formula/settings, implemented consumers,
remaining unsupported rules, automated checks and native evidence for each.
Required coverage includes Strength for melee/carrying/fatigue; Intelligence
for magicka; Willpower for spell checks/fatigue; Agility for combat/balance/fatigue;
Speed for movement; Endurance for health progression/fatigue recovery; Personality
for disposition/persuasion; and Luck for the original skill-check modifiers.
Verify the original consumers and exceptions rather than applying one universal
bonus. Displaying or saving a stat is not proof that its gameplay effects are complete.
Reuse existing combat/stat consumers and Quake physics before adding new work;
this roadmap requirement does not claim new attribute implementation in RC2.

The requested [raw identity inspector](bugs/DBG-ENTITY-INSPECT-39.md) is a source
candidate to bind reports to entities/references. Its ordinary overlays remain
separate from click interception. Torch equipment and both-view swimming repeats
remain open; no broader mechanics acceptance follows from the RC1 inspection.

The latest maintainer instruction makes
[third-person torch holding](bugs/PLAYER-TORCH-THIRDPERSON-38.md) required for RC2.
Its source candidate is implemented; all 20 isolated companion bake/readbacks,
35 converter and 36 runtime focused checks pass. Fresh target/native, matched
original, complete image/package and maintainer checks remain pending. This supersedes
the earlier player-torch deferral.

## v0.0.40 - Unfinished work and new features

The maintainer's reported swimming/diving, gait and combat repairs are required for
RC2. Their source, matched original reference, native/package and maintainer gates
remain open; this future-feature milestone does not defer them. v0.0.40 retains
new extensions such as optional cloud/lava effects and terrain texture fidelity.
Existing open issues retain their IDs/evidence and require scoped acceptance;
no broad closure or new gameplay completion is claimed here.

## v0.0.38 - Lava Is All You Need (And A Hint Of Tel Uvirith)

v0.0.38 is published. Its full-world conversion includes both lava paths, all
27 lava-bearing exterior cells and the optimized completed-stage Tel Uvirith
stronghold in cell (10,1). The compact replacement passed exact RC1 HDF/package
readback, scoped native inspection and delivery. Final v0.0.39 retains that
implemented scope and requires its own final-source and image checks. See the
[release checklist](RELEASE-v0.0.38.md) for acceptance requirements and the
[bug register](BUGS.md) for current issue status.

The Toolkit's Included counts must come from verified package contents.
Conversion plans, passing offline checks and packaged coverage remain distinct.
Further coast coverage, gameplay repairs and measured streaming/cache work
continue after this release; they are not implied to be shipped in v0.0.38.

## v0.0.37 - Proofreading the Cantons (fix release)

The v0.0.36 release notes and README brought in line with the released code, and the logo images fixed. No
game change. Its earlier roadmap assigned a working title and broader feature
plans to v0.0.38; the release sections above supersede that assignment.
For real machines with lots of Fast RAM (first tester: A4000 with a 68060 accelerator),
adaptive cache sizing and non-blocking CHIM disk reads remain follow-up work;
the cache, prefetch and lookahead themselves exist already
([real hardware](REAL_HARDWARE.md)).
The proposed follow-up is adaptive CHIM caching and non-blocking world streaming: keep `-chimcache` as the manual
override; detect usable Fast RAM and grow the cache conservatively without touching the tested baseline heap (done
in v0.0.42-rc1: [memory guide](chim/build_guide/MEMORY.md#more-fast-ram-the-automatic-chim-cache)); count
cache hits, misses and evictions; and turn CHIM's blocking pack reads (`Chim_PackRead`,
[ENGINE-SYNC-IO-MAIN-LOOP-36](bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md)) into reads that complete in the background,
starting from the asynchronous music reader (`aw_aread.c`). A cache only makes a hit faster; only asynchronous reads
stop a miss from stalling a frame. The 2 MiB Chip + 16 MiB Fast machine stays a supported, tested fallback.

## v0.0.36 - 36 Lessons of Vivec's Cantons (And Vvardenfell Shorelines) (released)

v0.0.36 starts moving the open world onto CHIM inside the game itself. Converted areas sit inside
the legacy island, the border between the two is measured and made seamless, and CHIM takes over
cell by cell, from the sea and the coast inward. Draft notes: [release notes](RELEASE-v0.0.36.md).

Historical target: v0.0.36 = the whole coastline on CHIM (every cell of the outer ring and every passing cell of the second ring),
the open ocean placed in the game (one shared ocean chunk), the whole city of Vivec by default, and Seyda Neen and
Balmora. The earlier plan assigned every green zone on the map to v0.0.38.
That was a target, not a record of shipped coverage; use the release's package
evidence and the current coverage explanation above for actual inclusion.

Steps, each one a playtest build:

1. One CHIM block inside the legacy island (a 3 x 3 Bitter Coast area): the handover between CHIM
   and legacy land, the border audit ([STITCH_AUDIT.md](chim/STITCH_AUDIT.md)) and its fixes
   (shoreline detail, a terrain margin around the frame). Measured after the fixes: no height
   step and no gap on any edge of the test area.
2. The sea and the shoreline ring: the seabed cells, the open sea (one shared ocean chunk stored
   once) and the coastal cells, chosen as cell lists (region names, a CSV or JSON list, or a
   selection exported from the Toolkit's World Map). Their legacy region maps leave the image.
3. Vivec, which closes the ring on the south coast: the existing canton split as CHIM areas, with
   very large models cut into chunk-sized pieces and the densest meshes simplified. If Vivec is
   not ready in time, it moves to the next release instead of holding this one.

Measured on the way (10 October 2026): with shared terrain stored once and referenced by each cell
(`--chim-terrain-refs on`, with `--chim-terrain-hull compiled`; experimental, off by default), CHIM cells
in the open world take 0.91 to 0.93 times the bytes of the legacy maps they replace, where each cell's
own terrain copy took about 3.5 times. Cells the legacy builder split over several maps cannot switch
yet (CHIM-REGION-DIVIDED-CELLS-36).

World bounds (on by default, `--world-bounds off` to turn off; `dbg worldbounds` in game): a player who
swims or sails out past the island meets a sea current along the edge of the world and is pushed back, instead
of the invisible wall at the end of the outer maps; out of the water the push back works the same way, and the
edge moves out by itself as more cells join the world. Quake's own current, applied by position. The original
game has no such limit; this is an AmiWind addition ([WORLD_BOUNDS.md](WORLD_BOUNDS.md)).

Still to do along the way: buildings of a CHIM area appear only when the player crosses into it
(seen from legacy land the area shows its ground and rocks); harvestable plants in extra CHIM
areas; collision for thin underwater plants; and rebuild cascades in the builder.

Next, v0.0.38: all green zones. Every cell shown green (finished) on the CHIM Progress Tracker map, about 670 cells,
moves onto CHIM in the game and is tested there, with bug fixes along the way. The first item is the lava
stale-source fix (CHIMPORT-RETRY-LAVA-STALE-SOURCE-36). The tracker already shows this plan in pale gold.
Also for v0.0.38, from the maintainer's dev5 playtest: the NPC you are fighting must stay visible in third person
(CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36), and, longer term, blocking: NPCs block by their Block skill with a block animation, and the player
blocks with the right mouse button, with the companion pick on another key (COMBAT-BLOCKING-36; the original rules are
researched first).
Then the rest of the island follows the conversion spiral, ring by ring from the coast inward. Each ring gets the
same border checks and a playtest.

## v0.0.35 - CHIMporting It All: Gathering Up The Loose Branches From The Seashore (released)

v0.0.35 gathers in the work that was finished over the last releases but left on side
branches: builder improvements (resumable image step, unit caches and output hashes, a
shared storage pool, a build preflight, tighter reuse keys), lava, the CHIMport tracker
and more. Unfinished or experimental work ships behind a switch that is off by default.
Release notes: [RELEASE-v0.0.35.md](RELEASE-v0.0.35.md).

After v0.0.35, with no dates promised:

### Next: build system

**Very near term: a fast build system (11 October 2026, top priority after the current fixes).**

- Fast and parallel everywhere it is safe: no phase runs on one core while the others wait; any phase over 30 s below
  half of its core budget is flagged by the build itself.
- No useless runs and no re-runs: every step is computed once, recorded by the SHA-256 of its inputs, and reused by
  every build and every developer job; only what changed is computed again.
- Checks that have passed stay passed: the stair walk becomes a lookup of recorded results (walked again only when a
  frame's collision changes, with a small random spot check); smoke tests run on fuller builds when they are needed,
  not on every build.
- Every phase shows what it is doing and how long it took.

Build speed (10-11 October 2026): a rebuild should cost only what changed, and a first build should keep every core busy.
Every step keyed by the SHA-256 of its inputs and reused (stair walks, CHIM statistics per frame, image passes per map);
CHIM region frames prepared side by side; the worker pool resizes while it runs; side jobs back off during a release
build; no silent phases (start and end lines with timings, progress counters, a heartbeat; quiet only as an option);
honest per-phase time estimates; the live stage timeline in the Toolkit Monitor. Engine side: the float-to-integer
conversion overhead, the edge and clip code, then hand-written 68k routines where measurements point.

- One build tool with the stages described as a table, so a stage's inputs and outputs are
  declared once and checked by the builder.
- Smaller units of work for the slow stages (rooms, regions, image parts), each with its own
  content hash, so a change or a failure rebuilds only what it touches.
- One shared content store for every cache, with clear cache keys, and a checked build
  environment.
- A test harness and continuous checks that run the same way locally and on a second machine.

### Build pipeline speed (very near term, after Vivec)

A build should spend time only on what changed, and the first build should keep the whole machine busy. In order:

1. A world map manifest first. One list decides, for every map, CHIM or legacy before the first stage runs; every stage
   reads it. The image step's replace-in-place becomes a check that must find no legacy map of a CHIM cell
   (a v0.0.36 development build converted and optimized 270 such maps, 194.7 MB, and threw them out at the end).
2. Dead weight out: legacy maps of CHIM cells are neither built nor processed (a development build built 335 of them,
   65 Seyda Neen maps and 270 CHIM region cells, and removed them again before packing; this saves build time, not
   image size).
3. Every phase parallel: the image step (maps, audio, video), the statistics step and the optimizer, through the shared
   worker pool, with results identical for 1 and for 24 workers.
4. Incremental rebuilds by hash for every unit, and the optimizer cache key fixed so a small change redoes only its units.
5. No silent phases: verbose by default with a heartbeat, quiet only as an option.
6. One profiler (`tools/build_profile.py`): the timeline and the optimize sweep in one tool.
7. The Toolkit Monitor shows the activity of each phase.
8. Honest estimates: a time estimate is based on measured earlier runs and says how reliable it is.
9. A measured build that proves it: cores used per section, what was reused, and the time against the earlier build.

These problems are persisting, not resolved: several were found and fixed in part since 8 October 2026 and came back. Tracker: BUILD-PIPELINE-UNDERUTILIZATION-36, whose page indexes these as the eight build rules with every earlier entry, and the bugs linked from it.

### Perf, profiler and optimizer (future)

A better pipeline for finding and removing slow or idle build sections:

- A perf database of every run (stage times, cores used, what was reused, host load).
- Automatic detection of sections that leave cores idle, with each one turned into a tracker item automatically.
- Per-section core use in every build summary.
- Comparison across runs, so a slower section shows up at once.
- A CI or gate check on a benchmark build that fails on new underutilization.

### Next: CHIMport region by region, coast first

- The open world converted to CHIM region by region, from the sea and the coast inward, with
  live cell status in [docs/chim/CELL_TRACKER.md](chim/CELL_TRACKER.md).
- CHIM lighting: the terrain light bake (the "hybrid" lighting type is partial until then).
- Heightmap terrain collision: a prototype, measured first.

### Gameplay

- Implemented in published v0.0.38 source: saved noclip-only walking bob and
  movement roll, `dbg noclipwobble [on|off]` with alias `dbg noclipbob`, default
  **off** (`0` / `false`). It reuses AmiQuake's view-bob and roll paths in
  `view.c`; ordinary walking retains its existing behavior. Photo mode
  temporarily disables it and restores the previous setting. Preserve the
  existing off/on, normal-walking and photo-restoration checks in later builds;
  source presence alone does not establish native acceptance for a new image.

- Combat and companion leftovers: hit chance, block, voices, death animation and sound,
  first-person weapons.
- Background music: the `dbg music on/off` / `aw_music` switch already exists.
  The audio settings menu, saved setting and builder option remain follow-up
  work ([ENGINE-MUSIC-NO-OFF-SWITCH-36](bugs/ENGINE-MUSIC-NO-OFF-SWITCH-36.md)).
- More of Morrowind's animation groups wired ([ANIMKIT.md](ANIMKIT.md) lists them).
- Modular NPCs: a shared parts library converted once, with per-character recipes.
- A third-person view, following the original game's camera (the original and OpenMW as the references),
  which also gives the death scene its original look: the view leaves the player and fades out.
  In v0.0.36-dev: Tab, the held orbit, the wheel zoom, the vanity camera and the death camera with a stand-in
  body per race and sex ([THIRD_PERSON.md](THIRD_PERSON.md)). Next: the character's own head and hair, the
  worn clothes and armour, a jump group and smoother walk/run cycles.
- After a lost fight: the original's choices (load a save, main menu) plus an optional quick retry (in
  v0.0.36-dev: `--death-retry`, default on).
- The original's on-screen display, bottom corners (planned for a later version, agreed 10 October 2026;
  OpenMW frames as the reference): bottom left the player's health, magicka and fatigue bars, the equipped weapon box and the
  selected spell box; bottom right the local map with the player's arrow and the active magic effect icons.
  The original draws its local map live from the world; here the builder pre-draws one small map picture per
  exterior cell and per interior, and the engine shows the current one and turns the arrow. If that proves too
  heavy, a simple compass in the same frame replaces it (both kept selectable). Drawn with Quake's own status
  bar pictures, converted at build time from the maintainer's game data; memory measured against the town limits
  first.
  Layout: sizes and positions from OpenMW's HUD files, scaled to the AmiWind screen, A/B'd at the same pose.
- Waiting and resting with the original's rules (planned, 10 October 2026). Today **T** only moves the clock
  forward ([DIALOGUE_AND_WAIT.md](DIALOGUE_AND_WAIT.md)); nothing is restored while waiting. To be taken from the
  original's own rules (OpenMW's source, the game settings in the master file and the original's documentation),
  never invented: rest versus wait (where sleeping is allowed, enemies nearby, owned beds), what each restores per
  hour (health, magicka, fatigue) and from which attributes, what blocks it (for example a birthsign that stops
  magicka returning), what does not heal with time (diseases, blight), timed spell effects running out, sleep
  interrupted by a creature in the wilderness, and levelling up when sleeping. Each rule records its source.
  The study with numbers and sources: [WAIT_AND_REST.md](WAIT_AND_REST.md).
  Memory: nothing about where sleeping is allowed stays in memory. The builder writes one bit per exterior cell into a
  small table indexed by the cell's coordinates; pressing T reads the one byte that holds the current cell's bit from
  disk. An interior carries its flag in its own map, which is loaded anyway. Rare rule lookups in general follow the
  same pattern: coordinates to an index, read on demand.
- Living towns: every NPC that can move or fight gets walk, run, swim and attack animations (checked by the
  builder for every NPC), and residents follow their original Wander packages - strolling within their
  authored radius along the cells' path grids and playing their idles, as in the original.

### CHIM maps become their own format (approved 10 October 2026)

CHIM frame maps are named `.chim`, separately from legacy `.bsp` maps. Their
current shell still uses the BSP29 binary layout and decoder; the streamed
world already has its separate container format. The next format step remains
planned: a `.chim` gets its own header
(CHIM magic, map version, world format) and its own loader in the engine, a CHIM major-version step; then its
contents leave BSP29 one measured step at a time: entities as a compact binary table, no dummy BSP parts, no BSP29
limits where CHIM needs more, precomputed tables. An interior's format is
independent of exterior replacement and may remain BSP29 or move to CHIM. Design and
measurements: [.chim map format](chim/CHIM_MAP_FORMAT.md).

### Tiny squeezes: memory that stays resident

Small savings that add up, and a guard so they cannot grow back (10 October 2026; candidates with numbers in
[MEMORY_ALLOCATION.md](MEMORY_ALLOCATION.md)):

- A ratchet test: every command, setting and permanent name table the engine registers is counted with its exact
  byte cost against a committed budget. Growing past it fails the gate; moving something to disk lowers the budget
  for good. In place (ENGINE-RESIDENT-REGISTRY-GROWTH-36, `tests/test_resident_registry.py`); budget of 10
  October 2026: 266 commands (32 bytes each, 8,512 bytes of hunk) and 321 settings (7,704 bytes of structures and
  10,496 bytes of zone for their values).
- Console commands behind on-disk routes: the `dbg` names, aliases and help are already read from disk only when a
  command is submitted; most of the commands behind them can follow, leaving a few dispatchers per module (keys
  that are held, such as Tab, keep real commands).
- Rare rule lookups from disk: coordinates to an index, one byte read when the question comes up (where sleeping is
  allowed first, then similar rules).
- Disk-backed console history instead of the resident 16 KiB output ring.
- About 13 KB in Balmora's CHIM ring, so that exact building collision can be switched on for every model.

### Roadmap horizon: one partition with CHIM

With the whole island on CHIM, the whole game on one disk image, with the world in a single
partition. This is a horizon, not a promise for a release: the image stays as it is until the
whole island runs on CHIM. Details and measurements: [IMAGE_SIZE.md](IMAGE_SIZE.md).

The goal is one image file, not two. v0.0.36-dev3 ships as two image files (4,026,564,608 and 1,610,645,504 bytes, 5.25 GiB
together) with three world partitions (the system partition and one world partition on the first disk, two world partitions
on the second). Every partition is under 2 GiB and starts below 2 GiB, so the platform limits hold, but the target is not
met. One image of about 3.75 GiB means the payload must shrink by about 1.5 GiB. The path: dead weight out (see the
build pipeline section above, which saves build time, not image size), store-once CHIM for the open world, and a payload breakdown by kind printed by every image
summary so each kind has a visible budget:

| Kind | dev3 today | Budget for one image |
| --- | --- | --- |
| World maps (CHIM and legacy) | not yet measured per kind | to be set from the breakdown |
| Audio: voices (6,447 files) | not yet measured per kind | to be set from the breakdown |
| Audio: effects (717) and music (18) | not yet measured per kind | to be set from the breakdown |
| Video (17 files) | not yet measured per kind | to be set from the breakdown |
| Interiors | not yet measured per kind | to be set from the breakdown |
| Total | 5,637,210,112 bytes | about 3.75 GiB (4,026,531,840 bytes) |

Tracker: IMAGE-ONE-HDF-TARGET-36 and BUILD-PARTITION-GROWTH-UNGATED-36 (nothing gates the number of world partitions or the image size yet).

## v0.0.34 - CHIM: Tightening the Bolts (released)

A fix release on top of v0.0.33: the silt strider's hull is closed and every Bitter Coast
mushroom can be picked, each with an island-wide check that runs in every build
([release notes](RELEASE-v0.0.34.md)).

## v0.0.33 - Towards CHIM: Replacing the Engine Block (released)

v0.0.33 is out: the first release on the CHIM engine, the world streamer, with
Balmora and Seyda Neen on CHIM and the CHIM builder as the default
([release notes](RELEASE-v0.0.33.md); plan below and [world streamer](WORLD_STREAMER.md)).
The release before it, v0.0.32, was the last on the legacy engine
([release notes](RELEASE-v0.0.32.md)).
What CHIM is, its versions and milestones: [CHIM](chim/README.md); every
idea that is designed, measured or held back, with its status:
[CHIM ideas](chim/IDEAS.md).

Next: the animation kit for all character types, Vivec on CHIM and the CHIM open
world (milestones M3 and M4), with no dates promised.

The open world on CHIM started with v0.0.35 (above); live cell status in
[docs/chim/CELL_TRACKER.md](chim/CELL_TRACKER.md) (generated from the conversion tracker). A cell is only complete
when it is lit like the original: the [CHIM lights roadmap](chim/LIGHTING_ROADMAP.md) lists the lighting milestones
for this release and later (light tracker done; shared light entities and lightstyles; terrain lightmaps; a light
level per placed model; dynamic lights of every class; per-plant glow; later per-placement lightmaps for an
increased-memory version, shadows and interiors).

## v0.0.32 - Last Stop on the Old Line: Window-Shopping in Vivec (released)

v0.0.31 (Lamps, Lanterns and Loading) was out. v0.0.32 started with Vivec, built
by the generic town importer with no hand-building, and with fixes found by
measuring the whole island on 8 October 2026
([world progress](trackers/WORLD_PROGRESS.md), [bug register](BUGS.md)):

1. **Vivec first.** The Arena and the cantons through the normal doors, after
   the limits that block them: texture mappings read unsigned (32,767 to
   65,535, [VIVEC-TEXINFO-31](bugs/VIVEC-TEXINFO-31.md)), leaf face lists read
   unsigned ([MODEL-MARKSURF-SIGNED-31](bugs/MODEL-MARKSURF-SIGNED-31.md)),
   surface extents ([MESH-EXTENT-GRID-31](bugs/MESH-EXTENT-GRID-31.md)), the
   lightmap overrun ([LIGHTMAP-TAIL-31](bugs/LIGHTMAP-TAIL-31.md)), the night
   lamp cache ([LAMPS-CACHE-31](bugs/LAMPS-CACHE-31.md)) and interior
   coordinates ([INTERIOR-COORDS-31](bugs/INTERIOR-COORDS-31.md)).
2. **Real 68040 compatibility and speed.** The engine reaches FPU instructions
   the 68040 does not implement, every frame, and the boot disk loads no FPU
   support library; the emulator hides both
   ([ENGINE-FPU-UNIMPL-31](bugs/ENGINE-FPU-UNIMPL-31.md),
   [ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md)). Fixes reuse
   Quake's own answers: no rotation for unrotated brush models, table
   sine and cosine, work done once per frame.
3. **Distant shells.** Buildings far away drawn as closed low-poly shells
   instead of full meshes, so the town stays visible without its full cost
   (prototype on Balmora first).
4. **Your own estimate.** A builder command that estimates every map of the
   island from your own Morrowind files, shown as a layer on the Toolkit's
   World Map.

Before the v0.0.32 release (fix-before-release list):

- Visiting Vivec: `dbg tp vivec` takes you to the Vivec Arena preview (outside only;
  its doors do not open yet), and the release notes say so
  ([DEBUG-TP-TOWN-NAMES-32](bugs/DEBUG-TP-TOWN-NAMES-32.md), fixed in source).
- A from-scratch build with the repository builder reproduces the release payload,
  file by file, with the recorded Seyda Neen exception
  ([BUILD-WORLD-LAYOUT-DRIFT-32](bugs/BUILD-WORLD-LAYOUT-DRIFT-32.md) byte check
  included).
- No private-test waiver: the Arena residents pass the actor check or are left out
  ([VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md)).

### Decided: a world streamer with no duplicated assets - the whole game on one hard file

Keep the AmiQuake engine (renderer, lighting, collision, QuakeC) and change how
the open world is stored: every asset stored once and placed by reference, as
Morrowind itself does (its base game holds all meshes and textures in about
310 MB and the whole world in an 80 MB file), streamed around the player.

**Why.** Today every exterior region is a self-contained Quake map holding
everything visible from it, so each exterior object is stored about ten times
([WORLD-REGION-DUPLICATION-31](bugs/WORLD-REGION-DUPLICATION-31.md); Seyda Neen
24 times per face, Balmora 7 times, [sub-cell redundancy](SUBCELL_REDUNDANCY.md)).
Two towns and the terrain already take 4.8 GB; with today's pipeline the whole
game would need about 24 GB (15 legacy partitions), and the oversized regions
cause most heap failures. Quake's `vis` gives little outdoors
([town visibility](performance/TOWN-VISIBILITY.md)), so the new layout gives up
nothing it was providing.

**Measured result (8 October 2026, estimate built from the game's own data:
every unique mesh, collision hull and texture counted, light per placement
checked against real bakes; [asset census](ASSET_CENSUS.md),
[streamer design](WORLD_STREAMER.md)):**

| | Today's pipeline | World streamer |
| --- | ---: | ---: |
| Whole game, all files | about 24 GB | **about 1.75 GB** (a leaner layout 1.61 GB) |
| Legacy-safe drive images (under 4 GiB) | 8 | **1** (estimated; see the note below the table) |
| Every texture of the game | about 1.4 GB (a copy in every map) | **19 MB** (each stored once) |
| Island terrain | about 1.8 GB compiled | **17 MB** as a heightfield |
| Exterior model variants | 33,076 | **1,405** meshes (scale and tilt applied at run time) |
| Worst memory around the player | regions over the heap budget | **4.9 MB** with 256-unit chunks |
| Largest load while walking Balmora | 4.6 MB per region crossing | **0.8-1.4 MB** per chunk |

The non-map part of these totals (sound, music, video, the NPC gallery) is still
v0.0.31's, which covers two towns: the whole game's actors and voices will add to
it, so expect the hard file to be well over half full, but still one hard file.

The target is the whole game on one legacy-safe drive image (under 4 GiB, with
partitions under 2 GiB); two images is the absolute limit. Every file follows
classic FFS: files well under 2 GiB (asset packs of about 1 GiB at most, split
by area), names of at most 30 characters, few files per directory, packs
written last and whole in map order. The builder will check this layout.

**How it works:**

- **Asset packs** (Quake PAK files, split by area and stored in map order): each
  mesh, collision hull and texture once, one shared texture pool.
- **Chunks** (grain still to be measured; 256 units looked best on memory, larger
  chunks need fewer disk reads): each holds terrain (compiled per chunk first; a
  quantized heightfield built at load is a later optimisation, because collision
  then needs a new path) and a list of placements: which mesh, where, which
  way, how large, and a lighting record.
- **Scale and tilt at run time** for drawing; collision hulls stored once and
  expanded per placement at load.
- **Three lighting tiers:** terrain keeps its lightmaps; buildings, furniture
  and rocks get lightmaps per placement on shared geometry; flora and clutter
  get one light level each (outdoor objects already have no lightmaps today).
- **Memory:** a ring of chunks around the player inside draw distance, loaded
  ahead of you and released through Quake's cache (made able to move brush
  models); a loader process reads the disk while the game keeps drawing;
  coordinates re-centred as you travel so they stay within Quake's range.
- **Distance tiers** for the frame rate: full detail nearby, closed low-poly
  shells further out, the horizon beyond.
- **Interiors** stay legacy Quake maps behind doors in the first CHIM releases.
  Moving their pieces to shared placements later removes the 220-model limit, but
  then they also need the per-sector visibility lists outdoors needs, because
  placements are not culled by Quake's `vis`.

**Plan:**

1. **v0.0.32 - Last Stop on the Old Line: Window-Shopping in Vivec** (released, the last
   release on the legacy engine and builder, built from scratch): Vivec with today's format; the measurements behind the
   streamer (census done; renderer counters and a cycle-approximate emulator
   profile in progress); real 68040 safety (no library sine and cosine per
   frame, Quake-style number parsing, your own FPU support library if you have
   one); a map loader without temporary copies; one shared face builder with a
   validator; builder types: today's region pipeline kept as the "legacy"
   builder, CHIM as the new one (named, not numbered; CHIM has its own version).
2. **v0.0.33 - Towards CHIM: Replacing the Engine Block** (released, the first CHIM engine release): the streamer (CHIM builder and engine 0.1.0) on Balmora, Seyda Neen and the cells
   between them, measured against v0.0.31 on the same routes: worst frame time,
   bytes per crossing, memory peak, saves mid-stream.
3. **Next:** the south-west corridor (Seyda Neen, Pelagiad, Balmora, Vivec,
   Ebonheart exteriors), then the rest of the island release by release. CHIM 1.0
   is the release in which the whole island runs; expect months, not weeks. We
   are aiming for the whole island by Morrowind's 25th anniversary, 1 May 2027:
   an aim, not a promise.

Repository layout from v0.0.33 (decided 8 October 2026). CHIM is the same AmiQuake
engine growing a streamer, not a second engine, so the engine stays one tree:

- `engine/aga/src/` remains the one engine; CHIM's own code (model library, chunk
  loader, world shift) lives in `engine/aga/src/chim/` with small hooks in the
  Quake files. "Legacy" is the old code path, used whenever no CHIM data is
  present, and the v0.0.32 tag.
- `tools/chim/` holds the CHIM builder. The parts both builders use (model and
  texture conversion, BSP writing) move step by step into one shared package, so
  the legacy builder and CHIM call the same code rather than copies.
- `docs/chim/` holds the CHIM format, design, measurements and release notes.
- Licences stay clear per folder: the engine is GPLv2 (from Quake), the builder
  GPLv3.
- Existing files move only after v0.0.32 ships, in one restructure commit with
  `git mv` (history follows) and the path tests and release file list updated
  in the same commit. Until then CHIM work only adds new folders.

The open question is speed on a real 68040: every figure so far comes from the
emulator ([BENCH-JIT-PROFILE-32](bugs/BENCH-JIT-PROFILE-32.md)), so a small
benchmark for real accelerated A1200s is being prepared. How data streams
today: [DATA_STREAMING.md](DATA_STREAMING.md).

### Near future: fires and lava across the world

- **Fires everywhere.** The new hearth fire (flames shaped by each Morrowind
  emitter, a hot colour ramp and rising embers) reaches every fireplace,
  brazier, campfire and firepit as maps are rebuilt; each keeps its baked
  light, and Morrowind's flicker and pulse light flags become Quake light
  styles so the firelight flickers (cost measured on the 68040 first).
- **Lava fields** (Molag Amur and Sheogorad outdoors, and 59 interiors such as
  the Dagoth Ur facility, [lava census](LAVA.md)): Morrowind's lava pools
  converted to Quake liquid surfaces, which the engine already draws with an
  animated warp and full brightness, with lava contents (blood-red view tint
  and Morrowind's damage when entered) and a few embers rising from the surface.

Before building more of the world at scale: the [trackers](trackers/README.md)
(world progress, entities, points of interest), so nothing is left behind.

After that: lighting follow-ups, a battle-arena test room, then inventory,
character statistics, a map that reveals as you travel, and the heap option
below.

## Planned: heap size matched to the host machine, 7 October 2026

The game heap is a fixed 11 MiB. On the reference configuration a fully loaded
Seyda Neen sub-cell leaves only about 2.6 MB of it for cached models, so each
crossing evicts and re-reads actor models
([Seyda Neen performance](SEYDA_NEEN_PERFORMANCE.md)). Accelerated Amigas such
as an A1200 with a PiStorm32 Lite or a full 68060 board have far more Fast RAM
([hardware FAQ](FAQ.md#can-todays-heavily-upgraded-amigas-realistically-run-amiwind)).

Plan, measured before it is built:

1. Emulator test: more Fast RAM and a larger heap on the same Seyda Neen route.
   Continue only if evictions and crossing times improve clearly.
2. [x] Startup check: when much more Fast RAM is available, the game uses it by itself
   (maintainer, 16 October 2026: the benefits come automatically): a short notice in plain
   words says how much extra RAM was found and that it is being used for caches, with a key
   (M) to skip it for this start (the game then runs on the baseline). An Options setting
   (Extra RAM) turns it off for good; the engine falls back to no extra caches if the larger
   allocation fails. Done in v0.0.42-rc1 for the CHIM cache, the chunks kept after leaving
   them and the look-ahead, with no upper limit but the machine (one bank per memory region,
   each under 2 GiB); measured 17 October 2026 in FS-UAE, 16 MiB against 128 MiB: zone
   failures 625-655 and 288-312 to none, evictions on a Seyda Neen flight 487-550 to none,
   frame time unchanged within drift; 16 MiB takes nothing
   ([memory guide](chim/build_guide/MEMORY.md#more-fast-ram-the-automatic-chim-cache)).
   The game heap stays at its built size: a larger heap only feeds Quake's actor and sound
   cache, and step 1 (does it help the Seyda Neen crossing?) is not measured yet, so it
   stays manual (`-heapmb`).

The baseline does not change: AmiWind must stay playable on the reference
configuration with the 11 MiB heap. Memory budgets, release gates and
acceptance stay measured there, and nothing may depend on the larger heap.

### The cache plan: extra RAM spent on not doing work twice (16 October 2026)

Project decision, 16 October 2026: the baseline game keeps working on today's memory setup, and the game uses more
RAM when a machine has it, as caches. This extends the 11 October plan (adaptive CHIM caching and non-blocking world
streaming). Step zero exists already: the start arguments `-chimcache KIB` (shared models and textures kept across
map changes) and `-heapmb N` ([hardware guide](REAL_HARDWARE.md#more-fast-ram-the-memory-settings-that-exist-today));
they stay as the manual override when the sizing becomes automatic. The memory budgets that must fit (the CHIM zone gate) stay the same; a
16 MB machine plays exactly as today, a 128 MB card or a PiStorm plays smoother. At start-up the engine asks how
much fast RAM is free and sizes the caches from it; each gain is measured in the emulator, then on real hardware,
in order of expected gain:

1. A larger surface cache: Quake's lit surfaces rebuilt less often, a direct frame-rate gain.
2. [x] Streamed CHIM chunks, models and textures kept resident in a larger LRU cache (Quake's `Cache_*`), so ground
   already seen costs no disk reads. v0.0.42-rc1: the automatic CHIM cache banks (step 2 above); measured: no
   evictions and no failed loads where 16 MiB had hundreds.
3. [x] Prefetch further ahead: the next frames' chunks loaded before the edge is reached, seamless crossings on slow
   disks. v0.0.42-rc1: the look-ahead doubles from 8 MiB of cache and triples from 32 MiB; first-time ground
   still reads in the frame (worst frames 0.19-0.29 s on a flight in FS-UAE, against 0.22-0.36 s on 16 MiB):
   that needs reads that finish in the background.
4. Visited interiors kept in RAM: going back through a door needs no loading pause.
5. Read caching for the hard file: recently read blocks stay in memory.

## Other ideas and wildcards

Ideas worth keeping, not scheduled. They wait until the work they depend on
exists.

### Sky fading into the horizon

At its lowest points the sky should fade into a gradient, not end in a crude cut-out. This pairs with the sea skirt
being prototyped for the open ocean (off by default until the maintainer approves it): both fade into the same horizon colour.

### Sea skirt: the sea runs to the horizon

The sea runs to the horizon and fades into it: flat colour bands beyond the draw distance, going from the sea colour to
the horizon colour. Views over water from high places, such as Vivec's cantons, then show sea instead of a flat fog band.
Targeted at v0.0.36 if it is ready in time, otherwise first in v0.0.37.

### Weather: ash storms and blight winds

Morrowind's regions have their own weather, and two kinds define the land
around Red Mountain: ash storms and the red blight winds. Both belong in
AmiWind at some point, built from what the engine already has: the
[day and night sky](DAY_NIGHT_AND_SKY.md) layers with faster, darker clouds,
the distance fog pulled in close, a full-screen colour tint like the one Quake
uses under water and in lava (ash grey, blight red), and a capped stream of
wind-driven grit from Quake's particle system, plus the storm sound. Each
region keeps its Morrowind weather chances; the cost is measured on the 68040
before it ships.

### Long-term possibility: a reusable Amiga game engine

Underneath the Morrowind content, AmiWind is becoming a general open-world
toolkit for AGA Amigas, all GPL: streaming sub-cell worlds with bounded memory
and build-time memory budgets; a converter pipeline from large 3D scenes to
Quake BSP maps; glow, NPC floor lighting, emitter-shaped flames,
Quake-particle embers and warped liquids; menus, rebindable controls, a book
and journal reader, music streaming, saves, dialogue and first-person hands;
and headless emulator testing, a debugger harness and heap auditing.

Someone making their own Amiga RPG, dungeon crawler or adventure game could
start from this instead of from zero. The aim: document the engine and tools as
reusable on their own, separate from the Morrowind conversion, with a small
example project that uses no game data.

### Long-term possibility: an RTG display path

AGA stays the primary display, and the project's look is built around the Amiga's own OCS and AGA graphics
modes. On fast CPUs (a PiStorm, a Vampire, a quick 68060) the screen starts to take a real share of the frame,
and a graphics card screen could take the renderer's 8-bit chunky buffer as it is, without the chunky-to-planar
conversion AGA needs. Picasso96 also provides the CyberGraphX interface, so one path would serve both, and the
engine already carries an inherited, untested CyberGraphX path. The emulators' virtual graphics card (UAEgfx)
makes it testable without hardware. Possible scope: choose an RTG screen at startup when one is present (AGA
otherwise), the palette and double buffering, the HUD, menus and video, and a measured comparison with AGA. A
future path to look into, not a planned release item ([FAQ](FAQ.md#why-not-use-pistorm32-rtg-and-minigl)).

### Long-term possibility: Lua scripting

Game logic today runs in QuakeC (the engine's built-in script VM) plus C.
A small Lua interpreter could later carry quest, dialogue and event scripts
(Morrowind's own scripts translated at conversion time) and make AmiWind
moddable without recompiling. To be decided by measurement on the reference
Amiga: the interpreter's code and heap cost against the 11 MiB budget, script
speed on a 68040, and whether it replaces or complements QuakeC.

### From Quake Arena to Vivec Arena: two-Amiga 1v1 duels

Once the battle arena and its test fights work, two Amigas could fight each
other: a 1v1 player-versus-player arena under a new **Extras** entry in the
main menu.

- **Link options.** A null-modem serial cable between the two machines, or
  TCP/IP over a network: an A1200 can take a PCMCIA network card with a
  standard Amiga TCP/IP stack. A TCP/IP stack can also run over the same
  serial cable (SLIP/PPP), so one network layer could serve both; a raw
  serial path (through `serial.device`, or directly through the Amiga's UART)
  remains an option for the lowest latency.
- **Bandwidth is small.** A duel needs two players' positions, view angles and
  action events (attack, block, hit, dodge), sent 10-20 times a second: a few
  hundred bytes per second, well within a 19,200-baud serial link. Quake's own
  network protocol, which the engine source still carries, was designed for
  28.8k modems.
- **Fair results.** Combat follows the arena rules (Morrowind's hit chance,
  shown as dodges and parries). One machine decides each roll and sends the
  result, so both screens agree.
- **The venue.** Morrowind already has the right place: the Arena Pit in
  Vivec's Arena canton. Converted on its own, it makes a small, closed duel
  map: from Quake's arenas to Vivec's.
- **Scope.** Two players, the arena map, no world state. Both machines run the
  same AmiWind version and their own copy of the converted game data; only
  game state crosses the link.

## Older history

Roadmap entries from v0.0.29 and earlier (6 October 2026 and before) are in the
[roadmap history](ROADMAP_HISTORY.md).
