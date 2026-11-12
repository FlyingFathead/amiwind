# AmiWind v0.0.65-rc3: Reintroducing Vvardenfell

_Last updated with AmiWind v0.0.65-rc3 (12 November 2026)._

Release candidate, 12 November 2026. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.64: Gone Beyond The Gate](RELEASE-v0.0.64.md); earlier builds of this line:
[v0.0.65-rc2](RELEASE-v0.0.65-rc2.md), [v0.0.65-rc1](RELEASE-v0.0.65-rc1.md) and the snapshot
[v0.0.65-dev1](RELEASE-v0.0.65-dev1.md) (dev1 and rc1 carry the earlier title, "Reintroduction").

v0.0.65, "Reintroducing Vvardenfell", completes the opening on the original game's own scripts and repairs what v0.0.62
to v0.0.64 broke at the start of a new game. In rc2, Sellus Gravius still could not take the papers, so the census office
could not be left; rc3 fixes that, and everyone in the opening now talks in the dialogue window as in the original.
Everything else is v0.0.64 unchanged; the work for the expansions moves to v0.0.66. The game needs 32 MB of Fast RAM,
and the emulator presets of this candidate have it.

## Seen in play before this candidate

The opening was played in the emulator on the rc2 image with this candidate's engine: the registration with the clerk
(class, birthsign and stat review) up to the papers on the table, the dialogue windows of the clerk, the hall guard and
Sellus Gravius, and Sellus taking the papers and giving the package, the directions, the gold and the first journal entry.

## Since v0.0.65-rc2

- **The people of the opening talk in the dialogue window.** Once the class, birthsign and stat review are done and the
  papers are on the table, the use key opens the dialogue window for the clerk, the hall guard and Sellus Gravius, at the
  same moment that taking things from the tables unlocks. Sellus Gravius takes the papers in his greeting; his answer on
  Morrowind leads to his duties, and that answer gives the package for Caius Cosades, the directions, 87 gold and the
  first journal entry, as in the original. Before, the window was refused for the whole registration, so the papers could
  never be handed over (`SELLUS-GRAVIUS-GREETING-ONLY-64`).
- **No box stands in for the dialogue window.** When a person's dialogue window does not open, no subtitle and no hello
  line take its place, and the console says why; the greeting shown as a row of dots is gone
  (`OPENING-SPEECH-LEADING-DOTS-65`). Spoken lines keep their subtitles while their voice plays.
- **The dock guard steps aside at the census office door.** After the race menu he walks to a point in front of the door,
  then steps aside to a post beside it, clear of the doorway, and faces the sea, the pier and the ship. Before, he walked
  into the door frame and pushed against it for about half a minute (`PIER-GUARD-WALKS-INTO-DOOR-65`).

## From v0.0.65-rc2 and earlier

Everything of [rc2](RELEASE-v0.0.65-rc2.md): nothing used or taken in the census office before the papers, the office's
people fighting with attack animations, the tutorial boxes naming your own keys, readying magic without the weapon,
the opening's holds, the torch and the fists.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## What to check in play

- On the pier: after the race, the dock guard walks to the front of the census office door, steps aside beside it and
  faces the sea; the way through the door stays clear.
- In the census office: the registration first; then E on the clerk and on the hall guard opens their dialogue windows;
  taking things from the tables works from the papers on.
- Sellus Gravius with the papers: his dialogue window, the papers taken, Morrowind, then duties: the package, the
  directions and 87 gold; then the way out of the office.

## Known in this build

- Readied magic shows the fists of hand-to-hand; the open spell-casting hands come in v0.0.66
  (`READY-MAGIC-SHOWS-WEAPON-65`).
- A crime in the census office is not yet seen answered with the guards' arrest as in the original
  (`CENSUS-THEFT-NO-ARREST-65`).
- The pack guar at Ahemmusa Camp is drawn with its parts apart (`ACTOR-PACK-GUAR-MESH-BROKEN-64`); shalks on Azura's
  Coast hang in the air (`CREATURE-FLOATING-SHALK-64`); the battle music can keep playing after a fight
  (`COMBAT-MUSIC-STUCK-64`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- Mournhold and Solstheim are not in the game; they move to v0.0.66.
