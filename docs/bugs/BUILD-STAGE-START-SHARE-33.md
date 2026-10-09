# BUILD-STAGE-START-SHARE-33: A pooled stage that starts while others run gets one worker as its start value

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | tools/build_parallel.py (execute_parallel start share) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: No effect on the game; vis threads and worker choices stayed at one for whole stages (bsp: vis 87.9 s on one thread while holding 8-12 workers). |
| Family | Build speed (`build-speed`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 735fa0e |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on the v0.0.33 stage-parallel branch, not shipped. Present in the v0.0.32 builder.

## Symptom

In a parallel build a pooled stage (one with `--jobs`) that became ready while other pooled stages
were running started with `--jobs 1`: the running stages held the whole budget and the scheduler
left one worker free for each waiting stage. A tenth of a second later the scheduler rebalanced
and the stage held its fair share, but everything the stage decides from its `--jobs` value at the
start stayed at one: vis `-threads`, the split of tool threads between maps compiled side by side,
and every "workers" choice made before the first pool. v0.0.32 from-scratch build (`--jobs 24`):

| Stage | Started with | Held | What stayed at one |
| --- | ---: | ---: | --- |
| bsp | 1 | 8-12 | vis of the Seyda Neen map: 87.9 s on one thread (`running with 1 threads`) |
| interior | 1 | 12-24 | vis of the prison ship (small) |
| balmora, town-vivec_arena | 1 | 12 | vis of every region, "Scenery geometry workers: 1" |
| balmora-interiors, actor-contact, character | 1 | 12 | tool threads of every map |

## Where

`tools/build_parallel.py` `execute_parallel`: the start value was the free remainder
`(free - serial) // (parallel + 1)`, and `free` was nearly zero whenever pooled stages ran.

## How it happened

BUILD-SCHEDULER-JOBSHARE-32 made running stages share the budget evenly and follow an allowance
file, so pools inside a stage grow and shrink. The start value kept the older rule, which assumed
free workers exist when a stage starts. Tool threads (vis) and decisions taken before the first
pool cannot follow the allowance file.

## Why it was not caught

The profile compared cores with the start value (BUILD-PROFILE-JOBS-START-ONLY-33), so these
stages looked busy; the scheduler test only required the late stage to grow eventually.

## Reproduction

Any parallel build: `jobs` and `worker_changes` of bsp or balmora in `build-state.json`, and
`running with 1 threads` in their logs.

## Repair

A pooled stage now takes its even share when it starts: the running pooled stages are rebalanced
first, counting the incoming stage(s), so their allowance shrinks before the new stage starts with
the same share the next rebalance would give it. Serial stages still start only when a worker is
free. The budget is never exceeded in the accounting (shrink first, then start).

## Verification

`tests/test_build_parallel.py` `test_late_stage_gets_a_fair_share_and_shares_follow_the_budget`:
the late stage starts with 4 of 8 (was 1), the running stage's shrink to 4 is recorded no later
than the late stage's start, and the held workers never exceed the budget. Stage-only runs of bsp
started with the held share: see the stage-parallel measurements in
[BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md).

## Prevention

The test above fails if a late pooled stage starts with the free remainder again. Outputs do not
depend on vis thread counts (ericw vis is identical for any thread count; light keeps one thread).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build speed (`build-speed`). Every stage on the shared worker pool; per-stage time and CPU in the build profile. See [families](README.md#families).

- [BUILD-CACHE-ABSOLUTE-PATHS-33](BUILD-CACHE-ABSOLUTE-PATHS-33.md): Stage fingerprints contain absolute paths, so a moved workspace or checkout reuses nothing
- [BUILD-CACHE-CHIM-UNITS-33](BUILD-CACHE-CHIM-UNITS-33.md): The chim stage's fingerprint changes whenever the CHIM unit cache gains units, so the stage is never reused
- [BUILD-CACHE-CLOSURE-WIDE-33](BUILD-CACHE-CLOSURE-WIDE-33.md): Stage fingerprints count every module any imported module could import, so unrelated edits rebuild most stages
- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it
- [BUILD-CACHE-OVERBROAD-33](BUILD-CACHE-OVERBROAD-33.md): CHIM builds rerun the scene chain after merges that cannot change its outputs
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
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md): Docker builds and disk-image steps on Windows folders are slow
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

<!-- END GENERATED CATEGORY -->
