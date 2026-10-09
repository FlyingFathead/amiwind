# BUILD-TMP-SCRATCH-33: Builder stages build, load or store files in the system temp directory

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | builder stages calling tempfile with no directory (zone_sim, prepare_video, import_town) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | high: /tmp in the build container is a noexec, RAM-backed tmpfs: code loaded from it fails and gigabytes stored there exhaust memory. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-tmp-audit, not shipped at the time of writing.

Provenance: raised by the owner after CHIM-ZONE-TMP-NOEXEC-33 ("isn't /tmp kind of a bad place"); audit of
tools/, src/, the build scripts and the CI workflow at the v0.0.33-dev1-build head.

## Symptom

None of its own beyond [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): a stage that loads code from
`/tmp` stops in the build container. The same habit would also put large files in memory.

## Where

Builder stages that called `tempfile` without a directory (the system temp directory). Audit table:

| Use | Class | Result |
| --- | --- | --- |
| tools/chim/zone_sim.py: host shared object built and loaded | (a) executes code | scratch folder (already moved by CHIM-ZONE-TMP-NOEXEC-33; now the shared helper); the unused `library_in_temp` removed |
| tools/prepare_video.py: raw RGB frames and PCM of a movie (up to about 3 GB) | (b) large | scratch folder |
| tools/prepare_world_ui.py: terrain survey arrays and map image | (b) large | scratch folder |
| tools/import_town.py: pickled town context for the region pool | (b) large | scratch folder |
| tools/build_parallel.py `captured`: stdout of each pool item | (b) unbounded log text | scratch file |
| tools/build_aga.py, build_versions.py, check_world_map_heap.py, collision_bsp.py, prepare_area.py, prepare_intro.py, prepare_media_assets.py, prepare_npcs.py | (c) small, nothing executed from them | unchanged, audited by name and count in the test |
| tools/run_tests.py: test worker plan, event and log files | (c) small | unchanged |
| tools/fsuae_headless_probe.py: fixed `/tmp` paths in its own throwaway worker container | (c) diagnostic | unchanged |
| .github/workflows/source-check.yml: tools installed under `$RUNNER_TEMP` | (c) hosted CI runner, not the build container | unchanged |
| tools/compare_bsp_trials.py, gallery_cache.py, music_catalogue.py, optimize_world_maps.py, package_opening.py, fetch_*.py, release.py, setup_windows.py and others | next to their destination (`dir=`) | already correct |

## How it happened

Python's `tempfile` defaults to the system temp directory, and nothing in the builder named a better place.
In the build container `/tmp` is a size-limited, RAM-backed tmpfs that Docker mounts noexec.

## Why it was not caught

Developer machines and the hosted CI have an ordinary, executable, disk-backed temp directory. The video
stage was only fast enough on short movies to stay under any limit.

## Reproduction

Start the build container with `--tmpfs /tmp` and run any stage from the table's classes (a) or (b).

## Repair

`tools/build_scratch.py`: one scratch folder per use under `AMIWIND_SCRATCH` (the builder sets it to
`RUN/scratch` for every stage it starts, serial and parallel; a value set by the caller wins), else a
`.scratch` folder next to a caller-given path, else `out/scratch` in the checkout. The folder is removed after
success and kept after a failure for inspection. The class (a) and (b) uses above call it.

## Verification

`tests/test_build_scratch.py`: unit tests of the helper (root order, cleanup, keep on failure, a program written
there can run, both stage launchers pass the environment) and a static test over `tools/` and `src/` that fails
on any `tempfile` call without `dir=` or a `/tmp` string outside the audited list, on a stale audited list, and
on `/tmp`, `mktemp` or `TMPDIR` in the build scripts. `test_gate_builds_its_library_under_the_output_folder_not_tmp`
and `test_gate_follows_the_run_scratch_folder` (tests/test_chim_zone_sim.py).

## Prevention

Builder code never uses the system temp directory for anything it executes or that can grow: it asks
`build_scratch`. The static test is the guard; a new small use must be argued for in its audited list.

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
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

Related bugs in other categories:

- [CHIM-ZONE-TMP-NOEXEC-33](CHIM-ZONE-TMP-NOEXEC-33.md): The CHIM zone walk gate cannot load its host library when /tmp is mounted noexec

<!-- END GENERATED CATEGORY -->
