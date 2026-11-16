# AmiWind v0.0.66-dev11 (in development)

_Last updated with AmiWind v0.0.66-dev11 (16 November 2026)._

Development snapshot, 16 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev10](RELEASE-v0.0.66-dev10.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The eleventh snapshot of v0.0.66, and it carries everything that [v0.0.66-dev10](RELEASE-v0.0.66-dev10.md) holds. **The
game changes in three places:** residents that wander keep off doors as in the original, and two faults of the script
engine are fixed in source: a script's read or write of another object's local variable, and a script's `SetHealth 0`.
The rest is in the builder, the testing tools and the register. This is not the arrival of Mournhold or Solstheim: no finished Mournhold or Solstheim
content is in this snapshot. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## New since v0.0.66-dev10

- **Wanderers keep off doors, as in the original** (`WANDER-DOOR-RULE-66`). A resident on its Wander package that stands
  idle facing a door within reach (at most 60 degrees off its facing, within 1.6 times the activation distance, checked
  every 1.5 seconds of an idle) walks on to another destination, and a walker stuck with a door ahead drops that
  destination and the ones on its way there. These are the original's rules as the reference engine implements them,
  for every wanderer and every door; a resident with no wander distance, or one that only walks near its start, stays as
  before, and `chim actors ambient doors off` gives the old behaviour back. Fixed in source and covered by tests, to be
  confirmed in play: on the v0.0.66-dev10 image Fargoth (`fargoth`) stood by the census office's street door and took
  12 of the opening journey's 13 aims at it.
- **Two script engine faults, fixed in source** (found by the end of the main quest session below). A script that reads
  or writes a local variable of another object read the wrong field of that object's row, so every such read gave 0
  and every such write was lost: 464 such operations in 186 of the game's scripts
  (`MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66`). And a script's `SetHealth 0` did not kill
  (`MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66`). Both are fixed in source and covered by tests, to be confirmed by the session
  on the dev11 image.
- **The builder runs its reuse check once per snapshot**
  ([BUILD-CHECK-ONE-CORE-66](../../bugs/BUILD-CHECK-ONE-CORE-66.md)). A build request takes the passed check of an
  identical earlier request (the same commit, earlier build, build flags and check, at most 30 minutes old) instead of
  running the same check again, which took 4.5 to 8.2 minutes on the dev7 to dev10 snapshots; the check's file
  comparison and its unit-cache report run on more cores. The check waits on the disk more than on the cores: it
  measured 332 s with the check's 4 workers and 341 s with the build's full worker count before the change, and 299 s
  with that count after it (single runs). Fixed in source, to be confirmed by this snapshot's build.
- **Testing tools.**
  - `chim actors summon` takes an optional reference, and the opening journey's step 7 fights the armed Seyda Neen guard
    (`128967`) by reference instead of the nearest resident (`JOURNEY-STEP7-FIGHTER-NEAREST-66`). On the v0.0.66-dev10
    image the nearest was Fargoth again, who fights unarmed, and the step failed by chance. Fixed in source and covered
    by tests, to be confirmed by the next journey.
  - The stall examination names the file a stuck open, lock or delete asks for (the name sits at its BCPL pointer times
    four, and the raw value had been read as the address) and prints the stuck request's state word
    (`STALL-PROBE-NAME-BPTR-66`, seen fixed: at a stop of 16 November 2026 it named an open for output of the remote
    console's state file).
  - Session scripts and journeys can set emulator options with `emu KEY=VALUE` lines, and the repeat session of the load
    stall has a twin that runs the emulator in its deterministic mode (`tests/sessions/load_repeat_hops_det.txt`).
  - A test session for the end of the main quest (`tests/sessions/endgame_heart.txt`, `ENDGAME-HEART-SESSION-66`): a test
    character with Sunder, Keening and Wraithguard goes from the Heart Chamber to Azura in the Facility Cavern, each step
    checked from the game state.
- **What the end of the main quest session's first run measured** (the v0.0.66-dev10 image, FS-UAE at 32 MB Fast,
  JIT). The Heart Chamber loads in play at 32 MB from Seyda Neen, with the Heart of Lorkhan and Dagoth Ur in it and
  1,943 KiB of Fast RAM free inside, in one load frame of about 42 seconds
  ([ROOM-LOAD-LONG-FRAME-63](../../bugs/ROOM-LOAD-LONG-FRAME-63.md), seen again).
  Dagoth Ur fights from the arrival, his script holding his health and his first shield. The run stopped at the first
  strike, on the test sessions' emulator stall described below. Three console reads cannot pass today and are now
  checked as known gaps: the console does not count Keening
  ([CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66](../../bugs/CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66.md)); the console's
  equip skips an item's equip script, so Wraithguard worn through it leaves its script's flag unset, while the
  inventory's own route sets it (`CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66`, new); and the console's position read of an actor
  answers a point near the origin instead of where the actor stands (`CONSOLE-GETPOS-SCRATCH-ORIGIN-66`, new). The
  chamber's collapse is not animated (`ENDGAME-CHAMBER-COLLAPSE-63`); the session checks it as a known gap, and the
  first run did not reach it.
- **Its second run** (the same image, the emulator in its deterministic mode, no stall) passed 55 of 66 checks. In
  play: the Heart's script took Sunder's strike, five strikes with Keening destroyed the Heart of Lorkhan, Dagoth Ur's
  health was then capped at 200, and the end script ran from the chamber's entrance: the quest at its stage 20, the
  blight ended, Red Mountain's weather changed, teleporting allowed again and the reputation raised by 10. It found the
  two script engine faults above: Dagoth Ur's shield did not follow the first three Keening strikes, the dreamer
  workers stayed alive and Dagoth Ur was not dead after the end script. In the Facility Cavern the quest's end did not
  start, because of the session's own order of visits: the run first entered the cavern at stage 20, and Azura's spirit
  shows itself again only if its script hid it on an earlier visit. The session now visits the cavern first, as the
  quest goes; its next run is to show the ending. No run has reached the ending video yet. Known and not fixed yet: the
  collapse and the console's ShowVars on a reference (`CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66`).
- **The load stall in test sessions: its cause found and shown**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)). The stops examined on the
  v0.0.66-dev10 image were all requests to the test sessions' remote-console folder, a host folder the emulator serves
  as a drive: each finished on the emulator's host side, and the game was never woken. In FS-UAE 3.1.66 that drive's
  host thread announces a finished request in an interrupt word that the emulator thread rewrites as well, without
  atomic operations, so an overlap can lose the interrupt request. The emulator's own development line made these
  operations atomic in December 2016; the 3.1.66 version the test sessions run does not have that change. Read first
  from the emulator's source, the mechanism was then caught at work in a plain repeat session: it stopped with the
  remote console's poll of its command file finished by the emulator's host side and the drive's handler never told.
  Players have no such drive, so a player's game is not affected. The way out for the test sessions is an emulator
  option, its deterministic mode, which serves host folders on the emulator thread; it is being measured against the
  plain sessions, and the entry stays open until that measurement is in. The same race is in the newest stable FS-UAE,
  3.2.35; a note for anyone who mounts a host folder as a drive is on
  [FS-UAE development access](../../FS-UAE-DEVELOPMENT.md#engine-boot-and-map-load-smoke).
- **Seen on the v0.0.66-dev10 image.** The boot smoke and the six area hops passed at 32 MB Fast. The opening journey
  passed 38 of 42 checks: step 7's fighter was Fargoth again, and step 9's aim at the census office's street door went
  to Fargoth standing in front of it (the two fixes above).
- **Register entries:** the image step's partitions measured again on the v0.0.66-dev10 build, 1 min 37 s with no
  emulator session beside it; the performance guard passed it, just inside its limit. The builds' own logs show the
  step at 86 to 107 s on every build since v0.0.66-dev2, where the v0.0.65 builds took 66 to 82 s, as the boot
  partition grew from about 1,750 MiB to 2,015 MiB (`BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66`, now seen on every build).
  In the development container a file read can fail with "Cannot allocate memory", seen first in v0.0.54 and again
  under load, so a check that hits it reports an unrelated failure
  ([CONTAINER-READ-ENOMEM-66](../../bugs/CONTAINER-READ-ENOMEM-66.md), new).

### From v0.0.66-dev10

- Everything of [v0.0.66-dev10](RELEASE-v0.0.66-dev10.md) is in this snapshot: the stall examination that reads the
  game's own disk request and can no longer leave the emulator paused, and the remote console's log behind
  `aw_remote_log`; with it everything of [v0.0.66-dev9](RELEASE-v0.0.66-dev9.md),
  [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md), [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md),
  [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md), [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md) and
  [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md).

### Performance

The measurements of this snapshot are in the register entries above, not on the performance page yet: the builder's
reuse check (332 s with the check's 4 workers and 341 s with the build's full worker count before the change, 299 s
with that count after it), the image step's partitions
(86 to 107 s on every build since v0.0.66-dev2) and the Heart Chamber's load at 32 MB (one frame of about 42 seconds,
1,943 KiB of Fast RAM free inside). The figures of [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md) stand; the frame rate on the
Raspberry Pi 4B is still to be measured on a snapshot. See the
[v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The checklist of [v0.0.66-dev10](RELEASE-v0.0.66-dev10.md) stands.

- Watch the residents near doors in Seyda Neen: an idle wanderer facing a door close by walks on instead of standing in
  front of it (fixed in source, not yet seen in play).
- Leave the census office by its street door while a resident stands near it: the player arrives clear and can walk
  away (fixed in source, not yet seen in play).

## Known in this build

- **A load can stop in the emulator in test sessions**
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)): the cause is found and shown in a
  test session, an interrupt request lost in the drive that serves the test sessions' remote-console folder, and the
  way out, the emulator's deterministic mode, is being measured. Players have no such drive.
