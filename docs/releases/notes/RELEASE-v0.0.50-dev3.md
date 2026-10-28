# AmiWind v0.0.50-dev3: The Doors: Riders On The CHIM (in development)

Development snapshot, 24 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.49](RELEASE-v0.0.49.md).

The first build of v0.0.50's door work: every entrance of the game leads into its interior, and every way out leads
back ([roadmap](../../ROADMAP.md#v0050-the-doors-riders-on-the-chim-24-october-2026)).

## New since v0.0.50-dev2

- **One door table for the whole world.** Every load door of the game, and the markers where an arrest takes the
  player, are resolved from the game's own door records by one rule: a town frame holds what lies inside its box (Seyda
  Neen, Balmora and Vivec), the CHIM region frame of the cell holds the rest, a room holds its own doors. Every door
  bank of the image is written from it, and the image fails to build when a door does not resolve
  ([door graph](../../chim/DOOR_GRAPH.md), [CHIM-REGION-DOORS-NO-ROOMS-48](../../bugs/CHIM-REGION-DOORS-NO-ROOMS-48.md)).
- **Ways out around Vivec and Ebonheart.** 85 exits out of rooms into cells a town frame holds lead out again (among
  them Hawkmoth Towers, the Grand Council Chambers, the East Empire warehouses, several Vivec waistworks and Telvanni
  Plaza).
- **Entrances near the old towns.** 10 doors in cells inside the old town frames now open: Pelagiad's houses of
  Adanja, Ahnassi and Dralas Gilu, the Abaesen-Pulu Egg Mine, Assemanu, the Andrano Ancestral Tomb, the Akimaes and
  Nimawia Grottos and the two doors of the Remote Shipwreck.
- **`dbg tp heartchamber`** takes you to Akulakhan's Chamber, the Heart Chamber, where the game's own door puts you.
  Named places are listed in `config/teleport-names.txt` ([console commands](../../AMIWIND_CONSOLE_COMMANDS.md)).

## Known in this build

- Everything in [v0.0.50-dev1's known items](RELEASE-v0.0.50-dev1.md#known-in-this-build) still applies.
- Everything else is in the [bug register](../../BUGS.md).
