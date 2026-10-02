# Build and compiler toolkit roadmap

rc10 adds [verified persistent NPC model reuse](NPC_MODEL_CACHE.md). Full gallery
coverage and protected model quality remain mandatory.

**Outside approval is required for any exception affecting either gallery.**
Neither the NPC gallery nor the upcoming static-asset gallery may be disabled,
reduced or bypassed, including model/asset generation, catalogue coverage,
quality and validation, without a specific documented case or scenario **and
explicit approval from the project owner**. A builder or contributor cannot
approve its own exception. Build time, disk pressure and convenience do not
supply that approval. An opt-out flag is a mechanism for an approved exceptional
debugging case, not permission to choose that exception independently.

All NPCs and other game assets must remain intact, packaged and loadable by the
engine for the complete game to function properly. Skipping their creation
alongside either gallery is pointless and counterproductive: the final product
requires those assets anyway. An exceptional debug build must be labelled
incomplete and cannot redefine the complete game's required content. Runtime
loading may be on demand; this does not require every asset to reside in RAM
simultaneously. The static-asset gallery is still planned, not implemented.

## Capacity before conversion

Capacity is a prerequisite, not a content tradeoff. Verify the workspace can hold
all required game content, conversion intermediates, staging copies, temporary
and final images, readback copies and a margin before launching expensive work.
Check filesystem/quota limits and the shared RAM budget of memory-backed scratch.
Never skip NPC models or the mandatory gallery to compensate for missing space.
All character models remain required in the final product.

The current build does not provide a guaranteed whole-recipe peak-space estimate.
Add an automatic preflight using recipe/output estimates, retained-input sizes
and observed stage peaks, followed by checks before large allocations. A low-space
failure must preserve completed results and explain the capacity needed. Do not
turn it into an implicit reduced-content build or a gallery opt-out.

Status: proposed future work, 1 October 2026. No GPU backend, new compiler
provider, per-phase region profiler or performance improvement is implemented
by this documentation update. Complete and preserve the current build before
trying another checkpoint; a running conversion must keep its source and tools.

This roadmap covers host compilers, conversion tools, scheduling, profiling and
output assembly. The [Windows roadmap](WINDOWS_BUILD_ROADMAP.md) covers host
portability; the [third-party compiler plan](THIRD_PARTY_COMPILERS.md) covers
possible bundled QCC source and selectable compiler providers. Native
Windows/MSYS2 is the preferred Windows development direction. WSL2 is a fallback
if native integration proves troublesome. Both Windows routes remain untested.

## Asset inventory and coverage receipts

The [asset catalogue plan](ASSET_CATALOGUE_AND_GALLERY.md) separates original
object/dependency lookup, converted output and placed-reference coverage.
Implement its metadata inventory without regenerating world terrain. Carry
stable reference identities through conversion and report explicit omission
reasons. The confirmed scaled-flora omission demonstrates why a successful
model conversion alone cannot certify scene completeness.

Measure unique asset bytes, repeated chunk data, final partition payload and
filesystem free space separately. Expanding scenery should use bounded runtime
loading and dependency-aware conversion, not an eager all-assets resident set.
The proposed `dbg assetgallery` is a consumer of this catalogue, not a substitute
for checking source placements in the actual world.

## Top engineering priority: practical world build times

The reported workstation run spends an impractical part of an evening compiling
world-terrain regions despite full CPU utilization. Reducing that elapsed time
is now the top engineering priority. This is a reported usability problem, not
a completed benchmark or a newly verified successful build.

Order the next checkpoints accordingly:

1. Preserve the current run and record its actual completion or failure. Add
   phase timings for `vfXXXX`, especially visible and standing-hull `qbsp`.
2. Make unchanged terrain reusable across fresh build runs, with reliable cache
   keys and verified outputs. Ordinary engine/UI/documentation changes should
   not require recompiling all terrain once that reuse is implemented.
3. Reduce measured duplicate terrain/BSP work, including a separately cached
   collision result and investigation of a terrain-specific hull builder.
4. Resolve the measured CPU, scheduling and storage costs. Investigate GPU work
   only when the phase measurements demonstrate a useful target.

These build-time checkpoints take precedence over native Windows bring-up,
bundled-QCC provider work and speculative GPU-assisted QCC. Within the later
Windows workstream, native Windows/MSYS2 remains preferred and WSL2 a fallback.
Correctness failures remain blockers: no optimization may bypass collision,
shoreline, output-budget or image validation to obtain a faster success report.
Keep one small source checkpoint per logical change before another long build.

