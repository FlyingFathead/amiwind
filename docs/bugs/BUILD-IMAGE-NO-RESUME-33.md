# BUILD-IMAGE-NO-RESUME-33: A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | Image step (tools/build_aga.py image/finalize_image) and stages without unit caches |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-rc1, v0.0.48-rc1 (last seen) |
| Severity | high: The rc1c image step failed 3,082 s in on a check the preflight runs in 7 s; the rerun redid all 2,724 maps of every pass (51.7 min). |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | v0.0.33-rc1 builds rc1b and rc1c |
| From commit | source a266a40, engine a266a40, CHIM world a266a40 |
| CHIM engine version | CHIM 0.1.0, engine a266a40, world format 0.5 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Status: 9 October 2026](#status-9-october-2026)
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

## Status: 9 October 2026

In progress on v0.0.34-image-resume, not shipped at the time of writing. The payload preflight (the first part
of the repair) is in the v0.0.33 release line.

## Symptom

The v0.0.33-rc1 build rc1c passed 33 stages and then failed 3,082 s into the image step on the harvest
catalogue check (CHIM-HARVEST-SPECIALS-33). The rerun after the fix assembled the whole image step again:
every per-map pass (hidden-surface cull 123 s, BSP optimizer 685 s, stair walk 1,751 s) ran again on all
2,724 maps. The same error had stopped an earlier run that morning, so it cost two image runs (rc1b 2,803 s,
rc1c 3,099 s).

## Where

`tools/build_aga.py` (`image`, `finalize_image`): one sequential unit. The per-map pass cache
(`tools/pass_cache.py`) existed but was off for release candidates and finals. Stages without unit caches
(world scenery, world flora, the town regions) restart from zero too.

## How it happened

The image step grew pass by pass; each pass rewrites the staged maps in place and the payload checks ran
where their results were first needed, at the end. The pass cache was introduced for development builds only,
while release builds were meant to be built from scratch; a release build that failed late therefore had no
way to resume.

## Why it was not caught

Build time was measured per stage, not as the time from a payload error to its report, and no test or gate
checked that a check whose inputs exist early runs early.

## Reproduction

Build a release candidate whose image step fails on a payload check, fix the check, build again with
`--reuse-from`: the image step runs every pass on every map again.

## Repair

1. Payload preflight (release line, tools/payload_preflight.py): every read-only payload check over the staged
   payload, in parallel, before the image step writes anything; `build.py --check-payload RUN` runs it alone on
   a failed run. Measured on rc1c's real payload with the rc1c harvest check: the error in 7.2 s.
2. Per-map passes resume: the pass cache is on for release builds with `--allow-release-reuse` (the
   from-scratch reference build still runs separately); the sky pass is a cached per-map unit too.
3. Stage units resume: `pass_cache.UnitCache` stores a unit's folder of files and its receipt row by the
   content hash of all its inputs, the code that makes it and the settings it reads; world scenery and world
   flora regions use it.

## Verification

tests/test_payload_preflight.py (the harvest catalogue case from a fixture), tests/test_pass_cache.py
(maps and receipts identical with the cache off, cold and warm, for every cached pass),
tests/test_unit_cache.py (units: identical outputs off, cold and warm; a warm run converts nothing; a changed
input converts again; the key covers inputs, options, sources and settings).

## Prevention

Every stage resumes from its last completed unit; a stage that can only restart from zero is a bug. Checks
run as early as their inputs exist.

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
- [CHIMPORT-RETRY-AUDIT-FAILED-36](CHIMPORT-RETRY-AUDIT-FAILED-36.md): CHIMport --retry-failed never reran cells that converted but failed an audit (memory fit, doors, hull chains): the runner marks them done
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

Related bugs in other categories:

- [BUILD-SEYDA-CONVERTED-NOT-STAGED-35](BUILD-SEYDA-CONVERTED-NOT-STAGED-35.md): A default CHIM build stopped at the image step's payload preflight: the Seyda Neen region maps are converted later in that step
- [BUILD-SIZE-GUARD-LATE-48](BUILD-SIZE-GUARD-LATE-48.md): The size guard judges only after the image is built: an rc that grew for a known reason stops after 32 minutes of image work, and the rerun assembles the whole image again
- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out

<!-- END GENERATED CATEGORY -->
