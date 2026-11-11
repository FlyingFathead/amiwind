# AmiWind v0.0.64-dev5 (in development)

_Last updated with AmiWind v0.0.64-dev5 (11 November 2026)._

Development snapshot, 11 November 2026, in development. Running on CHIM Engine v0.2.2. Previous snapshot:
[v0.0.64-dev4](RELEASE-v0.0.64-dev4.md). Previous release: [v0.0.63: Every Script Of Vvardenfell](RELEASE-v0.0.63.md).

The fifth snapshot of v0.0.64, "Gone Beyond The Gate". Hollow models in every room get lighter collision, large rooms
such as the Heart Chamber fade into fog instead of showing blank patches, the console takes the original journal and
faction commands, scrolls are cast from the Magic window, the builder no longer converts the world again for a change
that does not reach it, and the Toolkit and the progress page follow the newest build. No expansion area is part of the
game image yet. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

**This snapshot was not pushed on its own: its changes went into the [v0.0.64 release](RELEASE-v0.0.64.md).** It builds
on [v0.0.64-dev4](RELEASE-v0.0.64-dev4.md) (and, through them, those of dev1 to dev3: dev4's
notes link [the dev3 notes](RELEASE-v0.0.64-dev3.md), which list dev1 and dev2). In short, dev4 brought see-through
cobwebs, moss and leaves on by default, spell and trap damage that meets the target's resistances and weaknesses, the
player's factions on the stats page, the journal's ending entry, the groundwork for Solstheim's map rows and HUD region
names, an area cache given back before a room load, a collision census of every model, a Raspberry Pi 4B drive image
tool and the Toolkit's one row per land.

Scripts: 605 of the 1,207 scripts run as scripts and 9 more are carried by AmiWind's own code, as in dev4 (measured again
for this snapshot; [the MWScript tracker](../../MWSCRIPT_FEATURES.md)).

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. Some were also seen on test builds of one
room or one place (named in the entries); none has been seen in play on an image of this snapshot yet. The register keeps
an entry open until its change is seen on an image.

## New since v0.0.64-dev4

### Collision

- **Hollow models in every room use approximate standing bevels by default.** The room configuration sets
  `hollow_bevels` to 2 for every room, the builder option is `--chim-hollow-bevels 0/1/2`, and a room or room type can
  opt back in with its own value. Exterior frames keep exact bevels for their authored walkways and underpasses until
  their own sweep. A sweep over 934 rooms found no sample pushed through a wall. By the builder's estimate the collision
  of the rooms goes from 667,788,436 to 307,535,200 bytes, about 46 % of before (`COLLISION-DISPARITY-WORLDWIDE-64`,
  [collision meshes](../../COLLISION_MESHES.md)). The image of this snapshot is the first to measure it.
- **Large models' standing hulls are routed** (`--model-hull auto`, was `chain`), so a movement check visits fewer
  pieces; the switch for building collision from the reduced drawn mesh exists and stays off, and the census records the
  source of each model's collision. This and the bevel default together make this snapshot's world a planned rebuild.

### The Heart Chamber and large rooms

- **Fog in large rooms and its own indoor distance.** Two settings, in Options > Video and on the console: `Fog in large
  rooms` (`aw_fog_large_rooms`, on by default) and `Fog distance indoors` (`aw_fog_distance_interior`, 100 to 4096,
  default 300; the outdoor distance stays `aw_drawdistance`). Past the fog end a large room no longer draws its faces,
  and the Heart Chamber has its own room type (3) with a reduced detail budget. On a test build of the chamber alone at
  32 MB Fast RAM no edges fell short (the white patches are gone), a full turn ran at 42.9 frames per second in the
  emulator, and the load took 20 seconds. The indoor distance was swept on the same test build: 540 is the largest step
  without the edge overflow returning (about 23 % fewer frames per second than 300); 1000 brings the overflow back. The
  default stays 300 (`INTERIOR-FAR-BLANK-MANOR-56`).

### The console and magic

- **The console takes the original journal and faction commands, reads included:** `Journal`, `SetJournalIndex`,
  `GetJournalIndex` and `GetPCExpelled`; `dbg mwscript call` also reads expulsion, rank and reputation
  (`CONSOLE-QUEST-READS-MISSING-64`).
- **Scrolls are cast from the Magic window's Magic Items, as in the original game:** a scroll chosen there and cast is
  used up; using one from the inventory reads it, as OpenMW does (`SCROLL-CAST-MISSING-64`).

### Trees

- **Tree crowns:** `aw_tree_crowns` 0/1, off by default, with the crown alternatives in compact files of their own:
  only the paired models and the textures the world does not already hold are carried, which costs 2.6 % more world
  data on the Solstheim test frame (an earlier form cost 74 %). With the star crowns, the renderer took 3.2 to 3.5 ms
  per frame there against 12.8 to 13.3 ms with the original trees (FS-UAE, 32 MB Fast, fog on). Solstheim itself is
  not in the full build yet, so nothing changes for the main island.

### The builder

- **The CHIM stage key follows what reaches the world.** A change to engine code, to switches that are off by default
  or to a page the world does not read no longer converts the world or fits the room actors again. All 69,510 world files
  of dev4 and dev3 were compared by SHA-256: 69,508 are identical, only the two timing files differ.
