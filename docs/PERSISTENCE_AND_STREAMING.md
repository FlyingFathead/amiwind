# Proposed approach: persistent world state and disk loading

**Status, 30 September 2026:** bounded character/world state and save/load are
implemented; broader object persistence and background region streaming remain
planned. Balmora replaces one resident BSP synchronously among 64 overlapping
regions, carrying player state across the boundary. It does not keep two complete
regions resident or prefetch the destination in the background.

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
