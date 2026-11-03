# AmiWind v0.0.59: Assembling The Bits And Pieces, Once Again

Release, 3 November 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.58](RELEASE-v0.0.58.md).

v0.0.59, "Assembling The Bits And Pieces, Once Again", puts the world together piece by piece: every item has its own
world model and the items of the game stand in their places, the world keeps what the player changes across rooms and
saved games, the player's body and hands are assembled from parts, containers open, the journal looks as in the
original, and resting and waiting follow the original's rules. The game needs 32 MB of Fast RAM, and the emulator
presets of this release have it. This release is the sixth development snapshot of v0.0.59 (dev6) with its final
version number; only fixes known to work went in, and what was planned beyond it moves, openly, to v0.0.60.

## Checked in game

The dev6 snapshot was delivered and run before this release: at 32 MB Fast RAM it boots and loads Seyda Neen, and the
delivery's six teleport hops between towns (Khuul among them) pass on FS-UAE with the emulated A1200 IDE controller.
The same image is installed on the project's Raspberry Pi 4B stick, where Amiberry opens it with 68040, FPU and JIT;
it has not been played there yet. The boot check at 16 MB Fast RAM fails, which is below the requirement. Not yet
checked in game is listed at the end of these notes.

## New since v0.0.58

### World items

- **Every item has a world model.** A builder stage converts the world model of every item the game has (weapons,
  armour, clothing, books, ingredients, tools, carried lights and the rest), 880 distinct models, into one shared model
  table: equal items share one model, and a dropped or placed item refers to its entry instead of carrying a copy. The
  models are read from disk only when an item is on the ground.
- **An item check in the builder.** Every carriable item (2,910 in the game) is checked for its inventory entry, its
  picture and its world model; a build stops if a kind of item is missing one. Two items have no picture in the game
  data itself.
- **A larger model table.** The engine's model table per map holds 512 models (it held 256). Sixteen slots stay
  reserved for dropped items, and up to 64 dropped items can be shown.
- **Items in their places.** The items the game data places in the world (bottles, dishes, books, tools and the rest on
  shelves, tables and counters) are drawn from the shared model table, in rooms and outdoors, and can be aimed at and
  taken. Dropping items outdoors works on the streamed towns.
- **The items index.** [ITEMS_INDEX.md](../../ITEMS_INDEX.md) lists every placed item you can pick up by cell, kind and
  owner, from the game's records. The builder makes it as its own stage.

### The world remembers

- **One change list for the whole world** keeps what the player changes: items taken, dropped or moved, objects a
  script disables or locks, the stolen mark, open doors, locks, the contents of containers and the faction ranks of
  NPCs. It holds across rooms, outdoor areas and saved games, with only the changes stored, up to 32,768 changes (the
  earlier tables held 1,024 objects and 32 dropped items). Saves made with earlier versions still load.
- **Respawn.** Containers refill and the actors that the original game brings back come back, by the rules of OpenMW,
  after the respawn time.
- **Saves after game-data changes.** A saved game made with other game data loads: the change list is matched against
  the data of the build that loads it, and what no longer exists is left out.
- **Per-area tables.** Containers, owners, item records and the container strip's pictures come from small tables
  loaded with the area, so opening a container, a take and a put read no file during play.
- **One conversion between map and game coordinates.** Script positions, lamps, weather, fog, the camera and the other
  engine parts that need a place in the game world find it on every map, the streamed towns included.

### The player

- **The player's body from parts.** The third-person body is assembled from parts by equipment slot on the shared
  skeleton instead of one baked model per race and sex, and the first-person arms are assembled the same way. The parts
  share their vertices (bare arms went from 2,988 to 852 vertices). The baked arms stay selectable
  (`dbg camera hands off`).
- **The body kept in memory.** The parts of the body load over several frames and stay in memory (about 281 KB), and
  the journal names are read in one pass, so the first frame after arriving in Seyda Neen takes about 1 second where
  it took 12 to 15 seconds in the snapshot before (a switch in the game config selects the old way).
- **`dbg give weapons`** gives one weapon of every type and the shields, and prints each one's stats from the game's
  records. The weapon box in the HUD shows a picture for every weapon.

### Containers, the journal, resting

- **The container strip.** E on a container opens a strip at the bottom of the screen with the container's items, a
  Take All button and an Inventory button. Containers that belong to someone are marked, and locks are shown.
- **The original journal view.** J opens the journal as in the original game: dated pages with the day headings in the
  original form, two pages at a time, with Prev, Topics, Quests, Close and Next. The quest list is the view by subject.
  The dated history has no cap of 32 quests or 256 entries any more; a saved game from v0.0.58 has its history taken
  over.
- **Resting and waiting as in the original,** the first part of levelling: Rest or Wait by the cell's no-sleep flag,
  beds (owned, rented, by guild rank), the refusals with the game's own lines, restoration by mode, Until Healed, the
  interruption in the wilderness, and the level-up after a full rest. The first training sources are in: persuasion
  trains Speechcraft, and an accepted Barter trade trains Mercantile. See [Resting](../../RESTING.md).

### Dialogue, sound and the cursor

- **Text macros as compact codes everywhere.** Dialogue answers and spoken greetings store the game's text macros (the
  player's name, race, class, the speaker's name and the like) as one-byte codes written when the game is built, as
  books and the journal already did; the time of day is read from the game clock, and texts that name an action show
  the key bound to it.
- **Sound events.** 34 named sound events (weapon swings, hits, blocks, bow and crossbow, spells by school, falls and
  creature sounds among them) each play their mapped sound and can be triggered with `dbg sound`. The build report
  names every sound that is not mapped.
