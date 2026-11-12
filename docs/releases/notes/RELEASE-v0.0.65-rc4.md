# AmiWind v0.0.65-rc4: Reintroducing Vvardenfell

_Last updated with AmiWind v0.0.65-rc4 (12 November 2026)._

Release candidate, 12 November 2026. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.64: Gone Beyond The Gate](RELEASE-v0.0.64.md); earlier builds of this line:
[v0.0.65-rc3](RELEASE-v0.0.65-rc3.md), [v0.0.65-rc2](RELEASE-v0.0.65-rc2.md), [v0.0.65-rc1](RELEASE-v0.0.65-rc1.md) and
the snapshot [v0.0.65-dev1](RELEASE-v0.0.65-dev1.md) (dev1 and rc1 carry the earlier title, "Reintroduction").

v0.0.65, "Reintroducing Vvardenfell", completes the opening on the original game's own scripts and repairs what v0.0.62
to v0.0.64 broke at the start of a new game. rc4 adds three fixes to rc3, found in the play of its opening: the people
of the opening fight with their attack animations, the tutorial boxes after the papers come once, and no hidden door by
the census office drops the player under its floor; and the census exit no longer gives the test torch. Everything else
is v0.0.64 unchanged; the work for the expansions
moves to v0.0.66. The game needs 32 MB of Fast RAM, and the emulator presets of this candidate have it.

## Seen in play before this candidate

This candidate's engine was played on the rc3 image, in the emulator and on a Raspberry Pi 4B. On the Pi the opening
was played through the census office to Seyda Neen; no fists could be raised before the papers, as in the original. In
the emulator: the census office loaded with none of its people's movement sets refused; the clerk, when hit, put on his
full set of movements for the fight, and the hall guard stepped in with the original's line before he swung; and Seyda
Neen's door table loaded without the prison marker (32 doors).

## Since v0.0.65-rc3

- **The people of the opening fight with their attack animations.** rc2 linked each of them (the clerk, the hall guard,
  Sellus Gravius, Jiub and the guards of the ship and the dock) to a model with the full set of movements, but the engine
  refused those movement sets when the people were placed: it checked them against a fixed 256 frames, which only the
  creatures' smaller models met, and the full sets run to 2,587 frames. In a fight they stood in their idle. A worn
  model's movements are now checked against its own frames once it is loaded, as the standing model's always were
  (`CENSUS-NPC-NO-ATTACK-ANIM-65`). The notes of rc2 and rc3 said these fights already had their attack animations; they
  did not.
- **The tutorial boxes after the papers come once each.** The original shows two boxes in turn when a menu is given to
  the player: the menu announced, then a hint on using menus with the mouse. The key hints of rc2 gave both the same
  text, so after the stat review and after taking the papers the same box came twice. The second box is now left out,
  as the first already names the keys (`TUTORIAL-BOX-SHOWN-TWICE-65`).
- **No hidden door by the census office drops the player under its floor.** After the opening, going back into the
  census office from the town could load the office with the player below its floor. The original's prison marker of
  Seyda Neen (the place an arrest sends the player to, stored as a door record) had been read as a door beside the
  building, and using it put the player on the jail spot. No prison marker is taken as a door anywhere in the game now;
  all 1,512 door tables of the image were checked, and this was the only one (`DOOR-PRISON-MARKER-65`).
- **A theft in the census office is answered as in the original** (already in rc3, seen in play since): after the
  papers, a guard who sees it walks up and talks to you in the dialogue window with the original's line for the
  registration, and the bounty is cleared (`CENSUS-THEFT-NO-ARREST-65`).

- **No test torch at the census office.** The torch that never burns out, given to every player leaving the census
  office while AmiWind was a preview, is no longer given; as in the original, the player leaves with what was taken there. The
  debug console still gives one for tests.

## From v0.0.65-rc3 and earlier

Everything of [rc3](RELEASE-v0.0.65-rc3.md): the people of the opening talk in the dialogue window from the papers on,
Sellus Gravius takes the papers and gives the package, no box stands in for the window, and the dock guard steps aside at
the census office door. Everything of [rc2](RELEASE-v0.0.65-rc2.md): nothing used or taken in the census office before
the papers, the tutorial boxes naming your own keys, readying magic without the weapon, the opening's holds, the torch
and the fists.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## What to check in play

- In the census office, before the papers: no fists can be raised and nobody can be attacked, as in the original.
- After the papers: hit the clerk, the hall guard or Sellus Gravius; he fights back with his attack, hit and death
  animations.
- A theft after the papers, seen by a guard: he walks up and talks to you in the dialogue window; the bounty is cleared.
- After the papers: each tutorial box once (the inventory, then the stats).
- After the opening, back into the census office from the town by every door: the player stands on its floor.
- The courtyard: the barrel's box announces the map, and the map key opens it.
- Sellus Gravius by the use key: his dialogue window, the papers taken, Morrowind, then duties: the package, the
  directions and 87 gold; then the way out of the office.

## Known in this build

- Readied magic shows the fists of hand-to-hand; the open spell-casting hands come in v0.0.66
  (`READY-MAGIC-SHOWS-WEAPON-65`).
- The pack guar at Ahemmusa Camp is drawn with its parts apart (`ACTOR-PACK-GUAR-MESH-BROKEN-64`); shalks on Azura's
  Coast hang in the air (`CREATURE-FLOATING-SHALK-64`); the battle music can keep playing after a fight
  (`COMBAT-MUSIC-STUCK-64`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- A carried light (torch, lantern or candlestick) shows in the hand only when it is equipped while the hands are
  raised; the original
  holds it in the left hand whenever it is equipped, and puts it away while the fists or a two-handed weapon are readied.
  The original's rule comes in v0.0.66 (`HELD-LIGHT-NOT-IN-HAND-65`).
- A player jailed in Seyda Neen may be placed where the census office has no floor (`CENSUS-JAIL-SPOT-NO-FLOOR-65`);
  in v0.0.66 the census office becomes a room built like every other interior.
- Mournhold and Solstheim are not in the game; they move to v0.0.66.
