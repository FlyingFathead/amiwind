# AmiWind v0.0.65-rc2: Reintroducing Vvardenfell

_Last updated with AmiWind v0.0.65-rc2 (12 November 2026)._

Release candidate, 12 November 2026. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.64: Gone Beyond The Gate](RELEASE-v0.0.64.md); earlier builds of this line:
[v0.0.65-rc1](RELEASE-v0.0.65-rc1.md) and the snapshot [v0.0.65-dev1](RELEASE-v0.0.65-dev1.md) (both carry the earlier
title, "Reintroduction").

The previous version, v0.0.64, had a fault in the game's scripting of the start area that kept the opening from working
properly: the dock guard, the race choice, the census office and Sellus Gravius' papers. v0.0.65 fixes it, and the
opening now follows the original Morrowind more exactly: the original's own scripts run the opening, with AmiWind's
rules on top.

v0.0.65, "Reintroducing Vvardenfell", completes the opening on the original game's own scripts. The simplified logic
AmiWind used for the prison ship, the pier, the census office and Sellus Gravius gives way to the original scripts
running for real: the clerk's steps, the guards, the menus the scripts switch on, Sellus Gravius' conversation and the
papers. AmiWind's own rules stay on top: the speech boxes, the hold, nothing taken before the papers, and hints that name
your own keys. The release also repairs what v0.0.62 to v0.0.64 broke at the start of a new game. Everything else is
v0.0.64 unchanged; the work for the expansions moves to v0.0.66. The game needs 32 MB of Fast RAM, and the emulator
presets of this candidate have it.

## Checked by tests, not yet in play

Every change below is checked by the test suite and the gate of this candidate. None of it has been seen in play on a
build of this candidate yet; the list at the end says what to look at.

## Since v0.0.65-rc1

- **Nothing in the census office can be used or taken before the papers.** The use key refuses every take and use route
  during the registration: placed items, containers, books, dropped items and the game code's own use. People are the
  exception, so talking still works (`OPENING-REGRESSION-64`).
- **The census office's people fight with attack animations.** The opening's own characters wear the full animation set
  in a fight, and every build now writes a table of the actors' animation coverage and refuses an attackable actor that
  has no attack animations (`CENSUS-NPC-NO-ATTACK-ANIM-65`).
- **The opening's tutorial boxes name the player's own keys** (map, inventory, magic, journal, the dagger and the stats)
  in one layout. The inventory's use and drop keys can be rebound, and a check refuses fixed key letters in the boxes.
- **Readying magic no longer draws the weapon:** the bare hands come up instead (for now the fists of hand-to-hand; the
  open spell-casting hands come in v0.0.66), and readying magic and readying the weapon exclude each other
  (`READY-MAGIC-SHOWS-WEAPON-65`).
- **Talking opens the dialogue window while the player has a bounty.** A guard's or Sellus Gravius' greeting from the
  voice table is a row without text when the player has a bounty, so only his hello played and the papers could not be
  handed over. A talk now tries the dialogue window before the greeting text can stop it
  (`SELLUS-GRAVIUS-GREETING-ONLY-64`).
- **The dialogue window says in the console why it does not open:** no table, no row for the speaker, or the file; one
  line for each refusal.
- **Every actor's record binding is checked in the build.** The actor coverage table checks each placed actor's binding
  to its own record (combat sheet, reference, room entry, wander row), and the image step refuses a missing one.
- **The clerk's hold and facing also follow when his own script starts first,** so the lock-in and his facing do not
  depend on which script runs first (`OPENING-REGRESSION-64`).

## From v0.0.65-rc1 and the snapshot

- The opening runs with its holds again: a New Game keeps the state the opening sets, the dock guard walks up on the
  pier and faces the pier and the ship at his post, the pier is closed until the opening lets the player through, the
  census office shows its message boxes and holds the player in during the clerk's talk, and the idle camera stays
  still before a race is chosen.
- The torch and the fists: the debug torch lights with V, fists fight with a torch lit, an unequipped torch is not drawn
  in the hand, and the fight reads the player's live attributes and skills each frame.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## What to check in play

The opening, from the ship to Sellus Gravius and out of the office:

- On the ship: the idle camera stays still before a race is chosen; the tutorial boxes name your own keys (map,
  inventory, magic, journal, the dagger, the stats) in one layout; rebind the inventory's use and drop keys and look at
  the boxes again.
- On the pier: the dock guard walks up, can be talked to (the race choice) and faces the pier and the ship at his post;
  the pier stays closed until the opening lets you through.
- In the census office: the message boxes and the lock-in during the clerk's talk; nothing can be used or taken before the
  papers, on any route of the use key (items on tables, containers, books, dropped items); the clerk's hold and facing
  with either script starting first.
- Talking to Sellus Gravius, with and without a bounty: the dialogue window opens, the papers can be handed over, and a
  console line names the reason if the window does not open.
- Readying magic: the bare hands come up, not the weapon.
- A fight with the office's people: they use attack animations.
- Out of the office after the registration; the torch with V, and fists with a torch lit.

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