- **The original mouse cursor,** taken from your copy of the game when the game is built, in every window. The previous
  cursor stays selectable: Options, Prefs, Mouse cursor, or `dbg cursortype 1` on the console.

### Fixes

- **Conversations open at once.** In v0.0.58 the first conversation of a session stood still for over 15 seconds
  (DIALOGUE-OPEN-STALL-58); later conversations took 3 to 6 seconds to open (DIALOGUE-CLOSE-FRAME-FREEZE-59). The
  topic tables are read in a few large reads and the short strings of the compiled scripts are kept, so the talk
  window opens in about half a second.
- **Topic links keep their words.** A text macro used the same marker byte as a topic link, so linked topic words could
  lose their link and show two of their letters as a number (DIALOGUE-LINK-MARK-AS-DEFINE-58).
- Placed items came back when the player left a room and returned (PLACED-ITEMS-ROOM-RESET-59), and outdoors on the
  streamed towns they were not drawn (PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59).
- A taken item and an object a script disabled shared one mark in the save (SAVE-TAKEN-DISABLED-ONE-FLAG-59), and a
  save with many changes in the world could be refused (SAVE-CHANGES-FULL-REFUSES-SAVE-59).
- The weapon box in the HUD stayed empty for every weapon outside the starting set (HUD-WEAPON-BOX-EMPTY-59).
- On the streamed towns the conversion to the game's coordinates found no place for most engine parts
  (CHIM-FRAME-SOURCE-CONVERSION-59).
- A dead actor restored from a saved game started combat on load (COMBAT-DEAD-ACTOR-RELOAD-59), and a town entered
  again from a room did not apply the change list to its own residents (ACTORS-TOWN-ROOM-RETURN-59).
- In Arrille's Tradehouse one frame could last about 10 seconds (TRADEHOUSE-LONG-FRAME-59), and a take in the
  container strip could hold the game for seconds (CONTAINER-STRIP-TAKE-STALL-59).
- The teleport hops stopped at Khuul when the last partition of a drive ended inside an IDE cylinder: every drive of
  the image is now padded to whole IDE cylinders (IMAGE-IDE-CYLINDER-TAIL-59).

### Builds and the tooling

- **Builds rebuild less.** A change to the engine alone, to the development label or to a text define no longer
  rebuilds the CHIM world, its rooms, the progress pages or the stages that write no text, and a change of the frame
  timing header re-keys no CHIM world stage.
- **The CHIM world pack runs in two passes on the worker pool,** the validation reads its visibility rows on the
  workers, a pool stage that the stages beside it throttle runs alone, and the animation table of the town bakes is
  built once per stage (its effect on the Vivec bake not yet confirmed in a full build).
- **Frame wait counters.** The lines for long frames and frame spikes show the time spent in file calls, the screen
  copy and the buffer swap, so a slow frame says what it waited for ([frame waits](../../performance/FRAME-WAITS.md)).
- **Test tooling.** The emulator sessions put the disks on the emulated A1200 IDE controller, and the probe tells an
  open window from a stall.
- **Toolkit 0.1.20.** The AmiWind Toolkit is updated with this version.

## Moved to v0.0.60

What v0.0.59 planned and did not finish moves, openly, to v0.0.60, in the [roadmap](../../ROADMAP.md):

- The walking residents' data kept in memory per area instead of being searched in files while they walk, and the rest
  of the arrival frame brought under half a second; residents drawn from parts get their appearance from small tables
  per area; game data in small chunks per cell and interior.
- What the player wears and wields in every stance, weapons and shields of every type in first and third person, and
  the first-person hands for every weapon type.
- Player casting and a spell-effect system; the original crime system; cliff racers that land their strikes.
- Levelling completed: skills rising with use in general and the level-up box with the attribute picks.
- The rest of the world change list (script locals, running global scripts, the journal, globals) and the complete
  conversation with its tracker page; every voice and sound moment heard in play.
- Containers whose contents come from levelled lists, and looting the bodies of the dead.
- The drop test of every kind of item, the scripted check of the Census and Excise Office's silver tray, a measured
  performance history per version, and confirming that the Vivec resident bake is back at its earlier cost.

## Known in this build

- Containers whose contents are levelled lists open empty
  ([CONTAINER-LEVELLED-CONTENTS-EMPTY-59](../../bugs/CONTAINER-LEVELLED-CONTENTS-EMPTY-59.md)).
- Bodies of dead actors cannot be looted yet
  ([CORPSE-INVENTORY-NOT-OPENABLE-59](../../bugs/CORPSE-INVENTORY-NOT-OPENABLE-59.md)).
- The first frame after arriving in Seyda Neen still takes about a second, and the residents' walking steps cost
  200 to 800 ms on some frames (v0.0.60).
- The back-room table of the Census and Excise Office is not drawn, the aim box measures the reach to an item's origin,
  and the player can hold only 8 spell changes (open in the [register](../../BUGS.md)).
- Casting spells you make, and using items you enchant, wait for player casting (v0.0.60).
- The performance check of a full build fails on the resident bake of the Vivec town, which costs about three and a
  half times its earlier CPU per unit; a fix is in this build and its effect is not yet confirmed in a full build
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)).
- Dropping a stack drops one piece per key press, so a map's limit of dropped items fills quickly (open in the
  [register](../../BUGS.md)).
- Travelling from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- Respawn of flagged and levelled actors over a long wait, and a save loaded after a change of game data.
- Dropping items of every kind and seeing their models; picking them up again across a save.
- The journal view and the rest and wait rules on the Pi 4B and on a 68040.
- The body and arms from parts on a 68040; the sound events on the WinUAE image.
- The time of day and an action key in a text.
- The two-pass CHIM world pack and the runs-alone scheduler in a full build of the whole world.
