# PLAYER-READY-THIRDPERSON-38: Third-person player lacks fists-up and weapon-draw animation

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Third-person player body and equipment |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2 (last seen) |
| Severity | medium: Visible player equipment and ready-state feedback are missing. |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | v0.0.38-dev2 |
| From commit | source c2eaa5a, engine c2eaa5a, CHIM world c2eaa5a |
| CHIM engine version | CHIM 0.2.0, engine c2eaa5a, world format unknown |
| Unknown because | World format not transcribed into this report. |
| Platform or emulator | unknown (Maintainer did not specify emulator.) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-12: reported in v0.0.38-dev2
- 2026-10-12: BUILD-LAVA-CORE-BOUNDS-38: PLAYER-READY-THIRDPERSON-38 (2026-10-12): Maintainer reports no fists-up pose or weapon unsheathing animation on the third-person player body.
- 2026-10-13: seen again in v0.0.39-rc1: Maintainer confirms RC1 fight-ready posture is good and must be preserved.
- 2026-10-13: UI-DEATH-DAMAGE-TINT-38, candidate: PLAYER-READY-THIRDPERSON-38 (2026-10-13): Source diagnosis confirms the body ignores QuakeC ready state and omits the original ready/equip/unequip groups.
- 2026-10-14: Renewed RC2 gameplay reports: INTRO-CAMERA-GATING-38, PLAYER-JUMP-THIRDPERSON-38, PLAYER-READY-THIRDPERSON-38 and UI-KEY-HELP-STALE-38: 13 October 2026: reconciled completed RC1 source suite/Amiga compilation with pending ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Timeline](#timeline)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Exact RC1 evidence, 13 October 2026](#exact-rc1-evidence-13-october-2026)
- [Scoped maintainer posture control, 13 October 2026](#scoped-maintainer-posture-control-13-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Maintainer reports no fists-up pose or weapon unsheathing animation on the third-person player body. Exact weapon and race are not yet identified.

## Where

Third-person player body and its equipment animation in v0.0.38-dev2.

## How it happened

Source diagnosis, 13 October 2026: aw_view.c does not read the existing QuakeC
aw_hand_state/aw_hand_goal when selecting the player's body frame. The body
converter requests locomotion, hit, death and block, without idlehh or the
handtohand equip/unequip sections. Those original keys exist in both human and
beast skeletons. First-person hand state alone cannot animate the separate body.

Further source-data review confirms authored `idlehh`, `walkforwardhh`,
`runforwardhh` and `jumphh` sections in the human and beast skeletons. The female
override lacks these sections and must follow the existing group fallback to
the human base. Ready walking/running/jumping must use these authored movements;
a standing fists-up pose must not replace the moving legs. Equip/unequip need
upper-body layering over locomotion, matching the original animation priorities.
This finding establishes available source clips, not a repaired player body.

## Why it was not caught

No exact-package third-person equipment transition check is attached. General
camera or NPC animation checks do not establish player equipment behavior.

## Reproduction

The maintainer confirms F is the default sheathe/unsheathe key. Test F with fists
and a weapon equipped, then compare the third-person pose and transition.

Repeat the maintainer scenario above in dev2, recording race, equipment, view changes,
idle and movement. Independent native reproduction remains pending.

## Repair

Partial source candidate, 13 October: reuse AmiQuake alias frame selection and
the current animation sampler for original idlehh/walkforwardhh/runforwardhh
and jumphh takeoff/landing. Select bare-hand ready movement from the existing
QuakeC hand goal/state without changing those rules. Swimming and carried torch
do not select the fists-only groups. Missing ready groups fall back to normal
movement. A stance change during takeoff/landing preserves normalized progress
instead of restarting it. Death and shield-block priorities are retained.

Female ready clips fall back to the base rig when no female override exists;
the normal female walk remains separate. No standing pose replaces moving legs.
The body builder requires the original ready sections and fits them inside the
same 512 KiB alias-file ceiling. Five extra shared layout entries model 3,900
bytes across the 64 model entries and player layout; actual target memory and
frame costs have not been measured.

The next source candidate connects bare-hand equip/lower. It reuses the guard's
offline local-bone overlay at `Bip01 Spine1`, baking each original arm phase over
idle, walk, run, jump and landing poses. Female movement still supplies the legs.
The engine selects a single alias frame from this grid using its current leg
frame and the existing QuakeC hand-state elapsed fraction. Changing stance
preserves the normal/ready gait fraction; camera changes cannot restart the
authoritative action timer. Death/block priorities, first-person rules and
physics are unchanged. Swimming, noclip, carried torch and disabled animation
do not use the bare-hand overlay.

The requested model has 253 frames before fitting; the minimum is 93 with two
arm endpoints and the existing movement floors. These are plan counts, not
converted-model measurements. Fitting reduces whole grid dimensions, retaining
both arm endpoints and the selected movement poses, within the existing 512 KiB
file limit, alias-frame byte limit and 256-frame maximum. No budget is raised.
If none of the existing geometry budgets fits, the bake fails with the affected
appearance. Body-only layout words avoid growing every NPC's shared layout.
Malformed, incomplete, overlapping or unbound grid data disables the overlay.

No runtime skeletal evaluation is introduced. The guard retains its original
left-clavicle mask and 8/21-frame timing. The RC1 source passed Amiga compilation on 13 October 2026;
target costs remain unverified. Punch overlays, armed-weapon variants and torch attachment remain
unfinished; this source candidate does not close the maintainer report.

## Verification

Open. Added synthetic plan checks for original ready keys, female fallback,
in-place movement and minimum jump endpoints, plus C fixture cases for ready
speeds, swimming, old layouts and mid-air stance changes. The integrated RC1 source completed its automated suite and Amiga
compilation on 13 October 2026. All 20 body bakes, memory checks and matched
OpenMW/native captures with F at rest, moving and airborne remain pending.

Offline layer fixtures are also prepared for moving legs, female boundary
transforms, rotation/translation order, nested left-arm priority and invalid
hierarchies. The guard pass-cache fixture requires the shared sampler to remain
in its source fingerprint. Earlier integrated source suites completed. The existing guard-torch
model/animation assets are covered by the 1,751 unchanged non-body asset
controls. Native guard behavior acceptance remains separate.

Prepared draw/lower cases cover independent female leg/arm phases, budget
exhaustion, fitted grid indexing, endpoint retention and alias limits. C cases
cover frame selection, malformed/incomplete/overlapping tables, old layouts and
normal/ready gait continuity. Earlier integrated source suites completed. All 20 actual RC1 body
bakes and exact layout/model bindings passed; Amiga compilation passed. Still require matched F-at-rest/walking/
running/airborne/landing views, including toggle reversal and camera changes.
Measure loading, cache/RAM and normal-speed frame time before acceptance.

## Prevention

Exact-package checks must cover equipment meshes and poses independently of
lighting, in both first and third person, at idle and while moving.

## Exact RC1 evidence, 13 October 2026

The exact RC1 package was independently extracted and read back. All 20 body
models and layouts passed their actual-format checks; 1,751 existing non-body
model/animation assets remained byte-identical. A Nord male session exercised
third-person ready/lower, movement, jump and camera changes. This is one
appearance and scene; matched original-game views, all-appearance motion,
loaded memory and performance acceptance remain separate.

## Scoped maintainer posture control, 13 October 2026

The maintainer explicitly confirms that the RC1 fight-ready posture is good and must be preserved. This is a scoped posture control; torch holding, leg shape, fast gait and punch acceptance remain separate. Preserve the existing fight-ready silhouette and posture while changing action grids, leg geometry or movement playback. Bare-hand posture approval does not close the broader original weapon/equipment issue.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- [AW-20260928-18](AW-20260928-18.md): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- [DEBUG-TORCH-64](DEBUG-TORCH-64.md): The debug torch no longer lights with V: the console says no light is equipped
- FIRST-PERSON-BLOCK-ITEM-TABLE-59 (no report page): The first-person shield block refuses a shield whose model comes from the shared item model table
- [FIRST-PERSON-WEAPON-SETS-MISSING-54](FIRST-PERSON-WEAPON-SETS-MISSING-54.md): First-person hands have only 4 of the 103 original animation groups: no weapon stance or attack, spellcast, hit, swim or storm
- [FP-ARMS-CUT-62](FP-ARMS-CUT-62.md): In first person, looking down shows the forearms ending in mid-air, with no upper arms or shoulders behind them
- [FP-ARMS-LANTERN-NOT-DRAWN-HANDSIMAGE-67](FP-ARMS-LANTERN-NOT-DRAWN-HANDSIMAGE-67.md): On a test build of the per-race first-person hands, the first-person arms, the held lantern and its light are not drawn at all, looking ahead or down; the same walk on the earlier build showed the arm, the lantern and its light
- [FP-ARMS-NO-MODEL-SLOT-67](FP-ARMS-NO-MODEL-SLOT-67.md): After the race or sex is changed several times in one place, the first-person arms turn into an old hand model with holes and the held lantern is not drawn
- [FP-BARE-HAND-OTHER-SKIN-67](FP-BARE-HAND-OTHER-SKIN-67.md): In first person the bare hand of some races has another race's skin and looks gloved, unlike the arm
- [FP-FISTS-LUMP-67](FP-FISTS-LUMP-67.md): Drawing the fists in first person shows a lump in the top left corner of the view instead of the fists
- [FP-FOREARMS-BELOW-VIEW-61](FP-FOREARMS-BELOW-VIEW-61.md): In first person only the hands show: the forearms and the sleeves worn on them stay below the view
- [FP-HANDS-PER-RACE-67](FP-HANDS-PER-RACE-67.md): In first person the Nord man, the Imperial woman and the Dark Elf and Redguard men show another race's or sex's hand, as the game's records name it, and the skin steps at the wrist
- [FP-WEAPON-SWAY-60](FP-WEAPON-SWAY-60.md): The weapon in first-person view moves more while walking than in the original
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- [HAND-PUNCH-TRANSITION-29](HAND-PUNCH-TRANSITION-29.md): Hands briefly disappear when changing into the punch animation
- [HELD-LIGHT-ALWAYS-TORCH-61](HELD-LIGHT-ALWAYS-TORCH-61.md): Any carried light held in the hand is drawn and lit as a torch
- [HELD-LIGHT-NOT-IN-HAND-65](HELD-LIGHT-NOT-IN-HAND-65.md): An equipped candlestick is not held in the hand; readying shows only the fists
- [PLAYER-3P-HELD-ITEM-STALE-65](PLAYER-3P-HELD-ITEM-STALE-65.md): After a new weapon is given and readied, the third-person body still holds the light that was equipped before
- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- [PLAYER-EQUIPMENT-NOT-WORN-54](PLAYER-EQUIPMENT-NOT-WORN-54.md): The player body shows no chosen head or hair, no worn clothing or armour and no weapon: it is baked per race and sex with fixed new-game looks
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- [PLAYER-PARTS-BAKE-REFUSED-59](PLAYER-PARTS-BAKE-REFUSED-59.md): Two body part meshes are refused by the assembled player body's parts library
- [PLAYER-PARTS-HAIR-FALSE-STOP-67](PLAYER-PARTS-HAIR-FALSE-STOP-67.md): The player-view stage stops on two of Tribunal's own Dark Elf hairs, calling them another race's part: their mesh names write the race without its space
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation
- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains
- [TORCH-ACTIVATE-CRASH-25](TORCH-ACTIVATE-CRASH-25.md): Raising the fists and pressing V crashed the game: a dynamic light was marked through a negative collision root
- [TORCH-FLAME-VISIBILITY-29](TORCH-FLAME-VISIBILITY-29.md): Torch flame not visible after changing styles
- [TORCH-FUEL-29](TORCH-FUEL-29.md): Torch never burns out; no unlit or fuel state
- [TORCH-HAND-NORD-29](TORCH-HAND-NORD-29.md): Detached-looking left grip fragment in dev4
- [TORCH-HAND-SEPARATION-29](TORCH-HAND-SEPARATION-29.md): Torch grip and hand appear to break during idle and running
- [TORCH-HAND-TO-HAND-64](TORCH-HAND-TO-HAND-64.md): With a torch equipped the fists cannot fight, raising them brings the torch back and V cannot put it away
- [TORCH-INPUT-29](TORCH-INPUT-29.md): F cannot raise hands; V only prints torch state
- [TORCH-INVENTORY-PICTURE-64](TORCH-INVENTORY-PICTURE-64.md): Unequipping the torch in the inventory still shows a torch in the hand

Related bugs in other categories:

- [PUNCH-3P-HEART-CHAMBER-67](PUNCH-3P-HEART-CHAMBER-67.md): After a teleport to the Heart Chamber the player's punch at a dreamer does not land or does not show in third-person view; in first person it works

<!-- END GENERATED CATEGORY -->
