# AmiWind v0.0.54-dev1 (in development)

Development snapshot, 27 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.53](RELEASE-v0.0.53.md).

The first snapshot of v0.0.54 (in development).

## New since v0.0.53

- **The Halloween cast is in every full-world build.** The scene's skeletons, Desele's dancers and Dagoth Ur (about
  1 MB, loaded only when the scene plays) come with every full image, so `aw bench halloween` works in release images
  too. `--halloween-cast off` leaves them out.
- **The GitHub test jobs have names.** The six parallel parts of the test suite show as "Test suite part 1 of 6" to
  "Test suite part 6 of 6" ([CI-JOBS-UNNAMED-53](../../BUGS.md)).
- **More time for the tools jobs on GitHub.** The first run of the split workflow needed 28 minutes 15 seconds to
  bootstrap every tool from nothing, 95 % of its limit: `tools` now has 40 minutes and `tools-from-nothing` 60
  ([CI-SOURCE-JOB-TIMEOUT-52](../../bugs/CI-SOURCE-JOB-TIMEOUT-52.md), [CI_DRY_RUN.md](../../CI_DRY_RUN.md)).
- **Every character's stats, from the game data.** All 3,437 NPCs and creatures of Morrowind, Tribunal and
  Bloodmoon have one record each: level, attributes, skills, health, magicka, fatigue, how they behave (Hello, Fight,
  Flee, Alarm), disposition, what they carry and their spells, autocalculated characters by the original rules. Play's
  changes to them are kept in saved games ([ACTOR_STATE.md](../../ACTOR_STATE.md)).
- **The game's scripts can use them.** With the experimental scripts on (`dbg mwscript on`), 87 more script functions
  run: the stats, items and spells of any character, SetFight, StartCombat, StopCombat, OnDeath, GetDeadCount and
  AIWander; 635 of the game's 1,207 scripts now run whole, up from 390. Not checked in game yet.
- **Smaller, faster scripts.** The most common test in the scripts is now one instruction instead of three: the
  compiled scripts are 9 % smaller and run 31 to 44 % fewer instructions a frame, with the same results
  ([MWSCRIPT_BYTECODE.md](../../MWSCRIPT_BYTECODE.md)).
- **Silt striders, boats, gondolas and guild guides travel again.** Talking to any caravaner, shipmaster, gondolier or
  Mages Guild guide opens the list of the places they go, from the game data, with the original prices: the distance
  from you to the destination for a ride outdoors (and the hours it takes pass on the clock), the guild's fixed price
  for a guild guide. A destination this build does not hold is not offered. Before this, only Seyda Neen's and
  Balmora's striders had a ride, and it no longer worked in the CHIM world
  ([TRAVEL-SERVICES-CHIM-51](../../BUGS.md)). The price does not yet change with disposition or Mercantile. Not checked in
  game yet.
- **No more rust-red speckle on dark ground at night.** Dark warm greys (walls, ground and rock at night, by a torch
  or a lamp) could take one of the palette's two dark rust-reds: up to 26 of the 256 colours of a night table. Dark
  colours now come from a finer table that never makes them redder than they are
  ([NIGHT-RUST-31](../../bugs/NIGHT-RUST-31.md)); the earlier lookup stays in the code (a build switch). Not checked in
  game yet.
- **Owned mushrooms indoors can be picked: it is theft.** The 93 small mushrooms in rooms that belong to someone (the
  St. Delyn Waistworks among them) stayed fixed in place. Now they are picked like any other, as the original and
  OpenMW allow; the pick is kept with its owner, ready for when crimes are added
  ([HARVEST-INTERIOR-PICK-47](../../bugs/HARVEST-INTERIOR-PICK-47.md)). Not checked in game yet.
- **NPC Gallery v2.0.** `dbg npcgallery` now shows the game's own characters: the same models, skeletons,
  animations and voices you meet in the world, so a fix to a character shows in the gallery at once. Nothing is baked
  for the gallery any more: the build loses its longest stage (up to an hour when its cache missed) and the image
  about 234 MB of separate gallery models. Search by name, ID, race, class or cell; G plays every animation, T turns
  the character round, E talks ([CHARACTER_MODEL_GALLERY.md](../../CHARACTER_MODEL_GALLERY.md)).
- **`dbg sweep`** checks every entity of the loaded area against what the image ships for it and names what is
  missing: a character without a model or animation, a plant that cannot be picked, a door that leads nowhere
  ([AMIWIND_CONSOLE_COMMANDS.md](../../AMIWIND_CONSOLE_COMMANDS.md)).

## Known in this build

- Some of the Suran dancers have no hair at the back of the head
  ([NPC-HAIR-BACK-MISSING-53](../../bugs/NPC-HAIR-BACK-MISSING-53.md)).
- One of the six GitHub test parts takes about six times as long as the others
  ([CI-TEST-SHARD-ONE-SLOW-53](../../bugs/CI-TEST-SHARD-ONE-SLOW-53.md)).
- Some large interiors, in Vivec above all, are still loading in when you are already there
  ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- Everything else is in the [bug register](../../BUGS.md).
