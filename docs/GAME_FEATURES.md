# Game features

_Last updated with AmiWind v0.0.61-dev1 (4 November 2026)._

<!-- Generated whole by tools/game_features.py render from docs/game-features.json; do not edit by hand. -->

One row per system of the base game: what state AmiWind has it in, which reference decides how it should behave, where the proof is, and which work items and register entries carry the rest. The states are taken from the work lists and the bug register; a row is marked done only when it names a proof.

**10 of 48 systems done**, 29 partial, 9 missing.

| Area | Done | Partial | Missing | Systems |
| --- | ---: | ---: | ---: | ---: |
| World and interiors | 4 | 4 | 2 | 10 |
| Actors and behaviour | 0 | 6 | 0 | 6 |
| The player | 2 | 5 | 0 | 7 |
| Combat, death and the law | 1 | 1 | 2 | 4 |
| Magic | 0 | 1 | 4 | 5 |
| Items, containers and trade | 0 | 3 | 1 | 4 |
| Dialogue, voices, journal and factions | 0 | 4 | 0 | 4 |
| MWScript | 1 | 2 | 0 | 3 |
| Sound, music and the interface | 2 | 3 | 0 | 5 |
| **All** | **10** | **29** | **9** | **48** |

A row counts the system, not its size: a done row can be small and a missing one large. The references are OpenMW 0.51 for behaviour (read for the rules, nothing copied) and the pages of the UESP mirror for the original's numbers.

## Measured: MWScript

