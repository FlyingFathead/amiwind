# Parallel host builds

<!-- contents start -->
## Contents

- [What runs concurrently](#what-runs-concurrently)
- [vis threads and vis mode](#vis-threads-and-vis-mode)
- [Image step](#image-step)
- [Progress and failure handling](#progress-and-failure-handling)
- [Profile and reuse](#profile-and-reuse)
- [Validation](#validation)
- [Automatic RAM headroom limit](#automatic-ram-headroom-limit)

<!-- contents end -->

`--jobs N` (`-j N`, `--j N`) is exact: the build runs N workers in total and every
stage and every worker pool inside a stage receives N (or its share of N when
stages overlap). It is never lowered to the CPU count. When N exceeds the usable
CPU threads (CPU count, process affinity and container CPU quota) the build
prints one warning, records it in `build-state.json` and the build summary, and
still runs N workers:

```text
WARNING: --jobs 100 exceeds 24 usable CPU threads; running 100 workers as requested (expect contention and higher temperatures)
```

Memory is not part of that warning. Without `--jobs` the default is automatic:
CPU count, affinity and quota, capped by available memory (see
[Automatic RAM headroom limit](#automatic-ram-headroom-limit)). `--single-thread`
means one worker and serial stages. `--serial-stages` retains each stage's worker
limit but disables overlap between stages for diagnosis. `--jobs 0` is refused.

Outer x inner never exceeds the budget: a stage that runs maps side by side gives
each map's tools `N // concurrent maps` threads, at least one; a pass that runs
alone gets all N.

## What runs concurrently

| Work | Parallel unit | Shared output |
| --- | --- | --- |
| Native Amiga compiler | make translation units | make dependencies; diagnostics grouped per target |
| Independent pipeline branches | engine, music, dialogue lookup, ordered world chain | separate stage directories |
| Scenery export | NIF model decode/collision extraction | one archive/index writer, sorted model order |
| Scene previews | sprite/alias model bake | one writer, original model order |
| BSP conversion | unique model preparation and placed-model lighting/hulls | one BSP writer with original offsets/order |
| Intro actors | ten actor bakes | one model/entity writer |
| Character previews | individual heads/hair | one writer, catalogue order |
| Soundtrack conversion | individual music tracks | one manifest writer, original track order |
| VIS | tool threads (`N // concurrent maps`) | ordered map stages, including Census |
| Town imports (Balmora, Vivec Arena) | one region per worker (tool threads `N // concurrent regions`) | regions in order; each region's log output printed in region order |
| Media | sounds and videos in one pool, long videos first | one catalogue writer, serial row order |
| Image step | one map, region or file per worker | the image directory; see [Image step](#image-step) |

Scene stages that copy or mutate a prior scene remain ordered. The image stage
waits for every input branch. Terrain, individual legacy NPC/hand conversion,
QBSP and final BSP/HDF serialization still contain serial work. The current
pinned QBSP has no thread flag. More workers cannot remove these dependencies.

The scheduler divides one CPU budget across concurrent stages and rebalances it
every round: a serial stage holds one worker, running pooled stages share the
rest evenly, and a ready stage that waits gets a worker taken from them. A pooled
stage starts with its even share: the running pooled stages shrink first, then it
starts (earlier it started with the one worker left free and kept that value for
its tool threads,
[BUILD-STAGE-START-SHARE-33](bugs/BUILD-STAGE-START-SHARE-33.md)). Each pooled
stage reads its share from an allowance file, so its worker pools shrink or grow
(up to the budget) while it runs, and a stage left alone ends up holding the whole
budget. Choices taken when a pass starts (map tool threads, whether a pass runs
serially at all) read the current share (`build_parallel.live_jobs`); tool
threads already running keep theirs. Pool workers do not see the allowance: a
pool a worker opens keeps the size it asked for, so outer x inner stays within
the stage's share ([BUILD-NESTED-POOL-ALLOWANCE-33](bugs/BUILD-NESTED-POOL-ALLOWANCE-33.md)).
Workers use spawn, open their own inputs, and return results in stable order.
An ordered pool runs at most its share at a time and holds at most four
results per worker ahead of the one it hands back next, so one slow item does
not idle the others and the pending conversion is not all kept in memory
([BUILD-ORDERED-WINDOW-33](bugs/BUILD-ORDERED-WINDOW-33.md)). Pools that know
what their items cost hand them out longest first and still return them in
input order: town regions and rooms, the area and Balmora interior rooms and the
open-world terrain regions use the seconds each item took in an earlier build of
the same workspace (`WORKSPACE/cache/item-costs`, `tools/build_costs.py`), else a
measure of the item (placed references; the survey's source triangles), scaled
to seconds. The history only orders work; it is not a stage input.
BLAS/OpenMP threads and each soundtrack FFmpeg decoder/filter are limited to one
inside workers. Numerical work therefore cannot silently multiply the budget.

On memory-limited machines use a smaller explicit `--jobs` value. CPU detection
is not a RAM-capacity guarantee; the retained base scene/model caches still need
memory. Input/output bandwidth and uneven model sizes also limit scaling.

## vis threads and vis mode

vis takes its thread count from the same `--jobs` budget. A map compiled on its
own (a Balmora or other town region, Census, the prison ship, Seyda) gets the
whole budget; maps compiled side by side (interior rooms, open-world terrain
regions) share it, `jobs // concurrent maps`, at least one each. With
`--jobs 1` every command line is exactly the historical one.

`--vis {fast,full}` (alias `--vis-mode`) selects the vis pass for every map
converter and `tools/build_aga.py image`; each converter also accepts
`--vis-mode`. The default `fast` keeps the portal-flood-only pass every build has
used, so outputs stay unchanged and no command line gains an option. `full` runs
the full portal flow: slower, and in today's towns it gains almost nothing,
because buildings are `func_wall` models that never form leaf walls. The tested occluders
changed that negligibly in towns; see
[performance/TOWN-VISIBILITY.md](performance/TOWN-VISIBILITY.md). Open-world
terrain regions key their reuse cache on a non-default mode.

## Image step

The image step (`tools/build_aga.py image`) runs after every other stage, so the
scheduler gives it the whole budget; it accepts `--jobs` like the other stages.
Its passes run one after another, each with N workers from the shared pool
(`tools/build_parallel.py`, spawn workers, results in map order):

| Pass | Parallel unit |
| --- | --- |
| Seyda Neen regions | one bounded region compile per worker (vis threads share N) |
| Balmora layout repair | the three rebuilt cores side by side (vis and models N // 3 each), then one bounded region per worker |
| Exterior sky cleanup | one map per worker, largest first |
| Hidden-surface cull | one map per worker, largest first; hash checks |
| Actor support fitting | one placement per worker, long offset searches in slices, all in one pool |
| NPC gallery staging | payload hashing; greetings read from every map |
| First-person hand metadata | one map per worker (plan, then write) |
| BSP optimizer | one map per worker; verification hashing |
| Actor contact audit | map reading, then contact measurement per owning map |
| Map heap estimate | chunks of maps |
| Content fingerprint | file hashing |

Order-dependent work stays serial and says why: canonical-owner selection and
receipt order in the actor audit, staging installs and rollbacks, the final
fingerprint fold, FFS image writing and readback. Passes that replace maps keep
the original as a hard link (a copy only across file systems) instead of
writing every changed map twice. Every parallel pass produces
the bytes of the serial path (`--jobs 1`); `tests/test_build_jobs_workers.py`
checks it with real workers and checks that N reaches every pool.

Map lighting (ericw `light`) always runs with one thread per map: with more
threads light 0.18.1 writes faces and lightmaps in a thread-dependent order, so
its output is not byte-reproducible. vis output is identical for any thread count.

The standalone `tools/optimize_world_maps.py` command keeps its own `--jobs N`
(default one).

## Progress and failure handling

Concurrent log lines carry the stage name. Each stage keeps a separate complete
log and records assigned workers, dependencies, start time, elapsed time and
status in `build-state.json`; CPU time, cores used and idle cores per stage are in
the [build profile](BUILD_PROFILE.md). A periodic active-stage line keeps long tasks
visible. Native make groups compiler diagnostics per target to prevent warning
messages from interleaving. `build-progress.json` in the run folder holds the
live state (stages done, running and pending, cores in use, percent and ETA);
`python tools/build.py status RUN` prints it on one screen. See
[Live progress and ETA](BUILD_PROFILE.md#live-progress-and-eta).

A failed stage stops scheduling new work, cancels running sibling process groups
on POSIX, and never starts dependent stages. Completed files/logs remain in the
immutable run directory; choose a new build name after correcting the failure.
The serial path and `--single-thread` remain available for diagnosis.

## Profile and reuse

Every build records each stage's CPU, average cores against its jobs, memory
and I/O, a one-second CPU timeline, the critical path and idle-core warnings in
`build-profile.json`; `python tools/build.py profile report RUN`, `profile compare
RUN OLD` and `profile optimize RUN...` print it, diff it and list where cores went
idle, with suggestions. Development builds can reuse unchanged stages with
`--reuse-from`. All performance options in one place:
[Performance options](BUILD_PROFILE.md#performance-options).

## Validation

See [v0.0.23-dev1](RELEASE-v0.0.23-dev1.md) for the measured builds and exact
validation boundary. Tests execute real process workers and subprocess stages,
check ordered results, stage prerequisites, budget limits, inherited limits,
worker errors and cancellation. Private source-data comparisons cover actual
BSP geometry, collision, textures, lightmaps, actor models and head previews.
Changes to the conversion recipe are not part of this scheduling checkpoint.

## Automatic RAM headroom limit

`--jobs auto` also considers host `MemAvailable` and container memory headroom
(cgroup v2, with a v1 fallback). It reserves a quarter of available headroom, at
least 256 MiB, and budgets 512 MiB per worker before applying the CPU/affinity/quota
limit. This is a conservative estimate, not a proof of the peak size of every
future source model. At least one worker is selected; a single unusually large
input can still require more memory than the machine has available.

The top-level scheduler shares that allocation between independent stages.
Children inherit their assigned `AMIWIND_BUILD_JOBS` rather than recalculating an
all-CPU budget. BLAS/OpenMP libraries use one thread per process worker. Explicit
`--jobs N` remains an override for measured environments, and `--single-thread`
remains available. Shared scene writes, final catalogues, HDF assembly and
readback verification keep their required ordering.

The final [build summary](BUILD_OUTPUT.md) measures total wall time across the
pipeline, including overlapping work; it does not add stage durations together.
Compiler warnings are counted from the completed engine log.
