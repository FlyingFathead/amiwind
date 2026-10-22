# BUILD-CHIM-SERIAL-SECTIONS-44: the CHIM stage runs several sections on one core while units wait

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 4 times; something has to be done

- Reported with v0.0.44 at 2026-10-19 17:00 +0300: v0.0.44 release build (before this fix merged): CHIM validation 131 s on 2.8 of 23 cores, stair gate 1,066 s on 4.9 of 23; perf guard FIX-NOW
- Reported with v0.0.46-dev1 at 2026-10-20 14:48 +0300: dev1 try 2: CHIM queues stalled with 1351 or 978 units queued, 0 running, 1.1-1.7 cores for 90-376 s; source and receipt 35 s at 2.3 cores; pack 3m51s on 1 core (serial)
- Reported with v0.0.47-dev1 at 2026-10-21 14:44 +0300: dev1 try 2: 6 underused:chim windows (longest 3m21s); pack 1m28s on 1 core, source and receipt 40 s at 2.05, stats 41 s at 1.34; first window 6.6 cores, 1,270 queued
- Reported with v0.0.47-dev2 at 2026-10-21 17:30 +0300: same pattern in the image step world read (23 units running on 2 cores); see BUILD-IMAGE-WORLD-READ-FRAMES-47

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 19 October 2026, in v0.0.44-dev1 |
| Where | CHIM stage of 2026_10_19_v0.0.44-dev1_full-batch5_27aff0d1 (fail_watch UNDERUSED) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.44-dev1 (last seen) |
| Severity | high: about 7 minutes of a 24-core stage on one core per build; perf-guard class |
| Family | Build speed (`build-speed`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_19_v0.0.44-dev1_full-batch5_27aff0d1 |
| From commit | source 27aff0d, engine 27aff0d, CHIM world 27aff0d |
| CHIM engine version | CHIM 0.2.1, engine 27aff0d, world format 0.7 |
| Platform or emulator | build (fail_watch UNDERUSED) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.47-dev2 (21 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 4 times; something has to be done](#persisting-reported-4-times-something-has-to-be-done)
- [Status: 19 October 2026](#status-19-october-2026)
- [Symptom](#symptom)
- [v0.0.47-dev1 (21 October 2026): what is still under half the cores](#v0047-dev1-21-october-2026-what-is-still-under-half-the-cores)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 19 October 2026

Open: causes measured, repair on branch v0.0.44-serial with the outputs byte-identical (SHA-256), waiting for a full
build to verify.

## Symptom

The CHIM stage of the v0.0.44-dev1 full build (1,351 frames, 24 cores) spent minutes on one or a few cores while it
held 24 workers. The stage's own phase lines:

- between `areas side by side: done` (+30m03s) and `visibility rows: started` (+31m13s): 70 s on one core;
- `visibility rows`: 3 min 7 s at 4.9 cores; the supervisor saw 523 frames queued and none running for 170 s;
- `pack`: 41 s on one core;
- after the pack until `CHIM world conversion: done`: 54 s on one core;
- the validation: about 1.5 minutes on one core before its pool fanned out, and a minute at 3.1 cores at its end;
  the next try of the same build (all validation units stored) took 4 min 59 s at 2.0 cores with 23-24 units
  "running" and 1-2 cores busy;
- the stair gate: 2.3 to 4 of 24 cores with 803 units queued and 3 running (`4 workers by memory ... about
  2855 MiB each`);
- the statistics: 8 min 14 s at 0.8 cores (36 s at 1.0 cores in the next try).

## v0.0.47-dev1 (21 October 2026): what is still under half the cores

The CHIM stage of the v0.0.47-dev1 build (try 2, 23 min 57 s at 13.4 of 24 cores, 1,351 frames) lists `underused:chim`
six times (longest window 3 min 21 s). By section (build profile, run `2026_10_21_v0.0.47-dev1_dev1-try2_4a2d42b9`):

| Section | Time | Cores | Why |
| --- | --- | --- | --- |
| areas side by side, first minutes | window of 61 s | 6.6 of 24, 1,270 units queued, 23 "running" | not determined: a `vivec_city` unit ran 192 s beside the region frames; the workers counted as running did not use their cores |
| pack | 1 m 28 s | 1.00 | inherently serial as written: model, texture and terrain ids are handed out in the order the walk first meets them; the walk also encodes every record (see the plan) |
| source and receipt | 39.7 s | 2.05 | `chim-source.json` (694 MB) and the receipt are encoded on the pool and written by the parent; not profiled |
| validation start | window of 65 s | 4.0, 423 queued | the parent loads the world before the pool fans out (known, above) |
| stats | 40.6 s | 1.34 | `chim.stats.chim_stats` over the validated world; not profiled |

Plan, not done (each needs a measured design, nothing is half-done in code): (1) the pack: split the walk into the
cheap serial part that hands out the ids and a parallel part that encodes each sector's records on the pool, byte
identical by the SHA-256 of every file; measure the share of the 88 s that is id handing and the share that is
`write_record`/`sector_file` first; (2) source and receipt: time `bind_index`, `write_json` of the source and of the
receipt separately, then send workers the sections instead of the encoded text; (3) stats: profile one run of
`chim_stats` on a stored world, then split by frame; (4) the first window: log what each of the 23 "running" workers
waits for (the parent feeding tasks, memory guard, disk) when a window starts; the supervisor already knows the units
queued and running but not what a running unit is doing.

## Where

`tools/chim/world.py` (`build_frames`, `frame_visibility`, `frame_order`), `tools/chim/ownership.py`
(`source_failures`, `original`), `tools/chim/far.py` (`write_layers`), `tools/chim/build.py` (the receipt and the
source manifest), `tools/chim/validate.py` (`load_world`, the cached frame and model checks), `tools/chim/collision.py`
and `tools/chim/stair_pool.py` (the stair gate's workers), `tools/chim/stats.py`, `tools/build_parallel.py`
(`governed_map`, `completed_map`).

## How it happened

Measured on 156 region frames around Balmora plus Balmora (the inputs of that build, 16 CPUs) with the parent
process under the profiler:

- Gap before the visibility rows: `ownership.source_failures` tested every reference against every frame's core
  (about 469,000 references x 1,351 cores at full size) and `world.frame_order` compared every pair of frames;
  both quadratic. `ownership.original` deep-copied a value it had just built from new lists, in every one of the
  three ownership checks of a build.
- Visibility rows: since BUILD-CHIM-REGION-FRAMES-TAIL-43 the frames' placement layouts were made in the parent by
  the generator that fed the pool, about 100 ms a frame (placing the referenced terrain and counting each
  placement's leaves); the workers finished their frames faster than the parent made them.
- Pack: one walk over the frames in pack order, as it must be (model, texture and terrain ids are handed out in the
  order the walk first meets them), but it also packed every chunk's visibility rows and checked every terrain
  shift, work that does not depend on those ids.
- End of the conversion: the far terrain layers one frame after another; `chim-source.json` (about 700 MB at
  full size) and the receipt written with `json.dumps(indent=1)`, which runs the pure Python encoder; and the heap
  check after the conversion read the whole world again on one core.
- Validation: `load_world` read and placed every frame's terrain on one core. With every check stored, each task
  still carried its chunk images through the pipe to a worker only to be hashed there, so the workers waited on
  the parent ("running" units, idle cores).
- Stair gate: every walk unit was given the memory share of the largest frame (Vivec, 2,855 MiB) and the room was
  measured with the reclaimable file cache counted as used, so 4 workers walked frames of about 300 MiB.
- Statistics: every model's faces and textures and every chunk's resident ring on one core, and the 110 MB
  document written by the pure Python encoder.
- Pools: `completed_map` and the memory-governed map waited for a unit to finish (or 30 s) before reading a raised
  allowance again, so a pool whose units were long did not grow when the scheduler gave it more cores.

## Why it was not caught

The perf guard compares whole stages with their baseline, and the phases between the timed ones printed nothing.
The test worlds have two frames, where neither the quadratic checks nor the parent-made layouts show.

## Reproduction

Any full build with the CHIM region frames: watch the CHIM stage's phase lines and `underused.jsonl`.

## Repair

On branch v0.0.44-serial, 19 October 2026; every method before it stays selectable:

- `chim.ownership.source_failures` finds the cores through a grid of cells (the same failures in the same order);
  `original` returns the value it builds without a deep copy; `chim.world.frame_order` compares only frames that
  share a cell. The section has its own timed phase: `CHIM world: aprons, ownership and effects`.
- `chim.world.frame_rows`: each frame's layout and visibility rows are made together on a worker, one frame per
  task, largest first; a town gets its layout there too and its row blocks over every worker. The worker also packs
  the chunks' visibility rows and checks the terrain shifts, so the pack only walks
  (`AMIWIND_CHIM_VIS_ROWS=frames-parent`: the v0.0.43 method; `serial`: the method before v0.0.42). The pack prints
  one line saying it is one walk in pack order and why.
- `chim.far.write_layers(jobs=...)`: one frame per task, each reading its own boxes; `tools/parallel_json.py`
  writes the source manifest, the receipt and the statistics with their long lists encoded on the workers (the
  same bytes as `json.dumps`); the heap, zone and stair gates read a world they are not given with the pool. New
  phases: `CHIM world: far terrain`, `CHIM world: source and receipt`.
- `chim.validate.load_world(jobs=...)`: the frame files are read on the workers, in groups, from the world's own
  files (the same frames and failures in the same order). The cached frame and model checks: the parent keys every
  unit (SHA-256 of what it reads), the workers look the keys up and return the stored results, and only the units
  that missed go out with their inputs (`AMIWIND_CHIM_VALIDATE_LOOKUP=in-task`: the method before).
- Stair gate: every unit is admitted at its own frame's size (`build_parallel.governed_map(item_mib=...)`, the
  memory governor's `admits`): units start while the room holds them, largest first, a waiting larger unit keeps
  its room; the counting pass takes the same path; the room leaves the reclaimable file cache out; a worker keeps
  built only what fits its unit's share.
- Statistics: the models' faces and textures and the resident rings on the workers; the document through
  `parallel_json`.
- Pools: `completed_map`, `governed_map` and `ordered_map` read the allowance at least once a second while units
  run, so a pool grows as soon as the allowance rises and shrinks only by starting no new units.

## Verification

On 156 region frames plus Balmora (16 CPUs, 16 GiB; the build container and two gate suites ran beside it, so the
after runs are on a busy host):

| Section | before | after (three runs) |
| --- | ---: | ---: |
| between the areas and the visibility rows | 4 s, 1 core | 1.6-2.1 s, 1 core |
| visibility rows | 33.1 s, 3.8 cores | 7.7-14.7 s, 9.5-12.7 cores |
| pack | 7.0 s, 1 core | 3.3-5.5 s, 1 core (the walk alone) |
| end of the conversion | 22 s, 1 core | 8-11 s (far terrain 0.6-1.0 s at 4-7 cores, source and receipt 1.7-1.9 s at 3.6-4.5 cores) |
| validation (no stored units) | 1 min 13 s, 8.5 cores | 45-55 s, 11.6-11.8 cores |
| validation (every unit stored) | 17.4-19.8 s | 16.1-19.9 s |
| stair gate | 2 min 20 s, 8.5 cores (9 of 16 workers) | 1 min 2 s - 1 min 33 s, 12.4-15.5 cores (16 of 16) |
| statistics | 6.8 s, 1 core | 4.3-6.2 s, 1.5 cores |
| from the areas to the end of the stage | 4 min 55 s | 2 min 23 s - 3 min 0 s |

At this size the stored-unit validation hardly changes: its frame reads were about 8 s of it and the chunk images it
no longer sends are few; at full size (1,351 frames) both grow with the world (the try 3 build: 4 min 59 s at 2.0
cores). Still serial in the validation, measured on 157 frames: opening its unit cache (3.8 s, once: it hashes the
checker's sources), the per-chunk bookkeeping between the parallel checks, and the walk measure.

Every file of the world, the source manifest, the receipt, the validation, stair, heap and zone reports and the
work folder (7,778 files) has the same SHA-256 before and after; `chim-timing.json` and the build-time fields of
`chim-stats.json` differ by nature (wall and CPU seconds). Pending: the next full build's phase lines.

## Prevention

Tests: `tests/test_chim_source_memo.py` (layouts and rows on the workers equal every earlier method byte for byte, and
the parent never makes a layout), `tests/test_chim_frames.py` (load_world on the workers, statistics on the
workers), `tests/test_chim_far.py`, `tests/test_parallel_json.py`, `tests/test_chim_stage_speed.py` (keyed lookups
equal lookups in the task, with the same hit and miss counts, and no stored unit is sent its inputs),
`tests/test_pool_live_growth.py` (a pool started at 2 grows to 6 within a second of the allowance rising, for every
map kind; units admitted at their own sizes), `tests/test_stair_pool_memory.py`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build speed (`build-speed`). Every stage on the shared worker pool; per-stage time and CPU in the build profile. See [families](README.md#families).

- [AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36](AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36.md): Concurrent master-builder builds oversubscribe the machine: a gate step fails with 'cp: Cannot allocate memory'
- [AW-LEASE-MEMORY-DEADLOCK-36](AW-LEASE-MEMORY-DEADLOCK-36.md): Memory leases deadlocked builds: a 44 GiB build never fit while any gate held its 6 GiB, so builds queued for hours
- [AW-LEASE-NO-GROW-36](AW-LEASE-NO-GROW-36.md): A running build's core lease did not grow back when gates ended, and its worker pools never grow
- [BUILD-BODY-BAKE-SLOWER-44](BUILD-BODY-BAKE-SLOWER-44.md): The image step's player body bake ran 42 % slower than its baseline with the same 40 bodies
- [BUILD-CACHE-ABSOLUTE-PATHS-33](BUILD-CACHE-ABSOLUTE-PATHS-33.md): Stage fingerprints contain absolute paths, so a moved workspace or checkout reuses nothing
- [BUILD-CACHE-CHIM-UNITS-33](BUILD-CACHE-CHIM-UNITS-33.md): The chim stage's fingerprint changes whenever the CHIM unit cache gains units, so the stage is never reused
- [BUILD-CACHE-CLOSURE-WIDE-33](BUILD-CACHE-CLOSURE-WIDE-33.md): Stage fingerprints count every module any imported module could import, so unrelated edits rebuild most stages
- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it
- [BUILD-CACHE-OVERBROAD-33](BUILD-CACHE-OVERBROAD-33.md): CHIM builds rerun the scene chain after merges that cannot change its outputs
- [BUILD-CACHE-PER-WORKSPACE-33](BUILD-CACHE-PER-WORKSPACE-33.md): Per-file caches live in each build workspace, so a build on a new volume with --reuse-from converts everything again (MiniWind media 1,195 s instead of seconds)
- [BUILD-CACHE-TRACE-PYTHONPATH-33](BUILD-CACHE-TRACE-PYTHONPATH-33.md): The stage read trace refused reuse of a reused run when another checkout was on PYTHONPATH
- [BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46](BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46.md): A change in the shared collision converter rebuilds every CHIM frame and everything after it, even where the output is identical
- [BUILD-CHIM-FRAME-SWAP-LATE-36](BUILD-CHIM-FRAME-SWAP-LATE-36.md): The image step builds 335 legacy maps of cells already on CHIM, then removes them before packing
- [BUILD-CHIM-MAIN-MEMORY-46](BUILD-CHIM-MAIN-MEMORY-46.md): The CHIM stage main process holds so much memory that the memory guard starves its own workers
- [BUILD-CHIM-REGION-FRAMES-TAIL-43](BUILD-CHIM-REGION-FRAMES-TAIL-43.md): The CHIM region-frame step runs its last frames on one worker while the other cores sit idle
- [BUILD-CHIM-SOURCE-REPEAT-41](BUILD-CHIM-SOURCE-REPEAT-41.md): The CHIM stage parsed the whole master and read the same models again for every area: 723 source stages took 24,500 CPU seconds
- [BUILD-CHIM-STAGE-IDLE-START-36](BUILD-CHIM-STAGE-IDLE-START-36.md): The chim stage of the 270-frame coast build spends its first 35-45 minutes on 1-4 cores while it holds 12-24 workers
- [BUILD-CHIM-STAGE-SERIAL-TAIL-36](BUILD-CHIM-STAGE-SERIAL-TAIL-36.md): After the parallel world build the chim stage ran its validation, heap gate and zone walk on one core (about 10 minutes of the 270-frame coast build)
- [BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42](BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42.md): In-stage pools of the CHIM step stay at the --jobs the stage was launched with: the v0.0.42 final's stair gate walked on 2 workers with an allowance of 12
- [BUILD-CHIM-STAIR-NO-REUSE-42](BUILD-CHIM-STAIR-NO-REUSE-42.md): The v0.0.42 final walked all 1,118 frames again: the walks of the passed dev1 build carry no check mark, because its launcher never promotes them
- [BUILD-CHIM-STATS-SERIAL-TAIL-36](BUILD-CHIM-STATS-SERIAL-TAIL-36.md): The chim stage ended with its statistics validating the whole CHIM world a second time, on one core with no output (7 min 44 s on 273 frames)
- [BUILD-CHIM-UNIT-HULL-KEY-33](BUILD-CHIM-UNIT-HULL-KEY-33.md): CHIM unit cache ignores the standing-hull form: a --model-hull chain build reused routed-hull model units
- [BUILD-CHIM-VIS-ROWS-KEY-BROAD-46](BUILD-CHIM-VIS-ROWS-KEY-BROAD-46.md): The CHIM visibility rows are keyed on the frames' whole collision, so every collision change redoes 75,904 units, and each frame took 4 times longer
- [BUILD-CHIM-VIS-ROWS-SERIAL-42](BUILD-CHIM-VIS-ROWS-SERIAL-42.md): The CHIM visibility rows of a build with many new frames run on one worker at a time and print nothing for half an hour or more
- [BUILD-CHIM-WORLD-SERIAL-TAIL-41](BUILD-CHIM-WORLD-SERIAL-TAIL-41.md): After the region frames the CHIM world conversion prepared the towns one after another and worked out 723 frames' visibility rows in turn: about 7 minutes on 1 to 5 of 24 cores
- [BUILD-DOOR-REFERENCE-SERIAL-33](BUILD-DOOR-REFERENCE-SERIAL-33.md): The door step reads the whole master once per destination cell
- [BUILD-ENGINE-SOURCE-KEY-BROAD-36](BUILD-ENGINE-SOURCE-KEY-BROAD-36.md): Any engine source edit changes the keys of the chim and world-flora stages
- [BUILD-ENV-FINGERPRINT-GLOBAL-33](BUILD-ENV-FINGERPRINT-GLOBAL-33.md): The stair rule setting invalidates the reuse cache of every build stage, including stages that never read it
- [BUILD-ETA-CLOCK-UTC-ONLY-46](BUILD-ETA-CLOCK-UTC-ONLY-46.md): The build ETA printed its finish time on the container clock (UTC) only: 12:53 read as three hours ago on a +03:00 host
- [BUILD-EXCLUDE-STAGE-CLOSURE-33](BUILD-EXCLUDE-STAGE-CLOSURE-33.md): The quick test build table entered every conversion stage's fingerprint through the stage scheduler
- [BUILD-FLORA-FALLBACK-RETRY-35](BUILD-FLORA-FALLBACK-RETRY-35.md): The routed-hull fallback of a flora overlay could not retry: the failed try's candidate folder was looked up from the wrong place
- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-HEAP-GATE-AFTER-STAIRS-46](BUILD-HEAP-GATE-AFTER-STAIRS-46.md): The 12-second CHIM heap gate runs after the two-hour stair walk, so an over-budget frame fails the build late
- [BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md): Scene-chain stages leave most of the workers they hold idle
- [BUILD-IMAGE-AUDIO-SERIAL-36](BUILD-IMAGE-AUDIO-SERIAL-36.md): The image step puts the audio payload in one file at a time while 22 of 24 cores sit idle
- [BUILD-IMAGE-CHIM-MAPS-SERIAL-36](BUILD-IMAGE-CHIM-MAPS-SERIAL-36.md): The image step writes the CHIM region cells' .chim maps one by one on half a core, silently
- [BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36](BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36.md): The image step's CHIM frame-map heap check runs on one core: 66 s to 4.5 min per build while 23 cores idle
- [BUILD-IMAGE-HASH-UNDERUSED-36](BUILD-IMAGE-HASH-UNDERUSED-36.md): The image step hashes 34,592 payload files on 3 of 24 cores (one file per pool task)
- [BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36](BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36.md): The image step's world map heap audit estimates 170 maps on 5.3 of 24 cores
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
- [BUILD-IMAGE-NPC-CHECKS-LATE-44](BUILD-IMAGE-NPC-CHECKS-LATE-44.md): The image step's player body and guard torch bakes fail only at the end of a full build instead of before the expensive stages
- [BUILD-IMAGE-REGION-MAPS-SERIAL-43](BUILD-IMAGE-REGION-MAPS-SERIAL-43.md): The image step's CHIM frame-map phases run on one core: the world read six times, ground traces on whole frames
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47](BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47.md): The image step parses the 694 MB CHIM source manifest three times, on one core each (16.0 s, 18.5 s, 17.1 s)
- [BUILD-IMAGE-STAIR-WALK-CORES-43](BUILD-IMAGE-STAIR-WALK-CORES-43.md): The image step's stair walk used 45 % of its cores in the v0.0.43-dev3 build (95 % before): the perf guard failed its walk_unit section
- [BUILD-IMAGE-STAIR-WALK-SERIAL-36](BUILD-IMAGE-STAIR-WALK-SERIAL-36.md): The image step's stair walk runs one map per worker: a single heavy room keeps one core busy for 13-19 minutes while the others sit idle
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-IMAGE-WORLD-READ-FRAMES-47](BUILD-IMAGE-WORLD-READ-FRAMES-47.md): The image step CHIM world read ran its frame-read pool at 2.96 of 24 cores for 102 s (91 units): perf guard FIX-NOW
- [BUILD-INPUTCHECK-SLOW-32](BUILD-INPUTCHECK-SLOW-32.md): The game data reference check takes over 12 minutes through Docker
- [BUILD-JOBS-RESOLVE-PER-STAGE-32](BUILD-JOBS-RESOLVE-PER-STAGE-32.md): With automatic jobs, stages of one build plan can get different worker counts
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33](BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): Every build stage's source fingerprint took in the engine sources through the MiniWind module
- [BUILD-MINIWIND-STAGE-CLOSURE-33](BUILD-MINIWIND-STAGE-CLOSURE-33.md): The MiniWind plan puts the CHIM builder modules into every conversion stage's fingerprint
- [BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md): Pool workers open their own pools sized to the whole stage's allowance
- [BUILD-NPC-GALLERY-REBUILT-46](BUILD-NPC-GALLERY-REBUILT-46.md): The NPC gallery (3,551 models, 36 minutes) is rebuilt after a change in collision code that its models do not use
- [BUILD-NPCLOD-PATH-ARG-34](BUILD-NPCLOD-PATH-ARG-34.md): The first --npc-lod on build stopped at its area stage: a Path in the command broke build-state.json
- [BUILD-OPTIMIZER-CACHE-KEY-BROAD-36](BUILD-OPTIMIZER-CACHE-KEY-BROAD-36.md): Regression: the image step's BSP optimizer pass cache reused 13 of 2,658 maps; its key covers the whole image tool, so any image-code change redoes every map
- [BUILD-OPTION-RECORD-KEYS-STAGES-47](BUILD-OPTION-RECORD-KEYS-STAGES-47.md): A new builder option entry rebuilds the CHIM, town, flora, engine and image stages: their keys counted all of config/
- [BUILD-ORDERED-WINDOW-33](BUILD-ORDERED-WINDOW-33.md): The ordered worker pool idles behind one slow item, and hands long items out last
- [BUILD-PARTITION-GROWTH-UNGATED-36](BUILD-PARTITION-GROWTH-UNGATED-36.md): Nothing gates the number of world partitions or the growth of the image
- [BUILD-PASS-KEY-TOP-BROAD-43](BUILD-PASS-KEY-TOP-BROAD-43.md): A pass key counts a reached module's whole import-time code: a new constant in chim/models.py rekeyed all 1,295 region frame maps
- [BUILD-PIPELINE-UNDERUTILIZATION-36](BUILD-PIPELINE-UNDERUTILIZATION-36.md): Umbrella: several builder phases run on one core while the rest of the machine idles, and some do work the build no longer needs
- [BUILD-PRERENDERED-PRUNE-ORDER-33](BUILD-PRERENDERED-PRUNE-ORDER-33.md): Prerendered store prune picks the superseded entry by folder name when two entries share a timestamp
- [BUILD-PROFILE-JOBS-START-ONLY-33](BUILD-PROFILE-JOBS-START-ONLY-33.md): The build profile compares a stage's cores with the workers it started with, not the ones it held
- [BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42](BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42.md): The build profiler's sampled timeline counts a finished child process twice
- [BUILD-PROFILE-SECTIONS-MISSING-36](BUILD-PROFILE-SECTIONS-MISSING-36.md): Long builder phases printed no elapsed time and recorded no sections: the chim stage's 44-minute stair gate was visible only from cache file times
- [BUILD-PROFILER-NO-WASTE-ALARM-36](BUILD-PROFILER-NO-WASTE-ALARM-36.md): No profiler, perf ledger or gate flagged idle cores, work done for maps that are removed, or growth of the image
- [BUILD-PROGRESS-ETA-BASIS-36](BUILD-PROGRESS-ETA-BASIS-36.md): The live build progress took a stage's expected time from earlier runs of any size: dev3's chim stage was expected at 154 s and ran 1 h 48 min
- [BUILD-RESIDENT-MAP-SLOWER-46](BUILD-RESIDENT-MAP-SLOWER-46.md): The resident-map step of the area and balmora-interiors stages ran 55 to 60 percent slower than its baseline with the same units
- [BUILD-RESOURCE-PLAN-CHIM-ESTIMATE-44](BUILD-RESOURCE-PLAN-CHIM-ESTIMATE-44.md): The resource plan estimated the CHIM stage at 2 workers and 6 h 13 min; it ran on 24 workers in about 75 min
- [BUILD-REUSE-APPLY-SERIAL-41](BUILD-REUSE-APPLY-SERIAL-41.md): A reused stage staged its files one at a time: world terrain, scenery and flora took 8 to 12 seconds each, one after another, at the start of every reuse build
- [BUILD-REUSE-KEYS-TOO-BROAD-35](BUILD-REUSE-KEYS-TOO-BROAD-35.md): A whole build reused no stage, and the cost was not visible before the build started
- [BUILD-REUSE-TMP-UNDECLARED-33](BUILD-REUSE-TMP-UNDECLARED-33.md): A stage that runs while a reused stage is copied becomes non-reusable
- [BUILD-SCHEDULER-EVEN-SHARE-33](BUILD-SCHEDULER-EVEN-SHARE-33.md): The stage scheduler splits the workers evenly between running stages, so the longest stage gets no more than the shortest (MiniWind media on 1 of 4 workers for 1,195 s)
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts
- [BUILD-SCHEDULER-LOWBUDGET-33](BUILD-SCHEDULER-LOWBUDGET-33.md): With a small --jobs budget the stage scheduler starts nothing when more branches are ready than the budget (busy loop)
- [BUILD-SCHEDULER-MEMORY-STARVED-42](BUILD-SCHEDULER-MEMORY-STARVED-42.md): The scheduler's memory guard held the v0.0.42 final's chim stage on 1 of its 6 workers for over an hour, and nothing said so before or while it happened
- [BUILD-SILENT-PHASES-36](BUILD-SILENT-PHASES-36.md): Builder phases run silent: no start/end timing, no progress, no heartbeat; the CHIM stats step is a single-core tail
- [BUILD-SIZE-GUARD-OLD-BASELINE-45](BUILD-SIZE-GUARD-OLD-BASELINE-45.md): The size guard compared a release build with an older release's record: v0.0.45, every folder the size of v0.0.44's, failed on 0.44 GiB of CHIM world growth against v0.0.41
- [BUILD-STAGE-ALLOWANCE-STUCK-43](BUILD-STAGE-ALLOWANCE-STUCK-43.md): A build stage's worker allowance stays at 1 after the other stages finish, so the CHIM stage runs on one core
- [BUILD-STAGE-INTERRUPT-ABSORBED-36](BUILD-STAGE-INTERRUPT-ABSORBED-36.md): The stage wrapper absorbed Ctrl-C: a stage that handled the interrupt and returned 0 counted as passed, and the build went on
- [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md): A pooled stage that starts while others run gets one worker as its start value
- [BUILD-STAIR-GATE-OOM-42](BUILD-STAIR-GATE-OOM-42.md): The CHIM stair gate runs a whole-Vivec MiniWind out of memory: its worker pool breaks
- [BUILD-STAIR-WALK-BORDER-COPIES-41](BUILD-STAIR-WALK-BORDER-COPIES-41.md): The CHIM stair gate walks every frame's whole border, so each cell's flights are walked many times and unreachable copies can fail a build
- [BUILD-STAIR-WALK-OFF-46](BUILD-STAIR-WALK-OFF-46.md): Every build walked the island stairs (about 1.5 million steps per release cycle); the stair walk is now off by default
- [BUILD-STAIR-WALK-SCOPE-KEY-46](BUILD-STAIR-WALK-SCOPE-KEY-46.md): Development builds walk every step of the island again after any collision change: the CHIM gate ignored the walk scope and keyed each frame by all of its collision
- [BUILD-STAIR-WALK-SLOW-33](BUILD-STAIR-WALK-SLOW-33.md): The image step's stair walk spent most of its time in interpreted collision traces and brute-force headroom tests (1,751 s of the rc1c image step)
- [BUILD-STATS-SERIAL-36](BUILD-STATS-SERIAL-36.md): The CHIM stats step runs serially and silently on one core
- [BUILD-STORAGE-DUPLICATES-33](BUILD-STORAGE-DUPLICATES-33.md): Build storage keeps full duplicate copies of images, stage outputs and packages, and nothing removes them
- [BUILD-UNDERUSE-GATE-36](BUILD-UNDERUSE-GATE-36.md): The profiler did not flag long underused phases: 7 min 44 s of CHIM statistics on 1 of 24 cores and 77 s of zone walk on 1 core showed nowhere
- [BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md): Docker builds and disk-image steps on Windows folders are slow
- [CHIM-EMPTY-MODEL-REPORT-40](CHIM-EMPTY-MODEL-REPORT-40.md): Terrain-only CHIM validation crashes while reporting the largest scenery model
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-STAIR-GATE-WORLD-RELOAD-36](CHIM-STAIR-GATE-WORLD-RELOAD-36.md): The CHIM stair gate's workers read the whole CHIM world again every time they switch frames (about 14.5 s per read on the 273-frame world)
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- [MINIWIND-NO-INTERIOR-SCOPE-42](MINIWIND-NO-INTERIOR-SCOPE-42.md): A MiniWind of one room built the whole town: no scope converted only the start room
- [MINIWIND-NOT-MINUTES-33](MINIWIND-NOT-MINUTES-33.md): A reused MiniWind build took about two hours instead of minutes
- [MINIWIND-SCENE-CHAIN-WEIGHT-42](MINIWIND-SCENE-CHAIN-WEIGHT-42.md): Every MiniWind bakes all playable races and the opening rooms, and walks its whole frame stairs
- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change

Related bugs in other categories:

- [BUILD-REUSE-SCHEDULER-TOP-45](BUILD-REUSE-SCHEDULER-TOP-45.md): A scheduler-only edit rekeys every stage, NPC gallery face and stair walk that reaches tools/build_parallel.py

<!-- END GENERATED CATEGORY -->
