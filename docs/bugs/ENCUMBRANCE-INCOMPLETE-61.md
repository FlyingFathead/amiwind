# ENCUMBRANCE-INCOMPLETE-61: Carry weight is only half there: no burden shown, no message over the limit, Burden and Feather do nothing, and the kinds of item are capped

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 5 November 2026, in v0.0.61-dev1 |
| Where | Engine: the item table (aw_state.h), the movement inputs (aw_move.c), the inventory window |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.61-dev1 (last seen) |
| Severity | medium: the player sees no burden and no reason when the character stops; magic cannot change the load; a session of collecting runs into the kind limit |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.61-dev1 |
| From commit | source 374d59b, engine 374d59b, CHIM world 374d59b |
| CHIM engine version | CHIM 0.2.2, engine 374d59b, world format unknown |
| Unknown because | found in a review of the engine source of the delivered dev build |
| Platform or emulator | not in game (found in a review of the engine source) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.61-dev1 (6 November 2026)._

<!-- contents start -->
## Contents

- [Status: 5 November 2026](#status-5-november-2026)
- [Symptom](#symptom)
  - [The movement rules against OpenMW 0.51, term by term](#the-movement-rules-against-openmw-051-term-by-term)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 5 November 2026

Open, v0.0.61 (tracker INVENTORY-ORIGINAL-LIMITS-61), repaired on the v0.0.61 line. Fixed once a numbered build
with the repair is checked in game.

## Symptom

In the original game the only limit on what the player carries is its weight: the load (the items' weight, plus
Burden, less Feather) against the capacity, Strength times the game setting fEncumbranceStrMult (5). The inventory
window shows it as a bar
("carried / maximum"), and a player over the limit cannot move and sees the game's own line "You are
over-encumbered." There is no limit on the number of kinds of item.

In AmiWind v0.0.61-dev1:

- the number of kinds of item is the limit that bites: 32 kinds in v0.0.61-dev1 (128 on the v0.0.61 line since the
  stopgap of COLLECT-CAPACITY-REJECTED-60), after which every new kind is refused whatever it weighs;
- the burden is not shown anywhere (the inventory window's bar is part of UI-INVENTORY-ORIGINAL-LAYOUT-42);
- the movement rules do apply the weight (slower with more load, no movement over the limit), but the player gets no
  message and cannot tell why the character stands still;
- Burden and Feather have no way in: their magnitudes are always 0;
- the carried weight is found by hashing every carried kind's name and count on every movement call (three times a
  frame) and, after any change, by reading every carried kind's record again, during play.

### The movement rules against OpenMW 0.51, term by term

Checked on 5 November 2026 (`engine/aga/src/aw_move_rules.c` against OpenMW 0.51 `mwclass/actor.cpp`,
`mwclass/npc.cpp`, `mwclass/actor.hpp`, `mwworld/class.cpp`, `mwmechanics/character.cpp`,
`mwphysics/physicssystem.cpp`); the 30 game settings the rules read come from the master file at build time, and the
fallback table used only for an image without them equals the master's values. n is the load over the capacity.

| Term | OpenMW 0.51 | AmiWind | Same |
| --- | --- | --- | --- |
| Load | items' weight + Burden (not in god mode) - Feather, at least 0 | the same; Burden and Feather were always 0 | yes (no effects yet) |
| Capacity | modified Strength x fEncumbranceStrMult | the same | yes |
| n | 0 with no load; 1 + 1e-6 with no capacity; else load / capacity | the same | yes |
| Walk | fMinWalkSpeed + 0.01 x Speed x (fMaxWalkSpeed - fMinWalkSpeed), x (1 - fEncumberedMoveEffect x n), at least 0, x fSneakSpeedMultiplier sneaking | the same | yes |
| Run | walk x (0.01 x Athletics x fAthleticsRunBonus + fBaseRunMultiplier) | the same | yes |
| Over the limit | n > 1: speed 0, no jump | the same | yes |
| Levitation | fMinFlySpeed + 0.01 x (Speed + Levitate) x (fMaxFlySpeed - fMinFlySpeed), x (1 - fEncumberedMoveEffect x n), at least 0 | the same (Levitate always 0 so far) | yes |
| Swimming | walk or run x (1 + 0.01 x Swift Swim) x (fSwimRunBase + 0.01 x Athletics x fSwimRunAthleticsMult) | the same | yes |
| Werewolf run | x fWereWolfRunMult | none | no werewolves (Bloodmoon is not in) |
| Fatigue per second | only within the capacity: sneaking fFatigueSneakBase + n x Mult; in water walking or running SwimWalk / SwimRun Base + n x Mult; running fFatigueRunBase + n x fFatigueRunMult; none in god mode | the same | yes |
| Jump | 0 over the limit; (fJumpAcrobaticsBase + (a / 15) ^ fJumpAcroMultiplier + 3 b fJumpAcroMultiplier + 64 Jump) x (fJumpEncumbranceBase + fJumpEncumbranceMultiplier x (1 - n)) x run multiplier x fatigue term, + 8.96 x 69.99, / 3 | the same | yes |
| Jump fatigue | fFatigueJumpBase + min(1, n) x fFatigueJumpMult, not in god mode | the same | yes |
| The message | sNotifyMessage59 while trying to move or jump over the capacity | none | no: missing |
| The bar | ceil(load) / capacity above the inventory picture | none | no: missing |

So the formulas were right; what was missing is the kind limit lifted, the message, the bar and the way in for
Burden and Feather. The native test `tests/aga_move_rules_test.c` checks every row at a load by values worked out by
hand.

## Where

The item table (`engine/aga/src/aw_state.h`, `AW_ITEM_VALUES`), the movement inputs (`engine/aga/src/aw_move.c`,
`carried`, `AW_MovePlayerInputs`) and the inventory window (`engine/aga/src/aw_worldui.c`).

## How it happened

The inventory was first built as a list of counts in the same fixed table as the globals and quest stages; the
movement rules (PLAYER-MOVEMENT-STATS-PARITY-39) took the weight from it later, but the rest of the original's
encumbrance (the bar, the message, the spell effects) was never written down as missing, so nothing tracked it.

## Why it was not caught

The game features table had no row for carry weight, and the register had only the missing bar inside a layout entry.

## Reproduction

Always: carry more than Strength times 5 (for example `dbg inventory grant` of heavy armour) and try to walk; or carry
32 kinds of item in v0.0.61-dev1 and try to pick up a new one.

## Repair

Done on the v0.0.61 line (5 November 2026):

- The item table has no fixed number of kinds: 24-byte rows (a hash of the id, the count, condition, charge and
  weight, the name's place and the marks) in blocks of 32 from the game's memory, each id once in a name pool; the
  globals and quest stages are back to their own 32 rows. A new kind takes a row at 0 first. A save writes what is
  there (feature bit 512 past 32 kinds, a mark word per 32 kinds); the saves of v0.0.61-dev1 (32 kinds) and of the
  128-kind table (feature bit 256) still load. The inventory window keeps a 40-byte sort key per kind and the whole
  record only for the rows in view and one page either side; the container strip's inventory side is as long as
  the kinds carried.
- The carried weight is a running total in the item table, changed by every count change and summed again exactly
  when a place loads; the movement rules read it (no hashing per frame).
- The inventory shows the blue bar with load/capacity above the picture; trying to move or jump over the capacity
  shows the game's line (sNotifyMessage59, written into the image by the builder), raised again every 2 s.
- `AW_EncumbranceSetEffects(burden, feather)` (aw_move.h) is the call the spell effects make.

The plan it followed: an item table without a fixed number of kinds, growing in blocks from the game's memory
as needed (weight is the only limit, as in the original); the carried weight kept as a running total when items come
and go, never added up per frame; the bar in the inventory window; the game's own message when the player tries to
move over the limit; a function the spell effects call to set Burden and Feather. Rules from OpenMW 0.51
(`mwclass/actor.cpp` getEncumbrance, `mwclass/npc.cpp` getCapacity, `mwworld/class.cpp` getNormalizedEncumbrance,
`mwgui/inventorywindow.cpp` the bar, `mwgui/windowmanagerimp.cpp` the message), own code.

## Verification

Native tests: every movement term at a load against values worked out by hand (`tests/aga_move_rules_test.c`); the
running total through adds, removals and 400 kinds, summed again the same (`tests/aga_inventory_test.c`); the
message, its repeat and the Burden and Feather call in the movement (`tests/aga_move_test.c`); 400 kinds collected,
granted and taken (harvest, weapon kit, debug torch, pickup); 400 kinds with marks on the last row through a save
and back, a 128-kind save of feature bit 256 loaded (`tests/aga_inventory_save_test.c`); the bar's place and numbers
(`tests/aga_inventory_ui_test.c`).

In game (FS-UAE, JIT, 32 MB Fast, the v0.0.61-dev1 image with this line's engine, 6 November 2026): 399 kinds carried in 18,228 bytes of item table; the bar in the inventory read 8 of 300 at the start, 59 of 300 after the grants and 1858 of 300 with a heavy item taken; moving at that load gave the game's box "You are over-encumbered." and no movement (walk, run and swim 0); a quicksave of 399 kinds came back with the same load (1858.45); the inventory opened with no frame over half a second, and the reload's longest frame was 2.0 s, the same as with an empty inventory. Saves of the v0.0.61-dev1 engine (27 kinds) and of the 128-kind engine with feature bit 256 (106 kinds) loaded, and a resave of 107 kinds came back.

## Prevention

A row for carry weight in the game features table (docs/GAME_FEATURES.md), with its proof and what is missing.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- ACTOR-HELLO-CLAMPED-61 (no report page): An actor's Hello value is cut to 255 although the record holds it in 16 bits (up to 300 in the game data)
- ACTOR-STATS-FAR-FALLBACK-61 (no report page): A being outside the loaded areas still reads its stats from the island-wide actor table
- [ACTOR-STATS-SCATTERED-61](ACTOR-STATS-SCATTERED-61.md): Actor stats are kept in five separate copies, each covering only some beings and some stats
- ACTORS-TOWN-ROOM-RETURN-59 (no report page): A town resident killed before entering a room is alive again on the way back out
- ALCHEMY-MISSING-61 (no report page): Alchemy is missing: no alchemy window, potions cannot be drunk and ingredients cannot be eaten
- ARENA-MERGE-54 (no report page): Requested: one arena mode: the main game's arena minigame and the combat playground merged, with NPC against NPC fights to watch
- ATTACK-TYPE-ANIMS-62 (no report page): With a sword and best attack off, slash, chop and thrust play the same attack animation
- [AW-20260928-10](AW-20260928-10.md): Interior door animation and sound missing
- [AW-20260928-12](AW-20260928-12.md): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- [AW-STATE-32-SLOTS-48](AW-STATE-32-SLOTS-48.md): The game state table holds 32 globals, 32 quests and 32 items; the game has 143 globals and 318 journal topics
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- BC-TREE-FLOATING-60 (no report page): A Bitter Coast tree near cell -2,-8 floats above the ground
- [CARRIED-RECORDS-SEARCH-PER-KIND-61](CARRIED-RECORDS-SEARCH-PER-KIND-61.md): With hundreds of kinds of item carried, a place load takes up to a minute: one catalogue search per kind
- CAST-ANIM-THIRD-PERSON-62 (no report page): The player's third-person body plays no spellcasting animation when casting
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- CENSUS-INTRO-NOT-SCRIPTED-62 (no report page): Opening: the Census and Excise Office and its courtyard run on hand-written story steps, not the game's own character-creation scripts
- [CENSUS-INTRO-SCRIPTS-62](CENSUS-INTRO-SCRIPTS-62.md): The opening in the Census and Excise Office and its courtyard runs on hand-written rules, not on the game's own character-creation scripts
- CENSUS-OFFICE-HOLDS-OFF-64 (no report page): In the census office the clerk's message boxes do not show and the player is not held during his talk
- CENSUS-OFFICE-NO-EXIT-64 (no report page): The player cannot leave the census office after the registration
- CENSUS-TABLE-TAKE-GRAB-HIM-62 (no report page): Census and Excise Office: taking an item from the table in front of Sellus Gravius makes a guard call out a theft line
- CENSUS-THEFT-NO-ARREST-65 (no report page): A theft in the census office after the papers brings no guard and no arrest talk
- CHARGEN-INVENTORY-LOCKED-60 (no report page): After character creation the inventory key does not open the inventory
- CHARGEN-NO-STARTING-CLOTHES-60 (no report page): The player has no starting clothes after character creation, also after leaving the Census and Excise Office
- CHARGEN-TUTORIAL-ITEM-MESSAGES-59 (no report page): Character creation: taking the bread, crab meat, candle, lockpick, whiskey, note or dagger in the Census Office shows no tutorial message
- CHARGENSTATE-START-VALUE-63 (no report page): A new game sets the CharGenState global to 1, where the original opening script sets it to 10
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- [CHIM-FRAME-SOURCE-CONVERSION-59](CHIM-FRAME-SOURCE-CONVERSION-59.md): On CHIM frame maps the conversion to the game's coordinates says no for most engine callers
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COLLECT-CAPACITY-REJECTED-60](COLLECT-CAPACITY-REJECTED-60.md): After looting a corpse, picking up items fails with an inventory or state capacity message
- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button
- [COMBAT-CHASE-CHIM-STUCK-46](COMBAT-CHASE-CHIM-STUCK-46.md): Actors spawned on a CHIM frame without a baked ground point stay in the air: the spawn floor snap runs before the streamed ground under them is collidable (the chase itself works)
- [COMBAT-DAEDROTH-NO-HIT-51](COMBAT-DAEDROTH-NO-HIT-51.md): A daedroth outside the Azura s Coast stronghold cannot be punched: the blows pass through it; its runtime health reads 0.0
- [COMBAT-FATIGUE-HEALTH-DAMAGE-39](COMBAT-FATIGUE-HEALTH-DAMAGE-39.md): Clarify Eldafire bare-fist fatigue damage versus armed guard health damage
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- COMBAT-HIT-CHANCE-EFFECTS-62 (no report page): The melee hit chance leaves out Fortify Attack, Blind, Sanctuary, Chameleon and Invisibility, and the player's attributes are counted without their Fortify and Damage
- COMBAT-HIT-CONTACT-CONE-62 (no report page): The player's melee swing strikes only the actor exactly under the crosshair, not the nearest one in the original's hit cone, so flyers and small creatures are hard to reach
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- COMBAT-NO-AGGRO-SHOWN-51 (no report page): Punching a worshipper shows no hostility when the first blow lands
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NODICE-READOUT-40](COMBAT-NODICE-READOUT-40.md): No-dice combat readout labels living targets already down
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- COMBAT-SHIELD-EFFECT-NO-ARMOR-61 (no report page): A Shield effect on the player does not lower the damage of the blows that land on the player
- COMBAT-STYLE-PRESETS-62 (no report page): Requested: combat style presets for fights, such as the dice and best-attack choices, chosen before a fight
- COMBAT-THINK-COST-68040-54 (no report page): On the slow 68040 preset one combat decision step (think) costs 34 ms with one fighter and 44 ms with four
- [CONTAINER-LEVELLED-CONTENTS-EMPTY-59](CONTAINER-LEVELLED-CONTENTS-EMPTY-59.md): Containers whose contents are levelled lists open empty
- [CONTAINER-STRIP-OPEN-MANY-KINDS-61](CONTAINER-STRIP-OPEN-MANY-KINDS-61.md): With hundreds of kinds of item carried, opening a body or a container holds the game for about 10 seconds
- [CORPSE-INVENTORY-NOT-OPENABLE-59](CORPSE-INVENTORY-NOT-OPENABLE-59.md): Bodies of dead NPCs and creatures cannot be opened to take what they carried
- CREATURE-BIPED-ANIMS-62 (no report page): An actor without walk or attack animations glides and does not fight back (ash slave, corprus stalker, the arena NPC Zennammu)
- CRIME-FINE-GOLD-NOT-TAKEN-62 (no report page): Paying a guard's fine clears the bounty but takes no gold: the answer's RemoveItem of the bounty's worth of gold leaves the purse as it was
- CRIME-ONLY-THEFT-62 (no report page): Only a theft was a crime: attacking or killing someone in front of witnesses raised no bounty, guards never came to arrest, and the guards' answers to pay the fine or go to jail did nothing
- CRIME-SAVE-PURSUERS-62 (no report page): The marks a crime leaves on people are lost on loading a save: guards forget a pursuit, the Alarmed mark and the crime's disposition change go, and a murder is no longer known
- DBG-ARENA-PICKER-62 (no report page): Requested: dbg arena offers a choose-your-opponent list of every NPC and creature
- DBG-SUBWORD-ROUTE-DROPPED-62 (no report page): dbg camera fpview/hands/parts and dbg cast casting/now/ready/spell/start/strike reach their command without their own word
- DBG-SUPERSPEED-62 (no report page): A bare dbg superspeed does not toggle it, and stamina drains while it is on
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- DIALOGUE-AGGRO-62 (no report page): A robber whose answer ends in a threat does nothing once the talk closes
- DIALOGUE-CHOICES-62 (no report page): Dialogue choices are not shown as rows to pick, and the branch after a pick is not filtered as in the original
- DIALOGUE-GLOBAL-NAMES-CLASH-59 (no report page): Dialogue conditions on a global could read the wrong global name table
- DIALOGUE-RING-DISPOSITION-CHECK-60 (no report page): Disposition after handing Fargoth his ring needs checking against the original
- DIALOGUE-TOPIC-WHO-60 (no report page): Shargam gro-Shagdub answers "Who?" about Ralen Hlaalo right after naming him in his rumors
- [DOOR-LOAD-LOCKS-MISSING-51](DOOR-LOAD-LOCKS-MISSING-51.md): Load doors ignore the original game's locks: every door into a room opens, locked or not
- [DOOR-TRAPS-NOT-SPRUNG-55](DOOR-TRAPS-NOT-SPRUNG-55.md): Trapped doors and containers open without their trap
- DROP-CHIM-REFUSED-59 (no report page): Dropping an item on a streamed outdoor map is refused: Cannot place items in this area yet
- DROP-ROOM-BRUSH-ENTITY-59 (no report page): Dropping an item in a converted room is refused: Item path or footprint obstructed
- DROP-STACK-ONE-ROW-PER-UNIT-59 (no report page): Dropping a stack drops one piece per key press, each its own ground item, so the map's ground item limit (32) fills with single coins
- [DROPPED-LIGHT-NO-EFFECTS-61](DROPPED-LIGHT-NO-EFFECTS-61.md): A carriable light that is dropped shows no flame and gives no light where it lies
- ENDGAME-CHAMBER-COLLAPSE-63 (no report page): The ending in the Heart Chamber cannot play: the heart cannot play its death animation and the chamber's collapse is not animated
- ENEMY-HEALTH-BAR-62 (no report page): In a fight with a cliff racer the HUD shows no enemy health bar
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [EQUIP-ACTION-REGRESSION-62](EQUIP-ACTION-REGRESSION-62.md): Some weapons, armour and clothing show no Equip action in the inventory (the census office dagger reads "Actions unavailable for this item")
- EQUIP-SHARDAXE-REFUSED-61 (no report page): Equipping the iron shardaxe is refused while the iron longsword can be equipped
- FACTION-EXPEL-MESSAGE-64 (no report page): An expulsion from a faction shows no message to the player
- FACTION-STATS-PAGE-64 (no report page): The stats page shows no factions, ranks, reputation or bounty
- [FALL-LANDING-KNOCKDOWN-62](FALL-LANDING-KNOCKDOWN-62.md): A hard landing does not knock the player or an actor down, and an NPC's landing plays no landing sound
- [GODMODE-COMBAT-DAMAGE-61](GODMODE-COMBAT-DAMAGE-61.md): With god mode on, a fight's blows still take the player's health and kill the player
- GODMODE-LAVA-DEATH-62 (no report page): The player can die in a lava pool with god mode on
- GUARD-RESIST-ARREST-NOTHING-61 (no report page): Choosing to resist arrest in a guard's conversation does nothing: the guard does not attack
- [HAND-TO-HAND-NO-HIT-64](HAND-TO-HAND-NO-HIT-64.md): Fists rarely land and do almost nothing, even after the stats are raised during the fight
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md): Inventory catalogue lookup and name sorting use an equality-only comparison
- INVENTORY-CATALOGUE-PARTIAL-54 (no report page): The item catalogue holds Morrowind items only: no lockpicks, probes, repair tools, apparatus or carried lights
- INVENTORY-ITEM-MODEL-PATH-59 (no report page): The inventory catalogue refuses every item whose world model comes from the item model table (progs/items/)
- [INVENTORY-OPEN-COST-MANY-KINDS-61](INVENTORY-OPEN-COST-MANY-KINDS-61.md): With hundreds of kinds of item the inventory takes seconds to open, and every Tab reads the item file again
- JOURNAL-BOOK-32-QUESTS-59 (no report page): The journal book lists only the quests of the old 32-slot table, although every quest's stage is now kept
- JOURNAL-LOWER-INDEX-ENTRY-64 (no report page): A Journal command at or below the quest index adds no entry, no finished or restart mark and no notice
- LAVA-NO-DAMAGE-63 (no report page): Lava does no damage and is not drawn in the Red Mountain lava pool
- [LOADED-ITEMS-NOT-WEIGHED-61](LOADED-ITEMS-NOT-WEIGHED-61.md): After loading a save of another character the carried weight reads 0 until the next place load
- [MAP-MENU-BLOCKED-COURTYARD-65](MAP-MENU-BLOCKED-COURTYARD-65.md): In the opening the courtyard announces the map, but the map key stays blocked until the opening ends
- MARKS-SUMMON-CARRIERS-NOT-LIVE-63 (no report page): The guarded items whose taking summons a guardian are not live references, so the summon never comes
- MWSCRIPT-CELLCHANGED-VOLATILE-54 (no report page): CellChanged made the sound-marker scripts volatile: 85 percent of Vivec's per-frame script work
- MWSCRIPT-CONSOLE-LOCAL-NAMES-63 (no report page): Show and ShowVars cannot name a script's local variables: Show reads globals only, ShowVars lists the locals by slot number, and ToggleScripts flips the saved scripts switch
- MWSCRIPT-DATA-UNKNOWN-NAMES-48 (no report page): Four Bloodmoon scripts read names declared nowhere in the game data and do not compile
- MWSCRIPT-INERT-SEEN-62 (no report page): Scripts whose only effect is a message box, a door or item use they take over, or a local the dialogue reads were left out of the build as doing nothing
- MWSCRIPT-INTERIOR-PLACEMENTS-48 (no report page): Scripted placements in rooms that have no edict are not attached: the engine has no room identity to match them (3,612 of 4,907 bindings are in rooms)
- MWSCRIPT-LATER-MASTER-SCRIPT-61 (no report page): An object placed in Vvardenfell whose record gets its script from a later master is not attached
- MWSCRIPT-MISSING-FUNCTIONS-63 (no report page): Game scripts call MWScript functions the interpreter does not carry out yet: those calls do nothing and read 0 (69 scripts after the first v0.0.63 batch, most of them in Mournhold and Solstheim)
- MWSCRIPT-OLD-CONFIG-OFF-57 (no report page): An install whose saved config holds aw_mwscript 0 keeps compiled scripts off after the default turned on
- [MWSCRIPT-PLACE-NO-MODEL-62](MWSCRIPT-PLACE-NO-MODEL-62.md): A script cannot place an NPC or a creature whose record has no placed reference in Vvardenfell
- [MWSCRIPT-PLACE-OTHER-KINDS-62](MWSCRIPT-PLACE-OTHER-KINDS-62.md): A script cannot place an activator, a container or a levelled creature list yet
- MWSCRIPT-POSITIONCELL-NPC-62 (no report page): A script or a dialogue answer that moves an NPC or a creature to another place (PositionCell) does nothing
- [MWSCRIPT-POSITIONCELL-OUTDOOR-62](MWSCRIPT-POSITIONCELL-OUTDOOR-62.md): An NPC or a creature a script sends outdoors appears there only while its home area is loaded
- MWSCRIPT-REFUSED-SCRIPT-COUNT-58 (no report page): The compiled game scripts are refused at load since the dialogue result scripts joined the file: no script runs
- MWSCRIPT-ROTATE-NO-ENTITY-59 (no report page): A script's Rotate on a streamed outdoor object without an entity is not carried out: the object does not turn
- MWSCRIPT-STANDING-NOT-SAVED-57 (no report page): The players standing the scripts change (crime level, reputation, faction ranks, expelled marks, faction reputation) is not in saved games
- [MWSCRIPT-STATE-NOT-SAVED-48](MWSCRIPT-STATE-NOT-SAVED-48.md): The compiled scripts' values (globals, object and script locals, journal indexes) are not in saved games
- MWSCRIPT-STOPCOMBAT-UNWIRED-62 (no report page): A script's StopCombat never ended a fight: the combat layer's end of one actor's fight was never connected to it
- [MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61](MWSCRIPT-UNPLACED-RECORD-SCRIPTS-61.md): Scripts of records that are never placed in a cell (items carried, given or sold, actors from levelled lists) are compiled but never run
- [NEWGAME-OPENING-UNRESTRICTED-64](NEWGAME-OPENING-UNRESTRICTED-64.md): After New Game the opening runs as a free game: the dock guard stays idle on the pier, the race menu never opens, the pier and the census office hold nothing
- [NEWGAME-STATE-RESET-62](NEWGAME-STATE-RESET-62.md): A New Game started from the menu after playing leaves the fireplace of the Census and Excise Office unlit
- [OBJECT-ENABLE-NOT-DRAWN-65](OBJECT-ENABLE-NOT-DRAWN-65.md): Objects switched back on by a script stay invisible: the release papers in the census office can be read but are not drawn on the table
- OPENING-CAPTAIN-HINT-SUBTITLE-63 (no report page): The hint about talking to the captain shows as a subtitle instead of the original message box with an Ok button
- OPENING-HOLDS-OFF-NEWGAME-64 (no report page): A New Game clears the opening's state right after setting it: the dock guard does not meet the player and no race can be chosen
- OPENING-SHIP-BLOCKER-NOT-CONVERTED-63 (no report page): The invisible blocker inside the prison ship, one of the opening's 23 blockers, is not converted; the 22 outdoor ones are
- OPENING-SHIP-GUARD-STEPS-63 (no report page): On the prison ship the guard waits for the cellmate's warning before he speaks, and the movement hint is a box to close with Enter instead of the original message box
- [OPENING-VANITY-CAMERA-64](OPENING-VANITY-CAMERA-64.md): The idle camera orbit and the view switch run on the prison ship and the pier before the race is chosen
- OPENING-WEATHER-NOT-CLOUDY-63 (no report page): A new game does not start with the Bitter Coast weather set to cloudy, as the original opening script does
- PERSUASION-BROKEN-62 (no report page): Persuasion in dialogue does nothing: Admire and Intimidate return to the topic list, Taunt shows nothing
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- PICKUP-PLACED-E-NO-TAKE-58 (no report page): The activate key on a placed item in reach takes nothing
- PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59 (no report page): Outdoors no placed items are drawn after a teleport or load: the table is read before the player stands at the arrival
- PLACED-ITEMS-ROOM-RESET-59 (no report page): Entering a room with placed items drawn resets the machine to the boot screen
- PLACED-PIT-AXE-NO-FOCUS-61 (no report page): The iron shardaxe in the Seyda Neen pit is drawn but shows no item box and cannot be taken
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- PLAYER-FORTIFY-END-AS-DAMAGE-61 (no report page): When a Fortify Attribute effect on the player ends, the character sheet keeps it as a raised modifier and records the drop as damage
- PLAYER-HEALTH-OVER-MAX-63 (no report page): The player starts with health above its maximum (100 of 40) and restoring the stats keeps it there
- [PLAYER-JUMP-ORIGINAL-RULES-48](PLAYER-JUMP-ORIGINAL-RULES-48.md): The jump height and in-air control are still Quake's, not the original's Acrobatics, load and fatigue rules
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue
- [PLAYER-READY-MOVEMENT-39](PLAYER-READY-MOVEMENT-39.md): Third-person player cannot move with fists drawn
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- [PLAYER-START-SPELLS-NOT-KNOWN-61](PLAYER-START-SPELLS-NOT-KNOWN-61.md): Character creation never puts the race, birthsign and class spells and abilities on the player record, so they cannot be cast or apply
- PLAYER-WALK-SPEED-SLOW-51 (no report page): The starting walk speed feels very slow; check it against the original and OpenMW
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RACE-RESIST-NOT-ON-SPELL-DAMAGE-64 (no report page): A race ability that resists an element does not reduce spell damage of that element
- READY-MAGIC-SHOWS-WEAPON-65 (no report page): Readying magic (R by default) raises the equipped weapon instead of the spell-casting hands
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- RESIST-NORMAL-WEAPONS-61 (no report page): Ghosts and other creatures that resist normal weapons take full damage from ordinary weapons, with no "no effect" message
- REST-CENSUS-NO-CELL-ID-61 (no report page): The rest window offers Rest in the Census and Excise Office, a cell the game marks as no sleeping
- REST-OWNED-BED-ALWAYS-REFUSED-62 (no report page): Someone else's bed was always refused; in the original sleeping in it is a crime only when someone sees it
- SAVE-ACTOR-BLOCK-OVERFLOW-59 (no report page): A full actor record pool (128 actors) can exceed the save's 32 KB actor block, which would refuse the save (calculated, not measured)
- SAVE-CHANGES-FULL-REFUSES-SAVE-59 (no report page): When the world change list is full (2,048 entries for all actors and objects), the whole save is refused and the previous one kept
- SAVE-EFFECTS-BLOCK-SIZE-61 (no report page): Loading a save with a spell effect active loses the effects and the made spells, enchanted items, soul gems and other blocks saved after them
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SAVE-LAVA-DEATH-LOOP-38](SAVE-LAVA-DEATH-LOOP-38.md): Lava fall can leave an autosave that reloads into repeated death
- SAVE-TAKEN-DISABLED-ONE-FLAG-59 (no report page): A taken object and an object a script disabled share one flag in the save, so one cannot be told from the other
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- SCRIPT-ENABLED-ACTOR-NOT-DRAWN-62 (no report page): An actor a script enables in a loaded area is not drawn: the falling mage near Seyda Neen falls and dies unseen, his body searchable but invisible
- SCRIPT-LOOP-SOUND-DISABLED-OBJECT-61 (no report page): A looping script sound keeps playing after a script disables its object
- [SCRIPTED-EVENT-FALLING-MAGE-61](SCRIPTED-EVENT-FALLING-MAGE-61.md): The falling mage north of Seyda Neen does not fall: he is in the world from the start and his scripted fall does not run
- [SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62](SCRIPTED-EVENT-PAST-DRAW-DISTANCE-62.md): The falling mage near Seyda Neen plays out past the default draw distance: on his platform and for most of his fall he is too far up to be drawn from anywhere the player can stand when his event starts
- SCROLL-CAST-MISSING-64 (no report page): Scrolls cannot be cast: a scroll opens like a book and its spell never takes effect
- SELLUS-GRAVIUS-GREETING-ONLY-64 (no report page): Using Sellus Gravius gives only his greeting line instead of his dialogue
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- SERVICE-REFUSAL-UNCLOTHED-60 (no report page): Arrille refuses to barter at disposition 80 (player without clothes)
- SKILL-BOOKS-MISSING-62 (no report page): Reading a skill book does not raise its skill: the original raises it by one on the first read
- SKILL-RAISE-NOT-SEEN-62 (no report page): In a playtest of v0.0.61 no skill was ever seen to rise: no skill-increased line and no sound in normal play
- SPELL-EFFECTS-TABLE-CUT-64 (no report page): Game spells cast nothing: the actor table read only the first 32 sections of the compiled scripts file
- STEAL-WITNESSED-NO-CRIME-60 (no report page): Taking an owned item in full view of its owner or other people has no consequence
- SWEEP-ARENA-PIT-TWO-FAIL-54 (no report page): dbg sweep reports two failing entities in the Vivec Arena Pit (map vai000) in every session of the Arena Pit images
- TAKEN-LIGHT-FLAME-STAYS-60 (no report page): Picking up a lit candle leaves its flame floating where it stood
- [TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61](TAKEN-LIGHT-OUTDOOR-EFFECTS-UNLINKED-61.md): The flames and night lights of carriable lights outdoors are not tied to the item
- TAKEN-LIGHT-OUTDOORS-NOT-TAKEN-61 (no report page): A carriable light placed outdoors (a lantern in Seyda Neen) cannot be taken
- TALK-PROMPT-NOT-TALKABLE-54 (no report page): The Talk prompt shows for any target with a voice string: hostile, dead, knocked out or without dialogue
- THIRDPERSON-ANIMS-AUDIT-62 (no report page): Third-person actions are not all mapped to the original's animation groups
- TORCH-HIDES-HELM-62 (no report page): Holding a torch makes the worn helm disappear from the third-person body and the inventory figure; it returns when the torch is put away
- TRAVEL-SERVICES-CHIM-51 (no report page): Silt strider rides between towns do not work: travel knows only the old Seyda Neen and Balmora town maps, not the CHIM world, and none of the other routes
- UI-HUD-TOGGLE-KEY-51 (no report page): Requested: a key combination (for example Ctrl+Alt+H) that hides and shows the whole HUD in game, the crosshair with it
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete
- [UNDERWATER-BREATH-62](UNDERWATER-BREATH-62.md): Underwater there is no breath meter and no drowning, and Water Breathing is not applied
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- [WATER-GAMEPLAY-PARITY-38](WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification
- WEAPON-STRIKE-ENCHANT-NOT-CAST-61 (no report page): A weapon's Cast When Strikes enchantment is not cast when the weapon hits
- WEREWOLF-BODY-NOT-DRAWN-63 (no report page): A player turned into a werewolf by a script keeps his own body: the werewolf model is not drawn
- WEREWOLF-RUN-SPEED-63 (no report page): A player in werewolf form runs at his normal run speed: the werewolf run multiplier is not applied
- WORLD-BUTTONS-62 (no report page): Buttons and levers that should act do nothing, for example the Ghostgate gate buttons on both sides
- WORLD-OBJECT-STATE-NOT-SAVED-59 (no report page): World objects taken or moved are not remembered: they come back when the cell or room reloads, and saves do not keep them

Related bugs in other categories:

- INVENTORY-BURDEN-TEXT-UNREADABLE-61 (no report page): The carried and maximum weight on the inventory burden bar cannot be read
- [UI-INVENTORY-ORIGINAL-LAYOUT-42](UI-INVENTORY-ORIGINAL-LAYOUT-42.md): The inventory lacks the original encumbrance bar, armour rating and item icon grid

<!-- END GENERATED CATEGORY -->
