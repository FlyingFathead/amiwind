# AmiWind v0.0.69-dev3 (in development)

_Last updated with AmiWind v0.0.69-dev3 (25 November 2026)._

Development snapshot, 25 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.68: Solstheim Is Here](RELEASE-v0.0.68.md). Previous snapshot: [v0.0.69-dev2](RELEASE-v0.0.69-dev2.md).

The third snapshot of v0.0.69. The version has no title yet. It takes the first small item of the Known lists: a video a
script starts now follows the script's choice of whether it may be skipped. Its emulator presets,
`AmiWind-v0.0.69-dev3-FS-UAE.fs-uae` and `AmiWind-v0.0.69-dev3-WinUAE.uae`, both start with 32 MB of Fast RAM, which the
game needs. Otherwise the game is the one of v0.0.69-dev2.

## New since v0.0.69-dev2

### Fixed

- **A video a script plays to its end cannot be skipped any more.** The script function that starts a video says whether
  the player may skip it. The engine ignored that and let Esc skip every video, so a story video the original shows in
  full could be cut short. Now a video started without the skip permission plays to its end: no key cancels or ends it.
  A video started with the permission, the startup logo and the debug video can still be skipped with Esc
  ([MWSCRIPT-PLAYBINK-SKIP-FLAG-68](../../bugs/MWSCRIPT-PLAYBINK-SKIP-FLAG-68.md)). The video player's test covers both
  kinds; it has not been seen in play yet.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of v0.0.69-dev2](RELEASE-v0.0.69-dev2.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **A story video plays to its end.** Where a script starts a video the original shows in full, Esc does not end it;
  where the original lets the player skip, Esc still does.

## Known in this build

- **Water Walking is applied deep under the water too,** where the original refuses the spell; the original's rule is
  found and the fix is planned for a coming snapshot
  ([WATER-WALKING-DEEP-CAST-NOT-REFUSED-68](../../bugs/WATER-WALKING-DEEP-CAST-NOT-REFUSED-68.md)).
- **The screen mode check on a graphics card** has been run by the test suite only; a log from an affected Picasso96
  setup will confirm it ([VIDEO-P96-MODEID-LOOKUP-FAILS-69](../../bugs/VIDEO-P96-MODEID-LOOKUP-FAILS-69.md)).
- From [v0.0.69-dev2](RELEASE-v0.0.69-dev2.md#known-in-this-build) and [v0.0.69-dev1](RELEASE-v0.0.69-dev1.md#known-in-this-build):
  their Known lists stand, among them the object in Solstheim's eastern waters
  ([SOL-SEA-INVISIBLE-BLOCKER-68](../../bugs/SOL-SEA-INVISIBLE-BLOCKER-68.md)) and the build's expansion stages under half
  of their cores ([TRIBUNAL-STAGE-UNDERUSED-68](../../bugs/TRIBUNAL-STAGE-UNDERUSED-68.md)). The next snapshots take these
  open items first, the small ones first. Every other open entry is in the [bug tracker](../../BUGS.md).
