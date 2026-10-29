# PLAYER-READY-MOVEMENT-39: Third-person player cannot move with fists drawn

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 14 October 2026, in v0.0.39-rc2 |
| Where | Third-person player locomotion on land with fists drawn |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-rc2 (last seen) |
| Severity | high: A normal combat-ready state prevents the maintainer from moving. |
| Family | Game logic (QuakeC) and saves (`game-logic`) |
| Playtest version | v0.0.39-rc2 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Maintainer names RC2 and the same gameplay as final; the exact owner-running image and cell were not independently read back. |
| Platform or emulator | unknown (Maintainer did not restate the emulator or CPU preset for this observation.) |

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
- [Character-change testing aid, 14 October 2026](#character-change-testing-aid-14-october-2026)
- [Prevention](#prevention)
- [Development audit, 14 October 2026](#development-audit-14-october-2026)
- [Input-gate readout, 14 October 2026](#input-gate-readout-14-october-2026)
- [Disabled-combat lock edge, 14 October 2026](#disabled-combat-lock-edge-14-october-2026)
- [Scoped male-Nord ready movement, 14 October 2026](#scoped-male-nord-ready-movement-14-october-2026)
- [Selected Argonian movement control, 14 October 2026](#selected-argonian-movement-control-14-october-2026)
- [Fast race-switch testing candidate, 14 October 2026](#fast-race-switch-testing-candidate-14-october-2026)
- [Race shortcut resident-budget follow-up, 14 October 2026](#race-shortcut-resident-budget-follow-up-14-october-2026)
- [Khajiit follow-up diagnostic, 14 October 2026](#khajiit-follow-up-diagnostic-14-october-2026)
- [Nord gait diagnostic, 14 October 2026](#nord-gait-diagnostic-14-october-2026)
- [Original gait reference and measurement correction, 14 October 2026](#original-gait-reference-and-measurement-correction-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

On 14 October 2026 the maintainer explicitly reports that the third-person player
cannot move with fists drawn in RC2, and says its gameplay is the same as final
v0.0.39. This is a locomotion failure, separate from coarse or skipped gait
frames in [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md).
The approved RC1 fight-ready posture is a positive control to preserve.

## Where

Third-person player locomotion on land with fists drawn. The exact owner scene,
appearance, input bindings and running binary need reproduction/readback.

## How it happened

Unknown. The symptom does not establish whether input, QuakeC movement gating,
collision, ready-state transitions or displayed movement caused the failure.
No source repair has been verified.

## Why it was not caught

Earlier ready-pose and authored-frame checks did not cover the maintainer's physical
movement sequence. A pose, file readback or unrelated moving diagnostic does
not accept unobstructed ordinary-input locomotion.

## Reproduction

Start in a clear, normally colliding area. Record the loaded build, appearance,
view, pose and bindings. Measure position with fists lowered, draw with physical
F, then hold physical W/A/S/D individually and repeat after lowering. Compare
both views and record whether attack or guard is active. Do not use noclip to
accept normal collision.

## Repair

Pending reproduction and diagnosis. Inspect the existing AmiQuake SV_ClientThink
movement dispatch, input and collision paths before designing a correction;
reuse their normal movement behavior and preserve story/menu restrictions,
combat rules and the approved ready posture. No new mechanism is selected yet.

## Verification

An exact delivered RC2 baseline uses engine SHA-256
`ef0bfa4fc2b5225fb6583f0ca012e62a77291b79652235900d730c23c1bb6da1`.
The first movement attempt ran into a guard and is not an unobstructed control.

A separate after-Census Nord control starts at (0, 0, 57), reaches ready state
2/goal 1 from physical F, and physical A/S/D moves to (-255, -48, 24),
(-239, -276, 14) and (-52, -236, 50), with the ready body visible. The maintainer
failure is not reproduced in this one control; this does not disprove it or
accept another appearance, scene or state. Maintainer-case reproduction, repair,
both-view normal movement and exact repaired-package acceptance remain pending.

## Character-change testing aid, 14 October 2026

The `dbg characterchange` testing command is implemented in source:
it reuses the existing pier race/gender/head/hair appearance menu by default;
`all` selects the full quick-character page sequence. Two focused C/console
checks pass. Story-registration restrictions remain in place. Target/native
menu behavior and package acceptance remain pending; it is a diagnostic aid,
with no movement, punch, block or swimming repair claimed.

## Prevention

Require a physical-input, normally colliding lowered/ready movement comparison,
with position deltas and continuous body footage, on the exact proposed package.
Keep gait smoothness, movement mechanics, native checks and maintainer acceptance as
separate gates.


## Development audit, 14 October 2026

The diagnostic command was exercised in FS-UAE with physical keys: it opened the pier appearance page, changed Nord male to Orc female and changed head/hair choices, confirmed, selected the Orc female gameplay body and reopened the menu. Two focused C/console tests and post-exit engine readback pass; AmigaDOS exit was visually verified. Full-body chosen head/hair recomposition is still a separate limitation. Physical A/S movement with fists ready succeeded in this Orc control. This does not reproduce or close the maintainer's inability to move.


## Input-gate readout, 14 October 2026

The v0.0.40-dev1 source adds the active story/modal/combat/death predicates,
last movement command sent and attack latch to the existing hands diagnostic.
This does not alter those gates or establish the cause. The next native test
must capture the failing input state; fresh released controls that move do
not close the maintainer's report.


## Disabled-combat lock edge, 14 October 2026

The actual combat adapter fixture now reproduces a conditional second failure:
disable the raw combat cvar while the player is knocked down and the old code
continues locking movement and attack, although the disabled simulation no
longer advances recovery. The source repair applies the combat input lock
only while combat is enabled. The fixture fails before this change and passes
after it; enabled knockdown, including after re-enabling combat, still locks
input. Normal death and story restrictions remain independent.

There is no evidence yet that the maintainer disabled combat in the failing save.
This fixes the demonstrated edge without treating it as the established cause
of all fists-ready movement reports. Native and maintainer-case validation remain
pending.

## Scoped male-Nord ready movement, 14 October 2026

In the exact v0.0.40-dev1 male-Nord native diagnostic, physical F then held LMB
reaches attack state, followed by physical S and D with fists still ready.
Position changes from local (0,-59,72) through (-13,-72,75) to (115,36,74).
The player uses normal WALK movetype 3 without noclip. This establishes
movement in this one ready-state control, not reproduction or resolution of
the maintainer's inability to move, all-appearance coverage or hit/damage behavior.

## Selected Argonian movement control, 14 October 2026

The later actual character-menu confirmation selects Argonian male. With fists
readied and normal WALK3, local positions change from (16,44,60) to (7,-42,60)
and then (-108,-55,43). This establishes movement in that selected-body control.
Complete gait, anatomy, original parity, other cases and full acceptance remain
open; the retained physical punch clip needs closer pose review.

## Fast race-switch testing candidate, 14 October 2026

The new dev1 diagnostic adds dbg set race and dbg set playerrace. With no value
or list, it prints the loaded race catalogue's zero-based numeric IDs/names and
current selection. Numeric input is strict; names compare case-insensitively
while ignoring spaces, underscores and hyphens, including quoted or unquoted
High Elf. IDs describe the currently loaded catalogue, not a universal race
enumeration.

The refined contract validates the selected race and compatible head/hair with
AW_CharacterSet on a temporary character, chooses the first valid target
race/gender head and hair, then applies only race/head/hair and live eye height.
A same-race request is a no-op preserving the selected head/hair. Gender, name, class, birthsign, equipment, current health,
attributes/skills, maxima and level remain unchanged. This is a visual/test
shortcut: it does not reapply racial statistics or rebuild character progression.
The existing full-body selected-head/hair composition limitation remains separate.

The command reuses AmiQuake's registered console command path and existing
character builder. Invalid/overflow input and dead, unavailable local-game,
restricted-story or active-menu changes are refused without applying a partial
character. Existing story restrictions remain.

Fourteen final focused automated checks pass for the refined preservation path.
New target, native shortcut behavior, packaging and complete acceptance remain
pending. Earlier characterchange menu and movement controls
do not validate this new route, and no movement/combat/swimming fix is inferred.

## Race shortcut resident-budget follow-up, 14 October 2026

The new shortcut's direct registration adds a resident command and the complete
candidate gate rejects its extra 32 bytes. The recurrence is tracked under
[ENGINE-RESIDENT-REGISTRY-GROWTH-36](ENGINE-RESIDENT-REGISTRY-GROWTH-36.md).
The correction reuses the existing on-demand AWDC1 dbg path, preserving the
unchanged registry budget rather than raising it.

The preceding fourteen functional checks did not override the failed full
gate. After the AWDC1 correction, twenty focused checks pass, including actual
character/console dispatch, help/catalogue and resident-budget controls. New
exact target/full-gate/native/package verification remains pending. The race/head/hair-only
preservation contract and the original movement issue stay separate.

## Khajiit follow-up diagnostic, 14 October 2026

Test source `90ba44c2cc079de50e50b8e1a8cde76dd2bcf318`, engine SHA-256 `166ffbecbcd399f9d9fe3ed2d5f3bdc259bf17a0bfe7f1e933a1222bf264b2a2`, using the previously delivered v0.0.40-dev1 world. The post-Census diagnostic character was changed through the actual appearance menu. This is an unreleased diagnostic, not a new shipment.

The actual Khajiit female selection (face 1, hair 1) is a scoped positive control. Physical F lowers fists (state 0 / goal 0) and redraws them (state 2 / goal 1). Physical W/A/S/D changes position in dry normal WALK movement with fists drawn. Stationary LMB produces attack state 3 and body frames 86-87 of 106; a D-strafe punch produces state 3 / body frame 97 with velocity 119.6, 1.6, 0. Original video frames show arm changes. The first forward-moving capture missed the transient in its delayed readout and remains inconclusive for simultaneous attack state.

Warp was visibly disabled, and recordings contain actual game audio. This does not reproduce or close the reported failure, establish damage, or accept anatomy, gait quality, blocking, swimming, all appearances or original-game parity.

The separate normal shutdown check records actual emulator-parent and container exit status 0, followed by 194 resource checks, 33 key bindings and a valid bitmap. This does not retroactively repair the earlier failed shutdown receipt. Played disks remain diagnostic evidence only.

## Nord gait diagnostic, 14 October 2026

Test source `90ba44c2cc079de50e50b8e1a8cde76dd2bcf318`, engine SHA-256 `166ffbecbcd399f9d9fe3ed2d5f3bdc259bf17a0bfe7f1e933a1222bf264b2a2`, with the previously delivered v0.0.40-dev1 world. This is an unreleased diagnostic, not a new package or acceptance. The original emulator frames were retained; warp was visibly disabled before recording.

Male Nord physical W input for three seconds moved the readied character while the camera eye changed from local (0,-59,72) to (0,28,79); Shift+W from the same verified camera start reached (-2,405,85). These rounded remote readings describe the camera eye, not the actor or feet. Normal dry WALK movement was verified separately. Lowered walking used the same start, but the lowered run started from the walk endpoint, so it is not an exact paired comparison. Three decoded ready-run frames show changing leg/arm poses and world translation; this is not complete-video smoothness acceptance.

Initial ready captures remained at an endpoint and are excluded as movement evidence. A subsequent placement attempt was rejected inside solid; corrected captures used the existing scene reset and a start-position guard. The sampled clock read 09:31. The remote daynight field describes the separate midday-hold override, not the automatic clock-step setting, so its on value does not show that the requested clock stop failed. Exact original-game alignment and the full normal-speed comparison with the historical v0.0.38 control are still pending. No all-appearance, anatomy, hit/damage, blocking or swimming acceptance follows.

The run closed normally and passed its separate post-exit resource readback. Its played disk is diagnostic evidence only. All related gameplay reports remain open.

## Original gait reference and measurement correction, 14 October 2026

An OpenMW 0.51.0 reference records physical W and Shift+W for three seconds
with fists lowered and drawn. The displayed Nord male, Barbarian, The Steed
attributes match the diagnostic: 60,30,40,30,75,50,30,40; health55 and fatigue180.
The original common shirt, pants and shoes match the body recipe. Hair00 matches;
the reference uses head06 while the prebuilt body uses head01.

The exact compiled coordinate table maps Seyda local coordinates by adding
(-2816,-17920,0) and multiplying by4. The native initial camera eye is rounded
to (-11264,-71915,286); the settled reference eye is
(-11264,-71913.5547,294.2199). Horizontal heading and pitch are zero in original
coordinates; vertical FOV is50.8154 degrees at the matching scene aspect ratio.
The approximately8.2-unit eye-height difference, different travelled positions,
head, weather, active NPCs and rendering differences remain explicit limits.
The reference holds09:31. Do not treat a camera sample as an actor position or
the remote daynight label as the automatic clock-step setting.

Unaltered ready-run frames show raised arms and changed leg poses in both
engines. This is a scoped reference, not an exact frame match, a complete
motion-quality judgement or acceptance of the reported failure. No new
implementation or package is claimed. Next compare motion at measured actual
speeds and phases, preserving the historical v0.0.38 control and these limits.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Game logic (QuakeC) and saves (`game-logic`). QuakeC entities, saves and game state. See [families](README.md#families).

- ARENA-MERGE-54 (no report page): Requested: one arena mode: the main game's arena minigame and the combat playground merged, with NPC against NPC fights to watch
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
- COMBAT-DAEDROTH-NO-HIT-51 (no report page): A daedroth outside the Azura s Coast stronghold cannot be punched: the blows pass through it; its runtime health reads 0.0
- [COMBAT-FATIGUE-HEALTH-DAMAGE-39](COMBAT-FATIGUE-HEALTH-DAMAGE-39.md): Clarify Eldafire bare-fist fatigue damage versus armed guard health damage
- [COMBAT-FIST-BLOCK-33](COMBAT-FIST-BLOCK-33.md): A fighter with a shield blocks while fighting with fists
- [COMBAT-HIT-RECOVERY-33](COMBAT-HIT-RECOVERY-33.md): Fatigue hits did not stagger, and knockdowns lasted half a second too long
- COMBAT-NO-AGGRO-SHOWN-51 (no report page): Punching a worshipper shows no hostility when the first blow lands
- [COMBAT-NO-CONDITION-33](COMBAT-NO-CONDITION-33.md): Weapon and shield condition were ignored in combat
- [COMBAT-NODICE-READOUT-40](COMBAT-NODICE-READOUT-40.md): No-dice combat readout labels living targets already down
- [COMBAT-NOT-SAVED-33](COMBAT-NOT-SAVED-33.md): Combat state and NPC deaths are not saved
- [COMBAT-PLAYER-ATTACK-TYPE-33](COMBAT-PLAYER-ATTACK-TYPE-33.md): The player's attack type and swing strength were random
- [COMBAT-PLAYER-DEATH-FALL-33](COMBAT-PLAYER-DEATH-FALL-33.md): The player does not collapse on death
- [COMBAT-PLAYER-KNOCKDOWN-33](COMBAT-PLAYER-KNOCKDOWN-33.md): The player's knockdown and knockout exist only in the combat rules
- [COMBAT-SETUP-DICE-BLOCK-33](COMBAT-SETUP-DICE-BLOCK-33.md): The Arena setup offers no dice/style choice before a fight, and there is no block button
- COMBAT-THINK-COST-68040-54 (no report page): On the slow 68040 preset one combat decision step (think) costs 34 ms with one fighter and 44 ms with four
- [DEBUG-MAP-SAVE-VALIDATION-32](DEBUG-MAP-SAVE-VALIDATION-32.md): After a debug map load of an open-world map the autosave fails validation; two of three also report Interior spawn blocked
- [DOOR-LOAD-LOCKS-MISSING-51](DOOR-LOAD-LOCKS-MISSING-51.md): Load doors ignore the original game's locks: every door into a room opens, locked or not
- [DOOR-TRAPS-NOT-SPRUNG-55](DOOR-TRAPS-NOT-SPRUNG-55.md): Trapped doors and containers open without their trap
- [ENGINE-ANGLEMOD-RANGE-35](ENGINE-ANGLEMOD-RANGE-35.md): anglemod returned 360 for -360 and passed NaN and out-of-range values on
- [ENGINE-QC-ARGS-SYSERROR-35](ENGINE-QC-ARGS-SYSERROR-35.md): Bad QuakeC sound arguments stopped the program; lightstyle had no range check
- [INTRO-CAMERA-GATING-38](INTRO-CAMERA-GATING-38.md): Opening vanity and third-person cameras expose an unselected default race
- [INVENTORY-CATALOG-LOOKUP-40](INVENTORY-CATALOG-LOOKUP-40.md): Inventory catalogue lookup and name sorting use an equality-only comparison
- INVENTORY-CATALOGUE-PARTIAL-54 (no report page): The item catalogue holds Morrowind items only: no lockpicks, probes, repair tools, apparatus or carried lights
- MWSCRIPT-CELLCHANGED-VOLATILE-54 (no report page): CellChanged made the sound-marker scripts volatile: 85 percent of Vivec's per-frame script work
- MWSCRIPT-DATA-UNKNOWN-NAMES-48 (no report page): Four Bloodmoon scripts read names declared nowhere in the game data and do not compile
- MWSCRIPT-INTERIOR-PLACEMENTS-48 (no report page): Scripted placements in rooms that have no edict are not attached: the engine has no room identity to match them (3,612 of 4,907 bindings are in rooms)
- MWSCRIPT-STATE-NOT-SAVED-48 (no report page): The compiled scripts' values (globals, object and script locals, journal indexes) are not in saved games
- [PHYSICS-GRAVITY-SCALE-36](PHYSICS-GRAVITY-SCALE-36.md): Gravity is Quake's 800 although the world is scaled 0.25: jumps and falls are several times faster than the original
- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry
- [PLAYER-JUMP-ORIGINAL-RULES-48](PLAYER-JUMP-ORIGINAL-RULES-48.md): The jump height and in-air control are still Quake's, not the original's Acrobatics, load and fatigue rules
- [PLAYER-JUMP-THIRDPERSON-38](PLAYER-JUMP-THIRDPERSON-38.md): Third-person player jump animation is missing
- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue
- [PLAYER-READY-WATER-MOVEMENT-38](PLAYER-READY-WATER-MOVEMENT-38.md): Readied weapon or torch appears to allow walking on water
- PLAYER-WALK-SPEED-SLOW-51 (no report page): The starting walk speed feels very slow; check it against the original and OpenMW
- [QC-AW-FLAME-SPAWN-32](QC-AW-FLAME-SPAWN-32.md): Every aw_flame entity prints load errors: the game logic has no aw_flame spawn function or aw_flame_size/aw_flame_shape fields
- RENDER-METADATA-29 (no report page): Native renderer metadata warns as an unknown QuakeC field
- SAVE-EQUIPMENT-29 (no report page): Quickload returns with hands and torch put away
- [SAVE-LAVA-DEATH-LOOP-38](SAVE-LAVA-DEATH-LOOP-38.md): Lava fall can leave an autosave that reloads into repeated death
- [SAVE-TELEPORT-CHECKPOINT-38](SAVE-TELEPORT-CHECKPOINT-38.md): Successful teleport needs a safe destination checkpoint
- [SERVER-FRAME-ARRIVAL-33](SERVER-FRAME-ARRIVAL-33.md): The server frame costs about 226 ms per frame at the Balmora arrival camera on a slow 68040
- SWEEP-ARENA-PIT-TWO-FAIL-54 (no report page): dbg sweep reports two failing entities in the Vivec Arena Pit (map vai000) in every session of the Arena Pit images
- TALK-PROMPT-NOT-TALKABLE-54 (no report page): The Talk prompt shows for any target with a voice string: hostile, dead, knocked out or without dialogue
- TRAVEL-SERVICES-CHIM-51 (no report page): Silt strider rides between towns do not work: travel knows only the old Seyda Neen and Balmora town maps, not the CHIM world, and none of the other routes
- UI-HUD-TOGGLE-KEY-51 (no report page): Requested: a key combination (for example Ctrl+Alt+H) that hides and shows the whole HUD in game, the crosshair with it
- [UI-INVENTORY-INTEGRATION-40](UI-INVENTORY-INTEGRATION-40.md): Inventory integration and safe world placement remain incomplete
- [WAIT-DURING-COMBAT-36](WAIT-DURING-COMBAT-36.md): Waiting is allowed in the middle of a fight
- [WAIT-FEET-IN-WATER-36](WAIT-FEET-IN-WATER-36.md): Waiting is allowed with the feet in water (the original refuses it)
- [WATER-GAMEPLAY-PARITY-38](WATER-GAMEPLAY-PARITY-38.md): Water gameplay lacks complete original behavior verification

Related bugs in other categories:

- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation

<!-- END GENERATED CATEGORY -->
