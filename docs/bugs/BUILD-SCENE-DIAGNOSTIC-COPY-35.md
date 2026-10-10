# BUILD-SCENE-DIAGNOSTIC-COPY-35: Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | tools/build_cache.py read trace hook; shutil.copytree in prepare_npcs/hands/interior/intro |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | medium: npcs, hands, interior and intro rebuilt in every reuse build although their inputs had not changed |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | 2026_10_10_v0.0.35-dev1_full-try2_901f8e9 |
| From commit | source 901f8e9, engine 901f8e9, CHIM world 901f8e9 |
| CHIM engine version | CHIM 0.1.0, engine 901f8e9, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on the v0.0.35 line, not shipped.

## Symptom

The v0.0.35-dev1 reuse plan: `rebuild npcs: old outputs not reusable: read build diagnostics written by other
stages, which are not stage inputs: bsp-scene/light.log, bsp-scene/seyda.log, bsp-scene/standing-collision.log`, and
the same for hands (npc-scene), interior (hands-scene) and intro (interior-scene).

## Where

The read trace hook in `tools/build_cache.py`; the scene chain copies its input scene whole
(`prepare_npcs.py`, `prepare_hands.py`, `prepare_interior.py`, `prepare_intro.py`).

## How it happened

The rule from BUILD-OUTPUTS-NOT-REPRODUCIBLE-33 refuses a stage that reads another stage's diagnostic, because
diagnostics are not compared between runs and could carry a difference into an output. The scene chain does not use
the logs: it copies the whole previous scene, and the copy opens every file for reading, logs included. The copied
bytes only land in a log of the stage's own output folder, itself a diagnostic that no stage reads and no reuse
compares. The code shows it: the only access is the folder copy; no scene stage names a `.log` file
(`test_no_repository_code_reads_a_log_file`).

## Why it was not caught

The diagnostic rule's tests used direct reads only.

## Reproduction

A build, then a `--reuse-from` build: npcs, hands, interior and intro always rebuild.

## Repair

The trace hook watches the `shutil.copyfile` audit event: when a run-folder diagnostic is copied into a file that is
itself a diagnostic, that copy's own open of the source is not listed. Any other read of the same file, or a copy into
a non-diagnostic name, is still listed and still refuses reuse.

## Verification

`tests/test_stage_key_coverage.py` `DiagnosticCopyTests`: copies through `copy_tree` and plain `shutil.copytree` are
not reads; a direct read and a copy into a `.txt` file are; a scene-chain stage whose only diagnostic access is the
copy stays reusable.

## Prevention

The root cause, the shared scene chain (every stage copies and edits the whole previous scene), is planned for
redesign; until then the copy is recognised precisely, and any real read of a foreign diagnostic still refuses reuse.

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
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
