# BUILD-CHIM-CELLS-PRIVATE-LIST-47: The releases' CHIM cell list was not in the source tree; public builds had no CHIM exterior cells

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 11 times; something has to be done

- Reported with v0.0.36 at 2026-10-11 (time not recorded): Built with the coastline selection of the v0.0.36-dev5 tracker file, kept outside the source tree
- Reported with v0.0.38 at 2026-10-13 (time not recorded): Built with the full selection of 310 cells (CSV), kept outside the source tree
- Reported with v0.0.39-rc1 at 2026-10-14 (time not recorded): Built with the same 310-cell CSV, kept outside the source tree
- Reported with v0.0.41 at 2026-10-16 (time not recorded): Built with the dev5 regional cell list, kept outside the source tree
- Reported with v0.0.42 at 2026-10-17 (time not recorded): Built with the release cell list without 98 seabed cells, kept outside the source tree
- Reported with v0.0.43 at 2026-10-19 (time not recorded): Built with CHIMport batch 5 (1,394 cells), kept outside the source tree
- Reported with v0.0.44 at 2026-10-19 (time not recorded): Built with CHIMport batch 5 (1,394 cells), kept outside the source tree
- Reported with v0.0.45 at 2026-10-20 (time not recorded): Built with CHIMport batch 5 (1,394 cells), kept outside the source tree
- Reported with v0.0.46 at 2026-10-20 (time not recorded): Built with CHIMport batch 5 (1,394 cells), kept outside the source tree
- Reported with v0.0.47-dev2 at 2026-10-21 (time not recorded): Built with CHIMport batch 5 (1,394 cells), kept outside the source tree; found while checking the dev2 build options
- Reported with v0.0.48-rc1 at 2026-10-24 05:05 +0300: PERSISTING: the rc1 image was built with the private batch5 cell list (same 1348 CHIM cells as the in-tree default); the release guard refuses it

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 11 October 2026, in v0.0.36 |
| Where | tools/build.py --chim-regions default; the release build commands |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.47 |
| Severity | high: The public builder never built the CHIM exterior of a release: GitHub users got the legacy region maps. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_21_v0.0.47-dev2_dev2-try3_c20bc0d8 |
| From commit | source c20bc0d, engine c20bc0d, CHIM world c20bc0d |
| CHIM engine version | CHIM unknown, engine c20bc0d, world format unknown |
| Unknown because | found in the build options, CHIM version not material |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.47-dev2 (21 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 11 times; something has to be done](#persisting-reported-11-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

A default build from the public repository put no exterior cell on CHIM. Every release image since v0.0.36 was
built with a list of CHIM cells that lived only on the project's own build machine (`--chim-regions @FILE`), and
`--chim-regions` was an experimental option, off by default. So the public builder could not reproduce a single
release: a GitHub user's build converted the whole open world into the legacy region maps instead of the CHIM
exterior the release notes describe. That is the path a tester's default build took when it stopped at
world-scenery ([BUILD-LAVA-TERRAIN-BUDGET-38](BUILD-LAVA-TERRAIN-BUDGET-38.md)), a consequence of this bug.

## Where

`tools/build.py` (`--chim-regions`, `resolve_chim_regions`), the release build commands, and the project rule that
the public builder builds the whole game from the user's own data with no private input.

## How it happened

The cell lists were made with `tools/chim_cell_list.py` on the build machine while the CHIMport batches grew, and
each release build named its list there:

- v0.0.36: the coastline selection of the v0.0.36-dev5 tracker file;
- v0.0.38 and v0.0.39-rc1: the full selection of 310 cells (a CSV);
- v0.0.41: the dev5 regional cell list;
- v0.0.42: the release cell list without the 98 seabed cells held back;
- v0.0.43, v0.0.44, v0.0.45, v0.0.46 and v0.0.47-dev2: CHIMport batch 5 (1,394 cells).

None of these files was committed. `--public-defaults` (the from-scratch check) rightly refused a cell list outside
the source tree, so the check could only run without the list, which is a different build.

## Why it was not caught

The from-scratch check compares a clean public build with the release payload; it was not run with the release's
own options, and no test checked that the default CHIM build plan holds the release cells.

## Reproduction

Build from the public repository with the default options: the build log has no `CHIM regions` line and the world
manifest lists every exterior cell as a legacy region map.

## Repair

Branch v0.0.47-chim-cells: the cell list is in the source tree as `config/chim-cells.json` (format
`aw-chim-cells-1`, listed in `tools/release-files.json`): every exterior cell of the game data (1,404) plus the 5
open-sea cells without a cell record, 1,409 in all. A full `--builder chim` build without `--chim-regions` takes it,
checked against the public tracker reference `docs/chim/cell-progress-reference.json` (the default of
`--chim-regions-status`). `--chim-regions none` builds without CHIM region cells (the earlier default, kept
selectable); `--chim-regions @FILE` and the named sets still work.

## Verification

The builder's read-only plan with the v0.0.47-dev2 options and no `--chim-regions` resolves 1,348 region cells
(197 seabed, 1,132 land, 19 open sea), the same cell string and the same chim stage options as dev2's explicit list;
the 15 cells added to the list lie wholly inside a town frame (Balmora, Vivec) and are listed as dropped, so they are
on CHIM as part of their town. Tests: `tests/test_chim_regions.py` (the default is the in-tree list, the same cells
as naming the file, `none`, no default for legacy or MiniWind builds), `tests/test_clean_build.py`
(`--public-defaults` accepts the default list).

## Prevention

The release cells are a file in the source tree and the builder default; a release build that names a cell list
outside the tree is refused by `--public-defaults`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the user's own data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-ACTOR-CONTACT-REGRESSION-38](BUILD-ACTOR-CONTACT-REGRESSION-38.md): Full dev3 rebuild rejects116 previously grounded actors
- [BUILD-ACTOR-MODEL-UNSUPPORTED-48](BUILD-ACTOR-MODEL-UNSUPPORTED-48.md): A Balmora build-speed measurement stopped on Unsupported actor model
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
- [CHIM-FRAME-ALONE-FLAMES-48](CHIM-FRAME-ALONE-FLAMES-48.md): A town frame map read alone stops in its flames step: the frame-alone world holds its frames by index, the flames lookup walked them as a list
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

<!-- END GENERATED CATEGORY -->
