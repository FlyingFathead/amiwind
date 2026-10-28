# AmiWind v0.0.52: Skeletons Of Society, Vvardenfell Edition

Released 26 October 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.51](RELEASE-v0.0.51.md); development
snapshots [v0.0.52-dev1](RELEASE-v0.0.52-dev1.md), [v0.0.52-dev2](RELEASE-v0.0.52-dev2.md) and
[v0.0.52-dev3](RELEASE-v0.0.52-dev3.md).

Every character of Vvardenfell now moves by one shared skeleton and one shared table of every action a humanoid can
do, as in the original game, instead of frames baked one character at a time. The base game's 2,612 placed characters
take 512 MB of models instead of 3.2 GB, and each of them can walk, run, swim, fight with every weapon, cast, block,
dodge, fall and die. Dagoth Ur and the Heart of Lorkhan are in Akulakhan's Chamber for the first time.

## What changed since v0.0.51

- **One skeleton for everyone.** Residents, guards and the actor library are each one model in its skeleton's rest
  pose; one table holds the actions (about 140 groups: idles, walking, running, sneaking, swimming, every attack set,
  spellcasting, blocking, hits, knockdowns, deaths, the torch, the inventory poses) on a 29-bone stick figure at 8
  frames a second, with the hands closing on their weapons. Two tables serve everyone: the common one, which also holds
  the women's own walk and idles, and the beast races' (Argonians and Khajiit, on their toes, with the tail). The
  table carries each action's phases and the footsteps. Baked characters stay a build option (`--npc-anim-type 1`).
- **A sixth of the space.** 512 MB of character models against 3,222 MB baked, plus about 1.2 MB of tables; the 97
  characters that never fitted the baked budget all fit now.
- **Cheap to draw.** A character is posed only when its animation frame changes, characters of one model on one frame
  share the pose, and up to 32 posed frames are kept where Fast RAM allows. A posed character is drawn only when the
  box of the pose it stands in is on screen. On the slow 68040 preset, at Balmora's arrival, a whole frame takes
  1,261 ms with skeletons against 1,272 ms baked (0.9 % faster), the characters 25.1 ms against 25.7 ms; with eight
  characters changing their action every frame, +5.6 % ([SKEL-RUNTIME-COST-52](../../BUGS.md)).
- **Carried things ride the bones.** Weapons, shields and the guards' torches (by the day and night cycle) hang on the
  table's hand bones; a guard who shows his torch at night holds it up with his left arm, on the table's torch group
  ([SKEL-ITEM-TAGS-52](../../BUGS.md)). The enhanced combat's block and dodge play as before.
- **Dagoth Ur and the Heart of Lorkhan.** No earlier build placed them: Dagoth Ur stands in the Facility Cavern and in
  Akulakhan's Chamber as his whole original model, every one of his 2,254 triangles, and the Heart hangs where the game
  puts it. Their scripts (the fight, the strikes on the Heart) come with the script work of v0.0.53
  ([scripted actors](../../SCRIPTED_ACTORS.md)).
- **No Software Failure from a full memory.** The Amiga toolchain's `malloc` stops the machine instead of saying "no
  memory"; every allocation of the engine now asks first, so the game copes where it used to stop.
- **A WARNING box under 32 MB** of Fast RAM, before the logo, for five seconds.
- **Akulakhan's Chamber on 32 MB, also coming from a town.** The room, with its activators, Dagoth Ur and the Heart,
  grows into the free Fast RAM. Memory that can be made again (the skeletal characters' tables and posed frames) is
  given back first, and the room's bank grows in 64 KiB steps: on 32 MB, coming from Balmora, the chamber takes
  3,456 KiB and leaves 804 KiB of its zone free
  ([CHIM-ROOM-HEART-CHAMBER-LOAD-50](../../bugs/CHIM-ROOM-HEART-CHAMBER-LOAD-50.md)). The build's room check counts the
  route through a town and the room's own actors, so a room that would not fit stops the build instead of the game.
- **Balmora's canal banks** without dents; **coloured light** in the rooms; **the music** fed through loads.
- **Builds**: the reuse checks found three ways to reuse stale or foreign outputs, all fixed. Every build now stops
  before its first stage when its disk has less than 35 GiB free (a tester's build filled its disk halfway; a
  measured, per-release figure follows in v0.0.53).
- **The Toolkit** shows v0.0.52 in the CHIM inclusion ledger, released with its readback and boot smoke
  (Toolkit 0.1.14).

## Known in this build

- The heads of skeletal characters use the reduced detail (full heads where there is room: v0.0.53); the NPC gallery
  and the player's own body are still baked; Vivec keeps his reduced model.
- Dagoth Ur does not fight or speak yet; nobody attacks on sight yet, and residents idle in place without wandering
  (wander, idles and aggro from each actor's own record: v0.0.53).
- Some large interiors, in Vivec above all, are still loading in when you are already there
  ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
- Doors of the region frames do not open after walking across a frame border until the next load
  ([DOOR-BANK-STREAMED-FRAME-51](../../bugs/DOOR-BANK-STREAMED-FRAME-51.md)): the first fix of v0.0.53.
- The v0.0.51 playtest findings still open (entrances, silt striders, the crosshair, the night speckle, loose fire
  sprites) are in the [bug register](../../BUGS.md) for v0.0.53.
