# Memory allocation and heap clearance

Current release status, 3 October 2026: [v0.0.27 is published](RELEASE-v0.0.27.md).
Its final private package passed the complete 2,717-map static heap gate and
both HDF filesystem readbacks. The worst modeled margin is 135,952 bytes after
the unchanged 3 MiB non-map allowance and 2 MiB safety reserve. No target heap
lifecycle or performance certification follows from these build results;
CRASH-01 remains open for exact-route target verification.

## Current v0.0.28 candidate accounting — 4 October 2026

The earlier combined image's matching-ABI audit records 58 modeled reserve warnings and
no modeled hard allocation-ceiling failures. The target ABI was measured with
the selected Amiga compiler in Linux Docker. All 10,766 image payloads and three
partition ownership checks passed; file readback does not establish live memory
clearance. The original stars/moons use fixed renderer storage, while guard
companions add first-use model-cache loading. Their disk bytes are not resident
RAM, and finite light/guard caps are not performance measurements. The newer
AWN2 point mask adds 2,048 fixed bytes plus a version flag. With the night gallery,
the corrected target has 648,636 CODE, 11,260 DATA and 1,395,360 BSS bytes:
2,055,256 total. Its BSS is 2,056 bytes larger than the preceding night/guard
engine, including the point mask, version flag and gallery mode. Corrected-image
readback and accounting are complete; actual live pressure is still pending.
Slower cloud phase is not itself a measured CPU saving.

Treat this as a private playtest candidate with explicit reserve warnings.
Native cold/warm loads, guard-cache pressure, transitions and high-pressure
routes remain acceptance work; no reserve policy, hard heap ceiling or reference
emulator memory setting was lowered to obtain these results. See the
[current release record](RELEASE-v0.0.28.md).

## Mandatory: LEAVE HEADROOM

Always leave headroom. A map that only just fits is not acceptable. Audit the
expanded target allocations and temporary loading peaks, reserve non-BSP state,
and leave an additional positive safety margin. Never silently lower reserves
or raise emulator memory to turn a failed reference-target build into a pass.

This guide applies to each town subdivision, world region and interior.
Update it when allocation behavior, runtime structures or the target changes.
Every incident belongs in [the bug journal](BUG_JOURNAL.md), with affected and
introducing versions, cause, repair candidate, verified fixed version and proof.
Unknown/pending fields must remain explicit. Documentation freshness is part
of completing a repair, not an optional follow-up.

## Current mapping baseline and mandatory checks as it grows

Much of the v0.0.27 world is still a LAND-derived terrain/topomap with authored
rocks and giant mushrooms. Detailed towns and interiors have additional content,
but this is not yet a complete gameplay world with every vegetation placement,
actor, encounter and system resident. Even at this incomplete mapping stage,
the rc3 map audit finds heap/headroom failures. Terrain visibility, subdivisions,
overlap coverage and runtime BSP expansion can consume substantial memory before
later scenery or gameplay is added. A terrain-heavy scene is not automatically a
cheap scene, and today's estimate is not a budget approval for future content.

Memory estimation and profiling are mandatory throughout mapping development:

- After conversion or a change to coverage, subdivision, geometry, textures or
  loader structures, estimate each final runtime map using the matching target
  ABI and retain its allocation breakdown, loading peak and remaining headroom.
- Before full-image assembly, run the audit on the final prepared map payloads,
  including maps destined for additional world HDFs. Reject insufficient reserve
  or safety headroom; a second disk adds storage, not engine heap capacity.
- During target playtests, profile scene loads and cell/sub-cell crossings using
  runtime heap reports. Include dense scenes and restart/teleport paths, then
  compare the measurements with estimates. Report external allocations and cache
  limitations separately; the hunk audit alone is not a whole-machine profiler.
- Preserve comparable reports with each candidate build and rerun them as new
  mapping/content is introduced. Identify increases before packaging, document
  their causes, and reduce or subdivide the working set where required.

Assemble-first development means creating representative content so optimization
can be measured. It does not postpone memory checks or permit shipping a build
that already exceeds its allowance. Leave room for later content and transient
loads; never treat a barely successful allocation as adequate clearance.

## Heap is not total Fast RAM

The reference emulator has 16 MiB Fast RAM. AmiWind reserves an 11-MiB hunk
heap (11534336 bytes); the remaining machine RAM is not additional hunk space.
The OS, executable, stacks, file buffers and other allocations also need memory.
Read the current engine reservation from sys_amiga.c rather than assuming it.

