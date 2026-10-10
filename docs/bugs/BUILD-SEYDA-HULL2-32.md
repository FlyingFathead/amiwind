# BUILD-SEYDA-HULL2-32: From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | bsp stage, Seyda Neen full-town map (tools/prepare_quake.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.28, v0.0.32-dev (last seen) |
| Severity | critical: From-scratch builds stop at qbsp because hull 2 exceeds the clipnode limit; release blocker for the builder. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the first from-scratch build with the repository builder (v0.0.32-dev1 attempt). Release blocker for the public builder (MANDATORY from-scratch rule).

## Symptom

The builder's `bsp` stage stops: qbsp reports "Clipnode count exceeds bsp 29 max (68655 >
65520)" for hull 2 of the Seyda Neen full-town standing collision map. The builder never uses
hull 2, but qbsp aborts on it. v0.0.26 and v0.0.27 pass; v0.0.28 to today fail identically.

## Where

`tools/prepare_quake.py` (`town_ground_triangles`, `required_edge_samples` added in v0.0.28:
69 more terrain brushes) and the qbsp call for that map.

## How it happened

v0.0.28 added edge samples to the town ground; hull 2 crossed the limit.

## Why it was not caught

No from-scratch build was run between releases; release images were patched up from older images.

## Reproduction

Run `tools/build.py` from scratch with your own data.

Cost signals from the fix: the v0.0.28 edge samples grow the full-town standing hull 1 from
19,156 to 35,292 nodes (+84 %), and the full-town map's hull 0 is at 31,162 of 32,767 nodes (95 %).

## Repair

Fixed in source (v0.0.32-dev, a97861b): the engine uses hulls 0 and 1 only (hull 2 is never
traced: world.c selection rule, every QuakeC and engine trace box fits hull 1). The standing-hull
intermediate is compiled as BSP2 (32-bit indices, no overflow) and only its hull 1 is grafted;
`rebuild_world_hull` is the one standing-hull path for every map (the region converter's inline
copy now calls it). The graft uses the engine's real limit (65,520) with unsigned 16-bit
children, as the engine reads them. A new gate, `check_engine_hulls`, fails a map only when
hull 0 or 1 breaks an engine limit. The v0.0.28 edge samples are kept; maps that already fit
are byte-identical. Residual risk: each map's own base compile is still BSP29 with all hulls.

## Verification

From-scratch build (25 min 38 s) passes `bsp`: the full-town Seyda Neen map has 55,632
clipnodes and 31,162 nodes, within the engine limits. Tests: `tests/test_engine_hulls.py`
(engine contract, synthetic grafts, BSP2/BSP29 intermediates graft to identical bytes).

## Prevention

A periodic from-scratch build (mandatory project rule) and a builder test for hull limits.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the owner's data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [BUILD-SEYDA-CULL-STABLE-32](BUILD-SEYDA-CULL-STABLE-32.md): From-scratch builds stop in Seyda Neen terrain culling (fragment not repeat-stable)
- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells

<!-- END GENERATED CATEGORY -->
