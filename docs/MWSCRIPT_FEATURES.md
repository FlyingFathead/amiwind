# MWScript features

_Last updated with AmiWind v0.0.69-dev7 (27 November 2026)._

<!-- contents start -->
## Contents

- [Why the others do not run](#why-the-others-do-not-run)
- [AmiWind adaptations](#amiwind-adaptations)
  - [CharGen](#chargen)
  - [CharGenBoatNPC](#chargenboatnpc)
  - [CharGenBoatWomen](#chargenboatwomen)
  - [CharGenDisable](#chargendisable)
  - [CharGenNameNPC](#chargennamenpc)
  - [CharGenRaceNPC](#chargenracenpc)
  - [CharGenWalkNPC](#chargenwalknpc)
  - [Main](#main)
- [Follows OpenMW's fix](#follows-openmws-fix)
- [By area](#by-area)
- [By function](#by-function)
  - [Effect in play](#effect-in-play)
- [Every script](#every-script)
  - [Morrowind](#morrowind)
  - [Tribunal](#tribunal)
  - [Bloodmoon](#bloodmoon)
- [Not used in the original game](#not-used-in-the-original-game)
  - [Morrowind (88)](#morrowind-88)
  - [Tribunal (19)](#tribunal-19)
  - [Bloodmoon (26)](#bloodmoon-26)

<!-- contents end -->

<!-- Generated whole by tools/mwscript_features.py render from docs/mwscript-features.json; do not edit by hand. -->

One row per script record of the game: what names it, where it stands, which functions it calls and what its conditions test, and what state AmiWind has it in. The data is measured from the game's masters with the builder's own compiler; the page lists record ids, counts and states only. When the work list runs dry, the scripting work is taken from here row by row, toward the next landmark: every game script playing as in the original, which means every function the scripts call with the original's effect in play (the section Effect in play) and every script AmiWind's own code does an adaptation with no step open.

Of the 1,074 scripts the original game uses, **1,066 run** as scripts and **7 are AmiWind adaptations** (AmiWind's own code does every step of the script). The rest, by state: done by AmiWind's own code with steps still open 1, using a function the interpreter lacks 0, attached but not run 0, compiled but not attached 0, placed only in add-on cells the image does not carry 0, not converted 0. A script that runs is not yet a script that plays as the original: Effect in play, under By function, says for each function the scripts call how much of the original's effect the engine has. The 133 scripts not used in the original game (they never run there either: test and example scripts, replaced versions, cut content) are not counted toward completion and are listed apart under Not used in the original game.

| State | Scripts | What it means |
| --- | ---: | --- |
| runs | 1,066 | compiles whole, and the build attaches it to its objects or starts it (a record that is never placed: while the player carries its item, on the actor a levelled list gives, or on the object a script places; a script with no function, whose own locals the dialogue keeps on the speaker without it, counts as running) |
| AmiWind adaptation | 7 | not run as a script because AmiWind's own code does what it does, feature complete: every step the original's script does is carried out (the section AmiWind adaptations names the code and compares it step by step) |
| AmiWind's own code, steps open | 1 | not run as a script; AmiWind's own code does part of what it does, and at least one step of the script is missing or different: a gap, not an adaptation (its open steps are in the section AmiWind adaptations) |
| uses a function the interpreter lacks | 0 | compiles, but calls at least one function the interpreter does not carry out yet (those calls do nothing and read 0) |
| attached, not run | 0 | the game attaches it, but the build does not run it: a hand-written rule carries it, or nothing it does is seen yet |
| compiled, not attached | 0 | compiles whole, but nothing in the build attaches or starts it: its records are never placed, and nothing makes them at run time yet |
| only in an add-on world | 0 | compiles whole, but its records are placed (or made by scripts) only in cells of Mournhold or Solstheim that the image does not carry (the image's own districts and rooms count as carried: the measurement reads them from the build) |
| not converted | 0 | does not compile |
| **Used in the original game** | **1,074** | |
| Not used in the original game (never runs there either; not counted toward completion) | 133 | compiles whole, but no record, start, StartScript or dialogue result names it, or the records that name it are never placed and nothing makes them: it never runs in the original either |
| **All script records** | **1,207** | |

| Game file | All | Used in the original | Runs | Adaptation | Own code, steps open | Function missing | Attached, not run | Not attached | Add-on world | Not converted | Not used |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Morrowind.esm | 616 | 528 | 520 | 7 | 1 | 0 | 0 | 0 | 0 | 0 | 88 |
| Tribunal.esm | 255 | 236 | 236 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 19 |
| Bloodmoon.esm | 336 | 310 | 310 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 26 |

Dialogue result scripts (the lines a topic answer runs) are compiled as scripts of their own: 7,411 results, 7,411 run whole, 0 use a function the interpreter lacks, 0 are not converted.

Dialogue answers that start or change a fight (StartCombat, SetFight, ModFight): 293.

| Engine path | Answers |
| --- | ---: |
| another actor's Fight changes: weighed by that actor's next aggression check | 7 |
| another actor attacks (StartCombat on a reference) | 9 |
| the speaker's Fight changes: weighed when the talk ends | 148 |
| the speaker attacks (StartCombat): found by the answer's reference | 124 |
| a fight between two actors: both are set against each other (since v0.0.63) | 5 |

Measured on 27 November 2026 from the three masters (Morrowind, Tribunal, Bloodmoon) with the builder's own compiler (tools/mwscript), 11,171 placed scripted references, 11,542 bindings in the compiled file, 4 start scripts. The states are worked out again from the interpreter's function table (tools/mwscript/functions.py) whenever the page is rendered, so a function carried out later moves its scripts without a new measurement.

The image measured: build v0.0.69-dev6. Its scripts stage bound the own placements of Tribunal, Bloodmoon; the image carries 5 outdoor districts, 1,321 rooms of the interior store and 593 add-on exterior cells, and 2,447 of the 2,447 add-on bindings in the file sit in those cells (Tribunal 1,227, Bloodmoon 1,220). A script placed only in add-on cells outside them is "only in an add-on world".

## Why the others do not run

Each script that does not run, by its reason, and where its area is: Vvardenfell (the world in the image, including the start scripts, the dialogue-only ones and records with no place) or an add-on world (Mournhold, Solstheim). A missing function is one reason here; By function names the functions.

| State | Reason | Vvardenfell | Add-on world | All |
| --- | --- | ---: | ---: | ---: |
| named by nothing | nothing names it: it never runs in the original either | 122 | 0 | 122 |
| named by nothing | its records are never placed and nothing makes them: it never runs in the original either | 11 | 0 | 11 |
| AmiWind's own code, steps open | engine/aga/src/aw_mwvm.c AW_MwvmNewGame (the game always runs it, OpenMW GlobalScripts::addStartup) does it, but 1 of its 3 steps is not as the script: every frame | 1 | 0 | 1 |

## AmiWind adaptations

The game scripts whose work AmiWind's own code does instead of running them, each with the code that does it and a step-by-step comparison with the script (the tracker of these is config/mwscript-counterparts.json, checked by its test). A script is an **AmiWind adaptation** only when it is feature complete: every step the original's script does is carried out. With a step that is missing or different it is not an adaptation but a gap, counted as "AmiWind's own code, steps open", and its open steps are listed under its name below. Of the 8 scripts here, 7 are adaptations and 1 have open steps. Decided for the project: the opening from the prison ship to the census office is AmiWind's own implementation.

| Script | What it does | AmiWind counterpart | State | Open steps | Seen in play | Register |
| --- | --- | --- | --- | ---: | --- | --- |
| CharGen | the new game's start: the player's controls off, the player placed on the prison ship, the Bitter Coast weather set to cloudy, CharGenState 10 | engine/aga/src/aw_story.c AW_StoryReset (with aw_intro.c AW_IntroBegin) | AmiWind adaptation | 0 | not yet | OPENING-WEATHER-NOT-CLOUDY-63, CHARGENSTATE-START-VALUE-63, OPENING-FIGHTING-ON-BEFORE-PAPERS-66 |
| CharGenBoatNPC | the guard on deck: sends the player down to the dock, repeats | engine/aga/src/aw_intro.c AW_IntroTick, the deck_state steps | AmiWind adaptation | 0 | not yet | - |
| CharGenBoatWomen | the woman on the upper deck: hurries the player, repeats | engine/aga/src/aw_intro.c AW_IntroTick, the upper_state steps | AmiWind adaptation | 0 | not yet | - |
| CharGenDisable | the opening's invisible blockers (the ACTI CharGenCollision - extra placements) kept while CharGenState is 0 or over, disabled after | engine/aga/src/aw_barrier.c AW_BarrierClip (the blockers converted by tools/prepare_character.py, active while AW_StoryRestricted; since v0.0.68 each one also off once a script's Disable of its reference is in the world change list, the references from id1/world-barriers.txt) | AmiWind adaptation | 0 | not yet | OPENING-SHIP-BLOCKER-NOT-CONVERTED-63 |
| CharGenNameNPC | Jiub on the ship: wakes the player, asks the name, talks about the storm, warns of the guard, repeats his warning | engine/aga/src/aw_intro.c AW_IntroTick, the jiub_state steps | AmiWind adaptation | 0 | not yet | - |
| CharGenRaceNPC | the dock guard: walks to the plank, greets the player, the race window, leads him to the office door, repeats | engine/aga/src/aw_opening.c AW_OpeningTick, the aw_story.dock steps | AmiWind adaptation | 0 | not yet | INTRO-DOCK-GUARD-BLOCKS-DOOR-62 |
| CharGenWalkNPC | the ship's guard: comes to the player, the movement hint, leads him to the deck hatch, repeats his order | engine/aga/src/aw_intro.c AW_IntroTick, the guard_state steps | AmiWind adaptation | 0 | not yet | OPENING-SHIP-GUARD-STEPS-63 |
| Main | the script the game always runs: it rolls the global Random100 every frame and starts the new game's scripts | engine/aga/src/aw_mwvm.c AW_MwvmNewGame | AmiWind's own code, steps open | 1 | not yet | - |

Functions whose work AmiWind's own code does (the script calls into it):

| Functions | What | AmiWind counterpart | Parity | Note | In game |
| --- | --- | --- | --- | --- | --- |
| AIFollow, AIFollowCell, AIEscort, AIEscortCell | an actor follows or escorts a target; the packages' rules (the hours, the place, the end that GetAIPackageDone reads) in aw_ambient.c | engine/aga/src/aw_companion.c AW_FollowThink (the debug companion's follow think, aw_follow.h; the movement of the packages since v0.0.63) | same | one implementation since ESCORT-FOLLOW-63; the packages never place a follower near its target inside a cell, which is OpenMW's own rule (the follower catches up through doors with the player, aw_ambient.c) | not yet |
| StartCombat, StopCombat, GetTarget | an actor fights the player or another actor; the fight ends; whom it fights | engine/aga/src/aw_combat.c AW_CombatEngage, AW_CombatEngageAgainst (a slot's target: the player or another actor), AW_CombatTargetOf; through aw_mwhost.c host_combat | same | fights between two actors since COMBAT-ACTOR-VS-ACTOR-62; allies (followers and escorts, both ways) and guards (against creatures in a fight) join on sight (aw_mwhost.c join_fights, OpenMW actors.cpp engageCombat); the player's own followers and escorts help the player against whoever fights him and never start a fight with the player by their Fight value; OpenMW's optional setting for followers attacking on sight (off by default) is not carried | not yet |

The original game's console commands (docs/CONSOLE_COMMANDS_MORROWIND.md): 502 in all; 22 run AmiWind's own command, 428 run through the script interpreter's host, 3 are AmiWind's own names (kept), 36 planned, 13 not applicable. The aliases:

| Original | AmiWind | Parity | Note |
| --- | --- | --- | --- |
| ToggleGodMode, tgm | dbg god | same | no damage of any kind |
| ToggleCollision, tcl | noclip (AmiWind's own tcl) | same | walk through walls and fly |
| CenterOnCell, coc | dbg tp | partial | the cell name goes to dbg tp, which knows the towns and the map names; an original interior cell name tp does not know gives tp's own list |
| CenterOnExterior, coe | dbg tp X Y | same | the exterior cell's centre in the original's coordinates (8192 a cell) |
| FixMe | dbg unstuck | partial | OpenMW moves the player a short way; unstuck takes the nearest clear standing spot |
| ToggleMenus, tm | dbg killhud | partial | the HUD hidden; killhud also frees the camera (photo mode) |
| ToggleVanityMode, tvm | dbg vanitycam on | same | the idle orbit now |
| SetLevel | dbg setlvl | same | the player's level, as the game's SetLevel |
| AddItem, RemoveItem, GetItemCount | aw_mwhost.c host_item | same | on any reference by id-> or the console target (dbg mw target), found as a script's own reference; an item no actor carries and no script names: the player's inventory by its id (dbg give's own call) |
| AddSpell, RemoveSpell | aw_mwhost.c host_spell | same | on any actor |
| Enable, Disable, GetDisabled | aw_mwhost.c host_object | same | on any reference |
| Position, SetPos, GetPos, SetAngle, GetAngle | aw_mwhost.c host_call, host_position | same | as a script line moves or turns the reference |
| AIWander, AITravel, AIFollow, AIEscort | aw_mwhost.c host_wander, host_call | same | the ambient tables' packages, as from a script |
| Equip | the inventory's equip (aw_inventory.c AW_InventoryEquip) | partial | the player only; an actor's equipment from a console line: not yet |
| PositionCell | dbg tp | partial | the player to the cell by its name; the point in the cell and another reference: not yet |
| EnableNameMenu, EnableRaceMenu, EnableClassMenu, EnableBirthMenu, EnableStatReviewMenu | dbg quickchar name / dbg characterchange race / dbg quickchar class, birthsign, review | same | the character creation pages |
| Set/Mod/Get<attribute, skill, Health, Magicka, Fatigue>, ModCurrent<Health, Magicka, Fatigue> | aw_mwhost.c host_actor | same | the MWScript host's actor call that a compiled script line makes; on the player |
| ToggleDebugText, tdt | dbg hud | partial | AmiWind's debug HUD (position, target identity) instead of the original's debug text lines |
| ToggleStats, tst | dbg fps | partial | the frame rate counter; the original also lists render counts |
| ToggleCombatStats, tcs | aw_combat_readout toggled | same | the combat rolls printed on the console |
| ToggleLights, tl | r_fullbright toggled | partial | the lighting off and on as the engine draws it |
| RepairedOnMe | echo 0 | same | OpenMW 0.51 reads it as always 0 |
| Journal | aw_mwscript_status call journal | same | the host route a script's Journal takes: the dated entry, a lower index ignored |
| SetJournalIndex | aw_mwscript_status call setjournalindex | same | the index alone, as a script's SetJournalIndex |
| GetJournalIndex | aw_mwscript_status call getjournalindex | same | the index the scripts read, printed |
| GetPCExpelled | aw_mwscript_status call pcexpelled | same | PCExpelled through the host route, printed |

### CharGen

| Step | Original | AmiWind | Same? |
| --- | --- | --- | --- |
| controls | DisablePlayerControls, -Jumping, -ViewSwitch, VanityMode, -Fighting, -Magic | the same six switches off at the new game's start, from the script's own calls (the compiler's NGCS row, aw_mwhost.c new_game_controls; v0.0.66; before it every switch read on from the start), beside the opening's own restriction (AW_StoryRestricted, AW_IntroUse); the later scripts switch them on as in the original (the clerk, the papers, the hall guard, the courtyard barrel, the exit door) | same |
| the ship | PositionCell into Imperial Prison Ship at 61, -135, 24, facing 340 | the new game starts on the ship map at its arrival | same |
| weather | ChangeWeather Bitter Coast Region 1 (cloudy) | set cloudy at a new game from the script's own call (the compiler's NGWE row, aw_mwhost.c new_game_weather; v0.0.63) | same |
| CharGenState | set to 10 | set to 10 (fixed in v0.0.63; every reader of the game tests -1, not -1 or 0 and over) | same |

### CharGenBoatNPC

| Step | Original | AmiWind | Same? |
| --- | --- | --- | --- |
| first | the player within 180, no line playing: CharGenBoat1 | within 45 map units (180 original), no line playing: chargenboat1 | same |
| repeat | every 6 s near: CharGenBoat2 | every 6 s near: chargenboat2 | same |
| the use key | the script reads OnActivate and does nothing with it: the player cannot talk to him | a person with a part in the opening is not offered for talk (aw_talk.c AW_TalkFacts) | same |

### CharGenBoatWomen

| Step | Original | AmiWind | Same? |
| --- | --- | --- | --- |
| first | the player within 180, no line playing: CharGenWoman1 | within 45 map units, after the hatch is open: chargenwoman1 | same |
| repeat | every 6 s near, the last line done: CharGenWoman2 | the same; its timer advances only while the player is near and no line plays (fixed in v0.0.63) | same |
| the use key | the script reads OnActivate and does nothing with it: the player cannot talk to her | a person with a part in the opening is not offered for talk (aw_talk.c AW_TalkFacts) | same |

### CharGenDisable

| Step | Original | AmiWind | Same? |
| --- | --- | --- | --- |
| every frame | CharGenState below 0: Disable, on each of its 23 placed references | the blockers clip the player while CharGenState is 0 or over and stop after (the same rule); all 23 are converted: the 22 outdoor ones and, since v0.0.63, the one inside the prison ship (reference 481585, intro/barriers-ship.awb) | same |

### CharGenNameNPC

| Step | Original | AmiWind | Same? |
| --- | --- | --- | --- |
| 0 | after 1 s: CharGenName1 | after 1 s: chargenname1 | same |
| 10 | line done: EnableNameMenu | line done: the name window | same |
| 20 | 1 s after the window: CharGenName2 | 1 s after the name: chargenname2 | same |
| 40 | line done and the second guard within 400: CharGenName3 | the second guard within 100 map units (400 original): chargenname3 | same |
| -1 | every 14 s the player stays within 150: CharGenName4 | the same; its timer advances only while the player is near (fixed in v0.0.63) | same |
| the use key | the script reads OnActivate and does nothing with it: the player cannot talk to him | a person with a part in the opening is not offered for talk (aw_talk.c AW_TalkFacts) | same |

### CharGenRaceNPC

| Step | Original | AmiWind | Same? |
| --- | --- | --- | --- |
| 0-10 | AITravel to the plank; the player within 108 | the route to the plank; the player within 27 map units (108 original) | same |
| 20-30 | controls off, CharGenDock1; line done: EnableRaceMenu | the player held (and the controls switch off, v0.0.66), chargendock1; line done: the race window | same |
| 40 | 1.5 s after the window: CharGenDock2 | 1.5 s after the race is accepted: chargendock2 | same |
| 50 | line done: controls on, AITravel next to the door (-9944, -72481) | line done: the player free (the switch on, v0.0.66), the route to the script's own point next to the door, standing as the walk leaves him (v0.0.63). Measured in the dock map's units against the shipped door table: his box x 322.68..337.32, y -207.37..-193.13; the office door's box x 308.86..332.61, y -173.38..-149.62; no overlap, 19.75 units between them, wider than the player's box (14.64), so the player can pass between him and the door (INTRO-DOCK-GUARD-BLOCKS-DOOR-62 not brought back) | same |
| -1 | every 6 s near: CharGenDock3 | every 6 s near: chargendock3 | same |
| the use key | the script reads OnActivate and does nothing with it: the player cannot talk to him | a person with a part in the opening is not offered for talk (aw_talk.c AW_TalkFacts) | same |

### CharGenWalkNPC

| Step | Original | AmiWind | Same? |
| --- | --- | --- | --- |
| 0-10 | after 8 s: AITravel 90, -90, -88 | after 8 s: the route to 90, -90, -88 | same |
| 20 | arrived: CharGenWalk1 | arrived: chargenwalk1 (the wait for Jiub's warning removed in v0.0.63) | same |
| 30 | line done: a message box with the movement keys and Ok | line done: the script's text with AmiWind's keys, closed with Enter (Ok) (v0.0.63) | same |
| 40-57 | EnablePlayerControls, AIEscort to 195, 100, 170, then AITravel 185, 174, 170 | the controls free (the switch on, v0.0.66), the route to 195, 100, 170, then to 185, 174, 170 | same |
| 60 | the player within 200: CharGenWalk2 | within 50 map units (200 original): chargenwalk2 | same |
| -1 | every 6 s the player stays within 150: CharGenWalk3 | the same; its timer advances only while the player is near (fixed in v0.0.63) | same |
| the use key | the script reads OnActivate and does nothing with it: the player cannot talk to him | a person with a part in the opening is not offered for talk (aw_talk.c AW_TalkFacts) | same |

### Main

| Step | Original | AmiWind | Same? |
| --- | --- | --- | --- |
| every frame | outside the menus: Random100 set to a roll of 0 to 100 | not done: a script that reads the global Random100 reads 0 (the dialogue rolls its own Random100 for each line it picks, aw_glut.c) | different |
| a new game | CharGenState 1: StartScript Startup and VampireCheck | both started once when a new game begins (the compiler's list of them, AW_MwvmNewGame) | same |
| character creation | StartScript CharGen unless it runs already | CharGen is an AmiWind adaptation (its own entry) | same |

## Follows OpenMW's fix

Where OpenMW 0.51 deliberately differs from the original engine in what a script does, AmiWind follows OpenMW, not the original's bug. Each fix names the original's behaviour and OpenMW's, taken from OpenMW's own source notes; Scripts and Dialogue count the script records and dialogue results whose calls hit it, and the rows of those scripts name it in their own column.

| Fix | Original | OpenMW 0.51 | AmiWind | Scripts | Dialogue |
| --- | --- | --- | --- | ---: | ---: |
| dagoth-ur-remote-change | The endgame scripts change dagoth_ur_1's health, magicka or fatigue from afar, after he is gone. | Such a change on dagoth_ur_1 through an explicit reference that finds no loaded actor is ignored, as a workaround for those broken scripts (apps/openmw/mwscript/statsextensions.cpp OpModDynamic). | follows: a change on dagoth_ur_1 with no entity is ignored (engine/aga/src/aw_mwhost.c) | 1 | 0 |
| showmap-empty-name | ShowMap with an empty name errors out or ends the game. | ShowMap with an empty name stops the script with an error (apps/openmw/mwscript/guiextensions.cpp OpShowMap). | safe, not the same: nothing is revealed and the script goes on (engine/aga/src/aw_mwhost.c) | 0 | 0 |
| dontsaveobject-ignored | DontSaveObject keeps its object out of the saved game. | DontSaveObject does nothing, a deliberate and marginal difference (apps/openmw/mwscript/miscextensions.cpp OpDontSaveObject). | follows: compiled to no code (tools/mwscript/codegen.py) | 25 | 0 |
| repairedonme-zero | RepairedOnMe does not work. | RepairedOnMe always reads 0, deliberately (apps/openmw/mwscript/miscextensions.cpp OpRepairedOnMe). | not in the compiler's table: no script of the three masters calls it | 0 | 0 |

## By area

The area of a script is where most of its placed references stand: the region for the exteriors, the region its doors lead out to for an interior. Scripts with no placed reference are grouped by what starts them.

| Area | Scripts | Runs | Adaptation | Own code, steps open | Function missing | Attached, not run | Not attached | Add-on world | Named by nothing | Not converted |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| mournhold (tribunal) | 194 | 194 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| named by nothing | 123 | 0 | 0 | 1 | 0 | 0 | 0 | 0 | 122 | 0 |
| ascadian isles region | 115 | 115 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| hirstaang forest region | 103 | 103 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| dialogue only | 82 | 82 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| azura's coast region | 73 | 73 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| records not placed | 69 | 58 | 0 | 0 | 0 | 0 | 0 | 0 | 11 | 0 |
| ashlands region | 66 | 66 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| west gash region | 65 | 65 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| isinfier plains region | 48 | 48 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| felsaad coast region | 45 | 45 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| bitter coast region | 41 | 35 | 6 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| molag mar region | 37 | 37 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| global scripts | 33 | 32 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| red mountain region | 22 | 22 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| thirsk region | 20 | 20 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| moesring mountains region | 17 | 17 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| solstheim (bloodmoon) | 16 | 16 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| grazelands region | 14 | 14 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| sheogorad | 13 | 13 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| brodir grove region | 7 | 7 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| interior with no way out | 4 | 4 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| **All** | **1207** | **1066** | **7** | **1** | **0** | **0** | **0** | **0** | **133** | **0** |

## By function

Every function the game's scripts call. Scripts: the script records that call it; In conditions: of those, the ones whose if or while tests read it; Missing in: the scripts where the call is not carried out; Only gap: the scripts it alone keeps from running whole; Dialogue: the result scripts that call it, and of those the ones where the call is not carried out. Carried out "host" means the engine carries the call out through the import route; "in part" means some of its calls are carried out (the player's PositionCell to a known room, a Cast of a cure) and the others are not. Effect in play: whether what the engine does for the call is the original's effect, in full, in part or none (the list under the table says what is missing).

| Function | Group | Carried out | Effect in play | Scripts | Uses | In conditions | Missing in | Only gap | Dialogue | Dialogue missing |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| cast | spells | host, in part | in part | 53 | 126 | 0 | 1 | 1 | 5 | 0 |
| getjournalindex | journal | yes | full | 547 | 1371 | 535 | 0 | 0 | 0 | 0 |
| disable | world | yes | full | 390 | 832 | 0 | 0 | 0 | 52 | 0 |
| journal | journal | yes | full | 378 | 610 | 0 | 0 | 0 | 3091 | 0 |
| enable | world | yes | full | 299 | 500 | 0 | 0 | 0 | 111 | 0 |
| menumode | core | yes | full | 289 | 297 | 289 | 0 | 0 | 0 | 0 |
| onactivate | world | yes | full | 258 | 280 | 257 | 0 | 0 | 0 | 0 |
| getdisabled | world | yes | full | 225 | 434 | 225 | 0 | 0 | 0 | 0 |
| ondeath | combat | yes | full | 221 | 245 | 216 | 0 | 0 | 0 | 0 |
| cellchanged | core | yes | in part | 201 | 208 | 201 | 0 | 0 | 0 | 0 |
| getdistance | core | yes | full | 194 | 301 | 183 | 0 | 0 | 0 | 0 |
| messagebox | ui | yes | full | 172 | 413 | 0 | 0 | 0 | 11 | 0 |
| getsecondspassed | core | yes | full | 169 | 237 | 0 | 0 | 0 | 0 | 0 |
| stopscript | core | yes | full | 124 | 143 | 0 | 0 | 0 | 2 | 0 |
| getitemcount | inventory | yes | full | 120 | 241 | 118 | 0 | 0 | 0 | 0 |
| activate | world | yes | full | 118 | 146 | 0 | 0 | 0 | 0 | 0 |
| startcombat | combat | yes | full | 106 | 205 | 0 | 0 | 0 | 138 | 0 |
| getdeadcount | stats | yes | full | 105 | 247 | 102 | 0 | 0 | 0 | 0 |
| forcegreeting | dialogue | host | full | 98 | 134 | 0 | 0 | 0 | 25 | 0 |
| removeitem | inventory | yes | full | 81 | 239 | 0 | 0 | 0 | 782 | 0 |
| say | audio | yes | full | 79 | 182 | 0 | 0 | 0 | 0 | 0 |
| additem | inventory | yes | in part | 77 | 157 | 0 | 0 | 0 | 1135 | 0 |
| getpccell | cell | yes | full | 77 | 139 | 77 | 0 | 0 | 0 | 0 |
| aiwander | ai | yes | in part | 73 | 130 | 0 | 0 | 0 | 101 | 0 |
| setfight | ai | yes | full | 73 | 234 | 0 | 0 | 0 | 173 | 0 |
| gethealth | stats | yes | full | 69 | 94 | 63 | 0 | 0 | 0 | 0 |
| playsound | audio | yes | full | 62 | 108 | 0 | 0 | 0 | 3 | 0 |
| positioncell | position | host | in part | 57 | 96 | 0 | 0 | 0 | 14 | 0 |
| addspell | spells | yes | in part | 52 | 175 | 0 | 0 | 0 | 50 | 0 |
| getbuttonpressed | ui | yes | full | 48 | 76 | 1 | 0 | 0 | 0 | 0 |
| getcurrentaipackage | ai | yes | in part | 48 | 51 | 48 | 0 | 0 | 0 | 0 |
| getsoundplaying | audio | yes | in part | 40 | 48 | 40 | 0 | 0 | 0 | 0 |
| stopcombat | combat | yes | in part | 40 | 119 | 0 | 0 | 0 | 8 | 0 |
| playloopsound3dvp | audio | yes | in part | 39 | 41 | 0 | 0 | 0 | 0 | 0 |
| getcommondisease | spells | yes | full | 37 | 37 | 37 | 0 | 0 | 0 | 0 |
| getpos | position | yes | in part | 37 | 127 | 2 | 0 | 0 | 0 | 0 |
| getaipackagedone | ai | yes | full | 35 | 99 | 35 | 0 | 0 | 0 | 0 |
| sethealth | stats | yes | full | 33 | 56 | 0 | 0 | 0 | 3 | 0 |
| sethello | ai | yes | none | 30 | 75 | 0 | 0 | 0 | 5 | 0 |
| playgroup | anim | host | in part | 29 | 84 | 0 | 0 | 0 | 0 | 0 |
| getblightdisease | spells | yes | full | 28 | 67 | 28 | 0 | 0 | 0 | 0 |
| startscript | core | yes | in part | 28 | 51 | 0 | 0 | 0 | 140 | 0 |
| getpcrank | stats | host | full | 26 | 43 | 23 | 0 | 0 | 0 | 0 |
| dontsaveobject | world | yes | full | 25 | 25 | 0 | 0 | 0 | 0 | 0 |
| aitravel | ai | host | full | 24 | 89 | 0 | 0 | 0 | 5 | 0 |
| placeitem | position | host | in part | 24 | 37 | 0 | 0 | 0 | 0 | 0 |
| saydone | audio | yes | full | 24 | 79 | 24 | 0 | 0 | 0 | 0 |
| getpccrimelevel | stats | host | full | 23 | 45 | 0 | 0 | 0 | 2 | 0 |
| random | core | yes | full | 22 | 27 | 2 | 0 | 0 | 0 | 0 |
| geteffect | spells | host | in part | 21 | 32 | 21 | 0 | 0 | 0 | 0 |
| rotate | position | host | in part | 21 | 51 | 0 | 0 | 0 | 0 | 0 |
| addtopic | dialogue | host | full | 20 | 105 | 0 | 0 | 0 | 86 | 0 |
| becomewerewolf | stats | host | in part | 18 | 22 | 0 | 0 | 0 | 0 | 0 |
| getspell | spells | yes | full | 18 | 52 | 17 | 0 | 0 | 0 | 0 |
| lock | world | yes | full | 18 | 18 | 0 | 0 | 0 | 1 | 0 |
| aifollow | ai | host | full | 17 | 21 | 0 | 0 | 0 | 85 | 0 |
| removespell | spells | yes | full | 17 | 82 | 0 | 0 | 0 | 8 | 0 |
| unlock | world | yes | full | 17 | 17 | 0 | 0 | 0 | 0 | 0 |
| modhealth | stats | yes | full | 16 | 27 | 0 | 0 | 0 | 0 | 0 |
| setdisposition | dialogue | yes | full | 16 | 38 | 0 | 0 | 0 | 65 | 0 |
| disableplayercontrols | control | host | full | 15 | 19 | 0 | 0 | 0 | 0 | 0 |
| getangle | position | host | in part | 15 | 17 | 0 | 0 | 0 | 0 | 0 |
| gettarget | ai | host | full | 15 | 36 | 15 | 0 | 0 | 0 | 0 |
| placeatpc | position | host | in part | 15 | 30 | 0 | 0 | 0 | 7 | 0 |
| enableplayercontrols | control | host | full | 14 | 20 | 0 | 0 | 0 | 0 | 0 |
| iswerewolf | stats | host | full | 14 | 23 | 14 | 0 | 0 | 0 | 0 |
| playsound3d | audio | yes | full | 14 | 15 | 0 | 0 | 0 | 0 | 0 |
| position | position | host | in part | 14 | 23 | 0 | 0 | 0 | 0 | 0 |
| getstandingpc | world | host | in part | 13 | 13 | 12 | 0 | 0 | 0 | 0 |
| modreputation | dialogue | host | in part | 12 | 15 | 0 | 0 | 0 | 175 | 0 |
| getpcsleep | stats | host | full | 11 | 13 | 11 | 0 | 0 | 0 | 0 |
| getdetected | ai | host | in part | 10 | 13 | 10 | 0 | 0 | 0 | 0 |
| playbink | ui | host | full | 10 | 50 | 0 | 0 | 0 | 0 | 0 |
| resurrect | stats | host | in part | 10 | 16 | 0 | 0 | 0 | 0 | 0 |
| setdelete | world | host | full | 10 | 10 | 0 | 0 | 0 | 0 | 0 |
| xbox | core | yes | full | 10 | 13 | 10 | 0 | 0 | 0 | 0 |
| getwaterlevel | cell | host | full | 9 | 10 | 4 | 0 | 0 | 0 | 0 |
| modcurrenthealth | stats | yes | full | 9 | 12 | 0 | 0 | 0 | 0 | 0 |
| moddisposition | dialogue | yes | full | 9 | 10 | 0 | 0 | 0 | 1219 | 0 |
| setpos | position | host | in part | 8 | 12 | 0 | 0 | 0 | 0 | 0 |
| wakeuppc | stats | host | full | 8 | 23 | 0 | 0 | 0 | 0 | 0 |
| fadein | ui | host | full | 7 | 10 | 0 | 0 | 0 | 0 | 0 |
| fadeout | ui | host | full | 7 | 10 | 0 | 0 | 0 | 0 | 0 |
| modrestoration | stats | yes | full | 7 | 7 | 0 | 0 | 0 | 0 | 0 |
| setangle | position | host | in part | 7 | 16 | 0 | 0 | 0 | 0 | 0 |
| modfatigue | stats | yes | in part | 6 | 9 | 0 | 0 | 0 | 0 | 0 |
| modresistfire | spells | host | full | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| modresistfrost | spells | host | full | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| modresistmagicka | spells | host | full | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| modresistparalysis | spells | host | full | 6 | 12 | 0 | 0 | 0 | 0 | 0 |
| modresistpoison | spells | host | full | 6 | 12 | 0 | 0 | 0 | 0 | 0 |
| setatstart | position | host | full | 6 | 6 | 0 | 0 | 0 | 0 | 0 |
| setscale | position | host | in part | 6 | 12 | 0 | 0 | 0 | 0 | 0 |
| stopsound | audio | yes | in part | 6 | 9 | 0 | 0 | 0 | 0 | 0 |
| changeweather | sky | host | full | 5 | 12 | 0 | 0 | 0 | 0 | 0 |
| enableplayerfighting | control | host | full | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| enableplayermagic | control | host | full | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| explodespell | spells | host | in part | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| getattacked | combat | host | in part | 5 | 5 | 5 | 0 | 0 | 0 | 0 |
| getfatigue | stats | yes | full | 5 | 8 | 2 | 0 | 0 | 0 | 0 |
| loopgroup | anim | host | in part | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| move | position | host | in part | 5 | 5 | 0 | 0 | 0 | 0 | 0 |
| moveworld | position | host | in part | 5 | 7 | 0 | 0 | 0 | 0 | 0 |
| onknockout | combat | host | full | 5 | 5 | 5 | 0 | 0 | 0 | 0 |
| onmurder | combat | host | full | 5 | 5 | 5 | 0 | 0 | 0 | 0 |
| pcraiserank | stats | host | full | 5 | 9 | 0 | 0 | 0 | 55 | 0 |
| playloopsound3d | audio | yes | in part | 5 | 7 | 0 | 0 | 0 | 0 | 0 |
| setfatigue | stats | yes | in part | 5 | 6 | 0 | 0 | 0 | 1 | 0 |
| setflee | ai | yes | in part | 5 | 10 | 0 | 0 | 0 | 0 | 0 |
| undowerewolf | stats | host | in part | 5 | 7 | 0 | 0 | 0 | 0 | 0 |
| aiescort | ai | host | full | 4 | 5 | 0 | 0 | 0 | 0 | 0 |
| clearforcesneak | control | host | in part | 4 | 19 | 0 | 0 | 0 | 4 | 0 |
| enableteleporting | control | host | none | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| forcesneak | control | host | in part | 4 | 12 | 0 | 0 | 0 | 0 | 0 |
| getlocked | world | yes | full | 4 | 4 | 4 | 0 | 0 | 0 | 0 |
| hassoulgem | inventory | host | full | 4 | 85 | 4 | 0 | 0 | 0 | 0 |
| modregion | sky | host | full | 4 | 12 | 0 | 0 | 0 | 0 | 0 |
| modspeed | stats | yes | in part | 4 | 7 | 0 | 0 | 0 | 0 | 0 |
| modstrength | stats | yes | in part | 4 | 7 | 0 | 0 | 0 | 2 | 0 |
| playsound3dvp | audio | yes | in part | 4 | 6 | 0 | 0 | 0 | 0 | 0 |
| setalarm | ai | yes | full | 4 | 7 | 0 | 0 | 0 | 2 | 0 |
| showrestmenu | ui | host | full | 4 | 4 | 0 | 0 | 0 | 0 | 0 |
| disableteleporting | control | host | none | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| drop | inventory | host | full | 3 | 6 | 0 | 0 | 0 | 0 | 0 |
| enableinventorymenu | ui | host | full | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| enablemagicmenu | ui | host | full | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| enablemapmenu | ui | host | full | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| enablestatsmenu | ui | host | full | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| getlevel | stats | yes | full | 3 | 10 | 3 | 0 | 0 | 0 | 0 |
| getrace | stats | host | full | 3 | 22 | 3 | 0 | 0 | 0 | 0 |
| getspelleffects | spells | host | in part | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| getweapondrawn | combat | host | full | 3 | 5 | 3 | 0 | 0 | 0 | 0 |
| getwerewolfkills | stats | host | full | 3 | 3 | 3 | 0 | 0 | 0 | 0 |
| hurtcollidingactor | combat | host | in part | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| modwillpower | stats | yes | in part | 3 | 5 | 0 | 0 | 0 | 0 | 0 |
| setmagicka | stats | yes | full | 3 | 4 | 0 | 0 | 0 | 0 | 0 |
| setmarksman | stats | yes | in part | 3 | 4 | 0 | 0 | 0 | 0 | 0 |
| setwaterlevel | world | host | full | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| setwerewolfacrobatics | stats | host | full | 3 | 3 | 0 | 0 | 0 | 0 | 0 |
| disablelevitation | control | host | none | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| enablelevitation | control | host | none | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| getcollidingpc | world | host | in part | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| getinterior | cell | host | in part | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| getlos | ai | host | full | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| getpcinjail | stats | host | full | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| getpcsneaking | control | host | full | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| getpctraveling | stats | host | none | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| getsecurity | stats | yes | full | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| getsneak | stats | yes | full | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| getstrength | stats | yes | full | 2 | 2 | 1 | 0 | 0 | 0 | 0 |
| hasitemequipped | inventory | host | full | 2 | 2 | 2 | 0 | 0 | 0 | 0 |
| hitonme | combat | host | in part | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| hurtstandingactor | combat | host | in part | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| modagility | stats | yes | in part | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| modblock | stats | yes | in part | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| modcurrentfatigue | stats | yes | in part | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| modendurance | stats | yes | in part | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| modmagicka | stats | yes | full | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| modmediumarmor | stats | yes | in part | 2 | 3 | 0 | 0 | 0 | 0 | 0 |
| modpcfacrep | stats | host | full | 2 | 3 | 0 | 0 | 0 | 482 | 0 |
| placeatme | position | host | in part | 2 | 6 | 0 | 0 | 0 | 0 | 0 |
| removesoulgem | inventory | host | full | 2 | 42 | 0 | 0 | 0 | 0 | 0 |
| setagility | stats | yes | in part | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| setathletics | stats | yes | in part | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| setblock | stats | yes | in part | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| setlongblade | stats | yes | in part | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| setpccrimelevel | stats | host | in part | 2 | 3 | 0 | 0 | 0 | 34 | 0 |
| setrestoration | stats | yes | full | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| setspeed | stats | yes | in part | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| setstrength | stats | yes | in part | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| setwillpower | stats | yes | in part | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| showmap | ui | host | full | 2 | 7 | 0 | 0 | 0 | 249 | 0 |
| disableplayerfighting | control | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| disableplayerjumping | control | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| disableplayermagic | control | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| disableplayerviewswitch | control | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| disablevanitymode | control | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| enablebirthmenu | ui | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| enableclassmenu | ui | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| enablenamemenu | ui | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| enableplayerjumping | control | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| enableplayerviewswitch | control | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| enableracemenu | ui | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| enablerest | ui | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| enablestatreviewmenu | ui | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| enablevanitymode | control | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| face | ai | host | in part | 1 | 6 | 0 | 0 | 0 | 0 | 0 |
| fall | position | yes | full | 1 | 3 | 0 | 0 | 0 | 0 | 0 |
| forcerun | control | host | in part | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| getagility | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| getchameleon | spells | host | full | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| getcollidingactor | world | host | in part | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| getcurrentweather | sky | host | full | 1 | 4 | 1 | 0 | 0 | 0 | 0 |
| getdisposition | dialogue | yes | in part | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| getendurance | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| getflee | ai | yes | full | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| getintelligence | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| getluck | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| getmagicka | stats | yes | full | 1 | 2 | 1 | 0 | 0 | 0 | 0 |
| getmarksman | stats | yes | full | 1 | 2 | 1 | 0 | 0 | 0 | 0 |
| getparalysis | spells | host | full | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| getpersonality | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| getspeed | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| getsquareroot | core | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| getstandingactor | world | host | in part | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| getstat | stats | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| getweapontype | combat | host | in part | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| getwillpower | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| gotojail | stats | host | full | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| modarmorer | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| modathletics | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| modaxe | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| modbluntweapon | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| modfactionreaction | dialogue | host | full | 1 | 2 | 0 | 0 | 0 | 6 | 0 |
| modfight | ai | yes | full | 1 | 1 | 0 | 0 | 0 | 83 | 0 |
| modheavyarmor | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| modintelligence | stats | yes | in part | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| modlongblade | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| modluck | stats | yes | full | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| modmarksman | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| modmercantile | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 8 | 0 |
| modpersonality | stats | yes | full | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| modshortblade | stats | yes | in part | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| modspear | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| modwaterlevel | world | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| payfine | stats | host | in part | 1 | 1 | 0 | 0 | 0 | 3 | 0 |
| pcclearexpelled | stats | host | full | 1 | 1 | 0 | 0 | 0 | 23 | 0 |
| pcexpelled | stats | host | full | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| pcjoinfaction | stats | host | full | 1 | 1 | 0 | 0 | 0 | 13 | 0 |
| placeitemcell | position | host | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| playsoundvp | audio | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| raiserank | stats | host | full | 1 | 1 | 0 | 0 | 0 | 1 | 0 |
| rotateworld | position | host | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| scriptrunning | core | yes | full | 1 | 1 | 1 | 0 | 0 | 0 | 0 |
| setalchemy | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setalteration | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setarmorer | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setaxe | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setbluntweapon | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setconjuration | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setdestruction | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setenchant | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setendurance | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setheavyarmor | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setillusion | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setmediumarmor | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setmysticism | stats | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| setspear | stats | yes | in part | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| streammusic | audio | yes | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| turnmoonred | sky | host | full | 1 | 2 | 0 | 0 | 0 | 0 | 0 |
| turnmoonwhite | sky | host | full | 1 | 1 | 0 | 0 | 0 | 0 | 0 |
| aifollowcell | ai | host | full | 0 | 0 | 0 | 0 | 0 | 19 | 0 |
| choice | dialogue | host | full | 0 | 0 | 0 | 0 | 0 | 1103 | 0 |
| clearinfoactor | dialogue | host | full | 0 | 0 | 0 | 0 | 0 | 31 | 0 |
| goodbye | dialogue | host | full | 0 | 0 | 0 | 0 | 0 | 1012 | 0 |
| modflee | ai | yes | in part | 0 | 0 | 0 | 0 | 0 | 3 | 0 |
| payfinethief | stats | host | full | 0 | 0 | 0 | 0 | 0 | 10 | 0 |
| pcexpell | stats | host | in part | 0 | 0 | 0 | 0 | 0 | 11 | 0 |
| setmercantile | stats | yes | full | 0 | 0 | 0 | 0 | 0 | 1 | 0 |

245 functions of the compiler's table are called by no script of the game.

### Effect in play

Carried out says that a call is executed; Effect in play says whether what the engine then does is what the original game does. Of the 259 functions the game's scripts call, 161 have the original's effect in full, 92 in part and 6 have none yet (the call is accepted and nothing of its effect happens). How each class is known: 251 read from the source against the original's rules, 6 kept by a test, 2 checked in play. A class read from the source is not yet proven in play. Seen in play: what of a function's effect a play session has shown, with its build and date; 4 functions have such a note, and a note covers only what it says, not the whole function. The rows were last checked against the source and the register for AmiWind v0.0.69-dev6 (27 November 2026).

| Function | Effect | Scripts | Dialogue | What is missing | Known from | Seen in play | Register |
| --- | --- | ---: | ---: | --- | --- | --- | --- |
| cellchanged | in part | 201 | 0 | A global script sees it only when another map loads, and an object's script when its object is attached or comes into range; walking from one outdoor cell into the next within the same map does not set it. | source | not yet | MWSCRIPT-CELLCHANGED-OUTDOOR-STEP-68, MWSCRIPT-CELLCHANGED-VOLATILE-54 |
| additem | in part | 77 | 1135 | A person given an item does not put it on when it is better than what it wears, as people do in the original; the count itself is right for the player, people, creatures and containers. | source | not yet | MWSCRIPT-ADDITEM-NO-EQUIP-68 |
| aiwander | in part | 73 | 101 | A wander a script gives is not kept in a saved game: after loading, the actor goes back to the wander of its game data. The wander's area is taken around where the actor was placed, not around where it stands when the call comes, and an actor that is not loaded when the call comes takes no wander. | source | not yet | MWSCRIPT-AIWANDER-NOT-SAVED-68 |
| positioncell | in part | 57 | 14 | An NPC or creature sent outdoors appears at its new place only while its own home area is loaded. An object that is no person or creature moves only within the place the player is in, not to another place, and one drawn without its own entity does not move at all. A player move into a room the image lacks does nothing. | source | not yet | MWSCRIPT-POSITIONCELL-OUTDOOR-62, MWSCRIPT-ROTATE-NO-ENTITY-59, MWSCRIPT-POSITIONCELL-NPC-62 |
| cast | in part | 53 | 5 | A spell cast at the player lands only when every effect is a stat change, a cure or a plain effect; then all of its effects land on him, also those meant for the caster, and its fire, frost, shock and poison damage lands with no resistance. A Target spell lands at once with no bolt flying. Cast by the player himself does nothing, where the original makes it his selected spell. | source | not yet | MWSCRIPT-CAST-PARTIAL-68 |
| addspell | in part | 52 | 50 | The spell joins the actor's list and can be cast, and resistances, water breathing and similar effects of an ability count where they are read, but the attribute, skill, health, magicka and fatigue effects of an ability, disease or curse added this way (a disease's drain, vampirism's gains) are never applied to the stats. | source | not yet | MWSCRIPT-ABILITY-EFFECTS-NOT-APPLIED-68 |
| getcurrentaipackage | in part | 48 | 0 | After a travel, a follow or an escort has ended, the actor goes on reading 1 (travel) and its package stays done; the original goes on to the package under it (its own wander reads 0), or reads -1 when none is left. | source | not yet | MWSCRIPT-AIWANDER-NOT-SAVED-68 |
| stopcombat | in part | 40 | 8 | Only the actor's own fight ends: an actor it was fighting, and that actor's allies, go on fighting it. | source | not yet | MWSCRIPT-STOPCOMBAT-OTHER-SIDE-68, MWSCRIPT-STOPCOMBAT-UNWIRED-62 |
| getsoundplaying | in part | 40 | 0 | It asks only about sounds the same script started: a sound another script or the game started on that object reads as not playing, and an object named before the call is not looked at. | source | not yet | MWSCRIPT-SOUND-OWN-SCRIPT-ONLY-68 |
| playloopsound3dvp | in part | 39 | 0 | The pitch argument is not used (the mixer has no pitch); the volume is. A loop started on another object starts again at the script's own object once its first sample ends. | source | not yet | MWSCRIPT-SOUND-OWN-SCRIPT-ONLY-68 |
| getpos | in part | 37 | 0 | An object named by its id reads 0 on every axis when it is drawn as scenery without its own entity and is no scripted mover, or when it is in another place than the player's, where the original reads where it stands there. | source | not yet | MWSCRIPT-ROTATE-NO-ENTITY-59 |
| sethello | none | 30 | 5 | The value is kept and read back by GetHello (a value over 255 as 255), but nothing uses it: the distance at which a person greets the player stays the one from its game data. | source | not yet | MWSCRIPT-ACTOR-SETTINGS-NOT-USED-68, ACTOR-HELLO-CLAMPED-61 |
| playgroup | in part | 29 | 0 | A person or creature with a converted skeleton plays the group, but its start-mode argument is not read. An animated object in a room (a door, a lever) is not seen moving: when the group's time has passed it shows the group's last pose and keeps it, also in a saved game. An object outside the rooms and the player play nothing. | source | not yet | MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68, MWSCRIPT-PLAYGROUP-FRAME-OBJECTS-68 |
| startscript | in part | 28 | 140 | A global script started from an object's script or from a conversation does not take that object or speaker as its own, so its calls that name no object act on nothing. | source | not yet | MWSCRIPT-STARTSCRIPT-NO-TARGET-68 |
| placeitem | in part | 24 | 0 | An object no map converted is made and runs its script but is not drawn; an activator, static or container the world draws as scenery is not made. Past the copies the build plans, a copy's script does not run, and a full map leaves it out. | source | not yet | MWSCRIPT-PLACE-OTHER-KINDS-62, MWVM-PLACE-COPIES-FOUR-66 |
| geteffect | in part | 21 | 0 | Only the player is asked: on any NPC or creature it reads 0. An effect of an ability, disease or curse the player has (not cast) reads 0. | source | not yet | MWSCRIPT-ABILITY-EFFECTS-NOT-APPLIED-68, GETEFFECT-TABLE-84-OF-143-68 |
| rotate | in part | 21 | 0 | Scenery without its own entity that is no scripted mover does not turn. Rotate on the player changes nothing he sees (his view is not turned). A turned object with its own entity that is no person or creature that is no person or creature is back at its angle when its map loads again or a game is loaded. | source | not yet | MWSCRIPT-ROTATE-NO-ENTITY-59, WORLD-OBJECT-STATE-NOT-SAVED-59 |
| becomewerewolf | in part | 18 | 0 | Not handled: the doubled health; the witnesses of the change, the known-werewolf state and its bounty; people attacking a werewolf on sight and guards leaving him alone; the refusal to take, open, loot, read or use things and to sleep, with the game's message and sounds (the inventory and magic windows, spell casting and talk are refused); skills not improving in the form; carried weight not counting, and the run bonus applying only with the claws put away; the camera height, view angle, screen border and hand icon of the form; silver weapons doing double damage to a werewolf; the werewolf's own swing, hit, readying and running sounds; the werewolf name over a turned NPC, and attacks on a turned NPC not being a crime. Carried in source and not yet seen in play: the stats' values, the run bonus, and the form kept in a saved game. | source | the player's werewolf body and claws are drawn in first and third person at his race's size, his gear comes off, the inventory and magic windows stay shut and the use key talks to nobody (v0.0.68-dev8, 23 November 2026); an NPC a script turns is drawn as the werewolf, holds nothing, fights with its claws only and cannot be talked to (v0.0.68-dev8, 23 November 2026) | WEREWOLF-BODY-NOT-DRAWN-63, WEREWOLF-RUN-SPEED-63, WEREWOLF-TRANSFORM-RULES-PARTIAL-68, NPC-WEREWOLF-NO-MODEL-66, WEREWOLF-FIGHT-RULES-LEFT-68 |
| placeatpc | in part | 15 | 7 | An object no map converted is made but not drawn, and an activator, static or container the world draws as scenery is not made. Past the script-made copies the build plans for one map (four of each record), a further copy appears but its script does not run, and a full map leaves a made object out. | source | not yet | MWVM-PLACE-COPIES-FOUR-66, MWSCRIPT-PLACE-OTHER-KINDS-62 |
| getangle | in part | 15 | 0 | On the player the angle about z reads 90 degrees off the view. A scripted object drawn as part of the scenery without its own entity reads 0 instead of its angle, also one that SetAngle or Rotate has turned, and so does an object in another place than the player's; a script that turns such an object from its own reading goes wrong. | source | not yet | GETANGLE-PLAYER-Z-READS-OBJECT-AXIS-67, MWSCRIPT-ROTATE-NO-ENTITY-59 |
| position | in part | 14 | 0 | The rotation argument is not applied to anyone. The player is always moved to the outdoor point, also when he is inside a room (the original moves him within that room). Another object moves only within the map it is in now, and a moved object that is no person or creature goes back when its map loads again. Scenery drawn without its own entity is not moved. | source | not yet | WORLD-OBJECT-STATE-NOT-SAVED-59, MWSCRIPT-POSITION-ROOM-ROTATION-68, MWSCRIPT-ROTATE-NO-ENTITY-59 |
| getstandingpc | in part | 13 | 0 | Only an object with its own entity is asked; scenery without one (pressure plates and platforms drawn with the world) reads 0. | source | not yet | MWSCRIPT-ROTATE-NO-ENTITY-59 |
| modreputation | in part | 12 | 175 | Only the player's reputation changes: on a person (the speaker of a conversation, or the script's own object when no one is named) nothing happens. | source | not yet | MWSCRIPT-REPUTATION-DISPOSITION-PARTIAL-68 |
| getdetected | in part | 10 | 0 | When the observer is not a person (a creature or an object), only people nearby are asked whether they notice the actor; creatures nearby, the observer itself included, are not. | source | not yet | MWSCRIPT-SMALL-DIFFERENCES-68 |
| resurrect | in part | 10 | 0 | Only an NPC or creature loaded in the player's map is brought back; one elsewhere, or the player, is not. A living one is reset to its game data too, where the original leaves it alone. In a room the one brought back does not stand up where it fell: it is gone until the room is entered again, then stands where the game data puts it. | source | not yet | MWSCRIPT-RESURRECT-LOADED-ONLY-68 |
| setpos | in part | 8 | 0 | A changed place of an object with its own entity that is no person or creature that is no person or creature is not kept when its map loads again or a game is loaded. Scenery without an entity that is no scripted mover does not move. | source | not yet | MWSCRIPT-ROTATE-NO-ENTITY-59, WORLD-OBJECT-STATE-NOT-SAVED-59, SETPOS-MOVER-NO-ENTITY-68 |
| setangle | in part | 7 | 0 | On the player the angle about z is set 90 degrees off from the original's. Scenery drawn without its own entity turns only when its script reacts to its use or another script names it. A changed angle of an object that is no person or creature is not kept when its map loads again or a game is loaded. | source | not yet | GETANGLE-PLAYER-Z-READS-OBJECT-AXIS-67, WORLD-OBJECT-STATE-NOT-SAVED-59, MWSCRIPT-ROTATE-NO-ENTITY-59 |
| modfatigue | in part | 6 | 0 | An NPC or creature whose fatigue falls below zero this way falls unconscious only if it is fighting. While the player fights, a change of his fatigue is lost. | source | not yet | MWSCRIPT-FATIGUE-KNOCKOUT-FIGHT-ONLY-68 |
| setscale | in part | 6 | 0 | The new size is not kept: a room or area load builds the object at the game data's size again, and a saved game does not hold it. An object without its own entity is not scaled. Collision keeps its size. | source | not yet | WORLD-OBJECT-STATE-NOT-SAVED-59 |
| stopsound | in part | 6 | 0 | It stops only a sound the same script started: a sound another script started on that object goes on, and an object named before the call is not looked at. | source | not yet | MWSCRIPT-SOUND-OWN-SCRIPT-ONLY-68 |
| setfatigue | in part | 5 | 1 | An NPC or creature set below zero fatigue falls unconscious only if it is fighting. While the player fights, the new value is lost. | source | not yet | MWSCRIPT-FATIGUE-KNOCKOUT-FIGHT-ONLY-68 |
| explodespell | in part | 5 | 0 | The Self and Touch effects with an area reach the actors around the object, but the spell's Target effects are not sent off as a bolt. Called on an actor or on the player it explodes at once where they stand, where the original has the actor cast the spell at itself and only makes it the player's selected spell. | source | not yet | MWSCRIPT-CAST-PARTIAL-68 |
| getattacked | in part | 5 | 0 | Only an attack by the player marks the actor; an attack by another person or creature does not, and the mark goes when the fight ends instead of staying until the crime is settled. It is not kept in a saved game. | source | not yet | MWSCRIPT-COMBAT-MARKS-PLAYER-ONLY-68 |
| loopgroup | in part | 5 | 0 | A person or creature with a converted skeleton plays the group, but its start-mode argument is not read. An animated object in a room is not seen moving: once its loops have played it shows the group's last pose and keeps it, also in a saved game. After the ice wall of the Halls of Penumbra breaks, the passage behind it stays blocked. An object outside the rooms and the player play nothing. | source | not yet | MWSCRIPT-PLAYGROUP-ACTORS-ONLY-68, MWSCRIPT-PLAYGROUP-FRAME-OBJECTS-68, PENUMBRA-ICE-WALL-NO-PASSAGE-68 |
| move | in part | 5 | 0 | A scripted object drawn as scenery without its own entity does not move along its own axes (only along the world's axes). A moved object with its own entity that is no person or creature that is no person or creature goes back to its place when its map loads again or a game is loaded. Only the player is carried along when standing on it. | source | not yet | MWSCRIPT-ROTATE-NO-ENTITY-59, WORLD-OBJECT-STATE-NOT-SAVED-59, MWSCRIPT-MOVE-WAITS-FOR-CONSOLE-67 |
| moveworld | in part | 5 | 0 | A moved object that is no person or creature goes back to its place when its map loads again or a game is loaded; only the player is carried along when standing on it. Scenery drawn without its own entity moves only when its script reacts to its use or to the water, or another script names it, and then carries no one standing on it. | source | not yet | WORLD-OBJECT-STATE-NOT-SAVED-59, MWSCRIPT-ROTATE-NO-ENTITY-59 |
| playloopsound3d | in part | 5 | 0 | A loop started on another object (named before the call) starts again at the script's own object once its first sample ends. | source | not yet | MWSCRIPT-SOUND-OWN-SCRIPT-ONLY-68 |
| setflee | in part | 5 | 0 | The new Flee is kept and read back, but a fighting actor still decides whether to flee by the Flee of its game data. | source | not yet | MWSCRIPT-ACTOR-SETTINGS-NOT-USED-68 |
| undowerewolf | in part | 5 | 0 | Not handled: the health going back from the doubled amount, the witnesses of the change back, and damage to the stats being healed on the change back. | source | the player's own body, arms and stats come back, the werewolf robe is taken off and away, the windows open again and the items he wore stay in the inventory, as in the original (v0.0.68-dev8, 23 November 2026); an NPC is drawn with its own body again and fights with its own weapon (v0.0.68-dev8, 23 November 2026) | WEREWOLF-TRANSFORM-RULES-PARTIAL-68, NPC-WEREWOLF-NO-MODEL-66 |
| clearforcesneak | in part | 4 | 4 | On a person or creature the flag counts only for the detection rules: the actor does not take the sneaking stance, animation or speed. | source | not yet | MWSCRIPT-FORCED-STANCE-ACTORS-68 |
| modstrength | in part | 4 | 2 | Maximum fatigue does not follow the new Strength. On an NPC or creature only the load it carries in a fight follows the change; its damage keeps the game data's Strength. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68, MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68 |
| enableteleporting | none | 4 | 0 | The switch is kept and saved, but nothing reads it: the engine has no Mark, Recall or Intervention effects for it to allow again. | source | not yet | MWSCRIPT-TELEPORT-LEVITATE-SWITCHES-UNREAD-68 |
| forcesneak | in part | 4 | 0 | On a person or creature the flag counts only for the detection rules: the actor does not take the sneaking stance, animation or speed. | source | not yet | MWSCRIPT-FORCED-STANCE-ACTORS-68 |
| modspeed | in part | 4 | 0 | On an NPC or creature the change counts for its walking but not in a fight, where it moves at the game data's Speed. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| playsound3dvp | in part | 4 | 0 | The pitch argument is not used (the mixer has no pitch); the volume is. | source | not yet | MWSCRIPT-SOUND-OWN-SCRIPT-ONLY-68 |
| disableteleporting | none | 3 | 0 | The switch is kept and saved, but nothing reads it: the engine has no Mark, Recall or Intervention effects for it to stop. | source | not yet | MWSCRIPT-TELEPORT-LEVITATE-SWITCHES-UNREAD-68 |
| getspelleffects | in part | 3 | 0 | Reads 1 only while effects of the spell that were cast are active; an ability, disease or curse the actor carries (always active in the original) reads 0. | source | not yet | MWSCRIPT-ABILITY-EFFECTS-NOT-APPLIED-68 |
| hurtcollidingactor | in part | 3 | 0 | Only the player touching the object is hurt; people and creatures touching it are not. An object drawn without its own entity hurts no one, and every object the game uses this on is one: the spikes, dicers and tenderizers of the Clockwork City do no harm. | source | not yet | MWSCRIPT-COMBAT-MARKS-PLAYER-ONLY-68, MWSCRIPT-ROTATE-NO-ENTITY-59 |
| modwillpower | in part | 3 | 0 | Maximum fatigue does not follow the new Willpower. On an NPC or creature it counts for its spellcasting and its resistance to spells, not for its fatigue in a fight. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68, MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68 |
| setmarksman | in part | 3 | 0 | On an NPC the change does not reach its fighting with bows and thrown weapons. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| setpccrimelevel | in part | 2 | 34 | The bounty changes and pursuit ends at 0, but a crime level set to 0 does not calm the witnesses as a paid fine does: their alarm and the disposition change stay, and those who attacked the player for the crime go on fighting him. | source | not yet | MWSCRIPT-SMALL-DIFFERENCES-68 |
| disablelevitation | none | 2 | 0 | The switch is kept and saved, but nothing reads it: a Levitate spell still lands and stays on the player, where the original ends it with a message that levitation is not allowed here. The engine has no Levitate movement for the switch to stop: a Levitate effect only spares the player fall damage. | source | not yet | MWSCRIPT-TELEPORT-LEVITATE-SWITCHES-UNREAD-68 |
| enablelevitation | none | 2 | 0 | The switch is kept and saved, but nothing reads it: the engine has no Levitate movement for it to allow again, and a Levitate effect only spares the player fall damage. | source | not yet | MWSCRIPT-TELEPORT-LEVITATE-SWITCHES-UNREAD-68 |
| getcollidingpc | in part | 2 | 0 | Scenery without its own entity reads 0, except the invisible walls built as barrier boxes. | source | not yet | MWSCRIPT-ROTATE-NO-ENTITY-59 |
| getinterior | in part | 2 | 0 | In the Mournhold districts shown as outdoor areas it reads 0, where the original reads 1 (they are interior cells that behave like outdoors). | source | not yet | MWSCRIPT-SMALL-DIFFERENCES-68 |
| getpctraveling | none | 2 | 0 | Always reads 0: the frame right after a paid travel, in which the original reads 1, is never given. | source | not yet | MWSCRIPT-SMALL-DIFFERENCES-68 |
| hitonme | in part | 2 | 0 | Only a blow with the player's weapon is recorded: a blow by another person's or creature's weapon is not, and the player's own HitOnMe always reads 0. | source | not yet | MWSCRIPT-COMBAT-MARKS-PLAYER-ONLY-68 |
| hurtstandingactor | in part | 2 | 0 | Only the player standing on the object is hurt; people and creatures standing on it are not. Scenery drawn without its own entity, which is every placement the game uses this on, hurts no one through this call; the lava hurts the player by the engine's own lava rule instead. | source | not yet | MWSCRIPT-COMBAT-MARKS-PLAYER-ONLY-68, MWSCRIPT-ROTATE-NO-ENTITY-59 |
| modagility | in part | 2 | 0 | Maximum fatigue does not follow the new Agility. On an NPC or creature the change does not reach its fighting (hit chance, evasion and block keep the game data's Agility). | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68, MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68 |
| modblock | in part | 2 | 0 | On an NPC or creature the change does not reach its blocking in a fight, which keeps the game data's skill. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| modcurrentfatigue | in part | 2 | 0 | An NPC or creature whose fatigue a script takes below zero falls unconscious only if it is fighting. While the player fights, a change of his fatigue is lost. | source | not yet | MWSCRIPT-FATIGUE-KNOCKOUT-FIGHT-ONLY-68 |
| modendurance | in part | 2 | 0 | Maximum fatigue does not follow the new Endurance. On an NPC or creature the change does not reach its fighting (fatigue return in a fight keeps the game data's value). | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68, MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68 |
| modmediumarmor | in part | 2 | 0 | On an NPC or creature the change does not reach its armour rating in a fight. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| placeatme | in part | 2 | 0 | An object no map converted (a record placed only by scripts) is made where it should be and runs its script, but it is not drawn. An activator, static or container the world draws as scenery is not made. Past the script-made copies the build plans for one map (four of each record), a further copy appears but its script does not run, and a full map leaves a made object out. | source | not yet | MWVM-PLACE-COPIES-FOUR-66, MWSCRIPT-PLACE-OTHER-KINDS-62 |
| setagility | in part | 2 | 0 | Maximum fatigue does not follow the new Agility. On an NPC the change does not reach its fighting. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68, MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68 |
| setathletics | in part | 2 | 0 | On an NPC the change does not reach its movement in a fight. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| setblock | in part | 2 | 0 | On an NPC the change does not reach its blocking in a fight. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| setlongblade | in part | 2 | 0 | On an NPC the change does not reach its fighting with long blades. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| setspeed | in part | 2 | 0 | On an NPC the change counts for its walking but not in a fight. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| setstrength | in part | 2 | 0 | Maximum fatigue does not follow the new Strength. On an NPC or creature only the load it carries in a fight follows the change; its damage keeps the game data's Strength. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68, MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68 |
| setwillpower | in part | 2 | 0 | Maximum fatigue does not follow the new Willpower. On an NPC it counts for spellcasting and spell resistance, not for its fatigue in a fight. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68, MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68 |
| payfine | in part | 1 | 3 | The bounty goes, stolen goods are taken and the witnesses calm down, but the player's weapon or spell is not put away as in the original. | source | not yet | MWSCRIPT-SMALL-DIFFERENCES-68 |
| modaxe | in part | 1 | 1 | On an NPC or creature the change does not reach its fighting: its axe attacks keep the game data's skill. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| face | in part | 1 | 0 | The actor turns to the point at once instead of turning there at its turning speed. | source | not yet | MWSCRIPT-AIWANDER-NOT-SAVED-68 |
| forcerun | in part | 1 | 0 | A person or creature given it does not run: the flag is kept, saved and read back, but its walks keep their walking speed, on its wander and travel walks as when it follows or escorts. | source | not yet | MWSCRIPT-FORCED-STANCE-ACTORS-68 |
| getcollidingactor | in part | 1 | 0 | Only an object with its own entity is asked; scenery without one reads 0. | source | not yet | MWSCRIPT-ROTATE-NO-ENTITY-59 |
| getdisposition | in part | 1 | 0 | It reads the person's own base disposition, without the race, faction, reputation, personality and temporary changes the original adds, and without the limit to 0 to 100. | source | not yet | MWSCRIPT-REPUTATION-DISPOSITION-PARTIAL-68 |
| getstandingactor | in part | 1 | 0 | Only an object with its own entity is asked; scenery without one reads 0. | source | not yet | MWSCRIPT-ROTATE-NO-ENTITY-59 |
| getweapontype | in part | 1 | 0 | Lockpicks and probes cannot be held yet, and any held item that is not a weapon reads -1 where the original reads -2 for a lockpick and -3 for a probe. A person reads the weapon of its game data rather than the one it holds now. | source | not yet | MWSCRIPT-SMALL-DIFFERENCES-68, INVENTORY-EQUIP-KINDS-NOT-YET-67 |
| modathletics | in part | 1 | 0 | On an NPC or creature the change does not reach its movement in a fight, which keeps the game data's Athletics. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| modbluntweapon | in part | 1 | 0 | On an NPC or creature the change does not reach its fighting with blunt weapons. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| modheavyarmor | in part | 1 | 0 | On an NPC or creature the change does not reach its armour rating in a fight. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| modintelligence | in part | 1 | 0 | Maximum magicka does not follow the new Intelligence (the original recalculates it at once). | source | not yet | MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68 |
| modlongblade | in part | 1 | 0 | On an NPC or creature the change does not reach its fighting with long blades. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| modmarksman | in part | 1 | 0 | On an NPC or creature the change does not reach its fighting with bows and thrown weapons. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| modshortblade | in part | 1 | 0 | On an NPC or creature the change does not reach its fighting with short blades. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| modspear | in part | 1 | 0 | On an NPC or creature the change does not reach its fighting with spears. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| placeitemcell | in part | 1 | 0 | An object no map converted is made but not drawn, and an activator, static or container the world draws as scenery is not made. Past the copies the build plans, a copy's script does not run, and a full map leaves a made object out. | source | not yet | MWSCRIPT-PLACE-OTHER-KINDS-62, MWVM-PLACE-COPIES-FOUR-66 |
| playsoundvp | in part | 1 | 0 | The pitch argument is not used (the mixer has no pitch); the volume is. | source | not yet | MWSCRIPT-SOUND-OWN-SCRIPT-ONLY-68 |
| rotateworld | in part | 1 | 0 | Scenery without its own entity that is no scripted mover does not turn, and a turned object with its own entity that is no person or creature that is no person or creature is back at its angle when its map loads again or a game is loaded. | source | not yet | MWSCRIPT-ROTATE-NO-ENTITY-59, WORLD-OBJECT-STATE-NOT-SAVED-59 |
| setaxe | in part | 1 | 0 | On an NPC the change does not reach its fighting with axes. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| setbluntweapon | in part | 1 | 0 | On an NPC the change does not reach its fighting with blunt weapons. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| setendurance | in part | 1 | 0 | Maximum fatigue does not follow the new Endurance. On an NPC the change does not reach its fighting. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68, MWSCRIPT-DERIVED-MAXIMA-NOT-FOLLOWED-68 |
| setheavyarmor | in part | 1 | 0 | On an NPC the change does not reach its armour rating in a fight. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| setmediumarmor | in part | 1 | 0 | On an NPC the change does not reach its armour rating in a fight. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| setspear | in part | 1 | 0 | On an NPC the change does not reach its fighting with spears. | source | not yet | MWSCRIPT-NPC-STATS-SKIP-FIGHT-68 |
| pcexpell | in part | 0 | 11 | The player is marked expelled, but the message that tells him he was expelled from the faction is not shown. | source | not yet | FACTION-EXPEL-MESSAGE-64, MWSCRIPT-SMALL-DIFFERENCES-68 |
| modflee | in part | 0 | 3 | The changed Flee is kept and read back, but a fighting actor still decides whether to flee by the Flee of its game data. | source | not yet | MWSCRIPT-ACTOR-SETTINGS-NOT-USED-68 |

Functions with the original's effect in full and a note of what was seen in play:

| Function | Seen in play | Known from | Register |
| --- | --- | --- | --- |
| modwaterlevel | the water of the two Old Mournhold rooms rises and falls with their levers (v0.0.68-dev2, 20 November 2026) | play | MWSCRIPT-WATER-LEVEL-STATIC-67 |
| setwaterlevel | the water of the two Old Mournhold rooms rises and falls with their levers (v0.0.68-dev2, 20 November 2026) | play | MWSCRIPT-WATER-LEVEL-STATIC-67 |

## Every script

Referenced by: the records that carry the script and their placed references per master, levelled lists, the start scripts, StartScript in other scripts and in dialogue results. Conditions: the number of if, elseif and while tests and what they read.

### Morrowind

| Script | Area | State | Referenced by | Records | Functions | Conditions | Follows OpenMW's fix | Why |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| ahnassiScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 51 dialogue results | ahnassi | disable, getdisabled, getjournalindex | 3: getdisabled, getjournalindex, global, local | - | - |
| AmayaJournal | ascadian isles region | runs | 1 book; placed 1 (Morrowind 1) | bk_notetoamaya | activate, journal, onactivate | 2: local, onactivate | - | - |
| BarDoor | ascadian isles region | runs | 2 activator; placed 13 (Morrowind 12, Tribunal 1) | active_com_bar_door, active_de_bar_door | getsecondspassed, menumode, onactivate, playsound3d, rotate, setatstart | 10: local, menumode, onactivate | - | - |
| barenAlenScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | baren alen | getitemcount | 1: getitemcount | - | - |
| Bed_Standard | ascadian isles region | runs | 40 activator; placed 1356 (Morrowind 1225, Tribunal 65, Bloodmoon 66) | active_com_bed_01, active_com_bed_02, active_com_bed_03, active_com_bed_04, active_com_bed_05, active_com_bed_06 and 34 more | menumode, onactivate, showrestmenu | 2: menumode, onactivate | - | - |
| beluelleBowl | ascadian isles region | runs | 1 item; placed 1 (Morrowind 1) | misc_beluelle_silver_bowl | activate, addtopic, journal, onactivate | 2: local, onactivate | - | - |
| BILL_GTs_Cursed_Chest | ascadian isles region | runs | 1 container; placed 1 (Morrowind 1) | chest_tomb_sandas | activate, disable, enable, messagebox, onactivate | 2: local, onactivate | - | - |
| BILL_GTs_Skeletal_Guardians | ascadian isles region | runs | 2 creature; placed 2 (Morrowind 2) | skeleton champ_sandas00, skeleton champ_sandas10 | cellchanged, disable, gettarget, menumode, startcombat | 4: cellchanged, gettarget, local, menumode | - | - |
| BILL_MarksDwvGhostSummon | ascadian isles region | runs | 1 item; placed 2 (Morrowind 2) | misc_dwrv_cursed_coin00 | activate, onactivate, placeatpc | 2: local, onactivate | - | - |
| BILL_MT_WritBemis | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1) | mathyn bemis | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| BILL_MT_WritBero | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 17 dialogue results | dram bero | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| BILL_MT_WritGalasa | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | galasa uvayn | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| BILL_MT_WritGuril | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | guril retheran | cellchanged, getjournalindex, getpccrimelevel, gettarget, journal, menumode, ondeath, setfight, startcombat, stopcombat | 16: cellchanged, getjournalindex, gettarget, local, menumode, ondeath | - | - |
| BILL_MT_WritMavon | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | mavon drenim | cellchanged, getjournalindex, getpccrimelevel, gettarget, journal, menumode, ondeath, setfight, startcombat, stopcombat | 23: cellchanged, getjournalindex, gettarget, local, menumode, ondeath | - | - |
| BILL_MT_WritNavil | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | navil ienith | cellchanged, getdeadcount, getjournalindex, getpccrimelevel, journal, menumode, ondeath, placeatpc, say | 10: cellchanged, getdeadcount, getjournalindex, local, menumode, ondeath | - | - |
| BILL_MT_WritOran | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | feruren oran | cellchanged, getjournalindex, getpccrimelevel, gettarget, journal, menumode, ondeath, setfight, startcombat, stopcombat | 22: cellchanged, getjournalindex, gettarget, local, menumode, ondeath | - | - |
| BILL_MT_WritSaren | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | toris saren | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| BILL_MT_WritVendu | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | idroso vendu | cellchanged, getdeadcount, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 7: cellchanged, getdeadcount, getjournalindex, local, menumode, ondeath | - | - |
| BILL_MT_WritVendu2 | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | ethal seloth | cellchanged, getdeadcount, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 7: cellchanged, getdeadcount, getjournalindex, local, menumode, ondeath | - | - |
| BILL_TT_Elvil_Vidron | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 6 dialogue results | elvil vidron | getjournalindex, journal, ondeath | 2: getjournalindex, ondeath | - | - |
| BILL_TT_Tanusea_Veloth | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | tanusea veloth | getjournalindex, journal, menumode, ondeath | 3: getjournalindex, menumode, ondeath | - | - |
| bookPilgrimsPath | ascadian isles region | runs | 1 book; placed 73 (Morrowind 61, Tribunal 6, Bloodmoon 6); levelled lists 1; held by placed containers and actors 1 | bk_pilgrimspath | activate, getjournalindex, journal, onactivate, showmap | 2: getjournalindex, onactivate | - | - |
| brerasScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | brethas deras | cellchanged, disable, getdisabled, getjournalindex, getpccell, journal, ondeath, stopcombat | 6: cellchanged, getdisabled, getjournalindex, getpccell, ondeath | - | - |
| cassiusScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 6 dialogue results | cassius olcinius | forcegreeting, getdistance, getjournalindex, menumode | 13: getdistance, getjournalindex, local, menumode | - | - |
| clientScript | ascadian isles region | runs | 1 book; placed 1 (Morrowind 1) | bk_clientlist | enable, getitemcount, menumode, moddisposition, modfight, startcombat | 3: getitemcount, local, menumode | - | - |
| crassiusScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 44 dialogue results | crassius curio | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| DaedraMephala | ascadian isles region | runs | 2 activator; placed 1 (Morrowind 1) | active_dae_mephala, active_velothi_altar_mephala | additem, disable, enable, getjournalindex, journal, messagebox, onactivate, say, saydone | 4: getjournalindex, local, onactivate, saydone | - | - |
| DaedraSheogorath | ascadian isles region | runs | 1 activator; placed 1 (Morrowind 1) | active_dae_sheogorath | additem, addtopic, enable, getitemcount, getjournalindex, journal, messagebox, onactivate, removeitem, say, saydone | 13: getitemcount, getjournalindex, local, onactivate, saydone | - | - |
| danarScript | ascadian isles region | runs | 1 creature; placed 1 (Morrowind 1) | corprus_stalker_danar | getjournalindex, journal, menumode, ondeath | 3: getjournalindex, menumode, ondeath | - | - |
| dancingGirlScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1) | breton dancer girl | - | 1: local | - | - |
| disableEnnbjof | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | ennbjof | cellchanged, disable, getdisabled, getjournalindex | 3: cellchanged, getdisabled, getjournalindex | - | - |
| doorVassirDidanat | ascadian isles region | runs | 1 door; placed 1 (Morrowind 1) | door_cavern_vassir_un | activate, addtopic, onactivate | 1: onactivate | - | - |
| drarelAndusScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); placed by scripts (1 records) | drarel andus | getdisabled, gethealth, gettarget, startcombat | 3: getdisabled, gethealth, gettarget | - | - |
| dreamer_talkerEnable | ascadian isles region | runs | 12 NPC; placed 12 (Morrowind 12) | dreamer_talker01, dreamer_talker02, dreamer_talker03, dreamer_talker04, dreamer_talker05, dreamer_talker06 and 6 more | enable, getdisabled, getjournalindex | 2: getdisabled, local | - | - |
| drenSlaveOwners | ascadian isles region | runs | 5 NPC; placed 5 (Morrowind 5); speaker of 1 dialogue results | aebondeius jucanis, frinnius posuceius, hrargal the crow, manos othreleth, mavus ules | getdeadcount, getdetected, getdisabled, getjournalindex, getsecondspassed, startcombat | 17: getdeadcount, getdetected, getdisabled, getjournalindex, local, other script | - | - |
| eb_pestScript | ascadian isles region | runs | 1 creature; placed 10 (Morrowind 10) | rat_telvanni_unique | disable, enable, getdisabled, getjournalindex, journal, ondeath | 9: getdisabled, getjournalindex, global, local, ondeath | - | - |
| edras_oril | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 22 dialogue results | edras oril | aifollow, forcegreeting, getdistance, geteffect, getjournalindex, journal, menumode | 20: getdistance, geteffect, getjournalindex, local, menumode | - | - |
| edrynoArethiScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 30 dialogue results | edryno arethi | - | - | - | - |
| enoHlaaluScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 83 dialogue results | eno hlaalu | additem, cellchanged, disable, getdisabled, getjournalindex, getpcrank, modreputation, ondeath, pcraiserank | 32: cellchanged, getdisabled, getjournalindex, local, ondeath | - | - |
| expelledMG | ascadian isles region | runs | 1 clothing; placed 4 (Morrowind 4) | common_ring_01_mge | pcclearexpelled, pcexpelled | 6: global, local, pcexpelled | - | - |
| fraldScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 13 dialogue results | frald the white | - | - | - | - |
| freleneAcquesScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | frelene acques | aiwander, forcegreeting, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, gettarget, journal, menumode, say, sethello, stopcombat | 11: getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, gettarget, global, local, menumode | - | - |
| freleneCellDoor | ascadian isles region | runs | 1 door; placed 1 (Morrowind 1) | in_v_s_jaildoor_frelene | getlocked | 1: getlocked | - | - |
| furiusScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | furius acilius | getjournalindex, journal, ondeath | 3: getjournalindex, ondeath | - | - |
| gadaynScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 11 dialogue results | gadayn andarys | getdistance | 3: getdistance, local | - | - |
| gardingScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | garding | cellchanged, forcegreeting, getdeadcount, gethealth, getjournalindex, getpccell, journal, ondeath, onknockout, positioncell, setfight, stopcombat | 9: cellchanged, getdeadcount, gethealth, getjournalindex, getpccell, local, ondeath, onknockout | - | - |
| hidesFootScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | hides_his_foot | aiwander, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getpos, getsecondspassed, journal, menumode, say, saydone, sethello | 14: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode, saydone | - | - |
| hlaaluPrisonGuard | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1) | ordinator wander_hp | getdetected, getjournalindex, getsecondspassed, startcombat, stopcombat | 6: getdetected, getjournalindex, local | - | - |
| HuleeyaFollow | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 9 dialogue results | huleeya | aiwander, forcegreeting, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getpccell, getsecondspassed, journal, menumode, moddisposition, modreputation, say, sethello | 10: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getpccell, global, local, menumode | - | - |
| jeannechestScript | ascadian isles region | runs | 1 container; placed 1 (Morrowind 1) | com_chest_02_jeanne_u | activate, forcegreeting, getdetected, getdistance, getjournalindex, journal | 6: getdetected, getdistance, getjournalindex, local | - | - |
| jeannedoorScript | ascadian isles region | runs | 1 door; placed 1 (Morrowind 1) | in_velothismall_ndoor_01_jeanne | activate, forcegreeting, getdetected, getjournalindex, journal, onactivate | 8: getdetected, getjournalindex, local, onactivate | - | - |
| jobashaScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | jobasha | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| kwamaQueenShurdan | ascadian isles region | runs | 2 creature; placed 1 (Morrowind 1) | kwama queen_shurdan, kwama queen_shurdan_c | getblightdisease, getjournalindex, journal | 3: getblightdisease, getjournalindex | - | - |
| kwamaShurdan1 | ascadian isles region | runs | 1 creature; placed 3 (Morrowind 3) | kwama warrior shurdan | cellchanged, disable, enable, getjournalindex | 2: cellchanged, getjournalindex | - | - |
| landDeedChest | ascadian isles region | runs | 1 container; placed 1 (Morrowind 1) | chest_small_02_hhrd | getitemcount | 3: getitemcount, other script | - | - |
| LegionUniform | ascadian isles region | runs | 5 armour; placed 13 (Morrowind 10, Tribunal 1, Bloodmoon 2); levelled lists 3; held by placed containers and actors 202 | imperial cuirass_armor, imperial_chain_cuirass, lords_cuirass_unique, silver_dukesguard_cuirass, templar_cuirass | - | 3: local | - | - |
| llovynAndusScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | llovyn andus | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| lorbumolScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 19 dialogue results | lorbumol gro-aglakh | forcegreeting, getdistance, getjournalindex, startcombat | 3: getdistance, getjournalindex, local | - | - |
| MehraMiloScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 13 dialogue results | mehra milo | aiwander, getaipackagedone, getcurrentaipackage, getpos, menumode, sethello | 5: getaipackagedone, getcurrentaipackage, getpos, local, menumode | - | - |
| nels_llendoScript | ascadian isles region | runs | 1 activator; placed 1 (Morrowind 1) | active_nels_pelagiad | aiwander, getdeadcount, getjournalindex, getpccell, journal, positioncell | 4: getdeadcount, getjournalindex, getpccell | - | - |
| nevrasa_dralor | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 9 dialogue results | nevrasa dralor | aiwander, forcegreeting, getdistance, getjournalindex, journal, ondeath | 5: getdistance, getjournalindex, ondeath | - | - |
| nolore | ascadian isles region | runs | 217 NPC; placed 191 (Morrowind 143, Tribunal 21, Bloodmoon 27); levelled lists 32; placed by scripts (1 records); speaker of 1128 dialogue results | addhiranirr, aengoth, aeta wave-breaker, afer flaccus, afer flaccus_guard, agrippina herennia and 211 more | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| OrdinatorUniform | ascadian isles region | runs | 6 armour; placed 9 (Morrowind 9); held by placed containers and actors 352 | indoril cuirass, indoril helmet, indoril_almalexia_cuirass, indoril_almalexia_helmet, indoril_mh_guard_cuirass, indoril_mh_guard_helmet | - | 3: local | - | - |
| paur_maston | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | paur maston | aiwander, getcurrentaipackage, getdistance, getjournalindex, getpccell, journal, ondeath | 7: getcurrentaipackage, getdistance, getjournalindex, getpccell, ondeath | - | - |
| prisonerScript | ascadian isles region | runs | 12 NPC; placed 12 (Morrowind 12); speaker of 6 dialogue results | daglin selarar, dro'zharim, eldil bradyn, femer veralor, frizkav brutya, hyna dorn'ke and 6 more | cellchanged, disable | 3: cellchanged, local | - | - |
| Pub_Ebon_Six | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | agning | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Pelagiad_Halfway | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | drelasa ramothran | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Vivec_Black | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | raril giral | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Vivec_Flower | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | sorosi radobar | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Vivec_Lizard | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | manara othan | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| puzzlecanal | ascadian isles region | runs | 1 activator; placed 1 (Morrowind 1) | puzzle canal stairs | disable, enable, fadein, fadeout, gethealth, getsecondspassed, menumode, modcurrenthealth, playsound | 8: gethealth, local, menumode | - | - |
| racistSafe | ascadian isles region | runs | 3 NPC; placed 3 (Morrowind 3); speaker of 10 dialogue results | ethys savil, favel gobor, urven davor | gethealth, getjournalindex, setdisposition, setfight, stopcombat | 3: gethealth, getjournalindex, local | - | - |
| ralenTilvurScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | ralen tilvur | aiwander, getcurrentaipackage, getdeadcount, getpccell, positioncell | 3: getcurrentaipackage, getdeadcount, getpccell | - | - |
| rollie | ascadian isles region | runs | 1 creature; placed 1 (Morrowind 1); speaker of 5 dialogue results | guar_rollie_unique | getjournalindex, journal, ondeath | 4: getjournalindex, local, ondeath | - | - |
| rothisScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | rothis nethan | cellchanged, disable, getdisabled, getflee, gethealth, getitemcount, getjournalindex, getpccell, journal, modhealth, ondeath, removeitem, setflee, stopcombat | 9: cellchanged, getdisabled, getflee, gethealth, getitemcount, getjournalindex, getpccell, ondeath | - | - |
| rovoneArvelScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | rovone arvel | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| sapriusAttack | ascadian isles region | runs | 2 NPC; placed 2 (Morrowind 2) | ordinator wander_ilpe_1, ordinator wander_ilpe_2 | disable, getdisabled, startcombat | 4: getdisabled, local | - | - |
| sapriusScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | saprius entius | aiwander, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, say, sethello | 11: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode | - | - |
| shrineAldSotha | ascadian isles region | runs | 1 activator; placed 1 (Morrowind 1) | active_dae_mehrunes_as | cast, getjournalindex, journal, messagebox, modreputation, onactivate | 4: getjournalindex, onactivate | - | - |
| shrineAralor | ascadian isles region | runs | 1 activator; placed 3 (Morrowind 3) | furn_shrine_aralor_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrineDelyn | ascadian isles region | runs | 1 activator; placed 3 (Morrowind 3) | furn_shrine_delyn_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrineFelms | ascadian isles region | runs | 1 activator; placed 4 (Morrowind 4) | furn_shrine_felms_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrineImperial | ascadian isles region | runs | 1 activator; placed 10 (Morrowind 8, Tribunal 1, Bloodmoon 1) | furn_imp_altar_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrineKummu | ascadian isles region | runs | 1 activator; placed 1 (Morrowind 1) | furn_shrine_vivec_cure_02 | cast, getbuttonpressed, getitemcount, journal, messagebox, onactivate, removeitem | 7: getitemcount, local, onactivate | - | - |
| shrineNerevar | ascadian isles region | runs | 1 activator; placed 5 (Morrowind 5) | furn_shrine_nerevar_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrineOlms | ascadian isles region | runs | 1 activator; placed 3 (Morrowind 3) | furn_shrine_olms_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrinePalace | ascadian isles region | runs | 1 activator; placed 2 (Morrowind 2) | ac_shrine_palace | cast, getbuttonpressed, getitemcount, journal, messagebox, onactivate, removeitem | 7: getitemcount, local, onactivate | - | - |
| shrinePuzzleCanal | ascadian isles region | runs | 1 activator; placed 1 (Morrowind 1) | ac_shrine_puzzlecanal | cast, getjournalindex, journal, messagebox, onactivate | 3: getjournalindex, onactivate | - | - |
| shrinePuzzleCanal_m | ascadian isles region | runs | 1 activator; placed 1 (Morrowind 1) | puzzle canal message | messagebox, onactivate | 1: onactivate | - | - |
| shrineSeryn | ascadian isles region | runs | 1 activator; placed 3 (Morrowind 3) | furn_shrine_seryn_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrineStopMoon | ascadian isles region | runs | 1 activator; placed 1 (Morrowind 1) | ac_shrine_stopmoon | cast, getbuttonpressed, getitemcount, journal, messagebox, onactivate, removeitem | 17: getitemcount, local, onactivate | - | - |
| shrineVivecFury | ascadian isles region | runs | 1 activator; placed 4 (Morrowind 4) | furn_shrine_vivec_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| sirilonweChest | ascadian isles region | runs | 1 container; placed 1 (Morrowind 1) | de_p_chest_02_sirilonwe | getitemcount, menumode | 2: getitemcount, menumode | - | - |
| sjoringScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 8 dialogue results | sjoring hard-heart | getpcrank, ondeath, pcraiserank | 2: getpcrank, ondeath | - | - |
| slaveScript | ascadian isles region | runs | 154 NPC; placed 153 (Morrowind 153); levelled lists 3; speaker of 6 dialogue results | abanji, adharanji, affri, ah-meesei, ahaht, ahdahni and 148 more | aifollow, aiwander, cellchanged, disable, drop, getcurrentaipackage, getitemcount | 9: cellchanged, getcurrentaipackage, getitemcount, local | - | - |
| sleeperScript | ascadian isles region | runs | 14 NPC; placed 14 (Morrowind 14); speaker of 167 dialogue results | alvura othrenim, assi serimilk, daynasa telandas, dralas gilu, dravasa andrethi, endris dilmyn and 8 more | forcegreeting, getdistance, getjournalindex | 9: getdistance, getjournalindex, global, local | - | - |
| Sound_Cave_Drip | ascadian isles region | runs | 1 activator; placed 476 (Morrowind 444, Tribunal 29, Bloodmoon 3) | sound_cave_drip00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Water_Spout | ascadian isles region | runs | 9 activator; placed 403 (Morrowind 329, Tribunal 74) | ex_vivec_waterfall_01, ex_vivec_waterfall_03, ex_vivec_waterfall_05, furn_lavacave_spout00, furn_moldcave_spout00, in_om_waterfall and 3 more | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| staceyScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 45 dialogue results | stacey | additem, cellchanged, disable, getdisabled, getitemcount, getjournalindex, ondeath | 8: cellchanged, getdisabled, getitemcount, getjournalindex, local, ondeath | - | - |
| tarvynFollow | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | tarvyn faren | aiwander, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, say, sethello | 11: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode | - | - |
| templeStewards | ascadian isles region | runs | 6 NPC; placed 6 (Morrowind 6); speaker of 96 dialogue results | endryn llethan, feldrelo sadri, tharer rotheloth, tholer saryoni, tuls valen, uvoo llaren | cellchanged, getjournalindex | 9: cellchanged, getjournalindex, local | - | - |
| tenisiScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | tenisi lladri | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| teris | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 8 dialogue results | teris raledran | aiwander, forcegreeting, getcurrentaipackage, getdistance, getjournalindex, getpccell, journal, menumode, ondeath | 11: getcurrentaipackage, getdistance, getjournalindex, getpccell, local, menumode, ondeath | - | - |
| tulScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 12 dialogue results | tul | aiwander, forcegreeting, getdistance, getjournalindex, journal, ondeath, stopcombat | 7: getdistance, getjournalindex, ondeath | - | - |
| vamppapersScript | ascadian isles region | runs | 1 book; placed 3 (Morrowind 3); held by placed containers and actors 1 | bk_galur_rithari's_papers | activate, journal, onactivate | 2: local, onactivate | - | - |
| varusVantiniusScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 10 dialogue results | varus vatinius | getjournalindex, getpccell, journal, ondeath, pcraiserank | 5: getjournalindex, getpccell, global, local, ondeath | - | - |
| vedamDrenScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 12 dialogue results | vedam dren | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| vivecArenaScript | ascadian isles region | runs | 1 clothing; placed 1 (Morrowind 1) | common_ring_01_arena | cellchanged, getdeadcount, getjournalindex, positioncell, setdisposition, setfight, startcombat | 15: cellchanged, getdeadcount, getjournalindex, global | - | - |
| WaitOneDay | ascadian isles region | runs | 1 creature, 3 NPC; placed 4 (Morrowind 4); speaker of 181 dialogue results | yagrum bagarn, iulus truptor, kaye, synnolian tunifus | - | 1: global, local | - | - |
| yellowBookScript | ascadian isles region | runs | 1 book; placed 6 (Morrowind 6); held by placed containers and actors 1 | bk_yellowbook426 | activate, onactivate, startscript | 3: local, onactivate | - | - |
| ynglingScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 16 dialogue results | yngling half-troll | journal, ondeath | 1: ondeath | - | - |
| anoScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | ano vando | forcegreeting, getdistance, getjournalindex, journal, menumode, ondeath | 19: getdistance, getjournalindex, global, local, menumode, ondeath | - | - |
| assantusScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | assantushansar | getcommondisease, getdisabled, getjournalindex, journal, say | 3: getcommondisease, getdisabled, getjournalindex | - | - |
| athynSarethiScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 36 dialogue results | athyn sarethi | ondeath, onmurder | 2: ondeath, onmurder | - | - |
| bandenIndarysScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1) | banden indarys | cellchanged, disable, enable, getpcrank | 2: cellchanged, getpcrank | - | - |
| BILL_TT_Anhaedra | ashlands region | runs | 1 creature; placed 1 (Morrowind 1); speaker of 5 dialogue results | dremora_ttmg | cellchanged, getjournalindex, journal, ondeath, setfight, stopcombat | 3: cellchanged, getjournalindex, ondeath | - | - |
| bolvynScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 10 dialogue results | bolvyn venim | getjournalindex, getpccell, journal, messagebox, ondeath, onmurder, pcraiserank | 9: getjournalindex, getpccell, local, ondeath, onmurder | - | - |
| broderGarilScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1) | broder garil | cellchanged, disable, enable | 3: cellchanged, global, local | - | - |
| codusScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | codus callonus | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| deadSarethiGuard | ashlands region | runs | 2 NPC; placed 2 (Morrowind 2) | redoran guard sarethi1, redoran guard sarethi2 | disable, enable, getdisabled, getjournalindex | 5: getdisabled, getjournalindex | - | - |
| devalFollow | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | deval beleth | aiwander, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, say, sethello | 11: getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode | - | - |
| disableWulf | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | wulf | cellchanged, disable, getdisabled, getjournalindex | 4: cellchanged, getdisabled, getjournalindex | - | - |
| drerel_indaren | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | drerel indaren | addtopic, forcegreeting, getcurrentaipackage, getdistance, getjournalindex, journal, ondeath | 7: getcurrentaipackage, getdistance, getjournalindex, local, ondeath | - | - |
| edwinnaScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 41 dialogue results | edwinna elbert | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| enableNotice | ashlands region | runs | 1 book; placed 9 (Morrowind 9); held by placed containers and actors 1 | bk_nerevarinenotice | disable, enable, getdisabled, getjournalindex | 5: getdisabled, getjournalindex | - | - |
| enableSpiderTGAD | ashlands region | runs | 2 creature; placed 2 (Morrowind 2) | centurion_spider_tga1, centurion_spider_tga2 | cellchanged, disable, enable, getjournalindex | 2: cellchanged, getjournalindex | - | - |
| fonus_rathryon | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 11 dialogue results | fonus rathryon | forcegreeting, getcurrentaipackage, getdistance, getjournalindex, getsecondspassed, journal, ondeath | 8: getcurrentaipackage, getdistance, getjournalindex, local, ondeath | - | - |
| GG_OpenGate1 | ashlands region | runs | 1 activator; placed 2 (Morrowind 2) | ex_gg_gateswitch_01 | getsecondspassed, menumode, moveworld, onactivate, playsound, playsound3dvp, setatstart | 8: global, local, menumode, onactivate | - | - |
| GG_OpenGate2 | ashlands region | runs | 1 activator; placed 2 (Morrowind 2) | ex_gg_gateswitch_02 | getsecondspassed, menumode, moveworld, onactivate, playsound, playsound3dvp, setatstart | 8: global, local, menumode, onactivate | - | - |
| GhostfenceScript | ashlands region | runs | 6 activator; placed 198 (Morrowind 198) | ex_gg_fence_s_01, ex_gg_fence_s_02, ex_gg_fence_s_03, ex_gg_fence_s_04, ex_gg_fence_s_h_01, ex_gg_particles_01 | cellchanged, disable, getdisabled, getjournalindex, getsoundplaying, playloopsound3dvp, stopsound | 4: cellchanged, getdisabled, getjournalindex, getsoundplaying | - | - |
| manisVirmScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | manis virmaulese | disable, enable, forcegreeting, getdisabled, getjournalindex | 5: getdisabled, local | - | - |
| mastriusScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 11 dialogue results | mastrius | addspell, fadein, fadeout, forcegreeting, getfatigue, gethealth, getjournalindex, getsecondspassed, getspell, menumode, messagebox, modagility, modarmorer, modathletics, modaxe, modblock, modbluntweapon, modcurrentfatigue, modcurrenthealth, modendurance, modfatigue, modhealth, modheavyarmor, modlongblade, modmagicka, modmarksman, modmediumarmor, modrestoration, modspear, modspeed, modstrength, modwillpower, setagility, setarmorer, setathletics, setaxe, setblock, setbluntweapon, setendurance, setfatigue, setfight, sethealth, setheavyarmor, setlongblade, setmagicka, setmarksman, setmediumarmor, setrestoration, setspear, setspeed, setstrength, setwillpower | 19: getjournalindex, getspell, local, menumode | - | - |
| mathisFollow | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | mathis dalobar | aiwander, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, say, sethello | 10: getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode | - | - |
| mentanaScript | ashlands region | runs | 1 creature; placed 1 (Morrowind 1) | daedroth_menta_unique | getjournalindex, journal, ondeath | 2: getjournalindex, ondeath | - | - |
| MoonAndStar | ashlands region | runs | 1 clothing; placed 1 (Morrowind 1) | moon_and_star | activate, addtopic, disable, enable, getdistance, getpcrank, journal, menumode, modfactionreaction, modreputation, onactivate, pcjoinfaction, playbink, rotate, startscript | 8: getdistance, getpcrank, local, menumode, onactivate | - | - |
| morvaynCreatures | ashlands region | runs | 2 creature; placed 5 (Morrowind 5) | corprus_lame_morvayn, corprus_stalker_morvayn | addspell, cellchanged, disable, getblightdisease, getjournalindex | 3: cellchanged, getblightdisease, getjournalindex | - | - |
| nemindaScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 35 dialogue results | neminda | cellchanged, gettarget, stopcombat | 2: cellchanged, gettarget | - | - |
| NibaniMaesa | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 52 dialogue results | nibani maesa | journal, ondeath | 2: global, local, ondeath | - | - |
| Pub_Aldruhn_Skar | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | boderi farano | cellchanged | 6: cellchanged, global, local | - | - |
| Pub_Ghost_Dusk | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1) | galore salvi | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Maargan_Andus | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | manse andus | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| redBookScript | ashlands region | runs | 1 book; placed 3 (Morrowind 3) | bk_redbook426 | activate, onactivate, startscript | 3: local, onactivate | - | - |
| RedoranCouncilor | ashlands region | runs | 4 NPC; placed 4 (Morrowind 4); speaker of 54 dialogue results | brara morvayn, garisa llethri, hlaren ramoran, miner arobar | ondeath, onmurder | 2: ondeath, onmurder | - | - |
| regularSarethiGuard | ashlands region | runs | 3 NPC; placed 3 (Morrowind 3) | domesea sarethi, redoran guard sarethi3, redoran guard sarethi4 | cellchanged, disable, enable, getdisabled, getjournalindex | 5: cellchanged, getdisabled, getjournalindex | - | - |
| sanvynScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 12 dialogue results | sanvyn llethri | forcegreeting, gethealth, getjournalindex, gettarget, journal, menumode, ondeath, stopcombat | 11: gethealth, getjournalindex, gettarget, local, menumode, ondeath | - | - |
| Shishi_door | ashlands region | runs | 1 activator; placed 1 (Morrowind 1) | misc_skull00_shishi | getsecondspassed, menumode, move, onactivate, playsound, rotateworld | 7: local, menumode, onactivate | - | - |
| shrineMaarGan | ashlands region | runs | 1 activator; placed 1 (Morrowind 1) | ac_maar_gan_magic_rock | addtopic, cast, getjournalindex, journal, messagebox, onactivate | 2: getjournalindex, onactivate | - | - |
| shrineMeris | ashlands region | runs | 1 activator; placed 4 (Morrowind 4) | furn_shrine_meris_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrineRoris | ashlands region | runs | 1 activator; placed 4 (Morrowind 4) | furn_shrine_roris_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| Sixth_Bell_01 | ashlands region | runs | 1 activator; placed 20 (Morrowind 20) | active_6th_bell_06 | menumode, onactivate, playsound3d | 2: menumode, onactivate | - | - |
| Sixth_Bell_02 | ashlands region | runs | 1 activator; placed 20 (Morrowind 20) | active_6th_bell_05 | menumode, onactivate, playsound3d | 2: menumode, onactivate | - | - |
| Sixth_Bell_03 | ashlands region | runs | 1 activator; placed 20 (Morrowind 20) | active_6th_bell_04 | menumode, onactivate, playsound3d | 2: menumode, onactivate | - | - |
| Sixth_Bell_04 | ashlands region | runs | 1 activator; placed 20 (Morrowind 20) | active_6th_bell_03 | menumode, onactivate, playsound3d | 2: menumode, onactivate | - | - |
| Sixth_Bell_05 | ashlands region | runs | 1 activator; placed 20 (Morrowind 20) | active_6th_bell_02 | menumode, onactivate, playsound3d | 2: menumode, onactivate | - | - |
| Sixth_Bell_06 | ashlands region | runs | 1 activator; placed 20 (Morrowind 20) | active_6th_bell_01 | menumode, onactivate, playsound3d | 2: menumode, onactivate | - | - |
| Sound_Cave_Wind | ashlands region | runs | 1 activator; placed 620 (Morrowind 523, Tribunal 42, Bloodmoon 55) | sound_cave_wind00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Flies | ashlands region | runs | 1 activator, 21 container, 36 NPC; placed 192 (Morrowind 134, Tribunal 6, Bloodmoon 52) | sound_flies00, bm_contain_corpse_01, bm_corpseloot_01, bm_corpseloot_02, contain_corpse10, contain_corpse10_ftr_01 and 52 more | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_mud_bubbles | ashlands region | runs | 1 activator; placed 78 (Morrowind 78) | terrain_ashmire_02 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Spirit_Whisper | ashlands region | runs | 1 activator; placed 311 (Morrowind 301, Tribunal 7, Bloodmoon 3) | sound_spirit_whisper00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Strong1_Complete | ashlands region | runs | 2 door; placed 2 (Morrowind 2) | ex_h_pcfort_exdoor_ 01, ex_r_pcfort_d_01 | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| Strong2 | ashlands region | runs | 18 activator, 1 light; placed 84 (Morrowind 84) | ex_h_pcfort_02, ex_h_pcfort_bt_01, ex_h_pcfort_lp_01-2, ex_h_pcfort_w_01, ex_h_pcfort_w_02, ex_h_pcfort_wc_01 and 13 more | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| strong_foreman | ashlands region | runs | 3 NPC; placed 3 (Morrowind 3); speaker of 5 dialogue results | bugdul gro-kharbush, durbul gro-rush, gashnakh gra-mughol | cellchanged, disable, enable | 8: cellchanged, global | - | - |
| strongholdServices | ashlands region | runs | 21 NPC; placed 21 (Morrowind 21) | arvs raram, avron gols, farena arelas, gaden folvyn, galvene othrobar, garila vedas and 15 more | disable, enable, getdisabled | 4: getdisabled, global, local | - | - |
| strongholdWives | ashlands region | runs | 2 NPC; placed 2 (Morrowind 2); speaker of 6 dialogue results | aryni orethi, fathusa girethi | - | - | - | - |
| sulMatuulNoLore | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 37 dialogue results | sul-matuul | journal, ondeath | 1: ondeath | - | - |
| UrshilakuKill | ashlands region | runs | 14 NPC; placed 14 (Morrowind 14); speaker of 9 dialogue results | ahasour, hainab, kurapli, maeli, ninirrasour, sakiran and 8 more | journal, ondeath | 1: ondeath | - | - |
| varvurSarethiScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | varvur sarethi | additem, aiwander, cellchanged, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, gettarget, journal, menumode, positioncell, say, setfight, sethello, stopcombat | 15: cellchanged, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, gettarget, global, local, menumode | - | - |
| venimGuardScript | ashlands region | runs | 10 NPC; placed 10 (Morrowind 10) | bevadar bels, idros givyn, malsa ules, nathyne uvelas, nidryne redas, novor gorvas and 4 more | getdetected, getjournalindex, getsecondspassed, startcombat | 5: getdetected, getjournalindex, local | - | - |
| viatrix_petilia | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | viatrix petilia | forcegreeting, getcurrentaipackage, getdistance, getjournalindex, getsecondspassed, journal, ondeath, stopscript | 10: getcurrentaipackage, getdistance, getjournalindex, local, ondeath | - | - |
| virasGulsScript | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | viras guls | cellchanged, disable, enable, getdisabled | 7: cellchanged, getdisabled, global, local, other script | - | - |
| Warp_Beran | ashlands region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_beran | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| Warp_Falas | ashlands region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_falas | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| Warp_Roth | ashlands region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_roth | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| Warp_Valen | ashlands region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_valen | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| zabamundNoLore | ashlands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 12 dialogue results | zabamund | journal, ondeath | 1: ondeath | - | - |
| abebaalSlaves | azura's coast region | runs | 5 NPC; placed 5 (Morrowind 5) | ahnarra, dan_ru, dro'zah, j'dato, seen-rei | cellchanged, disable, drop, getitemcount, getjournalindex | 5: cellchanged, getitemcount, getjournalindex | - | - |
| AhemmusaKill | azura's coast region | runs | 15 NPC; placed 15 (Morrowind 15); speaker of 26 dialogue results | addammus, assamma-idan, dutadalk, kammu, kausi, lanabi and 9 more | journal, ondeath | 1: ondeath | - | - |
| araraUvulasScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 13 dialogue results | arara uvulas | cellchanged, disable, getdeadcount | 2: cellchanged, getdeadcount | - | - |
| BILL_FG_Hrelvesuu | azura's coast region | runs | 1 creature; placed 1 (Morrowind 1) | daedroth_fg_nchur | getjournalindex, getlos, journal, menumode, ondeath, startcombat | 7: getjournalindex, getlos, local, menumode, ondeath | - | - |
| BILL_FG_Larienna_Macrina | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | larienna macrina | aiwander, cast, gethealth, getjournalindex, journal, menumode, ondeath, say | 6: gethealth, getjournalindex, local, menumode, ondeath | - | - |
| BILL_FG_Nchurdamz01 | azura's coast region | runs | 2 clothing; placed 1 (Morrowind 1) | common_ring_01_fg_corp01, common_ring_01_fg_nchur01 | getdeadcount, getdistance, getjournalindex, getsecondspassed, menumode, onactivate, say | 7: getdeadcount, getdistance, getjournalindex, local, menumode, onactivate | - | - |
| BILL_FG_Nchurdamz02 | azura's coast region | runs | 1 clothing; placed 1 (Morrowind 1) | common_ring_01_fg_nchur02 | getdeadcount, getdistance, getjournalindex, getsecondspassed, menumode, onactivate, say | 7: getdeadcount, getdistance, getjournalindex, local, menumode, onactivate | - | - |
| BILL_FG_Nchurdamz03 | azura's coast region | runs | 1 clothing; placed 1 (Morrowind 1) | common_ring_01_fg_nchur03 | getdeadcount, getdistance, getjournalindex, getsecondspassed, menumode, onactivate, say | 7: getdeadcount, getdistance, getjournalindex, local, menumode, onactivate | - | - |
| BILL_FG_Nchurdamz_Centurions | azura's coast region | runs | 3 creature; placed 8 (Morrowind 8) | centurion_sphere_nchur, centurion_spider_nchur, centurion_steam_nchur | getdetected, getsecondspassed, menumode, startcombat | 4: getdetected, local, menumode | - | - |
| BILL_MarksDaedraSummon | azura's coast region | runs | 1 armour, 1 container, 6 ingredient, 1 light, 2 item, 3 WEAP; placed 33 (Morrowind 33) | imperial helmet armor_dae_curse, com_chest_daed_cursed, ingred_cursed_daedras_heart_01, ingred_dae_cursed_diamond_01, ingred_dae_cursed_emerald_01, ingred_dae_cursed_pearl_01 and 8 more | activate, onactivate, placeatpc | 2: local, onactivate | - | - |
| BILL_MT_WritTherana | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 19 dialogue results | therana | cellchanged, forcegreeting, getjournalindex, getpccrimelevel, journal, menumode, ondeath, setfight, stopcombat | 7: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| BILL_MT_WritYasalmibaal | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | odaishah yasalmibaal | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| BILL_TT_Lette | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | lette | getcommondisease, getdisabled, getjournalindex, journal, moddisposition, say | 3: getcommondisease, getdisabled, getjournalindex | - | - |
| blockedDoor | azura's coast region | runs | 1 door; placed 1 (Morrowind 1) | ex_dae_door_static | messagebox, onactivate | 1: onactivate | - | - |
| botrirScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 10 dialogue results | botrir | forcegreeting, getcurrentaipackage, getdeadcount, getdistance, getitemcount, getjournalindex, journal, menumode, ondeath, startcombat | 10: getcurrentaipackage, getdeadcount, getdistance, getitemcount, getjournalindex, local, menumode, ondeath | - | - |
| brallionScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 8 dialogue results | brallion | getitemcount, getjournalindex, ondeath, position, positioncell | 7: getitemcount, getjournalindex, local, ondeath | - | - |
| brownBookScript | azura's coast region | runs | 1 book; placed 5 (Morrowind 5) | bk_brownbook426 | activate, onactivate, startscript | 3: local, onactivate | - | - |
| DaedraAzura | azura's coast region | runs | 1 activator; placed 1 (Morrowind 1) | active_dae_azura | additem, cellchanged, enable, getitemcount, getjournalindex, journal, messagebox, onactivate, say, saydone | 16: cellchanged, getitemcount, getjournalindex, local, onactivate, saydone | - | - |
| DaedraMolagBal | azura's coast region | runs | 1 activator; placed 1 (Morrowind 1) | active_dae_molagbal | additem, enable, getjournalindex, journal, messagebox, onactivate, say, saydone | 14: getjournalindex, local, onactivate, saydone | - | - |
| delynaScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | delyna mandas | aiwander, forcegreeting, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, say, sethello | 10: getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode | - | - |
| diseaseBlackHeart | azura's coast region | runs | 5 creature; placed 15 (Morrowind 15); levelled lists 55 | alit_blighted, corprus_lame, nix-hound blighted, rat_blighted, rat_cave_hhte2 | addspell, cellchanged, dontsaveobject, getblightdisease | 2: cellchanged, getblightdisease | dontsaveobject-ignored | - |
| diseaseSwampFever | azura's coast region | runs | 1 creature; placed 6 (Morrowind 6); levelled lists 1 | mudcrab-diseased | addspell, cellchanged, dontsaveobject, getcommondisease | 2: cellchanged, getcommondisease | dontsaveobject-ignored | - |
| draramuScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | draramu hloran | getjournalindex, journal, ondeath | 3: getjournalindex, ondeath | - | - |
| eleedalScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | eleedal_lei | aifollow, cellchanged, disable, drop, getitemcount | 8: cellchanged, getitemcount, local | - | - |
| enarRelethScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | enar releth | cellchanged, disable, getdeadcount | 2: cellchanged, getdeadcount | - | - |
| FaluraScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 23 dialogue results | falura llervu | aiwander, forcegreeting, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getpccell, getsecondspassed, journal, menumode, say, sethello | 10: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getpccell, global, local, menumode | - | - |
| felisaUlessenScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 12 dialogue results | felisa ulessen | cellchanged, disable, getdeadcount | 2: cellchanged, getdeadcount | - | - |
| fightbethes | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 9 dialogue results | bethes sarothril | cellchanged, getdeadcount, getdistance, startcombat | 8: cellchanged, getdeadcount, getdistance, local | - | - |
| fightBovkinna | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | bovkinna | cellchanged, getdeadcount, startcombat | 5: cellchanged, getdeadcount, local | - | - |
| fightBrelda | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1) | brelda quintella | cellchanged, getdeadcount, startcombat | 3: cellchanged, getdeadcount, local | - | - |
| fightClendil | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | clendil | cellchanged, getdeadcount, startcombat | 5: cellchanged, getdeadcount, local | - | - |
| fightDaral | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1) | daral thireloth | cellchanged, getdeadcount, startcombat | 5: cellchanged, getdeadcount, local | - | - |
| fightDomba | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | domba | cellchanged, getdeadcount, startcombat | 5: cellchanged, getdeadcount, local | - | - |
| fightDroresArvel | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 9 dialogue results | drores arvel | getdeadcount, getdistance, startcombat | 6: getdeadcount, getdistance, local | - | - |
| fightEigma | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | eigma | cellchanged, getdeadcount, startcombat | 3: cellchanged, getdeadcount, local | - | - |
| fightEndroni | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1) | endroni dalas | cellchanged, getdeadcount, startcombat | 5: cellchanged, getdeadcount, local | - | - |
| fightFieryra | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | fieryra | aifollow, cellchanged, getdeadcount, getdistance, startcombat | 11: cellchanged, getdeadcount, getdistance, local | - | - |
| fightForepaw | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | fore paw | getdeadcount, getdistance, startcombat | 6: getdeadcount, getdistance, local | - | - |
| fightGnaw_Tooth | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | gnaw tooth | cellchanged, getdeadcount, startcombat | 5: cellchanged, getdeadcount, local | - | - |
| fightKardryn | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | kardryn | cellchanged, getdeadcount, startcombat | 3: cellchanged, getdeadcount, local | - | - |
| fightNals | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1) | nals indrano | cellchanged, getdeadcount, startcombat | 3: cellchanged, getdeadcount, local | - | - |
| fightSalvas | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1) | salvas areleth | cellchanged, getdeadcount, startcombat | 5: cellchanged, getdeadcount, local | - | - |
| fightUresa | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1) | uresa omoril | cellchanged, getdeadcount, startcombat | 5: cellchanged, getdeadcount, local | - | - |
| galosMathendisScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 10 dialogue results | galos mathendis | cellchanged, disable, getdeadcount | 2: cellchanged, getdeadcount | - | - |
| HolamayanCover | azura's coast region | runs | 1 activator; placed 1 (Morrowind 1) | ex_holamayan_cover_01 | getsecondspassed, menumode, playsound, rotate, setatstart | 12: global, local, menumode | - | - |
| llunelaHleranScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 13 dialogue results | llunela hleran | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| mallamRyonScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 12 dialogue results | mallam ryon | cellchanged, disable, getdeadcount | 2: cellchanged, getdeadcount | - | - |
| mirpalFollow | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 36 dialogue results | sinnammu mirpal | aiwander, forcegreeting, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, modreputation, ondeath, say, sethello | 12: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode, ondeath | - | - |
| nartiseArobarScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | nartise arobar | aiwander, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getsecondspassed, journal, menumode, say, sethello | 11: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, global, local, menumode | - | - |
| nartiseGuards | azura's coast region | runs | 3 NPC; placed 3 (Morrowind 3) | drodos galen, galmir, rerynea salas | cellchanged, getdetected, getjournalindex, gettarget, startcombat, stopcombat | 5: cellchanged, getdetected, getjournalindex, gettarget | - | - |
| Pub_SMora_Faras | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | fara | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Smora_Gateway | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | ery | cellchanged | 6: cellchanged, global, local | - | - |
| Pub_TelBran_Sethan | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | llorayna sethan | cellchanged | 6: cellchanged, global, local | - | - |
| Pub_TelMora_Covenant | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | thaeril | cellchanged | 6: cellchanged, global, local | - | - |
| Pub_Vos_Varo | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | burcanius varo | cellchanged | 6: cellchanged, global, local | - | - |
| ravenOmaynScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 19 dialogue results | raven omayn | cellchanged, disable, getdeadcount | 2: cellchanged, getdeadcount | - | - |
| ResurrectHaunt | azura's coast region | runs | 1 clothing; placed 1 (Morrowind 1) | common_ring_01_haunt_ken | cellchanged, gethealth, resurrect | 2: cellchanged, gethealth | - | - |
| satyanaScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 9 dialogue results | satyana | aitravel, aiwander, cellchanged, disable, forcegreeting, getcurrentaipackage, getdistance, getitemcount, getjournalindex, getpos, getsecondspassed, menumode | 15: cellchanged, getcurrentaipackage, getdistance, getitemcount, getjournalindex, local, menumode | - | - |
| savileSlaveTrader | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 35 dialogue results | savile imayn | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| shrineAldDaedroth | azura's coast region | runs | 1 activator; placed 1 (Morrowind 1) | active_dae_sheogorath_ad | cast, getitemcount, getjournalindex, journal, messagebox, modpcfacrep, modreputation, onactivate, removeitem | 6: getitemcount, getjournalindex, onactivate | - | - |
| shrineTemple | azura's coast region | runs | 1 activator; placed 24 (Morrowind 23, Tribunal 1) | furn_shrine_tribunal_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 35: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| skinkScript | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 18 dialogue results | skinkintreesshade | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| Sound_Boat_Hull | azura's coast region | runs | 1 activator, 1 container; placed 33 (Morrowind 33) | sound_boat_hull00, ship hull barrel | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_chimes_wood | azura's coast region | runs | 1 activator; placed 25 (Morrowind 25) | sound_ashl_chimes | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Crystal_Ringing | azura's coast region | runs | 4 activator; placed 139 (Morrowind 139) | act_crystal_01_pulse, act_crystal_02_pulse, in_strong_platform, sound_crystal_chime | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Daedric_Chant | azura's coast region | runs | 1 activator; placed 62 (Morrowind 52, Tribunal 8, Bloodmoon 2) | sound_daedric_chant00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| TelvanniCouncilor | azura's coast region | runs | 3 NPC; placed 3 (Morrowind 3); speaker of 35 dialogue results | dratha, gothren, neloth | ondeath | 1: ondeath | - | - |
| tenyeminweFollow | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | tenyeminwe | aiwander, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getsecondspassed, journal, menumode, say, sethello | 11: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, global, local, menumode | - | - |
| UleniDead | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | uleni heleran | disable, ondeath | 1: ondeath | - | - |
| unemployedMiners | azura's coast region | runs | 2 NPC; placed 2 (Morrowind 2); speaker of 2 dialogue results | ilasour tansumiran, llaals ores | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| vedeleaFollow | azura's coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | vedelea othril | aiwander, getcurrentaipackage, getdistance, gethealth, getjournalindex, getsecondspassed, journal, menumode, say, sethello | 11: getcurrentaipackage, getdistance, gethealth, getjournalindex, global, local, menumode | - | - |
| Warp_Falen | azura's coast region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_falen | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| BILL_MT_WritBrilnosu | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | brilnosu llarys | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| CharGenBed | bitter coast region | runs | 1 activator; placed 1 (Morrowind 1) | chargen_bed | enablerest, menumode, messagebox, onactivate, showrestmenu, xbox | 4: local, menumode, onactivate, xbox | - | - |
| CharGenBoatNPC | bitter coast region | AmiWind adaptation | 1 NPC; placed 1 (Morrowind 1) | chargen boat guard 1 | getdisabled, getdistance, getsecondspassed, menumode, onactivate, say, saydone | 8: getdisabled, getdistance, local, menumode, onactivate, saydone | - | an AmiWind adaptation: engine/aga/src/aw_intro.c AW_IntroTick, the deck_state steps does every step of the script |
| CharGenBoatWomen | bitter coast region | AmiWind adaptation | 1 NPC; placed 1 (Morrowind 1) | chargen boat guard 3 | getdistance, getsecondspassed, menumode, onactivate, say, saydone | 7: getdistance, local, menumode, onactivate, saydone | - | an AmiWind adaptation: engine/aga/src/aw_intro.c AW_IntroTick, the upper_state steps does every step of the script |
| CharGenClassNPC | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | chargen class | activate, disable, disableplayercontrols, enable, enablebirthmenu, enableclassmenu, enableplayercontrols, enableplayerviewswitch, enablestatreviewmenu, enablestatsmenu, enablevanitymode, getdistance, gethealth, getitemcount, getsecondspassed, menumode, messagebox, onactivate, say, saydone, sethello, startscript, xbox | 39: getdistance, gethealth, getitemcount, global, local, menumode, onactivate, other script, saydone, xbox | - | - |
| CharGenCustomsDoor | bitter coast region | runs | 1 door; placed 1 (Morrowind 1) | chargen_shipdoor | getdistance, menumode, messagebox, xbox | 4: getdistance, local, menumode, xbox | - | - |
| CharGenDagger | bitter coast region | runs | 1 WEAP; placed 1 (Morrowind 1) | chargen dagger | activate, messagebox, onactivate, xbox | 9: global, local, onactivate, xbox | - | - |
| CharGenDialogueMessage | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | chargen captain | getdistance, menumode, messagebox, xbox | 4: getdistance, local, menumode, xbox | - | - |
| CharGenDisable | bitter coast region | AmiWind adaptation | 1 activator; placed 23 (Morrowind 23) | chargencollision - extra | disable | 1: global | - | an AmiWind adaptation: engine/aga/src/aw_barrier.c AW_BarrierClip (the blockers converted by tools/prepare_character.py, active while AW_StoryRestricted; since v0.0.68 each one also off once a script's Disable of its reference is in the world change list, the references from id1/world-barriers.txt) does every step of the script |
| CharGenDoorEnterCaptain | bitter coast region | runs | 1 door; placed 1 (Morrowind 1) | chargen door captain | activate, getitemcount, messagebox, onactivate | 3: getitemcount, local, onactivate | - | - |
| CharGenDoorExitCaptain | bitter coast region | runs | 1 door; placed 1 (Morrowind 1) | chargen exit door | activate, enableinventorymenu, enablemagicmenu, enablemapmenu, enableplayerfighting, enableplayermagic, enablestatsmenu, getitemcount, messagebox, onactivate | 3: getitemcount, local, onactivate | - | - |
| CharGenDoorGuardTalker | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1) | chargen door guard | enableplayerfighting, enableplayermagic, getdistance, getitemcount, getsecondspassed, menumode, playsound3d, say, saydone, unlock | 8: getdistance, getitemcount, local, menumode, saydone | - | - |
| CharGenFatigueBarrel | bitter coast region | runs | 1 container; placed 1 (Morrowind 1) | chargen barrel fatigue | enablemapmenu, enableplayerfighting, enableplayerjumping, enableplayermagic, getdistance, menumode, messagebox | 3: getdistance, local, menumode | - | - |
| CharGenJournalMessage | bitter coast region | runs | 1 door; placed 1 (Morrowind 1) | chargendoorjournal | getdistance, menumode, messagebox, xbox | 4: getdistance, local, menumode, xbox | - | - |
| CharGenNameNPC | bitter coast region | AmiWind adaptation | 1 NPC; placed 1 (Morrowind 1) | chargen name | enablenamemenu, getdistance, getsecondspassed, menumode, onactivate, say, saydone | 17: getdistance, local, menumode, onactivate, saydone | - | an AmiWind adaptation: engine/aga/src/aw_intro.c AW_IntroTick, the jiub_state steps does every step of the script |
| CharGenRaceNPC | bitter coast region | AmiWind adaptation | 1 NPC; placed 1 (Morrowind 1) | chargen dock guard | aitravel, aiwander, disableplayercontrols, enableplayercontrols, enableracemenu, getdisabled, getdistance, getsecondspassed, menumode, onactivate, say, saydone | 16: getdisabled, getdistance, local, menumode, onactivate, saydone | - | an AmiWind adaptation: engine/aga/src/aw_opening.c AW_OpeningTick, the aw_story.dock steps does every step of the script |
| CharGenStatsSheet | bitter coast region | runs | 1 book; placed 1 (Morrowind 1) | chargen statssheet | activate, enableinventorymenu, enableplayerfighting, enableplayermagic, menumode, messagebox, onactivate, xbox | 7: local, menumode, onactivate, xbox | - | - |
| CharGenStuffRoom | bitter coast region | runs | 1 activator; placed 1 (Morrowind 1) | chargen stuff room | getitemcount, getstandingpc, menumode, messagebox, xbox | 17: getitemcount, getstandingpc, global, local, menumode, xbox | - | - |
| CharGenWalkNPC | bitter coast region | AmiWind adaptation | 1 NPC; placed 1 (Morrowind 1) | chargen boat guard 2 | aiescort, aitravel, enableplayercontrols, getaipackagedone, getdistance, getsecondspassed, menumode, messagebox, onactivate, say, saydone, xbox | 22: getaipackagedone, getdistance, local, menumode, onactivate, saydone, xbox | - | an AmiWind adaptation: engine/aga/src/aw_intro.c AW_IntroTick, the guard_state steps does every step of the script |
| CorprusOnPC | bitter coast region | runs | 1 creature; placed 1 (Morrowind 1); speaker of 7 dialogue results | dagoth gares | addspell, forcegreeting, getdistance, journal, messagebox, ondeath | 3: getdistance, local, ondeath | - | - |
| DaedraBoethiah | bitter coast region | runs | 2 activator; placed 1 (Morrowind 1) | active_dae_b_bo_head, active_dae_boethiah_ruin | addtopic, getdeadcount, getjournalindex, journal, menumode, onactivate, say, saydone | 10: getdeadcount, getjournalindex, local, menumode, onactivate, saydone | - | - |
| DaedraBoethiah2 | bitter coast region | runs | 2 activator; placed 1 (Morrowind 1) | active_dae_boethiah, ex_dae_boethiah_fixed | additem, getjournalindex, journal, messagebox, onactivate, say, saydone | 7: getjournalindex, local, onactivate, saydone | - | - |
| dandsaScript | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | dandsa | aiwander, forcegreeting, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, say, sethello | 11: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode | - | - |
| duma2script | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | duma gro-lag2 | getdisabled, getjournalindex | 3: getdisabled, getjournalindex | - | - |
| fallingScript | bitter coast region | runs | 1 book; placed 1 (Morrowind 1) | bk_falljournal_unique | disable, enable, fall, getdistance, getsecondspassed, ondeath, say | 8: getdistance, local, ondeath | - | - |
| farvynScript | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | farvyn oreyn | getjournalindex, journal, ondeath | 3: getjournalindex, ondeath | - | - |
| fjolgeirScript | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | fjorgeir | getcurrentaipackage, getdistance, gethealth, getsecondspassed, menumode, say | 7: getcurrentaipackage, getdistance, gethealth, global, local, menumode | - | - |
| lookoutScript | bitter coast region | runs | 1 activator; placed 1 (Morrowind 1) | active_lookout_unique | additem, aitravel, aiwander, clearforcesneak, forcesneak, getaipackagedone, getdistance, getitemcount, getjournalindex, getsecondspassed, removeitem | 41: getaipackagedone, getdistance, getitemcount, getjournalindex, global, local | - | - |
| Netch_breeding | bitter coast region | runs | 2 creature; placed 2 (Morrowind 2) | netch_betty_ilgn, netch_bull_ilgn | menumode, messagebox, ondeath | 2: menumode, ondeath | - | - |
| processusScript | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1) | processus vitellius | activate, addtopic, getjournalindex, journal, onactivate | 2: getjournalindex, onactivate | - | - |
| rabinna_death | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 17 dialogue results | rabinna | additem, aifollow, forcegreeting, getcurrentaipackage, getdistance, getjournalindex, getpccell, journal, ondeath | 9: getcurrentaipackage, getdistance, getjournalindex, getpccell, local, ondeath | - | - |
| raynasaRethanScript | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1) | raynasa rethan | cellchanged, disable, enable, getpcrank | 2: cellchanged, getpcrank | - | - |
| Sound_Boat_Creak | bitter coast region | runs | 1 activator; placed 254 (Morrowind 254) | sound_boat_creak00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Strong1 | bitter coast region | runs | 5 activator, 1 light; placed 6 (Morrowind 6) | ex_h_pcfort_01, ex_h_pcfort_ds_01, ex_h_pcfort_lp_01, ex_h_pcfort_win_01, ex_r_pcfort_01, light_h_pcfort__01 | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| Strong1_Construct | bitter coast region | runs | 15 activator; placed 44 (Morrowind 44) | ex_de_constr_01, ex_de_constr_02, ex_de_constr_03, ex_de_constr_04, ex_de_constr_05, ex_de_constr_06 and 9 more | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| Strong2_Construct | bitter coast region | runs | 23 activator; placed 81 (Morrowind 81) | ex_de_constr_01-2, ex_de_constr_03-2, ex_de_constr_04-2, ex_de_constr_05-2, ex_de_constr_06-2, ex_de_scaffold_01-2 and 17 more | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| Strong3_Construct | bitter coast region | runs | 13 activator; placed 45 (Morrowind 45) | ex_de_constr_01-3, ex_de_constr_02-3, ex_de_constr_03-3, ex_de_constr_05-3, ex_de_constr_06-3, ex_de_scaffold_01-3 and 7 more | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| treestumpScript | bitter coast region | runs | 1 container; placed 1 (Morrowind 1) | flora_treestump_unique | activate, getjournalindex, journal, onactivate | 5: getjournalindex, global, local, onactivate | - | - |
| voduniusScript | bitter coast region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | vodunius nuccius | cellchanged, disable, getdisabled, getjournalindex | 3: cellchanged, getdisabled, getjournalindex | - | - |
| Warp_Andra | bitter coast region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_andra | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| Warp_Maran | bitter coast region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_maran | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| AbebaalAttack | dialogue only | runs | started by 1 dialogue results | - | startcombat, stopscript | - | - | - |
| blueScript | dialogue only | runs | started by 1 dialogue results | - | additem, getitemcount, messagebox, removeitem, stopscript | 2: getitemcount | - | - |
| boneScript | dialogue only | runs | started by 1 dialogue results | - | enable, getitemcount, getjournalindex, journal, ondeath, sethealth | 11: getitemcount, getjournalindex, local, ondeath | - | - |
| CountMonopolyVotes | dialogue only | runs | started by 1 dialogue results | - | getdeadcount, stopscript | 11: getdeadcount, local, other script | - | - |
| CountTelvanniHortator | dialogue only | runs | started by 6 dialogue results | - | getdeadcount, getjournalindex, stopscript | 12: getdeadcount, getjournalindex | - | - |
| CountWizardSpells | dialogue only | runs | started by 2 dialogue results | - | getspell, stopscript | 9: getspell, local | - | - |
| eraldilScript | dialogue only | runs | started by 1 dialogue results | - | aiwander, getdeadcount, getjournalindex, getpccell, positioncell | 8: getdeadcount, getjournalindex, getpccell, global, local | - | - |
| FastEddieAmulet | dialogue only | runs | started by 1 dialogue results | - | getjournalindex, journal, stopscript | 3: getjournalindex, global, local | - | - |
| FastEddieRing | dialogue only | runs | started by 1 dialogue results | - | getjournalindex, journal, stopscript | 3: getjournalindex, global, local | - | - |
| fightStopOrdinators | dialogue only | runs | started by 3 dialogue results | - | getdeadcount, setfight, stopcombat, stopscript | 8: getdeadcount | - | - |
| fightStopWitches | dialogue only | runs | started by 3 dialogue results | - | getdeadcount, setfight, stopcombat, stopscript | 14: getdeadcount | - | - |
| FraldCounter | dialogue only | runs | started by 1 dialogue results | - | stopscript | 3: global, local, other script | - | - |
| glathelScript | dialogue only | runs | started by 1 dialogue results | - | getdeadcount, getjournalindex, getpccell, positioncell | 8: getdeadcount, getjournalindex, getpccell, global, local | - | - |
| HentusTravel | dialogue only | runs | started by 1 dialogue results | - | aitravel, aiwander, getaipackagedone, getangle, getsecondspassed, position, stopscript | 13: getaipackagedone, local | - | - |
| maurrieScript | dialogue only | runs | started by 2 dialogue results | - | disable, stopscript | - | - | - |
| moveAhnassi | dialogue only | runs | started by 1 dialogue results | - | cellchanged, getjournalindex, positioncell, stopscript | 3: cellchanged, getjournalindex | - | - |
| MoveMehra | dialogue only | runs | started by 1 dialogue results | - | cellchanged, getjournalindex, positioncell, stopscript | 2: cellchanged, getjournalindex | - | - |
| moveSarandas | dialogue only | runs | started by 2 dialogue results | - | additem, cellchanged, getjournalindex, positioncell, stopscript | 2: cellchanged, getjournalindex | - | - |
| MoveSinnammu | dialogue only | runs | started by 1 dialogue results | - | cellchanged, getjournalindex, positioncell, stopscript | 2: cellchanged, getjournalindex | - | - |
| PrisonSafe | dialogue only | runs | started by 2 dialogue results | - | getdeadcount, getjournalindex, setdisposition, setfight, stopcombat, stopscript | 5: getdeadcount, getjournalindex | - | - |
| ShishiOdirniranFights | dialogue only | runs | started by 4 dialogue results | - | getpcrank, setfight, stopscript | 1: getpcrank | - | - |
| ShrineBoethiah | dialogue only | runs | started by 1 dialogue results | - | disable, enable, getdeadcount, getpccell, stopscript | 8: getdeadcount, getpccell, global, local | - | - |
| SkinkSoul1 | dialogue only | runs | started by 1 dialogue results | - | hassoulgem, stopscript | 25: hassoulgem | - | - |
| SkinkSoul2 | dialogue only | runs | started by 1 dialogue results | - | hassoulgem, removesoulgem, stopscript | 25: hassoulgem, local | - | - |
| Sleepers | dialogue only | runs | started by 1 dialogue results | - | addtopic, getdeadcount, getjournalindex, getpccell, getpcsleep, journal, messagebox, placeatpc, wakeuppc | 22: getdeadcount, getjournalindex, getpccell, getpcsleep, local | - | - |
| Strong_Build1_H | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build1_R | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build1_T | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build2_H | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build2_R | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build2_T | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build3_H | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build3_R | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build3_T | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build_Start_H | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build_Start_R | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| Strong_Build_Start_T | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, stopscript | 5: getpccell, global, local | - | - |
| StrongholdWifeTeleport | dialogue only | runs | started by 1 dialogue results | - | positioncell, stopscript | 2: other script | - | - |
| StrongSoulCheck | dialogue only | runs | started by 1 dialogue results | - | hassoulgem, stopscript | 19: hassoulgem, local | - | - |
| StrongSoulRemove | dialogue only | runs | started by 1 dialogue results | - | hassoulgem, removesoulgem, stopscript | 36: hassoulgem, local | - | - |
| TeleportTanusea | dialogue only | runs | started by 1 dialogue results | - | getpccell, positioncell, stopscript | 1: getpccell | - | - |
| TG_LootMG | dialogue only | runs | started by 1 dialogue results | - | disable, stopscript | - | - | - |
| TG_LootMG2 | dialogue only | runs | started by 1 dialogue results | - | enable, stopscript | - | - | - |
| TopicsWebspinner | dialogue only | runs | started by 1 dialogue results | - | addtopic, stopscript | - | - | - |
| All_Hortator | global scripts | runs | started by MoonAndStar | - | getjournalindex, journal, stopscript | 3: getjournalindex | - | - |
| All_Nerevarine | global scripts | runs | started by MoonAndStar | - | getjournalindex, journal, stopscript | 4: getjournalindex | - | - |
| CharGen | global scripts | AmiWind adaptation | started by Main | - | changeweather, disableplayercontrols, disableplayerfighting, disableplayerjumping, disableplayermagic, disableplayerviewswitch, disablevanitymode, positioncell, stopscript | - | - | an AmiWind adaptation: engine/aga/src/aw_story.c AW_StoryReset (with aw_intro.c AW_IntroBegin) does every step of the script |
| CouncilorTopicsHlaalu | global scripts | runs | started by yellowBookScript; started by 2 dialogue results | - | addtopic, stopscript | - | - | - |
| CouncilorTopicsRedoran | global scripts | runs | started by redBookScript | - | addtopic, stopscript | - | - | - |
| CouncilorTopicsTelvanni | global scripts | runs | started by brownBookScript | - | addtopic | - | - | - |
| RaceCheck | global scripts | runs | started by CharGenClassNPC | - | getrace, stopscript | 10: getrace | - | - |
| Startup | global scripts | runs | started by Main, VampTest, VampTest1, VampTest2, VampTest3, testPlayerStats | - | disable, stopscript | - | - | - |
| vampdreamScript | global scripts | runs | started by Vampire_Aundae_PC, Vampire_Berne_PC, Vampire_Quarra_PC | - | gethealth, getpcsleep, messagebox, modcurrenthealth, random | 20: getpcsleep, global, local | - | - |
| Vampire_Aundae_PC | global scripts | runs | started by TestMakePCVampire, VampTest1, VampireCheck | - | addspell, removespell, startscript, stopscript | 1: global | - | - |
| Vampire_Berne_PC | global scripts | runs | started by VampTest2, VampireCheck | - | addspell, removespell, startscript, stopscript | 1: global | - | - |
| Vampire_Cure_PC | global scripts | runs | started by VampireMolag | - | removespell, stopscript | 1: global | - | - |
| Vampire_Quarra_PC | global scripts | runs | started by VampTest, VampTest3, VampireCheck | - | addspell, removespell, startscript, stopscript | 1: global | - | - |
| aryonScript | grazelands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 52 dialogue results | aryon | additem, ondeath | 1: ondeath | - | - |
| ashamanuScript | grazelands region | runs | 1 NPC; placed 1 (Morrowind 1) | ashamanu | disable, enable, getdisabled, getdistance, getjournalindex, journal | 11: getdisabled, getdistance, getjournalindex | - | - |
| diseaseAshWoe | grazelands region | runs | 3 creature; placed 6 (Morrowind 6); levelled lists 36; speaker of 7 dialogue results | ash_ghoul, ash_slave, shalk_blighted | addspell, cellchanged, dontsaveobject, getblightdisease | 2: cellchanged, getblightdisease | dontsaveobject-ignored | - |
| kaushadNoLore | grazelands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 23 dialogue results | kaushad | journal, ondeath | 1: ondeath | - | - |
| kwamaQueenMudan | grazelands region | runs | 1 creature; placed 1 (Morrowind 1) | kwama queen_mudan | getblightdisease, getjournalindex, journal | 3: getblightdisease, getjournalindex | - | - |
| molaggrundaScript | grazelands region | runs | 1 creature; placed 1 (Morrowind 1) | winged twilight_grunda_ | getdeadcount, journal, ondeath | 2: getdeadcount, ondeath | - | - |
| nomeggwaiScript | grazelands region | runs | 1 creature; placed 1 (Morrowind 1) | atronach_frost_gwai_uni | getdeadcount, journal, ondeath | 2: getdeadcount, ondeath | - | - |
| sonummuNoLore | grazelands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 11 dialogue results | sonummu zabamat | journal, ondeath | 1: ondeath | - | - |
| teresArothanScript | grazelands region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | teres arothan | aiwander, getcurrentaipackage, getdistance, gethealth, getjournalindex, getsecondspassed, journal, menumode, say, sethello | 10: getcurrentaipackage, getdistance, gethealth, getjournalindex, global, local, menumode | - | - |
| vampcureScript | grazelands region | runs | 1 activator; placed 5 (Morrowind 5) | act_furn_dae_rubble_01b | disable, getjournalindex, stopscript | 1: getjournalindex | - | - |
| Warp_Indo | grazelands region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_indo | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| Warp_Telas | grazelands region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_telas | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| whiteguarScript | grazelands region | runs | 1 creature; placed 1 (Morrowind 1) | guar_white_unique | aiescort, disable, enable, getdisabled, getdistance, getjournalindex, journal | 10: getdisabled, getdistance, getjournalindex, local | - | - |
| ZainabKill | grazelands region | runs | 8 NPC; placed 8 (Morrowind 8); speaker of 10 dialogue results | ababael timsar-dadisun, ashibaal, ashur-dan, minassour, patababi, sakulerib and 2 more | journal, ondeath | 1: ondeath | - | - |
| bittercup | interior with no way out | runs | 1 item; placed 2 (Morrowind 2) | artifact_bittercup_01 | activate, disable, getagility, getbuttonpressed, getendurance, getintelligence, getjournalindex, getluck, getpersonality, getspeed, getstrength, getwillpower, journal, menumode, messagebox, modagility, modendurance, modintelligence, modluck, modpersonality, modspeed, modstrength, modwillpower, onactivate | 40: local, menumode, onactivate | - | - |
| magasScript | interior with no way out | runs | 1 creature; placed 1 (Morrowind 1) | dremora_special_fyr | additem, messagebox, ondeath, positioncell, removeitem | 1: ondeath | - | - |
| SoundTest | interior with no way out | runs | 1 activator; placed 1 (Morrowind 1) | test_sounds | getbuttonpressed, getsoundplaying, messagebox, onactivate, playloopsound3d, playloopsound3dvp, playsound, playsound3d, playsound3dvp, playsoundvp, stopsound | 11: getsoundplaying, local, onactivate | - | - |
| testPlayerStats | interior with no way out | runs | 1 activator; placed 1 (Morrowind 1) | test_stats | additem, addspell, messagebox, onactivate, playsound, setalchemy, setalteration, setathletics, setblock, setconjuration, setdestruction, setenchant, sethealth, setillusion, setlongblade, setmagicka, setmarksman, setmysticism, setrestoration, setspeed, setstrength, startscript | 1: onactivate | - | - |
| Arkn_doors | molag mar region | runs | 1 activator; placed 1 (Morrowind 1) | in_dwrv_crank_arkn | getsecondspassed, menumode, onactivate, playsound, rotate, setangle | 10: local, menumode, onactivate | - | - |
| assabaScript | molag mar region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 12 dialogue results | assaba-bentus | aiwander, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpos, getsecondspassed, journal, menumode, ondeath, say, sethello | 15: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, global, local, menumode, ondeath | - | - |
| atronachMountKand | molag mar region | runs | 3 creature; placed 3 (Morrowind 3); speaker of 11 dialogue results | atronach_flame_ttmk, atronach_frost_ttmk, atronach_storm_ttmk | cellchanged, setfight, stopcombat | 1: cellchanged | - | - |
| BILL_MT_WritSadus | molag mar region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | sarayn sadus | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| Dwemer_box | molag mar region | runs | 1 item; placed 1 (Morrowind 1) | misc_dwrv_ark_cube00 | activate, getjournalindex, journal, onactivate | 3: getjournalindex, local, onactivate | - | - |
| ErabenimsunKill | molag mar region | runs | 7 NPC; placed 7 (Morrowind 7); speaker of 35 dialogue results | addut-lamanu, assemmus, kummu, massarapal, ulibabi, yantus and 1 more | journal, ondeath | 1: ondeath | - | - |
| girasScript | molag mar region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 6 dialogue results | giras indaram | additem, forcegreeting, gethealth, getjournalindex, getsecondspassed, journal, ondeath, onknockout, setfight, sethealth, stopcombat | 8: gethealth, getjournalindex, local, ondeath, onknockout | - | - |
| hanAmmuNoLore | molag mar region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 32 dialogue results | han-ammu | journal, ondeath | 1: ondeath | - | - |
| hgwcScript | molag mar region | runs | 1 book; placed 1 (Morrowind 1) | bk_hanginggardenswasten | activate, addtopic, getdistance, getjournalindex, journal, onactivate | 5: getdistance, getjournalindex, local, onactivate | - | - |
| lava | molag mar region | runs | 6 activator; placed 687 (Morrowind 687) | in_lava_1024, in_lava_1024_01, in_lava_256, in_lava_256a, in_lava_512, in_lava_oval | cellchanged, getsoundplaying, hurtstandingactor, menumode, playloopsound3dvp | 3: cellchanged, getsoundplaying, menumode | - | - |
| maniraiNoLore | molag mar region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 17 dialogue results | manirai | journal, ondeath | 1: ondeath | - | - |
| nchuleftingthWrong1 | molag mar region | runs | 1 activator; placed 1 (Morrowind 1) | in_dwrv_crank_nchuleft_01 | cast, disable, enable, getdisabled, getsecondspassed, onactivate, rotate | 5: getdisabled, local, onactivate | - | - |
| nchuleftingthWrong2 | molag mar region | runs | 1 activator; placed 1 (Morrowind 1) | in_dwrv_crank_nchuleft_02 | cast, disable, enable, getdisabled, getsecondspassed, onactivate, rotate | 5: getdisabled, local, onactivate | - | - |
| nchulfetingthRight | molag mar region | runs | 1 activator; placed 1 (Morrowind 1) | in_dwrv_crank_nchuleft_03 | cellchanged, disable, getsecondspassed, messagebox, moveworld, onactivate, playsound, rotate | 7: cellchanged, local, onactivate | - | - |
| reynelUvirithScript | molag mar region | runs | 1 NPC; placed 1 (Morrowind 1) | reynel uvirith | cellchanged, disable, enable, getpcrank | 2: cellchanged, getpcrank | - | - |
| secretsAnimunculi | molag mar region | runs | 1 book; placed 1 (Morrowind 1) | bk_secretsdwemeranimunculi | activate, addspell, onactivate | 2: local, onactivate | - | - |
| shrineAssarnibibi | molag mar region | runs | 1 activator; placed 1 (Morrowind 1) | ac_shrine_assarnibibi | additem, cast, getjournalindex, journal, messagebox, modreputation, onactivate | 7: getjournalindex, onactivate | - | - |
| shrineMountKand | molag mar region | runs | 1 activator; placed 1 (Morrowind 1) | ac_mount_kand_triolith | cast, getjournalindex, journal, messagebox, modreputation, onactivate | 3: getjournalindex, onactivate | - | - |
| sondaaleFollow | molag mar region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | sondaale of shimmerene | aiwander, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, say, sethello | 12: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode | - | - |
| Sound_Dwemer_Ambient | molag mar region | runs | 2 activator; placed 150 (Morrowind 121, Tribunal 26, Bloodmoon 3) | sound_dwemer_ruin00, sound_sotha_sparks | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Haunted | molag mar region | runs | 1 activator; placed 275 (Morrowind 241, Tribunal 5, Bloodmoon 29) | sound_haunted00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Lava_Vat | molag mar region | runs | 1 activator; placed 56 (Morrowind 52, Tribunal 4) | sound_lave_vat | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Machinery | molag mar region | runs | 4 activator; placed 49 (Morrowind 42, Tribunal 3, Bloodmoon 4) | furn_dwrv_beltdrive, furn_dwrv_dynamo, furn_dwrv_steam_00, furn_dwrv_tranny00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Power_light | molag mar region | runs | 1 activator; placed 53 (Morrowind 39, Tribunal 4, Bloodmoon 10) | sound_generator | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Steam | molag mar region | runs | 4 activator; placed 395 (Morrowind 374, Tribunal 18, Bloodmoon 3) | act_terrain_lava_vent, act_terrain_lava_ventlg, furn_dwrv_fitting40, volcano_steam | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Strong1_Only | molag mar region | runs | 12 activator; placed 9 (Morrowind 9) | ex_t_pc_hold_root_03_p1_comp, ex_t_pc_hold_root_03_p1comp, ex_t_pc_hold_root_04_p1_comp, ex_t_pc_hold_root_stem_p1_comp, ex_t_playertower_sprout_p1comp, flora_t_pc_hold_podbud_01 and 6 more | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| Strong2_Complete | molag mar region | runs | 12 activator, 6 door, 1 light; placed 46 (Morrowind 46) | ex_t_pc_hold_bridge_lcurved, ex_t_pc_hold_doorway_01, ex_t_pc_hold_doorway_02a, ex_t_pc_hold_housepod_02, ex_t_pc_hold_housestem_01, ex_t_pc_hold_housestem_02a and 13 more | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| Strong2_Only | molag mar region | runs | 6 activator; placed 5 (Morrowind 5) | ex_t_pc_hold_housepod_02b, ex_t_pc_hold_housepod_03, ex_t_pc_hold_root_xl_02aa, ex_t_pc_hold_root_xl_02cc, ex_t_pc_hold_tower_seedling_lrg, in_t_pc_holds_plain_hall_plug_b | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| Strong3 | molag mar region | runs | 19 activator, 1 door, 1 light; placed 27 (Morrowind 27) | ex_h_pcfort_03, ex_h_pcfort_04, ex_h_pcfort_bal_01, ex_h_pcfort_ds_01-3, ex_h_pcfort_lp_01-3, ex_h_pcfort_win_01-3 and 15 more | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| Strong3_Complete | molag mar region | runs | 11 activator, 2 creature, 3 door, 1 light; placed 54 (Morrowind 54) | ex_h_pcfort_bench_01, ex_h_pcfort_table_01, ex_t_pc_hold_doorway_01a, ex_t_pc_hold_gateway_great_a, ex_t_pc_hold_menhir_l_01_a, ex_t_pc_hold_root_hook_b and 11 more | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| Strong3_Not | molag mar region | runs | 2 activator; placed 2 (Morrowind 2) | in_t_pc_holds_plain_hall_plug_a, in_t_pc_holds_plain_hall_plug_d | disable, enable, getdisabled | 3: getdisabled, global | - | - |
| telaseroDisable | molag mar region | runs | 1 book, 1 WEAP; placed 2 (Morrowind 2) | bk_notefromsondaale, iron dagger_telasero_unique | disable, enable, getdisabled, getjournalindex | 5: getdisabled, getjournalindex, local | - | - |
| Vampire_Berne | molag mar region | runs | 23 NPC; placed 23 (Morrowind 23); speaker of 8 dialogue results | arenara, berne vampire 1, berne vampire 2, berne vampire 3, berne vampire 4, berne vampire 5 and 17 more | additem, addspell, getjournalindex, getspell, modrestoration, ondeath, setdisposition, setfight | 18: getjournalindex, getspell, global, local, ondeath | - | - |
| VampireMolag | molag mar region | runs | 1 activator; placed 1 (Morrowind 1) | active_dae_molagbal2 | addspell, cast, getjournalindex, journal, menumode, messagebox, modreputation, onactivate, say, saydone, startscript | 17: getjournalindex, global, local, menumode, onactivate, saydone | - | - |
| WarLoverKill | molag mar region | runs | 8 NPC; placed 8 (Morrowind 8); speaker of 56 dialogue results | ahaz, ainab, ashu-ahhe, hirarend, kushishi, ranabi and 2 more | journal, ondeath | 1: ondeath | - | - |
| Warp_Hlor | molag mar region | runs | 1 activator; placed 2 (Morrowind 2) | active_port_hlor | getitemcount, menumode, messagebox, onactivate, playsound, positioncell | 3: getitemcount, menumode, onactivate | - | - |
| diseaseWitbane | mournhold (tribunal) | runs | 1 creature; placed 15 (Morrowind 6, Tribunal 9); levelled lists 38 | rat_diseased | addspell, cellchanged, dontsaveobject, getcommondisease | 2: cellchanged, getcommondisease | dontsaveobject-ignored | - |
| LocalState | mournhold (tribunal) | runs | 17 activator, 1 NPC; placed 16 (Morrowind 3, Tribunal 13); speaker of 5 dialogue results | act_sotha_door10, act_sotha_door3, act_sotha_door9, act_sotha_mach_door1, act_sotha_mach_door2, act_sotha_oilbridge and 12 more | - | - | - | - |
| nohello | mournhold (tribunal) | runs | 10 NPC; placed 10 (Morrowind 5, Tribunal 5) | anden thilarvel, arnas therethi, drals indobar, ervis ules, sadas mavandes, sarvil sadus and 4 more | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| Sound_Bubbles | mournhold (tribunal) | runs | 1 activator; placed 9 (Tribunal 9) | sound_bubbles00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Main | named by nothing | AmiWind's own code, steps open | - | - | menumode, random, scriptrunning, startscript | 3: global, menumode, scriptrunning | - | engine/aga/src/aw_mwvm.c AW_MwvmNewGame (the game always runs it, OpenMW GlobalScripts::addStartup) does it, but 1 of its 3 steps is not as the script: every frame |
| amuletAundaeScript | records not placed | runs | 1 clothing | amulet_aundae | getbuttonpressed, messagebox, positioncell | 10: global, local | - | runs while the player carries one of its items |
| amuletBerneScript | records not placed | runs | 1 clothing | amulet_berne | getbuttonpressed, messagebox, positioncell | 10: global, local | - | runs while the player carries one of its items |
| amuletDaedraScript | records not placed | runs | 1 clothing; held by placed containers and actors 1 | daedric_special | getbuttonpressed, messagebox, positioncell | 9: local | - | runs on the items placed containers and actors hold, while their area is loaded |
| amuletQuarraScript | records not placed | runs | 1 clothing | amulet_quarra | getbuttonpressed, messagebox, positioncell | 10: global, local | - | runs while the player carries one of its items |
| amuletTelFyrScript | records not placed | runs | 1 clothing; held by placed containers and actors 1 | daedric_special01 | getbuttonpressed, messagebox, positioncell | 9: local | - | runs on the items placed containers and actors hold, while their area is loaded |
| BILL_FG_Nchurdamz04 | records not placed | runs | 1 clothing | common_ring_01_fg_nchur04 | getdeadcount, getdistance, getitemcount, getjournalindex, menumode, onactivate, say | 12: local, menumode, onactivate | - | runs while the player carries one of its items |
| BILL_MT_WritNavil2 | records not placed | runs | 1 NPC; placed by scripts (1 records); speaker of 1 dialogue results | ranes ienith | cellchanged, getdeadcount, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 7: cellchanged, getdeadcount, getjournalindex, local, menumode, ondeath | - | runs on the object a script places |
| BILL_TT_MountKand05 | records not placed | runs | 1 clothing | common_ring_01_tt_mountkand | getdistance, getjournalindex, menumode, onactivate, setfight | 10: local, menumode, onactivate | - | runs while the player carries one of its items |
| cattleScript | records not placed | runs | 19 NPC; levelled lists 25 | cattle_arg_f01, cattle_arg_f02, cattle_arg_m01, cattle_bos_f01, cattle_bos_m01, cattle_bre_f01 and 13 more | getjournalindex, journal, menumode, ondeath, setfight, setflee, stopcombat | 17: getjournalindex, global, local, menumode, ondeath | - | runs on the actor a levelled list gives |
| darksunScript | records not placed | runs | 1 armour; held by placed containers and actors 1 | darksun_shield_unique | getsecondspassed, menumode, messagebox, modcurrenthealth | 5: global, local, menumode | - | runs on the items placed containers and actors hold, while their area is loaded |
| diseaseAscended | records not placed | runs | 1 creature; levelled lists 10; speaker of 2 dialogue results | ascended_sleeper | addspell, cellchanged, dontsaveobject | 1: cellchanged | dontsaveobject-ignored | runs on the actor a levelled list gives |
| diseaseAshChancreKW | records not placed | runs | 1 creature; levelled lists 6 | kwama worker blighted | addspell, cellchanged, disable, dontsaveobject, enable, getblightdisease, getdeadcount, getjournalindex, getpccell, removespell, setfight | 45: cellchanged, getblightdisease, getdeadcount, getjournalindex, getpccell | dontsaveobject-ignored | runs on the actor a levelled list gives |
| diseaseAtaxia | records not placed | runs | 1 creature; levelled lists 19 | alit_diseased | addspell, cellchanged, dontsaveobject, getcommondisease | 2: cellchanged, getcommondisease | dontsaveobject-ignored | runs on the actor a levelled list gives |
| diseaseChanthrax | records not placed | runs | 1 creature; levelled lists 11 | kagouti_blighted | addspell, cellchanged, dontsaveobject, getblightdisease | 2: cellchanged, getblightdisease | dontsaveobject-ignored | runs on the actor a levelled list gives |
| diseaseCollywobbles | records not placed | runs | 1 creature; levelled lists 23 | shalk_diseased | addspell, cellchanged, dontsaveobject, getcommondisease | 2: cellchanged, getcommondisease | dontsaveobject-ignored | runs on the actor a levelled list gives |
| diseaseHelljoint | records not placed | runs | 1 creature; levelled lists 13 | cliff racer_diseased | addspell, cellchanged, dontsaveobject, getcommondisease | 2: cellchanged, getcommondisease | dontsaveobject-ignored | runs on the actor a levelled list gives |
| diseaseYellowTick | records not placed | runs | 1 creature; levelled lists 19 | kagouti_diseased | addspell, cellchanged, dontsaveobject, getcommondisease | 2: cellchanged, getcommondisease | dontsaveobject-ignored | runs on the actor a levelled list gives |
| disguisedArmor | records not placed | runs | 1 armour | bonemold_gah-julan_hhda | getpccell | 2: getpccell, local | - | runs while the player carries one of its items |
| gloveScript | records not placed | runs | 1 clothing | common_glove_r_balmolagmer | - | 1: local | - | runs while the player carries one of its items |
| lightofdayScript | records not placed | runs | 1 WEAP; held by placed containers and actors 1 | lightofday_unique | getsecondspassed, menumode, messagebox, modcurrenthealth | 5: global, local, menumode | - | runs on the items placed containers and actors hold, while their area is loaded |
| lucanScript2 | records not placed | runs | 1 NPC; placed by scripts (1 records); speaker of 1 dialogue results | lucan ostorius2 | forcegreeting, getdistance | 2: getdistance, local | - | runs on the object a script places |
| ouch_sunder | records not placed | runs | 1 WEAP; held by placed containers and actors 1 | sunder | gethealth, getitemcount, getsecondspassed, journal, menumode, messagebox, modcurrenthealth, random | 8: gethealth, getitemcount, global, local, menumode | - | runs on the items placed containers and actors hold, while their area is loaded |
| ouch_wraithguard | records not placed | runs | 1 armour | wraithguard_jury_rig | modhealth, random | 2: local | - | runs while the player carries one of its items |
| pillowScript | records not placed | runs | 1 item | misc_uni_pillow_unique | getitemcount, getpcsleep, messagebox | 7: getitemcount, getpcsleep, global, local | - | runs while the player carries one of its items |
| sealedTreasuryOrders | records not placed | runs | 3 book; held by placed containers and actors 1 | bk_landdeed_hhrd, bk_landdeedfake_hhrd, bk_treasuryorders | activate, additem, disable, getbuttonpressed, getdisabled, getsecurity, messagebox, onactivate, random | 20: getdisabled, getsecurity, local, onactivate | - | runs on the items placed containers and actors hold, while their area is loaded |
| sealedTreasuryReport | records not placed | runs | 1 book | bk_treasuryreport | activate, additem, disable, getbuttonpressed, getdisabled, getsecurity, messagebox, onactivate, random | 20: getdisabled, getsecurity, local, onactivate | - | runs while the player carries one of its items |
| theranaSkirtScript | records not placed | runs | 1 clothing | therana's skirt | - | 1: local | - | runs while the player carries one of its items |
| wraithguardScript | records not placed | runs | 1 armour | wraithguard | - | 1: local | - | runs while the player carries one of its items |
| Akula_innerdoors | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | in_dwrv_crank_akula00 | getsecondspassed, menumode, onactivate, playsound, rotate, setangle | 10: local, menumode, onactivate | - | - |
| ashStatueTopic | red mountain region | runs | 3 item; placed 240 (Morrowind 240); held by placed containers and actors 32 | misc_6th_ash_hrcs, misc_6th_ash_hrmm, misc_6th_ash_statue_01 | activate, addtopic, onactivate | 1: onactivate | - | - |
| ashvampire | red mountain region | runs | 7 creature; placed 7 (Morrowind 7); speaker of 15 dialogue results | dagoth araynys, dagoth endus, dagoth gilvoth, dagoth odros, dagoth tureynul, dagoth uthol and 1 more | gethealth, getjournalindex, modfatigue, modhealth, modmagicka, modspeed, modstrength, modwillpower, ondeath, sethealth | 3: gethealth, getjournalindex, ondeath | dagoth-ur-remote-change | - |
| Dagoth_doors | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | ex_dwrv_crank_dagoth | getsecondspassed, menumode, onactivate, playsound, rotate, setangle | 10: local, menumode, onactivate | - | - |
| DagothDoorDetector | red mountain region | runs | 1 activator; placed 2 (Morrowind 2) | dagoth destroy detector | getdistance, startscript | 3: getdistance, global | - | - |
| DagothTaunt_1 | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | in_dagoth_taunt1 | getitemcount, getjournalindex, getstandingpc, menumode, say | 5: getitemcount, getjournalindex, getstandingpc, local, menumode | - | - |
| DagothTaunt_2 | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | in_dagoth_taunt2 | getitemcount, getjournalindex, getstandingpc, menumode, say | 5: getitemcount, getjournalindex, getstandingpc, local, menumode | - | - |
| DagothTaunt_3 | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | in_dagoth_taunt3 | getitemcount, getjournalindex, getstandingpc, menumode, say | 5: getitemcount, getjournalindex, getstandingpc, local, menumode | - | - |
| DagothTaunt_4 | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | in_dagoth_taunt4 | getitemcount, getjournalindex, getstandingpc, menumode, say | 5: getitemcount, getjournalindex, getstandingpc, local, menumode | - | - |
| DagothTaunt_5 | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | in_dagoth_taunt5 | getitemcount, getjournalindex, getstandingpc, menumode, say | 5: getitemcount, getjournalindex, getstandingpc, local, menumode | - | - |
| DagothTaunt_6 | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | in_dagoth_taunt6 | getitemcount, getjournalindex, getstandingpc, menumode, say | 5: getitemcount, getjournalindex, getstandingpc, local, menumode | - | - |
| DagothTaunt_7 | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | in_dagoth_taunt7 | getitemcount, getjournalindex, getstandingpc, menumode, say | 5: getitemcount, getjournalindex, getstandingpc, local, menumode | - | - |
| DagothUrCreature2 | red mountain region | runs | 1 creature; placed 1 (Morrowind 1) | dagoth_ur_2 | addspell, disableteleporting, gethealth, getmagicka, getsecondspassed, getspell, menumode, removespell, say, sethealth, setmagicka | 28: gethealth, getmagicka, getspell, global, local, menumode, other script | - | - |
| diseaseBrownRot | red mountain region | runs | 4 creature; placed 6 (Morrowind 6); levelled lists 12 | bonewalker, bonewalker_greater, bonewalker_greater_summ, bonewalker_summon | addspell, cellchanged, dontsaveobject, getcommondisease | 2: cellchanged, getcommondisease | dontsaveobject-ignored | - |
| dreamerWorkerScript | red mountain region | runs | 1 NPC; placed 3 (Morrowind 3) | dreamer worker | disable, getdeadcount, sethealth | 5: getdeadcount, global, local | - | - |
| ouch_keening | red mountain region | runs | 1 WEAP; placed 1 (Morrowind 1) | keening | gethealth, getitemcount, getsecondspassed, journal, menumode, messagebox, modcurrenthealth, random | 8: gethealth, getitemcount, global, local, menumode | - | - |
| ringAzuraScript | red mountain region | runs | 1 clothing; placed 1 (Morrowind 1) | ring of azura | activate, cast, cellchanged, disable, onactivate, rotate | 3: cellchanged, local, onactivate | - | - |
| shrineGhostgate | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | furn_shrine_vivec_cure_03 | cast, getbuttonpressed, getitemcount, journal, messagebox, onactivate, removeitem | 16: getitemcount, local, onactivate | - | - |
| BILL_MarksSpiritSummon | sheogorad | runs | 1 WEAP; placed 8 (Morrowind 8) | silver dagger_hanin cursed | activate, getpccell, getpos, onactivate, placeatpc | 4: getpccell, local, onactivate | - | - |
| BILL_MT_WritBelvayn | sheogorad | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | tirer belvayn | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| da_forkScript | sheogorad | runs | 1 WEAP; placed 1 (Morrowind 1) | fork_horripilation_unique | getjournalindex, journal, ondeath | 5: getjournalindex, local, ondeath | - | - |
| DaedraMalacath | sheogorad | runs | 1 activator; placed 1 (Morrowind 1) | active_dae_malacath | additem, addtopic, enable, getjournalindex, getrace, journal, messagebox, onactivate, say, saydone | 14: getjournalindex, getrace, local, onactivate, saydone | - | - |
| DoorBarricaded | sheogorad | runs | 1 activator; placed 1 (Morrowind 1) | a_ex_de_shack_door | menumode, messagebox, onactivate | 2: menumode, onactivate | - | - |
| eotScript | sheogorad | runs | 1 book; placed 1 (Morrowind 1) | bk_eggoftime | activate, addtopic, onactivate | 2: local, onactivate | - | - |
| mararaScript | sheogorad | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | marara | addspell, getjournalindex, journal, modrestoration, ondeath, setfight | 8: getjournalindex, global, local, ondeath | - | - |
| raynaScript | sheogorad | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | rayna drolan | forcegreeting, getdistance | 2: getdistance, local | - | - |
| shrineDagonFel | sheogorad | runs | 1 activator; placed 1 (Morrowind 1) | active_dae_malacath_df | cast, getitemcount, getjournalindex, journal, messagebox, modreputation, onactivate, removeitem | 3: getitemcount, getjournalindex, onactivate | - | - |
| shrineSanctus | sheogorad | runs | 1 activator; placed 1 (Morrowind 1) | ac_sanctus_shrine_triolith | cast, getjournalindex, journal, messagebox, onactivate | 4: getjournalindex, onactivate | - | - |
| staadaScript | sheogorad | runs | 1 creature; placed 1 (Morrowind 1) | golden saint_staada | getjournalindex, journal, ondeath | 2: getjournalindex, ondeath | - | - |
| ulyneFollow | sheogorad | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 6 dialogue results | ulyne henim | aiwander, forcegreeting, getcurrentaipackage, getdeadcount, getdistance, gethealth, getjournalindex, getsecondspassed, journal, menumode, say, sethello | 10: getcurrentaipackage, getdeadcount, getdistance, gethealth, getjournalindex, global, local, menumode | - | - |
| Vampire_Aundae | sheogorad | runs | 21 NPC; placed 25 (Morrowind 25); speaker of 17 dialogue results | aleri duro, ano dran, aundae vampire 1, aundae vampire 2, aundae vampire 3, aundae vampire 4 and 15 more | additem, addspell, getjournalindex, getspell, modrestoration, ondeath, setdisposition, setfight | 18: getjournalindex, getspell, global, local, ondeath | - | - |
| ajiraReports | west gash region | runs | 2 book; placed 2 (Morrowind 2) | bk_ajira1, bk_ajira2 | disable, enable, getjournalindex | 4: getjournalindex, local | - | - |
| ajiraScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 18 dialogue results | ajira | cellchanged, getjournalindex, raiserank | 5: cellchanged, getjournalindex, local | - | - |
| alvisTeriScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | alvis teri | cellchanged, getdisabled, getjournalindex, gettarget, onmurder, setdisposition, setfight, startcombat, stopcombat | 7: cellchanged, getdisabled, getjournalindex, gettarget, local, onmurder | - | - |
| arethanMandasScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | arethan mandas | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| attack_slave | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | vorar helas | aiwander, getdeadcount, getdistance, getjournalindex, journal, startcombat | 3: getdeadcount, getdistance, getjournalindex | - | - |
| avSlavehunter | west gash region | runs | 3 NPC; placed 3 (Morrowind 3); speaker of 3 dialogue results | anes hlaren, garyn girith, sadal doren | cellchanged, disable, enable, getdetected, getdistance, getjournalindex, getsecondspassed, startcombat | 7: cellchanged, getdetected, getdistance, getjournalindex, local | - | - |
| baladasCenturion | west gash region | runs | 1 creature; placed 1 (Morrowind 1) | centurion_shock_baladas | aifollow, cellchanged, disable, enable, getdeadcount, getjournalindex, positioncell | 6: cellchanged, getdeadcount, getjournalindex, local | - | - |
| balynScript | west gash region | runs | 2 NPC; placed 2 (Morrowind 2) | balyn omavel, balyn omavel-dead | forcegreeting, getdistance, getjournalindex, getlos, getsecondspassed, journal | 7: getdistance, getjournalindex, getlos, local | - | - |
| BILL_MT_WritBaladas | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 35 dialogue results | baladas demnevanni | cellchanged, getdetected, getjournalindex, getpccrimelevel, getsecondspassed, journal, menumode, ondeath, startcombat, stopcombat | 8: cellchanged, getdetected, getjournalindex, local, menumode, ondeath | - | - |
| BILL_MT_WritVarro | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 17 dialogue results | larrius varro | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| BILL_synette_jeline | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | synette jeline | aitravel, getitemcount, getjournalindex, journal, menumode, say, setfight, startcombat | 8: getitemcount, getjournalindex, local, menumode | - | - |
| BILL_TT_Bulfim_gra-Shugharz | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | bulfim_gra_shugarz | getblightdisease, getjournalindex, journal, moddisposition, say | 2: getblightdisease, getjournalindex | - | - |
| corrudusScript | west gash region | runs | 2 NPC; placed 1 (Morrowind 1); speaker of 19 dialogue results | corrudus secunia, cunius pelelius | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| DaedraMehrunes | west gash region | runs | 1 activator; placed 1 (Morrowind 1) | active_dae_mehrunes | additem, getbuttonpressed, getdistance, getitemcount, getjournalindex, journal, messagebox, onactivate, removeitem, say, saydone | 20: getdistance, getitemcount, getjournalindex, local, onactivate, saydone | - | - |
| dariusScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 39 dialogue results | general darius | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| dinScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 11 dialogue results | din | aiwander, forcegreeting, getdistance, getjournalindex, getspell, journal, ondeath | 8: getdistance, getjournalindex, getspell, ondeath | - | - |
| diseaseAshChancre | west gash region | runs | 4 creature; placed 2 (Morrowind 2); levelled lists 52 | cliff racer_blighted, kwama forager blighted, kwama warrior blighted, scrib blighted | addspell, cellchanged, disable, dontsaveobject, enable, getblightdisease, getdeadcount, getpccell, removespell | 43: cellchanged, getblightdisease, getdeadcount, getpccell | dontsaveobject-ignored | - |
| diseaseDroops | west gash region | runs | 2 creature; placed 3 (Morrowind 3); levelled lists 40 | kwama worker diseased, scrib diseased | addspell, cellchanged, dontsaveobject, getcommondisease | 2: cellchanged, getcommondisease | dontsaveobject-ignored | - |
| diseaseWither | west gash region | runs | 1 NPC; placed 36 (Morrowind 36); speaker of 2 dialogue results | dreamer | addspell, cellchanged, dontsaveobject, getcommondisease | 2: cellchanged, getcommondisease | dontsaveobject-ignored | - |
| dmamiScript | west gash region | runs | 1 book; placed 1 (Morrowind 1) | bk_divinemetaphysics | activate, addtopic, onactivate | 2: local, onactivate | - | - |
| druleneScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 11 dialogue results | drulene falen | getcurrentaipackage, getdistance, getsecondspassed | 4: getcurrentaipackage, getdistance, local | - | - |
| eydisScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 29 dialogue results | eydis fire-eye | forcegreeting, getdistance, getjournalindex, startcombat | 3: getdistance, getjournalindex, local | - | - |
| fastEddieScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 12 dialogue results | edd theman | cellchanged, disable, enable, getjournalindex | 5: cellchanged, getjournalindex | - | - |
| fedrisTharenScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | fedris tharen | getcommondisease, getdisabled, getjournalindex, journal | 3: getcommondisease, getdisabled, getjournalindex | - | - |
| galbedirDesk | west gash region | runs | 1 container; placed 1 (Morrowind 1) | de_p_desk_01_galbedir | getitemcount, getjournalindex | 3: getitemcount, getjournalindex | - | - |
| galbedirScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1) | galbedir | aitravel, aiwander, cellchanged, getaipackagedone, getdistance, getjournalindex, getsecondspassed | 14: cellchanged, getaipackagedone, getdistance, getjournalindex, local | - | - |
| hannatScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 8 dialogue results | hannat zainsubani | aiwander, cellchanged, disable, forcegreeting, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, say, sethello | 13: cellchanged, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local | - | - |
| hisin_deep_raed | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | hisin deep-raed | forcegreeting, getjournalindex, getspell, journal | 3: getjournalindex, getspell, local | - | - |
| hlormarScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 18 dialogue results | hlormar wine-sot | forcegreeting, getcurrentaipackage, getdistance, getitemcount, getjournalindex, menumode | 7: getcurrentaipackage, getdistance, getitemcount, getjournalindex, local, menumode | - | - |
| Ingwold_disable | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 11 dialogue results | ingwold | cellchanged, disable, getdisabled, getjournalindex | 3: cellchanged, getdisabled, getjournalindex | - | - |
| irarakScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | irarak | addspell, getjournalindex, getspell, journal, modrestoration, ondeath, setfight | 9: getjournalindex, getspell, local, ondeath | - | - |
| itermerelScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | itermerel | aiwander, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, say, sethello | 11: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode | - | - |
| jsaddhaScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | j_saddha | aifollow, cellchanged, disable, enable, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getsecondspassed, journal, menumode, say, sethello | 14: cellchanged, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, global, local, menumode | - | - |
| kwamaQueenGnisis | west gash region | runs | 1 creature; placed 1 (Morrowind 1) | kwama queen_gnisis | getblightdisease, getjournalindex, journal | 3: getblightdisease, getjournalindex | - | - |
| lugrubScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | lugrub gro-ogdum | cellchanged, forcegreeting, getdistance, getjournalindex, getsecondspassed, menumode, startcombat, stopcombat | 8: cellchanged, getdistance, getjournalindex, local, menumode | - | - |
| MaduraFollow | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | madura seran | aiwander, forcegreeting, getcurrentaipackage, getdistance, gethealth, getpccell, getsecondspassed, journal, menumode, moddisposition, modpcfacrep, modreputation, say, sethello | 9: getcurrentaipackage, getdistance, gethealth, getpccell, global, local, menumode | - | - |
| mandasGuards | west gash region | runs | 7 NPC; placed 7 (Morrowind 7) | danaronea daryon, dramis maryon, faver seran, gandela indoran, ilmyna romoren, ivela uvenim and 1 more | getjournalindex, setdisposition, setfight, stopcombat | 2: getjournalindex, local | - | - |
| mertaScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | merta | addspell, forcegreeting, getdistance, getjournalindex, getspell, journal, modrestoration, ondeath, setfight | 12: getdistance, getjournalindex, getspell, global, local, ondeath | - | - |
| noPickUp | west gash region | runs | 1 item; placed 1 (Morrowind 1) | misc_vivec_ashmask_01_fake | onactivate | 1: onactivate | - | - |
| NPC_State | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 2 dialogue results | vatollia apo | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| odralHelviScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 21 dialogue results | odral helvi | - | - | - | - |
| ondresNeranoScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | ondres nerano | cellchanged, forcegreeting, gethealth, getjournalindex, journal, ondeath, onknockout, onmurder, setfight, stopcombat | 6: cellchanged, gethealth, getjournalindex, ondeath, onknockout, onmurder | - | - |
| pemenieScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 9 dialogue results | pemenie | aiwander, forcegreeting, getcurrentaipackage, getdistance, getjournalindex, getpccell, journal, ondeath | 7: getcurrentaipackage, getdistance, getjournalindex, getpccell, ondeath | - | - |
| poisonfoodScript | west gash region | runs | 1 activator; placed 1 (Morrowind 1) | active_cauldron_balyn | getbuttonpressed, getitemcount, getjournalindex, journal, messagebox, onactivate, removeitem | 7: getitemcount, getjournalindex, local, onactivate | - | - |
| Pub_Balmora_Council | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 4 dialogue results | banor seran | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Balmora_Eight | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 3 dialogue results | dulnea ralaal | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Balmora_Lucky | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | benunius agrudilius | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Balmora_South | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | bacola closcius | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| Pub_Caldera_Shenk | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 1 dialogue results | shenk | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| ragashScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 6 dialogue results | ragash gra-shuzgub | aiwander, disable, enable, forcegreeting, getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, say, sethello | 15: getaipackagedone, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode | - | - |
| ralenHlaaloScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1) | ralen hlaalo | activate, addtopic, journal, onactivate | 2: local, onactivate | - | - |
| sasonScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 7 dialogue results | sason | aifollow, forcegreeting, getdistance, getjournalindex, menumode | 5: getdistance, getjournalindex, local, menumode | - | - |
| scampScript | west gash region | runs | 1 creature; placed 1 (Morrowind 1); speaker of 5 dialogue results | scamp_creeper | - | 1: local | - | - |
| shrineGnisis | west gash region | runs | 1 activator; placed 1 (Morrowind 1) | ac_shrine_gnisis | cast, getbuttonpressed, getitemcount, journal, messagebox, onactivate, removeitem | 8: getitemcount, local, onactivate | - | - |
| shrineGnisisRealMask | west gash region | runs | 1 item; placed 1 (Morrowind 1) | misc_vivec_ashmask_01 | addspell, cast, getspell, onactivate | 2: getspell, onactivate | - | - |
| shrineGnisisSecret | west gash region | runs | 1 activator; placed 1 (Morrowind 1) | ac_shrine_gnisis_mv | cast, cellchanged, getbuttonpressed, getitemcount, getjournalindex, getsecondspassed, journal, menumode, messagebox, move, onactivate, playsound3d, removeitem, setpos | 15: cellchanged, getitemcount, getjournalindex, local, menumode, onactivate | - | - |
| shrineKoalCave | west gash region | runs | 1 activator; placed 1 (Morrowind 1) | ac_shrine_koalcave | additem, cast, getbuttonpressed, getdeadcount, getitemcount, journal, messagebox, onactivate, removeitem | 8: getdeadcount, getitemcount, local, onactivate | - | - |
| shrineLlothis | west gash region | runs | 1 activator; placed 5 (Morrowind 5) | furn_shrine_llothis_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrineRilm | west gash region | runs | 1 activator; placed 5 (Morrowind 5) | furn_shrine_rilm_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 26: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| shrineVeloth | west gash region | runs | 1 activator; placed 33 (Morrowind 32, Tribunal 1) | furn_shrine_veloth_cure_01 | cast, getblightdisease, getbuttonpressed, getcommondisease, geteffect, getitemcount, getpcrank, menumode, messagebox, onactivate, removeitem | 29: getblightdisease, getcommondisease, geteffect, getitemcount, getpcrank, local, menumode, onactivate | - | - |
| Sound_Creeky_Wood | west gash region | runs | 1 activator; placed 68 (Morrowind 68) | sound_cave_oldwood00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| SpyMasterScript | west gash region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 55 dialogue results | caius cosades | cellchanged, disable, getjournalindex, menumode | 6: cellchanged, getjournalindex, global, local, menumode | - | - |
| talosTraitorScript | west gash region | runs | 2 NPC; placed 2 (Morrowind 2); speaker of 3 dialogue results | arius rulician, oritius maro | getitemcount, setdisposition, setfight | 2: getitemcount, local | - | - |
| vabdasGhostScript | west gash region | runs | 1 creature; placed 1 (Morrowind 1); speaker of 1 dialogue results | ancestor_ghost_vabdas | disable, forcegreeting, getdisabled, getdistance, getjournalindex, menumode | 5: getdisabled, getdistance, getjournalindex, menumode | - | - |
| Vampire_Quarra | west gash region | runs | 17 NPC; placed 23 (Morrowind 23); speaker of 13 dialogue results | areas, garalo andalas, igna, kjeld, knurguri, ninimilk addinibi and 11 more | additem, addspell, getjournalindex, getspell, modrestoration, ondeath, setdisposition, setfight | 18: getjournalindex, getspell, global, local, ondeath | - | - |

### Tribunal

| Script | Area | State | Referenced by | Records | Functions | Conditions | Follows OpenMW's fix | Why |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| fab_attack_disable | ascadian isles region | runs | 3 activator, 1 light; placed 20 (Morrowind 11, Tribunal 9) | ex_mh_almalexia_statue, ex_mh_pav_top, ex_mh_pav_water_spray, blue candle bulb_177 | disable | 1: global | - | - |
| lucan_ostorius | ashlands region | runs | 1 activator; placed 1 (Morrowind 1) | lucan_scriptholder | disable, getdeadcount, getjournalindex, getpccell, placeatpc | 11: getdeadcount, getjournalindex, getpccell, local | - | - |
| BILL_MT_calc_legit_kills | dialogue only | runs | started by 8 dialogue results | - | getitemcount, getjournalindex, getpccrimelevel, stopscript | 70: getitemcount, getjournalindex | - | - |
| BILL_MT_redeem_writs | dialogue only | runs | started by 3 dialogue results | - | getitemcount, getjournalindex, removeitem, setpccrimelevel, stopscript | 74: getitemcount, getjournalindex, global, local | - | - |
| bladefixScript | dialogue only | runs | started by 1 dialogue results | - | menumode | 6: global, local, menumode | - | - |
| Contract_Calvus | dialogue only | runs | started by 2 dialogue results | - | aiwander, menumode, ondeath, stopscript | 11: global, local, menumode, ondeath, other script | - | - |
| DrothPost | dialogue only | runs | started by 1 dialogue results | - | getjournalindex, getpccell, journal, removeitem, stopscript | 2: getjournalindex, getpccell | - | - |
| GaenorTimer | dialogue only | runs | started by 2 dialogue results | - | disable, getdisabled, getjournalindex, getpccell, journal, menumode, stopscript | 11: getdisabled, getjournalindex, getpccell, global, local, menumode | - | - |
| GetPCGold | dialogue only | runs | started by 10 dialogue results | - | getitemcount | - | - | - |
| GoToJailWhenDone | dialogue only | runs | started by 1 dialogue results | - | gotojail, menumode, stopscript | 1: menumode | - | - |
| helsMoveScript | dialogue only | runs | started by 1 dialogue results | - | getjournalindex, getpccell, position, stopscript | 3: getjournalindex, getpccell, local | - | - |
| HighPocketsCellCheck | dialogue only | runs | started by 1 dialogue results | - | cellchanged | 1: cellchanged | - | - |
| HolmarCellCheck | dialogue only | runs | started by 3 dialogue results | - | cellchanged, getjournalindex, stopscript | 4: cellchanged, getjournalindex | - | - |
| IgnatiusCellCheck | dialogue only | runs | started by 1 dialogue results | - | cellchanged, stopscript | 3: cellchanged, other script | - | - |
| IlnoriCellCheck | dialogue only | runs | started by 1 dialogue results | - | cellchanged, getjournalindex, stopscript | 3: cellchanged, getjournalindex, other script | - | - |
| JournalistCombat | dialogue only | runs | started by 2 dialogue results | - | startcombat, stopscript | - | - | - |
| MatchMakerTimer | dialogue only | runs | started by 3 dialogue results | - | getjournalindex, getpccell, journal, positioncell, startscript, stopscript | 10: getjournalindex, getpccell, global, local | - | - |
| MHTransportScript | dialogue only | runs | started by 2 dialogue results | - | menumode, playsound, positioncell, stopscript | 1: menumode | - | - |
| SadriThief | dialogue only | runs | started by 1 dialogue results | - | disable, lock, positioncell, removeitem, sethealth, stopscript | - | - | - |
| ScrollSales | dialogue only | runs | started by 1 dialogue results | - | activate, enable, forcegreeting, getdisabled, getjournalindex, journal, menumode, onactivate, ondeath, stopscript | 9: getdisabled, getjournalindex, local, menumode, onactivate, ondeath | - | - |
| SothaSilTeleport | dialogue only | runs | started by 1 dialogue results | - | menumode, playsound, positioncell, stopscript | 1: menumode | - | - |
| TherdonCellCheck | dialogue only | runs | started by 1 dialogue results | - | cellchanged, stopscript | 1: cellchanged | - | - |
| VelasCellCheck | dialogue only | runs | started by 1 dialogue results | - | cellchanged, stopscript | 1: cellchanged | - | - |
| VVTransportScript | dialogue only | runs | started by 1 dialogue results | - | menumode, playsound, positioncell, stopscript | 1: menumode | - | - |
| Warlord_aScript | dialogue only | runs | started by 1 dialogue results | - | getpccell, journal, positioncell, removeitem, sethealth | 5: getpccell, global, local | - | - |
| dbattackScript | global scripts | runs | started by MarkTRStartScript | - | getjournalindex, getlevel, getpccell, getpcsleep, messagebox, placeatpc, random, wakeuppc | 28: getjournalindex, getlevel, getpccell, getpcsleep, local | - | - |
| karrodMovement | global scripts | runs | started by karrodScript; started by 1 dialogue results | - | aitravel, aiwander, face, getaipackagedone, getjournalindex, getpccell, getsecondspassed, menumode, positioncell, say, startcombat, stopscript | 73: getaipackagedone, getjournalindex, getpccell, global, local, menumode | - | - |
| MarkTRStartScript | global scripts | runs | start script | - | disable, startscript, stopscript | 1: local | - | - |
| MatchMakeFons | global scripts | runs | started by MatchMakerTimer | - | aiwander, getdeadcount, positioncell, random, stopscript | 10: getdeadcount, global, random | - | - |
| MatchMakeGoval | global scripts | runs | started by MatchMakerTimer | - | additem, aiwander, getdeadcount, positioncell, random, stopscript | 11: getdeadcount, global, random | - | - |
| MatchMakeSunel | global scripts | runs | started by MatchMakerTimer | - | getdeadcount, positioncell, random, stopscript | 10: getdeadcount, global, local | - | - |
| TribFabAttackCheck | global scripts | runs | start script | - | getdeadcount, getjournalindex, getpccell, journal, stopscript | 10: getdeadcount, getjournalindex, getpccell, global, local | - | - |
| TribunalMain | global scripts | runs | start script | - | disablelevitation, disableteleporting, enablelevitation, enableteleporting, getinterior, getpccell | 7: getinterior, getpccell, local | - | - |
| AhniaDead | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 3 dialogue results | ahnia | getjournalindex, journal, ondeath | 3: getjournalindex, ondeath | - | - |
| AhniaNote | mournhold (tribunal) | runs | 1 book; placed 1 (Tribunal 1) | bk_ahnia | activate, disable, enable, forcegreeting, getdeadcount, getdisabled, getjournalindex, journal, onactivate | 10: getdeadcount, getdisabled, getjournalindex, local, onactivate | - | - |
| Alen_note | mournhold (tribunal) | runs | 1 book; placed 1 (Tribunal 1) | bk_alen_note | activate, disable, enable, getdisabled, getjournalindex, journal, onactivate | 5: getdisabled, getjournalindex, local, onactivate | - | - |
| almaScript | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1); speaker of 24 dialogue results | almalexia | disable, getdisabled, getdistance, getjournalindex, random, say, startcombat | 12: getdisabled, getdistance, getjournalindex, local | - | - |
| alusannahScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 1 dialogue results | alusannah | disable, enable, getjournalindex | 2: getjournalindex | - | - |
| armionScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1) | armion | journal, ondeath | 2: local, ondeath | - | - |
| bakhScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 2 dialogue results | bakh gro-sham | disable, enable, getdisabled, getjournalindex | 3: getdisabled, getjournalindex | - | - |
| barAssScript | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | active_assassin_unique | aitravel, clearforcesneak, disable, enable, forcesneak, getaipackagedone, getdistance, getjournalindex, getsecondspassed, journal, menumode, playsound3d, say, startcombat | 46: getaipackagedone, getdistance, getjournalindex, global, local, menumode, other script | - | - |
| bardoor1Script | mournhold (tribunal) | runs | 1 door; placed 1 (Tribunal 1) | in_mh_door_02_bar1_uni | activate, onactivate | 2: local, onactivate | - | - |
| bardoor2Script | mournhold (tribunal) | runs | 1 door; placed 1 (Tribunal 1) | in_mh_door_02_bar2_uni | activate, getjournalindex, messagebox, onactivate, playsound | 4: getjournalindex, local, onactivate | - | - |
| bardoor4Script | mournhold (tribunal) | runs | 1 door; placed 1 (Tribunal 1) | in_mh_door_02_bar4_uni | activate, getjournalindex, messagebox, onactivate, playsound | 2: getjournalindex, onactivate | - | - |
| barilzarScript | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1); speaker of 1 dialogue results | lich_barilzar | forcegreeting, getdistance, getjournalindex | 4: getdistance, getjournalindex, local | - | - |
| BattleBot1Script | mournhold (tribunal) | runs | 2 creature; placed 1 (Tribunal 1) | centurion_sphere_bbot1, centurion_spider_bbot1 | gethealth, getjournalindex, menumode, startcombat | 5: gethealth, getjournalindex, local, menumode, other script | - | - |
| BattleBot2Script | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1) | centurion_steam_bbot2 | gethealth, getjournalindex, menumode, startcombat | 5: gethealth, getjournalindex, local, menumode, other script | - | - |
| BolsIndalen | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 56 dialogue results | bols indalen | - | 1: global, local | - | - |
| cavein_script | mournhold (tribunal) | runs | 1 activator; placed 2 (Tribunal 2) | act_dwe_cavein00 | getangle, getbuttonpressed, getdistance, getitemcount, getpos, getsecondspassed, messagebox, onactivate, playgroup, removeitem, sethealth | 20: getdistance, getitemcount, local, onactivate | - | - |
| cent_fab_attack | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1) | centurion_steam_c_l | cellchanged, sethealth, startcombat | 3: cellchanged, local, other script | - | - |
| changeWater_-550_400 | mournhold (tribunal) | runs | 1 activator; placed 2 (Tribunal 2) | act_h20crank_-550_400 | getangle, getsecondspassed, getwaterlevel, menumode, onactivate, playsound3d, setangle, setwaterlevel | 15: local, menumode, onactivate | - | - |
| chapeldoorScript | mournhold (tribunal) | runs | 2 door; placed 4 (Tribunal 4) | ex_mh_temple_door_01_ch, in_mh_door_02_chapel | activate, getjournalindex, messagebox, onactivate, playsound | 3: getjournalindex, local, onactivate | - | - |
| Collide_damage_100 | mournhold (tribunal) | runs | 1 activator; placed 2 (Tribunal 2) | act_sotha_spikes | hurtcollidingactor | - | - | - |
| Collide_damage_kill | mournhold (tribunal) | runs | 2 activator; placed 5 (Tribunal 5) | act_sotha_dicer, act_sotha_tenderizer | hurtcollidingactor | - | - | - |
| cryptboulderScript | mournhold (tribunal) | runs | 4 activator; placed 4 (Tribunal 4) | in_moldboulder00_uni, in_moldboulder01_uni, in_moldrock05_uni, in_moldrock06_uni | disable, enable, getdisabled, getjournalindex, menumode | 5: getdisabled, getjournalindex, local, menumode | - | - |
| dandrasScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 2 dialogue results | dandras vules | forcegreeting, gethealth, modhealth, resurrect | 4: local | - | - |
| dbHideoutScript | mournhold (tribunal) | runs | 1 activator; placed 3 (Tribunal 3) | active_dbhideout | getdistance, getjournalindex, journal | 4: getdistance, getjournalindex, local | - | - |
| denegorScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 3 dialogue results | denegor | cellchanged, disable, getdeadcount, gethealth, getjournalindex, journal, menumode, messagebox, ondeath, onknockout, setfatigue | 14: cellchanged, getdeadcount, gethealth, getjournalindex, local, menumode, ondeath, onknockout | - | - |
| DetritusScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 17 dialogue results | detritus caria | disable, enable, getjournalindex | 4: getjournalindex | - | - |
| dilbornScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 3 dialogue results | dilborn | cellchanged, disable, getdeadcount, getjournalindex, journal, ondeath, startcombat | 22: cellchanged, getdeadcount, getjournalindex, local, ondeath | - | - |
| drathasNerusScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 9 dialogue results | drathas nerus | getattacked, ondeath, startcombat | 3: getattacked, ondeath, other script | - | - |
| DrathasScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 2 dialogue results | drathas reyas | - | - | - | - |
| DrathasThugScript | mournhold (tribunal) | runs | 2 NPC; placed 2 (Tribunal 2); speaker of 4 dialogue results | alam merys, melur savil | getattacked, getdeadcount, getjournalindex, ondeath, startcombat | 10: getattacked, getdeadcount, getjournalindex, local, ondeath | - | - |
| dravilScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 2 dialogue results | dravil indrano | additem, getjournalindex, journal, messagebox, ondeath, setdisposition, setfight, startcombat | 5: getjournalindex, local, ondeath | - | - |
| DrothCopy | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | silver dagger_droth_unique_a | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| DrothGeon | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 15 dialogue results | geon auline | getjournalindex, journal, ondeath | 3: getjournalindex, ondeath | - | - |
| drownOnExit | mournhold (tribunal) | runs | 4 NPC; placed 4 (Tribunal 4) | black dart adren, black dart gilur, black dart malar, black dart urvyn | cellchanged, gethealth, getwaterlevel, sethealth | 4: cellchanged, gethealth, getwaterlevel, local | - | - |
| dulniScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 7 dialogue results | urvel dulni | aifollow, aitravel, disable, enable, forcegreeting, getaipackagedone, getdistance, getjournalindex, getsecondspassed, journal, menumode, playgroup, playsound | 17: getaipackagedone, getdistance, getjournalindex, local, menumode | - | - |
| enoScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 3 dialogue results | eno romari | disable, enable, getdisabled, getjournalindex | 5: getdisabled, getjournalindex, local | - | - |
| ExitBlockMessage | mournhold (tribunal) | runs | 1 activator; placed 5 (Tribunal 5) | editormarker_box_02 | getcollidingpc, messagebox | 2: getcollidingpc, local | - | - |
| fab_attack_1 | mournhold (tribunal) | runs | 1 creature; placed 4 (Tribunal 4) | fabricant_hulkin_attack | disable, enable, getjournalindex, journal, startcombat | 3: getjournalindex, global, local | - | - |
| fab_attack_2 | mournhold (tribunal) | runs | 1 creature; placed 4 (Tribunal 4) | fabricant_verm_attack | disable, enable, startcombat | 1: global | - | - |
| fab_attack_enable | mournhold (tribunal) | runs | 15 activator; placed 17 (Tribunal 17) | ex_mh_pav_bstatue_01, ex_mh_pav_bstatue_02, ex_mh_pav_bstatue_03, ex_mh_pav_bstatue_05, ex_mh_pav_bstatue_06, ex_mh_pav_bstatue_07 and 9 more | disable, enable | 1: global | - | - |
| fab_attack_enable2 | mournhold (tribunal) | runs | 1 door; placed 1 (Tribunal 1) | ex_mh_pav_ladder_01 | disable, enable, getjournalindex | 1: getjournalindex | - | - |
| fab_attack_helseth | mournhold (tribunal) | runs | 1 NPC; placed 3 (Tribunal 3) | guard_helseth_attack | getdistance, gethealth, getjournalindex, journal, say, saydone | 7: getdistance, gethealth, getjournalindex, global, local, saydone | - | - |
| fab_attack_highord | mournhold (tribunal) | runs | 1 NPC; placed 3 (Tribunal 3) | guard_highord_attack | getdistance, getjournalindex, journal, say, saydone | 6: getdistance, getjournalindex, global, local, saydone | - | - |
| fab_cent_attack | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1) | fabricant_hulking_c_l | cellchanged, sethealth, startcombat | 3: cellchanged, local, other script | - | - |
| fab_cent_fight_die | mournhold (tribunal) | runs | 2 creature; placed 9 (Tribunal 9) | fabricant_hulking_c, fabricant_verminous_c | cellchanged, sethealth | 2: cellchanged, other script | - | - |
| fab_cent_fight_watch | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | fab_cent_fight_watcher | cellchanged, getdistance, journal, menumode, placeitem | 7: cellchanged, getdistance, local, menumode | - | - |
| floatAboveStartHeight | mournhold (tribunal) | runs | 1 container; placed 9 (Tribunal 9) | crate_01_float1 | getangle, getpos, getsecondspassed, getwaterlevel, menumode, random, setangle, setpos | 8: local, menumode | - | - |
| Gaenor_bScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 1 dialogue results | gaenor_b | disable, enable, forcegreeting, getdisabled, getdistance, getjournalindex, journal, menumode, ondeath | 9: getdisabled, getdistance, getjournalindex, local, menumode, ondeath | - | - |
| GaenorScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 20 dialogue results | gaenor | cast, disable, forcegreeting, getchameleon, getjournalindex, journal, menumode, ondeath, stopscript | 8: getchameleon, getjournalindex, local, menumode, ondeath | - | - |
| galmsScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 11 dialogue results | galms seles | random | - | - | - |
| GavisScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 2 dialogue results | gavis velas | disable, enable, forcegreeting, getdeadcount, getdisabled, getdistance, getjournalindex, getsecondspassed, journal, lock, ondeath, playsound, unlock | 15: getdeadcount, getdisabled, getdistance, getjournalindex, local, ondeath | - | - |
| goblinchiefScript1 | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1) | goblin_warchief1 | getdeadcount, journal, ondeath | 3: getdeadcount, global, ondeath | - | - |
| goblinchiefScript2 | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1) | goblin_warchief2 | getdeadcount, journal, ondeath | 3: getdeadcount, global, ondeath | - | - |
| helsAssScript | mournhold (tribunal) | runs | 3 NPC; placed 3 (Tribunal 3) | hels_assassin1, hels_assassin2, hels_assassin3 | disable, enable, getdisabled, getjournalindex, journal, menumode, ondeath | 9: getdisabled, getjournalindex, global, menumode, ondeath | - | - |
| helsdoorScript | mournhold (tribunal) | runs | 1 door; placed 1 (Tribunal 1) | in_mh_door_02_hels_uni | activate, getjournalindex, messagebox, onactivate, playsound | 3: getjournalindex, local, onactivate | - | - |
| helsethScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 16 dialogue results | king hlaalu helseth | disable, enable, getdisabled, gethealth, getjournalindex, setalarm, setfight, startcombat | 10: getdisabled, gethealth, getjournalindex, global, local | - | - |
| HessionScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 10 dialogue results | hession | cellchanged, lock, menumode, unlock | 7: cellchanged, global, local, menumode | - | - |
| highPocketsScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 12 dialogue results | high_pockets | disable, ondeath, removeitem | 4: local, ondeath | - | - |
| holmarScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 5 dialogue results | holmar | aiwander, disable, getdeadcount, getfatigue, gethealth, getjournalindex, getsecondspassed, journal, menumode, ondeath, setfatigue, setfight, stopcombat | 23: getdeadcount, getfatigue, gethealth, getjournalindex, local, menumode, ondeath | - | - |
| IgnatiusBBot2Script | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | script_ignbbot2 | disable, enable, getjournalindex, startcombat | 1: getjournalindex | - | - |
| IgnatiusScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 22 dialogue results | ignatius_flaccus | disable, enable, forcegreeting, getdeadcount, menumode | 10: getdeadcount, local, menumode, other script | - | - |
| IgnatiusScript2 | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 4 dialogue results | ignatius_flaccus2 | getdeadcount, menumode | 10: getdeadcount, local, menumode | - | - |
| IlnoriScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 4 dialogue results | ilnori_faustus | cellchanged, disable, getdeadcount | 5: cellchanged, getdeadcount, local | - | - |
| Irano_note | mournhold (tribunal) | runs | 1 book; placed 1 (Tribunal 1) | bk_irano_note | activate, disable, enable, getdisabled, getjournalindex, journal, onactivate | 6: getdisabled, getjournalindex, local, onactivate | - | - |
| JournalistPals | mournhold (tribunal) | runs | 3 NPC; placed 3 (Tribunal 3); speaker of 6 dialogue results | feranos hlando, sendel tedas, veros nerethi | getattacked, setdisposition, setfight, startcombat | 1: getattacked | - | - |
| karrodDoorScript | mournhold (tribunal) | runs | 2 door; placed 2 (Tribunal 2) | in_mh_door_02_throne1, in_mh_door_02_throne2 | activate, messagebox, onactivate | 3: global, onactivate | - | - |
| karrodfightstopScript | mournhold (tribunal) | runs | 5 NPC; placed 5 (Tribunal 5); speaker of 56 dialogue results | diradeni farano, drusus gratus, evo othreloth, ivulen irano, tienius delitian | aiwander, getjournalindex, setalarm, setfight, setflee, startcombat, stopcombat | 19: getjournalindex, global, local | - | - |
| karrodScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 3 dialogue results | karrod | addspell, forcegreeting, getfatigue, gethealth, getjournalindex, menumode, modblock, modfatigue, modhealth, modmediumarmor, modshortblade, modspeed, modstrength, placeatpc, removespell, resurrect, setdisposition, setfatigue, setfight, setflee, sethealth, startcombat, startscript, stopcombat | 25: getfatigue, gethealth, getjournalindex, global, local, menumode | - | - |
| Mercenary_Calvus | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 11 dialogue results | calvus horatius | aiwander, forcegreeting, getdistance, gethealth, getjournalindex, getsecondspassed, journal, menumode, ondeath, say, stopscript | 18: getdistance, gethealth, getjournalindex, global, local, menumode, ondeath | - | - |
| MerynScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 26 dialogue results | meryn othralas | getjournalindex, getsecondspassed, journal, menumode, messagebox | 4: getjournalindex, local, menumode | - | - |
| MHCityGates | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | ex_mh_city_gate | messagebox, onactivate | 1: onactivate | - | - |
| mitanneScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1) | mitanne limax | aifollow, aitravel, aiwander, getaipackagedone, getdistance, sethello | 13: getaipackagedone, getdistance, global, local | - | - |
| MuseumAurielBow | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | ebony_bow_auriel_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumAurielShield | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | ebony_shield_auriel_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumBiPolarBlade | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | bipolar blade_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumBitterMercy | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | spear_mercy_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumBootsApostle | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | boots_apostle_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumBootsBlinding | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | boots of blinding speed_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumBootsTenPace | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | tenpaceboots_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumBowShadows | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | longbow_shadows_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumChrysamere | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | claymore_chrysamere_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumDaggerFang | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | dagger_fang_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumDagSym | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | glass dagger_symmachus_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumDragonBone | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | dragonbone_cuirass_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumEbonyMail | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | ebon_plate_cuirass_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumEleidonsward | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | towershield_eleidon_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumGoldbrand | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | katana_goldbrand_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumHelmBearclaw | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | helm_bearclaw_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumHelmBloodworm | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | bloodworm_helm_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumIceblade | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | claymore_iceblade_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumLordsMail | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | lords_cuirass_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumMaceMolagBal | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | mace of molag bal_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumMaceSlurring | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | mace of slurring_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumRingPhynaster | mournhold (tribunal) | runs | 1 clothing; placed 1 (Tribunal 1) | ring_phynaster_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumRingVampiric | mournhold (tribunal) | runs | 1 clothing; placed 1 (Tribunal 1) | ring_vampiric_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumRingWarlock | mournhold (tribunal) | runs | 1 clothing; placed 1 (Tribunal 1) | ring_warlock_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumRobeLich | mournhold (tribunal) | runs | 1 clothing; placed 1 (Tribunal 1) | robe_lich_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumSaviorsHide | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | cuirass_savior_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 102 dialogue results | torasa aram | addtopic, getitemcount, stopscript | 64: getitemcount, local | - | - |
| MuseumSkullCrusher | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | warhammer_crusher_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumSpellBreaker | mournhold (tribunal) | runs | 1 armour; placed 1 (Tribunal 1) | spell_breaker_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumStaffHasedoki | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | staff_hasedoki_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumStaffMagnus | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | staff_magnus_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumUmbraSword | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | longsword_umbra_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| MuseumVelothJudgment | mournhold (tribunal) | runs | 1 WEAP; placed 1 (Tribunal 1) | daedric warhammer_ttgd_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | - |
| NarisaAdus | mournhold (tribunal) | runs | 2 NPC; placed 1 (Tribunal 1); speaker of 11 dialogue results | narisa adus, narissa adus | - | 1: global, local | - | - |
| OvisScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 2 dialogue results | ovis velas | disable, enable, forcegreeting, getdistance, getjournalindex, getsecondspassed, journal, menumode, ondeath, playsound, setdisposition, setfight, startcombat, stopscript | 13: getdistance, getjournalindex, local, menumode, ondeath, other script | - | - |
| passageScript | mournhold (tribunal) | runs | 1 activator, 1 door; placed 4 (Tribunal 4) | act_black_load03, door_load_darkness00 | activate, getbuttonpressed, messagebox, onactivate | 5: local, onactivate | - | - |
| Plague_Gedna | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1); speaker of 2 dialogue results | lich_relvel | forcegreeting, getdistance, getjournalindex, getstat, journal, menumode, modhealth, ondeath | 6: getdistance, getjournalindex, local, menumode, ondeath | - | - |
| PlagueAthelyn | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 3 dialogue results | athelyn malas | disable, enable, getdisabled, getjournalindex, removespell | 8: getdisabled, getjournalindex, local | - | - |
| PlagueHallRat1 | mournhold (tribunal) | runs | 2 creature; placed 7 (Tribunal 7) | rat_plague_hall1, rat_plague_hall1a | disable, enable, getdisabled, getjournalindex, ondeath | 7: getdisabled, getjournalindex, ondeath | - | - |
| PlagueHallRat2 | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1) | rat_plague_hall2 | disable, enable, getdisabled, getjournalindex | 6: getdisabled, getjournalindex | - | - |
| PlagueOrdBasement | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1) | ordinator_mh_tbasement | disable, enable, getdeadcount, getdisabled, getjournalindex, modcurrentfatigue, setfatigue, stopscript | 11: getdeadcount, getdisabled, getjournalindex, local | - | - |
| PlagueOrdHall | mournhold (tribunal) | runs | 1 NPC; placed 2 (Tribunal 2) | ordinator_mh_th_uni | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| PlagueRat1 | mournhold (tribunal) | runs | 1 creature; placed 15 (Tribunal 15) | rat_plague | disable, enable, getdisabled, getjournalindex | 6: getdisabled, getjournalindex | - | - |
| PlagueRock1 | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_plague_rock1 | getsecondspassed, moveworld, playloopsound3d, setpos, stopscript, stopsound | 4: global, local | - | - |
| PlagueRock2 | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_plague_rock2 | getsecondspassed, moveworld, playloopsound3d, setpos, stopscript, stopsound | 4: global, local | - | - |
| PlagueRock3 | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_plague_rock3 | getjournalindex, getsecondspassed, getstandingpc, journal, menumode, move, playsound3d, setpos | 6: getjournalindex, getstandingpc, local, menumode | - | - |
| PlagueStart | mournhold (tribunal) | runs | 1 door; placed 1 (Tribunal 1) | in_db_door_oval_relvel | activate, getlocked, onactivate | 3: getlocked, local, onactivate | - | - |
| PlagueWarning | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_plague_starter | getdistance, messagebox | 2: getdistance, local | - | - |
| playScript | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | script_playscript | activate, disableplayercontrols, enableplayercontrols, getbuttonpressed, getdistance, getjournalindex, getsecondspassed, journal, menumode, messagebox, playsound, say, saydone | 90: getdistance, getjournalindex, local, menumode, saydone | - | - |
| powerboxScript | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_dwe_powerbox00 | enable, getbuttonpressed, getitemcount, journal, messagebox, onactivate, removeitem | 7: getitemcount, local, onactivate | - | - |
| profaneScript | mournhold (tribunal) | runs | 1 creature; placed 5 (Tribunal 5) | lich_profane_unique | disable, enable, getdeadcount, getdisabled, getjournalindex, journal, ondeath | 7: getdeadcount, getdisabled, getjournalindex, local, ondeath | - | - |
| projectileMine | mournhold (tribunal) | runs | 1 activator; placed 3 (Tribunal 3) | prox_proj_mine | getangle, getdistance, getpcsneaking, getpos, getsecondspassed, getsneak, menumode, placeitem, random | 7: getpcsneaking, local, menumode | - | - |
| proximityMine | mournhold (tribunal) | runs | 1 activator; placed 11 (Tribunal 11) | misc_dwrv_prox_mine | cast, getdistance, getpcsneaking, getsecondspassed, getsneak, menumode, random | 12: getpcsneaking, local, menumode | - | - |
| radacScript | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1); speaker of 3 dialogue results | dwarven ghost_radac | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| raiseWaterToOpen | mournhold (tribunal) | runs | 2 door; placed 2 (Tribunal 2) | ex_mh_swr_trapdr_blkd, in_m_sewer_trapdoor_01_blkd | activate, getwaterlevel, messagebox, onactivate | 3: local, onactivate | - | - |
| replenishammoShock | mournhold (tribunal) | runs | 1 creature; placed 2 (Tribunal 2) | centurion_projectile_c | additem, getitemcount, menumode, ondeath | 4: getitemcount, local, menumode, ondeath | - | - |
| rerlas | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 11 dialogue results | rerlas mon | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| rockslide | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_rockslide01 | disable, getdisabled, getjournalindex, getpccell, getsecondspassed, playgroup, playsound | 6: getdisabled, getjournalindex, getpccell, local | - | - |
| SadriDoor | mournhold (tribunal) | runs | 1 door; placed 1 (Tribunal 1) | ex_mh_sewer_trapdoor_sadri | activate, getjournalindex, journal, onactivate | 2: getjournalindex, onactivate | - | - |
| SadriFight | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 1 dialogue results | golena sadri_a | additem, disable, forcegreeting, getdistance, getitemcount, getparalysis, journal, menumode, ondeath, removeitem | 10: getdistance, getitemcount, getparalysis, local, menumode, ondeath | - | - |
| SadriTadera | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1) | tadera andules | activate, getdeadcount, getjournalindex, journal, onactivate | 4: getdeadcount, getjournalindex, local, onactivate | - | - |
| SalasDead | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 10 dialogue results | salas valor | getjournalindex, journal, ondeath | 2: getjournalindex, ondeath | - | - |
| Shunari_Plague | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 7 dialogue results | shunari eye-fly | disable, enable, getcommondisease, getdeadcount, getdisabled, getjournalindex, journal, moddisposition, positioncell | 11: getcommondisease, getdeadcount, getdisabled, getjournalindex, local | - | - |
| Sotha_Alma | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1) | almalexia_warrior | disable, disableplayercontrols, enable, enableplayercontrols, getdeadcount, getdistance, getjournalindex, getsecondspassed, journal, menumode, ondeath, playsound, say, saydone, setfight, sethealth, stopcombat | 20: getdeadcount, getdistance, getjournalindex, local, menumode, ondeath, other script, saydone | - | - |
| sotha_machine1 | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_sotha_monster1 | getsecondspassed, getstandingpc, loopgroup, onactivate, placeitemcell, playgroup, playsound | 19: getstandingpc, local, onactivate, other script | - | - |
| sotha_machine2 | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_sotha_monster2 | onactivate, playgroup, playsound | 5: local, onactivate, other script | - | - |
| Sotha_SothaSil | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | in_sotha_sil00 | changeweather, getjournalindex, journal, menumode, messagebox, modregion, onactivate | 5: getjournalindex, local, menumode, onactivate | - | - |
| SothaHotOil | mournhold (tribunal) | runs | 1 activator; placed 20 (Tribunal 20) | act_hot_oil_512 | cellchanged, getsoundplaying, hurtstandingactor, menumode, playloopsound3dvp | 3: cellchanged, getsoundplaying, menumode | - | - |
| SothaImperfect | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1) | imperfect | disable, getdistance, getsecondspassed, playgroup, playsound, setfight | 4: getdistance, local | - | - |
| SothaImperfectDoor | mournhold (tribunal) | runs | 1 door; placed 1 (Tribunal 1) | door_sotha_imp_door | activate, getdeadcount, messagebox, onactivate | 2: getdeadcount, onactivate | - | - |
| SothaLever1 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever1a, act_sotha_lever1b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| SothaLever10 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever10a, act_sotha_lever10b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| SothaLever11 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever11a, act_sotha_lever11b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| SothaLever2 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever2a, act_sotha_lever2b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| SothaLever3 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever3a, act_sotha_lever3b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| SothaLever4 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever4a, act_sotha_lever4b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| SothaLever5 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever5a, act_sotha_lever5b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| SothaLever6 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever6a, act_sotha_lever6b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| SothaLever8 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever8a, act_sotha_lever8b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| SothaLever9 | mournhold (tribunal) | runs | 2 activator; placed 2 (Tribunal 2) | act_sotha_lever9a, act_sotha_lever9b | onactivate, playgroup | 4: local, onactivate, other script | - | - |
| sothalightScript | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_sotha_red00 | disable, enable, getdisabled | 12: getdisabled, other script | - | - |
| SothaOilLever | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_sotha_lever_bridge | getstrength, messagebox, onactivate, playgroup, playsound | 5: getstrength, local, onactivate, other script | - | - |
| sothasteam1Script | mournhold (tribunal) | runs | 1 activator; placed 2 (Tribunal 2) | act_sotha_steam00 | disable, enable, getdisabled, playgroup | 3: getdisabled, other script | - | - |
| sothasteam2Script | mournhold (tribunal) | runs | 1 activator; placed 2 (Tribunal 2) | act_sotha_steam10 | disable, enable, getdisabled, playgroup | 3: getdisabled, other script | - | - |
| Sound_Dwemer_Fan | mournhold (tribunal) | runs | 1 activator; placed 8 (Tribunal 8) | act_dwe_fan00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_MournEnv | mournhold (tribunal) | runs | 1 activator; placed 39 (Tribunal 39) | sound_mournenv1 | cellchanged, getsoundplaying, playloopsound3dvp | 9: cellchanged, getsoundplaying, global | - | - |
| Sound_MournFount | mournhold (tribunal) | runs | 1 activator; placed 6 (Tribunal 6) | sound_mournspray | cellchanged, disable, getdisabled, getsoundplaying, playloopsound3dvp | 5: cellchanged, getdisabled, getsoundplaying, global | - | - |
| Sound_MournTempleAm | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | sound_temple | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Power_Thrum | mournhold (tribunal) | runs | 2 activator; placed 5 (Tribunal 5) | act_dwe_gyro00, sound_power_hum | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_Rock_Crumble | mournhold (tribunal) | runs | 1 activator; placed 15 (Tribunal 15) | sound_rocks00 | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_SothaAmbient | mournhold (tribunal) | runs | 1 activator; placed 20 (Tribunal 20) | sound_sotha_amb | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_SothaGears | mournhold (tribunal) | runs | 2 activator; placed 61 (Tribunal 61) | act_sotha_clockwork, sound_sotha_gears | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_SothaLab | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | sound_sotha_lab | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| Sound_SothaRoll | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | sound_sotha_roll | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| SpellCast | mournhold (tribunal) | runs | 5 activator; placed 5 (Tribunal 5) | column_cast, column_cast2, column_cast3, column_cast4, column_cast5 | cast | 2: local | - | - |
| tarenScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 5 dialogue results | taren andoren | aifollow, aitravel, clearforcesneak, disable, enable, forcegreeting, forcesneak, getaipackagedone, getattacked, getdeadcount, getdistance, gethealth, getjournalindex, getsecondspassed, journal, menumode, messagebox, ondeath, setdisposition, setfight, startcombat | 42: getaipackagedone, getattacked, getdeadcount, getdistance, gethealth, getjournalindex, local, menumode, ondeath | - | - |
| ThendasTravel | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 9 dialogue results | arnsa thendas | aitravel, getaipackagedone, getsecondspassed, random | 18: getaipackagedone, local | - | - |
| Therdon2Script | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 1 dialogue results | therdon2 | disable, enable, getdeadcount | 4: getdeadcount, local, other script | - | - |
| TherdonScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 3 dialogue results | therdon | disable | 2: local | - | - |
| ThrudScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 8 dialogue results | thrud | aiwander, cellchanged, disable, getdeadcount, getjournalindex, ondeath | 11: cellchanged, getdeadcount, getjournalindex, local, ondeath | - | - |
| torch_lever | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_torch_lever_uni | gethealth, getsecondspassed, getwaterlevel, menumode, messagebox, modwaterlevel, onactivate, playgroup, playsound, sethealth, setwaterlevel | 10: gethealth, local, menumode, onactivate | - | - |
| tr_weathlev1 | mournhold (tribunal) | runs | 3 activator; placed 3 (Tribunal 3) | act_dwe_lever_a, act_dwe_lever_b, act_dwe_lever_c | getjournalindex, messagebox, onactivate, playgroup | 6: getjournalindex, local, onactivate, other script | - | - |
| tr_weathmachine | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | act_dwe_weather00 | changeweather, getangle, getsecondspassed, journal, menumode, modregion, playsound, setangle | 35: local, menumode | - | - |
| treedeadScript | mournhold (tribunal) | runs | 2 activator; placed 136 (Tribunal 136) | act_flora_treedead_mh_01, act_flora_treedead_mh_02 | disable, enable, getdisabled | 4: getdisabled, global, local | - | - |
| treeliveScript | mournhold (tribunal) | runs | 2 activator; placed 136 (Tribunal 136) | act_flora_tree_mh_01, act_flora_tree_mh_02 | disable, enable, getdisabled | 4: getdisabled, global, local | - | - |
| TribEnd | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | azura spirit_trib | changeweather, disable, disableplayercontrols, enable, enableplayercontrols, getdeadcount, getdisabled, getdistance, getjournalindex, getsecondspassed, journal, menumode, modregion, playgroup, say, saydone | 33: getdeadcount, getdisabled, getdistance, getjournalindex, local, menumode, saydone | - | - |
| trigger_spells | mournhold (tribunal) | runs | 1 activator; placed 1 (Tribunal 1) | shrine_trigger | getdistance | 1: getdistance | - | - |
| VarisDead | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 13 dialogue results | trels varis | getjournalindex, journal, menumode, ondeath | 3: getjournalindex, menumode, ondeath | - | - |
| VarninerGhost | mournhold (tribunal) | runs | 1 creature; placed 1 (Tribunal 1); speaker of 3 dialogue results | ancestor_ghost_variner | cellchanged, disable, enable, getdisabled, getjournalindex, journal, ondeath | 13: cellchanged, getdisabled, getjournalindex, local, ondeath | - | - |
| velnyaWalkScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 2 dialogue results | velyna seran | aitravel, aiwander, disable, getaipackagedone, getjournalindex, journal, menumode, ondeath | 17: getaipackagedone, getjournalindex, local, menumode, ondeath, other script | - | - |
| WarlordOren | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 20 dialogue results | dovor oren | activate, getjournalindex, journal, onactivate, ondeath | 5: getjournalindex, onactivate, ondeath | - | - |
| waterstate_torchdisable | mournhold (tribunal) | runs | 3 light; placed 16 (Tribunal 16) | light_com_torch_01_uni, light_logpile_uni, light_tikitorch00_uni | disable, enable, getpos, getwaterlevel | 4: getwaterlevel, local | - | - |
| waterstate_torchenable | mournhold (tribunal) | runs | 1 activator, 2 light; placed 16 (Tribunal 16) | active_tikitorch_uni, light_com_torch_burnedout_uni, light_logpile_burnedout | disable, enable, getpos, getwaterlevel | 4: getwaterlevel, local | - | - |
| weatherpowerScript | mournhold (tribunal) | runs | 1 item; placed 1 (Tribunal 1) | misc_dwrv_weather2 | disable, messagebox, onactivate | 4: local, onactivate, other script | - | - |
| WritAlen | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 4 dialogue results | bedal alen | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| WritBerano | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 4 dialogue results | forven berano | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| WritHloggar | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1); speaker of 3 dialogue results | hloggar the bloody | cellchanged, getjournalindex, getpccrimelevel, journal, menumode, ondeath | 5: cellchanged, getjournalindex, local, menumode, ondeath | - | - |
| yarnarScript | mournhold (tribunal) | runs | 1 NPC; placed 1 (Tribunal 1) | yarnar | journal, ondeath | 2: local, ondeath | - | - |
| bladeScript | records not placed | runs | 1 WEAP | nerevarblade_01_flame | additem, getitemcount, getweapondrawn, removeitem | 11: getitemcount, getweapondrawn, local | - | runs while the player carries one of its items |
| CharGen_ring_keley | records not placed | runs | 1 clothing; held by placed containers and actors 1 | ring_keley | enablemagicmenu, getbuttonpressed, menumode, messagebox, xbox | 11: getbuttonpressed, global, local, menumode, xbox | - | runs on the items placed containers and actors hold, while their area is loaded |
| db_assassinScript | records not placed | runs | 5 NPC; placed by scripts (5 records) | db_assassin1, db_assassin1b, db_assassin2, db_assassin3, db_assassin4 | getdistance, getitemcount, getjournalindex, journal, menumode, ondeath, setfight, setflee, startcombat | 8: getdistance, getitemcount, getjournalindex, local, menumode, ondeath | - | runs on the object a script places |
| dbcontractScript | records not placed | runs | 1 book; held by placed containers and actors 1 | bk_dbcontract | getitemcount, journal | 2: getitemcount, local | - | runs on the items placed containers and actors hold, while their area is loaded |
| DrothDagger | records not placed | runs | 1 WEAP; held by placed containers and actors 1 | silver dagger_droth_unique | getitemcount, journal | 2: getitemcount, global | - | runs on the items placed containers and actors hold, while their area is loaded |
| karrodguardScript | records not placed | runs | 1 NPC; placed by scripts (1 records) | royal guard_karrod | cellchanged, disable, forcegreeting, getsecondspassed, menumode | 7: cellchanged, global, local, menumode | - | runs on the object a script places |
| mazedbandEnd_Script | records not placed | runs | 1 clothing; held by placed containers and actors 1 | mazed_band_end | getbuttonpressed, getjournalindex, messagebox, playsound, positioncell | 17: getjournalindex, local | - | runs on the items placed containers and actors hold, while their area is loaded |
| mazedbandScript | records not placed | runs | 1 clothing; held by placed containers and actors 1 | mazed_band | getitemcount, journal, menumode | 4: getitemcount, local, menumode | - | runs on the items placed containers and actors hold, while their area is loaded |
| MuseumStendarHammer | records not placed | runs | 1 WEAP | stendar_hammer_unique_x | activate, additem, disable, enable, onactivate, removeitem | 3: onactivate, other script | - | runs while the player carries one of its items |
| packrat | records not placed | runs | 1 creature; placed by scripts (1 records); speaker of 3 dialogue results | rat_pack_rerlas | getjournalindex | 1: getjournalindex | - | runs on the object a script places |
| replenishammo | records not placed | runs | 1 creature; levelled lists 3 | centurion_projectile | additem, getitemcount, menumode, ondeath | 4: getitemcount, local, menumode, ondeath | - | runs on the actor a levelled list gives |
| trapProjScript | records not placed | runs | 1 activator; placed by scripts (1 records) | trapprojectile | disable, explodespell, getdistance, getpos, getsecondspassed, getsquareroot, menumode, setdelete, setpos | 16: local, menumode | - | runs on the object a script places |
| AzuraEnd | red mountain region | runs | 1 activator; placed 1 (Morrowind 1) | azura spirit | disable, disableplayercontrols, enable, enableplayercontrols, getdisabled, getdistance, getjournalindex, getsecondspassed, journal, menumode, playbink, playgroup | 15: getdisabled, getdistance, getjournalindex, local, menumode | - | - |

