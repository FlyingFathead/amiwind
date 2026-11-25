# AmiWind v0.0.69-dev2 (in development)

_Last updated with AmiWind v0.0.69-dev2 (25 November 2026)._

Development snapshot, 25 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.68: Solstheim Is Here](RELEASE-v0.0.68.md). Previous snapshot: [v0.0.69-dev1](RELEASE-v0.0.69-dev1.md).

The second snapshot of v0.0.69. The version has no title yet. It makes the start more reliable on Amigas with a
graphics card: the game now checks the screen mode the card offers, searches the card's modes itself when that offer
cannot be used, and opens the normal AGA screen when the card has no usable mode at all. Its emulator presets,
`AmiWind-v0.0.69-dev2-FS-UAE.fs-uae` and `AmiWind-v0.0.69-dev2-WinUAE.uae`, both start with 32 MB of Fast RAM, which the
game needs. Otherwise the game is the one of v0.0.69-dev1.

## New since v0.0.69-dev1

### Fixed

- **The game finds a usable screen mode on more graphics card setups.** With a graphics card the game asks the card's
  software (Picasso96 or CyberGraphX) for an 8-bit mode of its screen size. Some Picasso96 setups, one of them on
  PiStorm, answer with no mode or with one the game cannot use, and the start stopped with "Can't FindDisplayInfo()".
  The game now checks the answer: the mode must be available, 8 bits deep and at least the game's screen size. If the
  answer is refused, the game goes through the card's modes itself and takes the exact size, or else the closest larger
  mode. If the card has no usable mode, the game opens the normal AGA screen instead. Each step is written to the
  console, so a log shows the mode offered, why it was refused and the mode chosen. A setup whose card already offered
  a usable mode keeps the same mode as before
  ([VIDEO-P96-MODEID-LOOKUP-FAILS-69](../../bugs/VIDEO-P96-MODEID-LOOKUP-FAILS-69.md)).
  The choice is checked by the test suite over made-up mode lists; it has not been seen on an affected card yet.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

The [checklist of v0.0.69-dev1](RELEASE-v0.0.69-dev1.md#in-game-checklist-for-this-snapshot) stands. In addition:

- **The screen mode on a graphics card.** Start the game on an Amiga with a graphics card and look at the console's
  first lines: one line names the mode used. On a setup that could not start before, the lines show the offered mode,
  why it was refused and the mode chosen, or that the normal AGA screen is used.

## Known in this build

- **The screen mode check on a graphics card** has been run by the test suite only; a log from an affected Picasso96
  setup will confirm it ([VIDEO-P96-MODEID-LOOKUP-FAILS-69](../../bugs/VIDEO-P96-MODEID-LOOKUP-FAILS-69.md)).
- From [v0.0.69-dev1](RELEASE-v0.0.69-dev1.md#known-in-this-build): its Known list stands, among them the build's
  expansion stages under half of their cores ([TRIBUNAL-STAGE-UNDERUSED-68](../../bugs/TRIBUNAL-STAGE-UNDERUSED-68.md)),
  the actor library limited by memory ([BUILD-MEMPLAN-CHIM-5-OF-22-68](../../bugs/BUILD-MEMPLAN-CHIM-5-OF-22-68.md)) and
  the object in Solstheim's eastern waters ([SOL-SEA-INVISIBLE-BLOCKER-68](../../bugs/SOL-SEA-INVISIBLE-BLOCKER-68.md)).
  The next snapshots take these open items first, the small ones first. Every other open entry is in the
  [bug tracker](../../BUGS.md).
