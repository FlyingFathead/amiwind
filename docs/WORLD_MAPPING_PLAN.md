# World mapping and streaming plan

Core design recorded 27 September 2026. This is the intended architecture;
checkpoint-015 still loads one resident scene and streams only music during play.
The existing terrain packets and scenery index are host experiments, not proof
that this whole runtime design is already implemented.

> Source cells preserve Morrowind's world structure; smaller runtime chunks
> determine what the Amiga loads.

> *Fog only saves rendering work when we also cull what it hides.*

## Source coordinates remain authoritative

Exterior CELL records form an 8192 x 8192 source-unit grid. Compute cell X/Y
with floor division, including negative coordinates. For example (-11394,-71667)
lies in (-2,-9), not (-1,-8). Retain source positions and transforms in the host
manifest. At the current scale of 0.25, a source cell spans 2048 local units.

Current scene conversion uses:

- local X = (source X - center X) * 0.25
- local Y = (source Y - center Y) * 0.25
- local Z = source Z * 0.25
- current center = (-11264,-71680)

These are current converter coordinates, not a universal engine-format mandate.
Document any future axis, scale or origin change and rebuild collision, doors,
actor placement and diagnostics together. A moving/local origin must preserve
stable world position and state, not accumulate rounding drift between chunks.
Interior cells are distinct named spaces with their own coordinates and door
links; they are not grid tiles appended to exterior terrain.

## Source cells are not RAM allocation units

Start with the owner's [Seyda Neen vicinity](SEYDA_NEEN_SCOPE.md). Inventory a
neighboring source-cell region, then select the desired coverage using bounds.
Accept the connected exteriors, including the opposing shore and Silt Strider
approach, before the first interior. Keep local containers, actors and opening
state in that same area as the first gameplay slice; defer other towns.
Do not force an entire 3x3 source-cell region into memory just because it was
useful for conversion. Choose smaller runtime chunk dimensions from measured
resident geometry, collision, textures, actors and I/O cost. No universal chunk
size or active-ring count has been accepted yet.

A host manifest should connect source cells, placed-reference IDs, shared base
records/assets, runtime chunk IDs, data extents and conversion hashes. Keep
original record type and scripted/disabled/deleted state. An omitted unsupported
record must be reported rather than silently interpreted as empty space.

An object belongs to a stable placed reference, even when its transformed bounds
intersect several chunks. Give it one owner and dependency/overlap entries; do
not duplicate colliders, inventory or scripts at seams. Origin-only rejection
omitted parts of the prison ship in checkpoint-014. Checkpoint-015 selects that
explicit assembly by bounds; general boundary-structure selection still needs work. Shared
building meshes, actor appearances and textures should load once per cache entry,
with separate placement/state records. Convert supported visible ACTI objects
explicitly; editor markers do not become visible scenery.

## Optional polygonal POI regions

Horstator's [28 September evening note](HORSTATORS_JOURNAL_2026-09-28.md#evening--polygonal-poi-regions-if-streaming-is-insufficient)
adds a fallback experiment only if fog-assisted exterior streaming/offloading,
including brief pauses at selected crossings, cannot meet the target budgets:
compile polygonal regions around POIs and explicitly swap scenes at controlled
crossings, with inexpensive backdrops and brief Loading feedback. Seyda Neen is
the first proposed region. Preserve cell/chunk loading as a separate option.
Fog provides a visibility limit for scheduling work; culling alone does not free
RAM. Keep collision and movement headroom ready beyond what the fog conceals.
For outdoor cell-crossing pauses, use only a minimal upper-center "Loading..."
box, without a large overlay window. Preserve the original-style loading screens
for interior/exterior transitions that already use that presentation.

Source cells define original data and game semantics; runtime regions define
residency. They need not have the same boundaries. Record their many-to-many
mapping, world transforms, region dependencies, crossing/arrival data and stable
reference ownership. Overlap is coverage, not permission to duplicate active
objects or their state. Preserve original cell-dependent scripts, environmental
rules and location queries even when a source-cell boundary lies inside one
loaded region.

Use "polygonal BSP regions with associated resource packs" for this proposal.
The earlier "WAD" shorthand referred to the idea of swapping levels. Current
AmiWind scenes are loose BSP files in `id1/maps/`; `gfx.wad` serves graphics.
The polygon describes the region footprint, independently of its file container.
Reuse the compiled scene/asset path where practical and measure the
actual resource budgets. Snapshot dirty persistent state before releasing a
region, validate destination dependencies, and provide recovery without assuming
both whole scenes remain resident. Enter play only after the destination's
collision and state are ready. Preserve baseline recipes and compare identical
routes for memory, loading stalls, audio and seams before choosing a strategy.
This is design work only; no region converter or loader is claimed as complete.

