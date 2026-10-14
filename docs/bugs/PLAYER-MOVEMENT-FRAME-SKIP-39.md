# PLAYER-MOVEMENT-FRAME-SKIP-39: Third-person Nord and Khajiit fast movement loses smooth foot animation

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 3 times; something has to be done

- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Owner identifies v0.0.38 as last known good fast gait. RC1 has few poses; sample coverage and speed-linked playback both need repair checks. Owner comparison, not independent acceptance.
- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Source candidate: two male bodies retain full8/6 gait plus punch within512 KiB;83 affected tests pass. Target/native/visual/all-appearance/RC2-package acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): All 20 body pairs pass binary checks; prior bake failure retained. Full 8/6 gait declarations do not establish speed-linked smoothness or native/package/owner acceptance.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 13 October 2026, in v0.0.39-rc1 |
| Where | Third-person Nord and Khajiit walking/running, fists lowered and readied |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-rc1 (last seen) |
| Severity | high: Visible RC1 player/NPC presentation failure reported by the owner. |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | v0.0.39-rc1 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Owner named RC1; the exact running image and binary were not independently read back for this report. |
| Platform or emulator | unknown (Emulator not restated for this specific observation.) |

<!-- END GENERATED FACTS -->

## Symptom

Fast third-person movement no longer has the earlier quick foot animation and looks like skipped frames. The owner additionally describes the run as two frames.

## Where

Third-person Nord and Khajiit walking/running, fists lowered and readied. Reported on 13 October 2026 in v0.0.39-rc1.

## How it happened

Replay of the RC1 player-body frame fitter with actual geometry counts reduces requested normal walk/run from eight/six poses to two/two for Nord and Khajiit. Ready walk/run remain eight/six. Draw/lower action grids multiply the normal movement counts, so the budget fitter preferentially removes their poses. The inherited alias renderer selects supplied frames; it cannot restore absent poses.

## Why it was not caught

Earlier model-budget and scoped native checks did not demonstrate this exact
appearance and behavior. Passing file/layout validation is not visual acceptance.

## Reproduction

Capture Nord and Khajiit at walk and fast run, lowered and readied, with the same speed and normal emulator pacing. Read actual body MDL/ANM counts; compare previous working body and matched OpenMW. Also check draw/lower, punch, jump, camera switches and leg proportions.

## Repair

Source candidate compacts upper-body action grids while preserving normal walk8/run6 and ready walk8/run6, plus authored punch layers. The isolated Nord/Khajiit male output actually contains those groups; this corrects source sample loss without proving target smoothness. Retain movement-speed-linked playback and compare the owner-reported v0.0.38 control at normal emulator pacing.

## Verification

Source candidate uses compact draw/lower/punch layer grids while retaining full normal and ready gait. Isolated Nord and Khajiit male bakes/readbacks pass under the exact RC1 budget environment: normal walk8/run6, ready walk8/run6 and authored punch layers;105 frames each,512x96 atlas. Nord has357 triangles and520,564 bytes; Khajiit358 triangles and521,876 bytes, each below512 KiB. Eighty-three affected automated checks pass. These were the first two isolated source-candidate controls; the corrected all-body binary result below extends file coverage. Actual native/visual repair, complete RC2 package readback and owner acceptance remain pending.

The owner explicitly confirms that the RC1 fight-ready posture is good and must be preserved. This is a scoped posture control; torch holding, leg shape, fast gait and punch acceptance remain separate. The owner-reported v0.0.38 working gait remains a comparison requirement, not independent candidate acceptance.

## Prevention

Check the actual extracted package, original identity and normal-speed animation
in addition to model/layout budgets. Preserve earlier working controls.

## RC1 owner evidence, 13 October 2026

The original images remain private. Rounded HUD readings are location aids,
not exact source/package bindings or proof of motion.

- Text report: run animation looks like two frames. Source fitter replay independently yields two normal walk/run poses for Nord and Khajiit.

## Pose coverage and speed-linked playback, 13 October 2026

