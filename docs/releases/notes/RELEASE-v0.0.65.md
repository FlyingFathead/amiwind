# AmiWind v0.0.65: Reintroducing Vvardenfell

_Last updated with AmiWind v0.0.65 (12 November 2026)._

Release, 12 November 2026. Running on CHIM Engine v0.2.2. Previous release:
[v0.0.64: Gone Beyond The Gate](RELEASE-v0.0.64.md). Built through the snapshot
[v0.0.65-dev1](RELEASE-v0.0.65-dev1.md) and the candidates [rc1](RELEASE-v0.0.65-rc1.md), [rc2](RELEASE-v0.0.65-rc2.md),
[rc3](RELEASE-v0.0.65-rc3.md) and [rc4](RELEASE-v0.0.65-rc4.md) (dev1 and rc1 carry the earlier title,
"Reintroduction").

## What v0.0.65 is

v0.0.65 is a fix release made from v0.0.64. It completes the opening on the original game's own scripts and repairs what
v0.0.62 to v0.0.64 broke at the start of a new game. Most of the fixes are regressions that came in when the opening was
moved onto the original game's own scripts: the opening's scenes still kept some of their earlier, separate handling, and
the two did not always agree. The dock guard, the race choice, the census office and Sellus Gravius' papers had stopped
working properly.

The opening now follows the original Morrowind more exactly: the original's own scripts run the prison ship, the pier,
the census office and Sellus Gravius' conversation, with AmiWind's rules on top (the speech boxes, the hold, nothing taken
before the papers, hints that name your own keys). Everything else is v0.0.64 unchanged; the work for the expansions moves
to v0.0.66. This release is the fourth candidate, rc4, with the final's version label.

## What is fixed

### The opening
- **New Game state.** A New Game keeps the state the opening sets instead of clearing it right away: the dock guard walks
  up on the pier, faces the pier and the ship at his post and can be talked to (the race choice); the pier is closed
  until the opening lets the player through; the idle camera stays still before a race is chosen
  (`OPENING-HOLDS-OFF-NEWGAME-64`, `OPENING-VANITY-CAMERA-64`).
- **The census office.** It shows its message boxes and holds the player in during the clerk's talk; the clerk's steps run
  by themselves, scripted lines show in the speech box, objects are drawn again when a script enables them, and the map,
  Stats and Magic windows open once the scripts have switched them on (`CENSUS-OFFICE-HOLDS-OFF-64`,
  `CENSUS-OFFICE-NO-EXIT-64`, `OBJECT-ENABLE-NOT-DRAWN-65`, `MAP-MENU-BLOCKED-COURTYARD-65`).
  Nothing in the census office can be used or taken before the papers, on every route of the use key (people excepted),
  and the clerk's hold and facing follow when his own script starts first.
- **Dialogue windows and Sellus Gravius' papers.** Talking opens the dialogue window while the player has a bounty, and
  the window says in the console why it does not open. From the papers on, the clerk, the hall guard and Sellus Gravius
  talk in the dialogue window: Sellus Gravius takes the papers in his greeting, and his answer on Morrowind leads to his
  duties, which give the package for Caius Cosades, the directions, 87 gold and the first journal entry, as in the
  original. No box stands in for a window that does not open, and the greeting shown as a row of dots is gone
  (`SELLUS-GRAVIUS-GREETING-ONLY-64`, `OPENING-SPEECH-LEADING-DOTS-65`).
- **The theft and the guard.** A theft in the census office after the papers is answered as in the original: a guard who
  sees it walks up and talks to the player in the dialogue window with the original's line for the registration, and the
  bounty is cleared (`CENSUS-THEFT-NO-ARREST-65`).
- **The dock guard's route.** After the race menu he walks to a point in front of the census office door, then steps aside
  to a post beside it, clear of the doorway, and faces the sea, the pier and the ship; before, he walked into the door
  frame and pushed against it (`PIER-GUARD-WALKS-INTO-DOOR-65`).
