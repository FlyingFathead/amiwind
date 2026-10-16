# BUILD-PASS-KEY-OVERBROAD-36: Image-pass and unit cache keys changed with code no pass runs: a new function in a shared module and edits to the cache's own key code rekeyed every character head preview twice (Vivec stage A try2 and try3: 275 of 275 recomputed)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 11 October 2026, in v0.0.36-dev3 |
| Where | tools/pass_cache.py source_digest: the key form of every pass and unit cache |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3 (last seen) |
| Severity | high: Hold-level reuse bug: unchanged inputs, every recorded result keyed out by an edit no pass runs |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | v0.0.36-dev3 |
| From commit | source 0dbcd4f, engine 0dbcd4f, CHIM world 0dbcd4f |
| CHIM engine version | CHIM 0.1.0, engine 0dbcd4f, world format 0.7 |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 11 October 2026](#status-11-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 11 October 2026

Open; repaired in source on v0.0.36-build-timeline, not shipped at the time of writing. Hold-level (a reuse
bug that reruns verified work).

## Symptom

The unit reuse audit of `2026_10_11_v0.0.36-dev3_miniwind-vivec-arena-chim-vivec-stage-a-try3_0dbcd4f` showed the
character stage's head previews (`image-passes/character-head`) at 275 computed and 0 reused. The shared cache
already held 1,375 entries. Each of the 275 inputs that try3 hashed (SHA-256 of the head part and palette)
already had an entry there under another key. The inputs had not changed; the key had. The same thing had
already happened on try2 (8ad8810). try4 (61a1ea0) reused all 275, because its key equals try3's.

## Where

`tools/pass_cache.py` `source_digest`, which computes the "sources" part of every pass key (`PassCache`) and
unit key (`UnitCache`).

## How it happened

The sources part hashes the code that the pass module can reach (`build_cache.SourceIndex`, scope "units").
Head previews pass the whole module (`prepare_character.py`). Computed in the builder image for each commit,
the source digest of the head preview cache was:

| Commit | Run | Sources digest | Changed file in the closure |
| --- | --- | --- | --- |
| 3b5e7a9, c8812db | dev3 coast, Vivec stage A | 063e6ccb... | - |
| 8ad8810 | Vivec stage A try2 | 1eca6a67... | `tools/pass_cache.py`: `source_digest` and `_source_digest` learned the (module, worker) form (98933e9) |
| 0dbcd4f, 61a1ea0 | Vivec stage A try3, try4 | e6e06e5a... (as recorded in try3's provenance) | `tools/build_parallel.py`: new function `create_run` (BUILD-RUN-FOLDER-PRECREATED-36) |

Neither change can alter a head preview:

1. The per-unit caches kept import-time form 1: every plain function's default values count as the module's
   import-time code. Adding `create_run(run, metadata)` to `build_parallel.py` (which the previews reach for
   `ordered_map`) therefore changed the key, though no preview calls it. Stage keys had moved to form 2 for
   exactly this reason (BUILD-KEY-FUNCTION-DEFAULTS-TOP-36). The pass caches were deliberately left on form 1
   "until their own key format changes".
2. `tools/pass_cache.py` is the cache's own key and storage code, yet it counted in every pass key that reaches
   it. An edit to how keys are computed rekeyed every stored result. Changing what a stored result means is
   what `FORMAT` is for.

## Why it was not caught

The key-coverage tests checked that an edit elsewhere in the same tool keeps a worker's key, and that a worker
or callee edit rekeys it. No test added a function to a shared module, and no test edited the cache module
itself. Until the provenance writer (CACHE-NO-PROVENANCE-36) and the unit reuse audit, no run reported which
pass entries it computed afresh.

## Reproduction

Always: add a plain function with a default argument to any module a pass reaches, or edit
`tools/pass_cache.py`, then run the pass on the same inputs.

## Repair

Pass and unit keys use key form 2 (`PASS_KEY_FORM`):

- the import-time code counts only default values that run code on import, as in the stage keys;
- `tools/pass_cache.py` is left out of the keys (`PASS_KEY_NEUTRAL`, passed as `exclude` to
  `SourceIndex.digest` and `entry_digest`).

Code a pass reaches still rekeys it. The switch costs nothing: on a miss, `PassCache.load` looks the input up
once under the form-1 key (`previous_digests`), verifies the entry's SHA-256 as for any entry, and records it
under the new key. Stair-walk adoption (`stair_records.walker_sources`) reads an earlier source
tree's walks under that tree's own key form: form 2 when its `pass_cache.py` names `PASS_KEY_FORM`, form 1
before that.

## Verification

- With the repaired `pass_cache.py` and `build_cache.py` laid over the trees of c8812db, 8ad8810, 0dbcd4f and
  61a1ea0, the head preview key in form 2 is the same for all four (876796f7...). Form 1 reproduces the three
  recorded digests exactly (063e6ccb..., 1eca6a67..., e6e06e5a...). The pool's try3 entries are therefore
  found through the fallback.
- `tests/test_pass_cache.py` `PassKeyFormTests`:
  - a new function in a shared module, and an edit to the cache module, keep the key in both forms (whole module
    and worker);
  - an edit to reached code still rekeys;
  - an older-form entry is found, verified and recorded under the new key, and a damaged one is a miss.

## Prevention

The tests above keep both kinds of edit out of the keys. The unit reuse audit (`build_profile.py reuse`)
reports computed and reused units per cache after every build, so a cache that computes everything again on
unchanged inputs shows at once.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CACHE-PROVENANCE-41](BUILD-CACHE-PROVENANCE-41.md): Some cache entries record no time or no versions: pool keys from CHIMport have empty versions and commit, world-terrain units and stage records have no creation time or version
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
- [BUILD-CHIM-KEY-UNDERDECLARED-35](BUILD-CHIM-KEY-UNDERDECLARED-35.md): The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk
- [BUILD-DIAGNOSTIC-INPUT-REFUSED-36](BUILD-DIAGNOSTIC-INPUT-REFUSED-36.md): The cell-progress stage was never reusable: it reads the CHIM stage's statistics report, which counted as a forbidden diagnostic read
- [BUILD-ENGINE-KEY-SDK-33](BUILD-ENGINE-KEY-SDK-33.md): The engine stage is never reused: the Amiga SDK is not part of its key
- [BUILD-FLORA-RECEIPT-SECONDS-36](BUILD-FLORA-RECEIPT-SECONDS-36.md): The world flora receipt held the stage's wall time, so a rerun with the same inputs never wrote the same receipt
- [BUILD-GALLERY-JSON-KEY-ORDER-35](BUILD-GALLERY-JSON-KEY-ORDER-35.md): NPC gallery outputs differed between two builds only in JSON key order (cache vs fresh results)
- [BUILD-IMAGE-NO-RESUME-33](BUILD-IMAGE-NO-RESUME-33.md): A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds
- [BUILD-IMAGE-STALE-PYTHONPATH-35](BUILD-IMAGE-STALE-PYTHONPATH-35.md): Builder container images put an old builder copy on PYTHONPATH
- [BUILD-KEY-FUNCTION-DEFAULTS-TOP-36](BUILD-KEY-FUNCTION-DEFAULTS-TOP-36.md): Adding a function to a shared module changed the key of every stage that imports it, although no stage runs the new code
- [BUILD-KEY-OVERBROAD-33](BUILD-KEY-OVERBROAD-33.md): A new bug page or release file list change rebuilds interior, census, harvest and the CHIM stages: an import search path counted as a read of every file under tools/
- [BUILD-NPC-BAKE-CACHE-KEY-40](BUILD-NPC-BAKE-CACHE-KEY-40.md): New NPC shell fallback dependencies are absent from the model cache key
- [BUILD-OUTPUTS-NOT-REPRODUCIBLE-33](BUILD-OUTPUTS-NOT-REPRODUCIBLE-33.md): A stage that runs again never matches its old outputs (tool logs, timings, run paths), so every stage after it is rebuilt
- [BUILD-PASS-KEY-RULE-NO-CARRYOVER-36](BUILD-PASS-KEY-RULE-NO-CARRYOVER-36.md): A pass key rule change carried no entries written by older trees: dev4 recomputed 2,372 optimizer maps and the exterior sky maps with code and outputs identical to dev3
- [BUILD-POOL-APPLY-READ-MISS-35](BUILD-POOL-APPLY-READ-MISS-35.md): In a pool-mode build every reused stage was refused as the next reuse source: the reuse step's read of tools/storage_pool.py counted as a stage input
- [BUILD-POOL-ARG-UNFINGERPRINTED-35](BUILD-POOL-ARG-UNFINGERPRINTED-35.md): The balmora stage was never reusable once the shared storage pool grew past 512 MiB: its --npc-model-pool folder was hashed as an input
- [BUILD-POOL-READONLY-SCENE-WRITE-35](BUILD-POOL-READONLY-SCENE-WRITE-35.md): A pool-mode resume failed in 17 s: npcs could not rewrite its copy of seyda.bsp (copytree kept the pool's read-only mode)
- [BUILD-RESUME-HAZARD-STATIC-35](BUILD-RESUME-HAZARD-STATIC-35.md): A resume failed in 'area': the rebuild hazard counted files of a reused stage that had run again after all
- [BUILD-RESUME-OUTPUTS-DIFFER-35](BUILD-RESUME-OUTPUTS-DIFFER-35.md): Every v0.0.35 resume refused the stages after a rerun scene-chain stage as 'outputs differ' without comparing them
- [BUILD-REUSE-ATTRIBUTION-33](BUILD-REUSE-ATTRIBUTION-33.md): Two stages that ran at the same time were both refused reuse when one wrote files under a folder the other only reads
- [BUILD-REUSE-AUDIT-WITHOUT-REASON-36](BUILD-REUSE-AUDIT-WITHOUT-REASON-36.md): The reuse audit and preflight called a stage rerun because its old record was short a replaced file UNEXPECTED, although the reason explains it
- [BUILD-REUSE-CASCADE-36](BUILD-REUSE-CASCADE-36.md): A fix in CHIM-native town code made 23 of 36 stages rebuild: the interior stage reran with different outputs and 5 rebuilds were unexpected
- [BUILD-REUSE-CUTOFF-MODE-36](BUILD-REUSE-CUTOFF-MODE-36.md): Early cutoff compared file modes with their write bits: a stage reused by hard link (read-only) never matched the same bytes written fresh, so 10 stages after dev3's bsp rerun were refused
- [BUILD-REUSE-PLAN-ENV-36](BUILD-REUSE-PLAN-ENV-36.md): The standalone reuse plan reports environment changes the real build does not have
- [BUILD-REUSE-RECORD-RETIRED-36](BUILD-REUSE-RECORD-RETIRED-36.md): Early cutoff and the reuse audit lost their records when an older run was retired: stages with byte-identical outputs counted as changed
- [BUILD-REUSE-REDUCED-RECORD-36](BUILD-REUSE-REDUCED-RECORD-36.md): A stage reused from a run that had itself reused it came back without the files a later stage replaced there, so that later stage failed when it ran again
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SEYDA-BOUNDED-RUN-PATHS-36](BUILD-SEYDA-BOUNDED-RUN-PATHS-36.md): The actor-contact stage wrote its run folder path into 67 Seyda Neen region records, so its outputs differed in every run folder
- [BUILD-STAIR-KEY-BOOKKEEPING-36](BUILD-STAIR-KEY-BOOKKEEPING-36.md): Stair walk keys count the progress lines (stair_progress.py) and the record bookkeeping (stair_records.py): an edit to either rekeys every walk
- [BUILD-STAIR-PASS-NOT-KEPT-41](BUILD-STAIR-PASS-NOT-KEPT-41.md): A frame's passed stair walk is not reused when the build it ran in failed, and the walker key changes with converter code
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [CACHE-NO-PROVENANCE-36](CACHE-NO-PROVENANCE-36.md): Cache and pool entries were keyed by SHA-256 but did not record when, by which run, from which version and commit they were made, and some recorded no output hash
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [CHIMPORT-POOL-CROSS-MOUNT-36](CHIMPORT-POOL-CROSS-MOUNT-36.md): CHIMport run folder and the storage pool on two mounts of one volume: hard links fail across the mounts, so pooled units were copied, not linked
- [CHIMPORT-RETRY-AUDIT-FAILED-36](CHIMPORT-RETRY-AUDIT-FAILED-36.md): CHIMport --retry-failed never reran cells that converted but failed an audit (memory fit, doors, hull chains): the runner marks them done
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
