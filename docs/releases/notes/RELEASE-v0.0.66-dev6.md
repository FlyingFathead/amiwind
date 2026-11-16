# AmiWind v0.0.66-dev6 (in development)

_Last updated with AmiWind v0.0.66-dev6 (15 November 2026)._

Development snapshot, 15 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev5](RELEASE-v0.0.66-dev5.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The sixth snapshot of v0.0.66, and it carries everything that [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md) holds. **The game
itself is the same as in v0.0.66-dev5 apart from the version.** What is new is in the builder, the play journey and the
roadmap: the build's reuse check counts the regions a world scenery or flora stage converts (it still stopped both stages
on this snapshot's own check, so that stop stays open), the play journey aims from where the player stands and checks the
crab meat on the census office's silver plate, and the roadmap names automated playthroughs. This is not the arrival of Mournhold or Solstheim: no finished Mournhold or
Solstheim content is in this snapshot. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have
it.

## Seen in play on the v0.0.66-dev5 image

- **The opening held its controls until the papers were taken**
  (`OPENING-FIGHTING-ON-BEFORE-PAPERS-66`): the opening journey's first step passed all six of its checks on the
  v0.0.66-dev5 image. On the ship and before the papers the fighting switch reads on in the way the original's scripts
  leave it (both of those probes read 0 on the v0.0.66-dev4 image), the papers are not taken before the census office and
  taken after it, and after the papers fighting and magic read off. The fix is the one of v0.0.66-dev5; it is no longer
  only checked by tests.

## New since v0.0.66-dev5

### The builder

- **The reuse check counts the regions a world scenery or flora stage converts.** The check that decides whether a
  stage's finished units can be reused counted the units stored under earlier keys as units the stage would have to bake,
  and stopped the build when they were many. Every region of those two stages is a CHIM cell and neither stage bakes a
  unit, so the stop now counts the regions a stage converts (`BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64`; covered by
  tests). This snapshot's own check still stopped both stages with the same counts: the check's stage plan treats them
  as stages that run, while the build takes both from the earlier build. That second cause is still open, and this
  snapshot was built with both stages allowed to run, as the earlier snapshots were; both were taken from the earlier
  build.

### The play journey

- **Every aim comes from where the eye is when the aim is made.** An aim reads the eye again before each try and turns
  again when it has moved since the turn, the nudges are centred on the aim from that eye, and a point too near on the
  floor plane, or needing too steep a look, first has the player step back
  ([gameplay journeys](../../GAME_RECORDER.md#gameplay-journeys); `JOURNEY-AIM-RETRY-YAW-66`).
- **A crab meat step.** In the census back room the journey aims at the crab meat on the Silverware Plate
  (`misc_imp_silverware_plate_01`), checks that the game's focus names the crab meat (`ingred_crab_meat_01`) and not the
  plate, takes it with the use key, and checks that the crab meat is counted and the plate is not (`CENSUS-CRAB-PLATE-FOCUS-66`).
- **Step 7's fight has a fighter at the player's feet.** The fighter is a copy of the nearest resident put at the player's
  feet first, since the nearest resident by itself can stand behind a wall, cannot reach the player and flees
  (`JOURNEY-STEP7-FIGHT-UNREACHABLE-66`).

### The roadmap

- The [roadmap](../../ROADMAP.md) names automated playthroughs in the emulator's fast mode, as later work and not
  scheduled.

### From v0.0.66-dev5

- Everything of [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md) is in this snapshot: the opening's control switches, the use key
  going to what the view meets first, the disk buffers for the sound loading of an area load, and the journey's fixes;
  and with it everything of [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md).

### Performance

Checked by tests; the frame rate on the Raspberry Pi 4B is still to be measured on this snapshot. All figures, with what
measured them and what is not measured yet, are on the [v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).
The builder's change above removes a stop, not a cost: it does not change how long a stage takes.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The game is the same as v0.0.66-dev5, so the checklist of that snapshot stands:

- A New Game: on the ship and through the clerk's registration, fighting and magic are off until the papers are taken
  from the census office table; after the papers both are on (seen in play on the v0.0.66-dev5 image).
- In the census back room, aim at the crab meat on the silver plate: E takes the crab meat, not the plate (the journey of
  this snapshot checks it).
- Travel to Seyda Neen, Balmora and Vivec: the loads are no slower than in v0.0.66-dev1 (not measured yet).
- Everything on dev4's checklist that has not been played yet: the papers, the hall guard's door, the dagger in the back
  room, Fargoth's ring in the courtyard barrel, Sellus Gravius' topics and the release, and `dbg tp` to a town typed while
  an area is still loading.

## Known in this build

- **The load times of the area loads are not measured yet on the new disk buffers**
  ([IMAGE-LOADS-SLOWER-66](../../bugs/IMAGE-LOADS-SLOWER-66.md),
  [BUILD-HDF-BUFFERS-32](../../bugs/BUILD-HDF-BUFFERS-32.md)): the image step of v0.0.66-dev5 relinked the name lookups
  (86 of 4,559 chains on the program partition, the median lookup from 73 to 25 header blocks) and gave the partitions
  150 and 40 buffers; both entries stay open until the loads are timed in play.
- **The crab meat's plate** (`CENSUS-CRAB-PLATE-FOCUS-66`): the use key's fix is checked by tests; the journey's new crab
  meat step is what shows it in play, and has not run yet.
- **The journey's aim retry and step 7's fight** (`JOURNEY-AIM-RETRY-YAW-66`, `JOURNEY-STEP7-FIGHT-UNREACHABLE-66`) stay
  open until a journey passes them.
- **The image step's room resident step takes about two minutes on one core when every room is cached**
  (`IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66`): seen in the builds of v0.0.66-dev4 and v0.0.66-dev5; the output is right.
- **A load can stop in the emulator** ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)):
  the trip from Seyda Neen to Balmora sometimes stalls on the loading screen, and the v0.0.66-dev4 opening journey on
  foot stopped twice, once at the census office's street door right after its kill and once in the Load game window. A
  second run of the same journey on the same image went through. The cause is not found.
- **The census courtyard arrival got stuck once** (`COURTYARD-ARRIVAL-STUCK-66`): in one of two arrivals from the back
  room the player came into the courtyard stuck in solid and was moved out twice.
- **The console's item count** (`CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66`): `player->getitemcount` answers "no such item
  id" for an item the player carries when no script and no actor names it (the census iron dagger).
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
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- From [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md), [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md),
  [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md), [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md),
  [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and [v0.0.65](RELEASE-v0.0.65.md): the open entries of their Known lists
  stand, but for the one this snapshot has seen in play (fighting before the papers). Every other open entry is in the
  [bug register](../../BUGS.md); the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and
  part has come.
