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
