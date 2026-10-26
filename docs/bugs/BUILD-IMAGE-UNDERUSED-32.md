# BUILD-IMAGE-UNDERUSED-32: Parts of the image step still run serially or leave most CPUs idle

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 8 times; something has to be done

- Reported with v0.0.32-dev at 2026-10-08 (time not recorded): BUILD-IMAGE-UNDERUSED-32: parts of the image step still serial
- Reported with v0.0.36-dev3 at 2026-10-11 00:43 +0300: audio payload and CHIM maps serial, stats on one core
- Reported with v0.0.45 at 2026-10-20 02:30 +0300: v0.0.45 perf guard FAILED: image bake_body 14.17/24 cores +50 percent, four image sections at about one core
- Reported with v0.0.46-dev1 at 2026-10-20 14:48 +0300: dev1 try 2: image 15m38s at 8.9 of 24; finalize 10m at 7.1; boot partition 50 s and CHIM volume 45 s at 1 core (xdftool one by one); a 281 s stall, 62 queued, 0 running
- Reported with v0.0.46 at 2026-10-20 20:02 +0300: v0.0.46 release image: CHIM world volume 43.4 s then boot partition 42.0 s, each on 1 core, one after the other; written at once on branch v0.0.46-span-what-we-need
- Reported with v0.0.47-dev1 at 2026-10-21 14:44 +0300: dev1 try 2: image 8m00s at 8.4 of 24, 4 windows (3m16s); finalize 3m19s at 2.95; preflight 16.0 s and 18.5 s at 1.1; partitions 36.9 s at 1.67 of 2
- Reported with v0.0.47-dev2 at 2026-10-21 17:30 +0300: dev2 try 3, FIX-NOW: frame-read pool 102 s on 2.96 of 24 cores, 91 units; see BUILD-IMAGE-WORLD-READ-FRAMES-47
- Reported with v0.0.48-dev2 at 2026-10-23 (time not recorded): dev2 try8 payload preflight 47 s on 1.6 of 24 cores; try5 bake_unit map 66 s on 0.0 of 24 (waits); image failed both runs

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | image step passes (tools/build_aga.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48 |
| Severity | medium: Several image passes run serially or leave most CPUs idle, slowing builds. |
| Family | Build speed (`build-speed`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48 (23 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 8 times; something has to be done](#persisting-reported-8-times-something-has-to-be-done)
- [Status: 23 October 2026 (v0.0.48)](#status-23-october-2026-v0048)
- [Status: 8 October 2026](#status-8-october-2026)
- [Symptom](#symptom)
- [Remaining serial work (profile of 8 October 2026, after the image-step parallel work)](#remaining-serial-work-profile-of-8-october-2026-after-the-image-step-parallel-work)
- [v0.0.47-dev1 (21 October 2026)](#v0047-dev1-21-october-2026)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 23 October 2026 (v0.0.48)

Fixed for v0.0.48 on the branch v0.0.48-fix-serial-steps: the payload preflight, which the image step runs twice
(45 s at 1.6 cores in the dev2 try 9 build; 21.7 s and 23.5 s), and the room batch install.

Measured read-only on the try 9 staged payload (container of 12 cores, the whole `payload_preflight.run`, the same
report either way): 36 to 44 s with the method before, 10.5 to 12.6 s now. Per part:

- **Engine map limits** (`map_engine_limits.audit_maps`): 1,135 maps read and parsed one by one, 12.5 to 15 s at
  0.17 cores (waiting for the disk) -> 2.0 to 2.2 s on the worker pool, the report in map order as before. Also in
  finalize's own engine limits check.
- **The source manifest's sprite sections** (`chim.frame_map.region_source_sections`, the disk layout): the whole
  694 MB manifest parsed to keep three keys of each frame, 10.4 s on one core -> 2.1 s at 6.9 cores
  (`parallel_json.load_list`: each worker parses whole frames of its byte range; the same sections, SHA-256 compared).
- **The layout walk** (`layout_plan.walk`, the disk layout's file sizes): pathlib over 37,000 CHIM and 27,000 boot
  files, about 4 s on one core -> os.walk with string paths, the same list.
- **One interpreter lock.** The checks ran on threads of one process; the Python-bound ones (payload names, file
  formats, host paths, actor frame layouts: under 1 s each alone) took 8 to 18 s side by side. They now run in
  processes of their own (`build_parallel.Background`), and the disk layout starts beside them as soon as the music
  sizes are known instead of after all of them.
- **The room batch install** (`room_batches.install`): 13,141 files hashed twice and copied one by one, untimed (5 to
  14 s) -> hashed and copied on the stage's threads, and a timed phase "Image: room batches install".

The methods before stay behind `AMIWIND_MAP_LIMITS_POOL=off`, `AMIWIND_JSON_POOL=ordered`,
`AMIWIND_LAYOUT_WALK=pathlib`, `AMIWIND_PREFLIGHT_METHOD=threads` and `AMIWIND_ROOM_INSTALL_THREADS=1`. Tests:
`tests/test_image_preflight_pool.py`. Still on one core and under a minute: the torch conversion (7.5 s, its receipt
order) and the world UI (14.6 s, beside the combat data).

## Status: 8 October 2026

Open; tagged performance. Found by the image-parallel work after the
[BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md) repair.

## Symptom

One image pass on the dev1 inputs (16-CPU container, `--jobs 16`) still spends:

| Work | Time | CPU use |
| --- | --- | --- |
| Guard torches | 60 s | serial |
| Shared sky | 53 s | serial |
| DH0 readback | 41 s | about 1 busy CPU |
| Night lighting | 23 s | serial |
| Balmora's three rebuilds | 78 s | about 2 busy CPUs |
| Hidden-surface cull | 190 s | about 6 of 16 CPUs |

Update (8 October 2026, 517d548, not shipped at the time of writing): the hidden-surface cull's imbalance came from
the parent process rewriting a 4 MB progress receipt after every map, which starved the workers;
it now writes at most every 2 s, and the cull went from 186.5 s to 83.1 s (busy host). Drive
readback is now parallel (in slices). Still open: guard torch conversion stays serial (60 s)
because its receipt records assets in first-read order, so per-entry asset recording is needed
before it can run in parallel; shared sky, night lighting and the Balmora rebuilds are not yet
re-measured.

## Remaining serial work (profile of 8 October 2026, after the image-step parallel work)

Measured on a busy host (21-30 % of the machine used by other work), `--jobs 16`, 16-CPU container.
bake_ground, the Balmora repair, the cull hash checks, sky and gallery staging now use the pool
(bake_ground 102.3 s at 2.2 cores -> 24.8 s at 12.0 cores; repair 85.5 s at 1.9 cores -> 23-32 s at
about 5.7 cores; outputs byte for byte identical). Still serial:

- xdftool: 60 s on one core, eight batched writes into the boot FFS image. One image cannot be
  written in parallel, but the boot volume could be built while the world partitions are packed.
- rdbtool: 24 s on one core (two calls).
- night_lighting stage: 21.7 s on one core; town maps are classified one by one and could use the
  pool with one scenery-source cache per worker.
- World partition packing: 19.5 s at two cores (three partitions); readback 23 s at six cores.
- The cull runs at about 15.8 of 16 cores for most of its 80-90 s: CPU-bound, not idle.

## v0.0.47-dev1 (21 October 2026)

The image step of the v0.0.47-dev1 build (try 2) took 8 min 0 s at 8.4 of 24 cores and lists `underused:image` four
times (longest window 3 min 16 s). The sections under half their cores: finalize 3 min 19 s at 2.95; payload
preflight 16.0 s and 18.5 s at 1.1 (the same disk layout check, twice, each parsing the 694 MB CHIM source manifest:
[BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47](BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47.md), repaired in source); partitions
(all at once) 36.9 s at 1.67 of the 2 tasks it has (the boot partition and the CHIM volume, one disk-tool process
each: inherently serial per image file, the larger one sets the time); harvest 9.2 s at 1.0; actor ground check 9.7 s
at 5.4; the CHIM world read 13.0 s at 5.4 (one pass held for the readers); the entity tracker 7.6 s at 1.7; the media
payload (7,181 files) 3.0 s at 3.9. Perf guard: `bake_body` 137 s against 92 s
([BUILD-BODY-BAKE-SLOWER-44](BUILD-BODY-BAKE-SLOWER-44.md), cause found and repaired in source).

## Where

`tools/build_aga.py` image step.

## How it happened

Guard torch and shared sky conversion write one shared asset archive and were kept serial; the
rest was not yet split into independent pieces.

## Why it was not caught

Per-pass CPU use was first measured by the build profiler.

## Reproduction

The build profile of an image pass (per-pass time and busy CPUs).

## Repair

Not yet: split the shared-archive passes into parallel conversion plus one ordered write, read the
boot drive back in parallel, and find what keeps the cull and the Balmora rebuilds below their
share.

## Verification

`tests/test_hidden_surface_build.py` `test_progress_receipt_writes_are_throttled_and_final_receipt_complete`,
`tests/test_world_volumes_readback.py` `test_sliced_parallel_readback_equals_serial`. Remaining
passes pending; outputs must stay byte-identical to the serial code.

## Prevention

Idle-core warnings in the build profile ([BUILD_PROFILE.md](../BUILD_PROFILE.md)).

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
- [BUILD-IMAGE-STAIR-WALK-SERIAL-36](BUILD-IMAGE-STAIR-WALK-SERIAL-36.md): The image step's stair walk runs one map per worker: a single heavy room keeps one core busy for 13-19 minutes while the others sit idle
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

Related bugs in other categories:

- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread

<!-- END GENERATED CATEGORY -->
