# Heap watcher: build estimates and complete scene lifecycles

This is the memory review and implementation contract for the unreleased
v0.0.27-rc3 repair. It extends [memory allocation](MEMORY_ALLOCATION.md) and
[cell changing](CELL_CHANGING.md). A planned metric or checkpoint below is not
implemented merely because it appears here. Target runtime acceptance remains
pending; the original rc3 playtest image is not repaired by these documents.

## Build receipts: used, free and growth margin

Implemented in the unreleased rc3 repair builder on 3 October 2026:
`build.json.heap_watcher` summarizes the worst modeled map. The same summary is
written to `heap-watcher.json` immediately after the map audit, before a failing
headroom gate aborts packaging. A failed audit does not produce a ready image.
The detailed, hashed `world-map-heap.json` retains every map's allocations and
margin; consult it when selecting cells for reduction or subdivision.

| Receipt field | Meaning |
| --- | --- |
| `heap_budget_bytes` | Target Hunk capacity |
| `estimated_map_peak_used_bytes` | Worst map's ordered BSP loading peak |
| `estimated_free_before_reserves_bytes` | Capacity minus that peak; not freely available gameplay memory |
| `non_map_reserve_bytes` | Reserved engine, actor and other non-BSP allowance |
| `required_safety_headroom_bytes` | Independent required spare capacity |
| `estimated_growth_margin_after_reserves_bytes` | Capacity minus map peak and both allowances; negative means reject |
| `worst_map`, `over_budget_maps` | Map requiring the largest budget and all modeled gate failures |
| `report_sha256`, `loader_source_sha256` | Exact estimate evidence and matching loader provenance |
| `runtime_validation` | `pending` until separately verified on the target |
| `runtime_measured_used_bytes`, `runtime_measured_free_bytes` | `null` at build time; no runtime measurement is invented |

For example, a 5-MiB map peak within an 11-MiB Hunk leaves 6 MiB before
reserves. With 3 MiB reserved for non-map work and 2 MiB safety, only **1 MiB**
remains for modeled growth. The 6 MiB is not permission to add 6 MiB of assets.
At a 6-MiB map peak the growth margin is zero, while safety remains reserved.

These numbers are **target-ABI estimates**, not measured total application use.
The runtime watcher records lifecycle snapshots in `heap-audit.log`; acceptance
must bind that evidence to the exact engine, maps and emulator configuration.
Missing measurements mean unknown, not zero. Cache pressure, zone fragmentation,
external Fast/Chip allocations and transition peaks still need target profiling.
Future content additions must rerun this gate on final prepared maps and refresh
both receipts and affected issue documentation; never reuse an older green result.

## Budget and growth policy

Keep the reference 11-MiB hunk, the 3-MiB non-BSP allowance, and at least 2 MiB
of independent safety allowance. This leaves a **6-MiB maximum modeled BSP
loading peak**. The safety allowance is 18.2% of the entire hunk; the two
allowances together occupy 45.5%. These are conservative policies, not measured
proof that all future content will fit. Never lower them to make an audit green.

For new subdivisions, **about 5 MiB of BSP peak is a planning target**, leaving
approximately another 1 MiB within the current map allowance for content growth.
This is not a second, secretly changed build gate. Preserve the existing 6-MiB
hard limit while recording how much of the additional growth room remains.

Much of this version still contains topographic terrain, rocks and giant
mushrooms rather than the complete intended world. Later vegetation, actors,
inventory, AI, effects and gameplay consume real memory. Measure representative
content early and increase the non-BSP allowance when evidence requires it:

```
non_BSP_allowance = max(3 MiB, measured_non_BSP_peak + explicit_growth_allowance)
required_hunk = BSP_load_peak + non_BSP_allowance + safety_allowance
safety_allowance >= 2 MiB
```

Record the growth allowance and its workload assumptions. Reconcile allocations
by stage/category so that an existing baseline or temporary is not counted twice.
If measurement/model discrepancies or new unmodeled transients exceed the margin,
increase the allowance or reduce residency. Do not call a single successful
teleport a measured upper bound.

The polygon shape does not change this policy. Irregular polygonal residency
cores can follow streets, coastlines and occluding structures. Coverage, viewing
distance, hysteresis and collision continuity remain separate constraints.
Reducing the core only helps memory if the actual loaded payload shrinks; keeping
the original complete node tree/PVS can defeat otherwise tighter boundaries.

## Four different memory pressures

1. **Low/high hunk:** persistent decoded geometry and temporary input share one
   arena. Report low, high, their simultaneous peak and the allocation that set
   it. A snapshot after a temporary is freed misses the loading peak.
2. **Evictable cache:** aliases, sounds and optional prefetch occupy the gap.
   Record current/peak cache bytes, largest request, relocations, evictions and
   reloads. The low/high gap is potential cache capacity, not unused RAM.
   Enough total gap does not establish enough useful simultaneous model cache.
   Separate normal map cleanup from pressure-driven eviction. Do not count a
   cache relocation as a new logical resident asset or a gameplay eviction.
