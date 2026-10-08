# Parallel host builds

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
| Image step | one map, region or file per worker | the image directory; see [Image step](#image-step) |

Scene stages that copy or mutate a prior scene remain ordered. The image stage
waits for every input branch. Terrain, individual legacy NPC/hand conversion,
QBSP and final BSP/HDF serialization still contain serial work. The current
pinned QBSP has no thread flag. More workers cannot remove these dependencies.

The scheduler divides one CPU budget across concurrent stages and rebalances it
every round: a serial stage holds one worker, running pooled stages share the
rest evenly, and a ready stage that waits gets a worker taken from them. Each
pooled stage reads its share from an allowance file, so its worker pools shrink
or grow (up to the budget) while it runs; map tool threads keep the value the
stage started with.
Workers use spawn, open their own inputs, and return results in stable order.
At most twice the stage's worker count is submitted at a time, bounding queued
results instead of retaining the entire pending conversion in memory.
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
| Balmora layout repair | vis threads and model preparation (N) |
| Exterior sky cleanup | one map per worker |
| Hidden-surface cull | one map per worker |
| First-person hand metadata | one map per worker (plan, then write) |
| BSP optimizer | one map per worker; verification hashing |
| Actor contact audit | map reading, then contact measurement per owning map |
| Map heap estimate | chunks of maps |
| Content fingerprint | file hashing |

Order-dependent work stays serial and says why: canonical-owner selection and
receipt order in the actor audit, staging installs and rollbacks, the final
fingerprint fold, FFS image writing and readback. Every parallel pass produces
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
messages from interleaving.

A failed stage stops scheduling new work, cancels running sibling process groups
on POSIX, and never starts dependent stages. Completed files/logs remain in the
immutable run directory; choose a new build name after correcting the failure.
The serial path and `--single-thread` remain available for diagnosis.

## Profile and reuse

Every build records each stage's CPU, average cores against its jobs, memory
and I/O, a one-second CPU timeline, the critical path and idle-core warnings in
`build-profile.json`; `tools/build_profile.py report RUN [--compare OLD]` prints
and diffs it. Development builds can reuse unchanged stages with
`--reuse-from`. See [BUILD_PROFILE.md](BUILD_PROFILE.md).

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
