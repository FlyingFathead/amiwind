# AmiWind v0.0.65-dev1 (Reintroduction, in development)

_Last updated with AmiWind v0.0.65-dev1 (11 November 2026)._

Development snapshot, 11 November 2026, in development. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.64: Gone Beyond The Gate](RELEASE-v0.0.64.md).

The first snapshot of v0.0.65, "Reintroduction", a fix release made from v0.0.64 alone. Since v0.0.62 the start of a
New Game reset the opening's state right after setting it, so the opening ran without its holds. This snapshot restores
the opening as it was designed; everything else is v0.0.64 unchanged. The work that was under way for the next version
(the reader for the expansions' files, the Heart of Lorkhan, the row of effect icons) is not in this line: it moves to
v0.0.66. The game needs 32 MB of Fast RAM, and the emulator presets of this snapshot have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this snapshot. None of it has been seen in play on a
build of this snapshot yet; the in-game checklist at the end lists what to look at.

## New since v0.0.64

### The opening

- **The opening runs with its holds again.** In the opening a New Game now keeps the state the opening sets, instead of
  clearing it straight away. The parts that were missing, and are restored:
  - the dock guard walks up on the pier and can be talked to, so the race can be chosen;
  - the pier is closed until the opening lets the player through;
  - the census office shows its message boxes and holds the player in during the clerk's talk;
  - things cannot be taken before the papers are accepted;
  - Sellus Gravius talks again instead of only greeting;
  - the idle camera no longer orbits before a race is chosen (`OPENING-VANITY-CAMERA-64`).
- The work on the opening follows the opening's own register entry for this regression; the entries stay open until the
  opening is seen in play on a build of this snapshot.

### The register

- The pack guar at Ahemmusa Camp (Azura's Coast) is drawn with its body parts scattered apart in v0.0.64; the cause is
  not known yet and the entry (`ACTOR-PACK-GUAR-MESH-BROKEN-64`) is open. This snapshot does not change it.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this snapshot

- A New Game from the menu: the dock guard walking up the pier and the talk with him, the race choice, the closed pier,
  the census office with its message boxes and the lock-in during the clerk's talk, taking things only after the papers
  are accepted, and Sellus Gravius's talk.
- The idle camera at the race choice: it stays still until a race is chosen.
- Ahemmusa Camp: the Pack Guar's body.

## Known in this build

- The pack guar at Ahemmusa Camp is drawn broken (`ACTOR-PACK-GUAR-MESH-BROKEN-64`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- Mournhold and Solstheim are not in the game; they move to v0.0.66.
- From [v0.0.64](RELEASE-v0.0.64.md): the open entries of its Known list stand. Every other open entry is in the
  [bug register](../../BUGS.md).
