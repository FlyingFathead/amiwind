# AmiWind v0.0.66-dev3 (in development)

_Last updated with AmiWind v0.0.66-dev3 (14 November 2026)._

Development snapshot, 14 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev2](RELEASE-v0.0.66-dev2.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The third snapshot of v0.0.66, and it carries everything that [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md) holds. **The save
now holds the game's changes without the fixed limits that could refuse it or drop state.** The actors' rows, the
explored map, the script values, the made spells and items, the crime marks and the revealed places grow with the game up
to guards that sit above the game's own counts, a save is written only when every part of it went in, and two copies of
one item are kept apart. The road to Mournhold and Solstheim goes on in the builder: the selected expansions' files are
checked like the base game's before any stage, the seven expansion rooms the room stage refused are built or listed, every
table the build makes reads the expansions' data, and a build runs its new work first. This is not the arrival of Mournhold
or Solstheim: no finished Mournhold or Solstheim content is in this snapshot. The game needs 32 MB of Fast RAM, and the
emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet. The save in particular is checked by tests on the host; a round trip of a long game in the
emulator, with the load and save times on the 68040 preset and on the Raspberry Pi 4B, is still to be done.

## New since v0.0.66-dev2

### The save

The save is described in [the saved game plan](../../SAVEGAME_PLAN.md) and its measured size and cost in the
[saved game budget](../../performance/SAVE-BUDGET.md).

- **The actors' rows have no fixed cap.** The saved state of people and creatures (position, facing, health, the
  greeting counters) was kept in 256 rows for about 2,700 people; once full, the rest of a place's people were not saved.
  The rows are now kept on the world change list, which grows with the game, and are captured when an area is unloaded and at
  the save. A row is written only for an actor whose state differs from the game data: dead, fighting, following, hurt, or
  moved. The people of the Tribunal and Bloodmoon rooms are saved too, where the old form refused their place ids
  (`SAVE-STATE-FIXED-CAPS-66`, `SAVE-ACTOR-ROWS-EXPANSION-ROOMS-66`).
- **The explored map has a room of its own in the save and never stops it.** The map's squares and rooms are a separate
  section; the part of the save that holds the actors' other lists is a setting (64 KB by default) that grows before a save
  is refused, and the map's land is never cut. More than 256 rooms are remembered.
- **Saves are all or nothing, and say what failed.** A save is written only when every part reported success; the
  previous save stays when one does not, and the message names the part of the game state that could not be kept
  (`SAVE-EXPORT-FAILURE-ACCEPTED-65`).
- **Script values come back by name.** The values of a scripted object's variables are saved under the variable's name
  with a signature of the script's layout, so a rebuilt script table in another order still finds them, and a changed
  layout is reported instead of mixed up. The script values of items are saved too, with the items the player wears and
  those that containers and actors hold (`SAVE-SCRIPT-ROW-HINT-ONLY-65`, `SAVE-ITEM-SCRIPT-LOCALS-66`).
- **Two copies of one item stay two.** Two swords with different condition or charge were saved as one row; each copy
  now keeps its own, and the worn one is still the worn one after a load. A worn copy's script values belong to that copy
  (`SAVE-ITEM-INSTANCES-ONE-PER-KIND-66`).
- **Bounds above the game.** The map markers may reach 4,096 (the setting's default allowance stays 256), the script
  values 65,536, the saved actor changes 32,768, the made spells, enchanted items, potions and filled soul gems 1,024
  each, the crime marks 1,024 witnesses, the revealed places 1,024 and the explored land 8,192 cells; the weather rows a
  script may set are 32. Each is a guard sized above the counts of the game with both expansions, not a limit play
  reaches (`SAVE-MADE-RECORDS-64-CAP-66`, `SAVE-ACTOR-ROWS-BOUND-UNDER-GAME-66`, `SAVE-LOCALS-BOUND-UNDER-GAME-66`,
  `SAVE-CRIME-MARKS-32-ROWS-66`, `SAVE-REVEALED-PLACES-128-CAP-66`). Before, the 33rd witness of a crime took a bystander's
  row, a script could reveal no more than 128 places, and a long game of brewing passed the 64 made items.
- **A save asked for inside a script step waits for it.** A save requested from the menu or the console while a script
  step runs is queued ("Save queued") and written when the step ends, so no half-done step is saved
  (`SAVE-INSIDE-SCRIPT-STEP-66`).
- **Measured:** a synthetic long game (about 7,700 changed objects, 3,000 changed actors, 2,800 scripted objects, 242
  containers, 2,489 journal entries) saves to about 985 KB; on the host the save takes 45 ms and the load 120 ms. The times
  on the Amiga presets are not measured yet.

### Tribunal and Bloodmoon in the build

- **The selected expansions' files are checked like the base game files.** With an expansion selected (both by
  default), its master and archive (`Tribunal.esm`, `Tribunal.bsa`, `Bloodmoon.esm`, `Bloodmoon.bsa`) are required and
  their sizes and SHA-256 are compared with the known Game of the Year files before any stage; a missing or different
  file stops the build and names the file and what was expected. An expansion that is left out (`--no-dlc`) is not
  required (`BUILD-EXPANSION-INPUTS-UNCHECKED-66`).
- **Every table the build makes reads the expansions' data.** The tables for travel, magic, container rooms, the
  reference file list and the dialogue choices read the selected expansions too, and a check lists the tables that still
  read the base game alone; a table of tables in the docs index shows each one. With the base game alone each table is as
  it was (`EXPANSION-BASE-ONLY-TABLES-66`).
