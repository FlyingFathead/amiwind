# BUILD-OUTPUTS-NOT-REPRODUCIBLE-33: A stage that runs again never matches its old outputs (tool logs, timings, run paths), so every stage after it is rebuilt

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | Stage outputs (tool logs, receipts) and the reuse comparison (tools/build_cache.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-rc1 (last seen) |
| Severity | high: rc1d: census, area, balmora and the Balmora interiors differed from rc1c only in logs; 13 later stages ran again. |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | v0.0.33-rc1 builds rc1b, rc1c and rc1d |
| From commit | source d49f324, engine d49f324, CHIM world d49f324 |
| CHIM engine version | CHIM 0.1.0, engine d49f324, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-reuse-keys, not shipped at the time of writing.

## Symptom

A build reusing an earlier run rebuilds a stage (a real change, or a chain of replaced outputs) and then refuses
every stage after it: "an earlier stage it depends on ran again and its outputs differ from the old run". Compared
file by file (tools/reuse_report.py), rc1d against rc1c, same inputs: census differed in 3 files, area in 52,
balmora in 316 and the Balmora interiors in 183, all of them `.log` files of the map tools ("0.306 seconds
elapsed"). Further differences: `seconds` in world-flora-assets/tree-sprites.json, in every world-scenery region
receipt (2,463 files) and the world-scenery receipt, and in the world-terrain region receipts and
world-regions.json; worker count, unit cache hits and wall time in chim-world/chim-receipt.json; timing in
npc-gallery/gallery-cache.json and chim-stats.json; the run folder's path in world-flora's collision-packing
reports. The world-flora input contract hashes tree-sprites.json and the world-scenery receipt, so it differed too.
In rc1d this refused npc-gallery, world-flora-assets, hand-catalog, door-audio, character, reading,
opening-references, world-ui, actor-contact, world-terrain, world-scenery and world-flora.

## Where

Stage outputs written by the map tools (logs), tools/prepare_tree_sprites.py, tools/prepare_world_scenery.py,
tools/prepare_world_regions.py, tools/prepare_world_flora.py, tools/chim/build.py, tools/survey_vvardenfell.py;
the comparison in tools/build_cache.py `same_outputs`.

## How it happened

Receipts recorded how long their step took and how many workers it had, logs of the map compilers were kept as
stage outputs, and one report kept an absolute folder path. The reuse planner compares a rebuilt stage's outputs
byte for byte with the old run's (BUILD-CACHE-NO-CUTOFF-33), so any of these made "the same outputs" impossible.

## Why it was not caught

No test ran a stage twice on the same inputs and compared its outputs, and the reuse records showed only the
first refused dependant, not which file differed.

## Reproduction

Build with `--reuse-from` where census (or area) must run again: before the repair every stage after it ran again.

## Repair

1. Diagnostics: files named `*.log`, and the reports chim-stats.json, chim-timing.json, gallery-cache.json and
   world-terrain-cache.json, are not compared by `same_outputs`; they are still recorded and copied on reuse. No
   stage may read one: the stage trace lists every run-folder diagnostic a stage opens, and a stage that reads one
   another stage wrote is not reused; a test checks that no repository code reads a `.log` file outside reviewed
   uses (the builder's own run-private logs).
2. Wall time, worker counts and run paths left the stage receipts (they go to the stage log); the CHIM build's
   worker count, unit cache hits and timing moved to chim-world/chim-timing.json, which chim-stats reads.

## Verification

tests/test_build_cache.py `DiagnosticOutputTests`; tests/test_stage_output_determinism.py (no wall time, worker
count or run path in the receipts of the fixed writers). Measured rerun: to be recorded with the first builds on
the published head (tools/reuse_report.py lists every stage still refused and which files differ).

## Prevention

A stage output is byte-reproducible; timings belong in logs and the build profile. The reuse audit reports any
rebuilt stage whose non-diagnostic outputs differ with unchanged inputs.

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

Related bugs in other categories:

- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it

<!-- END GENERATED CATEGORY -->
