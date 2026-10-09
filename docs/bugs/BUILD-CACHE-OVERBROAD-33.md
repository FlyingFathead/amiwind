# BUILD-CACHE-OVERBROAD-33: CHIM builds rerun the scene chain after merges that cannot change its outputs

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Stage fingerprints (tools/build_cache.py closures via tools/build_parallel.py; media stage) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Development builds rerun the whole scene chain (about 30-40 min) after edits such as a new console command or a MiniWind option. |
| Family | Build speed (`build-speed`) |

<!-- END GENERATED FACTS -->

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

Repair in v0.0.33 development (not shipped). CHIM build issue: found in the CHIM builder's development
builds; the repair is in the shared stage cache, so legacy builds get it too.

Provenance: owner report on the AmiWind "MiniWind" Playtester Build runs, version 0.0.33-dev1:
mw-033a (source v0.0.33-miniwind 08d0613) and mw-033c (source 76a324f), both built with
`--reuse-from` the full development run full-033a (source v0.0.33-dev1-build 7fa9b3a).

## Symptom

After merges, MiniWind and CHIM builds reran most of the stages before `chim` and `image` (scenery,
scene, bsp, npcs, hands, interior, intro, census, balmora, balmora-interiors, character, ...) although
the merged changes could not change those stages' outputs: engine fixes, CHIM builder changes, tracker
and documentation edits. mw-033c reused 3 of its 24 stages (setup, dialogue-lookup, terrain). Each
needless rerun costs minutes per stage (measured medians: balmora about 8 min, balmora-interiors 6,
actor contact 4, media 3.5, character 2), tens of minutes per build.

## Where

`tools/build_cache.py`, the stage fingerprints that decide reuse:

1. The development line the MiniWind builds came from still had the first fingerprint method
   (`amiwind-stage-cache-v1`, every import of every imported module, every file of a top folder the
   code names). The narrower method (BUILD-CACHE-CLOSURE-WIDE-33, `amiwind-stage-cache-v2`) was on
   another branch.
2. The narrower method still hashed every reached module as a whole file. `tools/build_parallel.py`,
   which every stage imports for its worker pool (`ordered_map`), also holds the builder's own build
   plan code (`stage_dependencies`); the MiniWind change to the build plan changed every stage's
   fingerprint.
3. A path built from a registry row, `ROOT / 'config' / row['config']` (the town code), named the whole
   `config/` folder: an edit to the release coverage table `config/release-features.json` changed the
   fingerprint of every town stage. A longer path such as `ROOT / 'config' / 'towns.json'` was also read
   as its inner part `ROOT / 'config'` (the whole folder).

## How it happened

Measured with the builder's own fingerprint code on the source trees of the runs (their recorded
`source_sha256` maps identify the commits: full-033a 7fa9b3a, mw-033c 76a324f), per stage and per
fingerprint part, for the first method (v1, used by the runs), the narrower one (v2, `symbols`) and
the repair (`units`). Only `sources` changed for the scene chain: no environment variable, command
line, tool or game input. Stages whose fingerprint part changed (of the 22 fingerprinted stages):

| Changed file | v1 | v2 | units | Kind |
| --- | --- | --- | --- | --- |
| full-033a to mw-033c: `tools/build_parallel.py` (MiniWind build plan, `stage_dependencies`) | 21 | 20 | 0 | over-broad: code no stage runs |
| `tools/miniwind.py` (imported inside `stage_dependencies`) | 21 | engine, image | engine, image | over-broad (v1) |
| `tools/collision_bsp.py` (`compile_standing` lattice parameter) | 15 | 9 | 9 | real: bsp, interior, census, balmora, balmora-interiors, opening-references, chim |
| 25 engine C files and `engine/aga/Makefile` | 9 | 3 | 3 | v1 over-broad; chim real (its heap gate compiles the engine structures) |
| `docs/bugs/bugs.json` (bug tracker) | 9 | 0 | 0 | over-broad (v1) |
| `tools/prepare_logo.py` (startup screen) | 9 | media, intro | media, intro | real |
| mw-033c to v0.0.33-miniwind-ext 1120d84: `config/release-features.json` | 22 | 8 | chim, engine, image | over-broad for the town stages (no town file) |
| `docs/bugs/bugs.json`, `tools/build_aga.py`, `tools/stair_walk.py`, `tools/recorded_stage.py`, `tools/engine_limits.py` | 21 each | engine, image, chim | engine, image, chim | v1 over-broad |

Stages reused, counting the dependency chain (a stage after a rebuilt one rebuilds): full-033a to
mw-033c 3 of 24 (v1), 3 (v2), 6 (units: the rest is the real collision converter, startup screen
and release file list changes and the stages after them); mw-033c to 1120d84 2 (v1), 3 (v2), 10
(units: scenery, scene, bsp, npcs, hands, interior, music, setup, terrain, dialogue-lookup; intro
changes for real and every stage after it in the chain reruns, BUILD-CACHE-NO-CUTOFF-33).

## Why it was not caught

The tests checked that edits to modules a stage cannot import keep its fingerprint, not edits to
functions it cannot reach inside a module it does import, and no test measured reuse across a real
merge on the MiniWind stage list.

## Reproduction

Fingerprint the MiniWind stage list (mw-033c) on the full-033a and mw-033c source trees with each
method (`tools/build_cache.py predict OLD_RUN` with the checkout of the new source).

## Repair

On the v0.0.33 development line (not shipped):

- The narrower method (`amiwind-stage-cache-v2`, BUILD-CACHE-CLOSURE-WIDE-33) is part of the line.
- New default fingerprint scope `units`: the same reach as `symbols`, but a reached module counts as its
  import-time code (everything outside its plain functions, function default values included) plus
  the source of each function the stage reaches. An edit to a function no stage reaches keeps every
  fingerprint. `symbols` (whole files) and `modules` stay selectable (`--fingerprint-scope`).
