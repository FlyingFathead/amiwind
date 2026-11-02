# AmiWind v0.0.59-dev4 (in development)

Development snapshot, 2 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.58](RELEASE-v0.0.58.md).

The fourth snapshot of v0.0.59: everything of dev3 ([dev3 notes](RELEASE-v0.0.59-dev3.md)), and the items of the world
placed from the shared model table, a world that remembers what the player takes and drops, and the original mouse
cursor. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it. This snapshot is for
testing in game.

## New since dev3

- **Items in their places.** The items the game data places in the world (bottles, dishes, books, tools and the rest on
  shelves, tables and counters) are drawn from the shared model table, in rooms and outdoors, as references to one
  model each. They can be aimed at and taken.
- **The world remembers.** One list for the whole world keeps what the player changes: items taken, dropped or moved,
  objects a script disables or locks, the stolen mark. It holds across rooms, outdoor areas and saved games, with only
  the changes stored and no fixed limit. Saves made with earlier snapshots still load.
- **Dropping items outdoors works on the streamed towns.** A drop was refused on every streamed map.
- **The original mouse cursor.** The mouse cursor is the original game's, taken from your copy of the game when the
  game is built, in every window. The previous cursor stays selectable: Options, Prefs, Mouse cursor, or
  `dbg cursortype 1` on the console.

## Fixed since dev3

- Placed items came back when the player left a room and returned (PLACED-ITEMS-ROOM-RESET-59).
- Placed items outdoors were not drawn on the streamed towns (PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59).
- A taken item and an object a script disabled shared one mark in the save, so enabling the object brought the item
  back (SAVE-TAKEN-DISABLED-ONE-FLAG-59).
- A save with many changes in the world could be refused (SAVE-CHANGES-FULL-REFUSES-SAVE-59).

## Known in this build

- What scripts and conversations change (dispositions, topics learned, journal stages, script values) is not yet kept
  across saved games ([MWSCRIPT-STATE-NOT-SAVED-48](../../bugs/MWSCRIPT-STATE-NOT-SAVED-48.md)); it is the next part
  of the same work.
- Several engine parts still look up places through the region table only, which has no entry on the streamed towns
  ([CHIM-FRAME-SOURCE-CONVERSION-59](../../bugs/CHIM-FRAME-SOURCE-CONVERSION-59.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- Moving between two streamed outdoor areas with items taken in both; an outdoor take after a load.
- Dropping items of every kind and seeing their models.
