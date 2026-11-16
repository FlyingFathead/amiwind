# AmiWind v0.0.66-dev10 (in development)

_Last updated with AmiWind v0.0.66-dev10 (15 November 2026)._

Development snapshot, 15 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev9](RELEASE-v0.0.66-dev9.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The tenth snapshot of v0.0.66, and it carries everything that [v0.0.66-dev9](RELEASE-v0.0.66-dev9.md) holds. **The game
is the same as in dev9 apart from the version, plus one test-only setting:** `aw_remote_log`, the remote console's log of
the test sessions, on by default; players have no remote console. The rest is in the testing tools and the register.
This is not the arrival of Mournhold or Solstheim: no finished Mournhold or Solstheim content is in this snapshot. The
game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.66-dev9

- **Testing tools.** The stall examination reads the game's own disk request, every handler's wait and the game's own
  clock, and can no longer leave the emulator paused. The remote console's log is traced and can be switched off
  (`aw_remote_log`).
- **What the load stall investigation showed.** A repeat test session stopped once, after 19 good loads, in play and not
  in a map load; the stop reads as inside the remote console's log write on its folder. The cause is not proven, and the
  entry ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)) stays open until the log is
  measured on and off.
- **Seen on the v0.0.66-dev9 image: the opening journey passed 41 of 42 checks.** Step 6 killed its fixed victim, Erene
  Llenim (`128960`), by reference, and no player was left stuck (`JOURNEY-STEP6-VICTIM-NEAREST-66`, seen fixed). Step 7's
  fighter, chosen as the nearest resident, was Fargoth (`fargoth`), who fights unarmed: 14 swings gave misses and three hits on the fatigue
  only, so the health stayed at 910 and the check that it fell failed. Hand-to-hand damage goes to the fatigue first, as
  in the original; this is not a fault of the combat but of the choice of the fighter
  (`JOURNEY-STEP7-FIGHTER-NEAREST-66`, new). The step summons a copy of the nearest resident and the console command
  takes no reference, so the step is unchanged in this snapshot.
- **The door arrival was not exercised.** No actor stood on the street door's arrival point after step 6 and the console
  of neither part has a "player is stuck." line, so the fix of dev9 has not been seen at work
  (`DOOR-ARRIVAL-INSIDE-ACTOR-66` stays open: fixed in source, covered by tests, to be confirmed in play).
- **Register entries:** the build's reuse check was seen again on one core (`BUILD-CHECK-ONE-CORE-66`: the starter's
  check and the build's own check of the same commit, one core each), and the image step wrote its partitions in 107 s
  where the earlier build took 67 s with the same two units, once, in one build; it is to be measured again on the next
  build (`BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66`, new).

### From v0.0.66-dev9

- Everything of [v0.0.66-dev9](RELEASE-v0.0.66-dev9.md) is in this snapshot: the player no longer ends inside an actor at a
  door's or a teleport's arrival point (fixed in source and covered by tests), the stall examination that reads the
  running game, the journey's door aim, and the correction of what the earlier notes said about the journey's stops; with
  it everything of [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md), [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md),
  [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md), [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md) and
  [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md).

### Performance

One measurement is recorded in the register entry above, not on the performance page yet: the image step's partitions
took 107 s on the dev9 build against 67 s on the earlier one. No other new measurement in this snapshot. The figures of
[v0.0.66-dev7](RELEASE-v0.0.66-dev7.md) stand; the frame rate on the Raspberry Pi 4B is still to be measured on a
snapshot. See the [v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The checklist of [v0.0.66-dev9](RELEASE-v0.0.66-dev9.md) stands.

- Leave the census office by its street door while the guard stands near it: the player arrives clear of him and can
  walk away (the fix is in source and not yet seen in play).
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

- **A load can stop in the emulator in test sessions**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)): the stop was reproduced on demand in
  a test session and placed in the remote console's log write, not in a map load; it is being measured with the log on
  and off. Players have no remote console.
- **Coming back out of the census office onto the street could leave the player stuck inside a guard who had walked to
  the door** (`DOOR-ARRIVAL-INSIDE-ACTOR-66`): fixed in source and covered by tests; the dev9 journey did not exercise the
  case, so the entry stays open until it is seen in play.
- **The opening journey's step 7 can pick an unarmed fighter** (`JOURNEY-STEP7-FIGHTER-NEAREST-66`): the nearest resident
  is the fighter, and when that is Fargoth the health may not fall.
- **Wandering residents do not keep away from doors as in the original game** (`WANDER-DOOR-RULE-66`): a wanderer can stop
  at a destination right by a door and stand there.
- **In Vivec the server's entity update overflows the client's packet every frame**
  (`NET-VIVEC-ENTITY-PACKET-OVERFLOW-66`).
- **The reuse check runs about six minutes on one core, twice before every build** (`BUILD-CHECK-ONE-CORE-66`).
- **The image's partitions were written slower once** (`BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66`): 107 s against 67 s on the
  dev9 build; to be measured again.
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
- From [v0.0.66-dev9](RELEASE-v0.0.66-dev9.md), [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md),
  [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md), [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md),
  [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md), [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md),
  [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md), [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md),
  [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and [v0.0.65](RELEASE-v0.0.65.md): the open entries of their Known lists stand.
  Every other open entry is in the [bug register](../../BUGS.md); the
  [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.
