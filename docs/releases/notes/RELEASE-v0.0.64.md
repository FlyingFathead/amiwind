# AmiWind v0.0.64: Gone Beyond The Gate

_Last updated with AmiWind v0.0.64 (11 November 2026)._

Release, 11 November 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.63: Every Script Of Vvardenfell](RELEASE-v0.0.63.md).

v0.0.64, "Gone Beyond The Gate", is the release that prepares the road to the two expansion worlds and mends what the
checks of v0.0.63 found. It does **not** carry the expansion worlds themselves: Mournhold (Tribunal) and Solstheim
(Bloodmoon) are not built into the game image, and they move to the next version. What it carries is the builder's
expansion switch and the census of both expansions, a first Solstheim frame and its tree methods as test builds, and,
for the game of Vvardenfell, game spells, powers and enchantments that take effect again, traps that spring, lava that
kills, the console's switches and journal and faction commands, scrolls cast from the Magic window, spell and trap damage
that meets resistances, cobwebs and moss drawn see-through, lighter collision in every room, large rooms that fade into
fog, and a builder that converts the world again only for a change that reaches it. The game needs 32 MB of Fast RAM, and
the emulator presets of this release have it.

The notes below cover the whole of v0.0.64 since v0.0.63, by area, not by snapshot: the five development snapshots
[dev1](RELEASE-v0.0.64-dev1.md), [dev2](RELEASE-v0.0.64-dev2.md), [dev3](RELEASE-v0.0.64-dev3.md),
[dev4](RELEASE-v0.0.64-dev4.md) and [dev5](RELEASE-v0.0.64-dev5.md), and the register work made after dev5. Almost every
change was checked by the test suite and the gate; the few that were also looked at in play are named, and none of the
release's changes has been seen on the image of this release (see "Checked in game").

## What the release does not carry yet

- **Mournhold and Solstheim are not in the game.** The [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) counts
  none of Solstheim's land cells as converted and no Mournhold room as in the game; 433 of the 1,207 scripts belong to
  those worlds and wait for them (`BUILD-EXPANSIONS-31`, open; [the page](../../bugs/BUILD-EXPANSIONS-31.md)). Both worlds
  move to the next version, with their scripts and the scripted world events of their own.
- **Solstheim exists only in test builds.** Its first frame, its tree methods and its map rows and region names are
  groundwork; a Solstheim forest is not yet cheap enough to draw on the Amiga.
- **The Heart Chamber's end** cannot play: the heart is not placed in the room and the chamber's collapse is not animated.
- Locks on doors and picking owned locks, and the other items listed under "Known in this build".

## The game scripts

The three game files hold 1,207 script records, of which the original game uses 1,074. The tracker was measured again for
this release, with the builder's own compiler: 605 run as scripts and 9 more are carried by AmiWind's own code (605 and 9
in v0.0.63), 27 wait for a function the interpreter lacks (28 in v0.0.63), 433 belong to the add-on worlds and wait for
them, and 133 are named by nothing in the original game and never ran there either
([MWScript tracker](../../MWSCRIPT_FEATURES.md)). Scripts can now cast spells on characters other than the player.

## The game systems table

[Game features](../../GAME_FEATURES.md) lists 49 systems of the base game: **7 of 49 done, 39 partial, 3 missing**, as in
v0.0.63.

## New since v0.0.63

### Spells, powers and enchantments

- **Game spells take effect again.** The engine's actor table read only 32 of the 39 sections of the compiled scripts
  file, so since v0.0.63 the spell effects, magic effects, enchantments and starting spells were never found and every game
  spell, power and enchantment did nothing when cast. The engine now reads up to 64 sections and refuses a file with
  more, and a gate test checks the limit against the builder's section list (`SPELL-EFFECTS-TABLE-CUT-64`, open until seen
  on an image).
- **Spell and trap damage meets the target's resistances and weaknesses.** An effect that can be resisted (the elements,
  poison, paralysis, the drains, damages and absorbs, the mind effects, disintegration) is weighed against the target's
  resist, elemental shield and weakness magnitudes, from its active effects and the always-on abilities of its race,
  birthsign and spells, with its Willpower and Luck roll. A full resistance stops the effect, a partial one scales it, a
  weakness raises it; a Nord's frost immunity stops a frost trap (`RACE-RESIST-NOT-ON-SPELL-DAMAGE-64`; seen in play on a
  test build).
- **Scrolls are cast from the Magic window's Magic Items,** as in the original game: a Cast Once scroll chosen there is
  cast with no skill roll and used up; using one from the inventory reads it, as OpenMW does (`SCROLL-CAST-MISSING-64`).
