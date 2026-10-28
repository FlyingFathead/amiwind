# AmiWind v0.0.48-rc1: Inner CHIM & Actors On Stage

Release candidate, 23 October 2026. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.47](RELEASE-v0.0.47.md); development snapshot [v0.0.48-dev1](RELEASE-v0.0.48-dev1.md).

The outdoors went on CHIM in the last releases; now the indoors follow. Every interior of the base game but two is
built as a CHIM room, the people the game places in those rooms stand in them with their full set of animations,
and the plants in them can be picked. The places that need more than 16 MB of Fast RAM are marked when the game is
built and say so at the door instead of failing. The emulator presets start with 32 MB of Fast RAM.

<!-- TODO (main session, after the rc1 build): replace the interior and actor counts below with the rc1 build
summary's numbers (interiors planned / converted / kept classic, room NPCs, rooms and frames marked for 32 MB),
then delete this comment. -->

## What changed since v0.0.47

### The interiors: Inner CHIM

- **Every base-game interior on CHIM rooms.** The builder plans all 1,134 interiors of the base game as CHIM rooms
  and converts 1,132 of them; the prison and the census office stay classic room maps for now. Rooms with water or
  lava are converted too ([CHIM-ROOMS-WATER-LAVA-48](../../bugs/CHIM-ROOMS-WATER-LAVA-48.md)), and 27 rooms a wrong size
  estimate had set aside are back in ([CHIM-ROOM-ESTIMATE-48](../../bugs/CHIM-ROOM-ESTIMATE-48.md)). Counts from the rc1
  build summary.
- **Actors on stage.** The NPCs and creatures the game places in a room stand where the game puts them: 2,359 room
  NPCs in the v0.0.48-dev2 build (counts from the rc1 build summary). They carry the full animation kit; the alias
  model budget grew from the 16 MB era's 512 KiB to 768 KiB, with models streamed in as they are needed, and every
  NPC greets with its own voice
  ([NPC-GREETINGS-LIBRARY-MUTE-48](../../bugs/NPC-GREETINGS-LIBRARY-MUTE-48.md)).
- **Plants in CHIM rooms can be picked.** The rooms place their harvestable plants as pickable objects instead of
  baked scenery ([ROOM-BATCH-HARVEST-48](../../bugs/ROOM-BATCH-HARVEST-48.md),
  [CHIM-ROOM-HARVEST-DOUBLE-48](../../bugs/CHIM-ROOM-HARVEST-DOUBLE-48.md)).
- **The Progress Tracker shows the interiors**: a room list and counts per island and state
  ([TRACKER-INTERIORS-NOT-SHOWN-48](../../bugs/TRACKER-INTERIORS-NOT-SHOWN-48.md)).

### 32 MB of Fast RAM, and what 16 MB still runs