- A call trace checks it in every profiled build: the read-trace hook also lists the first run of
  each repository function (`sys.monitoring`, Python 3.12+, once per function); a function that ran
  but whose source the fingerprint left out marks the stage's outputs as not reusable, with a warning.
- Paths: a whole `ROOT / 'a' / 'b'` chain counts once (not also its inner `ROOT / 'a'`); a module
  string constant in a path counts as its value; `FOLDER / row['KEY']` counts the files that JSON
  registries in that folder, already named by the code, give under KEY (no registry or no such value:
  the whole folder, as before). Python reads outside the result are caught by the read trace.
- `explain`, `predict` and the build's reuse report name the files whose fingerprint part changed.

Version stamps: `VERSION` and `CHIM_VERSION` count only for stages whose code reads them (engine,
image, chim); they are real inputs there.

The stage cache schema stays `amiwind-stage-cache-v2`; a v1 run (such as mw-033c) is not a reuse
source, so the first build with this repair runs every stage once.

## Verification

`tests/test_build_cache.py`: functions a stage never reaches do not count and reached ones do
(fake repository); registry-named files; an unreached edit reuses every stage and the reused outputs
equal a fresh build byte for byte; the call trace catches a function no static scan reached; on a copy
of this repository with the MiniWind stage list: a docs and tracker edit keeps all 22 stage
fingerprints, three engine C edits change only engine and chim, the build plan edit of
`build_parallel.py` keeps all, an edit to the worker pool every stage runs and an edit to the
collision converter still change their stages, and `config/release-features.json` keeps the scene
chain while `config/balmora.json` changes Balmora.

## Prevention

The repository reuse tests run in every gate; the read and call traces run in every profiled build;
the from-scratch build compared file by file with a reuse build stays the check before every release.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build speed (`build-speed`). Every stage on the shared worker pool; per-stage time and CPU in the build profile. See [families](README.md#families).

- [BUILD-CACHE-ABSOLUTE-PATHS-33](BUILD-CACHE-ABSOLUTE-PATHS-33.md): Stage fingerprints contain absolute paths, so a moved workspace or checkout reuses nothing
- [BUILD-CACHE-CHIM-UNITS-33](BUILD-CACHE-CHIM-UNITS-33.md): The chim stage's fingerprint changes whenever the CHIM unit cache gains units, so the stage is never reused
- [BUILD-CACHE-CLOSURE-WIDE-33](BUILD-CACHE-CLOSURE-WIDE-33.md): Stage fingerprints count every module any imported module could import, so unrelated edits rebuild most stages
- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it
- [BUILD-CACHE-TRACE-PYTHONPATH-33](BUILD-CACHE-TRACE-PYTHONPATH-33.md): The stage read trace refused reuse of a reused run when another checkout was on PYTHONPATH
- [BUILD-CHIM-UNIT-HULL-KEY-33](BUILD-CHIM-UNIT-HULL-KEY-33.md): CHIM unit cache ignores the standing-hull form: a --model-hull chain build reused routed-hull model units
- [BUILD-DOOR-REFERENCE-SERIAL-33](BUILD-DOOR-REFERENCE-SERIAL-33.md): The door step reads the whole master once per destination cell
- [BUILD-ENV-FINGERPRINT-GLOBAL-33](BUILD-ENV-FINGERPRINT-GLOBAL-33.md): The stair rule setting invalidates the reuse cache of every build stage, including stages that never read it
- [BUILD-EXCLUDE-STAGE-CLOSURE-33](BUILD-EXCLUDE-STAGE-CLOSURE-33.md): The quick test build table entered every conversion stage's fingerprint through the stage scheduler
- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md): Scene-chain stages leave most of the workers they hold idle
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-INPUTCHECK-SLOW-32](BUILD-INPUTCHECK-SLOW-32.md): The game data reference check takes over 12 minutes through Docker
- [BUILD-JOBS-RESOLVE-PER-STAGE-32](BUILD-JOBS-RESOLVE-PER-STAGE-32.md): With automatic jobs, stages of one build plan can get different worker counts
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33](BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): Every build stage's source fingerprint took in the engine sources through the MiniWind module
- [BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md): Pool workers open their own pools sized to the whole stage's allowance
- [BUILD-ORDERED-WINDOW-33](BUILD-ORDERED-WINDOW-33.md): The ordered worker pool idles behind one slow item, and hands long items out last
- [BUILD-PRERENDERED-PRUNE-ORDER-33](BUILD-PRERENDERED-PRUNE-ORDER-33.md): Prerendered store prune picks the superseded entry by folder name when two entries share a timestamp
- [BUILD-PROFILE-JOBS-START-ONLY-33](BUILD-PROFILE-JOBS-START-ONLY-33.md): The build profile compares a stage's cores with the workers it started with, not the ones it held
- [BUILD-REUSE-SCRATCH-UNDECLARED-33](BUILD-REUSE-SCRATCH-UNDECLARED-33.md): A rerun with --reuse-from reused 1 of 33 stages: the builder's scratch folder made the first stages non-reusable
- [BUILD-REUSE-TMP-UNDECLARED-33](BUILD-REUSE-TMP-UNDECLARED-33.md): A stage that runs while a reused stage is copied becomes non-reusable
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts
- [BUILD-SCHEDULER-LOWBUDGET-33](BUILD-SCHEDULER-LOWBUDGET-33.md): With a small --jobs budget the stage scheduler starts nothing when more branches are ready than the budget (busy loop)
- [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md): A pooled stage that starts while others run gets one worker as its start value
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md): Docker builds and disk-image steps on Windows folders are slow
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

<!-- END GENERATED CATEGORY -->
