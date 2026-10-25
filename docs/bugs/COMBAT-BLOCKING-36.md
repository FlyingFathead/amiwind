# COMBAT-BLOCKING-36: Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.39-rc2 at 2026-10-14 (time not recorded): Maintainer repeats missing block presentation in both views. Eligible shield control guards but shows fists/Guard HUD and low third-person arms. Original shield eligibility preserved.
- Reported with v0.0.40-dev1 at 2026-10-14 (time not recorded): Target FPU gate recurrence in block orientation; safe-math repair and focused pose checks pass, linked target/native gates pending.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | Engine and QuakeC: combat blocking, block animations, input bindings |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev5, v0.0.39-rc2 (last seen) |
| Severity | high: Maintainer repeatedly sees no block presentation in either view; a shield-equipped control also lacks the expected visible shield pose. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.36-dev5 |
| From commit | source 6c29a23, engine 6c29a23, CHIM world 6c29a23 |
| CHIM engine version | CHIM 0.1.0, engine 6c29a23, world format 0.7 |
| Build note | run 2026_10_11_v0.0.36-dev5_full-coast-arena-seyda-dev5_6c29a23 (playtest v0.0.36-dev5) |
| Platform or emulator | FS-UAE, JIT (dev5 playtest build) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.45 (19 October 2026)._

<!-- contents start -->
## Contents

