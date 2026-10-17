# PLAYER-PUNCH-THIRDPERSON-39: Third-person punches have no visible player-body attack animation

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 4 times; something has to be done

- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Source candidate: two male bodies retain full8/6 gait plus punch within512 KiB;83 affected tests pass. Target/native/visual/all-appearance/RC2-package acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): All 20 body pairs pass binary checks with gait/punch declarations; 33 guard checks pass, earlier 83 retained. Visible punch, seams and native/package/maintainer acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): Scoped Nord male/Orc female candidate footage shows torso/arm punch motion and ready movement. Display only: damage, LMB, all appearances, matched A/B, seams, package/maintainer acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-14 (time not recorded): Maintainer repeats no third-person punch from physical LMB in RC2. One exact input/damage control succeeds; maintainer-case visible animation remains unaccepted.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 13 October 2026, in v0.0.39-rc1 |
| Where | Gameplay/combat: third-person player with fists readied |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-rc1, v0.0.39-rc2 (last seen) |
| Severity | critical: The maintainer stopped release because basic third-person combat has no visible punch animation. |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | v0.0.39-rc1 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Maintainer named RC1; the exact running image and binary were not independently read back for this report. |
| Platform or emulator | unknown (Emulator not restated for this specific observation.) |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [PERSISTING: reported 4 times; something has to be done](#persisting-reported-4-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Earlier all-appearance failure, 13 October 2026](#earlier-all-appearance-failure-13-october-2026)
- [Corrected RC2 all-body result and seam limits, 13 October 2026](#corrected-rc2-all-body-result-and-seam-limits-13-october-2026)
- [Scoped candidate native punch observation, 13 October 2026](#scoped-candidate-native-punch-observation-13-october-2026)
- [Post-pin RC2 package observation, 14 October 2026](#post-pin-rc2-package-observation-14-october-2026)
- [Renewed maintainer failure and ordinary-input controls, 14 October 2026](#renewed-maintainer-failure-and-ordinary-input-controls-14-october-2026)
- [Held attack during raising: 14 October 2026, v0.0.40-dev1](#held-attack-during-raising-14-october-2026-v0040-dev1)
- [Scoped physical-input native control, 14 October 2026](#scoped-physical-input-native-control-14-october-2026)
- [Later outgoing-hit control, 14 October 2026](#later-outgoing-hit-control-14-october-2026)
- [Selected Argonian recording limit, 14 October 2026](#selected-argonian-recording-limit-14-october-2026)
- [Queued diagnostic sampling limit, 14 October 2026](#queued-diagnostic-sampling-limit-14-october-2026)
- [Argonian ordinary-view attack observation, 14 October 2026](#argonian-ordinary-view-attack-observation-14-october-2026)
- [Khajiit follow-up diagnostic, 14 October 2026](#khajiit-follow-up-diagnostic-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Drawing the fists animates, but pressing default attack LMB shows no third-person punching animation. The maintainer corrected the initial input-failure report: the punch apparently executes; missing body animation is the confirmed symptom. Actual hit/damage behavior is not independently verified.

## Where

Gameplay/combat: third-person player with fists readied. Reported in v0.0.39-rc1 on 13 October 2026.
Exact running binary, map pose and appearance details require capture/readback.

## How it happened

Source review identifies a missing body-punch selection/bake path. RC1 ready/draw/lower body groups did not bind the existing QuakeC aw_hand_punch clock to a third-person punch arm layer. The candidate reuses the existing first-person action state/timing and AmiQuake alias frame interpolation; it does not introduce a second damage clock or equate a displayed punch with a hit.

## Why it was not caught

Earlier scoped checks did not establish this exact visual behavior in the maintainer scenario. Successful damage, movement, model parsing or unrelated animations do not prove this animation or shape is correct.

## Reproduction

Switch to third person, draw fists with F, then press LMB at rest and while moving. Record the body and attack state; compare first-person attack and camera changes without equating absent animation with absent damage.

## Repair

Source candidate binds the original punch state/clock and authored punch layers over ready idle/walk/run/jump/land. Compact action grids retain full gait samples inside the existing budgets. Preserve block/death priorities and the approved fight-ready posture. No repaired native/package or maintainer punch acceptance is claimed.

## Verification

Source candidate uses compact draw/lower/punch layer grids while retaining full normal and ready gait. Isolated Nord and Khajiit male bakes/readbacks pass under the exact RC1 budget environment: normal walk8/run6, ready walk8/run6 and authored punch layers;105 frames each,512x96 atlas. Nord has357 triangles and520,564 bytes; Khajiit358 triangles and521,876 bytes, each below512 KiB. Eighty-three affected automated checks pass. These were the first two isolated source-candidate controls; the corrected all-body binary result below extends file coverage. Actual native/visual repair, complete RC2 package readback and maintainer acceptance remain pending.

The maintainer explicitly confirms that the RC1 fight-ready posture is good and must be preserved. This is a scoped posture control; torch holding, leg shape, fast gait and punch acceptance remain separate.

## Prevention

Require an exact-package native reproduction and repaired capture of this scenario, with unaffected first/third-person behavior and normal-speed timing as controls. Keep automated checks, target observation and maintainer acceptance separate.

## Earlier all-appearance failure, 13 October 2026

The earlier isolated RC2 body run failed on Breton female: the 480 attempt could not fit and the lower-budget retries failed the leg-section guard. Preserve this failure under [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md) as historical evidence. The corrected all-body result below supersedes its incomplete-set limit without providing native/visual or package acceptance.

## Corrected RC2 all-body result and seam limits, 13 October 2026

The corrected isolated candidate now passes actual-format model/layout checks for all 20 race/sex body pairs under the unchanged 512 KiB limit. Sixteen exact prior pairs were reused with provenance checks; High Elf, Nord, Orc and Redguard female models were newly baked/read back at 523,464, 522,164, 520,864 and 520,864 bytes respectively, with 104 frames each. Full normal/ready walk 8/run 6 and authored punch declarations are retained. These are body-file checks, not a complete RC2 image or package.

The anatomical leg-section guard now uses labelled leg parts 17â€“22 in both compared meshes, excluding Khajiit tail part 26 from the width test. Its 75% threshold and the actual model/alias budgets remain unchanged. Thirty-three focused automated checks pass against the exact corrected source snapshot, including the tail/narrow-leg regression. The earlier 83 affected body/animation checks remain separate evidence, not a rerun of the latest full suite.

Read-only section audits still identify possible knee/calf gaps in five fallback bodies. Part extrema extend up to 0.415 units beyond authored bounds; knee/calf 2D section Hausdorff distance increases from about 0.45â€“0.58 to 1.17â€“1.83 units. Plain 384 simplification causes most of that increase; contour adjustment adds 0â€“0.13 units. These are geometry metrics, not proof of a visible hole or an accepted repair. Native silhouette/seam inspection, matched v0.0.38 gait and RC1 ready controls, original-game comparison, memory/performance, exact package and maintainer acceptance remain pending.

## Scoped candidate native punch observation, 13 October 2026

Review of isolated candidate footage shows displayed punches on Nord male and Orc female bodies: torso twist/arm extension differs from the earlier RC1 ready-only observation. The Orc female view shows extension at 8.0/8.2 seconds and return by 8.4, with actual ready-movement positions progressing Y 0â†’225â†’468. Both diagnostics use the earlier compiled candidate engine and isolated body assets, not a complete RC2 image. This is scoped visible animation evidence only; it does not establish damage, LMB input, all appearances, matched original-game/v0.0.38 comparison, leg seams, package or maintainer acceptance.

## Post-pin RC2 package observation, 14 October 2026

The independently extracted RC2 package shows Nord third-person torso/arm punch changes in an unaltered native clip. Post-exit readback preserves exact assets. Console attack control does not prove physical LMB input or damage; all appearances, matched original comparison, seams and maintainer acceptance remain pending.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Maintainer acceptance and final v0.0.39 clearance remain pending.

## Renewed maintainer failure and ordinary-input controls, 14 October 2026

The maintainer again reports no third-person punching animation from physical LMB in
RC2, and identifies its gameplay as the same as final v0.0.39. This finding
supersedes any implication that the earlier console-driven pose clip accepted
the ordinary-input scenario. The current register entry remains open.

The exact delivered RC2 engine SHA-256
`ef0bfa4fc2b5225fb6583f0ca012e62a77291b79652235900d730c23c1bb6da1`
reaches ready state 2/goal 1 from physical F; physical LMB reaches attack state 3,
frame 24 and registers a 60-point fatigue hit against a guard. This proves one
physical-input and damage path. It does not prove visible body motion, the maintainer
appearance/state or universal combat correctness. A separate after-Census Nord
control records physical LMB pulses; a still taken after a pulse cannot establish
the punch animation. Inspect the continuous native capture before judging it.

Repeat physical LMB at rest and during unobstructed ready movement, in both
views, while recording input, body clock/frame and damage separately. Preserve
the approved ready posture. No gameplay repair or maintainer acceptance follows from
these baseline controls.


## Held attack during raising: 14 October 2026, v0.0.40-dev1

A second, narrower input failure is now reproduced by executing the compiled
QuakeC in the existing engine VM fixture. Press and hold LMB while F is still
raising the fists: the old code set the attack latch before state 2 could
accept the attack, so continuing to hold LMB never punched.

The source repair leaves that held press pending only during raising. A
release cancels it; after acceptance the usual latch still prevents held
autofire. The same fixture verifies cancellation by lowering, no punch while
carrying a torch, a subsequent genuine press, all authored animation bounds
and region-transition hand state. It fails on the old code and passes on the
repair. This reuses AmiQuake's input bit and existing QuakeC state machine;
it adds no second action clock.

This is a source and executable-VM result. Native physical-input verification
and visible third-person animation remain pending, and this is not yet an
established explanation for the maintainer's inability to move with fists drawn.

## Scoped physical-input native control, 14 October 2026

The exact v0.0.40-dev1 male-Nord diagnostic starts with fists stowed, presses
physical F and holds physical LMB through raising. Diagnostics reach hands
state 3, frame 23, attack 1 and latched 1; the original game clip shows arm
changes. This is scoped visible attack/input evidence for that control.
No target was hit and damage was not tested. Other appearances, smoothness,
the maintainer's original scenario and maintainer acceptance remain separate; this
observation does not close the issue.

## Later outgoing-hit control, 14 October 2026

Physical held-fist attacks against Fargoth with normal dice produce outgoing
misses: recorded chances fall from 19 to 1 to 0 as the exchange continues.
Fargoth remains at health 41/41 and fatigue 153/154. This establishes outgoing
attack processing in this control, not a successful hit or outgoing damage.
It does not accept the maintainer's animation case, all appearances or pacing.

## Selected Argonian recording limit, 14 October 2026

The later male-Argonian selected-body diagnostic retains physical punch and
ordinary fists-readied movement footage. Movement succeeds in WALK3, but closer
punch/pose review remains pending. Neither movement nor a separate no-dice
readout control establishes normal-dice unarmed damage or complete original
punch presentation.

## Queued diagnostic sampling limit, 14 October 2026

A later side-view recording's 120 state-2-only readouts cannot establish absent
punch animation. Its diagnostic wait/readout burst was submitted before the host physical LMB
press/release submissions. The input bindings append to the same tail, so this
arrangement can defer the attack until those samples have finished.

AmiQuake Key_Event appends the bound +attack and -attack commands with
Cbuf_AddText. That routine appends to the existing tail; wait stops command
execution until the next frame while retaining the remaining queue. Consuming
a diagnostic mailbox proves enqueueing, not completion. The retained timing
records host input-submission times before observation of the burst end marker;
exact guest Key_Event and end-marker execution timestamps were not recorded.

This explains the sampling limitation without introducing a gameplay defect.
The missing attack-state/body frame in those samples is not proof of a missing
punch, and does not establish Preview-specific LMB suppression. Source inspection
of normal Preview input does not identify such a blocker; death-prompt input
handling is a separate context. This does not accept every Preview/input state.

Before another physical-input capture, confirm the diagnostic queue has drained
and keep observations from blocking the input being measured. Retain physical
event timing, actual state transitions and original footage together. The prior
scoped animation and movement evidence is preserved; correct visible punches,
normal-dice unarmed damage, all appearances and complete acceptance remain open.
No engine or shipped-package change is made by this finding.

## Argonian ordinary-view attack observation, 14 October 2026

A fresh diagnostic of the unchanged delivered v0.0.40-dev1 build now records
physical LMB from stationary, dry-ground, fists-readied male Argonian gameplay.
The ordinary third-person camera reports attack state 3 and body frames 102 and
103 of 122. Original video frames show arm movement; a separate side Preview
recording makes the extension and return easier to inspect and also records
state 3/frame 102. Warp-off was visually confirmed before both recordings,
which retain actual game audio. Short diagnostics completed before input;
no wait/readout burst preceded the physical mouse edges.

This establishes the selected body's attack animation in these two contexts.
It does not establish normal-dice hit/damage, every race/sex, transitions while
moving, original animation quality or overall playtest acceptance. The initial
reported failures and older inconclusive recording remain evidence. No game
source or delivered package was changed for this observation; newer inventory
pose source is separate. The issue remains OPEN.

The emulator parent and container both exited normally with status 0. A strict
closure log check nevertheless rejected two handled JIT diagnostics during boot;
that failed gate remains preserved. A separately labelled post-exit check
verified all 153 declared resources, 33 key bindings and a valid disk bitmap.
It does not turn the failed closure gate into a pass, and the played diagnostic
disk is never a packaging input. CHIM coverage is unchanged.

## Khajiit follow-up diagnostic, 14 October 2026

Test source `90ba44c2cc079de50e50b8e1a8cde76dd2bcf318`, engine SHA-256 `166ffbecbcd399f9d9fe3ed2d5f3bdc259bf17a0bfe7f1e933a1222bf264b2a2`, using the previously delivered v0.0.40-dev1 world. The post-Census diagnostic character was changed through the actual appearance menu. This is an unreleased diagnostic, not a new shipment.

The actual Khajiit female selection (face 1, hair 1) is a scoped positive control. Physical F lowers fists (state 0 / goal 0) and redraws them (state 2 / goal 1). Physical W/A/S/D changes position in dry normal WALK movement with fists drawn. Stationary LMB produces attack state 3 and body frames 86-87 of 106; a D-strafe punch produces state 3 / body frame 97 with velocity 119.6, 1.6, 0. Original video frames show arm changes. The first forward-moving capture missed the transient in its delayed readout and remains inconclusive for simultaneous attack state.

Warp was visibly disabled, and recordings contain actual game audio. This does not reproduce or close the reported failure, establish damage, or accept anatomy, gait quality, blocking, swimming, all appearances or original-game parity.

The separate normal shutdown check records actual emulator-parent and container exit status 0, followed by 194 resource checks, 33 key bindings and a valid bitmap. This does not retroactively repair the earlier failed shutdown receipt. Played disks remain diagnostic evidence only.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- AW-20260928-18 (no report page): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- HAND-PUNCH-TRANSITION-29 (no report page): Hands briefly disappear when changing into the punch animation
- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- [PLAYER-READY-THIRDPERSON-38](PLAYER-READY-THIRDPERSON-38.md): Third-person player lacks fists-up and weapon-draw animation
- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains
- TORCH-FLAME-VISIBILITY-29 (no report page): Torch flame not visible after changing styles
- TORCH-FUEL-29 (no report page): Torch never burns out; no unlit or fuel state
- TORCH-HAND-NORD-29 (no report page): Detached-looking left grip fragment in dev4
- TORCH-HAND-SEPARATION-29 (no report page): Torch grip and hand appear to break during idle and running
- TORCH-INPUT-29 (no report page): F cannot raise hands; V only prints torch state

Related bugs in other categories:

- [PLAYER-READY-MOVEMENT-39](PLAYER-READY-MOVEMENT-39.md): Third-person player cannot move with fists drawn

<!-- END GENERATED CATEGORY -->
