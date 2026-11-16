# AmiWind v0.0.66-dev9 (in development)

_Last updated with AmiWind v0.0.66-dev9 (15 November 2026)._

Development snapshot, 15 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev8](RELEASE-v0.0.66-dev8.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The ninth snapshot of v0.0.66, and it carries everything that [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md) holds. **The game
changes for the first time since v0.0.66-dev5:** the player no longer ends inside an actor at a door's or a teleport's
arrival point. The rest is in the testing tools, the builder's check and the register, and a correction of what the
earlier notes said about the opening journey's stops. This is not the arrival of Mournhold or Solstheim: no finished
Mournhold or Solstheim content is in this snapshot. The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it.

## New since v0.0.66-dev8

- **The player no longer ends inside an actor at a door's or a teleport's arrival point**
  (`DOOR-ARRIVAL-INSIDE-ACTOR-66`): two overlapping bodies may now move apart, the search that frees a stuck player leaves
  bodies out, and an actor that joins on the arrival point steps the player once to a clear spot beside it. Before the
  fix, a player who arrived inside the guard could not walk out (a test with the measured boxes). This is fixed in source
  and covered by tests; it is to be confirmed by this snapshot's opening journey, and the entry stays open until then.
- **A correction to the earlier notes about the opening journey.** The journey's stops at the census street door on the
  v0.0.66-dev4 image (twice) and on the v0.0.66-dev6 image were not the load hang
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)). The game was running: the body of
  the killed guard lay in front of the door, or a message box took the key. The v0.0.66-dev8 journey stopped the same way
  in its step 6. Only the stop in the v0.0.66-dev7 delivery's area hops (the teleport from Vivec to the arena pit)
  matches the load hang. The notes of dev6, dev7 and dev8 said otherwise and are left as they were; this is what is known
  now.
- **Testing tools.** The stall examination reads the running game correctly: it had read a running game as a missing task
  or as waiting on a file (`STALL-PROBE-RUNNING-GAME-66`, fixed in v0.0.66-dev9). The journey's door aim now refuses a door
  whose use goes to an actor, and answers a message box first (`JOURNEY-DOOR-USE-GOES-TO-ACTOR-66`, fixed in
  v0.0.66-dev9). The journey's step 6 kills a resident who stands away from the door, not the nearest one
  (`JOURNEY-STEP6-VICTIM-NEAREST-66`; fixed in source, to be confirmed by this snapshot's journey). A repeat session for
  one area load was added (`tests/sessions/load_repeat_hops.txt`).
- **The builder's reuse check on the world scenery and flora stages** is fixed since v0.0.66-dev8
  ([BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64](../../bugs/BUILD-REUSE-STOP-COUNTS-STORED-GROUP-64.md)): the dev8 unit check
  passed those stages without any allowance for them.
- **Register entries added:** the reuse check runs about six minutes on one core and twice before every build
  (`BUILD-CHECK-ONE-CORE-66`), and in Vivec the server's entity update overflows the client's packet every frame
  (`NET-VIVEC-ENTITY-PACKET-OVERFLOW-66`). Related to the door arrival and still open: wandering residents do not keep
  away from doors as in the original game (`WANDER-DOOR-RULE-66`).

### From v0.0.66-dev8

- Everything of [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md) is in this snapshot: the reuse check that plans the same commands
  as the build, the check's whole output kept beside its result, the opening journey that passed all nine steps on the
  dev7 image, and the two study pages ([AmiWind on a PiStorm-equipped Amiga 500](../../PISTORM_RTG_STUDY.md) and
  [the THEA1200 as a target](../../THEA1200_STUDY.md)); with it everything of
  [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md), [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md),
  [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md) and [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md).

### Performance

No new measurement in this snapshot. The figures of [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md) stand; the frame rate on the
Raspberry Pi 4B is still to be measured on a snapshot. See the
[v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The checklist of [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md) stands, with one addition:

- Leave the census office by its street door while the guard stands near it: the player arrives clear of him and can
  walk away (the fix is in source and not yet seen in a build).
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

- **A load can stop in the emulator** ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)):
  the trip from Seyda Neen to Balmora sometimes stalls on the loading screen. There is one real sighting so far: the
  v0.0.66-dev7 delivery's area hops stopped at the teleport from Vivec to the arena pit (the hops passed when run again).
  The earlier journey stops at the census street door are not this hang (see the correction above). The cause is not
  found.
- **Coming back out of the census office onto the street could leave the player stuck inside a guard who had walked to
  the door**
  (`DOOR-ARRIVAL-INSIDE-ACTOR-66`): fixed in source in this snapshot and covered by tests; the entry stays open until the
  opening journey shows the player walking out.
- **Wandering residents do not keep away from doors as in the original game** (`WANDER-DOOR-RULE-66`): a wanderer can stop
  at a destination right by a door and stand there.
- **The opening journey's step 6** (`JOURNEY-STEP6-VICTIM-NEAREST-66`) is changed in source and not yet run on a build.
- **The reuse check runs about six minutes on one core, twice before every build** (`BUILD-CHECK-ONE-CORE-66`).
- **In Vivec the server's entity update overflows the client's packet every frame**
  (`NET-VIVEC-ENTITY-PACKET-OVERFLOW-66`).
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
- From [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md), [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md),
  [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md), [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md),
  [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md), [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md),
  [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md), [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and
  [v0.0.65](RELEASE-v0.0.65.md): the open entries of their Known lists stand. Every other open entry is in the
  [bug register](../../BUGS.md); the [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and
  part has come.
