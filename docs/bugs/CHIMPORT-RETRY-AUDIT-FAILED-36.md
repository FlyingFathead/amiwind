# CHIMPORT-RETRY-AUDIT-FAILED-36: CHIMport --retry-failed never reran cells that converted but failed an audit (memory fit, doors, hull chains): the runner marks them done

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.36-dev1 |
| Where | tools/chimport.py run, pending_rows(): only runner-state failures were retried |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | medium: The 546 hull-pending cells and every audit-failed cell of the island run could not be rerun after a shared-layer fix without hand-editing state.json |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 0c948b3, engine 0c948b3, CHIM world 0c948b3 |
| CHIM engine version | CHIM 0.1.0, engine 0c948b3, world format 0.5 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.41 (16 October 2026)._

## Status: 10 October 2026

Repaired in source on the v0.0.36 CHIMport region line, not shipped.

## Symptom

After the shared standing-hull rule reached the v0.0.36 line, a region rerun with
`chimport.py run --region "Bitter Coast Region" --retry-failed` selected 0 of the region's 123 cells, although 10 cells
waited for the hull rule and 3 had failed audits (memory fit, door links).

## Where

`tools/chimport.py`, `run`: `pending_rows()` chooses the cells to run from `RUN/state.json`.

## How it happened

The runner records two things per cell: its own state (`done` when the cell process converted without an error,
`failed` when it crashed or reported an error) and the cell's result (`passed`, `empty`, `hull_pending`, `failed`,
`not_converted`). A cell that converted but failed an audit is `done` in the runner state, with result `failed` or
`hull_pending`. `--retry-failed` looked only at the runner state, so those cells were never selected again. On the
island run that is the 546 hull-pending cells and every cell whose only failures were audits.

## Why it was not caught

The runner test made failing cells only by crashing or by a converter error, never by a failed audit, so the
difference between runner state and cell result was not tested.

## Reproduction

Run a cell whose audit fails (for example memory fit), then run again with `--retry-failed`: the cell is skipped.

## Repair

`--retry-failed` also runs every cell whose recorded result is `failed`, `hull_pending` or `not_converted`
(`RETRY_RESULTS`); passed and empty cells are never rerun. Without `--retry-failed` nothing changes.

## Verification

`tests/test_chimport.py` `test_retry_runs_converted_cells_whose_audits_failed`: a cell with a failed audit is `done`
with result `failed`; a plain rerun skips it, `--retry-failed` runs it again and a passed cell stays untouched. The
Bitter Coast region dry run then selects its 13 non-passing cells.

## Prevention

