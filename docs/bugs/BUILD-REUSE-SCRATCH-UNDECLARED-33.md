# BUILD-REUSE-SCRATCH-UNDECLARED-33: A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | Stage output recorder (tools/build_cache.py RUN_PRIVATE, Recorder.after) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.33 |
| Severity | high: Every reuse of a run made since the scratch folder: the first stages and every stage after them run again (about 1,427 s of conversion in the rc1c rerun). |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | v0.0.33-rc1 builds rc1b and rc1c |
| From commit | source a266a40, engine a266a40, CHIM world a266a40 |
| CHIM engine version | CHIM 0.1.0, engine a266a40, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-reuse-scratch, not shipped at the time of writing.

Provenance: found reading the stage-cache records of the v0.0.33-rc1 builds rc1b (source 27058ec) and rc1c
(source a266a40, built with `--reuse-from` rc1b and `--allow-release-reuse`).

## Symptom

rc1c was a rerun of rc1b after a one-file fix in the image step. Its build state listed one reused stage
(setup) and "old outputs not reusable: created run-folder entries outside every declared stage path: scratch"
for terrain, dialogue-lookup, world-survey, world-scenery-assets and music. Every stage after them was then
refused because "an earlier stage it depends on ran again and its outputs differ from the old run". The whole
conversion ran again: about 1,427 s before the image step started.

## Where

`tools/build_cache.py`: `RUN_PRIVATE` (run-folder entries that belong to no stage) and `Recorder.after`,
which marks a stage non-reusable when a new top-level run-folder entry belongs to no declared stage path.

## How it happened

BUILD-TMP-SCRATCH-33 gave every stage the scratch folder RUN/scratch (`build_scratch.stage_environment`).
It is created by the first stage that needs scratch space, so it appears in the window of every stage running
at that moment; the recorder counted it as their undeclared output. Those stages were recorded non-reusable,
and a later build cannot use them or prove that a rerun made the same outputs (BUILD-CACHE-NO-CUTOFF-33),
so every dependent stage ran again too. The outputs themselves were identical: terrain 8 of 8 files, music
19 of 19 and media 7,185 of 7,185 match between rc1b and rc1c.

## Why it was not caught

The scratch helper and the reuse recorder were tested apart: no test started a stage with the builder's
stage environment and then checked its manifest. The reuse tests ran without RUN/scratch, and the rc builds'
reuse counts were not compared with the expected stage list.

## Reproduction

Build once, then build again with `--reuse-from` that run: the stages that ran when RUN/scratch first
appeared are listed as not reusable, and every stage after them runs again.

## Repair

RUN/scratch is run-private (`RUN_PRIVATE`). Records written by the old code are read through
`build_cache.requalify`: a manifest whose only reason not to be reused is exactly the scratch entry is
reusable again; its fingerprint and the same-output checks apply as for any other stage, and any other
reason still refuses reuse. Read against the real records: rc1b 33 of 33 conversion stages reusable (7
requalified), rc1c 33 of 33 (2 requalified); the image step is always assembled again.

## Verification

`test_the_builder_scratch_folder_is_not_an_undeclared_output` (fails without the repair) and
`test_old_records_refused_only_for_scratch_are_reusable` in tests/test_build_cache.py.

Measured on the v0.0.33 release builds (`--reuse-from`, same workspace): before the repair the release
candidate reruns reused 17, 18 and 25 of 34 stages, and every conversion stage that ran after the scratch
folder appeared was refused even when its outputs were byte-identical. A read-only re-check of those records
with the repaired loader finds all 33 conversion stages reusable. The v0.0.33 final image, built with the
repair from the last release candidate, reused 30 of 34 stages; the four that ran: `engine` (compiled with
the Amiga SDK, whose files are not fingerprinted, about 15 s), `harvest` and `chim` (their sources include
`tools/release-files.json` and `VERSION`, which the version change touches) and `image` (always assembled
and verified from the stage outputs).

## Prevention

The first test takes the scratch folder's name from `build_scratch.stage_environment` itself, so a moved or
renamed scratch folder fails it. A related open finding: BUILD-SURVEY-NOT-REPRODUCIBLE-33.

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
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