- **The tutorial boxes, once each.** They name the player's own keys (map, inventory, magic, journal, the dagger, the
  stats) in one layout, and the inventory's use and drop keys can be rebound. The original's second box after a menu, a
  hint on using menus with the mouse, had been given the same text as the first, so the same box came twice after the
  stat review and after the papers; it is now left out (`TUTORIAL-BOX-SHOWN-TWICE-65`). Text boxes keep clear rows above
  and below their text, message box buttons fit their labels, and the focused OK of the character windows is highlighted
  (`RACE-MENU-OK-HIGHLIGHT-65`).
- **No hidden door by the census office.** The original's prison marker of Seyda Neen, the place an arrest sends the
  player to, had been read as a door beside the building, and using it put the player on the jail spot, below the
  office's floor. No prison marker is taken as a door anywhere in the game now; all 1,512 door tables of the image were
  checked, and this was the only one (`DOOR-PRISON-MARKER-65`).

### Fights and the torch
- **Attack animations of the opening's people.** The clerk, the hall guard, Sellus Gravius, Jiub and the guards of the ship
  and the dock are linked to a model with the full set of movements, but the engine refused those movement sets when the
  people were placed: it checked them against a fixed 256 frames, which only the creatures' smaller models met, and the
  full sets run to 2,587 frames. In a fight they stood in their idle. A worn model's movements are now checked against its
  own frames once it is loaded. Every build also writes an actor animation coverage table, refuses an attackable actor
  without them, and checks each actor's binding to its own record (`CENSUS-NPC-NO-ATTACK-ANIM-65`). The notes of rc2 and
  rc3 said these fights already had their attack animations; they did not.
- **Readying magic.** It no longer draws the weapon: the bare hands come up instead, and readying magic and readying the
  weapon exclude each other (`READY-MAGIC-SHOWS-WEAPON-65`). For now the hands are the same fists as hand-to-hand.
- **The fists with a torch.** Fists fight with a torch lit; an unequipped torch is not drawn in the hand; the fight reads
  the player's live attributes and skills each frame (`TORCH-HAND-TO-HAND-64`, `TORCH-INVENTORY-PICTURE-64`,
  `HAND-TO-HAND-NO-HIT-64`).
- **No test torch at the census exit.** The torch that never burns out, given to every player leaving the census office
  while AmiWind was a preview, is no longer given; as in the original, the player leaves with what was taken there. The
  debug console lights a torch with V and still gives one for tests (`DEBUG-TORCH-64`).

## Seen in play

The opening was played in the emulator on the candidates' images (rc2 and rc3, and rc4's engine on the rc3 image): the registration with the
clerk (class, birthsign and stat review) up to the papers on the table, the dialogue windows of the clerk, the hall guard
and Sellus Gravius, and Sellus taking the papers and giving the package, the directions, the gold and the first journal
entry. The census office loaded with none of its people's movement sets refused; the clerk, when hit, put on his full set
of movements for the fight, and the hall guard stepped in with the original's line before he swung; and Seyda Neen's door
table loaded without the prison marker (32 doors). The maintainer played the opening on the Raspberry Pi 4B through the
census office to Seyda Neen; no fists could be raised before the papers, as in the original.

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box. The emulator presets
of this release have it.

## What to check in play

- In the census office, before the papers: no fists can be raised and nobody can be attacked, as in the original.
- After the papers: hit the clerk, the hall guard or Sellus Gravius; he fights back with his attack, hit and death
  animations.
- A theft after the papers, seen by a guard: he walks up and talks to you in the dialogue window; the bounty is cleared.
- After the papers: each tutorial box once (the inventory, then the stats).
- The courtyard: the barrel's box announces the map, and the map key opens it.
- After the opening, back into the census office from the town by every door: the player stands on its floor.
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
  raised; the original holds it in the left hand whenever it is equipped, and puts it away while the fists or a
  two-handed weapon are readied. The original's rule comes in v0.0.66 (`HELD-LIGHT-NOT-IN-HAND-65`).
- A player jailed in Seyda Neen may be placed where the census office has no floor (`CENSUS-JAIL-SPOT-NO-FLOOR-65`);
  in v0.0.66 the census office becomes a room built like every other interior.
- Mournhold and Solstheim are not in the game; they move to v0.0.66.
- From [v0.0.64](RELEASE-v0.0.64.md): the open entries of its Known list stand. Every other open entry is in the
  [bug register](../../BUGS.md).