- **32 MB is the safe minimum and the default** of the emulator presets and the launcher; more is used
  automatically ([RAM-REQUIREMENT-32MB-48](../../bugs/RAM-REQUIREMENT-32MB-48.md),
  [why 32 MB](../../REAL_HARDWARE.md#why-32-mb-of-fast-ram)).
- **Most of the island still runs on 16 MB.** A place too large for 16 MB is built at full quality and marked when
  the game is built: about 50 interiors and 5 region frames (counts from the rc1 build summary). On 16 MB (or with
  Extra RAM off) its door shows "Sorry, but this interior cannot be run with 16MB of Fast RAM." and "Press ENTER to
  return." on the loading art and returns you to where you stood; a marked frame says "this area" and keeps you
  at its border. A saved game, a start or a console jump into a marked place is refused the same way
  ([CHIM-32MB-SAVE-ENTRY-48](../../bugs/CHIM-32MB-SAVE-ENTRY-48.md)). On 32 MB and more these places load as usual.

### The game

- **The Stats window (P)** with the character's attributes, skills and health, magicka and fatigue, and a **Magic
  window placeholder (O)** with the race's and birthsign's spells, both in the original look. Both are in
  Options > Controls next to the inventory (I), journal (J) and map (M), and every one of these keys can be rebound
  ([UI-STATS-WINDOW-48](../../bugs/UI-STATS-WINDOW-48.md), [keymaps](../../KEYMAPS.md)).
- **Original movement speeds.** Walking, running and swimming follow the character's Speed, Athletics and load,
  with running fatigue; `dbg superspeed on|off` gives back the old fixed fast speeds
  ([PLAYER-MOVEMENT-STATS-PARITY-39](../../bugs/PLAYER-MOVEMENT-STATS-PARITY-39.md)).
- **Campfires burn.** Campfires, braziers, fire pits and flame lamps outdoors have their flame and light the objects
  around them; `dbg campfires on|off` turns them on and off
  ([CHIM-EXTERIOR-FLAMES-MISSING-48](../../bugs/CHIM-EXTERIOR-FLAMES-MISSING-48.md)).
- **Sound markers.** The original's 2,163 sound markers are placed, and the game's compiled scripts play them with
  `dbg mwscript on` (experimental, off by default; [MWSCRIPT-AUDIO-FIRST-48](../../bugs/MWSCRIPT-AUDIO-FIRST-48.md)).
- **Options**: mouse sensitivity and the crosshair colour and shape, on four framed pages.

### CHIM 0.2.2

- CHIM moves to 0.2.2 with the new [CHIM compatibility table](../../chim/README.md#compatibility): each CHIM version names
  the oldest version whose worlds and caches it reads. 0.2.2 reads everything 0.2.1 built, and the version label no
  longer counts in the builder's stage keys, so a release step no longer rebuilds the CHIM world
  ([BUILD-CHIM-LABEL-IN-KEYS-48](../../bugs/BUILD-CHIM-LABEL-IN-KEYS-48.md)).

### The builder

- **Reuse keys.** Stages key on what they really read: stages whose earlier outputs differed from their records,
  stages that counted whole classes or files they never read, and the room and script stages that left inputs out of
  their keys are rebuilt only when their inputs change.
- **Build speed.** The CHIM stage no longer recomputes every frame's visibility, the stages hand their pools units
  large enough to keep every core busy, the CHIM and room stages no longer starve each other of memory, room
  residents are cached, and the image step's serial parts run on every core.
- **Disk layout.** A boot payload larger than one partition moves the interior store, the actor models and maps to
  the world volume, so every partition stays under 2 GiB
  ([IMAGE-BOOT-PAYLOAD-OVER-2GIB-48](../../bugs/IMAGE-BOOT-PAYLOAD-OVER-2GIB-48.md)); identical resident models and
  greetings are stored once.
- The build summary says how many interiors a build includes and how many places it marked for 32 MB.

## Known in this build

- [ROOM-RESIDENT-MODELS-SIZE-48](../../bugs/ROOM-RESIDENT-MODELS-SIZE-48.md): the room residents' models still take about
  1.35 GB, one model set per resident.
- [BUILD-REUSE-VERIFY-DISK-48](../../bugs/BUILD-REUSE-VERIFY-DISK-48.md): a reused CHIM stage reads and hashes all of its
  outputs again.
- [ACTOR-MODEL-ERROR-UNNAMED-48](../../bugs/ACTOR-MODEL-ERROR-UNNAMED-48.md): the actor model check's stops name neither the
  model nor the refused field.
- [CHIM-ROOM-EFRAG-LIMIT-48](../../bugs/CHIM-ROOM-EFRAG-LIMIT-48.md) and
  [CHIM-ROOM-SURFCACHE-LIGHT-48](../../bugs/CHIM-ROOM-SURFCACHE-LIGHT-48.md): large rooms can leave placements undrawn,
  and the same model at different room light levels rebuilds its surfaces. CHIM rooms light each placement at one
  level, so some rooms look flatter and brighter than the old room maps.
- [CHIM-REGION-DOORS-NO-ROOMS-48](../../bugs/CHIM-REGION-DOORS-NO-ROOMS-48.md): the load doors of the region frames do not
  lead into rooms yet.
- [INTERIOR-PLACED-ITEMS-47](../../bugs/INTERIOR-PLACED-ITEMS-47.md): items, books and containers in rooms are not live
  objects yet.
- [HARVEST-ORGANIC-PLANTS-47](../../bugs/HARVEST-ORGANIC-PLANTS-47.md): only the small mushrooms can be picked.
- [MWSCRIPT-AUDIO-FIRST-48](../../bugs/MWSCRIPT-AUDIO-FIRST-48.md): the game's scripts, and with them the sound markers,
  run only with `dbg mwscript on`.
- [NPC-VOICE-NONASCII-IDS-48](../../bugs/NPC-VOICE-NONASCII-IDS-48.md): two Orc NPCs with accented record ids stay silent.
- [PLAYER-JUMP-ORIGINAL-RULES-48](../../bugs/PLAYER-JUMP-ORIGINAL-RULES-48.md): the jump height and air control are still
  Quake's.
- [CHIM-ACTORS-TOWN-RETURN-EMPTY-47](../../bugs/CHIM-ACTORS-TOWN-RETURN-EMPTY-47.md): walking into or out of a town is
  still a level change.

The Vivec Arena Pit runs slowly, and the rest is as in the [v0.0.47 notes](RELEASE-v0.0.47.md#known-in-this-build);
everything else is in the [bug register](../../BUGS.md), and what comes next is in the [roadmap](../../ROADMAP.md).
