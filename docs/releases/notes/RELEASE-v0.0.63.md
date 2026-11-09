# AmiWind v0.0.63: Every Script Of Vvardenfell

_Last updated with AmiWind v0.0.63 (9 November 2026)._

Release, 9 November 2026. Running on CHIM Engine v0.2.2. Previous release: [v0.0.62: Stick To The Script](RELEASE-v0.0.62.md).

v0.0.63, "Every Script Of Vvardenfell", is the release of the base game's scripting. The three game files hold 1,207
scripts, of which the original game uses 1,074; every script of Vvardenfell that the original uses now runs. 605 run as
scripts, 9 more (the opening's and the game's main script) are carried by AmiWind's own code, and what waits belongs to
Mournhold and Solstheim, the worlds of the Tribunal and Bloodmoon expansions, which come with the next release, or
calls a function not carried out yet. Around the scripts the release brings creatures that walk, run
and fight wherever they are met, characters that fight each other and take sides, breath and drowning under water, the
original's hit chance, the original game's console commands, a text box that leaves the stats visible, and a builder that
keeps every finished unit of work. The game needs 32 MB of Fast RAM, and the emulator presets of this release have it.

The notes below cover the whole of v0.0.63 since v0.0.62, by what a player notices, not by snapshot: the five
development snapshots [dev1](RELEASE-v0.0.63-dev1.md), [dev2](RELEASE-v0.0.63-dev2.md), [dev3](RELEASE-v0.0.63-dev3.md),
[dev4](RELEASE-v0.0.63-dev4.md) and [dev5](RELEASE-v0.0.63-dev5.md), and the fixes made after dev5. dev3 was not
published on its own; it came to the main line with dev4.

## The game's scripts, by file

The 1,207 script records of the three game files, measured on the same files with the builder's own compiler. 1,074 of
them are used by the original game; the other 133 are scripts that no object, character, item, dialogue line, start
record or other script ever names or starts, so they never ran in the original game either (the developers' test and
example scripts, earlier versions replaced by others, and cut content). They stay in the game as they are, and the
[MWScript tracker](../../MWSCRIPT_FEATURES.md) lists them apart, and every other script with its state and area:

| Game file | All | Used in the original | Run | Carried by AmiWind's own code | Wait for a function | Belong to an add-on world | Not used |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Morrowind.esm | 616 | 528 | 518 | 9 | 0 | 1 | 88 |
| Tribunal.esm | 255 | 236 | 42 (in Vvardenfell) | 0 | 8 | 186 (Mournhold) | 19 |
| Bloodmoon.esm | 336 | 310 | 45 | 0 | 20 | 245 (Solstheim) | 26 |
| **All** | **1,207** | **1,074** | **605** | **9** | **28** | **432** | **133** |

- Of the 528 Morrowind.esm scripts the original uses, 518 run, 9 are carried by AmiWind's own code (the 8 of the
  character creation opening, and Main, the global script the game always starts, whose new game block AmiWind runs),
  and one, `Sound_Bubbles`, is placed only by Tribunal. So every script of the base game that the original uses runs,
  except that one add-on script.
- Of the 546 scripts Tribunal and Bloodmoon use, 87 run (42 and 45), 431 belong to Mournhold and Solstheim and cannot
  run before those worlds are built in, and 28 also call a function not carried out yet (placing their own records,
  moving into their cells, the water level).
- 605 run, against 588 in v0.0.62. 460 of the original's 504 script functions are carried out.

## What changed

### Scripts and quests

