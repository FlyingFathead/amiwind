# AmiWind v0.0.59-dev2 (in development)

Development snapshot, 1 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.58](RELEASE-v0.0.58.md).

The second snapshot of v0.0.59. It was not published: its build was stopped, and dev3 carries its contents. The dev1
snapshot was built and checked but not published either (it predates the v0.0.58 release on GitHub), so everything
of dev1 is in this one too ([dev1 notes](RELEASE-v0.0.59-dev1.md)). The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot
have it. This snapshot is for testing in game.

## New since v0.0.58

- **Every item has a world model.** A builder stage converts the world model of every item the game has (weapons,
  armour, clothing, books, ingredients, tools, carried lights and the rest), 880 distinct models, into one shared
  model table: equal items share one model, and a dropped item refers to its entry instead of carrying a copy. The
  models are read from disk only when an item is on the ground.
- **An item check in the builder.** Every carriable item (2,910 in the game) is checked for its inventory entry, its
  picture and its world model; a build stops if a kind of item is missing one. Two items have no picture in the
  game data itself.
- **A larger model table.** The engine's model table per map holds 512 models (it held 256). Sixteen slots stay
  reserved for dropped items, and up to 64 dropped items can be shown, using free slots beyond those sixteen.
- **Builds rebuild less.** A change to the engine alone, or to the development label, no longer rebuilds the CHIM
  world, its rooms or the cell progress pages.
- **Text macros as compact codes everywhere.** Dialogue answers and spoken greetings now store the game's text macros
  (the player's name, race, class, the speaker's name and the like) as one-byte codes written when the game is built,
  as books and the journal already did; the time of day is read from the game clock, and texts that name an action
  show the key bound to it. Filling a text is one pass instead of three.
- **Toolkit 0.1.20.** The AmiWind Toolkit is updated with this version.

## Fixed since v0.0.58

- **Topic links in conversations.** A text macro used the same marker byte as a topic link, so linked topic words in
  answers and on the journal's topic pages could lose their link and show two of their letters as a number
  (DIALOGUE-LINK-MARK-AS-DEFINE-58). The macro now has a marker of its own.

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
- Topic links in a conversation, the time of day and an action key in a text.
