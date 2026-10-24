# BUILD-HEAP-RECEIPT-TUPLES-32: The image step refuses its own final heap receipt (tuples against lists)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev2 |
| Where | image step final heap receipt (tools/build_aga.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.32 |
| Severity | critical: The image step refuses its own heap receipt after about 20 minutes, so no image is made. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | v0.0.32-dev2 |
| From commit | source and engine 2af54eb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (2ca08b5), not shipped at the time of writing. Found by the
v0.0.32-dev2 image build.

## Symptom

The dev2 image step stopped at the very end, after about 20 minutes, with "Saved final heap
receipt differs from the supplied audit".

## Where

`tools/build_aga.py` (`audit_world_map_heap_with_receipt`, `bind_heap_report`),
`tools/compact_harvest_heap.py`.

## How it happened

Since the harvest builder step (BUILD-HARVEST-NOT-BUILT-32), the heap audit's
`harvest_external_profile.fingerprint_entries` held Python tuples (made by
`compact_harvest_heap`). Saved as JSON they come back as lists. `bind_heap_report` compares the
audit held in memory with the saved receipt, so every tuple counted as a difference and the
binding refused. dev1 had no harvest catalogues, so the list was empty and nothing tripped.

## Why it was not caught

The harvest tests used synthetic data and never ran the final heap binding with a non-empty
harvest profile.

## Reproduction

On the real dev2 maps: 389 differences between the in-memory audit and the saved receipt, all
tuple against list.

## Repair

In source (2ca08b5): `audit_world_map_heap_with_receipt` returns exactly the saved JSON, and the
fingerprint entries are built as lists.

## Verification

`tests/test_heap_receipt_roundtrip.py` (`test_returned_audit_equals_saved_receipt_with_tuples`,
`test_compact_harvest_fingerprint_entries_are_lists`). A finished dev2 image is pending.

## Prevention

The round-trip test; the finalize stages bind to the saved receipts, not to in-memory objects.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the user's own data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-ACTOR-CONTACT-REGRESSION-38](BUILD-ACTOR-CONTACT-REGRESSION-38.md): Full dev3 rebuild rejects116 previously grounded actors
- [BUILD-ACTOR-MODEL-UNSUPPORTED-48](BUILD-ACTOR-MODEL-UNSUPPORTED-48.md): A Balmora build-speed measurement stopped on Unsupported actor model
- [BUILD-CHIM-CELLS-PRIVATE-LIST-47](BUILD-CHIM-CELLS-PRIVATE-LIST-47.md): The releases' CHIM cell list was not in the source tree; public builds had no CHIM exterior cells
- [BUILD-CHIM-VIS-VARIANT-SORT-42](BUILD-CHIM-VIS-VARIANT-SORT-42.md): CHIM world visibility step stops on mixed variant keys (model numbers beside terrain tile variants)
- [BUILD-DIAGNOSTIC-PALETTE-38](BUILD-DIAGNOSTIC-PALETTE-38.md): Lava diagnostic mixes conversion and runtime palettes
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-FLORA-BSP-BYTES-38](BUILD-FLORA-BSP-BYTES-38.md): Exterior flora BSPs exceed the storage budget during the full build
- [BUILD-INVENTORY-PALETTE-41](BUILD-INVENTORY-PALETTE-41.md): Inventory icons and metadata stop the sky palette image pass
- [BUILD-LAVA-TERRAIN-BUDGET-38](BUILD-LAVA-TERRAIN-BUDGET-38.md): Detailed lava terrain exceeds region storage budget
- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread
- [BUILD-MINIWIND-SEYDA-COMPILE-42](BUILD-MINIWIND-SEYDA-COMPILE-42.md): A CHIM MiniWind of another town stops at its bsp stage: it compiles the whole Seyda Neen town, which exceeds the BSP29 node limit
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-NPC-GALLERY-SKIPPED-DEV-42](BUILD-NPC-GALLERY-SKIPPED-DEV-42.md): Development and playtest builds leave out the NPC gallery to save build time
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md): Player body fitting stops before trying smaller meshes
- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- [BUILD-RELEASE-READINESS-HIDDEN-41](BUILD-RELEASE-READINESS-HIDDEN-41.md): A development build did not say what a final would refuse: dev5 passed with a waiver, an accepted plant loss and no NPC gallery
- [BUILD-ROOM-SHELL-WRITER-UNPINNED-48](BUILD-ROOM-SHELL-WRITER-UNPINNED-48.md): The room shell form writes its conversion report without pinned encoding and line ends
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
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
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- [VIVEC-ROOM-PRECACHE-LIMIT-42](VIVEC-ROOM-PRECACHE-LIMIT-42.md): Telvanni Tower was listed again although its map needs 257 model precaches; the engine holds 256
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder

<!-- END GENERATED CATEGORY -->