### Bloodmoon

| Script | Area | State | Referenced by | Records | Functions | Conditions | Follows OpenMW's fix | Why |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Float | ascadian isles region | runs | 11 activator, 12 container, 1 light, 1 item; placed 742 (Morrowind 725, Tribunal 7, Bloodmoon 10) | a_ex_de_oar, a_ex_de_rowboat, a_ex_de_rowboat_colony, ex_com_bottle_11_float, ex_gondola_01, ex_scrapwood01 and 19 more | getsecondspassed, menumode, rotate, setatstart | 4: local, menumode | - | - |
| SignRotate | ascadian isles region | runs | 30 activator, 14 light, 2 item; placed 466 (Morrowind 455, Tribunal 11) | a_furn_de_chair_3, a_furn_de_table_6, a_furn_de_table_8, active_sign_c_arms_caldera, active_sign_c_clothing_01, active_sign_c_clothing_falanaam and 40 more | dontsaveobject, getdistance, getsecondspassed, menumode, rotate, setatstart | 5: getdistance, local, menumode | dontsaveobject-ignored | - |
| treboniusScript | ascadian isles region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 18 dialogue results | trebonius artorius | getjournalindex, getpccell, journal, ondeath, pcraiserank | 5: getjournalindex, getpccell, global, local, ondeath | - | - |
| CavernIncarnateDoor | ashlands region | runs | 1 door; placed 1 (Morrowind 1) | in_ci_door_01 | activate, disableplayercontrols, enableplayercontrols, getjournalindex, getsecondspassed, onactivate, say | 12: getjournalindex, global, local, onactivate | - | - |
| OutsideBanner | azura's coast region | runs | 80 activator; placed 134 (Morrowind 130, Bloodmoon 4) | act_banner_ald_velothi, act_banner_gnaar_mok, act_banner_hla_oad, act_banner_khuul, act_banner_sadrith_mora, act_banner_tel_aruhn and 74 more | getcurrentweather, loopgroup, menumode, playgroup, random | 7: getcurrentweather, local, menumode | - | - |
| fortloreboozeCarn1Script | brodir grove region | runs | 1 NPC; placed 1 (Bloodmoon 1) | bm_imperial guard_carn1 | disable, enable, getdisabled, getjournalindex | 8: getdisabled, getjournalindex, global | - | - |
| stoneErlendrScript | brodir grove region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_erlendr | cast, getjournalindex, menumode, messagebox, onactivate | 4: getjournalindex, menumode, onactivate | - | - |
| stoneHunroorScript | brodir grove region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_hunroor | cast, getjournalindex, menumode, messagebox, onactivate | 4: getjournalindex, menumode, onactivate | - | - |
| stoneNikulasScript | brodir grove region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_nikulas | cast, getjournalindex, menumode, messagebox, onactivate | 4: getjournalindex, menumode, onactivate | - | - |
| stoneUlfgarScript | brodir grove region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_ulfgar | cast, disable, enable, getjournalindex, menumode, messagebox, onactivate | 6: getjournalindex, menumode, onactivate | - | - |
| UlfgarGhostScript | brodir grove region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | ulfgar_ghost | addspell, disable, enable, forcegreeting, getdisabled, getdistance, getjournalindex, getpos, getsecondspassed, menumode, placeitem | 16: getdisabled, getdistance, getjournalindex, local, menumode | - | - |
| UlfgarScript | brodir grove region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 11 dialogue results | ulfgar the unending | forcegreeting, gethealth, getjournalindex, journal | 4: gethealth, getjournalindex, local | - | - |
| ColonyAssassin | dialogue only | runs | started by 2 dialogue results | - | additem, aitravel, aiwander, enable, forcerun, getaipackagedone, getdeadcount, getdistance, getjournalindex, getsecondspassed, getstandingpc, gettarget, getweapondrawn, hasitemequipped, journal, menumode, ondeath, position, positioncell, setagility, setfight, setwillpower, startcombat, stopcombat, stopscript | 53: getaipackagedone, getdeadcount, getdistance, getjournalindex, getstandingpc, gettarget, getweapondrawn, global, hasitemequipped, local, menumode, ondeath | - | - |
| ColonyEstateTimer | dialogue only | runs | started by 3 dialogue results | - | getpccell, journal, stopscript | 20: getpccell, global, local, other script | - | - |
| ColonyGuards | dialogue only | runs | started by 6 dialogue results | - | disable, enable, getjournalindex, stopscript | 6: getjournalindex, global, local | - | - |
| ColonyNordAxe | dialogue only | runs | started by 1 dialogue results | - | getdeadcount, getitemcount, getjournalindex, journal, stopscript | 5: getdeadcount, getitemcount, getjournalindex | - | - |
| ColonyNordEquip | dialogue only | runs | started by 1 dialogue results | - | getjournalindex, journal | 6: getjournalindex, other script | - | - |
| ColonyReportTimer | dialogue only | runs | started by 1 dialogue results | - | getjournalindex, getpccell, getsecondspassed, journal, positioncell, random, stopscript | 17: getjournalindex, getpccell, global, local | - | - |
| ColonyRootTimer | dialogue only | runs | started by 2 dialogue results | - | getjournalindex, stopscript | 5: getjournalindex, global, local | - | - |
| ColonyServTimer | dialogue only | runs | started by 3 dialogue results | - | journal, stopscript | 15: global, local | - | - |
| ColonyTimer | dialogue only | runs | started by 3 dialogue results | - | aiwander, getdeadcount, getjournalindex, getpccell, getpcrank, journal, position, positioncell | 55: getdeadcount, getjournalindex, getpccell, getpcrank, global, local | - | - |
| CorprusBeastSafe | dialogue only | runs | started by 1 dialogue results | - | getdeadcount, getjournalindex, setdisposition, setfight, stopcombat, stopscript | 8: getdeadcount, getjournalindex | - | - |
| GlenmorilCaveTeleport | dialogue only | runs | started by 1 dialogue results | - | menumode, playsound, positioncell, stopscript | 1: menumode | - | - |
| IngmarTeleport | dialogue only | runs | started by 2 dialogue results | - | aiwander, getpccell, positioncell, stopscript | 1: getpccell | - | - |
| JeleenScript | dialogue only | runs | started by 1 dialogue results | - | additem, cellchanged, getjournalindex, sethealth, stopscript | 2: cellchanged, getjournalindex | - | - |
| RitualTransform | dialogue only | runs | started by 1 dialogue results | - | becomewerewolf, getdeadcount, getpos, getsecondspassed, journal, menumode, modfatigue, modhealth, placeitem, resurrect, startcombat | 7: getdeadcount, global, local, menumode | - | - |
| smugdeadScript | dialogue only | runs | started by 1 dialogue results | - | enable, getjournalindex, journal | 4: getjournalindex, global, local | - | - |
| aeslipScript | felsaad coast region | runs | 1 creature; placed 1 (Bloodmoon 1); speaker of 8 dialogue results | draugr_aesliip | forcegreeting, getdistance, getjournalindex, getsecondspassed, journal, ondeath | 11: getdistance, getjournalindex, global, local, ondeath | - | - |
| BMFrostDaedraScript | felsaad coast region | runs | 1 creature; placed 10 (Bloodmoon 10) | atronach_frost_bm | getjournalindex, journal, ondeath | 4: getjournalindex, global, local, ondeath | - | - |
| BrandrScript | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 3 dialogue results | brandr | getjournalindex, journal, ondeath | 2: getjournalindex, ondeath | - | - |
| caenScript | felsaad coast region | runs | 3 creature; placed 3 (Bloodmoon 3) | bm_wolf_caenlorn1, bm_wolf_caenlorn2, bm_wolf_caenlorn3 | aiwander, disable, getangle, getdeadcount, getpos, getsecondspassed, ondeath, placeitem | 6: getdeadcount, local, ondeath | - | - |
| ColonyAenar | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 20 dialogue results | aenar | setfight, startcombat | 3: global, local | - | - |
| ColonyCoventina | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1) | coventina celata | disable, enable, getdeadcount, getdisabled, getjournalindex, journal, ondeath, startcombat | 12: getdeadcount, getdisabled, getjournalindex, local, ondeath | - | - |
| ColonyGraring | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 5 dialogue results | graring | getdisabled, gethealth, getjournalindex, gettarget, journal, ondeath, setfight, startcombat | 10: getdisabled, gethealth, getjournalindex, gettarget, local, ondeath | - | - |
| ColonyHidar | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 12 dialogue results | hidar | setfight, startcombat | 3: global, local | - | - |
| deadhorkerScript | felsaad coast region | runs | 1 creature; placed 82 (Bloodmoon 82) | bm_horker_dead | disable, enable, getdisabled, getjournalindex | 6: getdisabled, getjournalindex | - | - |
| ErnaNoteScript | felsaad coast region | runs | 1 book; placed 1 (Bloodmoon 1) | sc_erna | activate, getjournalindex, journal, onactivate | 3: getjournalindex, local, onactivate | - | - |
| ErnaScript | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | erna the quiet | getjournalindex, journal, ondeath | 2: getjournalindex, ondeath | - | - |
| fjalddoorScript | felsaad coast region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_snowdoor5 | disable, getdisabled, getjournalindex | 2: getdisabled, getjournalindex | - | - |
| forcefieldScript | felsaad coast region | runs | 1 activator; placed 1 (Bloodmoon 1) | bm_aesliipforcefield | disable, getdistance, getjournalindex, getsecondspassed, loopgroup, setdelete | 8: getdistance, getjournalindex, local | - | - |
| glendoor2Script | felsaad coast region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_tombdoor4 | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| glendoorScript | felsaad coast region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_tombdoor3 | disable, getdisabled, getjournalindex | 2: getdisabled, getjournalindex | - | - |
| hunter3Script | felsaad coast region | runs | 1 NPC; placed 9 (Bloodmoon 9) | skaal_hunter2 | disable, enable, getdisabled, getjournalindex, ondeath | 5: getdisabled, getjournalindex, ondeath | - | - |
| hunterScript | felsaad coast region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_huntercentral | getdistance, getjournalindex, getsecondspassed, placeatme | 14: getjournalindex, global, local | - | - |
| korstScript | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 27 dialogue results | korst wind-eye | getspell | 1: getspell | - | - |
| LairDoor | felsaad coast region | runs | 2 door; placed 1 (Bloodmoon 1) | bm_ka_door_dark_udyr, ex_nord_door_lair | disable, enable, getjournalindex | 2: getjournalindex | - | - |
| lakefireScript | felsaad coast region | runs | 1 light; placed 1 (Bloodmoon 1) | act_bm_firelake00 | disable, enable, getdisabled, getjournalindex | 6: getdisabled, getjournalindex | - | - |
| LassnrScript | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 9 dialogue results | lassnr | getjournalindex, journal, ondeath | 2: getjournalindex, ondeath | - | - |
| rieklingsword | felsaad coast region | runs | 1 creature; placed 1 (Bloodmoon 1); levelled lists 20 | bm_riekling_mounted | additem, ondeath | 2: local, ondeath | - | - |
| rigmorDoorScript | felsaad coast region | runs | 1 door; placed 1 (Bloodmoon 1) | ex_s_door_rigmor2 | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| rigmorScript | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | rigmor halfhand | aitravel, aiwander, getaipackagedone, getdistance, getjournalindex, getpccell, getsecondspassed, menumode, ondeath, startcombat | 19: getaipackagedone, getdistance, getjournalindex, getpccell, local, menumode, ondeath | - | - |
| rignoteScript | felsaad coast region | runs | 1 book; placed 1 (Bloodmoon 1) | bk_bmtrial_unique | activate, disable, enable, getdisabled, getjournalindex, journal, onactivate | 8: getdisabled, getjournalindex, local, onactivate | - | - |
| ringviewScript | felsaad coast region | runs | 1 clothing; placed 1 (Bloodmoon 1) | bm_ring_view | disable, enable, getbuttonpressed, getdisabled, getjournalindex, messagebox, playbink | 19: getdisabled, getjournalindex, local | - | - |
| skaalaradoorScript | felsaad coast region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_snowdoor1 | disable, getdisabled, getjournalindex | 3: getdisabled, getjournalindex | - | - |
| skaaldoorSound | felsaad coast region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_attacksound | getjournalindex, menumode, playloopsound3d, stopsound | 5: getjournalindex, global, local, menumode | - | - |
| skaalGuardScript | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 1 dialogue results | skaal_guard2 | forcegreeting, getsecondspassed, menumode | 7: global, local, menumode | - | - |
| skaalwere1Script | felsaad coast region | runs | 2 NPC; placed 2 (Bloodmoon 2) | bm_werewolf_skaal1a3, bm_werewolf_skaal1e3 | becomewerewolf, disable, enable, getdisabled, getjournalindex, journal, ondeath, sethealth, startcombat | 9: getdisabled, getjournalindex, global, local, ondeath | - | - |
| skaalwere2Script | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1) | bm_werewolf_skaal1b3 | becomewerewolf, disable, enable, getdisabled, getjournalindex, journal, ondeath, sethealth, startcombat | 10: getdisabled, getjournalindex, global, local, ondeath | - | - |
| skaalwere3Script | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1) | bm_werewolf_skaal1c3 | becomewerewolf, disable, enable, getdisabled, getjournalindex, journal, ondeath, sethealth, startcombat | 10: getdisabled, getjournalindex, global, local, ondeath | - | - |
| skaalwere4Script | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1) | bm_werewolf_skaal1d3 | becomewerewolf, disable, enable, getdisabled, getjournalindex, journal, ondeath, sethealth, startcombat | 10: getdisabled, getjournalindex, global, local, ondeath | - | - |
| skaalwere5Script | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1) | bm_werewolf_skaal1f3 | becomewerewolf, disable, enable, getdisabled, getjournalindex, journal, ondeath, sethealth, startcombat | 10: getdisabled, getjournalindex, global, local, ondeath | - | - |
| skaalwere6Script | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1) | bm_werewolf_skaal1g3 | becomewerewolf, disable, enable, getdisabled, getjournalindex, journal, ondeath, sethealth, startcombat | 10: getdisabled, getjournalindex, global, local, ondeath | - | - |
| spiritBearScript | felsaad coast region | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_bear_spr_unique | disable, enable, getdisabled, getjournalindex, journal, moddisposition, ondeath | 10: getdisabled, getjournalindex, local, ondeath | - | - |
| stoneBeastsScript | felsaad coast region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_beast_01 | enable, getjournalindex, journal, messagebox, onactivate | 8: getjournalindex, global, local, onactivate | - | - |
| stoneeffect1Script | felsaad coast region | runs | 2 activator; placed 2 (Bloodmoon 2) | act_bm_sun_parts, active_bm_stonesound1 | getjournalindex, playsound | 2: getjournalindex, local | - | - |
| totemchestScript | felsaad coast region | runs | 1 container; placed 1 (Bloodmoon 1) | chest_clawfang_unique | activate, getitemcount, getjournalindex, journal, messagebox, onactivate, removeitem | 5: getitemcount, getjournalindex, global, onactivate | - | - |
| TymvaulScript | felsaad coast region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | tymvaul | disable, enable, getjournalindex, journal, ondeath | 5: getjournalindex, ondeath | - | - |
| UdyrfrykteDead | felsaad coast region | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_udyrfrykte | disable, enable, getjournalindex, journal, ondeath, startscript | 4: getjournalindex, ondeath | - | - |
| wereCeremonyScript | felsaad coast region | runs | 1 NPC; placed 10 (Bloodmoon 10) | werewolf_ceremony | becomewerewolf, disable, enable, getdisabled, getjournalindex, ondeath | 6: getdisabled, getjournalindex, local, ondeath | - | - |
| wereskaalScript | felsaad coast region | runs | 1 NPC; placed 2 (Bloodmoon 2) | bm_werewolf_skaal2a | addspell, becomewerewolf, disable, enable, getdeadcount, getdisabled, getjournalindex, journal, ondeath, position, startcombat | 9: getdeadcount, getdisabled, getjournalindex, global, local, ondeath | - | - |
| windbagScript | felsaad coast region | runs | 2 container; placed 1 (Bloodmoon 1) | bm_greedyman, bm_windbag | activate, disable, enable, getdisabled, getjournalindex, journal, onactivate, playsound | 7: getdisabled, getjournalindex, onactivate | - | - |
| windlightScript | felsaad coast region | runs | 1 light; placed 10 (Bloodmoon 10) | light_bm_tomb_wind | disable, getdisabled, getjournalindex | 3: getdisabled, getjournalindex | - | - |
| BloodmoonMain | global scripts | runs | started by hircine1Script | - | disablelevitation, disableteleporting, enablelevitation, enableteleporting, getinterior, getpccell | 5: getinterior, getpccell, local | - | - |
| bloodmoonScript | global scripts | runs | started by BMStartUpScript | - | getjournalindex, turnmoonred, turnmoonwhite | 6: getjournalindex, local | - | - |
| BMStartUpScript | global scripts | runs | start script | - | disable, getjournalindex, startscript, stopscript | 15: getjournalindex, global | - | - |
| dbFixScript | global scripts | runs | started by BMStartUpScript | - | cellchanged, getpccell | 4: cellchanged, getpccell, global, local | - | - |
| EndGame | global scripts | runs | started by DagothDoorDetector | - | changeweather, disable, enableteleporting, journal, modregion, modreputation, playgroup, sethealth, stopscript | - | - | - |
| MirisaTeleport | global scripts | runs | started by UdyrfrykteDead | - | aiwander, gethealth, getjournalindex, positioncell, stopscript | 2: gethealth, getjournalindex | - | - |
| plant2Script | global scripts | runs | started by plantScript | - | disable, enable, getdistance | 9: getdistance, global, local | - | - |
| VampireCheck | global scripts | runs | started by Main, VampTest, VampTest1, VampTest2, VampTest3, testPlayerStats | - | getpcsleep, getspell, messagebox, startscript, stopscript, wakeuppc | 19: getpcsleep, getspell, global, local | - | - |
| WereChangeScript | global scripts | runs | started by WereCheckScript | - | addspell, becomewerewolf, disable, disableplayercontrols, enable, enableplayercontrols, fadein, fadeout, getjournalindex, getpcinjail, getpctraveling, getsecondspassed, getwerewolfkills, iswerewolf, journal, menumode, messagebox, playbink, positioncell, removespell, setwerewolfacrobatics, startscript, stopscript, undowerewolf, wakeuppc | 52: getjournalindex, getpcinjail, getpctraveling, getwerewolfkills, global, iswerewolf, local, menumode | - | - |
| WereCheckScript | global scripts | runs | started by BMStartUpScript | - | getspell, startscript, stopscript | 10: getspell, global, local | - | - |
| werehungerScript | global scripts | runs | started by WereChange2Script, WereChangeScript | - | gethealth, iswerewolf, messagebox, modcurrenthealth | 7: global, iswerewolf, local | - | - |
| wildhuntStartScript | global scripts | runs | started by WereChange2Script, WereChangeScript; started by 1 dialogue results | - | disableplayercontrols, fadein, fadeout, getjournalindex, getpcsleep, getsecondspassed, iswerewolf, journal, placeatpc, positioncell, stopscript, wakeuppc | 18: getjournalindex, getpcsleep, iswerewolf, local | - | - |
| artoriaScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 14 dialogue results | gaea artoria | forcegreeting, getdistance, getjournalindex, ondeath, setfight, startcombat | 8: getdistance, getjournalindex, global, local, ondeath | - | - |
| bm_bloodskal_creatures | hirstaang forest region | runs | 4 creature; placed 5 (Bloodmoon 5); levelled lists 3 | bm skeleton champion gr, bm_draugr_bloodskal, bm_sk_champ_bloodskal01, bm_sk_champ_bloodskal02 | disable, enable, getjournalindex | 3: getjournalindex, local | - | - |
| bm_bloodskal_sword | hirstaang forest region | runs | 1 WEAP; placed 1 (Bloodmoon 1) | bm_nordic_silver_lgswd_bloodska | journal | 2: local | - | - |
| cariusgoneScript | hirstaang forest region | runs | 1 activator; placed 10 (Bloodmoon 10) | active_frostattack_unique | disable, enable, getdistance, getjournalindex, journal | 6: getdistance, getjournalindex, global, local | - | - |
| Colony_D_1_F | hirstaang forest region | runs | 14 activator; placed 37 (Bloodmoon 37) | colony flora_tree_bm_snow_01_s2, colony flora_tree_bm_snow_02_s2, colony flora_tree_bm_snow_04_s2, colony flora_tree_bm_snow_05_s2, colony terrain_rock_bm_19_s2, colony terrain_rock_bm_20_s2 and 8 more | disable, getdisabled | 2: getdisabled, global | - | - |
| Colony_D_1_I | hirstaang forest region | runs | 14 activator; placed 59 (Bloodmoon 59) | colony flora_tree_bm_snow_01_s1, colony flora_tree_bm_snow_02_s1, colony flora_tree_bm_snow_04_s1, colony flora_tree_bm_snow_05_s1, colony terrain_rock_bm_19_s1, colony terrain_rock_bm_20_s1 and 8 more | disable, getdisabled | 2: getdisabled, global | - | - |
| Colony_D_1_Mine | hirstaang forest region | runs | 2 activator; placed 5 (Bloodmoon 5) | ex_colony_const_house02_1, ex_colony_const_struc01_1 | disable, enable, getdisabled | 6: getdisabled, global | - | - |
| Colony_D_2_F | hirstaang forest region | runs | 10 activator; placed 31 (Bloodmoon 31) | colony flora_tree_bm_snow_01_s3, colony flora_tree_bm_snow_02_s3, colony flora_tree_bm_snow_04_s3, colony flora_tree_bm_snow_05_s3, colony terrain_rock_bm_59_s3, colony terrain_rock_bm_60_s3 and 4 more | disable, getdisabled | 2: getdisabled, global | - | - |
| Colony_D_3_F | hirstaang forest region | runs | 9 activator; placed 19 (Bloodmoon 19) | colony flora_tree_bm_snow_01_s4, colony flora_tree_bm_snow_02_s4, colony flora_tree_bm_snow_04_s4, colony flora_tree_bm_snow_05_s4, colony terrain_rock_bm_60_s4, colony terrain_rock_bm_61_s4 and 3 more | disable, getdisabled | 2: getdisabled, global | - | - |
| Colony_Door_Uryn | hirstaang forest region | runs | 1 door; placed 1 (Bloodmoon 1) | ex_colony_door03_1_uryn | disable, enable, getdisabled, getjournalindex, lock | 6: getdisabled, getjournalindex, global, local | - | - |
| Colony_E_1_F | hirstaang forest region | runs | 9 activator, 4 door; placed 14 (Bloodmoon 14) | a_furn_com_table_colony, ac_furn_rug_colony2, colony_smoke_1, colony_smoke_4_1, ex_colony_barn01_1, ex_colony_chimney01_1 and 7 more | disable, enable, getdisabled | 4: getdisabled, global | - | - |
| Colony_E_1_M | hirstaang forest region | runs | 6 activator; placed 7 (Bloodmoon 7) | ex_colony_const_barn01_1, ex_colony_const_brick01_1, ex_colony_const_brick02, ex_colony_const_house01_1, ex_colony_const_house03_1, flora_tree_bm_snow_05_1 | disable, enable, getdisabled | 7: getdisabled, global, local | - | - |
| Colony_E_1_Mine | hirstaang forest region | runs | 2 activator; placed 1 (Bloodmoon 1) | ex_colony_mine_entrance01, ex_colony_mine_entrance01_1 | disable, enable, getdisabled, stopscript | 4: getdisabled, global | - | - |
| Colony_E_2_F | hirstaang forest region | runs | 8 activator, 5 door; placed 12 (Bloodmoon 12) | colony_smoke_4_2, ex_colony_bar_inn01_2, ex_colony_barn02_2, ex_colony_chimney01_2, ex_colony_house01_2, ex_colony_house02_2 and 7 more | disable, enable, getdisabled | 4: getdisabled, global | - | - |
| Colony_E_2_M | hirstaang forest region | runs | 8 activator; placed 10 (Bloodmoon 10) | ex_colony_const_barn01_2, ex_colony_const_brick02_2, ex_colony_const_house01_2, ex_colony_const_house02_2, ex_colony_const_house03_2, ex_colony_const_struc01_2 and 2 more | disable, enable, getdisabled | 7: getdisabled, global, local | - | - |
| Colony_E_3_F | hirstaang forest region | runs | 8 activator, 4 door; placed 12 (Bloodmoon 12) | colony_smoke_4_3, ex_colony_chimney01_3, ex_colony_house01_3, ex_colony_house02_3, ex_colony_house03_3, ex_colony_house03b_3 and 6 more | disable, enable, getdisabled | 4: getdisabled, global | - | - |
| Colony_E_3_M | hirstaang forest region | runs | 8 activator; placed 10 (Bloodmoon 10) | ex_colony_const_brick01_3, ex_colony_const_brick02_3, ex_colony_const_house01_3, ex_colony_const_house02_3, ex_colony_const_house03_3, ex_colony_wall_01m_3 and 2 more | disable, enable, getdisabled | 7: getdisabled, global, local | - | - |
| Colony_E_4_F | hirstaang forest region | runs | 6 activator, 3 door; placed 12 (Bloodmoon 12) | colony_smoke_4_4, ex_colony_tower01_4, ex_colony_wall_01_4, ex_colony_wall_02_3, ex_colony_wall_02_4, ex_colony_wall_03_4 and 3 more | disable, enable, getdisabled | 4: getdisabled, global | - | - |
| Colony_E_4_M | hirstaang forest region | runs | 8 activator; placed 14 (Bloodmoon 14) | ex_colony_const_brick01_4, ex_colony_const_brick02-4, ex_colony_const_struc01_4, ex_colony_const_stud01_4, ex_colony_const_wood01_4, ex_colony_wall_01m_4 and 2 more | disable, enable, getdisabled | 7: getdisabled, global, local | - | - |
| Colony_E_Torch | hirstaang forest region | runs | 3 light; placed 3 (Bloodmoon 3) | colony_torch_1, colony_torch_2, colony_torch_3 | disable, enable, getdisabled, setdelete | 6: getdisabled, global | - | - |
| Colony_first_boat | hirstaang forest region | runs | 1 activator, 1 container; placed 4 (Bloodmoon 4) | a_ex_colonyboat, barrel_01_empty_co1 | disable, enable, getdisabled | 6: getdisabled, global, local | - | - |
| ColonyAldam | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 13 dialogue results | aldam berendus | aitravel, aiwander, disable, enable, getaipackagedone, getdisabled, getdistance, getitemcount, getjournalindex, getsecondspassed, menumode | 27: getaipackagedone, getdisabled, getdistance, getitemcount, getjournalindex, local, menumode | - | - |
| ColonyAlfbrand | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | alfbrand | disable, enable, forcegreeting, getdeadcount, getdisabled, getjournalindex, journal, ondeath, setfight, startcombat | 18: getdeadcount, getdisabled, getjournalindex, global, local, ondeath, other script | - | - |
| ColonyAssassinItems | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | colony_assassin_act | disable, enable, getdisabled, getjournalindex, stopscript | 8: getdisabled, getjournalindex | - | - |
| ColonyAudmund | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | audmund | disable, enable, forcegreeting, getdeadcount, getdisabled, getjournalindex, journal, ondeath, setfight, startcombat | 18: getdeadcount, getdisabled, getjournalindex, global, local, ondeath, other script | - | - |
| ColonyBaro | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 5 dialogue results | baro egnatius | disable, enable, getdisabled, getdistance, getjournalindex, getweapondrawn, getweapontype, hasitemequipped, journal, menumode, ondeath | 15: getdisabled, getdistance, getjournalindex, getweapondrawn, getweapontype, global, hasitemequipped, local, menumode, ondeath | - | - |
| ColonyBaroShip | hirstaang forest region | runs | 3 activator; placed 4 (Bloodmoon 4) | act_ex_de_ship_door_baro, ex_co_ship_baro, ex_co_ship_trapdoorb | disable, enable, getdisabled | 4: getdisabled | - | - |
| ColonyBryngrim | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | bryngrim | disable, enable, forcegreeting, getdeadcount, getdisabled, getjournalindex, journal, ondeath, setfight, startcombat | 18: getdeadcount, getdisabled, getjournalindex, global, local, ondeath, other script | - | - |
| ColonyCarnius | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 118 dialogue results | carnius magius | getdeadcount, getjournalindex, journal, ondeath | 8: getdeadcount, getjournalindex, local, ondeath, other script | - | - |
| ColonyChestMaryn | hirstaang forest region | runs | 1 container; placed 1 (Bloodmoon 1) | com_chest_02_maryn | activate, additem, disable, enable, getdisabled, getitemcount, getjournalindex, journal, onactivate | 14: getdisabled, getitemcount, getjournalindex, local, onactivate | - | - |
| ColonyConstans | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 15 dialogue results | constans atrius | disable, enable, getdisabled, getjournalindex | 9: getdisabled, getjournalindex, local | - | - |
| ColonyDock | hirstaang forest region | runs | 1 activator, 3 container; placed 6 (Bloodmoon 6) | ex_colony_pier01, barrel_01_cheapfood_co, barrel_02_cheapfood_co, crate_01_random_pos_co | disable, enable, getdisabled | 4: getdisabled, global | - | - |
| ColonyDralora | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 3 dialogue results | dralora favelnim | disable, enable, forcegreeting, getdisabled, getdistance, getjournalindex | 8: getdisabled, getdistance, getjournalindex, global, local | - | - |
| ColonyEquipBag | hirstaang forest region | runs | 2 container; placed 2 (Bloodmoon 2) | com_sack_01_colony, com_sack_02_colony | disable, enable, getdisabled, getjournalindex | 5: getdisabled, getjournalindex, global | - | - |
| ColonyFactor1_D | hirstaang forest region | runs | 4 activator; placed 8 (Bloodmoon 8) | colony flora_tree_bm_snow_05_f1, colony terrain_rock_bm_59_f1, colony terrain_rock_bm_60_f1, colony terrain_rock_bm_65_f1 | disable, getdisabled | 3: getdisabled, global | - | - |
| ColonyFactor1_Final | hirstaang forest region | runs | 2 activator, 2 door; placed 4 (Bloodmoon 4) | colony_smoke_4_4_f1, ex_colony_p_residence01a_4, ex_colony_door05_int_a, ex_colony_door05a_4 | disable, enable, getdisabled | 6: getdisabled, global | - | - |
| ColonyFactor1_Mid | hirstaang forest region | runs | 5 activator; placed 6 (Bloodmoon 6) | ex_colony_const_barn01_4, ex_colony_const_brick02-4 f1, ex_colony_const_house02_4, ex_colony_const_struc01_4 f1, ex_colony_const_stud01_4 f1 | disable, enable, getdisabled | 6: getdisabled, global | - | - |
| ColonyFactor2_D | hirstaang forest region | runs | 4 activator; placed 7 (Bloodmoon 7) | colony flora_tree_bm_snow_04_f2, colony flora_tree_bm_snow_05_f2, colony terrain_rock_bm_60_f2, colony terrain_rock_bm_64_f2 | disable, getdisabled | 3: getdisabled, global | - | - |
| ColonyFactor2_Final | hirstaang forest region | runs | 2 activator, 2 door; placed 4 (Bloodmoon 4) | colony_smoke_4_4_f2, ex_colony_p_residence01b_4, ex_colony_door05_int_b, ex_colony_door05b_4 | disable, enable, getdisabled | 6: getdisabled, global | - | - |
| ColonyFactor2_Mid | hirstaang forest region | runs | 5 activator; placed 6 (Bloodmoon 6) | ex_colony_const_brick01_4 f2, ex_colony_const_house03_4, ex_colony_const_struc01_4 f2, ex_colony_const_stud01_4 f2, ex_colony_const_wood01_4 f2 | disable, enable, getdisabled | 6: getdisabled, global | - | - |
| ColonyFactor3_D | hirstaang forest region | runs | 5 activator; placed 10 (Bloodmoon 10) | colony flora_tree_bm_snow_01_f3, colony flora_tree_bm_snow_05_f3, colony terrain_rock_bm_60_f3, colony terrain_rock_bm_64_f3, colony terrain_rock_bm_65_f3 | disable, getdisabled | 3: getdisabled, global | - | - |
| ColonyFactor3_Final | hirstaang forest region | runs | 2 activator, 2 door; placed 4 (Bloodmoon 4) | colony_smoke_4_4_f3, ex_colony_p_residence01c_4, ex_colony_door05_int_c, ex_colony_door05c_4 | disable, enable, getdisabled | 4: getdisabled, global | - | - |
| ColonyFactor3_Mid | hirstaang forest region | runs | 4 activator; placed 5 (Bloodmoon 5) | ex_colony_const_brick01_4 f3, ex_colony_const_house01_4, ex_colony_const_struc01_4 f3, ex_colony_const_stud01_4 f3 | disable, enable, getdisabled | 6: getdisabled, global | - | - |
| ColonyFalco | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 82 dialogue results | falco galenus | forcegreeting, getdistance, geteffect, getjournalindex, journal, menumode, ondeath, sethealth | 19: getdistance, geteffect, getjournalindex, local, menumode, ondeath | - | - |
| ColonyGarnas | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | garnas uvalen | disable, enable, getdisabled, getjournalindex | 6: getdisabled, getjournalindex, global | - | - |
| ColonyGratian | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 1 dialogue results | gratian caerellius | disable, enable, getdisabled, getjournalindex | 5: getdisabled, getjournalindex, global | - | - |
| ColonyHroldar_B | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | hroldar the strange_b | aiescort, aiwander, disable, enable, forcegreeting, getaipackagedone, getdisabled, getjournalindex, journal, ondeath, setfight, startcombat | 17: getaipackagedone, getdisabled, getjournalindex, local, ondeath | - | - |
| ColonyMineBoulder1 | hirstaang forest region | runs | 2 activator; placed 4 (Bloodmoon 4) | in_co_mine_boulder3, in_co_mine_boulder5 | disable, getdisabled, getjournalindex | 6: getdisabled, getjournalindex, global | - | - |
| ColonyMineBoulder2 | hirstaang forest region | runs | 5 activator; placed 7 (Bloodmoon 7) | in_co_mine_boulder0_2, in_co_mine_boulder1_2, in_co_mine_boulder2_2, in_co_mine_boulder3_2, in_co_mine_boulder5_2 | disable, getdisabled, getjournalindex | 2: getdisabled, getjournalindex | - | - |
| ColonyMineDoor | hirstaang forest region | runs | 2 door; placed 2 (Bloodmoon 2) | door_ravenrock_mine, ex_colony_minedoor | activate, disable, enable, getdisabled, getdistance, getjournalindex, messagebox, onactivate | 10: getdisabled, getdistance, getjournalindex, global, onactivate | - | - |
| ColonyNordAttack | hirstaang forest region | runs | 10 NPC; placed 10 (Bloodmoon 10) | alfbrand_b, audmund_b, balfring, bryngrim_b, eifid, fjorkvar and 4 more | disable, enable, getdisabled, ondeath | 6: getdisabled, global, ondeath | - | - |
| ColonyOrmvard | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | ormvard | disable, enable, forcegreeting, getdeadcount, getdisabled, getjournalindex, journal, ondeath, setfight, startcombat | 18: getdeadcount, getdisabled, getjournalindex, global, local, ondeath, other script | - | - |
| ColonyRoot1 | hirstaang forest region | runs | 3 activator; placed 6 (Bloodmoon 6) | act_ex_colony_root_1, act_ex_colony_root_2, act_ex_colony_root_4 | disable, getdisabled, getjournalindex | 2: getdisabled, getjournalindex | - | - |
| ColonyRoot1a | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_ex_colony_root_3 | disable, getdisabled, getdistance, getjournalindex, journal | 5: getdisabled, getdistance, getjournalindex, local | - | - |
| ColonyRoot2 | hirstaang forest region | runs | 4 activator; placed 7 (Bloodmoon 7) | act_ex_colony_root_1b, act_ex_colony_root_2b, act_ex_colony_root_3b, act_ex_colony_root_4b | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| ColonyRugTrap | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | ac_furn_rug_colony | cast, getjournalindex, getstandingpc, messagebox | 4: getjournalindex, getstandingpc, local | - | - |
| ColonySeler | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 9 dialogue results | seler favelnim | aiwander, forcegreeting, getdistance, getfatigue, getjournalindex, getsecondspassed, journal, menumode, ondeath, positioncell, setfight, startcombat, stopcombat, stopscript | 17: getdistance, getjournalindex, local, menumode, ondeath | - | - |
| ColonyServSmith | hirstaang forest region | runs | 3 activator, 1 door; placed 3 (Bloodmoon 3) | colony_smoke_smith, ex_colony_sop01, ex_colony_sop02b_2, ex_colony_door04_2b | disable, enable, getdisabled, stopscript | 4: getdisabled, global | - | - |
| ColonyServSmithConst | hirstaang forest region | runs | 2 activator; placed 2 (Bloodmoon 2) | ex_colony_const_barn01_2_ser, ex_colony_const_house02_2_ser | disable, enable, getdisabled, stopscript | 6: getdisabled, global | - | - |
| ColonyServSmithDisable | hirstaang forest region | runs | 4 activator; placed 7 (Bloodmoon 7) | colony flora_tree_bm_snow_01_t2, colony flora_tree_bm_snow_05_t2, colony terrain_rock_bm_60_t2, colony terrain_rock_bm_61_t2 | disable, getdisabled | 4: getdisabled, global | - | - |
| ColonyServTrader | hirstaang forest region | runs | 2 activator, 1 door; placed 2 (Bloodmoon 2) | ex_colony_sop01_2, ex_colony_sop02, ex_colony_door02_2 | disable, enable, getdisabled, stopscript | 4: getdisabled, global | - | - |
| ColonyServTraderConst | hirstaang forest region | runs | 2 activator; placed 2 (Bloodmoon 2) | ex_colony_const_barn01_2_2t, ex_colony_const_house02_2t | disable, enable, getdisabled, stopscript | 6: getdisabled, global | - | - |
| ColonyServTraderDisable | hirstaang forest region | runs | 4 activator; placed 5 (Bloodmoon 5) | colony flora_tree_bm_snow_01_t1, colony flora_tree_bm_snow_05_t1, colony terrain_rock_bm_59_t1, colony terrain_rock_bm_65_t1 | disable, getdisabled | 4: getdisabled, global | - | - |
| ColonySpriggan1 | hirstaang forest region | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_spriggan_co1 | activate, disable, enable, getdisabled, getjournalindex, getpos, getsecondspassed, menumode, modhealth, modresistfire, modresistfrost, modresistmagicka, modresistparalysis, modresistpoison, onactivate, ondeath, placeitem, resurrect, setfight, setscale, startcombat | 23: getdisabled, getjournalindex, local, menumode, onactivate, ondeath | - | - |
| ColonySpriggan2 | hirstaang forest region | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_spriggan_co2 | activate, disable, enable, getdisabled, getpos, getsecondspassed, menumode, modhealth, modresistfire, modresistfrost, modresistmagicka, modresistparalysis, modresistpoison, onactivate, ondeath, placeitem, resurrect, setfight, setscale, startcombat | 22: getdisabled, local, menumode, onactivate, ondeath, other script | - | - |
| ColonySpriggan3 | hirstaang forest region | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_spriggan_co3 | activate, disable, enable, getdisabled, getpos, getsecondspassed, menumode, modhealth, modresistfire, modresistfrost, modresistmagicka, modresistparalysis, modresistpoison, onactivate, ondeath, placeitem, resurrect, setfight, setscale, startcombat | 22: getdisabled, local, menumode, onactivate, ondeath, other script | - | - |
| ColonySpriggan4 | hirstaang forest region | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_spriggan_co4 | activate, disable, enable, getdisabled, getpos, getsecondspassed, journal, menumode, modhealth, modresistfire, modresistfrost, modresistmagicka, modresistparalysis, modresistpoison, onactivate, ondeath, placeitem, resurrect, setfight, setscale, startcombat | 26: getdisabled, local, menumode, onactivate, ondeath, other script | - | - |
| ColonyStalhrim | hirstaang forest region | runs | 1 container; placed 26 (Bloodmoon 26) | contain_bm_stalhrim_01 | activate, getitemcount, getjournalindex, journal, messagebox, onactivate | 4: getitemcount, getjournalindex, onactivate | - | - |
| ColonyToralf | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | toralf | disable, enable, forcegreeting, getdeadcount, getdisabled, getjournalindex, journal, ondeath | 16: getdeadcount, getdisabled, getjournalindex, global, local, ondeath | - | - |
| ColonyUnel | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 7 dialogue results | unel lloran | aiwander, disable, enable, forcegreeting, getcurrentaipackage, getdisabled, getdistance, getjournalindex, journal | 7: getcurrentaipackage, getdisabled, getdistance, getjournalindex | - | - |
| ColonyUryn | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 6 dialogue results | uryn maren | additem, aitravel, aiwander, clearforcesneak, disable, enable, forcegreeting, forcesneak, getaipackagedone, getdeadcount, getdisabled, getdistance, getjournalindex, journal | 71: getaipackagedone, getdeadcount, getdisabled, getdistance, getjournalindex, global, local | - | - |
| ColonyValgeir | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | valgeir | disable, enable, forcegreeting, getdeadcount, getdisabled, getjournalindex, journal, ondeath, setfight, startcombat | 18: getdeadcount, getdisabled, getjournalindex, global, local, ondeath, other script | - | - |
| ColonyVeresa | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1) | veresa alver | disable, enable, getdisabled, position | 8: getdisabled, global, local | - | - |
| ColonyWolf_Hroldar | hirstaang forest region | runs | 1 creature; placed 2 (Bloodmoon 2) | bm_wolf_hroldar | disable, enable, getdeadcount, getdisabled, getdistance, getjournalindex, setfight, startcombat, stopcombat | 9: getdeadcount, getdisabled, getdistance, getjournalindex, local | - | - |
| ColonyWolfKill | hirstaang forest region | runs | 2 NPC; placed 1 (Bloodmoon 1); speaker of 3 dialogue results | chappy_test_guy, tirvel balen | disable, enable, getdisabled, gethealth, getjournalindex, gettarget, journal | 7: getdisabled, gethealth, getjournalindex, gettarget, local | - | - |
| faustusScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | zeno faustus | - | 2: global, local | - | - |
| fortDisableScript | hirstaang forest region | runs | 6 activator; placed 8 (Bloodmoon 8) | act_bm_imp_plat_01, act_bm_wall_01, act_bm_wall_arch_01, act_bm_wall_corner_01, act_bm_wall_corner_03, act_bm_well_01 | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| fortEnableScript | hirstaang forest region | runs | 8 activator; placed 15 (Bloodmoon 15) | act_bm_imp_plat_02, act_bm_rubble_01, act_bm_rubble_02, act_bm_wall_02, act_bm_wall_03, act_bm_wall_arch_02 and 2 more | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| fortloreboozeScript | hirstaang forest region | runs | 3 NPC; placed 20 (Bloodmoon 20) | bm_imperial guard, raccan, vilbia herennia | - | - | - | nothing to run but its own locals, which the dialogue keeps on the speaker |
| GaminScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 3 dialogue results | gamin girith | aifollow, aiwander, getdistance, getjournalindex, journal, ondeath, setalarm, setfight, startcombat | 9: getdistance, getjournalindex, local, ondeath | - | - |
| GidarScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 7 dialogue results | gidar verothan | forcegreeting, getcurrentaipackage, getdistance, getjournalindex, journal, menumode, ondeath, setfight, startcombat | 9: getcurrentaipackage, getdistance, getjournalindex, local, menumode, ondeath | - | - |
| HroldarScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 6 dialogue results | hroldar the strange | aitravel, aiwander, disable, enable, forcegreeting, getdisabled, getdistance, getfatigue, gethealth, getjournalindex, getpos, journal, ondeath, placeitem, position, setfight, startcombat, stopcombat | 36: getdisabled, getdistance, getjournalindex, global, local, ondeath | - | - |
| icewallcrackScript | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_penumbra3 | getjournalindex, playsound | 2: getjournalindex, local | - | - |
| icewallScript | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | bm_ice_wall | getbuttonpressed, getitemcount, getjournalindex, journal, loopgroup, messagebox, onactivate, playgroup, removeitem | 10: getitemcount, getjournalindex, local, onactivate | - | - |
| luciusScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 15 dialogue results | saenus lusius | forcegreeting, getdistance, getjournalindex, ondeath, setfight, startcombat | 8: getdistance, getjournalindex, global, local, ondeath | - | - |
| nunciusClosetScript | hirstaang forest region | runs | 1 container; placed 1 (Bloodmoon 1) | de_p_closet_02_nuncius | activate, getitemcount, getlocked, messagebox, onactivate | 6: getitemcount, getlocked, local, onactivate | - | - |
| nunciuskeyScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 7 dialogue results | antonius nuncius | additem, getjournalindex, ondeath | 2: getjournalindex, ondeath | - | - |
| nunciusStashScript | hirstaang forest region | runs | 1 container; placed 1 (Bloodmoon 1) | de_p_desk_nuncius | activate, getjournalindex, getlocked, journal, onactivate | 4: getjournalindex, getlocked, onactivate | - | - |
| OddfridFind | hirstaang forest region | runs | 1 item; placed 1 (Bloodmoon 1) | misc_skull_oddfrid | activate, disable, enable, getjournalindex, journal, onactivate | 5: getjournalindex, local, onactivate | - | - |
| OddRumorScript | hirstaang forest region | runs | 1 book; placed 1 (Bloodmoon 1) | sc_rumornote_bm | activate, disable, enable, journal, onactivate | 4: global, local, onactivate | - | - |
| pentorch1Script | hirstaang forest region | runs | 1 light; placed 26 (Bloodmoon 26) | bm_light_penumbra1 | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| pentorch2Script | hirstaang forest region | runs | 1 activator; placed 26 (Bloodmoon 26) | bm_light_penumbra2 | disable, getdisabled, getjournalindex | 2: getdisabled, getjournalindex | - | - |
| penumbra2Script | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_penumbra2 | getdistance, getjournalindex, journal | 4: getdistance, getjournalindex, local | - | - |
| penumbradoorScript | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_snowdoor2 | disable, getdisabled, getjournalindex | 2: getdisabled, getjournalindex | - | - |
| penumbraScript | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_penumbra | getdistance, getjournalindex, journal | 4: getdistance, getjournalindex, local | - | - |
| Pub_RavenRock | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 1 dialogue results | alcedonia amnis | cellchanged, lock, unlock | 6: cellchanged, global, local | - | - |
| SabinusScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 1 dialogue results | sabinus oranius | aifollow, aiwander, getdistance, getjournalindex, journal, ondeath, setalarm, setfight, startcombat | 9: getdistance, getjournalindex, local, ondeath | - | - |
| severiaScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 10 dialogue results | severia gratius | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| smugcheckScript | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_smugglers | getdistance, getjournalindex, journal | 4: getdistance, getjournalindex, local | - | - |
| smugScript | hirstaang forest region | runs | 4 NPC; placed 4 (Bloodmoon 4) | mazorn gro-gar, mol gro-shat, mus roscius, sorian | ondeath, setfight | 5: local, ondeath, other script | - | - |
| spuriousScript | hirstaang forest region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 6 dialogue results | gualtierus spurius | disable, enable, forcegreeting, getdisabled, getdistance, getjournalindex, ondeath, setfight, stopcombat | 11: getdisabled, getdistance, getjournalindex, global, local, ondeath | - | - |
| stoneEarthScript | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_earth_01 | enable, getjournalindex, journal, messagebox, onactivate | 8: getjournalindex, global, local, onactivate | - | - |
| stoneeffect2Script | hirstaang forest region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_stonesound2 | getjournalindex, playsound | 2: getjournalindex, local | - | - |
| AirshipJournalScript | isinfier plains region | runs | 1 book; placed 1 (Bloodmoon 1) | bk_airship_captains_journal | activate, getjournalindex, journal, onactivate, showmap | 6: getjournalindex, local, onactivate | - | - |
| beastbearScript | isinfier plains region | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_bear_be_unique | aifollow, aiwander, disable, enable, getdisabled, getdistance, gethealth, getitemcount, getjournalindex, journal, ondeath, startcombat | 21: getdisabled, getdistance, gethealth, getitemcount, getjournalindex, global, local, ondeath | - | - |
| beastriekScript | isinfier plains region | runs | 6 creature; placed 5 (Bloodmoon 5) | bm_riekling_be_unique, bm_riekling_be_unique1, bm_riekling_be_unique2, bm_riekling_be_unique3, bm_riekling_be_unique4, bm_riekling_be_unique5 | disable, enable, getdisabled, getdistance, getjournalindex, ondeath, startcombat | 7: getdisabled, getdistance, getjournalindex, local, ondeath | - | - |
| BedDisable | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_kolfinna_beddisable | disable, getdisabled, getjournalindex, menumode, onactivate, showrestmenu | 4: getdisabled, getjournalindex, menumode, onactivate | - | - |
| BedEnable | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_kolfinna_bedenable | disable, enable, getdisabled, getjournalindex, menumode, onactivate, showrestmenu | 6: getdisabled, getjournalindex, menumode, onactivate | - | - |
| ColonyApronia | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 9 dialogue results | apronia alfena | aiwander, disable, enable, forcegreeting, getcurrentaipackage, getdisabled, getdistance, getjournalindex, journal | 8: getcurrentaipackage, getdisabled, getdistance, getjournalindex, local | - | - |
| ColonyElberoth | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1) | elberoth | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| ColonyShipwreck | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | ex_co_shipwreck | disable, enable, getdisabled, getdistance, getjournalindex, journal | 7: getdisabled, getdistance, getjournalindex, local | - | - |
| ColonyShipwreckDoor | isinfier plains region | runs | 1 creature, 2 door; placed 3 (Bloodmoon 3) | draugr_co_3_dead, ex_co_ship_cabindoor, ex_co_ship_trapdoor | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| ColonySWDraugr | isinfier plains region | runs | 1 creature; placed 3 (Bloodmoon 3) | draugr_co_3 | disable, enable, getdisabled, getjournalindex, ondeath | 5: getdisabled, getjournalindex, ondeath | - | - |
| fireenableScript | isinfier plains region | runs | 1 light; placed 3 (Bloodmoon 3) | bm_firepit_uni | disable, enable, getdisabled, getjournalindex | 6: getdisabled, getjournalindex | - | - |
| fireregenScript | isinfier plains region | runs | 3 creature; placed 6 (Bloodmoon 6) | bm_ice_troll, bm_ice_troll_sun, bm_ice_troll_tough | addspell, geteffect, removespell | 8: geteffect, local | - | - |
| fortloreboozeCarn2Script | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1) | bm_imperial guard_carn2 | disable, enable, getdisabled, getjournalindex | 8: getdisabled, getjournalindex, global | - | - |
| fortloreboozeCarn3Script | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1) | bm_imperial guard_carn3 | disable, enable, getdisabled, getjournalindex | 8: getdisabled, getjournalindex, global | - | - |
| GlenmorilRaven | isinfier plains region | runs | 1 creature; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | glenmoril_raven | disable, enable, forcegreeting, getdisabled, getdistance, getjournalindex, getpos, getsecondspassed, menumode, placeitem | 14: getdisabled, getdistance, getjournalindex, local, menumode | - | - |
| GlenmorilRavenCave | isinfier plains region | runs | 1 creature; placed 1 (Bloodmoon 1) | glenmoril_raven_cave | disable, enable, getdisabled, getjournalindex, getpos, getsecondspassed, menumode, placeitem | 13: getdisabled, getjournalindex, local, menumode | - | - |
| GlenmorilRitual | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | glenmoril_witch_altar_2 | disable, enable, forcegreeting, getdisabled, getdistance, getjournalindex, getpccell | 8: getdisabled, getdistance, getjournalindex, getpccell, local | - | - |
| GlenmorilWitchAltar | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | glenmoril_witch_altar | disable, forcegreeting, getdisabled, getjournalindex, getsecondspassed | 8: getdisabled, getjournalindex, local | - | - |
| GlenmorilWitchCave | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | glenmoril_witch_cave | cellchanged, disable, enable, forcegreeting, getdisabled, getdistance, getjournalindex, getpos, getsecondspassed, menumode | 19: cellchanged, getdisabled, getdistance, getjournalindex, local, menumode | - | - |
| GloomyCaveScript | isinfier plains region | runs | 2 NPC; placed 2 (Bloodmoon 2); speaker of 8 dialogue results | glenmoril_witch_cave_2, glenmoril_witch_cave_3 | cellchanged, disable, enable, getjournalindex | 5: cellchanged, getjournalindex | - | - |
| GrandfatherFrostScript | isinfier plains region | runs | 2 NPC; placed 1 (Bloodmoon 1); speaker of 3 dialogue results | grandfather frost, uncle sweetshare | getjournalindex, journal, ondeath | 3: getjournalindex, ondeath | - | - |
| IcicleScript | isinfier plains region | runs | 1 container; placed 1 (Bloodmoon 1) | contain_bm_fakerock_2 | disable, enable, getdisabled, getjournalindex | 8: getdisabled, getjournalindex, global | - | - |
| IngmarFollow | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 13 dialogue results | ingmar | getcurrentaipackage, getdeadcount, getdistance, getjournalindex, getsecondspassed, journal, menumode, ondeath, say, sethello | 10: getcurrentaipackage, getdeadcount, getdistance, getjournalindex, global, local, menumode, ondeath | - | - |
| musicdoor2Script | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_tombdoor2 | disable, enable, getdisabled, getjournalindex | 4: getdisabled, getjournalindex | - | - |
| musicdoorScript | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_tombdoor1 | disable, getdisabled, getjournalindex | 2: getdisabled, getjournalindex | - | - |
| plantScript | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_garden_plot_01 | getbuttonpressed, getdistance, getitemcount, journal, messagebox, removeitem, startscript | 7: getdistance, getitemcount, local | - | - |
| RitualDaggerScript | isinfier plains region | runs | 1 WEAP; placed 1 (Bloodmoon 1) | bm_dagger_wolfgiver | disable, enable, getjournalindex | 2: getjournalindex | - | - |
| rolfScript | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 11 dialogue results | rolf long-tooth | getjournalindex, journal | 11: getjournalindex, global, local | - | - |
| SigvatrScript | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 3 dialogue results | sigvatr the strong | getitemcount, getjournalindex, journal, ondeath | 7: getitemcount, getjournalindex, ondeath | - | - |
| SnowPrinceBook | isinfier plains region | runs | 1 book; placed 1 (Bloodmoon 1) | bk_snowprince | activate, getjournalindex, journal, onactivate | 3: getjournalindex, local, onactivate | - | - |
| stal1Script | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_pipe_01 | enable, getjournalindex, journal, menumode, onactivate, playsound | 7: getjournalindex, global, menumode, onactivate | - | - |
| stal2Script | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_pipe_02 | enable, getjournalindex, journal, menumode, onactivate, playsound | 6: getjournalindex, global, menumode, onactivate | - | - |
| stal3Script | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_pipe_03 | enable, getjournalindex, journal, menumode, onactivate, playsound | 7: getjournalindex, global, menumode, onactivate | - | - |
| stalloopScript | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_pipe_05 | enable, getdistance, getjournalindex, getsecondspassed, journal, playsound | 42: getdistance, getjournalindex, global, local | - | - |
| stalresetScript | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_stalreset | getjournalindex, journal | 20: getjournalindex, global, other script | - | - |
| stalsteamScript | isinfier plains region | runs | 6 activator; placed 6 (Bloodmoon 6) | act_bm_steam_01, act_bm_steam_02, act_bm_steam_03, act_bm_steam_04, act_bm_steam_05, act_bm_steam_06 | disable, getdisabled, getsecondspassed | 2: getdisabled, local | - | - |
| stoneeffect3Script | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_stonesound3 | getjournalindex, playsound | 2: getjournalindex, local | - | - |
| stoneeffect4Script | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_stonesound4 | getjournalindex, playsound | 2: getjournalindex, local | - | - |
| stoneSunScript | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_sun_01 | enable, getjournalindex, journal, messagebox, onactivate | 8: getjournalindex, global, local, onactivate | - | - |
| stoneTreesScript | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_tree_01 | enable, getjournalindex, journal, messagebox, onactivate | 8: getjournalindex, global, local, onactivate | - | - |
| ThormoorTeleport | isinfier plains region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 6 dialogue results | thormoor gray-wave | disable, enable, getjournalindex, getpccell | 3: getjournalindex, getpccell | - | - |
| trackerScript | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_tracker1 | aifollow, aitravel, aiwander, forcegreeting, getaipackagedone, getdistance, getitemcount, getjournalindex, journal, placeatpc, playsound, sethealth, sethello | 43: getaipackagedone, getdistance, getitemcount, getjournalindex, global, local | - | - |
| treesprigScript | isinfier plains region | runs | 1 creature; placed 5 (Bloodmoon 5) | bm_spriggan_st_unique | activate, aiwander, disable, enable, getdisabled, getitemcount, getjournalindex, getpos, getsecondspassed, menumode, modhealth, modresistfire, modresistfrost, modresistmagicka, modresistparalysis, modresistpoison, onactivate, ondeath, placeitem, resurrect, setfight, setscale, stopcombat | 24: getdisabled, getitemcount, getjournalindex, local, menumode, onactivate, ondeath | - | - |
| treesriekScript | isinfier plains region | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_riekling_st_unique | disable, enable, getdisabled, getdistance, getitemcount, getjournalindex, journal | 8: getdisabled, getdistance, getitemcount, getjournalindex, local | - | - |
| ValbrandrDraugr | isinfier plains region | runs | 1 creature; placed 1 (Bloodmoon 1) | draugr_valbrandr | gethealth, getjournalindex, hitonme, journal, ondeath | 6: getjournalindex, local, ondeath | - | - |
| weretrackerScript | isinfier plains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_skaaltrackcentral | getdistance, getjournalindex, getsecondspassed, iswerewolf, placeatme | 15: getjournalindex, global, iswerewolf, local | - | - |
| weretrackerStatScript | isinfier plains region | runs | 3 NPC; placed 3 (Bloodmoon 3); placed by scripts (3 records) | skaal_tracker, skaal_tracker2, skaal_tracker3 | aitravel, disable, enable, getdisabled, getdistance, getjournalindex, journal, messagebox, ondeath, startcombat | 11: getdisabled, getdistance, getjournalindex, global, local, ondeath | - | - |
| WolfenderInnocent | isinfier plains region | runs | 3 NPC; placed 1 (Bloodmoon 1) | wolfender_f_imperial, wolfender_f_nord, wolfgiver_f_nord | additem, disable, enable, getitemcount, getjournalindex, journal, modfatigue, modhealth, ondeath | 7: getitemcount, getjournalindex, local, ondeath | - | - |
| dulkScript | moesring mountains region | runs | 1 creature; placed 1 (Bloodmoon 1); speaker of 3 dialogue results | bm_riekling_dulk_unique | forcegreeting, getdistance, getjournalindex, iswerewolf | 7: getdistance, getjournalindex, iswerewolf, local | - | - |
| HrothmundAxe | moesring mountains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_axe_hrothmund | cast, getjournalindex, journal, menumode, messagebox, onactivate | 8: getjournalindex, local, menumode, onactivate | - | - |
| karstaagdoor1Script | moesring mountains region | runs | 1 door; placed 1 (Bloodmoon 1) | bm_kartaag_door | activate, getjournalindex, iswerewolf, messagebox, onactivate | 3: getjournalindex, iswerewolf, onactivate | - | - |
| karstaagdoor2Script | moesring mountains region | runs | 1 door; placed 1 (Bloodmoon 1) | bm_karstcav_door | activate, getdistance, getjournalindex, messagebox, onactivate | 5: getdistance, getjournalindex, global, onactivate, other script | - | - |
| karstaagentryScript | moesring mountains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_karstaag | getdistance, getjournalindex, journal | 3: getdistance, getjournalindex, local | - | - |
| karstaagtrollScript | moesring mountains region | runs | 1 creature; placed 8 (Bloodmoon 8) | bm_icetroll_fg_uni | addspell, geteffect, getjournalindex, getspell, journal, ondeath, removespell | 17: geteffect, getjournalindex, getspell, global, local, ondeath | - | - |
| karstcavdoorScript | moesring mountains region | runs | 1 activator; placed 2 (Bloodmoon 2) | act_bm_snowdoor3 | disable, getdisabled, getjournalindex | 3: getdisabled, getjournalindex | - | - |
| krishScript | moesring mountains region | runs | 1 creature; placed 1 (Bloodmoon 1); speaker of 6 dialogue results | bm_riekling_krish_uniqu | aifollow, aiwander, forcegreeting, getdistance, getjournalindex, getsecondspassed, journal, menumode, ondeath, setfight | 22: getdistance, getjournalindex, global, local, menumode, ondeath | - | - |
| Sound_BM_IceSheet | moesring mountains region | runs | 1 activator; placed 14 (Bloodmoon 14) | sound_bm_ice | cellchanged, getsoundplaying, playloopsound3dvp | 2: cellchanged, getsoundplaying | - | - |
| stahldoorScript | moesring mountains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_snowdoor4 | disable, getdisabled, getjournalindex | 2: getdisabled, getjournalindex | - | - |
| stoneeffect5Script | moesring mountains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_stonesound5 | getjournalindex, playsound | 2: getjournalindex, local | - | - |
| stoneeffect6Script | moesring mountains region | runs | 1 activator; placed 1 (Bloodmoon 1) | active_bm_stonesound6 | getjournalindex, playsound | 2: getjournalindex, local | - | - |
| stoneWaterScript | moesring mountains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_water_01 | enable, getitemcount, getjournalindex, journal, messagebox, onactivate, removeitem | 9: getitemcount, getjournalindex, global, local, onactivate | - | - |
| stoneWindScript | moesring mountains region | runs | 1 activator; placed 1 (Bloodmoon 1) | act_bm_stone_wind_01 | enable, getjournalindex, journal, messagebox, onactivate | 8: getjournalindex, global, local, onactivate | - | - |
| swimmerScript | moesring mountains region | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_horker_swim_unique | aiescort, disable, enable, getaipackagedone, getdisabled, getdistance, getjournalindex, journal | 14: getaipackagedone, getdisabled, getdistance, getjournalindex, local | - | - |
| watersScript | moesring mountains region | runs | 1 item; placed 1 (Bloodmoon 1) | bm_waterlife_unique1 | disable, enable, getdisabled, getitemcount, getjournalindex, journal | 6: getdisabled, getitemcount, getjournalindex | - | - |
| WolfDoorScript | moesring mountains region | runs | 2 door; placed 1 (Bloodmoon 1) | bm_ic_door_pelt_wolf, ex_nord_door_wolf | activate, getbuttonpressed, getjournalindex, journal, menumode, messagebox, onactivate, say | 9: getjournalindex, local, menumode, onactivate | - | - |
| reeh_jahScript | molag mar region | runs | 1 NPC; placed 1 (Morrowind 1); speaker of 5 dialogue results | reeh_jah | cellchanged, disable, getcurrentaipackage, getdisabled, getdistance, getjournalindex, journal, ondeath | 11: cellchanged, getcurrentaipackage, getdisabled, getdistance, getjournalindex, ondeath | - | - |
| GlenmorilRing | records not placed | runs | 1 clothing; placed by scripts (1 records) | glenmoril_ring_bm | disable, explodespell, getsecondspassed, setdelete | 2: local | - | runs while the player carries one of its items |
| hircinekey2Script | records not placed | runs | 2 item; held by placed containers and actors 4 | key_hircine2, key_hircine3 | getitemcount, getjournalindex, journal | 3: getitemcount, getjournalindex, local | - | runs on the items placed containers and actors hold, while their area is loaded |
| hircinekeyScript | records not placed | runs | 1 item; held by placed containers and actors 1 | key_hircine1 | getitemcount, getjournalindex, journal | 3: getitemcount, getjournalindex, local | - | runs on the items placed containers and actors hold, while their area is loaded |
| hircineringScript | records not placed | runs | 1 clothing | bm_ring_hircine | addspell, becomewerewolf, disableplayercontrols, enableplayercontrols, fadein, fadeout, getbuttonpressed, getsecondspassed, menumode, messagebox, playbink, removespell, setwerewolfacrobatics, undowerewolf | 32: global, local, menumode | - | runs while the player carries one of its items |
| HroldarRing | records not placed | runs | 1 clothing; placed by scripts (1 records) | hroldar_ring | disable, explodespell, getsecondspassed, setdelete | 2: local | - | runs while the player carries one of its items |
| hunter2Script | records not placed | runs | 1 NPC; placed by scripts (1 records) | skaal_hunter | additem, aitravel, disable, getaipackagedone, getdistance, getitemcount, getjournalindex, journal, messagebox, ondeath, removeitem | 15: getaipackagedone, getdistance, getitemcount, getjournalindex, global, local, ondeath | - | runs on the object a script places |
| Lycanthropycure | records not placed | runs | 1 book; held by placed containers and actors 1 | sc_lycanthropycure | activate, getitemcount, getjournalindex, journal, messagebox, onactivate | 14: getitemcount, getjournalindex, global, local, onactivate | - | runs on the items placed containers and actors hold, while their area is loaded |
| SovngardeBook | records not placed | runs | 1 book; held by placed containers and actors 2 | bk_sovngarde | activate, getjournalindex, journal, messagebox, onactivate | 7: getjournalindex, local, onactivate | - | runs on the items placed containers and actors hold, while their area is loaded |
| Spriggan | records not placed | runs | 1 creature; levelled lists 4 | bm_spriggan | activate, getpos, getsecondspassed, menumode, modhealth, modresistfire, modresistfrost, modresistmagicka, modresistparalysis, modresistpoison, onactivate, ondeath, placeitem, resurrect, setscale, startcombat | 17: local, menumode, onactivate, ondeath | - | runs on the actor a levelled list gives |
| sprigganeffect | records not placed | runs | 2 activator; placed by scripts (2 records) | sprigganup, wildwerewolf | disable, getsecondspassed, loopgroup, menumode, setdelete | 5: local, menumode | - | runs on the object a script places |
| totemScript | records not placed | runs | 1 item; held by placed containers and actors 1 | misc_bm_clawfang_unique | getitemcount, getjournalindex, getlevel, getpcsleep, journal, messagebox, placeatpc, wakeuppc | 9: getitemcount, getjournalindex, getlevel, getpcsleep, local | - | runs on the items placed containers and actors hold, while their area is loaded |
| UlfgarRing | records not placed | runs | 1 clothing; placed by scripts (1 records) | ulfgar_ring | disable, explodespell, getsecondspassed, setdelete | 2: local | - | runs while the player carries one of its items |
| wereBearhuntScript | records not placed | runs | 1 NPC; placed by scripts (1 records) | werewolf_bearhunt | becomewerewolf, ondeath | 2: local, ondeath | - | runs on the object a script places |
| wereeffectScript | records not placed | runs | 3 activator; placed by scripts (3 records) | bm_wereeffect, bm_wereeffect2, bm_wereeffect3 | disable, getsecondspassed, menumode, setdelete | 4: local, menumode | - | runs on the object a script places |
| werewolf_connor | records not placed | runs | 1 NPC; levelled lists 1 | bm_werewolf_wildernessc | addspell, becomewerewolf, getpos, getsecondspassed, menumode, ondeath, placeitem, undowerewolf | 11: global, local, menumode, ondeath | - | runs on the actor a levelled list gives |
| Werewolfwilderness | records not placed | runs | 9 NPC; levelled lists 9 | bm_werewolf_wild01, bm_werewolf_wild02, bm_werewolf_wild03, bm_werewolf_wild04, bm_werewolf_wild05, bm_werewolf_wild06 and 3 more | addspell, becomewerewolf, getpos, getsecondspassed, menumode, ondeath, placeitem, undowerewolf | 11: global, local, menumode, ondeath | - | runs on the actor a levelled list gives |
| wildwereScript | records not placed | runs | 4 NPC; placed by scripts (4 records) | bm_werewolf_wildhunt, bm_werewolf_wildhunt2, bm_werewolf_wildhunt3, bm_werewolf_wildhunt4 | becomewerewolf, disable, getdisabled, getjournalindex | 3: getdisabled, getjournalindex, local | - | runs on the object a script places |
| WolfRitualRing | records not placed | runs | 1 clothing; placed by scripts (1 records) | ritual_ring | disable, explodespell, getsecondspassed, setdelete | 2: local | - | runs while the player carries one of its items |
| DagothUrCreature1 | red mountain region | runs | 1 creature; placed 1 (Morrowind 1); speaker of 29 dialogue results | dagoth_ur_1 | disable, enable, getdisabled, getdistance, getitemcount, getsecondspassed, menumode, ondeath, playgroup, playsound3d, rotate, say | 12: getdisabled, getdistance, getitemcount, local, menumode, ondeath | - | - |
| enable_teleport | red mountain region | runs | 1 activator; placed 2 (Tribunal 1, Bloodmoon 1) | teleport_enabler | enableteleporting | - | - | - |
| LorkhanHeart | red mountain region | runs | 1 creature; placed 1 (Morrowind 1) | heart_akulakhan | cellchanged, disable, getdistance, getsoundplaying, hitonme, menumode, playgroup, playloopsound3d, positioncell, say, setfight, sethealth, startcombat, stopsound | 32: cellchanged, getdistance, getsoundplaying, global, local, menumode | - | - |
| aspect1Script | solstheim (bloodmoon) | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_hircine_straspect | disable, getangle, getitemcount, getjournalindex, getpos, getsecondspassed, journal, menumode, ondeath, placeitem | 7: getitemcount, getjournalindex, local, menumode, ondeath | - | - |
| aspect2Script | solstheim (bloodmoon) | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_hircine_spdaspect | disable, getangle, getitemcount, getjournalindex, getpos, getsecondspassed, journal, menumode, ondeath, placeitem | 7: getitemcount, getjournalindex, local, menumode, ondeath | - | - |
| aspect3Script | solstheim (bloodmoon) | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_hircine_huntaspect | disable, getangle, getitemcount, getjournalindex, getpos, getsecondspassed, journal, menumode, ondeath, placeitem | 7: getitemcount, getjournalindex, local, menumode, ondeath | - | - |
| cariushuntScript | solstheim (bloodmoon) | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 5 dialogue results | falx carius2 | aiwander, forcegreeting, getcurrentaipackage, getdistance, getjournalindex, getsecondspassed, iswerewolf, journal, ondeath | 17: getcurrentaipackage, getdistance, getjournalindex, iswerewolf, local, ondeath | - | - |
| giantScript | solstheim (bloodmoon) | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_frost_giant | addspell, getdistance, geteffect, getjournalindex, journal, ondeath, removespell | 13: getdistance, geteffect, getjournalindex, local, ondeath | - | - |
| heartfanghuntScript | solstheim (bloodmoon) | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 6 dialogue results | tharsten heart-fang2 | additem, becomewerewolf, forcegreeting, getangle, getdistance, getjournalindex, getpos, getsecondspassed, gettarget, iswerewolf, journal, menumode, messagebox, ondeath, placeitem, setfight, startcombat, stopcombat | 19: getdistance, getjournalindex, gettarget, iswerewolf, local, menumode, ondeath | - | - |
| hircine1Script | solstheim (bloodmoon) | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_hircine | disable, disableplayercontrols, enable, enableplayercontrols, getangle, getpos, getsecondspassed, journal, placeitem, say, saydone, startscript | 9: local, saydone | - | - |
| hircine2Script | solstheim (bloodmoon) | runs | 1 creature; placed 1 (Bloodmoon 1) | bm_hircine2 | disable, disableplayercontrols, enable, enableplayercontrols, getangle, getbuttonpressed, getdisabled, getdistance, getjournalindex, getpos, getsecondspassed, journal, messagebox, placeitem, say, saydone | 30: getdisabled, getdistance, getjournalindex, local, saydone | - | - |
| hircinechestScript | solstheim (bloodmoon) | runs | 1 container; placed 1 (Bloodmoon 1) | com_chest_01_hircine2 | activate, onactivate | 2: onactivate, other script | - | - |
| mazegate1Script | solstheim (bloodmoon) | runs | 1 door; placed 1 (Bloodmoon 1) | bm_mazegate_01 | activate, getitemcount, iswerewolf, messagebox, onactivate | 3: getitemcount, iswerewolf, onactivate | - | - |
| mazegate2Script | solstheim (bloodmoon) | runs | 1 door; placed 1 (Bloodmoon 1) | bm_mazegate_02 | activate, getitemcount, iswerewolf, messagebox, onactivate | 3: getitemcount, iswerewolf, onactivate | - | - |
| mazegate3Script | solstheim (bloodmoon) | runs | 1 door; placed 1 (Bloodmoon 1) | bm_mazegate_03 | disable, enable, getdeadcount, getitemcount, getjournalindex, iswerewolf, journal, messagebox, onactivate, playbink, positioncell | 8: getdeadcount, getitemcount, getjournalindex, iswerewolf, local, onactivate | - | - |
| ringdoorScript | solstheim (bloodmoon) | runs | 1 door; placed 1 (Bloodmoon 1) | ex_bm_ringdoor | messagebox, onactivate | 1: onactivate | - | - |
| weremazeScript | solstheim (bloodmoon) | runs | 1 NPC; placed 31 (Bloodmoon 31); placed by scripts (1 records) | bm_werewolf_maze1 | becomewerewolf | 1: local | - | - |
| werestatue1Script | solstheim (bloodmoon) | runs | 1 activator; placed 4 (Bloodmoon 4) | act_werewolf_statue_1 | disable, getangle, getdistance, getitemcount, getpos, iswerewolf, placeitem | 4: getdistance, getitemcount, iswerewolf, local | - | - |
| werestatue2Script | solstheim (bloodmoon) | runs | 1 activator; placed 5 (Bloodmoon 5) | act_werewolf_statue_2 | disable, getangle, getdistance, getitemcount, getpos, iswerewolf, placeitem | 4: getdistance, getitemcount, iswerewolf, local | - | - |
| BrynjolfrScript | thirsk region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 42 dialogue results | brynjolfr | - | 1: global, local | - | - |
| ErichScript | thirsk region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | erich the unworthy | disable, forcegreeting, getdistance, getjournalindex, journal, ondeath, sethealth | 8: getdistance, getjournalindex, local, ondeath | - | - |
| GrissSkull | thirsk region | runs | 1 activator; placed 1 (Bloodmoon 1) | bm_griss_skull | disable, getjournalindex | 1: getjournalindex | - | - |
| JastalOutside | thirsk region | runs | 1 NPC; placed 1 (Bloodmoon 1) | bereditte jastal_out | disable, enable, gethealth, getjournalindex | 7: gethealth, getjournalindex | - | - |
| JastalThirsk | thirsk region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 2 dialogue results | bereditte jastal | disable, enable, gethealth, getjournalindex | 5: gethealth, getjournalindex | - | - |
| meadhallhead | thirsk region | runs | 2 activator; placed 2 (Bloodmoon 2) | bm_whitebear_thirsk, bm_whitewolf_thirsk | disable, enable, getjournalindex, stopscript | 2: getjournalindex | - | - |
| MeadScript | thirsk region | runs | 1 container; placed 3 (Bloodmoon 3) | crate_02_mead_unique | disable, enable, getjournalindex, stopscript | 2: getjournalindex | - | - |
| MirisaFollow | thirsk region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 5 dialogue results | mirisa | aiwander, getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, getsecondspassed, journal, menumode, ondeath, say, sethello | 13: getcurrentaipackage, getdistance, gethealth, getjournalindex, getpccell, global, local, menumode, ondeath | - | - |
| SvenjaOutside | thirsk region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 4 dialogue results | svenja_outside | disable, enable, getjournalindex, journal, ondeath | 6: getjournalindex, ondeath | - | - |
| SvenjaThirsk | thirsk region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 13 dialogue results | svenja snow-song | disable, enable, gethealth, getjournalindex | 6: gethealth, getjournalindex, global, local | - | - |
| ThirskBuilder | thirsk region | runs | 3 NPC; placed 3 (Bloodmoon 3); speaker of 3 dialogue results | thirsk_build, thirsk_build_2, thirsk_build_3 | disable, enable, getjournalindex | 4: getjournalindex | - | - |
| ThirskCorpse | thirsk region | runs | 5 NPC; placed 4 (Bloodmoon 4); speaker of 4 dialogue results | andrelheim, olfeigr the fair, skjoldr wolf-runner, skjoldr wolf-runner_ded, ulfrun | disable, getjournalindex, sethealth | 2: getjournalindex | - | - |
| ThirskDoorsClosed | thirsk region | runs | 2 door; placed 2 (Bloodmoon 2) | in_thirsk_door_main_1_b, in_thirsk_door_main_2_b | disable, enable, getjournalindex, getpccell | 6: getjournalindex, getpccell | - | - |
| ThirskDoorsOpen | thirsk region | runs | 2 door; placed 2 (Bloodmoon 2) | in_thirsk_door_main_1, in_thirsk_door_main_2 | disable, enable, getjournalindex, getpccell | 6: getjournalindex, getpccell | - | - |
| thirskdudes | thirsk region | runs | 2 NPC, 1 WEAP; placed 3 (Bloodmoon 3) | bm_bathmar, bm_bergljot, bm nordic silver longsword_cft | disable, enable, getjournalindex, stopscript | 2: getjournalindex | - | - |
| ThirskFixed | thirsk region | runs | 1 door; placed 1 (Bloodmoon 1) | ex_s_door_double_fixed | disable, enable, getjournalindex | 4: getjournalindex | - | - |
| ThirskRepair | thirsk region | runs | 1 door; placed 1 (Bloodmoon 1) | ex_s_door_double_fixing | disable, enable, getjournalindex, messagebox, onactivate | 6: getjournalindex, onactivate | - | - |
| ThirskRubble | thirsk region | runs | 6 activator; placed 6 (Bloodmoon 6) | in_thirsk_archpiece01, in_thirsk_archpiece02, in_thirsk_beampiece01, in_thirsk_beampiece03, in_thirsk_columnpiece01, in_thirsk_columnpiece02 | disable, enable, getjournalindex, getpccell | 6: getjournalindex, getpccell | - | - |
| ThormoorOutside | thirsk region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 3 dialogue results | thormoor_out | disable, enable, gethealth, getjournalindex | 12: gethealth, getjournalindex | - | - |
| ThormoorThirsk | thirsk region | runs | 1 NPC; placed 1 (Bloodmoon 1); speaker of 3 dialogue results | thormoor_thirsk | disable, enable, gethealth, getjournalindex | 16: gethealth, getjournalindex | - | - |

