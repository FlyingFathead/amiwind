# BUILD-IDLE-STAGES-33: Scene-chain stages leave most of the workers they hold idle

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | scene-chain stage scripts (import_town, prepare_doors, check_scene_actors, media, bsp, area) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: No effect on the game; eight scene-chain stages ran far below the workers they held beside the NPC gallery (critical path), so builds took longer. |
| Family | Build speed (`build-speed`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 735fa0e |
| CHIM engine version | none: legacy engine |

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

Repaired in source on the v0.0.33 stage-parallel branch, not shipped; open until a profiled
from-scratch build confirms it. Present in the v0.0.32 builder.

## Symptom

Measured against the workers each stage held (allowance-aware profile,
[BUILD-PROFILE-JOBS-START-ONLY-33](BUILD-PROFILE-JOBS-START-ONLY-33.md)), v0.0.32 from-scratch build
with `--jobs 24` on a 24-thread host:

| Stage | Wall | Cores used | Workers held |
| --- | ---: | ---: | ---: |
| balmora | 510 s | 2.84 | 12 |
| balmora-interiors | 387 s | 9.40 | 12 (about 16 used for 2 min, then 1 for 80 s) |
| actor-contact | 256 s | 1.39 | 12 |
| town-vivec_arena | 200 s | 2.38 | 12 |
| bsp | 122 s | 0.98 | 8-12 |
| interior | 119 s | 1.40 | 12-24 |
| media | 260 s | 2.62 | about 12 |
| area | 161 s | 3.36 | about 10 |

The NPC gallery (34 min, the critical path to the world terrain) ran beside these stages and could
only take the workers they held, so their idle time lengthened the whole build.

## Where

The stage scripts: `tools/import_town.py` (balmora and every town: regions compiled one at a time),
`tools/prepare_doors.py` (door reference reads the master once per destination cell, in interior,
area, balmora-interiors and census), `tools/check_scene_actors.py`, `tools/prepare_media_assets.py`,
`tools/prepare_mesh_bsp.py`, `tools/prepare_interior.py`, `tools/prepare_area.py`, and the
scheduler causes [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md) and
[BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md).

## How it happened

Each stage was parallelized where it was first measured slow; the serial parts left inside
(per-region loops, one external tool after another, a master read per cell) were hidden because
the profile compared cores with the start value of one worker.

## Why it was not caught

See BUILD-PROFILE-JOBS-START-ONLY-33: the profile showed these stages at or above their jobs.

## Reproduction

`python tools/build.py profile report RUN` on a parallel from-scratch build (the profile now
compares with the workers held), or a stage-only run with the private stage bench.

## Repair

- Scheduler: a pooled stage starts with its even share
  ([BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md)); pool workers do not follow the
  stage allowance ([BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md)); ordered
  pools hold four results per worker and hand work out longest first from item history
  ([BUILD-ORDERED-WINDOW-33](BUILD-ORDERED-WINDOW-33.md)); `build_parallel.live_jobs` gives a pass
  the stage's current share instead of its start value (actor support fitting, bsp vis threads).
- balmora and town imports (`import_town.compile_regions`): regions compile side by side on the
  shared pool, each region's log output printed in region order; the collision cache writes are
  atomic.
- Door reference: one pass over the master
  ([BUILD-DOOR-REFERENCE-SERIAL-33](BUILD-DOOR-REFERENCE-SERIAL-33.md)); this was the one-core tail
  of interior, area and balmora-interiors.
- media: sounds and videos in one process pool that follows the stage share (the thread pool was
  fixed at the start value of one), videos first, rows in serial order.
- npc-gallery: the source meshes are parsed and hashed on the pool before the identities (the
  serial pass: 103 s on four CPUs, about 125 s on a busier host, at the start of the critical path).

## Verification

Stage-only runs from the v0.0.32 release run's inputs (private stage bench: the stage command
from `build.py`, profiled like a build), 4 CPUs, `--jobs 4`, on a host 75-98 % busy with other
work (timings comparable only roughly). Before: the v0.0.33-dev code started with `--jobs 1` and
held 4 (as the v0.0.32 build started these stages with 1 and gave them 12). After: started with 4.
Every pair byte-identical over all output files (stage tool logs excepted).

| Stage | Before | Cores | After | Cores | Files identical |
| --- | ---: | ---: | ---: | ---: | ---: |
| balmora | 716 s | 1.50 | 268 s | 2.79 | 4,620 |
| media | 753 s | 0.88 | 258 s | 2.85 | 7,185 |
| balmora-interiors | 904 s | 3.00 | 614 s | 3.36 | 4,241 |
| actor-contact | 346 s | 1.09 | 194 s | 2.32 | 396 |
| area | 308 s | 2.55 | 172 s | 2.90 | 3,731 |
| town-vivec_arena | 291 s | 1.40 | 157 s | 2.14 | 3,796 |
| interior | 130 s | 1.17 | 59 s | 1.38 | 95 |
| bsp | 125 s | 1.04 | 53 s | 1.93 | 67 |

World terrain on 48 regions: every `scene.bsp` identical with the old code, the new code without
history and the new code with history. The NPC gallery's identities are identical with and without
the pool. Regression tests: `tests/test_build_jobs_workers.py` `StageParallelTests` (town regions,
their limit order, media and the gallery prefetch against the serial path; support fitting with
the stage share), `tests/test_build_parallel.py` (scheduler start share, nested pools, captured
output order, window, cost order, cost history), `tests/test_harvest_room.py` (one-pass interior
reader).

## Prevention

The profile's idle-core warnings now use the workers held; the optimizer lists idle stages.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build speed (`build-speed`). Every stage on the shared worker pool; per-stage time and CPU in the build profile. See [families](README.md#families).

