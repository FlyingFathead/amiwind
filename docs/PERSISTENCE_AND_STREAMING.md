# Proposed approach: persistent world state and disk loading

**Status: design proposal, not implemented.** v0.0.16 loads one prepared scene
at a time and has no working save/load system. This proposal records a direction
for extending that model without requiring the whole world to fit in RAM.

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
