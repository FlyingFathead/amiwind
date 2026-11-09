# AmiWind v0.0.63-dev2 (in development)

_Last updated with AmiWind v0.0.63-dev2 (9 November 2026)._

Development snapshot, 9 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.63-dev1](RELEASE-v0.0.63-dev1.md); previous release: [v0.0.62: Stick To The Script](RELEASE-v0.0.62.md).

The second snapshot of v0.0.63. It carries fights between characters, followers and guards that take sides, the
opening on the prison ship and the Seyda Neen dock closer to the original, the original game's console commands, fire
pits and scripted turning objects, and a builder that bakes the player's view in one flow with the risky stages first.
605 of the 1,207 scripts run as scripts and 8 more are carried by the game's own code (599 in v0.0.63-dev1). The game
needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet; the in-game checklist at the end lists what to look at.

## New since v0.0.63-dev1

### Fights, followers and guards

- **Characters fight each other.** A script that starts combat between two characters sets both against each other, as
  in the original (`COMBAT-ACTOR-VS-ACTOR-62`).
- **Allies and guards join fights** as in the original: a guard or an ally of the attacked side takes part.
- **Followers side with the player**, and the followers and escorts of the scripts' packages move by the same follow
  behaviour as the player's companions.

### The opening

- A new game starts with the original's opening state: the character generation state, the ship guard's steps, the
  captain's hint box and the cloudy Bitter Coast weather (`CHARGENSTATE-START-VALUE-63`, `OPENING-SHIP-GUARD-STEPS-63`,
  `OPENING-CAPTAIN-HINT-SUBTITLE-63`, `OPENING-WEATHER-NOT-CLOUDY-63`).
- The dock guard keeps to his own post beside the census office door, and the prison ship's blocker is in the world
  (`INTRO-DOCK-GUARD-BLOCKS-DOOR-62`, `OPENING-SHIP-BLOCKER-NOT-CONVERTED-63`).
- The name, race and rest menus are opened by the scripts that open them in the original
  (`CENSUS-INTRO-SCRIPTS-62`).

### Scripts and the console

- **The original game's console commands**: the census of them, their short aliases and the stat family, usable on any
  reference with a target finder; `dbg help mw` lists them ([console commands](../../CONSOLE_COMMANDS_MORROWIND.md)).
- A placed object is bound to its record's final script, and the scripts carried by the game's own code are listed in
  the [MWScript tracker](../../MWSCRIPT_FEATURES.md) with a parity check.
- A dialogue result reads its rows in one block.

| State | Scripts |
| --- | ---: |
| Run as scripts | 605 of 1,207 (599 in v0.0.63-dev1) |
| Carried by the game's own code | 8 |
| Use a function the interpreter lacks | 29 |
| Belong to an add-on world not in the image yet | 431 |
| Named by nothing (they never run in the original either) | 134 |

### The world

- **Fire pits burn**: the fires of every frame of a world window are drawn.
- **Scripts turn the objects they name**, and moved or turned objects are kept in saved games (`WORLD-BUTTONS-62`).
- Every room's containers, items and creatures are counted in a census, and a check confirms that every container in a
  room can be aimed at (`ROOM-OBJECTS-MISSING-62`).

### The builder

- **The player's view is baked in one flow**: the torch bodies follow their own body, and fitting tries run on idle
  workers.
- **Risky stages first**: the player bodies are their own stage right after the census, with a pre-flight of the stored
  models, and the player-view stage runs before the image instead of inside the scene chain, so a failure there shows
  within minutes instead of late in the build.
- **Every NPC and creature model is kept as its own unit.** The actor library's NPC appearances and creature models,
  the arena fighters, each room resident's ground fit and the guard torch skip verdicts go into the unit cache the
  moment each one is finished, so a build that stops part way, or a change to one character, no longer bakes the whole
  actor library again (`NPC-LIBRARY-NO-UNIT-CACHE-63`). Every stored unit is read back at once: a unit the cache did
  not keep stops the stage with a `STORE FAILED` line, and the build's first minute stops on a cache folder it cannot
  write ([BUILD_CACHE](../../BUILD_CACHE.md)).
- The world stages count only the values an engine file gives them when they read a single define from it, so a
  change elsewhere in that file no longer rebuilds the world (`BUILD-ENGINE-SOURCE-KEY-BROAD-36`).
- Two stages that ran side by side are no longer both refused for reuse when a third stage wrote a file during their
  run: the files the stage traces attribute are settled first, earlier records refused only for that reason become
  reusable again, and the files two stages both write are listed and checked (`BUILD-SHARED-WRITES-UNATTRIBUTED-52`).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- A guard joining a fight in Balmora; a follower fighting beside the player.
- The opening: the ship guard's walk, the captain's hint, cloudy weather at Seyda Neen, the dock guard beside the census
  office door.
- The original's console commands on a target (`dbg help mw`).
- Fire pits burning outdoors; a scripted turning object, kept after a save and load.
- Everything on the [v0.0.63-dev1 checklist](RELEASE-v0.0.63-dev1.md#in-game-checklist-for-this-snapshot).

## Known in this build

- A player who becomes a werewolf is not drawn as the werewolf (`WEREWOLF-BODY-NOT-DRAWN-63`).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- The game image is still larger than the original game data (`IMAGE-BIGGER-THAN-ORIGINAL-62`).
- The Seyda Neen and Vivec town stages write the same shared files while running side by side, so the builder cannot
  reuse them and bakes both again in every build (`BUILD-SHARED-WRITES-UNATTRIBUTED-52`).
- From [v0.0.62](RELEASE-v0.0.62.md): pickpocketing and owned locks are not done, and the Heart Chamber may not load at
  32 MB Fast RAM.