The owner reiterates that faster movement previously hastened the foot animation and explicitly identifies v0.0.38 as the last known good comparison. This is owner-reported comparison evidence, not an independently reproduced native control. RC1 appears to show only a couple of frames. The source fitter replay independently confirms two normal walk and two normal run samples for Nord and Khajiit. Restoring samples and making playback follow actual movement speed are separate checks: a faster clock cannot restore missing poses. Source presence alone does not establish baked coverage. The isolated two-male-body readback below now confirms restored samples for those bodies; normal-speed native smoothness, other appearances and complete package acceptance remain pending. Check slow walk, ordinary run and convenient debug-fast movement, lowered/readied states and both appearances against the original and exact v0.0.38 control.

## Earlier all-appearance failure, 13 October 2026

The earlier isolated RC2 body run failed on Breton female: the 480 attempt could not fit and the lower-budget retries failed the leg-section guard. Preserve this failure under [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md) as historical evidence. The corrected all-body result below supersedes its incomplete-set limit without providing native/visual or package acceptance.

## Corrected RC2 all-body result and seam limits, 13 October 2026

The corrected isolated candidate now passes actual-format model/layout checks for all 20 race/sex body pairs under the unchanged 512 KiB limit. Sixteen exact prior pairs were reused with provenance checks; High Elf, Nord, Orc and Redguard female models were newly baked/read back at 523,464, 522,164, 520,864 and 520,864 bytes respectively, with 104 frames each. Full normal/ready walk 8/run 6 and authored punch declarations are retained. These are body-file checks, not a complete RC2 image or package.

The anatomical leg-section guard now uses labelled leg parts 17–22 in both compared meshes, excluding Khajiit tail part 26 from the width test. Its 75% threshold and the actual model/alias budgets remain unchanged. Thirty-three focused automated checks pass against the exact corrected source snapshot, including the tail/narrow-leg regression. The earlier 83 affected body/animation checks remain separate evidence, not a rerun of the latest full suite.

Read-only section audits still identify possible knee/calf gaps in five fallback bodies. Part extrema extend up to 0.415 units beyond authored bounds; knee/calf 2D section Hausdorff distance increases from about 0.45–0.58 to 1.17–1.83 units. Plain 384 simplification causes most of that increase; contour adjustment adds 0–0.13 units. These are geometry metrics, not proof of a visible hole or an accepted repair. Native silhouette/seam inspection, matched v0.0.38 gait and RC1 ready controls, original-game comparison, memory/performance, exact package and owner acceptance remain pending.

## Post-pin RC2 package observation, 14 October 2026

Full gait samples are present in the read-back RC2 body assets, but package presence and scoped punch/water footage do not establish normal-speed fast-gait timing, original speed-linked playback or owner acceptance. Preserve the owner-reported v0.0.38 comparison and good RC1 ready posture.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Owner acceptance and final v0.0.39 clearance remain pending.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- AW-20260928-18 (no report page): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- HAND-PUNCH-TRANSITION-29 (no report page): Hands briefly disappear when changing into the punch animation
- [PLAYER-BODY-LEG-SHAPE-39](PLAYER-BODY-LEG-SHAPE-39.md): Nord player legs appear abnormally thin in RC1
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation
- [PLAYER-READY-THIRDPERSON-38](PLAYER-READY-THIRDPERSON-38.md): Third-person player lacks fists-up and weapon-draw animation
- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains
- TORCH-FLAME-VISIBILITY-29 (no report page): Torch flame not visible after changing styles
- TORCH-FUEL-29 (no report page): Torch never burns out; no unlit or fuel state
- TORCH-HAND-NORD-29 (no report page): Detached-looking left grip fragment in dev4
- TORCH-HAND-SEPARATION-29 (no report page): Torch grip and hand appear to break during idle and running
- TORCH-INPUT-29 (no report page): F cannot raise hands; V only prints torch state

Related bugs in other categories:

- [PLAYER-MOVEMENT-STATS-PARITY-39](PLAYER-MOVEMENT-STATS-PARITY-39.md): Walking/running use fixed debug speeds and do not apply original stats or running fatigue

<!-- END GENERATED CATEGORY -->
