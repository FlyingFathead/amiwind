# MiniWind: the test ground

MiniWind is AmiWind's quick test ground: a small, fast build of one area,
scene or mechanism, started straight inside it. Use it to try a fix, a mechanism
or a lighting case without building the whole game. A full build is for
releases and whole-island checks; a MiniWind build is for everything else.

<!-- contents start -->
## Contents

- [What it is](#what-it-is)
- [Build one](#build-one)
- [The presets](#the-presets)
- [What is left out](#what-is-left-out)
- [Add a new sandbox](#add-a-new-sandbox)
- [The startup screen and the menu](#the-startup-screen-and-the-menu)
- [Console and automation](#console-and-automation)
- [Limits](#limits)
- [Where the details are](#where-the-details-are)
- [Setting the scene up on arrival](#setting-the-scene-up-on-arrival)

<!-- contents end -->

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
| `--miniwind-scope full\|exterior` | `exterior` holds the town exterior only |
| `--miniwind-town TOWN` | another town table row than Balmora |
| `--miniwind-description TEXT` | the startup screen's `Scene:` line |
| `--direct-to-game-map START` | start in a room or at a spot instead of the arrival point |
| `--quick-character RACE,CLASS[,NAME]` | the ready-made character (default: the Hors preset) |
| `--with-video` | keep the videos, which a MiniWind build leaves out |
| `--miniwind-debug` | a DEBUG ONLY sandbox, never a playtest |

Options you give yourself win over a preset's. `--plan` prints the stage plan
and the stages left out, with reasons, without building.

## The presets

The table is `config/miniwind-presets.json`; the builder makes one
`--miniwind-<name>` option per row.

<!-- presets start -->
| Preset | Option | Scene |
| --- | --- | --- |
| `balmora` | `--miniwind-balmora` | Balmora: exterior and interiors |
| `balmora-exterior` | `--miniwind-balmora-exterior` | Balmora exterior (map only) |
| `vivec-arena-pit` | `--miniwind-vivec-arena-pit` | Vivec Arena Pit: combat test |
| `opening-ship` | `--miniwind-opening-ship` | Opening ship: lantern and ship lighting check |
| `animkit` | `--miniwind-animkit` | Animation kit: walk and run with a companion and hostiles |
<!-- presets end -->

Notes: `balmora-exterior` leaves out the interiors, so every door says
"Area unavailable". `vivec-arena-pit` stops before any stage with the start
point's own message until the Vivec Arena interiors are converted.
`opening-ship` shows the quick character screen on arrival. A test
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

A new sandbox is a new row in `config/miniwind-presets.json`, never a new
script:

```json
{
  "name": "balmora-council-club",
  "description": "Council Club: talk test",
  "scope": "full",
  "start": "interior:Balmora, Council Club",
  "exclude": [],
  "unreferenced": "voice,npcs",
  "character": "Dark Elf,Battlemage,Ilmeni",
  "skip_census": null
}
```

`--miniwind-balmora-council-club` then exists. Every row has exactly these
keys, and the builder checks each with the same rules as the options
(`tests/test_miniwind_presets.py`). Add the row to the table above too; the
docs test insists. The key reference is in the
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

A preset row may list `boot_commands`: debug console commands (`dbg ...`) the sandbox runs once when it
arrives, for example `["dbg companion test", "dbg combat on"]` in the `animkit` row. `--miniwind-boot
"dbg companion test;dbg combat on"` does the same without a preset. Only `dbg` commands are accepted.
