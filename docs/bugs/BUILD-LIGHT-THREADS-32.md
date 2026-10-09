# BUILD-LIGHT-THREADS-32: ericw light is not byte-reproducible with more than one thread

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | ericw light calls in the builder (tools) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Multi-threaded light is not byte-reproducible, breaking from-scratch comparison. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (e77370a), not shipped at the time of writing. Found by the
image-parallel work ([BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md)).

## Symptom

ericw-tools `light` 0.18.1 writes faces and lightmaps in a thread-dependent order: two runs of the
same map with 2-8 threads differ in the faces and lighting lumps. One thread is reproducible; `vis`
is identical for any thread count. Multi-threaded light therefore breaks the file-by-file
comparison of a from-scratch build ([BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md)).

## Where

Every builder step that runs `light -threads N` with N above 1. The Seyda Neen regions and the
Balmora repair already run one light thread per map on the v0.0.32 development line. Still
multi-threaded: `tools/build_gallery.py`, `tools/prepare_census.py`, `tools/prepare_interior.py`,
`tools/prepare_mesh_bsp.py`.

## How it happened

Light threads were set from `--jobs` (or fixed counts) for speed, without a reproducibility check.

## Why it was not caught

No test compared two builds of the same map with different thread counts.

## Reproduction

Light one map twice with `-threads 4` and compare the faces and lighting lumps.

## Repair

In source (e77370a): one shared helper, `tools/vis_options.py` (`LIGHT_THREADS = 1`,
`light_args()`), supplies the thread argument to all 11 light calls in the builder, including the
four tools above; their map-level pools stay parallel. Cost of one thread against 16 is negligible
(Seyda Neen 3.8 s against 3.6 s).

Expected differences: maps that were lit with `--jobs` threads before (the gallery plane, Census,
the prison and the Seyda Neen mesh scene) differ from earlier builds, which were not reproducible
either. The from-scratch comparison against v0.0.31 and dev1 must list these as expected.

## Verification

`tests/test_build_jobs_workers.py` `test_light_compiles_single_threaded`: `LIGHT_THREADS` is 1
and a static scan finds every light call in the builder taking its arguments from `light_args`
(mutation-checked: a call with its own thread count fails it). A from-scratch build is pending.

## Prevention

`tests/test_build_jobs_workers.py` fails when a map light compile becomes multi-threaded; extend it
to the four tools.

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
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
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

- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts

<!-- END GENERATED CATEGORY -->