Low-hunk allocations hold persistent engine/map structures. High-hunk storage
holds loading temporaries and other high allocations. The space between them
is also used by evictable model caches. Reported hunk clearance is potential
cache capacity, not unallocated OS memory or a measurement of malloc usage.
Fragmentation, external allocations and future gameplay state still require
target validation and a conservative margin.

## Why BSP file size is insufficient

Disk records expand during loading. The current 32-bit Amiga ABI has 4-byte
pointers; a 20-byte disk face becomes a 64-byte runtime surface, a 24-byte node
becomes 40 bytes, and a 28-byte leaf becomes 48 bytes. Edges, texinfo, texture
headers/pixels, pointer arrays and generated collision hulls also allocate.
Hunk headers and alignment count. Temporary input may coexist with decoded
output; the maximum is determined by allocation order, not the largest lump
or final resident total alone.

The audit compiles sizeof probes using the selected Amiga SDK and engine
architecture flags. Read initialized sizeof constants, not distances between
object symbols: alignment padding once misleadingly reported a six-byte
pointer. Validate the ABI sanity checks and preserve compiler/profile provenance.
A host Python process or 64-bit host C sizeof is not the Amiga ABI.

## v0.0.27-rc3 incident: Seyda Neen sn012

Observed version: v0.0.27-rc3 local playtest. Trigger: issue `dbg aw hors 0`
from Jiub's name-entry scene. The game returned to AmigaDOS; WinUAE stayed open.
ERROR.TXT reported:

```
Hunk_Alloc sn012: need 2767120 bytes, free 1682208 of 11534336
```

The rc3 terrain-handoff correction added a 768-unit real LAND apron without
moving the existing FPS residency cores. sn012's BSP grew from 5507736 to
8395232 bytes; its visibility lump grew from 473407 to 2767103 bytes.
The streaming loader buffered that visibility lump in the high hunk, then
allocated a second resident copy in the low hunk. The second allocation failed.
The held-input preservation change does not allocate this map data. The loader's
double-buffer behavior predates rc3; its first introducing version is unverified.

Repair introduced during rc3 and included in v0.0.27: the loader reads byte-only
visibility, lighting and entities directly into final storage. This preserves
bytes and avoids the extra complete input copy. The real loader regression uses
the failing 2767103-byte size, checks byte identity and absence of temporary
allocation, and exercises invalid/truncated input. The repaired Amiga engine
compiled. Fatal exits now print the reason after closing the game screen and
still attempt ERROR.TXT. The older minimal boot image lacks AmigaDOS Type;
inspect the detached filesystem with host tools when needed.

Verified fixed version: pending. Eliminating the failing second copy is not
proof that subsequent nodes, hulls, actors and renderer allocations fit.
The historical unbounded sn012 estimate after the loader-only correction was
10803456 resident bytes and a 10860976-byte loading peak, before non-BSP reserve
or safety margin. That candidate failed policy. Later bounded town maps and
the final 2,717-map package pass the static gate; published v0.0.27 still requires
the exact target lifecycle test before this incident can be closed.

## Separate loader trap: extra-HDF search paths

The pre-repair section-streaming path opened `com_gamedir + map name` directly.
Additional world HDFs are registered as filesystem search paths (`AW_WORLDn:id1`),
not as changes to com_gamedir. A map moved to those volumes could therefore miss
section streaming and fall back to COM_LoadStackFile, holding a complete BSP
input buffer while decoded structures accumulated. A section-only estimate would
understate that path's loading peak even when the same map passed on the boot disk.
This is a separate issue from sn012's duplicate visibility allocation.

Affected code: inspected v0.0.27-rc3 working tree and multi-HDF layout. First
introducing version: unverified. Target occurrence: not yet reproduced; this is
confirmed path-analysis evidence, not a claimed observed target crash.
The repair introduced during rc3 and included in v0.0.27 uses COM_FOpenFile and the normal
search order, then streams sections relative to the returned member's starting
offset. This includes mounted volumes and pack-file members without assuming
BSP offsets are absolute file offsets. Loader regressions and Amiga compilation
passed; a verified target-fixed version still requires multi-volume playtesting.

Keep build estimates tied to the actual loader path. Until streaming is verified,
account for the complete-file fallback or fail acceptance; do not assume a second
HDF makes runtime memory safer. Validate maps from both boot and world volumes,
including lookup precedence, missing files, member-relative bounds and read errors.

