# BUILD-REUSE-SCHEDULER-TOP-45: a scheduler-only edit rekeys every stage, NPC gallery face and stair walk

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 19 October 2026, in v0.0.45 |
| Where | v0.0.45 release build: npc-gallery, CHIM stair gate, world-terrain |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.45 (last seen) |
| Severity | high: about 30 minutes of a release build redone; reuse-bug class (hold-level) |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_19_v0.0.45_release_c9099fb8 |
| From commit | source c9099fb, engine c9099fb, CHIM world c9099fb |
| CHIM engine version | CHIM 0.2.1, engine c9099fb, world format 0.7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [Status: 19 October 2026](#status-19-october-2026)
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

## Status: 19 October 2026

Open. Part 1 repaired in v0.0.45: scheduling functions no longer change a module's import-time key
(`tools/build_cache.py`, `SchedulingKeysTest`), which removes the NPC gallery's re-conversion. Part 2 for v0.0.46: the
stair walks are keyed by the code of the world loader they reach (see "How it happened"); they should be keyed by
the bytes of the frames they walk. The v0.0.45 release build ran before any repair and paid for it once.

PERSISTING: the same mechanism as [BUILD-KEY-FUNCTION-DEFAULTS-TOP-36](BUILD-KEY-FUNCTION-DEFAULTS-TOP-36.md).
First ran into it with v0.0.36-dev1 (10 October 2026: stage keys, fixed there for stage keys only); ran into it
again with v0.0.36-dev3 (11 October 2026: image-pass keys,
[BUILD-PASS-KEY-OVERBROAD-36](BUILD-PASS-KEY-OVERBROAD-36.md)); and again with v0.0.45 (19 October 2026: NPC gallery
face keys and the stair walker key, this page).

## Symptom

The v0.0.45 release build (`2026_10_19_v0.0.45_release_c9099fb8`, reused from the v0.0.44 release) redid work whose
inputs had not changed:

- the NPC gallery: `Gallery cache: 0 verified hits, 3551 conversions required` (about 20 minutes);
- the CHIM stair gate: `1351 frames walked, 0 reused; why walked: 1351 walker code changed` (7 min 28 s on about
  22 cores);
- world-terrain and the gallery stage itself were planned as `rebuild EXPECTED: tools/build_parallel.py changed`.

The only change those keys saw between v0.0.44 and the build commit was `tools/build_parallel.py`, and that change
only touched how the pools schedule their units.

## Where

`tools/build_cache.py` `SourceIndex.unit_digest` and `unit_hashes` (scope `units`): the code part of every stage
fingerprint, of each NPC gallery face key (`tools/gallery_cache.py` `converter_sources`) and of the stair walker's key.

## How it happened

Measured 19 October 2026 by computing each key in both source trees (v0.0.44 release commit c84f850 and the
v0.0.45 build commit c9099fb8), each with its own code:

| Key | Changed inputs |
| --- | --- |
| NPC gallery faces (`tools/gallery_cache.py` `converter_sources`, key form 1) | `tools/build_parallel.py` only |
| CHIM stair walks (`chim.collision.stair_code_selection`, form `chim-stair-code-1`) | `tools/chim/validate.py` only |
| Legacy-map stair walks (`stair_walk.walk_key_sources`) | changed; inputs not yet measured |

So the gallery re-keyed through the form-1 import-time text (below). The CHIM stair walks re-keyed because the
walker reaches `load_world` in `tools/chim/validate.py`, which v0.0.45 rewrote to load frames on the worker pool
(BUILD-CHIM-SERIAL-SECTIONS-44): real code on the walk's input path, so the key is not wrong, only too coarse. A
first measurement of the walker's older key form (`stair_records.walker_sources`, used only to adopt old records)
showed `VERSION` and the stair pool among its inputs; that form is not the one the build uses.

The v0.0.45 pool changes ([BUILD-CHIM-SERIAL-SECTIONS-44](BUILD-CHIM-SERIAL-SECTIONS-44.md)) added the functions
`_grow_seconds` and `_sized_map` and a default `item_mib=None` to `governed_map`. Their own text was already left
out of the keys (`SCHEDULING_UNITS`), but a module's import-time text in top format 1 lists every plain function's
default values (`\0defaults NAME: ...`), so adding a function, or a default to one, still changed the import-time
code of `tools/build_parallel.py`, and with it every key that reaches that module.

## Why it was not caught

- The comment above `SCHEDULING_UNITS` named a test in `tests/test_build_cache.py` that did not exist.
- The reuse preflight (`CHECK=1`) labels any changed input file as EXPECTED, so a key that is too broad looks the
  same as a real change. The rebuild list was not read against the commit diff before the build started: a change
  to scheduling code alone should rebuild nothing.

## Reproduction

Always: edit only a scheduling function of `tools/build_parallel.py` (add one, or add a default value to one) and
compute the key of a stage that calls `ordered_map` or `governed_map`.

## Repair

`build_cache.scheduling_top_text` leaves the default-value lines of a module's scheduling functions out of its
import-time text; `unit_digest` and `unit_hashes` hash that text. The scheduling functions are still followed (what
they call keys the stages that reach it), and every other edit of the module still changes the keys.

The repair itself changes the import-time text of `tools/build_parallel.py` once, so the first build after it
recomputes the keys that reach that module once more; from then on a scheduling edit keys nothing.

Still to do in v0.0.46 (this page stays open until then): the NPC gallery face keys move to key form 2 like the
stage and pass keys; a stair walk is keyed by the SHA-256 of the frame data it walks instead of by the loader's code
(a loader rewrite with identical output reuses every walk, a changed frame walks again); the legacy-map walk key's
changed inputs are measured; each with a test that edits only that input and expects the right key.

## Verification

`SchedulingKeysTest` (in a container): a changed scheduling body, a default added to `governed_map` and a default on
`_grow_seconds` keep the key in both top formats; the v0.0.44 scheduler (no `_grow_seconds`, no `_sized_map`, no
`item_mib`) has the same key as the v0.0.45 one; an import-time constant and a reached function still change it. The
same tests run against the previous `tools/build_cache.py` fail twice.

## Prevention

- The test above runs in every gate.
- Before a build, every EXPECTED rebuild is read against the commit diff; one explained only by scheduling code
  stops the build (planned: the reuse preflight refuses it itself).

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
- [BUILD-PASS-KEY-OVERBROAD-36](BUILD-PASS-KEY-OVERBROAD-36.md): Image-pass and unit cache keys changed with code no pass runs: a new function in a shared module and edits to the cache's own key code rekeyed every character head preview twice (Vivec stage A try2 and try3: 275 of 275 recomputed)
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

Related bugs in other categories:

- [BUILD-CHIM-SERIAL-SECTIONS-44](BUILD-CHIM-SERIAL-SECTIONS-44.md): The CHIM stage runs several sections on one core while units wait: visibility rows starve their workers
- [BUILD-REUSE-KEYS-TOO-BROAD-35](BUILD-REUSE-KEYS-TOO-BROAD-35.md): A whole build reused no stage, and the cost was not visible before the build started

<!-- END GENERATED CATEGORY -->
