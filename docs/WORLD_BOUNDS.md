# World bounds: the sea current at the edge of the world

An AmiWind extension: in the original game the open sea goes on past the island. AmiWind's open world ends a
little past its outermost cells (896 units, the overlap of the open-world maps), and until v0.0.36 an
invisible wall stopped you there.

## What it does

With world bounds on (the default), the water near the edge of the world carries a current along the edge,
as the sea at the map edge of some open-world games does: swim out and you are turned aside and carried
along the coast, anticlockwise round the island, and slowly back in. Swimming against it gets you no further
out; stop swimming and it brings you back. Out of the water (walking on the seabed, jumping off a ledge,
flying) there is no current, but outward motion fades to nothing before the wall and a gentle push leads
back in. The push always points into the world, so it never holds you anywhere. Debug flight (`noclip`)
is never pushed.

## Settings

| Where | Setting |
| --- | --- |
| Builder | `--world-bounds on` (default) or `--world-bounds off` |
| Game | the setting `aw_world_bounds` (1 on, 0 off), written by the builder into the game's default settings |
| Console | `dbg worldbounds on` / `off` (also `true`/`false`, `1`/`0`); no argument shows the state, the world's box and how far you are from its edge. Not saved: the next start uses the build's setting. |

`--world-bounds off` writes nothing: the game's settings and the image step are the same as a build made
before world bounds existed, and the game behaves as before (the wall).

## Where the edge is: the cell table

The cells of the open world come from a lookup table, never a guess: the open-world directory of the image
(`world/regions.awr`), the same table the game uses to hand you from map to map. A cell belongs to the world
when an open-world map's core lies in it (a cell split into several maps counts once). The game builds its
bit table of cells from that directory when it first needs it; `tools/world_bounds.py report` reads the same
table (or a CHIM Progress Tracker file) and prints the box, the edge ring by cell kind and each edge cell's
drift:

```text
python tools/world_bounds.py report --regions <image>/id1/world/regions.awr [--json report.json]
python tools/world_bounds.py report --progress cell-progress.json [--json report.json]
```

Measured on the v0.0.36 development builds (both tables agree cell for cell):

| | |
| --- | --- |
| Cells in the open world | 1,404 (1,292 with land data, 112 open sea) |
| Box | cells -18,-19 to 23,27 (42 x 47 cells) |
| Edge ring | 176 cells: 83 open sea (no land data), 67 seabed (land data, nothing placed), 26 land; 141 with an open side (48 east, 48 west, 44 north, 44 south; a cell can have more than one), 35 open only at a corner |
| Pockets inside the box that no map covers | none |

When more cells join the open world (such as the shared ocean chunk of [CHIMport](chim/CHIMPORT.md#open-sea-one-shared-ocean-chunk)
once the game places it), the edge moves out with the directory; nothing else changes.

## How it works

Quake's own mechanism for "the sea drags you" is water currents: leaf contents `CONTENTS_CURRENT_0` to
`CONTENTS_CURRENT_DOWN` that push a swimmer at 150 units a second, scaled by depth (`SV_CheckWater` in
`sv_phys.c`), added to the velocity for the move and taken off after it (`basevelocity`). They are not used
as such here, because:

- the push code is compiled only for Quake 2 (`#ifdef QUAKE2`), and its `basevelocity` field belongs to the
  Quake 2 game code;
- the map compiler we use does not write current contents (a Quake 1 map has water, slime and lava only);
- currents are baked into each map, so every outer open-world map would need its own copy and its own
  rebuild, and they act only in water.

So the same push is applied by position: in the server's player physics (`SV_Physics_Client`, walking and
flying), the game looks up the player's cell in the bit table and, near an open side, works out how far past
the edge the player is and which way is out (`aw_bounds_rules.c`, the same rule as `tools/world_bounds.py`):

| Distance past the edge | Effect |
| --- | --- |
| more than 128 inside the last cell | nothing |
| from 128 inside to 640 past | ramps up: outward motion fades, the push back in grows to 48 units/s, the current along the edge to Quake's 150 units/s in deep water (by depth, as Quake's currents) |
| past 640 | outward motion gone; full push and current |
| past 768 | the push back in is four times as strong (the wall is at 880 for the player's box) |
| no world cell next to the player (a teleport, debug flight) | straight back towards the middle of the world |

The current runs along the edge, turned a quarter left from "out" (east edge: north; north edge: west), so
round a corner it follows the coast. The drift is added for the move and taken off after it, like Quake's
`basevelocity`; only the fading of outward motion is kept.

## Cost

- No new data file: the table comes from the open-world directory the game already reads.
- Memory: a 2 KB bit table (room for 128 x 128 cells; the island uses 44 x 49) and a few numbers; while the
  table is built, once, 8 bytes per open-world map (20 KB for 2,532 maps), freed at once.
- Per frame, for the player only: off, one test of the setting; on, the player's cell from the directory
  (the same lookup the map hand-over uses) and one bit test; near the edge up to eight bit tests and eight
  distances.
- In the image: three lines in the game's default settings (`default-game.cfg`).

## Tests

`tests/test_world_bounds.py`: the edge ring, open sides and drift directions of a test island, the cells of a
directory, the public reference tracker (1,292 land cells, box -18,-16 to 23,27), the field and the push,
"never trapped" (from every point of the band the push alone leads back in), the builder default (on) and
`off` writing nothing, and the engine's rules compiled natively against the reference at 2,738 points
(`tests/aga_bounds_test.c`).
