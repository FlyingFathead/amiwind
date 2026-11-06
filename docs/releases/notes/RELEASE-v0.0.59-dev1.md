# AmiWind v0.0.59-dev1 (in development)

Development snapshot, 1 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.58](RELEASE-v0.0.58.md).

The first snapshot of v0.0.59: world models for items. The game needs 32 MB of Fast RAM, and the emulator presets of
this snapshot have it. This snapshot is for testing in game; the new parts below have not been checked in game yet.

## New since v0.0.58

- **Every item has a world model.** A new builder stage converts the world model of every item the game has (weapons,
  armour, clothing, books, ingredients, tools, carried lights and the rest), 880 distinct models, into one shared
  model table: equal items share one model, and a dropped or placed item refers to its entry instead of carrying a
  copy. The models are read from disk only when an item is on the ground.
- **A larger model table.** The engine's model table per map holds 512 models (it held 256). Sixteen slots stay
  reserved for dropped items, and up to 64 dropped items can be shown, using free slots beyond those sixteen; past
  that, a drop is kept in the inventory with a message. The model limits of every map are unchanged.
- **Builds rebuild less.** A change to the engine alone, or to the development label, no longer rebuilds the CHIM
  world, its rooms or the cell progress pages: their keys follow only the inputs that change their output.

## Known in this build

- Items placed in the world by the game data are not yet placed from the new table (the next step); dropped items
  use it.
- The player's own gear is not yet shown on the hands or the body (a later snapshot).
- A build's performance check can fail on loaded machines when other builds run beside it
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- Dropping items of every kind and seeing their models; picking them up again; a save and reload with items on the
  ground.
- The model counts on the busiest maps with dropped items.
