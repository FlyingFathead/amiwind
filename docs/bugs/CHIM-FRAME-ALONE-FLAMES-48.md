# CHIM-FRAME-ALONE-FLAMES-48: a town frame map read alone stops in its flames step

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:suite |
| First noticed | 23 October 2026, in v0.0.48-rc1 |
| Where | tools/chim/frame_map.py frames_at (add_flames of build and build_docks) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48 |
| Severity | high: every chim-town stage's frame map stops: the build cannot finish |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 7f5d043, engine 7f5d043, CHIM world 7f5d043 |
| CHIM engine version | CHIM 0.2.1, engine 7f5d043, world format 0.12 |
| Platform or emulator | not in game (a builder or gate check) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

## Status: 23 October 2026

Fixed for v0.0.48 on the v0.0.48-rc1 line. Found by gate 3745 (the v0.0.48-rc1 merge of four fix branches): 11 tests
of `tests/test_chim_frame_map.py` and `tests/test_chim_exterior_flames.py` stopped with the same `TypeError`.

## Symptom

`chim.frame_map.build` and `build_docks` (the chim-town stages' frame maps) stopped in `add_flames`:
`frames_at` raised `TypeError: 'int' object is not subscriptable` for every town frame map made without a loaded
CHIM world.

## How it happened

BUILD-POOL-TINY-UNITS-48 made the chim-town stages read only their own frame (`frame_alone`), which returns the
frames as `{world index: frame row}`. CHIM-EXTERIOR-FLAMES-MISSING-48 had added the flames step, whose lookup
(`frames_at`) walked the frames as a list: over a dict it walked the indices. The two met on the
v0.0.48-fix-build-speed branch, which fails the same tests alone.

## Repair

`frames_at` takes either form: a list (positions are list positions) or `frame_alone`'s dict (positions are its world
indices). Every frame map maker is unchanged.

## Verification

`tests/test_chim_frame_map.py` and `tests/test_chim_exterior_flames.py` (75 tests) pass; they build the town and docks
frame maps from a world folder, which takes the frame-alone path.

## Prevention

