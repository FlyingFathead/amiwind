# BUILD-POOL-ARG-UNFINGERPRINTED-35: The balmora stage was never reusable once the shared storage pool grew past 512 MiB: its --npc-model-pool folder was hashed as an input

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | tools/build_cache.py external_inputs (--npc-model-pool of balmora, area, interiors, towns) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | high: balmora (and every other stage given the pool folder) rebuilt in every build: hold-level reuse loss under the primary build imperative |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | MiniWind v0.0.35-dev1 animkit-companion |
| From commit | source c2b7a3e, engine c2b7a3e, CHIM world c2b7a3e |
| CHIM engine version | CHIM 0.1.0, engine c2b7a3e, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on the v0.0.35 line, not shipped.

## Symptom

The reuse preflight of a v0.0.35-dev1 MiniWind build printed
`rebuild balmora UNEXPECTED other: --npc-model-pool={WORKSPACE}/cache/asset-pool-v1: folder larger than 512 MiB is
not fingerprinted`, and the build's failure watch reported `balmora (other)` before it. Once the shared storage
pool was really used it grew past 512 MiB, and from then on the balmora stage could never be reused.

## Where

`tools/build_cache.py`, `external_inputs`: every stage the builder gives the pool folder as `--npc-model-pool`
(`tools/build.py` `npc_lod_arguments`: area, balmora, balmora-interiors and every town stage).

## How it happened

The builder fingerprints a folder named on a stage's command line by hashing every file in it, and refuses
(stage not reusable) when the folder is over 512 MiB. The stage table of content-addressed caches
(`CONTENT_ADDRESSED`) listed the media and intro stages' `--cache`, which is the same pool, but not the resident
NPC bake's `--npc-model-pool`. So the balmora fingerprint also changed with every object any build added to the
pool, and failed outright once the pool passed the limit.

The pool is content-addressed: a stage reads it only through keyed lookups (`tools/file_cache.py`: a key is a hash
of the source files, settings and code an output depends on) and verifies every object against its SHA-256. What
balmora reads from it is fixed by inputs its fingerprint already covers (the game data, its code).

## Why it was not caught

The tests named a pool only through the media and intro stages, and the development pools stayed under 512 MiB
until every build started to use the shared pool (`--reuse-mode pool`).

## Reproduction

Any build whose storage pool holds more than 512 MiB: balmora is rebuilt with reason "other".

## Repair

- One rule at the shared layer: an argument naming the storage pool, or a folder inside it (the default
  `WORKSPACE/cache/asset-pool-v1` or the configured `--storage-pool-dir`), counts as its token
  (`in_storage_pool`), for every stage and option. The 512 MiB guard still applies to every other folder.
- The read trace lists every file a stage reads inside the pool. A read that is not a keyed lookup
  (`keys/NAMESPACE/..`) or an object it names (`objects/..`) makes the stage not reusable; the stage manifest
  records the pool reads per namespace (`pool_reads`).
- The resident bake's pool key now covers all the code the bake runs (`npc_lod.BAKE_MODULES`: NPC geometry and
  faces, NIF and archive reading, root rules) and the versions of the packages it computes with. Before, only two
  modules counted, so an edit elsewhere on the bake path could reuse an older bake. The resident bakes are made
  once more with the new keys.

## Verification

`tests/test_build_pool_arg.py`: balmora keeps its fingerprint with a pool over the limit and as the pool grows; the
same for area, interiors, a town and a pool named elsewhere; the media and intro keys are unchanged; a changed game
data file (the NPC meshes) still changes balmora's fingerprint; a real input folder over the limit is still
refused; the bake modules cover what the bake imports and an edit to one changes the key; the read trace lists pool
reads and refuses any that is not keyed.

## Prevention

The trace check after every build reports a stage that reads the pool outside its keyed lookups; build_audit lists
it with the other uncovered reads.

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
- [BUILD-POOL-READONLY-SCENE-WRITE-35](BUILD-POOL-READONLY-SCENE-WRITE-35.md): A pool-mode resume failed in 17 s: npcs could not rewrite its copy of seyda.bsp (copytree kept the pool's read-only mode)
- [BUILD-RESUME-HAZARD-STATIC-35](BUILD-RESUME-HAZARD-STATIC-35.md): A resume failed in 'area': the rebuild hazard counted files of a reused stage that had run again after all
- [BUILD-RESUME-OUTPUTS-DIFFER-35](BUILD-RESUME-OUTPUTS-DIFFER-35.md): Every v0.0.35 resume refused the stages after a rerun scene-chain stage as 'outputs differ' without comparing them
- [BUILD-REUSE-ATTRIBUTION-33](BUILD-REUSE-ATTRIBUTION-33.md): Two stages that ran at the same time were both refused reuse when one wrote files under a folder the other only reads
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

<!-- END GENERATED CATEGORY -->
