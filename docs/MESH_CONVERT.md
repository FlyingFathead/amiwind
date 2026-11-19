# Converting models: game, AmiWind and OBJ+MTL, in any unit

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

`tools/mesh_convert.py` turns a model into OBJ+MTL and back, in Morrowind units, Quake (AmiWind) units or any scale,
so a model can go to a 3D program or another tool and come back without anyone multiplying positions by hand. It
reads the game's models through the builder's own reader, and the builder's converted maps and actor models; it
writes OBJ+MTL (with the textures as PNG pictures if asked) or the builder's own mesh form.

The two units are explained in [units](UNITS.md): 4 Morrowind units are 1 Quake unit. The model census
([MODEL_CENSUS.md](MODEL_CENSUS.md)) says what the builder makes of every model; Mesh Compare in the Toolkit shows two
OBJ files side by side.

## What goes in and what comes out

| In | Read as |
| --- | --- |
| `meshes/l/light_com_lantern_02.nif` | a model of your own game files, by its path (loose or in an archive; `--data-files`) |
| `light_com_lantern_02` | a record id: its model, looked up in the game's masters (the latest master wins; `--data-files`) |
| `FILE.nif` | a NIF file on disk |
| `FILE.obj` | an OBJ and the MTL beside it that its `mtllib` line names |
| `FILE.bsp`, `FILE.chim` | a map as the build wrote it: the faces of one model (`--model N`, default 0). A CHIM map holds collision-only models; its drawn geometry is in the CHIM world. |
| `FILE.mdl` | an actor or item model as the build wrote it (a Quake alias model): one frame (`--frame N`, default 0) |
| `FILE.mwg` | the builder's mesh form, as this tool writes it |

| Out | Written |
| --- | --- |
| `FILE.obj` | OBJ + `FILE.mtl` beside it; with `--textures`, the textures as PNG beside them, read from your game files and named by the texture's own name (`tx_wood_brown_posts_02.png`), so a model made from it and brought back still names the game's texture |
| `FILE.mwg` | the builder's mesh form: the geometry packet the builder's scenery export stores for every model (Morrowind units), and `FILE.mesh.json` beside it with the materials and their textures, the units, the counts and the packet's SHA-256 |

A NIF is never written: nothing in the build reads one back. A hand-made model comes back to the builder as its mesh
form; a recipe row then names it, so the build converts it like any model (the row kind for a hand-made model file is
its own work item).

## Units

| Option | Meaning |
| --- | --- |
| `--units morrowind` / `--units quake` | the output's units (default: Morrowind units) |
| `--scale N` | the output in units of N per Morrowind unit (`--scale 0.25` is Quake units) |
| `--in-units` / `--in-scale` | an OBJ's units, only when the file does not say them itself |

Every OBJ this tool writes names its units in a header line, which the tool reads back:

```
# amiwind-mesh: format=1 units=quake scale=0.25 up=z v=up winding=ccw
```

An OBJ without that line (one made by hand or by another program) is refused until you say its units with
`--in-units` or `--in-scale`; a NIF, a map, an alias model and the mesh form have fixed units and refuse a different
one. The builder's mesh form is always Morrowind units.

The other conventions are the same in both directions:

- **Z up**, as in the game and in AmiWind: no axis is swapped. Import an OBJ into a 3D program with Z up.
- **Texture V counted from the bottom** in the OBJ (the OBJ convention); the game's files count it from the top, so
  the tool writes `1 - v` and reads it back the same way.
- **Faces counter-clockwise seen from their front** in the OBJ, the NIF and the mesh form. The engine's map and alias
  faces are clockwise; the tool turns them on the way in.

Converting a model to OBJ and back to the mesh form keeps every position within 1e-5 in either unit (a test checks
this on a synthetic model).

## Examples

Game model to OBJ+MTL in Quake units, with its textures:

```
python3 tools/mesh_convert.py light_com_lantern_02 lantern.obj --data-files "/path/to/Data Files" --units quake --textures
```

A hand-made OBJ in Quake units back to the builder's mesh form:

```
python3 tools/mesh_convert.py lantern-lowpoly.obj lantern-lowpoly.mwg --in-units quake
```

A room's converted model, as the build wrote it, to OBJ in Morrowind units:

```
python3 tools/mesh_convert.py build/maps/room.bsp room.obj --model 0
```

An actor model of a build to OBJ, its first frame:

```
python3 tools/mesh_convert.py build/progs/npc.mdl npc.obj --units quake
```

## Keep it private

A model or a picture converted from your game files holds the game's geometry or artwork. The tool marks such an
output private: the OBJ's header says so, the mesh form's record says `"private": true`, and `--textures` writes a
`FILE.PRIVATE.txt` note beside the pictures. Keep these files to yourself; share only your own work.

## For the Toolkit's Mesh Compare

`tools/mesh_export.py` fills the Toolkit's Mesh Compare list: one model through each of the builder's mesh methods
(the original, the converter's faces, planar merge, meshoptimizer), in Quake units. The original keeps its texture
coordinates and its MTL names each texture. Compare files of the same units; each file's header line names them.
