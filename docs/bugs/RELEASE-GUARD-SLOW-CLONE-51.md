# RELEASE-GUARD-SLOW-CLONE-51: The release guard, the fail-fast first step of a release, took 6 minutes on about 0.14 of a core: its release check clones the whole repository through the Windows-mounted drive

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 25 October 2026, in v0.0.51 |
| Where | the release guard's release check container: git clone through a bind mount |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.51, v0.0.66-dev2 (last seen) |
| Severity | medium: The first release step takes minutes instead of seconds, idle on one core; every guard rerun repeats it |
| Family | Build speed (`build-speed`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine d74cc65 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (a release pipeline step on the build host) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-25: reported in v0.0.51
- 2026-11-15 06:12 +0200: seen again in v0.0.66-dev2: Seen again in the v0.0.66-dev2 source step: the release guard took about 15 min on about 0.13 of a core (about 6 min on 0.14 when first reported).

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build speed (`build-speed`). Every stage on the shared worker pool; per-stage time and CPU in the build profile. See [families](README.md#families).

- [ACTOR-CONTACT-NEW-BODY-62](ACTOR-CONTACT-NEW-BODY-62.md): With the v0.0.62 character bake one cave resident (Breves Omoril in Kunirai) no longer fits his floor: the actor placement gate stopped the release build late in the image step
- [AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36](AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36.md): Concurrent master-builder builds oversubscribe the machine: a gate step fails with 'cp: Cannot allocate memory'
- AW-LEASE-DEAD-CONTAINER-54 (no report page): A core lease whose build was killed keeps its cores and memory for 24 hours
- [AW-LEASE-MEMORY-DEADLOCK-36](AW-LEASE-MEMORY-DEADLOCK-36.md): Memory leases deadlocked builds: a 44 GiB build never fit while any gate held its 6 GiB, so builds queued for hours
- [AW-LEASE-NO-GROW-36](AW-LEASE-NO-GROW-36.md): A running build's core lease did not grow back when gates ended, and its worker pools never grow
- AW-QUEUE-DEAD-TICKET-54 (no report page): A requester killed while queued leaves its queue ticket at the head of the strict FIFO: every build machine-wide waited
- [BUILD-ACTOR-LIBRARY-SHARE-RACE-67](BUILD-ACTOR-LIBRARY-SHARE-RACE-67.md): The actor library stage's two pools wrote their worker share through one temporary file name: a write found its file gone
- [BUILD-ACTOR-LIBRARY-UNDERUSED-54](BUILD-ACTOR-LIBRARY-UNDERUSED-54.md): The actor-library stage ran at 2.69 of 8 allowed cores with 130 units queued and 7 running
- [BUILD-AGA-AT-TEXT-LIMIT-60](BUILD-AGA-AT-TEXT-LIMIT-60.md): tools/build_aga.py is 7 bytes under the release text size limit: the next change to it fails the gate unless a stage is split out
- [BUILD-BALMORA-KEY-PALETTE-OVERBROAD-68](BUILD-BALMORA-KEY-PALETTE-OVERBROAD-68.md): A scene palette change re-bakes every Balmora interior room and resident although about half the rooms and all residents come out byte for byte the same
- [BUILD-BODY-BAKE-SLOWER-44](BUILD-BODY-BAKE-SLOWER-44.md): The image step's player body bake ran 42 % slower than its baseline with the same 40 bodies
- [BUILD-CACHE-ABSOLUTE-PATHS-33](BUILD-CACHE-ABSOLUTE-PATHS-33.md): Stage fingerprints contain absolute paths, so a moved workspace or checkout reuses nothing
- [BUILD-CACHE-CHIM-UNITS-33](BUILD-CACHE-CHIM-UNITS-33.md): The chim stage's fingerprint changes whenever the CHIM unit cache gains units, so the stage is never reused
- [BUILD-CACHE-CLOSURE-WIDE-33](BUILD-CACHE-CLOSURE-WIDE-33.md): Stage fingerprints count every module any imported module could import, so unrelated edits rebuild most stages
- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it
- [BUILD-CACHE-OVERBROAD-33](BUILD-CACHE-OVERBROAD-33.md): CHIM builds rerun the scene chain after merges that cannot change its outputs
- [BUILD-CACHE-PER-WORKSPACE-33](BUILD-CACHE-PER-WORKSPACE-33.md): Per-file caches live in each build workspace, so a build on a new volume with --reuse-from converts everything again (MiniWind media 1,195 s instead of seconds)
- [BUILD-CACHE-TRACE-PYTHONPATH-33](BUILD-CACHE-TRACE-PYTHONPATH-33.md): The stage read trace refused reuse of a reused run when another checkout was on PYTHONPATH
- [BUILD-CELL-PROGRESS-UNDECLARED-OUTPUT-67](BUILD-CELL-PROGRESS-UNDECLARED-OUTPUT-67.md): The tracker data stage (cell-progress) writes flora-support.json at the run folder's top, outside its declared outputs, so a later build refuses to reuse the stage
- [BUILD-CENSUS-PHASE-UNDERUSED-68](BUILD-CENSUS-PHASE-UNDERUSED-68.md): A fresh census stage ran on under 4 of 22 cores for about 6 minutes before its worker pool started
- [BUILD-CHECK-ONE-CORE-66](BUILD-CHECK-ONE-CORE-66.md): The build's reuse check runs about six minutes on one core, and every snapshot runs it twice before its build starts
- [BUILD-CHECK-REPEATED-AFTER-PASSED-CHECK-68](BUILD-CHECK-REPEATED-AFTER-PASSED-CHECK-68.md): Before building, the builder checks the plan again even when an identical check passed a few minutes earlier
- [BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46](BUILD-CHIM-CONVERTER-CHANGE-FULL-REBUILD-46.md): A change in the shared collision converter rebuilds every CHIM frame and everything after it, even where the output is identical
- [BUILD-CHIM-FRAME-SWAP-LATE-36](BUILD-CHIM-FRAME-SWAP-LATE-36.md): The image step builds 335 legacy maps of cells already on CHIM, then removes them before packing
- [BUILD-CHIM-KEY-SKY-OVERLAY-TABLE-59](BUILD-CHIM-KEY-SKY-OVERLAY-TABLE-59.md): The CHIM world stage and its ocean units are keyed by the whole sky palette overlay module, so a new image file extension rebuilds the CHIM world
- [BUILD-CHIM-KEY-SOURCE-UNITS-ENV-68](BUILD-CHIM-KEY-SOURCE-UNITS-ENV-68.md): The source catalogue cache of the CHIM areas puts the settings of several unrelated modules into the CHIM world stage's key
- [BUILD-CHIM-MAIN-MEMORY-46](BUILD-CHIM-MAIN-MEMORY-46.md): The CHIM stage main process holds so much memory that the memory guard starves its own workers
- [BUILD-CHIM-POOL-MEMORY-THROTTLE-59](BUILD-CHIM-POOL-MEMORY-THROTTLE-59.md): A CHIM stage rebuild runs its area pool on 8 of 24 workers because the stage's parent and the stages beside it hold most of the build's memory
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
- [BUILD-CHIM-WORLD-POOL-BROKEN-64](BUILD-CHIM-WORLD-POOL-BROKEN-64.md): The first full build with routed standing hulls stopped in the CHIM world step: a converter worker ended abruptly
- [BUILD-CHIM-WORLD-SERIAL-TAIL-41](BUILD-CHIM-WORLD-SERIAL-TAIL-41.md): After the region frames the CHIM world conversion prepared the towns one after another and worked out 723 frames' visibility rows in turn: about 7 minutes on 1 to 5 of 24 cores
- BUILD-DIRECT-START-CELL-LATE-57 (no report page): A MiniWind with --direct-to-game-map cell:X,Y outside its maps fails only in the image step, 12 minutes in
- [BUILD-DOOR-CHECK-LATE-54](BUILD-DOOR-CHECK-LATE-54.md): The door engine check reads only the CHIM world's collision but runs in image finalize, hours into a full build
- [BUILD-DOOR-REFERENCE-SERIAL-33](BUILD-DOOR-REFERENCE-SERIAL-33.md): The door step reads the whole master once per destination cell
- [BUILD-ENGINE-SOURCE-KEY-BROAD-36](BUILD-ENGINE-SOURCE-KEY-BROAD-36.md): Any engine source edit changes the keys of the chim and world-flora stages
- [BUILD-ENV-FINGERPRINT-GLOBAL-33](BUILD-ENV-FINGERPRINT-GLOBAL-33.md): The stair rule setting invalidates the reuse cache of every build stage, including stages that never read it
- [BUILD-ETA-CHIM-STALE-48](BUILD-ETA-CHIM-STALE-48.md): The build ETA said the CHIM world had about 4 minutes left for over 20 minutes while 40 % of its frames remained
- [BUILD-ETA-CLOCK-UTC-ONLY-46](BUILD-ETA-CLOCK-UTC-ONLY-46.md): The build ETA printed its finish time on the container clock (UTC) only: 12:53 read as three hours ago on a +03:00 host
- [BUILD-ETA-FRAME-SCALING-63](BUILD-ETA-FRAME-SCALING-63.md): The build progress scales one-frame test builds up to the whole island: a 34-hour chim estimate
- [BUILD-EXCLUDE-STAGE-CLOSURE-33](BUILD-EXCLUDE-STAGE-CLOSURE-33.md): The quick test build table entered every conversion stage's fingerprint through the stage scheduler
- [BUILD-FIGHTER-BAKE-SLOWER-62](BUILD-FIGHTER-BAKE-SLOWER-62.md): The image step's arena fighter bake took 130 s in the v0.0.62 release build against 44 s before (+198 %) with the same 4 units
- [BUILD-FLORA-FALLBACK-RETRY-35](BUILD-FLORA-FALLBACK-RETRY-35.md): The routed-hull fallback of a flora overlay could not retry: the failed try's candidate folder was looked up from the wrong place
- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-HEAP-GATE-AFTER-STAIRS-46](BUILD-HEAP-GATE-AFTER-STAIRS-46.md): The 12-second CHIM heap gate runs after the two-hour stair walk, so an over-budget frame fails the build late
- [BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md): Scene-chain stages leave most of the workers they hold idle
- [BUILD-IMAGE-AFTER-OPTIMIZER-SERIAL-68](BUILD-IMAGE-AFTER-OPTIMIZER-SERIAL-68.md): After its optimizer check the image step ran on one of 22 cores for more than six minutes, with no named section
- [BUILD-IMAGE-AUDIO-SERIAL-36](BUILD-IMAGE-AUDIO-SERIAL-36.md): The image step puts the audio payload in one file at a time while 22 of 24 cores sit idle
- [BUILD-IMAGE-CHIM-MAPS-SERIAL-36](BUILD-IMAGE-CHIM-MAPS-SERIAL-36.md): The image step writes the CHIM region cells' .chim maps one by one on half a core, silently
- [BUILD-IMAGE-FINALIZE-UNDERUSED-48](BUILD-IMAGE-FINALIZE-UNDERUSED-48.md): The image step ran on about 4 of 24 cores for 85 s after the player view (serial steps, then finalize at 2.6 cores), and the underused warning named no sub-step
- [BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36](BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36.md): The image step's CHIM frame-map heap check runs on one core: 66 s to 4.5 min per build while 23 cores idle
- [BUILD-IMAGE-HASH-UNDERUSED-36](BUILD-IMAGE-HASH-UNDERUSED-36.md): The image step hashes 34,592 payload files on 3 of 24 cores (one file per pool task)
- [BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36](BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36.md): The image step's world map heap audit estimates 170 maps on 5.3 of 24 cores
- [BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66](BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66.md): The image step of the v0.0.66-dev9 build wrote its partitions in 107 seconds where the earlier build took 67
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
- [BUILD-IMAGE-NPC-CHECKS-LATE-44](BUILD-IMAGE-NPC-CHECKS-LATE-44.md): The image step's player body and guard torch bakes fail only at the end of a full build instead of before the expensive stages
- [BUILD-IMAGE-REGION-MAPS-SERIAL-43](BUILD-IMAGE-REGION-MAPS-SERIAL-43.md): The image step's CHIM frame-map phases run on one core: the world read six times, ground traces on whole frames
- [BUILD-IMAGE-SCAN-GROUND-UNDERUSED-52](BUILD-IMAGE-SCAN-GROUND-UNDERUSED-52.md): The image step scans maps on about one core and runs the actor ground check under half the pool
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47](BUILD-IMAGE-SOURCE-MANIFEST-REPARSED-47.md): The image step parses the 694 MB CHIM source manifest three times, on one core each (16.0 s, 18.5 s, 17.1 s)
- [BUILD-IMAGE-STAIR-WALK-CORES-43](BUILD-IMAGE-STAIR-WALK-CORES-43.md): The image step's stair walk used 45 % of its cores in the v0.0.43-dev3 build (95 % before): the perf guard failed its walk_unit section
- [BUILD-IMAGE-STAIR-WALK-SERIAL-36](BUILD-IMAGE-STAIR-WALK-SERIAL-36.md): The image step's stair walk runs one map per worker: a single heavy room keeps one core busy for 13-19 minutes while the others sit idle
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-IMAGE-WORLD-READ-FRAMES-47](BUILD-IMAGE-WORLD-READ-FRAMES-47.md): The image step CHIM world read ran its frame-read pool at 2.96 of 24 cores for 102 s (91 units): perf guard FIX-NOW
- [BUILD-INPUTCHECK-SLOW-32](BUILD-INPUTCHECK-SLOW-32.md): The game data reference check takes over 12 minutes through Docker
- BUILD-INPUTS-LOCK-TMP-RACE-54 (no report page): Two MiniWinds started together race on the input lock: one fixed temp name, so the first build dies at start
- [BUILD-INTERIORS-UNDERUSED-62](BUILD-INTERIORS-UNDERUSED-62.md): The Balmora interiors stage ran at 2.46 of 12 allowed cores with 16 units queued in the v0.0.62 release build
- [BUILD-JOBS-RESOLVE-PER-STAGE-32](BUILD-JOBS-RESOLVE-PER-STAGE-32.md): With automatic jobs, stages of one build plan can get different worker counts
- [BUILD-KIT-SOURCE-COPY-ONE-CORE-67](BUILD-KIT-SOURCE-COPY-ONE-CORE-67.md): The source copy of a release kit writes 4.5 GB on about one core and takes about eighteen minutes
- [BUILD-LARGE-ROOMS-CHECK-LATE-66](BUILD-LARGE-ROOMS-CHECK-LATE-66.md): The large-rooms table check runs about an hour and a half into a build instead of in its first minute
- BUILD-M68K-ICE-SKEL-PARSE-52 (no report page): The m68k compiler crashed on the animation table parse (internal compiler error in patch_jump_insn); the host tests compile it with the host compiler only
- [BUILD-MEMPLAN-CHIM-5-OF-22-68](BUILD-MEMPLAN-CHIM-5-OF-22-68.md): The build's memory plan runs the outdoor world stage on 5 of 22 workers, taking about an hour instead of about half that, because it counts a 25 GB parent process
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33](BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): Every build stage's source fingerprint took in the engine sources through the MiniWind module
- [BUILD-MINIWIND-STAGE-CLOSURE-33](BUILD-MINIWIND-STAGE-CLOSURE-33.md): The MiniWind plan puts the CHIM builder modules into every conversion stage's fingerprint
- [BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md): Pool workers open their own pools sized to the whole stage's allowance
- [BUILD-NEW-WORK-NOT-FIRST-66](BUILD-NEW-WORK-NOT-FIRST-66.md): The builder does not run the work that is new in a build first, so a failure in new content can show hours in
- [BUILD-NO-STALL-ALERT-66](BUILD-NO-STALL-ALERT-66.md): A build reports no progress before its first stage and has no stall alert: an idle or one-core start-up or a stalled stage goes unnoticed unless someone watches the monitor
- [BUILD-NPC-GALLERY-KEY-NEUTRAL-READ-47](BUILD-NPC-GALLERY-KEY-NEUTRAL-READ-47.md): The NPC gallery stage is never reused: making its model keys reads tools/chim/units.py, which the stage key leaves out
- [BUILD-NPC-GALLERY-REBUILT-46](BUILD-NPC-GALLERY-REBUILT-46.md): The NPC gallery (3,551 models, 36 minutes) is rebuilt after a change in collision code that its models do not use
- [BUILD-NPCLOD-PATH-ARG-34](BUILD-NPCLOD-PATH-ARG-34.md): The first --npc-lod on build stopped at its area stage: a Path in the command broke build-state.json
- [BUILD-OPTIMIZER-CACHE-KEY-BROAD-36](BUILD-OPTIMIZER-CACHE-KEY-BROAD-36.md): Regression: the image step's BSP optimizer pass cache reused 13 of 2,658 maps; its key covers the whole image tool, so any image-code change redoes every map
- [BUILD-OPTION-RECORD-KEYS-STAGES-47](BUILD-OPTION-RECORD-KEYS-STAGES-47.md): A new builder option entry rebuilds the CHIM, town, flora, engine and image stages: their keys counted all of config/
- [BUILD-ORDERED-MAP-SCAN-51](BUILD-ORDERED-MAP-SCAN-51.md): The pool map that hands results back in input order scans every held future on each turn: the main process works O(n squared) while large maps run
- [BUILD-ORDERED-WINDOW-33](BUILD-ORDERED-WINDOW-33.md): The ordered worker pool idles behind one slow item, and hands long items out last
- [BUILD-PARTITION-GROWTH-UNGATED-36](BUILD-PARTITION-GROWTH-UNGATED-36.md): Nothing gates the number of world partitions or the growth of the image
- [BUILD-PASS-KEY-TOP-BROAD-43](BUILD-PASS-KEY-TOP-BROAD-43.md): A pass key counts a reached module's whole import-time code: a new constant in chim/models.py rekeyed all 1,295 region frame maps
- [BUILD-PERF-GUARD-BUSY-HOST-CORES-61](BUILD-PERF-GUARD-BUSY-HOST-CORES-61.md): The perf guard fails a build on a lower core share even when it has marked the run as a busy host
- [BUILD-PIPELINE-UNDERUTILIZATION-36](BUILD-PIPELINE-UNDERUTILIZATION-36.md): Umbrella: several builder phases run on one core while the rest of the machine idles, and some do work the build no longer needs
- [BUILD-PLAN-AT-RISK-CASCADE-64](BUILD-PLAN-AT-RISK-CASCADE-64.md): The start-up resource plan counts a stage whose reuse is at risk as reused, so a rebuilt stage that writes different files makes the build run much longer than planned
- BUILD-PLAN-BESIDE-STALE-48 (no report page): The resource plan held a reuse build at 1 of 24 room batch workers against memory that stages it no longer runs held in the measured run
- BUILD-PLAN-HISTORY-ROW-CORRUPT-54 (no report page): The resource plan refuses every 16 GiB build: the mwscript stage is priced at 32,412 MiB from one corrupt history row, while its largest process measured 277 MiB
- [BUILD-PLAN-PESSIMISTIC-48](BUILD-PLAN-PESSIMISTIC-48.md): The start-up resource plan predicts hours for stages that run in minutes: it sums every stage that could run beside one at full speed
- [BUILD-PLAN-UNIT-KEY-UNREADABLE-67](BUILD-PLAN-UNIT-KEY-UNREADABLE-67.md): The build's stage plan cannot read the creature-model unit keys: it prints '? of 97 units (key unreadable)' beside '0 of 97 from the cache'
- [BUILD-PLAYER-VIEW-UNDERUSED-48](BUILD-PLAYER-VIEW-UNDERUSED-48.md): The image step player view remade all 80 player bodies in every build on four fresh worker pools (2m05s at 16.2 of 24 cores)
- [BUILD-PLAYER-VIEW-UNITS-REKEYED-66](BUILD-PLAYER-VIEW-UNITS-REKEYED-66.md): The layer-view unit keys re-keyed every player view unit: the first dev2 build baked all 80 again
- BUILD-POOL-MEMORY-PEAK-48 (no report page): The CHIM and room stages ran side by side at 42 of 44 GiB and were both throttled to one worker for over ten minutes
- BUILD-POOL-TINY-UNITS-48 (no report page): Stages hand their pools units too small to keep the cores busy (CHIM slices, the town stages)
- [BUILD-PREFLIGHT-SERIAL-REPEATED-66](BUILD-PREFLIGHT-SERIAL-REPEATED-66.md): The build's unit reuse preflight runs on one core for about ten minutes, and the build runs it again in full right after its own check did
- [BUILD-PREFLIGHT-SETTING-VALUES-64](BUILD-PREFLIGHT-SETTING-VALUES-64.md): The reuse check counted unit caches by their code digest only: a changed setting value could still bake every unit again after a clean check
- [BUILD-PRERENDERED-PRUNE-ORDER-33](BUILD-PRERENDERED-PRUNE-ORDER-33.md): Prerendered store prune picks the superseded entry by folder name when two entries share a timestamp
- [BUILD-PROFILE-JOBS-START-ONLY-33](BUILD-PROFILE-JOBS-START-ONLY-33.md): The build profile compares a stage's cores with the workers it started with, not the ones it held
- [BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42](BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42.md): The build profiler's sampled timeline counts a finished child process twice
- [BUILD-PROFILE-SECTIONS-MISSING-36](BUILD-PROFILE-SECTIONS-MISSING-36.md): Long builder phases printed no elapsed time and recorded no sections: the chim stage's 44-minute stair gate was visible only from cache file times
- [BUILD-PROFILER-NO-WASTE-ALARM-36](BUILD-PROFILER-NO-WASTE-ALARM-36.md): No profiler, perf ledger or gate flagged idle cores, work done for maps that are removed, or growth of the image
- [BUILD-PROGRESS-ETA-BASIS-36](BUILD-PROGRESS-ETA-BASIS-36.md): The live build progress took a stage's expected time from earlier runs of any size: dev3's chim stage was expected at 154 s and ran 1 h 48 min
- [BUILD-PVS-RECOMPUTE-UNANNOUNCED-64](BUILD-PVS-RECOMPUTE-UNANNOUNCED-64.md): The visibility step of the CHIM world ran almost from scratch after a world-wide hull change, unannounced
- BUILD-PY-TEXT-LIMIT-52 (no report page): tools/build.py is a few bytes under the release text size limit: the next change to it fails the gate unless it is split
- [BUILD-REGION-KEY-NO-LEGACY-64](BUILD-REGION-KEY-NO-LEGACY-64.md): The world flora and scenery region caches lost every stored region when their key changed form
- [BUILD-RESIDENT-BAKE-CPU-18X-67](BUILD-RESIDENT-BAKE-CPU-18X-67.md): The town stages' resident bake costs about 18 to 20 times the CPU per resident of its earlier builds (Vivec: 39 residents at about 140 s each, was 7 s), on the v0.0.67-dev3 line
- [BUILD-RESIDENT-BAKE-SLOWER-52](BUILD-RESIDENT-BAKE-SLOWER-52.md): The skeletal resident bake of the town stages is 74 to 149 % slower than its baseline with the same residents
- [BUILD-RESIDENT-HAIR-SLOWER-54](BUILD-RESIDENT-HAIR-SLOWER-54.md): build_resident ran 87 to 159 percent slower with the same units in the v0.0.54-dev2 town stages
- [BUILD-RESIDENT-KEY-TOOLKIT-PAGE-64](BUILD-RESIDENT-KEY-TOOLKIT-PAGE-64.md): An edit to a Toolkit page changed the key of every baked resident
- [BUILD-RESIDENT-MAP-SLOWER-46](BUILD-RESIDENT-MAP-SLOWER-46.md): The resident-map step of the area and balmora-interiors stages ran 55 to 60 percent slower than its baseline with the same units
- [BUILD-RESOURCE-PLAN-CHIM-ESTIMATE-44](BUILD-RESOURCE-PLAN-CHIM-ESTIMATE-44.md): The resource plan estimated the CHIM stage at 2 workers and 6 h 13 min; it ran on 24 workers in about 75 min
- [BUILD-RESOURCE-PLAN-MINIWIND-FULL-PARENT-52](BUILD-RESOURCE-PLAN-MINIWIND-FULL-PARENT-52.md): A MiniWind build is refused by the resource plan: its one-area CHIM stage is estimated from the full build's island-wide chim parent (19,868 MiB) and labelled a stair walk although the walk is off
- [BUILD-RESOURCE-PLAN-UNIT-REUSE-66](BUILD-RESOURCE-PLAN-UNIT-REUSE-66.md): The build's resource plan estimates the wall time as if every unit cache held, while the reuse guard finds them all stale
- [BUILD-REUSE-APPLY-SERIAL-41](BUILD-REUSE-APPLY-SERIAL-41.md): A reused stage staged its files one at a time: world terrain, scenery and flora took 8 to 12 seconds each, one after another, at the start of every reuse build
- [BUILD-REUSE-CHECK-ONE-CORE-59](BUILD-REUSE-CHECK-ONE-CORE-59.md): The reuse check phase runs on one core for several minutes on every full build
- [BUILD-REUSE-KEYS-TOO-BROAD-35](BUILD-REUSE-KEYS-TOO-BROAD-35.md): A whole build reused no stage, and the cost was not visible before the build started
- [BUILD-REUSE-STOP-WHOLE-STAGE-64](BUILD-REUSE-STOP-WHOLE-STAGE-64.md): The reuse preflight lets a long stage run again in full without a stop when its key changed
- [BUILD-REUSE-TMP-UNDECLARED-33](BUILD-REUSE-TMP-UNDECLARED-33.md): A stage that runs while a reused stage is copied becomes non-reusable
- [BUILD-REUSE-VERIFY-DISK-48](BUILD-REUSE-VERIFY-DISK-48.md): Reusing the chim stage reads and hashes all 9.35 GB of its outputs again: 78 s at 1.7 of 11 cores, counted as an underused stage
- [BUILD-ROOM-ACTOR-KEY-SWITCH-64](BUILD-ROOM-ACTOR-KEY-SWITCH-64.md): The image step fitted all 2,342 room residents again: the room-actor cache key moved and the reuse preflight did not see that cache
- [BUILD-ROOM-BATCHES-UNDERUSED-54](BUILD-ROOM-BATCHES-UNDERUSED-54.md): The chim-room-batches stage ran 43.5 minutes at 9 of 24 cores in the v0.0.54-dev2 full build
- [BUILD-SCHEDULER-EVEN-SHARE-33](BUILD-SCHEDULER-EVEN-SHARE-33.md): The stage scheduler splits the workers evenly between running stages, so the longest stage gets no more than the shortest (MiniWind media on 1 of 4 workers for 1,195 s)
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts
- [BUILD-SCHEDULER-LOWBUDGET-33](BUILD-SCHEDULER-LOWBUDGET-33.md): With a small --jobs budget the stage scheduler starts nothing when more branches are ready than the budget (busy loop)
- [BUILD-SCHEDULER-MEMORY-STARVED-42](BUILD-SCHEDULER-MEMORY-STARVED-42.md): The scheduler's memory guard held the v0.0.42 final's chim stage on 1 of its 6 workers for over an hour, and nothing said so before or while it happened
- [BUILD-SETUP-ONE-CORE-66](BUILD-SETUP-ONE-CORE-66.md): A full build spends about five minutes on one core before its first stage starts
- BUILD-SEYDA-BSP-CARRIER-48 (no report page): Stages pass data through a legacy map file: seyda.bsp's entities and compiled room.bsp files carry what JSON could
- [BUILD-SEYDA-ENTITY-BUS-48](BUILD-SEYDA-ENTITY-BUS-48.md): Four scene stages still pass Seyda Neen's entities through the seyda.bsp carrier's entity lump
- [BUILD-SILENT-PHASES-36](BUILD-SILENT-PHASES-36.md): Builder phases run silent: no start/end timing, no progress, no heartbeat; the CHIM stats step is a single-core tail
- [BUILD-SIZE-GUARD-LATE-48](BUILD-SIZE-GUARD-LATE-48.md): The size guard judges only after the image is built: an rc that grew for a known reason stops after 32 minutes of image work, and the rerun assembles the whole image again
- [BUILD-SIZE-GUARD-OLD-BASELINE-45](BUILD-SIZE-GUARD-OLD-BASELINE-45.md): The size guard compared a release build with an older release's record: v0.0.45, every folder the size of v0.0.44's, failed on 0.44 GiB of CHIM world growth against v0.0.41
- [BUILD-STAGE-ALLOWANCE-STUCK-43](BUILD-STAGE-ALLOWANCE-STUCK-43.md): A build stage's worker allowance stays at 1 after the other stages finish, so the CHIM stage runs on one core
- [BUILD-STAGE-INTERRUPT-ABSORBED-36](BUILD-STAGE-INTERRUPT-ABSORBED-36.md): The stage wrapper absorbed Ctrl-C: a stage that handled the interrupt and returned 0 counted as passed, and the build went on
- [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md): A pooled stage that starts while others run gets one worker as its start value
- [BUILD-STAIR-GATE-OOM-42](BUILD-STAIR-GATE-OOM-42.md): The CHIM stair gate runs a whole-Vivec MiniWind out of memory: its worker pool breaks
- [BUILD-STAIR-MESH-UNIT-SLOW-67](BUILD-STAIR-MESH-UNIT-SLOW-67.md): One stair collision unit of a Mournhold district model takes 8 to 12 minutes on one core
- [BUILD-STAIR-WALK-BORDER-COPIES-41](BUILD-STAIR-WALK-BORDER-COPIES-41.md): The CHIM stair gate walks every frame's whole border, so each cell's flights are walked many times and unreachable copies can fail a build
- [BUILD-STAIR-WALK-OFF-46](BUILD-STAIR-WALK-OFF-46.md): Every build walked the island stairs (about 1.5 million steps per release cycle); the stair walk is now off by default
- [BUILD-STAIR-WALK-SCOPE-KEY-46](BUILD-STAIR-WALK-SCOPE-KEY-46.md): Development builds walk every step of the island again after any collision change: the CHIM gate ignored the walk scope and keyed each frame by all of its collision
- [BUILD-STAIR-WALK-SLOW-33](BUILD-STAIR-WALK-SLOW-33.md): The image step's stair walk spent most of its time in interpreted collision traces and brute-force headroom tests (1,751 s of the rc1c image step)
- [BUILD-STATS-SERIAL-36](BUILD-STATS-SERIAL-36.md): The CHIM stats step runs serially and silently on one core
- [BUILD-STORAGE-DUPLICATES-33](BUILD-STORAGE-DUPLICATES-33.md): Build storage keeps full duplicate copies of images, stage outputs and packages, and nothing removes them
- [BUILD-TESTER-32GB-OOM-67](BUILD-TESTER-32GB-OOM-67.md): A tester's build on a machine with 32 GB of memory ran out of memory after about 32 hours
- [BUILD-TOWN-ACTOR-FIT-SERIAL-64](BUILD-TOWN-ACTOR-FIT-SERIAL-64.md): The Vivec town stage fits its residents onto the frame collision on one core after the resident bake
- [BUILD-UNDERUSE-GATE-36](BUILD-UNDERUSE-GATE-36.md): The profiler did not flag long underused phases: 7 min 44 s of CHIM statistics on 1 of 24 cores and 77 s of zone walk on 1 core showed nowhere
- [BUILD-UNIT-KEYS-REACH-64](BUILD-UNIT-KEYS-REACH-64.md): New collision settings re-keyed the NPC, creature, player-body and resident unit caches, which never read them
- [BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md): Docker builds and disk-image steps on Windows folders are slow
- [CHIM-BUDGET-RERUN-SERIAL-48](CHIM-BUDGET-RERUN-SERIAL-48.md): When one CHIM unit is over the brush image budget, every unit of its kind runs again one by one on one core to name it
- [CHIM-EMPTY-MODEL-REPORT-40](CHIM-EMPTY-MODEL-REPORT-40.md): Terrain-only CHIM validation crashes while reporting the largest scenery model
- [CHIM-INTERIORS-UNDERUSED-48](CHIM-INTERIORS-UNDERUSED-48.md): The CHIM interiors stage ran at 8.6 of 24 cores for 1 min 11 s
- [CHIM-LEGACY-CHAIN-33](CHIM-LEGACY-CHAIN-33.md): CHIM builds still run the legacy exterior chain: frame maps read the legacy region maps, and the open world is built
- [CHIM-MESH-STAIR-UNIT-SLOW-67](CHIM-MESH-STAIR-UNIT-SLOW-67.md): One stair collision unit of a Solstheim glacier cell takes 19.5 minutes on one core, and its second over 25
- [CHIM-PVS-SLOW-33](CHIM-PVS-SLOW-33.md): Seyda Neen's CHIM visibility rows take 5.5 minutes and are rebuilt whenever the worker count changes
- [CHIM-REBUILD-NOT-IDENTICAL-68](CHIM-REBUILD-NOT-IDENTICAL-68.md): The CHIM world rebuilt from unchanged inputs wrote files that differ from the cached build, so the stages after it ran again
- [CHIM-ROOM-FAIL-STAGE-48](CHIM-ROOM-FAIL-STAGE-48.md): One CHIM room that cannot be made failed the whole CHIM interiors stage (HOLD-LEVEL with every room batch by default)
- [CHIM-ROOM-OVER-BUDGET-RETRY-48](CHIM-ROOM-OVER-BUDGET-RETRY-48.md): A model over the image budget is tried whole again on every run before its cached tiles are used: its room runs on one core
- [CHIM-SOL-FLORA-PATH-64](CHIM-SOL-FLORA-PATH-64.md): The Solstheim test frame converts its trees as full models, not through the world flora cards Vvardenfell uses
- [CHIM-STAIR-GATE-WORLD-RELOAD-36](CHIM-STAIR-GATE-WORLD-RELOAD-36.md): The CHIM stair gate's workers read the whole CHIM world again every time they switch frames (about 14.5 s per read on the 273-frame world)
- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world
- [EXPANSION-READER-ONE-MASTER-64](EXPANSION-READER-ONE-MASTER-64.md): Most builder readers load only the base game file; the roadmap calls the readers master-list readers
- [GATE-IMAGE-REMOVED-52](GATE-IMAGE-REMOVED-52.md): A cleanup removed the image the gate s Linux host-parity step runs: the in-use check looked at containers only
- [GATE-PRIVACY-NOT-IN-PREGATE-52](GATE-PRIVACY-NOT-IN-PREGATE-52.md): The privacy word check runs only in the full gate: the quick pre-gate checks passed text the gate then refused
- [GUARD-TORCH-SCRATCH-SERIAL-67](GUARD-TORCH-SCRATCH-SERIAL-67.md): From scratch, the guard torch step bakes the six boat guard models one after another only to skip every one of them
- [HARVEST-CHIM-COVERAGE-ONE-AREA-48](HARVEST-CHIM-COVERAGE-ONE-AREA-48.md): The image step harvest coverage check failed on every CHIM world of one area (every MiniWind sandbox of one town)
- [IMAGE-BIGGER-THAN-ORIGINAL-62](IMAGE-BIGGER-THAN-ORIGINAL-62.md): The game image (3,022 MB in v0.0.62) is bigger than the original game data it is made from (1.93 GB)
- [IMAGE-FORMAT-EFFECTS-AWE-66](IMAGE-FORMAT-EFFECTS-AWE-66.md): The image step's format check did not know the active-effect icon file, and stopped the build at its end
- [IMAGE-GUARD-TORCHES-SLOW-66](IMAGE-GUARD-TORCHES-SLOW-66.md): The image step's torch guards bake took 3.4 times as long, and the step ran on under half its cores
- [IMAGE-ROOM-ACTOR-BAKE-REFIT-66](IMAGE-ROOM-ACTOR-BAKE-REFIT-66.md): The image step's CHIM room actor bake fitted all 2,594 room residents again in the v0.0.66-dev3 build, where the v0.0.66-dev2 run had every one of them cached
- [IMAGE-ROOM-HEAP-ONE-CORE-66](IMAGE-ROOM-HEAP-ONE-CORE-66.md): The image step's room heap check measures every room on one core
- [IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66](IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66.md): The image step's CHIM room actor bake takes about two minutes on one core when every room resident is already cached
- [IMAGE-TORCHES-GUARD-3X-BASELINE-68](IMAGE-TORCHES-GUARD-3X-BASELINE-68.md): The image step's torch check takes about three times its recorded time with the same six units
- [MINIWIND-NO-INTERIOR-SCOPE-42](MINIWIND-NO-INTERIOR-SCOPE-42.md): A MiniWind of one room built the whole town: no scope converted only the start room
- [MINIWIND-NOT-MINUTES-33](MINIWIND-NOT-MINUTES-33.md): A reused MiniWind build took about two hours instead of minutes
- [MINIWIND-NPCS-ONE-WORKER-64](MINIWIND-NPCS-ONE-WORKER-64.md): The npcs stage of a MiniWind sandbox build runs alone on 1 of its 8 workers
- [MINIWIND-SCENE-CHAIN-WEIGHT-42](MINIWIND-SCENE-CHAIN-WEIGHT-42.md): Every MiniWind bakes all playable races and the opening rooms, and walks its whole frame stairs
- [NPC-BAKE-STAGES-OVERRUN-62](NPC-BAKE-STAGES-OVERRUN-62.md): The new seam and floor character bake made every stage that bakes characters run far past its history: room batches about 2 h 40 min, actor library about 40 min, player bodies 35+ min
- [NPC-BAKED-WHOLE-DUPLICATION-33](NPC-BAKED-WHOLE-DUPLICATION-33.md): Every NPC appearance is baked whole: shared body parts are converted again for each actor, and equipment cannot change
- [NPC-LIBRARY-NO-UNIT-CACHE-63](NPC-LIBRARY-NO-UNIT-CACHE-63.md): The NPC appearance bakes of the actor library stage had no unit cache, so every rebuild of the stage baked all 418 appearances again (about 45 minutes)
- [PARTITION-CACHE-FIXED-WORKERS-66](PARTITION-CACHE-FIXED-WORKERS-66.md): The new partition cache hashed its files on a fixed eight threads instead of the stage's own allowance
- [PERF-DB-FOLDER-CONFLICT-67](PERF-DB-FOLDER-CONFLICT-67.md): A folder ingest of the performance database stops at the first changed file
- [PERF-GUARD-BASIS-BY-COUNT-66](PERF-GUARD-BASIS-BY-COUNT-66.md): The performance guard judges the image step's partition write by the number of partitions and not by their size, so a slowdown back to the old time would pass
- [PERF-GUARD-RESIDENT-BUSY-HOST-57](PERF-GUARD-RESIDENT-BUSY-HOST-57.md): The dev5 full build's perf guard failed chim-town-balmora and chim-town-vivec_city build_resident as slower (129 s, was 52 s; 147 s, was 62 s) while two other builds ran beside it: contention, not code
- [PLAYER-VIEW-SKIN-ROWS-STOP-62](PLAYER-VIEW-SKIN-ROWS-STOP-62.md): The image step's player view stopped the v0.0.62 final build after 1 h 13 min: an Alias skin rows overflow ended it instead of trying the next smaller body
- RELEASE-SUITE-RECORD-SERIAL-51 (no report page): The release's suite record runs the whole test suite again on one core for about 22 minutes, right after the gate ran the same tests in about 2 minutes
- [REUSE-POOL-LINK-LIMIT-68](REUSE-POOL-LINK-LIMIT-68.md): A stage's reuse was refused because one shared file had reached the file system's hard link limit, so the whole CHIM world stage was rebuilt
- [REUSE-VERIFY-SLOW-BESIDE-MODULE-STAGES-68](REUSE-VERIFY-SLOW-BESIDE-MODULE-STAGES-68.md): Reusing the room batches of an earlier build took about 37 seconds where earlier reuses took 5
- [ROOM-BAKE-FOOTPRINT-SLOW-48](ROOM-BAKE-FOOTPRINT-SLOW-48.md): The room actor bake's footprint rule with the collision-box test is more than 100 times slower
- [ROOM-BATCH-CORES-49](ROOM-BATCH-CORES-49.md): The room batches stage ran on about two of its eight cores for minutes before its first room, and kept few of its finished rooms when stopped
- ROOM-RESIDENTS-KEY-SERIAL-49 (no report page): The room residents step opens its unit cache once per resident: 233 s on one core before any cached resident is restored
- [SHELL-ORPHAN-STARVES-GATE-66](SHELL-ORPHAN-STARVES-GATE-66.md): A leftover process in the shell container starved a gate; nothing in the master builder noticed the stall
- [SOL-MODULE-CONVERSION-HALF-CORES-68](SOL-MODULE-CONVERSION-HALF-CORES-68.md): Solstheim's world stage converted on about half of its cores
- [SOL-STAGE-ASSEMBLY-SERIAL-68](SOL-STAGE-ASSEMBLY-SERIAL-68.md): The Solstheim stage, rebuilt with every CHIM unit taken from the cache, spends about six minutes of its world assembly on one core
- [STALL-SLOW-STAGE-VS-REUSE-TIME-68](STALL-SLOW-STAGE-VS-REUSE-TIME-68.md): The builder's slow-stage warning compared a stage that had to run with the few seconds an earlier build took to reuse it, and so called a normal run eight times too slow
- [STALL-ZERO-CORES-WHILE-POOLS-BUSY-68](STALL-ZERO-CORES-WHILE-POOLS-BUSY-68.md): The build's stall check reported no cores in use while a stage's worker pools were running
- [UNIT-CACHE-STORE-ERRORS-SILENT-63](UNIT-CACHE-STORE-ERRORS-SILENT-63.md): A unit that the unit cache failed to store was reported as stored: a cache folder the build user could not write lost every unit without a word
- [UNIT-KEY-WHOLE-FILE-63](UNIT-KEY-WHOLE-FILE-63.md): The resident and room unit caches keyed every unit on the whole of their tool files, so an unrelated edit to tools/prepare_area.py re-keyed all 1,769 residents and every room, and the v0.0.63-dev1 build baked them all again
- [UNIT-STORED-AT-MAP-END-62](UNIT-STORED-AT-MAP-END-62.md): The image step's player view stored its finished bodies only when its whole pool map ended: a step stopped midway kept none of them, so every resume baked every player body again

<!-- END GENERATED CATEGORY -->