## Establish the current pipeline before optimizing it

The rc6 source uses CPU compilers and conversion tools. It has no GPU execution
path. Installing a GPU or changing the operating system does not move existing
work onto that GPU. C compilation, assembly, QCC and linking remain CPU work in
this plan; optional GPU work concerns selected asset-conversion operations.

The current terrain survey produces 2,526 `vfXXXX` regions. Inspection of
`tools/prepare_world_regions.py` shows this sequence for a newly compiled region:

1. Load the terrain packet on first use by a worker; sample source heights and
   materials, refine shoreline triangles, and generate map text.
2. Hash the generated map and shared texture WAD, then check the cached result.
3. Write the map and copy the WAD into the region directory.
4. Run `qbsp`, `vis -threads 1 -fast`, and `light -threads 1 -minlight 24`.
5. Compact the BSP and generate the scaled standing-collision map.
6. Run `qbsp` again for that collision map, then graft the standing hull.
7. Deduplicate BSP data, hash and check output budgets, write the receipt, and
   remove selected scratch files.

Region jobs can run concurrently through `tools/build_parallel.py`; the parent
publishes shared scene files and indices in order. Texture WAD preparation,
final world publication and HDF assembly also cost time outside an individual
region. Detailed town/interior mesh conversion is a separate workload.

The existing `converted.seconds` reports a region total, not a phase breakdown.
It excludes the worker's first terrain load and subsequent scene publication.
A cache hit returns the previous receipt, including its old conversion timing;
that value must not be mistaken for the elapsed time of the cache lookup.
The [build summary](BUILD_OUTPUT.md) and stage receipts provide broader timings.
100% CPU utilization establishes occupancy, not which operation dominates.

### Compile order and worker allocation audit

The current order is safe for shared scene writes; it is not established as the
fastest order. Source inspection of `tools/build_parallel.py` identifies these
constraints, which require measurements before changing the scheduler:

- Setup/terrain, dialogue lookup, world survey, music and engine compilation can
  overlap when workers are available. The scheduler divides its budget between
  ready branches; it does not use measured stage costs or critical-path priority.
- Each launched stage keeps its initial `--jobs` allocation. Finishing another
  branch releases slots for new stages, but does not enlarge an already running
  process pool. Measure idle slots and competition with the main scene chain.
- Scene converters are serialized because they copy or modify predecessor scene
  trees. In rc3 world terrain waits for `opening-references` and `world-survey`;
  rc6 also validates world UI between those prerequisites and terrain.
  `prepare_world_regions.py` reads the scene palette, compiles regions into its
  own directory, then copies results and writes the world index into the scene.
  Investigate splitting region compilation from final scene publication so it
  can start once the survey and a verified, stable palette are available.
  Preserve shared-write ordering and reserve enough CPU/RAM/I/O for both branches.
- `ordered_map` submits at most twice the worker count, waits for the oldest
  result, then submits one replacement. A slow early region can hold back later
  submissions even after other queued jobs finish. Completion-driven refill
  with bounded buffering and deterministic final publication is a candidate.
- Region order follows cell/subcell coordinates, not predicted compilation cost.
  Test expensive-region-first scheduling to reduce a long tail, while accounting
  for the current per-worker shoreline cache and possible locality losses.
- The default budget uses logical CPU availability and estimated memory headroom.
  Compare worker counts below the logical-CPU maximum on the same regions;
  contention can make extra workers slower. Preserve nested thread limits.

Capture the dependency critical path, ready/queue wait, stage allocation,
per-worker busy/idle time, region completion distribution and I/O pressure.
Compare end-to-end wall time and regions per minute for identical inputs, tool
versions and cache state. Summed per-region seconds overlap in parallel and
cannot be read as whole-build duration. Reordering cannot eliminate duplicate
geometry work or make a fresh run reuse old terrain; those remain separate
priorities below. The rc6 world-UI validation dependency catches failures earlier;
it is not the proposed scheduling optimization or a claimed speedup.

## Checkpoint 1: measure phases and resource use

**First target: world-terrain `vfXXXX` compilation.** The reported workstation
run identifies this stage as the major observed wait with full CPU utilization.
That observation sets profiling priority; it does not yet identify the costly
internal phase. An uncached 2,526-region pass invokes `qbsp` up to 5,052 times,
with another 2,526 fast-VIS and 2,526 lighting calls. Instrument the two BSP
passes separately before choosing an algorithm change or GPU backend. QCC
acceleration is lower priority unless measurements overturn this assessment.

Add optional profiling without changing geometry, compiler flags or validation
gates. Retain the ordinary build path as the comparison reference. Record:

