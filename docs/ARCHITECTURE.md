# Architecture

Core world/cell/chunk design: [WORLD_MAPPING_PLAN.md](WORLD_MAPPING_PLAN.md).

The host reads the owner's game data, converts a selected region, and writes a
small target data representation outside the repository. A separate native
Amiga runtime is intended to consume that representation.

| Component | Implemented now | Future work |
| --- | --- | --- |
| Setup | External game path, guided Linux build, source/private separation | Broader installation tooling |
| Content loader | Base TES3/BSA reader, ordered voice index, NPC/outfit inspection | Plugin merges, complete conditions/scripts |
| Terrain/scenery | Bounded AGA BSP terrain, shared building meshes, sprite foliage and fog culling | Complete vicinity, LOD, chunk seams and runtime streaming |
| Actors/body | Three dressed idle NPCs, facing/Hello; Nord hand animations | Full registry, wandering, dialogue, equipment and combat |
| Audio | Full-song streaming, shuffle/history, limited voices | Better worst-frame deadline servicing and effects arbitration |
| Runtime | Preserved 68000 experiment; current 040/FPU AGA scene and debug tools | Proven lower-spec performance |
| Streaming | Terrain packets/host indices; native music streaming | Native world residency, prefetch and eviction |
| Interaction | Menu, noclip/recall, nearby Hello audition | Linked interiors, quests, saves and complete gameplay |

The initial Python converter uses format facts from OpenMW sources. It does not
run or link OpenMW. The intended character baker uses OpenMW's actual actor
assembly, animation and rendering on the PC; that integration is future work.
See `OPENMW_BAKER.md`. Hunter's patch is a reference for optimization experiments.

## Memory and streaming

Keep CPU-side geometry/cache data separate from Chip RAM buffers used by display,
blitter and Paula DMA. The A500 planning profile assumes 512 KiB Chip plus
512 KiB expansion RAM until the actual machine's layout is confirmed.

Load terrain and collision before decorations. Keep surrounding chunks for
sudden turns and add priority in the movement direction. Use different load and
eviction distances. Preserve modified world state independently of cache eviction.
Coalesce tiny packets into larger disk requests.

A fully opaque fog band can mask the draw cutoff. Set the preload distance from
travel speed and measured worst-case I/O/conversion latency plus a margin.
The visible screen horizon alone is insufficient on hills or when looking down.
Audio refill deadlines take priority over decorative world reads.

The 36 KiB initial terrain experiment still describes 18,432 triangles. Compact
storage is not proof of fast rendering; culling and coarser distant terrain are
necessary experiments. No frame-rate target is claimed as achieved.
