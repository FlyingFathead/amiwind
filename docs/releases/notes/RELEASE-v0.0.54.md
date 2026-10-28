# AmiWind v0.0.54: Hair, Movement, Magic And More

Released 28 October 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.53](RELEASE-v0.0.53.md); development
snapshots [v0.0.54-dev1](RELEASE-v0.0.54-dev1.md) and [v0.0.54-dev2](RELEASE-v0.0.54-dev2.md).

Characters move by what they are doing, keep their hair whole, and every one of the 3,437 NPCs and creatures has its
own record of stats, items and spells from the game data, which the game's scripts can read and change. Silt
striders, boats, gondolas and guild guides travel again. Spells can show the game's own effect textures (an
experimental option). 34 of the 35 doorways the converted collision still closed off open, the Vivec Arena Pit draws about 29 % faster, and a version change or an engine
change no longer rebuilds the CHIM world. The game needs 32 MB of Fast RAM; the emulator presets have it.

This release is the v0.0.54-dev2 snapshot with the version changed: the same world, rebuilt once for v0.0.54 on the
caches of the v0.0.53 release build, with only the engine and the image built again for the release.

## What changed since v0.0.53

- **Characters move by what they are doing.** Every animation group of the humanoid characters is chosen by their
  state (standing, walking, running, fighting, casting, dying), by OpenMW's rules, and the first-person hands play
  their own clips, driven by the engine's own C code. Not checked in game yet.
- **Hair kept whole.** Characters' hair is no longer cut back to fit a budget, the player's body has hair too, and the
  heads beside whole hair keep enough triangles to stay recognisable
  ([NPC-HEAD-STARVED-WHOLE-HAIR-54](../../bugs/NPC-HEAD-STARVED-WHOLE-HAIR-54.md)). The Suran dancers are whole at the back
  of the head again, checked in game ([NPC-HAIR-BACK-MISSING-53](../../bugs/NPC-HAIR-BACK-MISSING-53.md)).
- **Every character's stats, from the game data.** All 3,437 NPCs and creatures of Morrowind, Tribunal and Bloodmoon
  have one record each: level, attributes, skills, health, magicka, fatigue, how they behave (Hello, Fight, Flee,
  Alarm), disposition, what they carry and their spells, autocalculated characters by the original rules. Play's
  changes to them are kept in saved games ([ACTOR_STATE.md](../../ACTOR_STATE.md)).
- **The game's scripts go further.** With the experimental scripts on (`dbg mwscript on`), the scripts can read and
  change the stats, items and spells of any character, start and stop combat, count the dead and ask a character's
  current package (wander, travel, follow): 715 of the game's 1,207 scripts now run whole, up from 390. The most common test in the scripts
  is one instruction instead of three: the compiled scripts are 9 % smaller and run 31 to 44 % fewer instructions a
  frame ([MWSCRIPT_BYTECODE.md](../../MWSCRIPT_BYTECODE.md)). Not checked in game yet.
- **Silt striders, boats, gondolas and guild guides travel again.** Talking to any caravaner, shipmaster, gondolier or
  Mages Guild guide opens the list of the places they go, from the game data, with the original prices
  ([TRAVEL-SERVICES-CHIM-51](../../BUGS.md)). The price does not yet change with disposition or Mercantile. Not checked in
  game yet.
- **Magic effects (experimental, off by default).** Spells can show the game's own effect textures as sprites and
  particles: the glow on the casting hands, the bolt in flight and the burst where it lands, with their sounds
  ([MAGIC_EFFECTS.md](../../MAGIC_EFFECTS.md)).
- **Blocked entrances open.** Of the 35 entrances whose converted collision kept the use key out of reach, 34 can be
  walked to and used: the Redoran guard towers' top rooms, the Daedric shrines' entry steps and two Dwemer doors in a
  dip ([DOOR-USE-COLLISION-FILLED-53](../../bugs/DOOR-USE-COLLISION-FILLED-53.md)). The Unmarked Shipwreck's upper trapdoor
  stays out of reach: its tilted deck is steeper than the walk. Every build checks all exterior entrances. Not checked
  in game yet.
- **Weather, smoke and fog indoors.** Rain and smoke follow the game's own tables, and interiors get their fog
  ([INTERIOR-FOG-UNUSED-51](../../BUGS.md)). Not checked in game yet.
- **Levelled creatures outdoors.** Outdoor creatures come from the game's levelled lists, as in the original, and
  creatures have more of their animations. Not checked in game yet.
- **Interface.** A crosshair, a key that hides the HUD, a notice at locked doors, an arrow for you on the map and the
  console's command history. Not checked in game yet.
- **NPC Gallery v2.0.** `dbg npcgallery` shows the game's own characters: the same models, skeletons, animations and
  voices you meet in the world. Search by name, ID, race, class or cell; G plays every animation, T turns the
  character round, E talks ([CHARACTER_MODEL_GALLERY.md](../../CHARACTER_MODEL_GALLERY.md)).
- **`dbg sweep`** checks every entity of the loaded area against what the image ships for it and names what is
  missing ([AMIWIND_CONSOLE_COMMANDS.md](../../AMIWIND_CONSOLE_COMMANDS.md)).
- **No more rust-red speckle on dark ground at night** ([NIGHT-RUST-31](../../bugs/NIGHT-RUST-31.md)), and **owned mushrooms
  indoors can be picked: it is theft** (pickable plants indoors), kept with its owner for when crimes are added
  ([HARVEST-INTERIOR-PICK-47](../../bugs/HARVEST-INTERIOR-PICK-47.md)). Not checked in game yet.
- **The Vivec Arena Pit draws about 29 % faster:** its upper ring takes 18.0 ms a frame instead of 27.5.
- **The Halloween cast is in every full-world build**, so `aw bench halloween` works in the release images
  ([HALLOWEEN.md](../../HALLOWEEN.md)).
- **Faster builds.** A change to the engine, or to a part of the builder the world does not use, no longer rebuilds
  the CHIM world, which took hours each time.

## Known in this build

- Some large interiors, in Vivec above all, are still loading in when you are already there
  ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- One of the six GitHub test parts takes about six times as long as the others
  ([CI-TEST-SHARD-ONE-SLOW-53](../../bugs/CI-TEST-SHARD-ONE-SLOW-53.md)).
- Characters do not yet wander or attack on sight by their own records, Dagoth Ur does not fight or speak, and
  creatures are not yet on skeletons of their own files: all moved to v0.0.55 ([roadmap](../../ROADMAP.md)).
- Everything else is in the [bug register](../../BUGS.md).
