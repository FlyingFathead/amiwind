# AmiWind v0.0.66-dev2 (in development)

_Last updated with AmiWind v0.0.66-dev2 (14 November 2026)._

Development snapshot, 13 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.66-dev1](RELEASE-v0.0.66-dev1.md); previous release: [v0.0.65: Reintroducing Vvardenfell](RELEASE-v0.0.65.md).

v0.0.66-dev1 was not published on its own: this is the first published snapshot of v0.0.66, and it carries everything
that [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) holds too (its notes list it).

The second snapshot of v0.0.66. **The data of Tribunal and Bloodmoon is part of the build by default.** The builder
already selected both expansions unless told otherwise; from this snapshot the build's cache keys know which expansions
are selected, so switching them on or off rebuilds only what they change and leaves the rest of the world as it was.
This is the road to Mournhold and Solstheim, not their arrival: no finished Mournhold or Solstheim content is in this
snapshot.

Besides that, dev2 carries a large round of work on how the game's people and creatures behave (their own speeds,
fatigue, spells, bows, death and respawn rules), on the map and on finding your way, on containers and the prison ship,
and on the builder's checks. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet.

## New since v0.0.66-dev1

### Tribunal and Bloodmoon in the build

- **Both expansions are selected by default, and the keys know it.** A build's stage keys, unit caches and CHIM unit keys
  follow the expansions that are selected. Switching them on rebuilds only what the expansion files change; a build for
  the base game alone keeps the keys it had.
- **Unit caches are keyed by what each unit reads.** The two readers that merge the base game file with the expansion
  files and read the archives in load order are keyed by what they hand out, not by their code, so a change to a reader
  that gives the same output re-keys nothing. Before, a reader change made the dev1 build bake all 1,769 room residents
  again for the base game alone. A unit that names the records and archive files it reads is keyed by what the expansions
  change in them (a "layer view"): measured against the dev1 units, with both expansions selected 55 of the 1,769 room
  residents change and about 3 % of the NPC library's appearances; the rooms that read textures the expansion archives
  replace bake again. The player view's units bake again once in this snapshot: the game-data part of their cache key
  changed with the layer view, so none of the 80 matched the dev1 units.
- **Every resident of the expansions' rooms stands where the game puts it.** The people and creatures of the Tribunal
  and Bloodmoon rooms (630 of them) are classified like the base game's: on the floor, kept off the floor where the game
  places them so, or placed dead. The base game's classes are unchanged. The builder now checks every room resident in its
  first minute, before any stage, so a missing class stops a build at once instead of in the middle of the room batches.
- **The `dbg tp` place list holds the expansions' places.** The list box of places is read from the selected
  expansions as well as the base game: Mournhold's and the other expansion rooms the image holds are listed by their
  names (a search for "Mournhold" finds them), and a Solstheim place is listed only where the build holds its world (the
  others are named in the build report). With the base game alone the list is the same as before.
- **The build's plan check sees every reuse stop.** The plan check before a build now runs the same per-unit reuse check
  as the build's first minute, so a change that would bake stored work again is seen before any gate, and a change to a
  module's shared lines no longer re-keys every unit that reads the module.
- **The world survey reads the expansions' data.** The survey that plans the island's map now reads the archives of the
  selected expansions as well as the base game. This is the fix that lets a build with the expansions switched on
  start: before it, such a build stopped in the survey. Solstheim's new exterior cells are listed in the survey and
  planned when its exterior is converted.
- **Every stage that reads the game's data reads the expansions' archives.** The stages that build the actor, room, item,
  door, terrain and interface tables read the selected expansions' archives in load order, so a model or texture only an
  expansion holds is no longer missing. With the base game alone each stage reads what it read before.
- **Mournhold's five outdoor districts are set aside in this build.** Godsreach, the Great Bazaar, Plaza Brindisi Dorom,
  the Royal Palace courtyard and the Temple courtyard are listed in the build report and not converted; they come with
  Mournhold's own exterior ([the expansions](../../EXPANSIONS.md)). The rest of the city's rooms are ordinary rooms.
