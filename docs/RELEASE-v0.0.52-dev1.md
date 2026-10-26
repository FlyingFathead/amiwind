# AmiWind v0.0.52-dev1 (in development)

Development snapshot, 25 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.51](RELEASE-v0.0.51.md).

v0.0.52 is called "Skeletons Of Society, Vvardenfell Edition": every humanoid moves by one shared skeleton and one
shared animation table, as in the original game, drawn by the engine's own model renderer
([modular NPCs, method C](MODULAR_NPCS.md#runtime-method-c-one-shared-animation-table-posed-in-the-alias-renderer)).
This first snapshot carries the skeletons and the fixes that were already done.

## New since v0.0.51

- **Every character moves by one shared skeleton.** Residents, guards and the actor library are no longer baked
  frame by frame: each is one model in its skeleton's rest pose, and one shared table holds every action a humanoid
  can do (139 groups: idles, walking, running, sneaking, swimming, every attack set, spellcasting, blocking, hits,
  knockdowns, deaths, the torch, the inventory poses), on a 29-bone figure at 8 frames a second. Three tables serve
  everyone: the common one, the women's walk and idles over it, and the beast races' own (Argonians and Khajiit:
  their walk on the toes, the tail). The table carries each action's phases (equip, release, hit, stop) and the
  footstep sounds as frames.
- **A fraction of the space.** For the base game's 2,612 placed characters: 512 MB of character models against
  3,222 MB baked, plus 1.8 MB of tables; the 97 characters that did not fit the baked budget now all do
  ([NPC-BAKED-WHOLE-DUPLICATION-33](bugs/NPC-BAKED-WHOLE-DUPLICATION-33.md)). The baked characters stay a build option
  (`--npc-anim-type 1`); skeletons are the default.
- **Cheap to draw.** An actor is posed only when its animation frame changes (about 8 times a second), actors of one
  model on one frame share the pose, and every other drawn frame costs what a baked frame costs.
- **Carried weapons, shields and torches** follow the hand bones; guards carry their torches at night, as before, and
  their shields in fights by day ([SKEL-ITEM-TAGS-52](BUGS.md)). The enhanced combat's block and dodge are unchanged.
- **Akulakhan's Chamber fits 32 MB with everything in it.** A room that does not fit its share of the heap grows into
  the free Fast RAM ([ROOM-AKULAKHAN-HEAP-52](BUGS.md)).
- **Balmora's canal banks** keep their tops: the shoreline tiles no longer sag into V-shaped dents between their
  samples ([BALMORA-GROUND-DENTS-51](BUGS.md)).
- **The heart of Lorkhan is back in Akulakhan's Chamber.** Interiors left out every activator but the beds; now they
  keep them all, so the heart, the tavern counters, the shrines, the Dwemer machinery and the Sixth House bells are in
  their rooms again. Lava, waterfalls, mist, steam and bubbles stay out as before
  ([INTERIOR-ACTIVATORS-LEFT-OUT-52](BUGS.md)).
- **Coloured light in the rooms.** A room's light keeps its colour: Akulakhan's Chamber is lit red as in the original,
  tinted lamps tint their room (world format 0.13; [INTERIOR-SUNLIGHT-COLOUR-51](bugs/INTERIOR-SUNLIGHT-COLOUR-51.md)).
- **The music through loads.** The music stream is fed while a level loads, so it does not run dry
  ([AUDIO-LOAD-29](bugs/AUDIO-LOAD-29.md)).
- **Builds.** A build from an empty workspace was checked against the cached v0.0.51 build: 557,483 of the 557,495
  recorded checksums are identical; the rest name their commit.

## Known in this build

- First snapshot of the skeletons: the animation stage that plays every action in MiniWind
  ([SKEL-ANIM-STAGE-52](BUGS.md)) and the in-game frame-time measurement on a slow CPU are still to come; the heads
  use the reduced detail for now ([SKEL-VERTEX-LIMIT-52](BUGS.md)); the NPC gallery and the player's own body are
  still baked.
- The playtest findings of v0.0.51 that are still being worked on are in the [bug register](BUGS.md) and move to
  v0.0.53: entrances that cannot be entered, silt strider travel, the crosshair in inspect mode, the night colour
  speckle, loose fire sprites, NPCs outside the towns without movement animations (the skeletons fix those).
- Everything else is in the [bug register](BUGS.md).