## Not used in the original game

Scripts that no object, character, item, dialogue line, start record or other script ever names or starts, so they never ran in the original game either: the developers' test and example scripts, earlier versions replaced by others, and cut content. They stay in the game as they are; the counts above count only the scripts the original uses, and the data file keeps every script with its state. The rule, checked for every script here: no record carries the script and no start record, StartScript or dialogue result names it; or the records that carry it are placed in no cell of the three masters, no levelled list gives them, no script or dialogue result makes one (PlaceAtPC, PlaceAtMe, PlaceItem, PlaceItemCell), no container or character holds one, and they are not items a script could hand out (a script on an item always counts as used). Of the 133 scripts here, 122 are carried by no record at all and 11 by records that exist nowhere in the game (10 on activator records, 1 on creature records).

### Morrowind (88)

| Script | Why |
| --- | --- |
| Akula_doors | nothing names it: it never runs in the original either |
| Akula_outerdoors | its records are never placed and nothing makes them: it never runs in the original either |
| AzurasStarScript | nothing names it: it never runs in the original either |
| BILL_common_trapped_rug | its records are never placed and nothing makes them: it never runs in the original either |
| BILL_FG_Berwen_Corp | nothing names it: it never runs in the original either |
| BILL_shrineMaarGan | nothing names it: it never runs in the original either |
| BILL_shrineSanctus | nothing names it: it never runs in the original either |
| BILL_TT_Bjadmund | nothing names it: it never runs in the original either |
| BILL_TT_Dagoth_Fovon | nothing names it: it never runs in the original either |
| BILL_TT_Delvam_Andarys | nothing names it: it never runs in the original either |
| BILL_TT_MinistryHeathen | nothing names it: it never runs in the original either |
| BILL_TT_MountKand01 | nothing names it: it never runs in the original either |
| BILL_TT_MountKand02 | nothing names it: it never runs in the original either |
| BILL_TT_MountKand03 | nothing names it: it never runs in the original either |
| BILL_TT_MountKand04 | nothing names it: it never runs in the original either |
| BILL_TT_Tralas_Rendas | nothing names it: it never runs in the original either |
| boethiabuildScript | nothing names it: it never runs in the original either |
| bulfimScript | nothing names it: it never runs in the original either |
| CharGenDoorExit | nothing names it: it never runs in the original either |
| da_bullnetchScript | nothing names it: it never runs in the original either |
| daric_bielleScript | nothing names it: it never runs in the original either |
| diseaseChills | nothing names it: it never runs in the original either |
| diseaseCorprus | nothing names it: it never runs in the original either |
| diseaseDampworm | nothing names it: it never runs in the original either |
| diseaseGreenspore | nothing names it: it never runs in the original either |
| diseaseRattles | nothing names it: it never runs in the original either |
| diseaseRockjoint | nothing names it: it never runs in the original either |
| diseaseRustChancre | nothing names it: it never runs in the original either |
| diseaseSerpiginous | nothing names it: it never runs in the original either |
| diseaseWtichwither | nothing names it: it never runs in the original either |
| doortestwarp | nothing names it: it never runs in the original either |
| Dummy | nothing names it: it never runs in the original either |
| DwRuins_Ark_Lv_A | nothing names it: it never runs in the original either |
| example_Containers | nothing names it: it never runs in the original either |
| Example_NPC_Stuff | nothing names it: it never runs in the original either |
| Example_NPC_Stuff_Gold_Edition | nothing names it: it never runs in the original either |
| fightGnawTooth | nothing names it: it never runs in the original either |
| fools_dead_check | nothing names it: it never runs in the original either |
| gameRatScript | nothing names it: it never runs in the original either |
| GlobalFixNPCs | nothing names it: it never runs in the original either |
| GnisisEggmineDoor | nothing names it: it never runs in the original either |
| GnisisWarpDoor | nothing names it: it never runs in the original either |
| high_fane_alert | nothing names it: it never runs in the original either |
| Huleeya_disposition_check | nothing names it: it never runs in the original either |
| jeanneScript | nothing names it: it never runs in the original either |
| letteScript | nothing names it: it never runs in the original either |
| marksmanToggle | nothing names it: it never runs in the original either |
| menhirTelNaga | its records are never placed and nothing makes them: it never runs in the original either |
| menhirTelUvirith | nothing names it: it never runs in the original either |
| MessageTest | nothing names it: it never runs in the original either |
| MiloKey | nothing names it: it never runs in the original either |
| MiloTravel | nothing names it: it never runs in the original either |
| MoveAndTurn | nothing names it: it never runs in the original either |
| MoveTriolith | its records are never placed and nothing makes them: it never runs in the original either |
| NibaniWaitOneDay | nothing names it: it never runs in the original either |
| noflee | nothing names it: it never runs in the original either |
| noidle | nothing names it: it never runs in the original either |
| nointruder | nothing names it: it never runs in the original either |
| nothief | nothing names it: it never runs in the original either |
| ouch_falsesunder | nothing names it: it never runs in the original either |
| Pub_TelAruhn_Plot | nothing names it: it never runs in the original either |
| ranisScript | nothing names it: it never runs in the original either |
| ratScript | nothing names it: it never runs in the original either |
| ringDrarelSummoning | nothing names it: it never runs in the original either |
| shashurariDoor | nothing names it: it never runs in the original either |
| SheogorathBlessing | nothing names it: it never runs in the original either |
| shrineBalUr | nothing names it: it never runs in the original either |
| shrineVivecHumility | nothing names it: it never runs in the original either |
| shrineVivecMystery | nothing names it: it never runs in the original either |
| Sound_Fire | nothing names it: it never runs in the original either |
| Sound_Fire_Small | nothing names it: it never runs in the original either |
| Strong2_Not | nothing names it: it never runs in the original either |
| StrongZero | nothing names it: it never runs in the original either |
| TelVosTeleport1 | its records are never placed and nothing makes them: it never runs in the original either |
| TelVosTeleport2 | nothing names it: it never runs in the original either |
| Test_AddSanguine | nothing names it: it never runs in the original either |
| TestMakePCVampire | nothing names it: it never runs in the original either |
| TestRefRotate | nothing names it: it never runs in the original either |
| TestRotate | nothing names it: it never runs in the original either |
| TestRotateSlow | nothing names it: it never runs in the original either |
| TGDiscountScript | nothing names it: it never runs in the original either |
| ThiefTraderScript | nothing names it: it never runs in the original either |
| UseTest | nothing names it: it never runs in the original either |
| uupse_Bagrum | nothing names it: it never runs in the original either |
| VampTest | nothing names it: it never runs in the original either |
| VampTest1 | nothing names it: it never runs in the original either |
| VampTest2 | nothing names it: it never runs in the original either |
| VampTest3 | nothing names it: it never runs in the original either |