## Build-time audit

The compilation tool is `tools/check_world_map_heap.py`. It inspects BSP29
lumps, compiles the target ABI profile, models ordered loader allocations and
writes a per-map JSON breakdown. A failing audit returns nonzero. The full-image
pipeline must run the audit on its final prepared runtime maps before HDF
assembly and preserve the report in its build evidence. Asset-free notice builds
are separate; they do not establish full-map clearance.

Example standalone use (installed matching SDK required):

```bash
python tools/check_world_map_heap.py \
  --maps /path/to/private/scene/id1/maps \
  --sdk /path/to/amiga-sdk \
  --out /path/to/private/heap-audit.json
```

Current conservative defaults reserve 3 MiB for non-BSP engine/gameplay state
and a separate 2 MiB safety headroom. These are explicit assumptions, not a
measured upper bound for all possible gameplay. Overrides must remain positive,
be justified with target measurements and retain the reference target; they are
not a release bypass. A passing estimate is not an emulator or gameplay pass.

The report includes map/hash, ABI provenance, each resident allocation, largest
input section, actual ordered loader peak, reserve, safety margin, total required
bytes and remaining clearance. Negative clearance fails. Retained rc3 boot maps:
774 of 802 boot maps pass the estimate, 28 fail under these defaults. The complete
final-HDF readback audit covers 2678 BSPs: 2650 pass and the same 28 fail. That
report includes both world partitions and binds the maps to file/HDF hashes.
These are section-stream estimates; the extra-HDF loader caveat above applies. Aggregate
source BSPs and the actual runtime-selected subdivisions must be distinguished
when prioritizing repairs; do not load or ignore them based on filenames alone.

## Audit while crossing cells

The v0.0.27 runtime records the hunk load peak after old-map memory is
cleared, then reports use/clearance at scene spawn, including automatic sub-cell
loads. Allocation paths update the peak; no per-frame polling is added. A
transition or explicit diagnostic appends `heap-audit.log` when writable.
Use `dbg heap` for the current snapshot and load peak. The reported scene name
identifies the resident world model where available.

A peak clearance below 2 MiB prints a LOW_HEADROOM warning. This is a diagnostic,
not a crash recovery or replacement for the build gate. It covers hunk storage,
not total OS memory or every malloc allocation. Runtime auditing is included
in the v0.0.27 engine; older playtest disks may predate it.

## Profile, then reduce or subdivide

1. Identify the actual resident map and failing allocation, preserving the
   fatal report and source hash. Compare with the previous accepted version.
2. Rank resident allocations and loading peaks. Separate visibility, terrain,
   brush geometry/collision, textures/lightmaps, dynamic models and non-BSP state.
3. Prefer byte-preserving sharing and avoid duplicate temporary storage first.
   Measure the saving; do not assume compressed disk bytes equal resident use.
4. If the resident region remains too heavy, reduce its residency core or split
   it. Derive visible coverage separately: retain sufficient view distance,
   crossing hysteresis and corner coverage. Asymmetric aprons are possible only
   with seam/collision/visibility validation on each edge.
5. Preserve original cell coordinates and object identities, state and held
   input across subdivision changes. Do not duplicate gameplay objects because
   geometry appears in neighboring coverage. See [cell changing](CELL_CHANGING.md).
6. Re-run the full affected-map audit with the same reserve policy, then test
   both-direction crossings, fast noclip, restart/teleport, interiors, NPCs,
   hands/torch and audio on the target. Record measured peaks and headroom.
7. Update the incident and fixed-version evidence before packaging or publication.

A smaller town-square core does not automatically reduce all PVS/node data if
conversion still retains the whole source tree. Inspect the allocation breakdown
and actual selected payload rather than promising a fix from subdivision alone.

## Whole-cycle profiling and buffer planning

Profile the outgoing scene before resetting its peak, old-scene unload, persistent
state after cleanup, new BSP loading, restored actors, first presented frame and
warmed gameplay. Include save/load and explicit restart/teleport paths. Hunk gap
is only one metric: cache occupancy/evictions, zone largest-free-block and external
Fast/Chip allocations need separate accounting. Scene spawn alone is insufficient.

