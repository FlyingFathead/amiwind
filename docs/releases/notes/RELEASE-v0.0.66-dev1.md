# AmiWind v0.0.66-dev1 (in development)

_Last updated with AmiWind v0.0.66-dev1 (12 November 2026)._

Development snapshot, 12 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The first snapshot of v0.0.66. It is built on the v0.0.65 release, so every fix of v0.0.65 to the opening is in it, and
it continues the road to the two expansion worlds: the builder now has one reader that merges the base game file with
the files of Tribunal and Bloodmoon, and its stages are keyed by the expansion layers that are selected. In the game,
the Heart of Lorkhan is a resident of its room, and the effects on the player are shown as a row of icons. The
expansions' cells and rooms are being brought in through the same builder and stages as Vvardenfell; no expansion area
is built in this snapshot, and the dev1 build itself has not been made yet. The game needs 32 MB of Fast RAM, and the
emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet.

## New since v0.0.65

### The builder

- **One reader for the base game and the expansions.** The reader merges the base game file with the files of the
  selected expansions (Tribunal and Bloodmoon) by the rules the reference engine uses for a load order, so a stage that
  reads the cells, rooms and records sees the merged result. The merged files are written in the builder's own scratch
  folder, and only the master list that was set for the build selects what is read.
- **Stage keys follow the selected layers.** The stages that read the game data are keyed by the expansion layers that
  are selected, so choosing a different set of layers re-keys exactly the stages that read them and no others. Both
  expansion layers are selected by default. When they are selected, the builder first checks that the expansion files
  are present and compares their SHA-256 with the known ones, and stops at once, before any stage, when a file is missing
  or differs.
- **The expansions' cells and rooms join the base lists.** When Bloodmoon is selected, the named set of Solstheim's
  cells is added to the cell list, taking only the cells that are finished and dropping the rest with their reason;
  the expansions' rooms, Mournhold's five districts among them, are added as their own batches after the island's, so
  the island's batches and ids do not change. Without the expansions (`--no-dlc`) the lists are as before.
- **Archives in load order.** The room converter and the scenery export read the selected expansions' archives over the
  base game's archive, the later one winning, as the reference engine does; the base game alone reads its own archive
  as before. The creature tables read the selected game files too.
- **Cell keys follow the layers.** A CHIMport cell is keyed by what the layers change in its frame (its own and its
  neighbours' merged cell and land records, placed objects and layer archive models), so cells the expansions do not
  touch keep their base key and are reused.
- **CHIMport through the master builder.** CHIMport cells are measured through a request of their own to the master
  builder, with a check run before the run itself.
- **Layer stores in the image.** The image carries the expansions' stores beside the base world, and the engine has a
  store table and a guard that refuses a target that was not built.
- **The release file list names the reader and its tests.**

### The game

- **The Heart of Lorkhan is a room resident.** The heart is placed in its chamber as a resident of the room, with its own
  animation table, instead of being left out of the room.
- **The active effects are shown as a row of icons.** A row under the view shows the small icon of each effect on the
  player, up to three rows with a "+N" for the rest; the Stats window shows the same icons, and V opens the full list
  ([active-effect HUD](../../HUD_ACTIVE_EFFECTS.md)).
- **Groundwork for the Heart chamber's collapse.** The engine has a reader and a sampler for the tracks that move the
  chamber's parts in the collapse. The game does not call it yet: the collapse is not animated in this snapshot.

### From v0.0.65

- **The opening's fixes.** Everything [v0.0.65](RELEASE-v0.0.65.md) fixed in the opening (the dock guard, the race
  choice, the census office, Sellus Gravius and the papers, the tutorial boxes with the player's own keys, the attack
  animations of the opening's people, the torch and the fists) is in this snapshot.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- The row of effect icons: a lasting effect, several effects at once, more than three rows, the same icons on the Stats
  window, and V for the full list.
- The Heart Chamber: the Heart of Lorkhan in its room, and the load of the chamber.
- A New Game through the opening to Seyda Neen, as checked for v0.0.65.
- The trip from Seyda Neen to Balmora several times, for the load stall.

## Known in this build

- Tribunal and Bloodmoon are not built yet: the merging reader and the layer keys are in, and the cells and rooms of
  Mournhold and Solstheim are being brought in through the same builder and stages as Vvardenfell.
- The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet
  (`ENDGAME-CHAMBER-COLLAPSE-63`).
- The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run.
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- From [v0.0.65](RELEASE-v0.0.65.md): the open entries of its Known list stand. Every other open entry is in the
  [bug register](../../BUGS.md); the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land
  and part has come.
