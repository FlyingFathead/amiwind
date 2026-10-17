# Bug journal

[CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md) — 15 October 2026, v0.0.41-dev1: full-build preparation rejected five explicitly selected ocean routing cells absent from the original CELL/LAND inventory, before legacy compilation. The source checklist now records additional ocean routing cells separately and allows their absence only before routing rows are appended. Final classification/stage verification still requires every row and CHIM routing flags; undeclared or unselected missing cells are rejected. All 98 targeted checks across five modules pass, including three new ocean checklist regressions. Exact production conversion, native ocean behavior, image/package and delivery checks remain pending; coverage states are unchanged.

<!-- contents start -->
## Contents

- [BUILD-TORCH-CREATURE-RESIDENT-42, 17 October 2026](#build-torch-creature-resident-42-17-october-2026)
- [VIVEC-ROOM-PRECACHE-LIMIT-42, 17 October 2026](#vivec-room-precache-limit-42-17-october-2026)
- [BUILD-CHIM-VIS-VARIANT-SORT-42, 17 October 2026](#build-chim-vis-variant-sort-42-17-october-2026)
- [NIGHT-WINDOWS-LOST-CHIM-36, 17 October 2026](#night-windows-lost-chim-36-17-october-2026)
- [UI-INVENTORY-PREVIEW-STILL-42, 17 October 2026](#ui-inventory-preview-still-42-17-october-2026)
- [UI-INVENTORY-PREVIEW-GAP-41, 17 October 2026](#ui-inventory-preview-gap-41-17-october-2026)
- [UI-WINDOW-TITLE-BAR-42 and UI-INVENTORY-HEADING-CENTRE-42, 17 October 2026](#ui-window-title-bar-42-and-ui-inventory-heading-centre-42-17-october-2026)
- [HUD-STATS-29: original weapon and magic boxes, 17 October 2026](#hud-stats-29-original-weapon-and-magic-boxes-17-october-2026)
- [UI-ICONS-INVENTORY-42, 17 October 2026](#ui-icons-inventory-42-17-october-2026)
- [CHIMport by weight: tracker headroom and seabed cells, 17 October 2026](#chimport-by-weight-tracker-headroom-and-seabed-cells-17-october-2026)
- [ENGINE-060-MUL64-41, 17 October 2026](#engine-060-mul64-41-17-october-2026)
- [FPU-SUPPORT-MMULIB-SETPATCH-41, 17 October 2026](#fpu-support-mmulib-setpatch-41-17-october-2026)
- [BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42, 17 October 2026](#build-profile-reaped-child-double-count-42-17-october-2026)
- [SKY-FLAT-PALETTE-DRIFT-41: palette-matched cloud sky, 17 October 2026](#sky-flat-palette-drift-41-palette-matched-cloud-sky-17-october-2026)
- [SKY-FLAT-PALETTE-DRIFT-41, 17 October 2026](#sky-flat-palette-drift-41-17-october-2026)
- [Register audit: open means open, 16 October 2026](#register-audit-open-means-open-16-october-2026)
- [BUILD-STAIR-GATE-OOM-42, 17 October 2026](#build-stair-gate-oom-42-17-october-2026)
- [INTERIOR-SPAWN-UNDERWATER-41, 17 October 2026](#interior-spawn-underwater-41-17-october-2026)
- [INTERIOR-EXCLUDE-STALE-41, 16 October 2026](#interior-exclude-stale-41-16-october-2026)
- [BUILD-STAIR-WALK-BORDER-COPIES-41: repair on the v0.0.42 line, 16 October 2026](#build-stair-walk-border-copies-41-repair-on-the-v0042-line-16-october-2026)
- [STAIR-FLIGHT-CORE-SPLIT-41, 16 October 2026](#stair-flight-core-split-41-16-october-2026)
- [STAIR-DETECT-POSITION-41, 16 October 2026](#stair-detect-position-41-16-october-2026)
- [BUILD-RELEASE-READINESS-HIDDEN-41, 16 October 2026](#build-release-readiness-hidden-41-16-october-2026)
- [BUILD-PROGRESS-ETA-BASIS-36: PERSISTING in v0.0.41-dev5, 16 October 2026](#build-progress-eta-basis-36-persisting-in-v0041-dev5-16-october-2026)
- [BUILD-CHIM-STAGE-SERIAL-TAIL-36: one pool for the CHIM step, 16 October 2026](#build-chim-stage-serial-tail-36-one-pool-for-the-chim-step-16-october-2026)
- [CHIM-VIVEC-FRAME-WIDE-41: wide support ring, 16 October 2026](#chim-vivec-frame-wide-41-wide-support-ring-16-october-2026)
- [CHIM-VIVEC-FRAME-WIDE-41: residents, 16 October 2026](#chim-vivec-frame-wide-41-residents-16-october-2026)
- [HARVEST-CHIM-REGION-LOSS-41, 16 October 2026](#harvest-chim-region-loss-41-16-october-2026)
- [BUILD-STAIR-PASS-NOT-KEPT-41: repair on the v0.0.42 line, 16 October 2026](#build-stair-pass-not-kept-41-repair-on-the-v0042-line-16-october-2026)
- [BUILD-CACHE-PROVENANCE-41, 16 October 2026](#build-cache-provenance-41-16-october-2026)
- [ENGINE-060-FSCC-41, 16 October 2026](#engine-060-fscc-41-16-october-2026)
- [CHIM-OCEAN-ROUTING-UNNAMED-41, 16 October 2026](#chim-ocean-routing-unnamed-41-16-october-2026)
- [CHIMPORT-OCEAN-LAND-41, 16 October 2026](#chimport-ocean-land-41-16-october-2026)
- [INTERIOR-CREATURES-MISSING-41, 16 October 2026](#interior-creatures-missing-41-16-october-2026)
- [CHIMPORT-STATUS-STALE-41, 16 October 2026](#chimport-status-stale-41-16-october-2026)
- [CHIM-COLLISION-UNION-FALLBACK-41, 16 October 2026](#chim-collision-union-fallback-41-16-october-2026)
- [CHIM-VOS-TEMPLE-WALKWAY-41, 16 October 2026](#chim-vos-temple-walkway-41-16-october-2026)
- [BUILD-STAIR-WALK-BORDER-COPIES-41, 16 October 2026](#build-stair-walk-border-copies-41-16-october-2026)
- [BUILD-STAIR-PASS-NOT-KEPT-41, 16 October 2026](#build-stair-pass-not-kept-41-16-october-2026)
- [CHIM-STATICS-FALLBACK-41, 16 October 2026](#chim-statics-fallback-41-16-october-2026)
- [CHIM-VIVEC-FRAME-WIDE-41, 16 October 2026](#chim-vivec-frame-wide-41-16-october-2026)
- [BUILD-LAVA-TERRAIN-BUDGET-38, 16 October 2026](#build-lava-terrain-budget-38-16-october-2026)
- [BUILD-SEYDA-HULL2-32, 16 October 2026](#build-seyda-hull2-32-16-october-2026)
- [BUILD-SEYDA-HULL2-32, 15 October 2026](#build-seyda-hull2-32-15-october-2026)
- [BUILD-IDLE-STAGES-33, 15 October 2026](#build-idle-stages-33-15-october-2026)
- [v0.0.41 candidate - visibility aprons, 15 October 2026](#v0041-candidate---visibility-aprons-15-october-2026)
- [v0.0.41 candidate - window support, 15 October 2026](#v0041-candidate---window-support-15-october-2026)
- [v0.0.41 candidate - lava coverage, 15 October 2026](#v0041-candidate---lava-coverage-15-october-2026)
- [Compiled apron selection, 15 October 2026](#compiled-apron-selection-15-october-2026)
- [Paired boundary validation, 15 October 2026](#paired-boundary-validation-15-october-2026)
- [CHIM-FRAME-STATIC-SEAM-40 - 15 October 2026](#chim-frame-static-seam-40---15-october-2026)
- [v0.0.40 - original kelp ownership, 15 October 2026](#v0040---original-kelp-ownership-15-october-2026)
- [v0.0.40 - retain authored boundary collision, 15 October 2026](#v0040---retain-authored-boundary-collision-15-october-2026)
- [v0.0.40 - sub-cell scenery apron parity, 15 October 2026](#v0040---sub-cell-scenery-apron-parity-15-october-2026)
- [v0.0.40 - coastal scenery apron guard, 15 October 2026](#v0040---coastal-scenery-apron-guard-15-october-2026)
- [v0.0.40 - regional scenery apron repair, 15 October 2026](#v0040---regional-scenery-apron-repair-15-october-2026)
- [15 October 2026 - combined-world collision crossing](#15-october-2026---combined-world-collision-crossing)
- [15 October 2026 - final source update baseline](#15-october-2026---final-source-update-baseline)
- [15 October 2026 - ring plan and public image selection](#15-october-2026---ring-plan-and-public-image-selection)
- [15 October 2026 - boundary ownership repair](#15-october-2026---boundary-ownership-repair)
- [15 October 2026 - combined-world boundary ownership](#15-october-2026---combined-world-boundary-ownership)
- [15 October 2026 - combined-world preparation incomplete](#15-october-2026---combined-world-preparation-incomplete)
- [15 October 2026 - original ground reference distinction](#15-october-2026---original-ground-reference-distinction)
- [15 October 2026 - terrain detail and original diagonals](#15-october-2026---terrain-detail-and-original-diagonals)
- [15 October 2026 - complete carrier and expanded contact findings](#15-october-2026---complete-carrier-and-expanded-contact-findings)
- [15 October 2026 - NPC model cache dependencies](#15-october-2026---npc-model-cache-dependencies)
- [15 October 2026 - source carrier voice prerequisite](#15-october-2026---source-carrier-voice-prerequisite)
- [15 October 2026 - expanded Seyda offline conversion](#15-october-2026---expanded-seyda-offline-conversion)
- [15 October 2026 - carrier original-data failure and text output](#15-october-2026---carrier-original-data-failure-and-text-output)
- [15 October 2026 - source-only carrier and expanded stairs](#15-october-2026---source-only-carrier-and-expanded-stairs)
- [15 October 2026 - CHIM ownership reporting](#15-october-2026---chim-ownership-reporting)
- [15 October 2026 - option and tracker record validation](#15-october-2026---option-and-tracker-record-validation)
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: shared exterior carrier, 15 October 2026](#chim-cell-feature-list-incomplete-38-shared-exterior-carrier-15-october-2026)
- [BUILD-SEYDA-OCEAN-FLOOR-40: expanded ocean floor, 15 October 2026](#build-seyda-ocean-floor-40-expanded-ocean-floor-15-october-2026)
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 and CHIM-EMPTY-MODEL-REPORT-40: offline ocean results, 15 October 2026](#chim-cell-feature-list-incomplete-38-and-chim-empty-model-report-40-offline-ocean-results-15-october-2026)
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: town source, 15 October 2026](#chim-cell-feature-list-incomplete-38-town-source-15-october-2026)
- [CHIM-EMPTY-MODEL-REPORT-40: empty model reporting, 15 October 2026](#chim-empty-model-report-40-empty-model-reporting-15-october-2026)
- [BUILD-TOOLKIT-VERSION-40: source label, 15 October 2026](#build-toolkit-version-40-source-label-15-october-2026)
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: ocean source and town scope, 15 October 2026](#chim-cell-feature-list-incomplete-38-ocean-source-and-town-scope-15-october-2026)
- [NPC-ANIMATION-OFFSET-40: rotating simplification offsets, 15 October 2026](#npc-animation-offset-40-rotating-simplification-offsets-15-october-2026)
- [PLAYER-MOVEMENT-FRAME-SKIP-39: original reference and measurement labels, 14 October 2026](#player-movement-frame-skip-39-original-reference-and-measurement-labels-14-october-2026)
- [PLAYER-MOVEMENT-FRAME-SKIP-39: Nord gait control, 14 October 2026](#player-movement-frame-skip-39-nord-gait-control-14-october-2026)
- [CHIM-CHUNK-LOAD-FAIL-33: Seyda terrain allocation retries, 14 October 2026](#chim-chunk-load-fail-33-seyda-terrain-allocation-retries-14-october-2026)
- [PLAYER-PUNCH-THIRDPERSON-39: Khajiit movement and punch control, 14 October 2026](#player-punch-thirdperson-39-khajiit-movement-and-punch-control-14-october-2026)
- [CHIM-CHUNK-LOAD-FAIL-33: Seyda model allocation retry, 14 October 2026](#chim-chunk-load-fail-33-seyda-model-allocation-retry-14-october-2026)
- [HUD-STATS-29: original paper pickup and scoped HUD comparison, 14 October 2026](#hud-stats-29-original-paper-pickup-and-scoped-hud-comparison-14-october-2026)
- [UI-INVENTORY-LAYOUT-40: native preview and allowance correction, 14 October 2026](#ui-inventory-layout-40-native-preview-and-allowance-correction-14-october-2026)
- [UI-INVENTORY-LAYOUT-40 and HUD-STATS-29: build and conversion evidence, 14 October 2026](#ui-inventory-layout-40-and-hud-stats-29-build-and-conversion-evidence-14-october-2026)
- [PLAYER-PUNCH-THIRDPERSON-39: selected ordinary-view observation, 14 October 2026](#player-punch-thirdperson-39-selected-ordinary-view-observation-14-october-2026)
- [UI-INVENTORY-LAYOUT-40: dedicated pose source, 14 October 2026](#ui-inventory-layout-40-dedicated-pose-source-14-october-2026)
- [HUD-STATS-29: opening permission source repair, 14 October 2026](#hud-stats-29-opening-permission-source-repair-14-october-2026)
- [HUD-STATS-29: opening channel gates source audit, 14 October 2026](#hud-stats-29-opening-channel-gates-source-audit-14-october-2026)
- [UI-INVENTORY-LAYOUT-40: scrollbar source and repeated posture report, 14 October 2026](#ui-inventory-layout-40-scrollbar-source-and-repeated-posture-report-14-october-2026)
- [TRACKER-REGISTER-SIZE-33: journal rotation, 14 October 2026](#tracker-register-size-33-journal-rotation-14-october-2026)
- [UI-INVENTORY-INTEGRATION-40: scoped native equipment, 14 October 2026](#ui-inventory-integration-40-scoped-native-equipment-14-october-2026)
- [UI-INVENTORY-INTEGRATION-40: fixture links and journal guard, 14 October 2026](#ui-inventory-integration-40-fixture-links-and-journal-guard-14-october-2026)
- [UI-INVENTORY-INTEGRATION-40: harvest award reaches inventory modal, 14 October 2026](#ui-inventory-integration-40-harvest-award-reaches-inventory-modal-14-october-2026)
- [CHIM-VIEW-FACES-33: exterior Dwemer slowdown report, 14 October 2026](#chim-view-faces-33-exterior-dwemer-slowdown-report-14-october-2026)
- [ENGINE-FPU-UNIMPL-31: target pass and native inventory limits, 14 October 2026](#engine-fpu-unimpl-31-target-pass-and-native-inventory-limits-14-october-2026)
- [UI-INVENTORY-LAYOUT-40: native field overlap and preview orientation, 14 October 2026](#ui-inventory-layout-40-native-field-overlap-and-preview-orientation-14-october-2026)
- [ENGINE-FPU-UNIMPL-31: blocking recurrence, 14 October 2026](#engine-fpu-unimpl-31-blocking-recurrence-14-october-2026)
- [UI-INVENTORY-INTEGRATION-40: dev2 interaction scope, 14 October 2026](#ui-inventory-integration-40-dev2-interaction-scope-14-october-2026)
- [TEST-CENSUS-CONTRACTS-40: three expected failures, 14 October 2026](#test-census-contracts-40-three-expected-failures-14-october-2026)
- [UI-INVENTORY-INTEGRATION-40: command catalogue ordering, 14 October 2026](#ui-inventory-integration-40-command-catalogue-ordering-14-october-2026)
- [DOCS-CHIM-PROGRESS-STALE-38: final shipment wording recurrence, 14 October 2026](#docs-chim-progress-stale-38-final-shipment-wording-recurrence-14-october-2026)
- [CHIM-WINDOW-MOUNT-CROSS-CELL-33: offline conversion, 14 October 2026](#chim-window-mount-cross-cell-33-offline-conversion-14-october-2026)
- [PLAYER-MOVEMENT-STATS-PARITY-39: movement speed source study, 14 October 2026](#player-movement-stats-parity-39-movement-speed-source-study-14-october-2026)
- [UI-INVENTORY-INTEGRATION-40: integration and placement boundaries, 14 October 2026](#ui-inventory-integration-40-integration-and-placement-boundaries-14-october-2026)
- [COMBAT-BLOCKING-36: first-person source candidate, 14 October 2026](#combat-blocking-36-first-person-source-candidate-14-october-2026)
- [PLAYER-PUNCH-THIRDPERSON-39: held attack during raising, 14 October 2026](#player-punch-thirdperson-39-held-attack-during-raising-14-october-2026)
- [Renewed RC2 gameplay reports, 14 October 2026](#renewed-rc2-gameplay-reports-14-october-2026)
- [Stair fixes verified, AW-LEASE-NO-GROW-36, 11 October 2026](#stair-fixes-verified-aw-lease-no-grow-36-11-october-2026)
- [CHIM-FRAME-EDGE-EFRAG-CRASH-36 fixed, 11 October 2026](#chim-frame-edge-efrag-crash-36-fixed-11-october-2026)
- [SMOKE-PASSES-WITHOUT-MAP-36, 13 October 2026](#smoke-passes-without-map-36-13-october-2026)
- [CHIM-FRAME-EDGE-EFRAG-CRASH-36 (persisting) and ENGINE-CRASH-EXIT-KEYBOARD-36, 11 October 2026](#chim-frame-edge-efrag-crash-36-persisting-and-engine-crash-exit-keyboard-36-11-october-2026)
- [CHIM-FRAME-EDGE-EFRAG-CRASH-36 (persisting) and ENGINE-CRASH-EXIT-KEYBOARD-36, 11 October 2026](#chim-frame-edge-efrag-crash-36-persisting-and-engine-crash-exit-keyboard-36-11-october-2026-1)
- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36, COMBAT-BLOCKING-36 and the platform field, 11 October 2026](#camera-thirdperson-combat-npc-hidden-36-combat-blocking-36-and-the-platform-field-11-october-2026)
- [BUILD-IMAGE-HASH-UNDERUSED-36 and BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36 fixed, 11 October 2026](#build-image-hash-underused-36-and-build-image-heap-audit-underused-36-fixed-11-october-2026)
- [BUILD-IMAGE-STAIR-WALK-SERIAL-36, BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36, BUILD-IMAGE-HASH-UNDERUSED-36 and BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36: the perf guard, 11 October 2026](#build-image-stair-walk-serial-36-build-image-frame-map-heap-serial-36-build-image-hash-underused-36-and-build-image-heap-audit-underused-36-the-perf-guard-11-october-2026)
- [TRACKER-OCEAN-COUNTED-DONE-36, 11 October 2026](#tracker-ocean-counted-done-36-11-october-2026)
- [CHIM-LAVA-TERRAIN-AUDIT-37, 12 October 2026](#chim-lava-terrain-audit-37-12-october-2026)
- [BUILD-LAVA-PRESET-FIXTURE-38, 12 October 2026](#build-lava-preset-fixture-38-12-october-2026)
- [CHIM-COAST-OBJECTS-MISSING-36, 12 October 2026](#chim-coast-objects-missing-36-12-october-2026)
- [BUILD-VERSION-EMULATOR-PRESETS-38: 12 October 2026](#build-version-emulator-presets-38-12-october-2026)
- [BUILD-LAVA-CORE-BOUNDS-38: 12 October 2026](#build-lava-core-bounds-38-12-october-2026)
- [BUILD-LAVA-TERRAIN-BUDGET-38, 12 October 2026: complete scenery scan](#build-lava-terrain-budget-38-12-october-2026-complete-scenery-scan)
- [CHIM-MOLAG-MEMORY-38, 12 October 2026](#chim-molag-memory-38-12-october-2026)
- [2026-10-12 — TOOLKIT-CULL-DIAGNOSTICS-38](#2026-10-12--toolkit-cull-diagnostics-38)
- [2026-10-12 — CHIM-TERRAIN-ROCK-EXEMPT-38](#2026-10-12--chim-terrain-rock-exempt-38)
- [STAIRS-MOLAG-ACCESS-38, 13 October 2026](#stairs-molag-access-38-13-october-2026)
- [BUILD-SHADOWED-WORLD-MAPS-38, 13 October 2026](#build-shadowed-world-maps-38-13-october-2026)
- [SAVE-TELEPORT-CHECKPOINT-38, 13 October 2026](#save-teleport-checkpoint-38-13-october-2026)
- [SAVE-LAVA-DEATH-LOOP-38, 13 October 2026](#save-lava-death-loop-38-13-october-2026)
- [UI-DEATH-DAMAGE-TINT-38, 13 October 2026](#ui-death-damage-tint-38-13-october-2026)
- [DOCS-CHIM-PROGRESS-STALE-38, 13 October 2026](#docs-chim-progress-stale-38-13-october-2026)
- [SAVE-LAVA-DEATH-LOOP-38, candidate 13 October 2026](#save-lava-death-loop-38-candidate-13-october-2026)
- [SAVE-TELEPORT-CHECKPOINT-38, candidate 13 October 2026](#save-teleport-checkpoint-38-candidate-13-october-2026)
- [UI-DEATH-DAMAGE-TINT-38, candidate 13 October 2026](#ui-death-damage-tint-38-candidate-13-october-2026)
- [BUILD-CHECKLIST-JSON-CELLS-39 and RELEASE-PATCH-TARGET-VERSION-39, 13 October 2026](#build-checklist-json-cells-39-and-release-patch-target-version-39-13-october-2026)
- [DOCS-CHANGELOG-STALE-39 and DOCS-RC1-PREFLIGHT-39, 13 October 2026](#docs-changelog-stale-39-and-docs-rc1-preflight-39-13-october-2026)
- [DOCS-RELEASE-EVIDENCE-SCOPE-39 - final source reconciliation, 14 October 2026](#docs-release-evidence-scope-39---final-source-reconciliation-14-october-2026)
- [Development audit, 14 October 2026](#development-audit-14-october-2026)
- [PLAYER-READY-MOVEMENT-39: input diagnostic, 14 October 2026](#player-ready-movement-39-input-diagnostic-14-october-2026)
- [PLAYER-READY-MOVEMENT-39: disabled-combat lock, 14 October 2026](#player-ready-movement-39-disabled-combat-lock-14-october-2026)
- [CHIM-WINDOW-MOUNT-CROSS-CELL-33: neighbouring source wall candidate, 14 October 2026](#chim-window-mount-cross-cell-33-neighbouring-source-wall-candidate-14-october-2026)
- [BUILD-VERSION-EMULATOR-PRESETS-38: v0.0.40-dev1 recurrence, 14 October 2026](#build-version-emulator-presets-38-v0040-dev1-recurrence-14-october-2026)
- [TEST-NATIVE-TMPDIR-32: testbox relative drive, 14 October 2026](#test-native-tmpdir-32-testbox-relative-drive-14-october-2026)
- [INVENTORY-CATALOG-LOOKUP-40: native catalogue failure, 14 October 2026](#inventory-catalog-lookup-40-native-catalogue-failure-14-october-2026)

<!-- contents end -->

## BUILD-TORCH-CREATURE-RESIDENT-42, 17 October 2026

[BUILD-TORCH-CREATURE-RESIDENT-42](bugs/BUILD-TORCH-CREATURE-RESIDENT-42.md): the v0.0.42-dev1 full build stopped in
the image step's torch guard on Vivec, an interior creature resident placed as an NPC entity. Fixed in 5db820c:
creature residents are skipped; other unknown identities are still refused.

## VIVEC-ROOM-PRECACHE-LIMIT-42, 17 October 2026

[VIVEC-ROOM-PRECACHE-LIMIT-42](bugs/VIVEC-ROOM-PRECACHE-LIMIT-42.md): the v0.0.42-dev1 full build stopped in the
payload preflight: Vivec, Telvanni Tower (vti011) needs 257 model precaches, the engine holds 256. It was listed
again because its own model slots fit (210 of 220). Excluded again for v0.0.42-dev1. Open.

## BUILD-CHIM-VIS-VARIANT-SORT-42, 17 October 2026

[BUILD-CHIM-VIS-VARIANT-SORT-42](bugs/BUILD-CHIM-VIS-VARIANT-SORT-42.md): the v0.0.42-dev1 full build stopped after
about 44 minutes in the CHIM visibility rows: the variant keys of a frame mix model numbers and terrain tile
tuples, and the B5 change sorted them directly. Fixed in e5b0c0c (ordered by their text form) with a mixed-key test.

## NIGHT-WINDOWS-LOST-CHIM-36, 17 October 2026

[NIGHT-WINDOWS-LOST-CHIM-36](bugs/NIGHT-WINDOWS-LOST-CHIM-36.md): found while checking where the builder ships a
stand-in: the night-windows table (glowing window glass at night) has been empty in every image since v0.0.36
(v0.0.35: 86 maps). The towns moved to CHIM and their frame maps get no rows; the build printed one warning line.
Open.

## UI-INVENTORY-PREVIEW-STILL-42, 17 October 2026

[UI-INVENTORY-PREVIEW-STILL-42](bugs/UI-INVENTORY-PREVIEW-STILL-42.md): the maintainer: the inventory character
is a still picture in the original, never turning or moving. AmiWind drew it live every frame and turned it with
the arrow keys. Repair on v0.0.42-hud-icons: one render when the window opens and after each equipment action,
facing the viewer, kept as a 116 x 168 picture (19,488 bytes while the window is open); the pose model and
depth buffer are freed at once and later frames only copy the picture. `aw_inventory_preview_live 1` keeps the
old live preview.

## UI-INVENTORY-PREVIEW-GAP-41, 17 October 2026

[UI-INVENTORY-PREVIEW-GAP-41](bugs/UI-INVENTORY-PREVIEW-GAP-41.md): the maintainer found "Character preview
unavailable" in the inventory. Cause: since v0.0.40 the per-race inventory pose model (about 128 KB) was refused
whenever the free hunk gap was under a fixed 2 MiB; Seyda Neen on CHIM leaves 1.96 MiB in the v0.0.41 world, so
the preview never loaded there, in v0.0.41 as shipped too, behind a console line that named missing assets.
Repair on v0.0.42-hud-icons: the load is admitted by its real need (three times the file plus 256 KiB) and the
console names the refusing rule; `aw_inventory_preview_reserve 2` keeps the old rule.

## UI-WINDOW-TITLE-BAR-42 and UI-INVENTORY-HEADING-CENTRE-42, 17 October 2026

[UI-WINDOW-TITLE-BAR-42](bugs/UI-WINDOW-TITLE-BAR-42.md): menu windows lack the original title bar (the tiled
frame with the name on a dark plaque). [UI-INVENTORY-HEADING-CENTRE-42](bugs/UI-INVENTORY-HEADING-CENTRE-42.md):
the "Inventory" heading is not vertically centred. Both reported by the maintainer; to be repaired together by
importing the original title-bar art with the HUD art.

## HUD-STATS-29: original weapon and magic boxes, 17 October 2026

[HUD-STATS-29](bugs/HUD-STATS-29.md), persisting (reported a fifth time by the maintainer: the boxes were
placeholders). The HUD weapon and magic boxes are now composed from the original art, imported at build time
from the user's own game data into one lookup table (tools/prepare_icons.py): the item and hand-to-hand icons, the
thin box and bar frames, the bar tracks tinted by Morrowind.ini's fill colours and the magic backdrop behind
enchanted items. New engine state: the selected magic item and per-item enchantment charge (saved), the maximum
charge from the game records, recharge by fMagicItemRechargePerSecond; `aw_magic` selects until a magic menu
exists. Spells cannot be selected yet (no spell list). Evidence in FS-UAE on the v0.0.41 image with this engine
and data: unarmed, steel longsword, the ring selected at full and part charge. See [docs/HUD.md](HUD.md).

## UI-ICONS-INVENTORY-42, 17 October 2026

[UI-ICONS-INVENTORY-42](bugs/UI-ICONS-INVENTORY-42.md): new. The inventory shows icons only for the few staged
items, resampled from 32 to 14 pixels, without the original backdrops. Found in the audit of every UI screen for
missing icons (listed on the bug page); the repair uses the same icon table as the HUD.
## CHIMport by weight: tracker headroom and seabed cells, 17 October 2026

- [TRACKER-RELEASE-HEADROOM-MISSING-42](bugs/TRACKER-RELEASE-HEADROOM-MISSING-42.md): no cell of the v0.0.41 release
  run carried a headroom figure, and older CHIMport results replaced its audits; every figure in the tracker came
  from the v0.0.36-v0.0.40 builders. Fixed in source: each frame's figures go to its cells, and an older result no
  longer replaces a newer full build's audit.
- [TRACKER-AREA-CELLS-RUN-WIDE-42](bugs/TRACKER-AREA-CELLS-RUN-WIDE-42.md): every area of a multi-area build lists
  all of the build's cells (Balmora 811). Open.
- [CHIMPORT-OCEAN-LAND-41](bugs/CHIMPORT-OCEAN-LAND-41.md): the 98 cells are LAND records without height data; the
  tracker no longer takes an open-ocean result for them, and the CHIMport order plans them as seabed cells.
- New: `tools/chim_weight_table.py` and `config/chim-weight-classes.json` write the CHIMport order by weight
  ([CELL_WEIGHTS.md](chim/CELL_WEIGHTS.md)); 611 cells not on CHIM, 479 in the two easy classes on figures of older
  builders, measured again before the batch is built.
## ENGINE-060-MUL64-41, 17 October 2026

[ENGINE-060-MUL64-41](bugs/ENGINE-060-MUL64-41.md): the 68040 engine holds 151 64-bit `MULS.L`/`MULU.L` in 68 engine
functions (GCC's division by constants), which the 68060 traps; the first 68060 scan missed them. The new 68060
mode of the FPU check counts them; the `--engine-cpu 68060` build has none in engine code.

## FPU-SUPPORT-MMULIB-SETPATCH-41, 17 October 2026

[FPU-SUPPORT-MMULIB-SETPATCH-41](bugs/FPU-SUPPORT-MMULIB-SETPATCH-41.md): on an emulated 68060 the MMULib
`68060.library` stops the boot of a disk without `SetPatch` with an alert; with the system's `SetPatch` first the
game boots and runs.
## BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42, 17 October 2026

[BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42](bugs/BUILD-PROFILE-REAPED-CHILD-DOUBLE-COUNT-42.md): the build
profiler's sampled timeline counted a child process twice when the child ended between two readings of the
stage's process tree (gates 2519, 2610, 2651 and 2556 failed the timeline bound on loaded hosts). The sampler's
baseline no longer goes down, so the CPU is counted once. Stage CPU, average build-machine threads used and the
perf guard baselines were never affected; sampled per-stage peaks in earlier build profiles may read high.
PERSISTING since TEST-PROFILE-TIMELINE-BOUND-33 (v0.0.33-dev), which widened the bound instead.
## SKY-FLAT-PALETTE-DRIFT-41: palette-matched cloud sky, 17 October 2026

The first repair (sampling the palette from the old Seyda Neen textures) gave a third palette in a real build,
because the Seyda Neen ground textures in the sample changed too; the MiniWind stopped on the new image-step
refusal instead of shipping a flat sky. Replaced: the cloud sky is now converted for whatever palette the build
has, by nearest colour; nothing else is converted again and the palette stays the v0.0.41 one. Checked on the
real v0.0.41 palette in FS-UAE (clouds at noon and at dusk).

## SKY-FLAT-PALETTE-DRIFT-41, 17 October 2026

[SKY-FLAT-PALETTE-DRIFT-41](bugs/SKY-FLAT-PALETTE-DRIFT-41.md): the maintainer asked where the clouds and the sun had gone.
Every exterior of v0.0.40 and v0.0.41 has a flat sky without clouds (the sun disc, moons and day/night colours still
work). Cause: 01bdf9f widened the Seyda Neen scenery scope (107 to 183 textures), the sampled scene palette changed,
the shared cloud sky refused the unknown palette and the image fell back, with one warning line, to the converted
maps' one-colour placeholder. Fix on branch v0.0.42-sky: the palette is sampled from the historic scope only
(checked on the real v0.0.41 scenery stage: the v0.0.38 palette exactly), and the image step refuses the fallback.
Build and in-game check pending.

## Register audit: open means open, 16 October 2026

A read-only audit of every open entry against the git history (fix commit in a release line, its test at the current
head, release notes, later reports) was applied, each edit checked again against the current tree first. Before: 738
open, 95 fixed, 9 closed of 842 entries. After: 416 open, 380 fixed, 46 closed.

- 285 entries closed as fixed with the first release or numbered build whose source contains the fix (most in
  v0.0.32 to v0.0.36; their statuses still said "fixed in source, not shipped"). Fixed entries first found in v0.0.33
  or earlier and not persisting moved to the archive, as the rotation rule says.
- 37 closed: 26 superseded by CHIM (legacy Seyda, Balmora, Arena frame and region-map paths), 7 repaired outside the
  source tree or not AmiWind bugs, 4 duplicates. The two gate failures of the duplicate TEST-PARALLEL-ORDER-FLAKY-36
  and gate 1051 are now reports on [TEST-PARALLEL-ORDER-LOAD-33](bugs/TEST-PARALLEL-ORDER-LOAD-33.md).
- 204 open entries got a dated status line: what shipped, what is still missing, or what the maintainer has to decide.
  Nine entries whose fix shipped but which came back after an earlier fix stay open under the persisting rule.
- Two proposed closures were not applied because the bug was reported again after the audit:
  [BUILD-CHIM-STAGE-SERIAL-TAIL-36](bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md) and
  [BUILD-PROGRESS-ETA-BASIS-36](bugs/BUILD-PROGRESS-ETA-BASIS-36.md) (both again in v0.0.41-dev5).

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: whole-world metadata binding failed because tutorial barrel reference 172851 lacked its original CELL, while the original audit records [-2,-9]. A narrow source correction restores only that missing field before capture, rejecting nonempty wrong cells and every other identity/transform mismatch. Fifty focused Seyda/ownership checks pass, including three new semantic regressions. The preceding 4,247-test full-suite pass remains historical; the repaired world is pending. The prepared Linux source kit is held and undelivered. Native, image/package and playtest acceptance remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1 image integration follow-up: added Seyda dependency numbers and model digests are checked against the world-index-bound source manifest before source-carrier static parity includes them. Frames without supplements retain prior behavior. The focused ownership/apron module now passes 33 checks, including five new semantic regressions and missing/rebound-model rejection. The issue remains OPEN; exact world rebuild, held-boundary/native and image/package checks remain pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: a source repair supplements only missing Seyda apron dependencies using the included original-cell owner's exact compiled mesh and textures, preserving original identity and unique ownership while translating frame-local origins. It targets rock reference 251397 and shell reference 461804; 32 focused ownership/apron checks pass. The rebuilt world and held boundary/native checks remain pending. Separately, independent normal interior/actor/UI conversion completed 2,451 files with unchanged source and inputs; it is not image, native or package acceptance. CHIM coverage states are unchanged. Earlier full-suite and world results remain bound to their preceding source; changed apron acceptance is pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: exact source validation completed 4,242 tests (4,236 passed, three Windows-only skips and three Census expected failures), with zero failures/errors; the matching engine compiled. The completed 369-frame world passed structural/source, modeled heap, host zone-walk and scoped stair gates. Of 547 boundary comparisons, 544 measured agreement and three remain held (237, 241, 242). Of 36 sampled models, 22 have matching face counts and unique face correspondence; 14 differ in collision-only versus visual representation and require payload/sprite/native review. These measurements do not establish visual severity or universal equivalence. Native captures, independent interior conversion, image assembly/readback and package acceptance remain pending; coverage states are unchanged. Stair evidence retains 15,348 advisory findings despite zero blocking failures.

15 October 2026 — The preceding v0.0.41 source snapshot completed 4,242 tests: 4,236 passed, zero failures/errors, three Windows-only skips and three exact Census expected failures; source was unchanged. This does not validate the subsequent v0.0.41-dev1 version alignment or establish image/native/package acceptance.

15 October 2026: active preparation now targets v0.0.41-dev1. The planned final release title is **v0.0.41: Collisions And Boundaries**. Earlier source snapshots, checks and findings retain their recorded version identities; they do not establish acceptance of this development candidate. Matching source validation, completed image assembly/readback, native checks, packaging and delivery remain separate gates. See the [current development candidate](RELEASE-v0.0.41-dev1.md).

[BUILD-INVENTORY-PALETTE-41](bugs/BUILD-INVENTORY-PALETTE-41.md) — 15 October 2026, v0.0.41 source candidate: image assembly prepares inventory before the sky palette pass, which rejected current AWIC icons and AWI2/AWST metadata as unknown images. The source repair validates each inventory format at its exact path, remaps only icon pixels and preserves metadata bytes. Scoped evidence contains 15 passing palette checks and 2 passing inventory-asset checks on matching unchanged source. Actual image assembly, native verification, packaging and shipment remain pending.

[CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41 source candidate: the 941 world stopped at the unchanged ownership guard because ten explicitly deferred Seyda references reappeared through a named-town apron. The candidate applies the existing exact owner dispositions to named and regional neighbours alike. All ten original deferred IDs are verified and 38 focused checks pass. Fresh affected-world conversion and renewed boundary/memory checks remain pending; no coverage, native, package or maintainer acceptance is promoted.

[CHIM-MODEL-ARENA-RESERVE-41](bugs/CHIM-MODEL-ARENA-RESERVE-41.md) — 15 October 2026: exact allocation and predecessor-world checks remain separately recorded. The later 941 world stopped at its ownership guard because named aprons bypassed ten existing deferred-owner dispositions. The source-only disposition repair passes 38 focused checks; fresh world, boundary/model review and native/package acceptance remain pending.

[CHIM-RECIPE-APRON-SCOPE-41](bugs/CHIM-RECIPE-APRON-SCOPE-41.md) — 15 October 2026, v0.0.41 candidate: recipe repair converted all four affected frames with structural PASS. Three still failed the unchanged memory gate (peaks 6,957,632; 6,939,952; 6,644,768 bytes for (10,0), (10,1), (9,2)); (11,0) passed at 5,875,568 bytes. The separate placed-model reserve repair passes all four on identical world bytes. A complete successor world and recipe/model/sprite equivalence and native checks remain pending.

15 October 2026: exact-source validation completed 4,231 tests: 4,225 passed, three Windows-only skips and three tracked Census expected failures. The 71 focused tests and original-data readback across nine frame positions passed, consistently hiding 33 of 158 original references at stronghold state 6 while preserving unknown scripts. All 243 player resources are reusable after exact producer, input and file verification. Complete combined-world conversion, native comparison, packaging and shipment remain pending; coverage counts are unchanged.

## BUILD-STAIR-GATE-OOM-42, 17 October 2026

[BUILD-STAIR-GATE-OOM-42](bugs/BUILD-STAIR-GATE-OOM-42.md): the Vivec city MiniWind stopped in the CHIM stair
gate after about 20 minutes: a walk worker was killed (out of memory at 30 GiB) and the pool broke. The gate
walked the whole Vivec frame (83,236 steps and ramps) on 8 workers.

## INTERIOR-SPAWN-UNDERWATER-41, 17 October 2026

[INTERIOR-SPAWN-UNDERWATER-41](bugs/INTERIOR-SPAWN-UNDERWATER-41.md): seven Vivec underworks rooms used the
canal grate (under the water) as their own spawn, so loading the room by name put the player in the water.
The spawn is now the first arrival above the water; doors were never affected.

## INTERIOR-EXCLUDE-STALE-41, 16 October 2026

[INTERIOR-EXCLUDE-STALE-41](bugs/INTERIOR-EXCLUDE-STALE-41.md): Telvanni Tower and St. Delyn Underworks were
left out of Vivec on heap numbers from an older build; measured again with the v0.0.41 converter they fit
(589,004 and 302,268 bytes to spare). Listed again on the v0.0.42 line.

## BUILD-STAIR-WALK-BORDER-COPIES-41: repair on the v0.0.42 line, 16 October 2026

[BUILD-STAIR-WALK-BORDER-COPIES-41](bugs/BUILD-STAIR-WALK-BORDER-COPIES-41.md): a CHIM region frame's stair walk
covers the cell it owns plus the map-switch margin; its border copies are walked where they are owned. On the
v0.0.41 world 2,672,454 steps and ramps (3.07 per place) become 853,398 (1.11 per place); the Vos-edge test world
no longer fails on the Vos copy, and with Vos on CHIM the failure is found once, in Vos's own frame. The stair gate
now runs first among the CHIM checks (`--gate-order`).

## STAIR-FLIGHT-CORE-SPLIT-41, 16 October 2026

[STAIR-FLIGHT-CORE-SPLIT-41](bugs/STAIR-FLIGHT-CORE-SPLIT-41.md): flights are marked per 1024-unit core; 39 of 5,646
flight steps of the v0.0.41 world lose their mark where a flight crosses a core line, so a failure there would be
advisory only.

## STAIR-DETECT-POSITION-41, 16 October 2026

[STAIR-DETECT-POSITION-41](bugs/STAIR-DETECT-POSITION-41.md): step detection depends on the placement's position in
the frame: 107 of 869,846 places of the v0.0.41 world are found only in a neighbour frame's copy (2 flight steps).

## BUILD-RELEASE-READINESS-HIDDEN-41, 16 October 2026

[BUILD-RELEASE-READINESS-HIDDEN-41](bugs/BUILD-RELEASE-READINESS-HIDDEN-41.md): v0.0.41-dev5 passed with a waiver
for three Vivec residents, an accepted plant loss and no NPC gallery; the final found all three on its first run.
Repaired in source on v0.0.42-eta-ready, not shipped: every build prints a release readiness block before its first
stage (the builder's own private-test refusals, accepted entity losses, overridden retired flags, debugging
opt-outs), each item with a registered tracker ID; a full build with an item without one stops.

## BUILD-PROGRESS-ETA-BASIS-36: PERSISTING in v0.0.41-dev5, 16 October 2026

[BUILD-PROGRESS-ETA-BASIS-36](bugs/BUILD-PROGRESS-ETA-BASIS-36.md): PERSISTING. dev5's chim stage was expected at
43 minutes (364-frame history scaled to 726 frames) and ran over 85; the ETA said 23 minutes left at 12:40 and 25
at 13:07. The frame scaling held, but the per-frame cost of the history (frames reused from the unit cache) did not.
Repaired in source on v0.0.42-eta-ready, not shipped: a running stage is corrected from its own counter (units done
of total at the rate measured here, plus the later phases from history), stages keep the units they counted for
the next build's per-unit history, and the builder prints an "[eta]" line every 5 minutes with the basis.

## BUILD-CHIM-STAGE-SERIAL-TAIL-36: one pool for the CHIM step, 16 October 2026

[BUILD-CHIM-STAGE-SERIAL-TAIL-36](bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md): PERSISTING in v0.0.41-dev5 (validation on
one core for over half of its 6 minutes, heap gate 2.9 cores, zone walk one core between frames). Repaired in source
on v0.0.42-chim-pool, not shipped: one worker pool for the whole CHIM step, the cross-checks, variant audit and
ownership checks as frame and mesh units on it, the quadratic walk-measure, stats and home-rule lookups removed, the
gates reuse the validated world, one progress line per frame. On the dev5 world: validation, heap gate and zone walk
445 s to 269 s, reports identical by SHA-256.

## CHIM-VIVEC-FRAME-WIDE-41: wide support ring, 16 October 2026

[CHIM-VIVEC-FRAME-WIDE-41](bugs/CHIM-VIVEC-FRAME-WIDE-41.md): project decision: the support search tries 32 to 48 units
only after every spot within 32 units failed (--actor-search near keeps the old search). The Dreamer (297836) is
placed 37.5 units from its authored spot; all 58 Vivec residents ground with no waiver, the other 57 and Balmora's
18 unchanged; heap and stair gates pass. The game's Startup script disables this Dreamer until the Sixth House
journal reaches 50.

## CHIM-VIVEC-FRAME-WIDE-41: residents, 16 October 2026

[CHIM-VIVEC-FRAME-WIDE-41](bugs/CHIM-VIVEC-FRAME-WIDE-41.md): measured per resident. Nels Llendo stands in Seyda Neen's
cell 0,-9 and was placed by both town frames; a town frame now leaves a resident in another town's owned cells to
that town. Pilus Amatius and the Dreamer stand on sloped terrain the 128-unit tiles misrepresent; town frames now keep
the original LAND samples under ground residents (switch: --chim-terrain-resident-detail off). Vivec frame alone: 57 of
58 residents grounded, heap and stair gates pass. The Dreamer (28-degree slope, nearest fitting spot 37.5 units away,
search radius 32) stays open and needs an actor-policy decision. The report's "7x7" was wrong: the block is 6 x 6.

## HARVEST-CHIM-REGION-LOSS-41, 16 October 2026

[HARVEST-CHIM-REGION-LOSS-41](bugs/HARVEST-CHIM-REGION-LOSS-41.md): CHIM region cells got no harvest catalogue
(the plan kept only maps with a legacy map file) while the CHIM world leaves the harvestable mushrooms out,
so the plants of six cells were missing in v0.0.41-dev4 (413 island-wide by the new check). Each region
frame map now gets its catalogue and keeps it; a coverage check of every plant the CHIM world leaves out
stops the build. Replayed on the dev4 inputs: all six cells place every original plant.

## BUILD-STAIR-PASS-NOT-KEPT-41: repair on the v0.0.42 line, 16 October 2026

[BUILD-STAIR-PASS-NOT-KEPT-41](bugs/BUILD-STAIR-PASS-NOT-KEPT-41.md): a CHIM frame's stair walk that passed is
kept with its key, outcome and provenance and reused in development builds whatever the rest of its build did;
release candidates and finals keep the check mark. The walker key counts only the walk's own code: the dev5
rekey came from the CHIM_VERSION label (0.2.0 -> 0.2.1), not from collision_bsp. Two-frame world: 2 frames
walked again (22.5 s) before, 2 reused (3.5 s) after.

## BUILD-CACHE-PROVENANCE-41, 16 October 2026

[BUILD-CACHE-PROVENANCE-41](bugs/BUILD-CACHE-PROVENANCE-41.md): CHIMport's pool keys, the world-terrain units and the stage
records do not record when or with which builder they were made; one shared provenance writer planned.

## ENGINE-060-FSCC-41, 16 October 2026

[ENGINE-060-FSCC-41](bugs/ENGINE-060-FSCC-41.md): the engine holds 263 `fscc` instructions, which the 68060 traps to its
support library; the build's FPU check covers the 68040 only. No 64-bit integer multiply or divide was found.

## CHIM-OCEAN-ROUTING-UNNAMED-41, 16 October 2026

[CHIM-OCEAN-ROUTING-UNNAMED-41](bugs/CHIM-OCEAN-ROUTING-UNNAMED-41.md): world terrain refused the ocean cells of a regional
build without naming one. The error now names every cell and the rule it broke.

## CHIMPORT-OCEAN-LAND-41, 16 October 2026

[CHIMPORT-OCEAN-LAND-41](bugs/CHIMPORT-OCEAN-LAND-41.md): 98 seabed cells were marked open ocean and stopped the first
regional build 6 minutes into its CHIM stage. The preflight now refuses such cells in seconds; v0.0.41 keeps them
classic; v0.0.42 converts them as seabed cells.

## INTERIOR-CREATURES-MISSING-41, 16 October 2026

[INTERIOR-CREATURES-MISSING-41](bugs/INTERIOR-CREATURES-MISSING-41.md): the demigod Vivec is not in his palace. He is a
creature record, and the interior resident stage places NPC records only, so every interior creature is left out
without a log line. Planned for v0.0.42 (Complete Vivec): a creature branch, Vivec first, floating in his lotus pose.

## CHIMPORT-STATUS-STALE-41, 16 October 2026

[CHIMPORT-STATUS-STALE-41](bugs/CHIMPORT-STATUS-STALE-41.md): the first regional build's preflight refused six cells
on CHIMport audits from the v0.0.36 line, without saying how old they were. Results now record their creation
timestamp, AmiWind and CHIM versions and converter hash; the refusal names them and prints the command that
measures the cells again.

## CHIM-COLLISION-UNION-FALLBACK-41, 16 October 2026

[CHIM-COLLISION-UNION-FALLBACK-41](bugs/CHIM-COLLISION-UNION-FALLBACK-41.md): five ring-3 cells near Hla Oad stay out of
CHIM because Ashurnibibi's ruin meshes are over the memory budget. Their bytes are collision: the compact compiled
hull failed for three of them and the raw chains of convex pieces were kept (about 31,000 planes for 1,750 faces).
The mesh optimizer does not help here. Guide for such cells: CHIMport "When a cell does not fit the memory budget".

## CHIM-VOS-TEMPLE-WALKWAY-41, 16 October 2026

[CHIM-VOS-TEMPLE-WALKWAY-41](bugs/CHIM-VOS-TEMPLE-WALKWAY-41.md): the v0.0.41-dev5 build stopped at its CHIM
stair gate after 1 h 35 min on one step in Vos: a walkway stair that runs under the Velothi temple's base slab starts
inside the temple's convex collision, which reaches up to 5 units below the slab's visible underside. Vos had failed
its own stair walk in the CHIMport run of 11 October. The temple now keeps its authored collision surfaces, as its
sibling mesh already did; a two-frame test world passes the stair gate.

## BUILD-STAIR-WALK-BORDER-COPIES-41, 16 October 2026

[BUILD-STAIR-WALK-BORDER-COPIES-41](bugs/BUILD-STAIR-WALK-BORDER-COPIES-41.md): the CHIM stair gate walks every
frame's whole border, so each cell's flights are walked several times (2.67 million steps and ramps in dev5), and
a border copy of a classic neighbour that no player can reach from that frame stopped the build.

## BUILD-STAIR-PASS-NOT-KEPT-41, 16 October 2026

[BUILD-STAIR-PASS-NOT-KEPT-41](bugs/BUILD-STAIR-PASS-NOT-KEPT-41.md): dev5 reused none of its 726 frame walks, and
its rerun will not reuse the 724 that passed: a stored walk only counts after a whole build passes, and the walker's
key changed with collision compiler code it does not run. Persisting with BUILD-CHIM-STAIR-WALK-UNCACHED-36.

## CHIM-STATICS-FALLBACK-41, 16 October 2026

[CHIM-STATICS-FALLBACK-41](bugs/CHIM-STATICS-FALLBACK-41.md): source review. Seyda Neen's cell-aligned frame map holds
1,012 streamed statics; if its CHIM world cannot load, the engine's fallback spawns them as Quake statics and stops at
512 instead of running the map without its chunks. The builder now counts streamed statics against CHIM_MAX_STATICS.

## CHIM-VIVEC-FRAME-WIDE-41, 16 October 2026

[CHIM-VIVEC-FRAME-WIDE-41](bugs/CHIM-VIVEC-FRAME-WIDE-41.md): the v0.0.41-dev2 image actor gate stops on three Vivec
frame residents. Cause: v0.0.40 (f73aaa6) gave the Vivec frame a 7x7 block of whole owned cells and a wider source
radius, which takes in Ebonheart and reaches a Seyda Neen cell. The private playtest ships them as maintainer-accepted known
findings; the frame is narrowed before the release candidate.

## BUILD-LAVA-TERRAIN-BUDGET-38, 16 October 2026

[BUILD-LAVA-TERRAIN-BUDGET-38](bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md): PERSISTING. The v0.0.41-dev2 rings 0-2 build stopped
in world terrain: two more lava regions of cell (9,0) are over the 4 MiB cap (vf1697 4,739,260 bytes, vf2544 4,352,800).
Both are split with the existing refinement rules. The error now names the cell, the split and every exceeded limit.

## BUILD-SEYDA-HULL2-32, 16 October 2026

[BUILD-SEYDA-HULL2-32](bugs/BUILD-SEYDA-HULL2-32.md): repair in the v0.0.41-dev2 source. A CHIM-native Seyda Neen's
scene is the source-only carrier (entities and exact model boxes, no BSP29 compile), so the cell-aligned frame
stays; the opening objects the engine activates are checked at the bsp stage and per frame map (town frame,
sncourt, intro_docks), naming reference and map. The compiled town stays selectable for A/B tests. Original-data
check of the carrier and opening stages passed (9.2 s, barrel 172851 in sncourt); the end-to-end build is pending.

## BUILD-SEYDA-HULL2-32, 15 October 2026

[BUILD-SEYDA-HULL2-32](bugs/BUILD-SEYDA-HULL2-32.md): PERSISTING. The v0.0.41-dev1 rings 0-2 build stopped at the bsp
stage: the Seyda Neen full-town source map is over the BSP29 node/leaf limit since the v0.0.40 frame widening.

## BUILD-IDLE-STAGES-33, 15 October 2026

[BUILD-IDLE-STAGES-33](bugs/BUILD-IDLE-STAGES-33.md): PERSISTING. The same build kept 9.6 of 24 cores busy on average;
the bsp stage held 8 workers and used 1.2.

## v0.0.41 candidate - visibility aprons, 15 October 2026

[CHIM-VISIBILITY-APRON-SCOPE-41](bugs/CHIM-VISIBILITY-APRON-SCOPE-41.md) - The combined world stopped at Tel Uvirith, original cell (10, 1), because
its approved fixed stronghold snapshot required a source radius of zero.
Regional frames now audit neighbouring cells for separate aprons. The repair
keeps visibility snapshots bound to each original cell across all frames that
audit it. Unknown scripts and unaudited references remain visible. Runtime
quest progression is still deferred; complete conversion and native/package
acceptance remain pending. Coverage counts are unchanged.

## v0.0.41 candidate - window support, 15 October 2026

[CHIM-WINDOW-TOWER-SUPPORT-41](bugs/CHIM-WINDOW-TOWER-SUPPORT-41.md) - The combined v0.0.41 world build stopped while mounting four Nordic windows
from original cell (7, 22) into the adjacent frame apron. Their supporting
thatched tower was present, but the facade search accepted only model names
containing "house". Exact source triangles support all four windows under the
existing distance and outward-normal checks.

The candidate recognizes the original thatched-tower model in both local and
neighbouring facade searches. It keeps original reference ownership, geometry,
collision, mounting range and clearance. Arbitrary props are still rejected.
The failing build is preserved; complete conversion, native comparison and
fresh package readback remain pending. Coverage counts are not promoted.


15 October 2026, v0.0.41 candidate: 50 focused lava/polygon/terrain checks
and 47 emulator preset/launcher checks pass. Both original failing chunks pass
coverage against the unchanged cached geometry. Full combined-world, exact
source suite, native, package and shipment checks remain pending.

## v0.0.41 candidate - lava coverage, 15 October 2026

[CHIM-LAVA-DUPLICATE-VERTEX-40](bugs/CHIM-LAVA-DUPLICATE-VERTEX-40.md) - The v0.0.40 combined-world build stopped on two chunks in cell (2, -2).
Readback of the exact cached units found five affected coverage samples:
each has one lava surface and lava contents (-5) at the required depth.
A tiny edge collapses to identical adjacent vertices when the chunk is
translated into float32 frame coordinates. The polygon test mistook this
zero-length edge for a boundary through every sample.

The v0.0.41 candidate skips only exactly identical adjacent XY vertices.
It preserves edge ambiguity, outside rejection and empty/degenerate rejection;
no geometry, collision, pool height, tolerance or engine format is changed.
Full-world validation, native checks, fresh package readback and delivery
remain separate and pending. No coverage count is promoted.

## Compiled apron selection, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The full combined conversion found a conservative
source box overlapping an apron although the compiled rock footprint ends
0.83 game units outside it. The selection now records and excludes only external
references whose compiled pieces all miss that apron. Owned originals, reaching
pieces and missing-piece failures remain protected. The original reference and
compiled boxes remain in the source receipt. All 68 focused checks pass.
The preceding source passed 4,218 tests: 4,212 passed, three Windows checks
skipped and three tracked Census cases were expected failures. The later source
requires its own full suite and combined validation. Native, package and shipment
acceptance remain pending; no converted or accepted coverage count is promoted.

[Canonical report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).

## Paired boundary validation, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40 — The latest v0.0.40 paired conversion passes structural, heap, zone-walk and
stair validation. The 3,836 tested steps and ramps pass; 610 advisory results
remain recorded. Across 2,816 paired positions, full-static support states agree
and the maximum supported-height difference is 0.000077 game units. Terrain,
water and common standing-hull controls agree. The complete 369-frame successor
is being built from the same converter source; its acceptance remains pending.
The exact source full suite is running. Native gameplay, other boundary segments,
fresh package readback and shipment remain separate unfinished gates.

[Canonical report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).

UI-INVENTORY-LAYOUT-40: 14 Oct source inset rows/title; host checks pass; native pending.

## CHIM-FRAME-STATIC-SEAM-40 - 15 October 2026

The source owner check found twelve additional references in the sampled
regional apron: four placements of the fourth kelp mesh, four objects already
deferred by Seyda, and four nonsolid grasses represented by existing sprites.
The successor retains all four original kelp models. Regional aprons now honor
the included town's exact declared deferrals; nonsolid grasses retain the same
hash-verified sprite bytes and original transforms instead of duplicate meshes.
Unrecorded missing owners, changed original identities and corrupt sprite assets
still fail. The existing ownership validator is unchanged. Forty-seven focused
checks pass, including serialized ownership and sprite corruption controls.

The earlier authored-collision source passed 4,213 tests: 4,207 passed, three
Windows-only checks skipped, and three tracked Census expected failures. This
does not certify the later source. Combined conversion, native seams, gameplay,
fresh packaging and delivery remain pending; no coverage acceptance is promoted.

[Canonical report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).


## v0.0.40 - original kelp ownership, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40: Authored collision removes support-state mismatches
at2,816compiled boundary samples. The combined gate finds omitted original
kelp; the successor retains three source meshes and verifies their parity
against the original scenery index.43focusedchecks pass. Stair-gate memory
failure is preserved; full combined/native/package acceptance remains pending.
[Report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).


## v0.0.40 - retain authored boundary collision, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40: Compiled apron repair reduces mismatches477to69;
remaining rock disagreement comes from an authored collision shape omitted
by the Seyda carrier. A CHIM-only supplement verifies original source and
visible geometry hashes, preserves the carrier and retains the original
collision. Nineteen focused checks pass; compiled/native/package acceptance
remains pending. [Report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).


## v0.0.40 - sub-cell scenery apron parity, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40: Sub-cell coverage now retains the explicit scenery
apron without enlarging logical cores. 75 focused checks pass, including the
exact coverage union. Compiled, native and package verification remain pending.
[Report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).


## v0.0.40 - coastal scenery apron guard, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40: The expanded scenery survey permits heightless
ocean neighbors while rejecting missing owned-cell terrain. 74 focused checks
pass; compiled successor, native and package acceptance remain pending.
[Report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).


## v0.0.40 - regional scenery apron repair, 15 October 2026

CHIM-FRAME-STATIC-SEAM-40: Proposed source repair retains adjacent scenery
dependencies without enlarging owned cells. 73 focused checks pass; compiled
paired readback, native and package acceptance remain pending.
[Report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).


## 15 October 2026 - combined-world collision crossing

CHIM-FRAME-STATIC-SEAM-40: 477 of 2,816 paired samples differ in full-static
support at the southern Seyda crossing; native capture and repair pending.
[Report](bugs/CHIM-FRAME-STATIC-SEAM-40.md).

CHIM-FRAME-DEPENDENCY-OWNERSHIP-40: Repaired combined structural validation,
heap, zone-walk and stairs pass; model/sprite equivalence remains pending.
[Report](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).

CHIM-TERRAIN-DIAGONAL-40: Terrain/water agree at all six measured boundaries;
whole-world and native seam acceptance remain open.
[Report](bugs/CHIM-TERRAIN-DIAGONAL-40.md).

CHIM-SEYDA-ACTOR-CONTACT-33: Final compiled actor contact and native acceptance
remain pending after successful structural conversion.
[Report](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).


## 15 October 2026 - final source update baseline

BUILD-TOOLKIT-VERSION-40: verified v0.0.39 main comparison corrects the stale
v0.0.38 baseline. Toolkit implementation is unchanged; restore its published
update labels and retain 0.1.3. Final preflight pending.

PUBLIC-REFERENCE-SCREENSHOT-40: v0.0.40 source preparation preserves the public
image exclusion and AmiWind-only README photos. The Linux update starts at
published v0.0.39 main and records the explicit deletion. Final validation and
publication remain pending; no bug closure or CHIM coverage promotion.


## 15 October 2026 - ring plan and public image selection

- PUBLIC-REFERENCE-SCREENSHOT-40: selected two original AmiWind dev1 ring-2
  ship exterior captures for the main README, with exact version, cell and
  photo-mode captions. Current native/package acceptance counts are unchanged.

DOCS-CHIM-PROGRESS-STALE-38: Refreshed the reference and progress map from the canonical 06:48 UTC snapshot. Added the full rings 0-2 release plan without promoting conversion, native or packaged evidence.

CHIM-FRAME-DEPENDENCY-OWNERSHIP-40: Source 1a551532 passed 4,207 tests with 4,201 passes, three Windows skips and three tracked expected failures. Combined-world retry running; split-model companions, seams, native and package gates remain open.

PUBLIC-REFERENCE-SCREENSHOT-40: Removed the historical original-game screenshot from the mutable public source selection and comparison page. The rejection regression and fresh 2,943-file export/readback pass; 163 relevant focused checks passed after four unchanged cases were rechecked in the matching environment. No published history or sealed archive changed.


## 15 October 2026 - boundary ownership repair

CHIM-FRAME-DEPENDENCY-OWNERSHIP-40: Source repair adds original ownership and
exact compiled-piece bindings without changing the runtime format. 37 focused
checks and all 369 source catalogues pass. New combined-world, representation,
seam, native and package checks remain pending. No coverage promotion.
[Report](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).


## 15 October 2026 - combined-world boundary ownership

CHIM-FRAME-DEPENDENCY-OWNERSHIP-40: The 369-frame world fails six ownership
checks. Catalogue audit proves one logical owner for each of 36 repeated
references. Binary equivalence and repair remain pending.
[Report](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).

CHIM-TERRAIN-DIAGONAL-40: Generation completes; ownership validation holds
compiled seam acceptance. [Report](bugs/CHIM-TERRAIN-DIAGONAL-40.md).

CHIM-SEYDA-ACTOR-CONTACT-33: Final contact and native acceptance remain held
behind combined validation. No actor or tolerance changes.
[Report](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).


## 15 October 2026 - combined-world preparation incomplete

CHIM-TERRAIN-DIAGONAL-40: Combined-world preparation stopped before validation.
Source checks do not establish compiled or native seam acceptance.
[Report](bugs/CHIM-TERRAIN-DIAGONAL-40.md).

CHIM-SEYDA-ACTOR-CONTACT-33: The incomplete combined output establishes no
new actor-contact result; the existing failures remain open.
[Report](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).

## 15 October 2026 - original ground reference distinction

CHIM-TERRAIN-DIAGONAL-40: Complete source suite passes with explicit skips and
expected failures. Twelve original LAND rays explain the ray/contact diagonal
difference; compiled and native seam gates remain open.
[Report](bugs/CHIM-TERRAIN-DIAGONAL-40.md).

CHIM-SEYDA-ACTOR-CONTACT-33: Both original actors are observed on ground, with
position drift. This does not establish rendered sole contact or resolve the
converted dreamer constraint. Preserve all failed contact results.
[Report](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).

## 15 October 2026 - terrain detail and original diagonals

CHIM-TERRAIN-DIAGONAL-40: Integrated reference diamond splits for full-detail
terrain and checked original coordinates and shared edges. Coarse/adaptive
terrain unchanged; compiled/native verification pending.
[Report](bugs/CHIM-TERRAIN-DIAGONAL-40.md).

CHIM-SEYDA-ACTOR-CONTACT-33: Two local terrain-detail tiles preserve original
samples and neighbouring subdivisions. Nels' source contact is feasible;
the dreamer remains infeasible across all 12,853 existing offsets. Investigate
original grounding and foot pose; no tolerance or actor changes.
[Report](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).

## 15 October 2026 - complete carrier and expanded contact findings

CHIM-TERRAIN-DIAGONAL-40: Exact OpenMW 0.48 source uses alternating diamond
terrain triangles while the converter uses fixed AC splits. Coordinate and
shared-edge parity remain under review; no integrated or native fix.
[Report](bugs/CHIM-TERRAIN-DIAGONAL-40.md).

CHIM-SEYDA-ACTOR-CONTACT-33: Original LAND heights match the input audit, while
coarse converted triangles raise both sampled actor sites. Local detail,
original triangle topology and shared cell/chunk boundaries are under review;
the dreamer's fine-grid slope still exceeds the unchanged sole-contact band.
[Report](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).

PLAYER-MOVEMENT-FRAME-SKIP-39: All 243 current-source player resources pass
independent serialized readback. All 100 model headers and animation/attachment
metadata agree; Argonian male retains 122 frames. Native quality remains open.
[Report](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md).


BUILD-SEYDA-CARRIER-VOICE-DIR-40: Corrected original-data carrier and independent
resident/voice/reference readback pass with unchanged source and inputs.
[Report](bugs/BUILD-SEYDA-CARRIER-VOICE-DIR-40.md).

NPC-BAKE-VERTEX-32: Complete carrier preserves Tarhiel's 64-sample mover and
all 13 resident model sets. Native and package acceptance remain open.
[Report](bugs/NPC-BAKE-VERTEX-32.md).

CHIM-SEYDA-ACTOR-CONTACT-33: Expanded CHIM integration matches 1,390 statics;
13 actors are supported, Nels 204678 is blocked and dreamer 297837 has unresolved
mesh contact. The subsequent final frame-map contact also rejects both actors
after its bounded refit; cause diagnosis and matched native checks are pending.
No tolerance change, actor omission or package acceptance.
[Report](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md).

## 15 October 2026 - NPC model cache dependencies

BUILD-NPC-BAKE-CACHE-KEY-40: Full source suite reports one failure in 4,179
tests: two new NPC fallback helpers were missing from the model cache identity.
Both direct dependencies are now included; the unchanged coverage guard and
extended key-mutation control pass among 112 integrated checks without skips. Source/pin remained unchanged
during the failed run. No native or package promotion.
[Report](bugs/BUILD-NPC-BAKE-CACHE-KEY-40.md).

## 15 October 2026 - source carrier voice prerequisite

BUILD-SEYDA-CARRIER-VOICE-DIR-40: Original-data carrier stops at the first
resident greeting because sound/npc is absent. The source-only route skips the
prototype-NPC stage that previously created it. Source and 224 declared inputs
are unchanged. Narrow repair and actual-write regression pass among 112 integrated checks;
fresh complete carrier pending. No coverage or native/package promotion.
[Report](bugs/BUILD-SEYDA-CARRIER-VOICE-DIR-40.md).

## 15 October 2026 - expanded Seyda offline conversion

CHIM-SEYDA-EXPANDED-STAIRS-40: fresh full conversion at a4a475b passes
3,724 walked probes with zero blocking failures; 532 advisory remain. Original
failed evidence is preserved. Matched native traversal and seams pending.

CHIM-TRACKER-APRON-40: sixteen owned core cells/twenty apron cells reconciled;
2,982 owned references, 103 dependencies, 1,461 deferred references. Four Seyda
and two Vivec ring-2 overlaps have conversion evidence; package count unchanged.

## 15 October 2026 - carrier original-data failure and text output

NPC-BAKE-VERTEX-32: v0.0.40-dev2 carrier stops at Tarhiel after resident fitting.
Original identifier agronian guy, male Wood Elf. Source/inputs unchanged;
severity raised to critical. Overflow-only component-preserving repair now
passes 49 isolated tests; original-data Tarhiel retains all 64 samples at
487,192 bytes. Integrated NPC/writer validation passes 52 checks without
source changes. Complete suite, carrier and native verification remain pending.

CHIM-SEYDA-RECEIPT-TEXT-40: full suite 4,171 tests, one unexpected writer-policy
failure, three skips and three expected failures. Three metadata/carrier writers now pin
UTF-8/LF; 24 affected checks and exact Linux metadata-byte comparison pass.
Original full-suite and initial focused failures remain; full rerun pending.


## 15 October 2026 - source-only carrier and expanded stairs

BUILD-LEGACY-TOWN-MAPS-SHIPPED-36: Optional canonical source-only carrier added;
47 isolated tests pass. Original-data execution and native/package checks pending.

BUILD-SEYDA-HULL2-32: Full-town BSP29 failure retained; new carrier avoids that
terrain intermediate without raising engine limits. Actual conversion pending.

CHIM-SEYDA-EXPANDED-STAIRS-40: Expanded Seyda gate finds 15 starts in solid at refs 3322/3324.
Structure, active-heap and zone checks pass; cause and native capture pending.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: Vivec36core/28apron canonical ingestion
complete offline only; Seyda stair gate blocks the next candidate.

## 15 October 2026 - CHIM ownership reporting

CHIM-TRACKER-APRON-40: the old digest over-counted nine Vivec apron cells. The
source correction reads 36 original core cells and 28 apron-only cells, preserves
original reference types/deferred work, and avoids repeating frame metrics per
cell. Nine behavioral checks pass. The canonical tracker now records this
offline conversion; original types and deferred work remain explicit, and
global converted/package counts are unchanged. Runtime checks remain pending. [Report](bugs/CHIM-TRACKER-APRON-40.md).


## 15 October 2026 - option and tracker record validation

TEST-TOWN-BOUNDS-40 / BUILD-DIAGNOSTIC-PALETTE-38: after the three complete-suite
record failures, the corrected palette classification/history and generated
tracker page passed 168 affected checks, with three Node.js-dependent checks
skipped and no failures or errors. Full new-source validation remains pending.


BUILD-SEYDA-HULL2-32: 15 October 2026, v0.0.40-dev2: the corrected ocean
seal removes the earlier degenerate-floor failure; actual whole-town compilation
then exceeds BSP29 node/leaf limits. Preserve the failed output and engine limits.
[Build blocker](bugs/BUILD-SEYDA-HULL2-32.md).

TEST-TOWN-BOUNDS-40: 15 October 2026, v0.0.40-dev2: full suite ran 4,129 tests
with three new record failures, three platform skips and three expected failures.
Record the palette option in history/classification and regenerate the tracker
page instead of appending prose to generated content. The original failed gate
is preserved. [Gate records](bugs/TEST-TOWN-BOUNDS-40.md).


CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: 15 October 2026, v0.0.40-dev2:
expanded Vivec conversion passed structural, active-heap, allocator and stair
gates (12,828 steps/ramps; zero failures; 1,464 advisory). Ownership readback
and canonical tracker ingestion are complete for this offline conversion.
Seyda carrier, native seams and package inclusion remain pending.
[Report](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md).


## CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: shared exterior carrier, 15 October 2026

15 October 2026 source follow-up: the fresh Seyda gameplay carrier uses shared
original intro placement and validated hand timing. The full intro retains its
default ten-actor path; the carrier selects exterior roles with original IDs,
headings and grounding. It checks conversion/UI/runtime palette compatibility
before cloning, then uses the existing exterior population and opening scripts.
It rebuilds no unrelated interiors or movie. Seventeen focused checks pass;
actual carrier conversion, original-reference parity, native seams and packaging
remain pending. No converted or playable cell count is increased.
[Coverage](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md).


## BUILD-SEYDA-OCEAN-FLOOR-40: expanded ocean floor, 15 October 2026

v0.0.40-dev2: actual town compilation exposed zero-thickness prisms where
original seabed meets the old seal. Candidate source lowers only the hidden
base and enclosure. Eighteen affected checks pass; fresh compilation remains
pending. [Report](bugs/BUILD-SEYDA-OCEAN-FLOOR-40.md).


## CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 and CHIM-EMPTY-MODEL-REPORT-40: offline ocean results, 15 October 2026

v0.0.40-dev2: five original ocean frames converted without scenery placements;
four LEVC spawns remain deferred. The corrected empty-model reporter passes
structural/statistics/heap/zone checks on the retained original geometry.
The canonical tracker records the exact five results without native/package
promotion. Eighty combined town/reporting tests pass; town apron metadata and
generated engine bounds are reconciled. Town conversion and all native seams
remain open. [Coverage](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md),
[reporting](bugs/CHIM-EMPTY-MODEL-REPORT-40.md).


## CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: town source, 15 October 2026

Implemented the approved 52-cell Seyda/Vivec source ownership and separate
aprons; expanded actual source selection and retained existing story IDs.
Ten source tests and 18 bounded fixtures pass; actual conversion/native gates
remain pending. Five ocean frames converted; reporting failure preserved.
[Report](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md).

## CHIM-EMPTY-MODEL-REPORT-40: empty model reporting, 15 October 2026

Ocean validation exposed max() on an empty model list. Both inline/shared
terrain reproductions failed before and pass after the narrow reporting fix;
all ten statistics tests pass. Actual payload gates remain pending.
[Report](bugs/CHIM-EMPTY-MODEL-REPORT-40.md).

## BUILD-TOOLKIT-VERSION-40: source label, 15 October 2026

Git-aware preflight caught the stale Toolkit release label after earlier
exported-source checks skipped the history comparison. Corrected the labels;
retained the existing guard.
[Report](bugs/BUILD-TOOLKIT-VERSION-40.md).

## CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: ocean source and town scope, 15 October 2026

Integrated the explicit ocean admission/routing/shared-terrain candidate into
dev2 source. The isolated implementation has 64 synthetic passing checks;
100 current integration checks pass. Actual conversion/native/package gates
remain pending.
The original-cell-aligned Vivec and Seyda town expansion remains required for
dev2. No packaged or accepted coverage is added by this source integration.
[Report](bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md).

- BUILD-PLAYER-BODY-BUDGET-FALLBACK-39 — 15 October 2026, v0.0.40-dev2:
  continue past reduced animation fits to seek full action sampling under
  unchanged geometry and memory guards. The canonical Argonian diagnostic
  fits122 frames; production and native verification remain pending.
  [Report](bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md).


v0.0.40-dev2 candidate preparation, 15 October 2026: the animation correction
passes 115 shared converter checks. Regenerated assets, full release gates and
shipment remain pending. [Candidate notes](RELEASE-v0.0.40-dev2.md).


## NPC-ANIMATION-OFFSET-40: rotating simplification offsets, 15 October 2026

v0.0.40-dev2 source correction: simplified actor vertices now carry their
rest-pose offsets with the source triangle's rotation and scale. Two prior
rotation failures are reproduced; nine focused checks pass. Translation and
rest-pose controls pass. Broader checks, original-asset conversion and native
leg/gait verification remain pending; no new package or acceptance. Related
[leg shape](bugs/PLAYER-BODY-LEG-SHAPE-39.md) and
[gait](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md) remain open.



## PLAYER-MOVEMENT-FRAME-SKIP-39: original reference and measurement labels, 14 October 2026

Original Nord male/Barbarian/Steed physical lowered/ready gait controls are
recorded with matching displayed attributes and original clothes. Native remote
coordinates are camera-eye readings; earlier actor-position wording is corrected.
The daynight field describes midday hold, not the clock-step switch. Eye-height,
head and travelled-position differences prevent exact motion acceptance.
[Gait](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md),
[ready movement](bugs/PLAYER-READY-MOVEMENT-39.md).


## PLAYER-MOVEMENT-FRAME-SKIP-39: Nord gait control, 14 October 2026

Normal-speed male Nord testing records physical walking/running with fists
lowered and drawn. Corrected ready captures begin at a verified normal-WALK
start and show translation and changing limb poses. Initial endpoint captures
are excluded. Smoothness and matched original/v0.0.38 comparison remain open.
[Gait](bugs/PLAYER-MOVEMENT-FRAME-SKIP-39.md),
[ready movement](bugs/PLAYER-READY-MOVEMENT-39.md).

## CHIM-CHUNK-LOAD-FAIL-33: Seyda terrain allocation retries, 14 October 2026

Chunks224/248 retried terrain allocations of38,144/52,752 bytes. No specific
missing face, cause of route blockage or cell coverage promotion is inferred.
[Report](bugs/CHIM-CHUNK-LOAD-FAIL-33.md).


## PLAYER-PUNCH-THIRDPERSON-39: Khajiit movement and punch control, 14 October 2026

An unreleased diagnostic adds Khajiit female physical W/A/S/D movement with
fists drawn, F lower/redraw, and stationary/strafe LMB attack observations.
The strafe sample combines attack state3 with nonzero WALK velocity; the first
forward sample missed the transient. These positive controls do not close the
reported failure or establish damage, gait quality or original parity.
[Attack](bugs/PLAYER-PUNCH-THIRDPERSON-39.md),
[movement](bugs/PLAYER-READY-MOVEMENT-39.md).

## CHIM-CHUNK-LOAD-FAIL-33: Seyda model allocation retry, 14 October 2026

The same diagnostic logs chunk107/model1408 refusing386,448 bytes with only
11,872 bytes in the largest free run. Gameplay continued. No cell count,
conversion, package, visual-face attribution or coverage acceptance changed.
[Report](bugs/CHIM-CHUNK-LOAD-FAIL-33.md).


## HUD-STATS-29: original paper pickup and scoped HUD comparison, 14 October 2026

Original Morrowind and the candidate show fists becoming available after taking
the papers, before the hall guard; reading alone does not enable fighting.
Scoped review/paper/ring HUD observations are retained. Diagnostic placement and
the failed native exit-validation gate prevent full-route or release acceptance.
[Report](bugs/HUD-STATS-29.md).


## UI-INVENTORY-LAYOUT-40: native preview and allowance correction, 14 October 2026

Corrected model allowance metadata restores the dedicated male Nord inventory
preview after an initial native refusal. Physical equip changes the sword pose,
shows the shield and persists across close/reopen. Same-appearance OpenMW
reference reviewed; other appearances, torch and complete UI remain open.
[Report](bugs/UI-INVENTORY-LAYOUT-40.md).


## UI-INVENTORY-LAYOUT-40 and HUD-STATS-29: build and conversion evidence, 14 October 2026

The exact implementation source completed 4,086 tests: 4,080 passes, three Windows-only skips and three expected failures under TEST-CENSUS-CONTRACTS-40; zero unexpected failures or errors. The Amiga/FPU target also passed. All 20 race/sex inventory companions converted from original assets: ten frames each, 8,286,220 bytes including tags, independently checked for exact hashes, model layout, frame names, triangle indices and finite 12-value attachment rows. Matched native inventory/opening visuals, target cost, complete appearance and shipment remain pending. Both issues remain OPEN; these records do not close visual acceptance. CHIM coverage and delivered dev1 are unchanged.

See [inventory layout](bugs/UI-INVENTORY-LAYOUT-40.md), [opening HUD](bugs/HUD-STATS-29.md) and [the three expected failures](bugs/TEST-CENSUS-CONTRACTS-40.md).

## PLAYER-PUNCH-THIRDPERSON-39: selected ordinary-view observation, 14 October 2026

Unchanged delivered dev1, dry stationary male Argonian: physical LMB in ordinary
third person records attack state3/body102-103 and visible arm motion. Separate
side Preview confirms extension/return. Warp-off observed, original video and
game audio retained; diagnostic queue drained before input. Damage, other
appearances, moving transitions and quality remain OPEN. Normal parent/container
exit0; strict closure failed on boot JIT log diagnostics. Independent153-resource,
33-binding and bitmap readback passes without replacing that failed gate. No
new game code, shipment or CHIM coverage. [Report](bugs/PLAYER-PUNCH-THIRDPERSON-39.md).


## UI-INVENTORY-LAYOUT-40: dedicated pose source, 14 October 2026

The unreleased source selects dedicated original START poses for unarmed and
melee-equipped inventory bodies, with matching attachment tags and two-handed
left hiding. Six converter checks and the before/after runtime regression pass;
original human/female/beast keys and matrices resolve. Gameplay frame counts and
animation clocks are unchanged. Full suite, target, real conversion and matched
native visuals remain pending. Torch-specific posture, full chosen head/hair
and changing worn body parts are unfinished; starting clothing is still used.
The optional modal alias is released on close. No measured target cost or
complete appearance/visual acceptance is claimed. CHIM coverage is unchanged.
[Inventory layout](bugs/UI-INVENTORY-LAYOUT-40.md).


## HUD-STATS-29: opening permission source repair, 14 October 2026

Unreleased v0.0.40-dev2 now gates stats, weapon and magic HUD channels at their
separate registration events. Taking the papers permits fighting before hall
acknowledgement; activation alone permits the weapon slot. Persistent ring pickup
keeps magic visible after dropping it. Manual hiding, debug exemptions and the
remaining door/modal restrictions stay independent. Existing bounded state and
save encoding are reused; full-table activation refuses without taking papers.
Seven focused executable fixtures pass with three expected before-change failures.
Full suite, Amiga target and matched native sequence remain pending. Map/menu
admission, dedicated inventory pose and original artwork are separate work; no
third-person combat or swimming acceptance is claimed. [Report](bugs/HUD-STATS-29.md).


## HUD-STATS-29: opening channel gates source audit, 14 October 2026

Original registration scripts unlock stats, inventory/weapon, magic and map
channels separately. Current HUD drawing lacks these per-channel gates.
This is a source parity finding; matched opening native reproduction and repair
remain pending. Actual first-person weapon readiness is a separate rule.
[Report](bugs/HUD-STATS-29.md).


## UI-INVENTORY-LAYOUT-40: scrollbar source and repeated posture report, 14 October 2026

The v0.0.40-dev2 source adds the shared right scrollbar for lists over six
rows, preserving visible selection and authoritative inventory state. Sanitized
mouse/keyboard/focus/category/close checks and real equip targeting pass;
previous source fails the new scrollbar control. Existing shared-helper and
map/journal checks pass. Full suite, target/native comparison and shipment
remain pending. Further dev1 playtesting shows the rigid ordinary standing
preview again; dedicated original inventory posture remains unresolved.
CHIM coverage is unchanged. [Report](bugs/UI-INVENTORY-LAYOUT-40.md).


## TRACKER-REGISTER-SIZE-33: journal rotation, 14 October 2026

The current journal was 196,510 bytes, only 98 bytes below its unchanged
196,608-byte warning. Selected older entries now live in the
[v0.0.35-v0.0.36 journal archive](journals/BUG_JOURNAL-v0.0.35-v0.0.36.md).
All 133 entry bodies are preserved except relative link paths. Newer
entries, the latest CHIM links and every prior frozen archive are retained.
Current issue states remain in the [register](BUGS.md#fix-index).

## UI-INVENTORY-INTEGRATION-40: scoped native equipment, 14 October 2026

UI-INVENTORY-INTEGRATION-40/INVENTORY-CATALOG-LOOKUP-40: actual names/icons,
equip, modal pause and Russula persistence scoped; missing resources separate.
COMBAT-BLOCKING-36: later exact target/FPU+4079suite pass (4073passes,
3Windows skips/3trackedxfails). Actual Nord steel/shield incoming2BLOCKED
(7/45,15/49); final55health180fatigue is an end snapshot, not no-damageproof.
HUD-STATS-29: centre Guard absent, ordinary targetname retained; interim
fist/weapon+emptymagic remain. Original artwork/effects/selection planned.
COMBAT-NODICE-READOUT-40: actual no-dice armedhealth and unarmedfatigue print
correctly; previous old-controlFAIL/newPASS retained, no dice-on fist proof.
BUILD-PLAYER-BODY-BUDGET-FALLBACK-39:19current+legacyArgmale122frames/tags
retainhit3/death5/jump4. Legacyhold31~67msearly/anatomyguardlimit open.
PLAYER-READY-MOVEMENT-39: selectedArgmale physical WALK3 moves; held/released
shield observed. PLAYER-PUNCH-THIRDPERSON-39:120queuedreadouts can defer LMB;
exactguesttiming unknown, negativecapture inconclusive, Preview suppression unproven.
Death/jump/anatomy/matchedgait/allappearance acceptance remain open.
COMBAT-FATIGUE-HEALTH-DAMAGE-39: earlier19→1/2→0 decline explained; no new
chance regression. CHIM-CHUNK-LOAD-FAIL-33:249/107 retries, no coverageclaim.
NPC-HEAD-DECIMATION-33: menuhead distortion remains. WATER-GAMEPLAY-PARITY-38:
scoped depth controls positive, posture/entry/parity open. UI-INVENTORY-LAYOUT-40:
renewed bottom-hint crowding; inset/wrap and original UI/pose/actions planned. CHIM-CELL-FEATURE-LIST-INCOMPLETE-38:
World/Local reference planned, coverage unchanged. Reports preserve history.

PLAYER-READY-MOVEMENT-39: race shortcut preserves stats/identity/equipment;
14priorfunctional checks pass, revised routing/target/native pending.
ENGINE-RESIDENT-REGISTRY-GROWTH-36: full gate catches270>269commands,+32B;
reopened, historical guard retained. AWDC1 repair+20focusedPASS; new
fullgate/target/native/package pending.


## UI-INVENTORY-INTEGRATION-40: fixture links and journal guard, 14 October 2026

UI-INVENTORY-INTEGRATION-40: the next4,072-check gate has4 failures/0errors:
mouse GNU89/GNU99 and focus fixtures omit new comparator/text dependencies;
journal198,915B exceeds unchanged196,608B guard. Repair links real inventory
rules and bounded drawing captures; compact recent duplicate journal prose
with headings/history and full linked reports preserved. Runtime unchanged;
7affected checks pass; next full gate/native acceptance pending.



## UI-INVENTORY-INTEGRATION-40: harvest award reaches inventory modal, 14 October 2026

[UI-INVENTORY-INTEGRATION-40](bugs/UI-INVENTORY-INTEGRATION-40.md): synthetic
AW_HarvestTake-to-modal check passes: actual ingredient name/count, no repeat
award, and I/Escape reopen preserves state. Catalogue I/O is controlled;
physical pickup and repaired native presentation remain pending.


## CHIM-VIEW-FACES-33: exterior Dwemer slowdown report, 14 October 2026

[CHIM-VIEW-FACES-33](bugs/CHIM-VIEW-FACES-33.md): maintainer reports occasional exterior
Dwemer FPS drops; exact site/build/settings/cause and measurements are unknown,
not reproduced. Dev2 rings 0/1/2 stay primary; plan measured model, culling,
transform/overdraw, cache, server/collision and streaming audit. No gain claimed.


## ENGINE-FPU-UNIMPL-31: target pass and native inventory limits, 14 October 2026

[ENGINE-FPU-UNIMPL-31](bugs/ENGINE-FPU-UNIMPL-31.md): subsequent dev1 Amiga target
and linked68040 gate pass without allowlist expansion. Exact suite:4,072 run,
4,066 pass,0 failures/errors,3 Windows skips,3 expected failures.
COMBAT-BLOCKING-36/UI-INVENTORY-INTEGRATION-40: native catalogue/layout fail and
actual sword/shield grants refuse, invalidating equipped-block conclusions.
Catalogue/layout source repairs pass4 affected checks; their target/native
and maintainer acceptance were pending. Earlier target failures remain preserved.


## UI-INVENTORY-LAYOUT-40: native field overlap and preview orientation, 14 October 2026

[UI-INVENTORY-LAYOUT-40](bugs/UI-INVENTORY-LAYOUT-40.md): native text crosses
fields/footer and initial portrait faces away; AW_UITextBox centres without
clipping. Bounded console text/full-width name/half-turn source repair passes4
checks; target/native/original comparison and acceptance pending. Lookup is
separate INVENTORY-CATALOG-LOOKUP-40; no item loss established.


## ENGINE-FPU-UNIMPL-31: blocking recurrence, 14 October 2026

[ENGINE-FPU-UNIMPL-31](bugs/ENGINE-FPU-UNIMPL-31.md)/COMBAT-BLOCKING-36: initial
dev1 linked target fails68040 reachability via block library trig. Safe engine
math/pole-stable repair keeps allowlist/assets unchanged; old pose fixture fails,
1,925 repaired cases/21 checks/one object pass. Linked target/native/acceptance
were then pending; later target result recorded above.


## UI-INVENTORY-INTEGRATION-40: dev2 interaction scope, 14 October 2026

[UI-INVENTORY-INTEGRATION-40](bugs/UI-INVENTORY-INTEGRATION-40.md): earlier
4,071-check suite had0 unexpected failures/errors,3 Windows skips,3 expected
failures; target/native then pending. Dev2 requires full icons, drag-to-character
equip/use and category sorting/filtering. Selected10 assets/context actions
are incomplete; CHIM/scenery drops safely refuse. Later gates recorded separately.


## TEST-CENSUS-CONTRACTS-40: three expected failures, 14 October 2026

[TEST-CENSUS-CONTRACTS-40](bugs/TEST-CENSUS-CONTRACTS-40.md): three open expected
failures: inner brace defeats handler regex despite AW_QuickCharOpen;
quickchar set lacks catalogue alias despite raw handler; DIRECT_START lacks
--skip-census. Later loop terms require audit. No native/maintainer proof.


## UI-INVENTORY-INTEGRATION-40: command catalogue ordering, 14 October 2026

[UI-INVENTORY-INTEGRATION-40](bugs/UI-INVENTORY-INTEGRATION-40.md): 4,063-check
gate catches one grant-command sort failure. Catalogue sorter/page regeneration
correct source order; semantics unchanged. New gate/native then pending.


## DOCS-CHIM-PROGRESS-STALE-38: final shipment wording recurrence, 14 October 2026

DOCS-CHIM-PROGRESS-STALE-38/DOCS-RELEASE-EVIDENCE-SCOPE-39: reconcile README/map
guide with final039 delivery07:15:35UTC; earlier Nord views are historical.
Punch/readied movement/block/swim remain open. No new gameplay/coverage or
fresh-download acceptance; documentation checks remain separate.


## CHIM-WINDOW-MOUNT-CROSS-CELL-33: offline conversion, 14 October 2026

CHIM-WINDOW-MOUNT-CROSS-CELL-33: converter pin passes15checks; Pelagiad exits0
in40.74s(156.883s with verification):304stairs/0failures/22advisory,22door meshes/
1marker,3,487,056B modelled headroom. Selection294refs unchanged;6windows retained,
2borrow house3561 from(-1,-7);7outside-frame STATs excluded. Native/original/
traversal/interiors/package/maintainer gates pending.
CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: audit19ring0–2 entrances/22Pelagiad doors;
original locations/destinations recorded, interiors deferred. Only Ansi300699
has an activation row in inspected RC2 banks; exact-package/native/Dwemer
reference binding pending. Ring0's5sea cells lack runtime owners;4LEVC deferred.
Template history/town expansion plans add no runtime/package coverage.


## PLAYER-MOVEMENT-STATS-PARITY-39: movement speed source study, 14 October 2026

Maintainer renewed the fast-traversal report. Source study quantifies fixed120/216 ground targets, diagonal gain and level-water0.7 against original numerical settings/OpenMW stat, load, race, effect and fatigue calculations. [Study](MOVEMENT_SPEED_STUDY.md) separates source arithmetic from native timing. No speed tweak or parity acceptance; matched forward/directional/water timing remains pending.

## UI-INVENTORY-INTEGRATION-40: integration and placement boundaries, 14 October 2026

[UI-INVENTORY-INTEGRATION-40](bugs/UI-INVENTORY-INTEGRATION-40.md): fixed-hull,
edict quarantine and reserve findings yield bounded point/hull0 placement and
pre-transfer guards:32 carried IDs/32 drops/16 new models per level.39 checks
and6 objects pass; combined/native/acceptance then pending. CHIM/scenery safely
refuse without loss. COMBAT-BLOCKING-36: named8-frameAWB1, writers/stubs pass;
body frames unchanged, native visible block pending.


## COMBAT-BLOCKING-36: first-person source candidate, 14 October 2026

[COMBAT-BLOCKING-36](bugs/COMBAT-BLOCKING-36.md): dev1 alias renderer integrates
original left-arm block plus actual shield;2Nord appearances/15 checks pass.
Normal hand stage binds palette/block hashes and rejects stale catalogues;
18appearances/target/both-view native/acceptance were pending. No coverage gain.


## PLAYER-PUNCH-THIRDPERSON-39: held attack during raising, 14 October 2026

[PLAYER-PUNCH-THIRDPERSON-39](bugs/PLAYER-PUNCH-THIRDPERSON-39.md): compiledQC
old control fails heldLMB during raise; source defers latch until ready.
Cancellation/torch/no-autofire checks pass; physical-input/native maintainer-case
acceptance remains pending.


## Renewed RC2 gameplay reports, 14 October 2026


- PLAYER-READY-MOVEMENT-39: source dbg characterchange reuses pier appearance
  (all=full sequence);2 C/console checks pass, story gates retained. Target/native/
  package pending; no gameplay repair.
- PLAYER-PUNCH-THIRDPERSON-39: maintainer repeats no physicalLMB third-person punch.
  ExactRC2 input/damage control attacks/hits60fatigue; visible maintainer case unaccepted.
- PLAYER-READY-MOVEMENT-39: fists-ready immobility is separate from gait loss.
  After-Census Nord A/S/D control moves; obstructed first attempt proves nothing.
- COMBAT-BLOCKING-36: maintainer repeats missing both-view block. Eligible control
  guards but shows fists/GuardHUD/low arms; severity high, no-unarmed rule retained.
- WATER-GAMEPLAY-PARITY-38: maintainer repeats sinking/upright submersion; private
  screenshot retained. Earlier depth/pose controls do not accept this case.
- PLAYER-TORCH-THIRDPERSON-38: target and scoped Nord native F/V/hold/walk/run/off/
  first-person pass; original game/audio clip shows mesh/raised arm.20companions
  bake/readback pass; original/full image/package/maintainer gates pending.
- WATER-GAMEPLAY-PARITY-38:20swim companions bake; ordinary-collision native
  selects moving swim body but reproduces idle descent42units/s. Plan removal
  of Quake idle drift while preserving pitch/friction/acceleration. New behavior,
  both-view dive/original/package gates pending.


MESH-VIVEC-CAP-GAP-38: 13 October 2026, RC1 maintainer report and private evidence reviewed. Still visible in RC1: three newly inspected views in cell2,-10 show separated Vivec mushroom cap/rim seams. Exact variants and packaged model identities need binding; prior cell5,-10 evidence remains. No closure repair accepted.

NPC-ORDINATOR-APPEARANCE-39: 13 October 2026, RC1 maintainer report and private evidence reviewed. Open RC1 report; RC2 follow-up. The targeted actor is labelled Ordinator but appears unhelmeted, pointed-eared and brown/red-clothed. The maintainer compares the appearance to Fargoth. Exact actor/model identity is not yet established; no intentional placeholder is claimed.

PLAYER-MOVEMENT-FRAME-SKIP-39: 13 October 2026, RC1 maintainer report and private evidence reviewed. Open RC1 report; RC2 follow-up. Fast third-person movement no longer has the earlier quick foot animation and looks like skipped frames. The maintainer additionally describes the run as two frames.

WATER-GAMEPLAY-PARITY-38: 13 October 2026, RC1 maintainer report and private evidence reviewed. Still incomplete in RC1: maintainer reports absent third-person swimming/diving and sinking, with an inspected upright underwater pose at Vivec Hlaalu. Missing swim groups are source-confirmed; exact physical failure, breath/drowning and matched original behavior remain open.

PLAYER-PUNCH-THIRDPERSON-39: 13 October 2026, RC1 report / RC2 follow-up: Open RC2 release blocker reported on 13 October 2026. Drawing the fists animates, but pressing default attack LMB shows no third-person punching animation. The maintainer corrected the initial input-failure report: the punch apparently executes; missing body animation is the confirmed symptom. Actual hit/damage behavior is not independently verified.

PLAYER-BODY-LEG-SHAPE-39: 13 October 2026, RC1 report / RC2 follow-up: Open RC2 release blocker reported on 13 October 2026. The maintainer reports abnormally thin, distorted-looking legs on a Nord player body. Sex, exact pose and selected appearance were not specified. Shape and animation causes remain separate possibilities.

NPC-SPEAR-ATTACK-REGRESSION-39: 13 October 2026, RC1 report / RC2 follow-up: Open RC2 release blocker reported on 13 October 2026. In first-person view the maintainer no longer sees the guard spear-attack animation that worked before. The maintainer separately confirms the guard can kill the player; missing attack animation and actual combat damage are different observations.

COMBAT-FATIGUE-HEALTH-DAMAGE-39: 13 October 2026, RC1 report / RC2 follow-up: Closed as expected behavior for the clarified observation; no damage-rule repair claimed. The maintainer observes Eldafire bare-fist hits lowering the green fatigue bar while the red health bar remains unchanged, and confirms the armed guard can kill the player. Upright unarmed fatigue damage is expected; this observation does not prove a health-damage regression.

NPC-NO-RUN-ANIM-35: 13 October 2026, RC1 report / RC2 follow-up: Still present in v0.0.39-rc1 (maintainer, 13 October 2026): Seyda Neen guards and other NPCs chase without running animation. Repeated report, RC2 release blocker. Earlier source/default-profile changes did not establish this exact packaged chase behavior; cause and repair verification pending.

ANIMKIT-COVERAGE-35: 13 October 2026, RC1 report / RC2 follow-up: Still present in v0.0.39-rc1 (maintainer, 13 October 2026): Seyda Neen guards and other NPCs chase without running animation. Repeated report, RC2 release blocker. Earlier source/default-profile changes did not establish this exact packaged chase behavior; cause and repair verification pending.

DOCS-CHIM-PROGRESS-STALE-38: 13 October 2026, v0.0.39: the standard Toolkit release check required metadata version 0.1.3 and the AmiWind v0.0.39 last-update label because its documentation and inclusion data changed. Existing controls are unchanged; no native acceptance follows from version labels.

DOCS-CHIM-PROGRESS-STALE-38: 13 October 2026, v0.0.39 final preparation: the maintainer approved RC1 as the final-release basis. The main README, Toolkit imagery labels, dated CHIM map and exact RC1 package/native findings are reconciled. Final source and image checks remain separate. No issue is closed and no cell-wide or all-appearance acceptance is inferred from release approval.

BUILD-SHADOWED-WORLD-MAPS-38: 13 October 2026: RC1 finalization still demanded the 135 intentionally uncompiled town-owned exterior maps during sky preparation. The shared sky, cull, hand-metadata, always-included and night-lighting classifier now excludes only checklist-validated omissions, bound to the validated CHIM town plan before frame generation. Other missing maps still fail. Final fingerprint and packing still require actual CHIM owner frames. Engine and converted content are unchanged; exact-image checks remain required.

CHIM-CHUNK-LOAD-FAIL-33: 13 October 2026: maintainer reports heavy but working Dwemer access; cell (9,2), global 77750,20044,1980 shows chunk 116 zone-full retries. Evidence OWNER-20261013-DWEMER-CHUNK116; cause, recovery and costs remain open.

DOCS-CHIM-PROGRESS-STALE-38: 13 October 2026: the current 14:04 UTC reference records 1190 converted cells including 15 failing audits, 99 empty-sea cells, 3 not converted and a 1274/1292 audit milestone. Earlier counts stay dated history; native/package states are separate.

SAVE-TELEPORT-CHECKPOINT-38, SAVE-LAVA-DEATH-LOOP-38 and UI-DEATH-DAMAGE-TINT-38: 13 October 2026: unknown image metadata no longer labels reports legacy-only. Compiled source evidence is distinct from target acceptance.

INTRO-CAMERA-GATING-38, PLAYER-JUMP-THIRDPERSON-38, PLAYER-READY-THIRDPERSON-38 and UI-KEY-HELP-STALE-38: 13 October 2026: reconciled completed RC1 source suite/Amiga compilation with pending body/readback/native evidence. No new runtime scope; unfinished work continues in v0.0.40.

SAVE-TELEPORT-CHECKPOINT-38, SAVE-LAVA-DEATH-LOOP-38 and UI-DEATH-DAMAGE-TINT-38: 13 October 2026: exact RC1 registered arrival save/lava/death/reload session and post-exit AWS decode reviewed; health 55 checkpoint survives reload. Untinted prompt observed; immediate key-selection frame black, selection acceptance pending. Old unsafe saves and wider coverage remain open.

PLAYER-JUMP-THIRDPERSON-38, PLAYER-READY-THIRDPERSON-38 and BUILD-PLAYER-BODY-BUDGET-FALLBACK-39: 13 October 2026: twenty actual model/layout readbacks pass; 1,751 non-body assets unchanged. One Nord male motion/camera session inspected; broader motion, memory/performance and matched reference acceptance remain open.

ANIMKIT-ACTOR-ABI-SITES-35, BUILD-SHADOWED-WORLD-MAPS-38, BUILD-WORLD-FINGERPRINT-RETIRED-38 and BUILD-WORLD-PACK-RETIRED-38: 13 October 2026: normal RC1 image finalization, complete HDF ownership readback and independent ZIP extraction pass. Final v0.0.39 rebinding remains required.

DOCS-CHIM-PROGRESS-STALE-38: 13 October 2026: unchanged 14:04 UTC conversion/audit snapshot, separate 17:45 UTC RC1 package layer: 360 whole regional cells, six partial town overlaps excluded. Local served data readback matches; per-type converted/packaged actor/gameplay counts remain unknown.

CHIM-SEYDA-HUNK-GAP-33 and CHIM-ZONE-RESERVE-EARLY-33: 13 October 2026: exact RC1 native logs retain sub-2-MiB gaps, Seyda 2,091,392 bytes and Balmora 2,063,344. Reserve safety remains open.

CHIM-CHUNK-LOAD-FAIL-33 and CHIM-GRAFT-REPACK-EMPTY-33: 13 October 2026: vf1703 chunk20 allocation retries and nonempty fallback repacks remain. The historical zero-chunk collapse is not reproduced by these logs; full residency/visual/performance acceptance remains open.


ANIMKIT-ACTOR-ABI-SITES-35: 13 October 2026: RC1 full-image preflight rejected all twenty expanded bodies because its reader confused the 64-frame per-group limit with the existing 256-frame model limit. Reopened with a bounded reader correction and multi-group payload regression; image/native verification pending.

AUDIO-STOP-CHANNEL-RANGE-39: 13 October 2026: source review found S_StopSound scanning 0..7 while the allocator uses dynamic slots 4..11. Prepared the matching interval and extended the real-mixer fixture for every slot, exact matching, ambient/static controls and mixed PCM. Tests and native audio remain pending.

COMBAT-AMBIENT-SPEECH-GATING-38: 13 October 2026: traced ungated greeting/manual/idle paths and separate audio/subtitle lifetimes. The opponent's idle think stops, but bystanders can still speak. Recorded the original actor-local rule and the maintainer's broader combat policy; full suppression and native verification remain pending.

WATER-GAMEPLAY-PARITY-38: 13 October 2026: source review confirms player swim groups are absent and the inherited drowning routine is excluded by QUAKE2 and unused by the active player callbacks. Recorded OpenMW 0.48 breath and depth rules for comparison. No water behavior changed; matched native checks remain pending.

PLAYER-READY-WATER-MOVEMENT-38: 13 October 2026: inspected AmiQuake contents sampling and water movement dispatch; neither depends on equipment. Missing swim poses explain an animation gap but do not prove the physical cause of the reported water-walking. Issue remains open.

PLAYER-TORCH-THIRDPERSON-38: 13 October 2026: source review found no swimming/submersion restriction in player torch equip/toggle or hand updates. Recorded the original equipped-light transition for a matched comparison; no repaired behavior or native acceptance claimed.

UI-KEY-HELP-STALE-38: 13 October 2026: completed source coverage for fixed Escape, Shift+V, music and photo-mode shortcuts. The fixed console footer remains on every page. Conflicting saved bindings for reserved keys are no longer advertised as reachable actions; bindings themselves are untouched. Extended the unexecuted C fixture; native layout and the separate blank-frame report remain open.

DOCS-ROADMAP-IMPLEMENTATION-39: 13 October 2026: compared the roadmap with published v0.0.38 and current source. Corrected the stale noclip implementation claim, separated the existing console music switch from unfinished settings work, and labelled the old all-green-zone promise as a target. Kept the native CHIM frame-map header planned and player jump as a candidate. No new runtime or package acceptance.

UI-KEY-HELP-STALE-38: 13 October 2026: prepared font-aware help rows and columns, per-column clipping and page clamping when bindings or display settings change. Extended the existing wait/help C fixture; execution, compilation and native captures remain pending. The maintainer's separate blank-frame report still has no confirmed cause. No input bindings changed.

UI-KEY-HELP-STALE-38: 13 October 2026: prepared readable labels for default POV, zoom, movement, block/context and music bindings, and clarified both console keys in the footer. Updated the keyboard reference's stale version heading, missing camera defaults and historical torch-report wording. Layout and blank-frame reproduction remain open; compile and native checks pending.

PLAYER-READY-THIRDPERSON-38: 13 October 2026: original source-data review confirmed human/beast fists-ready idle, walk, run and jump sections, with female fallback to the base clips. Recorded the requirement to preserve locomotion during ready/equip states. No ready-pose repair or native acceptance is claimed.

BUILD-PLAYER-BODY-BUDGET-FALLBACK-39: 13 October 2026: source review found that an animation byte-budget failure aborts player-body conversion before smaller meshes are tried, and that a later vertex-budget failure can discard an earlier valid fit. Registered before repair. Bounded retry and five boundary regressions prepared; none executed, no affected race/sex bake demonstrated and no runtime acceptance claimed.

RELEASE-WORKING-VERSION-ISOLATION-39: 13 October 2026: source inspection found the final publication wrapper used the next development version record. Optional per-release argument forwarding and rejection regressions prepared; execution and upload validation pending.

DOCS-RELEASE-EVIDENCE-SCOPE-39: 13 October 2026: release guard rejected the rewritten known-issues heading. Restored its required heading and ID-labelled bullets; failed receipt retained.

DOCS-RELEASE-EVIDENCE-SCOPE-39: 13 October 2026: corrected release-note evidence scope and links to open animation issues. Prior image checks remain historical; compact-image and native gates remain pending.

13 October 2026 - BUILD-WORLD-PACK-RETIRED-38: Source audit found that disk packing still opens omitted routing-only BSPs after the fingerprint passes. The validated omission list now reaches partition selection; additional integration and refusal cases are prepared. Tests and full-image acceptance pending.

13 October 2026 - BUILD-WORLD-FINGERPRINT-RETIRED-38: Prebuild-skipped exterior maps now carry verified omission records into the final fingerprint. 65 focused checks, including the real image CLI, pass; duplicate maps, unused catalogues and missing CHIM owners fail. Full image pending.

13 October 2026 - BUILD-WORLD-FINGERPRINT-RETIRED-38: Full-image fingerprint failed after correct exterior BSP retirement; explicit removal filtering and a combined regression prepared. HDF/native validation pending.

13 October 2026 - BUILD-SHADOWED-WORLD-MAPS-38: Final routing audit flagged 135 retained maps; dependency review and used-map-only acceptance remain open.

13 October 2026 - RELEASE-LAVA-IMAGE-ALLOWLIST-38: Source preflight caught two unapproved image types; narrow allowlist repair prepared before packaging.

13 October 2026 - TOOLKIT-TEXT-ENCODING-38: 13 October 2026 recurrence in release documentation: a locale-decoded text edit damaged historical README punctuation and a heading anchor. The anchor gate detected it before packaging. Historical content was restored from the previous commit using explicit UTF-8 byte decoding; all 1,008 document checks pass. This is a source-editing workflow failure, not a game-runtime change.

13 October 2026 - CHIM-LAVA-TERRAIN-SPIKES-38: Final full-image verification, 13 October 2026: all 349 original lava references across 27 cells survive conversion and final HDF readback matches the rebuilt CHIM world. Scoped native views show a continuous shoreline with HUD and crosshair off. Contact with god mode and noclip off records health 100 -> 76.9 -> 64.8 -> 52.8, water level 1 and lava contents -5. This supersedes pending integration notes; sound, wider traversal and maintainer acceptance remain open.

13 October 2026 - CHIM-MOLAG-MEMORY-38: Final full-image verification, 13 October 2026: completed-stage Tel Uvirith and all four sprite assets passed HDF readback. Both teleport aliases reach its CHIM frame. Active-ring memory is 5,596,320 bytes and load-ring memory 5,767,824 bytes against 6,242,304 bytes. Arrival and scoped scene verified; normal staircase traversal and maintainer acceptance remain open.

13 October 2026 - BUILD-IMAGE-CHIM-MAPS-SERIAL-36: Full-image verification, 13 October 2026: 360 regional frame maps generated in 4.3 seconds at 1.5 reported cores with zero pass-cache hits, compared with 267 seconds in the preceding build. The complete image passed the performance guard without waivers. Earlier byte-equivalence verification remains applicable; final map readback also passed.

13 October 2026 - BUILD-FLORA-BSP-BYTES-38: Open: vf1099 exceeds the BSP byte budget by 72,048 bytes; vf2551 by 150,360 bytes. CHIM replacement and final package verification pending.

BUILD-CACHE-OWNER-FAILS-STAGE-34, 13 October 2026: a standalone v0.0.38
conversion wrote 123,873 root-owned cache entries. The normal image preflight
caught seven unwritable directories before any stage. Repaired ownership
without deleting cache data; require the regular builder user for standalone
conversions too. Full image retry pending; the early rejection worked as designed.

13 October 2026 - TOOLKIT-TEXT-ENCODING-38: Corrected in local source, including both Local view button variants; whole Toolkit text scan clean for observed corruption patterns. Packaged release verification pending.

13 October 2026 — TOOLKIT-CELL-HIGHLIGHT-SCALE-38: maintainer reported a displaced selected-cell outline. Corrected CSS/device-pixel scaling; verified alignment and checkbox behavior in the browser. Packaging pending.

12 October 2026 — CHIM-MOLAG-MEMORY-38: compiled door-panel test map loaded
and ran for 33 seconds in FS-UAE with both panels visible. The close and
oblique noclip captures do not establish appearance or door interaction;
matched reference and normal movement checks remain pending.

12 October 2026 — CHIM-MOLAG-MEMORY-38: compiled two bitmap-panel door types
for six placements. Active and load peaks fall 23,840 B each, leaving only
1,808 B nominal load-ring headroom against the old budget before separate
sprite Hunk costs. Collision graphs match; native door use and appearance
are pending. No memory-fit or release acceptance.

12 October 2026 — CHIM-MOLAG-MEMORY-38: compiled lantern/hook trial reduces
placed polygons 30,985 to 27,007; fixed-stage-6 ash sprites bring active peak
to 6,032,032 B but load peak remains 6,264,336 B, 22,032 over the old budget
before sprite Hunk allocation. Native 31-second load/run is a limited diagnostic;
reference appearance, movement, runtime stage selection and package acceptance
remain pending.

12 October 2026 — CHIM-MOLAG-MEMORY-38: stronger all-nonterrain reduction
plus terrain clipping reaches 30,985 placed faces and a 9,045,776 B modelled
all-stage peak, still 2,803,472 B over budget. A hypothetical stage-6 filter
misses the budget by 80 B at one position; runtime residency and native visual
checks are pending. No deployment or fixed status.

12 October 2026 — CHIM-MOLAG-MEMORY-38: targeted 128-unit root/slavemarket
tiling after optimizer and terrain cut raises the modelled peak 2,317,856 B
and fails three hull-limit checks. This setting is rejected; broader geometry
strategies and native acceptance remain open.

12 October 2026 — CHIM-MOLAG-MEMORY-38: lantern/support model audit finds
7,434 placement-expanded faces but 140,352 B across four distinct resident
models. A 512-unit tile trial after optimization and terrain clipping raises
the modelled all-stage peak by 670,208 B; this setting is not adopted.

12 October 2026 — CHIM-HIDDEN-FACES-33 / CHIM-MOLAG-MEMORY-38: opt-in Molag Mar
(10,1) terrain cut after optimizer removes 1,510 placed and 1,244 stored faces
and lowers the modelled peak by 149,408 B. Combined reduction from the original
is 6,905 placed / 6,247 stored faces and 1,005,680 B modelled peak. The cell
still exceeds the fixed memory budget; native/reference acceptance is pending.

12 October 2026 — BUILD-LAVA-TERRAIN-BUDGET-38: full candidate3fac049 reached scenery overlay but vf1397 exceeds the4MiB storage cap; no bypass or delivery.

12 October 2026 — MESH-VIVEC-CAP-GAP-38: candidate parasol town profile fails sampled material-boundary checks; boundary-lock diagnostic passes at160 versus135 triangles. Native comparison pending.

12 October 2026 — INTERIOR-HULL-CHAIN-33: maintainer reports severe Arena Pit interior slowdown; retain as a performance observation pending measured cause.

12 October 2026 — MESH-VIVEC-CAP-GAP-38: maintainer screenshot shows a cap opening at Vivec cell 5,-10. Exact model, installed build and cause unknown; matched original/native comparison pending. Separate regression from historical GEO-01.

12 October 2026 — CONFIG-COMMENT-29: the unshipped dev3 LAND-fill comment
reintroduced a semicolon, caught by the existing loading-delay source regression.
Quake splits command-buffer semicolons before discarding comments. Replaced
the separator with a period; final full-suite validation is pending. No shipped
config was changed and this does not promote the historical issue's status.

12 October 2026 — WORLD-SLOPE-STUCK-38: maintainer reports jumping cannot pass
the Vivec Arena boat-path obstruction; other docks remain untested.
CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: added maintainer-reported missing gondola
travel as a planned service, distinct from visible Dalse Adren and dock access.
HORIZON-HOLES-31: accounted for the requested persistent LAND-fill toggle in
the resident registry: one cvar, 24 structure bytes and 32 zone bytes; native
frame-time and complete terrain coverage remain unaccepted.

12 October 2026 — HORIZON-HOLES-31: added the cell 0,17 distant-terrain
reproduction sequence and Land Fill Independence v1 candidate. Saved
`aw_land_fill` and `dbg land fill 0/1` separate enabled LAND passes from fog;
the legacy rasterizer selector remains experimental. Five focused Docker
tests pass; target visual and CPU/RAM acceptance are pending.
WORLD-SHORE-OPEN-GEOMETRY-38: added the cell 0,18 rock-opening pose; source
reference identification and matched original/native repair evidence remain pending.

Entries for v0.0.35 (from 10 October 2026). Older entries are frozen: [8 October 2026 to the v0.0.34 release](journals/BUG_JOURNAL-v0.0.34.md), [7 October 2026](journals/BUG_JOURNAL-v0.0.31.md) and [v0.0.29 and earlier](journals/BUG_JOURNAL-v0.0.29.md). The current status of every bug is in the [register](BUGS.md).

## Stair fixes verified, AW-LEASE-NO-GROW-36, 11 October 2026

VIVEC-TEMPLE-STAIRS-33, STAIRS-EBONHEART-CHIM-36, STAIRS-VIVEC-ROOMS-JOINT-36 and BUILD-IMAGE-STAIR-WALK-SERIAL-36 are fixed
in v0.0.36. The whole-city Vivec MiniWind built from the integration line accepted no stair findings and had no blocking
failures, and every flight step of its 130 rooms passed. Its image stair walk covered 132 maps in 252.6 s on 16 workers;
before, it took 15 min 55 s on 1.8 cores. BUILD-STAIR-KEY-BOOKKEEPING-36 stays open until a rebuild shows the walks
reused. AW-LEASE-NO-GROW-36 (maintainer): a gate that starts or ends now shrinks or grows the running builds; their worker
pools still keep the size they started with.

## CHIM-FRAME-EDGE-EFRAG-CRASH-36 fixed, 11 October 2026

CHIM-FRAME-EDGE-EFRAG-CRASH-36 is fixed in v0.0.36. It was reported four times, by the maintainer in normal play among them.
The root cause was in CL_RelinkEntities: it pointed its loop cursor at the third-person body, so every entity after it
was read and written from the wrong memory. The body now has its own pointer, and labelled safety nets guard the efrag
links. In integration gate 2203 the smoke had Seyda Neen and Balmora in play, and the safety net was never used.

## SMOKE-PASSES-WITHOUT-MAP-36, 13 October 2026

SMOKE-PASSES-WITHOUT-MAP-36: scripted sessions also accepted an alive emulator
after Host_Error disconnected the game. Added final screen/signon/world-leaf
checks and a shell reproduction; seven smoke-harness tests pass. Diagnostic
image construction had omitted the changed CHIM index; correcting that fixture
allowed the lava cell to run. Its earlier PASS is invalid evidence.

## CHIM-FRAME-EDGE-EFRAG-CRASH-36 (persisting) and ENGINE-CRASH-EXIT-KEYBOARD-36, 11 October 2026

CHIM-FRAME-EDGE-EFRAG-CRASH-36 is PERSISTING: after the README screenshot session, the maintainer hit "R_StoreEfrags: Bad
entity type 270440" in normal play of the v0.0.36-dev5 playtest (FS-UAE JIT, Seyda Neen, backing away from a hostile
NPC). The value is the long at Amiga address 0x44, which is where model_t.type is read when the model is NULL: a leaf
link points to an entity whose model was cleared after it was linked. ENGINE-CRASH-EXIT-KEYBOARD-36: after that crash
the AmigaDOS shell typed "amiwind" as "AIWDID" (shift/caps latched, M and N eaten), consistent with the engine's
input.device handler left in the chain on the crash route.

Root cause, confirmed the same day by a same-scene comparison: the third-person view's player body overwrote the entity
loop pointer in CL_RelinkEntities, so the rest of that frame's entities were walked in foreign memory and damaged leaf
links. Without the fix the Seyda Neen third-person scene froze (2 of 2 runs) and the Balmora idle camera damaged a link
(2 of 2); with it, all runs were clean.

## CHIM-FRAME-EDGE-EFRAG-CRASH-36 (persisting) and ENGINE-CRASH-EXIT-KEYBOARD-36, 11 October 2026

CHIM-FRAME-EDGE-EFRAG-CRASH-36 is PERSISTING: after the README screenshot session, the maintainer hit "R_StoreEfrags: Bad
entity type 270440" in normal play of the v0.0.36-dev5 playtest (FS-UAE JIT, Seyda Neen, backing away from a hostile
NPC). The value is the long at Amiga address 0x44, which is where model_t.type is read when the model is NULL: a leaf
link points to an entity whose model was cleared after it was linked. ENGINE-CRASH-EXIT-KEYBOARD-36: after that crash
the AmigaDOS shell typed "amiwind" as "AIWDID" (shift/caps latched, M and N eaten), consistent with the engine's
input.device handler left in the chain on the crash route.

## CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36, COMBAT-BLOCKING-36 and the platform field, 11 October 2026

From the maintainer's dev5 playtest on FS-UAE with JIT. [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](bugs/CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md):
during a fight, switching to third person (Tab) hides the NPC you are fighting; it comes back in first person. The
cause is not known yet. [COMBAT-BLOCKING-36](bugs/COMBAT-BLOCKING-36.md) is a request: blocking in combat. NPCs should block by
their Block skill with a block animation, and the player should block with the right mouse button, so the companion pick
moves to another key.
Both are targeted at v0.0.37.

CHIM-FRAME-EDGE-EFRAG-CRASH-36 is PERSISTING. The maintainer hit the same efrag crash in normal play of the dev5 build in
Seyda Neen, after it was first seen in a noclip view past the Vivec frame edge. It blocks rc1.

Bug entries now carry a `platform` field, the platform or emulator a bug was seen on. The maintainer's game-side reports
on numbered builds from v0.0.36 on must fill it in, and the tracker test enforces this.
## BUILD-IMAGE-HASH-UNDERUSED-36 and BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36 fixed, 11 October 2026

[BUILD-IMAGE-HASH-UNDERUSED-36](bugs/BUILD-IMAGE-HASH-UNDERUSED-36.md): payload hashing now runs on
threads of the stage (size batches, largest first, one lane for small files) instead of one spawned
process task per file; the dev5 payload hashes in 0.8 s instead of 4.8 s with 1.5 instead of 10.6
CPU-seconds, same digests. The process method stays selectable (`AMIWIND_HASH_METHOD=process`).
[BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36](bugs/BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36.md): the world map heap
audit walks static entities through the BSP with float32 arrays, computes the edge-cache prefix with
span masks, reads the engine limits once per audit and deals maps round-robin into chunks; 2,377 dev5
maps in about 12 s instead of about 40 s (busy host), byte-identical report. The earlier loops stay
selectable (`AMIWIND_HEAP_AUDIT_METHOD=python`). Both perf guard waivers are removed.

## BUILD-IMAGE-STAIR-WALK-SERIAL-36, BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36, BUILD-IMAGE-HASH-UNDERUSED-36 and BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36: the perf guard, 11 October 2026

[BUILD-PROFILER-NO-WASTE-ALARM-36](bugs/BUILD-PROFILER-NO-WASTE-ALARM-36.md) PERSISTING: the image stair walk ran on 1.7 of
24 cores in the v0.0.36-dev5 Vivec build after 11.6 cores in the dev4 full build, and nothing failed. The new perf guard
(`tools/perf_guard.py`, docs/BUILD_PROFILE.md "Perf guard") now fails a build whose parallel section turns serial or
slower for the same work. Seeded with the v0.0.35 and v0.0.36 runs it lists four sections, each registered and waived
until 14 October 2026: [BUILD-IMAGE-STAIR-WALK-SERIAL-36](bugs/BUILD-IMAGE-STAIR-WALK-SERIAL-36.md),
[BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36](bugs/BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36.md),
[BUILD-IMAGE-HASH-UNDERUSED-36](bugs/BUILD-IMAGE-HASH-UNDERUSED-36.md) and
[BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36](bugs/BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36.md); the CHIM heap gate on one core is
[BUILD-CHIM-STAGE-SERIAL-TAIL-36](bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md), PERSISTING.

## TRACKER-OCEAN-COUNTED-DONE-36, 11 October 2026

[TRACKER-OCEAN-COUNTED-DONE-36](bugs/TRACKER-OCEAN-COUNTED-DONE-36.md): the tracker counted the open-ocean cells as done although the
engine does not place the ocean chunk yet. Fixed and verified in the browser (11 October 2026): they are silver, on their own line and totals row, and no longer done.

- 2026-10-12 CHIMPORT-RETRY-LAVA-STALE-SOURCE-36: synthetic pre-lava resume regression reproduced. Candidate adds converter identity and preserves/recollects stale source stages; affected-cell rerun and native visible-lava acceptance remain pending.

## CHIM-LAVA-TERRAIN-AUDIT-37, 12 October 2026

CHIM-LAVA-TERRAIN-AUDIT-37: all 25 targeted lava retries now reach frame validation and fail. Standing-floor and liquid-coverage checks do not account for lava beds and lava warp faces. Registered open; source-stage repair remains separate, and no cells or visible lava are accepted.

CHIM-LAVA-TERRAIN-AUDIT-37: the first candidate passed gate 2220 but failed actual sloping-ground cells. A fifth synthetic regression reproduced its face-centroid assumption; per-sample exposed-surface and contents checks pass the regression and the first actual cell. The wider retry and final gate remain pending; the issue stays open.

CHIM-LAVA-TERRAIN-AUDIT-37 and CHIMPORT-RETRY-LAVA-STALE-SOURCE-36: source 95db832 converts all 25 affected cells (one reused, 24 computed, zero failures). Revised full gate and visible native/reference acceptance remain pending; no release is claimed.

CHIM-LAVA-TERRAIN-AUDIT-37: readback finds all 25 cells converted but their format audit still rejects CONTENTS_LAVA (-5). Process conversion counts are not acceptance. Registered the additional validator omission under the same ID and reproduced it synthetically; unsupported contents must remain refused.

CHIM-LAVA-TERRAIN-AUDIT-37 and CHIMPORT-RETRY-LAVA-STALE-SOURCE-36: individual receipt readback at source 73c8441 confirms 25 conversions and 25 passing format reports; 19 recorded audit passes and six hull-policy holds. Unmeasured checks, native/reference acceptance and release remain outstanding.

## BUILD-LAVA-PRESET-FIXTURE-38, 12 October 2026

BUILD-LAVA-PRESET-FIXTURE-38: full validation caught an omitted expected preset name in the new lava sandbox candidate. Corrected the inventory; retain failed evidence and rerun the gate before building a playtest.

## CHIM-COAST-OBJECTS-MISSING-36, 12 October 2026

CHIM-COAST-OBJECTS-MISSING-36: reconciled the 11 October maintainer report and roadmap into the canonical register and report under the same ID. Missing coast objects and Dwemer ruins remain unresolved; exact references and matched native reproduction are pending.

## BUILD-VERSION-EMULATOR-PRESETS-38: 12 October 2026

Full gate caught missing version-named presets before playtest delivery. Added both matching presets without changing hardware settings; validation pending.

## BUILD-LAVA-CORE-BOUNDS-38: 12 October 2026

The first lava sandbox image build rejected a 768-unit core in 2048-unit bounds. Changed to the established single-cell core size of 1024; native acceptance pending.

- BUILD-LAVA-CORE-BOUNDS-38 (12 October 2026): image retry exposed an incompatible terrain margin after the core repair. Adopted the existing single-cell CHIM region margin and added direct grid construction regression; native validation remains pending.

- BUILD-EMPTY-RESIDENT-POOL-38 (12 October 2026): lava scene packaging exposed zero-worker resident conversion. Added a lower bound and a regression for empty resident manifests; native validation pending.

- BUILD-EMPTY-ACTOR-GATE-38 (12 October 2026): lava exterior without NPC residents failed the image contact gate. Five original leveled-creature markers remain unconverted and individually recorded. Candidate limits not-applicable to resident contact without granting production actor acceptance; image and native verification pending.

- CHIM-LAVA-HUNK-GAP-38 (12 October 2026): lava MiniWind boots but leaves 2,004,064 bytes of hunk gap at first presentation; 93,088 bytes below the safety threshold. Cause and repair pending.

- CHIM-LAVA-HUNK-GAP-38 (12 October 2026): fresh voice-off control removes the 108,384-byte cold temporary peak; packaged character greeting size and existing sound-loader allocation match exactly. Production voice remains enabled; reserve repair pending.

CHIM-HULL-CHAIN-COST-33, 12 October 2026: scoped fire-fern checked-union candidate; 19 focused tests pass. Fifteen sampled variants reach depths 19-28; fresh cell audits and native collision remain pending. No hold cleared.

CHIM-LAVA-RECOVER-38 (2026-10-12): Native lava contact reduced health and showed the damage tint, but debug recovery found no clear town spawn. Observed once; cause and repair pending.

CHIM-LAVA-RECOVER-38 (2026-10-12): Recovery also fails at the initial spawn before lava exposure while unstuck succeeds. Candidate reuses checked CHIM arrival placement and primes/restores collision residency; compiled host regression passes, target verification pending.

CHIM-FERN-NCO-SOLID-38 (12 October 2026): Normal-movement comparison in cell (3,-1) identifies a solid fire fern where the original walks through. Both source fern models carry NCO markers; mesh export loses that intent although the sprite path honors it. Repair pending; six holds retained.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 (12 October 2026): Maintainer requested complete exterior-cell feature accounting. Authored merchant placement and deferred creature category verified; source-to-package and gameplay coverage pending. Rings 0-2 are exterior only; interiors may use BSP29, CHIM or both. No repair shipped.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 (2026-10-12): Corrected the mutable tracker loader to replace complete reference-accounting snapshots; obsolete light-deferral reasons no longer accumulate. Tracker suite: 92 tests, three skips, no failures/errors. Preserved rings 0-2 result readback: 588 rows, zero accounting discrepancies. Live regeneration and original-to-package feature reconciliation remain pending.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 (2026-10-12): Exact dev2 package readback of 51 map/harvest files accounts for 235 of 458 town-overlap references absent from the CHIM source manifest. Another 223 remain absent (183 statics, 26 containers, four doors, ten activators); native/OpenMW comparison is pending. No sealed package was changed.

CHIM-FERN-NCO-SOLID-38 â€” 2026-10-12: Candidate preserves authored NC/NCO collision metadata through scenery export and mesh preparation; 41 focused Docker tests passed. Fresh six-cell conversion and native walking remain pending; all six holds stay open. Delivered dev2 unchanged.

CHIM-FERN-NCO-SOLID-38 â€” 2026-10-12: All six fresh cell conversions pass offline audits; 24 fern variants have empty point/standing hulls with visible faces retained. Native cell (3,-1) passes the former obstruction; matched traversal and remaining native cell checks pending. Holds remain open.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 â€” 2026-10-12: Of 223 package-path omissions, 170 origins are outside town boxes and 53 inside. All 53 inside-box entries are absent from Seyda's source audit; frame overlap is not coverage. Per-reference ownership repair remains pending.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 â€” 2026-10-12: dev2 directory audit places all 223 unresolved references outside town handoff cores, in eight open-world rows. Town terrain-frame intersection does not establish reference coverage. No native repair acceptance.

CHIM-FERN-NCO-SOLID-38 â€” 2026-10-12: controlled walking crosses reference 163515 in cell (2,-2), adding a second scoped candidate route. Noclip-only attempts are explicitly excluded. Matched acceptance and four remaining cell routes stay pending; no hold cleared.

- 2026-10-12 CHIM-FERN-NCO-SOLID-38: Candidate walking crossings now cover four of six diagnostic cells. Two obstructed setups need alternative approaches; one remained in noclip and is explicitly excluded. Original-game comparisons and per-route evidence retained. All six holds remain open; not packaged in dev2.

- 2026-10-12 CHIM-FERN-NCO-SOLID-38: Alternative routes establish normal-walking crossings in the remaining two diagnostic cells. All six now have scoped route evidence with original-game comparisons; exact pose and package acceptance remain pending. Holds remain open.

- 2026-10-12 CI-HOSTDEPS-30: A candidate fern-marker fixture reintroduced PyFFI into the minimal host-parity test. Restored the mocked parser boundary while retaining real marker coverage in converter tests. Failed integration receipt retained; targeted host checks rerun.

- INTRO-CAMERA-GATING-38 (2026-10-12): Maintainer reports default Argonian visible through Tab and idle vanity before race selection. Record separate original camera unlock checks and coherent dbg aw hors 0 bypass state; reproduction and repair pending.

- BUILD-LAVA-COVERAGE-38 (2026-10-12): Maintainer report recorded as open, needs fixing. Full dev2 world omits the reported lava cells. No repaired-package acceptance.

- COMBAT-AMBIENT-SPEECH-GATING-38 (2026-10-12): Maintainer report recorded as open, needs fixing. Ambient greetings and subtitles interrupt combat. No repaired-package acceptance.

- BUILD-LAVA-COVERAGE-38 (2026-10-12): Source inspection finds no lava integration in the legacy regional terrain/WAD builder. Maintainer requires both legacy and CHIM support; adding CHIM areas alone is insufficient. Shared Quake lava conversion is the repair basis; implementation and native gates pending.

- PLAYER-TORCH-THIRDPERSON-38 (2026-10-12): Maintainer reports a regression in v0.0.38-dev2: equip a torch and switch to third person; illumination remains, but the torch model, torch animation and raised holding pose are absent. Open, needs fixing; native reproduction pending.

- PLAYER-READY-THIRDPERSON-38 (2026-10-12): Maintainer reports no fists-up pose or weapon unsheathing animation on the third-person player body. Exact weapon and race are not yet identified. Open, needs fixing; native reproduction pending.

- PLAYER-READY-WATER-MOVEMENT-38 (2026-10-12): Maintainer reports apparent water-walking with weapon/torch ready. Record original swimming and Water Walking override comparison; cause unknown.
- PLAYER-TORCH-THIRDPERSON-38 (2026-10-12): Maintainer adds lighting a torch underwater to this report; original equipment/water rules and native reproduction pending.

- WATER-GAMEPLAY-PARITY-38 (2026-10-12): Maintainer requests full surface/swimming/submerged gameplay comparison and CPU/memory prudence. Preserve approved underwater visuals. Screenshot binds underwater torch report to cell 12,6; reference/native matrix pending.

- BUILD-LAVA-COVERAGE-38 (2026-10-12): Legacy candidate lava is visible in target noclip diagnostic; spawn death reaches lava damage. Matched camera, scenery, controlled gameplay and package gates remain open.
- WATER-GAMEPLAY-PARITY-38 (2026-10-12): Maintainer reports missing drowning damage and requests original feedback, swimming/diving and lava-entry behavior; reuse existing physics and measure cost.
- ANIMKIT-COVERAGE-35 (2026-10-12): Maintainer reports walking poses while swimming/diving; include player and NPC companion animation coverage in original comparison.

- PLAYER-JUMP-THIRDPERSON-38 (2026-10-12): Maintainer reports missing third-person jump animation; diagnosis and native/original comparison pending.
- BUILD-LAVA-COVERAGE-38 (2026-10-12): Maintainer requests explicit lava-height/topomap verification. Original transformed surface, converted surface, terrain and native contact height remain separate gates.

- BUILD-LAVA-COVERAGE-38 (2026-10-12): Partial one-region elevation audit preserves all 16 source pool heights, but 47/208 exposed-LAND samples have solid contents instead of expected lava. Suspect geometry; capture and terrain reconciliation pending, no height acceptance.
- ANIMKIT-COVERAGE-35 (2026-10-12): Roadmap explicitly retains full player/NPC animation coverage, including swimming/diving and companion needs.

- BUILD-LAVA-COVERAGE-38 (2026-10-12): Exact generated terrain explains all 47 flagged samples; sea-level refinement does not protect elevated lava shores. Local refinement candidate and cost/native gates remain pending.

- BUILD-LAVA-COVERAGE-38 (2026-10-12): Local original-resolution terrain candidate passes49 focused tests,208 exposed and467 buried sample controls, and23-second baseline noclip run. Geometry and heap costs increased; full acceptance pending.
- LAND-HORIZON-GAPS-29 (2026-10-12): Maintainer supplies dev2 Grazelands horizon screenshots; retain as provisional related report pending current native diagnosis.

- BUILD-LAVA-COVERAGE-38 (2026-10-12): Corrected local terrain passes reference-aligned native capture and scoped contact check (health 78.0 to 58.7). Full scene, exact rate/boundary, coverage and package gates remain open.

- BUILD-LAVA-COVERAGE-38 (2026-10-12): Pinned cold/warm single-map cache control produces identical BSP and lava WAV hashes in fresh scenes. Whole-stage restore and final package audio remain pending.

- BUILD-DIAGNOSTIC-PALETTE-38 (2026-10-12): Flora guard caught mixed conversion/runtime palettes in isolated lava diagnostic. Rebuilt layers consistently and verified production pixel remap; fresh native check pending.

- CHIM-LAVA-HUNK-GAP-38 (2026-10-12 13:44 UTC): Addressed from v0.0.38-dev2: startup WAV scratch reserve integrated. Scoped voice-on native cold peak gap 2112448 bytes and warm2220640 exceed2097152; cold margin15296. No observed chunk failure or partial activation. Wider cell/performance and maintainer acceptance remain open.

- CHIM-LAVA-RECOVER-38 (2026-10-12 13:44 UTC): Addressed from v0.0.38-dev2: checked arrival/collision recovery integrated. Native initial and displaced recovery returned to369,688,149 with walking movement state3. Screenshot-state lag and scripted final noclip limit evidence; broader traversal and maintainer acceptance remain open.

- CHIM-FERN-NCO-SOLID-38 (2026-10-12 13:44 UTC): Addressed in v0.0.38-dev3 candidate, not delivered: authored NC/NCO collision policy retained; six fresh offline audits and one scoped normal-walking crossing in each affected cell, with original-game corridor comparisons. Exact pose/terrain parity, whole-cell and final-package acceptance remain open; six holds not cleared.

- CHIMPORT-RETRY-LAVA-STALE-SOURCE-36 (2026-10-12 13:44 UTC): Addressed in v0.0.38-dev1 candidate source: all25 formerly stale-source cells converted and passed format validation;19 passed measured offline audits and6 retained hull holds. Retry/source invalidation is repaired at the tested boundary; complete visible/gameplay coverage and maintainer acceptance remain open.

- CHIM-HULL-CHAIN-COST-33 (2026-10-12 13:44 UTC): Scoped fern work addressed in v0.0.38-dev3 candidate: six fresh offline cell audits and six selected native crossing routes now recorded. This does not resolve the original routed-canton trace-cost issue or establish native performance; broad issue and six cell holds remain open.

- BUILD-ACTOR-CONTACT-REGRESSION-38 (2026-10-12): Full dev3 actor gate reports116 blocked contacts versus116 grounded in dev2; build stopped before packaging. Cause under investigation.

- BUILD-ACTOR-CONTACT-REGRESSION-38 (2026-10-12): Empty point-hull root was interpreted as solid. Candidate writes an empty node; old-writer regression fails, candidate and 15 related tests pass. Full build/native verification pending.

- UI-KEY-HELP-STALE-38 (2026-10-12): Maintainer reports sparse key help and raw action labels; F10/grave handlers verified in source. Multi-column layout requested; repair pending.
- PLAYER-JUMP-THIRDPERSON-38 (2026-10-12): Maintainer repeats that third-person jumping has no visible jump animation; existing report retained, no duplicate or closure.

- WORLD-SLOPE-STUCK-38 (2026-10-12): Maintainer reports being stuck beside a steep terrain face; slope involvement is suggested, not established. Exact HUD positions recorded; no repair or closure.

- WORLD-SHORE-OPEN-GEOMETRY-38 (2026-10-12): Maintainer reports broken shoreline objects and missing textures. Two screenshots show broad open-looking sections, thin edges and background visible through the objects. Texture loss versus omitted faces, orientation or visibility is not yet isolated. Exact HUD positions recorded; no repair or closure.

WORLD-SHORE-OPEN-GEOMETRY-38, 12 October 2026: preserved additional maintainer shoreline poses and repeated-model hypothesis. Read-only 153-model rim diagnostic identifies a simplification lead; no production geometry changed and no native repair acceptance. Findings added to WHAT_ARE_ROCKS.md.

BUILD-LAVA-TERRAIN-BUDGET-38, 12 October 2026: full dev3 terrain stage stopped; seven outputs exceed 4 MiB. Preserved evidence, no limit bypass, no package delivery.


## BUILD-LAVA-TERRAIN-BUDGET-38, 12 October 2026: complete scenery scan

12 October whole-region follow-up: the next full build confirms cells (5,-2) and (5,-1) are selected as CHIM, but stops at BSP29 scenery vf1516, cell (7,-4). A complete scenery-only scan of 2,103 legacy regions finds two storage failures: vf1516 is 4,384,176 bytes with 17,986 faces and 22,671 clipnodes; vf1907, cell (11,-1), is 4,551,576 bytes with 16,395 faces and 15,690 clipnodes. Both exceed the 4,194,304-byte cap while passing the face and clipnode limits. Both belong to Molag Mar Region. The current selection contains 26 of its 123 exterior cells. Whole-region CHIM coverage, collision validation, later overlays and exact-package native acceptance remain pending.


## CHIM-MOLAG-MEMORY-38, 12 October 2026

Whole Molag Mar conversion exposed a CHIM heap failure in exterior cell (10,1): 11,970,016 B against 6,242,304 B. Model allocation breakdown recorded; original references retained. Spatial model-cut investigation pending, no budget waiver or native acceptance.

CHIM-MOLAG-MEMORY-38 / CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 — 2026-10-12: traced 139 original stronghold phase-controlled references and heavy compiled root variants in Tel Uvirith (10,1). Script predicates and topology recorded; no native fix or package acceptance.

CHIM-MOLAG-MEMORY-38 — 2026-10-12: original-game stage0/6 views and per-stage residency estimates recorded. Stage6 still exceeds the fixed budget by 1,395,808 bytes; repair remains pending.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 — 2026-10-12: Added conservative original-script visibility audit and six passing focused Docker regressions. Tel Uvirith (10,1): 139 conditional references; event-driven script remains unresolved. Runtime and packaging pending.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 — 2026-10-12: Whole Molag Mar script census covers 123 exterior cells and 15,162 references; 139 recognized predicates, 652 unresolved by the visibility classifier, 14,371 without attached scripts. Feature-path and runtime acceptance remain separate.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38 — 2026-10-12: Reconciled 310 deferred lava meshes against separate liquid counts in 24 Molag Mar cells, zero count mismatches. Steam/sign/banner geometry accounted separately from unverified sound/animation.

## 2026-10-12 — TOOLKIT-CULL-DIAGNOSTICS-38

TOOLKIT-CULL-DIAGNOSTICS-38: Known collision-only tree boxes have no render polygons. A global missing-polygon guard disabled every terrain culling check. Synthetic buried-face and diagnostic-box regression passes; full browser visual verification remains pending. Candidate only.

## 2026-10-12 — CHIM-TERRAIN-ROCK-EXEMPT-38

CHIM-TERRAIN-ROCK-EXEMPT-38: The experimental compiler excluded every placed mesh with a terrain_ filename prefix, conflating rock props with authoritative LAND. Isolated cell (10,1) compile passed; 59 collision models match baseline. Active peak saves 34,112 bytes and load peak saves 32,864 bytes. Native terrain-contact and matched original comparison remain pending. Candidate only.

## STAIRS-MOLAG-ACCESS-38, 13 October 2026

STAIRS-MOLAG-ACCESS-38: Maintainer reports a blocked walkway step and door stair approaches in the Tel Uvirith diagnostic playtest. Original screenshots retained privately. Added to staircase/access fixes; cause and matched original-game traversal remain unverified.

CHIM-MOLAG-MEMORY-38 / STAIRS-MOLAG-ACCESS-38 — 2026-10-13: Corrected the inspected cell (10,1) location to Tel Uvirith / Uvirith's Grave, Molag Amur. Earlier diagnostic names said Molag Mar incorrectly; IDs retained. Maintainer selected the completed stronghold state for the full-world local playtest. Dynamic quest construction remains unimplemented.

TREE-VIEW-FLOAT-38: 13 October 2026: registered the 12 October maintainer report and first screenshot pose; direction-dependent follow-up and native reproduction remain pending.

BUILD-LAVA-COVERAGE-38: 13 October 2026: reconciled 2 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

WATER-GAMEPLAY-PARITY-38: 13 October 2026: reconciled 1 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

PLAYER-TORCH-THIRDPERSON-38: 13 October 2026: reconciled 1 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

TREE-VIEW-FLOAT-38: 13 October 2026: reconciled 2 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

HORIZON-HOLES-31: 13 October 2026: reconciled 10 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

UI-KEY-HELP-STALE-38: 13 October 2026: reconciled 2 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

WORLD-SLOPE-STUCK-38: 13 October 2026: reconciled 4 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

WORLD-SHORE-OPEN-GEOMETRY-38: 13 October 2026: reconciled 25 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

CHIM-CELL-FEATURE-LIST-INCOMPLETE-38: 13 October 2026: reconciled 1 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

MESH-VIVEC-CAP-GAP-38: 13 October 2026: reconciled 2 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

CHIM-MOLAG-MEMORY-38: 13 October 2026: reconciled 1 maintainer screenshot(s) with evidence IDs and original hashes. Originals remain private; no fix acceptance implied.

- CHIM-FRAME-GROUND-TRACE-38 (13 October 2026): Full v0.0.38 base image from 026caf4 failed in the regional frame ground trace. Isolated all 359 frames: cell (6,-5), rcp6_m5 is the sole failing probe. Traversal guard exceeded; cause unknown, release blocked, no fix claimed.

- CHIM-FRAME-GROUND-TRACE-38 (13 October 2026): Reference 244841, ex_dae_ruin_01, has an acyclic 4,579-node point hull. Bounded offline frame-start sweeps pass all 359 exact-world probes with previous heights preserved within 3.98e-13; source proposal only, final image/native pending.

- CHIM-MOLAG-MEMORY-38 (13 October 2026): Regular-builder recipe omitted the prototype 1% default tolerance, restoring faces and exceeding the active budget by 226192 B. Restored the cell-scoped tolerance: full-margin active/load peaks 5794080/6108240 B now pass the unchanged 6242304 B limit. Five sprite placements pass isolated frame-map binding; final image/native/package gates remain pending.

- TOOLKIT-INCLUSION-PACKAGE-38 (13 October 2026): Gate 2406 refuses the new inclusion script; exact auxiliary-file and live-tracker copy entries added. Final gate/package pending.

- AW-RUN-NAME-LONG-REASON-36 (13 October 2026): Reopened for the stricter 100-character build-name limit; request-ID length repair did not cover it. Identical source/selection starts with a short-label retry. Payload unchanged; fix queued after current release.

- BUILD-SCRATCH-DISK-GROWTH-32 (13 October 2026): Full v0.0.38 image assembly paused by the existing storage guard at 692 GiB against its 689 GiB cap; 1,304/2,278 surface checks completed. Build preserved, no guard bypass or image/native completion claim.

- BUILD-IMAGE-CHIM-MAPS-SERIAL-36 (13 October 2026): Full v0.0.38 at c2c2050 completed image assembly but failed the regional-frame CPU guard: 360 frames,267 seconds,1.01/16 cores. Existing issue persists; outputs retained for native validation. Serial input preparation versus worker execution requires profiling.

- BUILD-LAVA-COVERAGE-38 (2026-10-13): Candidate full image includes all27 original lava-bearing CHIM regions and349 references; final HDF regional readback passes. Native vf1703 contact with noclip/god off reports lava contents and health100 to52.6. Original comparison shows lava; steam, terrain-detail and lighting differences remain. Final package delivery, sound and complete parity remain pending.

- BUILD-LAVA-TERRAIN-BUDGET-38 (2026-10-13): Full image assembly completed with the overflowing regions converted to CHIM; production map-memory gate passes. All360 regional CHIM cells pass final HDF frame/chunk readback. Release delivery remains pending; conversion is not complete gameplay acceptance.

- BUILD-LAVA-COVERAGE-38 (2026-10-13): Retained a final-image suspect-geometry capture at source XY (81472,21952); original comparison pending before visual acceptance.

- CHIM-LAVA-TERRAIN-SPIKES-38 (2026-10-13): Final-image raised-camera lava inspection differs from the calibrated original slope. Captures retained; cause and affected faces pending.

- CHIM-LAVA-TERRAIN-SPIKES-38 (2026-10-13): Found missing CHIM lava-detail integration. Shared triangulator candidate passes11 stitching tests; affected frame1800 to5454ground triangles. Memory and native gates pending.

- BUILD-SHADOWED-WORLD-MAPS-38 (13 October 2026): implemented candidate default pruning with explicit dependency retention. Exact HDF audit identifies 135 removable BSP maps (141,790,676 bytes); four focused Docker tests pass. Fresh assembly and native routing remain pending.

- BUILD-SHADOWED-WORLD-MAPS-38 (13 October 2026): full gate caught direct CHIM filename construction in the new helper. Reused the canonical map resolver and extension list; eleven map-helper tests pass. Stopped the superseded build and suite, retaining failure evidence.

## BUILD-SHADOWED-WORLD-MAPS-38, 13 October 2026

BUILD-SHADOWED-WORLD-MAPS-38: Full clean build reached the final heap check and failed on an orphan harvest catalogue. Map/corresponding-catalogue retirement is now coupled in the candidate; real catalogue validation regression added. Image and native gates pending.

## SAVE-TELEPORT-CHECKPOINT-38, 13 October 2026

SAVE-TELEPORT-CHECKPOINT-38: Maintainer reported successful teleport needs a safe destination checkpoint. Recorded separately for v0.0.39-dev1; cause, reproduction and repair pending.

## SAVE-LAVA-DEATH-LOOP-38, 13 October 2026

SAVE-LAVA-DEATH-LOOP-38: Maintainer reported lava fall can leave an autosave that reloads into repeated death. Recorded separately for v0.0.39-dev1; cause, reproduction and repair pending.

## UI-DEATH-DAMAGE-TINT-38, 13 October 2026

UI-DEATH-DAMAGE-TINT-38: Maintainer reported lava damage tint also colours the death menu and selection. Recorded separately for v0.0.39-dev1; cause, reproduction and repair pending.

## DOCS-CHIM-PROGRESS-STALE-38, 13 October 2026

DOCS-CHIM-PROGRESS-STALE-38: Maintainer reports the main README map is stale. Confirmed v0.0.36 image and caption remain. Refresh queued for v0.0.39-dev1; audit and packaged coverage remain separate.

## SAVE-LAVA-DEATH-LOOP-38, candidate 13 October 2026

SAVE-LAVA-DEATH-LOOP-38: v0.0.39-dev1 source repair and compiled regression recorded in the issue report; native acceptance pending.

## SAVE-TELEPORT-CHECKPOINT-38, candidate 13 October 2026

SAVE-TELEPORT-CHECKPOINT-38: v0.0.39-dev1 source repair and compiled regression recorded in the issue report; native acceptance pending.

## UI-DEATH-DAMAGE-TINT-38, candidate 13 October 2026

UI-DEATH-DAMAGE-TINT-38: v0.0.39-dev1 source repair and compiled regression recorded in the issue report; native acceptance pending.

- BUILD-DEV1-EMULATOR-PRESETS-39 (2026-10-13): Full dev1 suite caught the missing versioned emulator presets; added both matching preset candidates. Launcher and full-gate verification pending.
- BUILD-SHADOWED-WORLD-MAPS-38 (2026-10-13): Added the pre-conversion exterior ownership candidate: source LAND inventory, exact CHIM selection, town-core subtraction, shared terrain/scenery/flora checklist. Tests and exact-output comparison in progress; interiors unchanged.

- PLAYER-JUMP-THIRDPERSON-38 (2026-10-13): Found omitted body jump groups and missing ground-state selection. Candidate adds original takeoff/air hold and landing alias frames, preserving physics and model limits. Regression execution, converted-body budgets and matched native evidence pending.
- PLAYER-READY-THIRDPERSON-38 (2026-10-13): Source diagnosis confirms the body ignores QuakeC ready state and omits the original ready/equip/unequip groups. Repair remains open.
- PLAYER-TORCH-THIRDPERSON-38 (2026-10-13): Source diagnosis confirms third-person flame suppression and missing player equipment/pose. Guard torch attachment is a reuse candidate, but its idle-only kit frame contract needs adaptation. Repair remains open.

- DOCS-CHIM-PROGRESS-STALE-38 (2026-10-13): prepared a current reference-derived README map and coherent coverage guide; corrected historical plan/lava/lighting figures. Audit, native and package evidence remain separate; delivery pending.

- PLAYER-READY-THIRDPERSON-38 (2026-10-13): prepared original bare-hand ready idle/walk/run/jump selection from existing hand state, female fallback and mid-air stance continuity. Reuses alias frame playback; unchanged file budget. Equip/lower, punches, weapons and torch remain separate. Added regression sources; compilation, body bakes, target memory and native comparison pending. Issue remains open.
- PLAYER-READY-THIRDPERSON-38 (2026-10-13): extracted the guard's offline bone overlay for future upper-body equip/lower over moving legs, preserving female boundary transforms and guard timing. Added layer and conversion-fingerprint regression sources. Player transition frame planning is unfinished; tests, old/new guard asset comparison and native checks remain pending. No new transition is enabled in the game.
- PLAYER-READY-THIRDPERSON-38 (2026-10-13): connected a source candidate for bare-hand draw/lower using a budgeted grid of arm and movement poses, the QuakeC action clock, body-only layout validation and retained normal/ready gait phase. Frame plan requests253/minimum93; no raised alias budget. Regression sources prepared, not run. All20 body bakes, Amiga compile, native comparison and cost measurement remain pending; punches/weapons/torch still open.

- SAVE-TELEPORT-CHECKPOINT-38 (2026-10-13): RC1 source integrates settled-arrival autosaving and retention of the prior safe checkpoint. Compiled save regressions and Amiga compilation passed; exact RC1 character teleport/save/reload acceptance pending. Not shipped.
- SAVE-LAVA-DEATH-LOOP-38 (2026-10-13): RC1 source defers automatic saves during falls, damaging/deep liquid, combat, loading and modal menus. Compiled save regressions passed. Existing unsafe saves are not rewritten; exact RC1 lava/fall/reload native checks pending. Not shipped.
- UI-DEATH-DAMAGE-TINT-38 (2026-10-13): RC1 source requests an untinted death-prompt palette and freezes world clocks after the death animation. Palette and host/client regressions and Amiga compilation passed; exact native death-choice visual acceptance pending. Not shipped.
- PLAYER-JUMP-THIRDPERSON-38 (2026-10-13): Jump takeoff, airborne and landing groups and movement-state selection are integrated in RC1 source. Amiga compilation passed. All-appearance bake/readback and matched native/reference checks pending; not shipped.
- PLAYER-READY-THIRDPERSON-38 (2026-10-13): RC1 source integrates bare-hand ready idle/walk/run and offline upper-body draw/lower over moving legs, using the action clock and retained gait phase. Amiga compilation passed. All-appearance model readback, guard asset identity, native/reference checks and performance pending; complete punches/weapons/torch remain separate. Not shipped.
- BUILD-PLAYER-BODY-BUDGET-FALLBACK-39 (2026-10-13): Bounded mesh retry within unchanged alias/frame budgets is integrated in RC1 source. All 20 actual race/sex bakes, readbacks and native memory checks remain pending. Not shipped.
- AUDIO-STOP-CHANNEL-RANGE-39 (2026-10-13): RC1 integrates cancellation over the allocator dynamic interval (4..11), retaining entity/channel matching and music controls. Amiga compilation passed. Exact RC1 native listening remains pending; combat greeting/subtitle policy is separate. Not shipped.
- UI-KEY-HELP-STALE-38 (2026-10-13): RC1 integrates current labels, reserved-shortcut contexts, font/viewport-aware page capacity and live paging clamps. Amiga compilation passed. Exact native readability and reported blank-frame reproduction pending; not shipped.
- BUILD-SHADOWED-WORLD-MAPS-38 (2026-10-13): RC1 source integrates the pre-conversion ownership checklist and excludes the identified 135 redundant town-owned BSP cores while retaining partial cores and dependencies. Old v0.0.38 correction delivery cancelled. RC1 full image, ownership/readback, routing and measured archive size pending; not shipped.

- BUILD-WORLD-PACK-RETIRED-38 (2026-10-13): Full RC1 conversion completed, but the early image disk-layout preflight still expected the deliberately absent vf0302 BSP. Extended the validated ownership handoff to that preflight, retaining strict final owner-frame and unexpected-missing-map checks. Thirty focused Docker regressions pass; repaired image and native acceptance remain pending.
- BUILD-WORLD-FINGERPRINT-RETIRED-38 (2026-10-13): RC1 integrates validated retirement and never-built omissions into content fingerprinting without allowing undeclared missing maps. Prior focused regression passed; full RC1 image/readback and native routing pending. Not shipped.
- BUILD-WORLD-PACK-RETIRED-38 (2026-10-13): RC1 integrates the same validated omission list into world-disk packing after fingerprinting. Exact full-image and package readback and native routing remain pending. Not shipped.
- DOCS-CHIM-PROGRESS-STALE-38 (2026-10-13): RC1 source contains the 12 October reference-derived map, 1265/1292 conversion/audit milestone and separate 360-cell v0.0.38 package record. Added the generated image gitignore exception and restored the totals label after first RC1 preflight. RC1 package coverage and public delivery remain pending.
- RELEASE-WORKING-VERSION-ISOLATION-39 (2026-10-13): Per-release version record support is prepared in the publication wrapper. Four isolated wrapper regression checks passed; RC1 exact publication guard/finalization still required. Public publishing remains separate from private delivery.
- TEST-RC1-INTEGRATION-CONTRACTS-39 (2026-10-13): The first exact RC1 suite at 88aba74 fails four image-wiring checks and the guard cache-key assertion. Follow the wrapper while retaining worker-count forwarding and pass-order assertions. Check that the guard reaches module import code, then mutate the real shared layer in a temporary fixture and require a changed worker key. The production cache algorithm is unchanged. Exact-source rerun pending.
- DOCS-RC1-PREFLIGHT-39 (2026-10-13): RC1 preflight rejects the new generated progress PNG; suite checks reject its missing totals label and stale contents lists. Add only the generated map image exception, restore the totals label without changing coverage counts, and regenerate affected document contents. Maintainer screenshots remain private. Exact-source rerun pending.

## BUILD-CHECKLIST-JSON-CELLS-39 and RELEASE-PATCH-TARGET-VERSION-39, 13 October 2026

BUILD-CHECKLIST-JSON-CELLS-39: the full RC1 build exposed a serialized cell-list
failure before scenery conversion. A disk-round-trip regression reproduces it;
tuple normalization passes all 21 world-manifest tests while altered ownership
still fails. Complete image and target acceptance remain pending.

RELEASE-PATCH-TARGET-VERSION-39: the Linux kit's successful dry run explicitly
remained unsuitable for publication because the baseline omitted its target
version. Metadata is corrected; a newly pinned strict kit is still required.

## DOCS-CHANGELOG-STALE-39 and DOCS-RC1-PREFLIGHT-39, 13 October 2026

DOCS-CHANGELOG-STALE-39: maintainer requested a maintained changelog and mandatory
synchronization with bug tracking, CHIM coverage and release notes. Backfilled
v0.0.36-38 and recorded RC1 implemented work, findings and pending acceptance.

DOCS-RC1-PREFLIGHT-39: exported-source validation caught two new issue reports
missing from the allowlist. Added their paths with the changelog report and
strengthened the workflow to verify actual exported records before freezing.

- PLAYER-TORCH-THIRDPERSON-38 (2026-10-13, RC2 follow-up): Still present in RC1: F draws the fists in third person, but V after F lights the world without a visible third-person torch, holding pose or torch animation. World lighting and fist readiness do not establish carried-torch completion. Source implementation and native acceptance remain pending.
- WATER-GAMEPLAY-PARITY-38 (2026-10-13, RC2 follow-up): Still incomplete in RC1: the maintainer reports missing swimming AND diving animation in both first-person and third-person views, with reported third-person sinking. Missing third-person swim groups are source-confirmed; each view/action presentation, physical behavior, breath/drowning and matched original behavior remain open.
- PLAYER-MOVEMENT-FRAME-SKIP-39 (2026-10-13, RC2 follow-up): Open RC1 repeat and RC2 blocker: fast movement appears to use only a couple of poses rather than the earlier rapid foot animation; the maintainer explicitly identifies v0.0.38 as the last known good comparison. Actual frame-fitter replay reduces normal Nord/Khajiit walk/run to two/two samples. A fuller-gait source candidate is being prepared; speed-linked playback, baked pose coverage and exact native/package verification remain pending.
- PLAYER-MOVEMENT-STATS-PARITY-39 (2026-10-13, RC2 follow-up): Open maintainer report: default walking/running feels overpowered. Faithful gameplay should use the original Speed, Athletics, encumbrance and running-fatigue formulas. The latest clarification retains convenient fast, less strict debug builds; no immediate replacement of the debug preset or movement repair is claimed.
- DBG-ENTITY-INSPECT-39 (2026-10-13, RC2 follow-up): Requested during RC1 appearance investigation. Source candidate adds explicit dbg hud on/off click-to-pin entity/reference/model/position inspection; target compilation, candidate native checks and delivery remain pending. Ordinary overlay controls retain their previous combat behavior.
- NPC-ORDINATOR-APPEARANCE-39 (2026-10-13, RC2 follow-up): Open RC1 appearance/target identity investigation. All four original Hlaalu Waistworks Ordinators are male Dark Elves with Indoril helmets and armor; exact packaged vhi015 references, labels and model mappings agree. Nearby Eloroth is a male Wood Elf. The actor in the maintainer screenshot is not bound to a raw reference/model; the foreground Eloroth explanation remains a hypothesis, not a finding or repair.
- NPC-NO-RUN-ANIM-35 (2026-10-13, RC2 follow-up): RC1 recurrence reproduced after same-map reload: actual packaged Seyda run/attack mover assets exist, but mover registration is lost when server precaches reset while the world-model pointer is reused. Source candidate resets animation scene caches at each server spawn and warns on declared mover fallback. Focused7 animation,21 combat and42 NPC checks pass; new target/native/package verification and maintainer acceptance remain pending.
- ANIMKIT-COVERAGE-35 (2026-10-13, RC2 follow-up): RC1 recurrence reproduced after same-map reload: actual packaged Seyda run/attack mover assets exist, but mover registration is lost when server precaches reset while the world-model pointer is reused. Source candidate resets animation scene caches at each server spawn and warns on declared mover fallback. Focused7 animation,21 combat and42 NPC checks pass; new target/native/package verification and maintainer acceptance remain pending.
- NPC-SPEAR-ATTACK-REGRESSION-39 (2026-10-13, RC2 follow-up): Same-map mover activation and authored guard spear stance are separate checks. Runtime reset is a source candidate; exact spear animation remains open.
- DBG-ENTITY-INSPECT-39 (2026-10-13): Seventeen focused automated checks pass, including real C identity/occlusion/click/reset/viewport integration. Target/native/package verification remains pending.
- PLAYER-PUNCH-THIRDPERSON-39 (2026-10-13, RC2 source candidate): Authored punch-clock/layer source candidate and two male body bakes/readbacks pass; 83 affected checks pass. Target/native/all-appearance/package acceptance pending; preserve approved RC1 ready posture.
- PLAYER-BODY-LEG-SHAPE-39 (2026-10-13, RC2 source candidate): Combined-section fallback guard and two male body bakes/readbacks pass; 83 affected checks pass. Budget-480 proxy and exact old/new measurements are diagnostics, not an appearance fix; native acceptance pending.
- PLAYER-MOVEMENT-FRAME-SKIP-39 (2026-10-13, RC2 source candidate): Compact source action grids retain actual isolated normal/ready walk8/run6 plus punch; 83 affected checks pass. Maintainer-reported v0.0.38 control, native speed-linked smoothness and complete package checks pending.
- PLAYER-READY-THIRDPERSON-38 (2026-10-13): The maintainer explicitly confirms that the RC1 fight-ready posture is good and must be preserved. This is a scoped posture control; torch holding, leg shape, fast gait and punch acceptance remain separate.
- DBG-ENTITY-INSPECT-39 (2026-10-13): First RC2 target compile rejects implicit AW_CharacterActive declaration. Source includes existing aw_character.h; exact corrected-source retry pending. Prior17 focused checks do not establish target/native/package acceptance.
- DBG-ENTITY-INSPECT-39 (2026-10-13, scoped RC2 evidence): Corrected target compile passes; native HUD pins background Ord201385 through the foreground actor because whole-model bounds include other poses. Visible identity selection remains open.
- NPC-ORDINATOR-APPEARANCE-39 (2026-10-13, scoped RC2 evidence): Native maintainer-pose view repeats foreground elf/background armored actor; coarse bounds choose background Ord201385. Original/package identities agree; foreground reference remains unbound.
- NPC-NO-RUN-ANIM-35 (2026-10-13, scoped RC2 evidence): Scoped native reload now activates full guard mover and changing chase/attack poses with health damage. Authored spear, other NPCs, complete RC2 package and maintainer acceptance pending.
- ANIMKIT-COVERAGE-35 (2026-10-13, scoped RC2 evidence): Scoped native reload now activates full guard mover and changing chase/attack poses with health damage. Authored spear, other NPCs, complete RC2 package and maintainer acceptance pending.
- BUILD-PLAYER-BODY-BUDGET-FALLBACK-39 (2026-10-13, scoped RC2 evidence): RC2 all-body run fails Breton female:480 exceeds alias budget;384/320/256 trip leg guard. Two controls plus Argonian male/female and Breton male read back; remaining set incomplete.
- CHIM-SEYDA-HUNK-GAP-33 (2026-10-13, scoped repeat/documentation correction): Scoped corrected-engine diagnostic repeats existing gap warnings: initial gap2091392B; post-reload stable2113264B but first-presented peak1586032B. No new regression or memory acceptance.
- DEBUG-MAP-SAVE-VALIDATION-32 (2026-10-13, scoped repeat/documentation correction): Scoped corrected-engine diagnostic map-load vhi015 repeats save validation refusal; previous saves retained. No normal-transition/save acceptance or new regression claimed.
- PLAYER-MOVEMENT-STATS-PARITY-39 (2026-10-13, scoped repeat/documentation correction): Suite catalogue coverage rejects roadmap wording that resembles an implemented maxstats command. Corrected to explicitly proposed option; no command or godmode-speed implementation added.
- DBG-ENTITY-INSPECT-39 (2026-10-13): Current client-frame box/pose source candidate passes the real C UBSan death-envelope/stale-client/cache/pitch-scale and prior control regression. Corrected selector target/native/package acceptance pending.
- PLAYER-MOVEMENT-STATS-PARITY-39 (2026-10-13): One affected catalogue-doc check passes after roadmap maxstats wording becomes explicitly proposed. Failed full suite retained; no catalogue handler, speed or fatigue implementation added.
- PLAYER-TORCH-THIRDPERSON-38 (2026-10-13, original-key/source finding): Original human/beast and common first-person torch groups confirmed. Player companion/pose remains unwired; guard overlay has layout limits. No torch/native acceptance.
- WATER-GAMEPLAY-PARITY-38 (2026-10-13, original-key/source finding): Original third-person swim families confirmed; no dedicated dive key in16 base NIF/KF members. First-person visuals need state/camera/fallback parity; local0.52 source is not native0.48 acceptance.
- ANIMKIT-COVERAGE-35 (2026-10-13, original-key/source finding): Original group availability confirmed; full NPC mapping includes swim/idle while player move profile excludes them. This source finding does not implement or accept player water/torch.
- DBG-ENTITY-INSPECT-39 (2026-10-13, original-key/source finding): Latest source explicitly labels server runtime/position separate from rendered client selection. One actual C UBSan check passes differing-frame assertion; corrected target/native acceptance pending.
- BUILD-PLAYER-BODY-BUDGET-FALLBACK-39 (2026-10-13, corrected RC2 body-file evidence): RC2 body checks pass 20/20: 16 prior pairs reused, four female models newly baked below 512 KiB. Tail excluded from leg guard; 33 checks pass. Native/package acceptance pending.
- PLAYER-BODY-LEG-SHAPE-39 (2026-10-13, corrected RC2 body-file evidence): All 20 bodies pass binary checks. Section audits flag possible knee/calf gaps, mostly simplification. Metrics do not prove visible holes; native/original and maintainer acceptance pending.
- PLAYER-PUNCH-THIRDPERSON-39 (2026-10-13, corrected RC2 body-file evidence): All 20 body pairs pass binary checks with gait/punch declarations; 33 guard checks pass, earlier 83 retained. Visible punch, seams and native/package/maintainer acceptance pending.
- PLAYER-MOVEMENT-FRAME-SKIP-39 (2026-10-13, corrected RC2 body-file evidence): All 20 body pairs pass binary checks; prior bake failure retained. Full 8/6 gait declarations do not establish speed-linked smoothness or native/package/maintainer acceptance.
- RELEASE-PATCH-TARGET-VERSION-39 (2026-10-13, RC2 metadata preparation): RC2 metadata prepared: target version matches VERSION, published baseline retained and known issues use canonical IDs. Pre-pin completion only; exact guard/export/strict kit still pending.
- TRACKER-REGISTER-SIZE-36 (2026-10-13, RC2 size recurrence): RC2 suite catches 896,776B above 85% warning. Canonical live JSON now stores one complete issue per line, without fact/history loss or archive/guard changes. Focused checks pending.
- PLAYER-PUNCH-THIRDPERSON-39 (2026-10-13, scoped candidate native observation): Scoped Nord male/Orc female candidate footage shows torso/arm punch motion and ready movement. Display only: damage, LMB, all appearances, matched A/B, seams, package/maintainer acceptance pending.
- TRACKER-REGISTER-SIZE-36 (2026-10-13, focused validation): 56 tracker/export checks pass with exact source ZIP readback; lossless compact JSON and unchanged archive/guard verified. Failed full suite retained; fresh integrated pin/gates pending.
- PLAYER-TORCH-THIRDPERSON-38 (2026-10-13, maintainer RC2 scope override): Maintainer now requires third-person torch holding in RC2. Source integration IN PROGRESS; exact bake/tests/native/package/maintainer acceptance pending. Swimming scope unchanged.
- PLAYER-TORCH-THIRDPERSON-38 (2026-10-13, implemented RC2 source candidate): RC2 torch source candidate implemented. All 20 companion bake/readbacks, 35 converter and 36 runtime checks pass. Exact target/native, matched original, package/maintainer acceptance pending.
- WATER-GAMEPLAY-PARITY-38 (2026-10-13, maintainer RC2 scope override): Maintainer requires reported swimming/diving in RC2. Both-view original 0.48 reference and source integration in progress; original clip inventory is separate. Native/package/maintainer acceptance pending.
- NPC-SPEAR-ATTACK-REGRESSION-39 (2026-10-14, RC2): Use original two-hand-wide attack/hit poses for spear-equipped residents; preserve mover frame counts and damage. 43 focused checks pass. Target asset/native/package verification pending.
- PLAYER-PUNCH-THIRDPERSON-39 (14 October 2026, post-pin RC2): The independently extracted RC2 package shows Nord third-person torso/arm punch changes in an unaltered native clip. Post-exit readback preserves exact assets. Console attack control does not prove physical LMB input or damage; all appearances, matched original comparison, seams and maintainer acceptance remain pending.
- PLAYER-TORCH-THIRDPERSON-38 (14 October 2026, post-pin RC2): The independently extracted RC2 package shows a raised left arm and carried torch on Nord, then torch-off and water/land model selection. Full disk readback verifies all 20 body/held-torch companions. Scoped native evidence is not all-appearance or matched-original visual acceptance; maintainer acceptance remains pending.
- WATER-GAMEPLAY-PARITY-38 (14 October 2026, post-pin RC2): The extracted RC2 package holds origin (704, -320, -25) for a four-second no-input water control after noclip is disabled. Pitch45 with forward movement descends to origin (832.7, -320, -153.7) at waterlevel 3 and shows changing swim poses. Both readied first-person fists remain visible at default horizontal FOV 90/viewsize 100. Actual OpenMW0.48 reference holds depth and retains first-person fists; no dedicated first-person stroke or blanket body pitch is established. Broader drowning, fatigue, combat, all appearances and maintainer acceptance remain pending.
- PLAYER-READY-WATER-MOVEMENT-38 (14 October 2026, post-pin RC2): RC2 package native water/land selection and changing swim poses are verified in the scoped Nord control, with both default-camera first-person fists visible. This does not close the historical water-walking report or establish all states, appearances and original behavior parity.
- BUILD-PLAYER-BODY-BUDGET-FALLBACK-39 (14 October 2026, post-pin RC2): Full RC2 disk readback and independent package extraction verify all 20 declared base bodies and140 torch/held/swim companion files within the unchanged 512 KiB model cap. Exact played readback preserves186 engine/metadata/body files. Binary coverage does not certify all 20 visual appearances, native memory, leg seams or maintainer acceptance.
- PLAYER-BODY-LEG-SHAPE-39 (14 October 2026, post-pin RC2): All 20 body and companion sets are present in the exact RC2 package. The scoped Nord package footage does not establish knee/calf continuity or fix the maintainer-reported thin legs. Prior section metrics and possible simplification gaps remain diagnostic; matched original/v0.0.38, all-appearance and maintainer acceptance remain pending.
- PLAYER-MOVEMENT-FRAME-SKIP-39 (14 October 2026, post-pin RC2): Full gait samples are present in the read-back RC2 body assets, but package presence and scoped punch/water footage do not establish normal-speed fast-gait timing, original speed-linked playback or maintainer acceptance. Preserve the maintainer-reported v0.0.38 comparison and good RC1 ready posture.
- NPC-SPEAR-ATTACK-REGRESSION-39 (14 October 2026, post-pin RC2): Exact-source 690 staged diagnostic footage shows guard pursuit and changing strike poses, with hits reducing health 995 to 899 then 882.3. Post-exit readback verifies 21 movers plus engine, bootcheck and catalogue (24 files). This supports scoped chase/attack and preserved damage, not damage balance or complete spear attachment alignment. Final RC2 disk readback separately verifies the 21 equipped-resident files and palette binding; it does not turn the staged diagnostic into final-package guard native acceptance. Matched OpenMW and maintainer acceptance remain pending.
- NPC-NO-RUN-ANIM-35 (14 October 2026, post-pin RC2): Exact-source 690 staged diagnostic footage shows guard pursuit and multiple strike poses, with health 995 to 899 then 882.3. Guest exit reaches AmigaDOS and 24 played-file hashes pass. This extends scoped mover evidence after the same-map reset; all-NPC, matched original, final-package guard and maintainer acceptance remain separate.
- ANIMKIT-COVERAGE-35 (14 October 2026, post-pin RC2): Exact RC2 package readback covers all 20 player appearances and their torch/held/swim companions. Scoped Nord package native footage verifies punch changes, carried torch, swim poses and underwater first-person fists. Original group availability and binary declarations still do not establish every actor/equipment animation or all-appearance acceptance.
- CHIM-SEYDA-HUNK-GAP-33 (14 October 2026, post-pin RC2): Exact RC2 package native inspection repeats startup hunk-reserve warnings and zone-full chunks 100/107 retries after water and land return. A playable scene and successful guest exit do not prove complete chunk recovery, memory headroom or performance acceptance. This remains an existing open finding.
- ENGINE-SYNC-IO-MAIN-LOOP-36 (14 October 2026, post-pin RC2): Exact RC2 package native inspection repeats zone-full chunks 100/107 retries after water and land return. Scoped gameplay and successful AmigaDOS exit do not clear blocking streaming, heavy loading, memory/performance or all-cell traversal issues.
- DOCS-CHIM-PROGRESS-STALE-38 (14 October 2026, post-pin RC2): RC2 full disk readback and independent extraction verify360 whole regional CHIM cells; six partial town overlaps remain excluded. The exact inspection package and matching source artifacts were finalized at 2026-10-13T22:15:44Z. Conversion/audit/native-cell coverage and maintainer acceptance are unchanged. Historical empty RC1 plan remains incorrectly selected as next by the existing selector; no supported historical flag permits a truthful metadata-only correction.

## DOCS-RELEASE-EVIDENCE-SCOPE-39 - final source reconciliation, 14 October 2026

14 October 2026: Final v0.0.39 source packaging authorized from delivered RC2. README and release notes distinguish RC2 checks from final-source validation. No individual issue acceptance, new cell coverage or final artifact shipment is inferred.

DOCS-CHIM-PROGRESS-STALE-38: final source retains the exact RC2 coverage and remaining tracker display limitation.

## Development audit, 14 October 2026

PLAYER-MOVEMENT-FRAME-SKIP-39: sealedRC2 actual vertices/declarations show8walk/
6run poses in all20normal bodies and matching ready gait. RC1's2/2action grids
were restored in RC2; v0.0.38 speed/root-clock/clamp unchanged. LowFPS skipping
is a hypothesis, not a new diagnosed regression. Matched normal-speed/maintainer
gait acceptance pending.

PLAYER-READY-MOVEMENT-39: native physical characterchange opens pier, changes
Nordmale→Orcfemale/head/hair, confirms gameplay body and reopens;2checks,
post-exit engine readback and observed DOS exit pass. Full-body chosen head/hair
remains separate. Orc ready A/S moves; maintainer immobility not reproduced/closed.

COMBAT-BLOCKING-36: earlier Orc test-sheet physical RMB guards, body25/104,
GuardHUD but no first/third shield. State/frame alone is not visual acceptance.

WATER-GAMEPLAY-PARITY-38: exactRC2 Nord/Seyda WALK3/noclipoff/water3 at
(704,-320,-25) holds6s; down-pitch forward changes depth then velocity/depth
settle. Shore entry holds6s; swim companion loads without warning. Upright look,
maintainer sinking and original parity unresolved; failed Vivec attempt is not
Vivec acceptance.


## PLAYER-READY-MOVEMENT-39: input diagnostic, 14 October 2026

v0.0.40-dev1 source adds gate/latch/movement readout to the existing hands
diagnostic. No movement repair or maintainer-case reproduction is claimed.
[Report](bugs/PLAYER-READY-MOVEMENT-39.md).

## PLAYER-READY-MOVEMENT-39: disabled-combat lock, 14 October 2026

v0.0.40-dev1: disabled combat no longer retains a knocked-player input lock
whose recovery cannot advance. Actual adapter regression fails before and
passes after; enabled knockdown still locks. Maintainer-case cause and native
verification remain pending.
[Report](bugs/PLAYER-READY-MOVEMENT-39.md).

- COMBAT-BLOCKING-36 (14 October 2026, v0.0.40-dev1): Inventory-backed actual shield identity now feeds the first-person block bridge and per-frame third-person alias attachments. Real equip/drop refreshes combat gear without resetting vitals; weapon/shield condition persists. Focused host checks and selected source asset readback pass. Integrated build, native visual alignment and maintainer-case acceptance remain pending; original unarmed/two-handed block restrictions remain.

- COMBAT-BLOCKING-36 (14 October 2026): the first combined target compile linked but failed the warning-free gate for adjacent clamp statements. Split the statements without changing their conditions; repeat the affected target gate on a new immutable candidate. No native acceptance claimed.

- GATE-SUITE-WRITABLE-32 — 14 October 2026, v0.0.40-dev1: read-only snapshot modes propagated into temporary fixtures and caused write errors in the full integration suite. Preserve the failed evidence; validate a separate normal-permission hash-matched test copy. Other assertion failures remain open. [Report](bugs/GATE-SUITE-WRITABLE-32.md).

- GATE-SUITE-WRITABLE-32 — 14 October 2026: the five affected modules now pass 92 tests on a writable copy matching all 2,889 frozen source hashes, which remain unchanged after testing. The full corrected candidate still requires validation.

## CHIM-WINDOW-MOUNT-CROSS-CELL-33: neighbouring source wall candidate, 14 October 2026

CHIM-WINDOW-MOUNT-CROSS-CELL-33: v0.0.40-dev1 prepares a lazy source-only supporting-wall lookup after local mounting fails. Owned Pelagiad geometry mounts all eight windows; four use two houses in neighbouring cells. The same 301 selected scenery references remain, with no neighbouring runtime placements added. Twelve focused checks pass, including retained source dependency evidence through the real cell pool. Full cell conversion, original/native facade and traversal comparison, packaging and maintainer acceptance remain pending. Three cells remain unconverted; no coverage promotion is made. [Report](bugs/CHIM-WINDOW-MOUNT-CROSS-CELL-33.md).

## BUILD-VERSION-EMULATOR-PRESETS-38: v0.0.40-dev1 recurrence, 14 October 2026

VERSION advanced without its two emulator presets. Real config lookup reproduced the omission. Matching FS-UAE/WinUAE files now retain the v0.0.39 machine/input settings with version labels changed and both files source-allowlisted. All 73 focused existing tests passed; integrated full gate and package acceptance remain pending.

## TEST-NATIVE-TMPDIR-32: testbox relative drive, 14 October 2026

A long host temp path exposed the testbox fixture's incorrect assumption that an absolute host prefix fits the engine's bounded AWTEST drive reader. A focused native run reproduced the assertion. The fixture now uses its private cwd, deliberately exercises a long host path and asserts overlong-drive refusal. Engine guards remain unchanged; the UBSan native regression and focused 73-test batch passed. Integrated full gate pending.

## INVENTORY-CATALOG-LOOKUP-40: native catalogue failure, 14 October 2026

[INVENTORY-CATALOG-LOOKUP-40](bugs/INVENTORY-CATALOG-LOOKUP-40.md): dev1 native
rawIDs/noicons and real sword/shield grants refuse. Equality-only Q_strcasecmp
breaks binary search/name sort. Real-common old controls fail; local ordered
comparator passes2checks. Target/native pending; refused grants invalidate
equipped-shield conclusions.

BUILD-DIAGNOSTIC-PALETTE-38 — 15 October 2026, v0.0.40-dev2: optional scene palette input preserves indexed dependencies when source coverage expands; six focused checks pass. Default sampling is unchanged; conversion/native/package checks remain pending.

TEST-TOWN-BOUNDS-40 — 15 October 2026, v0.0.40-dev2: full-suite town integration exposed eight stale recovery-fixture errors and one obsolete coordinate-audit entry. Source records are repaired and all19 affected checks pass; renewed full gate remains pending. No guards weakened.

CHIM-SEYDA-EXPANDED-STAIRS-40: 15 October 2026, v0.0.40-dev2: all 15 original start failures reproduce. Six centre ascents from supported free starts still stop on a same-stair 57.50-degree support face. Independent descent also stops, while top/bottom idle controls stay stable. Start sampling alone does not clear the route. Original authored-surface comparison and matched native traversal remain pending; no repair or shipment. [Report](bugs/CHIM-SEYDA-EXPANDED-STAIRS-40.md).

COLLISION-STAIR-SLOPE-32 and CHIM-SEYDA-EXPANDED-STAIRS-40: 15 October 2026, v0.0.40-dev2: strict authored collision for the two measured Imperial wall stairs passes all 15 prior probes in the bounded producer diagnostic using unchanged lateral sampling; six supported ascents and descents pass, visuals preserved. Fresh source/world and native gates remain pending. [Collision repair](bugs/COLLISION-STAIR-SLOPE-32.md).

CHIM-TRACKER-APRON-40: 15 October 2026, v0.0.40-dev2: direct Seyda source metadata now validates original audit scope/counts/identities. Fourteen focused tests and original-data readback give 16 core cells, 2982 core references, 103 dependencies and 1695 non-static/deferred references, with original types retained. No coverage or gameplay acceptance promoted. [Report](bugs/CHIM-TRACKER-APRON-40.md).

BUILD-CHIM-SOURCE-REPEAT-41: 17 October 2026, v0.0.42-dev1: the v0.0.41-dev5 CHIM stage ran 723 source stages for 24,585 s: each area parsed the whole master again and read the same models up to a dozen times. Repaired in source (B5): per-process memory in the CHIM stage; 160 frames and three towns byte-identical, CPU seconds 15,855 -> 8,626.

BUILD-CHIM-WORLD-SERIAL-TAIL-41: 17 October 2026, v0.0.42-dev1: after the region frames dev5's world conversion ran the towns one after another and the visibility rows frame by frame, about 7.5 minutes on 1 to 5 of 24 cores. Repaired in source (B5): towns beside the region frames, one-cell frames' rows whole on the workers, timed phases; byte-identical.

BUILD-REUSE-APPLY-SERIAL-41: 17 October 2026, v0.0.42-dev1: the v0.0.41 final build applied the reused world terrain, scenery and flora on under one core each, about 30 s on the critical path. Repaired in source (B8): files staged on up to eight threads.

BUILD-REUSE-KEYS-TOO-BROAD-35: 17 October 2026, v0.0.42-dev1: PERSISTING; narrowed reuse by each stage's record of what it really ran, read and listed (B7), repaired in source, takes effect from the first build that records it.
