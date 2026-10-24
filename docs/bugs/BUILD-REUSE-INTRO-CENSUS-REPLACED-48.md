# BUILD-REUSE-INTRO-CENSUS-REPLACED-48: a reused MiniWind rooms build rebuilt intro, census, balmora-interiors and actor-library

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 22 October 2026, in v0.0.48-dev2 |
| Where | tools/build_cache.py reuse plan; stages intro, census, balmora-interiors |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.48-dev2 (last seen) |
| Severity | medium: minutes of finished work redone in a reused build (project rule 7) |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | 2026_10_22_v0.0.48-dev2_miniwind-balmora-rooms-chim_f577f015 |
| From commit | source f577f01, engine f577f01, CHIM world f577f01 |
| CHIM engine version | CHIM 0.2.1, engine f577f01, world format 0.12 |
| Platform or emulator | not in game (a build step; nothing in the game changes) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

<!-- contents start -->
## Contents

- [Status: 22 October 2026](#status-22-october-2026)
- [Symptom](#symptom)
- [The refusal reasons (B's build-state.json, stage_cache.not_reused and each step's reuse_refused)](#the-refusal-reasons-bs-build-statejson-stage_cachenot_reused-and-each-steps-reuse_refused)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Repair](#repair)
- [Verification](#verification)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 22 October 2026

Repaired on the v0.0.48 room-passes branch (22 October 2026); not in a build yet.

## Symptom

2026_10_22_v0.0.48-dev2_miniwind-balmora-rooms-chim_f577f015 (B of the rooms A/B) reused
2026_10_22_v0.0.48-dev2_miniwind-balmora-rooms-chim_1ca025a1 (`--reuse-from`, pool mode; not the A run), yet ran
intro (15 s), census (10 s), balmora-interiors (1 m 21 s against 4 s reused), chim-town-balmora (28 s), actor-library
(2 m 41 s against 1 s), door-audio, character, reading, opening-references and chim-interiors again.

## The refusal reasons (B's build-state.json, stage_cache.not_reused and each step's reuse_refused)

| stage | reason recorded | cause |
| --- | --- | --- |
| balmora-interiors | old outputs not reusable: changed `intro-scene/area-work/bmbalyn/base.bsp` (and 378 more) while chim-town-balmora ran | this bug (below) |
| chim-town-balmora | the same, while balmora-interiors ran | this bug |
| census | its output `intro-scene/asset-name-map.json` was replaced later in 1ca025a1 by balmora-interiors, which is rebuilt | follows: three stages write that file, and the source run holds only the last version |
| intro | the same file, replaced later by census, which is rebuilt | follows |
| actor-library | an earlier stage it depends on ran again and its outputs differ: chim-town-balmora | follows: the source run's record of chim-town-balmora held the 379 room files it never wrote (489 files against 110) |
| door-audio, character, reading, opening-references | depends on balmora-interiors, whose outputs differ | follows |
| chim-interiors | `--unit-cache` folder larger than 512 MiB is not fingerprinted | CHIM-INTERIORS-REUSE-MISS-48, repaired on this branch after f577f015 |
| engine, image | never reused by rule | as intended |

The source run 1ca025a1 itself rebuilt these stages correctly: tools/map_files.py changed there (its own record:
"changed: sources (tools/map_files.py)" for bsp, interior, census, balmora-interiors, chim-town-balmora and the stages
after them). A (2026_10_22_v0.0.48-dev2_miniwind-balmora-rooms-bsp_1336ba94, reusing ..._bsp_dd768704) reused every
stage but engine, chim (tools/sky_palette_overlay.py changed: a correct rebuild) and image.

## Where

`tools/build_cache.py` `Recorder.close` and `attribute`. Two stages that run at the same time and both see a file
change under a run folder they both name are credited by the write trace: a file only one of them wrote is its output.
chim-town-balmora names `--scene RUN/intro-scene` (it reads the census palette there), so `intro-scene` is one of its
recorded roots, and it ran from 139 s to 171 s inside balmora-interiors' 77 s to 234 s. balmora-interiors compiles
each room with qbsp, vis and light (86, 43 and 43 processes in 1ca025a1). Those programs are not traced, so 112 of the
379 shared files (`room.prt`, `standing-collision.bsp`, `standing-collision.prt`, the `.log` files of 16 rooms) had no
traced writer, `attribute` returned "unknown", and both stages were recorded as not reusable.

## How it happened

Whether the attribution held depended on the run: in B the same two stages overlapped again (29.7 s to 110.4 s and
30.6 s to 58.3 s), but balmora-interiors' room compiles were copied in by Python (traced), so all 926 shared files were
credited to it and B's records are reusable. A real compile during the overlap made both stages, and everything after
them, unreusable.

## Repair

The read trace (`TRACE_HOOK` `spawned`) now lists, for every process it does not follow (a native program, or a Python
process started without the trace), the run folders it was pointed at: its working folder and the run paths on its
command line ('~' lines; `TRACE_MARKS`). `Recorder.traced_native_folders` reads them, and `attribute` counts a shared
file as possibly written by a stage when its Python processes wrote it or it lies under one of those folders. The
stage that may have written every shared file, while the other may have written none, is the writer. A program
started with no run folder named writes nothing in the run. Unknown or both: refused, as before.

On the 1ca025a1 overlap: the compiler's working folders are the room folders (`intro-scene/area-work/<room>`), and
chim-town-balmora's only untraced program (ffmpeg, 15 runs) was pointed at its own folder, so the 379 files go to
balmora-interiors and both stages stay reusable.

## Verification

`tests/test_build_cache.py` `WriteAttributionTests`: a compiler in the shared folder makes its stage the writer; a
compiler of either stage there, a program pointed at the whole run folder, or nobody's compiler keeps both refused;
the trace hook, run in a child process, lists a native program's working folder and its output path and nothing for
a program with no run path.

Expected: B's records of these stages are reusable, so a build reusing B reuses intro, census, balmora-interiors,
chim-town-balmora and actor-library unless their own inputs change; a build whose source run compiled rooms during
the overlap now records both stages as reusable. The first build of this branch still reruns the stages whose code
it changes, with that reason in its record (door-audio: tools/prepare_door_audio.py, AW-20260928-10; chim-interiors:
tools/chim/interior.py; any stage whose recorded units of tools/map_files.py changed).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-ACTOR-LIBRARY-MWAD-PATH-47](BUILD-ACTOR-LIBRARY-MWAD-PATH-47.md): The actor-library stage stopped at once: run as a script, tools/mwad.py hid the src/mwad package
- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CACHE-PROVENANCE-41](BUILD-CACHE-PROVENANCE-41.md): Some cache entries record no time or no versions: pool keys from CHIMport have empty versions and commit, world-terrain units and stage records have no creation time or version
- BUILD-CELL-PROGRESS-ENGINE-KEY-48 (no report page): The tracker data stage (cell-progress) counted every engine source in its key: an engine-only edit rebuilt it
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
- [BUILD-CHIM-KEY-UNDERDECLARED-35](BUILD-CHIM-KEY-UNDERDECLARED-35.md): The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk
- BUILD-CHIM-KEY-VERSION-48 (no report page): The CHIM world and cell-progress stages key on VERSION, so a version-only bump (rc to final) rebuilds the whole CHIM world
- [BUILD-CHIM-LABEL-IN-KEYS-48](BUILD-CHIM-LABEL-IN-KEYS-48.md): The CHIM version label was in the stage keys: the x.x.1 release step rebuilt about 25 stages, the CHIM world among them
- BUILD-CHIM-VIS-RECOMPUTED-48 (no report page): The CHIM stage recomputed every region frame's visibility (1 h 20 min on 24 cores)
- BUILD-DEV-GALLERY-SKIP-RC-REBUILD-48 (no report page): Development builds leave out the NPC gallery, so every release candidate builds all 3,551 faces fresh
- [BUILD-DIAGNOSTIC-INPUT-REFUSED-36](BUILD-DIAGNOSTIC-INPUT-REFUSED-36.md): The cell-progress stage was never reusable: it reads the CHIM stage's statistics report, which counted as a forbidden diagnostic read
- [BUILD-ENGINE-KEY-SDK-33](BUILD-ENGINE-KEY-SDK-33.md): The engine stage is never reused: the Amiga SDK is not part of its key
- [BUILD-FLORA-RECEIPT-SECONDS-36](BUILD-FLORA-RECEIPT-SECONDS-36.md): The world flora receipt held the stage's wall time, so a rerun with the same inputs never wrote the same receipt
- [BUILD-GALLERY-JSON-KEY-ORDER-35](BUILD-GALLERY-JSON-KEY-ORDER-35.md): NPC gallery outputs differed between two builds only in JSON key order (cache vs fresh results)
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
- [BUILD-RESUME-HAZARD-STATIC-35](BUILD-RESUME-HAZARD-STATIC-35.md): A resume failed in 'area': the rebuild hazard counted files of a reused stage that had run again after all
- [BUILD-RESUME-OUTPUTS-DIFFER-35](BUILD-RESUME-OUTPUTS-DIFFER-35.md): Every v0.0.35 resume refused the stages after a rerun scene-chain stage as 'outputs differ' without comparing them
- [BUILD-REUSE-ATTRIBUTION-33](BUILD-REUSE-ATTRIBUTION-33.md): Two stages that ran at the same time were both refused reuse when one wrote files under a folder the other only reads
- [BUILD-REUSE-AUDIT-WITHOUT-REASON-36](BUILD-REUSE-AUDIT-WITHOUT-REASON-36.md): The reuse audit and preflight called a stage rerun because its old record was short a replaced file UNEXPECTED, although the reason explains it
- [BUILD-REUSE-CASCADE-36](BUILD-REUSE-CASCADE-36.md): A fix in CHIM-native town code made 23 of 36 stages rebuild: the interior stage reran with different outputs and 5 rebuilds were unexpected
- [BUILD-REUSE-CUTOFF-MODE-36](BUILD-REUSE-CUTOFF-MODE-36.md): Early cutoff compared file modes with their write bits: a stage reused by hard link (read-only) never matched the same bytes written fresh, so 10 stages after dev3's bsp rerun were refused
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
- [CACHE-NO-PROVENANCE-36](CACHE-NO-PROVENANCE-36.md): Cache and pool entries were keyed by SHA-256 but did not record when, by which run, from which version and commit they were made, and some recorded no output hash
- CHIM-COLLISION-UNION-FAIL-NOT-CACHED-48 (no report page): A collision union that fails is compiled again for every room that uses the same mesh packet
- [CHIM-INTERIORS-REUSE-MISS-48](CHIM-INTERIORS-REUSE-MISS-48.md): The CHIM rooms stage (chim-interiors) is never reused: it hashed the shared CHIM unit cache, which is past the 512 MiB folder limit
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [CHIMPORT-POOL-CROSS-MOUNT-36](CHIMPORT-POOL-CROSS-MOUNT-36.md): CHIMport run folder and the storage pool on two mounts of one volume: hard links fail across the mounts, so pooled units were copied, not linked
- [CHIMPORT-RETRY-AUDIT-FAILED-36](CHIMPORT-RETRY-AUDIT-FAILED-36.md): CHIMport --retry-failed never reran cells that converted but failed an audit (memory fit, doors, hull chains): the runner marks them done
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
