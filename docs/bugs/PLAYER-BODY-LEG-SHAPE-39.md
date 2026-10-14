# PLAYER-BODY-LEG-SHAPE-39: Nord player legs appear abnormally thin in RC1

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.39-rc1 at 2026-10-13 (time not recorded): Source candidate: two male bodies retain full8/6 gait plus punch within512 KiB;83 affected tests pass. Target/native/visual/all-appearance/RC2-package acceptance pending.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): All 20 bodies pass binary checks. Section audits flag possible knee/calf gaps, mostly simplification. Metrics do not prove visible holes; native/original and owner acceptance pending.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 13 October 2026, in v0.0.39-rc1 |
| Where | Player body: Nord leg geometry and pose |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-rc1 (last seen) |
| Severity | high: The owner reports a major character-body shape regression. |
| Family | First-person hands and torch (`torch-hands`) |
| Playtest version | v0.0.39-rc1 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM unknown, engine unknown, world format unknown |
| Unknown because | Owner named RC1; the exact running image and binary were not independently read back for this report. |
| Platform or emulator | unknown (Emulator not restated for this specific observation.) |

<!-- END GENERATED FACTS -->

## Symptom

The owner reports abnormally thin, distorted-looking legs on a Nord player body. Sex, exact pose and selected appearance were not specified. Shape and animation causes remain separate possibilities.

## Where

Player body: Nord leg geometry and pose. Reported in v0.0.39-rc1 on 13 October 2026.
Exact running binary, map pose and appearance details require capture/readback.

## How it happened

The RC1 animation/frame budget fallback reduced the Nord model to227 triangles versus446 in the compared v0.0.38 body. This is a source/payload finding consistent with a geometry hypothesis, not proof of the visible leg cause. Pose, decimation, clothing and camera still need matched native/original comparison.

## Why it was not caught

Earlier scoped checks did not establish this exact visual behavior in the owner scenario. Successful damage, movement, model parsing or unrelated animations do not prove this animation or shape is correct.

## Reproduction

Capture the reported Nord body at idle, ready, moving and jumping in the same camera pose; compare the previous model and matched original-game reference. Inspect mesh budgets and limb silhouette without assuming simplification is the cause.

## Repair

Source candidate reduces action-grid multiplication to preserve geometry and full gait, and refuses a fallback that narrows combined visible leg sections against the budget-480 body proxy. The guard is not an exact v0.0.38 comparison. Section bounds/width alone do not establish limb appearance, per-leg topology or native repair.

## Verification

Source candidate uses compact draw/lower/punch layer grids while retaining full normal and ready gait. Isolated Nord and Khajiit male bakes/readbacks pass under the exact RC1 budget environment: normal walk8/run6, ready walk8/run6 and authored punch layers;105 frames each,512x96 atlas. Nord has357 triangles and520,564 bytes; Khajiit358 triangles and521,876 bytes, each below512 KiB. Eighty-three affected automated checks pass. These were the first two isolated source-candidate controls; the corrected all-body binary result below extends file coverage. Actual native/visual repair, complete RC2 package readback and owner acceptance remain pending.

Read-only leg-section measurements compare candidate, exact RC1 and v0.0.38 models. They remain geometric diagnostics, not a repaired appearance capture. The proxy guard and measurements must not be reported as visual acceptance.

The owner explicitly confirms that the RC1 fight-ready posture is good and must be preserved. This is a scoped posture control; torch holding, leg shape, fast gait and punch acceptance remain separate.

## Prevention

Require an exact-package native reproduction and repaired capture of this scenario, with unaffected first/third-person behavior and normal-speed timing as controls. Keep automated checks, target observation and owner acceptance separate.

## Earlier all-appearance failure, 13 October 2026

The earlier isolated RC2 body run failed on Breton female: the 480 attempt could not fit and the lower-budget retries failed the leg-section guard. Preserve this failure under [BUILD-PLAYER-BODY-BUDGET-FALLBACK-39](BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md) as historical evidence. The corrected all-body result below supersedes its incomplete-set limit without providing native/visual or package acceptance.