### Tribunal (19)

| Script | Why |
| --- | --- |
| audienceScript1 | nothing names it: it never runs in the original either |
| bardoor3Script | nothing names it: it never runs in the original either |
| dbattackScriptOLD | nothing names it: it never runs in the original either |
| dbdartScript | nothing names it: it never runs in the original either |
| DrothChest | nothing names it: it never runs in the original either |
| drowned | its records are never placed and nothing makes them: it never runs in the original either |
| explosion_pushout | nothing names it: it never runs in the original either |
| fluctuateWaterLevel | its records are never placed and nothing makes them: it never runs in the original either |
| gateSound | its records are never placed and nothing makes them: it never runs in the original either |
| Museum | nothing names it: it never runs in the original either |
| PlagueHallRat1a | nothing names it: it never runs in the original either |
| PlagueNerile | nothing names it: it never runs in the original either |
| poisonsteam | nothing names it: it never runs in the original either |
| Sound_SothaSparks | nothing names it: it never runs in the original either |
| Sound_Water_break | nothing names it: it never runs in the original either |
| Sound_Waterfall | nothing names it: it never runs in the original either |
| tarenEnableScript | its records are never placed and nothing makes them: it never runs in the original either |
| TestMoveRock | nothing names it: it never runs in the original either |
| weatherScript | nothing names it: it never runs in the original either |

