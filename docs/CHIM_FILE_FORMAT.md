# CHIM file format

_Last updated with AmiWind v0.0.45 (19 October 2026)._

**We use `.chim` as the format for CHIM maps to avoid confusion: the format is no longer directly
compatible with the Quake `.bsp` format.**

An overview of how AmiWind stores its world on CHIM, for someone meeting it for the first
time: what the files are, why they look the way they do, how the format has grown, how to
look inside, and where it is going. The byte-by-byte specification is
[CHIM world format](chim/WORLD_FORMAT.md); this page does not repeat it.

## What CHIM is, and why

CHIM ("[C]hunks and [H]eaps [I]n [M]emory") is AmiWind's world streamer on top of the
AmiQuake engine it has always used ([CHIM](chim/README.md)). The legacy open world was cut
into overlapping Quake maps, and every map held its own copy of every object it could see:
each exterior object was stored about ten times, the island would need about 20 GB of maps,
and Quake's visibility did little outdoors. CHIM follows four rules instead:

- **Stored once.** Every model, texture and piece of ground is stored once; a placement is a
  small record that names its model, as Morrowind's own data does.
- **Streamed.** The land is cut into frames of 3 x 3 cells, frames into chunks of 256 units,
  chunks into sectors of 3 x 3 chunks. A ring of chunks around the player is in memory, and a
  sector is one small file that a classic Amiga disk reads whole.
- **No duplication on disk or in memory.** A model that ten chunks place is loaded once.
- **Quake first.** Ground and models are still Quake brush data (BSP29 lumps), so the engine's
  own loaders, renderer and collision draw and touch them; CHIM adds only the directories and
  placement records around them.

## The files

| File | Name | What it is |
| --- | --- | --- |
| Quake map | `maps/<name>.bsp` | A regular Quake BSP29 map: the legacy open world and every interior (an interior cut into sub-cell sections is one map per section, joined by `interior-sections.txt`). |
| CHIM map | `maps/<name>.chim` | The CHIM version of the Quake map format, the modified BSP format: one per CHIM area or cell on CHIM. It holds the area's entities (characters, doors, the start) and the `"_chim_frame"` link to its frame; no ground or objects. Today it is laid out like a BSP29 file but is not a playable Quake map; it is becoming a format of its own (roadmap below). |
| CHIM world | `chim/world.cwi`, `chim/frames/.../frame.ccf`, `chim/frames/.../sNN.ccs` | CHIM's own binary format: the index (every file, model and texture), one frame file per frame, and the sector files that hold the chunk records, the placement records, the ground (stored once per content with terrain references), the shared models and the textures. |
| Far terrain | `maps/<name>.far` | The land outline beyond the chunk ring, drawn in the fog. |
| Texture effects | `.chimfx` | Optional text files the builder applies to chosen textures. |
| Reports | `chim-heap.json`, `chim-receipt.json`, ... | What the builder measured and checked, such as the memory every player position needs. |

The full table, with every record kind and where each file is specified:
[file types](chim/WORLD_FORMAT.md#file-types). The tools tell a CHIM map by its
`"_chim_frame"` key, not by its name, so a `.chim` is never mistaken for a Quake map.

## Versions so far

CHIM has its own version, separate from AmiWind's: CHIM 0.1.0 shipped with AmiWind v0.0.33 and
CHIM 0.2.0 with AmiWind v0.0.36; CHIM 0.2.1 (a patch step, the world format unchanged) with v0.0.41 and still
current in v0.0.44 (the `CHIM_VERSION` file; [versions](chim/README.md#versions)). CHIM 1.0 is the
release in which the whole island runs on CHIM. The world files carry a format version of their
own, in every file header; each step below was measured before it was kept
([version rules](chim/WORLD_FORMAT.md#version-rules)).

| World format | What it brought |
| --- | --- |
| 0.1 | The first frames: one model pack, one texture pack and one chunk pack per frame. |
| 0.2 | Sector files: 3 x 3 chunks per small file, read whole, in the order a walk meets them. |
| 0.3 | Placement lists: each chunk knows which placements a view from it may see. |
| 0.4 | Seamless ground: each chunk's standing hull also holds its neighbours' ground at the border. |
| 0.5 | Seyda Neen: irregular ground and placements hidden by the opening story. |
| 0.6 | Large frames: one folder per sector row, for a frame of more than 64 sectors such as all of Vivec (designed; the engine reads it, the builder does not write it yet). |
| 0.7 | Terrain references: identical ground stored once and placed where it repeats (the default since v0.0.36: `--chim-terrain-refs on`). |

The engine reads 0.4 to 0.7 and refuses anything else with a message naming both versions.

## What it has measured

Counts are the main currency; frame times are emulator numbers, relative until a hardware
number exists. From the v0.0.33 release, legacy against CHIM on the same Balmora cameras
([release notes](releases/notes/RELEASE-v0.0.33.md#measured-gains),
[measurements](performance/CHIM-v0.0.33-MEASUREMENTS.json)):

- Balmora's exterior: 162.1 MB of legacy region maps to 21.3 MB of CHIM world; Seyda Neen with
  the intro docks and the courtyard: 190.4 MB to 7.8 MB.
- Frame time 86.7 to 19.5 ms with the JIT, 4,135 to 1,614 ms on a cycle-exact slow 68040;
  brush models sent to the renderer 654 to 114; BSP nodes walked per clipped face 51.8 to 9.9.
- A walk through all 70 load doors reads 40.7 MB instead of 73.5 MB, in small steps instead
  of region stops.

Every CHIM feature with its measured gain: [CHIM features](chim/FEATURES.md); the disk budget
of the whole game: [disk space](chim/DISK_SPACE.md).

## How to look inside

The AmiWind Toolkit's 3D Map Inspector opens all three kinds of map file in the browser,
locally, with nothing uploaded ([3D Map Inspector](POLYCOUNT_INSPECTOR.md#chim-maps-and-chim-worlds)):

- a `.bsp`, with its polygons;
- a `.chim`, with its entities as markers and the CHIM frame it names;
- a CHIM world (the build's `chim-world` folder, or a zip of it): the ground and every
  placement of a frame, with the bytes of each chunk and model, and the memory overlay of the
  build's heap report: the memory the active ring needs at every player position, against
  the CHIM zone, with the worst positions marked.

## Roadmap

- **`.chim` becomes its own format** (approved 10 October 2026): a CHIM header and its own
  loader first, then the contents move away from BSP29 step by step, each step measured
  ([.chim map format](chim/CHIM_MAP_FORMAT.md)).
- **The whole island on CHIM** (CHIMport): every exterior cell converted from the sea and the
  coast inwards, each through every audit, shown on the CHIM Progress Tracker
  ([CHIMport](chim/CHIMPORT.md)).
- **More in the world files:** the walkable graph for characters
  ([CHIM NPC pathfinding](chim/CHIM_NPC_PATHFINDING.md)) and placements that carry their whole
  rotation ([planned](chim/WORLD_FORMAT.md#planned-tilt-per-placement-next-release-chim-tilt-variants-split-33)).
- **One partition:** with the whole island on CHIM, the whole game on one disk image, the
  world in a single partition ([roadmap horizon](ROADMAP.md#roadmap-horizon-one-partition-with-chim)).
- **CHIM 1.0:** the release in which the whole island runs on CHIM.
