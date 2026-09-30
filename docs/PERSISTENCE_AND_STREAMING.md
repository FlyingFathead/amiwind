# Proposed approach: persistent world state and disk loading

**Status, 30 September 2026:** bounded character/world state and save/load are
implemented; broader object persistence and background region streaming remain
planned. Balmora replaces one resident BSP synchronously among 64 overlapping
regions, carrying player state across the boundary. Method 1 does not prefetch. Experimental method 2 reads a bounded destination
prefix ahead of a crossing; neither keeps two complete regions resident.

Dev3 can hold the last rendered frame with a small top Loading box during these
swaps; Options retains the previous black-screen method. This masks the blank
transition, not the disk/decoding pause. Music servicing remains active.

Owner playtest: Balmora exteriors now look okay overall and often run faster than
Seyda Neen despite the city's size. Interiors remain a requested content priority.
This performance observation is not yet a controlled comparison.

Next investigation: measure disk reads, decoding, renderer/collision work, peak
RAM and audio deadlines separately. Trial smaller Seyda Neen sub-cells; preserve
opening routes, barriers, stable references and return spawns. Investigate bounded
prefetch and shared resource ownership only within a measured memory budget:
the current 11 MiB heap already approaches 10 MiB in a Strider region, so two full
BSPs are not an assumed solution. Save dirty authoritative state before offloading
runtime objects; release resources only when no active placement references them.

The remainder records the broader design direction. See [SAVEGAME_PLAN.md](SAVEGAME_PLAN.md)
for the save format and remaining persistence acceptance gates.

## Numbered transition investigation, 30 September 2026

Preserve the current synchronous transition implementation as method **1**.
Introduce a selector named `aw_cell_change_method` when an alternative is ready
to exercise. New incremental/prefetch experiments use **2**, then later numbers;
never overwrite method 1 or reuse a number for a different implementation.
Method 2 now exists as an opt-in bounded read-ahead experiment. It predicts an
adjacent regular region from current velocity, reads at most 8 KiB per frame
into an evictable 128, 256 or 512 KiB prefix cache, and reuses available bytes during the
ordinary BSP load. It does not incrementally build a second renderer/collision
world. Direction changes cancel speculation; insufficient headroom, eviction or
an incomplete prefix use the ordinary disk path. Method 1 remains the default after the comparison below. The Loading presentation is independent
of this implementation choice. Hide the box only when the transition actually
meets its frame/audio budget, not merely to conceal an unchanged stall.

Measure the same dense-city crossing in both directions with cold and warm
caches. Record disk read bytes/calls/time, BSP parse/plane/node/leaf and collision
setup time, texture/alias/sound loading and linking time, state restoration,
longest frame, total pause, steady frame rate, audio underruns and peak heap.
Retain captures, raw timings, target hardware and content hashes privately.

Try bounded per-frame work and early neighbour selection first. Cancel stale
prefetch after a direction change. Track ownership so speculative assets never
evict resources still used by the current frame. Bound scratch allocations and
reads within the measured headroom of the existing **11 MiB** heap; two resident
full BSPs are not presumed affordable. Resource pressure, late arrivals or an
unsupported case must fall back to method 1 with its honest Loading display.

Acceptance requires fewer disruptive pauses without slower city roaming,
missed audio deadlines, duplicated/lost NPCs, collision gaps or save regressions.
Repeat the [NPC ground-contact check](NPC_GROUND_CONTACT.md) after fresh loads,
sub-cell returns and restores for every tested method. Keep the experimental
method opt-in until the owner accepts those comparisons.

`cell-load-profile.tsv` records map, method, measured model/BSP disk bytes and
read calls, time inside those reads, BSP decode time, whole-world-model time,
entity/precache time, total server construction time, reused prefix bytes,
earlier prefetch read time, low hunk and high hunk bytes. These phase columns
overlap: do not add world time, its nested I/O/decode times and entity time as
independent totals. Sound/catalogue reads and filesystem open/seek overhead are
not all individually timed; total construction and entity/precache timing retain
that cost. Compare frame profiles separately, including the read-ahead frames.

## Controlled read-ahead comparison, 30 September 2026

Ten native FS-UAE runs repeated the same north/south Balmora crossing, with the
five configurations run in forward and reverse order. Conversion workers were
paused for this comparison. Each cell contains the two measured **complete
visible transition** times in milliseconds, from the change request through the
first presented frame after scene sign-on. Server construction alone is shorter
and must not be reported as the whole visible pause.

