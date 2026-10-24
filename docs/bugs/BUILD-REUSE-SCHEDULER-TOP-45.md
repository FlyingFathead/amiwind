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

_Last updated with AmiWind v0.0.45 (20 October 2026)._

<!-- contents start -->
## Contents

- [Status: 20 October 2026](#status-20-october-2026)
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

## Status: 20 October 2026

Open until a build verifies part 2. Part 1 repaired in v0.0.45: scheduling functions no longer change a module's
import-time key (`tools/build_cache.py`, `SchedulingKeysTest`), which removes the NPC gallery's re-conversion. Part 2
repaired on branch `v0.0.45-reuse-keys` (not merged, 20 October 2026): the NPC gallery face keys use key form 2, a
CHIM frame's stair walk is keyed by the frame data it walks and the walk's own code (not the frame loader's), the
pool sizing constants of `tools/stair_parallel.py` key no legacy-map walk, and the reuse preflight stops a build
whose rebuilds only scheduling code, `VERSION` or prose explain (see "Repair"). The v0.0.45 release build ran before
any repair and paid for it once; the first build after part 2 pays once more (below).

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
| Legacy-map stair walks (`stair_walk.walk_key_sources`) | `tools/stair_parallel.py` import-time code only |

Measured per reached unit on 20 October 2026 (each tree with its own code, pass key form 2): the CHIM stair key
changed only through the import-time code (`<top>`) of `tools/chim/validate.py`, no function the walk runs; the
legacy-map walk key only through the import-time code of `tools/stair_parallel.py`, where v0.0.45 added the pool
sizing constants `UNIT_MIN_HEAVY` and `COST_POOL` (BUILD-IMAGE-STAIR-WALK-CORES-43). Both are scheduling or loading
changes that cannot change a row.

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

Part 2 (branch `v0.0.45-reuse-keys`, 20 October 2026):

- NPC gallery faces: `tools/gallery_cache.py` `converter_sources` hashes import-time code in key form 2
  (`KEY_FORMAT` 'reached code 2', `KEY_TOP_FORMAT` = `build_cache.STAGE_TOP_FORMAT`). The form is part of every
  face's identity: every face is converted once more in the first build after the change.
- CHIM stair walks: key form `chim-stair-code-2`. A walk's key is the SHA-256 of the frame data it walks
  (`frame_stair_parts`: the frame grid, each chunk's terrain walk lumps, each owned placement with its model's
  walk lumps, computed from the world the gate read) plus the walk's own code. The frame loader
  (`STAIR_FRAME_LOADER`, `chim/validate.py` `load_frame`) is no longer in the code part: the reach stops there
  (`build_cache.SourceIndex.entry_units` with a stop list), and `face_polygons`, which the walk runs, moved to
  `tools/chim/faces.py` (`chim/validate.py` still offers it), so `chim/validate.py` is out of the walk's code. In
  exchange every walk worker checks the frame it reads against the walk's data key (`_stair_frame` EXPECT, passed
  with every walk unit) and walks nothing on a mismatch: a walk is never stored or reused for data other than what
  it walked. A loader rewrite with the same output reuses every walk; a changed frame gets another key and is
  walked again.
- Legacy-map stair walks: `build_cache.SCHEDULING_CONSTANTS` leaves the assignment lines of the pool sizing
  constants of `tools/stair_parallel.py` (`UNITS_PER_WORKER`, `UNIT_MIN`, `UNIT_MAX`, `UNIT_MIN_HEAVY`,
  `COST_POOL`) out of its import-time text. Measured with the new key code on both trees: the v0.0.44 and v0.0.45
  trees give the same legacy-map walk key and the same NPC gallery face key.
- The reuse preflight (`tools/reuse_report.py`, `CHECK=1` and `tools/build.py --reuse-plan`): a rebuild whose own
  changed inputs are only the pool scheduling modules (`tools/build_parallel.py`, `tools/stair_parallel.py`),
  `VERSION` (for a stage that does not write the version into its outputs; the chim stage does) or prose, with no
  real change upstream, is cause "scheduling or version only" and stops the build before any stage runs, like an
  over-broad key; `--accept-rebuild` with the reason builds anyway. The v0.0.45 release build's preflight would
  have stopped on 16 such stages.

One-time cost of part 2: the first build after it converts the NPC gallery faces and walks the CHIM frames and the
legacy maps once more (new key forms). `tools/stair_records.py` `adopt` can carry a passed run's walks over to the
new keys after walking a sample again.

## Verification

`SchedulingKeysTest` (in a container): a changed scheduling body, a default added to `governed_map` and a default on
`_grow_seconds` keep the key in both top formats; the v0.0.44 scheduler (no `_grow_seconds`, no `_sized_map`, no
`item_mib`) has the same key as the v0.0.45 one; an import-time constant and a reached function still change it. The
same tests run against the previous `tools/build_cache.py` fail twice.

Part 2 (in a container; each test fails against the code before part 2):

- `tests/test_gallery_cache.py` `test_face_keys_use_key_form_2`: a function or literal default added to a reached
  module keeps every face key; a default that runs code and a reached edit change it.
- `tests/test_chim_stair_pass.py` `test_loader_edits_keep_the_key_face_edits_change_it`: an import-time edit of
  `chim/validate.py` (what v0.0.45 changed), an edit of `load_frame` and of a file reader only the loader uses keep
  the walker key; an edit of `face_polygons` changes it. `WalkedDataIsKeyedData`: a walk worker given a frame key
  other than its frame's, or whose loader returns other data, walks nothing; a gate whose loader reads other data
  stores no walk; an unchanged world reuses its walks and a moved placement changes the frame's key. The traced
  walk runs nothing outside the walk's code but the loader's own functions.
- `tests/test_build_cache.py` `SchedulingConstantsTest`: the v0.0.44 stair pool's key equals v0.0.45's; a sizing
  constant edit keeps it, another import-time edit or a walk edit changes it; every sizing constant is a one-line
  literal read only by the pool sizing.
- `tests/test_reuse_report.py` `test_a_rebuild_explained_only_by_scheduling_code_or_version_stops_the_build`.

## Prevention

- The tests above run in every gate.
- The reuse preflight refuses a rebuild explained only by scheduling code, `VERSION` or prose before any stage runs.

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
- [CHIMPORT-RETRY-AUDIT-FAILED-36](CHIMPORT-RETRY-AUDIT-FAILED-36.md): CHIMport --retry-failed never reran cells that converted but failed an audit (memory fit, doors, hull chains): the runner marks them done
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

Related bugs in other categories:

- [BUILD-CHIM-SERIAL-SECTIONS-44](BUILD-CHIM-SERIAL-SECTIONS-44.md): The CHIM stage runs several sections on one core while units wait: visibility rows starve their workers
- [BUILD-FACE-KEY-FORM-TEST-48](BUILD-FACE-KEY-FORM-TEST-48.md): The face key test tied the gallery face keys to the stage key form; stage keys in form 3 failed it (the faces rightly keep form 2)
- [BUILD-REUSE-KEYS-TOO-BROAD-35](BUILD-REUSE-KEYS-TOO-BROAD-35.md): A whole build reused no stage, and the cost was not visible before the build started
- [BUILD-SIZE-GUARD-OLD-BASELINE-45](BUILD-SIZE-GUARD-OLD-BASELINE-45.md): The size guard compared a release build with an older release's record: v0.0.45, every folder the size of v0.0.44's, failed on 0.44 GiB of CHIM world growth against v0.0.41

<!-- END GENERATED CATEGORY -->
