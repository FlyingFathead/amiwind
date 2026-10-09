# BUILD-PROFILE-JOBS-START-ONLY-33: The build profile compares a stage's cores with the workers it started with, not the ones it held

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | tools/build_profile.py (stage rows, idle_periods, report and summary tables) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: No effect on the game; idle-core stages went unflagged, so the build stayed slower than it needed to be and speed work was aimed at the wrong stages. |
| Family | Build speed (`build-speed`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | found in source on the build progress branch; the commit was not recorded with the finding |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on the v0.0.33 build-progress branch, not shipped. Present in the v0.0.32 builder.

## Symptom

The build profile's idle-core warnings, its stage table and the suggestions compared each stage's
cores with `jobs`, the worker count the stage started with. The parallel scheduler rebalances that
count while stages run (`worker_changes` in `build-state.json`), often within a fraction of a second:
in the v0.0.32 from-scratch build (`--jobs 24`) these stages started with one worker and held twelve
from 0.1 to 0.2 seconds after they started, for their whole run:

| Stage | Wall | Cores used | Workers: start, then held |
| --- | ---: | ---: | --- |
| balmora | 510 s | 2.84 | 1, then 12 |
| balmora-interiors | 387 s | 9.40 | 1, then 12 |
| town-vivec_arena | 200 s | 2.38 | 1, then 12 |
| actor-contact | 256 s | 1.39 | 1, then 12 |
| interior | 119 s | 1.40 | 1, then 12 and 24 |
| bsp | 122 s | 0.98 | 1, then 8 and 12 |

Measured against one worker none of them looked idle; measured against twelve, balmora, the Vivec
Arena import, actor-contact, interior and bsp each used well under half of their workers for minutes. No
idle-core warning was raised for any of them, and the table showed `jobs 1` next to 9.4 cores.

## Where

`tools/build_profile.py`: the profile stage rows kept only the start value, and `idle_periods`,
`suggestions`, the report and summary tables used it. Records built from those rows inherited the
same single number.

## How it happened

The profiler was written while every stage kept its start allowance. The scheduler's rebalancing
(BUILD-SCHEDULER-JOBSHARE-32) came later and recorded its changes in `build-state.json` only; the
profile never read them.

## Why it was not caught

The profiler tests used stages whose allowance never changed. A stage with `jobs 1` and more than
one core in use was not treated as a contradiction anywhere.

## Reproduction

Any parallel build where a pooled stage starts while others still run: read its `worker_changes` in
`build-state.json` and its row in `build-profile.json` (v0.0.32 from-scratch build: balmora above).
Found while building the live progress file, which reads the current allowance.

## Repair

The profiler takes each stage's rebalances from the scheduler (shifted onto the profile clock) and
writes, per stage row, `worker_changes`, `jobs_min`, `jobs_max` and `jobs_mean` (time-weighted); `jobs`
stays the start value. Idle-core warnings compare each one-second sample with the workers held at
that moment (without a timeline: the average cores with the time-weighted mean), and report the
start value next to it. The stage tables show the range (`1-12`); `optimize` and the suggestions
use the workers held; live progress scales earlier runs by `jobs_max`.

## Verification

`tests/test_build_progress.py` `WorkerAllowanceTests`: the v0.0.32 numbers above (balmora, actor-contact,
dialogue-lookup) give warnings against 12 workers and none for a one-worker stage, the old rule
gives none; `report` shows `1-12` and "2.84 of 12 cores"; a real two-stage scheduler run records the
rebalance in the profile row and in `build-state.json`. Existing profiler tests unchanged.

## Prevention

The test above fails if the profile goes back to the start value. Earlier profiles stay readable:
rows without `worker_changes` are treated as before.

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
