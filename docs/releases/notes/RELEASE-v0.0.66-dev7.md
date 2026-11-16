# AmiWind v0.0.66-dev7 (in development)

_Last updated with AmiWind v0.0.66-dev7 (15 November 2026)._

Development snapshot, 15 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev6](RELEASE-v0.0.66-dev6.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The seventh snapshot of v0.0.66, and it carries everything that [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md) holds. **The game
itself is the same as in v0.0.66-dev6 and v0.0.66-dev5 apart from the version.** What is new is what was seen in play and
measured on the v0.0.66-dev6 build, and the bug register and the known list brought up to date with it: the census
office's crab meat was taken in the journey, the sound loading of three area loads was timed on the new disk layout, and
the memory the disk buffers cost was measured. This is not the arrival of Mournhold or Solstheim: no finished Mournhold or
Solstheim content is in this snapshot. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have
it.

## Seen in play and measured on the v0.0.66-dev6 build

- **The crab meat on the census office's plate is taken, not the plate**
  (`CENSUS-CRAB-PLATE-FOCUS-66`): in the opening journey's part A, step 2, on the v0.0.66-dev6 image, the use key took the
  crab meat (`ingred_crab_meat_01`) and the Silverware Plate (`misc_imp_silverware_plate_01`) under it was not taken. The
  fix is the one of v0.0.66-dev5; the register entry is fixed in v0.0.66-dev5.
- **The sound loading of an area load is fast again** (`IMAGE-LOADS-SLOWER-66`): measured on the v0.0.66-dev6 image, which
  has the disk layout of v0.0.66-dev5, the sound stage of a map load took 59 ms at Seyda Neen (139 ms on v0.0.66-dev1,
  480 ms on v0.0.66-dev2), 118 and 147 ms at Balmora after a teleport (139 and 777 ms), and 147 and 165 ms at Vivec (306
  and 1,078 ms): below the v0.0.66-dev1 figure at Seyda Neen (59 against 139 ms) and Vivec (147 and 165 against 306 ms);
  at Balmora one load below (118 ms) and one just above (147 ms) its 139 ms; all three far below the v0.0.66-dev2
  figures. This is the sound stage of the load, not the whole load.
  The register entry is fixed in v0.0.66-dev5.
- **What the disk buffers cost** (`BUILD-HDF-BUFFERS-32`): the 150 buffers of the boot partition and 40 of the world
  partition take 72 to 73 KiB of Fast RAM, measured as free memory after a load against the v0.0.66-dev4 image (Balmora
  2,010 to 1,938 KiB, Vivec 1,396 to 1,323 KiB at 32 MB Fast). The register entry is fixed in v0.0.66-dev5.
- The figures, with what measured them, are on the [v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

## New since v0.0.66-dev6

The game, the builder and the tests are those of v0.0.66-dev6. New in this snapshot: the version, the emulator presets,
the performance page's figures above, the bug register and these notes.

### From v0.0.66-dev6

- Everything of [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md) is in this snapshot: the reuse check's change for the world
  scenery and flora stages, the play journey's aim from the eye, its crab meat step and its fight step with a fighter at
  the player's feet, and the roadmap's automated playthroughs; and with it everything of
  [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md) and [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md).

### Performance

The sound loading and the memory of the disk buffers are measured, above. The frame rate on the Raspberry Pi 4B is still
to be measured on a snapshot; the whole area load time is compared only for its sound stage. See the
[v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The game is the same as v0.0.66-dev6, so the checklist stands:

- A New Game: on the ship and through the clerk's registration, fighting and magic are off until the papers are taken
  from the census office table; after the papers both are on (seen in play on the v0.0.66-dev5 image).
- In the census back room, aim at the crab meat on the silver plate: E takes the crab meat, not the plate (seen in the
  journey on the v0.0.66-dev6 image).
- Travel to Seyda Neen, Balmora and Vivec: the sound loading is measured as no slower than in v0.0.66-dev1; the whole
  load time is not compared.
- Everything on dev4's checklist that has not been played yet: the papers, the hall guard's door, the dagger in the back
  room, Fargoth's ring in the courtyard barrel, Sellus Gravius' topics and the release, and `dbg tp` to a town typed while
  an area is still loading.

## Known in this build

- **The reuse check still stops the world scenery and flora stages**
  ([BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64](../../bugs/BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64.md)): the region count of
  v0.0.66-dev6 is in, but the check of that snapshot still stopped both stages with the same counts (2,064 and 1,931),
  because its stage plan treats them as stages that run while the build takes both from the earlier build. A second cause
  is open.
- **A load can stop in the emulator** ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)):
  the trip from Seyda Neen to Balmora sometimes stalls on the loading screen. The opening journey on foot stopped at the
  census office's street door (113833) on the v0.0.66-dev4 image twice and on the v0.0.66-dev6 image once, and went through
  on the v0.0.66-dev5 image. The cause is not found.
- **The journey's step 7 fight and its journey run** (`JOURNEY-STEP7-FIGHT-UNREACHABLE-66`, `JOURNEY-AIM-RETRY-YAW-66`):
  the journey on the v0.0.66-dev6 image stopped in step 6 at the load above, so step 7's fighter at the player's feet and
  the later steps did not run; both entries stay open until a journey passes them.- **The image step's room resident step takes about two minutes on one core when every room is cached**
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
- From [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md), [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md),
  [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md), [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md),
  [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md), [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and
  [v0.0.65](RELEASE-v0.0.65.md): the open entries of their Known lists stand, but for the three this snapshot has seen in
  play or measured (the crab meat, the sound loads and the buffers' memory). Every other open entry is in the
  [bug register](../../BUGS.md); the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and
  part has come.
