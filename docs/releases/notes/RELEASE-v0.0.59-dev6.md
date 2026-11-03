# AmiWind v0.0.59-dev6 (in development)

Development snapshot, 3 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.58](RELEASE-v0.0.58.md).

The sixth snapshot of v0.0.59: everything of dev5 ([dev5 notes](RELEASE-v0.0.59-dev5.md)), and the world change list
extended to respawn and to saves made with other game data, a window for containers, the original journal view,
levelling with the original's rest and wait rules, a faster talk window, a list of the items you can pick up, and
changes to the builder and the test tooling. The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it. This snapshot is for testing in game.

## New since dev5

- **Respawn.** Containers refill and the actors that the original game brings back come back, by the rules of OpenMW:
  flagged actors and levelled actors return after the respawn time. The world change list keeps this across maps and
  saved games.
- **Saves after game-data changes.** A saved game made with other game data loads: the world change list is matched
  against the data of the build that loads it, and what no longer exists is left out.
- **The container strip.** E on a container opens a strip at the bottom of the screen with the container's items, a
  Take All button and an Inventory button. Containers that belong to someone are marked, and locks are shown. A take
  reads the container once, and the strip redraws only after a change (about 70 frames per second with it open).
- **The original journal view.** J opens the journal as in the original game: dated pages with the day headings in the
  original form, two pages at a time, with Prev, Topics, Quests, Close and Next. The quest list is the view by
  subject. The dated history has no cap of 32 quests or 256 entries any more; a saved game from an earlier snapshot
  has its history taken over.
- **Levelling, second slice.** Resting and waiting follow the original: Rest or Wait by the cell's no-sleep flag,
  beds (owned, rented, by guild rank), the refusals with the game's own lines, restoration by mode, Until Healed, the
  interruption in the wilderness, and the level-up after a full rest. The level-up box has no cancel. Persuasion trains
  Speechcraft, and an accepted Barter trade trains Mercantile, scaled by the share haggled. See
  [Resting](../../RESTING.md).
- **A faster talk window.** The short strings of the compiled scripts are kept after the first read, so the talk window
  opens much faster than in dev5.
- **A dead actor no longer starts combat on load.** A restored death stays a death.
- **The items index.** [ITEMS_INDEX.md](../../ITEMS_INDEX.md) lists every placed item you can pick up by cell, kind and
  owner, from the game's records. The builder makes it as its own stage.
- **Per-area tables.** Containers, owners, item records and the strip's pictures come from small tables loaded with
  the area, so opening the container strip, a take and a put read no file during play.
- **The player's body is kept.** The parts of the player's body load over several frames and stay in memory (about
  281 KB), and the journal names are read in one pass, so the first frame after arriving in Seyda Neen takes about
  1 second where it took 12 to 15 seconds (a switch in the game config selects the old way).
- **Frame wait counters.** The lines for long frames and frame spikes show the time spent in file calls, the screen
  copy and the buffer swap, so a slow frame says what it waited for.
- **Builder.** The CHIM world pack runs in two passes on the worker pool, and the validation reads its visibility rows
  on the workers (not yet measured in a full build). A pool stage that the stages beside it throttle runs alone. The
  stage keys ignore a change of a text define in the stages that write no text, and a change of the frame timing
  header re-keys no CHIM world stage. The animation table used by the town bakes is built once per stage and cached.
- **Disk images.** Every drive of the image is padded to whole IDE cylinders (16 heads, 63 sectors), so the emulated
  controller sees the whole last partition; a stop of the delivery hops at Khuul came from the missing tail.
- **Test tooling.** The emulator sessions put the disks on the emulated A1200 IDE controller, and the probe tells an
  open window from a stall.

## Fixed since dev5

- A dead actor that was restored from a saved game started combat on load (COMBAT-DEAD-ACTOR-RELOAD-59).
- A town entered again from a room did not apply the change list to its own residents (ACTORS-TOWN-ROOM-RETURN-59).
- A change of a text define re-keyed stages that write no text (BUILD-STAGE-KEY-TEXT-DEFINES-59).
- Opening a conversation took 3 to 6 seconds; it takes about half a second now
  ([DIALOGUE-CLOSE-FRAME-FREEZE-59](../../bugs/DIALOGUE-CLOSE-FRAME-FREEZE-59.md)).
- In Arrille's Tradehouse one frame could last about 10 seconds
  ([TRADEHOUSE-LONG-FRAME-59](../../bugs/TRADEHOUSE-LONG-FRAME-59.md)); a take in the container strip could hold the
  game for seconds ([CONTAINER-STRIP-TAKE-STALL-59](../../bugs/CONTAINER-STRIP-TAKE-STALL-59.md)).
- The delivery hops stopped at Khuul when the last partition of a drive ended inside an IDE cylinder
  (IMAGE-IDE-CYLINDER-TAIL-59).

## Known in this build

- Containers whose contents are levelled lists open empty
  ([CONTAINER-LEVELLED-CONTENTS-EMPTY-59](../../bugs/CONTAINER-LEVELLED-CONTENTS-EMPTY-59.md)).
- Bodies of dead actors cannot be looted yet
  ([CORPSE-INVENTORY-NOT-OPENABLE-59](../../bugs/CORPSE-INVENTORY-NOT-OPENABLE-59.md)).
- The first frame after arriving in Seyda Neen still takes about a second, and the residents' walking steps cost
  200 to 800 ms on some frames.
- Travelling from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).

## Not yet checked in game

- Respawn of flagged and levelled actors over a long wait, and a save loaded after a change of game data, on FS-UAE.
- The new journal view and the rest and wait rules on the Pi 4B and on a 68040.
- The two-pass CHIM world pack in a full build.
