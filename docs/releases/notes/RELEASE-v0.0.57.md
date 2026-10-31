# AmiWind v0.0.57: Remembering The Emperor

Release, 31 October 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.56](RELEASE-v0.0.56.md).

v0.0.57, "Remembering The Emperor", is dedicated to the memory of Sir Patrick Stewart (1940-2026), the voice of
Emperor Uriel Septim VII.

Vvardenfell comes alive: you can talk to its people, who answer with the game's own words, and they and its creatures
wander, walk and run with their feet on the ground; every resident animates, creatures attack with their own moves,
guards light their torches at night, and far more of the game's own scripts run. The busiest places are lighter to draw, and the fog starts at 300 by default. The game needs 32 MB of
Fast RAM, and the emulator presets of this release have it. This release is the fifth development snapshot of
v0.0.57 with its version number: what was planned beyond it moves, openly, to v0.0.58.

## New since v0.0.56

### The world comes alive

- **Creatures and people move.** Creatures and residents wander and idle by their own records, including the creatures
  that come from levelled lists (about 6,000 of the outdoor ones stood still before). Hostile creatures turn on the
  player within their fight distance. The wander table is read from disk; only a small index stays in memory.
- **Walking that matches the ground.** Wandering, chasing and fleeing characters play their walk and run cycles by the
  distance they cover, so their feet no longer slide, with the original's speed limits. The animation table is read
  from disk as it is needed: about 90 KB stays in memory around Seyda Neen instead of about 600 KB.
- **Every resident animates.** Characters whose models were read by the general model loader stood still; they now
  walk, run and fight like the rest (in Seyda Neen no character is left without animation).
- **Flyers and swimmers.** Cliff racers fly instead of standing on the ground, come at the player instead of turning
  away, and strike from just above head height; slaughterfish and dreugh swim near where they start, at their own
  depth, without leaving the water, and a fighting swimmer waits at the shore when the player is on land.
- **Creature attacks**: a creature with its own animation table picks one of its own attacks each time, and swimmers
  use their swimming attacks.
- **Guards carry torches at night**: the guards that carry one in the original light it in the dark hours and in ash
  and blight storms, with the original's light reach.
- **Plants to pick in every town.** Harvestable plants now grow in every CHIM town; before, only Seyda Neen and
  Balmora had them.

### Talking to people

- **The first conversations.** Talk (E) on a character opens the dialogue window: the greeting, the topics you know
  that this character can answer, and the game's own answer to each, chosen by the original's rule (the first answer
  whose conditions hold; "Info Refusal" when only disposition stands in the way). Topics named in an answer become
  known. Goodbye or Escape closes it.
- **Disposition** is shown as the blue bar with its number across the top of the window, worked out as OpenMW does:
  the character's own disposition, the same race, your Personality, the faction reaction and your crime level.
- **The answers follow the game as it is**: the journal, globals, the dead, your items, your faction rank and your
  stats are read live, and the text fills in %PCName, %PCRank, %Cell and the game's other placeholders.
- **Light on memory**: the game's whole dialogue (2,358 topics, 23,693 answers) is a table on disk; 26.6 KB of it
  stays in memory, and a conversation reads only what it needs and frees it when it ends.

### The game's own scripts

- **957 of the game's 1,207 scripts now run whole** (715 in v0.0.54). New: crime level, reputation, faction rank and
  expulsion, faction reputation, race checks, scripted animations (PlayGroup, LoopGroup), new dialogue topics
  (AddTopic), which magic effects are on the player (GetEffect), ForceGreeting, characters sent to travel or to follow
  someone (AITravel, AIFollow), moving and turning the player and objects (Position, Rotate), and whether the player
  stands on something (GetStandingPC).
- **Using things in the world.** Using a scripted object (an activator, book, item or container whose script waits for
  it) within the game's reach runs its script, as doors and characters already did.
- **Spells and cures.** Spells cast by scripts cure diseases and deal fire, frost, shock and poison damage; shrine and
  temple cures of common and blight diseases remove those diseases.
- **Saves** keep the player's standing and known topics, which room each changed character is in, and the characters'
  travel and follow orders. Quicksave says why it did nothing when no character profile is chosen.

