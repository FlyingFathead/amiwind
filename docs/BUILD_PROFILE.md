# Build profile and stage reuse

_Last updated with AmiWind v0.0.54-dev1 (27 October 2026)._

<!-- contents start -->
## Contents

- [Where it is](#where-it-is)
- [Performance options](#performance-options)
- [Reading a profile](#reading-a-profile)
- [Optimizer](#optimizer)
- [Perf guard](#perf-guard)
- [Resource plan](#resource-plan)
  - [While the build runs](#while-the-build-runs)
- [Perf database](#perf-database)
  - [Many builds: the stage ledger](#many-builds-the-stage-ledger)
- [Unit reuse audit](#unit-reuse-audit)
- [Build Timeline](#build-timeline)
- [Live progress and ETA](#live-progress-and-eta)
- [Sections](#sections)
- [Phases and the heartbeat](#phases-and-the-heartbeat)
- [Image step sub-phases (v0.0.36-dev3, 270 CHIM region cells)](#image-step-sub-phases-v0036-dev3-270-chim-region-cells)
- [How it is measured](#how-it-is-measured)
- [Stage reuse for development builds](#stage-reuse-for-development-builds)
  - [Reuse audit](#reuse-audit)
  - [Caches of another workspace](#caches-of-another-workspace)
  - [Cache provenance](#cache-provenance)
- [Build speed in CHIM](#build-speed-in-chim)
  - [CHIM world conversion (v0.0.42)](#chim-world-conversion-v0042)
- [Payload preflight](#payload-preflight)
- [Measured release builds (v0.0.33 -> v0.0.34)](#measured-release-builds-v0033---v0034)

<!-- contents end -->

Every build measures itself. The builder records, for each stage, how long it
ran, how much CPU it and all its child processes used, how many cores that
was on average against the jobs it was given, its memory peak and its disk
traffic. Long stages also time named sections. After the build the profiler
works out the critical path, flags stages that left their cores idle and
writes concrete suggestions. The same run records an input fingerprint and an
output manifest per stage, so a later development build can reuse unchanged
stages instead of running them again (`--reuse-from`, never silent, never for
releases).

Goal: compile fast, with zero errors and zero regressions. Measure before
optimizing; reuse only what is provably unchanged.

## Where it is

| File in the run folder | Content |
| --- | --- |
| `build-profile.json` | Per-stage measurements, CPU timeline, analysis and suggestions |
| `build-progress.json` | Live state while the build runs: stages, cores now, percent, ETA (see [Live progress and ETA](#live-progress-and-eta)) |
| `build-summary.json` | `profile`: wall, CPU, critical path, idle warnings, reused stages, overhead |
| `build-state.json` | Per stage: `profile` (CPU, cores, jobs, peak memory, I/O); `stage_cache` (fingerprints, reuse) |
| `profile/stages/NN-stage.json` | Raw counters from the stage wrapper |
| `profile/sections/NN-stage.jsonl` | One line per timed section call |
| `profile/manifests/STAGE.json` | Files the stage created, changed or deleted in the run folder, with SHA-256 |
| `profile/fingerprints.json` | What each stage fingerprint is made of (for `explain`) |

Run folders are deleted when a run is retired; the [perf database](PERF_DATABASE.md) keeps their
numbers (see [Perf database](#perf-database)).

The build summary footer shows the short form:

```text
Build profile: 1m16s wall, 0.05 CPU hours, 2.5 of 16 cores busy on average
Critical path (1m16s): engine > dry-run-image
  Slowest stages                 wall  cores  jobs   peak RSS
  *dry-run-image                1m10s    1.0    14   32.6 MiB
  *engine                        6.2s   3.87     5   94.7 MiB
  [idle] dry-run-image: 1.0 of 14 cores for 1m09s
```

`*` marks the critical path.

## Performance options

Everything the public builder offers to make builds faster and to see where
the time goes. None of these changes what a build produces.

| Option or command | What it does |
| --- | --- |
| `--jobs N` (`-j N`) | Exactly N workers for the whole build, shared by the stages that run at the same time; a warning when N exceeds the usable CPU threads, never a cap. Default: automatic (CPU count, quota, memory). See [PARALLEL_BUILD.md](PARALLEL_BUILD.md) |
| `--serial-stages`, `--single-thread` | Diagnosis: stages one after another (keeping their jobs), or one worker in total |
| `--reuse-from RUN` | Development builds: copy the outputs of stages whose input fingerprint did not change instead of running them; refused for release candidates and finals. See [Stage reuse](#stage-reuse-for-development-builds) |
| `python tools/build.py status RUN` | Live progress of a running build: stages, cores in use, percent, ETA, idle-core warnings. See [Live progress and ETA](#live-progress-and-eta) |
| `python tools/build.py profile report RUN` | The stage table, critical path, idle cores and suggestions of a finished build (`--html` for charts) |
| `python tools/build.py profile compare RUN OLDER_RUN` | Per-stage wall time against an older run; slower stages are regressions (`--fail-on-regression` exits 3) |
| `python tools/build.py profile optimize RUN [RUN ...]` | What to parallelize next, ranked: see [Optimizer](#optimizer) |
| `python tools/build.py profile timeline RUN [RUN ...] --png OUT.png` | Build Timeline: one picture of where the wall time went over one or more runs (stages, gates, CPU in use). See [Build Timeline](#build-timeline) |
| `--only-core-towns`, `--no-extra-town TOWN` | Debugging only: a smaller build without the shipped extra towns; the image does not match a release. See [LINUX_BUILD.md](LINUX_BUILD.md#shipped-towns-default) |
| `--log-level quiet\|normal\|verbose`, `--quiet` | How much the stages print (default `normal`, or `AMIWIND_LOG_LEVEL`). `quiet` drops only per-unit progress lines; phase start and end lines with their time and cores, the heartbeat, warnings and errors always print. Recorded in the receipt (`log_level`); outputs and stage keys are the same. See [Phases and the heartbeat](#phases-and-the-heartbeat) |
| `--no-profile` | Debugging only: no profile, no progress file, no output manifests (a later `--reuse-from` cannot use the run) |
| `AMIWIND_HASH_METHOD=process` | Debugging only: payload SHA-256 checks in one spawned-process task per file (the earlier method) instead of threads of the stage in size batches (default since v0.0.36; same digests). Each hashing call is the profile section `parallel hash: sha256` with its file count and bytes |
| `AMIWIND_HEAP_AUDIT_METHOD=python` | Debugging only: the world map heap audit's earlier per-entity leaf-link walk and edge-cache prefix loop instead of the float32 array methods (default since v0.0.36; the same report) |
| `--perf-guard fail\|warn\|off`, `--perf-guard-baselines FILE` | The perf guard at the end of every build: a section that ran in parallel before and now runs serial, or slower for the same work, fails the build (exit 3). See [Perf guard](#perf-guard) |
| `python tools/perf_guard.py check\|show\|seed ...` | Judge a finished run, show its verdict, or add finished runs to a baselines ledger. See [Perf guard](#perf-guard) |

`./build.sh status ...` and `./build.sh profile ...` are the same commands.
`--vis full` is not a speed option: it runs the slower full vis pass (see
[PARALLEL_BUILD.md](PARALLEL_BUILD.md#vis-threads-and-vis-mode)). There is no
general partial-area build yet (one region or cell instead of the whole game);
the town options above are the only way to build less, and only for debugging.

## Reading a profile

```text
python tools/build.py profile report RUN
python tools/build.py profile report RUN --html profile.html
python tools/build.py profile compare RUN OLDER_RUN [--fail-on-regression]
python tools/build.py profile report RUN --compare OLDER_RUN
python tools/build.py profile report RUN/profile/sections/22-image.jsonl
```

`tools/build_profile.py` takes the same arguments.

The table has one row per stage:

| Column | Meaning |
| --- | --- |
| start, wall | Seconds after the first stage started; stage duration |
| cpu | User + system CPU of the stage process and every child it waited for |
| cores | cpu / wall: average cores in use |
| jobs | The share of the `--jobs` budget the scheduler gave the stage: one number when it never changed, else the range it moved through (`1-12`: started with 1, held up to 12); the profile row has `jobs` (start), `jobs_min`, `jobs_max`, `jobs_mean` (time-weighted) and `worker_changes` |
| peak RSS | Largest summed memory of the stage's process tree (sampled), else its largest single process |
| read, written | Block device bytes (see limits below) |
| note | `critical`, `slack T` (how long the stage could have waited without delaying the build), `reused` |

Then:

- **Critical path**: the longest dependency chain by stage wall time. With
  unlimited cores the build cannot be shorter. Speeding up a stage off the
  path does not shorten the build; the slack column says by how much it could
  slip. "Waited on" is the chain the build actually waited for (the
  dependency that finished last, stage by stage); when it differs from the
  critical path, job slots, not dependencies, decided the order.
- **Slowest sections**: named parts of long stages (see below) with calls,
  wall time and cores.
- **Idle-core warnings**: a stage that used less than half of the workers it
  held at that moment for more than 60 s, from the one-second CPU timeline
  (without a timeline: average cores against the time-weighted mean workers).
  The workers held follow the scheduler's rebalancing, not only the start
  value: a stage that starts with one worker and gets twelve a moment later is
  measured against twelve
  ([BUILD-PROFILE-JOBS-START-ONLY-33](bugs/BUILD-PROFILE-JOBS-START-ONLY-33.md)).
  This is how a serial loop inside a stage shows up (the image step on one of
  24 threads for 23 minutes,
  [BUILD-IMAGE-SERIAL-32](bugs/BUILD-IMAGE-SERIAL-32.md)).
- **Host load**: every stage records the machine's CPU count, how busy the
  whole machine was while it ran (sampled from `/proc/stat`; in a container
  that is the virtual machine shared with every other container), and this
  build's own cores. When other work used more than 25 % of the machine the
  stage is marked `host_busy`: its timings are not comparable with a quiet
  host. `report` lists such stages, and `--compare` warns about every stage
  that was busy in one run and quiet in the other.
- **Suggestions**: idle stages with their slowest sections, serial stages on
  the critical path, the whole build's average cores against the budget,
  waiting for job slots, and stages a development rebuild could reuse.

`--compare` lists every stage's old and new wall time. A stage more than 10 %
and more than 5 s slower is a regression: the report prints
`REGRESSION: slower stages: ...` and `--fail-on-regression` exits with 3.
Stages whose fingerprint did not change are marked "reusable".

`--html` writes one self-contained page: a stage Gantt chart (critical path
red, reused green), the CPU timeline against the job budget (and the whole
container's CPU when available), suggestions and the table. Chart.js loads
from cdnjs; the table works without it.

## Optimizer

```text
python tools/build.py profile optimize RUN [RUN ...] [--json]
```

lists, for one or more finished builds, the places where cores sat idle,
ranked with the critical path first and then by the wall time they could save
(an upper bound: the low-core stretch run at the stage's parallel width):

| Kind | Found when | Suggestion |
| --- | --- | --- |
| `idle` | A stage used less than half of its jobs for more than 60 s (`--share`, `--seconds`) | Find the serial loop or the waits (its slowest sections are named), run independent items on the shared worker pool, or give the workers to other stages |
| `tail` | A stage ran on two or more cores, then spent more than 30 s (and 10 % of its time) at the end on about one core | One large item finished last: submit the largest items first, split it, or let the next stage start on the finished part |
| `serial-critical` | A one-core stage of more than 60 s on the critical path | A parallel inner loop shortens the whole build directly |
| `slot-wait` | The build took more than 1.25 times its longest dependency chain | Stages waited for job slots: give stages off the critical path fewer workers |
| `underused-phase` | A phase or outermost section ran more than 30 s on fewer than half of the workers its stage held (`build_profile.underused`; also `[underused]` lines in the build summary and `stages[].underused` live in `build-progress.json`) | Run its independent items on the shared worker pool, cache its result by the SHA-256 of its inputs, or give the workers back ([BUILD-UNDERUSE-GATE-36](bugs/BUILD-UNDERUSE-GATE-36.md)) |

With several runs each row says in how many of them the item appeared, so a
one-off (a busy host, a cold disk cache) stands apart from a stage that is
always slow. Items measured while other work loaded the machine say so: measure
them again on a quiet host before acting. Every speed-up must keep the outputs
byte for byte (check it against `--jobs 1`).

## Perf guard

Parallelization never regresses. The builder runs the perf guard (`tools/perf_guard.py`) after
every build whose stages passed, and the master builder puts its verdict into the build result
(`perf_guard`; step `perf-guard`) and `aw status`. It reads the run's `build-profile.json` and
judges every stage section, phase and parallel map of a stage that was not reused and that ran
for at least 30 s, against earlier runs of the SAME work only:

| Baseline tier | Same work means | Compared |
| --- | --- | --- |
| exact | the stage's input fingerprint and the unit count are the same | cores and time |
| units | the same unit count (a parallel map's items, a phase's unit total) | cores and time |
| saturating | both runs had at least as many independent units as cores, so both could fill every core | cores only (as a share of the cores the run could use), never time |

Anything else (another stage, another section, a run with fewer units than cores) is different
work and is never compared. The cores baseline is the best share of usable cores any run of the
same work reached (parallelism never falls back from what it achieved); the time baseline is the
median of the exact, else same-units, runs.

| Verdict | When | Fails the build |
| --- | --- | --- |
| `FAIL` | parallel -> serial (the baseline used 2+ cores, now under 1.5); or under half of the baseline's share of usable cores (and fewer cores); or more than 25 % and 30 s slower with the same units | yes |
| `FIX-NOW` | no baseline needed: over 1 min with independent units (items, a phase total, or a section `config/perf-guard.json` declares per-unit) on under a quarter of the cores it could use (min(cores held, units)) | yes |
| `WAIVED` | a FAIL or FIX-NOW covered by a waiver in `config/perf-guard.json` (bug ID, owning job, expiry date) | no; shown in the table, the result and `aw status` |
| `BUSY HOST` | other work loaded the machine (the profiler's `host_busy`) in this run or the only baseline: time is never compared; cores only when the section still had at least the baseline's cores free, or left most of its free cores idle (the reasons say which) | no |
| `ok`, `no baseline` | | no |

**A perf guard failure does not hold back a playtest, decided for the project on 19 October 2026.** When every
stage and every other check of a build passed and only the perf guard failed, the image works: it is delivered as a
playtest with the failing sections named as known builder bugs, and those bugs are fixed right after.
The guard still fails the build's result, so the regression is never quietly accepted.

Cores are compared only where at least 4 cores were usable (with two or three units one long unit
sets the cores, not the code). A waiver ends at its date, or as soon as the bug register marks its
bug fixed; a waiver lives at most 14 days (test-enforced) and must name a registered bug.

Output: one table per build (stage, section, units, cores used / usable (held), time, baseline,
verdict) ending with a TOTALS row, printed at the end of the build and written to `perf-guard.txt`
and `perf-guard.json` in the run folder. A failed guard ends `tools/build.py` with exit 3: every
stage passed and its outputs stay valid and reusable, but the build result is failed until the
section is fixed or waived. `--perf-guard warn` only prints; `--perf-guard off` is for debugging
only. Dry runs and `--no-profile` builds are not judged.

Baselines: a JSON-lines ledger, by default `<workspace>/cache/perf-guard/baselines.jsonl` (the
build pool's shared cache; `AMIWIND_PERF_GUARD_BASELINES` or `--perf-guard-baselines` override it).
A build whose guard passed adds its sections (busy-host ones marked); a profile is added once, by
its SHA-256. Seed or extend it from finished runs:

```text
python tools/perf_guard.py seed RUN [RUN ...] --baselines FILE
python tools/perf_guard.py check RUN [--baselines FILE] [--record] [--json]
python tools/perf_guard.py show RUN [--json]
```

The guard only reads the profile and the ledger; it never changes a build output. It sits beside
the [Optimizer](#optimizer) (what to parallelize next) and the underused-phase list: those list,
the guard fails.

## Resource plan

Every build checks, before its first stage, whether the memory and threads it
gets are enough for the stages that will actually run (the stages its reuse
plan does not reuse). Origin: a stair gate ran 22 whole-Vivec frame walks of
about 2.6 GiB each at once in a 30 GiB container and the container ran out of
memory (CHIM-STAIR-GATE-POOL-BROKEN-42); decided for the project on
2026-10-17: a checklist where the compute is worked out up front, with an
advisory to take more when it would help.

```sh
./build.sh --resource-plan ...the build's own options...      # read only, nothing is built
./build.sh --resource-plan --resource-memory-gb 30 --resource-threads 24 ...
./build.sh --resource-plan --resource-plan-json plan.json ...
```

`--resource-plan` prints the plan and exits (exit 5 when a stage will not
fit); with `--check` it runs after the checks. `--resource-memory-gb` and
`--resource-threads` name the container the build will run in (for example
its lease); without them the plan reads this container's own limits (cgroup
`memory.max` and `cpu.max`), else the machine's. A real build makes the same
plan automatically after the reuse preflight, records it as
`RESOURCE-PLAN.json` in the run folder (schema `resource-plan-1`, validated
before it is written) and prints it:

```text
Machine at start: 0.4 of 24 threads busy in this container; memory 1650 / 30720 MiB in use (...); asks 11 threads, 23929 MiB
Resource plan: 5 of 22 stages run; the build gets 30720 MiB (container limit (cgroup memory.max)) and 24 threads (...); --jobs 11
  OK            census                   11 of 11 workers; about 88 MiB a worker + 355 MiB parent, peak about 1322 MiB, wall about 0m36s [measured (2 runs)]
  WILL THROTTLE chim                     8 of 11 workers; about 2774 MiB a worker + 1734 MiB parent, ...: memory holds 8 workers at about 2774 MiB each beside a 1734 MiB parent [measured (2 runs, 2 failed) + stair model]
ADVISORY: this build would run up to 27 % faster in chim (...) with 10 GiB more memory (the lease to ask for: --threads 11 --mem-gb 40)
Resource plan: THROTTLED (4 OK, 1 WILL THROTTLE, 0 WILL NOT FIT); expected wall about 2m09s (stages added up)
```

One line per stage that runs:

| State | Meaning |
|---|---|
| `OK` | the stage gets its planned workers (`--jobs`; one for a stage without a pool) |
| `WILL THROTTLE` | fewer workers: the number, and why (the memory holds N at the stage's size per worker, or the CPU quota) |
| `WILL NOT FIT` | one unit alone (named, with its estimated MiB) is larger than the memory the build plans with (80 % of the limit): the build is refused before any stage runs (`--resource-check warn` builds anyway, `off` skips the plan) |

The `ADVISORY` line appears only when more memory or threads would make the
build at least 2 % faster; it never asks for more than the machine has (it
says so when full speed would need more).

Where the numbers come from, said on every line in brackets:

- **measured**: the `build-profile.json` of the `--reuse-from` run and the runs
  it reused from (only stages that really ran there; a failed stage still shows
  how much memory it reached) and the workspace's history
  (`WORKSPACE/cache/resource-history.jsonl`). Per stage: the largest single
  process (the parent, or one unit) and the memory of each further worker (the
  stage's peak less its largest process, per worker; the process tree's summed
  memory is bounded by the container's own peak while the stage ran, since
  shared pages count once per process). The largest of the measurements is used.
  Like for like: a MiniWind plan uses only MiniWind measurements and a full
  build only full ones (the scope of a run comes from its `build-state.json`,
  else its name; history rows carry `scope`, and the newest five of each scope
  are kept); a stage measured only in builds of the other scope gets the no-data
  estimate, its model line naming the other scope's figure. Without a sampled
  process tree (a stage shorter than the sampler's interval) the stage's total is
  its largest process, never the container's peak, and a measured worker larger
  than twice the stage's largest process is capped to that (a worker unit is one
  process and at most one child of it). Origin: v0.0.54-dev1 MiniWinds were
  refused against the v0.0.53 full final: the whole island's chim figures, and a
  0.7 s mwscript stage recorded at 32,412 MiB a worker (the container's peak).
- **stair model**: every stage that builds a CHIM world walks its stairs with
  one frame per worker: 128 MiB + 18 x the frame's placed MiB
  (`tools/chim/stair_pool.py`, calibrated on the v0.0.41 world and the
  whole-city Vivec frame of v0.0.42). The largest frame comes from the stair
  gate's own worker line of an earlier run, else from the stored frame's size
  on disk (about 2.03 placed bytes per stored byte, one calibration point).
  With `--stair-walk off` (the default) nothing is walked and no stair figure is
  looked for or priced.
- **estimated, no data yet**: a stage never measured (512 MiB a worker beside a
  256 MiB parent).
- **beside it**: the memory the other stages held at the stage's measured peak
  (the container's peak while it ran less its own process tree) is counted too,
  so a stage measured beside others is not planned as if it ran alone; every
  throttled stage names the lease that runs it at its planned workers
  (`lease_gb_full_speed`). Origin: the v0.0.42 final's chim stage was planned at
  21 GB alone and met 26.5 of 28 GiB in use beside the NPC gallery and the world
  terrain (BUILD-SCHEDULER-MEMORY-STARVED-42).

Wall times are the measured wall fitted with Amdahl's law (the stage's average
busy cores on its workers give its parallel share), so a stage that kept one
core busy gains nothing from more workers. Stages are added up although a
parallel build overlaps them: the totals are estimates.

After a passed build every stage's actual peak is written next to its estimate
in `RESOURCE-PLAN.json` (`actual`), a stage more than 25 % over its estimate is
flagged in the build log (`flagged_over_estimate`), and the measured rows join
the history, so the next plan starts from them: the models calibrate
themselves.

### While the build runs

The plan is not only a start-time check. The worker pools follow the memory
and the CPU quota the container has while the build runs, re-read every 30 s
between tasks:

- the scheduler (pooled stages): above 90 % of the memory limit in use (file
  cache not counted) the stage holding the most workers hands out no new units
  beyond three quarters of them; a capped stage grows back toward its share
  whenever the free memory under 80 % of the limit holds one of its units at the
  plan's size per worker, by as many as fit (stages without a known size: one
  at a time, below 70 % in use). Until 17 October 2026 it grew back only below
  70 % in use, which a large parent could keep out of reach for hours
  (BUILD-SCHEDULER-MEMORY-STARVED-42). A CPU quota lowered while the build runs (`docker update --cpus`)
  shrinks the shares; a raised one lets them grow back up to `--jobs`;
- the CHIM stair gate: starts with the walks that fit now and grows back toward
  its cores' count when memory frees up (another container ends, a raised
  lease: `docker update --memory`), and stops starting walks when memory gets
  tight.

Before a pooled stage starts, the scheduler compares its parent and its
workers (the plan's sizes) with the memory the container holds beside it at
that moment; when they will not fit under 90 % it prints one line, before the
stage's first unit:

```text
[scheduler] WILL NOT FIT AT FULL SPEED: chim needs about 26.8 GiB (a 13000 MiB parent + 12 workers x 1200 MiB) beside 10.0 GiB in use (running: npc-gallery, world-terrain), of 28.0 GiB; the memory guard will hold it back; a lease of 41 GB fits it
```

A pooled stage the guard holds below half its share for 5 minutes
(`AMIWIND_SCHEDULER_ALARM_SECONDS`, default 300) prints an alarm, again every 5
minutes while it lasts, with the lease under which it would grow back (its
missing workers fit under 80 % of the limit); the alarms are kept in `build-state.json` (`scheduler_alarms`):

```text
[scheduler] ALARM: chim held at 1 of 6 workers for 5 min by the memory guard (26.5 of 28.0 GiB in use, file cache not counted); a lease of 41 GB would let it run at 6 (5 more workers at about 1200 MiB each)
```

When the scheduler can read a stage's own processes (Linux `/proc`: the stage's
main process and the pool workers below it), the guard works from what the
workers really hold (BUILD-STAGE-ALLOWANCE-STUCK-43: in v0.0.43-dev3 it cut the
CHIM stage from 20 workers to 1 while the stage's main process held the memory,
and never grew it back):

- above 90 % it cuts only when the workers hold the memory over the line (what
  they hold above an idle worker), by as many workers as the excess needs; when
  the main process holds it, the workers stay and one line says so; above 96 %
  it cuts anyway;
- a held stage grows back by its measured worker size, up to 88 % of the limit;
- when a stage ends, the guard looks again at once.

The free-core checker: each pool map of a running stage writes its queued and
running units, and the slowest running unit by name, beside the stage's
allowance file (`jobs/NN-stage.pool`, `tools/pool_status.py`). The workers a
stage with nothing queued does not use go, on loan, to the stages that have
queued units; the loan ends at the scheduler's next look once that stage queues
units again.

The live supervisor (`tools/stage_watch.py`) looks every 5 s at the cores each
pooled stage really uses. A stage under half its share for over 60 s while its
pools have units queued is an occurrence: one warning line, and one JSON line in
`RUN/underused.jsonl` (stage, cores used, allowance and share, queued and
running units, the slowest unit, since when, who holds it, and the stage's phase
running at that moment with its age, `phase` and `phase_seconds`, from the
stage's own phase timer; BUILD-IMAGE-FINALIZE-UNDERUSED-48). One line per
occurrence; the build carries on, and the build summary lists it as a warning:

```text
[underused] WARNING: chim ran on 1.0 of 20 cores (allowance 1, share 20) for 65 s with 400 units queued and 1 running; slowest running unit: rcp16_p11 (42 s); phase now: CHIM stats: resident rings (running 12 s); held by: memory guard; the build carries on (RUN/underused.jsonl)
```

In the image step, the steps that share no file run side by side in spawned
workers, each as its own timed phase: the world UI and the player view beside the
combat data, and the carried torch beside the NPC gallery and the torch test map
(BUILD-IMAGE-FINALIZE-UNDERUSED-48). Before this, the v0.0.54-dev1 magic MiniWind
ran the torch, the combat data, the player view and the world UI one after the
other, on about one core each.

The build summary's digest (`tools/build_digest.py`) is written into
`RUN/build-summary.json` (schema `amiwind-build-summary-v2`, key `digest`) and
as `RUN/build-summary.md` (under about 60 lines) at every stage end and at the
end of the build, after the perf guard: per stage the wall time, the mean cores
used and allowed, the longest stretch under half its share, reuse and warnings
(underuse, perf guard, size growth, waivers, retired flags); a 'Needs attention'
list, empty when all is well, one stable key per entry (`underused:chim`,
`perf-guard:chim:<section>`, `stage-failed:image`, `size-growth:<folder>`,
`retired-flag:<flag>`, `slower:<stage>`); and stage times up or down by more
than 20 % (and 30 s) against the last passed build of the same kind beside it.

Pools hand out their heaviest units first: `ordered_map(..., history=NAME,
key=...)` by the seconds recorded for each unit in earlier builds whenever such
a history exists (this run's times are recorded for the next), `cost=` on
`ordered_map`, `completed_map`, `governed_map` and `spread_map`. Every caller gives a cost, a
history or a recorded reason (`tests/test_pool_cost_sweep.py`,
BUILD-CHIM-REGION-FRAMES-TAIL-43).

`spread_map(..., spread=...)` is `completed_map` for units that can use more
than one core: when fewer units are left to start than cores are free (the
tail), the free cores are offered to them by their cost, and each unit takes
what it can use; the cores in flight stay within the stage's share. The room
batches stage gives them to a big room's scenery geometry (ROOM-BATCH-CORES-49).

A stage sizes its own pools by its ceiling (the build budget under the
scheduler, `build_parallel.stage_ceiling`), not by the `--jobs` it was launched
with, which is only the scheduler's share at that moment: the CHIM stair gate
cuts its walk units and plans its workers by it, and the live allowance and the
memory decide how many run at each task (BUILD-CHIM-STAIR-JOBS-AT-LAUNCH-42).

A running unit is never stopped: a smaller allowance only stops new units.
Every change is printed with its reason (`[pool] ...: workers 8 -> 11 of 11
(memory or threads freed up; ...)`, `[scheduler] memory tight ...`). The
resource plan and the governor never change what a unit computes or the order
of any output, so they are not part of any stage key.

**`--jobs` keeps its level below 96 % of the memory limit** (decided for the
project, 21 October 2026; BUILD-SCHEDULER-MEMORY-STARVED-42). The memory guard
cuts a pooled stage's workers only above 96 %, to keep the build clear of the
out-of-memory killer. Below that line every stage runs at its full share of
`--jobs`, and a cut made above it is lifted as soon as the memory is back under
it (`[scheduler] memory ...: below the critical line (96 %), chim back to its
full share of --jobs`). The reason: a cut does not free memory. A pool's worker
processes stay alive between units and keep the memory they reached; a cut only
stops giving them new units. The earlier guard cut workers from 90 % and grew
them back only when memory came free, so a cut never reversed: a from-scratch
build's CHIM stage ran on 1 of 24 cores for an hour at 90 % memory.

**Idle workers end when the allowance falls** (BUILD-POOL-MEMORY-PEAK-48). Under
the scheduler each worker pool has a watcher thread: when the pool has held more
live worker processes than its stage's allowance (and its units in flight) for
about 20 s, the idle ones end and their memory goes back to the machine
(`[pool] 7 idle worker process(es) ended: 8 alive for an allowance of 1 ...`);
new workers start when the allowance grows again. A running unit is never
stopped. In the v0.0.48-dev2 build the CHIM and room batches stages sat at one
worker each for over ten minutes at 42 of 44 GiB, most of it idle workers.

**Small units go out in chunks** (BUILD-POOL-TINY-UNITS-48). `completed_map`
first hands out one unit per task; once a wave of units has measured the unit
time, each task takes a guided share of the units left (the units left divided
by four tasks per worker), at most about 2 s of measured work, so the chunks
shrink to single units in the tail. A chunk is pickled once, so units that share
a large input (the heap gate's position slices of one frame) send it once. Each
unit still runs its function on its item and yields its own result; a failing
unit ends the map as before. `AMIWIND_POOL_CHUNKS=off` keeps one task per unit
(the method before v0.0.48); it is not part of any key.

## Perf database

`tools/perf_db.py` reads these files (and the gate results, the reuse audits and the CPU samples)
into one SQLite database whose rows are never changed again, each file recorded with its SHA-256,
so a number can be compared across every run that has it, including runs whose folders are gone:

```text
python3 tools/perf_db.py --db perf.db ingest out/build
python3 tools/perf_db.py --db perf.db compare --metric heap.peak --frame frames/x-03/y-02
python3 tools/perf_db.py --db perf.db stage-history --stage chim
```

Tables, commands, the container recipe and the deterministic rebuild: [PERF_DATABASE.md](PERF_DATABASE.md).

### Many builds: the stage ledger

```text
python tools/build.py profile optimize --ledger LEDGER.jsonl [RUN ...]
```

With a stage ledger (one JSON object per stage and build: `stage`, `build`, `wall_s`, `cores_avg`, `jobs_max`,
`status`; the perf database writes one), `optimize` also prints, per stage, how many builds it ran in, its median
and longest wall time, its median cores, its slowest build and how often (and how long in total) it ran over 30 s
on fewer than half of its workers. The list is sorted by that underused time, so the stage that wastes the most
cores over many builds comes first.

## Unit reuse audit

```text
python tools/build.py profile reuse RUN --cache CACHE_DIR [--cache ...] [--json] [--fail-on-recompute]
```

Every unit cache (world terrain, image passes, CHIM units, stair-walk records, ...) keeps a provenance record per
entry (schema `aw-cache-provenance-1`: the entry's key, its input manifest, the run that made it) and a reuse log
(`.provenance/reuse.jsonl`). The audit reads them for one run and lists, per cache:

- **computed** and **reused** units of that run;
- for each computed unit the inputs whose SHA-256 changed against the newest earlier entry of the same unit
  (the `unit` name in its input manifest), or `parameters`; a unit with no earlier entry is `new unit`; one with
  no unit name is `unexplained`;
- **RECOMPUTED WITH AN UNCHANGED KEY**: a unit computed although an earlier entry, or an earlier reuse by another
  run, already had its key. That is a reuse bug; `--fail-on-recompute` exits 3 so a gate or the release flow
  stops on it;
- **unkeyed stages**: stages that ran in the run with no unit cache of their own (`build_profile.STAGE_CACHES`);
  they are reused or rebuilt only as a whole stage, and each is a work item under the hash-everything rule.

The benchmark `tests/test_unit_reuse_audit.py` (`NoChangeRebuildBenchmark`) checks the other side: a rebuild with no
change computes 0 units, and a changed input recomputes exactly its unit.

## Build Timeline

Part of the AmiWind Builder Profiler: one PNG that answers "where did the wall
time go" over one build or a whole evening of builds, resumes and gates.

```text
python tools/build.py profile timeline RUN [RUN ...] --png OUT.png
    [--labels NAME ...] [--title TEXT] [--start "YYYY-MM-DD HH:MM"] [--end ...]
    [--utc-offset +HH:MM] [--samples CPU.jsonl] [--gates GATES.jsonl]
    [--events JOBS.jsonl] [--commits REPO[:BRANCH]] [--host-cpus N] [--json OUT.json]
```

![Build Timeline of one v0.0.36-dev3 build](images/amiwind-v0.0.36-build-timeline.png)

The title reads "TITLE: where the wall time went" (default: the run name, or
the version of the runs). From top to bottom:

- **Lanes** for commits (`--commits`), gates (`--gates`) and any other timed
  jobs (`--events`, one lane per `lane` value): green outline passed, red
  failed, grey still running.
- **One block per run**, in start order: a bar for the whole run (light part:
  the checks before the first stage), the reused stages and the stages too
  short to read at the chart's scale as ticks on their own rows, then every
  other stage as a bar labelled with its wall time and average cores (CPU /
  wall). The shade is the share of the build's job budget it used (light: few
  cores, dark: all); red = failed, hatched = still running, black outline =
  critical path. A stage whose live expectation (from `build-progress.json`)
  was off by more than 2x, or had no comparable history, says so in its label
  with the basis (`expected 3 min (history (3 run(s)))`); a run that is still
  going shows its last ETA and its basis after the run name.
- **CPU cores in use**, stacked by job in 30 s means (`--step`), with the
  machine's CPU threads dashed and the whole machine as a black line. The
  legend gives each series' core-minutes inside the window.

Inputs. Only what every build writes is read: a finished run's
`build-profile.json` (stages, the one-second CPU timeline, `/proc/stat`
machine load, critical path); for a run that is still going (or ran with
`--no-profile`), `build-state.json` (each stage's start and duration),
`build-progress.json` (the clock origin and the last update: a running stage
ends there) and `build-summary.json`. The chart can be drawn while a build
runs. Everything else is optional and passed in:

| Option | One JSON object per line |
| --- | --- |
| `--samples` | `{"t": TIME, "name": "...", "cores": 3.2}`; optional `"group"` (the series to stack it in); the name `HOST` is the whole machine (`"cores"`, or `"cpu_pct"`: percent of all its CPUs). A sample whose name contains a drawn run's folder name joins that run's series (a build container named after its run); the run's own profiler timeline fills the time no sample covers. More than eight series: the smallest fold into "other". |
| `--gates`, `--events` | `{"name": "...", "start": TIME, "end": TIME or null, "result": "passed" \| "failed" \| "running"}`; optional `"lane"` and `"label"`. `end: null` = still running (drawn to the end of the data). |

TIME is epoch seconds or ISO 8601. Times with an offset (`Z`, `+00:00`, `+0300`)
are exact; the build records are written in the container's clock (UTC) and
are converted. Times without an offset are read in the `--utc-offset` zone,
which is also the zone the chart is drawn in (default: the zone of the machine
running the command; inside a container that is usually UTC, so pass the host's
offset). Unreadable lines are skipped.

How the CPU area is computed: each sample stands for the time since the
previous sample of the same series (the profiler measures CPU over the real gap
and divides by it); a gap over three times the usual one (a paused sampler)
counts only the usual interval, so a late sample never spreads its rate over
time it did not see; the 30 s means are time-weighted, so the area under a
series equals the CPU it measured
([TEST-PROFILE-TIMELINE-SUM-33](bugs/TEST-PROFILE-TIMELINE-SUM-33.md),
[TEST-PROFILE-TIMELINE-BOUND-33](bugs/TEST-PROFILE-TIMELINE-BOUND-33.md):
rates rounded to three decimals over jittered intervals stay within 0.2
core-seconds; `tests/test_build_timeline.py` pins both). Container samples
are snapshots, so where several jobs overlap the stack can pass the
whole-machine line; the gap under that line is load no series covers.

Drawing needs Pillow (in the builder Docker image); `--json OUT.json` writes
the chart data without it. Fonts: DejaVu Sans when installed, else Pillow's own
font. The same inputs give a byte-identical PNG with the same Pillow and fonts
(no time stamps or metadata in the file).

## Live progress and ETA

While a build runs, the builder rewrites `build-progress.json` in the run folder
about every 10 seconds and whenever a stage starts or ends
(`AMIWIND_PROGRESS_INTERVAL` changes the period):

```text
python tools/build.py status RUN [--json]
```

```text
Build dev-7: running, 47.3 %, elapsed 23m10s, ETA 25m40s (at 20:48:50, critical path)
Stages: 20 done, 2 running, 12 pending, 0 failed/cancelled (of 34)
  running                     elapsed    expected   cores  jobs  note
  world-terrain                12m03s     ~13m00s    14.2    20
  town-new                      2m10s  no history     1.0     4  no history, idle 2m05s
ETA waits on (25m40s): world-terrain > world-scenery > image
[idle] town-new: 1.0 of 4 cores for 2m05s
Host: 24 CPUs, 71.0 % busy, this build 15.2 cores, other work 7.7 %
No history (2m00s weight each): town-new
Expected durations from 2 earlier run(s) + the default table
Updated 2026-10-08T20:23:10+03:00 (4s ago)
```

What the file holds and how it is worked out:

- **Stages**: every stage of the build as `pending`, `running`, `passed`,
  `failed` or `cancelled`; for a running stage its elapsed time, its current
  worker allowance (the scheduler rebalances it), the cores its process tree
  used over the last 10 seconds, and its expected duration with the source.
- **Expected durations**: the median of the same stage in the newest ten
  earlier runs of the workspace that have a `build-profile.json` (sibling run
  folders), each scaled to this build's `--jobs` by its parallel share
  (Amdahl: a stage that averaged C cores on W workers is fitted, then run on
  W x new budget / old budget workers; a one-core stage does not scale). Without
  such runs the shipped table `config/build-stage-durations.json` (a from-scratch
  build on a 24-thread host) is used the same way. A stage in neither says
  "no history" and weighs the median of the known stages. A stage reused with
  `--reuse-from` weighs 5 s.
- **Stage size**: a stage whose amount of work can be read from its command
  line is compared only with earlier runs of a known size. Today that is the
  chim stage: its frames (one per `--area`, one per `--chim-regions-cells`
  cell). The history is scaled linearly by frames here / frames there (and
  named so when the sizes differ by more than 2x); earlier runs whose size is
  unknown do not count, and with none left the stage says `no comparable
  history`, weighs the median like a stage without history, and the ETA says
  `lower bound: no comparable history for chim` (`eta_lower_bound: true`)
  instead of a confident number. Every stage row carries `expected_basis`
  (`history (3 run(s))`, `history scaled by frames: 273 here, 3 in 3 earlier
  run(s)`, `default table`, `no history`, ...) and, with a size, `work` and
  `work_unit`. Origin: a 273-frame build's chim stage was expected at 154 s
  from three-area runs and ran 1 h 48 min, while the progress showed 27 % and
  about 22 minutes left
  ([BUILD-PROGRESS-ETA-BASIS-36](bugs/BUILD-PROGRESS-ETA-BASIS-36.md)).
- **The estimate follows the work while a stage runs**: a stage that counts
  its units (its phase timer's done/total, else the last counted progress line
  of its log, `[done/total unit] ...`) is corrected from them. The units still
  to do at the rate measured here, plus the history time of the phases that
  follow the current one (scaled by the work), are blended with the history
  estimate by the square root of the share done, so the estimate moves to the
  measured rate early and equals it when the counter is complete; once the
  history estimate is overrun, the measured rate alone counts. A stage past its
  history estimate with no counter takes the history of its current phase and
  the phases after it. The units a stage counted are kept in its row
  (`units_seen`), so the next build expects it per unit: history seconds per
  unit times this build's units (`expected_per_unit`). Each corrected stage
  row carries `counter` and `live` (remaining, measured, weight, seconds per
  unit, the later phases and a `basis` sentence), the ETA basis says which
  stages were corrected, and the builder prints one `[eta]` line every 5
  minutes (`AMIWIND_ETA_LINE_SECONDS`, 0 = off):

  ```text
  [eta] 67.6 %, ETA 27m46s (at 12:40:00 UTC / 15:40:00 local (+0300)) | chim: ~27m46s left, 539/723 frames done, 6.45 s each here (log counter 'CHIM region frames'), weight 1.00 against history (5 run(s), 364 frames there, 726 here); later phases 7m59s from history
  ```

  The builder's container runs on UTC, so the finish time is printed in UTC and, when
  `AMIWIND_LOCAL_UTC_OFFSET` gives the host's offset (`date +%z`, for example `+0300`), also in local
  time (without it, the builder's own clock offset is used, so a build run directly on the host shows local
  time too). A launcher that runs the builder in a container passes `-e AMIWIND_LOCAL_UTC_OFFSET=$(date +%z)`.
  The status lines do the same (BUILD-ETA-CLOCK-UTC-ONLY-46).

  Origin: v0.0.41-dev5's chim stage was expected at 43 minutes from history
  (364-frame runs scaled to 726 frames, many of their frames reused from the
  unit cache) and ran over 85; the ETA said 23 minutes left at 12:40 and still
  25 at 13:07. Replayed with an even frame rate, the corrected ETA at 12:40 says
  28 minutes (37 were left)
  ([BUILD-PROGRESS-ETA-BASIS-36](bugs/BUILD-PROGRESS-ETA-BASIS-36.md)).
- **Percent**: finished stages count their whole expected duration, a running
  stage its elapsed share (at most 95 % until it ends), pending stages nothing;
  the sum over all expected durations. Weighting by duration keeps a dozen
  one-second stages from looking like progress.
- **ETA**: the later of two bounds, named in `eta_basis`: the longest chain of
  remaining stage times through the dependencies (`critical path`), and the
  remaining CPU work (expected cores times remaining time) spread over the
  budget (`CPU budget`). A stage past its expected duration is marked `OVERRUN`
  and assumed to need another 10 % of its elapsed time. No ETA after a failure.
- **ETA waits on**: the chain of unfinished stages that sets the ETA.
- **Idle cores**: a running stage that has used less than half of its current
  workers for more than 60 seconds, and the same for the whole build against
  `--jobs` (the profiler's rule, live).
- **Host**: the machine's CPU count, how busy it was over the last 10 seconds,
  this build's cores and the share other work used (as in the profile).

The status command marks a running build whose file has not changed for three
periods plus 30 seconds as `STALE` (the builder stopped or the machine
suspended). A run without the file (`--no-profile`, or a builder older than
this) still shows its stage states from `build-state.json`, without percent or
ETA. Like the profile, the progress file is written next to the run's other
records, never into stage outputs, and writing it can never fail a build. The
cores and host lines need the profiler's Linux counters; elsewhere progress,
percent and ETA work without them.

## Sections

A stage marks its long parts with `build_profile.section`:

```python
from build_profile import section

with section('optimize maps'):
    ...

@section('stage night lighting')
def stage(...):
    ...
```

A section records wall time, its own CPU and the CPU of child processes it
waited for, so `cores` above 1 means its worker pool or map tools ran in
parallel. Without the builder the call costs two attribute reads and writes
nothing. For standalone commands set `AMIWIND_PROFILE_SECTIONS=FILE.jsonl`.

In `build-profile.json` each stage row lists its sections in one schema, the one
the Build Timeline and the Toolkit Monitor draw: `name`, `start` and `end`
(seconds after the first stage started; for a repeated section its first start
and last end), `cpu` (seconds, the section and its children), optional `detail`,
plus `calls`, `wall`, `cores_avg` and `phase` (a `build_profile.phase`).

The builder also times functions without touching their code:
`build_profile.instrument(stage)` wraps the functions listed for that stage in
`INSTRUMENT` (the image step's world, flora, sky, optimizer, heap and volume
passes; the world terrain and scenery loops; Census; the asset census), every
`ordered_map`/`completed_map` (as "parallel map: function", with the item count)
and every `subprocess.run` (as "exec qbsp", "exec vis", "exec make" ...). A
test fails when a listed function no longer exists, and a missing target is
reported in the profile, never silently dropped.

## Phases and the heartbeat

No part of a build runs silently. A stage marks its long steps with
`build_profile.phase`; the builder process watches every running stage for
silence.

```python
import build_profile

with build_profile.phase('CHIM stats', '273 frames', total=273, unit='frames') as timer:
    for frame in frames:
        ...
        timer.step(label=frame, line=True)     # counter (+ a progress line)
    timer.done('CHIM stats: 2768 models')
```

prints, in the stage's log:

```text
CHIM stats: started, 273 frames
[1/273 frames] CHIM stats: frames/x-11/y-01/frame.ccf
...
CHIM stats: 2768 models - took 38.0s, 23.1 cores
```

- **Start and end lines**: every phase prints when it starts and when it ends,
  with its wall time and its cores: the CPU of the stage process and every
  process under it (live worker pools included) divided by the wall time. A
  phase that raises ends with `NAME: FAILED (ValueError) - took ...`.
- **Records**: each phase is a line in the stage's sections file
  (`profile/sections/NN-stage.jsonl`, the same file as the sections above:
  `report` lists it) with its start and end as epoch times, wall, CPU, cores and
  its counter. The Build Timeline draws the phases as a strip under the stage's
  bar, also while the stage runs.
- **Without code changes**: functions in `build_profile.PHASES` are timed as
  phases by `instrument()` (the image step's world, sky, cull, optimizer, heap,
  pack, finalize and check passes, including the CHIM room actor bake that runs after the CHIM rooms install and
  before the actor ground check; world terrain; actor contact). The chim stage
  times its world conversion, validation, statistics, heap gate, zone walk and
  stair gate itself.
- **Heartbeat**: the builder (the parent process, so a stage whose child prints
  nothing at all is covered too) checks every running stage's log. After 30
  seconds without output (`AMIWIND_HEARTBEAT_SECONDS`, `off` disables it) it
  prints, and repeats after every further 30 silent seconds (every phase line and
  heartbeat starts with the time since the build started, `[+1h02m]`):

  ```text
  [heartbeat] chim: [112/273 frames] CHIM stats: frames/x-03/y-02/frame.ccf: still working, 4m10s, 1.0 cores (no output for 30.0s)
  ```

  naming the stage, its current phase and counter (from the phase timer;
  `(no phase recorded)` when the stage has none), how long that phase has run,
  and the cores the stage's process tree uses (the profiler's sampler). The
  last heartbeat and the current phase are also in `build-progress.json`
  (`stages[].phase`, `stages[].heartbeat`) and in `build.py status`.
- **Log level**: `--log-level quiet` (or `--quiet`) drops only the per-unit
  progress lines (`build_profile.progress`, `timer.step(line=True)`); start and
  end lines, heartbeats, warnings and errors always print. `verbose` is
  reserved for more detail.

The phase timer, the heartbeat and the log level only write logs and records
next to the run: `tools/build_profile.py` is outside every stage key
(`build_cache.INSTRUMENTATION_MODULES`) and `AMIWIND_LOG_LEVEL` and
`AMIWIND_HEARTBEAT_SECONDS` are ignored environment variables, so changing them
never rebuilds a stage; `tests/test_build_phases.py` checks that a stage's
output has the same SHA-256 with the heartbeat on or off and at every log
level. Origin: the chim stage of a 273-frame build ran its stair gate for about
44 minutes, and its statistics for almost 8 more, with nothing to show the time
([BUILD-PROFILE-SECTIONS-MISSING-36](bugs/BUILD-PROFILE-SECTIONS-MISSING-36.md)).

## Image step sub-phases (v0.0.36-dev3, 270 CHIM region cells)

Measured on the v0.0.36-dev3 full build (image step 1 h 22 min wall, 6.2 cores average on a 24-core budget):
`build_profile.py report` and `optimize` for the step and its sections, the end time of each sub-phase's output
file for the parts the profiler did not time yet, the builder's 30 s container CPU samples for the cores. "Reused by
hash" says whether the sub-phase's per-unit result is kept by the SHA-256 of its inputs. After = this change
(estimated until the next build measures it).

| Sub-phase | What it does | Wall | Cores | Serial or parallel | Reused by hash | After |
| --- | --- | --- | --- | --- | --- | --- |
| Scene copy, terrain, scenery, flora install | stage the converted world | 8 s | 4-10 | parallel copies | stage reuse | unchanged |
| Payload preflight, UI, torch, gallery staging | read-only checks, small conversions | 30 s | ~2 | serial | no | unchanged |
| Combat data, player view | NPC sheets, Arena fighters, player bodies | 42 s | ~20 | parallel | no | unchanged |
| Seyda Neen legacy region maps | convert the town into 65 region maps | 47 s | 19.6 | parallel | no | dead weight (see below) |
| Seyda Neen town flora | flora into the 65 legacy maps | 15 s | 1 | serial | no | dead weight |
| Harvest removal, QuakeC, actor annotate/bake | per-map passes | 19 s | 1-8 | mixed | no | unchanged |
| Payload preflight (again), sky assets | sky conversion and palette | 53 s | 1 | serial | no | to do |
| Guard torches | six guard models | 32 s | 1 | serial | no | to do |
| Exterior sky, hidden-surface cull, hand stamps, cell numbers | per-map passes | 21 s | 7 | parallel | pass cache | unchanged |
| World map optimizer | geometry/light/PVS sharing, 2,658 maps | 5 min 22 s | 21.7 | parallel | pass cache: 13 reused, 2,645 made | key fix to do |
| Harvest, actor contact, entity tracker, progress, arrivals | gates | 52 s | 1-20 | mixed | no | unchanged |
| Night lighting | lamp, glass and fog tables | 13 s | 1 | serial | no | unchanged |
| CHIM town frame maps (Balmora, Seyda Neen, Bitter Coast) | frame maps of the CHIM areas | 33 s | 1 | serial, world read 2x per map | no | world read once |
| CHIM region frame maps (270) | replace each region map by its frame map | about 23 min | 1 | serial, world read per map (about 5 s) | no | world read once, shared pool, pass cache |
| Frame-map heap, engine limits, stair walk, heap audit | gates on the final maps | in finalize 37 min 35 s | 5.9 | mixed | stair walk records | to measure |
| Fingerprints, audio and music, volumes, drives | payload and disk images | in finalize | ~1.8 during audio | audio serial | no | to do (BUILD-IMAGE-AUDIO-SERIAL-36) |

The region frame maps were the single largest idle stretch: `build_profile.py optimize` lists the image step at
1.2 of 24 cores for 24 min 49 s on the critical path (saves up to 23 min 35 s). Each region frame map read and
checked the whole 190 MB CHIM world again (`chim.validate.load_world`) for its placements; the image now reads it
once (`chim.frame_map.load`), makes the frame maps on the shared worker pool in table order (byte-identical with
one worker or many) and keeps each one in the image pass cache under the SHA-256 of its inputs (legacy map,
frame row, placement references, frame bounds and chunk grid, model files, activated-object header), so an
unchanged map is not made again (BUILD-IMAGE-CHIM-MAPS-SERIAL-36). Every part prints its start, counters and
"took X, N cores" (build_profile.phase, progress lines).

Dead weight in the same run (BUILD-LEGACY-TOWN-MAPS-SHIPPED-36): the image step converted 65 Seyda Neen region
maps and staged 270 open-world maps of CHIM region cells, ran every per-map pass on them and removed them before
packing (435,379,983 bytes in `chim-removed-legacy.json`); none of them shipped. The 42 `bm*` maps in the image
are Balmora interiors, not legacy region maps. The Seyda Neen frame map and its two special maps, and each region
frame map's point entities, are still made from those legacy maps; moving those sources to the game data is the
first part of the world map manifest (docs/BUILD_MANIFEST.md).

## How it is measured

Each stage runs through a small wrapper (`build_profile.py _stage`) that starts
the stage command unchanged (same arguments, working directory and
environment, plus `AMIWIND_PROFILE_SECTIONS`) and waits for it. Its child
resource usage gives the stage's exact CPU and largest process; Linux task I/O
accounting gives its disk bytes. A sampling thread in the builder reads, once
per second, `/proc` for every running stage's process tree (each process's own
CPU plus the CPU of the children it already waited for, so nothing is counted
twice) and the container's cgroup CPU and memory.

Measured cost (Docker on a 24-thread host): one sample of nine process trees
takes about 0.6-0.7 ms of CPU, so the default one-second interval costs under
0.1 % of one core; the wrapper adds about 40 ms per stage; output manifests
cost the time to hash what the stage wrote. Profiling never changes a stage's
outputs or logs (tested).

Limits:

- Linux gives every counter. Elsewhere the builder records wall time and jobs
  only; Windows runs stages unwrapped.
- Without task I/O accounting (Docker Desktop's kernel) bytes come from the
  container's cgroup: they cover everything in the container and are marked
  "I/O shared" when other stages ran at the same time. Files in memory
  (tmpfs) and writes not yet flushed are not disk bytes.
- Summed tree memory counts shared pages once per process.
- CPU of a process that leaves its stage's process tree (daemonized) is lost.

`--no-profile` (or `AMIWIND_BUILD_PROFILE=off`) runs stages unwrapped and
writes no profile and no manifests; such a run cannot be a reuse source.

## Stage reuse for development builds

```text
python tools/build.py ... --name dev-b --reuse-from out/build/dev-a
```

A stage is copied from the earlier run when its input fingerprint matches and none
of the files it read or wrote was touched by another stage at the same time. The
run's own scratch folder (`RUN/scratch`) is private to the run and never makes a
stage non-reusable (BUILD-REUSE-SCRATCH-UNDECLARED-33): before that fix release
candidate reruns reused 17 to 25 of 34 stages; with it the v0.0.33 final reused 30.
Since v0.0.49 release candidates and finals reuse like development builds by
default (the release kind never changes a key or switches a verified cache off;
[BUILD_CACHE.md](BUILD_CACHE.md)); the from-scratch build of the same commit is
its own release check (`--release-from-scratch`, or `--clean`).

Each stage has an input fingerprint, recorded in every build:

- its command line, with the `--jobs` value and every absolute location
  replaced by a token (`{RUN}`, `{REPO}`, `{DATA}`, `{TOOL:qbsp}`,
  `{WORKSPACE}`, `{PYTHON}`, `{EXTERNAL}`): a fingerprint holds content, not
  places, so a moved workspace or checkout keeps every fingerprint;
- the SHA-256 of the repository code the stage can run and of the data files
  that code names (see below); prose (`*.md`) and tests do not count;
- the game input hashes from the build's input lock, when the stage reads
  `--data-files`;
- the map compilers and other programs it runs, and every other file or folder
  outside the run named on its command line (by content);
- the `AMIWIND_*` environment variables its code names, the Python version and
  package versions;
- the fingerprints of the stages it depends on, so a change reaches every
  stage after it.

Which code counts (`--fingerprint-scope`, default `units`): starting from
the stage script, the builder reads the source and follows what can run: a
module's top level when it is imported (its `if __name__ == '__main__'` block
only for the script itself), and each function once something reached names
it (a call, a reference such as a worker passed to the pool, `module.name`, a
re-export). Imports inside a function count only when the function is reached.
Classes, decorated functions, `from m import *`, `getattr()`/`vars()` on a
module and `globals()` count the whole module; `import_module()` with a
computed name, `eval()` or `exec()` count every file. A data file counts when
reached code names it: a path such as `ROOT / 'config' / 'towns.json'` names
that file, a path that ends at a folder or continues with a computed part
(`ROOT / 'config' / name`) names the whole folder, and a bare file name names
every file with that name. A folder put on the import path
(`sys.path.insert(0, str(ROOT / 'tools'))`, `sys.path[:0] = [...]`, `site.addsitedir()`, or a loop over
folders that only go on `sys.path`) is where Python looks for modules, not a read: the imports are followed
and no data file counts for it (BUILD-KEY-OVERBROAD-33: it used to count every file under `tools/`, so a new
bug page rebuilt the scene and CHIM stages). A whole path chain counts once
(`ROOT / 'config' / 'towns.json'` names that file, not also the folder
`ROOT / 'config'`), a module string constant in a path counts as its value,
and `ROOT / 'config' / row['config']` counts the files that JSON registries in
that folder, themselves named by the code, give under that key
(`config/towns.json` rows name `config/balmora.json` and the other town
files); with no registry or no such value it counts the whole folder. With
scope `units`, a reached module counts as its import-time code (everything
outside its plain functions, including the default values of every function)
plus the source of each function the stage reaches, so an edit to a function
no stage reaches (the build plan code in `build_parallel.py`, which every
stage imports for its worker pool) keeps every fingerprint; data files are
hashed whole. Since v0.0.48 stage keys use import-time form 3: a plain class (no decorator, metaclass or
repository base class; a body of methods and literal attributes) is no longer import-time code but a unit of its
own, its body and each method (`Class.method`), so an edit to a method a stage never reaches keeps its key (an
instance reaches every method; `Class.static_method()` only that one; BUILD-STAGE-KEY-WHOLE-CLASS-48: one method
of `actor_grounding._Fitter` rekeyed the CHIM stages). Code a stage hands to a cache key
(`UnitCache.open(..., __file__)`, `PassCache.open(..., (__file__, 'worker'))`, `source_digest`) counts with the
reach that key reads, whole files (BUILD-ROOM-BATCHES-KEY-UNDERDECLARED-48), and the Python files of a folder the
code reads as bytes (`FOLDER.glob('*.py')`) count whole (BUILD-MWSCRIPT-KEY-UNDERDECLARED-48). A reuse source keyed
in an older form is compared in that form, so the change of form rebuilds nothing; the per-unit caches keep their
own forms. Scope `symbols` follows the same code but hashes whole files and
keeps the earlier path rules. Instrumentation modules (the profiler, its
progress display and the stage cache itself, an explicit list in
`tools/build_cache.py`) observe a build but never change its outputs; they
never count, so a profiler fix keeps every fingerprint. The earlier methods,
`--fingerprint-scope symbols` and `--fingerprint-scope modules` (every import
of every imported module, and every file in a top folder the code names), stay
selectable. `tools/build_cache.py explain RUN OLD_RUN`, `predict OLD_RUN` and
the build's reuse report name the files whose part of a fingerprint changed.

Environment variables work the same way: a stage's fingerprint has only the
`AMIWIND_*` names its reached code mentions (the stair rule,
`AMIWIND_STAIR_MITIGATION`, reaches the converters that import
`mesh_geometry`, not media or music); code that builds such names at run time
gets every `AMIWIND_*` variable. Worker counts, bookkeeping and interpreter
locations never count.

The read trace checks the fingerprints in every profiled build. The stage
wrapper puts a small hook first on the stage's `PYTHONPATH`
(`profile/trace-hook/sitecustomize.py`, written into the run; it chains to the
interpreter's own `sitecustomize`); every Python process of the stage, workers
included, lists the repository files it opens for reading and any Python file
it loads from outside the checkout (`profile/reads/NN-stage.txt`). After the
stage, the list is compared with what the fingerprint covered
(`profile/closures.json`): a file the fingerprint left out, a repository file
no fingerprint covers (prose, tests) or code from outside the checkout marks
the stage's outputs as not reusable, prints a warning and is a bug to
register. With scope `units` the same hook lists the first run of each
repository function (`@file<TAB>function`, a method as `Class.method`, once per function, through
`sys.monitoring` on Python 3.12 and later); a function that ran but whose
source the fingerprint left out marks the outputs as not reusable the same
way. The hook only observes; `AMIWIND_STAGE_TRACE=off` switches it off.
It does not see files read by other programs (map compilers, ffmpeg): those
are named on the command line and fingerprinted there. The same hook also lists
the run-folder files the stage's Python processes write, rename to, link or
remove (`>path` lines), which credits outputs to the stage that wrote them
(below).

`--reuse-from OLD_RUN` then copies a stage's outputs from the old run instead
of running it when all of these hold; otherwise the stage runs, and the build
prints the reason for every stage:

1. the fingerprint is the same and the stage passed in the old run;
2. its output manifest is complete and no stage that ran at the same time
   changed the same path, unless the write trace shows that only one of the
   two wrote it: the file is then that stage's output and leaves the other's
   manifest (`attributed` in it; BUILD-REUSE-ATTRIBUTION-33). With a writer the
   trace cannot see (a map compiler) or two writers, both stay not reusable;
3. every stage it depends on is reused too;
4. the files it wrote still exist in the old run: a file a later stage
   replaced is only skipped when that later stage is reused as well;
5. every file to copy still has its recorded SHA-256 (checked before the build
   starts, and again while copying);
6. the run-folder files named on its command line have the content they had
   in the old run.

"Wrote the same outputs" (the check that lets a stage after a rebuilt one be
reused) compares every output except diagnostics: `*.log` files and the
reports `chim-stats.json`, `chim-timing.json`, `gallery-cache.json` and
`world-terrain-cache.json`, which carry tool timings, wall time and cache hit
counts. Diagnostics are recorded and copied like any output, but no stage may
read one: the stage trace lists every run-folder diagnostic a stage opens
(`<path` lines), and a stage that reads one another stage wrote is not reused.
Every other output must be byte-reproducible: receipts carry no wall time,
worker counts or run paths (BUILD-OUTPUTS-NOT-REPRODUCIBLE-33).

Reused stages show `reused (fingerprint ...) from OLD_RUN` in `build-state.json`,
the stage log, the profile and the summary. A copy that fails its SHA-256 check
during the build runs the stage instead, unless earlier reused stages left out
files that this stage replaces; then the build stops and asks for a build
without reuse.

Never reused: `engine` (the Amiga SDK is not fingerprinted; it compiles in
seconds) and the image (`image`, `dry-run-image`), which is always assembled
and verified from the stage outputs. Inside the image step, development
(`-devN`) builds reuse the results of per-map passes for map bytes they have
seen before: the BSP optimizer, the hidden-surface cull and the stair walk look
up `WORKSPACE/cache/image-passes` by the input map's SHA-256, the pass options
and the SHA-256 of the pass's own repository sources (`tools/pass_cache.py`),
and run only on maps without a result; the exterior sky pass does the same. Maps
and receipts are byte-identical with and without the cache, apart from each
receipt's `pass_cache` entry, which counts the run's hits and misses
([BUILD-IMAGE-NOT-INCREMENTAL-33](bugs/BUILD-IMAGE-NOT-INCREMENTAL-33.md)).
Release candidates and finals use it too (by default since v0.0.49;
`--release-from-scratch` turns it off for the from-scratch check), so a release
build whose image step failed late resumes from the maps it had finished
([BUILD-IMAGE-NO-RESUME-33](bugs/BUILD-IMAGE-NO-RESUME-33.md)). Measured on 120
maps of the v0.0.33 rc1 payload (4 workers): cull, optimizer and stair walk
1,440 s with an empty cache, 20.3 s with every result cached.

The same rule holds inside long stages: a world scenery or world flora region
that finished is stored by the content hash of all its inputs
(`tools/pass_cache.py` `UnitCache`: the region record, its input map, every
shared input by content, the code that makes it and the settings it reads), so a
stage that failed late, or runs again after a small change, converts only the
regions whose inputs changed. See [BUILD_CACHE.md](BUILD_CACHE.md) for the rules
every unit follows.

### Reuse audit

```text
python tools/build.py --reuse-report RUN [--json FILE]
```

Read only. Lists every stage a `--reuse-from` run did not reuse, with the
recorded reason, as EXPECTED (a real input change, a stage that never reuses,
the image step, a stage that follows an expected rebuild, a stage the reuse
source had itself reused without a file a later stage replaced there and that
runs again because that later stage runs again) or UNEXPECTED (a key
that changed only with files no output depends on, such as the release file
list; a key that changed only with the pool scheduling modules or `VERSION`, for a
stage that does not write the version into its outputs; a refused old record; outputs of a rebuilt stage that differ although its
inputs did not, with the files that differ). Exit status 1 when anything is
UNEXPECTED, 2 for a run made without `--reuse-from`.

Release candidates and finals use the pass cache by default since v0.0.49
(`--release-from-scratch` turns it off; before, only with `--allow-release-reuse`,
project decision 9 October 2026), the same rule as the
world terrain and media caches: the from-scratch reference build runs separately
on the same commit, and its payload is compared file by file with the release
payload before the release; the hit counts in the optimizer, cull and stair-walk
receipts show what was reused. Without the option every pass runs on every map.

The stair walk (`--stair-walk`) is off by default since v0.0.47-dev1 (decided for the project, 20 October 2026,
BUILD-STAIR-WALK-OFF-46): `auto` means off, and no build walks stairs unless asked with `flights` or `all`. When asked,
`flights` walks only the steps of flights (what `auto` meant in every build from v0.0.46)
(`flights`: the rows that can stop a build; the v0.0.46-dev1 CHIM world had 1,971 flight rows among 261,038 steps
and ramps). `--stair-walk all` walks every step and ramp (the advisory findings too): a nightly or beta run on
request. Before v0.0.46, `auto` meant `all` for development builds, and the CHIM gate walked every step and ramp
whatever the scope (BUILD-STAIR-WALK-SCOPE-KEY-46). A flight row is the same in both walks; a flights receipt says
so (`scope`). Measured costs: [performance/BUILDER_PROFILE.md](performance/BUILDER_PROFILE.md).

What a CHIM frame's walk is keyed by (`--stair-walk-key`): `reach` (the default with the workspace's own walks)
keys each core of the frame by its steps and ramps (the items the walk tests, by their SHA-256) and by the collision
and polygons within the walk's reach of them: every chunk and placement whose polygons or collision box meet the
placements the items belong to, grown by how far a walk traces and tests ground and headroom (about 72 units,
made from the walker's own constants). Collision far from every stair (a rock's walls and underside out of reach)
no longer walks a frame again. A core's items are found once and kept in the pool by the SHA-256 of the
placements that can make them (`stair-walk-items/`), so an unchanged core does not read its frame to know them.
`frame` keys a frame by every chunk and placement it holds (the key before v0.0.46, and the default with
`--stair-walk-cache records`, whose shipped records are keyed by it). The sample check below stops the build when a
key missed an input, and `tests/test_chim_stair_reach_key.py` traces walks and checks they read nothing outside
their key.

The stair watch list (`config/stair-watch.json`, `--stair-watch FILE|off`) names the places stair and walkway
bugs reported (CHIM cells, frames and source references; interior maps): every build walks the frames and maps
holding them again, even when their walk is reused, and stops when a walk again differs from its record. A bug page
that reports a stair or walkway problem adds its place to the list, so the walk is the redundancy check for those
places. `--stair-walk-places FILE|ID,...` (development builds only) walks ONLY the named places: watch list IDs,
cells `x:y`, frame paths, source references `ref:N` and maps `map:NAME`; nothing else is walked or gated, and the
rows are reported, never stored.

The image step no longer walks the CHIM frame maps (`vf*.chim`: an empty world with the frame's entities and
collision boxes; v0.0.46-dev1 walked 1,353 of them and found no row): the CHIM stair gate walks every frame on its
real collision. `AMIWIND_STAIR_WALK_FRAME_MAPS=on` walks them again (the method before v0.0.46). The interiors and
other legacy maps keep the map key (the SHA-256 of the map's bytes): a compiled map's collision is one tree, so a
change anywhere in the map changes what a walk could read.

The stair walk is a check of the collision, not a step every build must repeat. Every legacy map and every
CHIM frame is walked once; its rows are kept by the SHA-256 of what the walk reads (the map's bytes, or the
frame's terrain, placements and placed models) together with the walk's own code and the stair rule, and reused
while that is unchanged (`--stair-walk-cache cached`, the default). The scope above says WHAT is walked: with the
cache, `all` never means walking an unchanged map or frame again. On every build a few reused ones (two by
default, `--stair-walk-sample N`, seeded and named in the log) are walked again and compared with their stored rows;
a difference stops the build, because it means the key missed one of the walk's inputs. `--stair-walk-cache full`
walks every map and frame again: for regression and beta-test runs, such as the from-scratch reference build
before a release or a nightly check, not for everyday builds.

Each stored walk is a record (`tools/stair_records.py`): its key, the rows and their counts by result, the walk's
code version, the AmiWind version, the source commit, the run name, the master builder request and the host time,
with the SHA-256 of the record itself. When the run that wrote it has passed every gate as a build of the master
builder (`tools/aw.py`), the master builder marks the run's records as checked (`stair_records.py promote --run
RUN`). A CHIM frame's record also holds the walk's outcome (`passed`: no flight step the standing box cannot walk;
`failed`) and its provenance: `walked_at` (ISO 8601 with the zone), the AmiWind and CHIM versions, the source commit
and the run. A pass is a pass (BUILD-STAIR-PASS-NOT-KEPT-41): in development builds a frame walk that passed is
reused while its key is unchanged, whatever the rest of the build that walked it did, so a build that fails late
keeps every frame that passed and its rerun walks only the frames that failed or changed. A failed walk is reused
only with a check mark (a private test's accepted known finding). Release candidates and finals keep the check-mark
rule: they reuse only checked records (and nothing with `--release-from-scratch`). The rule is
`AMIWIND_STAIR_WALK_REUSE` (`passes`, the default of development and stand-alone runs; `checked`, the earlier rule,
selectable for any build; `passes` is refused for an rc or final); it never keys a stage. The legacy maps' walks keep
the check-mark rule. A damaged record, or one written again since its check, is walked again. The build log and the
stair report name every map and frame as "walked", "reused from RUN (VERSION, COMMIT, TIME)" (checked) or "reused
pass from RUN (VERSION, COMMIT, TIME)", and the master builder's result counts the records it marked and how many
maps and frames the build reused and walked. The CHIM stage prints one line per frame as its walk
finishes. Since v0.0.42 it runs the stair gate first, right after the validation and before the statistics, the
heap gate and the zone walk (`tools/chim_build.py --gate-order stairs-first`, the default): with the stored passes
an unchanged frame costs nothing, so the gate walks the frames that changed and a stair failure stops the step
before anything else runs. `--gate-order stairs-last` keeps the earlier order (heap gate and zone walk first:
BUILD-CHIM-HEAP-GATE-LATE-36, BUILD-CHIM-STAIR-WALK-UNCACHED-36); the reports are the same either way. The receipts record the mode and how many maps or frames were reused, walked
and walked again.

The CHIM visibility units follow the same rule (`chim.world.chunk_visibility`). A chunk-visibility block is keyed by
the ground, the occluder grid (the solid columns of the placed collision pieces: a collision change that moves no
column keeps it), the chunk tops and the ring. A placement-visibility block is keyed in the frame's own placement
numbering (id minus the frame's first id) by what it reads: the ground, the occluder grid, its viewer chunks, their
candidates and near sets and those candidates' boxes; its result is numbered back. Keyed by the world-wide ids, one
placement more in an earlier frame recomputed every later frame's units (BUILD-CHIM-VIS-RECOMPUTED-48); units of
that earlier key are still found once and stored in the new key. Fire rows (`chim.flames`) are written after the
visibility rows and key none of them.

A CHIM frame's key (key form `chim-stair-key-2`, `chim.collision.frame_stair_parts`) holds exactly what its walk
reads: the frame's path, the stair tile and the frame grid (grain, low corner, size); per chunk its place and the
lumps of its terrain image the walk reads (planes, vertexes, nodes, texinfo, faces, clipnodes, leafs, edges,
surfedges, models); per chunk its owned placements in order (reference, origin, yaw, box and the same lumps of the
placed model's image, by content). It never holds the world's texture table entries (the textures lump), the
world's model numbers, placement ids, reach records or lighting, which change in every frame when a frame is
added anywhere in the world (the coast2 build walked all 330 frames again for that reason, although 220 of the
237 frames it shared with dev5 had byte-identical collision). The walker's code in the key (code form
`chim-stair-code-1`, `chim.collision.stair_key_sources`) is the frame worker (`stair_task`) and the code of it a walk
runs, in the files of `chim.collision.STAIR_WALK_CODE` only: the walk and the stair rule (`tools/stair_walk.py`), the
frame's scene, polygons and trace (`tools/chim/collision.py`, `tools/audit_walkability.py`, `tools/player_hull.py`)
and the frame reader (`tools/chim/validate.py`, `tools/chim/format.py`, `tools/chim/cut.py`,
`tools/chim/__init__.py`), each counted by the units the worker reaches. The collision compilers
(`tools/collision_bsp.py`, `tools/prepare_mesh_bsp.py`, `tools/chim/models.py` ...), which the frame reader's
imports name, the CHIM_VERSION label and the known-findings table are not in it: what the compilers made is in the
key already as the frame's collision lumps (v0.0.41-dev5 walked 604 unchanged frames again because CHIM_VERSION went
from 0.2.0 to 0.2.1). `tests/test_chim_stair_pass.py` keeps the list to the code a walk runs: a traced walk calls
nothing outside it, and no reached function of those files imports or names another repository module. Records
written under the earlier code form are not found under this one (one more walk of every frame, never a silent
reuse). A walked frame says why in its line and in the report: `walked: no earlier walk of this frame in the pool`,
`walked: inputs changed: 2 of 41 (chunk 0,1 terrain, chunk 0,1 placements)`, `walked: walker code changed (...)`,
`walked: its stored walk did not pass and has no check mark of a passed master build`, or (release rule) `walked:
its stored walk has no check mark of a passed master build`; one summary line counts the reasons. The pool keeps, per frame, the key and the
inputs of its last stored walk (`stair-walk-frames/`, bookkeeping only).

The walk itself is scheduled as units: the count step (one read per frame, in parallel) gives the steps and
ramps of every 1024-unit core; cores without any are skipped (they walk nothing), the others are cut in core
order into runs of about total / (4 x workers) steps, and the runs go to the full worker count largest first,
results taken as they finish. A worker reads a frame once per unit instead of once per core, and one large frame
no longer tails the gate. The rows are the per-core walk's, byte for byte (tests/test_chim_stair_key.py).

How many workers walk at once is set by cores AND by memory (CHIM-STAIR-GATE-POOL-BROKEN-42, `tools/chim/stair_pool.py`).
Each worker reads a whole frame (its scenes and polygons): measured high-water marks were 259-548 MiB for region
frames and 2,643 MiB for the whole-city Vivec frame, about 100 MiB plus 17 times the frame's placed bytes (chunk
images plus the model image of every owned placement). The gate estimates every frame to walk as 128 MiB plus 18
times its placed MiB and, since v0.0.44, admits each walk unit at its own frame's size: units start while 80 % of the
memory left in its container holds them beside the units in flight (cgroup `memory.max` minus `memory.current` less
the reclaimable file cache; the host's MemAvailable only when the container has no limit), largest first, and a
larger unit waiting at the head keeps its room reserved (`tools/build_parallel.py governed_map(item_mib=...)`).
Before, every worker got the share of the largest frame: the v0.0.44-dev1 build walked on 4 of 24 workers at
2,855 MiB each while its region frames hold about 300 MiB (BUILD-CHIM-SERIAL-SECTIONS-44). The line `CHIM stair gate: workers: ...` says which bound won and why. A worker lets go of
the frames it keeps built, oldest first, until the next frame fits its share. A map in the step's shared worker pool
keeps to the tasks it asked for (`tools/build_parallel.py completed_map`): before, 11 walk workers asked meant 22
frame walks at once in the 24-worker stage pool, and the Vivec palace sandboxes ran out of memory. A worker that is
killed anyway stops the gate with the unfinished units, their frames and estimates, the peak of the finished
units, the container's memory and its out-of-memory kill count. Measured on the Vivec palace sandbox frame
(83,247 steps and ramps) in a 12 GiB container: 3 workers by memory (cores allowed 11), passed in 511 s. None of
this is in the walk key: `stair_pool.py` is outside `STAIR_WALK_CODE`, so stored walks stay valid.

Each flight is walked once, where a player can stand on it (BUILD-STAIR-WALK-BORDER-COPIES-41, v0.0.42). A CHIM
region frame owns one cell, but its map holds copies of everything within about 3,500 units of it so that its edges
can be drawn; the engine changes to the next open-world map 64 units past the cell (`aw_world.c`
`AW_WorldDestination`), so most of those copies can never be walked from the map that holds them. A region frame's
walk therefore covers its walk area (`chim.collision.frame_walk_areas`): the cell it owns (`core` in the build's
ownership table `chim-regions.json`) plus `leave_margin` (64) plus the standing box's half width (7.32), so 71.32
units on every side. A step or ramp whose riser point lies farther out is a copy: it is walked in the frame that owns
its cell, or, for a classic cell, by the image step's stair walk on that cell's own map. Steps, ramps and flight marks
are still found on the whole 1024-unit core (`chim.collision.stair_task_in`), and only the walking is restricted, so
every row is the row the whole-frame walk gives for the same step, and a flight that crosses the area's edge keeps
its mark. Cores outside the area are not tasks at all. A town's frame (no ownership row) is walked whole, as before.
`--stair-walk-area frame` (`AMIWIND_STAIR_WALK_AREA`, also a `tools/chim_build.py` option) keeps the earlier
whole-frame walk.

An area walk is a record of its own: its key is the frame's key plus its walk area (`chim.collision.area_part`),
under the area walker's own code digest (`chim.collision.stair_area_key_sources`, the units `stair_task_in` reaches
in `STAIR_WALK_CODE`); whole-frame walks keep their keys, so their records stay valid. When a frame has no area
record yet but an unchanged whole-frame walk is stored, the area walk is taken from it without walking
(`chim.collision.derive_area_rows`: the whole-frame rows inside the area, which are exactly the area walk's rows) and
kept as a record with `derived_from` (key, record SHA-256, run). Under the release rule (`checked`) only a checked
whole-frame walk is used; under `passes` any intact one whose area rows pass, so a frame whose whole-frame walk
failed only on a border copy becomes a pass of its cell. The seeded sample walks derived frames again too and stops
on any difference. The report adds `walk_area` (mode, frames with an area, cores skipped, frames derived) and
`walk_counts`: the rows against the distinct places they test (placement, kind and riser point on the island, to the
unit); the gate prints both and warns when there are more than 1.2 rows per place.

Measured on the v0.0.41 final CHIM world (726 frames: 723 region frames, 3 towns), steps and ramps found by the
count step: whole frames 2,672,454 for 869,846 distinct places (3.07 per place); walk areas 853,398 for 771,793
places (1.11 per place: strips about 143 units wide along each shared edge are walked by both neighbours, and the
three town frames are walked whole). 2,718 distinct flight
places, 2,472 of them inside a CHIM frame's walk area; the others lie in classic cells and are walked on their own
maps. Vos edge test world (frames 12,13 and 12,14, the dev5 failure): see BUILD-STAIR-WALK-BORDER-COPIES-41.

The steps of a core are found the same way as on the whole frame (v0.0.42 stair round 2; one change to the
walker's code, so every frame was walked once more). Flight marks: a core's steps are found on the core plus
`stair_walk.FLIGHT_MARGIN` (128 units; `chim.collision.stair_polys` gives the polygons that far out), the flights
are marked on all of them, and only the core's own steps are kept, so a flight that crosses a core line keeps its
mark in both cores (STAIR-FLIGHT-CORE-SPLIT-41; v0.0.41 final world: 39 of 5,646 flight steps lost their mark per
core, now 0, and none gained). Position: every edge pair of two level faces is tested (bins searched wide enough
for the parallel and offset tolerances), the pair with the longest shared edge is taken whatever order the bins
hold them in, every threshold is met within `GRACE` (1e-6 units; normals 1e-9), and a face's normal is taken
relative to its first corner, so a placement gives the same steps in each frame that places it
(STAIR-DETECT-POSITION-41; places found only in a neighbour frame's copy 107 -> 63 on the v0.0.41 world, the rest
open). The count step and the walk are slower by the wider search: about 1.5 times the candidate time on the
heaviest frame (x+04/y-12: 20.1 s -> 31.8 s for all its cores), small next to the walk.

Known-good stair records (v0.0.42 plan 1.0b, B14). The pass records above live in a build workspace's cache. The
known-good stair records ship the same walks with the source as public data (`config/stair-records/*.json`,
`tools/stair_records.py`), so that a build from the same game data does not walk: one entry per CHIM frame, under
the frame walk's full key (the SHA-256 of exactly what the walk reads, `frame_stair_parts` plus the walk area, with
the walker's code digest and the stair rule: `PassCache.key`), with the frame's path and cell, the walker digest,
the rule, whether it has a walk area, the outcome, the counts by result, the SHA-256 of all its rows, every flight
step as `[reference, kind, x, y, z, direction x, direction y, rise, result, status]` and the SHA-256 of those, and
the entry's own SHA-256. Hashes, references and coordinates only: no game data. `--stair-walk-cache` chooses:
`records` (the default of a build without `--developer-mode`, so the end user's): a frame's walk is taken from
this workspace's own walks, else from the shipped records (`reused from the shipped records (0.0.41,
v0.0.41-chim.json)`: its flight steps are the report's rows, the other rows are counted); a frame in neither
(another converter, other game data) is named in the log and the report (`records.unmatched`) and NOT walked;
`cached` (the default with `--developer-mode`, every master-builder build): walk what changed, the shipped records
are not read; `full`: walk everything, ignoring every stored and shipped walk (regression and nightly reference
builds). A sampled shipped frame (`--stair-walk-sample`) is walked again and its flight steps must equal the shipped
ones, else the gate stops (a key that misses an input); an entry whose SHA-256 does not match is never used and is
counted as damaged. Legacy maps have no shipped records: in `records` mode they are walked as with `cached`.
Written by `stair_records.py export --world W --cache C --out F --version V --commit C --run R` from a full walk
into a pass cache C (it refuses when a frame has no stored walk). Shipped: `v0.0.41-chim.json`, from the v0.0.41
final CHIM world (run 2026_10_16_v0.0.41_release_ce7ace6) walked in full with the v0.0.42 walker: 726 frames, all
passed, 1,233 flight steps, 498,667 bytes (SHA-256 92662f56...). The full walk took 32 min on 16 workers (frame keys
about 15 min, the count step 9.6 min, the walk the rest). Any edit to the walker's code changes every key, so the
file must be written again with each walker change (planned for the nightly reference build; by hand until then);
a new world form (a converter change) gives new keys too.

Counted progress lines put the counters first (`tools/progress_line.py`): `[done/total work | done/total
containers] stage: unit: result`, the real work units first. The stair walks count their steps and ramps before
they start (polygons only, in parallel; a reused map or frame counts its recorded rows), so a line reads
`[12034/15415 stairs | 246/273 frames] CHIM stair gate: frames/x+21/y-08: 51 steps and ramps, 0 failed (walked)`,
with `(reused from RUN (VERSION, COMMIT, TIME))` or `(walked again: sample, matches its record)` for the others.

Scene stages that change an earlier stage's folder in place limit reuse: when
such a stage is rebuilt, the earlier stages whose files it replaced are rebuilt
too, because their versions no longer exist in the old run.

`--reuse-mode hardlink` links instead of copying and marks the linked files
read-only in both runs, so a later stage that tries to rewrite one fails
instead of changing the old run; it is refused as root (copies are made).
A scene stage that edits its inherited tree in place first makes such files private and writable
(`mwad.paths.unshare_tree`: same bytes, new inode); the stage's record leaves out every file it only unshared (the
storage pool object it was linked to has the SHA-256 the file still has), so its record lists what it wrote,
whether the stages before it were reused or ran (BUILD-REUSE-OUTPUTS-DIFFER-48: door audio recorded 2,124 files
after reused stages, 18 after stages that ran, and seven stages after it were refused as "outputs differ").

Assumptions, checked elsewhere: stage outputs do not depend on the worker
count (parallel tests; the from-scratch gate); the map tools give the same
result for the same input.

Why fingerprints do not change, or do:

```text
python tools/build_cache.py explain NEW_RUN OLD_RUN
```

Which stages a build from this checkout could reuse, before building (a dry
run on fingerprints only: no game data is read and no outputs are checked, so
the real plan can only reuse fewer):

```text
python tools/build_cache.py predict OLD_RUN
```

Inside the world terrain stage (2,532 maps), each map is also cached on its
own, across builds, in `WORKSPACE/cache/world-terrain-v1`: the key is the
map's own text, the texture WAD, the vis mode, the converter's code and data
files (counted as for the stage fingerprints), the map compilers' SHA-256, and
the Python and package versions. A hit is checked against its recorded
SHA-256 before it is used; anything else converts the map. So when the stage
reruns only because an earlier stage changed, the maps whose inputs did not
change come from the cache. Release candidates and
finals use it too since v0.0.49 (they convert every map, as the from-scratch
gate does, with `--release-from-scratch`); `--no-unit-cache` turns it off for a
debugging build.

The media stage (every owned sound and movie) and the intro stage (the
opening movie) keep each converted file in the asset pool,
`WORKSPACE/cache/asset-pool-v1` (`tools/file_cache.py`): every file once, by
its own SHA-256 (`objects/`), whatever stage or build made it, and per-file
reuse keys (`keys/`) that name the output a conversion gave. A key is the
source file's SHA-256, the conversion settings (format, size, rate), the
SHA-256 and version text of `ffmpeg` (and `ffprobe`, and the Pillow version,
for movies) and the source of the conversion code, so a changed input
converts only the files it touches. A hit is copied and checked against its
SHA-256; a missing or damaged object is converted again and stored again. The
builder never deletes pool files (the garbage collector decides what expires,
and the same pool keeps stage outputs, disk images and packages once:
[BUILD_CACHE.md](BUILD_CACHE.md)). The stage outputs are byte for byte those of a run without
the cache. The build summary lists, per stage, how many files came from the
cache and how many were converted (`profile/file-cache/STAGE.json`; a stage
reused whole writes none). Same rules as above: development builds only,
`--no-media-cache` turns it off for a debugging build. The media stage
converts on the stage's whole worker share and grows with the scheduler's
allowance as other stages finish (`build_parallel.ordered_map`).

Runs made before the fingerprint change (`amiwind-stage-cache-v1`) are not
reuse sources; the plan says so for every stage. One build without reuse
makes a new reuse source.

Releases: since v0.0.49 release candidates and finals take `--reuse-from` like
development builds (the version keys only what shows it, BUILD-CHIM-KEY-VERSION-48,
so a final built from its passing candidate reruns the engine and the image); the
receipt records it. The from-scratch reproducibility check is its own gate:
`--release-from-scratch` (or `--clean`) refuses `--reuse-from` and the per-file
caches for a release version.

Across runs and workspaces, `--prerendered DIR` keeps the outputs of chosen
stages (CHIM worlds, interiors, region maps) with these same fingerprints and
manifests, and uses them in later builds: see
[Speed](chim/build_guide/SPEED.md#prerendered-store---prerendered-dir).

The check on reuse itself is the from-scratch build: a build with the repo
builder in a fresh workspace (no reused stage, no caches), compared file by
file with the image a reuse build made from the same commit. Any difference
is a reuse bug and is registered. It runs before every release, after any
builder or converter change, and on a schedule; each such build is recorded
with its date, commit, duration and result.

### Caches of another workspace

The per-file caches (the media and intro stages' asset pool, the image step's
per-map pass cache) live in the build's workspace. When `--reuse-from` names a
run in another workspace, the builder also reads that workspace's caches,
read-only: an entry found there is verified like any other and copied into
this build's own cache; nothing is written to the other workspace
(`AMIWIND_CACHE_FALLBACK`, set by the builder; never part of a stage
fingerprint; BUILD-CACHE-PER-WORKSPACE-33). The whole-builder profile with
measured stage and section costs, failure costs and open items:
[performance/BUILDER_PROFILE.md](performance/BUILDER_PROFILE.md).

### Cache provenance

Every cache entry also records where it came from (`tools/cache_provenance.py`, one record format
`aw-cache-provenance-1` for every cache; CACHE-NO-PROVENANCE-36): the cache and key, the input manifest (each
input's name, SHA-256 and size, and the parameters, so a changed key can be explained), the output SHA-256 (never
empty) and its kind, the host time with offset, the AmiWind version, commit, run, master builder request and job,
the SHA-256 of the build's tools, the CHIM version and world format, a retention block and how each field was found
(exact, estimated, inferred or N/A).

Every pass names the unit it stores (the map, CHIM frame, region frame, route, head or model group) and the
inputs its key was made from one by one (`cache_provenance.name_unit`), together with the pass's own sources
and options, so the reuse audit can say which input of a recomputed unit changed.

| Cache | Where the record is |
| --- | --- |
| stage records (`profile/manifests/STAGE.json`) | `provenance` field (output = the unit tree's stage hash) |
| image passes, stage units, stair-walk records | `provenance` field of the entry's JSON |
| asset pool keys | `provenance` field, or `KEY.meta.json` beside a key written by `point` |
| asset pool objects | `.provenance/objects.jsonl` (named by SHA-256; who stored them, when) |
| CHIM unit cache | `KEY.meta.json` beside each pickle (the pickle's bytes unchanged) |
| world terrain cache | `provenance` field of the entry's `conversion.json` |
| entries written before 11 October 2026 | `.provenance/backfill.jsonl` of the cache |

Each cache also keeps `.provenance/reuse.jsonl` (one appended line per reuse: reuse count and last reuse per key)
and `.provenance/pins.jsonl` (entries pinned for the garbage collector: `cache_provenance.py pin`).

Rules: provenance never changes a stage, unit or pass key (the writers' provenance statements are left out of
every key computation, and the module reads only the environment); a missing, estimated or N/A field is never a
reason to rebuild; a reused entry whose output no longer has its recorded SHA-256 is a miss, built again, and never
fails the build. Commands:

    python tools/cache_provenance.py summary CACHE...          # entries, bytes, with/without provenance, ages, versions
    python tools/cache_provenance.py show KEY|PATH [--cache CACHE]
    python tools/cache_provenance.py backfill CACHE... --builds WORKSPACE/build [--trials TRIALS.jsonl] --dry-run

## Build speed in CHIM

The streamer's builder keeps this profiler and records a fingerprint per pack,
so a change rebuilds only the packs it reaches. See
[WORLD_STREAMER.md](WORLD_STREAMER.md).

### CHIM world conversion (v0.0.42)

The chim stage's world conversion is timed in phases, each with its start and end line,
time and build-machine threads used:

| Phase | What runs | Workers |
| --- | --- | --- |
| `CHIM world: areas side by side` | every region frame and, when the region frames fill the workers at least four times over, the towns too (towns first), one area per worker | the stage pool |
| `CHIM world: areas in turn` | areas not prepared side by side (a sandbox with few region frames, or `AMIWIND_CHIM_TOWN_PREP=after`), one after another, each with every worker | inside each area |
| `CHIM world: aprons, ownership and effects` | the apron dispositions, the ownership checks of every frame's source (cores found through a grid of cells) and the texture effects | one |
| `CHIM world: visibility rows` | every frame's placement layout and visibility rows on the workers, one frame per task, largest first; a town's layout there too, then its row blocks over every worker (`AMIWIND_CHIM_VIS_ROWS=frames-parent`: the layouts in the parent, the v0.0.43 method; `serial`: one frame after another) | the stage pool |
| `CHIM world: pack` | the world files, frame by frame in pack order: one walk, because model, texture and terrain ids are handed out as the walk first meets them (serial by nature; the visibility rows come packed from the workers) | one |
| `CHIM world: far terrain` | each frame's far terrain layer, one frame per task | the stage pool |
| `CHIM world: source and receipt` | `chim-source.json` and `chim-receipt.json`, their long lists encoded on the workers (`tools/parallel_json.py`, the same bytes as `json.dumps`) | the stage pool |

Measured 19 October 2026 (BUILD-CHIM-SERIAL-SECTIONS-44) on 156 region frames around Balmora plus Balmora, the inputs of
the v0.0.44-dev1 build, 16 CPUs and 16 GiB, the unit cache warm, a build and gate suites running beside it (after: three
runs); every world file, the receipt, the source manifest,
the validation, stair and heap reports byte for byte (SHA-256) the same before and after:

| Section | before | after |
| --- | ---: | ---: |
| between the areas and the visibility rows | 4 s, 1 core | 1.6-2.1 s, 1 core |
| visibility rows | 33.1 s, 3.8 cores | 7.7-14.7 s, 9.5-12.7 cores |
| pack | 7.0 s, 1 core | 3.3-5.5 s, 1 core (the walk alone) |
| end of the conversion (far terrain, source, receipt, heap check) | 22 s, 1 core | 8-11 s, far terrain 4-7 cores |
| validation | 1 min 13 s, 8.5 cores | 45-55 s, 11.6-11.8 cores |
| stair gate | 2 min 20 s, 8.5 cores (9 of 16 workers by memory) | 1 min 2 s - 1 min 33 s, 12.4-15.5 cores (16 of 16) |
| statistics | 6.8 s, 1 core | 4.3-6.2 s, 1.5 cores |

Each area's source stage parses the game's master once per worker process and remembers the
models it read by their SHA-256 (`tools/chim/source_memo.py`; `AMIWIND_SOURCE_MEMO=off` reads
everything again, `AMIWIND_SOURCE_MEMO_MB` sets the memory per process, default 384). Before,
every area parsed the whole master again (13.6 s of a light area's 21.9 s) and listed and hashed
the game files for its receipt (5.3 s), and a heavy area read the same 168 models twice
(213 s of 232 s, measured under the profiler).

Measured 16-17 October 2026 on the v0.0.41 final run's inputs, 160 region frames and the three
towns, 12 CPUs (`--cpus 12 --jobs 12`), the shared unit cache read-only, on a host shared with
about fifteen other containers (wall times and threads used skewed by that load; the CPU seconds are
the measure):

| | before (`old` modes) | after | |
| --- | ---: | ---: | --- |
| CPU seconds, whole conversion | 15,855 | 8,626 | -46 % |
| CPU seconds, source stages | 6,555 | 2,088 | -68 % |
| CPU seconds, ground samples | 1,023 | 72 | |
| wall (busy host) | 4,364 s | 2,750 s | |
| files of the world (8,318) | | | all byte-identical |

## Payload preflight

The image step starts with a payload preflight (`tools/payload_preflight.py`):
before it writes anything, it runs its read-only payload checks over the staged
payload in parallel and lists every error together, so a payload error stops
the build in seconds instead of at the end of a 25-40 minute image step. The
checks are the same functions the image step runs later: the harvest
catalogue check (on the map set the image will ship, with CHIM frame maps in
and the legacy maps of CHIM towns out), the CHIM world receipts and frame map
inputs, Amiga file names, build paths in shipped text, the soundtrack, and the
disk-layout gate on the planned partitions and drives. It prints one line:

```text
Payload preflight: 7 checks, 0 errors, 4.1 s
```

`tools/build.py --check-payload RUN` runs it alone on a run folder's staged
payload, with the image command recorded in its `build-state.json`. The later
checks still run on what the image step writes.

## Measured release builds (v0.0.33 -> v0.0.34)

Measured on a 24-thread desktop with `--jobs 22`, from the per-stage profiles of
the two release builds.

Critical path of the v0.0.34 release build: it is mostly stages that use a
small part of the workers they are given.

| Stage | Wall time | Workers used of given | Note |
| --- | --- | --- | --- |
| interior | 52 s | about 2 of 22 | about 1,030 idle core-seconds |
| intro | 33 s | 7 of 22 | |
| census | 17 s | about 6 of 22 | |
| bsp | 32 s | about 2.6 of 7 | |
| npcs | 21 s | 1 | single core |
| hands | 8 s | 1 | single core |

The fix is smaller units: per-room and per-region units (the hierarchical
output hashes in [BUILD_CACHE.md](BUILD_CACHE.md)) and work queues that keep
every given worker busy.

Over-broad stage keys: a change to the scheduler's stage table made 32 of 35
stages rebuild for a one-model change. Fixed:
[BUILD-SCHEDULER-TABLE-KEY-35](bugs/BUILD-SCHEDULER-TABLE-KEY-35.md). The
world-survey stage still ran again despite reuse; under investigation.

Release flow:

| Step | v0.0.33 | v0.0.34 |
| --- | --- | --- |
| Publish run start to published release | about 60 min | about 10 min |
| CI Docker job | 11 min 21 s | 1 min 34 s ([CI-SUITE-TWICE-33](bugs/CI-SUITE-TWICE-33.md)) |
| CI source job | 10 min 32 s | 8 min 50 s |
| Full test-suite runs per release | about 5 | 2 (one local single-interpreter run, one CI run) |

Method: every build's per-stage profile (wall time, CPU seconds, cores used
against workers given, idle core-seconds) goes into a ledger, and after every
build an optimizer list ranks idle cores on the critical path and unexpected
rebuilds (see [Optimizer](#optimizer)).

An optional `build.py --palette FILE` supplies the exact 768-byte RGB palette
to scene conversion before quantization. The stage cache fingerprints its bytes,
so changing the same file invalidates scene reuse. Omit it for the historical
scene-sampled palette. Use the palette from the matching conversion stage,
before UI and sky reservations; a final runtime palette is not interchangeable.

15 October 2026 source follow-up: the fresh Seyda gameplay carrier uses shared
original intro placement and validated hand timing. The full intro retains its
default ten-actor path; the carrier selects exterior roles with original IDs,
headings and grounding. It checks conversion/UI/runtime palette compatibility
before cloning, then uses the existing exterior population and opening scripts.
It rebuilds no unrelated interiors or movie. Seventeen focused checks pass;
actual carrier conversion, original-reference parity, native seams and packaging
remain pending. No converted or playable cell count is increased.
