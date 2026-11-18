# Units: Morrowind units and AmiWind units

_Last updated with AmiWind v0.0.67 (17 November 2026)._

AmiWind works in two units of length. Mixing them up makes a model four times too large or four times too small, so
every tool and file that handles positions should say which one it uses.

## The rule

The builder multiplies every position it converts by **0.25**: **4 Morrowind units are 1 AmiWind unit.**

- **Morrowind units** are the original game's: every model (`.nif`), every placement and every exterior cell in the
  game's data files is in these units.
- **AmiWind units** are the engine's. AmiWind runs on a Quake-derived engine, so "Quake units" in the code and the
  docs means the same thing.

The constant is set once, `SCALE=.25` in `tools/prepare_quake.py`, and the rest of the builder uses the same value
(`tools/chimport.py` and most of `tools/chim/`, each with a comment pointing back to it).

## What it looks like in practice

| What | Morrowind units | AmiWind units |
| --- | ---: | ---: |
| One exterior cell, side | 8192 | 2048 |
| The player's collision box | 58.56 x 56.96 x 133 | 14.64 x 14.24 x 33.25 |
| Step-up height | 34 | 8.5 |
| Walk, run and swim speeds | the original's, per second | a quarter of those, per second |

Sources: [player movement](PLAYER_MOVEMENT.md) (the box, the step height and the speed rules) and
[physics](PHYSICS.md).

What the scale changes and what it does not:

- Lengths, speeds and accelerations are multiplied by 0.25; areas by 1/16; volumes by 1/64.
- Angles are unchanged: the walkable slope (0.69, about 46 degrees) is the original's.
- Face and triangle counts, texture sizes and times are unchanged. A model's polygon budget is the same in either
  unit.
- Axes: both are Z up, so no axis swap is needed between them.

For comparison, the stock Quake player box is 32 x 32 x 56 units. An AmiWind person, about 33 units tall, is smaller
in engine units than a Quake player, which is why the engine's own movement constants had to be matched to Morrowind
rather than kept.

## Where it matters

### Exporting and re-importing a model

`tools/mesh_export.py` writes OBJ files in **AmiWind units**; its header line says so ("Quake units"). The builder
reads models from the game's files in **Morrowind units** and scales them itself on the way in. A model exported,
edited in a 3D program and handed back to the builder as a replacement must therefore be multiplied by **4** first,
or it comes out a quarter of its size.

When importing an exported OBJ into a 3D program, choose Z up: many programs assume Y up for OBJ files and would lay
the model on its side.

Planned: the converter gets `--units morrowind|quake` (or `--scale N`) for its input and its output separately, and
every file it writes names its unit in the header, so nobody has to multiply by hand. The same release handles the
texture coordinates the same way in both directions (OBJ counts V from the bottom, the game's files from the top).

### Gravity

The engine keeps Quake's gravity of 800 units per second squared, which was tuned for Quake's 56-unit player. In a
world scaled to a quarter it pulls much harder than the original: jumps and falls take about a third of the original
time. This is a known, open bug: [PHYSICS-GRAVITY-SCALE-36](bugs/PHYSICS-GRAVITY-SCALE-36.md).

### Numbers in the docs and the build tables

Distances in the build tables, the console (`dbg pos`, `dbg tp`) and the engine's own logs are AmiWind units. Values
quoted from the game's records, OpenMW or the construction set are Morrowind units. A doc that quotes both says which
is which, as the table above does.