- **The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet**
  (`ENDGAME-CHAMBER-COLLAPSE-63`).
- **Two script engine faults** (`MWSCRIPT-MEMBER-READS-ID-AS-SCRIPT-66`, `MWSCRIPT-SETHEALTH-ZERO-NO-DEATH-66`): fixed in
  source and covered by tests, to be confirmed by the end of the main quest session on the dev11 image.
- **In Vivec the server's entity update overflows the client's packet every frame**
  (`NET-VIVEC-ENTITY-PACKET-OVERFLOW-66`).
- **Coming back out of the census office onto the street could leave the player stuck inside a resident who had walked
  to the door** ([DOOR-ARRIVAL-INSIDE-ACTOR-66](../../bugs/DOOR-ARRIVAL-INSIDE-ACTOR-66.md)): fixed in source and
  covered by tests, still to be seen in play.
- **Wanderers and doors** (`WANDER-DOOR-RULE-66`): fixed in source and covered by tests, to be confirmed in play.
- **The opening journey's step 7** (`JOURNEY-STEP7-FIGHTER-NEAREST-66`): now fights the guard by reference, to be
  confirmed by the next journey.
- **The reuse check** ([BUILD-CHECK-ONE-CORE-66](../../bugs/BUILD-CHECK-ONE-CORE-66.md)): runs once per snapshot in
  source, to be confirmed by this snapshot's build.