Those tests; the gate runs them on every merge.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the user's own data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-ACTOR-CONTACT-REGRESSION-38](BUILD-ACTOR-CONTACT-REGRESSION-38.md): Full dev3 rebuild rejects116 previously grounded actors
- [BUILD-ACTOR-MODEL-UNSUPPORTED-48](BUILD-ACTOR-MODEL-UNSUPPORTED-48.md): A Balmora build-speed measurement stopped on Unsupported actor model
- BUILD-CACHE-NO-RETENTION-55 (no report page): The build cache keeps every entry forever: about 603 GB nothing recent uses
- [BUILD-CHIM-CELLS-PRIVATE-LIST-47](BUILD-CHIM-CELLS-PRIVATE-LIST-47.md): The releases' CHIM cell list was not in the source tree; public builds had no CHIM exterior cells
- BUILD-CHIM-EARLY-CHECK-POOL-55 (no report page): The chim stage's early frame checks forked a worker pool of their own outside the stage's memory allowance
- [BUILD-CHIM-VIS-VARIANT-SORT-42](BUILD-CHIM-VIS-VARIANT-SORT-42.md): CHIM world visibility step stops on mixed variant keys (model numbers beside terrain tile variants)
- [BUILD-DIAGNOSTIC-PALETTE-38](BUILD-DIAGNOSTIC-PALETTE-38.md): Lava diagnostic mixes conversion and runtime palettes
- [BUILD-DISK-NEED-UNKNOWN-52](BUILD-DISK-NEED-UNKNOWN-52.md): A public build can die halfway when the disk fills: the only space check runs once at the start, against a fixed 20 GiB, not what the release really takes
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-FLORA-BSP-BYTES-38](BUILD-FLORA-BSP-BYTES-38.md): Exterior flora BSPs exceed the storage budget during the full build
- BUILD-GUARD-BLIND-NO-CGROUP-55 (no report page): Without a container memory limit the build's memory guard, its alarm and every pool's memory governor saw no memory at all
- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-INVENTORY-PALETTE-41](BUILD-INVENTORY-PALETTE-41.md): Inventory icons and metadata stop the sky palette image pass
- [BUILD-LAVA-TERRAIN-BUDGET-38](BUILD-LAVA-TERRAIN-BUDGET-38.md): Detailed lava terrain exceeds region storage budget
- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread
- [BUILD-MINIWIND-SEYDA-COMPILE-42](BUILD-MINIWIND-SEYDA-COMPILE-42.md): A CHIM MiniWind of another town stops at its bsp stage: it compiles the whole Seyda Neen town, which exceeds the BSP29 node limit
- BUILD-MINIWIND-SEYDA-KELP-INDEX-54 (no report page): A Seyda Neen MiniWind can never pass: the chim-town-seyda stage stops because the kelp additions need the original scenery index, which a MiniWind plan does not build
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-NPC-GALLERY-SKIPPED-DEV-42](BUILD-NPC-GALLERY-SKIPPED-DEV-42.md): Development and playtest builds leave out the NPC gallery to save build time
- BUILD-OOM-DEGRADE-NOT-DIE-54 (no report page): A worker killed for memory broke its stage's pool and failed the whole build
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md): Player body fitting stops before trying smaller meshes
- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- [BUILD-RELEASE-READINESS-HIDDEN-41](BUILD-RELEASE-READINESS-HIDDEN-41.md): A development build did not say what a final would refuse: dev5 passed with a waiver, an accepted plant loss and no NPC gallery
- [BUILD-ROOM-SHELL-WRITER-UNPINNED-48](BUILD-ROOM-SHELL-WRITER-UNPINNED-48.md): The room shell form writes its conversion report without pinned encoding and line ends
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
- BUILD-STAGE-KEY-NPC-MODULE-53 (no report page): The CHIM and town stages are keyed on the whole of src/mwad/npc.py, so a change to four NPCs in outfit() re-keys the CHIM world (22 of 43 stages, about 7 hours)
- [BUILD-TESTS-UNLISTED-48](BUILD-TESTS-UNLISTED-48.md): Seven test files of the v0.0.48 fix branches were not on the release list, so no gate ever ran them
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-TORCH-CREATURE-RESIDENT-42](BUILD-TORCH-CREATURE-RESIDENT-42.md): Image step stops in the torch guard on Vivec, an interior creature resident placed as an NPC entity
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [CHIM-LAVA-DUPLICATE-VERTEX-40](CHIM-LAVA-DUPLICATE-VERTEX-40.md): Float32 duplicate vertices falsely fail lava surface coverage
- [CHIM-OCEAN-ROUTING-UNNAMED-41](CHIM-OCEAN-ROUTING-UNNAMED-41.md): The world-terrain stage refused ocean routing cells without naming a cell or which rule failed
- [CHIM-ROOM-SHELL-ACTORS-EARLY-48](CHIM-ROOM-SHELL-ACTORS-EARLY-48.md): The scene stage actor check measured residents of shell rooms, which have no collision until the image: 110 refused
- [CHIM-VISIBILITY-APRON-SCOPE-41](CHIM-VISIBILITY-APRON-SCOPE-41.md): Fixed stronghold visibility rejects regional aprons
- [CHIM-VIVEC-FRAME-WIDE-41](CHIM-VIVEC-FRAME-WIDE-41.md): Vivec's CHIM frame owns a 7x7 block of whole cells: Ebonheart and Seyda-side land sit in the city frame, three residents unsupported
- [CHIM-WINDOW-TOWER-SUPPORT-41](CHIM-WINDOW-TOWER-SUPPORT-41.md): Thatched tower omitted from decorative window facade support
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [ENGINE-FRAME-REFUSE-PROTOTYPE-48](ENGINE-FRAME-REFUSE-PROTOTYPE-48.md): The engine build stops on a missing prototype: AW_SceneFrameRefuse has no declaration
- PREFLIGHT-GUARD-UNSTAMPED-NPCS-48 (no report page): The payload preflight guard count refused census.bsp: its three NPCs get their source identity later in the image step
- [RELEASE-FINAL-LINE-STALE-RC-48](RELEASE-FINAL-LINE-STALE-RC-48.md): The v0.0.48 final line was cut from an older rc1 head than the image: it lacked the two layout fixes the shipped image was built with
- RELEASE-GUARD-NO-FROMSCRATCH-RULE-54 (no report page): No release guard rule requires a from-scratch build: v0.0.52 and v0.0.53 shipped without one
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- [VIVEC-ROOM-PRECACHE-LIMIT-42](VIVEC-ROOM-PRECACHE-LIMIT-42.md): Telvanni Tower was listed again although its map needs 257 model precaches; the engine holds 256
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- BUILD-POOL-TINY-UNITS-48 (no report page): Stages hand their pools units too small to keep the cores busy (CHIM slices, the town stages)
- [CHIM-EXTERIOR-FLAMES-MISSING-48](CHIM-EXTERIOR-FLAMES-MISSING-48.md): CHIM exteriors draw no fire: campfires, braziers, fire pits and flame lamps outdoors have no flame animation

<!-- END GENERATED CATEGORY -->
