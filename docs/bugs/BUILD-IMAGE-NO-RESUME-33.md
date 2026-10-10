# BUILD-IMAGE-NO-RESUME-33: A late failure in the image step reruns the whole image step, and the failing check could have run in its first seconds

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | Image step (tools/build_aga.py image/finalize_image) and stages without unit caches |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-rc1 (last seen) |
| Severity | high: The rc1c image step failed 3,082 s in on a check the preflight runs in 7 s; the rerun redid all 2,724 maps of every pass (51.7 min). |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | v0.0.33-rc1 builds rc1b and rc1c |
| From commit | source a266a40, engine a266a40, CHIM world a266a40 |
| CHIM engine version | CHIM 0.1.0, engine a266a40, world format 0.5 |

<!-- END GENERATED FACTS -->

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

- [BUILD-CACHE-OWNER-FAILS-STAGE-34](BUILD-CACHE-OWNER-FAILS-STAGE-34.md): A cache entry owned by another user failed a release build four minutes in, instead of being rebuilt or caught before any stage
- [BUILD-CELL-PROGRESS-KEY-BUGS-35](BUILD-CELL-PROGRESS-KEY-BUGS-35.md): Every bug registration stopped builds at the reuse preflight: the cell-progress key held all of docs/
- [BUILD-CHIM-KEY-UNDERDECLARED-35](BUILD-CHIM-KEY-UNDERDECLARED-35.md): The CHIM stage's fingerprint left out the tracker code it ran (8 files, 2 functions): a wrong-reuse risk
- [BUILD-ENGINE-KEY-SDK-33](BUILD-ENGINE-KEY-SDK-33.md): The engine stage is never reused: the Amiga SDK is not part of its key
- [BUILD-GALLERY-JSON-KEY-ORDER-35](BUILD-GALLERY-JSON-KEY-ORDER-35.md): NPC gallery outputs differed between two builds only in JSON key order (cache vs fresh results)
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
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SURVEY-KEY-CONFIG-35](BUILD-SURVEY-KEY-CONFIG-35.md): World survey, world terrain, world UI and CHIM stage keys counted every file under config/: a path built from a loop name read as the whole folder
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [CHIMPORT-NO-SHARED-POOL-35](CHIMPORT-NO-SHARED-POOL-35.md): The CHIMporter kept its own unit store beside the shared hashed storage pool: no pool flag, every run folder a private copy
- [MWAD-WALK-ORDER-35](MWAD-WALK-ORDER-35.md): Input check results depend on directory listing order

Related bugs in other categories:

- [BUILD-SEYDA-CONVERTED-NOT-STAGED-35](BUILD-SEYDA-CONVERTED-NOT-STAGED-35.md): A default CHIM build stopped at the image step's payload preflight: the Seyda Neen region maps are converted later in that step
- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out

<!-- END GENERATED CATEGORY -->