tools/mwscript/functions.py (the compiler's own table, counted in the builder container on 4 November 2026) and the builder's script measurement (docs/MWSCRIPT_BYTECODE.md).

| | Count |
| --- | ---: |
| Functions and instructions in the compiler's table | 504 |
| Carried out by the interpreter and the host | 229 (45.4 %) |
| Distinct functions the game's scripts use (23 October 2026, over the three masters) | 251 |
| Of those, carried out | used: pending |
| Scripts in the three masters | 1,207 |
| Scripts that compile | 1,207 |
| Scripts that run whole (30 October 2026) | 957 (79.3 %) |

used_and_carried_out is pending: the builder's script report does not record the used functions per build, so the overlap of the 251 used with the 229 carried out needs one run of python3 -m mwscript.measure on the game data in the builder container (MWSCRIPT-MORE-57).

## Sub-trackers

Each has its own source file and its own check.

| Tracker | Headline |
| --- | --- |
| [Dialogue features](DIALOGUE_FEATURES.md) | 5 of 29 done, 19 partial, 5 missing |
| [Voices and sounds](VOICE_FEATURES.md) | per kind of line, with its proof |
| [CHIM features](chim/FEATURES.md) | engine features with measured gains |
| [World, cell by cell](chim/CELL_TRACKER.md) | every cell converted and audited |
| [CHIM progress](chim/PROGRESS_TRACKER.md) | the island by region |
| [Asset coverage](ASSET_COVERAGE.md) | what of the original's assets is integrated |
| [Older trackers](trackers/README.md) | world progress, entities and points of interest, first versions |

## The systems

### World and interiors

| System | State | What | Reference | Proof | Missing | Work items | Register |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Vvardenfell exteriors | done | Every exterior cell of the base game as terrain, water, objects and sky on the CHIM world, streamed as the player walks. | OpenMW 0.51 cell and terrain loading; UESP Morrowind:Vvardenfell | docs/chim/CELL_TRACKER.md (1,390 of 1,390 cells converted and audited); tests/aga_chim_world_test.c, tests/test_world_survey.py. | - | - | - |
| Interiors | partial | Every interior of the base game but two as CHIM rooms with their lights, doors and residents; the load doors link both ways. | OpenMW 0.51 cell loading; UESP Morrowind:Interior cells | tests/test_chim_rooms.py, tests/aga_chim_room_record_test.c; release notes of v0.0.50 (every entrance linked both ways). | Two interiors are not converted; the items, containers and creatures of rooms are not yet loaded from per-area tables. | AREA-TABLES-60, AREA-DATA-CHUNKS-59, AREA-RECORD-ONE-READ-60 | - |
| Tribunal and Bloodmoon | missing | The two expansions' cells, quests and creatures. | OpenMW 0.51 content loading; UESP Tribunal and Bloodmoon pages | - | - | DLC-BUILD-LATER | - |
| Doors and load doors | partial | Hinged doors open and close, load doors move the player between cells with the destination marker, locks follow the game data and the scripts. | OpenMW 0.51 door and teleport handling; UESP Morrowind:Doors | tests/aga_hinged_door_test.c, tests/test_world_doors.py, tests/test_doors.py. | Gates, trapdoors, hatches and bar counter flaps do not move; load doors into rooms read no lock until lockpicks and keys exist. | DOOR-MOVERS-56 | [DOOR-LOAD-LOCKS-MISSING-51](bugs/DOOR-LOAD-LOCKS-MISSING-51.md) |
| Travel services | done | Silt strider, boat, gondola and guild guide travel from the travel provider's dialogue, with the fare and the arrival place. | OpenMW 0.51 travel services; UESP Morrowind:Transport | tests/aga_travel_test.c, tests/test_travel.py. | - | - | - |
| Weather | partial | Weather states, their sky and fog, and the choice by region. | OpenMW 0.51 weather and region records; UESP Morrowind:Weather | tests/aga_weather_rules_test.c, tests/test_region_weather.py. | Ash storms and blight storms in their regions are not driven by the region records yet. | WEATHER-REGIONS-56 | - |
| Day, night and sky | done | The calendar clock, sun and moons, the night sky, window and lamp lighting at night. | OpenMW 0.51 sky and time of day | tests/aga_daynight_test.c, tests/test_night_sky.py, tests/test_night_lighting.py. | - | - | - |
| Water and lava | done | Swimming, the sea, and lava that hurts. | OpenMW 0.51 water and lava handling | tests/aga_water_move_test.c, tests/aga_lava_rules_test.c, tests/test_chim_ocean.py. | - | - | - |
| Placed objects | partial | The statics, flora, lights and loose items the original places, drawn from one model table. | OpenMW 0.51 reference placement; the original's cell records | docs/ASSET_COVERAGE.md; tests/test_world_asset_coverage.py. | Not every placed item is drawn and takeable from the shared model table yet; trees have no depth steps. | WORLD-OBJECT-PLACEMENT-59, TREES-DEPTH-56, ITEMS-INDEX-57 | - |
| Area sounds | missing | The looping sounds of the invisible sound markers. | OpenMW 0.51 sound markers (static sounds); UESP Morrowind:Sound | - | - | SOUND-MARKERS-58 | - |

### Actors and behaviour

| System | State | What | Reference | Proof | Missing | Work items | Register |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Residents in the world | partial | Characters stand where the original places them, with the right face, hair and gear, in the exteriors and rooms that are built. | OpenMW 0.51 actor placement; UESP Morrowind:NPCs | tests/aga_ambient_test.c, tests/test_npc_recipes.py, tests/test_chim_actor_table.py. | Bodies are still baked into the image rather than built from parts at run time; the recipe tables are being cut per area. | NPC-RECIPES-PER-AREA-59, NPC-PARTS-RUNTIME-59 | - |
| Wander, idle and travel | partial | Residents walk and idle on their records' packages, and the scripts can send them travelling. | OpenMW 0.51 behaviour packages (wander, travel); UESP Morrowind:NPCs | tests/aga_ambient_test.c, tests/aga_npcpath_test.c, tests/test_ambient_lut.py. | Schedules by time of day, escort and the other packages are not carried out; compiled wander packages are built but off by default. | ACTORS-ALIVE-56, ACTORS-ON-57, AMBIENT-WALK-PER-AREA-60 | - |
| Creatures | partial | Creatures on their own models with idle, wander and attack on sight. | OpenMW 0.51 creature stats and behaviour | tests/test_creature_tables.py, tests/aga_chim_actor_table_test.c. | The cliff racer's strikes land none; Dagoth Ur's fight and voice are not in. | RACER-STRIKES-58, ACTORS-ALIVE-56 | - |
| Followers and companions | partial | A follower keeps with the player inside a cell. | OpenMW 0.51 AIFollow and AIFollowCell | tests/aga_companion_test.c, tests/test_companion_native.py. | Followers do not cross doors with the player. | FOLLOW-CELL-58 | - |
| Animation | partial | Standing, walking, running, fighting and scripted animation groups on skeletal actors. | OpenMW 0.51 animation groups; the original's keyframe files | tests/aga_animkit_test.c, tests/test_animkit.py, tests/test_anim_coverage.py. | Not every character plays its full set of sequences; walk and run cycles are being made cheaper. | ANIM-ALL-CHARACTERS-57, WALK-CYCLES-57 | [ANIMKIT-COVERAGE-35](bugs/ANIMKIT-COVERAGE-35.md) |
| Spawning by script | partial | Characters, creatures and items placed by scripts through one shared spawn. | OpenMW 0.51 PlaceAtMe, PlaceAtPC, PlaceItem | tests/aga_spawn_test.c, tests/test_entity_spawn_contract.py. | Spawned references are not yet proven across a save and reload. | SPAWNER-57, SPAWN-PROOF-58 | - |

### The player

| System | State | What | Reference | Proof | Missing | Work items | Register |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Character creation | done | The Census Office questions, race, face, hair, class and birthsign, with the install's class questions. | OpenMW 0.51 character generation; UESP Morrowind:Character Creation | tests/test_chargen_questions.py, tests/aga_quickchar_test.c, tests/aga_chargen_class_review_test.c. | - | - | - |
| The player's body and gear | partial | The player's hands and body in first and third person. | OpenMW 0.51 first and third person; the original's body parts | tests/test_player_parts.py, tests/aga_player_parts_test.c, tests/aga_saved_equipment_test.c. | Worn gear does not yet show on the hands and the body. | PLAYER-GEAR-VISUAL-59, FIRST-PERSON-WEAPONS-56 | - |
| Player movement | done | Walking, running, jumping, swimming, steps and collision on the original's movement rules. | OpenMW 0.51 player movement; UESP Morrowind:Movement | tests/aga_move_rules_test.c, tests/aga_step_rules_test.c, docs/PLAYER_MOVEMENT.md. | - | - | - |
| Attributes and skills | partial | The stat sheet with attributes, skills, health, magicka and fatigue, and the race and class numbers. | OpenMW 0.51 stats; UESP Morrowind:Skills, Morrowind:Attributes | tests/aga_statswin_test.c, tests/test_race_stats.py. | Skills do not yet rise with use. | LEVEL-UP-58 | - |
| Levelling | partial | The level-up rules and the attribute multipliers. | OpenMW 0.51 levelling; UESP Morrowind:Level | tests/aga_levelup_rules_test.c, tests/test_levelup.py (the rules); the level-up box is not in. | The level-up box after rest and skill advancement by use. | LEVEL-UP-58 | - |
| Rest and wait | partial | The rest rules and the wait dialog. | OpenMW 0.51 rest and wait; UESP Morrowind:Resting | tests/aga_rest_rules_test.c, tests/aga_wait_test.c, docs/RESTING.md. | Resting heals and levels up and waiting only passes time, both refused near enemies: the in-game behaviour is not yet proven end to end. | REST-WAIT-59 | - |
| Saved games | partial | Saves keep the character, the position, equipment, the journal, topics and the changes made to actors and objects. | OpenMW 0.51 saved games | tests/aga_save_changes_test.c, tests/aga_inventory_save_test.c, tests/test_save_changes.py. | Moved or taken objects, doors and locks, script variables and the calendar are not all kept; no default save titles; no import of the original's saves. | SAVEGAME-COMPLETE-57, SAVE-NAMES-57, CELL-CHANGES-59, SAVE-IMPORT-57 | - |

### Combat, death and the law

| System | State | What | Reference | Proof | Missing | Work items | Register |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Weapons | partial | Melee swings and the hit rules against actors, with the weapon kit. | OpenMW 0.51 combat; UESP Morrowind:Combat | tests/aga_combat_test.c, tests/aga_combat_rules_test.c, tests/aga_weapon_kit_test.c. | Weapons of every type in first and third person, bows and thrown weapons, and shields. | WEAPONS-57, FIRST-PERSON-WEAPONS-56 | - |
| Death and bodies | done | Actors die, the player's death is handled, and bodies are opened and looted through the container strip. | OpenMW 0.51 death and corpse inventory | tests/aga_player_dead_test.c, tests/aga_levelled_contents_test.c; CORPSE-LOOT-60 gated in v0.0.60-dev3. | - | CORPSE-LOOT-60, CONTAINER-LEVELLED-CONTENTS-60 | - |
| Crime and the law | missing | Theft, attacks and trespass seen by witnesses raise a bounty; guards arrest, fine or jail. | OpenMW 0.51 crime handling; UESP Morrowind:Crime | - | - | CRIME-59 | - |
| Sneaking and stealing | missing | Sneak, pickpocketing and the Security skill with locks and probes. | OpenMW 0.51 sneak and security; UESP Morrowind:Sneak, Morrowind:Security | - | - | CRIME-59, MWSCRIPT-TRAY-SMOKE-58 | - |

### Magic

| System | State | What | Reference | Proof | Missing | Work items | Register |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Spell effects | partial | Magic effects applied to actors over their duration, the active effects display, and the effect rules. | OpenMW 0.51 magic effects; UESP Morrowind:Magic Effects | tests/aga_magic_rules_test.c, tests/test_magic_effects.py, docs/MAGIC_EFFECTS.md, docs/HUD_ACTIVE_EFFECTS.md. | Effects over time on actors and the script calls that wait for them. | SPELL-EFFECTS-57 | - |
| Player casting | missing | Ready a spell, pay the magicka, roll to succeed, deliver Self, Touch and Target effects. | OpenMW 0.51 spell casting; UESP Morrowind:Magic | - | - | PLAYER-CASTING-59 | - |
| Spellmaking | missing | Making spells at a spellmaker. | OpenMW 0.51 spellmaking; UESP Morrowind:Spellmaking | - | - | - | - |
| Alchemy | missing | Making potions from apparatus and ingredients. | OpenMW 0.51 alchemy; UESP Morrowind:Alchemy | - | - | - | - |
| Enchanting | missing | Enchanting items with soul gems. | OpenMW 0.51 enchanting; UESP Morrowind:Enchant | - | - | - | - |

### Items, containers and trade

| System | State | What | Reference | Proof | Missing | Work items | Register |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Inventory | partial | The inventory window with the item list, the preview and the equip rules; drop and pick up. | OpenMW 0.51 inventory; UESP Morrowind:Inventory | tests/aga_inventory_test.c, tests/aga_inventory_ui_test.c, tests/aga_focus_pickup_test.c, docs/INVENTORY.md. | A test that every kind of item can be dropped, picked up again and kept across a save. | DROP-ALL-TEST-58 | - |
| Containers | partial | Baskets, crates, barrels and chests open into a strip of their items to take or put back, with levelled contents rolled by the original's rules. | OpenMW 0.51 containers; UESP Morrowind:Containers | tests/aga_container_strip_test.c, tests/aga_levelled_contents_test.c, docs/CONTAINERS.md. | The container window's in-game check and the per-area tables for container data. | CONTAINER-WINDOW-59, AREA-TABLES-60 | - |
| Barter | missing | Buying and selling with prices from disposition and Mercantile, both inventories, offer and haggle. | OpenMW 0.51 trading; UESP Morrowind:Mercantile | - | - | BARTER-FULL-58 | - |
| Training | partial | Paid training in the dialogue window. | OpenMW 0.51 training service; UESP Morrowind:Training | tests/aga_dial_test.c (the services row of docs/DIALOGUE_FEATURES.md). | A trained skill does not yet count toward the level. | LEVEL-UP-58 | - |

### Dialogue, voices, journal and factions

| System | State | What | Reference | Proof | Missing | Work items | Register |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Dialogue | partial | The conversation window, topics, conditions, disposition, persuasion and services; the headline of its own tracker is shown below. | OpenMW 0.51 dialogue; UESP Morrowind:Dialogue | docs/DIALOGUE_FEATURES.md and tests/test_dialogue_features.py. | The rows of docs/DIALOGUE_FEATURES.md that are not done. | DIALOGUE-COMPLETE-58, DIALOGUE-LIVE-STATE-58 | - |
| Voices | partial | Character voice lines and creature sounds mapped into the world and heard in game. | the original's voice files; OpenMW 0.51 sound handling | docs/VOICE_FEATURES.md and tests/test_voice_features.py. | Rows of the voice tracker not yet heard in game. | VOICE-COVERAGE-58 | - |
| Journal and quests | partial | The journal with dated entries and the quest book; journal indexes kept by the dialogue and the scripts. | OpenMW 0.51 journal; UESP Morrowind:Journal | tests/aga_journal_state_test.c, tests/aga_questbook_test.c, tests/aga_jhist_test.c. | Topic names in quest entries are not links yet; quests run only as far as the scripts do. | JOURNAL-QUEST-LINKS-58, MWSCRIPT-MORE-57 | - |
| Factions and ranks | partial | Faction membership, rank and reputation read by the dialogue conditions and the scripts. | OpenMW 0.51 factions; UESP Morrowind:Factions | docs/DIALOGUE_FEATURES.md (rank requirement conditions live); tests/test_dialogue_lut.py. | Joining, advancing and expelling through play, not only through script calls. | MWSCRIPT-MORE-57 | - |

### MWScript

| System | State | What | Reference | Proof | Missing | Work items | Register |
| --- | --- | --- | --- | --- | --- | --- | --- |
| MWScript compiler | done | All 1,207 scripts of the three masters compile to the compact bytecode, with the original's quirks kept. | OpenMW 0.51 script compiler (behaviour only); UESP Morrowind:Scripting | tests/test_mwscript.py; docs/MWSCRIPT_BYTECODE.md (1,207 of 1,207 compiled, none refused). | - | - | - |
| MWScript functions | partial | The compiler knows 504 functions and instructions; the interpreter and the host carry out 229 of them, the rest compile to the not-yet call. The game's scripts use 251 distinct functions. | OpenMW 0.51 script extensions (behaviour); UESP Morrowind:Script Functions | tools/mwscript/functions.py (the table and its RUN and HOST sets); tests/test_mwscript.py. | 275 table functions are not carried out. How many of the 251 used ones are among them is pending a measurement run. | MWSCRIPT-MORE-57, ACTORS-ON-57 | - |
| Scripts that run whole | partial | 957 of the 1,207 scripts run whole today: every function they call is carried out. | the original scripts run under OpenMW 0.51 | docs/MWSCRIPT_BYTECODE.md (measured 30 October 2026); tests/test_mwscript.py. | 250 scripts call at least one function that is not carried out. The census tray smoke test is not run. | MWSCRIPT-MORE-57, MWSCRIPT-TRAY-SMOKE-58, ACTORS-ON-57 | - |

### Sound, music and the interface

| System | State | What | Reference | Proof | Missing | Work items | Register |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Music | done | The soundtrack by region and situation, playing through loads. | OpenMW 0.51 music handling; the original's soundtrack | tests/test_music.py, tests/music_player_test.c, tests/aga_loading_audio_test.c. | - | - | [AUDIO-LOAD-29](bugs/AUDIO-LOAD-29.md) |
| Sound effects | partial | Door, footstep, ambient and spell sounds from the sound records. | OpenMW 0.51 sound handling | tests/aga_door_audio_test.c, tests/aga_sfx_names_test.c, tests/aga_audio_levels_test.c. | Area sounds from the markers, and the creature and combat sounds that are not yet mapped. | SOUND-MARKERS-58, VOICE-COVERAGE-58 | - |
| HUD and messages | done | The health, magicka and fatigue bars, the crosshair and aim box, the message line and message boxes, the active effects. | OpenMW 0.51 HUD | tests/aga_hud_test.c, tests/aga_msgbox_test.c, docs/HUD.md. | - | - | - |
| Menus and options | partial | The front menu, options, key bindings and the console. | OpenMW 0.51 settings and menus | tests/aga_menu_test.c, tests/aga_keymap_test.c, tests/aga_console_test.c. | A performance and quality preset and a screen-mode choice; new defaults do not reach existing settings files. | PERF-PRESET-57, SCREEN-MODE-59, CONFIG-DEFAULTS-UPGRADE-57 | - |
| The in-game map | partial | A world map and a local map. | OpenMW 0.51 map window; UESP Morrowind:Map | tests/aga_map_focus_test.c, docs/WORLD_MAP_AND_JOURNAL.md. | The original-style map with explored areas, the local map and the landmark markers. | INGAME-MAP-ORIGINAL-57 | - |
