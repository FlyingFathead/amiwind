# Bug journal

_Last updated with AmiWind v0.0.44-dev1 (19 October 2026)._

<!-- contents start -->
## Contents

- [TRACKER-CHIM-COUNT-STALE-44: the tracker counted audits, not the build, 19 October 2026](#tracker-chim-count-stale-44-the-tracker-counted-audits-not-the-build-19-october-2026)
- [INTERIOR-MORAG-TONG-FPS-43: every room installer copies its plant sprites, 19 October 2026](#interior-morag-tong-fps-43-every-room-installer-copies-its-plant-sprites-19-october-2026)
- [NPC-HEAD-DECIMATION-33: the player body falls back to the previous head reducer, 19 October 2026](#npc-head-decimation-33-the-player-body-falls-back-to-the-previous-head-reducer-19-october-2026)
- [CHIM-ROCKS-OPEN-SHELLS-43 and CHIM-CROSSING-SLUGGISH-43 registered, 19 October 2026](#chim-rocks-open-shells-43-and-chim-crossing-sluggish-43-registered-19-october-2026)
- [CHIM-BITTERCOAST-HEAP-SHAPEGUARD-43: two Bitter Coast frames over the heap zone, 19 October 2026](#chim-bittercoast-heap-shapeguard-43-two-bitter-coast-frames-over-the-heap-zone-19-october-2026)
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
