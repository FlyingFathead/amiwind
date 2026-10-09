# BUILD-IMAGE-NOT-INCREMENTAL-33: The image step redoes every per-map pass and the whole pack on every build

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.32 |
| Where | tools/build_aga.py image step (finalize_image and the passes before it) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32 (last seen) |
| Severity | medium: No effect on the game; median 1,240 s per build (longest 2,652 s) even when few maps changed; about half is per-map passes on unchanged maps. |
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

Open; the per-map pass cache (optimizer, hidden-surface cull, stair-walk gate) is in source on the
v0.0.33 pass-cache branch, not shipped; the remaining passes and incremental packing are not done.
Present in the v0.0.32 builder.

## Symptom

The image step is the largest fixed cost of every build: median 1,240 s, longest 2,652 s over the
13 builds recorded in the private build ledger, even when only a few maps changed since the
previous build. Where the time goes (section timers in the build profile):

v0.0.32 from-scratch build, `--jobs 24` (1,211 s):

| Part | Wall | Cores |
| --- | ---: | ---: |
| Staging and installs before the repair | about 40 s | |
| Balmora layout repair | 93 s | 2.2 |
| Actor support fitting (`bake_ground`) | 70 s | 3.3 |
| `finalize_image`, of which: | 980 s | 10.5 |
| - BSP optimizer over every map (`optimize_maps`) | 546 s | 14.1 |
| - hidden-surface cull | 73 s | 18.4 |
| - exterior sky configuration | 19 s | 16.3 |
| - actor contact audit, entity tracker, heap audit | 50 s | 1.8-14.7 |
| - staging the runtime (`stage`) | 21 s | 1.0 |
| - world partition packing | 17 s | 2.0 |
| - boot volume writes (`xdftool`, 8 calls), `rdbtool` (2) | 68 s | 1.0 |
| - drive readback | 14 s | 8.2 |

v0.0.33 CHIM MiniWind build, `--jobs 6` (725 s): repair 89 s, `finalize_image` 550 s (optimizer
187 s, per-map checks 92 s, `xdftool` 44 s, readback 27 s).

About half of the step is per-map passes (optimizer, cull, sky configuration, checks) whose output
depends only on each map's input bytes and the pass's own code; the boot volume writes and
readback are about 80 s and serial by nature.

## Where

`tools/build_aga.py` image step (`finalize_image` and the passes before it).

## How it happened

Each pass was written to run over the whole staged map set; the image step is never reused
(BUILD_PROFILE.md: always assembled and verified from the stage outputs).

## Why it was not caught

Development builds were compared with each other by total time; the per-pass profile showed the
fixed share only once section timers covered the image step.

## Reproduction

`python tools/build.py profile report RUN/profile/sections/NN-image.jsonl` on any build.

## Repair

`tools/pass_cache.py`: content-addressed results of per-map passes for development (`-devN`)
builds. Key: SHA-256 of the pass name, its options, the SHA-256 of the pass's repository sources
(its module and every repository module and data file it reads, transitively,
`build_cache.SourceIndex`) and the input map's SHA-256; value: the receipt row (key order kept)
and the output bytes when they differ. Stored outputs are checked against their SHA-256 when
read (a damaged entry is ignored and the pass runs); writes are atomic. The builder points
`AMIWIND_PASS_CACHE` at `WORKSPACE/cache/image-passes` for `-devN` versions and sets it to `off`
for release candidates and finals, so those run every pass on every map. Used by:

- the BSP optimizer (`optimize_world_maps.prepare_candidate`);
- the hidden-surface cull (`hidden_surface_build`, the builder's own processor only; key includes
  whether the map is an exterior);
- the stair-walk gate (`stair_walk.check`; key includes the map's core, the stair rule and the
  model table), so its verdict is unchanged: hits return the rows the check produced.

Not done yet: the Balmora layout repair (its rebuilt cores read the whole Balmora cache), actor
support fitting (`bake_ground`, placements read several maps), the sky configuration, and
incremental drive packing.

## Verification

`tests/test_pass_cache.py`: optimizer maps and receipt bytes identical with the cache off, cold
and warm, a warm run never prepares a map again, a damaged entry is ignored; hidden-surface maps,
proofs and receipt identical off/cold/warm; stair-walk report bytes identical off/cold/warm and a
warm check never re-checks a map; source or option changes miss; release versions turn the cache
off. Real maps (the 109 parseable maps of the v0.0.33-dev1 MiniWind image, 65 exteriors; busy
host, 4 then 1 CPUs): cull 48.2 s off, 52.0 s cold, 6.6 s warm; optimizer 388.4 s off, 519 s cold
(1 CPU), 5.7 s warm; maps, receipts and proofs byte-identical in all three; cache 23.7 MB. A
whole-image comparison (drive image of a warm run against a cold run) is pending.

## Prevention

The tests above; full passes forced for release candidates and finals.

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
