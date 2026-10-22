# Bug journal

_Last updated with AmiWind v0.0.47 (21 October 2026)._
_Last updated with AmiWind v0.0.47-dev2 (21 October 2026)._

<!-- contents start -->
## Contents

- [INTERIOR-PLACED-ITEMS-47: design of record, the shell baked and everything takeable as objects, 21 October 2026](#interior-placed-items-47-design-of-record-the-shell-baked-and-everything-takeable-as-objects-21-october-2026)
- [BUILD-CHIM-CELLS-PRIVATE-LIST-47 and CHIM-ACTOR-TABLE-OFF-IN-GAME-47 registered, 21 October 2026](#build-chim-cells-private-list-47-and-chim-actor-table-off-in-game-47-registered-21-october-2026)
- [BUILD-IMAGE-WORLD-READ-FRAMES-47: the v0.0.47-dev2 build's frame-read pool on 3 of 24 cores, 21 October 2026](#build-image-world-read-frames-47-the-v0047-dev2-builds-frame-read-pool-on-3-of-24-cores-21-october-2026)
- [BUILD-LAVA-TERRAIN-BUDGET-38 persisting: public default builds stop at world-scenery, 21 October 2026](#build-lava-terrain-budget-38-persisting-public-default-builds-stop-at-world-scenery-21-october-2026)
- [v0.0.47-dev1 build: the CHIM and image sections under half their cores, 21 October 2026](#v0047-dev1-build-the-chim-and-image-sections-under-half-their-cores-21-october-2026)
- [CHIM-DOCK-TERRAIN-SEAM-47: a pale sliver gap at a dock end, 21 October 2026](#chim-dock-terrain-seam-47-a-pale-sliver-gap-at-a-dock-end-21-october-2026)
- [CHIM-BC-TREE-PYRAMID-BOX-47: Bitter Coast trees drawn as a pyramid trunk with a floating box, 21 October 2026](#chim-bc-tree-pyramid-box-47-bitter-coast-trees-drawn-as-a-pyramid-trunk-with-a-floating-box-21-october-2026)
- [HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47: a tree sprite blocks the pick of some mushrooms, 21 October 2026](#harvest-seyda-tree-sprite-blocks-pick-47-a-tree-sprite-blocks-the-pick-of-some-mushrooms-21-october-2026)
- [BUILD-ACTOR-LIBRARY-MWAD-PATH-47: the v0.0.47-dev2 build stopped in the actor-library stage, 21 October 2026](#build-actor-library-mwad-path-47-the-v0047-dev2-build-stopped-in-the-actor-library-stage-21-october-2026)
- [BUILD-SPRITE-KEY-HASHLIB-47: the v0.0.47-dev1 build failed in its CHIM stage, 21 October 2026](#build-sprite-key-hashlib-47-the-v0047-dev1-build-failed-in-its-chim-stage-21-october-2026)
- [CHIM-ACTORS-TOWN-RETURN-EMPTY-47: a town frame never starts the type 1 window, 21 October 2026](#chim-actors-town-return-empty-47-a-town-frame-never-starts-the-type-1-window-21-october-2026)
- [CHIM-ACTORS-TOWN-RETURN-EMPTY-47: a town frame's own residents stay with it; the second cause found, 21 October 2026](#chim-actors-town-return-empty-47-a-town-frames-own-residents-stay-with-it-the-second-cause-found-21-october-2026)
- [BUILD-OPTION-RECORD-KEYS-STAGES-47: a new option entry no longer rebuilds stages that never read it, 21 October 2026](#build-option-record-keys-stages-47-a-new-option-entry-no-longer-rebuilds-stages-that-never-read-it-21-october-2026)
- [HARVEST-INTERIOR-PICK-47 found and fixed on a branch; INTERIOR-PLACED-ITEMS-47 and HARVEST-ORGANIC-PLANTS-47 registered, 21 October 2026](#harvest-interior-pick-47-found-and-fixed-on-a-branch-interior-placed-items-47-and-harvest-organic-plants-47-registered-21-october-2026)
- [GHOSTFENCE-NO-ANIMATION-46: the turbulent curtain is the default; dbg ghostfence on/off, 21 October 2026](#ghostfence-no-animation-46-the-turbulent-curtain-is-the-default-dbg-ghostfence-onoff-21-october-2026)
- [World format 0.11: the converter's own triangles generated too, 21 October 2026](#world-format-011-the-converters-own-triangles-generated-too-21-october-2026)
- [COMBAT-PURSUIT-SLOPE-STALL-46 fixed on a branch: actor steps follow walkable slopes, 21 October 2026](#combat-pursuit-slope-stall-46-fixed-on-a-branch-actor-steps-follow-walkable-slopes-21-october-2026)
- [World format 0.11: texture splits and water crossings generated too, 21 October 2026](#world-format-011-texture-splits-and-water-crossings-generated-too-21-october-2026)
- [World format 0.11: generated terrain records, off by default, 21 October 2026](#world-format-011-generated-terrain-records-off-by-default-21-october-2026)
- [World format 0.10: compact terrain records, off by default; CHIM-PLANE-TYPE-ALL-SLANTED-46 converter side measured, 21 October 2026](#world-format-010-compact-terrain-records-off-by-default-chim-plane-type-all-slanted-46-converter-side-measured-21-october-2026)
- [CHIM-PLACEMENT-MARGIN-COPIES-46: the reach index's reads, three variants priced, 21 October 2026](#chim-placement-margin-copies-46-the-reach-indexs-reads-three-variants-priced-21-october-2026)
- [CHIM-EXTERIOR-ACTORS-MISSING-46: the actor table, off by default, 21 October 2026](#chim-exterior-actors-missing-46-the-actor-table-off-by-default-21-october-2026)
- [CHIM-PLACEMENT-MARGIN-COPIES-46: world format 0.9 (reach references) written, off by default, 21 October 2026](#chim-placement-margin-copies-46-world-format-09-reach-references-written-off-by-default-21-october-2026)
- [CHIM-TILT-VARIANTS-SPLIT-33: world format 0.8 written, off by default, 21 October 2026](#chim-tilt-variants-split-33-world-format-08-written-off-by-default-21-october-2026)
- [COMBAT-CHASE-CHIM-STUCK-46 fixed on a branch: the spawn snap waits for the streamed ground, 21 October 2026](#combat-chase-chim-stuck-46-fixed-on-a-branch-the-spawn-snap-waits-for-the-streamed-ground-21-october-2026)
- [COMBAT-CHASE-CHIM-STUCK-46: the chase works; spawned actors without a baked ground float, 21 October 2026](#combat-chase-chim-stuck-46-the-chase-works-spawned-actors-without-a-baked-ground-float-21-october-2026)
- [CHIM-STAIR-COLLISION-MESH-47: default builds keep their keys, an exact box in the check, 21 October 2026](#chim-stair-collision-mesh-47-default-builds-keep-their-keys-an-exact-box-in-the-check-21-october-2026)
- [CHIM-STAIR-COLLISION-MESH-47: walkways and seams, 21 October 2026](#chim-stair-collision-mesh-47-walkways-and-seams-21-october-2026)
- [NPC-STORY-DISABLED-AT-START-42: the start script's disabled actors, off by default, 21 October 2026](#npc-story-disabled-at-start-42-the-start-scripts-disabled-actors-off-by-default-21-october-2026)
- [CHIM-COMPILED-HULL-OVERFILL-46: cause found, edge bevels measured, 21 October 2026](#chim-compiled-hull-overfill-46-cause-found-edge-bevels-measured-21-october-2026)
- [CHIM-STAIR-COLLISION-MESH-47: the stair check calibrated against the recorded walks, 21 October 2026](#chim-stair-collision-mesh-47-the-stair-check-calibrated-against-the-recorded-walks-21-october-2026)
- [CHIM-STAIR-COLLISION-MESH-47: stair collision method 1, a stairway collision mesh, 20 October 2026](#chim-stair-collision-mesh-47-stair-collision-method-1-a-stairway-collision-mesh-20-october-2026)
- [CHIM-COMPILED-HULL-OVERFILL-46: compiled model hulls solid outside their pieces, 21 October 2026](#chim-compiled-hull-overfill-46-compiled-model-hulls-solid-outside-their-pieces-21-october-2026)
- [ENGINE-STRICT-WARNINGS-36 persisting: the engine's warning level raised, 20 October 2026](#engine-strict-warnings-36-persisting-the-engines-warning-level-raised-20-october-2026)
- [CHIM-PLACEMENT-MARGIN-COPIES-46 and CHIM-TILT-VARIANTS-SPLIT-33: what the frame segments hold, 20 October 2026](#chim-placement-margin-copies-46-and-chim-tilt-variants-split-33-what-the-frame-segments-hold-20-october-2026)
- [CHIM-HULL-SURFACE-HEAP-46: the walkway collision fix put six frames over the CHIM zone, 20 October 2026](#chim-hull-surface-heap-46-the-walkway-collision-fix-put-six-frames-over-the-chim-zone-20-october-2026)
- [BUILD-STAIR-WALK-BRUTE-FORCE-46: collision from what the game already knows, 20 October 2026](#build-stair-walk-brute-force-46-collision-from-what-the-game-already-knows-20-october-2026)
- [BUILD-HEAP-GATE-AFTER-STAIRS-46 and BUILD-CHIM-MAIN-MEMORY-46 registered, 20 October 2026](#build-heap-gate-after-stairs-46-and-build-chim-main-memory-46-registered-20-october-2026)
- [TESTS-HEAD-REDUCER-BYTES-CI-45 persisting: the NPC bake follows the processor's linear algebra kernel, 20 October 2026](#tests-head-reducer-bytes-ci-45-persisting-the-npc-bake-follows-the-processors-linear-algebra-kernel-20-october-2026)
- [BUILD-REUSE-PLAN-ENV-36 persisting: the standalone reuse plan keyed stages with an empty environment, 20 October 2026](#build-reuse-plan-env-36-persisting-the-standalone-reuse-plan-keyed-stages-with-an-empty-environment-20-october-2026)
- [TRACKER-REGISTER-SIZE-33 and TRACKER-REGISTER-SIZE-36: the archive split by version range, 20 October 2026](#tracker-register-size-33-and-tracker-register-size-36-the-archive-split-by-version-range-20-october-2026)
- [BUILD-SIZE-GUARD-OLD-BASELINE-45: the size guard compared v0.0.45 with v0.0.41, 20 October 2026](#build-size-guard-old-baseline-45-the-size-guard-compared-v0045-with-v0041-20-october-2026)
- [BUILD-REUSE-SCHEDULER-TOP-45 part 2: walks keyed by the data they walk, preflight stops scheduling-only rebuilds, 20 October 2026](#build-reuse-scheduler-top-45-part-2-walks-keyed-by-the-data-they-walk-preflight-stops-scheduling-only-rebuilds-20-october-2026)
- [MESH-EBONHEART-DRAGON-PEDESTAL-42: the game drops a root node's translation, 20 October 2026](#mesh-ebonheart-dragon-pedestal-42-the-game-drops-a-root-nodes-translation-20-october-2026)
- [SKY-REDMOUNTAIN-BLUE-44: region weather, 20 October 2026](#sky-redmountain-blue-44-region-weather-20-october-2026)
- [BUILD-REUSE-SCHEDULER-TOP-45: a scheduler-only edit rekeyed the gallery and the stair walks, 19 October 2026](#build-reuse-scheduler-top-45-a-scheduler-only-edit-rekeyed-the-gallery-and-the-stair-walks-19-october-2026)
- [CHIM-ROCKS-OPEN-SHELLS-43: island-wide rock sweep finds no converter cause, 19 October 2026](#chim-rocks-open-shells-43-island-wide-rock-sweep-finds-no-converter-cause-19-october-2026)
- [TRACKER-CHIM-COUNT-STALE-44: the tracker counted audits, not the build, 19 October 2026](#tracker-chim-count-stale-44-the-tracker-counted-audits-not-the-build-19-october-2026)
- [INTERIOR-MORAG-TONG-FPS-43: every room installer copies its plant sprites, 19 October 2026](#interior-morag-tong-fps-43-every-room-installer-copies-its-plant-sprites-19-october-2026)
- [BUILD-CHIM-SERIAL-SECTIONS-44: causes and repair; BUILD-IMAGE-STAIR-WALK-CORES-43 and BUILD-REUSE-KEYS-TOO-BROAD-35, 19 October 2026](#build-chim-serial-sections-44-causes-and-repair-build-image-stair-walk-cores-43-and-build-reuse-keys-too-broad-35-19-october-2026)
- [NPC-HEAD-DECIMATION-33: the player body falls back to the previous head reducer, 19 October 2026](#npc-head-decimation-33-the-player-body-falls-back-to-the-previous-head-reducer-19-october-2026)
- [CHIM-ROCKS-OPEN-SHELLS-43 and CHIM-CROSSING-SLUGGISH-43 registered, 19 October 2026](#chim-rocks-open-shells-43-and-chim-crossing-sluggish-43-registered-19-october-2026)
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43: two Bitter Coast frames over the heap zone, 19 October 2026](#chim-bittercoast-heap-shapeguard-43-two-bitter-coast-frames-over-the-heap-zone-19-october-2026)
- [CHIM-CROSSING-SYNC-LOAD-43 and ENGINE-HEAP-FIXED-SIZE-43: the open-world pauses measured, 18 October 2026](#chim-crossing-sync-load-43-and-engine-heap-fixed-size-43-the-open-world-pauses-measured-18-october-2026)
- [NPC-HEAD-DECIMATION-33 locked head reducer and INTERIOR-MORAG-TONG-FPS-43 decided, 18 October 2026](#npc-head-decimation-33-locked-head-reducer-and-interior-morag-tong-fps-43-decided-18-october-2026)
- [INTERIOR-MORAG-TONG-FPS-43 and NPC-HEAD-DECIMATION-33 persisting, 18 October 2026](#interior-morag-tong-fps-43-and-npc-head-decimation-33-persisting-18-october-2026)
- [VIVEC-ARENA-WATER-FALL-32: the sea to the horizon without the day/night sky, 18 October 2026](#vivec-arena-water-fall-32-the-sea-to-the-horizon-without-the-daynight-sky-18-october-2026)
- [COLLISION-NC-FLAGS-32: editor markers, 18 October 2026](#collision-nc-flags-32-editor-markers-18-october-2026)
- [CHIM-AZURA-FLOATING-FLORA-43 cause found and CHIM-AZURA-DWEMER-RUIN-SHAPES-43 measured, 18 October 2026](#chim-azura-floating-flora-43-cause-found-and-chim-azura-dwemer-ruin-shapes-43-measured-18-october-2026)
- [BUILD-IMAGE-STAIR-WALK-CORES-43, 18 October 2026](#build-image-stair-walk-cores-43-18-october-2026)
- [CHIM-OCEAN-CELL-RECORD-ROUTING-43, 18 October 2026](#chim-ocean-cell-record-routing-43-18-october-2026)
- [BUILD-STAGE-ALLOWANCE-STUCK-43 and BUILD-CHIM-REGION-FRAMES-TAIL-43: causes and repair, 18 October 2026](#build-stage-allowance-stuck-43-and-build-chim-region-frames-tail-43-causes-and-repair-18-october-2026)
- [BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43, 18 October 2026](#build-image-all-chim-preflight-43-18-october-2026)
- [CHIM-VIVEC-DOCK-WALKWAY-43, 18 October 2026](#chim-vivec-dock-walkway-43-18-october-2026)
- [ENGINE-HEAP-FIXED-SIZE-43, 18 October 2026](#engine-heap-fixed-size-43-18-october-2026)
- [CHIM-TERRAIN-TEXTURE-BLOCKY-43, 18 October 2026](#chim-terrain-texture-blocky-43-18-october-2026)
- [BUILD-STAGE-ALLOWANCE-STUCK-43, 18 October 2026](#build-stage-allowance-stuck-43-18-october-2026)
- [MESH-MUCKSPUNGE-SEAM-43, 18 October 2026](#mesh-muckspunge-seam-43-18-october-2026)
- [CHIM-AZURA-DWEMER-RUIN-SHAPES-43, 18 October 2026](#chim-azura-dwemer-ruin-shapes-43-18-october-2026)
- [CHIM-AZURA-FLOATING-FLORA-43, 18 October 2026](#chim-azura-floating-flora-43-18-october-2026)
- [INTERIOR-MORAG-TONG-FPS-43, 18 October 2026](#interior-morag-tong-fps-43-18-october-2026)
- [BUILD-CHIM-REGION-FRAMES-TAIL-43, 18 October 2026](#build-chim-region-frames-tail-43-18-october-2026)
- [CHIM-RED-MOUNTAIN-SOLID-SKY-43: cause and repair, 18 October 2026](#chim-red-mountain-solid-sky-43-cause-and-repair-18-october-2026)
- [CHIM-RED-MOUNTAIN-SOLID-SKY-43, 18 October 2026](#chim-red-mountain-solid-sky-43-18-october-2026)
- [OPENING-JIUB-LANTERN-32 persisting, 18 October 2026](#opening-jiub-lantern-32-persisting-18-october-2026)
- [TRACKER-REGISTER-SIZE-33: journal rotation, 18 October 2026](#tracker-register-size-33-journal-rotation-18-october-2026)
- [CHIM-STAIR-STEPS-SOLID-43 repaired in the converter, 18 October 2026](#chim-stair-steps-solid-43-repaired-in-the-converter-18-october-2026)
- [BUILD-IMAGE-REGION-MAPS-SERIAL-43 and BUILD-PASS-KEY-TOP-BROAD-43, 18 October 2026](#build-image-region-maps-serial-43-and-build-pass-key-top-broad-43-18-october-2026)
- [CHIM-BALMORA-INSET-SLIVERS-43 and CHIM-OCEAN-CELL-RECORD-CLASSIC-43, 18 October 2026](#chim-balmora-inset-slivers-43-and-chim-ocean-cell-record-classic-43-18-october-2026)
- [CHIM-HULL-ROUTE-NO-CUT-43 and CHIM-STAIR-STEPS-SOLID-43, 18 October 2026](#chim-hull-route-no-cut-43-and-chim-stair-steps-solid-43-18-october-2026)
- [CHIM-REGION-SEABED-NO-HEIGHTS-42 fixed, 17 October 2026](#chim-region-seabed-no-heights-42-fixed-17-october-2026)
- [UI-INVENTORY-FONT-TABS-42, 17 October 2026](#ui-inventory-font-tabs-42-17-october-2026)
- [BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42 and BUILD-CHIM-STAIR-NO-REUSE-42, 17 October 2026](#build-chim-stair-jobs-at-launch-42-and-build-chim-stair-no-reuse-42-17-october-2026)
- [BUILD-SCHEDULER-MEMORY-STARVED-42, 17 October 2026](#build-scheduler-memory-starved-42-17-october-2026)
- [SKY-STAR-TWINKLE-LATE-42, 17 October 2026](#sky-star-twinkle-late-42-17-october-2026)
- [NPC-DREAMER-GREETING-DEFAULT-42, 17 October 2026](#npc-dreamer-greeting-default-42-17-october-2026)
- [NPC-STORY-DISABLED-AT-START-42, 17 October 2026](#npc-story-disabled-at-start-42-17-october-2026)
- [NOCLIP-BOB-DEFAULT-42, 17 October 2026](#noclip-bob-default-42-17-october-2026)
- [CHIM-ZONE-RELEASE-FLICKER-42, 17 October 2026](#chim-zone-release-flicker-42-17-october-2026)
- [MESH-EBONHEART-DRAGON-PEDESTAL-42, 17 October 2026](#mesh-ebonheart-dragon-pedestal-42-17-october-2026)
- [BUILD-TORCH-CREATURE-RESIDENT-42, 17 October 2026](#build-torch-creature-resident-42-17-october-2026)
- [VIVEC-ROOM-PRECACHE-LIMIT-42, 17 October 2026](#vivec-room-precache-limit-42-17-october-2026)
- [BUILD-CHIM-VIS-VARIANT-SORT-42, 17 October 2026](#build-chim-vis-variant-sort-42-17-october-2026)
- [NIGHT-WINDOWS-LOST-CHIM-36, 17 October 2026](#night-windows-lost-chim-36-17-october-2026)
- [UI-INVENTORY-PREVIEW-STILL-42, 17 October 2026](#ui-inventory-preview-still-42-17-october-2026)
- [UI-INVENTORY-PREVIEW-GAP-41, 17 October 2026](#ui-inventory-preview-gap-41-17-october-2026)
- [UI-INVENTORY-ORIGINAL-LAYOUT-42, 17 October 2026](#ui-inventory-original-layout-42-17-october-2026)
- [UI-WINDOW-TITLE-BAR-42 and UI-INVENTORY-HEADING-CENTRE-42, 17 October 2026](#ui-window-title-bar-42-and-ui-inventory-heading-centre-42-17-october-2026)
- [HUD-STATS-29: original weapon and magic boxes, 17 October 2026](#hud-stats-29-original-weapon-and-magic-boxes-17-october-2026)
- [UI-ICONS-INVENTORY-42, 17 October 2026](#ui-icons-inventory-42-17-october-2026)
- [CHIMport by weight: tracker headroom and seabed cells, 17 October 2026](#chimport-by-weight-tracker-headroom-and-seabed-cells-17-october-2026)
- [ENGINE-060-MUL64-41, 17 October 2026](#engine-060-mul64-41-17-october-2026)
- [FPU-SUPPORT-MMULIB-SETPATCH-41, 17 October 2026](#fpu-support-mmulib-setpatch-41-17-october-2026)
- [BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42, 17 October 2026](#build-profile-reaped-child-double-count-42-17-october-2026)
- [SKY-FLAT-PALETTE-DRIFT-41: palette-matched cloud sky, 17 October 2026](#sky-flat-palette-drift-41-palette-matched-cloud-sky-17-october-2026)
- [SKY-FLAT-PALETTE-DRIFT-41, 17 October 2026](#sky-flat-palette-drift-41-17-october-2026)
- [Register audit: open means open, 16 October 2026](#register-audit-open-means-open-16-october-2026)
- [BUILD-STAIR-GATE-OOM-42, 17 October 2026](#build-stair-gate-oom-42-17-october-2026)
- [INTERIOR-SPAWN-UNDERWATER-41, 17 October 2026](#interior-spawn-underwater-41-17-october-2026)

<!-- contents end -->

## INTERIOR-PLACED-ITEMS-47: design of record, the shell baked and everything takeable as objects, 21 October 2026

[INTERIOR-PLACED-ITEMS-47](bugs/INTERIOR-PLACED-ITEMS-47.md): decided for the project, 21 October 2026: an interior is
a baked shell (walls, floors, stairs, fixed furniture and fixtures) plus a per-room table of objects for everything that
can be taken, moved or opened (items, books, bottles, weapons on racks, containers and their contents, ingredients),
each its own Quake entity lit from the baked lightmap, its state kept per room in the save. Measured first: takeable
objects per room. Order: interiors, then object and container state, then the compiled game logic. The report's title
is widened to match.

## BUILD-CHIM-CELLS-PRIVATE-LIST-47 and CHIM-ACTOR-TABLE-OFF-IN-GAME-47 registered, 21 October 2026

[BUILD-CHIM-CELLS-PRIVATE-LIST-47](bugs/BUILD-CHIM-CELLS-PRIVATE-LIST-47.md), persisting since v0.0.36: every release
image was built with a CHIM cell list kept outside the source tree, and `--chim-regions` was off by default, so a
public build put no exterior cell on CHIM (the path of [BUILD-LAVA-TERRAIN-BUDGET-38](bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md)).
Fixed on branch v0.0.47-chim-cells: `config/chim-cells.json` (every exterior cell, 1,409) is the default of a full
CHIM build; the plan resolves the same 1,348 region cells as v0.0.47-dev2; `--chim-regions none` keeps the earlier
default. [CHIM-ACTOR-TABLE-OFF-IN-GAME-47](bugs/CHIM-ACTOR-TABLE-OFF-IN-GAME-47.md): v0.0.47-dev2 ships the actor
table, but the engine reads it only with `chim actors table 1`, which no shipped config sets; being fixed on branch
v0.0.47-defaults.
## BUILD-IMAGE-WORLD-READ-FRAMES-47: the v0.0.47-dev2 build's frame-read pool on 3 of 24 cores, 21 October 2026

[BUILD-IMAGE-WORLD-READ-FRAMES-47](bugs/BUILD-IMAGE-WORLD-READ-FRAMES-47.md) (new): the image step's CHIM world read
failed the perf guard of the v0.0.47-dev2 build (try 3): `_read_frames_task`, 91 units, 102 s on 2.96 of 24 cores
(the phase 1 m 55 s at 2.7 cores; the same phase in the dev1 build took 13.0 s). A single group measured read-only
on the stored world takes at most 3.5 s of CPU, so the 23 "running" units on 2.0 cores were waiting: either on file
reads that every worker repeats, or on the parent receiving about 1.5 GB of results. Not isolated yet; the plan on the
page starts with per-unit wall, CPU and byte counts in the phase log. Reported again with these numbers on
[BUILD-IMAGE-UNDERUSED-32](bugs/BUILD-IMAGE-UNDERUSED-32.md) and
[BUILD-CHIM-SERIAL-SECTIONS-44](bugs/BUILD-CHIM-SERIAL-SECTIONS-44.md). No code changed.

## BUILD-LAVA-TERRAIN-BUDGET-38 persisting: public default builds stop at world-scenery, 21 October 2026

[BUILD-LAVA-TERRAIN-BUDGET-38](bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md): a tester's default build from the public
repository (19 October, v0.0.43) stopped at the end of the world-scenery stage with 7 regions over the 4 MiB storage
cap. Reproduced on 21 October with the v0.0.46 tree: same seven regions, the same bytes. The project's builds put
these cells on CHIM, so nothing measured them as BSP29 regions. Repaired with eleven refinement splits (the seven
plus four regions within 5 % of the cap); both open-world stages pass from scratch with the default options, and the
scan is recorded in config/world-region-budget-scan.json with a test that ties it to the refinement table.

## v0.0.47-dev1 build: the CHIM and image sections under half their cores, 21 October 2026

The build summary of the v0.0.47-dev1 build (try 2, 41 minutes) listed `underused:chim` six times, `underused:image`
four times and the perf guard failure of the body bake. Read against the register:

- [BUILD-BODY-BAKE-SLOWER-44](bugs/BUILD-BODY-BAKE-SLOWER-44.md) (reported again, 137 s against 92 s, the host not
  busy): cause measured. A player body bake spent 4.5 of 10 s inverting the same small matrices again for every texel
  sample; fixed in source on branch v0.0.47-build-cores with identical output bytes (SHA-256 of three bakes of two
  real bodies) and 2 to 2.8 times faster bakes. The bodies that fall back to the previous head reducer (six in this
  build) bake up to twice as often: plan on the page.
- [BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47](bugs/BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47.md) (new): the image step
  parses the 694 MB `chim-source.json` three times on one core (payload preflight 16.0 s and 18.5 s, region frame map
  task preparation 17.1 s); parsed once per process on the branch, outputs identical.
- [BUILD-CHIM-SERIAL-SECTIONS-44](bugs/BUILD-CHIM-SERIAL-SECTIONS-44.md) (reported again): the pack (1 m 28 s on one
  core, serial because ids are handed out in walk order), source and receipt (40 s at 2.05 cores), stats (41 s at 1.34)
  and an early stall (6.6 cores with 1,270 units queued); plan on the page.
- [BUILD-IMAGE-UNDERUSED-32](bugs/BUILD-IMAGE-UNDERUSED-32.md), [BUILD-IMAGE-REGION-MAPS-SERIAL-43](bugs/BUILD-IMAGE-REGION-MAPS-SERIAL-43.md)
  and [BUILD-STATS-SERIAL-36](bugs/BUILD-STATS-SERIAL-36.md) (reported again with this build's numbers).
## CHIM-DOCK-TERRAIN-SEAM-47: a pale sliver gap at a dock end, 21 October 2026

[CHIM-DOCK-TERRAIN-SEAM-47](bugs/CHIM-DOCK-TERRAIN-SEAM-47.md): the maintainer, playing v0.0.47-dev1, saw a pale
sliver where the dock end `x/ex_de_docks_end@s1` (cell -5,-6, Bitter Coast) meets the ground. He guessed the lowered
polycount; the cause is not established. Registered open; the island-wide extent of dock-to-terrain gaps is not
measured.

## CHIM-BC-TREE-PYRAMID-BOX-47: Bitter Coast trees drawn as a pyramid trunk with a floating box, 21 October 2026

[CHIM-BC-TREE-PYRAMID-BOX-47](bugs/CHIM-BC-TREE-PYRAMID-BOX-47.md): the maintainer reported the `flora_bc_tree` family
at three spots in v0.0.47-dev1 (`_01` once, `_04` twice, including Hla Oad). The reduced meshes keep 16 % (`_04`) to
31 % (`_01`) of the original triangles; the cause of the flat crown is not established. Direction decided for the
project: crossed vertical planes with the tree's outline (angle impostors as the alternative), A/B against the
current look and the original game first.

## HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47: a tree sprite blocks the pick of some mushrooms, 21 October 2026

[HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47](bugs/HARVEST-SEYDA-TREE-SPRITE-BLOCKS-PICK-47.md): in the Seyda Neen region
some mushrooms cannot be picked because a tree sprite stands in the pick. Cause unknown; the first check is whether
the pick trace counts the sprite's box or its collision as a blocker. Registered open; no position pinned yet.
## BUILD-ACTOR-LIBRARY-MWAD-PATH-47: the v0.0.47-dev2 build stopped in the actor-library stage, 21 October 2026

[BUILD-ACTOR-LIBRARY-MWAD-PATH-47](bugs/BUILD-ACTOR-LIBRARY-MWAD-PATH-47.md): run as a script, `tools/actor_library.py`
found `tools/mwad.py` instead of the `src/mwad` package; the first real build with the actor table stopped there.
`src/` now goes ahead of `tools/`, as in `chim_build.py`, and a test runs the script the way the build does.

## BUILD-SPRITE-KEY-HASHLIB-47: the v0.0.47-dev1 build failed in its CHIM stage, 21 October 2026

[BUILD-SPRITE-KEY-HASHLIB-47](bugs/BUILD-SPRITE-KEY-HASHLIB-47.md): `sprite_key` in `tools/visual_recipes.py` used
`hashlib` without importing it (added with the CHIM unit code keys on 20 October); the CHIM stage failed after
45 minutes on the first mesh with a sprite recipe. Fixed with the import and a test that calls the function; a sweep
of tools/ and src/ found no other standard module used without an import.
## CHIM-ACTORS-TOWN-RETURN-EMPTY-47: a town frame never starts the type 1 window, 21 October 2026

[CHIM-ACTORS-TOWN-RETURN-EMPTY-47](bugs/CHIM-ACTORS-TOWN-RETURN-EMPTY-47.md): the second cause fixed on branch
v0.0.47-save-changes, decided for the project, 21 October 2026: a frame whose cell has no region map (a town's)
never becomes the window's home frame, so crossings into and out of towns stay level changes, as Seyda Neen's do; the
open world between towns keeps the window. A window that keeps a town as its home frame is a follow-up with an
in-game route check. Experimental settings only (`chim crossing 1`).

## CHIM-ACTORS-TOWN-RETURN-EMPTY-47: a town frame's own residents stay with it; the second cause found, 21 October 2026

[CHIM-ACTORS-TOWN-RETURN-EMPTY-47](bugs/CHIM-ACTORS-TOWN-RETURN-EMPTY-47.md): two causes, read from the console of the
save check. A town frame covers several cells, and the type 1 window released its residents in the cells beside its
own at once; fixed on branch v0.0.47-save-changes (the home map's own actors stay while the home frame or their
cell's frame is in the window; native test). Not fixed: a town frame that starts the window leaves it when the player
arrives at the town's edge, and a town frame never joins a window again, so the town stays empty until a level change
into its core. Experimental settings only (`chim crossing 1`, `chim actors table 1`).

## BUILD-OPTION-RECORD-KEYS-STAGES-47: a new option entry no longer rebuilds stages that never read it, 21 October 2026

[BUILD-OPTION-RECORD-KEYS-STAGES-47](bugs/BUILD-OPTION-RECORD-KEYS-STAGES-47.md): each new entry in
config/option-changes.json rekeyed the chim, town, world-flora, engine and image stages of a default build: their
keys counted every file of config/, through a function default (`config_dir=ROOT / 'config'` in
tools/map_engine_limits.py) and a loop name bound twice (tools/build_aga.py, three named debug catalogues). Fixed in
source on branch v0.0.47-option-keys, not shipped at the time of writing: a path default names its files only for
its own function, and loop reads name only the listed files. No default stage is keyed on the file now; a one-time
rekey of those stages (they drop files they never read); CHIM unit, gallery, image pass and stair record keys
unchanged.
## HARVEST-INTERIOR-PICK-47 found and fixed on a branch; INTERIOR-PLACED-ITEMS-47 and HARVEST-ORGANIC-PLANTS-47 registered, 21 October 2026

[HARVEST-INTERIOR-PICK-47](bugs/HARVEST-INTERIOR-PICK-47.md): in the v0.0.46 image a mushroom inside an interior is
drawn but cannot be picked (checked in game in Addamasartus; an outdoor pick on the Seyda Neen shore stays picked
across the cave visit, a return and a quicksave and quickload). The harvest step read only the exterior placements,
so no interior map got a catalogue. Fixed in source on v0.0.47-interior-picks: interior mushrooms get their room's
catalogue on the same global index as the world's (one pick state, save format unchanged), default on,
`--harvest-interiors off` keeps the old behaviour; on the v0.0.46 maps 305 mushrooms in 8 shipped interiors, every map
within the runtime bounds and the heap check. Not built yet.
[INTERIOR-PLACED-ITEMS-47](bugs/INTERIOR-PLACED-ITEMS-47.md): placed items, ingredients included, are left out of
every converted interior (2,581 placed ingredients in interiors, 294 in shipped rooms).
[HARVEST-ORGANIC-PLANTS-47](bugs/HARVEST-ORGANIC-PLANTS-47.md): only the small mushrooms are harvestable; 934 of
21,238 outdoor organic plants and none of 3,725 interior ones can be picked.

## GHOSTFENCE-NO-ANIMATION-46: the turbulent curtain is the default; dbg ghostfence on/off, 21 October 2026

[GHOSTFENCE-NO-ANIMATION-46](bugs/GHOSTFENCE-NO-ANIMATION-46.md): decided for the project, 21 October 2026: a build draws shapes whose texture scrolls in
the original (the Ghostfence curtain, the Vivec waterfalls, the ash mire) as Quake turbulent textures by default;
`--chim-uv-scroll off` keeps the still texture of before. New in-game switch `dbg ghostfence on/off`
(`aw_ghostfence`, default on, not saved): off draws every turbulent texture straight and still, also the water of
the interiors. Only models with a scrolling texture get a new unit key. First seen in a full build with
v0.0.47-dev1.
## World format 0.11: the converter's own triangles generated too, 21 October 2026

The 0.11 generator (still experimental and off) now also makes the records of the converter's own triangles
(shoreline and 32-unit detail tiles) from the chunk's 32-unit samples and the triangles, stored as record version 2.
On the v0.0.46 world 95,818 of 97,369 terrain records are generated (was 83,236), every tenth of each kind checked
through the engine's generator byte for byte, and the terrain records would go from 489.4 MB to 247.6 MB. Not
generated yet: 563 lava records, 886 too large for the engine's loading buffer, and 100 whose texture mappings
differ.

## COMBAT-PURSUIT-SLOPE-STALL-46 fixed on a branch: actor steps follow walkable slopes, 21 October 2026

[COMBAT-PURSUIT-SLOPE-STALL-46](bugs/COMBAT-PURSUIT-SLOPE-STALL-46.md): an actor's trial step was refused when it
moved more than a stair height (8.75 units); on a walkable 0.90 slope a full step moves 10.6. The allowance now
grows with the slope of the floor under the step; a ledge is still refused. The pursuer followed the player down
the slope and kept fighting.
## World format 0.11: texture splits and water crossings generated too, 21 October 2026

The 0.11 generator (still experimental and off) now also makes the ground polygons the builder cuts where their
texture span passes 240 texels and where the water line crosses a tile: on the v0.0.46 world 83,236 of 97,369 terrain
records are generated (was 77,020), every tenth checked through the engine's generator byte for byte, and the
terrain records would go from 489.4 MB to 298.5 MB. Not generated yet: the 13,284 records holding the converter's own
triangles, 738 lava-bed and shore records, and 183 others.

## World format 0.11: generated terrain records, off by default, 21 October 2026

World format 0.11 is in the source behind `--chim-terrain-pack generate` (experimental, off; needs terrain
references): a regular-path terrain record stored as its corner heights and a few decided facts, from which the engine
generates the render part of the chunk, the same bytes as the stored record. The planes and the standing hull stay
stored (the hull is qbsp's compiled union). Host tests only; on the v0.0.46 world 77,020 of 97,369 terrain records are
generated, every tenth of them checked through the engine's generator byte for byte, and the terrain records would
go from 489.4 MB to 310.4 MB. The shoreline, lava and converter-triangle records are not generated yet.

## World format 0.10: compact terrain records, off by default; CHIM-PLANE-TYPE-ALL-SLANTED-46 converter side measured, 21 October 2026

World format 0.10 is in the source behind `--chim-terrain-pack compact` (experimental, off; needs terrain
references): a terrain record stored as a lossless repack that the engine expands to the same BSP29 bytes before
loading it. Host tests only; on the v0.0.46 world every terrain record expands back byte for byte, and the terrain
records would go from 489.4 MB to 450.8 MB. The earlier estimate of 83.5 MB assumed more axial planes than there are:
85 % of the terrain planes are slanted. For [CHIM-PLANE-TYPE-ALL-SLANTED-46](bugs/CHIM-PLANE-TYPE-ALL-SLANTED-46.md):
planes with a negative axis normal are 0.65 % of the terrain planes and 3.3 % of the model planes; flipping them in the
builder is not done (it changes content and on-plane ties for little), pending an in-game gain of the loader's fix.

## CHIM-PLACEMENT-MARGIN-COPIES-46: the reach index's reads, three variants priced, 21 October 2026

[CHIM-PLACEMENT-MARGIN-COPIES-46](bugs/CHIM-PLACEMENT-MARGIN-COPIES-46.md): world format 0.9's reach references
read about twice as often as 0.8's copies. Three variants were priced on the same zone walks (one read for records
and references, owner chunks loaded before the chunks that reference them, whole copies where the owner chunk is usually
absent): none reads as seldom as 0.8 copies while saving bytes. 0.8 copies stay the recommended form; 0.9 stays
experimental and off. No code changed.

## CHIM-EXTERIOR-ACTORS-MISSING-46: the actor table, off by default, 21 October 2026

[CHIM-EXTERIOR-ACTORS-MISSING-46](bugs/CHIM-EXTERIOR-ACTORS-MISSING-46.md): the actor table is in the source behind
`--chim-actor-table on` (experimental, off): every exterior NPC and creature reference of the game data in one
table outside the frames (5,981 references, about 197 KB on the v0.0.46 data), and the type 1 window takes a
joining cell's actors from it with `chim actors table 1`. Host tests only. Only the 90 living town residents have a model
to spawn; the other NPCs, every creature and the levelled creature lists still need models and list resolution:
the bug stays open. Also measured for
[CHIM-PLACEMENT-MARGIN-COPIES-46](bugs/CHIM-PLACEMENT-MARGIN-COPIES-46.md): a 0.9 reach reference finds its owner
chunk's catalogue in the zone 42 % to 45 % of the time; 0.9 reads about 10 % fewer bytes but about twice as often.

## CHIM-PLACEMENT-MARGIN-COPIES-46: world format 0.9 (reach references) written, off by default, 21 October 2026

[CHIM-PLACEMENT-MARGIN-COPIES-46](bugs/CHIM-PLACEMENT-MARGIN-COPIES-46.md): world format 0.9 is in the source
behind `--chim-reach-index refs` (experimental, off; needs `--chim-placement-format 0.8`): a chunk that a
placement's drawn box reaches but does not own holds a 4-byte reference to the owner record in the same frame
instead of a whole copy. Host tests only: every chunk holds the same records as in 0.8 once the references are
resolved, the engine builds the same catalogue and collides the same, a default build is byte for byte as before.
Estimated on the v0.0.46 world: placement records 60.9 MB in 0.8 to 28.8 MB in 0.9; when the owner chunk is not in
the zone, reading a chunk's catalogue takes more reads. A placement is still stored once per frame, not once for
the island (about 3.5 frames per object): the bug stays open. Not built and not seen in game yet.

## CHIM-TILT-VARIANTS-SPLIT-33: world format 0.8 written, off by default, 21 October 2026

[CHIM-TILT-VARIANTS-SPLIT-33](bugs/CHIM-TILT-VARIANTS-SPLIT-33.md): world format 0.8 is in the source behind
`--chim-placement-format 0.8` (experimental, off): one model per mesh and scale, the whole rotation in a 56-byte
placement record, collision from the mesh's own convex pieces expanded by the world-aligned player box when a trace
meets them (which also removes [CHIM-YAW-PLAYER-BOX-TURNS-46](bugs/CHIM-YAW-PLAYER-BOX-TURNS-46.md) in such a
world). Host tests only: the same drawn vertices as 0.7, collision equal to the exact shape on every test trace, and
a default build byte for byte as before. Estimated on the v0.0.46 world: 32,714 models become 8,105, about 455 MB
less. Not built and not seen in game yet; both bugs stay open.

## COMBAT-CHASE-CHIM-STUCK-46 fixed on a branch: the spawn snap waits for the streamed ground, 21 October 2026

[COMBAT-CHASE-CHIM-STUCK-46](bugs/COMBAT-CHASE-CHIM-STUCK-46.md): the snap ran once at the spawn, before CHIM had
streamed the collision under the actor. A miss is now retried once a second until the ground is there; test residents
landed within three seconds and the pursuer chased the player over a frame border.

## COMBAT-CHASE-CHIM-STUCK-46: the chase works; spawned actors without a baked ground float, 21 October 2026

[COMBAT-CHASE-CHIM-STUCK-46](bugs/COMBAT-CHASE-CHIM-STUCK-46.md): narrowed the same day. A resident standing on the
ground chased the player over a frame border and back. The failures were a ledge in Balmora (the player dropped off
it; fleeing is the rule) and test residents standing a few units above the ground: the spawn floor snap did not put
them down on the CHIM ground, so they could not step. Residents with a builder-baked ground point are not affected.

## CHIM-STAIR-COLLISION-MESH-47: default builds keep their keys, an exact box in the check, 21 October 2026

[CHIM-STAIR-COLLISION-MESH-47](bugs/CHIM-STAIR-COLLISION-MESH-47.md): method 1 now runs in its own mesh worker and unit
kind, so the shared converter modules hold none of its code and a default build's mesh units keep the code keys they
had before method 1 (its first version had rekeyed four unit kinds). The stair check places the standing box exactly
(the pieces grown by the box); it agrees with the recorded walks on 97.9 % of the tread points they covered. Method 1
now changes 14 meshes and cannot fix 11.

## CHIM-STAIR-COLLISION-MESH-47: walkways and seams, 21 October 2026

[CHIM-STAIR-COLLISION-MESH-47](bugs/CHIM-STAIR-COLLISION-MESH-47.md): rope bridges, docks and boards are walkways in
stair collision method 1 (sloped plates along their boards instead of a block per board); the stair check follows
the standing box across every seam between treads. On the v0.0.46 release build's meshes method 1 now changes 11
meshes at +0.6 % collision bytes on them (it was +30 %); 19 meshes it cannot fix keep today's collision.

## NPC-STORY-DISABLED-AT-START-42: the start script's disabled actors, off by default, 21 October 2026

[NPC-STORY-DISABLED-AT-START-42](bugs/NPC-STORY-DISABLED-AT-START-42.md): the builder can now read the actors the
original's start script disables at a new game from the game data (78: 58 NPCs, 20 creatures), and with
`--start-disabled original` the resident stages leave them out. On the v0.0.46 release build that would remove 11
placed references: four Dreamers (two around Seyda Neen, one in Balmora, one in Vivec), the Dreamer Prophet and six
quest characters. The twelve Dreamers' enable rule (journal `A2_2_6thHouse` == 50) is read from their own script.
AmiWind does not run that journal stage yet, so a left-out actor would never come back: the default stays `placed`
(as before) until the runtime enable exists.
## CHIM-COMPILED-HULL-OVERFILL-46: cause found, edge bevels measured, 21 October 2026

[CHIM-COMPILED-HULL-OVERFILL-46](bugs/CHIM-COMPILED-HULL-OVERFILL-46.md): not the compiler. The models' standing
hulls are their pieces expanded without edge bevels: on the worst rocks the stored hull and that expansion classify
7,965 to 8,000 of 8,000 sample points alike, and a fresh qbsp compile of the same pieces has no extra solid. A new
builder option, `--chim-model-bevels exact` or `tol:N`, adds the bevels, off by default: over the models of every
frame's heap peak it grows the hull planes from 3.2 to 3.9 million (tol:4) or 5.8 million (exact) and puts 8 to 40
frames over the CHIM zone budget. The placed collision method of the next world format holds the exact shape
without storing the planes.

## CHIM-STAIR-COLLISION-MESH-47: the stair check calibrated against the recorded walks, 21 October 2026

[CHIM-STAIR-COLLISION-MESH-47](bugs/CHIM-STAIR-COLLISION-MESH-47.md): the geometric stair check now places the
standing box over each tread point. Compared, without walking, with the stair walks the v0.0.46 release build
recorded: on the 2,896 tread points those walks covered it agrees on 2,846 (98.3 %); the walks covered 8.6 % of the
tread points. Method 1 now climbs flights with one ramp per run of steps between landings, and a build with it gates
on the check. It changes 15 of 97 flight meshes at +30 % collision bytes on them; 14 it cannot fix yet.

## CHIM-STAIR-COLLISION-MESH-47: stair collision method 1, a stairway collision mesh, 20 October 2026

[CHIM-STAIR-COLLISION-MESH-47](bugs/CHIM-STAIR-COLLISION-MESH-47.md): method 1 beside today's stair collision, off by
default: a flight whose collision fails a geometric check (stand height against the drawn tread, slope, standing
room, rise between neighbouring points; plane arithmetic, no walk) gets one ramp or one block per tread. Measured on
the v0.0.46 release build's meshes: 24 of 97 flight meshes made walkable by it (29 flights), 46 already pass, 27
still fail and keep today's collision; +7.9 % collision bytes on the 24 changed meshes. Not in game yet.
## CHIM-COMPILED-HULL-OVERFILL-46: compiled model hulls solid outside their pieces, 21 October 2026

[CHIM-COMPILED-HULL-OVERFILL-46](bugs/CHIM-COMPILED-HULL-OVERFILL-46.md): measured while checking the placed
collision method on the real collision pieces of the v0.0.46 world's heaviest meshes. The stored compiled standing
hulls are solid in 0.7 to 0.9 % of the sampled volume where the exact expansion of their own pieces is free (up to
82 units from the nearest piece, mostly in open air), and 703 of 45,000 traces on tilted variants change between hit
and miss. Stored hulls that are plain piece chains match exactly. The placed method matches the exact expansion on
44,950 of the 45,000 traces. Not seen in game yet.

## ENGINE-STRICT-WARNINGS-36 persisting: the engine's warning level raised, 20 October 2026

[ENGINE-STRICT-WARNINGS-36](bugs/ENGINE-STRICT-WARNINGS-36.md) (PERSISTING since v0.0.36-dev3, 11 October 2026;
raised again by an outside review of v0.0.46): the gate still built with `-Wall -Wno-unused`. Measured on v0.0.46
over every engine variant: 451 warnings with `-Wall -Wextra`, 4,068 with a strict set, and 35 printf format
mismatches once the printf-like functions carry the format attribute. Real faults fixed: a `double` printed with
`%d`, two texts passed as the format, a float compared with the integer `abs()`, and unsigned screen-size
comparisons that filled the whole row for an off-screen rectangle or dropped text starting left of the screen.
The gate level is now `-Wall -Wextra` for every file and stricter for AmiWind's own; warning flags alone leave the
engine byte-identical. Branch v0.0.47-strict-warnings, not yet merged.
## CHIM-PLACEMENT-MARGIN-COPIES-46 and CHIM-TILT-VARIANTS-SPLIT-33: what the frame segments hold, 20 October 2026

[CHIM-PLACEMENT-MARGIN-COPIES-46](bugs/CHIM-PLACEMENT-MARGIN-COPIES-46.md): the v0.0.46 release world's 1,315 MB of
frame segments, read record by record: models 736 MB, terrain 489 MB, chunk records 80 MB, textures 2 MB. Every
object's placement record is stored in 3.55 frames on average (the region frame margins) plus 619,074 reach copies:
52 MB for 132,369 objects. [CHIM-TILT-VARIANTS-SPLIT-33](bugs/CHIM-TILT-VARIANTS-SPLIT-33.md) persists: 32,714
stored models come from 1,400 meshes; one copy per mesh would be about 57 MB of drawn geometry.

## CHIM-HULL-SURFACE-HEAP-46: the walkway collision fix put six frames over the CHIM zone, 20 October 2026

The v0.0.46-dev1 build stopped at its CHIM heap gate: six frames over the zone by 31 to 175 KB. Measured with the
problem cells and their neighbours built alone: the walkway fix (CHIM-VIVEC-DOCK-WALKWAY-43) gave every piece of its
484 meshes the hull of all its points, so every rock corner became a plane, a node and clipnodes in every scaled
copy; with that rule off the frames match v0.0.45. Repaired in the shared converter: the pieces hold only their
walkable surface, faces the stair rules leave deep become plates, scaled copies of collision-free flora are merged,
and one Daedric ruin collides with coarser pieces. All six frames fit (19 to 177 KB headroom); the full build is next.

## BUILD-STAIR-WALK-BRUTE-FORCE-46: collision from what the game already knows, 20 October 2026

[BUILD-STAIR-WALK-BRUTE-FORCE-46](bugs/BUILD-STAIR-WALK-BRUTE-FORCE-46.md): a full build walks about 1.5 million
steps to rediscover what the game data and movement rules already say; nine earlier entries since v0.0.36 made the
walks cheaper without asking why they were needed. Decided: a second collision method from the game data, A/B
against today on the same frames, today kept selectable ([roadmap](ROADMAP.md)).

## BUILD-HEAP-GATE-AFTER-STAIRS-46 and BUILD-CHIM-MAIN-MEMORY-46 registered, 20 October 2026

[BUILD-HEAP-GATE-AFTER-STAIRS-46](bugs/BUILD-HEAP-GATE-AFTER-STAIRS-46.md): the v0.0.46-dev1 build failed 2 h 38 min in
at the CHIM heap gate (six frames 0.6 to 2.8 % over the zone); the gate took 12.6 s and runs after the stair walk.
[BUILD-CHIM-MAIN-MEMORY-46](bugs/BUILD-CHIM-MAIN-MEMORY-46.md): in the same build the container reached 42.1 of
44 GiB in the world frames step and the memory guard cut the CHIM workers from 21 to 14.

## TESTS-HEAD-REDUCER-BYTES-CI-45 persisting: the NPC bake follows the processor's linear algebra kernel, 20 October 2026

TESTS-HEAD-REDUCER-BYTES-CI-45 (PERSISTING since v0.0.44, 19 October 2026; reported 4 times): the byte-exact head
reducer test failed in CI on some runners and passed on others with the same commit. Cause proven: OpenBLAS in the
NumPy and SciPy packages picks its kernels by the processor (SkylakeX with AVX-512, Haswell on AVX2 processors,
older families below), and the families round the bake's matrix products and pseudo-inverses differently in the last
bit; a skin texel meant to be 220 is then truncated to 219 on one of them (358 texels of the fixture; faces and UVs
identical). Forcing the Haswell family on this machine gives exactly the CI digest `1da14f60…`, also with the CI's
package versions, while SkylakeX (this machine's own) gives the pinned one. So NPC skins were not reproducible across
processors either. Repaired on branch v0.0.46-ci-reducer: builder and test runner pin one kernel family before NumPy
loads (`tools/blas_kernel.py`, Haswell), the NPC bake caches key on the kernel, the test checks exact bytes under the
pinned family in a child process, and CI prints the processor model. The whole suite run under the Haswell and the
native family differs in this one test only. The next build rebakes the NPC gallery and resident NPC models once.
[Report](bugs/TESTS-HEAD-REDUCER-BYTES-CI-45.md).

## BUILD-REUSE-PLAN-ENV-36 persisting: the standalone reuse plan keyed stages with an empty environment, 20 October 2026

BUILD-REUSE-PLAN-ENV-36 (PERSISTING since v0.0.36-dev1, 10 October 2026; reported again with v0.0.45):
`build.py --reuse-plan` returned before the build exported its options to the environment, so every stage key
that names an `AMIWIND_*` variable differed from the run's (15 variables, each recorded against "unset").
Against the v0.0.45 release run the plan showed 8 of 39 stages reused. Repaired on
branch v0.0.46-reuse-plan-env: the build and the plan share two export functions, the plan takes the options
after `--`, the run's recorded command (recorded from now on) or the build defaults, and says which; now 16 of 39
reused, every rebuild named by a changed file. Two tests, the first failing against the old code.
[Report](bugs/BUILD-REUSE-PLAN-ENV-36.md).

## TRACKER-REGISTER-SIZE-33 and TRACKER-REGISTER-SIZE-36: the archive split by version range, 20 October 2026

TRACKER-REGISTER-SIZE-33 (PERSISTING, reported a fifth time): the register audit of 20 October 2026 took the single
bug archive to 232,832 bytes, 89 % of its 256 KiB limit. The archive is now one file per range of the version a bug
was first found in (to v0.0.31, v0.0.32, v0.0.33, v0.0.34-v0.0.35; `ARCHIVES` in `tools/bug_register.py`), and the
rotation reaches v0.0.35, which is the second archive of TRACKER-REGISTER-SIZE-36. Archives 22-33 % of their limit,
`bugs.json` 66 % of 1 MiB; every tracker file warns at 75 % again. Not shipped.
[Report](bugs/TRACKER-REGISTER-SIZE-33.md). SKY-FLAT-PALETTE-DRIFT-41: both parts are merged on the dev line
(a6a9c6e9); status corrected.

## BUILD-SIZE-GUARD-OLD-BASELINE-45: the size guard compared v0.0.45 with v0.0.41, 20 October 2026

BUILD-SIZE-GUARD-OLD-BASELINE-45: the v0.0.45 release build failed its size guard on 0.44 GiB of CHIM world growth
although every folder had the size of the v0.0.44 release build's: the guard always compared with the committed
record, which was still of v0.0.41. Repaired on branch v0.0.45-reuse-keys: the release record is the previous
release's own ledger (tools/previous-release.json; its release build in the workspace, else the committed record of
that release); tools/size-baseline.json is now the v0.0.45 record. [Report](bugs/BUILD-SIZE-GUARD-OLD-BASELINE-45.md).

## BUILD-REUSE-SCHEDULER-TOP-45 part 2: walks keyed by the data they walk, preflight stops scheduling-only rebuilds, 20 October 2026

BUILD-REUSE-SCHEDULER-TOP-45: measured per reached unit, the CHIM stair key changed between v0.0.44 and v0.0.45 only
through the import-time code of tools/chim/validate.py (the frame loader's module) and the legacy-map walk key only
through two pool sizing constants in tools/stair_parallel.py. Repaired on branch v0.0.45-reuse-keys: NPC gallery face
keys in key form 2; a CHIM walk keyed by the SHA-256 of the frame data it walks plus the walk's own code, every walk
worker checking the frame it reads against that key; pool sizing constants key no walk; the reuse preflight stops a
build whose rebuilds only scheduling code, VERSION or prose explain. Each with a test that fails against the old
code. [Report](bugs/BUILD-REUSE-SCHEDULER-TOP-45.md).
## MESH-EBONHEART-DRAGON-PEDESTAL-42: the game drops a root node's translation, 20 October 2026

[MESH-EBONHEART-DRAGON-PEDESTAL-42](bugs/MESH-EBONHEART-DRAGON-PEDESTAL-42.md): the dragon statue's model has a
root NiNode with a translation of z 327.1; the game drops a root NiNode's whole transform (rule from OpenMW file
components/nif/node.cpp), the converter dropped only its rotation, so the statue and its plinth floated 327 units
over the plaza. Repaired for every model in `nif_common.scenery_root_local`; the new `tools/nif_root_audit.py` finds
25 models with 723 placements that move, among them 41 Daedric ruins drawn 1,018 units too low. Needs a world build.

## SKY-REDMOUNTAIN-BLUE-44: region weather, 20 October 2026

[SKY-REDMOUNTAIN-BLUE-44](bugs/SKY-REDMOUNTAIN-BLUE-44.md): the sky had only the clear weather's colours and no
build step wrote the regions' weather, so all nine regions drew the clear sky; Red Mountain's record is blight
100 %. Repaired: the builder writes `region-weather.aww`, the engine picks each region's weather and draws its sky,
horizon and fog colours. Needs a world build and an in-game look.

## BUILD-REUSE-SCHEDULER-TOP-45: a scheduler-only edit rekeyed the gallery and the stair walks, 19 October 2026

BUILD-REUSE-SCHEDULER-TOP-45: the v0.0.45 release build reconverted all 3,551 NPC gallery faces and walked all 1,351
stair frames again because the v0.0.45 pool changes added scheduling functions (and a default value) to
tools/build_parallel.py, and a module's import-time text lists every function's default values. Repaired in
tools/build_cache.py (scheduling_top_text) with SchedulingKeysTest, which fails against the previous code. The first
build after the repair recomputes those keys once. [Report](bugs/BUILD-REUSE-SCHEDULER-TOP-45.md).

## CHIM-ROCKS-OPEN-SHELLS-43: island-wide rock sweep finds no converter cause, 19 October 2026

[CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md): a new audit, `tools/rock_shell_audit.py`, compared
every rock mesh on CHIM (168 meshes, 9,591 stored variants, 37,133 placements) with the original. Morrowind's rocks
are one-sided shells left open where the game buries them, none drawn from both sides; the stored models keep every
face and its winding; the converter turns placements in OpenMW's order, which buries the rims best. CHIM rims stand
above the ground as rarely as the original's (0.99 % of rim samples against 1.07 %). Five meshes with more exposed
rims are recorded. The in-game look at reference 476548 and the OpenMW view at the same pose come next.

## TRACKER-CHIM-COUNT-STALE-44: the tracker counted audits, not the build, 19 October 2026

[TRACKER-CHIM-COUNT-STALE-44](bugs/TRACKER-CHIM-COUNT-STALE-44.md): after the v0.0.44-dev1 build was ingested the
tracker still printed 1,193 of 1,436 cells. That line counted audit-passed land cells over both islands (Solstheim
included), and seabed cells an older CHIMport run had called empty sea never counted, although the build carries them.
The tracker now records per cell the newest build that carries it and per build the cells on CHIM by island:
v0.0.44-dev1 has every Vvardenfell land cell (1,292 of 1,292) plus 117 sea cells on CHIM.

## INTERIOR-MORAG-TONG-FPS-43: every room installer copies its plant sprites, 19 October 2026

[INTERIOR-MORAG-TONG-FPS-43](bugs/INTERIOR-MORAG-TONG-FPS-43.md): since v0.0.43-dev4 the plants and trees of every
converted interior are sprites, written next to each room's own map. The Vivec room installer copied those sprites into
the game; the Balmora interiors, area and harvest room installers copied only the map. The first v0.0.44-dev1 image
step therefore stopped on a Mages Guild plant sprite that a map placed but the image did not have. One shared installer
now copies a room's files for all four, and a test checks that every room installer uses it.
## BUILD-CHIM-SERIAL-SECTIONS-44: causes and repair; BUILD-IMAGE-STAIR-WALK-CORES-43 and BUILD-REUSE-KEYS-TOO-BROAD-35, 19 October 2026

[BUILD-CHIM-SERIAL-SECTIONS-44](bugs/BUILD-CHIM-SERIAL-SECTIONS-44.md): the CHIM stage's one-core stretches of the
v0.0.44-dev1 build measured on 157 frames: quadratic ownership and overlap checks, layouts made in the parent while the
workers waited, far terrain and the large JSON files on one core, the validation sending every stored unit its chunk
images, and stair walks given the largest frame's memory share. Repaired on branch v0.0.44-serial with every output
byte-identical (SHA-256): visibility rows 33 s at 3.8 cores -> 8 s at 12; stair gate 2 min 20 s at 8.5 cores -> 1 min
2 s at 15.5; the pools read a raised allowance within a second.
[BUILD-IMAGE-STAIR-WALK-CORES-43](bugs/BUILD-IMAGE-STAIR-WALK-CORES-43.md): a tail of heavy-room units; walk times
recorded per map and heavy maps cut shorter (dev3 maps: 215-238 s -> 156 s, same report).
[BUILD-REUSE-KEYS-TOO-BROAD-35](bugs/BUILD-REUSE-KEYS-TOO-BROAD-35.md) PERSISTING: the chim stage keyed
tools/release-files.json through the words of a preflight refusal; that function is left out of the key closure.

## NPC-HEAD-DECIMATION-33: the player body falls back to the previous head reducer, 19 October 2026

[NPC-HEAD-DECIMATION-33](bugs/NPC-HEAD-DECIMATION-33.md): the v0.0.44-dev1 build stopped in its image step on the
Argonian female player body. With the boundary-locked head reducer no body fitted: the larger budgets were over the
alias vertex budget and the smaller ones narrowed the legs. The NPC bake already falls back to the previous head reducer
for such an appearance; the player body search now does the same, logged, and tests cover it.

The next run stopped one step later, at the guard torch models: a guard's held-torch pose must reproduce its existing
model exactly, that model had been baked with the previous head reducer, and the torch step tried only the locked one;
a budget too small for the guard's shapes also stopped the step instead of being skipped, and the error named no
guard. The step now tries both reducers, skips a budget that is too small, and names the guard if nothing fits.

The third stop, at the same step: one guard (the Seyda Neen boat guard) was rebuilt with 8 of its 85,050 coordinates
one quantisation step off in one frame, floating-point rounding with the locked reducer, and the step demanded a
bit-exact match. A rebuilt base pose now counts when every coordinate is within one step and at most 0.1 % differ; the
receipt records how many were off instead of claiming an exact match. All 13 guards were checked against that build's
own files before the next build.

## CHIM-ROCKS-OPEN-SHELLS-43 and CHIM-CROSSING-SLUGGISH-43 registered, 19 October 2026

[CHIM-ROCKS-OPEN-SHELLS-43](bugs/CHIM-ROCKS-OPEN-SHELLS-43.md): the maintainer saw several rock types on CHIM that do
not close up, first pinned at Bitter Coast cell -4,-6 (`terrain_rocks_ai_02`). Cause not found yet; an island-wide
open-edge sweep against the source meshes comes next.

[CHIM-CROSSING-SLUGGISH-43](bugs/CHIM-CROSSING-SLUGGISH-43.md): crossing between CHIM cells stalls, worst at cell
corners. The prefetch into spare RAM (measured about 450 ms down to about 230 ms per crossing with 128 MB) is the
first step, planned for v0.0.45-dev1.

## CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43: two Bitter Coast frames over the heap zone, 19 October 2026

[CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43](bugs/CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43.md): the v0.0.43-dev4 build stopped at the
CHIM heap gate: frames x-07/y-04 and x-08/y-04 were 113 and 110 KiB (1.9 %) over their zone. Only the drawn models
grew: the Bitter Coast trees got about 60 % larger when the trunk shape guard of
[CHIM-AZURA-FLOATING-FLORA-43](bugs/CHIM-AZURA-FLOATING-FLORA-43.md) re-reduced their trunks boundary-locked. The guard
now first retries the same reducer at 1.5 to 4 times the target and uses the first copy that keeps the trunk's height:
Bitter Coast trees 01 to 07 come out 16 to 42 % smaller, every trunk still keeps at least 90 % of its height, and the
Azura's Coast trees are unchanged. Fixed in source; the next build checks it.
## CHIM-CROSSING-SYNC-LOAD-43 and ENGINE-HEAP-FIXED-SIZE-43: the open-world pauses measured, 18 October 2026

[CHIM-CROSSING-SYNC-LOAD-43](bugs/CHIM-CROSSING-SYNC-LOAD-43.md): the open-world "yoinks" in v0.0.43-dev2 are the cell
crossings. Every exterior cell is its own CHIM frame map, and each crossing read and decoded the whole world index,
opened every earlier frame's file for its placement count, then loaded the ring around the arrival in 300-580 small
reads: two long frames per crossing, 0.3-1.1 s in FS-UAE. With extra Fast RAM the index and the counts now stay in
memory across maps and the cells ahead are read into spare RAM (the 2x2 block at the nearest corner first, then the
3x3 ring); crossings on the test route went from a 452 ms to a 209-223 ms median at 128 MiB. 16 MiB unchanged. On
that route dev2 and v0.0.42 cross alike within drift ([CHIM-READ-RUNS-33](bugs/CHIM-READ-RUNS-33.md)).

[ENGINE-HEAP-FIXED-SIZE-43](bugs/ENGINE-HEAP-FIXED-SIZE-43.md): the heap is now sized from the free Fast RAM at start
(24 MiB at most, the built 11 MiB on 16 MiB machines); with 128 MiB no "hunk-gap safety" warning in five laps of
Balmora, Caldera, Vivec and Seyda Neen, and the Hunk use was the same on every lap.
## NPC-HEAD-DECIMATION-33 locked head reducer and INTERIOR-MORAG-TONG-FPS-43 decided, 18 October 2026

Decided for the project, 18 October 2026 (the maintainer): plants and trees in interiors are sprites by default
([INTERIOR-MORAG-TONG-FPS-43](bugs/INTERIOR-MORAG-TONG-FPS-43.md); the page ranks the 20 meshes that draw the
most interior faces after that, with the step that fits each, and the A/B plan for the tramaroot planters), and
budget NPC heads are reduced with the boundary-locked reducer
([NPC-HEAD-DECIMATION-33](bugs/NPC-HEAD-DECIMATION-33.md), `--npc-head-reducer locked`, the previous reducer kept
as `default`): no rim moves on any of the 2,675 NPC records, for a median of 10 more triangles per model. Fix in
source, not yet built.

## INTERIOR-MORAG-TONG-FPS-43 and NPC-HEAD-DECIMATION-33 persisting, 18 October 2026

[INTERIOR-MORAG-TONG-FPS-43](bugs/INTERIOR-MORAG-TONG-FPS-43.md): the maintainer found the Balmora Morag Tong
Guild very slow in v0.0.43-dev2. Measured: 34,801 faces in one vis leaf (everything in view is drawn); the
planter ash tree is 1,454 faces (4.2 %), its grass 240; the converter keeps each mesh at about its original
triangle count, and the suspected desk's planes and clipnodes are collision the renderer does not walk; the 15
chairs are 19.8 %. Builder rule: plants and static trees of every interior as sprites, a solid tree keeping
its collision (island-wide 86,623 faces, 2.7 % of all interior faces). Open: in-game A/B, furniture recipes.

[NPC-HEAD-DECIMATION-33](bugs/NPC-HEAD-DECIMATION-33.md) persisting: Angahran (a gash in her head) and Shannat
Pansamsi (a crude, flat face) in the same room. The original-head bake exists since v0.0.35 but is
experimental and off: the shipped default `npc_head_detail` auto resolves to `budget` (decided for the project,
10 October 2026), so every humanoid head is still reduced. Angahran's head keeps 57 of 450 triangles and gains
open edges (10 to 15); Shannat's head 101 of 524, his hair 42 of 326 with 36 new open edges.

## VIVEC-ARENA-WATER-FALL-32: the sea to the horizon without the day/night sky, 18 October 2026

The maintainer's v0.0.43-dev2 report from the Vivec St. Olms ledge: sky and clouds below the horizon instead of the
sea. Cause: the day/night sky was off in that session (`aw_daynight 0`, confirmed by the maintainer); with it on, the
sky below the horizon takes the fog colour and joins the fogged sea past the far layer's reach. Repaired in the fog
pass: with the day/night sky off, sky below the horizon takes the static fog's last level (one comparison per sky
pixel; the day/night path unchanged; `aw_land_fill 0` keeps the old picture), with a native regression test. The
v0.0.32 fall through the water still waits for its recheck in whole-city CHIM Vivec.

## COLLISION-NC-FLAGS-32: editor markers, 18 October 2026

[COLLISION-NC-FLAGS-32](bugs/COLLISION-NC-FLAGS-32.md): in v0.0.43-dev2 the maintainer saw red editor-marker shapes
under the West Gash bridges (references 481808, 481815, 481812) and in a Khuul longboat (465744). All four are sound
activators whose model is `EditorMarker.nif`; the CHIM source stage only left out models named `marker_*`. The rule
now follows OpenMW (hidden marker ids, root `MRK` hides `Tri EditorMarker` shapes from drawing and collision), in one
place for every converter. Marker placements stay as invisible objects with their role in an emitter table. Island-wide:
4,705 marker placements (2,565 sound, 778 effect, 1,318 hidden, 30 collision, 14 script). The source stage stops if one
would be drawn. NC, NCC and AvoidNode stay open.

[CHIM-SEYDA-BALMORA-LOAD-HANG-43](bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): 18 October 2026, v0.0.43-dev1: the boot smoke hung on the Loading screen going from Seyda Neen to Balmora in two of about five runs (the v0.0.41-dev5 image in gate 2928 and the first v0.0.43-dev1 delivery smoke); each passed on a rerun. Seyda's CHIM zone runs full in every run. Cause unknown; open.

## CHIM-AZURA-FLOATING-FLORA-43 cause found and CHIM-AZURA-DWEMER-RUIN-SHAPES-43 measured, 18 October 2026

[CHIM-AZURA-FLOATING-FLORA-43](bugs/CHIM-AZURA-FLOATING-FLORA-43.md): along Azura's Coast the tree crowns hung in the
air with no trunk. The flora reducer collapsed the trunk of `flora_tree_ac_01` and `_02` (bark kept 12 % and 8 % of its
area); the placements are correct and not doubled. The flora profile now guards the height of trunks and stems: 31 of
250 reduced meshes change, +5.3 % triangles per variant. Fixed in source; in-game check to do.

[CHIM-AZURA-DWEMER-RUIN-SHAPES-43](bugs/CHIM-AZURA-DWEMER-RUIN-SHAPES-43.md): Daedric ruin pillars at cell 19,4 looked
like twisted shapes in the air. Their placements and models match the original data and the pillars stand on the ruin
base (placement 394429); whether that base is drawn in game is still to be checked. Open.

## BUILD-IMAGE-STAIR-WALK-CORES-43, 18 October 2026

[BUILD-IMAGE-STAIR-WALK-CORES-43](bugs/BUILD-IMAGE-STAIR-WALK-CORES-43.md): the v0.0.43-dev3 full build passed every
stage, but its perf guard failed the image step's stair walk: 45 % of its cores in use against a 95 % baseline.
v0.0.43-dev3 ships with it as a known issue by maintainer decision; the fix is planned for v0.0.43-dev4.

## CHIM-OCEAN-CELL-RECORD-ROUTING-43, 18 October 2026

[CHIM-OCEAN-CELL-RECORD-ROUTING-43](bugs/CHIM-OCEAN-CELL-RECORD-ROUTING-43.md): the v0.0.43-dev3 full build stopped
30 minutes in, in world terrain, on the 14 open-sea cells with a CELL record: the planner routed every ocean cell as
a cell without a map, although these 14 have one each. One rule now serves the checklist, world terrain and the
regions preflight: an ocean cell with a map is replaced in place like a land cell, and the preflight shows the split
in seconds. World terrain on the failed run's own inputs passed. Fixed.

## BUILD-STAGE-ALLOWANCE-STUCK-43 and BUILD-CHIM-REGION-FRAMES-TAIL-43: causes and repair, 18 October 2026

[BUILD-STAGE-ALLOWANCE-STUCK-43](bugs/BUILD-STAGE-ALLOWANCE-STUCK-43.md): the scheduler's memory guard cut the CHIM
stage 20 -> 1 workers while the stage's main process, not its workers, held the memory, and grew it back only by a
planned 2,842 MiB unit that never fit. The guard now measures the stage's own processes, cuts only what the workers
hold and grows back by their measured size; idle stages lend their workers to queued work; a stage under half its
share with units queued for a minute is named in the log and `underused.jsonl` (a warning, never a failure); the
build summary is written at every stage end.
[BUILD-CHIM-REGION-FRAMES-TAIL-43](bugs/BUILD-CHIM-REGION-FRAMES-TAIL-43.md): the region frames go to the pool
largest first (cost history, else references), the placement layouts overlap the visibility rows, and a sweep test
makes every pool caller give a cost or a reason. Verification waits for the next full build.

## BUILD-IMAGE-ALL-CHIM-PREFLIGHT-43, 18 October 2026

The v0.0.43-dev3 build, the first with every exterior cell on CHIM, converted everything and stopped in the image
preflight: with no classic world maps left, the disk layout check refused an empty list with a message naming no
file or limit. Nothing was lost; the fix counts the planned CHIM frame maps.

Cause confirmed on the run's own files (none of the 2,526 directory rows had a map on disk yet; the boot payload
was within budget). Repair: the preflight plans the 1,348 CHIM region frame maps by a recorded size bound, with
their far terrain and sprites in the boot plan; each partition refusal names its numbers. On the dev3 run the
preflight passes: one drive, boot, frame-map and CHIM world partitions, all within the Amiga limits.

## CHIM-VIVEC-DOCK-WALKWAY-43, 18 October 2026

The maintainer's v0.0.43-dev2 playtest: the walkway at the Vivec Hlaalu canton dock cannot be climbed; the player
gets stuck at its foot. Registered open; to be checked in v0.0.43-dev3 with the shared stair fix.

Cause measured the same day: the converter built each convex collision piece from its extreme points along 14
directions only, and on the dock's level-then-sloped deck that hull lies up to 19.4 units under the planks (the
authored collision follows them). A second spot by the Arena canton is the same mesh. Fixed in the shared converter
for 484 measured meshes, with a collision surface gate for every CHIM mesh; verification waits for a build.

## ENGINE-HEAP-FIXED-SIZE-43, 18 October 2026

The maintainer's v0.0.43-dev2 playtest with 128 MB of RAM: the game heap stays at the build's 11 MiB, so Vivec
warns about its memory gap and loads pause. Registered open; the heap will be sized from the free memory at start.

## CHIM-TERRAIN-TEXTURE-BLOCKY-43, 18 October 2026

The maintainer's v0.0.43-dev2 playtest: roads and paths look blocky, each texture square drawn with hard edges
instead of blending into its neighbours as in the original. Registered open; an A/B of blending methods planned.

## BUILD-STAGE-ALLOWANCE-STUCK-43, 18 October 2026

The v0.0.43-dev3 build ran the CHIM visibility rows on one core for about 40 minutes: the stage's worker allowance
stood at 1 after the other stages had finished. Raised by hand during the build; registered open.

## MESH-MUCKSPUNGE-SEAM-43, 18 October 2026

The maintainer's v0.0.43-dev2 playtest: a tilted muckspunge on Azura's Coast (cell 14,7) shows a black six-sided seam
where its cap meets its body. Registered open (small); cause not measured.

## CHIM-AZURA-DWEMER-RUIN-SHAPES-43, 18 October 2026

The maintainer's v0.0.43-dev2 playtest: a Dwemer ruin on Azura's Coast (cell 19,4) is drawn as twisted shapes that do
not match the original. Registered open; checked together with the floating plant pieces in the same cells.

## CHIM-AZURA-FLOATING-FLORA-43, 18 October 2026

The maintainer's v0.0.43-dev2 playtest: leafy plant or tree pieces hang in the air at Azura's Coast (cell 16,7).
Registered open; cause not measured.

## INTERIOR-MORAG-TONG-FPS-43, 18 October 2026

The maintainer's v0.0.43-dev2 playtest: the Morag Tong Guild interior runs at a very low frame rate; suspects
pinned in game are the planter tree with its roots and grass, and a table. Registered open; being measured.

## BUILD-CHIM-REGION-FRAMES-TAIL-43, 18 October 2026

The v0.0.43-dev3 build ended its CHIM region-frame step on one worker with the other cores idle: the frames are
started in list order, not largest first. Registered open; the fix passes each frame's cost to the scheduler.

## CHIM-RED-MOUNTAIN-SOLID-SKY-43: cause and repair, 18 October 2026

[CHIM-RED-MOUNTAIN-SOLID-SKY-43](bugs/CHIM-RED-MOUNTAIN-SOLID-SKY-43.md): the CHIM terrain and the frame maps closed
at a fixed 2,048 frame-local units, and Red Mountain's ground reaches 4,730 (69 of the 1,298 dev2 frames go over
2,048). Faces over their node boxes were drawn without clipping, so the view broke apart near 2,048; the region start
and the map teleport searched down from inside the mountain. Frames with ground near or over the ceiling now get the
ground plus a 4,096-unit flight band (9,216 there), every other frame keeps its bytes; the map placement search uses
the coordinate range. The validation checks faces against their boxes; a height audit covers the island. In-game
verification waits for a build with the fix.

## CHIM-RED-MOUNTAIN-SOLID-SKY-43, 18 October 2026

The maintainer's v0.0.43-dev2 playtest: climbing to the Red Mountain summit (cell 2,9, new on CHIM in dev2) left
the player inside solid with only the sky drawn. Registered open; cause not measured.

## OPENING-JIUB-LANTERN-32 persisting, 18 October 2026

The maintainer's v0.0.43-dev2 playtest: the lantern above Jiub at the start is unlit again (no warm light, no
glowing glass), although v0.0.33 fixed it. A lantern on a crate in the same Prison Ship cell does light (source
ref 299172), so the regression is specific to that lamp or its light. Reopened as persisting; cause not measured.

## TRACKER-REGISTER-SIZE-33: journal rotation, 18 October 2026

The current journal was 196,648 bytes, 40 bytes past its 196,608-byte warning (75 % of the
release text limit), so the tracker test failed. The 130 entries dated 11-16 October 2026
(the v0.0.37 to v0.0.41 releases) now live in the
[v0.0.37-v0.0.41 journal archive](journals/BUG_JOURNAL-v0.0.37-v0.0.41.md). Their text and order are unchanged
apart from relative link paths, and links between the two files were repointed. Entries
from 17 October 2026 (and one register audit note of 16 October) stay here. Earlier archives: [v0.0.35-v0.0.36](journals/BUG_JOURNAL-v0.0.35-v0.0.36.md),
[v0.0.34](journals/BUG_JOURNAL-v0.0.34.md), [v0.0.31](journals/BUG_JOURNAL-v0.0.31.md),
[before 7 October 2026](journals/BUG_JOURNAL-v0.0.29.md). Current issue states remain in the
[register](BUGS.md#fix-index).

## CHIM-STAIR-STEPS-SOLID-43 repaired in the converter, 18 October 2026

[CHIM-STAIR-STEPS-SOLID-43](bugs/CHIM-STAIR-STEPS-SOLID-43.md): the Redoran fan staircase collides as an authored ramp
7 to 14 units over its visible treads, the canal piece a Suran flight leads onto has a convex proxy that invents a
50-degree slope over its walkway, and the rope bridge's deck is one convex piece whose top is the chord over the sag.
One rule in the shared converter (`mesh_geometry.clear_visible_treads`, CHIM models only) checks the collision over
every visible flight tread: pieces standing over it are split, made authored plates, and an authored ramp over the
steps gives way to the visible flight. 64 of 4,076 meshes change (23 exterior, placed in 213 CHIM frames).
Cell-only frame builds: the 39 stair-held cells walk (10,883 steps, 0 failed; 32 failed before), and the 213 frames
that place a changed mesh walk again with 0 failures (75,321 steps).
[CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43](bugs/CHIM-STAIR-PLATE-BEVELS-PER-PIECE-43.md): found on the way: the CHIM model
variants take only the mesh-wide exact-bevel flag. Open; worked around for the changed meshes.

## BUILD-IMAGE-REGION-MAPS-SERIAL-43 and BUILD-PASS-KEY-TOP-BROAD-43, 18 October 2026

[BUILD-IMAGE-REGION-MAPS-SERIAL-43](bugs/BUILD-IMAGE-REGION-MAPS-SERIAL-43.md): the v0.0.43-dev2 full build failed its
perf guard on "Image: CHIM region frame maps" (1,295 frames, 61 s on 1.13 of 20 cores). Measured from its build profile:
the image step read the whole CHIM world six times (about 30 s each, 137 s of them before the entity tracker), traced
each region frame's player start on a scene of its whole frame (48 s) and made the town frame maps one by one. Repaired
on v0.0.43-imgpar: the world read once and handed on, ground traces on a column scene (same results, test), town frame
maps and door rows on the pool, the region cache keyed by both row methods (the old key named the legacy one only).
Checked on scratch copies of the dev2 run's own inputs: all 1,300 frame maps the repaired code makes are byte for byte
the run's (SHA-256), and so are the 20,266 other id1 files they touch; the world read, entity tracker placements,
frame maps and heap gate took 75.6 + 1.8 + 52.3 + 36.8 s (12 workers, a busy host, pass cache off), against
192.5 s for the placements alone with the code before. Persisting reports added to BUILD-IMAGE-CHIM-MAPS-SERIAL-36
and BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36.
[BUILD-PASS-KEY-TOP-BROAD-43](bugs/BUILD-PASS-KEY-TOP-BROAD-43.md): why the region cache had 0 hits: for the frame
maps both runs made only the pass's source digest differed, because a new constant in `tools/chim/models.py` (a module
the worker reaches, not the constant) changed its import-time code. Open; narrower key proposed.
## CHIM-BALMORA-INSET-SLIVERS-43 and CHIM-OCEAN-CELL-RECORD-CLASSIC-43, 18 October 2026

The v0.0.43-dev2 build keeps 61 exterior cells classic: 39 wait for the stair repair, and 22 more were missing from
the count. [CHIM-BALMORA-INSET-SLIVERS-43](bugs/CHIM-BALMORA-INSET-SLIVERS-43.md): Balmora's frame handed over 96
units inside its cells, so its 8 border cells kept classic strips (15 legacy maps, 11.4 MB); Balmora now owns its 3 x 3
cells like Seyda Neen (same placements and ring headroom, world +1.5 MB). Fixed.
[CHIM-OCEAN-CELL-RECORD-CLASSIC-43](bugs/CHIM-OCEAN-CELL-RECORD-CLASSIC-43.md): 14 open-sea cells with a CELL record and
no LAND kept a classic seafloor map each; the cell list tool now reports every cell left classic, and the 14 join the
next list as ocean cells (all audits passed). Fixed.

## CHIM-HULL-ROUTE-NO-CUT-43 and CHIM-STAIR-STEPS-SOLID-43, 18 October 2026

[CHIM-HULL-ROUTE-NO-CUT-43](bugs/CHIM-HULL-ROUTE-NO-CUT-43.md): the 14 hull-policy-pending cells all failed on two
flora meshes whose routed standing hull stayed one chain (285 and 465 clipnodes deep); compiled as the checked union
from a measured table they are 29 and 37 deep and all 14 cells pass.
[CHIM-STAIR-STEPS-SOLID-43](bugs/CHIM-STAIR-STEPS-SOLID-43.md): Ald-ruhn and Maar Gan (Redoran steps), Suran (Hlaalu
steps) and cell 0,8 (a rope bridge) fail the stair walk; 39 cells wait on them. Open.

[CHIM-SEYDA-BALMORA-LOAD-HANG-43](bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): 18 October 2026, v0.0.43-dev1: reproduced with a repeat loop under host load (5 hangs; none in 100 loads on a quiet host, at 16 and at 128 MiB Fast RAM alike). The debugger shows a deadlock below the engine: the processor idle, the game waiting on a file request taken by the boot partition's file system (DH0) that never answers, the same class as SEYDA-LOAD-HANG-30. The boot smoke now runs its map change three times and, when a load stalls, examines it with the emulator's monitor: this stall is reported as an emulator disk stall and retried once on a fresh play copy. Still open (under observation): which layer loses the request; real hardware is not believed affected, unproven.

[CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md) — 15 October 2026, v0.0.41-dev1: full-build preparation rejected five explicitly selected ocean routing cells absent from the original CELL/LAND inventory, before legacy compilation. The source checklist now records additional ocean routing cells separately and allows their absence only before routing rows are appended. Final classification/stage verification still requires every row and CHIM routing flags; undeclared or unselected missing cells are rejected. All 98 targeted checks across five modules pass, including three new ocean checklist regressions. Exact production conversion, native ocean behavior, image/package and delivery checks remain pending; coverage states are unchanged.

## CHIM-REGION-SEABED-NO-HEIGHTS-42 fixed, 17 October 2026

[CHIM-REGION-SEABED-NO-HEIGHTS-42](bugs/CHIM-REGION-SEABED-NO-HEIGHTS-42.md): a region cell whose LAND record has no
heights is now flat seabed at the original default height, as CHIMport converts it (rule from OpenMW's terrain
storage); a cell without any LAND record is still refused, and the refusal names frame, cell and audit file. The CHIM
stage alone on the 98 seabed cells and 50 new cells passed every gate.

## UI-INVENTORY-FONT-TABS-42, 17 October 2026

[UI-INVENTORY-FONT-TABS-42](bugs/UI-INVENTORY-FONT-TABS-42.md): the inventory categories are plain text in the console
font, not buttons in the game's font as in the original; asked for on 14 October and again on 17 October. Open.
## BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42 and BUILD-CHIM-STAIR-NO-REUSE-42, 17 October 2026

[BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42](bugs/BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42.md): the v0.0.42 final's stair gate
walked on the 2 workers of its stage's launch share while the allowance said 12; the stage's pools now size by the
build budget and follow the live allowance.
[BUILD-CHIM-STAIR-NO-REUSE-42](bugs/BUILD-CHIM-STAIR-NO-REUSE-42.md): the same gate walked all 1,118 frames: 494
passed in v0.0.42-dev1 but carry no check mark (the launcher never promotes walks), 392 are new, the rest changed
with the boundary-locked mushroom caps (a true change).

## BUILD-SCHEDULER-MEMORY-STARVED-42, 17 October 2026

[BUILD-SCHEDULER-MEMORY-STARVED-42](bugs/BUILD-SCHEDULER-MEMORY-STARVED-42.md): in the v0.0.42 final build the
scheduler's memory guard held the chim stage on 1 of its 6 workers for over an hour (26.5 of 28 GiB in use beside
the NPC gallery and the world terrain; it grows a stage back only below 70 %); its visibility rows took 2 h 11 min.
Given 42 GB live, the stage got 9 workers back. Repair: a fit check before each pooled stage starts, a
[scheduler] ALARM for a stage starved over 5 minutes, both with the lease that fixes it, and the plan counts the
memory beside a stage.

## SKY-STAR-TWINKLE-LATE-42, 17 October 2026

[SKY-STAR-TWINKLE-LATE-42](bugs/SKY-STAR-TWINKLE-LATE-42.md): the maintainer saw no star twinkle early in a
v0.0.42-dev1 night and some later on. Not a code change: the twinkle (three stars of the dome, unchanged since
v0.0.28) shows only once the midnight clearing opens the sky; the moving cloud veil can also read as twinkling.
Minor visual item; new saved switch `aw_star_twinkle` (default on, look unchanged; 0 = steady stars) with a test.

## NPC-DREAMER-GREETING-DEFAULT-42, 17 October 2026

[NPC-DREAMER-GREETING-DEFAULT-42](bugs/NPC-DREAMER-GREETING-DEFAULT-42.md): cause found: a talk said the NPC's Hello
bark; the conversation greeting topics (Greeting 0-9) were never read, and the Hello topic has no Dreamer line.
Repaired in source: a talk opens with the greeting picked by OpenMW's startDialogue rule (first meeting and later
talk), for every NPC; Dreamers now open with their Sixth House lines.

## NPC-STORY-DISABLED-AT-START-42, 17 October 2026

[NPC-STORY-DISABLED-AT-START-42](bugs/NPC-STORY-DISABLED-AT-START-42.md): registered: the original's Startup script
disables 58 NPCs (the twelve town Dreamers and the Dreamer Prophet among them) and 20 creatures at a new game, and
the Dreamers enable themselves at journal A2_2_6thHouse 50; AmiWind places them all from the start. Open.

## NOCLIP-BOB-DEFAULT-42, 17 October 2026

[NOCLIP-BOB-DEFAULT-42](bugs/NOCLIP-BOB-DEFAULT-42.md): reported again by the maintainer in v0.0.42-dev1: the view still
bobs in noclip, although the noclip bob was set to off by default after the first report on 13 October. Open.
## CHIM-ZONE-RELEASE-FLICKER-42, 17 October 2026

[CHIM-ZONE-RELEASE-FLICKER-42](bugs/CHIM-ZONE-RELEASE-FLICKER-42.md): reported by the maintainer in v0.0.42-dev1:
distant buildings at Ebonheart pop in and out while standing still; zone full there and at Khuul. Measured the
same in v0.0.41 (not a dev1 regression): the zone is locked full (world index 1,775 KiB) and chunks released for
a request that still fails come back 50 ticks later, with 50-530 ms CHIM work frames. Repair on
v0.0.42-outline-pop: release only what makes room (chim_release 2) and a world index without derivable paths
(1,056 KiB). Open until in a build.

## MESH-EBONHEART-DRAGON-PEDESTAL-42, 17 October 2026

[MESH-EBONHEART-DRAGON-PEDESTAL-42](bugs/MESH-EBONHEART-DRAGON-PEDESTAL-42.md): the Ebonheart dragon statue
floats (maintainer, v0.0.42-dev1). Its converted model starts 236 units above its origin; the same in v0.0.41
and with the whole ring loaded, so not streaming. Cause open.

## BUILD-TORCH-CREATURE-RESIDENT-42, 17 October 2026

[BUILD-TORCH-CREATURE-RESIDENT-42](bugs/BUILD-TORCH-CREATURE-RESIDENT-42.md): the v0.0.42-dev1 full build stopped in
the image step's torch guard on Vivec, an interior creature resident placed as an NPC entity. Fixed in 5db820c:
creature residents are skipped; other unknown identities are still refused.

## VIVEC-ROOM-PRECACHE-LIMIT-42, 17 October 2026

[VIVEC-ROOM-PRECACHE-LIMIT-42](bugs/VIVEC-ROOM-PRECACHE-LIMIT-42.md): the v0.0.42-dev1 full build stopped in the
payload preflight: Vivec, Telvanni Tower (vti011) needs 257 model precaches, the engine holds 256. It was listed
again because its own model slots fit (210 of 220). Excluded again for v0.0.42-dev1. Open.

## BUILD-CHIM-VIS-VARIANT-SORT-42, 17 October 2026

[BUILD-CHIM-VIS-VARIANT-SORT-42](bugs/BUILD-CHIM-VIS-VARIANT-SORT-42.md): the v0.0.42-dev1 full build stopped after
about 44 minutes in the CHIM visibility rows: the variant keys of a frame mix model numbers and terrain tile
tuples, and the B5 change sorted them directly. Fixed in e5b0c0c (ordered by their text form) with a mixed-key test.

## NIGHT-WINDOWS-LOST-CHIM-36, 17 October 2026

[NIGHT-WINDOWS-LOST-CHIM-36](bugs/NIGHT-WINDOWS-LOST-CHIM-36.md): found while checking where the builder ships a
stand-in: the night-windows table (glowing window glass at night) has been empty in every image since v0.0.36
(v0.0.35: 86 maps). The towns moved to CHIM and their frame maps get no rows; the build printed one warning line.
Open.

## UI-INVENTORY-PREVIEW-STILL-42, 17 October 2026

[UI-INVENTORY-PREVIEW-STILL-42](bugs/UI-INVENTORY-PREVIEW-STILL-42.md): the maintainer: the inventory character
is a still picture in the original, never turning or moving. AmiWind drew it live every frame and turned it with
the arrow keys. Repair on v0.0.42-hud-icons: one render when the window opens and after each equipment action,
facing the viewer, kept as a 116 x 168 picture (19,488 bytes while the window is open); the pose model and
depth buffer are freed at once and later frames only copy the picture. `aw_inventory_preview_live 1` keeps the
old live preview.

## UI-INVENTORY-PREVIEW-GAP-41, 17 October 2026

[UI-INVENTORY-PREVIEW-GAP-41](bugs/UI-INVENTORY-PREVIEW-GAP-41.md): the maintainer found "Character preview
unavailable" in the inventory. Cause: since v0.0.40 the per-race inventory pose model (about 128 KB) was refused
whenever the free hunk gap was under a fixed 2 MiB; Seyda Neen on CHIM leaves 1.96 MiB in the v0.0.41 world, so
the preview never loaded there, in v0.0.41 as shipped too, behind a console line that named missing assets.
Repair on v0.0.42-hud-icons: the load is admitted by its real need (three times the file plus 256 KiB) and the
console names the refusing rule; `aw_inventory_preview_reserve 2` keeps the old rule.

## UI-INVENTORY-ORIGINAL-LAYOUT-42, 17 October 2026

[UI-INVENTORY-ORIGINAL-LAYOUT-42](bugs/UI-INVENTORY-ORIGINAL-LAYOUT-42.md): the A/B of the inventory window with
the original shows no encumbrance bar, no armour rating and a list instead of the icon grid. Registered for the
inventory work after the icons.

## UI-WINDOW-TITLE-BAR-42 and UI-INVENTORY-HEADING-CENTRE-42, 17 October 2026

[UI-WINDOW-TITLE-BAR-42](bugs/UI-WINDOW-TITLE-BAR-42.md): menu windows lack the original title bar (the tiled
frame with the name on a dark plaque). [UI-INVENTORY-HEADING-CENTRE-42](bugs/UI-INVENTORY-HEADING-CENTRE-42.md):
the "Inventory" heading is not vertically centred. Both reported by the maintainer; to be repaired together by
importing the original title-bar art with the HUD art.

## HUD-STATS-29: original weapon and magic boxes, 17 October 2026

[HUD-STATS-29](bugs/HUD-STATS-29.md), persisting (reported a fifth time by the maintainer: the boxes were
placeholders). The HUD weapon and magic boxes are now composed from the original art, imported at build time
from the user's own game data into one lookup table (tools/prepare_icons.py): the item and hand-to-hand icons, the
thin box and bar frames, the bar tracks tinted by Morrowind.ini's fill colours and the magic backdrop behind
enchanted items. New engine state: the selected magic item and per-item enchantment charge (saved), the maximum
charge from the game records, recharge by fMagicItemRechargePerSecond; `aw_magic` selects until a magic menu
exists. Spells cannot be selected yet (no spell list). Evidence in FS-UAE on the v0.0.41 image with this engine
and data: unarmed, steel longsword, the ring selected at full and part charge. See [docs/HUD.md](HUD.md).

## UI-ICONS-INVENTORY-42, 17 October 2026

[UI-ICONS-INVENTORY-42](bugs/UI-ICONS-INVENTORY-42.md): new. The inventory shows icons only for the few staged
items, resampled from 32 to 14 pixels, without the original backdrops. Found in the audit of every UI screen for
missing icons (listed on the bug page); the repair uses the same icon table as the HUD.
## CHIMport by weight: tracker headroom and seabed cells, 17 October 2026

- [TRACKER-RELEASE-HEADROOM-MISSING-42](bugs/TRACKER-RELEASE-HEADROOM-MISSING-42.md): no cell of the v0.0.41 release
  run carried a headroom figure, and older CHIMport results replaced its audits; every figure in the tracker came
  from the v0.0.36-v0.0.40 builders. Fixed in source: each frame's figures go to its cells, and an older result no
  longer replaces a newer full build's audit.
- [TRACKER-AREA-CELLS-RUN-WIDE-42](bugs/TRACKER-AREA-CELLS-RUN-WIDE-42.md): every area of a multi-area build lists
  all of the build's cells (Balmora 811). Open.
- [CHIMPORT-OCEAN-LAND-41](bugs/CHIMPORT-OCEAN-LAND-41.md): the 98 cells are LAND records without height data; the
  tracker no longer takes an open-ocean result for them, and the CHIMport order plans them as seabed cells.
- New: `tools/chim_weight_table.py` and `config/chim-weight-classes.json` write the CHIMport order by weight
  ([CELL_WEIGHTS.md](chim/CELL_WEIGHTS.md)); 611 cells not on CHIM, 479 in the two easy classes on figures of older
  builders, measured again before the batch is built.
## ENGINE-060-MUL64-41, 17 October 2026

[ENGINE-060-MUL64-41](bugs/ENGINE-060-MUL64-41.md): the 68040 engine holds 151 64-bit `MULS.L`/`MULU.L` in 68 engine
functions (GCC's division by constants), which the 68060 traps; the first 68060 scan missed them. The new 68060
mode of the FPU check counts them; the `--engine-cpu 68060` build has none in engine code.

## FPU-SUPPORT-MMULIB-SETPATCH-41, 17 October 2026

[FPU-SUPPORT-MMULIB-SETPATCH-41](bugs/FPU-SUPPORT-MMULIB-SETPATCH-41.md): on an emulated 68060 the MMULib
`68060.library` stops the boot of a disk without `SetPatch` with an alert; with the system's `SetPatch` first the
game boots and runs.
## BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42, 17 October 2026

[BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42](bugs/BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42.md): the build
profiler's sampled timeline counted a child process twice when the child ended between two readings of the
stage's process tree (gates 2519, 2610, 2651 and 2556 failed the timeline bound on loaded hosts). The sampler's
baseline no longer goes down, so the CPU is counted once. Stage CPU, average build-machine threads used and the
perf guard baselines were never affected; sampled per-stage peaks in earlier build profiles may read high.
PERSISTING since TEST-PROFILE-TIMELINE-BOUND-33 (v0.0.33-dev), which widened the bound instead.
## SKY-FLAT-PALETTE-DRIFT-41: palette-matched cloud sky, 17 October 2026

The first repair (sampling the palette from the old Seyda Neen textures) gave a third palette in a real build,
because the Seyda Neen ground textures in the sample changed too; the MiniWind stopped on the new image-step
refusal instead of shipping a flat sky. Replaced: the cloud sky is now converted for whatever palette the build
has, by nearest colour; nothing else is converted again and the palette stays the v0.0.41 one. Checked on the
real v0.0.41 palette in FS-UAE (clouds at noon and at dusk).

## SKY-FLAT-PALETTE-DRIFT-41, 17 October 2026

[SKY-FLAT-PALETTE-DRIFT-41](bugs/SKY-FLAT-PALETTE-DRIFT-41.md): the maintainer asked where the clouds and the sun had gone.
Every exterior of v0.0.40 and v0.0.41 has a flat sky without clouds (the sun disc, moons and day/night colours still
work). Cause: 01bdf9f widened the Seyda Neen scenery scope (107 to 183 textures), the sampled scene palette changed,
the shared cloud sky refused the unknown palette and the image fell back, with one warning line, to the converted
maps' one-colour placeholder. Fix on branch v0.0.42-sky: the palette is sampled from the historic scope only
(checked on the real v0.0.41 scenery stage: the v0.0.38 palette exactly), and the image step refuses the fallback.
Build and in-game check pending.

## Register audit: open means open, 16 October 2026

A read-only audit of every open entry against the git history (fix commit in a release line, its test at the current
head, release notes, later reports) was applied, each edit checked again against the current tree first. Before: 738
open, 95 fixed, 9 closed of 842 entries. After: 416 open, 380 fixed, 46 closed.

- 285 entries closed as fixed with the first release or numbered build whose source contains the fix (most in
  v0.0.32 to v0.0.36; their statuses still said "fixed in source, not shipped"). Fixed entries first found in v0.0.33
  or earlier and not persisting moved to the archive, as the rotation rule says.
- 37 closed: 26 superseded by CHIM (legacy Seyda, Balmora, Arena frame and region-map paths), 7 repaired outside the
  source tree or not AmiWind bugs, 4 duplicates. The two gate failures of the duplicate TEST-PARALLEL-ORDER-FLAKY-36
  and gate 1051 are now reports on [TEST-PARALLEL-ORDER-LOAD-33](bugs/TEST-PARALLEL-ORDER-LOAD-33.md).
- 204 open entries got a dated status line: what shipped, what is still missing, or what the maintainer has to decide.
  Nine entries whose fix shipped but which came back after an earlier fix stay open under the persisting rule.
- Two proposed closures were not applied because the bug was reported again after the audit:
  [BUILD-CHIM-STAGE-SERIAL-TAIL-36](bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md) and
  [BUILD-PROGRESS-ETA-BASIS-36](bugs/BUILD-PROGRESS-ETA-BASIS-36.md) (both again in v0.0.41-dev5).

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: whole-world metadata binding failed because tutorial barrel reference 172851 lacked its original CELL, while the original audit records [-2,-9]. A narrow source correction restores only that missing field before capture, rejecting nonempty wrong cells and every other identity/transform mismatch. Fifty focused Seyda/ownership checks pass, including three new semantic regressions. The preceding 4,247-test full-suite pass remains historical; the repaired world is pending. The prepared Linux source kit is held and undelivered. Native, image/package and playtest acceptance remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1 image integration follow-up: added Seyda dependency numbers and model digests are checked against the world-index-bound source manifest before source-carrier static parity includes them. Frames without supplements retain prior behavior. The focused ownership/apron module now passes 33 checks, including five new semantic regressions and missing/rebound-model rejection. The issue remains OPEN; exact world rebuild, held-boundary/native and image/package checks remain pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: a source repair supplements only missing Seyda apron dependencies using the included original-cell owner's exact compiled mesh and textures, preserving original identity and unique ownership while translating frame-local origins. It targets rock reference 251397 and shell reference 461804; 32 focused ownership/apron checks pass. The rebuilt world and held boundary/native checks remain pending. Separately, independent normal interior/actor/UI conversion completed 2,451 files with unchanged source and inputs; it is not image, native or package acceptance. CHIM coverage states are unchanged. Earlier full-suite and world results remain bound to their preceding source; changed apron acceptance is pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: exact source validation completed 4,242 tests (4,236 passed, three Windows-only skips and three Census expected failures), with zero failures/errors; the matching engine compiled. The completed 369-frame world passed structural/source, modeled heap, host zone-walk and scoped stair gates. Of 547 boundary comparisons, 544 measured agreement and three remain held (237, 241, 242). Of 36 sampled models, 22 have matching face counts and unique face correspondence; 14 differ in collision-only versus visual representation and require payload/sprite/native review. These measurements do not establish visual severity or universal equivalence. Native captures, independent interior conversion, image assembly/readback and package acceptance remain pending; coverage states are unchanged. Stair evidence retains 15,348 advisory findings despite zero blocking failures.

15 October 2026 — The preceding v0.0.41 source snapshot completed 4,242 tests: 4,236 passed, zero failures/errors, three Windows-only skips and three exact Census expected failures; source was unchanged. This does not validate the subsequent v0.0.41-dev1 version alignment or establish image/native/package acceptance.

15 October 2026: active preparation now targets v0.0.41-dev1. The planned final release title is **v0.0.41: Collisions And Boundaries**. Earlier source snapshots, checks and findings retain their recorded version identities; they do not establish acceptance of this development candidate. Matching source validation, completed image assembly/readback, native checks, packaging and delivery remain separate gates. See the [current development candidate](RELEASE-v0.0.41-dev1.md).

[BUILD-INVENTORY-PALETTE-41](bugs/BUILD-INVENTORY-PALETTE-41.md) — 15 October 2026, v0.0.41 source candidate: image assembly prepares inventory before the sky palette pass, which rejected current AWIC icons and AWI2/AWST metadata as unknown images. The source repair validates each inventory format at its exact path, remaps only icon pixels and preserves metadata bytes. Scoped evidence contains 15 passing palette checks and 2 passing inventory-asset checks on matching unchanged source. Actual image assembly, native verification, packaging and shipment remain pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41 source candidate: the 941 world stopped at the unchanged ownership guard because ten explicitly deferred Seyda references reappeared through a named-town apron. The candidate applies the existing exact owner dispositions to named and regional neighbours alike. All ten original deferred IDs are verified and 38 focused checks pass. Fresh affected-world conversion and renewed boundary/memory checks remain pending; no coverage, native, package or maintainer acceptance is promoted.

[CHIM-MODEL-ARENA-RESERVE-41](bugs/CHIM-MODEL-ARENA-RESERVE-41.md) — 15 October 2026: exact allocation and predecessor-world checks remain separately recorded. The later 941 world stopped at its ownership guard because named aprons bypassed ten existing deferred-owner dispositions. The source-only disposition repair passes 38 focused checks; fresh world, boundary/model review and native/package acceptance remain pending.

[CHIM-RECIPE-APRON-SCOPE-41](bugs/CHIM-RECIPE-APRON-SCOPE-41.md) — 15 October 2026, v0.0.41 candidate: recipe repair converted all four affected frames with structural PASS. Three still failed the unchanged memory gate (peaks 6,957,632; 6,939,952; 6,644,768 bytes for (10,0), (10,1), (9,2)); (11,0) passed at 5,875,568 bytes. The separate placed-model reserve repair passes all four on identical world bytes. A complete successor world and recipe/model/sprite equivalence and native checks remain pending.

15 October 2026: exact-source validation completed 4,231 tests: 4,225 passed, three Windows-only skips and three tracked Census expected failures. The 71 focused tests and original-data readback across nine frame positions passed, consistently hiding 33 of 158 original references at stronghold state 6 while preserving unknown scripts. All 243 player resources are reusable after exact producer, input and file verification. Complete combined-world conversion, native comparison, packaging and shipment remain pending; coverage counts are unchanged.

## BUILD-STAIR-GATE-OOM-42, 17 October 2026

[BUILD-STAIR-GATE-OOM-42](bugs/BUILD-STAIR-GATE-OOM-42.md): the Vivec city MiniWind stopped in the CHIM stair
gate after about 20 minutes: a walk worker was killed (out of memory at 30 GiB) and the pool broke. The gate
walked the whole Vivec frame (83,236 steps and ramps) on 8 workers.

## INTERIOR-SPAWN-UNDERWATER-41, 17 October 2026

[INTERIOR-SPAWN-UNDERWATER-41](bugs/INTERIOR-SPAWN-UNDERWATER-41.md): seven Vivec underworks rooms used the
canal grate (under the water) as their own spawn, so loading the room by name put the player in the water.
The spawn is now the first arrival above the water; doors were never affected.