The regression test above, and the rule that a retry is decided by the cell's result, not by whether its process ended
cleanly.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-ACTOR-LIBRARY-MWAD-PATH-47](BUILD-ACTOR-LIBRARY-MWAD-PATH-47.md): The actor-library stage stopped at once: run as a script, tools/mwad.py hid the src/mwad package
- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CACHE-PROVENANCE-41](BUILD-CACHE-PROVENANCE-41.md): Some cache entries record no time or no versions: pool keys from CHIMport have empty versions and commit, world-terrain units and stage records have no creation time or version
- BUILD-CELL-PROGRESS-ENGINE-KEY-48 (no report page): The tracker data stage (cell-progress) counted every engine source in its key: an engine-only edit rebuilt it
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
- BUILD-CHIM-KEY-ENGINE-SOURCES-49 (no report page): An engine source edit rebuilds the whole CHIM world: the CHIM stage imports project_version, whose engine check names engine/aga/src files
- [BUILD-CHIM-KEY-UNDERDECLARED-35](BUILD-CHIM-KEY-UNDERDECLARED-35.md): The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk
- [BUILD-CHIM-KEY-VERSION-48](BUILD-CHIM-KEY-VERSION-48.md): The CHIM world and cell-progress stages key on VERSION, so a version-only bump (rc to final) rebuilds the whole CHIM world
- [BUILD-CHIM-LABEL-IN-KEYS-48](BUILD-CHIM-LABEL-IN-KEYS-48.md): The CHIM version label was in the stage keys: the x.x.1 release step rebuilt about 25 stages, the CHIM world among them
- BUILD-CHIM-VIS-RECOMPUTED-48 (no report page): The CHIM stage recomputed every region frame's visibility (1 h 20 min on 24 cores)
- BUILD-DEV-GALLERY-SKIP-RC-REBUILD-48 (no report page): Development builds leave out the NPC gallery, so every release candidate builds all 3,551 faces fresh
- [BUILD-DIAGNOSTIC-INPUT-REFUSED-36](BUILD-DIAGNOSTIC-INPUT-REFUSED-36.md): The cell-progress stage was never reusable: it reads the CHIM stage's statistics report, which counted as a forbidden diagnostic read
- [BUILD-ENGINE-KEY-SDK-33](BUILD-ENGINE-KEY-SDK-33.md): The engine stage is never reused: the Amiga SDK is not part of its key
- [BUILD-FLORA-RECEIPT-SECONDS-36](BUILD-FLORA-RECEIPT-SECONDS-36.md): The world flora receipt held the stage's wall time, so a rerun with the same inputs never wrote the same receipt
- [BUILD-GALLERY-JSON-KEY-ORDER-35](BUILD-GALLERY-JSON-KEY-ORDER-35.md): NPC gallery outputs differed between two builds only in JSON key order (cache vs fresh results)
- BUILD-IMAGE-LAYOUT-SERIAL-49 (no report page): The image step plans its disk layout and writes its partitions on about 1.6 of 24 cores for about three minutes
- [BUILD-IMAGE-NO-RESUME-33](BUILD-IMAGE-NO-RESUME-33.md): A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds
- [BUILD-IMAGE-STALE-PYTHONPATH-35](BUILD-IMAGE-STALE-PYTHONPATH-35.md): Builder container images put an old builder copy on PYTHONPATH
- [BUILD-KEY-FUNCTION-DEFAULTS-TOP-36](BUILD-KEY-FUNCTION-DEFAULTS-TOP-36.md): Adding a function to a shared module changed the key of every stage that imports it, although no stage runs the new code
- [BUILD-KEY-OVERBROAD-33](BUILD-KEY-OVERBROAD-33.md): A new bug page or release file list change rebuilds interior, census, harvest and the CHIM stages: an import search path counted as a read of every file under tools/
- BUILD-MWSCRIPT-KEY-UNDERDECLARED-48 (no report page): The mwscript stage's reuse record is refused: the stage reads tools/mwscript/measure.py, which its fingerprint leaves out
- [BUILD-NPC-BAKE-CACHE-KEY-40](BUILD-NPC-BAKE-CACHE-KEY-40.md): New NPC shell fallback dependencies are absent from the model cache key
- [BUILD-OUTPUTS-NOT-REPRODUCIBLE-33](BUILD-OUTPUTS-NOT-REPRODUCIBLE-33.md): A stage that runs again never matches its old outputs (tool logs, timings, run paths), so every stage after it is rebuilt
- [BUILD-PASS-KEY-OVERBROAD-36](BUILD-PASS-KEY-OVERBROAD-36.md): Image-pass and unit cache keys changed with code no pass runs: a new function in a shared module and edits to the cache's own key code rekeyed every character head preview twice (Vivec stage A try2 and try3: 275 of 275 recomputed)
- [BUILD-PASS-KEY-RULE-NO-CARRYOVER-36](BUILD-PASS-KEY-RULE-NO-CARRYOVER-36.md): A pass key rule change carried no entries written by older trees: dev4 recomputed 2,372 optimizer maps and the exterior sky maps with code and outputs identical to dev3
- [BUILD-POOL-APPLY-READ-MISS-35](BUILD-POOL-APPLY-READ-MISS-35.md): In a pool-mode build every reused stage was refused as the next reuse source: the reuse step's read of tools/storage_pool.py counted as a stage input
- [BUILD-POOL-ARG-UNFINGERPRINTED-35](BUILD-POOL-ARG-UNFINGERPRINTED-35.md): The balmora stage was never reusable once the shared storage pool grew past 512 MiB: its --npc-model-pool folder was hashed as an input
- [BUILD-POOL-READONLY-SCENE-WRITE-35](BUILD-POOL-READONLY-SCENE-WRITE-35.md): A pool-mode resume failed in 17 s: npcs could not rewrite its copy of seyda.bsp (copytree kept the pool's read-only mode)
- BUILD-PREFLIGHT-CELL-PROGRESS-VERSION-49 (no report page): The reuse preflight calls the tracker data stage (cell-progress) an unexpected VERSION-only rebuild, though its outputs name the release derived from VERSION
- [BUILD-RESUME-HAZARD-STATIC-35](BUILD-RESUME-HAZARD-STATIC-35.md): A resume failed in 'area': the rebuild hazard counted files of a reused stage that had run again after all
- [BUILD-RESUME-OUTPUTS-DIFFER-35](BUILD-RESUME-OUTPUTS-DIFFER-35.md): Every v0.0.35 resume refused the stages after a rerun scene-chain stage as 'outputs differ' without comparing them
- BUILD-REUSE-APPLY-SERIAL-49 (no report page): Reusing a stage links its cached files on about one core: 34,306 files took 1.4 minutes at the start of a version-only build
- [BUILD-REUSE-ATTRIBUTION-33](BUILD-REUSE-ATTRIBUTION-33.md): Two stages that ran at the same time were both refused reuse when one wrote files under a folder the other only reads
- [BUILD-REUSE-AUDIT-WITHOUT-REASON-36](BUILD-REUSE-AUDIT-WITHOUT-REASON-36.md): The reuse audit and preflight called a stage rerun because its old record was short a replaced file UNEXPECTED, although the reason explains it
- [BUILD-REUSE-CASCADE-36](BUILD-REUSE-CASCADE-36.md): A fix in CHIM-native town code made 23 of 36 stages rebuild: the interior stage reran with different outputs and 5 rebuilds were unexpected
- [BUILD-REUSE-CUTOFF-MODE-36](BUILD-REUSE-CUTOFF-MODE-36.md): Early cutoff compared file modes with their write bits: a stage reused by hard link (read-only) never matched the same bytes written fresh, so 10 stages after dev3's bsp rerun were refused
- [BUILD-REUSE-INTRO-CENSUS-REPLACED-48](BUILD-REUSE-INTRO-CENSUS-REPLACED-48.md): A reused MiniWind rooms build rebuilt the intro and census stages (replaced outputs) and its Balmora interiors (4 s to 1m21s)
- BUILD-REUSE-OUTPUTS-DIFFER-48 (no report page): Eight stages were rebuilt because their earlier outputs differed from their records (character, reading, world-ui, actor-contact, world-terrain and others)
- [BUILD-REUSE-PLAN-ENV-36](BUILD-REUSE-PLAN-ENV-36.md): The standalone reuse plan reports environment changes the real build does not have
- BUILD-REUSE-RC1-RECORDS-REFUSED-48 (no report page): Every stage that ran the idle-worker watcher or read the CHIM label module was marked not reusable: rc1-try2 had 24 unexpected rebuilds
- [BUILD-REUSE-RECORD-RETIRED-36](BUILD-REUSE-RECORD-RETIRED-36.md): Early cutoff and the reuse audit lost their records when an older run was retired: stages with byte-identical outputs counted as changed
- [BUILD-REUSE-REDUCED-RECORD-36](BUILD-REUSE-REDUCED-RECORD-36.md): A stage reused from a run that had itself reused it came back without the files a later stage replaced there, so that later stage failed when it ran again
- [BUILD-REUSE-SCHEDULER-TOP-45](BUILD-REUSE-SCHEDULER-TOP-45.md): A scheduler-only edit rekeys every stage, NPC gallery face and stair walk that reaches tools/build_parallel.py
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-REUSE-TMP-RECORDED-DELETED-48](BUILD-REUSE-TMP-RECORDED-DELETED-48.md): A reused stage removed another stage's reuse copies mid-copy: its record listed them as deleted (balmora-interiors stopped at os.replace)
- BUILD-ROOM-BATCHES-KEY-UNDERDECLARED-48 (no report page): The room stage's reuse record is refused: it reads 17 repository files its fingerprint leaves out
- BUILD-ROOM-BATCHES-SCENE-RACE-48 (no report page): A reused build stopped in the room stage: it ran before the area stage had restored the scene map it reads (seyda.bsp)
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SEYDA-BOUNDED-RUN-PATHS-36](BUILD-SEYDA-BOUNDED-RUN-PATHS-36.md): The actor-contact stage wrote its run folder path into 67 Seyda Neen region records, so its outputs differed in every run folder
- [BUILD-SPRITE-KEY-HASHLIB-47](BUILD-SPRITE-KEY-HASHLIB-47.md): The CHIM stage failed 45 minutes into a build: the sprite recipe key used hashlib without importing it
- BUILD-STAGE-KEY-WHOLE-CLASS-48 (no report page): A one-method edit in tools/actor_grounding.py rekeyed the CHIM stages: a class was import-time code of its module, so every stage importing the module hashed every method
- BUILD-STAGE-READS-UNFINGERPRINTED-48 (no report page): Two stages read repository files their fingerprint leaves out, so their records are refused and they rerun on every reuse
- [BUILD-STAIR-KEY-BOOKKEEPING-36](BUILD-STAIR-KEY-BOOKKEEPING-36.md): Stair walk keys count the progress lines (stair_progress.py) and the record bookkeeping (stair_records.py): an edit to either rekeys every walk
- [BUILD-STAIR-PASS-NOT-KEPT-41](BUILD-STAIR-PASS-NOT-KEPT-41.md): A frame's passed stair walk is not reused when the build it ran in failed, and the walker key changes with converter code
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [BUILD-VERSION-GETATTR-TRACE-49](BUILD-VERSION-GETATTR-TRACE-49.md): The v0.0.49 final rebuilt the CHIM world: the lazy VERSION (a module __getattr__ in project_version) ran in the CHIM stage, its read trace recorded it and the key could not
- [CACHE-NO-PROVENANCE-36](CACHE-NO-PROVENANCE-36.md): Cache and pool entries were keyed by SHA-256 but did not record when, by which run, from which version and commit they were made, and some recorded no output hash
- CHIM-COLLISION-UNION-FAIL-NOT-CACHED-48 (no report page): A collision union that fails is compiled again for every room that uses the same mesh packet
- [CHIM-INTERIORS-REUSE-MISS-48](CHIM-INTERIORS-REUSE-MISS-48.md): The CHIM rooms stage (chim-interiors) is never reused: it hashed the shared CHIM unit cache, which is past the 512 MiB folder limit
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [CHIMPORT-POOL-CROSS-MOUNT-36](CHIMPORT-POOL-CROSS-MOUNT-36.md): CHIMport run folder and the storage pool on two mounts of one volume: hard links fail across the mounts, so pooled units were copied, not linked
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
