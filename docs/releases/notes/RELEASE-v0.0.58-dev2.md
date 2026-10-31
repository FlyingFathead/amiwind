# AmiWind v0.0.58-dev2 (in development)

Development snapshot, 31 October 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.57](RELEASE-v0.0.57.md).

The second snapshot of v0.0.58, "Time To Talk". The game needs 32 MB of Fast RAM, and the emulator presets of this
snapshot have it. What the first snapshot brought is in the [dev1 notes](RELEASE-v0.0.58-dev1.md). This snapshot is
for testing in game; the new parts below have not been checked in game yet.

## New since dev1

- **Answers that do things.** The scripts attached to answers now run when the answer is shown, as in the original:
  choices to pick from, conversations that end with only Goodbye, and answers that change how factions regard each
  other. Places an answer reveals on the map are remembered for when the map shows them.
- **Enchanting** at an enchanter: name the item, pick a filled soul gem, choose how it casts and its effects, with the
  original's limits and prices. Using what you enchant comes with casting, which is not in yet.
- **Voices.** You say your race's pain and death lines in a fight; characters greet by the original's first-match rule,
  and several can greet at once in a crowd; a spell's sound no longer cuts a character off mid-line.
- **Faster, steadier builds.** The actor library uses every core it is allowed, and the boot check now tells a game
  that stops answering apart from an emulator that stalls on its disk.

## Known in this build

- Casting the spells you make, and using items you enchant, wait for player casting (a later version).
- The fuller combat sounds are still behind `dbg combat sounds on` until they are checked in game.
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