- **Argonian Breathing is the race's castable spell:** Water Breathing for 120 seconds on the caster. The console's id
  search had read the actor table the wrong way round and answered 0 for every spell; that is fixed, and the spell was
  cast and held under water for its 120 seconds on a test build (`UNDERWATER-BREATH-62`, open until seen on an image;
  [the page](../../bugs/UNDERWATER-BREATH-62.md)).
- **Scripts can cast on any other character,** following OpenMW: the cast always succeeds, the effects of range Self land
  on the caster, and those of range Touch and Target land on the target.

### Traps, doors, switches and lava

- **Opening a trapped door, load door or container springs its trap on the player** instead of opening, as the original
  does. The trap is used up when it springs and stays used up in saved games; a new game clears it; the key that opens the
  lock also disarms the trap. Morrowind.esm places 457 trapped references with 85 trap spells; with Tribunal and Bloodmoon
  there are 468 (290 containers, 167 hinged doors and 11 load doors). A trap does not yet spring on a failed lock pick,
  and the trap sounds and the tooltip line are missing (`DOOR-TRAPS-NOT-SPRUNG-55`, open until seen in play;
  [the page](../../bugs/DOOR-TRAPS-NOT-SPRUNG-55.md)). [World mechanisms](../../WORLD_MECHANISMS.md) counts the 54
  activators of the three game files that move, turn, enable, disable, lock, unlock or activate another object.
- **The console activates objects that are not characters,** also those no script names, by their id: the Ghostgate's
  switches, which raise the portcullises, and the cursed coin. On a test build the switches raised the portcullises when
  activated by id from the console (`WORLD-BUTTONS-62`, `MARKS-SUMMON-CARRIERS-NOT-LIVE-63`; both open until seen on an
  image, the coin not yet looked at in play).
- **Lava is stood in and kills.** A debug teleport onto lava was refused as a water surface and fell back to the centre of
  the frame; the feet now stand in the liquid on its bed, and `dbg tp X Y Z` reads Z as the floor under the feet, as the
  original does, and takes the nearest floor beside the point (rings of 32 units out to 128) when the point has none.
  Lava killed the character on a test build (`LAVA-NO-DAMAGE-63`, open until seen on an image; `GODMODE-LAVA-DEATH-62`).
- **God mode stays on across map changes:** the switch is kept and put back on the new player, and a new game clears it.
- **The door list shows each door's arrival point,** as a room start does; this was seen on a test build.

### The journal, the factions and the console

- **A quest's state follows its entries.** The journal book replays each quest's entries in the order earned against the
  journal table's finished and restart marks: a success or failure ending finishes the quest, a restart entry reopens it,
  and the active and finished lists are split by that. An entry at or below the quest's current index is still added once
  (`JOURNAL-LOWER-INDEX-ENTRY-64`).
- **The expulsion from a faction shows the game's own message** with the faction's name (`FACTION-EXPEL-MESSAGE-64`), and
  **the stats page lists the player's factions:** rank, what the next rank needs, reputation and bounty
  (`FACTION-STATS-PAGE-64`).
- **The console takes the original journal and faction commands, reads included:** `Journal`, `SetJournalIndex`,
  `GetJournalIndex` and `GetPCExpelled`; `dbg mwscript call` also reads expulsion, rank and reputation
  (`CONSOLE-QUEST-READS-MISSING-64`).
- A scripted placement can be found by name even when it has no entity.

### Rooms, collision and fog

- **Hollow models in every room use approximate standing bevels by default.** The room configuration sets
  `hollow_bevels` to 2 for every room, the builder option is `--chim-hollow-bevels 0/1/2`, and a room or room type can opt
  back in. Exterior frames keep exact bevels for their authored walkways and underpasses. A sweep over 934 rooms found no
  sample pushed through a wall. By the builder's estimate the collision of the rooms goes from 667,788,436 to 307,535,200
  bytes, about 46 % of before; this is an estimate, and the image of this release is the first to measure it
  (`COLLISION-DISPARITY-WORLDWIDE-64`, [the page](../../bugs/COLLISION-DISPARITY-WORLDWIDE-64.md);
  [collision meshes](../../COLLISION_MESHES.md)). Large models' standing hulls are routed (`--model-hull auto`), and every
  model of a build is ranked by its collision bytes against its drawn faces, with a warning for the worst.
