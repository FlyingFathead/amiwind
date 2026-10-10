# BUILD-SCHEDULER-TABLE-KEY-35: A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | Stage fingerprints: tools/build_cache.py module_symbols; DEPENDENCIES in tools/build_parallel.py |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | high: Stages with no real input change (media about 7 minutes cold, music, world-scenery-assets) rebuilt after the seam-audit row was added; hold-level reuse loss |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | v0.0.34 hotfix build |
| From commit | source 70b04e2, engine 70b04e2, CHIM world 70b04e2 |
| CHIM engine version | CHIM 0.1.0, engine 70b04e2, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on the v0.0.35 line, not shipped.

## Symptom

After the v0.0.34 line added a `seam-audit` row to the scheduler's stage table, a build with `--reuse-from`
rebuilt stages whose inputs had not changed: media (about 7 minutes from a cold cache), music and
world-scenery-assets.

## Where

`tools/build_cache.py`, the unit split behind stage source fingerprints (`module_symbols`, `unit_texts`), and the
`DEPENDENCIES` table in `tools/build_parallel.py`.

## How it happened

A stage fingerprint hashes a module's import-time code (`<top>`) plus each function the stage reaches. Every
stage script imports `tools/build_parallel.py` for its worker pool, and the scheduler's `DEPENDENCIES` table is a
top-level assignment, so it was part of `<top>` for every stage although only the build plan reads it.

## Why it was not caught

The repository reuse tests edited the scheduler's functions (`stage_dependencies`), which were already their own
units, but no test edited the table itself.

## Reproduction

Add a row to `DEPENDENCIES` and compare stage fingerprints: before the repair every stage changed.

## Repair

A top-level literal table (`NAME = {...}`, a list, a tuple or a set whose value is a literal and whose name no
other top-level statement binds) is its own unit, like a plain function (`lazy_tables`): it counts for a stage
only when the stage's reached code names it. A module read whole (`globals()`, `module.__dict__`,
`from m import *`) still reaches every table, so a key never under-declares. Every module with such a table gets
a new `<top>` digest once, so the first build after this change rebuilds once.

## Verification

tests/test_build_cache_repository.py `test_scheduler_table_row_reuses_stages_that_do_not_read_it`: a new
scheduler row changes exactly the stages whose code reads the table (none of media, music, setup or the scene
chain); `test_literal_tables_are_their_own_units` covers the rules.

## Prevention

The repository reuse tests run in the full suite; the reuse audit after each build lists every rebuilt stage with
its reason.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
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
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