| Method | Buffer | Prediction | North, ms | South, ms |
| --- | --- | --- | --- | --- |
| 1 | unused | unused | 319.8, 325.3 | 380.3, 329.0 |
| 2 | 128 KiB | 1.5 s | 316.7, 321.8 | 364.8, 348.2 |
| 2 | 256 KiB | 1.5 s | 333.1, 325.7 | 383.7, 384.7 |
| 2 | 512 KiB | 1.5 s | 316.0, 319.9 | 325.5, 373.5 |
| 2 | 512 KiB | 4 s | 314.5, 296.3 | 354.3, 364.0 |

Method 2 is **not a demonstrated overall improvement**. A larger buffer did not
consistently shorten the pause. The 128 KiB setting reused about 128 KiB in both
directions. Larger settings reused about 248–344 KiB northbound, but no prefix
bytes survived to the southbound load, despite earlier reads. Cache pressure or
prediction cancellation can consume the benefit before the crossing. The 512
KiB / 4 s pair also had widely differing sampled roaming frame medians (72.3 and
41.9 ms), so its best northbound result is not a reliable seamless-loading claim.

All ten runs recorded zero surface/edge overflow frames and zero reported audio
late events after warm-up. These were Linux FS-UAE A1200/AGA/PAL, 68040/FPU/JIT,
2 MiB Chip + 16 MiB Z3, with the existing 11 MiB runtime heap, a host-directory
drive and null audio. Host filesystem caches were not forced cold. This is not a
physical-drive, Windows/WSL or subjective audio-quality measurement. There are
two samples per direction/configuration; retain the raw profiles privately.

Options exposes the loading method and read-ahead buffer. Method 1 is the RC2
default; the buffer is relevant to method 2 only. The persisted variables are
`aw_cell_change_method` and `aw_cell_prefetch_kib`. Prediction horizon remains an
experimental console setting, `aw_cell_prefetch_seconds` (0.5–4 s). Bigger is not
a performance recommendation. No option increases the total 11 MiB heap.

`cell-visible-profile.tsv` records the complete visible pause. The load profile
also includes requested cache capacity, filled bytes, worst individual 8 KiB
prefetch read and prediction horizon. Prefix fill is not the same as bytes reused
at load. Further work should separate cache loss from read latency and reduce
synchronous decode/setup work before increasing speculative allocations again.

## Separate base content from saved changes

Keep converted cell/scene data immutable on disk. A save records changes to
that base rather than another complete copy of every model, texture and object.
Loading a cell means loading its base data, then applying saved changes.

| State | Proposed lifetime and storage |
| --- | --- |
| Converted geometry, textures, collision and original placements | Immutable cell/resource packs, shared across saves. |
| Player position, inventory, statistics and progression | Save-wide state, independent of loaded cells. |
| Quest variables, global flags and world time | Save-wide state; retained when cells unload. |
| Door/hatch state, container contents, removed or moved objects | Changes keyed by persistent object identity. |
| NPC location, health, inventory and script state | Persistent actor state; separate from its currently rendered model. |
| Spawned or dropped objects | Saved creation records with unique persistent IDs. |
| Renderer caches, pointers, audio buffers and transient effects | Reconstructed at load; never serialized as raw memory. |

Use stable identities derived from original placed-reference identities and a
recorded source/content namespace. A mesh name identifies an asset, not a unique
placed object; a RAM address, array position or current XYZ is also unsuitable.
Moving an object must not change its identity. Dynamically created objects need
a separate persistent ID allocation scheme.

Absence from the change store means "use the base state". Explicit removal needs
a tombstone so a taken item does not reappear whenever its cell reloads. An
object moved between cells must have one authoritative state and appear once.

## Cell load and unload

1. Select the destination and establish its resource/memory requirements.
2. Save dirty state from the current cell before releasing its runtime objects.
3. Read the destination base pack, then apply that cell's saved changes and
   any relevant global/quest state.
4. Create runtime entities, resolve persistent IDs to live entities and find a
   valid arrival position. Restore player/global state independently.
5. Enter play only after the destination is usable. A failed load must leave a
   recoverable previous state rather than a partially committed transition.

Start with explicit loading at interior doors and exterior cell boundaries.
This provides a useful persistent world before seamless traversal. A transition
may need a loading screen; keeping two full scenes resident is not assumed.

Unloaded NPCs should initially retain compact state rather than fully simulate
every frame. Later, selected schedules or timed events can use elapsed world
time when a cell is activated. Quest-critical events must not silently depend
on whether their NPC happens to be rendered. Define this behavior before adding
background simulation.

## Memory and disk access