- **More of the game's script functions are carried out: 460 of 504.** Added across the snapshots, each following
  OpenMW: TurnMoonRed and TurnMoonWhite, HasItemEquipped, the forced run (ForceRun, ClearForceRun, GetForceRun),
  ExplodeSpell, GetAttacked, GetSpellEffects, the werewolf functions (BecomeWerewolf, UndoWerewolf, IsWerewolf,
  SetWerewolfAcrobatics, GetWerewolfKills; the werewolf's attributes and speed follow the game settings), GetPCTraveling,
  SetScale, ModScale and GetScale, and the Water Breathing functions; then the effect family (Get, Set and Mod of
  Chameleon, WaterWalking, SwimSpeed, SuperJump, Flying, ArmorBonus, CastPenalty, Silence, Blindness, Paralysis,
  Invisible, AttackBonus and DefendBonus), the game hour and the phases of the two moons, a placed object's starting
  position and angle, the view switches, the player's run and the jump flags, the readied spell, the actors standing on
  or colliding with an object, the armour type, SameFaction and GetFactionReaction, RemoveEffects and
  RemoveSpellEffects, the soul gems and the level-up window; and the console group, callable from scripts too: Show,
  ShowVars, ToggleScripts, ToggleAI, ResetActors, OutputRefInfo, User1 to User4 and the console's aliases
  (`MWSCRIPT-MISSING-FUNCTIONS-63`).
- **The original game's console commands** work on any reference with a target finder, with their short aliases and the
  stat family; `dbg help mw` lists them. Five toggles are mapped to the game's own switches (ToggleDebugText,
  ToggleStats, ToggleCombatStats, ToggleLights, RepairedOnMe), the console takes up to 1,000 commands, and every
  function or toggle still left names its reason on the [console commands](../../CONSOLE_COMMANDS_MORROWIND.md) page.
- **Scripts move and turn the world objects they name.** The Ghostgate switch scripts raise their portcullis and set it
  back, as in the original; scripts that move placed activators, statics, doors and containers (MoveWorld, Move, SetPos,
  SetAtStart) find them, and moved or turned objects are kept in saved games (`WORLD-BUTTONS-62`).
- **Scripts that react to taking or using an object** (for example the Dwemer ruin guardians that appear when a
  valuable object is picked up) run; none of them has been seen in play yet.
- A placed object is bound to its record's final script; the scripts carried by AmiWind's own code are listed in the
  tracker with a parity check. Placements of an add-on are keyed by the load-order index of their file and are bound
  only for the add-on worlds an image carries (`MWSCRIPT-ADDON-ATTACH-62`; none is in the image yet). A dialogue result
  reads its rows in one block.
- **Sunder** hurts its bearer without Wraithguard also when equipped from the console: equipping and unequipping from the
  console run the item's script step as the inventory does, and taking an item off tells its script so.
- **Dates read as in the original:** the journal shows 18 Last Seed (Day 3), the rest and wait window adds the hour, a
  saved game shows 18 Last Seed 9 a.m., and `dbg date` prints the lore form (`LORE-DATE-FORMAT-62`).
- **A new game starts with the original's opening state:** the character generation state, the ship guard's steps, the
  captain's hint box and the cloudy Bitter Coast weather; the dock guard keeps to his post beside the census office
  door, the prison ship's blocker is in the world, and the name, race and rest menus are opened by the scripts that open
  them in the original (`CHARGENSTATE-START-VALUE-63`, `OPENING-SHIP-GUARD-STEPS-63`, `OPENING-CAPTAIN-HINT-SUBTITLE-63`,
  `OPENING-WEATHER-NOT-CLOUDY-63`, `INTRO-DOCK-GUARD-BLOCKS-DOOR-62`, `OPENING-SHIP-BLOCKER-NOT-CONVERTED-63`).

### Combat and creatures

- **Creatures walk, run and attack again wherever they are met** (`CREATURE-BIPED-ANIMS-62`): the engine kept a fixed
  number of animation layouts and movement models for a whole outdoor session and never freed them, so creatures met
  later glided on idle frames or fought with standing poses. A full table now reuses an entry no live actor needs. The
  arena's fighters get their movement and worn items (the shield shows).
- **Creatures stand on the ground.** Walking creatures placed high above the land in the game data (942 of the 5,082
  outdoor levelled creature placements sit more than 128 units above it) are set down onto what is under them, as
  OpenMW places actors; flying and swimming creatures keep their height (`CREATURE-FLOATING-62`).
- **Hostile creatures attack on their own** when the player comes in range, also those without a wander package,
  indoors and out; a fight the player leaves through a load door is kept, and the creature fights again when he comes
  back (`ACTOR-WANDER-AGGRO-52`).
