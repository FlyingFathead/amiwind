# AmiWind v0.0.66-dev4 (in development)

_Last updated with AmiWind v0.0.66-dev4 (15 November 2026)._

Development snapshot, 15 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev3](RELEASE-v0.0.66-dev3.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The fourth snapshot of v0.0.66, and it carries everything that [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md) holds. **Scripted
doors that opened only once now open every time their script allows**: the two doors of the census captain's wing let
the player out and back in after the opening, as in the original. **The opening is checked on foot**: the play journey
that checks the opening after a build now walks it as a player plays it, from the ship through the census office to the
release and on, waiting for the game at every step and stopping at the first wrong turn. This is not the arrival of
Mournhold or Solstheim: no finished Mournhold or Solstheim content is in this snapshot. The game needs 32 MB of Fast RAM,
and the emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. The scripted doors fix has not been seen
in play on a build yet; the journey on foot was played on the v0.0.66-dev2 image while it was written, and what it found
there is in the register (see "Known in this build").

## New since v0.0.66-dev3

### Scripted doors and objects

- **A scripted object takes the player's use only while its script reads it.** In the original a script takes the
  player's use of its object only while it keeps reading `OnActivate`; once it stops, and after its own `Activate`, the
  object works as a plain one again. The engine took the use of every object whose script mentioned `OnActivate` at
  all, so a script that stopped reading it after the first use swallowed every later use, also after the player left
  and came back. The census captain's exit door to Seyda Neen and the courtyard door into his room opened once and then
  did nothing; they now open every time. The rule holds for every scripted door, item and actor, and for uses from the
  console ([MWScript bytecode](../../MWSCRIPT_BYTECODE.md); `CAPTAIN-EXIT-DOOR-DEAD-AFTER-REENTRY-66`).

### The opening journey on foot

- **The play journey walks the opening as a player plays it** ([gameplay journeys](../../GAME_RECORDER.md#gameplay-journeys)):
  the ship, the pier walked up to the census office door, the papers taken off the table, the hall guard's door, the
  iron dagger from the back room, the courtyard and Keley's ring, Sellus Gravius' topics chosen by name, the release,
  and after it the captain's room left by both its doors. Each step waits for the game (a point reached, a window open,
  a map running) and turns the view to what it uses until the game's own use focus names it; the first wrong turn stops
  the part, names where the player stands, and every check after it is reported as not reached.
- It replaces a walk that counted key presses and lost its way in the census office
  (`JOURNEY-WALK-DIALOGUE-DESYNC-66`), and its second part now loads the first part's quicksave through the Load game
  window (`JOURNEY-PART-B-SAVE-NOT-CARRIED-66`).

### Late in v0.0.66-dev3

Two changes went into the v0.0.66-dev3 build after its notes were written:

- **A teleport typed during a load runs on arrival.** `dbg tp` or `dbg scene` typed while an area is still loading is
  held and runs once the load has arrived. Before, a town name did nothing, a place said no map held the point, and a
  room printed its name and stayed (`DBG-TP-DURING-LOAD-66`).
- **The image step's actor check counts the game data's empty rooms the way the room stage records them.** The room
  stage lists cells with no scenery and no door leading in (four in Tribunal) as empty; the actor spec check now sets
  aside an expansion's people in them under that list. The v0.0.66-dev3 build first stopped on the one person of such a
  Mournhold room (`BUILD-ACTOR-SPEC-EMPTY-ROOMS-66`).

### From v0.0.66-dev3

- Everything of [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md) is in this snapshot: the save without the fixed limits that could
  refuse it or drop state, the selected expansions' files checked before any stage, every table reading the expansions'
  data, the seven expansion rooms the room stage refused built or listed, the builder's new work first with its stall
  alert and failure page, and `dbg tp` by category and to people and creatures by name; and with it everything of
  [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md).

### Performance

Checked by tests; the frame rate on the Raspberry Pi 4B is still to be measured on this snapshot. All figures, with what
measured them and what is not measured yet, are on the [v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

- **Area loads** read their sounds more slowly since v0.0.66-dev2 (see "Known in this build"); the fix is in the image
  step's layout.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- After the release, go back into Sellus Gravius' room by the street door, leave by the courtyard door, come in again
  from the courtyard and leave by the exit door: every door opens, every time.
- A New Game through the census office on foot: the papers, the hall guard's door, the dagger in the back room, Keley's
  ring in the courtyard barrel, Sellus Gravius' topics and the release.
- `dbg tp` to a town typed while an area is still loading: the teleport happens once the area has arrived.
- Everything on dev3's checklist that has not been played yet (the save after a long walk, two weapons of one kind,
  a save during a speech, `dbg tp` by category).

## Known in this build

- **Fighting is allowed before the release papers** (`OPENING-FIGHTING-ON-BEFORE-PAPERS-66`): in the opening, fighting is
  already switched on before the papers are taken; the original keeps it off from the ship until the papers.
- **The crab meat on the census back-room table** (`CENSUS-CRAB-PLATE-FOCUS-66`): aimed at it, the use key goes to the
  silver plate under it, so E takes the plate, a theft, instead of the crab meat.
- **The census courtyard arrival got stuck once** (`COURTYARD-ARRIVAL-STUCK-66`): in one of two arrivals from the back
  room the player came into the courtyard stuck in solid and was moved out twice.
- **The console's item count** (`CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66`): `player->getitemcount` answers "no such item
  id" for an item the player carries when no script and no actor names it (the census iron dagger).
- **Area loads read their sounds more slowly since v0.0.66-dev2**
  ([IMAGE-LOADS-SLOWER-66](../../bugs/IMAGE-LOADS-SLOWER-66.md)): the image step places the sound folder where no sound
  lookup fits the boot partition's buffers, so every sound reads its name lookup from disk, 0.3 to 0.8 s more per area
  load at 32 MB Fast; the fix is in the image step's folder order and buffers.
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
- From [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md), [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md),
  [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and [v0.0.65](RELEASE-v0.0.65.md): the open entries of their Known lists
  stand. Every other open entry is in the [bug register](../../BUGS.md); the
  [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.
