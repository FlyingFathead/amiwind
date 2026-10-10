# BUILD-IMAGE-SERIAL-32: the image step runs on one core for about 23 minutes per pass

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | image step (tools/build.py, tools/build_aga.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | medium: Image step ran on one core for about 23 minutes per pass; slow but correct output. |
| Family | Build speed (`build-speed`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 8 October 2026](#status-8-october-2026)
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

## Status: 8 October 2026

Open: repair on the v0.0.32 development line, not shipped. Found during the v0.0.32-dev1
from-scratch build.

## Symptom

The image step takes about 23 minutes per pass on a 24-thread host while its container uses one
core (98.7 % CPU): sky cleanup, BSP optimizer verification, staging and hashing run map by map
over 2,741 maps. A private-test build with the actor waiver needs two passes (the waiver accepts
only the exact audit of the finished image, including every world map hash), so about 46 minutes;
every rebuild of the image costs the same again.

Wider than the image step (8 October 2026): worker counts are hard-coded in many places instead
of following `--jobs`: the map optimizer is fixed at 6 workers, the Balmora region repair at 4
threads, and several conversion, flora, scenery, area and census steps default to one worker or
pass `-threads 1` to the map tools without an outer parallel loop. The owner calls this a
regression: parallel builds existed; the job counts were not carried through as steps were added.

## Where

`tools/build.py` (the image and actor-contact stages got no `--jobs`), `tools/build_aga.py` image
step (per-map loops, a fixed optimizer pool of six), `tools/check_actor_ground.py` (the waiver's
full payload comparison).

## How it happened

Parallel builds exist since v0.0.23-dev1 (5163678): the scheduler gives every stage with `--jobs`
its share of the budget and every stage without it exactly one worker, with
`AMIWIND_BUILD_JOBS=1` inherited by everything it calls. The image stage never had `--jobs` (no
commit in the history of `tools/build.py` passed it), so it was scheduled as a one-worker stage.
Its passes were then added one by one, each serial or with a fixed count:

| Commit | Version | Image-step work | Workers |
| --- | --- | --- | --- |
| 4767ded | v0.0.24-rc2 | actor annotation, support fitting, actor audit | 1 |
| bdfc031 | v0.0.25-dev1 | world partition packing and readback | 1 |
| 8da8387 | v0.0.27 | BSP optimizer, world map heap estimate | optimizer fixed at 6 (`optimizer_jobs`, never exposed); heap 1 |
| 8da8387 | v0.0.27 | Seyda Neen region conversion | 66 regions one after another, ericw `-threads 8` |
| 752939b | v0.0.28 | exterior sky cleanup; hidden-surface cull | sky 1; cull fixed at 6 |
| eb08c92 | v0.0.29-dev4 | first-person hand metadata | 1 |
| da107ca, 1c08e51, 4a9dc8c | v0.0.31/32 | entity tracker, world progress, night lighting | 1 |
| bc089c2 | v0.0.32 | Balmora layout repair | ericw/model `threads=4` |

Nothing that once followed `--jobs` stopped following it: the regression audit of every
`tools/build.py` version (33 commits since v0.0.19) found no stage that lost `--jobs`. The two
pools of six were the only parallel work in the image step and never followed `--jobs`; the
stages `actor-contact` (Seyda conversion with a fixed eight threads) and `image` were the only
stages with pooled work and no `--jobs`. 511da01 moved the Seyda thread count into a constant
(`BUILDER_THREADS = 8`) without changing it.

Worker counts across the builder (audit of every call site, 8 October 2026):

| Location | Before | After | Why |
| --- | --- | --- | --- |
| `build.py` image, actor-contact stages | no `--jobs` (scheduled as 1) | `--jobs N` | pooled work inside |
| `build_aga.py` optimizer, hidden-surface cull | fixed 6 | N | per-map pools |
| `build_aga.py` sky, hands, actor passes, heap, staging, hashing, packing | 1 | N | per-map pools |
| `repair_balmora_maps` / `rebuild_balmora_region` | `threads=4` (light 4) | N for vis and models; light 1 | light output order follows threads |
| `prepare_seyda_regions` / `prepare_bounded_world` | regions serial, `-threads 8` | regions in the pool, vis `N // regions`, light 1 | same |
| `build_torchtest.py` vis/light `-threads 1` | 1 | unchanged | one six-brush room, under 0.2 s |
| `prepare_world_regions.py`, `import_town.py`, `prepare_area.py`, `world_estimate_sample.py` light `-threads 1` | 1 | unchanged | maps already run side by side in a pool of N; light reproducible |
| `prepare_area.py`, `prepare_world_flora.py`, `prepare_world_scenery.py` `append_meshes(jobs=1)` | 1 | unchanged | inside an outer pool of N (outer x inner = N) |
| `prepare_media_assets.py`, `prepare_music.py` ffmpeg `-threads 1` | 1 | unchanged | inside a pool of N |
| `asset_census`, `world_estimate_data` `scan_meshes(jobs=1)`, `generate_polygon_heatmap` `jobs=1` | library default | unchanged | every caller passes `--jobs` |
| `prepare_harvest_room.py`, `prepare_original_door_overlay.py` `jobs=1` | 1 | unchanged | stand-alone tools, not build stages |
| `build_gallery.py`, `prepare_census.py`, `prepare_interior.py`, `prepare_mesh_bsp.py` light `-threads N` | N | unchanged (reported) | follows `--jobs` but light output is not reproducible with more than one thread |

## Why it was not caught

Builds were not profiled per stage, and image steps were rarely rerun (images were patched).
No test checked that `--jobs` reaches a stage or a pool.

## Reproduction

Any full build: watch the image container's CPU use. Profile of one pass on the dev1 inputs
(2,741 maps, world flora, builder source of the dev1 build, 16-CPU container): see Verification.

## Repair

- `--jobs N` is exact: `tools/build.py` passes it to the image and actor-contact stages; the
  scheduler gives the image stage (it runs last) the whole budget. `tools/build_aga.py image`
  accepts `--jobs`, resolves it once (`image_jobs`) and hands it to every per-map pass; converters
  that use their default see it through `AMIWIND_BUILD_JOBS`. No pool is capped by the CPU count;
  one warning is printed (and recorded in `build-state.json` and the build summary) when N exceeds
  the usable CPU threads.
- Parallel passes, all through the shared pool (`build_parallel.process_pool`, spawn workers,
  results in serial order): Seyda regions (one region per worker, vis threads `N // regions`),
  Balmora repair (N threads), exterior sky, hidden-surface cull, hand metadata (plan and write),
  BSP optimizer and its hash checks, actor annotation, support fitting (grouped by owning map)
  and the actor audit (map reading, then contact measurement per owning map), entity tracker map
  reading, heap estimate (chunks of maps), world scenery and flora staging (hashing and copies),
  content fingerprint hashing, world partition packing and readback, boot file hashing.
- Serial on purpose: canonical-owner choice and receipt order in the actor audit, staging
  installs and rollbacks, the final fingerprint fold, the boot FFS volume (one file system),
  guard torch and shared sky conversion (one shared asset archive; not per map).
- ericw `light` stays single-threaded per map: light 0.18.1 writes faces and lightmaps in a
  thread-dependent order (measured: two runs with 2-8 threads differ in the faces and lighting
  lumps; one thread is reproducible; vis is identical for any thread count). The Balmora repair
  (4 threads) and Seyda regions (8 threads) therefore changed to one light thread per map.
- One-pass private-test waiver: the image step compares the approved actor findings (every row,
  error and count) instead of every payload hash, so the early actor-contact audit approves the
  image in the same pass. Any new, changed or missing finding refuses the waiver; the image is
  still named `-private-test`, `production_gate_passed` stays false and release candidates and
  final versions refuse the option.
- Per-stage CPU time and idle cores come from the build profiler ([BUILD_PROFILE.md](../BUILD_PROFILE.md)).

## Verification

Measured on a copy of the v0.0.32-dev1 inputs (2,741 maps with world flora, 16-CPU container, one
image pass, private-test waiver). Busy host: both runs shared the 24-thread machine with a dev1
image pass and the CHIM engine tests, so the times are relative, not quiet-host numbers:

| Pass | Before (6-worker pools) | After, `--jobs 16` |
| --- | --- | --- |
| Whole image step | 2,221 s, stopped at the boot partition (ARG_MAX), about 3.4 busy CPUs | 1,314 s complete with both drives read back, about 7 busy CPUs |
| Exterior sky cleanup | 286 s | 33 s |
| Hidden-surface cull | 253 s | 190 s |
| BSP optimizer | 898 s | 490 s (13 busy CPUs) |
| Support fitting | 249 s | 109 s |
| Heap estimate | 141 s | 14 s |
| World scenery and flora staging | 38 s | 32 s |
| Private test with known findings | two passes | one pass |

Outputs: 28,450 files and all 2,532 world maps byte-identical to the old serial code; the actor
audit has the same SHA-256. The rest differ only in paths, timestamps, worker counts, tool and
engine source hashes, file system image hashes and Balmora rebuild intermediates (final Balmora
maps identical). The early actor-contact audit approved the image audit in the same pass.

Tests: `tests/test_build_jobs_workers.py` (every pooled stage gets exactly `--jobs N` for N = 3, 16 and 100; every image pass hands N to the pool factory; serial and
parallel results byte-identical with real workers, including the old serial actor audit as a
reference; the warning once, only above the CPU count), one-pass waiver tests in
`tests/test_actor_ground.py`, the Seyda region pool test in `tests/test_seyda_bounded_pipeline.py`.

## Prevention

`tests/test_build_jobs_workers.py` fails when a stage or image pass stops receiving `--jobs`, when
a worker count is hard-coded, or when a map light compile becomes multi-threaded. Per-stage
timing and CPU use in the build summary; owner rule: parallelize as much as possible
([DEVELOPMENT.md](../DEVELOPMENT.md), [PARALLEL_BUILD.md](../PARALLEL_BUILD.md)).

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
- [BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md): Scene-chain stages leave most of the workers they hold idle
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
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

Related bugs in other categories:

- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread

<!-- END GENERATED CATEGORY -->
