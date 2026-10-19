# Build recipes

_Last updated with AmiWind v0.0.36 (11 October 2026)._

<!-- contents start -->
## Contents

- [The format](#the-format)
- [Building from a recipe](#building-from-a-recipe)
- [Writing a recipe](#writing-a-recipe)
- [The receipts](#the-receipts)
- [The master builder](#the-master-builder)
- [MiniWind presets](#miniwind-presets)
- [Examples](#examples)
- [Option changes](#option-changes)

<!-- contents end -->

A build recipe is one small JSON file that holds everything that makes a build what it is: its
options by name, the input files it reads with their SHA-256, and the build that checked it. Build
from it with `--recipe FILE`; write the recipe of any build with `--save-recipe FILE`. The MiniWind
presets are recipes too (`config/recipes/miniwind/`).

    ./build.sh --data-files "/path/to/Morrowind" --recipe config/recipes/release.json
    ./build.sh --data-files "/path/to/Morrowind" --recipe my-coast.json --chim-terrain-hull compiled
    ./build.sh --data-files "/path/to/Morrowind" --no-npc-gallery --save-recipe my-build.json

## The format

Schema `build-recipe-1` (`config/schemas/build-recipe-1.json`). The full-coast development build of
v0.0.36-dev3 as a recipe (`config/recipes/full-coast-dev.json`, the input notes shortened):

```json
{
  "schema": "build-recipe-1",
  "name": "full-coast-dev",
  "description": "The v0.0.36-dev3 full build: Balmora, Seyda Neen and the Bitter Coast test town on CHIM, ...",
  "options": {
    "chim_areas": ["balmora", "seyda", "bcoast_x7y2"],
    "extra_town": ["bcoast_x7y2"],
    "no_npc_gallery": true,
    "chim_regions": ["@chim-regions-cells.csv"],
    "chim_regions_status": "cell-progress.json",
    "chim_terrain_hull": "routed",
    "chim_terrain_refs": "on",
    "chim_native_towns": "on",
    "chim_frame_ext": "chim",
    "live_logs": true
  },
  "inputs": [
    {"option": "chim_regions", "role": "chim-regions-cells", "path": "chim-regions-cells.csv",
     "sha256": "33ae73f0a12832ab59e196a6e9dbcf99391f36c9ae652f7f0f75267fd8fb9c82", "kind": "file",
     "how": "The 270 finished coastal cells (columns x,y): ... tools/cell_progress.py export ..."},
    {"option": "chim_regions_status", "role": "chim-regions-status", "path": "cell-progress.json",
     "sha256": "0baeabf3ef88474f324db7268def10e93d7c085be2477c190237ffd1fbd0acbc", "kind": "file",
     "how": "The CHIM progress tracker file of the same CHIMport run ..."}
  ],
  "written_with": null,
  "checked_with": null,
  "status": "unverified"
}
```

| Field | Meaning |
| --- | --- |
| `name`, `description` | lower case letters, digits and hyphens; one line on what the build is for |
| `options` | the build's options as named fields (below) |
| `inputs` | every file or folder an option names, with its role and SHA-256 |
| `written_with` | the builder that wrote the recipe: `amiwind_version`, `chim_version`, `builder_commit`, `date` (host time with zone), `run` and its `result`; `null` for the recipes kept in this repository (`config/recipes/`), which follow the source tree they are in |
| `checked_with` | the passed build that verified the recipe: `amiwind_version`, `chim_version`, `builder_commit`, `run`, `date` and `result_sha256` (the SHA-256 of that build's result record); `null` = unverified |
| `status` | `verified` with a `checked_with` record, `unverified` without one |

### Options by name

Every option is named by the builder's own name for it: the option without its leading dashes, with
underscores (`--chim-terrain-hull` is `chim_terrain_hull`, `--chim-area` is `chim_areas`,
`--legacy-area` is `legacy_areas`). The value is what the option takes: a string or number, `true` or
`false` for a switch (`"follow_original_stair_rules": false` is `--no-follow-original-stair-rules`), a
list for a repeatable option, or `null` for the builder's default. An option left out is the
builder's default too. The builder reads the fields through its own option parser, so a value it
would refuse on the command line (an unknown choice, a word where a number goes) is refused in a
recipe with the same message.

CHIM frame maps are `.chim` files, CHIM's own map format: `"chim_frame_ext": "chim"` is the default;
`bsp` is the old method, kept selectable and labelled so.

Some options are never part of a recipe, because they are about one machine or one run, not about
what is built: tool and workspace paths (`--data-files`, `--workspace`, `--sdk`, ...), the run name,
reuse and caches (`--reuse-from`, `--storage-pool`, ...), `--jobs`, the modes (`--check`, `--plan`,
`--dry-run`, setup and inventories), `--developer-mode` and its waivers, and `--override`: a recipe can
never let a retired option through by itself. The list is `NOT_IN_RECIPE` in `tools/build_recipe.py`.

### Input files

Every path an option names (a path option such as `--chim-regions-status`, or a `--chim-regions @FILE`
entry) needs an `inputs` row: the option, a role, the path and its SHA-256. A folder (such as
`--amiga-libs`) is pinned by the SHA-256 of its hash list: one `<sha256>  <relative/path>` line per
file, sorted, joined with line feeds. Before any stage the builder hashes every input and refuses
the recipe when one is missing or its SHA-256 differs. A relative path is read from the folder the
build is started in; `--recipe-input ROLE=PATH` reads a role from another place (the SHA-256 must still
match). An `inputs` row may say `how` the file is made with the repository's tools: the full-coast
example's cells CSV is the CHIM Progress Tracker's export of the finished coastal cells
(`tools/cell_progress.py export`, or the Toolkit World Map's Export CSV), checked with
`tools/chim/regions.py @FILE --status cell-progress.json`.

## Building from a recipe

`--recipe FILE` fills the options before anything reads them. Options given on the command line win:
each difference is printed as `recipe says --chim-terrain-hull routed, command line says
--chim-terrain-hull compiled` and recorded in the receipts. Exclusions add up instead (`--exclude`
groups on the command line are added to the recipe's, as they were with the MiniWind presets). An
input whose option the command line gives again is not checked (the command line replaces it).

Versions decide how loud the build is:

- **The same AmiWind version** as `checked_with` (or `written_with` for an unverified recipe): the
  build runs quietly.
- **A newer builder:** one loud warning, `recipe checked with vX, this builder is vY`, listing every
  option whose meaning or default changed since vX (from `config/option-changes.json`), marking the
  ones the recipe sets itself (its value wins over the new default).
- **An older builder:** refused, `this recipe needs a newer builder (vZ)`, naming the options this
  builder does not know.

An option name the builder does not know is refused at any version. Retired options
(`tools/retired_flags.py`: `--legacy-area`, `--chim-native-towns off`, `--seyda-recorded`) are refused
in developer mode exactly as on the command line; only `--override NAME` on the command line lets one
through, for a labelled A/B test of a historical regression. An unverified recipe (`checked_with:
null`) builds with a one-line warning. `--recipe` and a MiniWind preset are one recipe each: give one.

## Writing a recipe

`--save-recipe FILE` writes the recipe of the build being run when it ends (passed, failed or
cancelled; with `--check` or `--plan` it is written at once): every recipe option with its value
after the defaults, the recipe and the command line, and the SHA-256 of every input. It is written
with `checked_with: null` and `status: unverified`; a plain build never verifies its own recipe.
The master builder fills in `checked_with` after a passed build (below).

Without a build, `tools/build_recipe.py` does the same from a command line, and checks recipes:

    python3 tools/build_recipe.py from-flags --name my-coast -- --chim-terrain-hull compiled --no-npc-gallery
    python3 tools/build_recipe.py check config/recipes/*.json [--inputs]
    python3 tools/build_recipe.py changes --since 0.0.36-dev1

## The receipts

Every build records its recipe in `build-state.json` and `build-summary.json` (`build_recipe`: the
recipe's name, file SHA-256, status, `written_with`, `checked_with`, the command-line overrides and the
input checks, plus `effective_sha256`, the SHA-256 of the build's options and input hashes, which a
build without a recipe has too) and, through the image step, in `image/build.json` (`build_recipe`:
name, SHA-256, status, `checked_with`, `effective_sha256`, run). The record is never part of a stage
key, so a recipe does not make a stage rebuild; an image step reused from another run keeps the
record of the run that made it (its `run` field says which).

## The master builder

`python3 tools/aw.py request --kind build ... --recipe FILE` sends a recipe instead of (or next to)
`--flags` ([AW.md](AW.md), "Build requests"). Its input files become declared inputs, hashed in the
build volume, so a recipe for the build server names them by their path there. The server refuses
retired options in the recipe (unless the request's override allows `retired-flags`), relative input
paths and builders without recipes; flags sent with a recipe win over it, as on the command line.
Every passed build of a builder with recipes saves its recipe, and the server writes the verified
copy next to its result (`results/<run name>.recipe.json`): `checked_with` names the AmiWind and CHIM
version, the commit, the run, the host time and the SHA-256 of the result record.

## MiniWind presets

The MiniWind presets (`--miniwind-preset NAME`, `--miniwind-NAME`) are the recipes in
`config/recipes/miniwind/`, one file per preset, and go through the same path as `--recipe`. A preset
recipe sets `miniwind` and only the MiniWind options (scope, description, start point, exclusions,
character, quick character screen, boot commands). Before v0.0.36 they were rows of one table
(`config/miniwind-presets.json`); `tests/test_build_recipe.py` proves each recipe gives exactly the
options its row gave. See [MiniWind](MINIWIND.md) for the presets.

## Examples

| Recipe | What it builds |
| --- | --- |
| `config/recipes/release.json` | a release build: every shipped feature at its default, nothing left out, every input hashed (`--check-hashes full`); run it with `--developer-mode` |
| `config/recipes/release-coast2.json` | the v0.0.36 release build: the release recipe plus the whole coastline on CHIM (coast2, the closed ring: 325 region cells), Balmora, Seyda Neen, the whole city of Vivec and the Bitter Coast test town on CHIM, no NPC gallery; the CHIMport tracker file is its one input |
| `config/recipes/full-coast-dev.json` | the v0.0.36-dev3 full build: Balmora, Seyda Neen and the Bitter Coast test town on CHIM, the finished coastal cells as CHIM region frames ([CHIM regions](chim/CHIM_REGIONS.md)), no NPC gallery |
| `config/recipes/miniwind-spot.json` | a MiniWind spot: the Balmora exterior only, started at one exterior cell ([Start straight in the game](chim/build_guide/DIRECT_START.md)) |
| `config/recipes/miniwind/*.json` | the MiniWind presets |

`tests/test_build_recipe.py` checks every recipe in `config/recipes/` against the current builder.

## Option changes

`config/option-changes.json` lists, by AmiWind version, every builder option that was added, changed
its default or meaning, was retired or removed (seeded from the history of
`config/build-defaults.json` and `tools/retired_flags.py`). Its `current` block is this builder's
defaults; a test fails when they differ, so a new option or a changed default is recorded there
first (`python3 tools/build_recipe.py snapshot` prints the block). The newer-builder warning reads
this table.
