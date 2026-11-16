# AmiWind v0.0.66-dev5 (in development)

_Last updated with AmiWind v0.0.66-dev5 (15 November 2026)._

Development snapshot, 15 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev4](RELEASE-v0.0.66-dev4.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

The fifth snapshot of v0.0.66, and it carries everything that [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md) holds. **The
opening holds the controls as the original does**: the opening's scripts keep fighting and magic switched off from the
prison ship until the release papers are taken, and the ready-magic key follows them. **The item you look at is the one
you take**: of two items lying one on the other, the use key goes to the one the view meets first, so the crab meat on
the census back room's silver plate is taken and not the owned plate under it. **Area loads read their sounds quickly
again**: the image step lays out the disk's folders so that a sound's name lookup fits the disk buffers, which it no
longer did since v0.0.66-dev2. This is not the arrival of Mournhold or Solstheim: no finished Mournhold or Solstheim
content is in this snapshot. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot; none of them has been seen in play on a
build yet. The scripted doors fix of v0.0.66-dev4 has been seen in play since, on the v0.0.66-dev4 image (see "From
v0.0.66-dev4").

## New since v0.0.66-dev4

### The opening's controls

- **The opening's control switches as in the original.** In the original the CharGen script switches the controls,
  jumping, fighting, magic, the view switch and vanity off when the new game starts, and the scripts of the ship guard,
  the dock guard, the clerk, the papers, the hall guard, the courtyard barrel and the exit door switch them on again in
  turn. AmiWind carries that script with its own code, and it had left the switches out, so every switch read on from
  the start: the opening's own rule still kept drawing a weapon and attacking off until the papers, but magic could be
  readied. The new game now sets the switches from the script's own calls when the opening starts on the ship, the ship
  guard and the dock guard switch the controls as their scripts do, and the ready-magic key readies nothing while a
  script keeps magic or the controls off. The builder refuses a script file in which a switch the new game turns off is
  switched on again by no script (`OPENING-FIGHTING-ON-BEFORE-PAPERS-66`).

### Taking items

- **The use key goes to what the view meets first.** Two items lying one on the other were told apart by their centres
  alone, so aimed at the crab meat on the census back room's silver plate, E could take the plate, a theft, instead of
  the crab meat. The use now goes to what the view ray meets first, as in the original, for every item drawn as an
  object of its own or by a CHIM room (an item lying outdoors keeps the earlier test); `aw_placed aim` names what the
  ray meets and always lists the aimed row (`CENSUS-CRAB-PLATE-FOCUS-66`).

### Area loads

- **The sound loading of an area load is short again**
  ([directory hash chains and disk buffers](../../STORAGE.md#directory-hash-chains-and-disk-buffers)): the image step
  orders every folder's hash chains busiest first and gives every partition the disk buffers its longest name lookup
  needs (the boot partition 150 instead of 30, about 75 KiB of Fast RAM). Measured on the v0.0.66-dev4 boot partition
  through the new code, a sound outside the sound pool is found in 6 header blocks instead of 34 (median), within the
  buffers every time ([IMAGE-LOADS-SLOWER-66](../../bugs/IMAGE-LOADS-SLOWER-66.md),
  [BUILD-HDF-BUFFERS-32](../../bugs/BUILD-HDF-BUFFERS-32.md)).

### The opening journey

- **God mode is on for the journey's kill only** ([gameplay journeys](../../GAME_RECORDER.md#gameplay-journeys)): it
  blocks every kind of damage, and left on after the kill it held the hurt, the heal and the fight of the next step at
  the same health.
- **The walk to the pier keeps clear of the courtyard barrel**, whose script switches fighting, magic and jumping on
  near it, so the check before the papers reads the switches as the opening leaves them.
- The opening's ring is named as the game names it, in the journey and on these pages: Fargoth's ring (the Engraved
  Ring of Healing, `ring_keley`).

### From v0.0.66-dev4

- Everything of [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md) is in this snapshot: scripted doors that open every time their
  script allows, the opening journey on foot, a teleport typed during a load and the actor check of the empty rooms;
  and with it everything of [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md).
- **Seen in play on the v0.0.66-dev4 image:** after the release the census captain's room lets the player out and back
  in by both its doors, every time (the street door, the courtyard door and the exit door;
  `CAPTAIN-EXIT-DOOR-DEAD-AFTER-REENTRY-66`).

### Performance

Checked by tests; the frame rate on the Raspberry Pi 4B is still to be measured on this snapshot. All figures, with what
measured them and what is not measured yet, are on the [v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

- **Area loads:** the header blocks of a name lookup are measured on the v0.0.66-dev4 layout (above); the sound loading
  of the Seyda Neen, Balmora and Vivec loads is still to be measured on this snapshot's build, against v0.0.66-dev1's
  139, 139 and 306 ms.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- A New Game: on the ship and through the clerk's registration, fighting and magic are off (the ready-magic key readies
  nothing) until the papers are taken from the census office table; after the papers both are on.
- In the census back room, aim at the crab meat on the silver plate: E takes the crab meat, not the plate.
- Travel to Seyda Neen, Balmora and Vivec: the loads are no slower than in v0.0.66-dev1.
- Everything on dev4's checklist that has not been played yet: a New Game through the census office on foot (the
  papers, the hall guard's door, the dagger in the back room, Fargoth's ring in the courtyard barrel, Sellus Gravius'
  topics and the release), and `dbg tp` to a town typed while an area is still loading.

## Known in this build

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
- From [v0.0.66-dev4](RELEASE-v0.0.66-dev4.md), [v0.0.66-dev3](RELEASE-v0.0.66-dev3.md),
  [v0.0.66-dev2](RELEASE-v0.0.66-dev2.md), [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and [v0.0.65](RELEASE-v0.0.65.md):
  the open entries of their Known lists stand, but for the three this snapshot fixes (fighting before the papers, the
  crab meat's plate and the slower sound loading, above). Every other open entry is in the
  [bug register](../../BUGS.md); the
  [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.
