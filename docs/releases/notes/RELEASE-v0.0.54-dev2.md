# AmiWind v0.0.54-dev2 (in development)

Development snapshot, 28 October 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.54-dev1](RELEASE-v0.0.54-dev1.md); previous release: [v0.0.53](RELEASE-v0.0.53.md).

The second snapshot of v0.0.54: the first full build of the whole game since v0.0.53, with everything that reached
the development line since dev1. The game needs 32 MB of Fast RAM; the emulator presets of this snapshot have it.
What dev1 brought (the characters' records, the scripts that use them, travel services, NPC Gallery v2.0 and more)
is listed in its [notes](RELEASE-v0.0.54-dev1.md).

This snapshot is a reuse build, not a build from scratch: the builder rebuilt the world once on the caches of the
v0.0.53 release build, then rebuilt only what the Daedric shrine entrance fix changed. A build from scratch of the
same source comes before the v0.0.54 release.

## New since v0.0.54-dev1

- **Characters move by what they are doing.** Every animation group of the humanoid characters is now chosen by
  their state (standing, walking, running, fighting, casting, dying), by OpenMW's rules, and the first-person hands
  play their own clips. Not checked in game yet.
- **Thirty-five blocked entrances open.** Doorways in the outdoor world that the converted collision still closed
  off can be walked through and used: a fix for
  [DOOR-USE-COLLISION-FILLED-53](../../bugs/DOOR-USE-COLLISION-FILLED-53.md). Not checked in game yet.
- **Weather and smoke, fog indoors.** Rain and smoke follow the game's own tables, and interiors get their fog.
  Not checked in game yet.
- **Levelled creatures outdoors.** Outdoor creatures come from the game's levelled lists, as in the original, and
  creatures have more of their animations. Not checked in game yet.
- **Interface.** A crosshair, a key that hides the HUD, a notice at locked doors, an arrow for you on the map and the
  console's command history. Not checked in game yet.
- **Hair.** Characters' hair is kept whole instead of being cut back to fit a budget, the player's body has hair
  too, and the heads beside whole hair keep enough triangles (136 to 178; they had dropped to 28 to 52 in the first
  whole-hair bake, [NPC-HEAD-STARVED-WHOLE-HAIR-54](../../bugs/NPC-HEAD-STARVED-WHOLE-HAIR-54.md)). Not checked in game yet.
- **Magic effects (experimental, off by default).** Spells can show the game's own effect textures as sprites and
  particles: the glow on the casting hands, the bolt in flight and the burst where it lands, with their sounds
  ([MAGIC_EFFECTS.md](../../MAGIC_EFFECTS.md)).
- **The scripts go further.** With the experimental scripts on (`dbg mwscript on`), 715 of the game's scripts now run
  whole, and the scripts can ask a character's current AI package. Not checked in game yet.
- **Faster test builds.** A change to the engine, or to a part of the builder the world does not use, no longer makes
  the builder rebuild the CHIM world, which took hours each time. This snapshot rebuilds the world once, for the
  changes above that the world really uses.

## Known in this build

- Some of the Suran dancers have no hair at the back of the head
  ([NPC-HAIR-BACK-MISSING-53](../../bugs/NPC-HAIR-BACK-MISSING-53.md)).
- One of the six GitHub test parts takes about six times as long as the others
  ([CI-TEST-SHARD-ONE-SLOW-53](../../bugs/CI-TEST-SHARD-ONE-SLOW-53.md)).
- Some large interiors, in Vivec above all, are still loading in when you are already there
  ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- Everything else is in the [bug register](../../BUGS.md).
