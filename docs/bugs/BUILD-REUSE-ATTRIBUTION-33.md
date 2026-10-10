# BUILD-REUSE-ATTRIBUTION-33: Two stages that ran at the same time were both refused reuse when one wrote files under a folder the other only reads

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33 |
| Where | Stage output recorder (tools/build_cache.py Recorder.close) |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.33 (last seen) |
| Severity | high: character (about 19 min) and chim-town ran again in every later build; the scheduler runs independent stages together, so it recurs. |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | v0.0.33 final-f583c7b and temple-debug-004/006 |
| From commit | source f583c7b, engine f583c7b, CHIM world f583c7b |
| CHIM engine version | CHIM 0.1.0, engine f583c7b, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-reuse-keys, not shipped at the time of writing.

## Symptom

temple-debug-006 (reusing 004) rebuilt character: "changed intro-scene/id1/character/h106.awh (and 29 more) while
chim-town-vivec_temple ran; outputs cannot be attributed". In 004 the two stages ran at the same time; chim-town
was refused for the same files.

## Where

`tools/build_cache.py`, `Recorder.close`: files that two stages running at the same time both saw change made
both stages non-reusable.

## How it happened

A stage's outputs are the files that changed under its run-folder paths during its run. chim-town names
intro-scene (it reads the scene), so its snapshot saw the character files that the character stage wrote while
chim-town ran. Without knowing who wrote them, both stages were refused, which is safe but rebuilds both every
time the scheduler runs them together.

## Why it was not caught

The overlap rule was tested with two stages that both wrote the same file, not with a writer and a reader.

## Reproduction

Run two stages at the same time where one writes under a folder the other has on its command line.

## Repair

The stage read trace (the hook every traced stage's Python processes load) also records writes into the run
folder: opens for writing, renames, links and removals ('>' lines). When two stages overlap, a shared file that
only one of them wrote is credited to that stage and dropped from the other's outputs (recorded in its manifest
as `attributed`). When a writer is unknown (a native tool wrote it, a stage was not traced) or both wrote it, both
stay refused as before. Records made before the repair carry no write trace, so their attribution refusals stay;
the scratch requalification (BUILD-REUSE-SCRATCH-UNDECLARED-33) applies only where the scratch folder was the only
reason.

## Verification

tests/test_build_cache.py `WriteAttributionTests`: the traced writer owns the file and both stages stay reusable;
untraced, native-tool and double writers still refuse both; the generated hook, run in a child process, lists the
writes, renames and removals. Measured rerun: to be recorded with the first builds on the published head.

## Prevention

Outputs are credited by who wrote them, not by time windows alone; the reuse audit lists every refusal.

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
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
