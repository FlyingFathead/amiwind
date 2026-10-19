# BUILD-REUSE-KEYS-TOO-BROAD-35: A whole build reused no stage, and the cost was not visible before the build started

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 6 times; something has to be done

- Reported with v0.0.35-dev1 at 2026-10-10 (time not recorded): BUILD-REUSE-KEYS-TOO-BROAD-35: a whole build reused no stage
- Reported with v0.0.36-dev3 at 2026-10-11 00:43 +0300: optimizer pass cache reused 13 of 2,658 maps
- Reported with v0.0.41-dev2 at 2026-10-16 02:28 +0300: chim stage rebuilt (~24 min) for aw_ui.c + debug-commands.txt
- Reported with v0.0.42-dev1 at 2026-10-17 01:10 +0300: fixlist B7: keys still count everything a stage can reach; rc1 traces: a model-reader edit keys 18 stages, 11 ran it; the HUD source keys 8, 1 opened it
- Reported with v0.0.42-dev1 at 2026-10-17 02:37 +0300: easy CHIMport batch vs the v0.0.41 run: 1 of 39 stages reusable; the pool file is in 36 stage keys
- Reported with v0.0.42-dev2 at 2026-10-17 13:10 +0300: config/actor_grounding.json is a whole input of 8 town stages: 6 NPCs added outside those towns rebuild them (reuse 31 -> 24 of 38)

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 10 October 2026, in v0.0.35-dev1 |
| Where | Stage reuse planning and the NPC gallery model cache key (tools/build_cache.py, gallery_cache.py) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.35-dev1 (last seen) |
| Severity | medium: A build after a large merge reran every stage with no warning before it started, and the gallery model cache key left out modules its converter runs. |
| Family | Build speed (`build-speed`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 901f8e9 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [PERSISTING: reported 6 times; something has to be done](#persisting-reported-6-times-something-has-to-be-done)
- [Status: 10 October 2026](#status-10-october-2026)
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

## Status: 10 October 2026

Repair in v0.0.35 development (not shipped).

## Symptom

The first v0.0.35 development build (source 901f8e9) ran with `--reuse-from` the v0.0.34 build and
`--reuse-mode pool`. It reused 0 of 35 stages, and the per-model NPC gallery cache reused 0 of 3,551
models. The build did not say so before it started: the per-stage reasons appeared only in
`build-state.json`, and the build log printed one rebuild line per stage with no summary.

## Where

- `tools/build_cache.py` and `tools/build.py`: no check of the reuse plan before the first stage, and
  no loud warning when (almost) nothing is reused.
- `tools/gallery_cache.py`: each gallery model's key held the whole-file SHA-256 of a fixed list of six
  source files.

## How it happened

Measured against the two runs' recorded fingerprints: every stage's own key changed, not only through
the stages it depends on. Sources changed in 35 of 35 stages (105 changed files from twelve merged
branches; the reached code of the converters changed, e.g. a new shared data-reader helper in
`src/mwad/esm.py` that every reader calls). Game inputs changed in 28 stages: the input lock now
lists the Tribunal and Bloodmoon masters and archives (the data-reader fixes widened what counts as a
game input). Environment changed in 21 stages: new settings (lava, the NPC root rule, the stair walk)
that new code reads. Every one of these is a real input change, so no stage could safely be reused,
and the early cutoff that already exists (BUILD-CACHE-NO-CUTOFF-33: a stage whose own key is
unchanged is reused when the stages before it write the same outputs again) had nothing to work on.

The gallery model key had two faults. It was too broad: an edit anywhere in `src/mwad/audit.py` or
`src/mwad/paths.py` changed every model's key, even where the converter never runs the edited code.
It was also too narrow: it left out modules the converter does run (`src/mwad/esm.py`,
`src/mwad/npc.py`, `tools/nif_common.py` and others), so an edit made only there would have reused
stale models.

## Why it was not caught

The reuse audit (`tools/reuse_report.py`) runs after a build. Nothing compared the plan with the
source diff before the expensive stages started. The gallery key was a hand-written file list with no
test against the converter's real reach.

## Reproduction

`tools/build.py --reuse-plan OLD_RUN` with a checkout that differs from OLD_RUN's source in a shared
data-reader module: every stage is listed as rebuilt, each with the changed files that touch it.

## Repair

- Reuse preflight (`tools/reuse_report.py` `preflight`, run by `tools/build_cache.py` `prepare`):
  with `--reuse-from`, before any stage runs, the builder compares the reuse source's recorded source
  tree (`source_sha256` in its `build-state.json`) with the checkout, then prints every stage that is
  not reused, its reason and the changed files that touch it. If a stage would be rebuilt for a source
  key change that no changed file explains, or only for files no output can depend on, the build stops
  before the first stage. `--accept-rebuild` builds anyway, and says so. A plan that reuses nothing,
  or less than half of the reusable stages, prints a "check" line.
- `tools/build.py --reuse-plan OLD_RUN` runs the same preflight alone. It is read only, reads no game
  data and takes about 10 seconds.
- Gallery model key (`tools/gallery_cache.py` `converter_sources`): the code the converter can reach
  from `tools/prepare_gallery.py`, scope `units` (the same reach analysis as the stage fingerprints),
  plus the data files that code names. The rc9 seed import keeps the file list it compared before.
  The key format changes once, so the gallery models are converted once more on the first build with
  this change.

## Verification

- `tests/test_reuse_report.py`: rebuilds explained by the source diff or by a real input change are
  EXPECTED and list the changed files; a source key that changed with no file changed is UNEXPECTED
  and stops the build; a plan that reuses nothing is loud.
- `tests/test_build_cache.py`: the preflight stops a build before any stage runs, `--accept-rebuild`
  continues, `--reuse-plan` gives the same verdict, and a real edit is explained and named. The
  existing early-cutoff tests (identical outputs keep later stages; changed outputs rebuild them) still
  pass.
- `tests/test_gallery_cache.py`: a model key keeps its value for an unreached edit, changes for a
  reached edit in a module the old list never named, and covers the converter's real modules.
- The preflight against the real v0.0.34 run and source 901f8e9: 0 of 35 stages reused, 2 by policy,
  0 unexplained (every rebuild names its changed files).

## Prevention

The preflight runs on every build with `--reuse-from`, so the cost of a change is visible before any
stage runs, and a key that is too broad stops the build. The gallery key is derived from the code
the converter reaches, not maintained by hand.

### PERSISTING: v0.0.41-dev2, 16 October 2026

The rings 0-2 build at 427e29b reran the whole chim stage (about 24 minutes on 12 workers) and the three CHIM town
stages after it. The reuse plan named the cause itself: "input change: sources (config/debug-commands.txt,
engine/aga/src/aw_ui.c)". Those are the HUD code (the Guard marker) and the debug command catalogue; the CHIM world
conversion reads neither. The plan marked the rebuild EXPECTED, so the preflight did not stop it. Repair: the chim
stage's key covers only the files the conversion reads, with a test that a HUD or debug-catalogue change does not
rebuild it; the preflight should flag a source in a key that the stage never opens.

### PERSISTING: v0.0.42-dev1, 17 October 2026 (fixlist B7)

Still persisting in the v0.0.41 builder: a key counts everything a stage's code can reach. On the read traces of
the v0.0.39-rc1 build (all 40 stages traced): an edit to `prepare_scenery._read_model` keys 18 stages, 11 ran it
(the NPC gallery, the CHIM towns and the image did not); `engine/aga/src/aw_ui.c` keys 8 stages, only the engine
opened it; `config/debug-commands.txt` keys 2 and no Python stage opened it; `mwad.audit.audit` keys 5, 2 ran it.

Repair in source on v0.0.42-build-cores (not shipped): every stage that runs records what it really used
(functions and module tops by the SHA-256 of their text, files read, folders listed; trace form 2 also lists the
processes a stage starts), and a later key that differs only in its sources reuses the stage when everything in
the record is unchanged (docs/BUILD_CACHE.md "Narrowed reuse"). A record is incomplete, and the whole key is
compared, when a Python process ran without the trace, a program was given a checkout path (the engine's
compiler) or code came from outside the checkout. The 16 October example: `mesh_geometry.collision_pieces` ran in
the Balmora interiors stage, so that rerun stays (the early cutoff keeps the stages after it when its outputs come
out the same). Takes effect from the first build that runs a stage with this builder (older runs have no records).
Tests: `tests/test_build_cache.py` `NarrowedReuseTests`.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Build speed (`build-speed`). Every stage on the shared worker pool; per-stage time and CPU in the build profile. See [families](README.md#families).

- [AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36](AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36.md): Concurrent master-builder builds oversubscribe the machine: a gate step fails with 'cp: Cannot allocate memory'
- [AW-LEASE-MEMORY-DEADLOCK-36](AW-LEASE-MEMORY-DEADLOCK-36.md): Memory leases deadlocked builds: a 44 GiB build never fit while any gate held its 6 GiB, so builds queued for hours
- [AW-LEASE-NO-GROW-36](AW-LEASE-NO-GROW-36.md): A running build's core lease did not grow back when gates ended, and its worker pools never grow
- [BUILD-CACHE-ABSOLUTE-PATHS-33](BUILD-CACHE-ABSOLUTE-PATHS-33.md): Stage fingerprints contain absolute paths, so a moved workspace or checkout reuses nothing
- [BUILD-CACHE-CHIM-UNITS-33](BUILD-CACHE-CHIM-UNITS-33.md): The chim stage's fingerprint changes whenever the CHIM unit cache gains units, so the stage is never reused
- [BUILD-CACHE-CLOSURE-WIDE-33](BUILD-CACHE-CLOSURE-WIDE-33.md): Stage fingerprints count every module any imported module could import, so unrelated edits rebuild most stages
- [BUILD-CACHE-NO-CUTOFF-33](BUILD-CACHE-NO-CUTOFF-33.md): A rebuilt stage whose outputs come out unchanged still rebuilds every stage after it
- [BUILD-CACHE-OVERBROAD-33](BUILD-CACHE-OVERBROAD-33.md): CHIM builds rerun the scene chain after merges that cannot change its outputs
- [BUILD-CACHE-PER-WORKSPACE-33](BUILD-CACHE-PER-WORKSPACE-33.md): Per-file caches live in each build workspace, so a build on a new volume with --reuse-from converts everything again (MiniWind media 1,195 s instead of seconds)
- [BUILD-CACHE-TRACE-PYTHONPATH-33](BUILD-CACHE-TRACE-PYTHONPATH-33.md): The stage read trace refused reuse of a reused run when another checkout was on PYTHONPATH
- [BUILD-CHIM-FRAME-SWAP-LATE-36](BUILD-CHIM-FRAME-SWAP-LATE-36.md): The image step builds 335 legacy maps of cells already on CHIM, then removes them before packing
- [BUILD-CHIM-REGION-FRAMES-TAIL-43](BUILD-CHIM-REGION-FRAMES-TAIL-43.md): The CHIM region-frame step runs its last frames on one worker while the other cores sit idle
- [BUILD-CHIM-SOURCE-REPEAT-41](BUILD-CHIM-SOURCE-REPEAT-41.md): The CHIM stage parsed the whole master and read the same models again for every area: 723 source stages took 24,500 CPU seconds
- [BUILD-CHIM-STAGE-IDLE-START-36](BUILD-CHIM-STAGE-IDLE-START-36.md): The chim stage of the 270-frame coast build spends its first 35-45 minutes on 1-4 cores while it holds 12-24 workers
- [BUILD-CHIM-STAGE-SERIAL-TAIL-36](BUILD-CHIM-STAGE-SERIAL-TAIL-36.md): After the parallel world build the chim stage ran its validation, heap gate and zone walk on one core (about 10 minutes of the 270-frame coast build)
- [BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42](BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42.md): In-stage pools of the CHIM step stay at the --jobs the stage was launched with: the v0.0.42 final's stair gate walked on 2 workers with an allowance of 12
- [BUILD-CHIM-STAIR-NO-REUSE-42](BUILD-CHIM-STAIR-NO-REUSE-42.md): The v0.0.42 final walked all 1,118 frames again: the walks of the passed dev1 build carry no check mark, because its launcher never promotes them
- [BUILD-CHIM-STATS-SERIAL-TAIL-36](BUILD-CHIM-STATS-SERIAL-TAIL-36.md): The chim stage ended with its statistics validating the whole CHIM world a second time, on one core with no output (7 min 44 s on 273 frames)
- [BUILD-CHIM-UNIT-HULL-KEY-33](BUILD-CHIM-UNIT-HULL-KEY-33.md): CHIM unit cache ignores the standing-hull form: a --model-hull chain build reused routed-hull model units
- [BUILD-CHIM-VIS-ROWS-SERIAL-42](BUILD-CHIM-VIS-ROWS-SERIAL-42.md): The CHIM visibility rows of a build with many new frames run on one worker at a time and print nothing for half an hour or more
- [BUILD-CHIM-WORLD-SERIAL-TAIL-41](BUILD-CHIM-WORLD-SERIAL-TAIL-41.md): After the region frames the CHIM world conversion prepared the towns one after another and worked out 723 frames' visibility rows in turn: about 7 minutes on 1 to 5 of 24 cores
- [BUILD-DOOR-REFERENCE-SERIAL-33](BUILD-DOOR-REFERENCE-SERIAL-33.md): The door step reads the whole master once per destination cell
- [BUILD-ENGINE-SOURCE-KEY-BROAD-36](BUILD-ENGINE-SOURCE-KEY-BROAD-36.md): Any engine source edit changes the keys of the chim and world-flora stages
- [BUILD-ENV-FINGERPRINT-GLOBAL-33](BUILD-ENV-FINGERPRINT-GLOBAL-33.md): The stair rule setting invalidates the reuse cache of every build stage, including stages that never read it
- [BUILD-EXCLUDE-STAGE-CLOSURE-33](BUILD-EXCLUDE-STAGE-CLOSURE-33.md): The quick test build table entered every conversion stage's fingerprint through the stage scheduler
- [BUILD-FLORA-FALLBACK-RETRY-35](BUILD-FLORA-FALLBACK-RETRY-35.md): The routed-hull fallback of a flora overlay could not retry: the failed try's candidate folder was looked up from the wrong place
- [BUILD-HAND-CATALOG-SERIAL-32](BUILD-HAND-CATALOG-SERIAL-32.md): The hand-catalog stage bakes every race and sex one after another
- [BUILD-IDLE-STAGES-33](BUILD-IDLE-STAGES-33.md): Scene-chain stages leave most of the workers they hold idle
- [BUILD-IMAGE-AUDIO-SERIAL-36](BUILD-IMAGE-AUDIO-SERIAL-36.md): The image step puts the audio payload in one file at a time while 22 of 24 cores sit idle
- [BUILD-IMAGE-CHIM-MAPS-SERIAL-36](BUILD-IMAGE-CHIM-MAPS-SERIAL-36.md): The image step writes the CHIM region cells' .chim maps one by one on half a core, silently
- [BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36](BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36.md): The image step's CHIM frame-map heap check runs on one core: 66 s to 4.5 min per build while 23 cores idle
- [BUILD-IMAGE-HASH-UNDERUSED-36](BUILD-IMAGE-HASH-UNDERUSED-36.md): The image step hashes 34,592 payload files on 3 of 24 cores (one file per pool task)
- [BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36](BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36.md): The image step's world map heap audit estimates 170 maps on 5.3 of 24 cores
- [BUILD-IMAGE-NOT-INCREMENTAL-33](BUILD-IMAGE-NOT-INCREMENTAL-33.md): The image step redoes every per-map pass and the whole pack on every build
- [BUILD-IMAGE-REGION-MAPS-SERIAL-43](BUILD-IMAGE-REGION-MAPS-SERIAL-43.md): The image step's CHIM frame-map phases run on one core: the world read six times, ground traces on whole frames
- [BUILD-IMAGE-SERIAL-32](BUILD-IMAGE-SERIAL-32.md): The image step runs on one core for about 23 minutes per pass
- [BUILD-IMAGE-STAIR-WALK-CORES-43](BUILD-IMAGE-STAIR-WALK-CORES-43.md): The image step's stair walk used 45 % of its cores in the v0.0.43-dev3 build (95 % before): the perf guard failed its walk_unit section
- [BUILD-IMAGE-STAIR-WALK-SERIAL-36](BUILD-IMAGE-STAIR-WALK-SERIAL-36.md): The image step's stair walk runs one map per worker: a single heavy room keeps one core busy for 13-19 minutes while the others sit idle
- [BUILD-IMAGE-UNDERUSED-32](BUILD-IMAGE-UNDERUSED-32.md): Parts of the image step still run serially or leave most CPUs idle
- [BUILD-INPUTCHECK-SLOW-32](BUILD-INPUTCHECK-SLOW-32.md): The game data reference check takes over 12 minutes through Docker
- [BUILD-JOBS-RESOLVE-PER-STAGE-32](BUILD-JOBS-RESOLVE-PER-STAGE-32.md): With automatic jobs, stages of one build plan can get different worker counts
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33](BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): Every build stage's source fingerprint took in the engine sources through the MiniWind module
- [BUILD-MINIWIND-STAGE-CLOSURE-33](BUILD-MINIWIND-STAGE-CLOSURE-33.md): The MiniWind plan puts the CHIM builder modules into every conversion stage's fingerprint
- [BUILD-NESTED-POOL-ALLOWANCE-33](BUILD-NESTED-POOL-ALLOWANCE-33.md): Pool workers open their own pools sized to the whole stage's allowance
- [BUILD-NPCLOD-PATH-ARG-34](BUILD-NPCLOD-PATH-ARG-34.md): The first --npc-lod on build stopped at its area stage: a Path in the command broke build-state.json
- [BUILD-OPTIMIZER-CACHE-KEY-BROAD-36](BUILD-OPTIMIZER-CACHE-KEY-BROAD-36.md): Regression: the image step's BSP optimizer pass cache reused 13 of 2,658 maps; its key covers the whole image tool, so any image-code change redoes every map
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
- [BUILD-REUSE-APPLY-SERIAL-41](BUILD-REUSE-APPLY-SERIAL-41.md): A reused stage staged its files one at a time: world terrain, scenery and flora took 8 to 12 seconds each, one after another, at the start of every reuse build
- [BUILD-REUSE-TMP-UNDECLARED-33](BUILD-REUSE-TMP-UNDECLARED-33.md): A stage that runs while a reused stage is copied becomes non-reusable
- [BUILD-SCHEDULER-EVEN-SHARE-33](BUILD-SCHEDULER-EVEN-SHARE-33.md): The stage scheduler splits the workers evenly between running stages, so the longest stage gets no more than the shortest (MiniWind media on 1 of 4 workers for 1,195 s)
- [BUILD-SCHEDULER-JOBSHARE-32](BUILD-SCHEDULER-JOBSHARE-32.md): The stage scheduler fixes a stage's worker share when it starts
- [BUILD-SCHEDULER-LOWBUDGET-33](BUILD-SCHEDULER-LOWBUDGET-33.md): With a small --jobs budget the stage scheduler starts nothing when more branches are ready than the budget (busy loop)
- [BUILD-SCHEDULER-MEMORY-STARVED-42](BUILD-SCHEDULER-MEMORY-STARVED-42.md): The scheduler's memory guard held the v0.0.42 final's chim stage on 1 of its 6 workers for over an hour, and nothing said so before or while it happened
- [BUILD-SILENT-PHASES-36](BUILD-SILENT-PHASES-36.md): Builder phases run silent: no start/end timing, no progress, no heartbeat; the CHIM stats step is a single-core tail
- [BUILD-STAGE-ALLOWANCE-STUCK-43](BUILD-STAGE-ALLOWANCE-STUCK-43.md): A build stage's worker allowance stays at 1 after the other stages finish, so the CHIM stage runs on one core
- [BUILD-STAGE-INTERRUPT-ABSORBED-36](BUILD-STAGE-INTERRUPT-ABSORBED-36.md): The stage wrapper absorbed Ctrl-C: a stage that handled the interrupt and returned 0 counted as passed, and the build went on
- [BUILD-STAGE-START-SHARE-33](BUILD-STAGE-START-SHARE-33.md): A pooled stage that starts while others run gets one worker as its start value
- [BUILD-STAIR-GATE-OOM-42](BUILD-STAIR-GATE-OOM-42.md): The CHIM stair gate runs a whole-Vivec MiniWind out of memory: its worker pool breaks
- [BUILD-STAIR-WALK-BORDER-COPIES-41](BUILD-STAIR-WALK-BORDER-COPIES-41.md): The CHIM stair gate walks every frame's whole border, so each cell's flights are walked many times and unreachable copies can fail a build
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

- [BUILD-STAIR-PASS-NOT-KEPT-41](BUILD-STAIR-PASS-NOT-KEPT-41.md): A frame's passed stair walk is not reused when the build it ran in failed, and the walker key changes with converter code

<!-- END GENERATED CATEGORY -->