A larger HDF increases storage capacity. It does not increase Chip/Fast RAM,
reduce seek latency or guarantee that the final converted content will fit.
Measure packed content and the chosen disk/filesystem/emulator limits before
selecting a final image size.

Set explicit resident budgets for the engine, active scene, textures/models,
state records, loading scratch space and audio. Begin with one cell and a bounded
shared-resource cache. Add a neighboring cell only when measured headroom permits
it; use reference counts or equivalent ownership to release shared resources
without invalidating the active cell.

Organize packs so a cell can load its required resources with predictable reads.
Prefer independently loadable blocks over a format that must decompress the
whole world first. Compression, block sizes and cache policy need measurements
on the target; no particular codec is selected by this proposal.

The current music stream already has audio-deadline issues. Cell loading must
account for that: bounded work between frames, audio-buffer headroom and limited
read sizes are initial experiments. Small synchronous reads can still stall;
they are not asynchronous streaming. Investigate prefetch and asynchronous I/O
only after measuring the current path and defining safe cancellation/failure
behavior.

## Save format and recovery

Use a versioned format with a content-set fingerprint, schema version, player
and global state, and cell/object change records. Record the build that wrote
the save, but do not assume that identical build numbers establish data
compatibility. Validate references, sizes and checksums before loading.

Write a new save generation, validate it, then commit it while retaining the
previous known-good generation. Do not assume a filesystem rename alone makes
a save power-loss safe. Confirm the write/flush/commit behavior on the selected
Amiga filesystem; a two-generation scheme with explicit validity information
is a candidate. Avoid unbounded append-only journals unless compaction and
recovery are designed alongside them.

Conversion changes can alter object identities or geometry. Define compatible
content versions and explicit migrations; refuse unsupported combinations with
an explanation rather than applying old records to unrelated objects.

## Proposed implementation stages

1. Stable reference IDs and a small state layer in the existing two-scene demo.
2. Door/container/item persistence across unload/reload within one session.
3. Player/global/cell state serialization, integrity checks and interrupted-save
   recovery, with previous saves preserved.
4. More converted cells loaded at explicit transitions under a measured memory
   budget; test repeated travel for leaks and duplicate/missing objects.
5. Bounded neighboring-cell prefetch and resource caching, then evaluate whether
   seamless exterior traversal is practical on the selected hardware.

Acceptance cases should include an opened door staying open, a taken item staying
removed, an object moved across a boundary appearing exactly once, quest state
surviving unloaded NPCs, and recovery from a failed load or interrupted save.
Test the same world state before and after a save/reload, not just whether a
file can be written and read.

This is a proposed architecture for AmiWind. It does not claim full Morrowind
script compatibility, completed persistence, or seamless world streaming.


## Owner acceptance: 30 September 2026

Balmora's v0.0.24-dev3 regions and sub-cells work surprisingly well in the
owner's playtest. The accepted frozen-frame Loading... presentation is the
current standard. This is a promising foundation for continuous travel across
a larger game world without disruptive scene breaks. Preserve this result
while extending coverage. Current loading is still synchronous and only one
BSP is resident; asynchronous streaming remains future work.


## Seyda Neen regions in dev4

`seyda-regions.txt` extends the same shared-coordinate runtime to 30 regular
regions, plus special `intro_docks.bsp` and `sncourt.bsp` areas. The first exterior
entry pins the arrival pier during the ship/dock/office stages. Court selection
uses its enclosed rotated footprint, including the ring barrel and door arrivals.
Regular core size is 768 (outer partial cores are merged), overlap 896, hysteresis 96.
Effective exterior viewing distance is capped at 540; player geometry is unchanged.

The compactor keeps selected models whole, remaps referenced BSP structures and
textures, and removes unmarked world faces. Inner source terrain collision and PVS
are retained; coverage planes bound the region. Actor reference identities and
restored positions use the same persistence path. Loading still replaces one BSP
synchronously with the accepted frozen view/top box or optional black screen.

The new files and nineteen collision-corrected Balmora regions change the save
content fingerprint. Start a new game or Demo Game; dev3 saves are incompatible.

## dev5 Seyda centre boundary

The regular grid now has 25 regions. The town-centre core spans X=-768..1024 and
Y=-768..474; the northern edge follows the reported bridge. Existing 96-unit
hysteresis means northbound switching occurs past Y=570. Positions in the centre
remain together. Intro pier and ring courtyard overrides retain their own rules.
The final HDF crosses sn012/sn017 and back with both frozen-frame and black
loading; no background or concurrent world loading is introduced.