### Bloodmoon (26)

| Script | Why |
| --- | --- |
| bearheartScript | nothing names it: it never runs in the original either |
| begin | nothing names it: it never runs in the original either |
| Colony_D_1_m | nothing names it: it never runs in the original either |
| Colony_E_1_I | nothing names it: it never runs in the original either |
| ColonyAfer | nothing names it: it never runs in the original either |
| heartfangChangeScript | nothing names it: it never runs in the original either |
| hunteract1Script | nothing names it: it never runs in the original either |
| JeleenNote | nothing names it: it never runs in the original either |
| MockChangeScript | nothing names it: it never runs in the original either |
| SacrificeNordFemale | nothing names it: it never runs in the original either |
| stoneeffectbeastScript | its records are never placed and nothing makes them: it never runs in the original either |
| ThirskSvenjaDeath | nothing names it: it never runs in the original either |
| ThirskUdyrfrykte | nothing names it: it never runs in the original either |
| TorchdayScript | nothing names it: it never runs in the original either |
| TorchNightScript | nothing names it: it never runs in the original either |
| tracksound1Script | nothing names it: it never runs in the original either |
| tracksound2Script | nothing names it: it never runs in the original either |
| waterbottleScript | nothing names it: it never runs in the original either |
| WereChange2Script | nothing names it: it never runs in the original either |
| wereDreamScript1 | nothing names it: it never runs in the original either |
| wereDreamScript2 | nothing names it: it never runs in the original either |
| wereDreamScript3 | nothing names it: it never runs in the original either |
| weretracker2Script | nothing names it: it never runs in the original either |
| WitchNoteScript | nothing names it: it never runs in the original either |
| WolfGiver | nothing names it: it never runs in the original either |
| WolfInnocent | its records are never placed and nothing makes them: it never runs in the original either |
