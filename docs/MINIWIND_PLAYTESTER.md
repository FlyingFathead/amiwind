# AmiWind "MiniWind" Playtester Build

Start with [MiniWind: the test ground](MINIWIND.md) (what it is for, presets,
how to add a sandbox). This page is the reference for the build type itself.

<!-- contents start -->
## Contents

- [How to build it](#how-to-build-it)
- [What it builds](#what-it-builds)
- [Scope: the Balmora exterior only](#scope-the-balmora-exterior-only)
- [Another town and DEBUG ONLY sandboxes](#another-town-and-debug-only-sandboxes)
- [How the game starts](#how-the-game-starts)
- [Boot notice](#boot-notice)
- [Startup logo screen](#startup-logo-screen)
- [Areas the build does not hold](#areas-the-build-does-not-hold)
- [PARTIAL-AREA marking](#partial-area-marking)
- [What it is not](#what-it-is-not)

<!-- contents end -->

A build type of the repository builder for quick playtests: Balmora only, with
the Balmora exterior on the CHIM engine, the Balmora interiors and what the
engine needs to run (menus, UI, fonts, audio and music). It builds in a
fraction of the time of a full build and boots straight into Balmora. It is a
PARTIAL-AREA test build for private `-devN` versions, never a release. The
leanest variant, `--miniwind-scope exterior`, holds the Balmora exterior only.

## How to build it

```sh
./build.sh --miniwind --data-files "/path/to/Morrowind"
./build.sh --miniwind --miniwind-description "Balmora on CHIM, incremental streaming, photo mode" \
  --data-files "/path/to/Morrowind"
./build.sh --miniwind --miniwind-scope exterior --data-files "/path/to/Morrowind" \
  --reuse-from "/path/to/workspace/build/<an earlier run>"
```

`build.cmd`, `build.ps1` and `tools/build.py` take the same options; the
wrappers pass every option through. `--plan` prints the stage plan, the stages
left out (each with its reason), the boot notice and the scope, without
building.

- `--miniwind` selects the build type. The help text, the build summary, the
  build receipt (`build-state.json`: `build_type`, recipe
  `miniwind-balmora-chim-v1`) and the image receipt (`image/build.json`:
  `build_type`) name it `AmiWind "MiniWind" Playtester Build`.
- `--miniwind-description TEXT` (optional) adds a "Scene:" line to the
  startup screen. Printable ASCII only (characters the game font has), at
  most 72 characters with the "Scene: " prefix, wrapped with the game font
  to at most two lines; anything else is refused with a clear message before
  any stage runs. The text is recorded in both receipts.
- `--miniwind-scope SCOPE` (optional): `full` (the default, everything this
  page describes) or `exterior` (the Balmora exterior on CHIM only, see
  [below](#scope-the-balmora-exterior-only)). Any other value, or the option
  without `--miniwind`, is refused before any stage runs.

The build is refused unless `VERSION` is a private `-devN` version (refused
for release candidates and finals, as the private-test waivers are), in every
scope. It always uses the CHIM builder with Balmora as its only CHIM area:
`--builder legacy`, another `--chim-area`, `--extra-town`, `--no-extra-town`,
`--only-core-towns`, `--seyda-recorded`, `--dry-run` and `--stage terrain`
stop it before any work.

## What it builds

The normal plan runs, minus the stages this build type leaves out
(`tools/miniwind.py`, `OMITTED`):

| Left out | Why |
| --- | --- |
| `area` | Seyda Neen rooms and residents |
| `npc-gallery` | the NPC inspection gallery, a debugging browser |
| `world-survey`, `world-ui` | the open-world survey and map tiles (the image writes the overview map from the game files) |
| `actor-contact` | the Seyda Neen scene actor audit (the image step keeps its final actor gate) |
| `world-terrain`, `world-scenery-assets`, `world-scenery` | the open world |
| `world-flora-assets`, `world-flora` | world flora (it needs the open-world terrain) |
| `town-<id>` | extra towns (the Vivec Arena) |

What runs: the scene chain the boot payload comes from (setup to census;
palette, models, UI), `balmora` (residents, doors, the region maps the CHIM
frame map is made from), `balmora-interiors`, `door-audio`, `character`,
`reading`, `opening-references`, `media`, `music`, `engine`, `harvest`,
`hand-catalog`, `chim` (the Balmora exterior as a CHIM world) and `image`.

The image step removes every map that is not Balmora's before any pass runs
(Seyda Neen, the prison ship, Census, other towns and their rooms). The videos
are left out by default (`--with-video` keeps them; see
[Quick test builds](chim/build_guide/QUICK_TEST_BUILDS.md#miniwind-builds-are-quick-test-builds-by-default)). Balmora's own region maps stay on the
disk: they are the source of the CHIM frame map, the town's door and arrival
data, and the `chim_towns 0` comparison. By default the Balmora exterior runs on CHIM
(`maps/balmora-chim.bsp`). The pruning is recorded in
`image/miniwind-prune.json`.

## Scope: the Balmora exterior only

`--miniwind-scope exterior` is the leanest test build: the Balmora exterior on
CHIM and nothing else that the exterior does not need to boot and play. It is
labelled "quick playtest, no NPC gallery" and implies `--no-npc-gallery`.

Left out on top of the table above (`tools/miniwind.py`, `SCOPE_OMITTED`):

| Left out | Why |
| --- | --- |
| `balmora-interiors` | the Balmora interiors; their doors say "Area unavailable" |
| `door-audio` | door sounds: every Balmora door leads to a left-out interior, so none opens |

Stage plan, in order: `setup`, `terrain`, `scenery`, `scene`, `bsp`, `npcs`,
`hands`, `interior`, `dialogue-lookup`, `intro`, `census`, `balmora`,
`character`, `reading`, `opening-references`, `media`, `music`, `engine`,
`harvest`, `hand-catalog`, `chim`, `image`.

Why the rest stays:

- `interior`, `intro`, `census`: the scene chain is one tree the image is
  assembled from (`intro-scene`: palette, `progs.dat`, models, actor talk and
  walk poses), and census writes the palette every later stage reads. Their
  maps (the prison ship, Census) leave the image as in the full scope.
- `balmora`: the residents (they live in the exterior frame map,
  `maps/balmora-chim.bsp`) and the region maps the frame map is made and
  checked from.
- `character`: the character catalogue the quick start's Hors preset needs.
- `reading`, `opening-references`, `dialogue-lookup`: residents' dialogue and
  the placed-reference identities of the exterior objects.
- `harvest`, `hands`, `hand-catalog`, `media`, `music`, `engine`, `chim`:
  plants, first-person hands, sounds, music, the engine and the CHIM world.

The image keeps only Balmora's town map and region maps (then the pure CHIM
image replaces them with the frame map as always); the image step's gates (map
budgets, stairs, actors, arrivals, the save fingerprint) check only what ships.
With `--reuse-from`, every stage whose fingerprint and run-folder inputs match
the earlier run is reused (docs/BUILD_PROFILE.md); the stages of the scene
chain after `balmora` see a tree without the interiors, so they may run again,
while the long stages up to `balmora` are reused.

Where the label appears: the default run folder name
(`build-<UTC time>-quick-playtest-no-NPC-gallery`; an explicit `--name` stays
as given), the HDF name
(`AmiWind-v<VERSION>-MiniWind-PARTIAL-AREA-quick-playtest-no-NPC-gallery.hdf`),
both receipts (`build_type`: `scope`, `label`, `partial_area`
`PARTIAL-AREA test build: Balmora exterior only; not a release`, recipe
`miniwind-balmora-exterior-chim-v1`), the build summary and the boot notice.

What it is NOT: not a test of any interior, door transition, door sound or
the NPC gallery; not the locked MiniWind scope (that is `full`, the default);
not a release or release candidate.

## Another town and DEBUG ONLY sandboxes

`--miniwind-town TOWN` builds the sandbox from another town table row
(`config/towns.json`, any row except Seyda Neen, which needs the recorded maps):
that town's exterior on CHIM, its residents and, in the full scope, its
interiors. The game boots straight into it. Balmora's scene stage still runs,
because it is part of the scene chain and the image step reads it, but Balmora's
interiors do not, and the image removes Balmora's maps. The notice, the marker,
the receipts (recipe `miniwind-<town>-chim-v1`) and the HDF and run names carry
the town. Balmora builds keep every name and command line they had.

`--miniwind-debug` marks a DEBUG ONLY sandbox, which is not a playtest. The boot
notice reads `DEBUG ONLY: MINIWIND DEBUG BUILD, NOT A PLAYTEST`, the startup
screen reads `MiniWind DEBUG ONLY`, and the marker, receipts (`debug_only`,
`debug_settings`) and HDF and run names (`-DEBUG-ONLY`) say so. Only a debug
sandbox takes `--chim-draw-distance N` (128..540): a stated closer view. The
CHIM world is built and heap-gated for that draw distance, and the image starts
with it. It is never a playtest or release setting.

Opt-in CHIM settings for any CHIM build: `--chim-detail-budget NAME`
(`config/chim-detail-budgets.json`) and `--chim-cut-models-over UNITS` (the
large-model cut). A private -devN build can also accept a known stair finding
with `--accept-known-stair-findings ID`.

Example: the Vivec Temple debugging sandbox, used for the in-engine stair walk
and the statue A/B shots:

    tools/build.py --miniwind --miniwind-town vivec_temple --miniwind-debug         --chim-draw-distance 448 --chim-detail-budget vivec-wide --chim-cut-models-over 512         --accept-known-stair-findings VIVEC-TEMPLE-STAIRS-33         --miniwind-description "Vivec Temple: stairs and statues, closer view"

## How the game starts

The startup screen comes up and waits for Enter (below); then the game starts
in Balmora at its arrival point as the Hors preset character (Nord, Barbarian,
The Steed), the same character `dbg tp balmora` creates. New Game in the main
menu starts there again; there is no ship opening or character creation. The
console command `aw_quick_start [town]` does the same in any build.

Why this way: the engine already had everything a quick start needs (the
Hors preset, a town's arrival point from its region table, the door arrival
placement). The engine reads the build's notice file (below) and, when it is
present, runs the quick start after the startup screen and for New Game.
Normal builds have no such file and keep the logo, main menu and ship opening.

## Boot notice

The builder writes `id1/miniwind.txt` into the image; the engine prints it to
the console at start-up and shows it in the game's message box (game font)
when the quick start arrives in Balmora:

```text
ATTENTION: THIS IS A MINIWIND PLAYTEST BUILD
FEATURES ONLY: Balmora exterior (CHIM), Balmora interiors, Balmora residents, harvestable plants, per-race hands, door sounds, books, music, sound effects and voices
```

With `--miniwind-scope exterior` the generated list is shorter and ends with
the scope's label:

```text
FEATURES ONLY: Balmora exterior (CHIM), Balmora residents, harvestable plants, per-race hands, books, music, sound effects and voices; quick playtest, no NPC gallery
```

The FEATURES list is generated from the stage plan: each entry comes from the
stage that builds it (`tools/miniwind.py`, `FEATURES`), so a stage the plan
does not run (for example `--no-harvest`) is not listed. Nobody types the list.
File format (`AWMW1`, one `key value` line each, printable ASCII):

```text
AWMW1
town balmora
title ATTENTION: THIS IS A MINIWIND PLAYTEST BUILD
features FEATURES ONLY: ...
```

## Startup logo screen

The startup screen shows, centred, the logo and three lines in the same game
font as the normal subtitle lines, and under them one line in the console
font. On the version line, "CHIM v0.1.0" is drawn in the console font too (the
font of "Press ENTER to start"); the rest of that line stays in the game font:

```text
AmiWind (logo)
MiniWind Playtest
AmiWind v0.0.33-dev1 / CHIM v0.1.0
Scene: <--miniwind-description text, one or two lines>
Press ENTER to start
```

The version line is generated from the `VERSION` and `CHIM_VERSION` files the
boot check already uses, never typed by hand. The "Scene:" line appears only
with `--miniwind-description`. The lines are checked against their fonts when
the image is made (every character must have a glyph, every line must fit the
screen).

Why "CHIM" is in the console font: the game font is Morrowind's own Magic Cards,
whose capital H is an uncial "h" (the original font's design), so "CHIM" would
read "ChIM". The font conversion is left as it is everywhere else. The builder
draws the "CHIM v..." part with the engine's console glyphs (the same 8x8 atlas
the engine's console and prompt use, `tools/debug_font.py`), on the game font's
baseline, as part of the logo stream; the whole line stays centred
(`tools/miniwind.py` `version_segments`, `tools/prepare_logo.py`). The build
receipt records the plain lines (`logo_lines`) and the console-font text
(`logo_console_font`).

How it works: the builder's logo stream fades in and ends on the fully lit
screen, with the prompt's rows left black (`tools/prepare_logo.py`,
`prompt_top`). The engine keeps showing that last frame, draws "Press ENTER to
start" in the console font at row 184 (`aw_miniwind.h`) and waits; Enter
starts the game (the quick start). Esc or Space during the fade only skip to
that screen. Normal builds keep their logo fade-out, then the main menu, and
"An open-source RPG engine / for the Commodore Amiga".

## Areas the build does not hold

Exits to areas that are not in the build say "Area unavailable" in the message
box and never load anything:

- the edge of Balmora's CHIM frame (past the union of Balmora's region cores):
  the player is held 32 units inside it;
- a door whose destination map is not on the disk (in the exterior scope:
  every Balmora door);
- the silt strider to Seyda Neen.

Noclip is never held, and neither are the legacy region maps (`chim_towns 0`),
which keep their own edges.

## PARTIAL-AREA marking

So that a MiniWind image is never mistaken for a release:

- the HDF is named `AmiWind-v<VERSION>-MiniWind-PARTIAL-AREA.hdf` (with
  `-quick-playtest-no-NPC-gallery` in the exterior scope);
- the boot volume's root holds `PARTIAL-AREA-TEST.txt` with the build type,
  version, notice, scope and description;
- `build-state.json`, `build-summary.json` and `image/build.json` record
  `build_type` with `PARTIAL-AREA test build: Balmora only; not a release`
  (or `PARTIAL-AREA test build: Balmora exterior only; not a release`);
- the build summary prints the build type, the scope, the notice and the
  description.

## What it is not

- Not a release, release candidate or playtest of the whole game: Seyda Neen,
  the open world, the Vivec Arena, the ship opening, character creation, the
  NPC gallery and world flora are not in it.
- Not a substitute for the from-scratch build and release gate, which always
  build the whole game.
