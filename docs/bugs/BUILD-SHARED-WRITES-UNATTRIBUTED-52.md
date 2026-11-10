# BUILD-SHARED-WRITES-UNATTRIBUTED-52: Stages running side by side write the same files, so their records are refused and they rebuild every time

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.63-dev2 at 2026-11-09 10:21 +0200: Seen again in the reuse plan of v0.0.63-dev2 against 2026_11_09_v0.0.63-dev1_full-v0.0.63-dev1_dc356e3: chim-town-seyda and chim-town-vivec_city both refused, because both changed intro-scene/id1/sound/env/lava_layer.wav and 10 more shared files while running side by side; both towns rebuild again.
- Reported with v0.0.63-dev2 at 2026-11-09 11:28 +0200: Cause found in the v0.0.63-dev1 records: the two towns did not write the 11 files. world-terrain wrote the lava loop sound and world-ui the 10 world files while both towns ran beside them. The records were judged pair by pair in name order, so the two towns were compared before the world stages had taken their files back, and both towns were refused. Fixed: every pair that the traces can attribute is settled first, a record refused only for such files is reusable when read again, and the files two stages write are listed and kept from growing by a test (config/shared-writes.json, 50 files left for one owner each). The reuse plan of v0.0.63-dev2 against the dev1 build now reuses both towns: 41 of 47 stages, 0 unexpected.
- Reported with v0.0.63-dev1 at 2026-11-09 11:43 +0200: The reuse plan of the next build against the v0.0.63-dev1 run refuses the records of chim-town-seyda and chim-town-vivec_city: both changed intro-scene/id1/sound/env/lava_layer.wav and ten more files while running side by side, so both stages are rebuilt.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 26 October 2026, in v0.0.52-dev1 |
| Where | the town stages (resident items folder) and the two room stages (door audio) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.52-dev1 (last seen) |
| Severity | medium: Five stages, the three towns and both room stages, rebuild in every resumed build: tens of minutes each time |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_26_v0.0.52-dev1_dev1-try8_9d4c05f7 |
| From commit | source 9d4c05f, engine 9d4c05f, CHIM world 9d4c05f |
| CHIM engine version | CHIM 0.2.2, engine 9d4c05f, world format 0.13 |
| Platform or emulator | builder |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.63-dev2 (9 November 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 3 times; something has to be done](#persisting-reported-3-times-something-has-to-be-done)
- [What happens](#what-happens)
- [Seen](#seen)
- [Status: 9 November 2026](#status-9-november-2026)
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

## What happens

When two build stages run side by side and both write the same file, the builder cannot tell which stage the
file belongs to. It refuses both stages' records, so the next build with reuse runs both stages again although
their own inputs did not change.

## Seen

- v0.0.52-dev1: the town carried-item models and the room door audio.
- v0.0.63-dev1: the reuse plan of the next build against the v0.0.63-dev1 run refuses the records of the
  Seyda Neen and Vivec town stages: both changed the lava sound layer of the intro scene and ten more files
  while running side by side.

## Status: 9 November 2026

Fixed on the v0.0.63 line for the case seen in v0.0.52 and again in v0.0.63-dev2: a file a third stage wrote no
longer refuses the two stages that saw it change beside it. The files two stages really both write are listed and
kept from growing; giving each of them one owner stage is still open (BUILD-STAGE-WRITES-OTHERS-OUTPUT-63).

## Symptom

The reuse plan of v0.0.63-dev2 against the v0.0.63-dev1 build refused the Seyda Neen and Vivec town stages: each
"changed intro-scene/id1/sound/env/lava_layer.wav (and 10 more) while" the other ran, and their outputs could not
be attributed. Both towns would have been rebuilt, the Vivec town alone about 11 minutes. The same refusal was seen
in the v0.0.52-dev1 builds.

## Where

The builder's stage records (`tools/build_cache.py`, `Recorder.close`), which decide after a build which stage
owns each file that changed while stages ran at the same time.

## How it happened

Neither town wrote those 11 files. The world terrain stage wrote the lava loop sound and the world map stage wrote
10 world files while both towns were running, so all four stages saw them change. The write trace of each stage
knows who wrote what, and `Recorder.close` uses it to give a file to its writer. It judged the stage pairs in name
order, though: the two towns were compared before the two world stages, while both town records still held the
world stages' files. Neither town had written them, so no single writer could be named for that pair, and both
towns were refused. The later pairs then gave the files to the world stages, but the refusal was already written.

## Why it was not caught

The tests of the attribution covered two stages at a time, never a third stage writing beside two others.

## Reproduction

Any build in which two stages run beside a third stage that writes into a folder all three record, and the two sort
before the third by name.

## Repair

- Every stage pair the write traces can attribute is settled first; only then are the remaining pairs judged.
- A record written before the fix and refused only for this reason is reusable when it is read again, if it and the
  other stage's record no longer share any file (`resettled` in the record).
- Each build records the files two stages both wrote (`profile/manifests/shared-writes.json`) and prints any file
  that `config/shared-writes.json` does not list.

## Verification

- `tests/test_shared_writes.py`: a file a third stage wrote refuses neither stage beside it; a file nobody wrote
  still refuses both; old records are made reusable only when nothing is shared any more; the list of shared files
  never grows.
- The reuse plan of v0.0.63-dev2 against the v0.0.63-dev1 build: 41 of 47 stages reused, both towns among them,
  0 unexpected rebuilds (39 of 47 with 2 unexpected before); no stage key changed.

## Prevention

`config/shared-writes.json` lists the 50 files that two stages of the v0.0.63-dev1 build both wrote (door lists,
the palette and the Seyda Neen map of the scene stages). Each is to get one owner stage; the test fails when the
list grows.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-ACTOR-LIBRARY-MWAD-PATH-47](BUILD-ACTOR-LIBRARY-MWAD-PATH-47.md): The actor-library stage stopped at once: run as a script, tools/mwad.py hid the src/mwad package
- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CACHE-PROVENANCE-41](BUILD-CACHE-PROVENANCE-41.md): Some cache entries record no time or no versions: pool keys from CHIMport have empty versions and commit, world-terrain units and stage records have no creation time or version
- BUILD-CACHE-PROVENANCE-GROWTH-54 (no report page): chim-units/.provenance is one append-only 8.8 GB file; its growth per build is not measured
- BUILD-CELL-PROGRESS-ENGINE-KEY-48 (no report page): The tracker data stage (cell-progress) counted every engine source in its key: an engine-only edit rebuilt it
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
- BUILD-CHIM-HEAP-KEY-LOADER-63 (no report page): An engine model loader edit re-keys the whole CHIM world and its interiors
- BUILD-CHIM-KEY-ENGINE-FILE-WHOLE-54 (no report page): chim_world.c is keyed whole into the CHIM world, so a diagnostic print re-keys the world
- BUILD-CHIM-KEY-ENGINE-SOURCES-49 (no report page): An engine source edit rebuilds the whole CHIM world: the CHIM stage imports project_version, whose engine check names engine/aga/src files
- [BUILD-CHIM-KEY-UNDERDECLARED-35](BUILD-CHIM-KEY-UNDERDECLARED-35.md): The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk
- [BUILD-CHIM-KEY-VERSION-48](BUILD-CHIM-KEY-VERSION-48.md): The CHIM world and cell-progress stages key on VERSION, so a version-only bump (rc to final) rebuilds the whole CHIM world
- [BUILD-CHIM-LABEL-IN-KEYS-48](BUILD-CHIM-LABEL-IN-KEYS-48.md): The CHIM version label was in the stage keys: the x.x.1 release step rebuilt about 25 stages, the CHIM world among them
- BUILD-CHIM-RECORD-COMPILER-INCOMPLETE-51 (no report page): The chim stage's read record is always incomplete: it starts compilers with checkout paths, so it can never be reused when only its key's sources changed
- BUILD-CHIM-VIS-RECOMPUTED-48 (no report page): The CHIM stage recomputed every region frame's visibility (1 h 20 min on 24 cores)
- [BUILD-CUTOFF-WHOLE-ANCESTOR-51](BUILD-CUTOFF-WHOLE-ANCESTOR-51.md): An interior light change reran exterior stages: the reuse cutoff refuses a stage when any earlier stage's whole output differs, not the files it reads
- BUILD-DEV-GALLERY-SKIP-RC-REBUILD-48 (no report page): Development builds leave out the NPC gallery, so every release candidate builds all 3,551 faces fresh
- [BUILD-DIAGNOSTIC-INPUT-REFUSED-36](BUILD-DIAGNOSTIC-INPUT-REFUSED-36.md): The cell-progress stage was never reusable: it reads the CHIM stage's statistics report, which counted as a forbidden diagnostic read
- [BUILD-ENGINE-KEY-SDK-33](BUILD-ENGINE-KEY-SDK-33.md): The engine stage is never reused: the Amiga SDK is not part of its key
- [BUILD-FLORA-RECEIPT-SECONDS-36](BUILD-FLORA-RECEIPT-SECONDS-36.md): The world flora receipt held the stage's wall time, so a rerun with the same inputs never wrote the same receipt
- [BUILD-GALLERY-JSON-KEY-ORDER-35](BUILD-GALLERY-JSON-KEY-ORDER-35.md): NPC gallery outputs differed between two builds only in JSON key order (cache vs fresh results)
- BUILD-GAME-INPUT-KEY-BROAD-64 (no report page): Every stage that reads the game data was keyed by every game input, so an expansion file being present re-keyed the base world
- [BUILD-IMAGE-LAYOUT-SERIAL-49](BUILD-IMAGE-LAYOUT-SERIAL-49.md): The image step plans its disk layout and writes its partitions on about 1.6 of 24 cores for about three minutes
- [BUILD-IMAGE-NO-RESUME-33](BUILD-IMAGE-NO-RESUME-33.md): A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds
- [BUILD-IMAGE-STALE-PYTHONPATH-35](BUILD-IMAGE-STALE-PYTHONPATH-35.md): Builder container images put an old builder copy on PYTHONPATH
- [BUILD-KEY-FUNCTION-DEFAULTS-TOP-36](BUILD-KEY-FUNCTION-DEFAULTS-TOP-36.md): Adding a function to a shared module changed the key of every stage that imports it, although no stage runs the new code
- BUILD-KEY-KEYED-REACH-WHOLE-51 (no report page): Code handed to an in-stage cache key counted whole in the stage key: a helper added to tools/map_files.py rebuilt the CHIM world
- BUILD-KEY-MESH-TABLE-WHOLE-54 (no report page): A per-mesh measured table is keyed whole: one new row of collision-standing-room.json re-keyed every room, resident and model unit
- [BUILD-KEY-OVERBROAD-33](BUILD-KEY-OVERBROAD-33.md): A new bug page or release file list change rebuilds interior, census, harvest and the CHIM stages: an import search path counted as a read of every file under tools/
- BUILD-KEY-RULE-NO-FORM-51 (no report page): A change of the stage key rules without a new key form rebuilt stages whose inputs did not change
- BUILD-KEY-UNIT-RESTORED-CODE-52 (no report page): A stage whose last real run restored its units from a cache was reused after the code those units come from changed: chim-room-batches kept actor models of the old animation tables
- BUILD-MINIWIND-REUSE-STALE-57 (no report page): The MiniWind build launcher reused the v0.0.53 final run instead of the newest passed run
- BUILD-MWSCRIPT-KEY-UNDERDECLARED-48 (no report page): The mwscript stage's reuse record is refused: the stage reads tools/mwscript/measure.py, which its fingerprint leaves out
- BUILD-MWSCRIPT-STAGE-REUSED-COMPILER-CHANGED-59 (no report page): The mwscript stage was reused after its compiler changed, so v0.0.59 ships compiled scripts of an older compiler
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
- BUILD-REUSE-FOREIGN-DIRS-52 (no report page): A reused stage recreates, as empty folders, the folders another stage filled beside it: the area stage then stops on its own room folder
- [BUILD-REUSE-INTRO-CENSUS-REPLACED-48](BUILD-REUSE-INTRO-CENSUS-REPLACED-48.md): A reused MiniWind rooms build rebuilt the intro and census stages (replaced outputs) and its Balmora interiors (4 s to 1m21s)
- BUILD-REUSE-KEY-WALK-LISTED-51 (no report page): The read records of the CHIM world stages list almost every folder of the checkout, so a new bug page refuses their narrowed reuse
- BUILD-REUSE-OUTPUTS-DIFFER-48 (no report page): Eight stages were rebuilt because their earlier outputs differed from their records (character, reading, world-ui, actor-contact, world-terrain and others)
- [BUILD-REUSE-PLAN-ENV-36](BUILD-REUSE-PLAN-ENV-36.md): The standalone reuse plan reports environment changes the real build does not have
- BUILD-REUSE-RC1-RECORDS-REFUSED-48 (no report page): Every stage that ran the idle-worker watcher or read the CHIM label module was marked not reusable: rc1-try2 had 24 unexpected rebuilds
- [BUILD-REUSE-RECORD-RETIRED-36](BUILD-REUSE-RECORD-RETIRED-36.md): Early cutoff and the reuse audit lost their records when an older run was retired: stages with byte-identical outputs counted as changed
- [BUILD-REUSE-REDUCED-RECORD-36](BUILD-REUSE-REDUCED-RECORD-36.md): A stage reused from a run that had itself reused it came back without the files a later stage replaced there, so that later stage failed when it ran again
- [BUILD-REUSE-SCHEDULER-TOP-45](BUILD-REUSE-SCHEDULER-TOP-45.md): A scheduler-only edit rekeys every stage, NPC gallery face and stair walk that reaches tools/build_parallel.py
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- BUILD-REUSE-STOPPED-SOURCE-52 (no report page): Reusing a build that stopped early reruns every stage it never reached, though the build it reused holds them
- [BUILD-REUSE-TMP-RECORDED-DELETED-48](BUILD-REUSE-TMP-RECORDED-DELETED-48.md): A reused stage removed another stage's reuse copies mid-copy: its record listed them as deleted (balmora-interiors stopped at os.replace)
- BUILD-ROOM-BATCHES-KEY-UNDERDECLARED-48 (no report page): The room stage's reuse record is refused: it reads 17 repository files its fingerprint leaves out
- BUILD-ROOM-BATCHES-SCENE-RACE-48 (no report page): A reused build stopped in the room stage: it ran before the area stage had restored the scene map it reads (seyda.bsp)
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SEYDA-BOUNDED-RUN-PATHS-36](BUILD-SEYDA-BOUNDED-RUN-PATHS-36.md): The actor-contact stage wrote its run folder path into 67 Seyda Neen region records, so its outputs differed in every run folder
- [BUILD-SPRITE-KEY-HASHLIB-47](BUILD-SPRITE-KEY-HASHLIB-47.md): The CHIM stage failed 45 minutes into a build: the sprite recipe key used hashlib without importing it
- BUILD-STAGE-KEY-CLIENT-H-58 (no report page): An engine declaration added to client.h re-converts the CHIM world and its interiors
- BUILD-STAGE-KEY-TEXT-DEFINES-59 (no report page): The CHIM world and CHIM rooms stages rebuild when tools/text_defines.py changes, although the world does not use the text macros
- BUILD-STAGE-KEY-UNIT-STORE-63 (no report page): Five stage keys count the unit store code as a whole file, so one reuse table row rebuilds them
- BUILD-STAGE-KEY-WHOLE-CLASS-48 (no report page): A one-method edit in tools/actor_grounding.py rekeyed the CHIM stages: a class was import-time code of its module, so every stage importing the module hashed every method
- [BUILD-STAGE-READS-UNFINGERPRINTED-48](BUILD-STAGE-READS-UNFINGERPRINTED-48.md): Two stages read repository files their fingerprint leaves out, so their records are refused and they rerun on every reuse
- BUILD-STAGE-WRITES-OTHERS-OUTPUT-63 (no report page): A failed image step wrote into a file another stage owns, so resuming rebuilt Vivec city (11 min), the actor library (40 min) and the Vivec rooms (28 min)
- [BUILD-STAIR-KEY-BOOKKEEPING-36](BUILD-STAIR-KEY-BOOKKEEPING-36.md): Stair walk keys count the progress lines (stair_progress.py) and the record bookkeeping (stair_records.py): an edit to either rekeys every walk
- [BUILD-STAIR-PASS-NOT-KEPT-41](BUILD-STAIR-PASS-NOT-KEPT-41.md): A frame's passed stair walk is not reused when the build it ran in failed, and the walker key changes with converter code
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [BUILD-TABLE-UNITS-REBAKE-63](BUILD-TABLE-UNITS-REBAKE-63.md): Every build bakes the dialogue and voice tables and the actor ground check again
- [BUILD-VERSION-GETATTR-TRACE-49](BUILD-VERSION-GETATTR-TRACE-49.md): The v0.0.49 final rebuilt the CHIM world: the lazy VERSION (a module __getattr__ in project_version) ran in the CHIM stage, its read trace recorded it and the key could not
- [CACHE-NO-PROVENANCE-36](CACHE-NO-PROVENANCE-36.md): Cache and pool entries were keyed by SHA-256 but did not record when, by which run, from which version and commit they were made, and some recorded no output hash
- CHIM-COLLISION-UNION-FAIL-NOT-CACHED-48 (no report page): A collision union that fails is compiled again for every room that uses the same mesh packet
- [CHIM-INTERIORS-REUSE-MISS-48](CHIM-INTERIORS-REUSE-MISS-48.md): The CHIM rooms stage (chim-interiors) is never reused: it hashed the shared CHIM unit cache, which is past the 512 MiB folder limit
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [CHIMPORT-POOL-CROSS-MOUNT-36](CHIMPORT-POOL-CROSS-MOUNT-36.md): CHIMport run folder and the storage pool on two mounts of one volume: hard links fail across the mounts, so pooled units were copied, not linked
- [CHIMPORT-RETRY-AUDIT-FAILED-36](CHIMPORT-RETRY-AUDIT-FAILED-36.md): CHIMport --retry-failed never reran cells that converted but failed an audit (memory fit, doors, hull chains): the runner marks them done
- DOOR-CHECK-KNOWN-UNKEYED-54 (no report page): config/door-check-known.json is in no stage key: an edit to the known list never re-runs a passed image's door check
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
