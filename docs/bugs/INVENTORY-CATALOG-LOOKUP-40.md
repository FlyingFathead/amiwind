# INVENTORY-CATALOG-LOOKUP-40: Inventory catalogue lookup and name sorting use an equality-only comparison

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 14 October 2026, in v0.0.40-dev1 |
| Where | Inventory AWI2 catalogue lookup and modal name sorting |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.40-dev1 (last seen) |
| Severity | high: Carried item metadata and icons are unavailable for many IDs; actual equipment grants and subsequent equipment verification cannot proceed. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.40-dev1 |
| From commit | source 7a783e0, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format unknown |
| Unknown because | Exact source commit and privately bound engine identify the native diagnostic; no separate engine/world commit is established. |
| Platform or emulator | FS-UAE, AmigaOS; Linux executable regressions |

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
- [Scoped subsequent native lookup, 14 October 2026](#scoped-subsequent-native-lookup-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

The v0.0.40-dev1 native diagnostic inventory displays raw carried item IDs and
no item icons. Requests to grant the actual steel longsword and steel shield
are refused. The inventory name sorter also leaves unequal names in insertion
order. This is a development candidate failure, not an established regression
in the published v0.0.39 package.

## Where

AW_InventoryRead in engine/aga/src/aw_inventory.c, the name-sort branch in
aw_worldui.c, and the catalogue/interaction fixtures.

## How it happened

AmiQuake's existing Q_strncasecmp and Q_strcasecmp in common.c are equality
helpers: they return zero for equal strings and minus one for every unequal
pair. They never return a positive ordering result. The inventory used that
helper as if it implemented strcmp ordering. Binary search therefore always
walked toward higher rows on a mismatch, missing keys below the current row.
Name sorting never moved an unequal preceding item.

The repair inspects and preserves the engine helper's original contract.
An inventory-local ordered ASCII case-insensitive comparator is shared by
catalogue search and name sorting. Original catalogue IDs are case-folded by
the converter. No engine-wide comparison semantics or asset data are changed.

## Why it was not caught

The metadata fixture contained only one row and replaced Q_strcasecmp with
libc strcasecmp, which supplies ordering the real engine does not. The UI
fixture carried only one item. Those checks could validate record fields and
transactions but could not detect real multirow lookup or sort failures.
The previous passing full suite did not establish native inventory behavior.

## Reproduction

Open inventory with physical I on the affected diagnostic and observe raw IDs
and absent icons. Request the actual steel longsword and steel shield through
the explicit diagnostic inventory grant; both are refused in the recorded run.

The executable regression links actual common.c, asserts its equality-only
behavior in both directions, and searches seven sorted catalogue rows at both
ends and in the middle. It includes mixed case and missing IDs before, between
and after real keys, preserving the output object on failure. The modal fixture
inserts Zulu, alpha and Middle out of order and checks actual rendered name,
value and weight order.

## Repair

AW_InventoryCompare returns negative, zero or positive ordering using unsigned
bytes and ASCII case folding. AW_InventoryRead and the name-sort branch use it.
Other inventory Q_strcasecmp uses were audited: the remaining diagnostic
"grant" comparison only tests equality and retains the original helper.

The fixtures link real AmiQuake common.c. Only synthetic catalogue I/O is
wrapped at link time; no libc substitute replaces the engine comparison.

## Verification

Two sanitizer-enabled executable regressions pass with the source repair.
Controls restoring both historical comparison call sites fail independently:
the catalogue misses an existing key and the rendered name order is wrong.
Single-row malformed-record, nonfinite numeric, path-escape and transactional
checks remain active.

The original native failure is preserved. The refused sword/shield grants mean
that run's shield checks do not verify actual equipped blocking. Rebuilt target,
physical I with names/icons, actual equip, first/third-person shield rendering,
pause, drop/pickup, save/load and maintainer acceptance remain pending. No fixed
version is assigned. CHIM conversion and coverage are unchanged.

## Prevention

Use ordered comparison only where its contract supplies ordering. Catalogue
tests must include multiple rows and the actual engine comparison implementation;
UI sort checks must use multiple out-of-order items. Keep native item metadata,
actual equipment and visible blocking as separate observable acceptance steps.

## Scoped subsequent native lookup, 14 October 2026

The next exact native diagnostic shows selected original item names and icons.
Both actual steel longsword and steel_shield grants succeed, and physical
inventory controls equip them with visible held equipment. This is native
evidence for those selected records, not every catalogue row or complete item
semantics. The earlier raw-ID/icon/grant failure remains preserved. Complete
final suite, package readback and maintainer acceptance remain pending.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- [AW-20260928-10](AW-20260928-10.md): Interior door animation and sound missing
- [AW-20260928-12](AW-20260928-12.md): Downstairs interior doors cannot open
- AW-20260928-19 (no report page): Courtyard barrel incorrectly says empty
- AW-STATE-32-SLOTS-48 (no report page): The game state table holds 32 globals, 32 quests and 32 items; the game has 143 globals and 318 journal topics
- AW25-06 (no report page): Quicksave shown as empty; save ordering confusing
- [CENSUS-DOOR-STUCK-29](CENSUS-DOOR-STUCK-29.md): Player stuck after opening Census Office hall door
- [CHIM-COURT-BARREL-USE-33](CHIM-COURT-BARREL-USE-33.md): Census courtyard on CHIM: Fargoth's ring barrel cannot be used, so the opening cannot proceed
- CLOCK-01 (no report page): Automatic clock dropped fractional milliseconds each frame
- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button
- [COMBAT-CHASE-CHIM-STUCK-46](COMBAT-CHASE-CHIM-STUCK-46.md): Actors spawned on a CHIM frame without a baked ground point stay in the air: the spawn floor snap runs before the streamed ground under them is collidable (the chase itself works)
- [COMBAT-FATIGUE-HEALTH-DAMAGE-39](COMBAT-FATIGUE-HEALTH-DAMAGE-39.md): Clarify Eldafire bare-fist fatigue damage versus armed guard health damage
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NODICE-READOUT-40](COMBAT-NODICE-READOUT-40.md): No-dice combat readout labels living targets already down
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- MWSCRIPT-DATA-UNKNOWN-NAMES-48 (no report page): Four Bloodmoon scripts read names declared nowhere in the game data and do not compile
- MWSCRIPT-INTERIOR-PLACEMENTS-48 (no report page): Scripted placements in rooms that have no edict are not attached: the engine has no room identity to match them (3,612 of 4,907 bindings are in rooms)
- MWSCRIPT-STATE-NOT-SAVED-48 (no report page): The compiled scripts' values (globals, object and script locals, journal indexes) are not in saved games
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- [PLAYER-JUMP-ORIGINAL-RULES-48](PLAYER-JUMP-ORIGINAL-RULES-48.md): The jump height and in-air control are still Quake's, not the original's Acrobatics, load and fatigue rules
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue
- [PLAYER-READY-MOVEMENT-39](PLAYER-READY-MOVEMENT-39.md): Third-person player cannot move with fists drawn
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SAVE-LAVA-DEATH-LOOP-38](SAVE-LAVA-DEATH-LOOP-38.md): Lava fall can leave an autosave that reloads into repeated death
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- [WATER-GAMEPLAY-PARITY-38](WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification

Related bugs in other categories:

- [BUILD-INVENTORY-PALETTE-41](BUILD-INVENTORY-PALETTE-41.md): Inventory icons and metadata stop the sky palette image pass

<!-- END GENERATED CATEGORY -->