- **The seven expansion rooms the room stage refused are handled.** The hot oil of Sotha Sil's works is drawn and acts as a
  molten pool, the Dome of Sotha Sil leaves out an effect model that has no drawn surface, and four cells that are empty in
  the game files are listed and not converted.
- **The CHIM world's source receipt lists the merged expansion master by its name.** Before, the CHIM world stopped on
  the merged master, which lives outside the data folder.
- **Bloodmoon's werewolf robe is a known gap.** The player parts stage no longer stops on it; the form has no player model
  yet (see "Known in this build").

### The debug teleport

- **`dbg tp` chooses a category.** The list shows All, Exteriors, Interiors or Beings. Beings lists people and creatures
  by name, and choosing one puts the player next to it on a free, walkable spot, facing it. A list too large to read whole
  is paged, and the list checks the memory it needs before it is read whole (`DBG-TP-BEINGS-66`).

### The builder

- **New work runs first in a build.** Stages with no history (new content) start before the known ones, and inside a
  unit stage the units with no recorded time go out first, so a failure in new content shows early. The resource plan
  counts the units each rebuilt stage bakes again and takes its time from them, not from a full rebuild
  ([build profile](../../BUILD_PROFILE.md), "New work first" and "Resource plan"; `BUILD-NEW-WORK-NOT-FIRST-66`).
- **A stalled build says so.** The builder writes its own live numbers from its first second (the phase, the cores in use
  against the cores planned, the time since the last progress) and raises a stall alert, which the build monitor shows
  first when no build is running. The master builder flags a step that uses under half its planned cores and stops a
  stalled step by default, naming what it waited on and the command to resume.
- **A failed build writes its failure details.** A failure page names the stage, the error, the traceback, the last lines
  of the log, what was not converted and the command to build again from the run; the build prints it, and the monitor
  links it as "See failure details" under the progress bar (`BUILD-FAILURE-NO-DETAILS-66`).
- **A build start that is refused says why.** A byte-order mark in the build options file is removed, or the file is
  refused by name; before, such a start stopped without a reason (`BUILD-FLAGS-MARK-SILENT-REFUSAL-66`).
- **Public texts name who raised an issue by role and date only.** Comments, test data and docs follow it, and a public
  test fails when the tree names where a report came through.

### From v0.0.66-dev2

- Everything of [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md) is in this snapshot: the expansions' data selected by default with
  keys that know it, the map, the characters casting spells, bows, fleeing and the weapon choice, the dead staying dead,
  the towns' scripts, the lighter prison ship hold and the builder's actor checks; the journal's expansion entries, the
  86 large expansion rooms, the exterior plan and the actor library's expansion creatures are in dev2's notes too.

### Performance

Checked by tests; the frame rate on the Raspberry Pi 4B is still to be measured on this snapshot. All figures, with what
measured them and what is not measured yet, are on the [v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

- **The saved game's size and cost** are measured on the host for a synthetic long game (the figures above); the
  actors' changed records, about 55 % of the file, are the part a later pass can make sparser (about 21 % of the file).
- **Builds**: new work first means a failure in new content shows in the first minutes instead of after the long stages.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Save and load a game after a long walk: the people you hurt or killed are as you left them, a companion still follows,
  and a message appears if a part cannot be saved.
- Two weapons of one kind with different condition, one worn: save, load, and see that both and the worn one are back.
- A save asked for during a speech or a script message box: it is written when the step ends.
- `dbg tp`: the All, Exteriors, Interiors and Beings choices, and teleporting to a person by name.
- Everything on dev2's checklist that has not been played yet (readied magic, fights with casters and archers, the map,
  the prison ship's hold, the Heart Chamber, a New Game through the opening to Seyda Neen and Balmora).

## Known in this build

- **The save's fixed limits are raised and made guards, but the whole is not proven in play.** What is left
  (`SAVE-STATE-FIXED-CAPS-66`): a round trip of a long game in the emulator at 32 MB Fast, with the load and save times on
  the 68040 preset and the Raspberry Pi 4B, is not done; the saved record of each changed actor is written whole (a
  sparser form would cut about a fifth of the file); a hurt, calm person saved and loaded is to be checked in play, since
  the ledger now holds that state; the flora's slot table (4,096) is checked against the base game (2,896) and its count
  with the expansions is not yet known; the block that holds the actors' other lists grows to 256 KB before a save is
  refused; and the ownership of an item stays by kind, not by copy.
- Tribunal and Bloodmoon data is selected by default, but the cells and rooms of Mournhold and Solstheim are not played
  in this snapshot: there is no finished Mournhold or Solstheim content.
- **Bloodmoon's werewolf form has no player model yet** (`PLAYER-WEREWOLF-ROBE-NOT-BAKED-66`): the form is not in the
  game, and its robe is left out of the player parts.
- The new weapon choice, fleeing and the outdoor bodies are checked by tests, not yet in play. Still open in the actors'
  mechanics: the crime audit, an NPC running while it wanders, potions and magic items as a fighter's best action.
- The game can stop in an ancestral tomb.
- The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet
  (`ENDGAME-CHAMBER-COLLAPSE-63`).
- The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run.
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- From [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md), [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and
  [v0.0.65](RELEASE-v0.0.65.md): the open entries of their Known lists stand. Every other open entry is in the
  [bug register](../../BUGS.md); the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and
  part has come.
