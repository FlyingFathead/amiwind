# BUILD-KEY-OVERBROAD-33: A new bug page or release file list change rebuilds interior, census, harvest and the CHIM stages: an import search path counted as a read of every file under tools/

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33 |
| Where | Stage source fingerprints (tools/build_cache.py SourceIndex, _unit_facts) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33 (last seen) |
| Severity | high: Every tracker commit rebuilt the chain from interior onward for every worker (chim alone 125-210 s); the v0.0.33 final rebuilt harvest and chim for nothing. |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | v0.0.33 final-f583c7b and temple-debug-004/006 |
| From commit | source f583c7b, engine f583c7b, CHIM world f583c7b |
| CHIM engine version | CHIM 0.1.0, engine f583c7b, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-reuse-keys, not shipped at the time of writing.

## Symptom

The v0.0.33 final (reusing rc1d) rebuilt harvest ("changed: sources (tools/release-files.json)") and chim
("changed: dependency harvest, sources (VERSION, tools/release-files.json)"), 125-210 s for chim alone. The
CHIM builder's temple-debug-006 (reusing 004) rebuilt interior, census, harvest, chim and chim-town for the same
reason, and every stage after them: 15 of 24 stages reused. tools/release-files.json changes with every new bug
page, so every tracker commit rebuilt that chain for every worker.

## Where

`tools/build_cache.py`, the static analysis behind stage source fingerprints (`_unit_facts`, `_match_data`).

## How it happened

Stage modules put the tools/ and src/ folders on the import path at import time
(`sys.path.insert(0, str(ROOT / 'tools'))`, `sys.path[:0] = [...]`, or a `for p in (ROOT / 'tools', ROOT / 'src')`
loop). The analysis read `ROOT / 'tools'` as a path the code opens, and a bare folder name names every
non-Python file in it: release-files.json, build-reference.json, polycount_inspector.html, the CHIM effect files.
interior and census reach such a module through tools/chim_town.py; harvest and chim through harvest_build.py,
chim_build.py, chim/validate.py, chim/disk.py and hull_chain_audit.py.

## Why it was not caught

The reuse records named the changed file, but nothing compared a rebuilt stage with the inputs its outputs
really depend on, and no test edited a file no stage reads and checked that nothing rebuilds.

## Reproduction

Change tools/release-files.json and build with `--reuse-from`: before the repair harvest and chim (and on the CHIM
builder branch interior, census and chim-town) ran again.

## Repair

Values given to `sys.path.insert/append/extend`, assigned to `sys.path` or a slice of it, passed to
`site.addsitedir`, and the folders of a `for` loop whose variable is only used on `sys.path`, are import search
paths, not data reads (`import_path_nodes`); the imports themselves are still followed. A computed read under
tools/ (`ROOT / 'tools' / name`) still names the folder, so the key never under-declares. Checked on the CHIM
builder branch tree: interior, census, harvest, chim and chim_town no longer include the release file list.
VERSION in chim's key (a waiver policy check and the zone-walk gate's temporary library) is a smaller over-broad
input, left for the per-stage declared-input work.

## Verification

tests/test_build_cache.py `StageKeyCoverageTests`: the idioms name no data file; a computed read under tools/ still
counts; no builder stage's key contains tools/release-files.json or a tracker file. Measured rerun: to be recorded
with the first builds on the published head.

## Prevention

The key-coverage test runs over every builder stage script in the full suite; the reuse audit lists every rebuilt
stage with its reason after each build with `--reuse-from`.

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
