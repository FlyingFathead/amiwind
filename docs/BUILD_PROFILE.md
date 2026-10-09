# Build profile and stage reuse

Every build measures itself. The builder records, for each stage, how long it
ran, how much CPU it and all its child processes used, how many cores that
was on average against the jobs it was given, its memory peak and its disk
traffic. Long stages also time named sections. After the build the profiler
works out the critical path, flags stages that left their cores idle and
writes concrete suggestions. The same run records an input fingerprint and an
output manifest per stage, so a later development build can reuse unchanged
stages instead of running them again (`--reuse-from`, never silent, never for
releases).

<!-- contents start -->
## Contents

- [Where it is](#where-it-is)
- [Performance options](#performance-options)
- [Reading a profile](#reading-a-profile)
- [Optimizer](#optimizer)
- [Live progress and ETA](#live-progress-and-eta)
- [Sections](#sections)
- [How it is measured](#how-it-is-measured)
- [Stage reuse for development builds](#stage-reuse-for-development-builds)
- [Build speed in CHIM](#build-speed-in-chim)
- [Payload preflight](#payload-preflight)

<!-- contents end -->

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
| `--only-core-towns`, `--no-extra-town TOWN` | Debugging only: a smaller build without the shipped extra towns; the image does not match a release. See [LINUX_BUILD.md](LINUX_BUILD.md#shipped-towns-default) |
| `--no-profile` | Debugging only: no profile, no progress file, no output manifests (a later `--reuse-from` cannot use the run) |

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

With several runs each row says in how many of them the item appeared, so a
one-off (a busy host, a cold disk cache) stands apart from a stage that is
always slow. Items measured while other work loaded the machine say so: measure
them again on a quiet host before acting. Every speed-up must keep the outputs
byte for byte (check it against `--jobs 1`).

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

The builder also times functions without touching their code:
`build_profile.instrument(stage)` wraps the functions listed for that stage in
`INSTRUMENT` (the image step's world, flora, sky, optimizer, heap and volume
passes; the world terrain and scenery loops; Census; the asset census), every
`ordered_map`/`completed_map` (as "parallel map: function", with the item count)
and every `subprocess.run` (as "exec qbsp", "exec vis", "exec make" ...). A
test fails when a listed function no longer exists, and a missing target is
reported in the profile, never silently dropped.

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
Release candidates and finals reuse only with `--allow-release-reuse`, while a
from-scratch build of the same commit runs separately as the release check.

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
every file with that name. A whole path chain counts once
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
hashed whole. Scope `symbols` follows the same code but hashes whole files and
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
repository function (`@file<TAB>function`, once per function, through
`sys.monitoring` on Python 3.12 and later); a function that ran but whose
source the fingerprint left out marks the outputs as not reusable the same
way. The hook only observes; `AMIWIND_STAGE_TRACE=off` switches it off.
It does not see files read by other programs (map compilers, ffmpeg): those
are named on the command line and fingerprinted there.

`--reuse-from OLD_RUN` then copies a stage's outputs from the old run instead
of running it when all of these hold; otherwise the stage runs, and the build
prints the reason for every stage:

1. the fingerprint is the same and the stage passed in the old run;
2. its output manifest is complete and no stage that ran at the same time
   changed the same path (such outputs cannot be attributed);
3. every stage it depends on is reused too;
4. the files it wrote still exist in the old run: a file a later stage
   replaced is only skipped when that later stage is reused as well;
5. every file to copy still has its recorded SHA-256 (checked before the build
   starts, and again while copying);
6. the run-folder files named on its command line have the content they had
   in the old run.

Reused stages show `reused (fingerprint ...) from OLD_RUN` in `build-state.json`,
the stage log, the profile and the summary. A copy that fails its SHA-256 check
during the build runs the stage instead, unless earlier reused stages left out
files that this stage replaces; then the build stops and asks for a build
without reuse.

Never reused: `engine` (the Amiga SDK is not fingerprinted; it compiles in
seconds) and the image (`image`, `dry-run-image`), which is always assembled
and verified from the stage outputs. Inside the image step, development
(`-devN`) builds reuse the results of per-map passes for map bytes they have
seen before: the BSP optimizer and the hidden-surface cull look up
`WORKSPACE/cache/image-passes` by the input map's SHA-256, the pass options and
the SHA-256 of the pass's own repository sources (`tools/pass_cache.py`), and
run only on maps without a result. Maps and receipts are byte-identical with and
without the cache; release candidates and finals never use it
([BUILD-IMAGE-NOT-INCREMENTAL-33](bugs/BUILD-IMAGE-NOT-INCREMENTAL-33.md)).

Scene stages that change an earlier stage's folder in place limit reuse: when
such a stage is rebuilt, the earlier stages whose files it replaced are rebuilt
too, because their versions no longer exist in the old run.

`--reuse-mode hardlink` links instead of copying and marks the linked files
read-only in both runs, so a later stage that tries to rewrite one fails
instead of changing the old run; it is refused as root (copies are made).

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
change come from the cache. Development builds only: release candidates and
finals convert every map (as the from-scratch gate does) unless
`--allow-release-reuse` is given; `--no-unit-cache` turns it off for a
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
builder never deletes pool files. The stage outputs are byte for byte those of a run without
the cache. The build summary lists, per stage, how many files came from the
cache and how many were converted (`profile/file-cache/STAGE.json`; a stage
reused whole writes none). Same rules as above: development builds only,
`--no-media-cache` turns it off for a debugging build. The media stage
converts on the stage's whole worker share and grows with the scheduler's
allowance as other stages finish (`build_parallel.ordered_map`).

Runs made before the fingerprint change (`amiwind-stage-cache-v1`) are not
reuse sources; the plan says so for every stage. One build without reuse
makes a new reuse source.

Releases: release candidates and finals refuse `--reuse-from`; their images are
built from scratch and compared with the from-scratch gate. Only while that
gate runs separately on the same commit may `--allow-release-reuse` be used,
and the receipt records it.

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

## Build speed in CHIM

The streamer's builder keeps this profiler and records a fingerprint per pack,
so a change rebuilds only the packs it reaches. See
[WORLD_STREAMER.md](WORLD_STREAMER.md).

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
