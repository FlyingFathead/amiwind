# Original door mapping

_Last updated with AmiWind v0.0.54-dev1 (27 October 2026)._

<!-- contents start -->
## Contents

- [Ordinary hinged doors (v0.0.48-dev2)](#ordinary-hinged-doors-v0048-dev2)
  - [Locks (load doors and hinged doors)](#locks-load-doors-and-hinged-doors)
  - [The worked example: the census hall door](#the-worked-example-the-census-hall-door)
  - [In-game check (pending)](#in-game-check-pending)
- [The door check in every build (v0.0.53)](#the-door-check-in-every-build-v0053)

<!-- contents end -->

The converter reads base DOOR records and their placed CELL references from the
maintainer's Morrowind.esm. A door's model/name/script and open/close sound IDs belong
to its base record. Each placement has its own reference number, transform,
scale and optional teleport destination. Do not infer a return link from a shared
base model: the other side is a separate placed reference.

| Source field | Meaning | AmiWind conversion |
| --- | --- | --- |
| DOOR NAME/MODL/FNAM | Base ID, model and displayed name | Retained in the private catalogue |
| DOOR SCRI/SNAM/ANAM | Script, opening sound, closing sound | Sounds played by load doors and hinged doors; scripts not run (flagged in the hinged door table) |
| CELL FRMR/DATA/XSCL | Placed ID, XYZ/rotation and scale | Stable audit identity and transformed mesh bounds |
| CELL FLTV/KNAM/TNAM | Lock level, key, trap of a placed door | Hinged door table: locked doors stay shut (see below) |
| DODT | Destination XYZ and rotation | Quarter-scale coordinates and destination yaw |
| DNAM | Named interior destination | Empty/absent means an exterior world position |

Interior coordinates are local to that cell. Exterior positions are world
coordinates; AmiWind subtracts the current exterior origin before quarter scaling.
The destination is a feet position, converted to the standing body's origin and
checked against collision/floor geometry when the destination map loads.

`tools/prepare_doors.py` now resolves the configured area through
`config/seyda_area.json`. The private audit contains 43 teleport placements,
including Addamasartus and both Tradehouse entrances. `scene-doors.txt` stores
source/target map IDs, transformed activation bounds, arrival, yaw and the
original destination label. All configured destinations have converted maps.
An unsupported destination still displays “Interior not found.” and preserves
location/state. Lock/key rules and general door scripts remain unfinished.

The Tradehouse front-door round trip passed a native emulator check. All scenes
also loaded through the inspector. This is not exhaustive validation of all
43 links or the introductory quest route. Original arrival coordinates are
retained, then checked with the standing hull and floor search. The private
catalogue retains each placed reference, including separate basement doors.

The prison hatch is `chargen_shipdoor`, an overhead teleport door. Activate its
visible surface to load the exterior deck. It does not require a physically
swinging lid. The exterior hatch is the separate `CharGen_ship_trapdoor`
reference. Aiming uses the transformed model bounds with half-unit padding,
a 56-unit reach and a world occlusion trace. AWD1 and the old single-origin format remain
readable for older conversion bundles. Both supported directions preserve current
health/hand state and queue at most one map load per activation.

Hostile-pursuit, companion eligibility and original teleport-door rules are recorded in the planned [NPC cell-traversal requirements](NPC_CELL_TRAVERSAL.md); no cross-boundary NPC gameplay is claimed as shipped.

This remains one active BSP at a time. Door mapping does not implement general lock/key rules, ownership,
character-creation gates or persistent reference state.

## Ordinary hinged doors (v0.0.48-dev2)

A placed DOOR reference without a destination (no DODT) is an ordinary hinged door: the game has 1,026 of them in
Morrowind.esm, 729 unlocked. Before v0.0.48-dev2 they were drawn and solid but never opened (AW-20260928-12); only
the census hall door had its own story rule, which snapped it open. Now the use key (E) opens one and the next use
closes it, the census hall door included: the story only holds its lock ([the worked example](#the-worked-example-the-census-hall-door)).

How it behaves (rules learned from OpenMW, our own code: `apps/openmw/mwclass/door.cpp` `Door::activate` and
`apps/openmw/mwworld/worldimp.cpp` `World::rotateDoor`):

- The door turns about its placement's origin and the Z axis (the model's hinge) by 90 degrees, at 90 degrees a
  second: one second to open, one to close. The original's Z rotation grows by 90; AmiWind's yaw is its negative,
  so an opening door's yaw falls by 90.
- Opening plays the DOOR record's Open Sound (SNAM), closing its Close Sound (ANAM), at the door. A use while it
  turns reverses it from where it is.
- A step that would turn the door into the player or a solid actor is undone: the door holds and its sound stops,
  and it goes on once they step aside. It never pushes anyone and never closes on the player. When it holds against
  the player, the screen says "The door is obstructed. Step aside." once for that hold. These words are AmiWind's:
  the original holds the door without a word (no game setting, script or message in Morrowind.esm says anything;
  OpenMW's `World::rotateDoor` only stops the turn). They come from the census hall door's earlier story rule.
- A locked door (a lock level above 0, or a key named: the rule OpenMW uses for content files) stays shut and plays
  the original `LockedDoor` sound; the prompt says "Locked". Keys, lockpicks, Open spells and traps are not in the
  game yet: the table records them (226 doors name a key, 166 a trap, 90 of those unlocked; an unlocked trapped
  door opens without its trap for now). The 3 doors with a script open like the others (scripts are not run). A
  story rule can hold a door's lock in place of its lock level (`aw_hinged_story`, today only the census hall door).
- The prompt shows the door's name (DOOR FNAM) with "Open: E", "Close: E" or "Locked"; the reach is the load
  doors' 56 units, and an actor or object in front hides the door.
- Doors close again when the map is loaded again; open doors are not in saves yet (the census hall door is: the
  story keeps whether it stands open).

The builder writes `id1/hinged-doors.txt` (format AWHD1) in the door-audio step (`tools/prepare_door_audio.py`):
the converted samples (the same `sound/doors/d<hash>.wav` files as the load doors), one row per DOOR record (open
and close sample, name) and one per placed door (reference, record, lock level, flags: locked, key, trap,
script). The engine (`engine/aga/src/aw_hinged_door.c`) reads it once (about 40 KB of fixed tables) and finds a map's
doors by reference:

| Door form | Where | How it turns |
| --- | --- | --- |
| Room maps (legacy room maps and the CHIM-native towns' room maps, `chim_rooms.py`) | each placement is a `func_wall` edict at the placement's origin and yaw | the edict's yaw: drawn by `R_RotateBmodel`, collided by `SV_ClipMoveToEntity`, relinked with the rotation box |
| CHIM frame maps outdoors | the door is a chunk placement (no edict) | its placement's yaw, collision sine and cosine (and the 0.8 placement matrix) on every copy in the zone; its box covers every pose, so nothing is relinked; a chunk loaded again starts at the door's present pose |
| CHIM rooms (`maps/<room>.chim` on the interior store, [INTERIOR_STORE.md](chim/INTERIOR_STORE.md); the batch rooms of `--room-batches` too) | the door is a placement of the room record `chimi/rooms/<room>.crm`, which keeps its reference (no edict) | `chim_room.c` asks the same hook as the frames when the room loads; the placement's yaw, sine and cosine and matrix (`ChimRoom_DoorYaw`), its collision through the placed path (`ChimRoom_DoorClip`); its box covers every pose. An activated object's collision-only marker edict for the same reference (the census hall door's) stops being solid |
| Legacy town region maps (retired) | captured scenery | a hinged door is kept out of the capture and works as a room map door |

Not supported yet: doors with a
tilt (12 in the game; their tilt is baked, so they turn about the world Z axis), Tribunal and Bloodmoon doors (the
table reads Morrowind.esm only). Collision against a turned door has the known limit of every yawed model
(CHIM-YAW-PLAYER-BOX-TURNS-46: the player's box turns with it, up to about 2.9 units at 45 degrees).

Cost on a 68040: a closed or open door does nothing per frame. The prompt looks only when a door is within reach
(one point trace); a turning door (one second) is turned and tested against the actors near it each frame.

For testing, `dbg door` opens or closes the door under the crosshair even when it is locked; `dbg door status` and
`dbg door list` show the table and this map's doors.

### Locks (load doors and hinged doors)

Until v0.0.54 every load door opened for everyone. Now the same table carries the locks of the load doors too: one
`K <reference> <lock level> <flags> [<key ID>]` row (references ascending) for every load door that is locked in the
game data (a lock level above 0 or a key, as OpenMW's `components/esm3/cellref.cpp` reads content files: 119 in
Morrowind.esm) and for every hinged door that names a key, and one `U` row with the game setting `sKeyUsed`. A
locked door, load or hinged, follows the original's rule as OpenMW's `apps/openmw/mwclass/door.cpp` describes it:

- the player carrying the door's key opens it, and the message box says "<the key's name> used to open lock";
- otherwise it stays shut with the `LockedDoor` sound, and the prompt says Locked;
- in god mode (`dbg god`) the player goes through, and the message box says "God mode used to enter a locked door"
  (the maintainer's request, 25 October 2026);
- a script's Lock and Unlock (the object state) count, and `GetLocked` on a load door reads its level;
- a story rule (the census hall door) is not a lock: it holds in god mode too.

Lockpicks and the Open spell do not exist yet, so `dbg doorlocks off` switches every lock off until they do
(default on, not saved; `dbg doorlocks` prints it).

### The worked example: the census hall door

The first door a new game meets after the boat is the one out of the census office's first room, toward the guard
and the next building: you cannot leave that room without your release papers. It is the model for every other
door: the same record fields, the same table rows, the same turn. Its values, read from Morrowind.esm:

**The DOOR record** `chargen door hall`: name (FNAM) "Door"; model `d\In_C_door_wood_square.nif`; Open Sound (SNAM)
"Door Latched Two Open" (`Fx\trans\drlatch_opn2.wav`); Close Sound (ANAM) "Door Latched One Close"
(`Fx\trans\drlatch_cls.wav`); no script (SCRI).

**The placement**: reference 172860 in "Seyda Neen, Census and Excise Office"; position 258.30, 255.69, 189.97; Z
rotation 3.14 radians (180 degrees); scale 1.02; lock level 100 (FLTV), no key (KNAM), no trap (TNAM); no
destination (DODT), so it is a hinged door, not a load door. The model's origin is its hinge edge, so the door turns
about the placement's origin. In the census map (quarter scale, the cell's own origin) it stands at about 64.6,
63.9, 47.5 with AmiWind yaw -180 (the negative of the original's Z rotation); opening takes the original's Z
rotation to 270 degrees, AmiWind's yaw to -270.

**Why it is shut, in the original**: the door itself has no script. It is locked at level 100, and the door guard
next to it ("chargen door guard") runs the script `CharGenDoorGuardTalker`: within 180 units of the player he checks
whether the player carries the papers (the item `CharGen StatsSheet`, taken from the desk). Without them he repeats
his "no further without your papers" line (`vo\Misc\CharGen Door1.wav`) every few seconds; with them he says his
second line (`CharGen Door2.wav`, go on to the next building and see Sellus Gravius), unlocks "CharGen Door Hall" and
plays the "Open Lock" sound. From then on it is an ordinary unlocked door.

**How AmiWind does it today** (`engine/aga/src/aw_opening.c`, `aw_hinged_door.c`):

- The papers: the desk's papers (reference 172859, `AW_REF_CENSUS_PAPERS`) are read and taken in the opening's
  reader; `AW_Papers()` is then true.
- The guard: the opening's proximity rule speaks `chargen_door1` every 3 seconds while the player is within 45 units
  (180 game units) without papers, and `chargen_door2` with them; when he has spoken it, `aw_story.hall` is set (the
  original's Unlock). Talking to him (E) does the same. The "Open Lock" sound is not played yet.
- The door: a hinged door like every other (its row is in the table: lock level 100, flag locked). The story hook
  `AW_OpeningHingedStory` holds its lock: locked while `aw_story.hall` is 0, unlocked after. Before that it was a
  separate story rule that snapped the door to yaw -90 (the other side: DOOR-HALL-SWING-DIRECTION-48); now it turns
  by the original's rule.
- Whether it stands open is kept in the save (`aw_story.hall_open`): a loaded game or the census map loaded again
  shows it as it was left.

**How the builder carries it**:

- `id1/hinged-doors.txt` (AWHD1, the door-audio step): a `W` row for each of its two samples (`doors/d<hash>.wav`,
  the same files as the load doors), a `B` row for `chargen door hall` (open sample, close sample, "Door") and the
  row `D 172860 <B> 100 1` (lock level 100, flag 1 = locked); the `L` row names the `LockedDoor` sample.
- `id1/door-sounds.txt` (AWSFX2) keeps a row for it too (the opening scene's links and the hall door), as before.
- The census map `maps/census.bsp` (`tools/prepare_census.py`, a room map in the default build: the CHIM rooms are
  made from the area rooms, which leave the census office and the prison ship to their own converters): the door is
  a `func_wall` edict with `"aw_ref" "172860"`, its own brush model at the placement's origin and its yaw.
- In a CHIM room it would be the room record's placement with reference 172860, plus the collision-only marker edict
  every activated object keeps (`tools/chim/frame_map.py keep_activated`); the hinged door code takes the placement
  and makes the marker non-solid. It is not a load door, so it has no door bank row.

**What the player sees and hears**:

- Before the papers: aiming at it within reach (56 units) shows "Door" and "Locked". The use key plays the locked
  sound and the line "The door is locked. Show your papers to the guard."; nothing turns. The guard repeats his line.
- After the guard's second line: "Door" and "Open: E". The use key plays the latch opening sound at the door and it
  turns 90 degrees in one second; its collision turns with it, so the doorway is free as it opens. "Close: E" turns
  it back with the latch closing sound.
- Standing in its swing: it turns until it would touch you and holds there, its sound stops, and the screen says
  "The door is obstructed. Step aside." once; step back and it finishes.

**Each form**:

| Form | The door is | It turns by |
| --- | --- | --- |
| Room map (`census.bsp`, the default build) | edict `func_wall` with `aw_ref` 172860 | the edict's yaw (`R_RotateBmodel`, `SV_ClipMoveToEntity`, relinked with its rotation box) |
| CHIM room (if the office became one) | room record placement, reference 172860 | `ChimRoom_DoorYaw` / `ChimRoom_DoorClip`; the marker edict is not solid |
| CHIM frame (outdoor doors, e.g. the census gates) | chunk placement | `ChimChunks_DoorYaw` / `ChimChunks_DoorClip` on every copy |

**Checking it**: `dbg door status` prints the table and this map's doors ("Hinged doors: 1026 in the table, N here
(E room map edicts, C CHIM placements), 0 moving"); `dbg door list` prints each, for this door a line like
`172860 edict 0/90 deg lock 100 locked (story) at 64 63 47` before the papers and without "locked" after;
`dbg door` aimed at it turns it whatever the lock (testing only). In a CHIM room, `chim` also says how many of the
room's placements are hinged doors.

### In-game check (pending)

In FS-UAE, on a build with this change (v0.0.48-dev2 or later). The census office's doors come first: they are the
first a new game meets.

1. **New game, at the desk without the papers: the hall door refuses; take the papers: it opens.** Start a new game
   and go up to the census office's first room. Before taking the papers, aim at the hall door (172860, beside the
   door guard): "Door", "Locked"; press E: the locked sound and "The door is locked. Show your papers to the
   guard."; the guard repeats his line. Take the papers from the desk, walk up to the guard: he says his second
   line. Aim again: "Open: E"; press E: the latch opening sound, the door swings 90 degrees in about one second; walk
   through. Note which way it swings against the original (DOOR-HALL-SWING-DIRECTION-48). Close it with E: the latch
   closing sound.
2. **The hall door holds against you.** Open it, stand in its swing, close it: it stops against you, its sound stops,
   "The door is obstructed. Step aside." shows once; step back: it shuts. The same while opening.
3. **The hall door keeps its state.** Leave it open, save, load: it is still open. Go out and come back in: still
   open.
4. Seyda Neen, Census and Excise Office: the Sturdy Arched Door (reference 397586, unlocked). Open it, hear "Door
   Heavy Open"; it swings away in about one second; walk through; close it, hear "Door Heavy Close".
5. Seyda Neen: the two Census and Excise gates outdoors (321262, 321263, CHIM frame): the prompt says "Locked" and
   the use plays the locked sound; `dbg door` opens one (a CHIM placement turning) and you can walk through; walk
   away until its chunk unloads and come back: it is still open.
6. Seyda Neen, Arrille's Tradehouse: the door 331481 (lock 40, key_arrile) stays locked.
7. Balmora in CHIM rooms (the default `--interior-format chim`): Council Club 57033 and 484383, Guild of Fighters
   56722 and 56780, Lucky Lockup 42064 and 42069, Eastern Guard Tower 213135, Western Guard Tower South 384326 and
   384332, Hlaalo Manor 378371, Hlaalu Council Manor 378381, Drarayne Thelas' House 378032 open and close with
   "Door Latched One/Two Open/Close"; walk through each way. `chim` shows the room's hinged doors; `dbg door list`
   shows them as CHIM placements.
8. Balmora locked doors stay shut, in CHIM rooms too: Eight Plates 244039, 56661, 56691; Lucky Lockup 42065; The
   Razor Hole 56408; Guild of Fighters 56718; Morag Tong 57288, 378730; Nerano Manor 64596; Milie Hastien 65187;
   Ra'Virr 131949; South Wall Cornerclub 367744; Council Club 244040.
9. Tharys Ancestral Tomb (in the Balmora MiniWind's CHIM rooms), where the maintainer first saw the doors stay shut;
   the same Balmora rooms on `--interior-format bsp` (room maps); and the doors of a batch room (`--room-batches 1`).
10. Frame time with a door turning and with it still (the like-for-like A/B rule), in a room map and in a CHIM
   room: no change while it is still.

Original transition sound IDs of load doors are played by the door-audio catalogue (`id1/door-sounds.txt`).

## The door check in every build (v0.0.53)

Every exterior entrance of the original (1,102 load doors from an exterior cell into an interior) is checked by the
image step of a whole-world build, door, then entrance, then interior, and the way back out:

- the door audit (`tools/door_audit.py`): the frame or town that holds the door, whether its CHIM frame places the
  door model, its row in that frame's door bank as the engine keeps it, its use box against the placed door, the room
  it leads to, the arrival inside that room, the room's exit back to the right exterior, and the original lock (level
  and key). It writes `door-audit.md`, `door-audit.json` and the per-door checklist `door-checklist.csv` beside the
  image (private: made from your game data);
- the door engine check (`tools/door_engine_check.py` with `tools/door_engine_check.c`): the engine's own door code
  (`aw_scene.c` with the files the scene test links) compiled for the host and run over the image's door banks,
  open-world directory and maps. A region frame's door is reached by a walk over a frame border from a neighbouring
  frame (the streamed crossing of `chim crossing 1`), a town's door in its town; at the spot where the game puts a
  player who walks out of that room, facing the door, the prompt must read `(Enter: E)`, the use key and a script's
  Activate must each load the door's room, and in the room the exit must lead back out. It takes seconds for all
  1,102 and writes `door-engine-check.md` and `door-engine-check.json`;
- the wall in the way (the same check, region-frame doors): the CHIM world's own collision (`chim.collision`, the
  frame's chunk terrain and the hulls of everything it places) gives where a player stands in front of the door
  (straight out from its face, 12 units to either side of that line and on the way to the room's way-out arrival, at
  the use reach and nearer, up to 80 units over the threshold, on a floor the player does not slide off; on and
  beside a trapdoor), and the engine's wall trace from the eye to the door's middle,
  upper and lower part. The engine refuses the use when a surface lies more than the doorway slack (`DOOR_USE_SLACK` in
  `aw_scene.c`, 16 units) before the use box: the converted collision of an entrance may close the doorway a few units
  in front of the door, which the original still opens. Town doors are not traced yet.

The usable counts only go up: `config/door-check-baseline.json` holds the last counts (from v0.0.53-dev2: 1,102 usable
after walking in, 1,102 both ways, 1,067 with the wall traced: the other 35, most of them Daedric shrines whose steps
the player slides off, are DOOR-USE-COLLISION-FILLED-53, for v0.0.54), and a whole-world image that uses fewer stops the
build. A build that uses more raises the numbers in that file. From v0.0.54 the check also goes over every entrance:
an entrance the wall check cannot reach must be listed in `config/door-check-known.json` with its measured reason and
register class, or a whole-world image stops the build; a listed entrance the check reaches again is named so it
leaves the list. The 35 of v0.0.53 came from three converter causes, each fixed for its whole class (measured on the
v0.0.53 image's own frames, the models rebuilt with the CHIM model builder's workers):

- the Daedric shrine entry steps (`ex_dae_ruin_entry`, 24 entrances): the stair rules turned some of its collision
  pieces into thin plates that need exact standing bevels, but a CHIM model took one flag for the whole model and
  dropped those plates' own request, so they got the approximate axial bevels and their standing hull grew over the
  steps beside them. A CHIM model now takes exact bevels when any of its pieces asks for them (its standing hull is
  then compiled and checked as for every exact model). That alone left 10 of the shrine entrances without a standing
  spot in the v0.0.54-dev2 world (its compiled pieces still filled the room over the steps), so the shrine entry also
  takes the standing-room rule below (143.6 to 182.6 KB of collision per variant);
- the Redoran guard towers (`ex_redoran_tower_01`, 8 entrances: the trapdoors on top and a hut door at the foot): a
  convex piece of the tower's authored collision closed the top room, solid from just over the trapdoor's floor. A
  convex piece may no longer fill the room a player stands in over a floor of the same mesh (more than a step up to
  the standing height): it is split, and a piece that cannot be split becomes the authored plates of its triangles
  (the tower: 54 to 81 pieces, 32.9 to 48.3 KB of collision). The rule applies to the meshes of the measured table
  `config/collision-standing-room.json` (a mesh joins when a door or walk-route check fails on it and the rule clears
  it); on every mesh it would change 190 of 1,380 meshes;
- the Dwemer doors of Nchuleft and Bthungthumz (2): the coarse terrain tiles (every 128 units) bridged the dip the
  entrance sits in, 170 to 190 units over a threshold the original ground meets. A load door on the ground whose coarse
  ground stands more than a step over the original keeps the original 32-unit ground samples around it, as the ground
  under residents does (measured on the v0.0.53 image: 251 entrances in 192 frames, most of them cave and tomb doors
  the coarse ground buried 10 to 60 units).

The shipwreck's upper trapdoor (Unmarked Shipwreck) stays listed: its tilted deck is steeper than the walk.
For A/B tests on development builds only: `AMIWIND_COLLISION_STANDING_ROOM=off` (or `all`, every mesh),
`AMIWIND_COLLISION_PLATE_BEVELS=drop` and the build setting `terrain_door_detail` `off` keep the methods before; an
rc or final build refuses the environment values before any stage. The same check with the v0.0.52 scene code over the same image finds 272: the
other 830 region-frame entrances were dead after walking in (DOOR-BANK-STREAMED-FRAME-51).

`dbg door roulette [SEED]` loads the player straight into a random room of the disk, at the room's own start, and
prints its name, map id and cell number with the seed; the same seed loads the same room again (random tests of
interior loading).

Reference: [OpenMW, Doors and Connecting Cells](https://openmw.readthedocs.io/en/latest/reference/modding/doors-and-teleports.html)
corroborates the interior-name/exterior-coordinate distinction. The owned master
is the source of the specific prison/town links.