## Corrected RC2 all-body result and seam limits, 13 October 2026

The corrected isolated candidate now passes actual-format model/layout checks for all 20 race/sex body pairs under the unchanged 512 KiB limit. Sixteen exact prior pairs were reused with provenance checks; High Elf, Nord, Orc and Redguard female models were newly baked/read back at 523,464, 522,164, 520,864 and 520,864 bytes respectively, with 104 frames each. Full normal/ready walk 8/run 6 and authored punch declarations are retained. These are body-file checks, not a complete RC2 image or package.

The anatomical leg-section guard now uses labelled leg parts 17–22 in both compared meshes, excluding Khajiit tail part 26 from the width test. Its 75% threshold and the actual model/alias budgets remain unchanged. Thirty-three focused automated checks pass against the exact corrected source snapshot, including the tail/narrow-leg regression. The earlier 83 affected body/animation checks remain separate evidence, not a rerun of the latest full suite.

Read-only section audits still identify possible knee/calf gaps in five fallback bodies. Part extrema extend up to 0.415 units beyond authored bounds; knee/calf 2D section Hausdorff distance increases from about 0.45–0.58 to 1.17–1.83 units. Plain 384 simplification causes most of that increase; contour adjustment adds 0–0.13 units. These are geometry metrics, not proof of a visible hole or an accepted repair. Native silhouette/seam inspection, matched v0.0.38 gait and RC1 ready controls, original-game comparison, memory/performance, exact package and owner acceptance remain pending.

## Post-pin RC2 package observation, 14 October 2026

All 20 body and companion sets are present in the exact RC2 package. The scoped Nord package footage does not establish knee/calf continuity or fix the owner-reported thin legs. Prior section metrics and possible simplification gaps remain diagnostic; matched original/v0.0.38, all-appearance and owner acceptance remain pending.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Owner acceptance and final v0.0.39 clearance remain pending.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: First-person hands and torch (`torch-hands`). First-person hands, punches and the carried torch. See [families](README.md#families).

- AW-20260928-18 (no report page): Punch blocked after Census office exit
- [DEBUG-GALLERY-TIMING-29](DEBUG-GALLERY-TIMING-29.md): Hands unavailable in the combat and torch test rooms
- HAND-IDLE-BLINK-29 (no report page): Fists disappear once per idle breathing cycle
- HAND-PUNCH-COVERAGE-29 (no report page): Near-plane opening at maximum punch extension
- HAND-PUNCH-TRANSITION-29 (no report page): Hands briefly disappear when changing into the punch animation
- [PLAYER-MOVEMENT-FRAME-SKIP-39](PLAYER-MOVEMENT-FRAME-SKIP-39.md): Third-person Nord and Khajiit fast movement loses smooth foot animation
- [PLAYER-PUNCH-THIRDPERSON-39](PLAYER-PUNCH-THIRDPERSON-39.md): Third-person punches have no visible player-body attack animation
- [PLAYER-READY-THIRDPERSON-38](PLAYER-READY-THIRDPERSON-38.md): Third-person player lacks fists-up and weapon-draw animation
- [PLAYER-TORCH-THIRDPERSON-38](PLAYER-TORCH-THIRDPERSON-38.md): Player torch and holding pose disappear in third person while light remains
- TORCH-FLAME-VISIBILITY-29 (no report page): Torch flame not visible after changing styles
- TORCH-FUEL-29 (no report page): Torch never burns out; no unlit or fuel state
- TORCH-HAND-NORD-29 (no report page): Detached-looking left grip fragment in dev4
- TORCH-HAND-SEPARATION-29 (no report page): Torch grip and hand appear to break during idle and running
- TORCH-INPUT-29 (no report page): F cannot raise hands; V only prints torch state

<!-- END GENERATED CATEGORY -->
