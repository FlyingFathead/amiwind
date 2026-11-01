# AmiWind v0.0.58-dev6 (in development)

Development snapshot, 1 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.57](RELEASE-v0.0.57.md).

The sixth snapshot of v0.0.58, "Time To Talk". The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it. What the earlier snapshots brought is in the [dev5 notes](RELEASE-v0.0.58-dev5.md), the
[dev4 notes](RELEASE-v0.0.58-dev4.md), the [dev3 notes](RELEASE-v0.0.58-dev3.md), the
[dev2 notes](RELEASE-v0.0.58-dev2.md) and the [dev1 notes](RELEASE-v0.0.58-dev1.md). This snapshot fixes what the
in-game check of dev5 found; it is for the last check before the v0.0.58 release.

## Fixed since dev5

- **The game's scripts run again.** The script file holds 8,618 scripts (most of them dialogue results), and the engine
  refused any file over 2,048, so no script ran on the dev2 to dev5 images. The engine now takes up to 16,384 scripts,
  and the builder refuses a script file over the engine's limits instead of shipping it
  (MWSCRIPT-REFUSED-SCRIPT-COUNT-58).
- **Taking items works.** E on an aimed item takes it, an owned item as stolen. Taking depended on the refused scripts;
  taken and disabled objects are now also kept hidden on every map when scripts are off
  (PICKUP-E-OWNED-NO-TAKE-58).
- **The aim box is for items and doors.** Creatures and people no longer get the box, since their name already shows
  under the view.
- **Character creation runs in order.** The birthsign page no longer jumps to the class confirm box, the review sheet
  asks for a name first and shows it, and the class questions button is greyed out when the game install has no
  question data (CHARGEN-BIRTHSIGN-REVIEW-58).
- **The debug restart lands in Seyda Neen.** `dbg aw hors` without a number now means 0, so after the Halloween scene
  it moves the player to Seyda Neen instead of leaving them in the Arena Pit (HORS-AFTER-HALLOWEEN-STAYS-ARENA-58).
- **Text macros are filled.** Placed books never ran the step that fills the game's text macros (the player's name,
  race, class and the like), so the raw names showed. Books, the journal, message boxes and dialogue now fill them from
  one table, and book and journal texts store each macro as a one-byte code written when the game is built
  (BOOK-TEXT-MACROS-58).

## Known in this build

- Dialogue texts and the time of day still fill their macros from the written name at run time; action-key macros
  show the action's word, not the bound key (both in the next version).
- The back-room table of the Census and Excise Office is not drawn, so the dagger on it is not seen
  (CENSUS-BACK-TABLE-NOT-DRAWN-58, open in the [register](../../BUGS.md)).
- The aim box measures the reach to an item's origin, not to its nearer surface as the original does
  (FOCUS-REACH-ITEM-ORIGIN-58, open in the [register](../../BUGS.md)).
- A build's performance check can fail on busy hosts when other builds run beside it
  ([PERF-GUARD-RESIDENT-BUSY-HOST-57](../../bugs/PERF-GUARD-RESIDENT-BUSY-HOST-57.md)).
- The netch bull's reduced model loses a stretch of one leg
  (CREATURE-NETCH-BULL-LEG-REDUCED-58, open in the [register](../../BUGS.md)).
- Casting the spells you make, and using items you enchant, wait for player casting (a later version).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).

## Not yet checked in game

- With the scripts running again, everything that depends on them, in a full play from character creation to Seyda
  Neen.
- The text macros in the release papers, other books and the journal.
- The debug restart from the main menu.
