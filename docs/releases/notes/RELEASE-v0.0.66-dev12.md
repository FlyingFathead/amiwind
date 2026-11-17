# AmiWind v0.0.66-dev12 (in development)

_Last updated with AmiWind v0.0.66-dev12 (16 November 2026)._

Development snapshot, 16 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev11](RELEASE-v0.0.66-dev11.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The twelfth snapshot of v0.0.66, and it carries everything that [v0.0.66-dev11](RELEASE-v0.0.66-dev11.md) holds. **The
game changes in two places:** the script engine is sized for the whole game with both expansions, and a fighter's spell
costs its magicka again. The builder writes the image's partitions in one pass, measured much faster on the dev11
inputs, to be confirmed on this snapshot's build. The first step of bringing Tribunal and
Bloodmoon in is in this snapshot, in the script engine; this is not the arrival of Mournhold or Solstheim, and no
finished Mournhold or Solstheim content is in it. The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it.

## New since v0.0.66-dev11

- **The script engine is sized for the whole game with both expansions** (`EXPANSION-SCRIPT-LIMITS-66`;
  `MWVM-INSTANCES-256-66`, `MWVM-PARKING-STORE-SMALL-66`, `MWSCRIPT-MEMBER-LOOKUP-COST-66`,
  `MWSCRIPT-MEMBER-QUIET-READER-66`). Its tables are planned from the counts in the three game files (Morrowind,
  Tribunal, Bloodmoon): 791 attached instances, 1,475 local values, 5,478 parked objects and 12,811 parked values, about
  83 KB more resident memory in Fast RAM. A map with more than 256 scripted objects runs every one of them (the blocks
  of Uvirith's Grave have 276 and 272, and Raven Rock's will have up to 350). A script that reads another object's
  variable does it in one step, and a change a shared script makes wakes the scripts that read it. The save file does not
  change. Fixed in source and covered by tests, to be confirmed in a session (`dbg mwscript status` prints the planned
  tables).
- **A fighter's spell costs its magicka again** (`NPC-CAST-MAGICKA-NOT-PAID-66`). The cast's payment named the wrong
  stat, so a fighter that could afford a spell once cast it every time; the original takes the cost when the cast
  starts. A test follows a fighter through two casts of a 10-point spell (its magicka falls 20, 10, 0, and it casts no
  third time). Fixed in source and covered by tests, to be confirmed in a game.
- **The image's partitions are written in one pass, and an unchanged partition is taken from a cache**
  ([BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66](../../bugs/BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66.md)). The old writer found the
  folder of every file by comparing names, one entry at a time, which took 91 % of the write and grew with the square of
  a folder's entries. The new writer (`tools/ffs_write.py`) makes every folder and file in the same order by the same
  file system code, each in the folder object it goes into, and writes the file data in runs of consecutive blocks; the
  dev11 boot partition written both ways had the same SHA-256. Measured on the dev11 inputs, one partition at a time:
  the boot partition 16.8 s instead of 115.5 s, and the world volume 22.1 s instead of 41.8 s. A partition whose
  contents, size, volume name and writer are those of a stored one is copied from the partition cache instead
  (`tools/partition_cache.py`, development builds): the world volume took 4.5 s from the cache against 29.6 s written
  and stored, and the boot partition 6.8 s against 13.9 s. `AMIWIND_PARTITION_WRITER=xdftool` gives the old writer back
  for a comparison build. To be confirmed on this snapshot's build.
- **Confirmed in play on v0.0.66-dev11** (26ed570f, gate 10941):
  - The opening journey passed all nine steps, 42 of 42 checks. Its step 9 went through the census office's street
    door with the aim on the door and no resident in the way (on dev10 the aim went to Fargoth, `fargoth`, in 12 of
    13 tries): residents keep off doors (`WANDER-DOOR-RULE-66`, now fixed in v0.0.66-dev11).
  - Step 7 cast and fought a fighter named by reference, and its health fell after the fight
    (`JOURNEY-STEP7-FIGHTER-NEAREST-66`, fixed in v0.0.66-dev11).
  - The build took the passed check of the identical starter request instead of running it again, as the build log says
    ([BUILD-CHECK-ONE-CORE-66](../../bugs/BUILD-CHECK-ONE-CORE-66.md), fixed in v0.0.66-dev11).
- **Run 3 of the end of the main quest session** on the dev11 image (the emulator's deterministic option on): after each
  of the first three strikes with Keening, Dagoth Ur's shield followed the Heart's strike count, read through his
  script's member read of the Heart's `countHits` (on the dev10 image it read 0), so the member read is confirmed
  (`MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66`, fixed in v0.0.66-dev11). EndGame's `SetHealth 0` killed Dagoth Ur (262014)
  and two of the three dreamer workers (234368 and 234371); the third (234367) stayed alive: the game's record of changed actors lists all three dead with health 0, but the live
  actor list shows 234367 still walking; the two that died had moved since the chamber loaded and are recorded with
  their room, 234367 had not and is recorded with no room, so the scripted death reached the record and not the live
  actor. In the original every dreamer worker's script sets its health to 0 once the Heart is destroyed. The fix is for a
  later snapshot, so
  `MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66` stays open.
- **The load stall in test sessions: the comparison so far**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)). Repeat sessions of the Arena Pit
  loads on the dev10 image, test sessions only: as sessions run today 8 valid runs, 76 loads and 2 stops; with the
  emulator's deterministic option 8 valid runs, 80 loads and 0 stops. The second stop's packet was again an open for
  writing of the test console's state file, whose host side had finished while the game was never told. The comparison
  continues; no conclusion beyond these numbers. Players have no such drive.
