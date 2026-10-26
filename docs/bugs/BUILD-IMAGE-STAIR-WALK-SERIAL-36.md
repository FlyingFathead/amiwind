# BUILD-IMAGE-STAIR-WALK-SERIAL-36: The image step's stair walk runs one map per worker: a single heavy room keeps one core busy for 13-19 minutes while the others sit idle

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 5 times; something has to be done

- Reported with v0.0.33-rc1 at 2026-10-09 14:00 +0300: rc1c: stair walk 1,751 s, 8.4 of 22 cores, maps handed out in name order (BUILD-STAIR-WALK-SLOW-33 sped up each trace and sorted maps largest first; the unit stayed one map)
- Reported with v0.0.36-dev4 at 2026-10-11 07:28 +0300: Arena Pit MiniWind 05c45b7: 3 maps walked in 13m12s at 1.0 cores (vai000 alone)
- Reported with v0.0.36-dev4 at 2026-10-11 08:37 +0300: whole-city Vivec with rooms try2 3734cf5: 132 maps in 19m24s at 1.7 cores
- Reported with v0.0.36-dev5 at 2026-10-11 09:41 +0300: whole-city Vivec with rooms f6e08fe: 132 maps in 15m55s at 1.8 cores, 0 reused
- Reported with v0.0.36-dev5 at 2026-10-11 10:09 +0300: maintainer order (TG): parallelize the stair walks; fix immediately

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 October 2026, in v0.0.36-dev4 |
| Where | Image step stair walk (tools/stair_walk.py check): one whole map is one parallel unit |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | high: Critical path of every build with new rooms: 13m12s at 1.0 cores, 15m55s at 1.8 of 24 cores; maintainer order to parallelize not met: FIX IMMEDIATELY |
| Family | Build speed (`build-speed`) |
| Playtest version | MiniWind v0.0.36-dev4 (vivec-arena-pit) |
| From commit | source 05c45b7, engine 05c45b7, CHIM world 05c45b7 |
| CHIM engine version | CHIM 0.1.0, engine 05c45b7, world format 0.5 |
| Build note | run 2026_10_11_v0.0.36-dev4_miniwind-vivec-arena-pit-arena-pit-rooms_05c45b7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 5 times; something has to be done](#persisting-reported-5-times-something-has-to-be-done)
- [Status: 11 October 2026](#status-11-october-2026)
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

## Status: 11 October 2026

FIX IMMEDIATELY (maintainer order). Persisting: the stair walks were ordered parallel before, and the image
step's walk still ends on one core whenever one map is heavy. Repair in progress on the
v0.0.36-stairs-rc1 line.

## Symptom

The image step's stair walk (the gate that walks every step and ramp of every map with the standing box)
spends most of its time on one core:

| Build | Maps | Took | Cores (of 24) |
| --- | ---: | ---: | ---: |
| Arena Pit MiniWind (v0.0.36-dev4, 05c45b7) | 3 | 13m12s | 1.0 |
| Whole-city Vivec with rooms, try2 (v0.0.36-dev4, 3734cf5) | 132 | 19m24s | 1.7 |
| Whole-city Vivec with rooms (v0.0.36-dev5, f6e08fe) | 132 | 15m55s | 1.8 |
| Full coast (v0.0.36-dev4, d050b6f) | 2,597 | 6m25s | 10.2 |
| **Totals** | **2,864** | **54m56s** | |

The full coast build spreads over many small maps and keeps about ten cores busy; the room builds do not:
one heavy room is walked by one worker from start to end.

## Where

`tools/stair_walk.py`: `check` hands `check_map_cached` one task per map to the worker pool
(`build_parallel.ordered_map`, largest first). The unit of parallel work is a whole map, so the walk can
never be faster than its slowest map. The rooms with routed standing hulls (the Arena Pit `vai000`, the
Palace `vpi000` with 1,488 rows) take minutes each: every trace there walks a long hull chain
(COLLISION-TRACE-COST-33).

## How it happened

The stair walk was made faster per trace and handed out largest map first on 9 October 2026
(BUILD-STAIR-WALK-SLOW-33, v0.0.33-rc1: 1,751 s at 8.4 of 22 cores), and on 9 October the
builder-performance line owned "parallelism inside the stair walk". The CHIM stair gate on frames was
split into tiles and runs on all cores (CHIM-STAIR-GATE-WORLD-RELOAD-36, 44 min to 169 s on 11 October),
but the image walk over ordinary maps kept the whole map as its unit. While the payload was hundreds of
small open-world maps that did not show; the CHIM line moves the open world into frames and adds big
converted rooms, so the image walk is now a few heavy maps.

## Why it was not caught

The build profile printed the walk's cores ("1.0 cores", "1.8 cores") on every build, but no gate failed
on a stage that used a fraction of the machine, and nobody turned the line into a fix item.

## Reproduction

Any MiniWind with converted rooms (`--miniwind-preset vivec-city-chim`): the image log line
`Image: stair walk: done - took ..., N cores`.

## Repair

In progress: every walked map's candidate steps and ramps are split into units of a bounded size, and the
units of all maps go to the worker pool together, the largest first; each unit walks its slice of the map's
candidates on the map's own collision, and the rows are put back together in candidate order, so the map's
rows and its stored record are byte for byte the rows of the whole-map walk. Records stay one per map,
keyed by the SHA-256 of the map's bytes (and the walker's own code), so unchanged maps are never walked
again. The builder prints the units and cores of the walk.

## Verification

11 October 2026, offline on the f6e08fe image (132 maps, 6,025 rows; busy host: two full builds beside it):
the unit walk's rows are byte for byte the run's rows (SHA-256 ab4c4ffb... both), in 452 units on 24 workers,
530 s at 4.7 cores against the run's 955 s at 1.8 cores; the dev5 coast image's 718 maps: 137,851 rows identical
with the walker of this line. The heavy Arena Pit (2,057 steps, 808 s alone) is now 17 units of at most 128.
tests/test_stair_parallel.py: same report as the whole-map walk for any unit size and worker count, the walk asks
the pool for --jobs workers and splits maps into several units, records shared with the whole-map walk (a reused
map is never walked: the unit worker raising on a call proves it), the image step uses the unit walk.

## Prevention

A test fails when the walk runs serially or a map is one unit; the perf guard compares the walk's cores
with its baseline.

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
- [BUILD-CHIM-SERIAL-SECTIONS-44](BUILD-CHIM-SERIAL-SECTIONS-44.md): The CHIM stage runs several sections on one core while units wait: visibility rows starve their workers
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
- BUILD-ETA-CHIM-STALE-48 (no report page): The build ETA said the CHIM world had about 4 minutes left for over 20 minutes while 40 % of its frames remained
- [BUILD-ETA-CLOCK-UTC-ONLY-46](BUILD-ETA-CLOCK-UTC-ONLY-46.md): The build ETA printed its finish time on the container clock (UTC) only: 12:53 read as three hours ago on a +03:00 host
- [BUILD-EXCLUDE-STAGE-CLOSURE-33](BUILD-EXCLUDE-STAGE-CLOSURE-33.md): The quick test build table entered every conversion stage's fingerprint through the stage scheduler
- [BUILD-FLORA-FALLBACK-RETRY-35](BUILD-FLORA-FALLBACK-RETRY-35.md): The routed-hull fallback of a flora overlay could not retry: the failed try's candidate folder was looked up from the wrong place
- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-HEAP-GATE-AFTER-STAIRS-46](BUILD-HEAP-GATE-AFTER-STAIRS-46.md): The 12-second CHIM heap gate runs after the two-hour stair walk, so an over-budget frame fails the build late
- [BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md): Scene-chain stages leave most of the workers they hold idle
- [BUILD-IMAGE-AUDIO-SERIAL-36](BUILD-IMAGE-AUDIO-SERIAL-36.md): The image step puts the audio payload in one file at a time while 22 of 24 cores sit idle
- [BUILD-IMAGE-CHIM-MAPS-SERIAL-36](BUILD-IMAGE-CHIM-MAPS-SERIAL-36.md): The image step writes the CHIM region cells' .chim maps one by one on half a core, silently
- [BUILD-IMAGE-FINALIZE-UNDERUSED-48](BUILD-IMAGE-FINALIZE-UNDERUSED-48.md): The image step ran on about 4 of 24 cores for 85 s after the player view (serial steps, then finalize at 2.6 cores), and the underused warning named no sub-step
- [BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36](BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36.md): The image step's CHIM frame-map heap check runs on one core: 66 s to 4.5 min per build while 23 cores idle
- [BUILD-IMAGE-HASH-UNDERUSED-36](BUILD-IMAGE-HASH-UNDERUSED-36.md): The image step hashes 34,592 payload files on 3 of 24 cores (one file per pool task)
- [BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36](BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36.md): The image step's world map heap audit estimates 170 maps on 5.3 of 24 cores
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
- [BUILD-IMAGE-NPC-CHECKS-LATE-44](BUILD-IMAGE-NPC-CHECKS-LATE-44.md): The image step's player body and guard torch bakes fail only at the end of a full build instead of before the expensive stages
- [BUILD-IMAGE-REGION-MAPS-SERIAL-43](BUILD-IMAGE-REGION-MAPS-SERIAL-43.md): The image step's CHIM frame-map phases run on one core: the world read six times, ground traces on whole frames
- BUILD-IMAGE-SCAN-GROUND-UNDERUSED-52 (no report page): The image step scans maps on about one core and runs the actor ground check under half the pool
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47](BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47.md): The image step parses the 694 MB CHIM source manifest three times, on one core each (16.0 s, 18.5 s, 17.1 s)
- [BUILD-IMAGE-STAIR-WALK-CORES-43](BUILD-IMAGE-STAIR-WALK-CORES-43.md): The image step's stair walk used 45 % of its cores in the v0.0.43-dev3 build (95 % before): the perf guard failed its walk_unit section
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-IMAGE-WORLD-READ-FRAMES-47](BUILD-IMAGE-WORLD-READ-FRAMES-47.md): The image step CHIM world read ran its frame-read pool at 2.96 of 24 cores for 102 s (91 units): perf guard FIX-NOW
- [BUILD-INPUTCHECK-SLOW-32](BUILD-INPUTCHECK-SLOW-32.md): The game data reference check takes over 12 minutes through Docker
- [BUILD-JOBS-RESOLVE-PER-STAGE-32](BUILD-JOBS-RESOLVE-PER-STAGE-32.md): With automatic jobs, stages of one build plan can get different worker counts
- BUILD-M68K-ICE-SKEL-PARSE-52 (no report page): The m68k compiler crashed on the animation table parse (internal compiler error in patch_jump_insn); the host tests compile it with the host compiler only
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33](BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): Every build stage's source fingerprint took in the engine sources through the MiniWind module
- [BUILD-MINIWIND-STAGE-CLOSURE-33](BUILD-MINIWIND-STAGE-CLOSURE-33.md): The MiniWind plan puts the CHIM builder modules into every conversion stage's fingerprint
- [BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md): Pool workers open their own pools sized to the whole stage's allowance
- [BUILD-NPC-GALLERY-KEY-NEUTRAL-READ-47](BUILD-NPC-GALLERY-KEY-NEUTRAL-READ-47.md): The NPC gallery stage is never reused: making its model keys reads tools/chim/units.py, which the stage key leaves out
- [BUILD-NPC-GALLERY-REBUILT-46](BUILD-NPC-GALLERY-REBUILT-46.md): The NPC gallery (3,551 models, 36 minutes) is rebuilt after a change in collision code that its models do not use
- [BUILD-NPCLOD-PATH-ARG-34](BUILD-NPCLOD-PATH-ARG-34.md): The first --npc-lod on build stopped at its area stage: a Path in the command broke build-state.json
- [BUILD-OPTIMIZER-CACHE-KEY-BROAD-36](BUILD-OPTIMIZER-CACHE-KEY-BROAD-36.md): Regression: the image step's BSP optimizer pass cache reused 13 of 2,658 maps; its key covers the whole image tool, so any image-code change redoes every map
- [BUILD-OPTION-RECORD-KEYS-STAGES-47](BUILD-OPTION-RECORD-KEYS-STAGES-47.md): A new builder option entry rebuilds the CHIM, town, flora, engine and image stages: their keys counted all of config/
- BUILD-ORDERED-MAP-SCAN-51 (no report page): The pool map that hands results back in input order scans every held future on each turn: the main process works O(n squared) while large maps run
- [BUILD-ORDERED-WINDOW-33](BUILD-ORDERED-WINDOW-33.md): The ordered worker pool idles behind one slow item, and hands long items out last
- [BUILD-PARTITION-GROWTH-UNGATED-36](BUILD-PARTITION-GROWTH-UNGATED-36.md): Nothing gates the number of world partitions or the growth of the image
- [BUILD-PASS-KEY-TOP-BROAD-43](BUILD-PASS-KEY-TOP-BROAD-43.md): A pass key counts a reached module's whole import-time code: a new constant in chim/models.py rekeyed all 1,295 region frame maps
- [BUILD-PIPELINE-UNDERUTILIZATION-36](BUILD-PIPELINE-UNDERUTILIZATION-36.md): Umbrella: several builder phases run on one core while the rest of the machine idles, and some do work the build no longer needs
- BUILD-PLAN-BESIDE-STALE-48 (no report page): The resource plan held a reuse build at 1 of 24 room batch workers against memory that stages it no longer runs held in the measured run
- BUILD-PLAN-PESSIMISTIC-48 (no report page): The start-up resource plan predicts hours for stages that run in minutes: it sums every stage that could run beside one at full speed
- [BUILD-PLAYER-VIEW-UNDERUSED-48](BUILD-PLAYER-VIEW-UNDERUSED-48.md): The image step player view remade all 80 player bodies in every build on four fresh worker pools (2m05s at 16.2 of 24 cores)
- BUILD-POOL-MEMORY-PEAK-48 (no report page): The CHIM and room stages ran side by side at 42 of 44 GiB and were both throttled to one worker for over ten minutes
- BUILD-POOL-TINY-UNITS-48 (no report page): Stages hand their pools units too small to keep the cores busy (CHIM slices, the town stages)
- [BUILD-PRERENDERED-PRUNE-ORDER-33](BUILD-PRERENDERED-PRUNE-ORDER-33.md): Prerendered store prune picks the superseded entry by folder name when two entries share a timestamp
- [BUILD-PROFILE-JOBS-START-ONLY-33](BUILD-PROFILE-JOBS-START-ONLY-33.md): The build profile compares a stage's cores with the workers it started with, not the ones it held
- [BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42](BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42.md): The build profiler's sampled timeline counts a finished child process twice
- [BUILD-PROFILE-SECTIONS-MISSING-36](BUILD-PROFILE-SECTIONS-MISSING-36.md): Long builder phases printed no elapsed time and recorded no sections: the chim stage's 44-minute stair gate was visible only from cache file times
- [BUILD-PROFILER-NO-WASTE-ALARM-36](BUILD-PROFILER-NO-WASTE-ALARM-36.md): No profiler, perf ledger or gate flagged idle cores, work done for maps that are removed, or growth of the image
- [BUILD-PROGRESS-ETA-BASIS-36](BUILD-PROGRESS-ETA-BASIS-36.md): The live build progress took a stage's expected time from earlier runs of any size: dev3's chim stage was expected at 154 s and ran 1 h 48 min
- BUILD-PY-TEXT-LIMIT-52 (no report page): tools/build.py is a few bytes under the release text size limit: the next change to it fails the gate unless it is split
- BUILD-RESIDENT-BAKE-SLOWER-52 (no report page): The skeletal resident bake of the town stages is 74 to 149 % slower than its baseline with the same residents
- [BUILD-RESIDENT-MAP-SLOWER-46](BUILD-RESIDENT-MAP-SLOWER-46.md): The resident-map step of the area and balmora-interiors stages ran 55 to 60 percent slower than its baseline with the same units
- [BUILD-RESOURCE-PLAN-CHIM-ESTIMATE-44](BUILD-RESOURCE-PLAN-CHIM-ESTIMATE-44.md): The resource plan estimated the CHIM stage at 2 workers and 6 h 13 min; it ran on 24 workers in about 75 min
- BUILD-RESOURCE-PLAN-MINIWIND-FULL-PARENT-52 (no report page): A MiniWind build is refused by the resource plan: its one-area CHIM stage is estimated from the full build's island-wide chim parent (19,868 MiB) and labelled a stair walk although the walk is off
- [BUILD-REUSE-APPLY-SERIAL-41](BUILD-REUSE-APPLY-SERIAL-41.md): A reused stage staged its files one at a time: world terrain, scenery and flora took 8 to 12 seconds each, one after another, at the start of every reuse build
- [BUILD-REUSE-KEYS-TOO-BROAD-35](BUILD-REUSE-KEYS-TOO-BROAD-35.md): A whole build reused no stage, and the cost was not visible before the build started
- [BUILD-REUSE-TMP-UNDECLARED-33](BUILD-REUSE-TMP-UNDECLARED-33.md): A stage that runs while a reused stage is copied becomes non-reusable
- [BUILD-REUSE-VERIFY-DISK-48](BUILD-REUSE-VERIFY-DISK-48.md): Reusing the chim stage reads and hashes all 9.35 GB of its outputs again: 78 s at 1.7 of 11 cores, counted as an underused stage
- [BUILD-SCHEDULER-EVEN-SHARE-33](BUILD-SCHEDULER-EVEN-SHARE-33.md): The stage scheduler splits the workers evenly between running stages, so the longest stage gets no more than the shortest (MiniWind media on 1 of 4 workers for 1,195 s)
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts
- [BUILD-SCHEDULER-LOWBUDGET-33](BUILD-SCHEDULER-LOWBUDGET-33.md): With a small --jobs budget the stage scheduler starts nothing when more branches are ready than the budget (busy loop)
- [BUILD-SCHEDULER-MEMORY-STARVED-42](BUILD-SCHEDULER-MEMORY-STARVED-42.md): The scheduler's memory guard held the v0.0.42 final's chim stage on 1 of its 6 workers for over an hour, and nothing said so before or while it happened
- BUILD-SEYDA-BSP-CARRIER-48 (no report page): Stages pass data through a legacy map file: seyda.bsp's entities and compiled room.bsp files carry what JSON could
- [BUILD-SEYDA-ENTITY-BUS-48](BUILD-SEYDA-ENTITY-BUS-48.md): Four scene stages still pass Seyda Neen's entities through the seyda.bsp carrier's entity lump
- [BUILD-SILENT-PHASES-36](BUILD-SILENT-PHASES-36.md): Builder phases run silent: no start/end timing, no progress, no heartbeat; the CHIM stats step is a single-core tail
- [BUILD-SIZE-GUARD-LATE-48](BUILD-SIZE-GUARD-LATE-48.md): The size guard judges only after the image is built: an rc that grew for a known reason stops after 32 minutes of image work, and the rerun assembles the whole image again
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
- [CHIM-BUDGET-RERUN-SERIAL-48](CHIM-BUDGET-RERUN-SERIAL-48.md): When one CHIM unit is over the brush image budget, every unit of its kind runs again one by one on one core to name it
- [CHIM-EMPTY-MODEL-REPORT-40](CHIM-EMPTY-MODEL-REPORT-40.md): Terrain-only CHIM validation crashes while reporting the largest scenery model
- [CHIM-INTERIORS-UNDERUSED-48](CHIM-INTERIORS-UNDERUSED-48.md): The CHIM interiors stage ran at 8.6 of 24 cores for 1 min 11 s
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-ROOM-FAIL-STAGE-48](CHIM-ROOM-FAIL-STAGE-48.md): One CHIM room that cannot be made failed the whole CHIM interiors stage (HOLD-LEVEL with every room batch by default)
- [CHIM-ROOM-OVER-BUDGET-RETRY-48](CHIM-ROOM-OVER-BUDGET-RETRY-48.md): A model over the image budget is tried whole again on every run before its cached tiles are used: its room runs on one core
- [CHIM-STAIR-GATE-WORLD-RELOAD-36](CHIM-STAIR-GATE-WORLD-RELOAD-36.md): The CHIM stair gate's workers read the whole CHIM world again every time they switch frames (about 14.5 s per read on the 273-frame world)
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- GATE-IMAGE-REMOVED-52 (no report page): A cleanup removed the image the gate s Linux host-parity step runs: the in-use check looked at containers only
- GATE-PRIVACY-NOT-IN-PREGATE-52 (no report page): The privacy word check runs only in the full gate: the quick pre-gate checks passed text the gate then refused
- [HARVEST-CHIM-COVERAGE-ONE-AREA-48](HARVEST-CHIM-COVERAGE-ONE-AREA-48.md): The image step harvest coverage check failed on every CHIM world of one area (every MiniWind sandbox of one town)
- [MINIWIND-NO-INTERIOR-SCOPE-42](MINIWIND-NO-INTERIOR-SCOPE-42.md): A MiniWind of one room built the whole town: no scope converted only the start room
- [MINIWIND-NOT-MINUTES-33](MINIWIND-NOT-MINUTES-33.md): A reused MiniWind build took about two hours instead of minutes
- [MINIWIND-SCENE-CHAIN-WEIGHT-42](MINIWIND-SCENE-CHAIN-WEIGHT-42.md): Every MiniWind bakes all playable races and the opening rooms, and walks its whole frame stairs
- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change
- RELEASE-GUARD-SLOW-CLONE-51 (no report page): The release guard, the fail-fast first step of a release, took 6 minutes on about 0.14 of a core: its release check clones the whole repository through the Windows-mounted drive
- RELEASE-SUITE-RECORD-SERIAL-51 (no report page): The release's suite record runs the whole test suite again on one core for about 22 minutes, right after the gate ran the same tests in about 2 minutes
- [ROOM-BAKE-FOOTPRINT-SLOW-48](ROOM-BAKE-FOOTPRINT-SLOW-48.md): The room actor bake's footprint rule with the collision-box test is more than 100 times slower
- [ROOM-BATCH-CORES-49](ROOM-BATCH-CORES-49.md): The room batches stage ran on about two of its eight cores for minutes before its first room, and kept few of its finished rooms when stopped
- ROOM-RESIDENTS-KEY-SERIAL-49 (no report page): The room residents step opens its unit cache once per resident: 233 s on one core before any cached resident is restored

<!-- END GENERATED CATEGORY -->