### Elevated views and the topographic map

Major unresolved risk, owner follow-up at 20:36 Helsinki: POI-region boundaries
may conflict with open-world traversal and continuous topographic coverage,
especially when the player can see above a concealing horizon or canopy.
Experiment with an elevated view/residency mode above configurable height X
over local terrain, using a broader/coarser terrain representation if feasible.
Define the up-axis and terrain-height query explicitly; the proposed plane/vector
is a representation choice, not a new disconnected gameplay coordinate system.
Keep map coordinates, reference identity and state consistent. Test visibility
into adjacent regions, interaction/collision from above, safe descent/detail
restoration, threshold hysteresis and peak memory. Ground-level transition tests
alone cannot validate the open-world design. No solution is selected yet.

### The fog is our friend

Preserve Morrowind's obscured
distance and sense of mystery while using the visibility limit to bound real
rendering work and resource residency. Horstator's reference is Xbox-era
Morrowind under constrained graphics resources. This is both an atmospheric goal
and a performance strategy to measure, not a claim that a fog effect by itself
culls or unloads data. Apply it to both streaming and optional BSP regions.

## Next milestone: entire-world terrain topomesh

Owner priority, 28 September 2026, 20:38–20:39 Helsinki: export the entire map's
terrain into a topographic mesh and provide a separate terrain inspection scene.
This is full source-world coverage, not another bounded Seyda Neen export.

1. Index all exterior terrain in the selected source-data set. Export consistent
   world coordinates and cell identities, report extents/missing cells, and keep
   the original full-detail baseline. Do not fabricate elevations to fill gaps.
2. Extract source water levels/coverage separately; inspect coastlines and
   terrain/water relationships without treating the temporary sea plane as truth.
3. Generate selectable terrain LODs with retained boundaries and measurable
   geometric error. Inspect neighboring LOD joins, hills and elevated views.
4. Provide a dedicated observer scene/viewer with free camera, coordinate/cell
   readout, optional wireframe/boundaries, water toggle, fog/view-distance controls
   and LOD selection, without gameplay actors or opening progression.
5. Compare mesh counts, resident/peak RAM, loading stalls, frame time and visual
   error. A complete host dataset/overview is distinct from native residency:
   use bounded chunks or a coarse overview rather than assume the whole original
   mesh fits in Amiga memory. Preserve both cell and region experiments.

This inspection work should inform region footprints, streaming/prefetch margins,
fog and height-triggered overview experiments before those choices are fixed.
It is planned work; dev4 does not include a whole-world mesh or observer mode.


## Recovered follow-up: world-scale flight and precomputed geometry experiments

This follow-up was recovered from the surviving conversation after the frozen
v0.0.21-dev4 package. It extends the terrain-topomesh milestone; it does not
change dev4's implementation status.

Add a dedicated native observer/stress mode, proposed as `dbg fly 1`, that can
traverse the entire terrain coordinate space without normal gameplay simulation.
The first representation should be deliberately simple: whole-world terrain
coverage, ground colour/texture identity where practical, and a sea-level plane,
with free noclip flight, fog, water, cell/region overlays, selectable terrain
LODs and profiling counters. The complete source topology may exist in the host
conversion/output model while the Amiga keeps only bounded/coarse resident
representations. "Entire world loaded" therefore means the whole world is
addressable by the experiment, not that every full-detail triangle is resident
at once.

Use this mode to determine whether the local mechanisms scale. Profile identical
flight paths and viewpoints for triangle/edge submission, visible surfaces,
cache churn, resident and peak memory, load/offload latency and audio continuity.
Include high-altitude passes specifically because levitation makes false horizons
and missing neighboring terrain much easier to expose.

Also evaluate **something akin to Nanite in spirit, but on these old pieces of
gear**: host-precomputed geometry hierarchies/clusters and multiple immutable
representations selected by very cheap runtime rules. Candidate inputs to that
selection include projected size, distance, altitude, fog limit and measured
visibility. Distant structures may become simplified geometry, baked detail,
silhouettes or nothing where the error is hidden. The Amiga must not perform
expensive mesh simplification at runtime. Any added selection hierarchy must beat
the existing AmiQuake renderer in measured total cost before adoption.