- **Register:** a new entry for the performance guard, which judges the image step's partition write against the
  median of 62 earlier records chosen by the number of partitions and not by their size: with the faster writer the step
  sits near the guard's minimum while the old records keep the median near 66 s, so a slowdown back to about 95 s would
  pass (`PERF-GUARD-BASIS-BY-COUNT-66`, new).

### From v0.0.66-dev11

- Everything of [v0.0.66-dev11](RELEASE-v0.0.66-dev11.md) is in this snapshot: wanderers keep off doors, the two script
  engine faults fixed in source, the builder's reuse check once per snapshot, the testing tools and the end of the main
  quest session; with it everything of [v0.0.66-dev10](RELEASE-v0.0.66-dev10.md),
  [v0.0.66-dev9](RELEASE-v0.0.66-dev9.md), [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md),
  [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md), [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md),
  [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md) and [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md).

### Performance

The measurements of this snapshot are in the register entries above, not on the performance page yet: the image step's
partition write (the boot partition 16.8 s instead of 115.5 s and the world volume 22.1 s instead of 41.8 s on the dev11
inputs; to be confirmed on this snapshot's build, where the step was 1 min 50 s on dev11) and the script engine's added
resident memory (about 83 KB of Fast RAM). The dev11 build's performance guard failed on the partition write (110 s
against its baseline of 68 s); that baseline is the median of earlier two-partition records, chosen by the number of
partitions and not their size, which is why it is old (`PERF-GUARD-BASIS-BY-COUNT-66`). The figures of
[v0.0.66-dev7](RELEASE-v0.0.66-dev7.md) stand; the frame rate on the Raspberry Pi 4B is still to be measured on a
snapshot. See the [v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The checklist of [v0.0.66-dev11](RELEASE-v0.0.66-dev11.md) stands, with these additions.

- Run a map with many scripted objects (Uvirith's Grave) and read `dbg mwscript status`: the planned tables are printed
  and every scripted object runs (fixed in source, not yet seen in play).
- Have a fighter with spells and little magicka fight: it stops casting when its magicka is spent (fixed in source, not
  yet seen in play).

## Known in this build

- **A load can stop in the emulator in test sessions**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)): the cause is found and shown in a
  test session, an interrupt request lost in the drive that serves the test sessions' remote-console folder, and the
  way out, the emulator's deterministic mode, is still being measured (the numbers above). Players have no such drive.
- **The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet**
  (`ENDGAME-CHAMBER-COLLAPSE-63`).
- **One of the three dreamer workers stays alive after EndGame's `SetHealth 0`** (234367;
  `MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66`): the scripted death reaches the record of changed actors but not the live actor
  of the one that had not moved; the fix is for a later snapshot.
