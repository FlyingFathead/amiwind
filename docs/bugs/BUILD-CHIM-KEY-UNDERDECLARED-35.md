# BUILD-CHIM-KEY-UNDERDECLARED-35: The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | tools/chim_build.py (cell progress subprocess named in parts), tools/build_cache.py source closure |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | high: A stage output (BUILD/toolkit) was produced by code its key did not cover; only the read trace refused the reuse |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | 2026_10_10_v0.0.35-dev1_full-try2_901f8e9 |
| From commit | source 901f8e9, engine 901f8e9, CHIM world 901f8e9 |
| CHIM engine version | CHIM 0.1.0, engine 901f8e9, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on the v0.0.35 line, not shipped.

## Symptom

The resumed v0.0.35-dev1 build printed in its reuse plan: `rebuild chim: old outputs not reusable: read 8 repository
files its fingerprint left out (first: tools/cell_lava.py); ran 2 repository functions its fingerprint left out
(first: tools/light_sources.py:classify)`. The stage's read trace caught it and refused the reuse; with a narrower
audit the CHIM stage could have been reused with a stale output.

## Where

`tools/chim_build.py` (the CHIM stage) started `tools/cell_progress_build.py` as a subprocess, which writes
`BUILD/toolkit/cell-progress.json`, an output of that stage. The fingerprint scan is `SourceIndex` in
`tools/build_cache.py`.

## How it happened

The fingerprint follows a script started as a subprocess when its file name is a string literal. The tracker's
name was written in two parts (`'cell_progress' + '_build.py'`) on purpose, to keep its code (and the documentation
files its code can name) out of the CHIM stage's key. But the tracker writes into a folder that is an output of the
stage, so its code is an input of that output: the key under-declared it. The 8 files were `tools/cell_lava.py`,
`cell_lighting.py`, `cell_progress.py`, `cell_progress_build.py`, `cell_progress_chim.py`, `cell_progress_order.py`,
`cell_progress_release.py` and `light_sources.py` (functions `classify` and `quake_style`).

## Why it was not caught

Nothing checked a stage's recorded read trace after a build except the reuse step of the next build, and no test
looked for script names built from parts.

## Reproduction

Any CHIM build with the tracker on, then a build with `--reuse-from` it: the CHIM stage is refused as a reuse source
(`profile/manifests/chim.json`, `reads.misses`).

## Repair

- The tracker runs as its own builder stage, `cell-progress`, after `chim` (`tools/cell_progress_build.py
  --never-fail`; scheduler row `'cell-progress': ('chim',)`; the image does not wait for it). Its key covers its own
  code. The CHIM stage's key no longer includes tracker code or the documentation files the tracker can read: keying
  the CHIM world on those would rebuild it on every documentation edit. `chim_build.py --cell-progress` now prints the
  command instead.
- Shared layer: the fingerprint scan folds strings built only from literals (`'a' + 'b.py'`, f-strings of literals),
  so a script or data file named in parts is followed like a plain literal (`build_cache.folded_string`).
- `tools/build_audit.py` reports, for every stage of a run, any read or call its fingerprint left out as a `wake`
  finding (`key-underdeclared`).

## Verification

`tests/test_stage_key_coverage.py`: a script named in parts or by an f-string of literals is in the closure (every
scope); the `cell-progress` stage's closure holds all 8 files and both functions, and the CHIM stage's holds no
tracker module and no `docs/` file; build_audit wakes on uncovered reads or calls of any stage. Builder plan tests
(`test_build_builder`, `test_build_defaults`, `test_miniwind`) check the new stage and its order.

## Prevention

A sweep test fails on any `.py` name built at run time from a non-literal part in `tools/` or `src/` (a script the
scan could not follow). The read trace stays the run-time half, now also reported by build_audit after every build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
- [BUILD-ENGINE-KEY-SDK-33](BUILD-ENGINE-KEY-SDK-33.md): The engine stage is never reused: the Amiga SDK is not part of its key
- [BUILD-GALLERY-JSON-KEY-ORDER-35](BUILD-GALLERY-JSON-KEY-ORDER-35.md): NPC gallery outputs differed between two builds only in JSON key order (cache vs fresh results)
- [BUILD-IMAGE-NO-RESUME-33](BUILD-IMAGE-NO-RESUME-33.md): A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds
- [BUILD-IMAGE-STALE-PYTHONPATH-35](BUILD-IMAGE-STALE-PYTHONPATH-35.md): Builder container images put an old builder copy on PYTHONPATH
- [BUILD-KEY-OVERBROAD-33](BUILD-KEY-OVERBROAD-33.md): A new bug page or release file list change rebuilds interior, census, harvest and the CHIM stages: an import search path counted as a read of every file under tools/
- [BUILD-OUTPUTS-NOT-REPRODUCIBLE-33](BUILD-OUTPUTS-NOT-REPRODUCIBLE-33.md): A stage that runs again never matches its old outputs (tool logs, timings, run paths), so every stage after it is rebuilt
- [BUILD-POOL-APPLY-READ-MISS-35](BUILD-POOL-APPLY-READ-MISS-35.md): In a pool-mode build every reused stage was refused as the next reuse source: the reuse step's read of tools/storage_pool.py counted as a stage input
- [BUILD-POOL-ARG-UNFINGERPRINTED-35](BUILD-POOL-ARG-UNFINGERPRINTED-35.md): The balmora stage was never reusable once the shared storage pool grew past 512 MiB: its --npc-model-pool folder was hashed as an input
- [BUILD-POOL-READONLY-SCENE-WRITE-35](BUILD-POOL-READONLY-SCENE-WRITE-35.md): A pool-mode resume failed in 17 s: npcs could not rewrite its copy of seyda.bsp (copytree kept the pool's read-only mode)
- [BUILD-RESUME-HAZARD-STATIC-35](BUILD-RESUME-HAZARD-STATIC-35.md): A resume failed in 'area': the rebuild hazard counted files of a reused stage that had run again after all
- [BUILD-RESUME-OUTPUTS-DIFFER-35](BUILD-RESUME-OUTPUTS-DIFFER-35.md): Every v0.0.35 resume refused the stages after a rerun scene-chain stage as 'outputs differ' without comparing them
- [BUILD-REUSE-ATTRIBUTION-33](BUILD-REUSE-ATTRIBUTION-33.md): Two stages that ran at the same time were both refused reuse when one wrote files under a folder the other only reads
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