- Region identity, subdivision, triangle/brush counts, input fingerprint, worker
  identity, cache hit/miss, status and exit code.
- Monotonic elapsed time for the phases above, separating first-worker setup,
  cache lookup, both `qbsp` invocations, VIS, lighting and final publication.
- Queue wait, task start/end and process CPU time where available. Distinguish
  parent Python time from subprocess time; label unavailable counters honestly.
- Peak RAM for the process tree, free/peak scratch usage, disk throughput where
  available, actual worker counts and nested tool-thread limits.
- For future GPU trials: selected device, driver/runtime versions, peak VRAM,
  upload/download time, initialization and synchronized execution time. Timing
  an asynchronous launch alone does not measure completed GPU work.

Write per-worker results independently; aggregate them in the parent. Preserve
failure records and avoid concurrent writes to one shared JSON file. Keep raw
logs outside the public source tree. Publish only sanitized summaries without
usernames, hostnames or personal filesystem paths.

Start with representative ocean, coastline, inland and complex regions across
the actual subdivision sizes, plus separate town/interior samples. The existing
`--only` diagnostic subset is useful for region experiments; it does not publish
a complete world or prove a complete build. Report median, p95 and worst-case
times, phase totals, cache behavior and the actual overall wall time. Repeat
matched runs and distinguish fresh conversions from warm-cache builds.

Saving one second on each of 2,526 regions removes 2,526 seconds (42 minutes
6 seconds) of accumulated task duration. It does **not** promise that wall-clock
saving when regions run concurrently. Twelve perfectly balanced workers would
reduce that idealized saving to about 3 minutes 31 seconds, before scheduling,
I/O and other stages. Measure the real critical path and end-to-end change.

## Checkpoint 2: improve the measured CPU and storage bottlenecks

Prioritize demonstrated costs over a particular acceleration technology:

- Investigate repeated sampling, map-string generation, serialization and
  geometry work. Compare batching, NumPy vectorization, bounded caching and
  compiled CPU routines before committing to a GPU implementation.
- Strengthen conversion-cache identity to include the tool binaries, recipe,
  configuration and relevant inputs. The present region key covers generated
  map/WAD content and a recipe marker; it does not include the native tool
  binaries. Reused results must remain verifiable across toolchain changes.
- Profile the ordered result queue for delayed submission behind slow regions.
  Consider completion-driven scheduling while retaining deterministic ordering
  for shared output publication. Preserve the total worker budget and prevent
  each worker from creating another full complement of library/tool threads.
- Bound concurrency by memory and scratch space as well as CPU availability.
  Add Windows memory detection during native-host bring-up. Check transient
  copies and HDF staging against real free space; clean only known disposable
  scratch after successful validation and retain failed-stage evidence.
- Investigate reproducible resume/checkpoint reuse with verified inputs and
  outputs. Do not introduce partial-world publication or skip production gates.
- Triage compiler warnings by behavior risk. Address uninitialized values,
  bounds, lifetimes and declarations with focused verification; suppressing
  warnings is not a performance improvement or proof of correctness.

A small faster kernel that leaves the dominant BSP or copying stage unchanged
may barely affect the complete build. For illustration, making a component
that occupies 20% of serial elapsed time ten times faster improves that total
by only about 1.22x. Parallel overlap needs its own measured analysis.

### Reuse across runs and reduce repeated BSP construction

The current region cache lives inside the chosen world-terrain output directory.
The main builder places that directory under a new immutable run name. Therefore
a fresh normal run does not automatically reuse the previous run's compiled
regions. The existing cache also generates map text before checking its key.
Addressing these limitations is an immediate candidate for shortening repeated
builds; it does not by itself accelerate the first uncached conversion.

Investigate an external persistent cache with content-based keys. Cover terrain
samples and materials throughout each region's overlap, region transforms and
bounds, texture/palette inputs, hull profile, configuration, generator recipe
and relevant tool identities. Do not key only on the core cell: a neighboring
change can affect overlapping geometry. Verify cached bytes and provenance,
publish cache entries atomically, and distinguish cache-hit time from the old
conversion time. A cache hit must still pass the required output checks.

Separate visual, lighting and collision dependencies where proven safe. The
collision result may be reusable after a visual-only input change, but this
requires explicit dependency analysis rather than assuming all textures are
irrelevant to contents or collision. Keep the final run immutable even when
reading shared cached results; downstream mutation must not alter cached files.

For the expensive second BSP pass, compare the current method with:

