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

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

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

- AW-20260928-18 (no report page): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- FIRST-PERSON-WEAPON-SETS-MISSING-54 (no report page): First-person hands have only 4 of the 103 original animation groups: no weapon stance or attack, spellcast, hit, swim or storm
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- HAND-PUNCH-TRANSITION-29 (no report page): Hands briefly disappear when changing into the punch animation
- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- PLAYER-EQUIPMENT-NOT-WORN-54 (no report page): The player body shows no chosen head or hair, no worn clothing or armour and no weapon: it is baked per race and sex with fixed new-game looks
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation
- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains
- TORCH-FLAME-VISIBILITY-29 (no report page): Torch flame not visible after changing styles
- TORCH-FUEL-29 (no report page): Torch never burns out; no unlit or fuel state
- TORCH-HAND-NORD-29 (no report page): Detached-looking left grip fragment in dev4
- TORCH-HAND-SEPARATION-29 (no report page): Torch grip and hand appear to break during idle and running
- TORCH-INPUT-29 (no report page): F cannot raise hands; V only prints torch state

<!-- END GENERATED CATEGORY -->
