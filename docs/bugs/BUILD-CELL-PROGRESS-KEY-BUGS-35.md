# BUILD-CELL-PROGRESS-KEY-BUGS-35: Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | tools/build_cache.py source closure (script-name rule); reuse preflight stop |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | high: A docs-only change (any new bug) stopped every build with --reuse-from before any stage ran |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | MiniWind animkit-abi build |
| From commit | source 02fa893, engine 02fa893, CHIM world 02fa893 |
| CHIM engine version | CHIM 0.1.0, engine 02fa893, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on the v0.0.35 line, not shipped.

## Symptom

After the cell-progress stage was merged (c2b7a3e), the MiniWind animkit-abi build of 02fa893 stopped at the reuse
preflight: `1 UNEXPECTED: cell-progress over-broad key: only files no output depends on changed: docs/bugs/bugs.json`.
Every bug registration changes that file, so every build with `--reuse-from` would stop.

## Where

`tools/build_cache.py`: the source closure's rule that follows a repository script named by a string literal, and the
reuse preflight's stop on a key too broad.

## How it happened

`cell_progress.ingest` writes `'generator': 'tools/cell_progress.py'` into its output. The closure took that label for
a run of the module as a script, reached its `main()` (the tracker's command line), and through it
`cell_progress_ref`, whose path is built from the single literal `'docs'`: the whole `docs/` folder (97 files, the bug
register among them) entered the key. The tracker does not read the bug register in a build (`cell_progress_build`
passes no bug list; the stage's read trace shows no `docs/` read), so the preflight's verdict was right: the key was
too broad.

## Why it was not caught

The repository reuse test (docs-only edits rebuild no stage) did not list the new stage.

## Reproduction

Any change under `docs/` and a build with `--reuse-from`.

## Repair

- A module naming its own path is not a run of its command line (unless that code starts a Python process). The
  tracker key now holds its 25 modules and 3 data files, no `docs/` file; it still covers every file and function the
  tracker ran.
- An advisory stage (`--never-fail`, no stage depends on it) whose key is too broad is reported and runs again; it
  never stops the build.

## Verification

`tests/test_stage_key_coverage.py` (`SelfNamingTests`, tracker closure without `docs/`);
`tests/test_build_cache_repository.py` now includes cell-progress: docs and tracker edits rebuild no stage.

## Prevention

The repository reuse test covers the tracker stage; the self-naming case is tested both ways.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CHIM-KEY-UNDERDECLARED-35](BUILD-CHIM-KEY-UNDERDECLARED-35.md): The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk
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
