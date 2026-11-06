# AmiWind v0.0.58-dev5 (in development)

Development snapshot, 1 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.57](RELEASE-v0.0.57.md).

The fifth snapshot of v0.0.58, "Time To Talk". The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it. What the earlier snapshots brought is in the [dev4 notes](RELEASE-v0.0.58-dev4.md), the
[dev3 notes](RELEASE-v0.0.58-dev3.md), the [dev2 notes](RELEASE-v0.0.58-dev2.md) and the
[dev1 notes](RELEASE-v0.0.58-dev1.md). This snapshot is for testing in game; the new parts below have not been
checked in game yet (see the last section).

## New since dev4

- **The Census and Excise Office's small items are back.** The office's items are placed objects again, so they are
  drawn, aimed at and taken. Equal items share one model, which keeps the office map within the engine's model limit
  (about 217 of 256 models, where the first attempt held 284). The census stage refuses an office map over 240 models.
- **The item prompt.** An aimed item that can be taken shows "E: Take" in the normal colour, or a red "E: Steal" when
  the item is owned. The wording comes from the game's own take string. Plants keep their "E: Pick".
- **Books and letters can be read.** A readable book or letter shows "E: Read" (red when owned) and opens a reader that
  pages the text. The reader shows "E: Take" (red "E: Steal" when owned) and "Esc: Close". Magic scrolls are not read:
  they are taken directly. A builder stage of its own prepares the texts of the books (445 books).
- **Sneaking.** Holding Left Ctrl sneaks: the player walks slower, the view sits lower, sneaking uses fatigue, and the
  HUD shows a sneak indicator. The key has its own row in the Options controls page, and saved key bindings are moved
  to the new command. In the debug free-fly mode Left Ctrl keeps its fast-flight use. Sneak animation and detection
  come in a later version.
- **Build-time prompt code.** The action of each aimed row (take, read, talk, owned, magic scroll) is decided when the
  game is built and stored in a spare byte of the row, so the prompt is read from a table and no row grows.
- **Toolkit 0.1.19.** The build monitor of the AmiWind Toolkit is updated with this version.
- **Engine-limit check for converted rooms.** The builder counts each converted room's models against the engine's
  limit before the room is accepted, and a test covers the limits of every map.

## Known in this build

- The back-room table of the Census and Excise Office is not drawn, so the dagger on it is not seen
  (CENSUS-BACK-TABLE-NOT-DRAWN-58, open in the [register](../../BUGS.md)).
- The aim box measures the reach to an item's origin, not to its nearer surface as the original does
  (FOCUS-REACH-ITEM-ORIGIN-58, open in the [register](../../BUGS.md)).
- A build's performance check can fail on loaded machines when other builds run beside it
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)).
- The netch bull's reduced model loses a stretch of one leg
  (CREATURE-NETCH-BULL-LEG-REDUCED-58, open in the [register](../../BUGS.md)).
- Casting the spells you make, and using items you enchant, wait for player casting (a later version).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- Everything new since dev4: the Census Office's small items drawn, aimed at and taken, with the saved state across a
  reload.
- The "E: Take" and "E: Steal" prompts, and the colours of owned items.
- The book reader: "E: Read", paging, "E: Take" or "E: Steal" and "Esc: Close", and scrolls taken directly.
- Sneaking: speed, view height, fatigue, the HUD indicator and the Options key binding.
- The Toolkit build monitor of Toolkit 0.1.19.