### Faster where it was slow

- **Fog at 300 by default.** The fog distance starts at 300 instead of 540, which brings back a good share of the frame
  rate in heavy places such as central Ald'ruhn (on a Raspberry Pi 4, 20 to 35 % at the same spots); it can still be
  changed in the console. Large interiors, the Manor District of Ald'ruhn first, fade into fog at the draw distance and
  draw nothing past it.
- **The sky fades into the fog** as the draw distance shortens, so a short view no longer shows a hard band of open sky
  above the fog. It costs nothing per pixel: the fade is part of the sky tables.
- **Lighter heavy models.** The models that cost the most to draw go through the shared mesh optimizer, with a check
  that keeps the edges where their parts meet closed: the Ashlander yurts and camp props, central Ald'ruhn, Ald Velothi,
  Bal Isra, Tel Aruhn, Holamayan, the Daedric ruins and the Dwemer ruins.
- **Smoother busy views**: the texture surface cache holds what busy views need instead of redrawing their lit
  surfaces every frame (in the prison ship's hold and around Seyda Neen the drawing time fell from about 10 ms to 3 to
  6 ms), without taking memory from the world cache at 32 MB.

### Getting around and testing

- **A settlement list for `dbg tp`**: `dbg tp` with no place name opens a searchable list of the 82 named places of
  Vvardenfell in the console font and takes you to the one you choose; every place lands on its street or on dry land
  next to it ([console commands](../../AMIWIND_CONSOLE_COMMANDS.md)). `dbg tp balmora` lands on the street outside a
  door.
- **Race stats.** The race page has a View Stats button: the race's base attributes for the chosen sex, its skill
  bonuses and its specials.
- **Toolkit world map**: copying works with a single selected cell, empty sea cells blend into the background, and a
  colour mode shows the faces placed per cell from the newest CHIM build, so the slowest places stand out. The server
  keeps running through a passing shortage of network buffers.
- **A faster builder**: the actor library and the image step use more of their cores (the actor library 512 s to
  393 s, the image's finalize 1,305 s to 862 s in the release build), and the world stage's tail went from 273 s to
  160 s. The whole game was also built from scratch, nothing reused, and every game file came out identical to this
  release's image.
- **Docs**: a section on running the game on a PiStorm-accelerated Amiga, and the plan for importing saves from the
  original game and from OpenMW. Bug pages and topic pages use plain project words, and the gate refuses assistant or
  model names anywhere in the tree.

## Moved to v0.0.58

The rest of the original's conversation (blue links in the text, persuasion and bribes, the services such as barter and
travel, disposition starting fights, choices and the journal entries of every quest), characters and creatures placed
by scripts, more weapons and the rest of the v0.0.57 list move to v0.0.58 as they stand, in the
[roadmap](../../ROADMAP.md).

## Known in this build

- A rare fault in sprite data was seen on arrival at Gnisis; the sprite is now left out of the frame instead of ending
  the game, and its cause is still being looked for
  ([SPRITE-BAD-TYPE-THREADED-56](../../bugs/SPRITE-BAD-TYPE-THREADED-56.md)).
- Loading Hlaalo Manor in Balmora with the console's map command ended the game in an earlier snapshot; through its
  door it loads and plays normally (ROOM-HLAALO-FATAL-EXIT-57).
- A few places are slow right after arriving: the Dwemer ruins and Daedric shrines with many large models in view
  ([SWEEP-SLOW-ARRIVALS-57](../../bugs/SWEEP-SLOW-ARRIVALS-57.md)), and the Manor District of Ald'ruhn
  ([INTERIOR-FAR-BLANK-MANOR-56](../../bugs/INTERIOR-FAR-BLANK-MANOR-56.md)).
- Whether a creature's attack plays its own attack animation is not yet confirmed in game; the strikes themselves land.
- On FS-UAE with a busy host, a load now and then waits forever on the emulated hard disk: nothing in the game runs,
  the emulator's disk handler never answers; restarting the emulator gets past it
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- Some rooms still load in after you arrive ([CHIM-ROOM-POPIN-51](../../bugs/CHIM-ROOM-POPIN-51.md)).