- A collision-only compilation path that avoids generating discarded rendering
  data, if the pinned tool supports it or a small verified extension can do so.
- A terrain-specific hull generator from the sampled terrain/brush geometry,
  without a second full general-purpose BSP compile.
- Simpler collision geometry only where tests establish equivalent required
  behavior, with independently cached hull results and local invalidation.
- Reuse of validated source geometry or intermediate work across the two passes
  and overlapping regions, where their coordinate transforms permit it.

These are investigations, not established replacements. `tools/player_hull.py`
currently scales geometry for the stock compiler and inverse-transforms the
standing hull to the project's humanoid dimensions. Reusing the stock Quake
hull or merely deleting the second invocation would change that behavior.
Preserve standing bounds, floor and slope contacts, blocking surfaces, water
contents, region seams and BSP29/clipnode limits. Keep detailed town/interior
hulls separate from terrain-only experiments. Compare representative traces
and full output checks against the existing pipeline before any default switch.

Measure tool startup, repeated map parsing and temporary-file I/O as well as
geometry computation. Thousands of subprocesses are a possible fixed cost, not
proof that startup dominates. Batch or reuse processes only if measurements
justify the added complexity and outputs remain deterministic.

Acceptance must distinguish two outcomes: fewer seconds for a fresh full-world
conversion, and avoiding unnecessary recompilation for incremental work. Report
both against the same inputs and worker budget, including cache storage cost,
whole-build elapsed time, peak memory and scratch use. No target speedup is
claimed until these comparisons have run.

## Checkpoint 3: investigate optional CPU plus GPU conversion

The following are hypotheses to test after profiling, not promises of speedup:

| Work | Initial direction | Main question before adoption |
| --- | --- | --- |
| Amiga GCC, assembler, QCC, linking | CPU toolchain | Correct host tools and reproducible output; no GPU compiler proposal. |
| Terrain sampling and bulk transforms | Batched CPU first; possible GPU kernel | Is arithmetic large enough to outweigh transfer/setup and preserve shoreline decisions? |
| Triangle normals and regular mesh calculations | Possible GPU batches | Are data layouts and batch sizes suitable without changing topology or winding? |
| Adaptive triangulation and BSP tree construction | CPU/algorithm investigation | Branching and topology dependencies may dominate; no simple array-library substitution is established. |
| Texture resize/filter/palette conversion | Possible GPU batches | Preserve color, palette, filtering and mipmap rules; measure transfer and batch overhead. |
| VIS/PVS | Profile existing CPU fast-VIS path | This pipeline already uses `-fast`; worst-case full-VIS anecdotes do not identify its bottleneck. |
| Light baking/ray queries | Possible optional GPU backend | Measure actual lighting share and prove target BSP/lightmap compatibility. |
| HDF packing, shared publication, file copies | CPU/I/O improvements | Capacity, throughput and duplicate writes may matter more than compute. |

Candidate experiments could use CuPy, a small CUDA kernel or another suitable
GPU library. Choose based on the measured operation, supported hosts, numerical
behavior, dependency cost and maintenance effort. No new heavyweight dependency
or map-tool replacement is selected by this roadmap. Pin experimental versions
and retain the CPU reference for every comparison.