- [BUILD-CACHE-ABSOLUTE-PATHS-33](BUILD-CACHE-ABSOLUTE-PATHS-33.md): Stage fingerprints contain absolute paths, so a moved workspace or checkout reuses nothing
- [BUILD-CACHE-CHIM-UNITS-33](BUILD-CACHE-CHIM-UNITS-33.md): The chim stage's fingerprint changes whenever the CHIM unit cache gains units, so the stage is never reused
- [BUILD-CACHE-CLOSURE-WIDE-33](BUILD-CACHE-CLOSURE-WIDE-33.md): Stage fingerprints count every module any imported module could import, so unrelated edits rebuild most stages
- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it
- [BUILD-CACHE-OVERBROAD-33](BUILD-CACHE-OVERBROAD-33.md): CHIM builds rerun the scene chain after merges that cannot change its outputs
- [BUILD-CACHE-PER-WORKSPACE-33](BUILD-CACHE-PER-WORKSPACE-33.md): Per-file caches live in each build workspace, so a build on a new volume with --reuse-from converts everything again (MiniWind media 1,195 s instead of seconds)
- [BUILD-CACHE-TRACE-PYTHONPATH-33](BUILD-CACHE-TRACE-PYTHONPATH-33.md): The stage read trace refused reuse of a reused run when another checkout was on PYTHONPATH
- [BUILD-CHIM-UNIT-HULL-KEY-33](BUILD-CHIM-UNIT-HULL-KEY-33.md): CHIM unit cache ignores the standing-hull form: a --model-hull chain build reused routed-hull model units
- [BUILD-DOOR-REFERENCE-SERIAL-33](BUILD-DOOR-REFERENCE-SERIAL-33.md): The door step reads the whole master once per destination cell
- [BUILD-ENV-FINGERPRINT-GLOBAL-33](BUILD-ENV-FINGERPRINT-GLOBAL-33.md): The stair rule setting invalidates the reuse cache of every build stage, including stages that never read it
- [BUILD-EXCLUDE-STAGE-CLOSURE-33](BUILD-EXCLUDE-STAGE-CLOSURE-33.md): The quick test build table entered every conversion stage's fingerprint through the stage scheduler
- [BUILD-FLORA-FALLBACK-RETRY-35](BUILD-FLORA-FALLBACK-RETRY-35.md): The routed-hull fallback of a flora overlay could not retry: the failed try's candidate folder was looked up from the wrong place
- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-INPUTCHECK-SLOW-32](BUILD-INPUTCHECK-SLOW-32.md): The game data reference check takes over 12 minutes through Docker
- [BUILD-JOBS-RESOLVE-PER-STAGE-32](BUILD-JOBS-RESOLVE-PER-STAGE-32.md): With automatic jobs, stages of one build plan can get different worker counts
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33](BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): Every build stage's source fingerprint took in the engine sources through the MiniWind module
- [BUILD-MINIWIND-STAGE-CLOSURE-33](BUILD-MINIWIND-STAGE-CLOSURE-33.md): The MiniWind plan puts the CHIM builder modules into every conversion stage's fingerprint
- [BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md): Pool workers open their own pools sized to the whole stage's allowance
- [BUILD-NPCLOD-PATH-ARG-34](BUILD-NPCLOD-PATH-ARG-34.md): The first --npc-lod on build stopped at its area stage: a Path in the command broke build-state.json
- [BUILD-ORDERED-WINDOW-33](BUILD-ORDERED-WINDOW-33.md): The ordered worker pool idles behind one slow item, and hands long items out last
- [BUILD-PRERENDERED-PRUNE-ORDER-33](BUILD-PRERENDERED-PRUNE-ORDER-33.md): Prerendered store prune picks the superseded entry by folder name when two entries share a timestamp
- [BUILD-PROFILE-JOBS-START-ONLY-33](BUILD-PROFILE-JOBS-START-ONLY-33.md): The build profile compares a stage's cores with the workers it started with, not the ones it held
- [BUILD-REUSE-KEYS-TOO-BROAD-35](BUILD-REUSE-KEYS-TOO-BROAD-35.md): A whole build reused no stage, and the cost was not visible before the build started
- [BUILD-REUSE-TMP-UNDECLARED-33](BUILD-REUSE-TMP-UNDECLARED-33.md): A stage that runs while a reused stage is copied becomes non-reusable
- [BUILD-SCHEDULER-EVEN-SHARE-33](BUILD-SCHEDULER-EVEN-SHARE-33.md): The stage scheduler splits the workers evenly between running stages, so the longest stage gets no more than the shortest (MiniWind media on 1 of 4 workers for 1,195 s)
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts
- [BUILD-SCHEDULER-LOWBUDGET-33](BUILD-SCHEDULER-LOWBUDGET-33.md): With a small --jobs budget the stage scheduler starts nothing when more branches are ready than the budget (busy loop)
- [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md): A pooled stage that starts while others run gets one worker as its start value
- [BUILD-STAIR-WALK-SLOW-33](BUILD-STAIR-WALK-SLOW-33.md): The image step's stair walk spent most of its time in interpreted collision traces and brute-force headroom tests (1,751 s of the rc1c image step)
- [BUILD-STORAGE-DUPLICATES-33](BUILD-STORAGE-DUPLICATES-33.md): Build storage keeps full duplicate copies of images, stage outputs and packages, and nothing removes them
- [BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md): Docker builds and disk-image steps on Windows folders are slow
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- [MINIWIND-NOT-MINUTES-33](MINIWIND-NOT-MINUTES-33.md): A reused MiniWind build took about two hours instead of minutes
- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

<!-- END GENERATED CATEGORY -->
