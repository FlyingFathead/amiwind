# AmiWind v0.0.69-dev5 (in development)

_Last updated with AmiWind v0.0.69-dev5 (26 November 2026)._

Development snapshot, 26 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.68: Solstheim Is Here](RELEASE-v0.0.68.md). Previous snapshot: [v0.0.69-dev4](RELEASE-v0.0.69-dev4.md).

The fifth snapshot of v0.0.69. The version has no title yet. The box shown when a load runs out of memory now names the
place and its map file together. Its emulator presets, `AmiWind-v0.0.69-dev5-FS-UAE.fs-uae` and
`AmiWind-v0.0.69-dev5-WinUAE.uae`, both start with 32 MB of Fast RAM, which the game needs. Otherwise the game is the one
of v0.0.69-dev4.

## New since v0.0.69-dev4

### Fixed

- **The failed-load box names both the place and its map file**, for example "Not enough memory to load Vivec, map
  vivec_city". When there is no name, or the name is the file's, it is written once
  ([LF5-BOX-DESTINATION-MAP-NAME-68](../../bugs/LF5-BOX-DESTINATION-MAP-NAME-68.md)). The box text is covered by the
  test suite. At 32 MB of Fast RAM the box should not appear at all: every build checks every frame, room and crossing
  of the game against that minimum and fails if one does not fit.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of v0.0.69-dev4](RELEASE-v0.0.69-dev4.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The failed-load box.** If a load runs out of memory (below the 32 MB requirement, for example), the box names the
  place first and its map file beside it.

## Known in this build

- **The build monitor's first minutes:** while a build that reuses earlier work chooses and copies the reused stages,
  the monitor shows no phase name for about five minutes; the cause is found and the fix is planned
  ([TOOLKIT-MONITOR-BLIND-PHASES-36](../../bugs/TOOLKIT-MONITOR-BLIND-PHASES-36.md)).
- **Water Walking is applied deep under the water too,** where the original refuses the spell
  ([WATER-WALKING-DEEP-CAST-NOT-REFUSED-68](../../bugs/WATER-WALKING-DEEP-CAST-NOT-REFUSED-68.md)).
- From [v0.0.69-dev4](RELEASE-v0.0.69-dev4.md#known-in-this-build) and the snapshots before it: their Known lists
  stand, among them the object in Solstheim's eastern waters
  ([SOL-SEA-INVISIBLE-BLOCKER-68](../../bugs/SOL-SEA-INVISIBLE-BLOCKER-68.md)). The next snapshots take these open items
  first, the small ones first. Every other open entry is in the [bug tracker](../../BUGS.md).