- **The expansions' large rooms fade into their fog like the base game's.** The 86 rooms of Tribunal and Bloodmoon at
  least 1,024 units across (Solstheim's caves, barrows and halls, Old Mournhold's sewers, Fort Frostmoth's quarters) join
  the large-rooms table, so each fades into its cell's fog colour at the draw distance and draws nothing past it; the
  table now holds 410 rooms. Before, the build stopped in the CHIM interiors stage on the first unlisted one
  (`CHIM-LARGE-ROOMS-EXPANSIONS-66`).
- **The journal reads the expansions' entries in load order.** Tribunal and Bloodmoon repeat 1,833 of the base game's
  journal entries under their own record id; a later master's entry now replaces the earlier one, as in the game. Where
  an expansion puts a quest title beside a journal entry at the same stage, the entry is kept (the book's quest titles
  come from the quest list). Before, the build stopped on the first repeated stage (`JOURNAL-EXPANSION-OVERRIDES-66`).
- **The exterior plan reads the same game data as the world survey.** The plan of which exterior cells go to which map
  is now made from the selected masters merged in load order, over the base game's exterior grid, as the survey reads
  them; before, the plan was made from the base game file alone and the terrain stage stopped on the two differing
  (`EXTERIOR-PLAN-MASTER-LAYERS-66`). With the base game alone the plan is the one it was.
- **Solstheim's exterior placements are left for its exterior.** The rocks, plants and trees of the 108 exterior cells
  only Bloodmoon adds (2,960 scenery placements and 4,857 flora placements) are listed by the survey and not planned
  yet; the scenery and flora stages now leave them out and count them, where before they stopped on them as omitted
  (`EXTERIOR-EXPANSION-ONLY-CELLS-66`).
- **The expansions' creatures get their models.** The actor library's creature bakes now read the expansion archives
  too: the 37 creature meshes only Tribunal and Bloodmoon hold (goblins, fabricants, liches, Almalexia, bears, wolves,
  rieklings, spriggans, draugr, horkers and others) are baked like the base game's, where before each was left out as
  missing (`ACTOR-LIBRARY-BASE-ARCHIVE-66`).
- **Doors to places this build does not hold are set aside, named.** The world door table holds back the doors and
  markers of Solstheim's exterior (192), of Mournhold's five outdoor districts and of the seven expansion rooms the room
  stage could not convert (81), and lists each with its reason; every other door must still be linked. Before, the image
  step would have stopped on all 273 (`EXPANSION-DOORS-HELD-BACK-66`).
- **The image step checks its file formats early.** Every file the palette overlay reads by name must be a known format,
  which catches an unknown file (the effects icon rows were the case) before the long steps, not at the end of a build.

### Map and finding your way

- **An explored-land map.** The world map shows land you have explored, and keeps the fog over the rest. A land-colours
  look is built in as a switch (off by default), and lava stays hidden under the fog until it is explored.
- **A local map and an interior plan.** A local map shows your surroundings, and inside a room a plan of the room with
  fog over the parts not yet seen ([world map and journal](../../WORLD_MAP_AND_JOURNAL.md)).
- **Places are named.** Hovering a map marker names the place, and known places are marked in play.
- **Your own markers.** The map keeps up to 256 named markers, listed and searchable in the map's own Markers menu and
  from the console. One quick unnamed "hot" marker has a simple compass that points towards it.
- **Names when you point.** Signposts show the place they name, and named objects such as beds and shrines show their
  name, as in the original.

### Magic

- **Characters cast spells.** People and creatures that know spells weigh them against their weapon about once a second
  in a fight, cast the best one from its range with their spellcast animation, and pay the magicka, by the rules the
  reference engine uses ([magic effects](../../MAGIC_EFFECTS.md), "Characters cast too"). `dbg combat spells off` keeps
  them to their weapons.
- **The cast look is on by default and in step with the cast.** The hand glow, the cast sprites, the sound and the shell
  around the caster begin together with the cast animation, and the bolt or hit starts on the frame the spell leaves. A
  settings file saved by an earlier version with the look off is switched on once.
- **More spell kinds are understood by fighters,** among them Burden, Feather, Dispel, the cures, Restore and Absorb
  Magicka and the bound weapons. A fighter's spells are read once at its first choice in a fight, so later choices read
  nothing from disk.
- **The player's body has the cast and ready groups** it needs for these animations.
- **Readied magic shows the open hands, whatever is equipped.** Readying magic (R by default) now shows the original's
  open spell-casting hands even when a torch, a lantern, a weapon or a shield was in use; the torch or light is put away
  while magic is ready and comes back when the magic is lowered. Before, a lit torch or a held light took the hands and
  the stance looked like the clenched fists of hand-to-hand, so magic and bare fists could not be told apart.

### Scripts in the towns

- **The towns' scripted objects run.** On the Seyda Neen and Balmora maps no scripted object without a character of its
  own was attached to its script, so all of them did nothing: Tarhiel's journal among them, so Tarhiel never fell. They are
  attached now (Seyda Neen: 37 places), and Tarhiel falls near his journal and dies on landing as in the original. A play
  journey checks the fall ([game recorder](../../GAME_RECORDER.md)).

### Character creation

- **What the abilities do.** The birthsign window lists the sign's abilities, powers and spells beside the list of signs,
  each with its effects under it (icon, magnitude, and for powers and spells the duration, area and range), as the original
  does; the race window's statistics show the race's specials the same way. Long lists scroll
  ([character creation](../../CHARACTER_CREATION.md)).

### Actors and combat

- **Each fighter moves at its own speed.** An NPC chases and flees at its run speed from its Speed and Athletics, a
  creature at its walk speed, a flyer and a swimmer by their own speeds. Until now every fighter moved at one fixed
  speed, well above the run of an ordinary person.
- **Load counts in fatigue.** A swing costs fatigue by the load carried as well as the weapon, as the original's formula
  has it. The formulas for the whole actor system are in a table, row by row against the reference
  ([mechanics parity](../../MECHANICS_PARITY.md)).
- **Bows and crossbows are held and shot.** People and creatures draw bows and crossbows and shoot with their ammunition,
  and throw thrown weapons, from a shot pool that costs no allocation in play.
- **Every actor's record is audited.** A record audit lists each person and creature against the original's data, with
  creature weapons and the carried-item tags of the NPC library ([actor records](../../ACTOR_RECORDS.md)). Creatures are
  baked on the skeletal method by default, after an audit of the animations each actor plays.
- **Dagoth Ur has his own animations.** He runs, swings, casts and dies on a skeletal model of 948 faces with every seam
  locked, and the strike scene at the Heart has its own test.
- **The Heart of Lorkhan stays in its place.** A creature that can move by no means no longer walks, chases or flees, so
  the Heart no longer follows the player beside Dagoth Ur.
- **Each fighter picks its weapon by its own skills.** A person or creature rates the weapons it carries by its own
  skill with each (a creature by its Combat, Magic or Stealth value), as the reference engine does, so a skeleton archer
  keeps to its bow and nobody draws a weapon it has no skill with. A table checks the choice of every record: 35 of 3,437
  chose differently before, none now ([actor records](../../ACTOR_RECORDS.md), "Combat styles").
- **Fleeing, paralysis and the carried load.** Fighters flee by their Flee rating (on by default; `dbg combat flee off`
  keeps the old rule), a paralysed victim takes punch damage to health and can neither evade nor block, and what a
  fighter carries counts in its fatigue costs and its speed in a fight ([mechanics parity](../../MECHANICS_PARITY.md)).
- **Scripted walkers go round what blocks their way.** A character on a scripted walk (the dock guard on his way from the
  pier to the office door in the opening among them) checks the straight line of his last leg and walks round a post or
  pylon on it instead of pressing against it. The opening walk now fails when the dock guard does not reach the door.
- **Murder bounty.** Killing someone adds the original's murder bounty (the crime table is reused where it was dropped),
  and the larger focus table lets more things be pointed at.

### Death and respawn

- **The dead stay dead.** Who is alive and who is dead is remembered in every cell, across area changes and saves.
- **Bodies are cleared as in the original.** A dead character or creature that does not respawn loses its body when its
  cell is next loaded after the original's delay (fCorpseClearDelay); the actor stays dead for good. People flagged
  Persistent keep their body. Outdoors too: a body lies where it fell and can be looted when the player comes back before
  the delay (`chim actors corpses 0` keeps the old way).
- **The essential message.** Killing an essential character shows the original's message that the thread of prophecy is
  severed, once per death; a body laid down again on a later visit does not show it a second time.
- **Saves are safer.** A save is refused, and the previous one kept, when any part of the game state fails to go into it.
  Saved script values come back by the script's name.

### The world

- **Containers.** The container box you aim at is measured for every outdoor container and used in the two opening room
  maps (the prison ship and the census office), so containers standing on the ground can be pointed at. Trapped
  containers are checked for their trap.
- **The prison ship's hold is lighter.** The hold's shell is drawn in tiles of at most 512 faces, small parts of the
  hammocks are boxed, and the hold's collision follows the room collision rule. Each method sits behind a builder
  switch (`--room-draw-tiles`, `--room-small-parts`) and the old way stays selectable
  ([ship interior](../../SHIP_INTERIOR.md#the-weight-of-the-hold)). A deck draw tiles switch for the ship and the silt
  strider is built in as off by default.
- **Outdoor creatures in town cells.** The mudcrabs and slaughterfish of the cells that hold towns are placed again, and
  the builder counts the creatures it places in those cells against the original.
- **The builder checks every actor against the original.** The image step counts the people and creatures placed per kind
  of area (interiors, the regions, the towns, the water) against the original's references, and checks each placed
  actor's record (level, attributes, skills, health, spells, inventory, weapons) against the original's data. A build that
  places fewer than the original or carries an actor out of spec stops, unless the gap is listed by name with its reason
  ([actor records](../../ACTOR_RECORDS.md), "The build's actor spec check").
- **Bracket fungi sit on their trees.** 106 of the bracket fungi in the built world floated beside their trees: 104 because
  the reduced trunk of their Bitter Coast tree lies inside the original one, 2 by the Seyda Neen lighthouse because their
  tree was drawn as a flat sprite. Each of the 104 is seated by its measured gap, that tree is drawn as a model, and the
  image step checks every fungus against its tree.
- **The inventory page arrows** look and act like the race selection arrows and are greyed at the ends.

### Performance

Checked by tests; the frame rate on the Raspberry Pi 4B is still to be measured on this snapshot. All figures, with what
measured them and what is not measured yet, are on the [v0.0.66 performance page](../../performance/V0.0.66-PERFORMANCE.md).

- **The prison ship's hold is lighter to draw and to collide with**: its shell in tiles of at most 512 faces, the small
  hammock parts boxed, its collision under the room rule (each behind a builder switch, see above). Measured with a model
  of the engine's own test from four spots in the hold (eight headings each):

  | Measure | Before | After |
  | --- | --- | --- |
  | Faces tested per view, average | 14,128 | 10,749 (-24 %) |
  | Faces tested, worst view (the start, looking down the hold) | 23,386 | 21,356 (-9 %) |
  | Faces facing the camera, average | 7,285 | 5,488 (-25 %) |
  | Faces drawn in all | 26,628 | 24,598 |
  | Collision clipnodes | 29,182 | 18,054 (-38 %) |
  | Steps of a collision point test, average | 837 | 649 (-22 %) |

  The worst view gains least: it looks at most of the room. The frame rate in the hold on the Raspberry Pi 4B is measured
  on this snapshot's build ([ship interior](../../SHIP_INTERIOR.md#the-weight-of-the-hold)).
- **Scripts cost less**: the interpreter's timers share their work, and script lookups are cheaper.
- **Fights read nothing from disk**: a fighter's spells are read once at its first choice in a fight, and shots come from
  a pool with no allocation in play.
- **The character windows** read their ability lists when the race or sign changes, never while drawing.
- **Builds**: the cache keys follow what each unit reads, so switching the expansions on rebuilds only what they change.

### The builder and the scripts

- **Script costs.** The script interpreter's timers share their work, the lookups of scripts are cheaper, and `SetDelete`
  removes an object and stops its script as in the original.
- **A play journey checks the opening.** A repeatable journey through the opening checks the inventory, the journal,
  rewards, a killed actor and a save and load after every build
  ([game recorder](../../GAME_RECORDER.md)).
- **The bug register records fixes.** Each entry can carry its fix commit, the date it was fixed and its planning item.

### From v0.0.66-dev1 and v0.0.65

- Everything of [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) is in this snapshot: the merging reader, the layer keys, the
  Heart of Lorkhan as a room resident and the row of active-effect icons. Everything [v0.0.65](RELEASE-v0.0.65.md) fixed
  in the opening is in it too.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Readied magic (R): the open hands with nothing equipped, with a weapon, with a lit torch and with a lantern; F still
  shows the fists.
- A fight with people and creatures that cast spells, shoot bows or swing at their own speed.
- A kill, an area change and a return, and a save and load: the dead stay dead, and bodies are cleared as described.
- The map: the explored land, the local map, a room plan, a named marker, the Markers menu, the hot marker and the compass.
- Pointing at a signpost, a bed and a container outdoors.
- The prison ship's hold at the start of a New Game, for the load and the frame rate on the Raspberry Pi 4B.
- The Heart Chamber with Dagoth Ur's animations, and the Heart staying in place.
- A New Game through the opening to Seyda Neen and the trip to Balmora several times, as checked for v0.0.65.

## Known in this build

- **The save has fixed size limits that are far too small (the most serious known issue).** The save keeps the changes
  since a new game in several fixed-size parts. The saved NPC rows (position, facing, health, greeting counters) stop at
  256 for about 2,700 NPCs; once full, the rest of that place's NPCs are not saved, and on loading they are back at
  their starting places at full health. Creatures the player interacts with (companions, pack animals, summoned and
  scripted creatures) may not be kept at all. The explored map shares a 32 KB part with other lists and can refuse the
  whole save when that part is full. The other fixed limits (the change list's rows, the changed actor records, picked
  plants and looted creatures) are being measured. The save must hold every change the game makes, with no fixed cap
  that can refuse a save or silently drop state (`SAVE-STATE-FIXED-CAPS-66`).
- Tribunal and Bloodmoon data is selected by default, but the cells and rooms of Mournhold and Solstheim are not played
  in this snapshot: there is no finished Mournhold or Solstheim content.
- The new weapon choice, fleeing and the outdoor bodies are checked by tests, not yet in play. Still open in the actors'
  mechanics: the crime audit, an NPC running while it wanders, potions and magic items as a fighter's best action.
- The game can stop in an ancestral tomb.
- The Heart Chamber's collapse is not animated, so the end of the main quest cannot play yet
  (`ENDGAME-CHAMBER-COLLAPSE-63`).
- The [MWScript tracker](../../MWSCRIPT_FEATURES.md) shows how many of the game's scripts run.
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- From [v0.0.66-dev1](RELEASE-v0.0.66-dev1.md) and [v0.0.65](RELEASE-v0.0.65.md): the open entries of their Known lists
  stand. Every other open entry is in the [bug register](../../BUGS.md); the
  [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) shows how far each land and part has come.