- **Characters fight each other.** A script that starts combat between two characters sets both against each other, as in
  the original (`COMBAT-ACTOR-VS-ACTOR-62`); allies and guards join fights, and followers side with the player, moving by
  one follow behaviour that the followers and escorts of the scripts' packages share.
- **Always use best attack** is a row in Options > Prefs, the same saved value as the console setting, and on by default
  (decided for the project; the original's default is off).
- **The chance to hit** follows the original's rule with the active effects: Fortify Attack, Blind, Sanctuary,
  Chameleon and Invisibility count before each swing (`COMBAT-HIT-CHANCE-EFFECTS-62`). **A blow reaches the nearest
  fighter in the original's hit cone** when the crosshair finds nobody, so a hovering cliff racer can be struck and the
  opponent's health bar shows (`COMBAT-HIT-CONTACT-CONE-62`, `ENEMY-HEALTH-BAR-62`).
- **God mode holds back every damage:** lava, falls, scripts and spells (a heal still lands); a script that lowers
  health with god mode on no longer takes it down (`GODMODE-LAVA-DEATH-62`).
- **Health and fatigue never stand above their maximum.** A map loaded fresh from the console or a restart takes the
  character's health, at most its maximum (Strength plus Endurance, halved), and restoring the stats sets it to the
  maximum; the combat sheet follows the character's maxima, also for the arena's set fighter, whose own maxima are kept
  unless the character's are higher (`PLAYER-HEALTH-OVER-MAX-63`).

### Breath and water

- **Breath under water.** The player holds his breath for the original's time under water, a breath bar shows at the top
  of the view, and when it runs out he takes the original's drowning damage with the drowning sound. Water Breathing
  from race abilities, potions, spells and worn items lets him breathe; `dbg breath` shows the state.
- **The race's Water Breathing is given again** after a load or a New Game empties the player's record, and an
  always-active effect that has no magnitude (the Argonian ability) counts once, as when it is cast; the kept value is
  read again when the race, birthsign or class spells change. This is the third attempt: see "Known in this build".

### Dialogue and the text box

- **Text box type 2 is the new default** (`SUBTITLE-BOX-HIDES-STATS-63`): the box of a spoken line (random and idle lines,
  greetings and notices) is drawn at once where it always was, without the rising animation, and blackens nothing
  outside the box, so the health, magicka and fatigue bars under the view stay visible. Type 1, the old rising strip,
  stays as a choice: Options, Prefs, "Text box" (saved), or `dbg ui textbox 1` and `dbg ui textbox 2`. Details:
  [dialogue and waiting](../../DIALOGUE_AND_WAIT.md).

### The world

- **Fire pits burn:** the fires of every frame of a world window are drawn.
- **Containers in rooms can be opened again.** An urn, chest or crate is aimed at by its placement box instead of a
  single point; every room's containers, items and creatures are counted in a census, and a check confirms that every
  container in a room can be aimed at (`ROOM-OBJECTS-MISSING-62`).
- **Items can be dropped on uneven tomb and cave floors.** A dropped item lands on the ground under the drop point, and
  on the floor under the player when the spot ahead has no ground (`DROP-ROOM-BRUSH-ENTITY-59`).
- The blight cloud at Dagoth Ur, an animated effect layer the world format would draw as a solid brown shape, is left
  out of the world (`CHIM-DAGOTH-UR-RUIN-CYLINDER-44`).

### Debug and test tools

- **`dbg tp` into any room.** Teleporting to a room by its map name (and from the scene picker) used a door of the
  listed doors first and refused with "No converted entrance" when the room's door stands on another town's or region's
  frame, or in a cell without a frame (the Andrano Ancestral Tomb). The room now loads at its own start, which the
  builder places at the first original door's arrival, so no exterior frame is needed (`CONSOLE-TP-ROOM-NAME-63`,
  `DEBUG-TP-ROOM-ENTRANCE-50`).
- **The `dbg tp` menu lists the rooms** as well as the settlements. A room shows its cell name with "(interior)" after
  it, and choosing it enters the room at its door's arrival point (`TP-MENU-INTERIORS-63`, `CONSOLE-TP-ROOM-NAME-63`). The
  longest names run past the right edge of the box (see "Known in this build"; the search still finds them).
