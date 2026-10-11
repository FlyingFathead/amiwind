# Start straight in the game

A development build can boot straight into a town, a room or a spot of your
choice, with a ready-made character: no intro movie, no prison ship, no
character creation. Use it to test one place again and again. A normal build
without these options still starts with the full intro.

<!-- contents start -->
## Contents

- [The four kinds of start point](#the-four-kinds-of-start-point)
- [The character: `--quick-character`](#the-character---quick-character)
- [The startup screen](#the-startup-screen)
- [Worked example: the Vivec Arena Pit](#worked-example-the-vivec-arena-pit)
- [With `--exclude-unreferenced`](#with---exclude-unreferenced)

<!-- contents end -->

```sh
./build.sh --data-files "/path/to/Morrowind" --direct-to-game-map balmora
```

Direct starts are for development versions only (a `VERSION` such as
`0.0.33-dev1`); release candidates and finals refuse them. The build is a
**quick test build**: its receipts, its run folder name and the game say
`quick test build: direct to <start>`.

## The four kinds of start point

`--direct-to-game-map` takes one start point, in one of four forms.

| Form | Example | Where you start |
| --- | --- | --- |
| An area | `balmora`, `seyda_neen`, `vivec_arena` | the area's normal arrival point |
| `interior:<cell id>` | `"interior:Balmora, Council Club"` | the arrival point of a door into that room |
| `cell:X,Y` | `cell:-3,-2` | the centre of that exterior cell, dropped to the ground |
| `pos:X,Y,Z[@HEADING]` | `pos:-20480,-12288,1200@90` | that spot, facing HEADING degrees (0 north, 90 east) |

Cell IDs contain commas and spaces: put the whole start point in quotes.

```sh
--direct-to-game-map "interior:Balmora, Council Club"
--direct-to-game-map cell:-3,-2
--direct-to-game-map pos:-20480,-12288,1200@90
```

`pos:` uses the same global coordinates the debug HUD shows on its
`GLOBAL XYZ` line (`dbg coords on`), so you can copy a spot from a screenshot. The
`@HEADING` part is optional; the HUD's compass shows the same degrees.

### What the builder checks

Before any stage runs:

- the area or room must be in the build: a MiniWind build holds its town
  (`--miniwind-town`, default Balmora) and, in its full scope, that town's
  rooms; a normal build holds Seyda Neen,
  Balmora, the shipped towns, their converted rooms and the open world. With
  `--exclude interiors` only the prison ship and the Census and Excise Office
  remain;
- a `cell:` must exist in your game files and lie in the area the build holds;
- a `pos:` must lie in the area the build holds.

When the image is made, on the final maps:

- `interior:` takes the arrival point of a door that leads into the room; a
  room no door leads into is refused;
- `cell:` and `pos:` find the map that holds the point and run the game's own
  arrival search on its collision: a spot inside a wall or a rock moves to the
  nearest place you can stand (within 16 units sideways and 64 units down); a
  spot in water or with no floor is refused with the reason.

The resolved start is written to `direct-start.json` beside the image and to
`build.json` (`direct_start`).

### The player starts in what the build holds

A build of one area starts the player in that area, for every partial-area
build (MiniWind presets and recipes, `--miniwind-town`, direct starts):

- **The start follows the content.** A MiniWind build without
  `--miniwind-town` whose start lies in a town (the area itself, one of its
  rooms or a cell of its grid) holds that town: `--miniwind-preset
  vivec-arena-chim` (start `vivec_arena`) is a Vivec Arena build with no
  further option. A MiniWind build with no start begins at its town's own
  arrival point.
- **A start outside the build is refused before any stage**, with what the
  build holds: its areas, its rooms and its cells. There is no fallback to
  another town.
- **The image checks it again**, in seconds, after every map is written and
  before the image is packed: the start map (or the town's CHIM frame map,
  `maps/<town>-chim.chim`) is in the image, and a start spot on a Quake map
  has a place to stand on its collision (`start-check.json`, `build.json`
  `start`).

The start and why it was chosen (explicit, from a recipe, or the town's
arrival) are recorded in `build-state.json` (`start`); the game's quick-start
notice (`id1/miniwind.txt`) carries the town and the start line it boots into.

## The character: `--quick-character`

By default you play the Hors preset: a Nord Barbarian born under The Steed,
the same character the debug teleport makes. Choose another with
`--quick-character RACE,CLASS[,NAME]`:

```sh
--quick-character "Dark Elf,Battlemage,Ilmeni"
--quick-character dark_elf,battlemage
```

Race and class must be playable in your own game files (an underscore stands
for a space). The character is a normal character of the game: saving works
once you walk around.

## The startup screen

A direct start shows a startup screen and waits for Enter, like a MiniWind
build:

```text
Quick Test Build
AmiWind v0.0.33-dev1
Scene: Balmora, Council Club
Press ENTER to start
```

In a MiniWind build the screen keeps its MiniWind title; its `Scene:` line
names the start point unless `--miniwind-description` gives another text. On
arrival the game's message box shows the build's notice once: `DIRECT TO:
<start>` (a MiniWind build shows its feature list).

## Worked example: the Vivec Arena Pit

The next MiniWind test spot is the fight interior of the Vivec Arena, cell ID
`Vivec, Arena Pit` (in Morrowind.esm; its neighbours are the Arena Holding
Cells, Fighters Quarters, Fighters Training, Storage and Hidden Area):

```sh
./build.sh --data-files "/path/to/Morrowind" \
  --miniwind --direct-to-game-map "interior:Vivec, Arena Pit" \
  --exclude-unreferenced --no-npc-gallery
```

or, with the preset, `--miniwind-vivec-arena-pit`
(see [MiniWind](MINIWIND.md#presets)).

**The interior must be in the build.** The Arena Pit is the Arena's first
room in `config/vivec_arena.json` (map `vai000`), and the start resolver finds it
there; the start makes the build a Vivec Arena build. A CHIM-native town's listed
rooms are made by its own stage, `chim-rooms-<town>` (`tools/chim_rooms.py`,
after `chim-town-<town>`): the same room converter as the legacy chain, one
hashed unit per room, with the doors into the rooms and out to the town's CHIM
frame linked. The game starts inside the Pit, at the arrival of the door that
leads into it. A room whose town has no such stage in the plan is refused before
any stage, naming the room and the missing stage
(BUILD-MINIWIND-ARENA-PIT-REFUSED-36).

## With `--exclude-unreferenced`

In an area build (MiniWind), `--exclude-unreferenced` builds only what the
start point references: an `interior:` start covers that room, a `cell:` or
`pos:` start its cell, an area start the whole area. See
[Quick test builds](QUICK_TEST_BUILDS.md#only-what-the-area-references---exclude-unreferenced).

Back to the [CHIM build guide](README.md).
