# The opening, step by step

_Last updated with AmiWind v0.0.67 (18 November 2026)._

What a New Game plays, from the prison ship to leaving the Census and Excise Office, with what the player sees and
may do at each step. This is the reference the opening checks follow: the in-game walk of every dev build and the
tests in `tests/test_game_reset.py` and `tests/aga_opening_test.c`.
The opening runs on the original's character creation scripts with AmiWind's rules on top: eight of the scripts are
carried by the game's own code, the others run as scripts, and the rules below (the speech boxes, the hold, nothing taken
before the papers, hints that name the player's own keys) are AmiWind's
([MWScript features](MWSCRIPT_FEATURES.md)).
It describes the default, `census type amiwind`; `census type legacy` and `census type original` are kept for
comparisons (`docs/AMIWIND_CONSOLE_COMMANDS.md`).

The story state of every step is printed by `aw_intro_status` ("Opening N" is the stage: 1 ship, 2 dock, 3 race,
4 office, 5 class, 6 birthsign, 7 review, 8 papers, 9 courtyard, 10 captain, 11 released; CharGenState stays 10
until the release, then -1).

## 1. The prison ship (stage 1)

- Right after New Game: stage 1 and CharGenState 10 (a New Game never starts as a free game).
- Jiub asks the name; the name window opens; Enter accepts it.
- The idle camera stays still before a race is chosen.
- The ship's guard comes, speaks, and the movement hint shows; the player follows him to the hatch.
- The tutorial boxes name the keys the player has bound (map, inventory, magic, journal, the dagger, the stats), in one
  layout; the inventory's use and drop keys can be rebound.
- The ship's blockers hold the player inside the ship's walkable parts.

## 2. The pier (stage 2)

- The player arrives on deck and walks down to the pier.
- The pier is closed: the player cannot leave it or walk into the water (invisible barriers along both sides and at
  the shore end, only while the registration runs).
- The dock guard walks toward the plank to meet the player, along the middle of the pier. When the player is near him
  he stops, the player is held, and he speaks his first line (with its text in the speech box).
- His walks follow the pier's centre line, measured from the built world's own collision: the line of the dock pieces,
  with the posts in pairs at the middle of each piece and 19 units of room for him on either side of the line. He never
  steers round anything there: someone standing on the line is waited for. Every tick of his walks his body is tested
  where it stands; `aw_intro_status` prints how many ticks it stood inside a solid (the opening journey checks it is
  none), how far he is from his post and which walk ran. His placement fits his feet to the deck, which leaves his
  body box 5.75 units into the deck where he waits; before a walk's first step the box is lifted onto the deck by the
  same search a first step makes, and the status line counts that apart ("settled at the start").

## 3. The race menu (stage 3)

- After his first line the race window opens ("Choose your appearance": race, sex, face, hair). Enter steps through
  the rows and accepts; the chosen race stays.
- He speaks his second line, then walks the middle of the pier to its end by the office door, steps to the point in
  front of the door and on to his post left of it (286 -214 in the dock map's units), out of the doorway, and turns
  slowly to face the player while the player is near (toward the pier and the ship when the player is gone). The
  original's own walk ends on the same side of the door. `dbg opening dock direct` brings back the earlier walk (a
  straight line from where he met the player, which could leave him among the posts and pilings at the pier's end),
  `dbg opening dock fixed` the default.
- Near him, his third line repeats ("Head on in.").

## 4. The Census and Excise Office (stages 4-8)

- The office door opens. The door back to the pier and the exit stay shut with a line saying why.
- As the player walks up to the clerk he turns to the player and starts his talk by himself; his lines show in the
  speech box. From then until his stat review is done the player is held in place. The hold and his facing follow
  whichever script starts the registration first, his own or the office's.
- Nothing in the office can be taken or used until the review is done (a line says to finish the registration). The use
  key refuses every route: placed items, containers, books, dropped items and the game code's own use. People are the
  exception, so talking still works.
- If a fight starts, the office's people use the full set of attack animations.
- His talk opens the class window, then the birthsign window, then the stat review, each with his line between them.
- After the review the papers are shown and he says to take them; from here the normal rules apply: items can be
  taken (the tutorial items show their messages), stealing in view is a crime.

## 5. The papers, the hall door and the courtyard (stages 8-10)

- Taking the papers moves to the courtyard stage and enables the inventory. The map, Stats and Magic windows open once
  the game's scripts have switched them on (the Magic window after the courtyard's ring, as in the original).
- The door guard unlocks the hall door once the player carries the papers.
- In the courtyard the barrel holds the ring; taking it moves to the captain stage.

## 6. Sellus Gravius and the exit (stages 10-11)

- Near the captain a message box says how to talk to him.
- Talking to him opens the ordinary dialogue window, also while the player has a bounty (a talk tries the window before
  the voice table's greeting can stop it); if the window does not open, the console says why. His greeting takes the papers; "duties" gives the package, the
  orders to Balmora and 87 gold.
- The exit door opens only with the package; leaving releases the player (stage 11, CharGenState -1).