## Compact indices without accidental signed limits

Use unsigned 16-bit local indices where the format and measured counts permit.
Validate counts and bounds in both host output and native loading. The pier bug
was a signed interpretation of an unsigned plane index, not insufficient address
space; bank switching was not the remedy. A namespace with 65536 entries needs
32-bit counts even if each valid index is 16-bit. An overflow must fail clearly.

For larger content, split independent chunks, reduce redundant geometry, or
version a wider format. Do not truncate indices or globally force addresses,
world coordinates and file offsets into 16 bits. Chunk IDs plus local indices
can express references without making every resident lookup global. Runtime
representation changes still need profiling on the actual target CPU.

## Loading, visibility and eviction are separate decisions

1. A coverage manifest says which world data exists and where it belongs.
2. The resident set contains the current collision/interaction neighborhood,
   visible dependencies and a measured prefetch margin.
3. Frustum and fog-distance tests reject invisible nodes/models before detailed
   rendering. Partially visible bounds must survive rejection.
4. Eviction releases unneeded chunk resources while retaining persistent state
   keyed by stable reference ID. Shared assets remain until their last user leaves.

Fog must not hide absent collision or justify dropping arbitrary visible faces.
Short visibility can reduce rendering and residency requirements, but a safe
movement/collision margin must remain ready even when the player turns quickly.
Limit detail before export using material/UV-aware geometry reduction and tested
variants; smaller textures alone do not reduce edge/surface counts.

Use bounded reusable I/O buffers, explicit queue priorities and measured read
sizes. Music deadlines come first; nearby collision and a pending interior
transition outrank distant detail. A large HDF is capacity, not extra CPU time,
RAM or guaranteed bandwidth. Each current filesystem read is synchronous; a
cooperative read budget does not make the underlying operation asynchronous.
Compare cold and warm cache, sequential throughput, seek latency and worst frame
stall before choosing compression or storage layout. Preprocessing belongs on
the host wherever it can replace repeated target work.

## Interior/exterior handoff

After exterior acceptance, first target: Census and Excise office. Read the original DOOR destination cell,
position and orientation. Validate the destination and safe spawn, show loading
feedback, release area-specific data in a controlled order, load the new scene
and restore input only when collision is ready. Budget peak overlap memory;
do not assume both complete scenes can coexist. Provide failure/recovery behavior
if destination loading fails. Keep music state and stable actor/quest state
separate from disposable geometry. Repeat entry/exit to detect leaks and stale
references. Opening character-generation state and post-registration state must
be tested separately, including the prison ship assembly's visibility.

Container contents, player inventory, door state and actor/quest changes are
mutable data keyed separately from shared meshes or base records. Area unloading
must not recreate looted containers or erase changed state. Keep bounded lookup
pages and sparse state changes; persistent save/load is a separate acceptance
gate from retaining state within one session. See [CONTAINERS.md](CONTAINERS.md).

## Coverage and the temporary sea

The checkpoint sea is a flat Z=0 placeholder extending beyond the small terrain
slice. Its debug toggle changes visibility only. It is not the actual archipelago,
verified water metadata or a continuous world. Replace it as nearby source cells
are converted. A host topographic report should distinguish true LAND heights,
water datum, selected coverage and missing cells. Never fill unknown land in a
report with invented elevations. Keep this limitation in code and release notes.

## Acceptance and profiling gates

Before enabling runtime chunk streaming, record:

- heap/cache/Chip/Fast budgets, shared assets, peak transition memory and failures;
- geometry/edge/surface high-water marks and overflow counts at fixed cameras;
- frame time and worst stalls, disk reads, cache misses and audio late updates;
- seam crossings in both directions, repeated turns and fast movement at the edge;
- stable object ownership, door return transforms and collision across boundaries;
- deterministic conversion, bounded index validation and missing-data behavior.

Compare equivalent scenes and camera routes. A broken renderer that drops faces
is not a valid faster baseline. Oversized render buffers can evict model caches;
measure their full effect, not just allocation success. Preserve earlier results
in OPTIMIZATION_HISTORY.md and distinguish local passes from owner confirmations
in PLAYTEST_STATUS.md. The current 040/FPU/JIT emulator remains a reference only;
stock A1200 and the preserved A500 experiment have separate budgets and evidence.

Storage profiles and conservative legacy image limits remain in STORAGE.md
and ROADMAP.md where applicable; validate the actual driver/filesystem path before
larger images. No raw asset archive design bypasses its device-offset limits.