- The console commands above, `dbg breath`, `dbg date`, `dbg ui textbox`, and `dbg restorestats` setting health to the
  maximum; the in-game `dbg` menu, `config/debug-commands.txt` and the
  [console commands page](../../AMIWIND_CONSOLE_COMMANDS.md) list them.

### The builder and the image

- **Every finished unit is kept at once.** The world (CHIM) units, the player's body parts and the first-person parts
  go into the unit cache the moment each one comes back, with one `[done/total]` line per unit; every NPC appearance,
  creature model, arena fighter, each room resident's ground fit, the guard torch verdicts, the dialogue and voice tables
  and the actor ground check are units of their own, read back at once (a unit the cache did not keep stops the stage
  with a `STORE FAILED` line). A build that stops part way keeps what was finished, and the next build reuses it
  ([UNIT-STORED-AT-MAP-END-62](../../bugs/UNIT-STORED-AT-MAP-END-62.md), `NPC-LIBRARY-NO-UNIT-CACHE-63`).
- **`--reuse-all-available`:** the builder reads the finished stages and units of every earlier run through a stage index,
  prints a plan for each stage (reused, rebuilt and why) before any stage runs, and stops when a stage would redo work
  that is already stored (`BUILD-UNIT-PREFLIGHT-63`; [BUILD_CACHE](../../BUILD_CACHE.md)).
- **The world stages rebuild only for their own inputs.** They count only the engine loader policies and the brush and
  edge-cache loaders reach, and only the values an engine file gives them when they read a single define from it, so a
  change to the actor model reader no longer rebuilds the world (`BUILD-ENGINE-SOURCE-KEY-BROAD-36`). Each stage keeps to
  its own outputs (`BUILD-STAGE-WRITES-OTHERS-OUTPUT-63`), and two stages that ran side by side are no longer both
  refused for reuse over a file a third stage wrote.
- **Risky stages first:** the player bodies are their own stage right after the census, with a pre-flight of the stored
  models, and the player view is baked in one flow before the image, so a failure shows within minutes.
- **Worker pools stay busy:** a pool hands back one result at a time and refills freed workers between two
  (`BUILD-IMAGE-QUEUE-STALL-62`).
- **Honest progress estimates:** a stage's time estimate comes from builds of a comparable size (`BUILD-ETA-FRAME-SCALING-63`);
  the build monitor shows `[done/total]` beside each running stage.
- **Shared actor shapes.** Actor models built on the same body store their repeated texture-coordinate and triangle
  blocks once in the image: 78,381,384 bytes less on the v0.0.62 payload, with the models rebuilt byte for byte when
  loaded, so resident memory is unchanged. `--shared-shapes off` keeps the earlier method
  ([PAYLOAD_SHARING](../../PAYLOAD_SHARING.md)). A read-only size report (`tools/image_size_report.py`) counts an image by
  kind, and actor skin tiles are an experimental method that is off by default.
- **The builder states what it found of Tribunal and Bloodmoon:** found, partly found or not found (a warning line), the
  records of the master, the files of the archive, the scripts that run now and those that wait, and the creatures built,
  in the build summary and the build records. It only reports; see [known inputs](../../KNOWN_INPUTS.md).

### The test suite and CI

- **The native engine checks run in smaller parts** on the source check, each with a time limit that scales on slower
  machines, and the test jobs get 45 minutes (a part took 27 of its 30 minutes on a slow runner). The timeout entry
  stays open until the checks run green with it (see "Known in this build").

## The game systems table

[Game features](../../GAME_FEATURES.md) lists 49 systems of the base game with their state, proof and the work that
carries the rest. Refreshed for this release: **7 of 49 done, 39 partial, 3 missing.** Barter, spellmaking, enchanting
and sneaking and stealing moved from missing to partial; water and lava, character creation and the HUD moved from done
to partial until their changes are seen in play.