Under the current 11 MiB / 3 MiB baseline / 2 MiB safety policy, the modeled BSP
loading peak may use at most 6 MiB. Aim new subdivisions near 5 MiB as a planning
target, leaving roughly 1 MiB growth room inside that map allowance. This target
is not yet a new gate and does not prove future complete gameplay fits. Polygonal
shapes receive no discount to reserves. Baseline planning should be at least
max(3 MiB, measured non-BSP peak plus an explicit upcoming-content allowance);
retain the 2 MiB safety floor and increase it for measured/model discrepancies or
unmodeled transients. Record assumptions with each matched build.

See [the fog observation and profiling plan](HORSTATORS_MUSINGS_2026-10-03.md).

## Incident reporting: correction versus mitigation

Use the version/circumstances, reproduction and fix structure in
[the rc3 crash report](HEAP_CRASH_v0.0.27-rc3.md). Producer's rule:
**mitigation is NOT a fix; it is a bandage**. Record workarounds and partial
corrections separately, and keep the verified fixed version pending until the
underlying issue is corrected and the required target acceptance succeeds.

## Complete lifecycle watcher and over-budget regions

See [the heap watcher](HEAP_WATCHER.md) for build-stage estimates and event-driven
runtime profiling across unload, BSP load, actor/player restoration and first
presentation, including cache, zone and external Fast/Chip memory. See
[the map memory profile](MAP_MEMORY_PROFILE.md) for the 28 over-headroom regions,
shortfalls and dominant allocations. Mark failures explicitly and prioritize
reduction/subdivision, preserving complete coverage and state continuity. A
smaller core that still retains an oversized parent tree/PVS is not a fix.
Every replacement must pass the same headroom gate and target crossing tests.

## Used/free margins in future build receipts

