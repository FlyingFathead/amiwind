# The model census: every model, its original triangles and what the builder makes of it

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

`tools/model_census.py` lists every model the game files place, with its original triangle count and what each of
AmiWind's mesh methods makes of it outdoors (the CHIM frames) and in the rooms, whether that method keeps the model
intact, and which method the builder uses today. Every build writes it, so the numbers in a discussion about a heavy
model are always the current build's, never an old estimate.

Mesh work starts and ends with this table: look a model up before reducing it, adding a recipe row or changing its
method, and read its row again afterwards. The methods themselves are described in
[CHIM mesh methods](chim/MESH_METHODS.md); how an actor model is reduced and checked is in
[model reduction](MODEL_REDUCTION.md).

## How to run it

The census reads your own game files and writes three files into the output folder:

```
python3 tools/model_census.py run --data-files "/path/to/Morrowind/Data Files" --out census
python3 tools/model_census.py check census/model-census.json
python3 tools/model_census.py diff previous/model-census.json census/model-census.json
```

| Option | What it does |
| --- | --- |
| `--jobs N` | worker processes (default: the build's allowance or every usable core) |
| `--no-quality` | faces and triangles only, without the seam and shape measures (much faster) |
| `--models a,b` / `--limit N` | only the named models, or the first N by path |
| `--cache DIR` | reuse each model's result while its NIF file, the census code and the method tables are unchanged |
| `--build-name`, `--build-commit` | the build the census belongs to, written into the record |

The output is made from your own game files. It holds names, counts and paths, never geometry or texture data, but
keep it private anyway; publish only counts and model names.

`check` exits 1 when the record breaks its schema (below); `diff` exits 1 when a model draws more triangles than in
the previous record or a model became heavier than its original.

## Every build writes it

After a passed image build, the builder runs the census as a measurement (`tools/build.py`, after the container
count). It writes `model-census/` into the run folder (`model-census.json`, `model-census.csv`, `MODEL_CENSUS.md`)
and its summary lines into the build log. It never fails a build: a census that cannot be made is reported in the
log and the build goes on. It is not a stage, so it changes no stage key.

Each model's result is kept in the workspace's cache (`cache/model-census-v1`), keyed by the SHA-256 of its NIF file,
of the census code and of the method tables, so a build only measures the models whose inputs changed. The first
build that runs it measures every model, which takes minutes, not seconds.

MiniWind builds skip it; `AMIWIND_MODEL_CENSUS=on` runs it there too, and `AMIWIND_MODEL_CENSUS=off` skips it in any
build.

## What it measures, and through which code

Everything goes through the builder's own code, never a second implementation:

- **The original:** the triangles the converter reads from the NIF file (the same reader the build uses).
- **The profile each space starts from:** outdoors, the CHIM frames' profile (or a named scenery group's own profile,
  such as the arrival ship's); in the rooms, the room converter's profile. Flattened window panels are included.
- **The methods**, one column each:

| Column | What it is |
| --- | --- |
| `current` | the converter's own faces after the profile's reduction |
| `merge` | the same reduction, then planar merge (the smaller face list) |
| `meshopt+merge` | meshoptimizer with locked borders in place of the reducer, then planar merge; only where the profile reduces the model |
| `row` | the everywhere recipe's row for the model (`config/visual-recipes.json`), when its SHA-256 matches |
| `method 2` | the hand-made mesh (`config/model-method-2.json`), when its row matches the NIF's SHA-256: the counts recorded in the row |

- **The method in use:** outdoors, the method table (`config/mesh-methods.json`); in the rooms, the room converter's
  faces; then the everywhere row where one matches (outdoors, and in the rooms while `everywhere_in_rooms` is on);
  then method 2 where its row matches and the build uses method 2. The switches `AMIWIND_VISUAL_EVERYWHERE` and
  `AMIWIND_MODEL_METHOD` are read as a build reads them.

Not in the per-model table: an area's own recipe (Mournhold, Solstheim, the Telvanni towns), an area's or a room's
detail budget, and a room's own planar-merge list. They change a model in that place only.

## How to read a row

Each model has one row in the JSON and one line per space in the CSV:

| Field | Meaning |
| --- | --- |
| `model` | the NIF path, e.g. `meshes/l/light_com_lantern_02.nif` |
| `records` | the records that use it: id, type and in-game name |
| `file`, `nif_bytes`, `nif_sha256` | the archive it ships in (or "loose only"; "loose copy differs" when a loose file replaces the archive's), its size and its SHA-256 |
| `placements`, `placed` | placements per land and space (Vvardenfell, Mournhold, Solstheim; outdoors, rooms), and per space |
| `original` | its triangles, its size in Morrowind units and the texture repeats (below) |
| `spaces` | for each space it is placed in: `profile` (ratio, texture size, a scenery group), `columns`, `in_use`, `default`, `today`, the flags |

Every column holds `faces` (the convex faces the engine draws) and `triangles` (a face of k corners counts k - 2),
and the quality of its drawn mesh against the original:

| Quality | Must be | Meaning |
| --- | --- | --- |
| `new_open` | 0 | open edges the method adds: a crack |
| `lost_open` | 0 | open edges of the original that are gone or moved: a gap to the part or model that meets there |
| `seam_torn`, `rim_torn` | 0 | the share of seam and free-rim length pulled away from where the original has it (the seam audit) |
| `shape_error` | small | the Hausdorff distance between the two surfaces, sampled both ways, as a share of the model's bounding-box diagonal |

A method that cuts faces but adds an open edge or tears a seam is a failure, whatever it saves. A replacement (a
primitive, a panel, a hand-made mesh) is another shape: its edges are compared with the original's too, and the
summary lists it after the reductions.

A model with nothing static to count is a special case, marked by kind: an editor marker, a particle effect, an
animated or skinned model (counted by the creature and NPC tools), a model with no triangles, a missing or an
unreadable file.

## The catchers

- **Heavier than the original.** A converted model (any method, any space) that draws more triangles than its
  original is a failure by default, listed in every build's census (`heavier_than_original`). It usually comes from
  a texture repeated many times across one triangle: the converter cuts such a surface into many faces to stay inside
  the engine's surface limit. An exception is allowed only with a recorded reason per model.
- **A row heavier than the model without it.** A recipe row, a method override or a method-2 mesh that draws more
  triangles than the model's default method (`row_heavier`).
- **Not intact.** The method in use adds or loses an open edge or tears a seam or rim (`not_intact`).
- **Texture repeats.** For each model, the largest number of times one triangle repeats its texture (the larger of
  its two texture-coordinate spans) and its count of triangles over 16 and over 64 repeats. An extreme repeat gets a
  texture bake that keeps the geometry, a matching replacement mapping, or a recorded exception, before any limit is
  raised.
- **Build to build.** `diff` names every model whose triangles changed since the previous record, the method before
  and after, and every model that became heavier than its original. A model that gained triangles is a regression
  until it is explained.

## The record and its schema

`model-census.json` has the format `amiwind-model-census-1`: the census code's SHA-256 (and each file's), the
method tables' SHA-256, the game masters' SHA-256, the switches, the build's name and commit, the rows and a summary
(placed triangles original against today per space, per method in use and per land, the special cases, and the
catchers' lists). `check` refuses a record with a missing field, an unknown method or special-case kind, an
impossible count (a negative count, fewer triangles than faces, placements per space that do not add up, a space
measured but not placed), a flag that does not follow from the counts, or a summary that differs from its rows.