| Area | Done | Partial | Missing | Systems |
| --- | ---: | ---: | ---: | ---: |
| World and interiors | 3 | 5 | 2 | 10 |
| Actors and behaviour | 0 | 6 | 0 | 6 |
| The player | 1 | 6 | 0 | 7 |
| Combat, death and the law | 1 | 3 | 0 | 4 |
| Magic | 0 | 4 | 1 | 5 |
| Items, containers and trade | 0 | 5 | 0 | 5 |
| Dialogue, voices, journal and factions | 0 | 4 | 0 | 4 |
| MWScript | 1 | 2 | 0 | 3 |
| Sound, music and the interface | 1 | 4 | 0 | 5 |
| **All** | **7** | **39** | **3** | **49** |

## Checked in game

A release check was played on the dev5 image at 32 MB Fast RAM in the emulator and on the Raspberry Pi 4B. Seen working:
the character's health at its maximum (40 of 40 at the start), god mode against a script's damage, the wild creatures
(creatures only), the hit chance by hand against the formula, the best-attack row in Options, the lore date forms, the
removed blight cloud (all nine frames), the builder's expansion report, and text box type 2. The Pi bench ran at 7.6
frames per second (7.4 in the v0.0.61 test image) with 2.8 at the 1 % low. Three things failed there. Two are fixed in
this release by the changes above, checked by tests, not yet seen in play: the Argonian's Water Breathing read 0 again,
and the arena's health readout stood above its maximum after `dbg maxstats`. The third stays open: Sunder's first damage
came only after about nine seconds, and then killed at once; its timing against the original's script is still to be
compared (`MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61`).

## Needs 32 MB Fast RAM

The game needs 32 MB of Fast RAM. At 16 MB parts run and over-limit interiors show the warning box.

## Not yet seen in game

The fixes below are checked by the test suite and the gate of this release, not yet in play:

- Water Breathing after a load and in a New Game, with an Argonian under water until the breath bar would run out; the
  arena's health readout after `dbg maxstats`; `dbg tp` into the Andrano Ancestral Tomb and another room whose door is
  on a far frame, and the `dbg tp` menu's room rows (type `andrano`, choose the tomb, read the arrival line).
- The containers of rooms opened by their placement box (an urn, a chest and a crate in a tomb and in a house); walking
  creatures that the game data places high above the land standing on the ground.
- The builder fixes (`BUILD-ENGINE-SOURCE-KEY-BROAD-36`, `BUILD-STAGE-WRITES-OTHERS-OUTPUT-63`,
  `BUILD-ETA-FRAME-SCALING-63`, `UNIT-STORED-AT-MAP-END-62`, `NPC-LIBRARY-NO-UNIT-CACHE-63`): checked by tests; the next
  full build of the release shows them at work.
- The Ghostgate switches on both sides and their portcullises; the Red Mountain lava with god mode; the guarded coins in
  Ald Sotha Lower Level (the guardian that appears when a valuable object is taken); a fire pit; a scripted turning
  object kept after a save and a load.
- Creatures met late in a long outdoor session (an ash slave, a corprus stalker) walking, running and attacking; a
  duel in the debug arena showing the shield; a guard joining a fight in Balmora; a follower fighting beside the player.
- The opening: the ship guard's walk, the captain's hint, cloudy weather at Seyda Neen, the dock guard beside the census
  office door; the original's console commands on a target (`dbg help mw`).
- Text box type 1 after a restart, the text box in a conversation and in passing; load times of rooms and towns with the
  shared actor shapes.
- Carried over from v0.0.62: the console history keys, the witnessed theft in the census office and the Balmora canal
  ground.

## Known in this build

- **The race's Water Breathing is not confirmed:** `UNDERWATER-BREATH-62` was reported twice and persists; this release's
  fix (the race's abilities given again after a load or a New Game) is checked by tests only.
- Sunder equipped without Wraithguard hurts after about nine seconds in the release check, not at once
  (`MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61`).
- A player who becomes a werewolf is not drawn as the werewolf (`WEREWOLF-BODY-NOT-DRAWN-63`). Show and ShowVars name no
  script locals (`MWSCRIPT-CONSOLE-LOCAL-NAMES-63`).
- The Pi bench's worst frame from the disk is 72.8 ms (48.1 in the v0.0.61 test image;
  `PI-BENCH-DISK-WORST-FRAME-63`).
- The shores and pond edges still run in saw-tooth steps; the fix needs a world rebuild
  ([INLAND-SHORE-29](../../bugs/INLAND-SHORE-29.md)).
