# Start straight in the game

A development build can boot straight into a town, a room or a spot of your
choice, with a ready-made character: no intro movie, no prison ship, no
character creation. Use it to test one place again and again. A normal build
without these options still starts with the full intro.

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

- the area or room must be in the build: a MiniWind build holds Balmora and
  (in its full scope) Balmora's rooms; a normal build holds Seyda Neen,
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

**The interior must be in the build.** Today the Vivec Arena interiors are not
converted (towns imported from `config/towns.json` have no interiors yet,
IMPORT-TOWN-NO-INTERIORS-32), so the builder refuses this start before any
stage runs:

```text
--direct-to-game-map "interior:Vivec, Arena Pit": the interior "Vivec, Arena Pit"
is not in this build. Towns imported from config/towns.json (the Vivec Arena)
have no converted interiors yet (IMPORT-TOWN-NO-INTERIORS-32). ...
```

It works as soon as a builder converts the Arena's rooms.

## With `--exclude-unreferenced`

In an area build (MiniWind), `--exclude-unreferenced` builds only what the
start point references: an `interior:` start covers that room, a `cell:` or
`pos:` start its cell, an area start the whole area. See
[Quick test builds](QUICK_TEST_BUILDS.md#only-what-the-area-references---exclude-unreferenced).

Back to the [CHIM build guide](README.md).