Check third-party claims against a specific source revision. As inspected on
1 October 2026, the [VibeyMapTools README](https://github.com/themuffinator/VibeyMapTools)
describes `vmt-light` as using CPU ray tracing through Embree. That README does
not substantiate a ready-to-use GPU backend. The fork is not adopted as a GPU
solution here. AmiWind remains pinned to ericw-tools 0.18.1; current upstream
features or library versions must not be attributed to that older package.

The first prototype should accelerate one measured operation on one GPU. Include
transfers, device synchronization, initialization, CPU contention and validation
in its timings. Do not predict 10x or 20x whole-build improvements from a kernel
benchmark. Only consider multiple GPUs once one device demonstrably helps.
Independent region batches could be assigned per device, but VRAM is generally
separate rather than one pooled allocation; duplicate data and the CPU feeding
each device must fit the budget. Two devices do not establish twice the speed.

## Checkpoint 4: configuration, compatibility and acceptance

Keep ordinary builds on the portable CPU path by default. Explore optional
acceleration first on available local GPU hardware, with the same source,
input data and correctness gates used by the CPU reference. A host without a
usable accelerator must remain able to build without installing CUDA or GPU
Python packages. Do not assume that a cloud environment exposes a usable GPU.

A possible future interface is `--gpu auto`; this flag does **not** exist in
the current builder. If implemented, automatic selection would need to check
the driver, runtime, supported device and free VRAM, and enable only stages
with a validated backend. Report stage-by-stage selections and CPU fallbacks.
An explicitly requested unsupported backend should fail clearly under a
documented policy. GPU availability alone would not accelerate GCC, QCC, BSP
construction or VIS.

Keep CPU and GPU tasks under a shared resource budget so device work can
overlap suitable CPU work without starving either side or exceeding RAM/VRAM.
Measure the CPU cost of feeding one GPU before considering multiple devices.
Remote GPU build hosts are a later option only if measured end-to-end gains,
data-transfer time and total operating cost justify them; they are not required
for local acceleration or the default build.

Any future acceleration option must leave CPU-only builds supported. Possible
configuration concepts are explicit CPU/GPU backend selection, device selection
and bounded batching. These are design possibilities, **not implemented CLI
options**. Report the actual backend in receipts; never silently claim GPU use.
Unsupported hardware or a failed optional backend must produce a clear result
under a documented fallback policy, without mixing partial outputs.

Before enabling a backend by default:

1. Demonstrate an operation-level speedup including all overhead on representative
   samples, then demonstrate a repeatable complete-build wall-time improvement.
2. Preserve shoreline wet/dry classifications, region seams and origins, mesh
   topology, collision hulls, material/palette semantics and BSP limits. Do not
   apply a broad floating-point tolerance to excuse changed terrain identity.
3. Compare exact hashes where output should be identical. Where an intentional
   numerical change is proposed, document its scope and acceptance tests and
   inspect rendered output. Validate the HDF payload separately from filesystem
   metadata; retain all ordinary image gates and emulator checks.
4. Exercise CPU-only, GPU-selected, missing-device, insufficient-VRAM, cancellation
   and interrupted-resume behavior. Prove determinism where required and absence
   of mixed results when switching tools or backends.
5. Record host/tool/driver versions, input hashes, build scope, resource settings,
   cache state, repeated timings, warnings and resulting output hashes. Evaluate
   native Windows and Linux separately; evaluate WSL2 only if using that fallback.

Promote one verified checkpoint at a time. Compiler success, a fast sample or a
GPU benchmark does not certify the full asset pipeline or a playable release.
The first implementation task is phase profiling, not writing CUDA.

## Deferred possibility: GPU-assisted QCC

Bundling QCC source would make controlled host-portability experiments easier;
it would not add CUDA support. A GPU-assisted compiler would be a separate
research project, conditional on profiling identifying enough parallel work
inside QCC to repay transfers, synchronization and maintenance costs.

The output must remain the existing Quake VM bytecode consumed by the Amiga
engine. Generating CUDA programs instead would target a different runtime and
would not replace AmiWind's QCC. CPU parsing and dependency-heavy compiler
passes are not automatically GPU workloads. Benchmark the actual AmiWind
QuakeC input, rather than extrapolating from a large unrelated codebase.

Measure QCC's share of total elapsed time first. Even eliminating compilation
time entirely cannot save more than its contribution to the build's critical
path. GPU-assisted QCC stays below measured asset-conversion opportunities in
priority unless the evidence changes. Any experiment must retain the CPU
compiler, exact program-version/CRC/opcode validation, bytecode comparisons
and runtime behavior checks. No CUDA-enabled QCC is supplied or selected here.


### rc6 early-gate implementation

The world-UI receipt and actual actor-contact check now run before world-terrain
on new complete builds. The actor check works on copied detailed scene maps and
models and reproduces the 23 known contact failures from retained rc3 conversion.
Final image validation repeats both checks. This reduces wasted work before a
known failure; it is not a terrain compiler speedup. The per-region profiling,
caching, scheduler changes and GPU experiments above remain roadmap items.

## Separately rebuildable scenery: near-term design target

Preserve terrain while adding original CELL/FRMR static placements in a separate
conversion and runtime layer. Record per-asset and per-cell dependencies so changes
to a tree, rock or plant invalidate only affected scenery and overlap products.
Prove terrain hashes unchanged on a scenery-only rebuild. See the
[cell-by-cell scenery plan](ASSET_CATALOGUE_AND_GALLERY.md). This needs runtime
loading/collision work and is not implemented by current image recovery.

## Mutable NPC equipment

[Character equipment and shared assets](CHARACTER_EQUIPMENT_ROADMAP.md) are
required for partial corpse looting and equipment changes. rc10 caches existing
appearance snapshots; it does not make fixed outfits the final runtime design.
Preserve reusable source parts and per-actor state; do not pre-bake every outfit
combination. Normal gallery coverage and owner-approval requirements remain.
