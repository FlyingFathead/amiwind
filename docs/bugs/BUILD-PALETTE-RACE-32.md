# BUILD-PALETTE-RACE-32: Census and world flora assets can run together on the same palette file

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | build stages world-flora-assets and census (shared palette file) |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Flora sprites may be made from either palette, so output can vary between runs. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the build profiler work (source-checked, not observed).

## Symptom

`world-flora-assets` depends only on `intro` and reads `intro-scene/id1/gfx/palette.lmp`; `census` also
runs right after `intro` and rewrites that file in place (truncate, then write). The flora sprites can
therefore be made from the palette before or after Census changes it, or stop on a half-written file.

## Where

`tools/build_parallel.py` stage dependencies; `tools/ui_palette.py` `reserve`.

## How it happened

Dependencies were declared by data flow at the time; Census later started rewriting the palette.

## Why it was not caught

Stages were never profiled or checked for shared outputs.

## Reproduction

Parallel build where both stages overlap; compare sprite hashes between runs.

## Repair

On the v0.0.32 development line (not shipped): `world-flora-assets` and `hand-catalog` (which also
read the scene palette) depend on `census`; `ui_palette` writes the palette, lookups and receipt
whole (temporary file, then rename). Flora sprites are now always made from the Census palette,
so their bytes can differ from builds where flora ran first.

Expected difference (8 October 2026): flora sprite bytes of a from-scratch build can differ from
earlier v0.0.32-dev1 builds in which flora ran before Census. From-scratch comparisons against
those builds list this as an expected difference, not a regression.

## Verification

`tests/test_build_parallel.py`: every stage that reads `intro-scene/id1/gfx/palette.lmp` runs after
Census or before it starts; in-place rewrites leave whole files only.

## Prevention

The profiler's output manifests mark stages that overlap on a path; a test that no two
concurrent stages write or read-while-written the same path.

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
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts

<!-- END GENERATED CATEGORY -->
