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

Goal: compile fast, with zero errors and zero regressions. Measure before
optimizing; reuse only what is provably unchanged.

## Where it is

| File in the run folder | Content |
| --- | --- |
| `build-profile.json` | Per-stage measurements, CPU timeline, analysis and suggestions |
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

## Reading a profile

```text
python tools/build_profile.py report RUN
python tools/build_profile.py report RUN --compare OLDER_RUN [--fail-on-regression]
python tools/build_profile.py report RUN --html profile.html
python tools/build_profile.py report RUN/profile/sections/22-image.jsonl
```

The table has one row per stage:

| Column | Meaning |
| --- | --- |
| start, wall | Seconds after the first stage started; stage duration |
| cpu | User + system CPU of the stage process and every child it waited for |
| cores | cpu / wall: average cores in use |
| jobs | The share of the `--jobs` budget the scheduler gave the stage |
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
- **Idle-core warnings**: a stage that used less than half of its jobs for
  more than 60 s, from the one-second CPU timeline. This is how a serial loop
  inside a stage shows up (the image step on one of 24 threads for 23 minutes,
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

Each stage has an input fingerprint, recorded in every build:

- its command line, with the run folder and the `--jobs` value normalized;
- the SHA-256 of every repository Python file it imports, transitively, found
  by reading the imports in the source (also those inside functions and
  scripts named by path), and of the non-Python repository files in folders
  its code names as paths (`config/`, `engine/`, `docs/trackers/` ...); prose
  (`*.md`) and tests do not count;
- the game input hashes from the build's input lock, when the stage reads
  `--data-files`;
- the map compilers and other programs it runs, and every other file or folder
  outside the run named on its command line;
- `AMIWIND_*` environment variables, the Python version and package versions;
- the fingerprints of the stages it depends on, so a change reaches every
  stage after it.

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
and verified from the stage outputs.

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

Releases: release candidates and finals refuse `--reuse-from`; their images are
built from scratch and compared with the from-scratch gate. Only while that
gate runs separately on the same commit may `--allow-release-reuse` be used,
and the receipt records it.

## Build speed in CHIM

The streamer's builder keeps this profiler and records a fingerprint per pack,
so a change rebuilds only the packs it reaches. See
[WORLD_STREAMER.md](WORLD_STREAMER.md).
