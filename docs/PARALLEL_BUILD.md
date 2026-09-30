# Parallel host builds

The default is a bounded worker budget derived from CPU count, process affinity
and cgroup CPU quota. `--jobs N` (`-j N`, `--j N`) overrides it; `--single-thread`
means one worker and serial stages. `--serial-stages` retains each stage's worker
limit but disables overlap between stages for diagnosis.

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
| VIS/LIGHT | tool threads | ordered map stages, including Census |

Scene stages that copy or mutate a prior scene remain ordered. The image stage
waits for every input branch. Terrain, individual legacy NPC/hand conversion,
QBSP and final BSP/HDF serialization still contain serial work. The current
pinned QBSP has no thread flag. More workers cannot remove these dependencies.

The scheduler divides one CPU budget across concurrent stages. Allocations stay
fixed for a running stage; the next stage can use capacity freed in the meantime.
Workers use spawn, open their own inputs, and return results in stable order.
At most twice the stage's worker count is submitted at a time, bounding queued
results instead of retaining the entire pending conversion in memory.
BLAS/OpenMP threads and each soundtrack FFmpeg decoder/filter are limited to one
inside workers. Numerical work therefore cannot silently multiply the budget.

On memory-limited machines use a smaller explicit `--jobs` value. CPU detection
is not a RAM-capacity guarantee; the retained base scene/model caches still need
memory. Input/output bandwidth and uneven model sizes also limit scaling.

## Progress and failure handling

Concurrent log lines carry the stage name. Each stage keeps a separate complete
log and records assigned workers, dependencies, start time, elapsed time and
status in `build-state.json`. A periodic active-stage line keeps long tasks
visible. Native make groups compiler diagnostics per target to prevent warning
messages from interleaving.

A failed stage stops scheduling new work, cancels running sibling process groups
on POSIX, and never starts dependent stages. Completed files/logs remain in the
immutable run directory; choose a new build name after correcting the failure.
The serial path and `--single-thread` remain available for diagnosis.

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
