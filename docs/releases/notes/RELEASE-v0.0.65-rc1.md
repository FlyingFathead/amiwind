# AmiWind v0.0.65-rc1: Reintroduction

_Last updated with AmiWind v0.0.65-rc1 (11 November 2026)._

Release candidate, 11 November 2026. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.64: Gone Beyond The Gate](RELEASE-v0.0.64.md); development snapshot
[v0.0.65-dev1](RELEASE-v0.0.65-dev1.md).

v0.0.65, "Reintroduction", is a fix release made from v0.0.64 alone. Since v0.0.62 the start of a New Game reset the
opening's state right after setting it, so the opening ran without its holds. This candidate restores the opening as it
was designed, and mends the torch and the fists that the check of the opening found broken; everything else is v0.0.64
unchanged. The work that was under way for the next version (the reader for the expansions' files, the Heart of Lorkhan,
the row of effect icons) is not in this line: it moves to v0.0.66. The game needs 32 MB of Fast RAM, and the emulator
presets of this candidate have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this candidate. None of it has been seen in play on a
build of this candidate yet; the in-game checklist at the end lists what to look at.

## New since v0.0.64

### The opening

- **The opening runs with its holds again.** A New Game keeps the state the opening sets, instead of clearing it
  straight away. The parts that were missing, and are restored:
  - the dock guard walks up on the pier and can be talked to, so the race can be chosen;
  - the pier is closed until the opening lets the player through;
  - the census office shows its message boxes and holds the player in during the clerk's talk;
  - things cannot be taken before the papers are accepted;
  - Sellus Gravius talks again instead of only greeting: the engine and the scripts now read one value of the character
    generation state, kept in step every tick and again after a New Game reset or a loaded save
    (`SELLUS-GRAVIUS-GREETING-ONLY-64`);
  - the idle camera and the view switch no longer run on the ship and the pier before a race is chosen
    (`OPENING-VANITY-CAMERA-64`).
- **The dock guard's walk to his post.** The walk to his post beside the office door was given up for good when the
  player stood in his way; it is now tried again, and at his post he faces the pier and the ship.
- **A check against the same fault.** The reset of a New Game is checked so that no reset writes the state of another
  module, and the boot mark is taken per module.
- The entries of the opening's regression are `OPENING-HOLDS-OFF-NEWGAME-64`, `CENSUS-OFFICE-HOLDS-OFF-64`,
  `SELLUS-GRAVIUS-GREETING-ONLY-64` and `CENSUS-OFFICE-NO-EXIT-64`; they stay open until the opening is seen in play on
  a build of this candidate.

### The torch and the fists

- **The debug torch lights with V again.** F then V equips the carried debug torch, or gives one while the debug torch
  switch is on (`DEBUG-TORCH-64`).
- **Fists fight with a torch lit.** F raises the fists and V alone switches the torch (`TORCH-HAND-TO-HAND-64`).
- **The torch follows the equip state at once:** unequipped in the inventory, no torch is drawn in the hand
  (`TORCH-INVENTORY-PICTURE-64`).
- **The fight reads the player's live attributes and skills each frame,** so a level, a potion or a debug change in the
  middle of a fight counts at the next blow (`HAND-TO-HAND-NO-HIT-64`).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## In-game checklist for this candidate

- A New Game from the menu: the dock guard walking up the pier, facing the pier at his post, and the talk with him; the
  race choice; the closed pier; the census office with its message boxes, the lock-in during the clerk's talk and the way
  out after the registration; taking things only after the papers are accepted; Sellus Gravius's talk.
- The idle camera on the ship and the pier before a race is chosen: it stays still.
- The torch: V with a torch and with the debug torch, F with a torch lit, unequipping the torch in the inventory.
- Fists in a fight: how often they land, and after raising the stats mid-fight.

## Known in this build

- The pack guar at Ahemmusa Camp is drawn with its body parts scattered apart (`ACTOR-PACK-GUAR-MESH-BROKEN-64`).
- Shalks on Azura's Coast hang high in the air (`CREATURE-FLOATING-SHALK-64`).
- The battle music keeps playing after a fight has ended (`COMBAT-MUSIC-STUCK-64`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- Mournhold and Solstheim are not in the game; they move to v0.0.66.
- From [v0.0.64](RELEASE-v0.0.64.md): the open entries of its Known list stand. Every other open entry is in the
  [bug register](../../BUGS.md).
