<p align="center">
  <img src="resources/media/AmiWind_logo.png" width="900" alt="AmiWind: an open-source RPG engine for the Commodore Amiga">
</p>

# AmiWind

_Last updated with AmiWind v0.0.65 (12 November 2026)._

An unofficial, experimental RPG engine and enthusiast project bringing Morrowind
to the Commodore Amiga, featuring CHIM: an AmiQuake-based engine and an asset
conversion pipeline that builds the game from your own legally obtained copy of
Morrowind, and, in time, a base for your own Amiga RPG adventures.

Like community projects such as
[OpenMW](https://openmw.org), [MGE XE](https://github.com/Hrnchamd/MGE-XE) and
[MWSE](https://github.com/MWSE/MWSE), AmiWind ships with no game data or proprietary assets.

*Not affiliated with or endorsed by Bethesda Softworks or ZeniMax. Please support the original creators: buy Morrowind.*

<p align="center">
  <img src="docs/images/amiwind-v0.0.32-gallery.gif" width="800" alt="AmiWind v0.0.32 in Vivec: ten in-game screenshots in turn">
</p>

<p align="center">Not painted backdrops: every frame is rendered in real time by the engine.</p>

More in the [gallery](docs/GALLERY.md).

## Where AmiWind stands (12 November 2026)

The newest release is **v0.0.65: Reintroducing Vvardenfell**, a fix release made from v0.0.64 ([release notes](docs/releases/notes/RELEASE-v0.0.65.md)). The previous version had a fault in the game's scripting of the start area that kept the opening from working properly (the dock guard, the race choice, the census office, Sellus Gravius' papers). v0.0.65 fixes it, and the opening now follows the original Morrowind more exactly: the original's own scripts run the prison ship, the pier, the census office and Sellus Gravius' conversation, with AmiWind's rules on top (the speech boxes, the hold, nothing taken before the papers, hints that name your own keys). It also mends the torch and the fists, readying magic (no weapon drawn) and the census office's fights. It follows the snapshot [dev1](docs/releases/notes/RELEASE-v0.0.65-dev1.md) and the candidates [rc1](docs/releases/notes/RELEASE-v0.0.65-rc1.md), [rc2](docs/releases/notes/RELEASE-v0.0.65-rc2.md), [v0.0.65-rc3](docs/releases/notes/RELEASE-v0.0.65-rc3.md) (the people of the opening talk in the dialogue window, Sellus Gravius takes the papers and gives the package, the dock guard steps aside at the door) and [v0.0.65-rc4](docs/releases/notes/RELEASE-v0.0.65-rc4.md) (the opening's people fight with their attack animations, the tutorial boxes after the papers come once, and no hidden door by the census office drops the player under its floor), runs on CHIM Engine v0.2.2 and needs 32 MB of Fast RAM. Most of its fixes were regressions that came in when the opening was moved onto the original game's own scripts, while the opening's scenes still kept some of their earlier, separate handling. The opening was played in the emulator on the candidates' images, and by the maintainer on the Raspberry Pi 4B through the census office to Seyda Neen. Known: readied magic shows the fists of hand-to-hand for now (the open spell-casting hands come in v0.0.66), a carried light shows in the hand only when it is equipped while the hands are raised (v0.0.66), a player jailed in Seyda Neen may be placed where the census office has no floor (v0.0.66), the pack guar at Ahemmusa Camp is drawn with its parts apart, shalks on Azura's Coast hang in the air, the battle music can keep playing after a fight, the trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator and the shores still run in saw-tooth steps; every other open entry is in the [bug register](docs/BUGS.md). Mournhold and Solstheim are not in the game: the work on the expansions moves to v0.0.66.

The previous release is **v0.0.64: Gone Beyond The Gate**, the release that prepares the road to the two expansion worlds
and mends what the v0.0.63 checks found ([release notes](docs/releases/notes/RELEASE-v0.0.64.md)). It follows five
development snapshots ([dev1](docs/releases/notes/RELEASE-v0.0.64-dev1.md),
[dev2](docs/releases/notes/RELEASE-v0.0.64-dev2.md), [dev3](docs/releases/notes/RELEASE-v0.0.64-dev3.md),
[dev4](docs/releases/notes/RELEASE-v0.0.64-dev4.md) and [dev5](docs/releases/notes/RELEASE-v0.0.64-dev5.md)), whose work it
carries. It runs on CHIM Engine v0.2.2 and needs 32 MB of Fast RAM. Its changes were checked by tests, and a few were seen
in play on test builds (Argonian Breathing, the Ghostgate's switches by id from the console, lava, race resistances, the
Heart Chamber loaded alone); none is yet seen on the release's own image. **Mournhold and Solstheim are not in the game
yet:** their worlds, with their scripts, move to the next version.

### Highlights of v0.0.64

- **Spells work again.** A fault since v0.0.63 left every game spell, power and enchantment without its effects (the
  engine read 32 of the 39 sections of the compiled scripts file); they take effect again, spell and trap damage meets the
  target's resistances and weaknesses, scrolls are cast from the Magic window, and Argonian Breathing is the race's
  castable spell.
- **Traps, switches and lava.** Opening a trapped door, load door or container springs its trap on the player (457 trapped
  references with 85 spells in the base game); the console activates the Ghostgate's switches by id; lava is stood in and
  kills; god mode stays on across map changes.
- **Lighter rooms and fog in large ones.** Hollow models in every room use approximate standing bevels by default (about
  46 % of the rooms' collision bytes by the builder's estimate, nothing pushed through in a sweep over 934 rooms); large
  rooms such as the Heart Chamber fade into fog instead of showing blank patches, with their own settings in Options >
  Video; cobwebs, hanging moss and leaves are drawn see-through, on by default.
- **The journal and the factions.** A quest's state follows its entries, so an ending finishes it; the stats page lists
  the player's factions; the expulsion message of a faction shows; the console takes the original journal and faction
  commands.
- **The road to Tribunal and Bloodmoon.** The builder chooses its expansion layers (`--dlc tribunal|bloodmoon|both|none`,
  `--no-dlc`) with the base world's keys independent of them, the two expansions are counted from the game files, and the
  first Solstheim frame, star-shaped spruces (a forest view goes from 45,964 faces at the median to 6,096) and the
  island's map rows and region names exist as test builds and groundwork; no expansion area is in the game image.
- **A builder that converts the world only for a change that reaches it,** makes a Raspberry Pi 4B drive image for test
  deliveries, and has a load trace and a memory line per load for the stall on the trip from Seyda Neen to Balmora.
- **The Toolkit and the progress pages** follow the newest build: the
  [CHIM progress tracker](docs/chim/PROGRESS_TRACKER.md) is written newest first with one pane for Vvardenfell, Solstheim
  and Mournhold, and the 3D Map Inspector opens CHIM rooms with collision views.
- **The game's scripts:** 605 of the 1,207 scripts run and 9 more are carried by AmiWind's own code, as in v0.0.63 (27
  wait for a function, 433 belong to Mournhold and Solstheim, 133 are named by nothing); 7 of the 49 systems of the base
  game are done, 39 partial, 3 missing ([game features](docs/GAME_FEATURES.md)).

The release before it was **v0.0.63: Every Script Of Vvardenfell**, the release of the base game's scripting
([release notes](docs/releases/notes/RELEASE-v0.0.63.md)); it followed five development snapshots
([dev1](docs/releases/notes/RELEASE-v0.0.63-dev1.md), [dev2](docs/releases/notes/RELEASE-v0.0.63-dev2.md),
[dev3](docs/releases/notes/RELEASE-v0.0.63-dev3.md), [dev4](docs/releases/notes/RELEASE-v0.0.63-dev4.md) and
[dev5](docs/releases/notes/RELEASE-v0.0.63-dev5.md)). It runs on CHIM Engine v0.2.2 and needs 32 MB of Fast RAM.

### Highlights of v0.0.63

- **The base game's scripting.** The three game files hold 1,207 scripts, of which the original game uses 1,074; the
  other 133 are scripts that no object, character, item, dialogue line, start record or other script ever names or
  starts, so they never ran in the original game either (the developers' test and example scripts, earlier versions
  replaced by others, and cut content). They stay in the game and are listed apart in the tracker. Of the 1,074 the
  original uses, 605 run as scripts and 9 are carried by AmiWind's own code (the opening's and the game's main script);
  the rest wait for Mournhold and Solstheim or for a function not carried out yet. Of Morrowind.esm's 616 scripts, 528
  are used: 518 run, 9 are carried and 1 belongs to an add-on, so every script of the base game that the original uses
  runs, except one that Tribunal places (88 are not used). Of Tribunal.esm's 255, 236 are used: 42 run in Vvardenfell, 8
  wait for a function, 186 belong to Mournhold (19 are not used). Of Bloodmoon.esm's 336, 310 are used: 45 run, 20 wait
  for a function, 245 belong to Solstheim (26 are not used). Mournhold and Solstheim come with the expansions, which
  are still to come. 460 of the original's 504 script functions are carried out, and the original game's console
  commands work on any reference (`dbg help mw`). Every script with its state:
  [the MWScript tracker](docs/MWSCRIPT_FEATURES.md).
- **The game's systems, in one table.** 49 systems of the base game with their state and proof: 7 done, 39 partial, 3
  missing ([game features](docs/GAME_FEATURES.md)).
- **Creatures and fights.** Creatures walk, run and attack wherever they are met and stand on the ground; hostile ones
  attack on sight; characters fight each other, and allies, guards and followers take sides; the original's chance to
  hit and hit cone, and an Always use best attack option in Options.
- **Breath and drowning under water,** with Water Breathing from the race, potions, spells and worn items, and a god mode
  that holds back every damage.
- **A text box that leaves the stats visible:** a spoken line's box is drawn at once (type 2, the new default; type 1
  stays a choice in Options).
- **A world that follows its scripts:** the opening as in the original, scripts that move and turn the objects they name
  (the Ghostgate's portcullises), fire pits that burn, containers in rooms that open, items that can be dropped on
  uneven tomb and cave floors.
- **A builder that keeps its work:** every finished unit is kept the moment it comes back, a later build reuses what
  exists and shows its plan before any stage runs, and actor models share their repeated shapes (78.4 MB less on the
  v0.0.62 payload).

The release before it was **v0.0.62: Stick To The Script**, the scripts, crime and alchemy release: alchemy as in
the original, the creatures placed in rooms, 588 of the game's 1,207 scripts running (the
[tracker of the game's scripts](docs/MWSCRIPT_FEATURES.md)), the census office running its own scripts, dialogue choices
as rows to pick, guards who arrest for crimes with the fine and the jail of the original, persuasion and dialogue links
that work, a room that fails to load recovered instead of locking the game, a New Game that resets the game state, a
double-click in the inventory, character models reduced with measured seams, and debug commands for gold, load and
level, running on CHIM Engine v0.2.2 and needing 32 MB of Fast RAM
([release notes](docs/releases/notes/RELEASE-v0.0.62.md)). It was cut from what was to be the third snapshot; the
second snapshot, dev2, was not delivered and its work ships in it. The one before it, **v0.0.61: Keep Your Lantern
Lit**, was the combat, magic and light release: casting with a spell-effect system, weapons and shields of every type in
their stances, enchanted items that cast, one set of stats for every person and creature, an inventory limited only by
carry weight, carriable lights that take their flame with them, theft that witnesses report, a fuller dialogue and loot
window, the first slice of an in-game recorder, and a faster game
([release notes](docs/releases/notes/RELEASE-v0.0.61.md)). Before it, **v0.0.60: Work With What
You've Got**, made beds and the two rank raises work again, levelled container contents show their items, the bodies of
the dead can be searched, and the residents read small per-area tables
([release notes](docs/releases/notes/RELEASE-v0.0.60.md)). Before that, **v0.0.59: Assembling The Bits And
Pieces, Once Again**, gave every item its own world model, a world that keeps what you change across rooms and saved
games, the player's body and hands assembled from parts, the container strip, the original's journal view, and resting
and waiting by the original's rules ([release notes](docs/releases/notes/RELEASE-v0.0.59.md)). The project's own builds have had every exterior cell of Vvardenfell on CHIM since v0.0.43 (a build from the
repository does so only from v0.0.47, when the cell list became part of the repository and the default): 1,409
cells, counting the 61 in the town frames (1,348 are one-cell region frames; 1,292 land cells, 98 sea-floor cells
and 19 open-sea cells), with no classic region maps left outdoors. What these numbers count:
[the counting table](docs/chim/CELL_TRACKER.md#what-we-count); every cell: the
[CHIM Progress Tracker](docs/chim/PROGRESS_TRACKER.md). Since v0.0.48 every interior of the base game but two (the
prison and the census office) is built as a CHIM room, with the people the game places in them. Solstheim is not
converted.

v0.0.62 shipped as what was to be its third snapshot with the final version number; its first snapshot
([dev1 notes](docs/releases/notes/RELEASE-v0.0.62-dev1.md)) added alchemy, the creatures placed in rooms, the scripts of
a new game and the falling mage, and its second ([dev2 notes](docs/releases/notes/RELEASE-v0.0.62-dev2.md)) was not
delivered. v0.0.61 shipped as its third snapshot with the final version number
([release notes](docs/releases/notes/RELEASE-v0.0.61.md)).

What comes next is in the [roadmap](docs/ROADMAP.md). The release after the fix release v0.0.65 (released: [notes](docs/releases/notes/RELEASE-v0.0.65.md)) is v0.0.66, and carries what v0.0.64 did not:
Tribunal (Mournhold) and Bloodmoon (Solstheim) built in by default where you own them (a warning when the files are
not found, and a builder switch for the base game only), their scripting, and scripted world events such as the
Ghostgate's doors and the traps of their worlds, with the tree method Solstheim's forests need; the open spell-casting
hands and every animation mode of a character; then the remaining
partial systems, among them the rest of the crime system (pickpocketing, picking owned locks), locks on doors, enchanting
and spellmaking in play, per-area data tables for containers, doors, items, activators and creatures, outdoor items that
can be picked up, dropped lights with their flame, the Constant Effect items of non-player characters, summoned
creatures that fight for the player, the shores' saw-tooth steps, and the in-game check of the pieces not yet seen in
play. No dates are promised. Items that are in no version's list yet stay in the backlog until they are scheduled.

### What v0.0.64 changed

Game spells, powers and enchantments take effect again (a fault since v0.0.63 left them without effects), spell and trap
damage meets resistances and weaknesses, scrolls are cast from the Magic window; trapped doors and containers spring
their trap, the console activates the Ghostgate's switches by id, lava kills, god mode survives map changes; a quest's
state in the journal follows its endings, the stats page lists the player's factions, the console takes the original
journal and faction commands; hollow models in every room use lighter approximate collision by default, large rooms
fade into fog with their own Options > Video rows, cobwebs and moss are drawn see-through by default; the builder chooses
its expansion layers, converts the world only for a change that reaches it and makes a Raspberry Pi 4B drive image;
Solstheim exists as test builds (a first frame, star-shaped spruces, map rows and region names), not in the game. Known
limits: Mournhold and Solstheim are not in the game, the Heart Chamber is checked only on a test build of the chamber
alone and the end of the main quest cannot play, locks on doors and lock picking are not done, the shores run in saw-tooth
steps, the stall on the trip from Seyda Neen to Balmora is not caught, and the release's changes were checked by tests, not
yet on its image. Full list: [v0.0.64 release notes](docs/releases/notes/RELEASE-v0.0.64.md).

### What v0.0.63 changed

The base game's scripting: 605 of the 1,074 scripts the original uses run and 9 more are carried by AmiWind's own code, with 460 of the
original's 504 script functions carried out (the werewolf, forced run, scale, moon, magic effect, game hour, soul gem and
console functions among them) and the original game's console commands usable on any reference; Mournhold's and
Solstheim's scripts wait for those worlds. Creatures that walk, run and attack wherever they are met, stand on the ground
and attack on sight; characters that fight each other, with allies, guards and followers taking sides; the original's
hit chance and hit cone; breath and drowning under water, god mode against every damage, and health that never stands
above its maximum. The opening closer to the original, scripts that move and turn the objects they name, fire pits,
containers in rooms that open, drops on uneven floors, dates as in the original, and `dbg tp` into any room (its menu lists the rooms too). A spoken
line's text box that leaves the stats visible. A builder that keeps every finished unit, reuses every earlier run and
shows its plan first, with world stages keyed on their own inputs, and an image whose actor models share their repeated
shapes. The [game systems table](docs/GAME_FEATURES.md) is refreshed (7 of 49 done, 39 partial, 3 missing). Known limits:
the race's Water Breathing is checked by tests only after two failed reports, a player who becomes a werewolf is not
drawn as one, pickpocketing and owned locks are not done, the Heart Chamber may not load at 32 MB Fast RAM, and the
fixes of the release were checked by tests, not yet in play. Full list:
[v0.0.63 release notes](docs/releases/notes/RELEASE-v0.0.63.md).

### What v0.0.62 changed

Alchemy as in the original (the window, potions, ingredients); the creatures placed in tombs, caves and other rooms;
588 of 1,207 game scripts running, among them the census office's own scripts, items that are carried or kept in
containers, HitOnMe, PlayBink and weather changes; dialogue choices as rows to pick, links that stay clickable, thin
scroll bars and persuasion that works; guards who arrest for theft, assault, murder and trespass, with the fine, resisting
arrest and jail, and pursuers saved in games; a failed room load that brings the player back and a New Game that resets
every state; the player's torch, the use key and the container and class windows reworked; a double-click in the
inventory; character bodies reduced with measured seams; summoned creatures; and debug commands for gold, the carrying
limit, the level and the stats. Known limits: the Heart Chamber may not load at 32 MB Fast RAM, pickpocketing and owned
locks are not done, 619 scripts do not run yet, and the new fixes were checked by tests, not yet in play. Full list:
[v0.0.62 release notes](docs/releases/notes/RELEASE-v0.0.62.md).

### What v0.0.61 changed

Player casting with a spell-effect system of 143 effects kept in saves; weapons and shields of every type in their
stances, first-person bow, crossbow and thrown stances, two styles of weapon sway and creatures that resist normal
weapons; enchanted items that cast (Cast When Strikes, Cast When Used, Constant Effect) and the class starting spells;
every person and creature carrying the full stats of its record; an inventory with no fixed number of kinds, only carry
weight; carriable lights that take their flame with them, held candles, candlesticks and lanterns drawn and lit as
themselves; witnessed theft with a bounty; dialogue notices, keys and a fuller loot window; first-person arms in their
own view, the armour rating and swimming in the worn clothes; and the first slice of an in-game recorder. Where it is faster:
Seyda Neen waits 31 to 49 % less for the disk, and containers, the inventory and place loads much faster with hundreds of kinds carried.
Known limits: a dropped light gets no flame, a Shield effect does not soften blows yet, and the full crime system,
alchemy, enchanting and spellmaking are v0.0.62. Full list: [v0.0.61 release notes](docs/releases/notes/RELEASE-v0.0.61.md).

### What v0.0.60 changed

The scripts stage is rebuilt whenever the script compiler changes, so placed beds open the rest window and the two
rank raises happen again (v0.0.59 shipped scripts of an older compiler). Containers whose contents are levelled lists
roll their items by the original's rules and keep them across saves, and a dead actor under the crosshair reads "E:
Search" and opens what it carried in the container strip. The walking residents and the residents built from parts take
their data from small tables per area, kept in memory. [The game feature tracker](docs/GAME_FEATURES.md) lists 48
systems of the base game; `dbg kill` kills the actor picked with a red crosshair, and the game shows its own message
when an essential character dies (both checked by tests, not yet in game). The builder warns early about size growth and
output names, and the reuse check is faster. Known limits: the first frame in Seyda Neen takes about a second, the
residents' walking steps can cost 200 to 800 ms on some frames (the new tables are not yet measured in game), and
casting waits for v0.0.61. Full list: [v0.0.60 release notes](docs/releases/notes/RELEASE-v0.0.60.md).

### What v0.0.59 changed

World items: 880 item models in one shared table, a model table of 512 entries per map, the game's own items placed
from it and taken, and [an index of the items you can pick up](docs/ITEMS_INDEX.md). The world change list keeps what
you change across rooms and saves, with respawn and saves that survive a change of game data. The player's body and
arms are built from parts and kept in memory, so arriving in Seyda Neen takes about a second instead of 12 to 15.
Containers open in a strip with Take All, the journal is the original's dated view, resting and waiting follow the
original, conversations open at once again, and the mouse cursor is the original's. Builds rebuild less, and the
disk images are padded to whole IDE cylinders. Known limits: containers with levelled contents open empty, bodies
cannot be looted yet, the residents' walking steps can cost up to 800 ms on some frames, and casting waits for
v0.0.60. Full list: [v0.0.59 release notes](docs/releases/notes/RELEASE-v0.0.59.md).

### What v0.0.58 changed

Dialogue: topic names in an answer are links; Admire, Intimidate, Taunt and Bribe work with the original's rules;
Travel, Training, Spells, Barter, Repair, Spellmaking and Enchanting open from the conversation; answers run their
scripts (choices, faction reactions); the greeting is picked at talk time; the journal's topic pages open the
dialogue. Character creation has a scrolled class list, the birthsign page, the install's class questions, a class of
your own and the review sheet. Aiming at something shows a box (name, weight and value for an item), placed items can
be taken, books and letters are read in place, and Left Ctrl sneaks. Creatures make their own sounds and the combat
sounds are on by default. The cliff racer is drawn whole, an NTSC machine starts, the presets show only the drawn
picture, and the AmiWind Toolkit's build monitor shows progress, gates and tests with their cores. The game's scripts
run, and a played character creation, a stolen item kept through a save and the debug restart from the main menu were
checked in game; the filled text macros in books and the journal, taking a free item, the aim box on doors, the
Fargoth greeting, your own footsteps, the creature sound test, the class questions with the install's data, a class of
your own and the class list are not yet checked in game. Known limits: the back-room table of the Census and Excise Office is
not drawn, casting waits for v0.0.59, dialogue texts still fill the player's name at run time (action-key macros show
the action's word, not the bound key), and the aim box measures the reach to an item's origin. Full list:
[v0.0.58 release notes](docs/releases/notes/RELEASE-v0.0.58.md).

### What v0.0.57 changed

Talk (E) opens the dialogue window: the greeting, the topics, and the game's own answers chosen by the original's
rule, with the blue disposition bar and answers that follow the game as it goes. People and creatures wander and idle
by their own records, walk and run by the distance they cover, and turn on the
player within their fight distance; cliff racers fly and attack, fish swim, every resident animates, and creatures
attack with their own moves. Guards light their torches at night. 957 of the game's 1,207 scripts run whole, using
scripted objects works, and saves keep the player's standing and the characters' orders. The fog starts at 300, the sky
fades into it, large interiors fade into fog, and the heaviest models are lighter. `dbg tp` opens a list of the 82
named places, and the race page shows each race's stats. Full list:
[v0.0.57 release notes](docs/releases/notes/RELEASE-v0.0.57.md).

### What v0.0.56 changed

A Raspberry Pi 4 starts straight into AmiWind from a USB stick, and `tools/pi_image/make_pi_image.sh` makes such a
stick from your own Kickstart and your own AmiWind image; on a Pi 4 the game is playable, about 10 to 50 frames a
second by scene. `dbg fps on` shows the frame rate without the debug HUD, and new teleports reach Khuul and the Vivec
Arena Pit. Full list: [v0.0.56 release notes](docs/releases/notes/RELEASE-v0.0.56.md).

### What v0.0.55 changed

Nearer Red Mountain the sky, the light on the land and, at half strength, the fog turn toward the game's own Blight
weather before the mountain's region begins (Ald'ruhn keeps its own weather), the clouds speed up toward Blight's and
the crater sky is darker still (`aw_redmountain`, on by default). The builder reads the machine's memory when there is
no container, retries a worker lost to memory with fewer units at once instead of failing, and watches the build disk
like the memory; the Toolkit's build monitor shows RAM, the disk, a memory curve and every warning of a build. The
garbage collector (`tools/build_gc.py`) now ages out the runs of old release series, and every build warns before its
disk is full and names it. The docs have folders and a generated index. Full list:
[v0.0.55 release notes](docs/releases/notes/RELEASE-v0.0.55.md).

### What v0.0.54 changed

Humanoid characters choose every animation by what they are doing (standing, walking, running, fighting, casting,
dying) by OpenMW's rules, and their hair is kept whole instead of being cut to a budget. All 3,437 NPCs and creatures
of Morrowind, Tribunal and Bloodmoon have one record each, from the game data (stats, behaviour, items, spells), kept
in saved games; the experimental scripts read and change them, and 715 of the game's 1,207 scripts now run whole.
Silt striders, boats, gondolas and guild guides travel again with the original destinations and prices. Spells can
show the game's own effect textures as sprites and particles (experimental, off by default). 34 of the 35 entrances
whose converted collision kept the use key out of reach can be used. Weather and smoke follow the game's tables,
interiors have their fog, outdoor creatures come from the levelled lists, and the interface has a crosshair, a
hide-HUD key and the player's arrow on the map. NPC Gallery v2.0 shows the game's own characters, and an engine
change no longer rebuilds the CHIM world.

### Memory: 32 MB of Fast RAM is the safe minimum (23 October 2026)

The base game's main pieces are finally coming together:
- every interior of the base game on its way in as a CHIM room;
- the people and creatures standing where the game places them;
- every NPC speaking with its own voice.

The good news: the whole thing still takes a reasonable amount of disk space. The sad part: some of it would need
far too much squeezing to fit a 16 MB expansion. Everything runs so smoothly with 32 MB that 32 MB is the default
from here on. On today's accelerator cards that is rarely a problem: many of them carry well over 32 MB of Fast
RAM, and AmiWind puts the extra to use. Most of the island can still be explored with 16 MB: of the 1,134 interiors in the image, the 16
biggest ask for 32 MB at the door (and 5 region frames at their border), and the rest open as before.

For now the game requires **32 MB of Fast RAM, the safe minimum**, which should be enough for the entire game. More
RAM is used automatically (a larger game heap, CHIM's caches and reading ahead). 16 MB still starts, with a warning
at boot and a warning box for a few seconds before the AmiWind logo (from v0.0.52), but parts of the game will run
incorrectly or not at all. The emulator presets and the launcher start with 32 MB. Why, with the measured
numbers: [why 32 MB](docs/REAL_HARDWARE.md#why-32-mb-of-fast-ram).

### What v0.0.53 changed

The doors of a region frame work after you walk into it across a frame border: before, the engine read only the door
table of the frame the game started in, and 830 of the 1,102 exterior entrances were dead once walked into. Every
build now runs the engine's own door code over all 1,102 entrances (the prompt, the use key, the way back out, and
the wall between the player and the door), and the count of usable entrances may only go up; 1,102 of 1,102 work after
a walk over a frame border. A stricter check, which also traces the wall between the player and the door in the world's own collision, counts
1,067 usable, 31 more than before the release's doorway slack; the 35 left (Daedric shrine steps the player slides
off, raised trapdoors, a few Dwemer and hut doors) move to v0.0.54. The four
dancers of the base game who have a dance of their own (Desele's House of Earthly Delights in Suran among them) now
dance it, from the shared animation table. A Halloween scene on the animation stage (the game's own skeletons, the
Suran dancers and Dagoth Ur dancing to a beat, filmed by a camera director) is also the standard benchmark: `aw bench
halloween` (the aliases `aw halloweenbench` and `dbg halloween bench`) plays the same 600 frames on every machine and
prints one line to copy. In v0.0.53 the scene and the benchmark need a build with the cast (`--miniwind-halloween`);
from v0.0.54 every full-world build carries the cast (about 1 MB, loaded only when the scene starts), so the
benchmark works in the release images ([HALLOWEEN.md](docs/HALLOWEEN.md)). A build can carry one track of your own for the scene (the custom OST slot); public builds
ship no song. Builds check the free disk space first and stop
before their first stage when it is short, the GitHub checks run in parallel jobs, a version-only change no longer
rebuilds the CHIM world, and a maintainer's deferral to a version stops counting at that version.

### What v0.0.52 changed

Every character moves by one shared skeleton and one shared action table, as in the original game, instead of frames
baked one character at a time ([modular NPCs](docs/MODULAR_NPCS.md#getting-npc-movement-right)): the base game's
2,612 placed characters take 512 MB of models instead of 3,222 MB, and each can walk, run, swim, fight with every
weapon, cast, block, dodge, fall and die, with weapons, shields and the guards' torches on the hand bones. On a slow
68040 a town frame draws as fast as with baked characters. Dagoth Ur, his whole original model, and the Heart of
Lorkhan are in Akulakhan's Chamber for the first time, and the chamber loads on 32 MB, also coming from a town. A full
memory no longer stops the machine with a Software Failure, and a WARNING box says so when there is less than 32 MB.

Earlier releases: the [release notes](docs/releases/notes/RELEASE-v0.0.54.md) link back through every version, and the sections the
front page used to carry are kept in [earlier README sections](docs/README_ARCHIVE.md).

### What works, and the honest limits

- **The whole main island is in.** All of Vvardenfell's outdoors, 1,409 exterior cells, is converted and streamed
  as you walk; visit the towns and cities of the main island, such as Seyda Neen, Balmora, Vivec and many others.
- **Every interior of Vvardenfell is in.** 1,121 of its 1,123 are CHIM rooms; the two where the opening sequence
  runs (the prison ship and the census office) stay classic room maps on purpose until rooms have object state. The
  people and creatures the game places in a room stand in it with their full set of animations and their own voices.
- **Every door leads in and back out.** All 3,133 load doors and markers of the base game resolve through one door
  table; the build fails if one does not ([door graph](docs/chim/DOOR_GRAPH.md)). Since v0.0.53 the build also runs
  the engine's own door code over all 1,102 exterior entrances, also after a walk across a frame border, and its
  count of usable entrances may only go up.
- **Play:** create your character through the opening sequence; the inventory (no limit on the kinds of item, only
  carry weight, with the armour rating and a preview that follows what you wear), the journal and the map; saving and
  loading, with what you change in the world staying changed; melee combat with the original's rules (damage, armour,
  block, knockdown, knockout, fatigue, death), creatures that walk, run and attack with their own animations, and
  weapons and shields of every type in first and third person;
  casting spells, with the original's chance, cost and effects, scrolls cast from the Magic window, and enchanted items that cast; traps that spring when a trapped door or container is opened; talking to people
  (topics, choices, disposition, persuasion and the services; spoken lines show in a box that leaves the stats visible); containers and the bodies of the dead opened in a strip;
  crimes seen by a witness bring the guards, with the arrest, the fine and jail; alchemy (making and drinking potions); breath and drowning under water; a torch, a candle, a candlestick or a lantern in the hand
  to explore Vvardenfell at night and underground; mushrooms to pick indoors and out; the original movement speeds;
  weather by region, and music streamed from disk; travel by silt strider, boat, gondola and guild guide.
- **Not yet:** Mournhold (Tribunal) and Solstheim (Bloodmoon), and with them their scripts (the goal of the next release); the quests played through
  from start to end in a test; the end of the main quest in the Heart Chamber; pickpocketing and picking owned locks, trespass,
  making your own enchantments, locks on doors, the
  shot of a bow or a thrown weapon, schedules by the time of day and most of the scripted AI packages, and Dagoth Ur's
  fight and voice. The jail markers are in the door table for the jail system to come. The Unmarked Shipwreck's upper
  trapdoor still keeps the use key out of reach ([v0.0.55 release notes](docs/releases/notes/RELEASE-v0.0.55.md#known-in-this-build)).
  [The game feature tracker](docs/GAME_FEATURES.md) lists every system of the base game with its state.
- **The game's scripts:** the three game files hold 1,207 script records, 1,074 of them used by the original game.
  Every one of Vvardenfell that the original runs also runs here: 605 run as scripts and 9 more, the opening's and the
  game's main script, are carried by the game's own code (in every Vvardenfell region all of them, for example the
  Ascadian Isles 115 of 115 and the Ashlands 66 of 66). The other 460 of the 1,074 wait: 433 belong to Mournhold or
  Solstheim and wait for those worlds to be built (one of them is a Morrowind.esm script that Tribunal places), and 27
  also call a function not carried out yet, such as placing their own records there. The remaining 133 are not named or
  started by anything in the original game and never ran there either; they stay in the game and are listed apart.
  460 of the original's 504 script functions are carried out
  ([the MWScript tracker](docs/MWSCRIPT_FEATURES.md) lists every script with its state and area).
- The reference target is an A1200 with AGA, a 68040 with FPU, 2 MiB Chip and 32 MiB Fast RAM (the safe minimum;
  16 MiB starts with a warning); development and
  every performance figure so far come from emulators and are relative. The first real-hardware figures, from testers
  in October 2026: about 0.2 frames per second on an A4000 with a 68060 at 100 MHz (an earlier build), and about 0.6
  to 0.7 on an A3000 with a 68060 at 80 MHz through RTG (a tester's own modified build): not playable yet. The game
  aims at today's accelerated 68k Amigas, with a classic 68060 as the floor. See [AmiWind on real hardware](docs/REAL_HARDWARE.md) and [AmiWind on the 68060](docs/68060.md).
- Crossing from one outdoor cell to the next is streamed; walking into or out of a town is still a level change
  ([cell crossings](docs/chim/CELL_CROSSINGS.md)).
- The known problems are listed in [the bug register](docs/BUGS.md) and under "Known in this build" in each
  release's notes.

## Build it from your own Morrowind

**Original Morrowind game files are required. You must provide your own copy**, and you need your own licensed
Amiga Kickstart 3.1 ROM to run the result. The repository includes neither. AmiWind recommends the GOG GOTY edition
(the best tested; the Steam GOTY edition is a supported fallback with bitmap fonts). More: [About AmiWind](docs/ABOUT.md).

On Ubuntu/Debian (or Ubuntu under WSL), compile with:

```sh
./build.sh --autoinstall
```

and, with FS-UAE installed, build and run in one go:

```sh
./build.sh --autoinstall --autorun-fs-uae \
  --kickstart-file "/path/to/your/kickstart-3.1-a1200.rom"
```

`--autoinstall --plan` shows the setup steps without installing anything. On Windows start with
`.\setup-windows.cmd -Plan` (experimental; [Windows setup guide](docs/WINDOWS_BUILD.md)). A normal build includes
everything the release ships; the default builder is CHIM. The recorded v0.0.31 Seyda Neen maps
(`--seyda-recorded DIR`) are optional and NOT RECOMMENDED since v0.0.31: by default Seyda Neen is converted from
your data ([which Seyda Neen is in my build](docs/LINUX_BUILD.md#which-seyda-neen-is-in-my-build)). For a quick
test image of one spot see [MiniWind: the test ground](docs/MINIWIND.md), the
[build type reference](docs/MINIWIND_PLAYTESTER.md) and the [CHIM build guide](docs/chim/build_guide/README.md).

Everything else about building, the build speed options, the FPU support library and running the image in FS-UAE or
WinUAE: [Building and playing](docs/BUILDING_AND_PLAYING.md), the [Linux build guide](docs/LINUX_BUILD.md) and the
[FS-UAE launcher](docs/FS-UAE-LAUNCHER.md). The newest emulator presets are
[`AmiWind-v0.0.65-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.65-FS-UAE.fs-uae) and
[`AmiWind-v0.0.65-WinUAE.uae`](resources/emulators/AmiWind-v0.0.65-WinUAE.uae) (for the fourth candidate:
[`AmiWind-v0.0.65-rc4-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.65-rc4-FS-UAE.fs-uae) and
[`AmiWind-v0.0.65-rc4-WinUAE.uae`](resources/emulators/AmiWind-v0.0.65-rc4-WinUAE.uae); for the third candidate:
[`AmiWind-v0.0.65-rc3-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.65-rc3-FS-UAE.fs-uae) and
[`AmiWind-v0.0.65-rc3-WinUAE.uae`](resources/emulators/AmiWind-v0.0.65-rc3-WinUAE.uae); for the second candidate:
[`AmiWind-v0.0.65-rc2-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.65-rc2-FS-UAE.fs-uae) and
[`AmiWind-v0.0.65-rc2-WinUAE.uae`](resources/emulators/AmiWind-v0.0.65-rc2-WinUAE.uae); for the first candidate:
[`AmiWind-v0.0.65-rc1-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.65-rc1-FS-UAE.fs-uae) and
[`AmiWind-v0.0.65-rc1-WinUAE.uae`](resources/emulators/AmiWind-v0.0.65-rc1-WinUAE.uae); for the first snapshot:
[`AmiWind-v0.0.65-dev1-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.65-dev1-FS-UAE.fs-uae) and
[`AmiWind-v0.0.65-dev1-WinUAE.uae`](resources/emulators/AmiWind-v0.0.65-dev1-WinUAE.uae); for the v0.0.64 release:
[`AmiWind-v0.0.64-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.64-FS-UAE.fs-uae) and
[`AmiWind-v0.0.64-WinUAE.uae`](resources/emulators/AmiWind-v0.0.64-WinUAE.uae); for the last snapshot of it:
[`AmiWind-v0.0.64-dev5-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.64-dev5-FS-UAE.fs-uae) and
[`AmiWind-v0.0.64-dev5-WinUAE.uae`](resources/emulators/AmiWind-v0.0.64-dev5-WinUAE.uae); then
[`AmiWind-v0.0.64-dev4-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.64-dev4-FS-UAE.fs-uae) and
[`AmiWind-v0.0.64-dev4-WinUAE.uae`](resources/emulators/AmiWind-v0.0.64-dev4-WinUAE.uae); then
[`AmiWind-v0.0.64-dev3-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.64-dev3-FS-UAE.fs-uae) and
[`AmiWind-v0.0.64-dev3-WinUAE.uae`](resources/emulators/AmiWind-v0.0.64-dev3-WinUAE.uae); then
[`AmiWind-v0.0.64-dev2-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.64-dev2-FS-UAE.fs-uae) and
[`AmiWind-v0.0.64-dev2-WinUAE.uae`](resources/emulators/AmiWind-v0.0.64-dev2-WinUAE.uae); for the first:
[`AmiWind-v0.0.64-dev1-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.64-dev1-FS-UAE.fs-uae) and
[`AmiWind-v0.0.64-dev1-WinUAE.uae`](resources/emulators/AmiWind-v0.0.64-dev1-WinUAE.uae); for the v0.0.63 release:
[`AmiWind-v0.0.63-FS-UAE.fs-uae`](resources/emulators/AmiWind-v0.0.63-FS-UAE.fs-uae) and
[`AmiWind-v0.0.63-WinUAE.uae`](resources/emulators/AmiWind-v0.0.63-WinUAE.uae)); all start with 32 MB of
Fast RAM, which is the requirement.

## Where to read more

- Every document, by topic: [the documentation index](docs/README.md) · every release with its notes:
  [releases](docs/releases/README.md)
- Project: [FAQ](docs/FAQ.md) · [Gallery](docs/GALLERY.md) · [Project state](docs/PROJECT_STATE.md) ·
  [Roadmap](docs/ROADMAP.md) · [Changelog](docs/CHANGELOG.md) · [Open bug reports](docs/BUGS.md)
- How it works: [Architecture](docs/ARCHITECTURE.md) · [Actor placement](docs/ACTOR_PLACEMENT.md) · [CHIM](docs/chim/README.md) ·
  [CHIM progress tracker](docs/chim/PROGRESS_TRACKER.md) · [CHIM progress map (colours)](docs/chim/CHIM_PROGRESS_MAP.md) · [Asset coverage](docs/ASSET_COVERAGE.md) · [Game features](docs/GAME_FEATURES.md)
- Building: [Building and playing](docs/BUILDING_AND_PLAYING.md) · [Build dependencies](docs/BUILD_DEPENDENCIES.md) ·
  [Release workflow](docs/RELEASE_WORKFLOW.md) · [Hosted CI jobs](docs/CI.md)
- Development: [Repository layout](docs/REPOSITORY_LAYOUT.md) · [Project rules](docs/PROJECT_RULES.md) (including the
  required Linux and Windows compatibility) · [Polycount Inspector](docs/POLYCOUNT_INSPECTOR.md) ·
  [Earlier README sections](docs/README_ARCHIVE.md)
- Licences and credits: [About AmiWind](docs/ABOUT.md) · [Licensing and credits](docs/LICENSING_AND_CREDITS.md)

## About

Created by **FlyingFathead a.k.a. Horstator**. Thanks to: **ChaosWhisperer**.
**Official project repository:** [FlyingFathead/amiwind](https://github.com/FlyingFathead/amiwind).

AmiWind runs on the CHIM engine, built on GPLv2 code from **id Software's Quake** (John Carmack and the id team) and
its Amiga port **AmiQuake** (Peter McGavin, NovaCoder, Stephen Leary). The CHIM builder that converts your own
Morrowind files is GPLv3 ([LICENSE](LICENSE)). The public source package holds no Quake or Morrowind game data, ROMs
or compiled AmiWind executable; game images you build yourself are private build outputs. Copyrights stay with their
holders; the full statement is in [About AmiWind](docs/ABOUT.md).

> Massive thanks to everyone in the Amiga community who have been willing to
> share code and ideas to make this dream come true to a beloved platform.
> *May the wind be on your back!*

---

<p align="center"><i>AmiWind is brought to you by <a href="https://github.com/FlyingFathead/">FlyingFathead</a></i></p>