3. **Zone allocator:** small strings/structures use a fixed zone inside the
   hunk (currently 48 KiB by default). Report free total, largest free block and
   failed request; fragmentation or exhaustion can fail while the hunk is clear.
   Zone usage is already within the hunk reservation and must not be added twice.
4. **External Fast/Chip RAM:** OS, executable, stacks, rendering buffers, audio,
   video, UI and malloc allocations are outside hunk-gap accounting. At lifecycle
   checkpoints report both total available and largest contiguous Fast/Chip
   blocks. A shutdown-only total is insufficient to describe transient pressure.

At 320x200, the current video pixel/depth/surface-cache malloc buffers alone total
716288 bytes, before display bitmaps and audio. Small alias loading can hold a
source malloc allocation up to 512 KiB and another decoded-copy malloc allocation
up to 512 KiB simultaneously. These are source-derived examples, not a complete
OS memory budget. Low-memory fallbacks use different hunk/cache peaks and need
their own test cases.

Sprite models deserve explicit accounting before rc4 vegetation: despite the
field name `mod->cache.data`, sprite frames are allocated in the low hunk and
are not evictable alias-cache blocks. Inventory unique loaded sprite models,
frame dimensions/counts and temporary complete-file input. Model bytes can be
shared by placements; placement/entity state still has its own cost.

## Required lifecycle evidence

Use a transition ID and source/destination map identities; bind the run to exact
engine, config, map and content-manifest hashes. Include transition reason
(automatic region, explicit teleport, door, restart, save load) and stage.

| Checkpoint | Evidence to preserve |
| --- | --- |
| Outgoing scene, before teardown | Current state and highest gameplay/late-allocation peak since entry; live/cache/zone/external metrics |
| After teardown | Memory retained intentionally, cache/prefetch retained or cleared; compare repeated crossings for leaks |
| Before new BSP | Engine/progs/edict baseline and selected loader path |
| BSP loading | Ordered section allocations, temporary overlap, largest request and peak-setting label |
| After BSP | Decoded BSP residency, collision/visibility contribution |
| After actor/scenery load | Unique models, sprites, sounds, placements and entity/string costs |
| After player restoration | Inventory, hands/weapon/torch, movement and actor-state restoration costs |
| First presented frame | Renderer/client setup, visible assets and deferred model loads |
| Initial gameplay window | Warm-cache/reload behavior, frame/audio stalls and late allocations |
| Next departure or fatal exit | Persist final outgoing peak or failing request before counters reset |

Allocation counters update when allocations happen. Emit reports at meaningful
checkpoints; do not add unconditional per-frame disk writes. A bounded first-frame
sampling window can be opt-in. OS free-memory snapshots do not capture every
malloc transient; state that limitation or add matching allocation accounting.
The failure path should preserve arena, requested size, available amount, map,
stage and engine version without trying another large allocation.

Implemented in the unreleased repair: low/high allocation peak and label, largest
request, logical cache current/peak bytes, pressure evictions, cache moves, zone
free/largest block, and available/largest external Fast/Chip blocks. Automatic
phases are outgoing, after-unload, before-BSP, after-BSP, after-actors and
after-restoration and first-presented, plus scene snapshots and fatal-exit. Departure is logged before
peak reset. First-presentation detection is armed by every world load, including
save loads; it is independent of optional crossing-time telemetry. `dbg heap`
remains an explicit snapshot. Host tests label unavailable OS metrics with
`os_metrics=0`; zero values must not be interpreted as target exhaustion.

These changes passed a real host-allocator regression and an Amiga target compile.
They still require target playtesting. The full contract also includes bounded initial-gameplay measurement, exact
content/config identity, and asset-specific reload accounting. Those are not
all established by the initial counters. The restoration checkpoint is after
both saved-game and normal spawn paths. Transition IDs are process-local; archive
the append-only log separately for each playtest and bind it to the engine receipt
and content/config hashes. Snapshot OS free memory remains
partial evidence rather than a record of every malloc transient.

## Build contract and target reconciliation

Audit every final runtime BSP before image creation, including additional HDFs.
Probe the exact target ABI and preserve its provenance. Match the estimate to the
packaged engine's loader behavior: new source hashes alone do not establish that
an older supplied binary uses section streaming. A binary hash receipt verifies
identity, but the receipt also needs the relevant allocator/loader source hashes
and build flags, or an explicit equivalent loader-contract identity.

Check the normal filesystem search path for boot/world volumes and pack members.
If a valid BSP can take a whole-file fallback, model that coexistence explicitly
or reject the unverified route. Missing/malformed input must fail clearly.

