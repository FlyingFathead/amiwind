# The .chim map format (planned: its own format)

Status: approved 10 October 2026; planned for after v0.0.36-dev3. Nothing below is implemented yet except
the `.chim` file name itself.

## Why

**We use `.chim` as the file format for CHIM maps to avoid confusion: a CHIM map is no longer directly
compatible with Quake's `.bsp` format.** A Quake engine cannot play one: its geometry lives in the CHIM world
and its entities need CHIM. From the own-format step on, its bytes leave BSP29 as well. A `.bsp` in AmiWind is
always a regular Quake map.

A CHIM map is not a Quake map. Since v0.0.36-dev the builder writes CHIM maps as `.chim` files
(`maps/<town>-chim.chim`, `maps/vfNNNN.chim` for a cell on CHIM inside the legacy open world), and `.bsp`
means a regular Quake BSP29 map only (the legacy open world and the interiors). The name keeps the two
apart, so it is always clear what is plain Quake and what is CHIM.

Inside, today's `.chim` is still laid out like a BSP29 file and says "version 29". It is an empty shell:
an entity list (characters, doors, the `_chim_frame` link to its CHIM frame) and a one-leaf world with no
faces; all geometry lives in the CHIM world files ([world format](WORLD_FORMAT.md)). Only the file name
and one entity key mark it as CHIM, and a Quake loader would accept it.

The rest of CHIM already goes well past a Quake map. The CHIM world is its own container (an index, frame
and sector files, texture, model and chunk records, terrain references, texture effects, the walkable graph for
characters), with every asset stored once and placed by reference, streamed as the player moves. It already
gets around BSP29's per-map limits by structure: no single map holds an area; each model and terrain chunk is a
small brush image kept under the limits, placements are linked to the leaves they touch, and statics are
streamed beyond the engine's static-entity limit. Inside, each brush image still uses BSP29 lumps so that
Quake's own decoders draw and collide with it ("Quake first"). The `.chim` map file is the last piece that
still presents itself as a Quake map; this plan brings it in line with the rest.

## The plan

1. **Its own header and its own loader.** A `.chim` starts with a CHIM magic, the CHIM map version and
   the world format it belongs to, instead of the BSP29 version. The engine loads it through a CHIM map
   loader (it may share the lump-reading code inside); the Quake map loader refuses a `.chim` and the
   CHIM loader refuses a `.bsp`. The builder, the tools and the Toolkit recognise it by its header, not
   by its extension. This changes the world format, so it is a CHIM major-version step (the engine refuses
   a world of another major with a clear message).
2. **Then its contents move away from BSP29, one measured step at a time:**
   - entities as a compact binary table instead of text (Balmora's entity text is 10.5 KB, parsed by
     Quake's text parser, and its strings stay in memory);
   - no dummy BSP parts (the empty world, planes, nodes and leaves that exist only to satisfy BSP29);
   - no BSP29 limits where CHIM needs more (16 leaves per entity, 16-bit indices, the marksurface and
     texinfo limits);
   - precomputed tables (links, lighting references) that the engine looks up instead of working out at
     load time.
3. **Interiors stay Quake `.bsp` maps** until they move to CHIM too.

Every step is measured against the step before it: bytes on disk, load time and the memory that stays
resident (the [resident memory budget](../MEMORY_ALLOCATION.md) applies).

## Speed

The loader itself buys little speed: today's `.chim` is 10 to 57 KB, read once when the player enters a
frame. CHIM's speed comes from its data layout, measured in v0.0.33 at the same Balmora cameras
(emulator numbers, relative): 86.7 to 19.5 ms frame time with the JIT, 4,135 to 1,614 ms on a
cycle-exact slow 68040, 654 to 114 brush models sent to the renderer, 51.8 to 9.9 BSP nodes walked per
clipped face. The format step's own gains are honesty, freedom from BSP29, faster entity loading and less
resident memory.

## First step

A short design note with the measured costs of today's shell (load time, entity parsing, resident memory),
then the owner's decision on the header and loader before any code changes.