- **In Vivec the server's entity update overflows the client's packet every frame**
  (`NET-VIVEC-ENTITY-PACKET-OVERFLOW-66`).
- **The performance guard's partition-write basis** (`PERF-GUARD-BASIS-BY-COUNT-66`): the guard compares the image step
  with earlier builds by the number of partitions and not their size, so a slowdown back to the old time would pass.
- **The builder tool `tools/mwad.py` still has the name of the `src/mwad` package** (`MWAD-NAME-CLASH-66`): a repair was
  made and held back, because it changes the source analysis of every build stage that imports `mwad`, so ten stages
  would have been built again with the same outputs; it returns with proven-equal key rows for those stages, and every
  caller keeps putting `src` before `tools` meanwhile.
- **The script engine keeps one limit** (`MWVM-PLACE-COPIES-FOUR-66`): 4 live copies per scripted Place row in one map
  (a fifth is refused with a console line); it is to be sized from the game's scripts.
- **The image's partitions** (`BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66`) and **a fighter's spell cost**
  (`NPC-CAST-MAGICKA-NOT-PAID-66`): fixed in source, to be confirmed by this snapshot's build and in a game.
- **Coming back out of the census office onto the street could leave the player stuck inside a resident who had walked
  to the door** ([DOOR-ARRIVAL-INSIDE-ACTOR-66](../../bugs/DOOR-ARRIVAL-INSIDE-ACTOR-66.md)): fixed in source and
  covered by tests, still to be seen in play.
- **The image step's room resident step takes about two minutes on one core when every room is cached**
  (`IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66`): the output is right.
- **The census courtyard arrival got stuck once** (`COURTYARD-ARRIVAL-STUCK-66`): in one of two arrivals from the back
  room the player came into the courtyard stuck in solid and was moved out twice.
- **The console's item count, equip, position and ShowVars reads**
  ([CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66](../../bugs/CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66.md),
  `CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66`, `CONSOLE-GETPOS-SCRATCH-ORIGIN-66`, `CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66`):
  `player->getitemcount` answers "no such item id" for an item the player carries that is not on the actors' item list;
  `player->equip` wears an item without its equip script; a position read of an actor answers a point near the origin;
  and ShowVars on a reference does not show that reference's variables. The game's own routes are not affected.
- **Checks in the development container can fail on a file read**
  ([CONTAINER-READ-ENOMEM-66](../../bugs/CONTAINER-READ-ENOMEM-66.md)): "Cannot allocate memory", and a retry works.
- **The save's fixed limits are raised and made guards, but the whole is not proven in play**
  (`SAVE-STATE-FIXED-CAPS-66`): a round trip of a long game in the emulator at 32 MB Fast, with the load and save times
  on the 68040 preset and the Raspberry Pi 4B, is not done; the flora's slot table (4,096) is checked against the base
  game (2,896) and its count with the expansions is not yet known.
- Tribunal and Bloodmoon data is selected by default, but the cells and rooms of Mournhold and Solstheim are not played
  in this snapshot: there is no finished Mournhold or Solstheim content.
- **Bloodmoon's werewolf form has no player model yet** (`PLAYER-WEREWOLF-ROBE-NOT-BAKED-66`): the form is not in the
  game, and its robe is left out of the player parts.
- The new weapon choice, fleeing and the outdoor bodies are checked by tests, not yet in play. Still open in the actors'
  mechanics: the crime audit, an NPC running while it wanders, potions and magic items as a fighter's best action.
- The game can stop in an ancestral tomb.
- The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run.
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- From [v0.0.66-dev11](RELEASE-v0.0.66-dev11.md), [v0.0.66-dev10](RELEASE-v0.0.66-dev10.md),
  [v0.0.66-dev9](RELEASE-v0.0.66-dev9.md), [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md),
  [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md), [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md),
  [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md), [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md),
  [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md), [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md),
  [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and [v0.0.65](RELEASE-v0.0.65.md): the open entries of their Known lists
  stand. Every other open entry is in the [bug register](../../BUGS.md); the
  [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.