- The game image is still larger than the original game data; the shared shapes are the first step
  (`IMAGE-BIGGER-THAN-ORIGINAL-62`).
- Files that two build stages write each are listed and kept from growing; each is to be written by one stage only
  ([BUILD-SHARED-WRITES-UNATTRIBUTED-52](../../bugs/BUILD-SHARED-WRITES-UNATTRIBUTED-52.md)). The voice table's unit key is
  not stable from one run to the next, so a build bakes six of its seven units again (about 10 s a build;
  `BUILD-TABLE-UNITS-REBAKE-63`). The image step and the CHIM validation still run on few cores in a full world rebuild
  ([BUILD-IMAGE-UNDERUSED-32](../../bugs/BUILD-IMAGE-UNDERUSED-32.md),
  [BUILD-CHIM-STAGE-SERIAL-TAIL-36](../../bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md)). The new world key is checked by tests;
  a build that proves it is still to come (`BUILD-CHIM-HEAP-KEY-LOADER-63`).
- Text box type 1 still hides the stat bars while a line shows; type 2 is the default.
- The longest room names of the `dbg tp` menu run past the box (`TP-MENU-LABEL-CUT-63`). The CI timeout of the native
  engine checks is raised and split but not yet seen green (`TEST-CHIM-BIG-FRAME-TIMEOUT-33`).
- The trip from Seyda Neen to Balmora sometimes stalls on the loading screen in the emulator; it was seen again in a gate
  smoke of this release line, and the cause is not found
  ([CHIM-SEYDA-BALMORA-LOAD-HANG-43](../../bugs/CHIM-SEYDA-BALMORA-LOAD-HANG-43.md)).
- Open in the register and met in play: a killed character comes back alive when the cell is entered again
  (`ACTOR-STATE-NOT-READ-ON-SPAWN-54`); the first-person hands have few weapon stances
  (`FIRST-PERSON-WEAPON-SETS-MISSING-54`); a few bodies of the reduced character models still show seams
  (`MESH-REDUCTION-SEAMS-62`); the guard of the opening may still turn on the spot on his way to his post
  (`GUARD-WALK-REGRESSION-62`); the Heart Chamber's load failure and a JIT freeze loading it
  (`CHIM-ROOM-HEART-CHAMBER-LOAD-50`, `DAGOTH-CHAMBER-JIT-FAULT-53`); the end of the main quest in the Heart
  Chamber cannot play yet: the Heart of Lorkhan is not placed and the chamber's collapse is not animated
  (`ENDGAME-CHAMBER-COLLAPSE-63`, planned with v0.0.64). Every other open entry is in the
  [bug register](../../BUGS.md).
- Fixed in v0.0.62 and still open in the register until seen in play: `EQUIP-ACTION-REGRESSION-62`,
  `DIALOGUE-LINKS-62`, `HELD-WEAPON-WRONG-MODEL-62`, `NEWGAME-STATE-RESET-62`, `FOCUS-NPC-OVERRIDES-ITEM-62`,
  `PERSUASION-BROKEN-62`, `STEAL-WITNESSED-NO-CRIME-60`, `TOMB-NO-CREATURES-60`, `BALMORA-GROUND-DENTS-51`. The dialogue
  result that held a frame for seconds reads one block of rows in this release and is still to be timed in play
  (`MWSCRIPT-RESULT-LONG-FRAME-62`).
- From [v0.0.62](RELEASE-v0.0.62.md): pickpocketing and owned locks are not done, and the Heart Chamber may not load at
  32 MB Fast RAM.

## Moved to v0.0.64

v0.0.64, "Gone Beyond The Gate": the Tribunal (Mournhold) and Bloodmoon (Solstheim) worlds built in by default where the
player owns them, with their scripts and scripted world events such as the Ghostgate's doors and the traps that poison
when opened, and then the remaining partial systems. Pickpocketing and owned locks, enchanting at an altar and
spellmaking in play, the per-area data tables, outdoor items that can be picked up, dropped lights with their flame and
the in-game check of the pieces listed above move with it. The list is in the [roadmap](../../ROADMAP.md).