- **The image's partitions are written slower since v0.0.66-dev2** (`BUILD-IMAGE-LAYOUT-WRITE-SLOWER-66`): with the
  larger boot partition; to be measured again on this snapshot's build. The output is right.
- **The image step's room resident step takes about two minutes on one core when every room is cached**
  (`IMAGE-ROOM-RESIDENTS-CACHED-ONE-CORE-66`): seen in the builds of v0.0.66-dev4 and v0.0.66-dev5; the output is right.
- **The census courtyard arrival got stuck once** (`COURTYARD-ARRIVAL-STUCK-66`): in one of two arrivals from the back
  room the player came into the courtyard stuck in solid and was moved out twice.
- **The console's item count, equip, position and ShowVars reads**
  ([CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66](../../bugs/CONSOLE-GETITEMCOUNT-UNNAMED-ITEM-66.md),
  `CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66`, `CONSOLE-GETPOS-SCRATCH-ORIGIN-66`, `CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66`):
  `player->getitemcount` answers "no such item id" for an item the player carries that is not on the actors' item list,
  the only list the console looks in (the census iron dagger, and Keening); `player->equip` wears an item without its
  equip script; a position read of an actor answers a point near the origin; and ShowVars on a reference does not show
  that reference's variables. The game's own routes are not affected.
- **Checks in the development container can fail on a file read**
  ([CONTAINER-READ-ENOMEM-66](../../bugs/CONTAINER-READ-ENOMEM-66.md)): "Cannot allocate memory", and a retry works.
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
- The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run.
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- From [v0.0.66-dev10](RELEASE-v0.0.66-dev10.md), [v0.0.66-dev9](RELEASE-v0.0.66-dev9.md),
  [v0.0.66-dev8](RELEASE-v0.0.66-dev8.md), [v0.0.66-dev7](RELEASE-v0.0.66-dev7.md),
  [v0.0.66-dev6](RELEASE-v0.0.66-dev6.md), [v0.0.66-dev5](RELEASE-v0.0.66-dev5.md),
  [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md), [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md),
  [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md), [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and [v0.0.65](RELEASE-v0.0.65.md):
  the open entries of their Known lists stand. Every other open entry is in the [bug register](../../BUGS.md); the
  [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.
