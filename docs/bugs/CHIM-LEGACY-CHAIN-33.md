# CHIM-LEGACY-CHAIN-33: CHIM builds still run the legacy exterior chain

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | tools/build.py CHIM plan, tools/chim/frame_map.py, tools/build_aga.py image step |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | medium: Nothing wrong ships, but a CHIM build pays for the open world and the Arena (20 min of stage medians, 18 on the critical path) and Balmora's region maps. |
| Family | Build speed (`build-speed`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 3ec2fdc, engine 3ec2fdc, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 3ec2fdc, world format 0.5 |
| Unknown because | found in source on the CHIM branch; no CHIM world build |

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

Open: measured and recorded. Every CHIM build records which legacy exterior stages it still runs
and which later step reads each one (`build-state.json` `chim_plan`, `tools/chim/plan.py`), and the
image step fails the build if a legacy exterior map of a CHIM area is packed
(`chim.frame_map.require_no_legacy_areas`). The stages themselves still run.

## Symptom

Owner decision: a CHIM build drops the old map method. A build with `--builder chim --chim-area
balmora --chim-area seyda` still runs every legacy exterior stage of the legacy plan: the Balmora
region maps (`balmora`), the Vivec Arena (`town-vivec_arena`) and the open world (`world-terrain`,
`world-scenery-assets`, `world-scenery`, `world-flora`). Nothing wrong ships: the image step removes
the CHIM towns' legacy maps. The time is lost. Perf ledger stage medians (3 to 4 builds each, host
load mixed, relative): `world-terrain` 779 s, `world-scenery-assets` 18 s, `world-scenery` 105 s,
`world-flora` 177 s, `town-vivec_arena` 146 s: 1,224 s (about 20 minutes) for the open world and the
Arena, of which `world-terrain`, `world-scenery` and `world-flora` (1,060 s, about 18 minutes) run in
series before the image. `balmora` (501 s) would shrink to its entities and residents.

## Where

`tools/build.py` (the CHIM plan is the legacy plan plus the `chim` stage),
`tools/chim/frame_map.py` (`build`, `build_docks`), `tools/build_aga.py` (image step).

## How it happened

The CHIM frame maps (`maps/<town>-chim.bsp`) were built as a strict derivative of the town's final
legacy region maps: they copy the actors, player starts and point entities from them and check
every static both ways. So the legacy region maps of a CHIM town have to exist in the image step
before they are removed. Three more readers tie the plan to the legacy chain:

- town flora: the image step installs the Seyda Neen and Balmora town flora from the `world-flora`
  stage, which needs the open-world terrain; the CHIM world adds the same flora as meshes, and the
  frame-map check needs both sides;
- the image step requires the complete open-world overlay (`--world-scenery`), and the entity
  tracker compares every placement with the release baseline;
- the Vivec Arena: `import_town` runs in the scene chain (later stages copy its tree). Owner decision
  (9 October 2026): a CHIM build leaves the Arena out of the image whole (exterior maps, region and
  door tables, harvest catalogues; `remove_towns_not_on_chim`, reason "not on CHIM yet"); its
  destination is not found in the engine until the CHIM Arena (M3). The Pit interior is not
  converted yet. The legacy open world ships as "not yet CHIM".

## Why it was not caught

The CHIM stage was added beside the legacy chain (DON'T DELETE ANY METHOD) and the first CHIM builds
compared the frame maps with the legacy maps on purpose. No record named the legacy stages a CHIM
plan still runs.

## Reproduction

`python3 tools/build.py --plan --builder chim --chim-area balmora --chim-area seyda ...`: the stage
list is the legacy list plus `chim`.

## Repair

Done (this change): the split is recorded per build (`chim_plan`), the image step fails on any legacy
exterior map of a CHIM area in the final payload (`chim_world.legacy_check` in `build.json`), and a
CHIM build with Seyda Neen takes the recorded v0.0.31 Seyda maps as an input directory
(`--seyda-recorded DIR`) instead of a rebuilt chain.

To do, in this order:

1. Frame maps from the converter's entity list (the `.map` entities the region conversion writes)
   instead of the compiled region maps; then `balmora` stops at its entities and residents.
2. Town flora for CHIM towns from `world-flora-assets` alone (no open-world terrain).
3. The image step without the open-world overlay when no open-world area is built (the MiniWind
   build type has the first version of this), the entity tracker scoped to the areas built; then
   `world-terrain`, `world-scenery-assets`, `world-scenery` and `world-flora` leave the CHIM plan.
4. The `town-<id>` stages of extra towns not on CHIM out of the CHIM plan (their output is left out
   of the image already); `import_town` interiors without the exterior (the Arena Pit for fight
   testing).

## Verification

`tests/test_chim_no_legacy.py`: the legacy plan is pinned (stages, tools, image options); the CHIM
plan's legacy stages are pinned with their readers; a legacy map of a CHIM area in the image fails
the check, also when a later pass puts one back; a CHIM build with Seyda Neen stops before setup
without `--seyda-recorded`.

## Prevention

The pinned `chim_plan` record: a reader that moves off the legacy chain must update it, and the
stage then leaves the CHIM plan. The image safety net stays.

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
- [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md): A pooled stage that starts while others run gets one worker as its start value
- [BUILD-SURVEY-NOT-REPRODUCIBLE-33](BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): The world-survey stage writes its wall time into its outputs, so a rerun never has the same outputs
- [BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md): Docker builds and disk-image steps on Windows folders are slow
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

Related bugs in other categories:

- [BUILD-SEYDA-REGEN-30](BUILD-SEYDA-REGEN-30.md): Public build cannot regenerate the Seyda Neen sub-cells
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [CHIM-PAYLOAD-PARITY-33](CHIM-PAYLOAD-PARITY-33.md): The CHIM world misses the image step's edits to Balmora (harvest mushrooms, town flora)

<!-- END GENERATED CATEGORY -->