- **The reuse preflight stops on a whole stage that would rebuild** before the build starts.
- **A Raspberry Pi 4B drive image** for each test delivery, in a full and a slim form (no ROMs, no personal settings).

### The Toolkit and the progress pages

- **The Toolkit** puts the shipping version in the inspector's exports, shows one headline row per land, has a help
  button beside every page title, follows the newest delivered build in its status strip instead of the clock, serves
  that build's maps, world and rooms without picking files, and sends the tracker data file only when it changed, compressed
  ([the Toolkit](../../AMIWIND_TOOLKIT.md)).
- **The [CHIM progress tracker](../../chim/PROGRESS_TRACKER.md) is written newest first,** its current state generated
  from the tracker data, and it counts every room a build puts in its image as in the game. Its figures are those of the
  newest ingested build (dev4); this snapshot's own image is ingested after its build.
- **A plan page for the active-effect HUD** ([HUD_ACTIVE_EFFECTS](../../HUD_ACTIVE_EFFECTS.md)).

### The register

- New entries include `COLLISION-DISPARITY-WORLDWIDE-64`, `SCROLL-CAST-MISSING-64`, `CONSOLE-QUEST-READS-MISSING-64`,
  `TRACKER-INTERIORS-IN-GAME-COUNT-64`, `DOCS-PROGRESS-TRACKER-STALE-64`, `BUILD-REUSE-STOP-WHOLE-STAGE-64`,
  `BUILD-ROOM-ACTOR-KEY-SWITCH-64`, `BUILD-TOWN-ACTOR-FIT-SERIAL-64`, `SMOKE-END-CONSOLE-TOGGLE-OUTSIDE-PLAY-64` and
  `CHIM-SEA-BETWEEN-ISLANDS-64`; the Toolkit's headline, help button, status and progress-file entries are set up for
  closing once seen on an image.

## Carried from v0.0.64-dev4 and earlier

See [the dev4 notes](RELEASE-v0.0.64-dev4.md) and [the dev3 notes](RELEASE-v0.0.64-dev3.md): see-through materials on by
default, race resistances on spell and trap damage, the stats page's factions, the journal's ending entry, Solstheim's
map rows and region names, the area cache given back on a room load, the collision census, game spells, powers and
enchantments taking effect again, Activate by id, lava that kills, god mode across map changes, trapped doors and
containers, the load trace and the expansion switch.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- Akulakhan's Chamber: it loads at 32 MB Fast RAM, shows no blank patches while turning, and the far parts fade into fog;
  `dbg fog indoors` and `dbg fog large rooms` change what is seen, and the same two rows in Options > Video agree.
- Walking through a few rooms and hollow models (arches, pillars, stairs, the Ald Daedroth antechamber and the Ald Sotha
  lower level, whose sweep results were the highest): nothing is walked through, and nothing blocks.
- Console: `Journal A1_1_FindSpymaster 10` then `GetJournalIndex A1_1_FindSpymaster`; `PCExpell`, `GetPCExpelled`,
  `PCClearExpelled` on a faction.
- A Cast Once scroll (the Almsivi Intervention scroll) is listed under Magic Items in the Magic window, cast with the
  cast key, takes effect and is used up.
- The stats page after joining a guild: faction, rank, the next rank's needs, reputation and bounty (from dev4).
- A cobweb in a tomb: see-through by default (from dev4).

## Known in this build

- **The Heart Chamber** was seen loading and drawing cleanly only on a test build of the chamber alone; it is not yet
  checked on this snapshot's full image, and the end of the main quest cannot play yet (`AKULAKHAN-CHAMBER-32MB-STALL-53`,
  `ENDGAME-CHAMBER-COLLAPSE-63`, `CHIM-ROOM-HEART-CHAMBER-LOAD-50`, `HEART-CHAMBER-POLYCOUNT-63`).
- **The collision figures** (about 46 % of before for rooms) are the builder's estimate; this snapshot's build measures
  the real image (`COLLISION-DISPARITY-WORLDWIDE-64`).
- Doors do not use the original game's locks, so a locked door opens and there is no lock picking
  ([DOOR-LOAD-LOCKS-MISSING-51](../../bugs/DOOR-LOAD-LOCKS-MISSING-51.md)).
- Potions cannot be drunk through the console's equip routes (`ALCHEMY-MISSING-61`); the inventory window route is not
  checked yet.
- **Not yet checked in play on this image:** the scroll cast, the journal and expulsion reads and the stats page's
  factions (`SCROLL-CAST-MISSING-64`, `CONSOLE-QUEST-READS-MISSING-64`, `FACTION-STATS-PAGE-64`).
- **The tree methods are not settled and are test-only,** and Solstheim is not playable in this build; Tribunal and
  Bloodmoon are not built into the image yet (`CHIM-STAR-TREES-POP-64`, `CHIM-SOLSTHEIM-STAR-HITCHES-64`,
  `BUILD-EXPANSIONS-31`).
- **The see-through materials' cost** is not yet measured on a full build (`ROOM-DECAL-ALPHA-62`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- From [v0.0.64-dev4](RELEASE-v0.0.64-dev4.md), [v0.0.64-dev3](RELEASE-v0.0.64-dev3.md) and
  [v0.0.63](RELEASE-v0.0.63.md): the open entries of their Known lists stand. Every other open entry is in the
  [bug register](../../BUGS.md).