- [PERSISTING: reported 2 times; something has to be done](#persisting-reported-2-times-something-has-to-be-done)
- [Historical source plan: 11 October 2026](#historical-source-plan-11-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Renewed maintainer failure and shield control, 14 October 2026](#renewed-maintainer-failure-and-shield-control-14-october-2026)
- [Development audit, 14 October 2026](#development-audit-14-october-2026)
- [Inventory-backed equipment candidate, 14 October 2026](#inventory-backed-equipment-candidate-14-october-2026)
- [Integration gate follow-up, 14 October 2026](#integration-gate-follow-up-14-october-2026)
- [Target FPU gate recurrence, 14 October 2026](#target-fpu-gate-recurrence-14-october-2026)
- [Subsequent native inventory failure, 14 October 2026](#subsequent-native-inventory-failure-14-october-2026)
- [Scoped subsequent actual-shield observation, 14 October 2026](#scoped-subsequent-actual-shield-observation-14-october-2026)
- [Third-person hold selects the start sample, 14 October 2026](#third-person-hold-selects-the-start-sample-14-october-2026)
- [Actual incoming-hit block control, 14 October 2026](#actual-incoming-hit-block-control-14-october-2026)
- [Authored-hit source correction and producer limits, 14 October 2026](#authored-hit-source-correction-and-producer-limits-14-october-2026)
- [Blocking balance and recovery scope, 14 October 2026](#blocking-balance-and-recovery-scope-14-october-2026)
- [Scoped later third-person native control, 14 October 2026](#scoped-later-third-person-native-control-14-october-2026)
- [Selected legacy block exception, 14 October 2026](#selected-legacy-block-exception-14-october-2026)
- [Later exact diagnostic mechanic and selected-body observations, 14 October 2026](#later-exact-diagnostic-mechanic-and-selected-body-observations-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Historical source plan: 11 October 2026

Open feature request from the maintainer on 11 October 2026, after playing the v0.0.36-dev5 playtest build on FS-UAE with JIT (widened the same day). Target: v0.0.37 or later.
Repaired in source on v0.0.36-blocking for v0.0.36-rc1 (maintainer order: into rc1), not yet in a build.

## Symptom

Block is a Morrowind skill, but in AmiWind the player cannot block on purpose and has no block button, and
NPCs seemed never to block: no block animation was seen in a fight.

## Where

Engine: the combat code (`engine/aga/src/aw_combat.c`, `aw_combat_rules.c`), the input (`cl_input.c`,
`config/keymaps.cfg`, the Controls menu in `aw_menu.c`), the third-person body (`aw_view.c`,
`tools/prepare_player_view.py`) and the HUD (`aw_ui.c`).

## How it happened

The original game has no block button: blocking is automatic whenever a shield is equipped (UESP Block page;
OpenMW `combat.cpp` blockMeleeAttack has no input). The v0.0.35 combat merge implemented that automatic rule
for every fighter, with the NPC block animation of the animation kit, and kept the right mouse button for a
held block that was not built. The rule only lets fighters with a shield and a one-handed weapon block, at
10 to 50 %, and only after the attacker's hit roll succeeded: most residents carry no shield, and the new
character has none, so blocks were rare and the player never saw one.

## Why it was not caught

A missing feature (the held block), and a rare event on the NPC side, not a fault: no smoke counted blocks.

## Reproduction

Always: start a fight. The right button does nothing in a fight, and an NPC without a shield never blocks.

## Repair

- Hold to block (an AmiWind extension, the default by project decision, `aw_combat_block 1`): the right mouse
  button (the Block action in Options > Controls) raises the shield while it is held. Each blow is still
  decided by the original formula and settings (Block skill, Agility, Luck, swing, fatigue, facing, the
  10..50 % clamp); the button decides when the player blocks. No swing while guarding. Without a usable shield
  the console says so. `aw_combat_block 0` (Blocking: Automatic) keeps the original automatic block
  (DON'T DELETE ANY METHOD). Console: `dbg combat block hold|auto`; `dbg combat` counts the blocks.
- Visible: the third-person body now carries the original block animation (base_anim "shield: block start"
  to "block stop") and plays it while guarding (held at the block's hit key) and after a blocked blow; first
  person shows "Guard" under the crosshair, the shield's sound and a view kick on a block. A first-person
  shield model is a later step.
- NPCs: unchanged, the original automatic rule with their block animation and the shield's sound.
- Fidelity: the stand-still block bonus now follows the forward key, as in the original (`combat.cpp`:
  movement forward <= 0), not any movement.
- Companion pick: unchanged; pick mode takes the left button and the right button, and outside pick mode the
  right button blocks.

## Verification

`tests/aga_combat_test.c` (the engine layer with a synthetic server, 40 blows each): blocks while held, none
while not held under hold-to-block, blocks without the button under the automatic rule, no guard without a
shield, the attack masked while guarding. `tests/test_combat.py`
`test_blocking_hold_to_block_default_and_original_kept` pins the default, the bindings, the menu, the body
group and the docs. Pending: the gate with its boot smoke, a MiniWind fight with the `sword_shield` loadout
counting BLOCKED lines, and the maintainer's playtest.

## Prevention

The default bindings and the block default are pinned by tests; `dbg combat` reports blocks per fight so a
smoke can count them.

## Renewed maintainer failure and shield control, 14 October 2026

The maintainer reports absent blocking animation in both first and third person in
RC2. The earlier source plan below is historical implementation evidence, not
current visible acceptance. The first-person shield model was explicitly left
unimplemented; the Guard HUD alone does not satisfy a visible blocking pose.

The exact RC2 baseline initially has no shield and reports that there is no
shield to block with. That control cannot validate shield animation. A separate
shield-equipped loadout reaches guarding from physical RMB: first person shows
ordinary fists and Guard HUD without a raised shield; the third-person body
keeps its arms low. This is a scoped presentation failure, with exact repair
and matched original/native/maintainer checks pending.

Keep the original usable-shield and one-handed-weapon eligibility rule.
Unarmed blocking is not requested. Verify no-shield refusal, eligible held and
automatic blocking, shield/body pose and first-person presentation separately;
successful block mechanics or a HUD word does not accept the visual behavior.


## Development audit, 14 October 2026

The new diagnostic Orc-female control reaches the guard state with an eligible shield test sheet and physical RMB. The third-person body selects frame 25 of 104 while the Guard HUD is shown, but no shield model appears. First person also lacks visible shield presentation. This verifies input/state selection only; a guard label and frame selection do not accept the visible blocking repair.


The first combined target compile linked successfully but failed its warning-free
gate on two adjacent clamp statements (-Wmisleading-indentation). They are now
on separate lines with unchanged conditions. The failed compile receipt is
retained; a new candidate must pass the target gate before native testing.

## Inventory-backed equipment candidate, 14 October 2026

The v0.0.40-dev1 [inventory source candidate](../INVENTORY.md) supplies the actual
owned, equipped shield ID/model to the first-person block bridge. Its
third-person held aliases reuse frame-matched AW_Items bone tags. Real
equip/drop updates cached combat equipment and preserves item condition, health,
fatigue and knockdown; a diagnostic preset alone is not real inventory admission.

Focused transaction, save, decoder and UI tests and selected source asset
readback pass. The subsequent complete Amiga target and linked instruction
gate pass; native visible shield/block alignment remains pending. No owner-case resolution or acceptance is claimed; original shield and
one-handed weapon eligibility remains required.

## Integration gate follow-up, 14 October 2026

The v0.0.40-dev1 source names the existing eight-frame AWB1 first-person
presentation contract independently of legacy actor-frame layouts. Normal
catalogue preparation retains block resources and explicit UTF-8/LF report
writes. Corrected host lighting stubs preserve the real block implementation
in its own fixtures. Focused integration checks pass. The subsequent complete
Amiga target passes; visible native block acceptance remains pending. No player-body animation frames are removed.

## Target FPU gate recurrence, 14 October 2026

The v0.0.40-dev1 target linked but failed the mandatory 68040 reachability check
through first-person block orientation and library trigonometry. The dedicated
recurrence is tracked under [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md).

The candidate now uses the engine's safe Q_SinCosDeg/Q_atan2 and nonnegative
horizontal-length square root, with stable near-pole roll extraction. An
independent executable orientation oracle fails before and passes after the
change across 1,925 cases; 21 affected host checks pass. A single target object
has no unsupported library trig references. The subsequent exact candidate
passes the complete linked Amiga target and mandatory 68040 instruction gate.
Its full suite ran 4,072 checks, with 4,066 passes, no unexpected failures or
errors, three Windows skips and three tracked expected failures. Visible
native blocking remains pending. Existing shield eligibility,
eight-frame AWB1 and unchanged player-body frames are preserved; no asset
rebake or maintainer-case acceptance is claimed.

## Subsequent native inventory failure, 14 October 2026

The first physical-I diagnostic shows unavailable metadata/icons and overlapping
inventory text with a rear-facing initial preview. These are tracked under
[INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md) and
[UI-INVENTORY-LAYOUT-40](UI-INVENTORY-LAYOUT-40.md).
Both actual sword/shield grants are refused. Consequently that run's nominal
shield captures do not validate actual equipped blocking in either view.

The ordered inventory comparator and bounded layout source repairs are now
integrated, with four affected automated checks passing. Their rebuilt target
and repaired native inventory/equipment checks remain pending. The original
shield and one-handed-weapon eligibility rules remain unchanged.

## Scoped subsequent actual-shield observation, 14 October 2026

Unlike the preceding failed-grant run, the subsequent exact native diagnostic
successfully grants and physically equips the actual Steel Longsword and Steel
Shield. Physical RMB visibly raises that shield in first person. The actual
item admission/equip precondition is established for this later control.

Third-person blocking posture remains unaccepted. Visible first-person raising
does not establish the original block formula, every appearance, pacing,
package completeness or maintainer acceptance. The issue stays open; shield and
one-handed-weapon eligibility remains unchanged.

## Third-person hold selects the start sample, 14 October 2026

The inherited Nord body metadata declares block:25:2:0.6667:0.250. In
body_block_frame, the guarded hold index is int(hit_fraction*(count-1)+0.5).
With two samples and hit fraction 0.25, this rounds to zero: the guard holds
the block-start frame 25. The real block-hit pose is absent from those two
baked endpoints. The exact native third-person capture shows the upright body
and low shield, consistent with that selection; it is not a third-person pass.

A repair must bake the real authored block-hit sample and select it for the
hold, preserving normal body frames and the original eligibility rules.
A bounded repair and executable regression are in progress; all-appearance
body/tag regeneration and actual native pose validation are still pending.
No repaired body output or maintainer acceptance is established here.
The separate actual first-person shield-raise observation remains valid.

## Actual incoming-hit block control, 14 October 2026

The exact v0.0.40-dev1 female-Nord native diagnostic uses actual inventory-
equipped Steel Longsword and Steel Shield, original combat/dice enabled, and
physical RMB held for seven seconds against Eldafire. The readout records
"Eldafire -> you: chance 55 roll 33 BLOCKED (block 27/50)" and the player's
credited block count increases from zero to one.

Other recorded attacks deal 6.1 and 10.0 fatigue, or miss. Lines labelled
"miss (blocks)" are not counted as successful blocks. Health remains 50 because
this opponent attacks unarmed; the control does not establish armed health
damage. The original game/audio clip and exact state receipt remain private.

This is positive held-block mechanic evidence for one actual equipped case.
The separately observed first-person shield raise remains valid. Third-person
guard presentation still holds the wrong start pose and fails visible
acceptance; real-hit sampling/all-appearance repair is pending. Do not turn
this scoped mechanic result into all-appearance, package or maintainer acceptance.

## Authored-hit source correction and producer limits, 14 October 2026

The player converter's uniform five-sample block plan and compact fitter kept
START and the 40-percent sample. Runtime rounding of the authored 25-percent
hit fraction over two samples then held START. The integrated player-only plan
now retains exact START/HIT; runtime reaches HIT at hit fraction times the
original clip duration and holds it. Larger groups retain exact hit timing and
their follow-through. The existing AmiQuake alias selector and frame-matched
equipment tags are reused, without a companion model or guard-triggered disk
read/allocation. NPC sampling and normal/ready gait, swim and torch resources
are outside this correction.

Six focused tests pass, including the real extracted C selector for two- and
five-frame groups before/at the hit, held, recoil and release. Nord readback
preserves headers, quantization, skin, UVs, topology and all 104 unrelated frames;
only held frame 26 and its matching attachment tag change.

A full twenty-body producer run completed, but output adoption is held:
sixteen human outputs preserve geometry/skin/header/animation layout and gaits
apart from that held sample/tag. Four beast outputs require review: female
global-X quantization expands; male outputs have broader fitting differences
also present in unchanged-source controls. They must not be described as twenty
byte-equivalent accepted bodies. No regenerated body has been injected into the
native disk. Engine and verified matching aliases/tags must be adopted together;
the older two-sample assets do not satisfy the new semantic contract.

The new source and HUD change still need their exact combined full suite,
Amiga target/FPU gate, staged readback and matched normal-speed native check.
The previous first-person raise and incoming-block mechanic evidence remains
scoped; the older third-person pose is still a failure. All appearances,
packaging and maintainer acceptance remain pending.

## Blocking balance and recovery scope, 14 October 2026

The maintainer asks that shield-block testing also account for losing grounding and
stagger while blocking. The one credited incoming block does not establish
balance, stagger, knockdown, recovery or every incoming weapon case.

Compare the applicable original behavior in a matched OpenMW control before
selecting or claiming a formula. Verify actual eligibility, chance/outcome,
reaction pose and duration, movement/attack restrictions and return to control
separately. Reuse the existing AmiQuake combat/reaction state machinery where
suitable; any needed behavior change remains unimplemented. No new native
stagger or recovery result is claimed by this requirement.

## Scoped later third-person native control, 14 October 2026

The subsequent exact diagnostic passes its linked Amiga/FPU target and full
suite: 4,078 checks run, 4,072 pass, no unexpected failure/error, three Windows
skips and three tracked expected failures. In its male-Nord actual inventory-
equipped Steel Longsword/Shield control, physical RMB enters a visibly raised
third-person shield/arm pose and release returns it, at normal speed.

This is scoped visible hold/release evidence, not an incoming block in that
sequence. The earlier female-Nord incoming BLOCKED control is separate.
All appearances, balance/stagger/knockdown/recovery, detailed asset quality,
packaging and maintainer acceptance remain pending. Male beast guarded fits retain
gait counts/timing but production adoption needs texture/jump/death comparison;
other group and fitting differences must not be hidden.

The maintainer also rejects the normal HUD's temporary centre Guard label. Its new
source removal changes only the draw call; guard logic and debug readout remain.
Real pixel and actual combat controls pass, while the preceding HUD fails the
new pixel regression. This change and the separate no-dice readout repair
postdate that native control and need their own target/native verification.

## Selected legacy block exception, 14 October 2026

The selected dev1 payload uses nineteen current bodies plus the previously
packaged 122-frame Argonian male body/layout and its matching 122-row item tags.
This retains more hit/death/jump sampling than the fresh fit; it is not a new
all-appearance exact-hit bake or an anatomy repair.

That Argonian's legacy five-frame block holds frame 31, sampled approximately
66.7 milliseconds before the authored hit. Start and hold geometry/shield tags
change, but exact-hit fidelity and matched native/original acceptance remain
pending. The selected target passes; the new Argonian native check is active,
and earlier Nord evidence does not accept it. Keep this retained-asset exception
and known anatomy-guard limit visible under
[BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md).

## Later exact diagnostic mechanic and selected-body observations, 14 October 2026

The exact later Amiga target/FPU gate and corrected nonroot full suite pass:
4,079 checks run, 4,073 pass, no unexpected failures/errors, three Windows skips
and three tracked expected failures. The recorded source/pin remains unchanged.

With an actual inventory-equipped steel weapon and shield, normal dice and
physical blocking, the Nord control records two incoming Fargoth BLOCKED
outcomes, with block rolls 7/45 and 15/49; the credited count is two. Miss lines
are excluded. Final health 55/55 and fatigue 180/180 are an end snapshot after
recovery, not proof that every earlier blow caused no fatigue damage. The normal
HUD no longer paints centre Guard text and keeps the NPC target name in its
usual location.

The actual character menu subsequently selects Argonian male. The selected
legacy 122-frame body with matching tags visibly raises the shield while held
and returns on release in separate original captures. Normal WALK3 movement
with fists readied changes local position from (16,44,60) to (7,-42,60) and
(-108,-55,43). Physical punch footage is retained; closer pose review is pending.

This does not verify death/jump clips, complete anatomy, matched gait, all
appearances or full acceptance. The legacy held sample remains approximately
66.7 ms before the authored hit. Fists plus a shield are ineligible under the
existing weapon rule; their refusal is an expected control, not a new defect.

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
- [DOOR-LOAD-LOCKS-MISSING-51](DOOR-LOAD-LOCKS-MISSING-51.md): Load doors ignore the original game's locks: every door into a room opens, locked or not
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md): Inventory catalogue lookup and name sorting use an equality-only comparison
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

- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)

<!-- END GENERATED CATEGORY -->
