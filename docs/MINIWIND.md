# MiniWind: the test ground

_Last updated with AmiWind v0.0.53 (27 October 2026)._

<!-- contents start -->
## Contents

- [What it is](#what-it-is)
- [Build one](#build-one)
- [Map inspection start](#map-inspection-start)
- [The presets](#the-presets)
- [What is left out](#what-is-left-out)
- [Add a new sandbox](#add-a-new-sandbox)
- [The startup screen and the menu](#the-startup-screen-and-the-menu)
- [Console and automation](#console-and-automation)
- [Limits](#limits)
- [Where the details are](#where-the-details-are)
- [Setting the scene up on arrival](#setting-the-scene-up-on-arrival)

<!-- contents end -->

MiniWind is AmiWind's quick test ground: a small, fast build of one area,
scene or mechanism, started straight inside it. Use it to try a fix, a mechanism
or a lighting case without building the whole game. A full build is for
releases and whole-island checks; a MiniWind build is for everything else.

## What it is

- One area, scene or mechanism per build: a town on CHIM, the Vivec Arena Pit
  fight, a stair flight, the opening ship's lighting, the companion, an
  animation scene.
- A build type of the repository builder (`tools/build.py --miniwind`, wrapped
  by `build.sh`, `build.cmd` and `build.ps1`), not a separate script.
- Built in minutes when it reuses an earlier run (`--reuse-from`), and it
  boots straight into the scene.
- A **partial-area test**: the image, the receipts, the run folder and the boot
  screens say so. It is for private `-devN` versions only and is refused for
  release candidates and finals.
- Testing a fix or a mechanism means a MiniWind build of just that scene, never
  a full build.

## Build one

A preset is a ready-made sandbox. List them, then build one:

```sh
./build.sh --data-files "/path/to/Morrowind" --miniwind-preset list
./build.sh --data-files "/path/to/Morrowind" --miniwind-balmora-exterior
./build.sh --data-files "/path/to/Morrowind" --miniwind-preset balmora-exterior \
  --reuse-from "/path/to/workspace/build/<an earlier run>"
```

Without a preset, `--miniwind` builds the default sandbox (Balmora on CHIM)
and you choose the rest with options:

```sh
./build.sh --miniwind --miniwind-description "Balmora on CHIM, photo mode" \
  --data-files "/path/to/Morrowind"
./build.sh --miniwind --miniwind-scope exterior --data-files "/path/to/Morrowind"
./build.sh --miniwind --direct-to-game-map "interior:Vivec, Arena Pit" \
  --data-files "/path/to/Morrowind"
```

| Option | Meaning |
| --- | --- |
| `--miniwind` | select the MiniWind build type |
| `--miniwind-preset NAME` or `--miniwind-NAME` | a named sandbox from the table below (`list` prints it) |
| `--miniwind-scope full\|exterior\|interior` | `exterior` holds the town exterior only; `interior` converts only the start room of an `interior:<cell>` start |
| `--miniwind-town TOWN` | another town table row than Balmora |
| `--miniwind-description TEXT` | the startup screen's `Scene:` line |
| `--direct-to-game-map START` | start in a room or at a spot instead of the arrival point |
| `--quick-character RACE,CLASS[,NAME]` | the ready-made character (default: the Hors preset) |
| `--with-video` | keep the videos, which a MiniWind build leaves out |
| `--miniwind-debug` | a DEBUG ONLY sandbox, never a playtest |
| `--miniwind-map-inspection` | opt-in direct inspection start with god mode, noclip and debug HUD |

Options you give yourself win over a preset's. `--plan` prints the stage plan
and the stages left out, with reasons, without building.

## Map inspection start

Use `--miniwind-map-inspection` with `--miniwind` to enter the selected test
scene without the logo, menus or character pages. It uses the existing quick
character and test-start path, then enables god mode, noclip and the debug
HUD. It is an inspection aid for private development builds; omit the option
for the normal MiniWind start. Choose the scene with the existing
`--direct-to-game-map` option, for example:

```sh
./build.sh --data-files "/path/to/Morrowind" --miniwind \
  --direct-to-game-map "interior:Vivec, Arena Pit" --miniwind-map-inspection
```

The option does not select arbitrary asset files or create a custom file-list
import. A saved preset or explicit build options still determine the content
included in the MiniWind image.

## The presets

Each preset is a build recipe in `config/recipes/miniwind/` (one file per
preset, [Build recipes](BUILD_RECIPES.md)); the builder makes one
`--miniwind-<name>` option per recipe.

<!-- presets start -->
| Preset | Option | Scene |
| --- | --- | --- |
| `balmora` | `--miniwind-balmora` | Balmora: exterior and interiors |
| `balmora-exterior` | `--miniwind-balmora-exterior` | Balmora exterior (map only) |
| `vivec-arena-pit` | `--miniwind-vivec-arena-pit` | Vivec Arena Pit: combat test |
| `vivec-arena-chim` | `--miniwind-vivec-arena-chim` | Vivec on CHIM (whole city) from the Arena arrival |
| `vivec-city-chim` | `--miniwind-vivec-city-chim` | All of Vivec on CHIM, one frame: cantons, Temple, frame edge |
| `vivec-city-exterior` | `--miniwind-vivec-city-exterior` | Vivec city on CHIM, exterior: mushrooms, HUD, inspect |
| `vivec-palace` | `--miniwind-vivec-palace` | Palace of Vivec: Vivec meditating, interior creatures |
| `opening-ship` | `--miniwind-opening-ship` | Opening ship: lantern and ship lighting check |
| `animkit` | `--miniwind-animkit` | Animation kit: walk and run with a companion and hostiles |
| `anim-stage` | `--miniwind-anim-stage` | Animation stage: skeletal NPCs play every shared-table group |
| `seyda-chim` | `--miniwind-seyda-chim` | Seyda Neen on CHIM (CHIM-native): arrival, residents, doors |
| `lava-pools` | `--miniwind-lava-pools` | Molag Mar lava pools: visibility, contact and damage |
| `redmountain` | `--miniwind-redmountain` | Red Mountain summit: terrain ceiling, standing, high flight |
| `halloween` | `--miniwind-halloween` | Halloween: skeletons, dancers and Dagoth Ur dance on the beat |
<!-- presets end -->

Notes: `balmora-exterior` leaves out the interiors, so every door says
"Area unavailable". `vivec-arena-chim` and `vivec-city-chim` start at the Arena arrival;
`vivec-palace` and `vivec-arena-pit` use the interior scope: the Vivec frame and only their start room
(the Palace of Vivec, `vpi015`, where Vivec meditates; the Arena Pit, `vai000`); every other door says "Area unavailable".
`opening-ship` shows the quick character screen on arrival. `anim-stage` (v0.0.52) is Balmora's exterior with
skeletal NPCs: on arrival the guard torches are forced on, a cast of NPCs is lined up in front of you and every group
of the shared animation tables plays one after another ([ANIMKIT.md](ANIMKIT.md), `dbg animkit stage`). `seyda-chim` (since v0.0.36-dev5: Seyda Neen is
CHIM-native, so it is a MiniWind town) starts at Seyda Neen's arrival with its houses; the Census office and the
prison ship are left out. `redmountain` (v0.0.43) is the 3 x 3 cells around Red Mountain's summit, the island's
highest ground, arriving on the summit: for the terrain ceiling over high ground (standing, the terrain drawn from the
eye, a high flight). `halloween` (v0.0.53) is the animation stage's Balmora with the Halloween scene's cast in the
image: on arrival `dbg halloween` starts the dance; `--custom-ost FILE` adds your own music to your image
([HALLOWEEN.md](HALLOWEEN.md)). A test
(`tests/test_miniwind_docs.py`) fails when a preset is missing from this table.

## What is left out

The point of the sandbox is a small payload. Every MiniWind build leaves out:

- the NPC gallery (the exterior scope is labelled "quick playtest, no NPC
  gallery");
- the videos (`--with-video` keeps them);
- voices and NPC records the scene does not reference
  (`--exclude-unreferenced voice,npcs`);
- the open world, other towns, the Seyda Neen rooms and the world flora;
- the quick character's census walk (`--skip-census`, on by default).

Music, the shared sky and every line the included NPCs can say stay. The stage
list of each scope is in [MiniWind playtester
build](MINIWIND_PLAYTESTER.md#what-it-builds), and the exclusion groups are in
[Quick test builds](chim/build_guide/QUICK_TEST_BUILDS.md).

## Add a new sandbox

A new sandbox is a new recipe file in `config/recipes/miniwind/`, named
after the preset (`balmora-council-club.json`), never a new script:

```json
{
  "schema": "build-recipe-1",
  "name": "balmora-council-club",
  "description": "MiniWind preset --miniwind-balmora-council-club: Council Club: talk test",
  "options": {
    "miniwind": true,
    "miniwind_scope": "full",
    "miniwind_description": "Council Club: talk test",
    "direct_to_game_map": "interior:Balmora, Council Club",
    "exclude_unreferenced": "voice,npcs",
    "quick_character": "Dark Elf,Battlemage,Ilmeni"
  },
  "inputs": [],
  "written_with": null,
  "checked_with": null,
  "status": "unverified"
}
```

`--miniwind-balmora-council-club` then exists. A preset recipe sets `miniwind`
and only the MiniWind options; the builder checks each with the same rules as
the options (`tests/test_miniwind_presets.py`, `tests/test_build_recipe.py`).
Add the preset to the table above too; the docs test insists. The key reference is in the
[MiniWind build guide](chim/build_guide/MINIWIND.md#adding-a-test-spot).

## The startup screen and the menu

The startup screen shows the AmiWind logo and, under it:

```text
MiniWind Playtest
AmiWind v<VERSION> / CHIM v<CHIM version>
Scene: <the description, one or two lines>
Press ENTER to start
```

Enter starts straight in the scene. The main menu of a MiniWind build shows
`MINIWIND TEST UNIT: <description>` at the top, and the game prints a boot
notice (`ATTENTION: THIS IS A MINIWIND PLAYTEST BUILD`, then the generated
`FEATURES ONLY:` list). Normal builds keep the plain logo, menu and ship
opening. Details: [startup logo
screen](MINIWIND_PLAYTESTER.md#startup-logo-screen).

## Console and automation

- On the startup screen, the console key (the backtick, or F10) leaves it for
  the main menu with the console open.
- `aw_quick_start [town]` starts the quick start from the console in any build.
- For automated tests, a test image can boot with `aw_boot_console 1` (the
  console opens over the main menu at once) or `aw_test_start 1` (the quick
  start at once), both without the startup screen.
- A test image also has a command mailbox in memory (signature `AWCMDBOX`; a
  harness that can read and write guest memory queues console commands and
  reads their output) and an optional `AWTEST:` drive: the engine runs
  `AWTEST:test.cfg` at start-up when it exists, and `aw_test_poll N` makes it
  read and delete `AWTEST:cmd.cfg` every N frames.

One image serves many tests: the character and the pose come from the image's
configuration.

## Limits

- Partial area: exits to areas the build does not hold say "Area unavailable"
  and load nothing (the frame edge, doors to left-out rooms, the silt strider).
- Private `-devN` versions only. A release candidate or final refuses
  `--miniwind` and every preset.
- Not a release, not a full-game check, not a performance claim for the whole
  island. The from-scratch build and the release gate always build the whole
  game.

## Where the details are

- [MiniWind playtester build](MINIWIND_PLAYTESTER.md): the build type, scopes,
  stage lists, receipts and marking.
- [MiniWind in the CHIM build guide](chim/build_guide/MINIWIND.md): presets and
  rows.
- [Start straight in the game](chim/build_guide/DIRECT_START.md): start points
  and characters.
- [Quick test builds](chim/build_guide/QUICK_TEST_BUILDS.md): exclusions.

## Setting the scene up on arrival

### Map inspection preset

Add `--miniwind-map-inspection` to a development MiniWind build to skip the
startup screens and character creation, then enable god mode, noclip and the
debug HUD on arrival. Omitting this flag keeps the regular MiniWind startup.
The preset reuses the existing quick-start, scripted-character and debug
commands; it does not require a different engine executable.

Select the included area with `--miniwind-town TOWN` and choose the initial
view with `--direct-to-game-map START`. START accepts a supported town,
`interior:<cell id>`, `cell:X,Y`, or `pos:X,Y,Z@HEADING`; see the
[direct-start guide](chim/build_guide/DIRECT_START.md) for coordinate units
and build-coverage checks. The full MiniWind scope includes the chosen town's
available interiors; the exterior scope omits them; the interior scope (`--miniwind-scope interior`, with an
`interior:<cell id>` start) converts only that room, leaves the island-wide mesh seam audit and the tracker data
out, and its other doors say "Area unavailable".

For another map already included in the image, the console command
`aw_quick_start map MAP X Y Z YAW` starts a fresh inspection there using local
map coordinates. It reapplies the inspection arrival commands. The map must
be recognized by the runtime and have its matching compiled resources in the
image. This option does not yet import an arbitrary list of loose map files.

Generate game data locally from your own game installation. The public
builder distributes code and documentation, not the original game assets.
Noclip inspection does not verify walking collision, and a successful local
scene load does not establish full-world memory or traversal safety.


A preset row may list `boot_commands`: debug console commands (`dbg ...`) the sandbox runs once when it
arrives, for example `["dbg companion test", "dbg combat on"]` in the `animkit` row. `--miniwind-boot
"dbg companion test;dbg combat on"` does the same without a preset. Only `dbg` commands are accepted.