The rc3 repair builder now writes `heap-watcher.json` after the map audit and
embeds it as `build.json.heap_watcher` for successfully assembled images. It
reports estimated map-peak use, free capacity before reserves and the growth
margin after the non-map reserve and mandatory safety headroom. Negative margins
reject packaging. Runtime measured use/free remain null until target evidence
exists. See [the receipt field definitions](HEAP_WATCHER.md#build-receipts-used-free-and-growth-margin).
These receipts support progressive mapping; they do not make the current repair
candidate a verified playable HDF or replace whole-cycle profiling.

## Duplication and deduplication guidelines for future growth

Account separately for packaged bytes, resident Hunk/cache/zone bytes, temporary
loading peaks and external Fast/Chip allocations. A smaller archive or second HDF
does not prove lower runtime memory use. Record before/after figures for each
budget and rerun the final-map headroom gate with the matching loader receipt.

- Remove redundant source-to-resident copies when the loader can read directly
  into the final allocation; validate bounds, short reads and pack-member offsets.
- Share byte-identical textures, light data or visibility rows only when all
  references, offsets, lifetimes and ownership remain correct. Preserve texture
  pixels, UVs, material flags, decoded visibility and collision behavior.
- Deduplicate repeated assets on disk with explicit references and stable source
  identity. Runtime sharing must also use a common cached/resident object; two
  filenames or two disks can still produce two allocations.
- Retain terrain/scenery overlap required for view coverage and reliable seams.
  Reduce each loading region's actual retained payload rather than merely making
  its selection core smaller. Check Seyda Neen and Balmora neighbors in both
  directions and preserve held inputs and gameplay state through handovers.
- Do not merge disconnected world leaves merely because their contents or
  visibility match: render traversal depends on correct parent ancestry. A
  deduplication that breaks that relationship is a regression, not a saving.
- If packing/compression is proposed, count the compressed input, decoded output,
  scratch space and simultaneous old/new resources. A new codec requires version,
  bounds and malformed-input checks, plus equivalent decoded output.
- Publish the issue/version/reproduction/cause/change and verification evidence.
  Keep mitigation explicitly separate from a verified fix; missing target
  measurements cannot be replaced with a successful one-off load.

A general automatic optimizer is not complete. Current candidate reductions and
exact-data sharing remain gated experiments until their final payload and target
transition behavior are accepted. Always leave headroom for subsequent content.

## Standing requirement: dense towns need bounded residency

Producer requirement, 3 October 2026: treat future settlements as potentially
polygon-heavy. The Seyda Neen/Balmora repair must establish reusable town
optimization rather than an exception that only makes one arrival scene fit.
A subcell count is not a memory budget: selection boundaries can be small while
each BSP still retains the parent town's large terrain or visibility payload.

Use content density and measured loading peaks to choose further subdivisions.
Each candidate must reduce actual retained world terrain/PVS and/or complete
out-of-coverage scenery and collision components. Retain all intersecting objects,
original textures/UVs and required source placements across the region union.
Keep adequate draw, hysteresis and collision overlap and preserve gameplay state.
Never lower the non-map reserve or safety margin simply to pass a town.

The process is: identify expensive cells, profile their allocation breakdown,
construct bounded payloads, compare before/after residency and loading peaks,
audit every affected neighbor, then test both-direction crossings on the target.
Apply the same checks when architecture, vegetation, actors or gameplay systems
are added to any future settlement. Also measure frame cost; a heap pass alone
cannot establish tolerable performance.

The builder introduced this order during rc3 and retains it in v0.0.27: the
final map heap gate runs **after** Seyda
subcell regeneration and actor annotation, before content fingerprinting and HDF
packaging. This prevents clearance evidence from referring to maps that are
subsequently replaced. The stable private image is assembled and read back;
runtime acceptance remains pending.

### Measured adaptive subdivision prototype

`tools/adaptive_town_regions.py` now provides a proposal planner with a supplied
candidate evaluator. That evaluator must compile and estimate actual bounded BSP
payloads; area-based guesses are not clearance evidence. The planner tries both
rectangular split axes, prioritizes failing/heavy cores, preserves each parent's
core union and the 896-unit coverage apron, and does not subdivide cheap regions.
It records candidate source identity, before/after costs, growth margins and
rejected splits. It stops on the native 64-region limit, minimum core size or no
measured saving; unresolved cells remain explicitly flagged. Five focused host
tests cover these policies and ownership/coverage behavior.

This planner is not yet wired into production conversion and does not install
region tables or approve an HDF. Its hard gate remains the documented 6-MiB map
peak; the separate 5-MiB planning target exposes inadequate growth room. Real
candidate compilation, full-map/neighbor audits and target transitions remain
required before accepting a new town layout.


## Boundary placement is a measured choice, not an FPS guarantee

Owner clarification, 3 October 2026: the suggested off-centre cut near sn017 is illustrative, not a required coordinate. Candidates may move boundaries or use nonuniform subdivision where actual payload measurements support it. Record the layout and map identity: sn017 in the original 25-region directory is not the same region as sn017 in the adaptive 64-region proposal.

Evaluate both sides of every changed boundary. Preserve the coverage apron, collision continuity and gameplay state; avoid merely transferring a failure to the neighbour. Density heatmap bins guide investigation but do not predict resident visibility, collision or loader allocation costs.

Acceptance has two independent axes: (1) loading-cycle peak and useful growth headroom under unchanged reserves, and (2) measured gameplay frame time plus crossing stalls and frequency. Subdivision can reduce payload but increase reloads, repeated shared-data preparation or clipping work. It must not be advertised as a performance improvement without matched target tests. Include requested and effective view distance, fixed position/view and settings; measure steady gameplay and both-direction crossings separately. The Balmora longer-view observation remains a hypothesis to test, not proof of its cause.


## Required pipeline: Heap Watcher → Profiler → Optimizer

Producer requirement, 3 October 2026: all three are essential as world content grows, in this order.

1. **HEAP WATCHER — detect pressure.** Audit final prepared maps and packaged loading paths; report used/free capacity, runtime reserve, safety headroom and growth margin. Flag exceeded limits and adjustable low-growth warnings. Watch the complete unload/load/restoration cycle; static estimates remain estimates.
2. **PROFILER — explain the pressure.** Identify which allocations, representations and phases consume the budget: resident payload, temporary loading overlap, cache pressure/fragmentation and external Fast/Chip memory. Also measure frame time, clipping/culling and transition stalls with matched scenes and effective settings. The watcher and profiler can share instrumentation, but their questions differ: “Are we running out?” and “Where, when and why?”
3. **OPTIMIZER — act on the evidence.** Decide what can be reduced or changed: remove demonstrated redundant representations, avoid unnecessary retained payload, or adjust boundaries/subdivision where measurements justify it. Preserve collision, textures, seams and gameplay state. Never lower safety reserves to force a pass; mitigation is not a fix.

The loop is: **watch → profile → optimize → watch/profile again → validate the exact packaged target → accept or revise**. A warning initiates investigation; it does not prescribe a split or establish a cause. Smaller cells or fewer visible polygons are not proof of faster gameplay.

Record version, circumstances, reproduction, cause, change, validation and unresolved limitations. No repaired playable-image acceptance may be inferred from an engine compile or a static audit alone.


## Vertical boundary review — 3 October 2026

An externally supplied review supports a small measured candidate set: nearby vertical cuts and a horizontal control, independently bounded terrain/PVS/collision, complete intersecting buildings retained, and unchanged visibility/hysteresis coverage. Its objective is to reduce the larger child loading peak, not equalize land area, heatmap color or polygon counts. This fits the current one-world-BSP model; it does not require two complete resident worlds.

In the focused 512-source-unit heatmap, the 0.25 scale makes the 896-runtime-unit apron seven bins wide per edge before outer-bound clipping. Illustratively, halving a 1792-runtime-unit-wide core with unchanged height reduces uncapped coverage width from 3584 to 2688, or 75%, not 50%. This is an area explanation, not a RAM estimate. Hotspots near a cut may remain in both loading aprons.

Actual retained candidates were re-estimated consistently with the rc4 node-loader allocation order. This trial shifts the shared original-25 sn017/sn018 vertical boundary; it is not a new equal subdivision or a target FPS test:

| Boundary X (runtime units) | sn017 loading peak | sn017 growth margin | sn018 loading peak | sn018 growth margin |
| --- | ---: | ---: | ---: | ---: |
| 1024 (baseline) | 6,497,984 B | −206,528 B | 4,882,752 B | 1,408,704 B |
| 768 (two focused bins left) | 6,317,072 B | −25,616 B | 5,363,264 B | 928,192 B |
| 640 (three focused bins left) | 6,247,120 B | 44,336 B | 5,516,480 B | 774,976 B |

Margins are after the unchanged 3 MiB non-map reserve and 2 MiB safety headroom in the 11 MiB Hunk. The three-bin shift clears the static ceiling but leaves only 43.3 KiB for sn017 growth: inadequate practical room and not an accepted layout. Original compile-time estimates were invalidated by the concurrent estimator update; these results explicitly re-evaluate every retained candidate with one current estimator. Geometry receipt hashes remain available privately.

Next comparisons should include actual subdivision candidates, a horizontal control and per-representation/shared-resource breakdowns. Preserve seams and input/equipment state, then profile exact packaged crossings and steady gameplay. Requested view distance must be recorded alongside the effective clamp; a current clamp does not diagnose a historical build's behavior.


## Historical rc4 estimate of the retained 64-core proposal

Re-estimated 3 October 2026 after the rc4 node-residency loader change. All 64 candidate BSP SHA-256 identities match the original proposal; geometry was not rebuilt for this comparison. The estimator models the changed loading order and transient hull0/node overlap rather than simply subtracting renderer-record bytes.

| Measure | Earlier rc3 estimator | Current rc4 estimator |
| --- | ---: | ---: |
| Cores within 6 MiB map ceiling | 64 / 64 | 64 / 64 |
| Cores above 5 MiB planning target | 39 | 39 |
| Highest modeled loading peak | 6,271,536 B | 5,886,736 B |
| Smallest growth margin after reserves | 19,920 B (19.5 KiB) | 404,720 B (395.2 KiB) |

The 3 MiB non-map reserve and independent 2 MiB safety headroom are unchanged. These margins are within the map allowance, not total machine free RAM. This was a saved-ABI estimate of the candidate before its later normal-converter generation; it was not evidence of packaged runtime acceptance. The 39 planning-target misses applied to that estimate only. See the later normal-converter audit below. No FPS improvement follows from this static estimate.

The heatmap must label current and historical estimates separately. Its full-town polygon background is spatial context, not the geometry or resource count of the 64 individual bounded candidates. See [node residency](NODE_RESIDENCY.md) and [the required watcher/profiler/optimizer pipeline](HEAP_WATCHER.md).

## Normal-converter bounded-town audit — 3 October 2026

The measured Seyda and Balmora layouts are now generated through the normal map
conversion path. These saved target-ABI reports establish static per-map policy
results, not a final packaged HDF, measured runtime allocation or accepted
gameplay. Keep the 11 MiB Hunk, 3 MiB non-map allowance, 2 MiB safety margin and
6 MiB modeled BSP ceiling unchanged; 5 MiB remains a planning target, not a hard
gate.

For bounded Seyda, the ordinary converter emitted 64 core maps plus the docks,
court and fallback entries: 67/67 estimates pass. The worst estimated peak is
5,884,944 bytes and the smallest post-reserve growth margin is 406,512 bytes.
The later complete actor/contact and final heap gates, image assembly and HDF
readbacks passed for this normal-converter output. Target transitions remain pending.

For Balmora, a 64-core non-overlapping partition plus the fallback has 65/65
static estimate passes. The source-to-region check covers all 1,488 references
with zero lost references; the core tiling has no holes or overlaps. Source and
output hashes are recorded in the audit. The revised layout merges inexpensive
outer regions to retain the 64-slot limit and splits the prior oversized area:

| BSP | Estimated load peak | Margin after 3 MiB + 2 MiB reserves |
| --- | ---: | ---: |
| merged `bm000` | 3,087,760 B | 3,203,696 B |
| upper `bm001` | 5,971,920 B | 319,536 B |
| lower `bm027` | 5,615,520 B | 675,936 B |
| `bm019` / `balmora` fallback (worst) | 6,155,504 B | 135,952 B |

The layout keeps the 896-unit visual apron, existing 224-unit physical collision
apron, 96-unit hysteresis and 540-unit draw policy. The lower `bm027` core is 128
units high. Because hysteresis is larger than the core height, the adjacent map
may remain active while the player crosses that core's center within the
hysteresis band; half-open core ownership is still unique and switch thresholds
were not changed. Test seam, scenery and collision continuity across the split
and merge in both directions, including rapid noclip and held controls. No target
transition or FPS result is claimed. The later image/actor/final heap gates
passed; target playtesting remains pending, so the load incident remains open.

## Transactional exact-sharing candidates — 3 October 2026

The normal source pipeline now stages exact BSP geometry sharing and independent
light/PVS deduplication for `addamasartus`, `bmmages` and `bmtemple`. It runs
after subcell regeneration and actor annotation/baking, then before independent
actor-contact checking, the final heap gate and content fingerprinting. The
optimizer validates every candidate before replacing any original map, rolls
back prior replacements if a commit fails, and rechecks output hashes before
the final gate and fingerprint. This protects the input set from a partial
failed optimization.

An initial candidate failed safely at Mages Guild face 285 (light offset 11,723):
wide intermediate UV arithmetic calculated a 30-byte sample span, while
per-operation binary32 arithmetic calculated 36 bytes. Copying the shorter span
would have changed the following six bytes. The target FPU's intermediate
precision is not established. The corrected light-range policy preserves the
longest original referenced byte span required under both policies. It changes
no UVs or extents and does not shorten source light data. The failed attempt and
receipt are retained; originals were not replaced.

Independent Python render-input validation and deduplication checks passed for
all three candidates, including face order/coordinates/winding, UV and extent
inputs, light samples, decoded visibility, and protected collision/model/lump
bytes. The Linux C loader comparison passed one synthetic before/after pair
(3 faces) and three real map pairs: Mages Guild 40,530 faces, Temple 35,242,
and Addamasartus 23,426 (99,198 real faces total). This does not establish Amiga
FPU/rendering behavior or target gameplay.

Using the existing target-ABI size receipt, the corrected static peaks and
remaining map headroom under the unchanged 3 MiB non-map reserve plus 2 MiB
safety margin are:

| Map | Peak | Remaining margin | Estimate gate |
| --- | ---: | ---: | --- |
| `addamasartus.bsp` | 5,812,864 B | 478,592 B | pass |
| `bmmages.bsp` | 5,688,464 B | 602,992 B | pass |
| `bmtemple.bsp` | 5,905,872 B | 385,584 B | pass |

These three-map numbers use saved ABI sizes; they are not a fresh allocation
probe or target playtest. Subsequent final packaging separately passed the
receipt-bound optimizer/actor/heap gates for all 2,717 maps and both HDF readbacks.
Runtime profiling remains pending. The matched `vis -fast` versus full-VIS
experiment was stopped on 3 October with its inputs, logs and saved state
preserved privately. It is deferred optional research; resumption is unverified
and no comparative FPS or memory result is available.

See [the corresponding bug-journal record](BUG_JOURNAL.md#mem-geometry-01-transactional-geometrylight-sharing-candidates)
for the version/cause/fix/status distinction. The rc3 duplicate-visibility-copy
incident remains open until the repaired trip and lifecycle pass on target.
