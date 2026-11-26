# AmiWind v0.0.69-dev4 (in development)

_Last updated with AmiWind v0.0.69-dev4 (25 November 2026)._

Development snapshot, 25 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.68: Solstheim Is Here](RELEASE-v0.0.68.md). Previous snapshot: [v0.0.69-dev3](RELEASE-v0.0.69-dev3.md).

The fourth snapshot of v0.0.69. The version has no title yet. It takes the next small item of the Known lists: the box
shown when a load runs out of memory now names the place instead of the map file. Its emulator presets,
`AmiWind-v0.0.69-dev4-FS-UAE.fs-uae` and `AmiWind-v0.0.69-dev4-WinUAE.uae`, both start with 32 MB of Fast RAM, which the
game needs. Otherwise the game is the one of v0.0.69-dev3.

## New since v0.0.69-dev3

### Fixed

- **The failed-load box names the place.** When a load that names only its map (a saved game, the start, a map load
  the game's code asks for) ran out of memory, the box wrote the map file's internal label, for example balmora in
  lower case, instead of the place's name. The game now reads the place's name from the map itself, as the screen's
  place name shows it, so the box says Balmora; a map without a name keeps its label
  ([LF5-BOX-DESTINATION-MAP-NAME-68](../../bugs/LF5-BOX-DESTINATION-MAP-NAME-68.md)). The name rule is covered by the
  test suite; it has not been seen in play yet.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of v0.0.69-dev3](RELEASE-v0.0.69-dev3.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The failed-load box.** If a load runs out of memory (at 16 MB Fast RAM, for example), the box names the place, such
  as Balmora, not a lower-case file label.

## Known in this build

- **Water Walking is applied deep under the water too,** where the original refuses the spell; the original's rule is
  found and the fix is planned for a coming snapshot
  ([WATER-WALKING-DEEP-CAST-NOT-REFUSED-68](../../bugs/WATER-WALKING-DEEP-CAST-NOT-REFUSED-68.md)).
- **The screen mode check on a graphics card** has been run by the test suite only; a log from an affected Picasso96
  setup will confirm it ([VIDEO-P96-MODEID-LOOKUP-FAILS-69](../../bugs/VIDEO-P96-MODEID-LOOKUP-FAILS-69.md)).
- From [v0.0.69-dev3](RELEASE-v0.0.69-dev3.md#known-in-this-build) and the snapshots before it: their Known lists
  stand, among them the object in Solstheim's eastern waters
  ([SOL-SEA-INVISIBLE-BLOCKER-68](../../bugs/SOL-SEA-INVISIBLE-BLOCKER-68.md)) and the build's expansion stages under half
  of their cores ([TRIBUNAL-STAGE-UNDERUSED-68](../../bugs/TRIBUNAL-STAGE-UNDERUSED-68.md)). The next snapshots take these
  open items first, the small ones first. Every other open entry is in the [bug tracker](../../BUGS.md).