- **Large rooms fade into fog.** Two settings, in Options > Video and on the console: `Fog in large rooms`
  (`aw_fog_large_rooms`, on by default) and `Fog distance indoors` (`aw_fog_distance_interior`, 100 to 4096, default 300;
  the outdoor distance stays `aw_drawdistance`). Past the fog end a large room no longer draws its faces; the Heart Chamber
  has its own room type (3) with a reduced detail budget. On a test build of the chamber alone at 32 MB Fast RAM no edges
  fell short (the white patches are gone), a full turn ran at 42.9 frames per second in the emulator and the load took
  20 seconds; 540 is the largest indoor distance that did not bring the edge overflow back, at about 23 % fewer frames per
  second than 300 (`INTERIOR-FAR-BLANK-MANOR-56`, [the page](../../bugs/INTERIOR-FAR-BLANK-MANOR-56.md);
  `AKULAKHAN-CHAMBER-32MB-STALL-53`, [the page](../../bugs/AKULAKHAN-CHAMBER-32MB-STALL-53.md)).
- **The Heart of Lorkhan's fire shield and hidden glows no longer cover it:** shapes that a model skin cannot draw (a
  translucent scrolling shield, glow quads seen only while it dies) are left out of a creature; the heart bakes at 480
  triangles (562 before reduction; `HEART-EFFECT-SHELLS-OPAQUE-64`).
- **A room load gives back the area cache first:** before a room sizes its growth from the free Fast RAM, every cached
  table of the area left is given back and read again from disk when needed; a memory census (`aw_memcensus`, off
  by default) lists the engine's live blocks of 4 KiB or more by the code that asked for them
  (`ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64`).

### The renderer

- **See-through materials are on by default.** Cobwebs, hanging moss and leaves, and decals are drawn with their
  see-through parts instead of solid rectangles. The converter marks a texture whose alpha leaves at least 1 % of its
  texels under half alpha as see-through, and the engine draws those faces in a separate pass after the opaque world. The
  console setting is `aw_seethrough_material` (`dbg seethrough`): 0 draws them as solid rectangles as before, 1 is the
  default, 2 also draws them from behind. A mirrored copy of each such face is a build option
  (`--chim-fence-twosided-faces mirror`) and stays off until measured. The cost on a full build is not yet measured
  (`ROOM-DECAL-ALPHA-62`, open; [the page](../../bugs/ROOM-DECAL-ALPHA-62.md)).
- **Animation tables carry scale keys:** the engine scales a bone and its children.

### Trees and Solstheim, in test builds

