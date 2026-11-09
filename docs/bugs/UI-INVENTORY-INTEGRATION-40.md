# UI-INVENTORY-INTEGRATION-40: Inventory integration and safe world placement remain incomplete

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:full-suite |
| First noticed | 14 October 2026, in v0.0.40-dev1 |
| Where | Inventory runtime placement, map budgets, command routing and integration fixtures |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.40-dev1 (last seen) |
| Severity | high: Unsafe admission can lose items or exhaust engine tables; full-game drop placement remains unavailable. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.40-dev1 |
| From commit | source 7a783e0, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format unknown |
| Unknown because | Exact native diagnostic source and engine are hash-bound privately; separate engine/world commits are unknown. Later catalogue/layout repairs need a new target/native gate. |
| Platform or emulator | FS-UAE native Amiga diagnostic and Linux automated checks |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Combined validation, 14 October 2026](#combined-validation-14-october-2026)
- [Native catalogue failure, 14 October 2026](#native-catalogue-failure-14-october-2026)
- [Follow-up full-suite integration failure, 14 October 2026](#follow-up-full-suite-integration-failure-14-october-2026)
- [Scoped subsequent native inventory observation, 14 October 2026](#scoped-subsequent-native-inventory-observation-14-october-2026)
- [Actual harvest reaches inventory; ingredient resources missing, 14 October 2026](#actual-harvest-reaches-inventory-ingredient-resources-missing-14-october-2026)
- [Additional planned item actions, 14 October 2026](#additional-planned-item-actions-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

The first v0.0.40-dev1 inventory source candidate failed integration gates. Its first
placement implementation could use the wrong engine collision hull for an item
box, miss narrow obstructions or unsupported floor, and admit an entity that
ED_Alloc would quarantine. Inventory entities and model precaches also lacked
their complete map-build reservation. Full-game drop placement across CHIM and
captured scenery remains unimplemented.

## Where

Inventory runtime and modal, engine map-table budgets, command routing and
focused integration fixtures. This is a development finding, not an established
regression in the published v0.0.39 package.

## How it happened

The first vertical slice tested ownership transfers separately from actual
engine placement. AmiQuake SV_HullForEntity selects fixed player hulls from the
requested box size; it does not construct an arbitrary item hull. A free edict
can remain unavailable because ED_Alloc quarantines recently freed entries.
The initial budget adapter also omitted persistent drops and newly loaded
inventory models. Extra diagnostic command registrations exceeded the existing
resident command budget.

## Why it was not caught

Transaction and preview checks did not exercise real drop admission against
hull0 geometry, model exhaustion and the allocator's exact reuse predicate.
The full integration suite exposed additional menu, actor-frame, lighting-stub
and deterministic text-writer fixture mismatches.

## Reproduction

Exercise the actual runtime drop path with a thin wall, a narrow floor hole,
a footprint crossing an edge, a blocked eye-to-placement path, a yaw-rotated
item, a full or quarantined edict table, all 32 ground records occupied, and
16 then 17 distinct newly loaded item models. Verify refusal retains ownership,
quantity and condition. Repeat in an active CHIM or captured-scenery scene:
the current development boundary must refuse placement clearly.

## Repair

The candidate reuses AmiQuake point traces and hull0 BSP planes in a bounded
placement-only traversal. It conservatively checks the complete swept bounds
and a solid support slab, with transformed brush bounds. This can refuse
otherwise valid complex placements; it must not silently bridge unsupported
floor or pass an obstruction.

Admission follows ED_Alloc's free/freetime predicate and checks persistent record
capacity before allocation. Map conversion reserves 32 runtime drop entities
and 16 distinct new inventory model slots per level; repeated models reuse a
slot. Scene changes reset the runtime model cache. The separate capacities
remain 32 carried IDs and 32 persistent ground records. Expansion beyond the
16-model development limit requires measured table-budget work.

Placement in active CHIM, captured scenery or restricted story contexts is
explicitly refused before ownership transfer. CHIM/scenery collision support
is still required for the full-game inventory goal; this refusal is a safe
development boundary, not completion.

The necessary I action uses one 32-byte resident command record. Character
change and explicit diagnostic grants route through the existing on-demand
catalogue and existing command handlers. The diagnostic recipe is
"dbg inventory grant \"steel longsword\" 1"; opening inventory grants nothing.
Menu and block fixtures follow their actual interfaces, AWB1 keeps its named
eight-frame presentation ABI, and metadata/report writers specify UTF-8/LF.
No player animation frames or original block eligibility rules are removed.

## Verification

Thirty-nine focused host integration checks pass, including the actual runtime
placement fixture with sanitizers. The same placement fixture fails against
the preceding source. Six affected C translation units compile successfully.
Additional focused catalogue and budget checks pass; the first expanded
multiprocessing run exposed a private test-runner main-guard error, retained
separately from product findings, and the corrected budget-order control passes.

The subsequent complete suite ran 4,072 checks: 4,066 passed, zero unexpected
failures or errors, three Windows skips and three tracked expected failures.
The complete Amiga target and mandatory linked 68040 instruction gate pass.
These results apply to that exact source candidate; they do not cover the
later catalogue/layout source repairs.

Native physical I exposes raw item IDs, absent icons, text overlap and an
initially rear-facing preview. Actual sword/shield grants refuse, so that run
does not verify real equipped shield presentation. Four affected checks pass
after the integrated ordered-comparator and bounded-layout source repairs;
their rebuilt target and repaired native verification remain pending.

Native pause/input/audio, plain-BSP drop/pickup/save/load, clear CHIM refusal,
held equipment alignment, matched original comparison and maintainer acceptance
remain pending. No first
fixed version is assigned. CHIM conversion and coverage counts do not change.

A focused synthetic harvest-to-modal regression passes: actual AW_HarvestTake updates AW_ITEM, the real modal displays the ingredient name and quantity, and I/Escape close/reopen preserves identical ownership/state. Repeating the same harvest grants nothing. Metadata/platform I/O are fixture-controlled; original catalogue resolution, physical mushroom pickup and repaired native layout remain pending.

## Prevention

Keep allocator admission, full-footprint geometry, no-loss capacity checks and
actual model/entity reservations in executable regressions. Test ordinary
physical I and equip/drop input on the exact proposed image. Preserve the
distinction between safe refusal, supported placement, native verification and
full-game completion.


## Combined validation, 14 October 2026

The first complete combined run exercised 4,063 tests with one failure and no errors. The new inventory grant catalogue entry was not in the required sorted group order. The canonical catalogue sorter and generated command-page renderer corrected it. The other test results remain evidence for their exact inputs; at that checkpoint, the corrected combined candidate still required its next complete gate and native verification. The subsequent 4,072-check suite and Amiga target pass as recorded above; later native catalogue/layout failures remain open. Three Windows-specific checks were skipped and three existing census/doc-contract checks reported expected failures; neither category is a pass.


## Native catalogue failure, 14 October 2026

The exact development native diagnostic exposed raw inventory IDs, missing
icons and refused actual sword/shield grants. The separate
[INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md) records the
equality-only comparison misuse and bounded source repair. Those refused
grants do not establish equipped-shield rendering. Full inventory native
acceptance remains pending.

## Follow-up full-suite integration failure, 14 October 2026

The next exact combined suite ran 4,072 tests and reported four failure events
and zero errors: mouse-event fixtures under GNU89 and GNU99, the focus-loss
fixture, and the journal-size guard. Three Windows skips and three tracked
expected failures remain separate. This failed run is preserved; it must not
be described using the preceding candidate's passing suite receipt.

The ordered comparator and bounded inventory text introduced real dependencies
in aw_worldui.c. The earlier focused set exercised inventory, map/journal and
console paths, but omitted two other world-UI fixture callers. Those callers
therefore lacked AW_InventoryCompare and AW_SmallStringColor at link time.
The failed checks did not reach their input/focus assertions.

The fixture repair links actual aw_inventory.c pure rules under the existing
AW_INVENTORY_RULES_ONLY switch. Narrow drawing captures supply bounded text
recording in the mouse/focus fixtures; the real console-renderer regression
continues to exercise glyph rendering. Every existing input/focus assertion
remains active. Every world-UI fixture caller was inspected.

The journal had reached 198,915 bytes, exceeding the unchanged 196,608-byte
warning guard (75 percent of its 262,144-byte release limit). Recent duplicate
prose is condensed while retaining dated headings, scoped observations and
full linked issue reports. Earlier suite/target/native history is preserved.
The limit and test assertions are unchanged.

Seven affected checks pass with no failures, errors or skips, covering all
world-UI callers, real catalogue ordering, real console rendering and the
original size assertion. Mouse cases execute under both language standards.
Runtime source and assets are unchanged by this repair. A fresh complete suite
for the final reconciled source, exact target-source compatibility check and
repaired native inventory/equipment acceptance remain required.

## Scoped subsequent native inventory observation, 14 October 2026

The next exact v0.0.40-dev1 native diagnostic resolves the selected carried
item names and icons. Actual Steel Longsword and Steel Shield diagnostic grants
succeed; physical inventory controls equip both, with the carried equipment
visible on the character. Physical RMB visibly raises the actual shield in
first person. These observations supersede the failed-grant precondition for
this later run only; the earlier native failure remains historical evidence.

A scoped male-Nord modal control also holds physical forward plus attack for
three seconds while inventory is open: position and hands time remain
unchanged, and attack stays zero. After closing inventory and stowing with F,
hands time advances. This is positive native pause/input evidence for that
control, not acceptance of every race, menu state or audio path.

Third-person block posture is not accepted. Broader modal input/audio,
plain-BSP transfer/pickup/save/load, CHIM refusal, broad item/appearance coverage
and maintainer acceptance remain separate gates. The maintainer still requests the
original inset black name plaque in the gold top border and correct original
inventory posture; these improvements are planned under
[UI-INVENTORY-LAYOUT-40](UI-INVENTORY-LAYOUT-40.md), not implemented by this
record update. The next complete source gate remains required after the
fixture/journal repair; the passing target does not erase the failed suite.

## Actual harvest reaches inventory; ingredient resources missing, 14 October 2026

The exact native diagnostic starts with an empty Ingredients category, targets
a Luminous Russula cap and uses physical E Pick. Inventory then shows Luminous
Russula, quantity one, weight 0.20 and value one, unchanged across three
physical close/reopen cycles. This is a real picked-item transfer and scoped
reopen observation, separate from the earlier synthetic harvest fixture.

The item icon is an empty framed slot and actions are unavailable. Catalogue
inspection identifies ingred_russula_01 with the correct name/basic values but
empty model/icon paths and flags zero. The converter prepares assets only for
ten selected items, which exclude this ingredient. The UI draws a frame when
no icon is available. This is missing resource/action coverage, not a recurrence
of the ordered-lookup defect. Missing model/drop admission is a separate limit
from the known CHIM placement refusal; this item has not demonstrated real
drop/use behavior.

A physical debug character-change control switches Nord male to Nord female
and confirms at the same world point. The character-stat rebuild changes health
55 to 50; original equipped clothes at quantity one, gold 87 and picked Russula
one remain present. Appearance-menu head distortion is tracked as a bounded
quality follow-up under [NPC-HEAD-DECIMATION-33](NPC-HEAD-DECIMATION-33.md);
the inventory body display alone does not accept all appearance quality.

Dev2 must include compact lookup tables for all original item identities,
properties and effects, preserving typed source semantics and explicit
implementation/asset support states with bounded on-demand assets. The current
AWI2 basic catalogue and selected ten resources do not implement complete
original effect/use coverage. This is required follow-up, not a new LUT feature
or full inventory acceptance.

## Additional planned item actions, 14 October 2026

The next inventory pass must support E or double-click context actions for the
actual selected carried item: equip/unequip, consume/use, and reading books or
papers where supported. Reuse actual ownership/admission and effects; unavailable
actions must remain explicit. These expanded use/read shortcuts are planned,
not implemented or accepted in this dev1 candidate.

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
- CENSUS-TABLE-TAKE-GRAB-HIM-62 (no report page): Census and Excise Office: taking an item from the table in front of Sellus Gravius makes a guard call out a theft line
- CHARGEN-INVENTORY-LOCKED-60 (no report page): After character creation the inventory key does not open the inventory
- CHARGEN-NO-STARTING-CLOTHES-60 (no report page): The player has no starting clothes after character creation, also after leaving the Census and Excise Office
- CHARGEN-TUTORIAL-ITEM-MESSAGES-59 (no report page): Character creation: taking the bread, crab meat, candle, lockpick, whiskey, note or dagger in the Census Office shows no tutorial message
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
- [ENCUMBRANCE-INCOMPLETE-61](ENCUMBRANCE-INCOMPLETE-61.md): Carry weight is only half there: no burden shown, no message over the limit, Burden and Feather do nothing, and the kinds of item are capped
- ENEMY-HEALTH-BAR-62 (no report page): In a fight with a cliff racer the HUD shows no enemy health bar
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [EQUIP-ACTION-REGRESSION-62](EQUIP-ACTION-REGRESSION-62.md): Some weapons, armour and clothing show no Equip action in the inventory (the census office dagger reads "Actions unavailable for this item")
- EQUIP-SHARDAXE-REFUSED-61 (no report page): Equipping the iron shardaxe is refused while the iron longsword can be equipped
- [FALL-LANDING-KNOCKDOWN-62](FALL-LANDING-KNOCKDOWN-62.md): A hard landing does not knock the player or an actor down, and an NPC's landing plays no landing sound
- [GODMODE-COMBAT-DAMAGE-61](GODMODE-COMBAT-DAMAGE-61.md): With god mode on, a fight's blows still take the player's health and kill the player
- GODMODE-LAVA-DEATH-62 (no report page): The player can die in a lava pool with god mode on
- GUARD-RESIST-ARREST-NOTHING-61 (no report page): Choosing to resist arrest in a guard's conversation does nothing: the guard does not attack
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md): Inventory catalogue lookup and name sorting use an equality-only comparison
- INVENTORY-CATALOGUE-PARTIAL-54 (no report page): The item catalogue holds Morrowind items only: no lockpicks, probes, repair tools, apparatus or carried lights
- INVENTORY-ITEM-MODEL-PATH-59 (no report page): The inventory catalogue refuses every item whose world model comes from the item model table (progs/items/)
- [INVENTORY-OPEN-COST-MANY-KINDS-61](INVENTORY-OPEN-COST-MANY-KINDS-61.md): With hundreds of kinds of item the inventory takes seconds to open, and every Tab reads the item file again
- JOURNAL-BOOK-32-QUESTS-59 (no report page): The journal book lists only the quests of the old 32-slot table, although every quest's stage is now kept
- [LOADED-ITEMS-NOT-WEIGHED-61](LOADED-ITEMS-NOT-WEIGHED-61.md): After loading a save of another character the carried weight reads 0 until the next place load
- MWSCRIPT-CELLCHANGED-VOLATILE-54 (no report page): CellChanged made the sound-marker scripts volatile: 85 percent of Vivec's per-frame script work
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
- [NEWGAME-STATE-RESET-62](NEWGAME-STATE-RESET-62.md): A New Game started from the menu after playing leaves the fireplace of the Census and Excise Office unlit
- PERSUASION-BROKEN-62 (no report page): Persuasion in dialogue does nothing: Admire and Intimidate return to the topic list, Taunt shows nothing
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- PICKUP-PLACED-E-NO-TAKE-58 (no report page): The activate key on a placed item in reach takes nothing
- PLACED-ITEMS-OUTDOORS-FIRST-FRAME-59 (no report page): Outdoors no placed items are drawn after a teleport or load: the table is read before the player stands at the arrival
- PLACED-ITEMS-ROOM-RESET-59 (no report page): Entering a room with placed items drawn resets the machine to the boot screen
- PLACED-PIT-AXE-NO-FOCUS-61 (no report page): The iron shardaxe in the Seyda Neen pit is drawn but shows no item box and cannot be taken
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- PLAYER-FORTIFY-END-AS-DAMAGE-61 (no report page): When a Fortify Attribute effect on the player ends, the character sheet keeps it as a raised modifier and records the drop as damage
- [PLAYER-JUMP-ORIGINAL-RULES-48](PLAYER-JUMP-ORIGINAL-RULES-48.md): The jump height and in-air control are still Quake's, not the original's Acrobatics, load and fatigue rules
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue
- [PLAYER-READY-MOVEMENT-39](PLAYER-READY-MOVEMENT-39.md): Third-person player cannot move with fists drawn
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- [PLAYER-START-SPELLS-NOT-KNOWN-61](PLAYER-START-SPELLS-NOT-KNOWN-61.md): Character creation never puts the race, birthsign and class spells and abilities on the player record, so they cannot be cast or apply
- PLAYER-WALK-SPEED-SLOW-51 (no report page): The starting walk speed feels very slow; check it against the original and OpenMW
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
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
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- SERVICE-REFUSAL-UNCLOTHED-60 (no report page): Arrille refuses to barter at disposition 80 (player without clothes)
- SKILL-BOOKS-MISSING-62 (no report page): Reading a skill book does not raise its skill: the original raises it by one on the first read
- SKILL-RAISE-NOT-SEEN-62 (no report page): In a playtest of v0.0.61 no skill was ever seen to rise: no skill-increased line and no sound in normal play
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
- UNDERWATER-BREATH-62 (no report page): Underwater there is no breath meter and no drowning, and Water Breathing is not applied
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- [WATER-GAMEPLAY-PARITY-38](WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification
- WEAPON-STRIKE-ENCHANT-NOT-CAST-61 (no report page): A weapon's Cast When Strikes enchantment is not cast when the weapon hits
- WEREWOLF-BODY-NOT-DRAWN-63 (no report page): A player turned into a werewolf by a script keeps his own body: the werewolf model is not drawn
- WEREWOLF-RUN-SPEED-63 (no report page): A player in werewolf form runs at his normal run speed: the werewolf run multiplier is not applied
- WORLD-BUTTONS-62 (no report page): Buttons and levers that should act do nothing, for example the Ghostgate gate buttons on both sides
- WORLD-OBJECT-STATE-NOT-SAVED-59 (no report page): World objects taken or moved are not remembered: they come back when the cell or room reloads, and saves do not keep them

Related bugs in other categories:

- [INTERIOR-PLACED-ITEMS-47](INTERIOR-PLACED-ITEMS-47.md): Takeable and movable items and containers in converted interiors are not live objects (placed items are left out)
- [UI-INVENTORY-LAYOUT-40](UI-INVENTORY-LAYOUT-40.md): Inventory text overlaps fields and footer; preview initially faces away

<!-- END GENERATED CATEGORY -->
