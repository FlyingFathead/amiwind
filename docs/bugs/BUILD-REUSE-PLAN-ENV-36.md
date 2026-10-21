# BUILD-REUSE-PLAN-ENV-36: The standalone reuse plan reports environment changes the real build does not have

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.36-dev1 at 2026-10-10 (time not recorded): standalone plan marked scene, bsp, world-survey and others rebuilt for environment; the build's own preflight reused 18 of 26
- Reported with v0.0.45 at 2026-10-20 05:45 +0300: plan of a6a9c6e9 against the v0.0.45 release run: 8 of 39 reused, 31 rebuilt, most for environment alone

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 10 October 2026, in v0.0.36-dev1 |
| Where | tools/reuse_report.py plan_main via build.py --reuse-plan |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev1, v0.0.45 (last seen) |
| Severity | medium: Under the reuse rule an unexplained rebuild stops a build: a false alarm can stop a valid build or teach people to ignore the plan |
| Family | Build reuse keys and output attribution (`build-cache-reuse`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine b932abd |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (20 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 2 times; something has to be done](#persisting-reported-2-times-something-has-to-be-done)
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

PERSISTING: first reported with v0.0.36-dev1 (10 October 2026), reported again with v0.0.45 (20 October 2026). The
planned repair (below, 10 October) was never made, so the plan kept giving false numbers for ten days. Cause found
and repaired on branch `v0.0.46-reuse-plan-env` on 20 October 2026 (not merged yet): the build and the standalone plan
set the stage environment through the same functions. Until it is merged, the workaround stands: read the reuse
preflight the build itself prints before its first stage (developer mode, line "(f)"), or the `--check` run of the
build service.

## Symptom

`build.py --reuse-plan OLD_RUN` marked several stages (scene, bsp, world-survey and others) as rebuilt with the cause
"input change: environment", with no changed file behind it. The build started right after with the same options
printed its own preflight: 18 of 26 stages reused, every rebuild explained by a changed file.

Again on 20 October 2026: the plan of the v0.0.45 dev line head (a6a9c6e9) against the v0.0.45 release run
`2026_10_19_v0.0.45_release-try2_c9099fb8` said "8 of 39 stages planned for reuse, 31 rebuilt (2 by policy),
0 UNEXPECTED". world-survey, scene, harvest, door-audio, reading, world-ui, actor-contact and cell-progress were among
the stages planned as rebuilt for the environment alone. The "0 UNEXPECTED" made it look plausible, because the
preflight counts an environment change as EXPECTED.

## Where

`tools/reuse_report.py` `plan_main`, reached through `build.py --reuse-plan`; the stage environment fingerprint
(`tools/build_cache.py` `stage_environment`).

## How it happened

A stage's fingerprint includes the AMIWIND_* variables its code reads. A build sets several of them from its options
before the stages run. The standalone plan runs without those options, so it sees the variables unset and compares
them with the values the old run recorded.

In detail (measured 20 October 2026): `build.py --reuse-plan` returns at the top of `main()`, before the two places
where `main()` exports its options. One is the option block: the NPC root rule, actor search, interior creatures,
the NPC animation kit, the stair walk scope and the CHIM native towns. The other is the converter block: the stair
rules, model hulls, lava, the world map, streamed statics, the CHIM frame extension and region rows, NPC head detail
and the head reducer. Each stage's computed environment was compared with the values the reuse source recorded in
`profile/fingerprints.json`. 15 variables differed, and in every case the run had a value that the plan left unset:
`AMIWIND_ACTOR_SEARCH`, `AMIWIND_CHIM_FRAME_EXT`, `AMIWIND_CHIM_NATIVE_TOWNS`, `AMIWIND_CHIM_REGION_ROWS`,
`AMIWIND_CHIM_STREAM_STATICS`, `AMIWIND_INTERIOR_CREATURES`, `AMIWIND_LAVA`, `AMIWIND_MODEL_HULL`, `AMIWIND_NPC_ANIM`,
`AMIWIND_NPC_HEAD_DETAIL`, `AMIWIND_NPC_HEAD_REDUCER`, `AMIWIND_NPC_ROOT_RULE`, `AMIWIND_STAIR_MITIGATION`,
`AMIWIND_STAIR_WALK` and `AMIWIND_WORLD_MAP`. For world-survey, the only difference was `AMIWIND_NPC_ROOT_RULE`
(the run recorded `legacy`, the plan left it unset). No bookkeeping variable (`AMIWIND_RUN_*`) was part of any key;
they are all in `IGNORED_ENV`.

The preflight inside a build was not affected. The developer-mode entry check, `--resource-plan` and the `--check`
preflight that the build service runs all come after both export blocks.

## Why it was not caught

The tests compare plans made with the same environment; no test runs the plan without the build's options against a
run that had them. When it was found on 10 October, the planned repair went no further than this page. Nothing
tracked the page while its status said "Open", and a workaround existed.

## Reproduction

Always: run `build.py --reuse-plan RUN` on a run built with options that set AMIWIND_* variables for its stages.

## Repair

Branch `v0.0.46-reuse-plan-env`, 20 October 2026:

- `tools/build.py` has two export functions, `export_option_environment(args)` and
  `export_converter_environment(args)`. They hold the two export blocks, and `main()` calls them where those blocks
  were. `plan_stage_environment(argv)` parses, resolves and exports with the same two functions.
- `build.py --reuse-plan OLD_RUN [-- BUILD OPTIONS]` sets that environment before planning and prints where the
  options came from (`Stage environment: ...`). It takes the options after `--` if given. Otherwise it takes the build
  command that the run recorded, and otherwise the build defaults. Options that the builder would refuse stop the
  plan. It does not guess.
- Every build now records its own options in `build-state.json` (`build_argv`). A later plan against that run then
  uses them.

## Verification

- `ReuseTests.test_the_standalone_reuse_plan_keys_stages_in_the_build_environment` (`tests/test_build_cache.py`):
  a stage that reads `AMIWIND_NPC_ROOT_RULE` is built with the default value, then planned from a clean environment
  through `build.main(['--reuse-plan', ...])`. Every stage must be reused. The test fails against the previous code
  (`beta` rebuilt for `environment`).
- `ReusePlanEnvironmentTests`: for eleven option sets, the environment the plan sets must equal the one
  `build.main()` has set when it reaches the prerequisites. The plan must also take the options after `--` first,
  then the recorded command, then the defaults.
- The plan of a6a9c6e9 plus this repair (04ed6047) against the same v0.0.45 release run gives 16 of 39 stages
  planned for reuse, 23 rebuilt (2 by policy), 0 UNEXPECTED. Every remaining rebuild is either a policy stage
  (engine, image) or names a source file that changed between the run's commit c9099fb8 and a6a9c6e9:
  `tools/mesh_geometry.py`, `tools/mesh_geometry_env.py`, `src/mwad/dialogue.py`, `tools/chim/collision.py`,
  `tools/gallery_cache.py`, the CHIM tools or the engine. Some of those reasons still list `environment`. That is
  the new variable `AMIWIND_COLLISION_HULL_POINTS`, read by the changed `tools/mesh_geometry_env.py`.

## Prevention

`ReusePlanEnvironmentTests` fails if `main()` exports a stage variable that the plan does not. A new export
therefore has to go into one of the two shared functions.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build reuse keys and output attribution (`build-cache-reuse`). A unit is rebuilt only when the content hash of all its inputs changes or its output is missing or damaged. Keys never under-declare (a missed input allows a wrong reuse) and should not over-declare (a file no output depends on forces rebuilds); outputs carry no wall-clock values; every changed file is credited to the stage that wrote it. See [families](README.md#families).

- [BUILD-ACTOR-LIBRARY-MWAD-PATH-47](BUILD-ACTOR-LIBRARY-MWAD-PATH-47.md): The actor-library stage stopped at once: run as a script, tools/mwad.py hid the src/mwad package
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
- [BUILD-REUSE-RECORD-RETIRED-36](BUILD-REUSE-RECORD-RETIRED-36.md): Early cutoff and the reuse audit lost their records when an older run was retired: stages with byte-identical outputs counted as changed
- [BUILD-REUSE-REDUCED-RECORD-36](BUILD-REUSE-REDUCED-RECORD-36.md): A stage reused from a run that had itself reused it came back without the files a later stage replaced there, so that later stage failed when it ran again
- [BUILD-REUSE-SCHEDULER-TOP-45](BUILD-REUSE-SCHEDULER-TOP-45.md): A scheduler-only edit rekeys every stage, NPC gallery face and stair walk that reaches tools/build_parallel.py
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-SCENE-DIAGNOSTIC-COPY-35](BUILD-SCENE-DIAGNOSTIC-COPY-35.md): Scene-chain stages were never reusable: copying the previous scene (logs included) counted as reading another stage's diagnostics
- [BUILD-SCHEDULER-TABLE-KEY-35](BUILD-SCHEDULER-TABLE-KEY-35.md): A new row in the build scheduler's stage table rebuilds stages that never read it: the table counted as import-time code of every stage
- [BUILD-SEYDA-BOUNDED-RUN-PATHS-36](BUILD-SEYDA-BOUNDED-RUN-PATHS-36.md): The actor-contact stage wrote its run folder path into 67 Seyda Neen region records, so its outputs differed in every run folder
- [BUILD-SPRITE-KEY-HASHLIB-47](BUILD-SPRITE-KEY-HASHLIB-47.md): The CHIM stage failed 45 minutes into a build: the sprite recipe key used hashlib without importing it
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

- [BUILD-ENV-FINGERPRINT-GLOBAL-33](BUILD-ENV-FINGERPRINT-GLOBAL-33.md): The stair rule setting invalidates the reuse cache of every build stage, including stages that never read it

<!-- END GENERATED CATEGORY -->
