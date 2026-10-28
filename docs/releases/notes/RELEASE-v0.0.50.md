# AmiWind v0.0.50: The Doors: Riders On The CHIM

Released 24 October 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.49](RELEASE-v0.0.49.md);
development snapshots [v0.0.50-dev1](RELEASE-v0.0.50-dev1.md), [v0.0.50-dev2](RELEASE-v0.0.50-dev2.md) and
[v0.0.50-dev3](RELEASE-v0.0.50-dev3.md).

Every entrance of the game leads into its interior, and every way out leads back. The game's 3,133 load doors and
markers are resolved through one door table built from the game's own door records, and the image no longer builds
when a door does not resolve. The v0.0.49 image had 106 of them unlinked. Nothing new is placed: only the links the
original game data already has.

## What changed since v0.0.49

- **One door table for the whole world.** Every load door, and every marker where an arrest takes the player, has one
  holder: a town frame holds what lies inside its box (Seyda Neen, Balmora and Vivec, the towns built before the region
  frames), the CHIM region frame of the cell holds the rest, and a room holds its own doors. Every door bank of the
  image is written from the table, and the build stops when a door does not resolve
  ([door graph](../../chim/DOOR_GRAPH.md#rooms-by-batch-in-the-builder),
  [CHIM-REGION-DOORS-NO-ROOMS-48](../../bugs/CHIM-REGION-DOORS-NO-ROOMS-48.md)).
- **Ways out around Vivec and Ebonheart.** 85 doors out of rooms into cells a town frame holds lead out again, among
  them Hawkmoth Towers, the Grand Council Chambers, the East Empire warehouses, several Vivec waistworks and Telvanni
  Plaza. The builder had checked each town's map by its own name, while a town on CHIM runs as its CHIM frame map, so
  it had dropped every town.
- **Entrances near the old towns.** 10 doors in cells inside the old town frames open now: Pelagiad's houses of
  Adanja, Ahnassi and Dralas Gilu, the Abaesen-Pulu Egg Mine, Assemanu, the Andrano Ancestral Tomb, the Akimaes and
  Nimawia Grottos and the two doors of the Remote Shipwreck.
- **The opening is untouched.** The prison ship, the pier, the census office and Seyda Neen's courtyard keep the doors
  the opening scene gives them: no leaving the census office before the papers are done, and then by one door only.
- **Markers for later.** The markers where an arrest takes the player are rows of the table, ready for the jail system
  and the game's scripts.
- **`dbg tp heartchamber`** heads for Akulakhan's Chamber, the Heart Chamber, where the game's own door puts you
  (the room itself does not load yet: see below). Named places are listed in `config/teleport-names.txt`
  ([console commands](../../AMIWIND_CONSOLE_COMMANDS.md)).
- **A guard on the public tree.** Every commit is checked for private words and for assistant instruction files in
  the public tree, and the bug register refuses private words.
- **The Toolkit Monitor follows the build.** "Follow latest" and "follow the running stage" are kept in the browser
  and on when nothing is saved, so a load or a reload shows the newest running build and its running stage
  (Toolkit 0.1.12).
- **A version change rebuilds only the engine and the image.** The v0.0.50-dev2 build changed only the version
  against dev1 and reused 40 of 43 stages; the CHIM world came from the cache
  ([BUILD-VERSION-GETATTR-TRACE-49](../../bugs/BUILD-VERSION-GETATTR-TRACE-49.md)).
- **Real hardware.** The hardware page leads with the machines AmiWind aims at (FPGA accelerators, PiStorm and new
  machines such as the THEA1200), with a classic 68060 as the floor; hardware 3D through Warp3D is a research item
  ([AmiWind on real hardware](../../REAL_HARDWARE.md),
  [roadmap](../../ROADMAP.md#research-hardware-3d-through-warp3d-v0050-study-24-october-2026)).
- **Release records.** The previous-release record and the size baseline describe v0.0.49.

## Known in this build

- Everything in [v0.0.49's known items](RELEASE-v0.0.49.md#known-in-this-build) still applies, except the version-only
  rebuild of the CHIM world, which is repaired.
- [CHIM-ROOM-HEART-CHAMBER-LOAD-50](../../bugs/CHIM-ROOM-HEART-CHAMBER-LOAD-50.md): entering Akulakhan's Chamber, the game's final room, ends the game: one
  of its models does not find room in the CHIM model zone, which stays the same size on 32 MB as on 16 MB
  ([CHIM-ZONE-BUDGET-33](../../bugs/CHIM-ZONE-BUDGET-33.md)). Found by this release's check of `dbg tp heartchamber`; the room has been on CHIM
  since v0.0.48. The fix is the first work of v0.0.51.
- [DEBUG-TP-ROOM-ENTRANCE-50](../../bugs/DEBUG-TP-ROOM-ENTRANCE-50.md): `dbg tp` with a room's map name finds the entrance only of rooms entered from
  Balmora; the doors themselves are not affected.
- [BUILD-CHIM-STAGE-SERIAL-TAIL-36](../../bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md): the CHIM stage's validation and world
  pack still run on a few cores for about four minutes of a build that rebuilds the world.
- Quests, dialogue, services, schedules, weapon and magic combat and most other game logic are unfinished; items and
  containers in rooms are not live objects yet (v0.0.51 and later: [roadmap](../../ROADMAP.md)).
- Everything else is in the [bug register](../../BUGS.md).