The next stage beyond the BSP estimate is a dependency ledger for unique sprite,
alias and sound assets, progs/edicts, renderer limits and placement records. Until
that exists, the 3-MiB allowance remains an assumption requiring target checks.
No additional HDF, smaller compressed download or high host RAM raises target
hunk capacity.

Compare equal-content, equal-config target runs across both directions of region
crossings, fast noclip, dense town views, restart/teleport, save restoration and
both HDFs. Exercise cold and warm caches. Preserve raw reports and regressions in
[the bug journal](BUG_JOURNAL.md), including affected/introducing/repair and
verified-fixed versions. Do not replace a failure history with a later green run.

## Residency is not the same as per-frame visibility

The owner observed improved central-Balmora performance at view distance 1000
compared with a lower setting. This is a playtest observation, not a verified
fog/culling cause. Record matched camera, route, scene, settings and cache state.
Compare render/server/audio time, edges/surfaces, visible entities, cache misses
and transition frequency. A different cutoff may change work distribution or
cache/load behavior; it does not by itself prove that more polygons are cheaper.
The renderer's view cutoff does not necessarily shrink already loaded BSP data.

## Synthetic regression coverage

`tests/test_heap_watcher_native.py` compiles the actual `zone.c` allocator with
synthetic data. It checks temporary loading peaks survive freeing, later gameplay
allocations update the peak, teardown/new-load counter behavior, cache eviction
under hunk pressure, cache relocation without double counting, phase-log retention
and transition IDs, oversized cache requests, and independent zone fragmentation
and coalescing. It uses host structure layout and proves allocator behavior only;
the target-size estimator and emulator lifecycle acceptance remain separate.

Run with `python -m unittest discover -s tests -p test_heap_watcher_native.py`.
Use a host GCC-compatible compiler available as `cc`/`gcc` or set `CC` to its
path. These tests neither boot an emulator nor validate a playable image.

## Required watcher / profiler / optimizer pipeline

Progressive mapping and subdivision require a repeatable pipeline, not occasional
manual heap checks:

1. **Estimate:** freeze the reference target, ABI, matching engine/loader identity
   and reserve policy; model each final runtime map's ordered resident and
   temporary loading costs.
2. **Flag:** mark every over-headroom map with its shortfall, source hash, region
   identity/bounds and dominant allocations. Retain a reduction/subdivision queue.
3. **Profile:** measure the complete unload/load/restoration/first-frame/gameplay
   cycle, cache pressure, zone fragmentation and external Fast/Chip memory. Compare
   measured costs with the estimate and explain discrepancies.
4. **Optimize or subdivide:** remove redundant residency, share exact data or fit
   smaller loading regions to expensive content. Preserve required assets, UVs,
   collision, source-reference identity, overlaps and gameplay continuity. Record
   each candidate's before/after costs and remaining defects.
5. **Re-audit:** test the changed final payload and all affected neighbors with
   unchanged positive headroom requirements. Reject candidates that merely hide
   content or move the failure into another stage/storage layout.
6. **Target playtest:** validate reproduction paths, both-direction crossings,
   fast travel/noclip, restart and save/load. Bind evidence to exact binaries,
   configs and maps before calling the incident fixed or the image releasable.

Repeat this loop as high-cost settlements and later world-detail passes grow.
The current build estimator/gate and event-driven runtime watcher implement parts
of this contract. Optimization is still measured candidate work, not a finished
automatic optimizer. A green estimate is not a gameplay pass.


## Required pipeline: Heap Watcher → Profiler → Optimizer

Producer requirement, 3 October 2026: all three are essential as world content grows, in this order.

1. **HEAP WATCHER — detect pressure.** Audit final prepared maps and packaged loading paths; report used/free capacity, runtime reserve, safety headroom and growth margin. Flag exceeded limits and adjustable low-growth warnings. Watch the complete unload/load/restoration cycle; static estimates remain estimates.
2. **PROFILER — explain the pressure.** Identify which allocations, representations and phases consume the budget: resident payload, temporary loading overlap, cache pressure/fragmentation and external Fast/Chip memory. Also measure frame time, clipping/culling and transition stalls with matched scenes and effective settings. The watcher and profiler can share instrumentation, but their questions differ: “Are we running out?” and “Where, when and why?”
3. **OPTIMIZER — act on the evidence.** Decide what can be reduced or changed: remove demonstrated redundant representations, avoid unnecessary retained payload, or adjust boundaries/subdivision where measurements justify it. Preserve collision, textures, seams and gameplay state. Never lower safety reserves to force a pass; mitigation is not a fix.

The loop is: **watch → profile → optimize → watch/profile again → validate the exact packaged target → accept or revise**. A warning initiates investigation; it does not prescribe a split or establish a cause. Smaller cells or fewer visible polygons are not proof of faster gameplay.

Record version, circumstances, reproduction, cause, change, validation and unresolved limitations. No repaired playable-image acceptance may be inferred from an engine compile or a static audit alone.
