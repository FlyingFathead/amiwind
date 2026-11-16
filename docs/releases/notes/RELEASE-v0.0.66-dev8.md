# AmiWind v0.0.66-dev8 (in development)

_Last updated with AmiWind v0.0.66-dev8 (15 November 2026)._

Development snapshot, 15 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev7](RELEASE-v0.0.66-dev7.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The eighth snapshot of v0.0.66, and it carries everything that [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md) holds. **The game
itself is the same as in v0.0.66-dev7 apart from the version.** What is new is in the builder and in the documents: the
reuse check plans the same commands as the build, the check's whole output is kept, and two study pages are added. This
is not the arrival of Mournhold or Solstheim: no finished Mournhold or Solstheim content is in this snapshot. The game
needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.66-dev7

- **The reuse check plans the same commands as the build**
  ([BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64](../../bugs/BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64.md)): the build binds the
  exterior checklist to its world terrain, world scenery and world flora commands (and the terrain folder to the image
  command) before it prepares the stages; the check built the same commands without that step, so against every earlier
  build it read the three stages as changed and counted the 2,064 and 1,931 units their caches store as baking again. The
  check now binds the steps as the build does. This is fixed in source and covered by tests; it is to be confirmed by this
  snapshot's own unit check, which runs without the allowances for the world scenery and world flora stages. The register
  entry stays open until that check has run.
- **The check's whole output is kept** in a file beside its result (`RUN.check.log`); the refusal and the result carry
  only its last lines, which had lost the plan line of a stopped stage.
- **The opening journey passed all nine steps on the v0.0.66-dev7 image** (42 of 42 checks): the papers, the back room,
  the courtyard, Fargoth's ring and Sellus Gravius, the release, the kill and the interiors, the spell and the fight (the
  fighter took health), the game's own quicksave, and a door after the load. The four journey faults of earlier
  snapshots are fixed (`JOURNEY-AIM-RETRY-YAW-66` and `JOURNEY-STEP7-FIGHT-UNREACHABLE-66` in v0.0.66-dev6,
  `JOURNEY-PART-B-SAVE-NOT-CARRIED-66` and `JOURNEY-WALK-DIALOGUE-DESYNC-66` in v0.0.66-dev3).
- **Two study pages**, feasibility notes written on 13 November 2026 and merged now. Neither claims anything works: the game
  has not been run on either machine.
  - [AmiWind on a PiStorm-equipped Amiga 500](../../PISTORM_RTG_STUDY.md) traces today's display path in the code (the
    chunky-to-planar copy into Chip RAM), sketches a selectable RTG display backend beside AGA, lists the likely blockers
    for the current build under AGA-STORM, and names the counters for a like-for-like comparison. The share of a frame the
    conversion takes is measured on the emulator (well under 1 %) and estimated for the Raspberry Pi 4B (about 10 % at
    most).
  - [The THEA1200 as a target](../../THEA1200_STUDY.md) sets down what the announced machine's makers say it offers, the
    open questions (how the game would start, the emulated machine's settings, the speed) and the order of tests once a
    unit is available.

### From v0.0.66-dev7

- Everything of [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md) is in this snapshot: the crab meat taken in the opening journey,
  the sound loading of area loads timed on the new disk layout, and the memory the disk buffers cost; with it everything
  of [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md), [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md) and
  [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md).

### Performance

No new measurement in this snapshot. The figures of [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md) stand; the frame rate on the
Raspberry Pi 4B is still to be measured on a snapshot. See the
[v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The game is the same as v0.0.66-dev7, so the checklist stands:

- A New Game: on the ship and through the clerk's registration, fighting and magic are off until the papers are taken
  from the census office table; after the papers both are on (seen in play on the v0.0.66-dev5 image).
- In the census back room, aim at the crab meat on the silver plate: E takes the crab meat, not the plate (seen in the
  journey on the v0.0.66-dev6 image).
- Travel to Seyda Neen, Balmora and Vivec: the sound loading is measured below the v0.0.66-dev1 figure at Seyda Neen and
  Vivec, and at Balmora one load below it and one just above it; the whole load time is not compared.
- Everything on dev4's checklist that has not been played yet: the papers, the hall guard's door, the dagger in the back
  room, Fargoth's ring in the courtyard barrel, Sellus Gravius' topics and the release, and `dbg tp` to a town typed while
  an area is still loading.

## Known in this build

- **The reuse check's stop on the world scenery and flora stages stays listed until this snapshot's check has run**
  ([BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64](../../bugs/BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64.md)): both causes are
  fixed in source; the check of this snapshot is the first to run with them and without the per-stage allowances, and the
  entry is closed only after it has passed.
- **A load can stop in the emulator** ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)):
  the trip from Seyda Neen to Balmora sometimes stalls on the loading screen. The opening journey on foot stopped at the
  census office's street door (113833) on the v0.0.66-dev4 image twice and on the v0.0.66-dev6 image once, and went through
  on the v0.0.66-dev5 image. It did not stop the v0.0.66-dev7 journey, and was seen again in the v0.0.66-dev7 delivery's
  area hops (the teleport from Vivec to the arena pit; the hops passed when run again). The cause is not found.
- **Coming back out of the census office after a crime can leave the player stuck inside a guard**
  (`DOOR-ARRIVAL-INSIDE-ACTOR-66`): after a kill on the Seyda Neen street the guard walks to the census
  office's street door, and the player who comes back out arrives inside him; the game then reports the player stuck
  every frame (seen in the opening journey on the v0.0.66-dev5 and v0.0.66-dev7 images). Whether a player can walk out is
  not yet seen.
- **The image step's room resident step takes about two minutes on one core when every room is cached**
  (`IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66`): seen in the builds of v0.0.66-dev4 and v0.0.66-dev5; the output is right.
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
- From [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md), [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md),
  [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md), [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md),
  [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md), [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md),
  [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and [v0.0.65](RELEASE-v0.0.65.md): the open entries of their Known lists
  stand. Every other open entry is in the [bug register](../../BUGS.md); the
  [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.