- **The first Solstheim frame** can be built as a test build (`--chim-sol-test`, off by default) from a layered copy of the
  game data. On the densest forest cell it fits the memory budget at 32 MB Fast RAM (61 % of the zone's ring budget), but
  its views draw 45,964 faces at the median against 7,562 on Vvardenfell, and the trees are 87 % of them
  ([the first Solstheim frame, measured](../../performance/SOLSTHEIM-FIRST-FRAME-v0.0.64.md)). The 25 Bloodmoon meshes the
  collision surface check did not know and three meshes of the stair check are covered.
- **Star-shaped spruces** (`--chim-sol-tree-copies star`, test builds only, unset by default) draw each Solstheim tree as a
  closed star-shaped crown on a six-sided trunk, 30 faces per tree instead of 472 to 724: faces per view at the median go
  from 45,964 to 6,096 (maximum 61,175 to 16,942) on the same frame. Their crowns pop in and out while the camera moves
  and a flight over them has single-frame hitches (`CHIM-SOLSTHEIM-TREE-FACES-64`, `CHIM-STAR-TREES-POP-64`,
  `CHIM-SOLSTHEIM-STAR-HITCHES-64`; all open).
- **Tree crowns as a player setting:** `aw_tree_crowns` 0/1, off by default, with the crown alternatives in compact files
  of their own, which costs 2.6 % more world data on the Solstheim test frame (an earlier form cost 74 %); with the star
  crowns the renderer took 3.2 to 3.5 ms per frame there against 12.8 to 13.3 ms with the original trees (FS-UAE, 32 MB
  Fast, fog on). Nothing changes for the main island.
- **Groundwork for Solstheim's map rows and HUD region names:** the region table has rows for the island's frame maps,
  its name and its region names, and the HUD names the land first, then the region ("Solstheim / Brodir Grove Region");
  the debug teleport and the marks read those rows (`WORLD-REGION-NAMES-VF-ONLY-64`). The cells around and between the two
  islands are counted by OpenMW's rule for cells no file defines (`CHIM-SEA-BETWEEN-ISLANDS-64`).

### The builder and the image

- **The expansion layers are a choice.** `--dlc tribunal|bloodmoon|both|none` chooses which expansion layers a build
  includes, and `--no-dlc` builds the base game only; the choice is the player's and is recorded in the builder's option
  record. Every stage that reads the game data counts only the game inputs it reads, so an expansion file on the disk does
  not re-key a stage that never reads it, and the cell and room readers take a master list. The expansions have their own
  room id ranges and store units, so a later build of Mournhold or Solstheim does not move the ids or the storage of the
  base world. The census of what Tribunal and Bloodmoon add, counted from the game files:
  [expansions census](../../performance/EXPANSIONS-CENSUS-v0.0.64.md).
- **The CHIM stage key follows what reaches the world.** A change to engine code, to switches that are off by default or
  to a page the world does not read no longer converts the world or fits the room actors again. All 69,510 world files of
  two builds were compared by SHA-256: 69,508 are identical, only the two timing files differ. The reuse preflight stops
  on a whole stage that would rebuild before the build starts, the unit cache keeps entries across the expansion rows of
  the collision table, and the world flora and scenery units are keyed on the region converter only.
- **A Raspberry Pi 4B drive image:** the builder can make a ready-to-write drive image (no ROMs, no personal settings),
  in a full and a slim form, for test deliveries.
- A MiniWind of the Heart Chamber alone for the chamber's load work; the resident budget tool keeps its caps block; the
  release kit takes the gate's test suite result for the same commit; the builder's start-up plan can count a stage whose
  reuse is at risk as reused (`BUILD-PLAN-AT-RISK-CASCADE-64`, open).

### The load stall and the test sessions

- **A load trace, off by default:** `dbg loadtrace on`, `off` and `dump` (`aw_loadtrace`) keep every file call of a load in a
  fixed ring in memory and print the last calls and every call that did not finish when the scene is ready; off, each file
  call costs one test. Every load also prints one memory line (the hunk, the zone, the cache, the Fast and Chip RAM free
  and largest). Both are for the stall on the trip from Seyda Neen to Balmora, which no snapshot has caught
  (`CHIM-SEYDA-BALMORA-LOAD-HANG-43`, open; [the page](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- The boot smoke examines every stop before a retry, can turn the trace on, and has options for the load stall
  experiments; an incomplete combat settings file is read once per load instead of once per spawned actor.

### The Toolkit and the progress pages

- **The Toolkit's CHIM Progress Tracker** has one map pane for Vvardenfell, one for Solstheim and one screen for Mournhold,
  each with its done, partial and missing counts; the headline shows one row per land and one for the build, its pages
  reload themselves when the served data changes, and it serves the newest delivered build's maps, world and rooms
  ([the Toolkit](../../AMIWIND_TOOLKIT.md)). The 3D Map Inspector opens CHIM rooms and shows, per placed model, its faces,
  drawing bytes, collision bytes and their ratio, with a heat view.
- **The [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) is written newest first,** its current state generated from
  the tracker data, and it counts every room a build puts in its image as in the game: 1,121 of Vvardenfell's 1,123
  interiors are CHIM rooms and 2 are room maps. Its build figures are those of the newest ingested build (the dev4
  snapshot's); this release's own image is ingested after its build.
- A plan page for the active-effect HUD ([HUD_ACTIVE_EFFECTS](../../HUD_ACTIVE_EFFECTS.md)).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## Checked in game

Seen working on test builds with the fixed engine, not on the image of this release: Argonian Breathing cast and held
under water for its 120 seconds, the Ghostgate's switches raising the portcullises when activated by id from the console,
the door list's arrival lines, lava killing a character stood in it with `dbg tp`, race resistances on spell and trap
damage, and the Heart Chamber loaded alone at 32 MB Fast RAM with no blank patches (42.9 frames per second in a full
turn, a 20 second load). Everything else in these notes is checked by the test suite and the gate only.

## In-game checklist for this release

- Cast Argonian Breathing as an Argonian and stay under water: 120 seconds with the breath bar not running out; a game
  spell, a power and an enchantment each have their effect.
- The Ghostgate's switches on both sides; the guarded coins in Ald Sotha Lower Level; a trapped chest or door (the first
  use springs the trap, the second opens; save and load keeps it used up; opening with its key does not spring it).
- The Red Mountain lava with `dbg tp` and god mode, across a door or a load.
- A frost spell or frost trap on a Nord: no damage; a fire spell on a Nord: full damage.
- Akulakhan's Chamber: it loads at 32 MB Fast RAM, shows no blank patches while turning and the far parts fade into fog;
  `dbg fog indoors` and `dbg fog large rooms` agree with the two rows in Options > Video. Then a walk through a few rooms
  and hollow models (arches, pillars, stairs, the Ald Daedroth antechamber and the Ald Sotha lower level): nothing is
  walked through, and nothing blocks.
- A cobweb in a tomb: see-through by default; `dbg seethrough 0` makes it a solid rectangle, `2` shows it from behind.
- Console: `Journal A1_1_FindSpymaster 10` then `GetJournalIndex A1_1_FindSpymaster`; `PCExpell`, `GetPCExpelled`,
  `PCClearExpelled` on a faction. The stats page after joining a guild. A quest with two endings in the journal.
- A Cast Once scroll (the Almsivi Intervention scroll) under Magic Items in the Magic window: cast with the cast key, it
  takes effect and is used up.
- `dbg loadtrace on` before the trip from Seyda Neen to Balmora, several times, then `dbg loadtrace dump`.
- The Toolkit's three map panes with a build that holds an expansion.

## Known in this build

- **Mournhold and Solstheim are not in the game image** (`BUILD-EXPANSIONS-31`; see the top of these notes). Solstheim's
  tree methods exist only in test builds and are not settled (`CHIM-SOLSTHEIM-TREE-FACES-64`, `CHIM-STAR-TREES-POP-64`,
  `CHIM-SOLSTHEIM-STAR-HITCHES-64`).
- **The Heart Chamber** was seen loading and drawing cleanly only on a test build of the chamber alone; it is not checked on
  the full image, and the end of the main quest cannot play yet (`AKULAKHAN-CHAMBER-32MB-STALL-53`, `ENDGAME-CHAMBER-COLLAPSE-63`,
  [`CHIM-ROOM-HEART-CHAMBER-LOAD-50`](../../bugs/CHIM-ROOM-HEART-CHAMBER-LOAD-50.md), `HEART-CHAMBER-POLYCOUNT-63`).
- **Spells, powers and enchantments take effect by the test suite;** only Argonian Breathing was cast on a test build, and
  the race's Water Breathing is still open in the register until it is seen on an image (`SPELL-EFFECTS-TABLE-CUT-64`,
  `UNDERWATER-BREATH-62`).
- **Not yet seen in play on an image:** trapped doors and containers springing their trap, the Ghostgate's switches and the
  guarded items that summon a guardian, lava, the scroll cast, the console's journal and faction reads, the stats page's
  factions, the expulsion message and the journal's ending entry (`DOOR-TRAPS-NOT-SPRUNG-55`, `WORLD-BUTTONS-62`,
  `MARKS-SUMMON-CARRIERS-NOT-LIVE-63`, `LAVA-NO-DAMAGE-63`, `SCROLL-CAST-MISSING-64`, `CONSOLE-QUEST-READS-MISSING-64`,
  `FACTION-STATS-PAGE-64`, `FACTION-EXPEL-MESSAGE-64`, `JOURNAL-LOWER-INDEX-ENTRY-64`; all open until seen).
- **The collision figures** (about 46 % of before for rooms) are the builder's estimate (`COLLISION-DISPARITY-WORLDWIDE-64`),
  and **the see-through materials' cost** is not measured on a full build (`ROOM-DECAL-ALPHA-62`).
- **Doors do not use the original game's locks,** so a locked door opens and there is no lock picking
  ([DOOR-LOAD-LOCKS-MISSING-51](../../bugs/DOOR-LOAD-LOCKS-MISSING-51.md)). Potions cannot be drunk through the console's
  equip routes; the inventory window route is not checked (`ALCHEMY-MISSING-61`, open in the register).
- **The shores and pond edges still run in saw-tooth steps;** the fix needs a world rebuild and moves to the next version
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)); the load trace is the tool for it.
- A player who becomes a werewolf is not drawn as the werewolf (`WEREWOLF-BODY-NOT-DRAWN-63`). The Pi bench's worst frame
  from the disk is 72.8 ms (48.1 in the v0.0.61 test image; `PI-BENCH-DISK-WORST-FRAME-63`). The game image is still
  larger than the original game data (`IMAGE-BIGGER-THAN-ORIGINAL-62`).
- Open entries of the builder, the gate and the test sessions that the maintainer moved to the next version are in the
  [bug register](../../BUGS.md), as is every other open entry. From [v0.0.63](RELEASE-v0.0.63.md): the open entries of its
  Known list stand, among them pickpocketing and owned locks not done.

## Moved to the next version

Tribunal (Mournhold) and Bloodmoon (Solstheim) built in by default where the player owns them, with their scripts and
scripted world events; the shores' saw-tooth steps, the Ghostgate's check in play, and the builder's remaining work on
using every core. The list is in the [roadmap](../../ROADMAP.md). No dates are promised.
