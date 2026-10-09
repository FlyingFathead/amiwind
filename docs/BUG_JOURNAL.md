# Bug journal

<!-- contents start -->
## Contents

- [TEST-ENV-LEAK-HULL-33, 9 October 2026](#test-env-leak-hull-33-9-october-2026)
- [CHIM-COURT-BARREL-USE-33, 9 October 2026](#chim-court-barrel-use-33-9-october-2026)
- [CHIM-INTRO-TP-OTHER-TOWN-33, 9 October 2026](#chim-intro-tp-other-town-33-9-october-2026)
- [BUILD-REUSE-SCRATCH-UNDECLARED-33 fixed in v0.0.33, 9 October 2026](#build-reuse-scratch-undeclared-33-fixed-in-v0033-9-october-2026)
- [GATE-PRIVACY-SCAN-33, 9 October 2026](#gate-privacy-scan-33-9-october-2026)
- [BUILD-SCHEDULER-LOWBUDGET-33: a small --jobs budget started no stage, 9 October 2026](#build-scheduler-lowbudget-33-a-small---jobs-budget-started-no-stage-9-october-2026)
- [CHIM-HARVEST-SPECIALS-33, 9 October 2026](#chim-harvest-specials-33-9-october-2026)
- [CHIM-SEYDA-ACTOR-CONTACT-33, 9 October 2026](#chim-seyda-actor-contact-33-9-october-2026)
- [BUILD-ROUTED-FLORA-RESERVE-33, 9 October 2026](#build-routed-flora-reserve-33-9-october-2026)
- [NPC-IDLE-ONLY-ANIM-33, 9 October 2026](#npc-idle-only-anim-33-9-october-2026)
- [ROUTED-HULL-NODE-ORDER-33 in the integration line, 9 October 2026](#routed-hull-node-order-33-in-the-integration-line-9-october-2026)
- [BUILD-CHIM-UNIT-HULL-KEY-33, 9 October 2026](#build-chim-unit-hull-key-33-9-october-2026)
- [CHIM-BALMORA-RING-OVER-33, 9 October 2026](#chim-balmora-ring-over-33-9-october-2026)
- [BUILD-INTERIOR-INDEX-ROUTED-33, 9 October 2026](#build-interior-index-routed-33-9-october-2026)
- [MINIWIND-NO-WINUAE-PROFILE-33, 9 October 2026](#miniwind-no-winuae-profile-33-9-october-2026)
- [MESH-LOD-OPEN-SEAMS-33 and CHIM-STRIDER-RING-33 in v0.0.33, 9 October 2026](#mesh-lod-open-seams-33-and-chim-strider-ring-33-in-v0033-9-october-2026)
- [NPC-FOLLOW-FLOORS-33: NPC companion test in FS-UAE, 9 October 2026](#npc-follow-floors-33-npc-companion-test-in-fs-uae-9-october-2026)
- [AMIGA-DISK-2GIB-LIMIT-33: partitions must also start below 2 GiB, 9 October 2026](#amiga-disk-2gib-limit-33-partitions-must-also-start-below-2-gib-9-october-2026)
- [LIGHT-ENTITIES-UNWIRED-33: Morrowind lights never become Quake light entities, 9 October 2026](#light-entities-unwired-33-morrowind-lights-never-become-quake-light-entities-9-october-2026)
- [CHIM-FAR-TERRAIN-33 repaired in source; CHIM-FAR-OBJECTS-33 found, 9 October 2026](#chim-far-terrain-33-repaired-in-source-chim-far-objects-33-found-9-october-2026)
- [CHIM-ARENA-MEMORY-33: the Arena's canton bodies do not fit the CHIM zone, 9 October 2026](#chim-arena-memory-33-the-arenas-canton-bodies-do-not-fit-the-chim-zone-9-october-2026)
- [CHIM-HULL-CHAIN-COST-33: canton bodies collide through one long chain, 9 October 2026](#chim-hull-chain-cost-33-canton-bodies-collide-through-one-long-chain-9-october-2026)
- [COLLISION-HULL-CHAINS-33: long standing-hull chains island-wide, 9 October 2026](#collision-hull-chains-33-long-standing-hull-chains-island-wide-9-october-2026)
- [CHIM-SEYDA-HUNK-GAP-33: Seyda Neen's statics stream with their chunks (builder), 9 October 2026](#chim-seyda-hunk-gap-33-seyda-neens-statics-stream-with-their-chunks-builder-9-october-2026)
- [CHIM-ZONE-RESERVE-EARLY-33: reloads of frame maps without a stated figure, 9 October 2026](#chim-zone-reserve-early-33-reloads-of-frame-maps-without-a-stated-figure-9-october-2026)
- [HEAP-12MB-FAST-ROOM-33: the 12 MiB heap test, 9 October 2026](#heap-12mb-fast-room-33-the-12-mib-heap-test-9-october-2026)
- [DEBUG-TP-CHIM-33: dbg tp on a pure-CHIM disk, 9 October 2026](#debug-tp-chim-33-dbg-tp-on-a-pure-chim-disk-9-october-2026)
- [BUILD-LAYOUT-GATE-AFTER-WRITE-33, 9 October 2026](#build-layout-gate-after-write-33-9-october-2026)
- [BUILD-PRERENDERED-PRUNE-ORDER-33, 9 October 2026](#build-prerendered-prune-order-33-9-october-2026)
- [BUILD-IMAGE-NOT-INCREMENTAL-33: per-map pass cache, 9 October 2026](#build-image-not-incremental-33-per-map-pass-cache-9-october-2026)
- [HUD-ENEMY-BAR-COLOUR-33, 9 October 2026](#hud-enemy-bar-colour-33-9-october-2026)
- [NPC-WEAPON-MESH-33, COMBAT-NOT-SAVED-33, TOOL-ALIAS-FRAMES-33, COMBAT-PLAYER-KNOCKDOWN-33: combat, 9 October 2026](#npc-weapon-mesh-33-combat-not-saved-33-tool-alias-frames-33-combat-player-knockdown-33-combat-9-october-2026)
- [BUILD-HULL-ROUTE-BUDGET-33: routed hulls overflowed a legacy map's clipnodes, 9 October 2026](#build-hull-route-budget-33-routed-hulls-overflowed-a-legacy-maps-clipnodes-9-october-2026)
- [BUILD-CHIM-HULL-RING-33: CHIM model hulls grew Balmora's ring past the zone, 9 October 2026](#build-chim-hull-ring-33-chim-model-hulls-grew-balmoras-ring-past-the-zone-9-october-2026)
- [BUILD-REUSE-SCRATCH-UNDECLARED-33 and BUILD-SURVEY-NOT-REPRODUCIBLE-33, 9 October 2026](#build-reuse-scratch-undeclared-33-and-build-survey-not-reproducible-33-9-october-2026)
- [CHIM-GRAFT-REPACK-EMPTY-33: the world vanishes in Seyda Neen on CHIM, 9 October 2026](#chim-graft-repack-empty-33-the-world-vanishes-in-seyda-neen-on-chim-9-october-2026)
- [CHIM-GRAFT-REPACK-EMPTY-33 safety net: the terrain floor, 9 October 2026](#chim-graft-repack-empty-33-safety-net-the-terrain-floor-9-october-2026)
- [BUILD-TMP-SCRATCH-33, 9 October 2026](#build-tmp-scratch-33-9-october-2026)
- [TEST-COST-ORDER-LOAD-33, 9 October 2026](#test-cost-order-load-33-9-october-2026)
- [TRACKER-CHIM-LINK-MERGE-33, 9 October 2026](#tracker-chim-link-merge-33-9-october-2026)
- [BUILD-WORLD-PARTITION-MOUNT-33, 9 October 2026](#build-world-partition-mount-33-9-october-2026)
- [MINIWIND-PAYLOAD-NOT-SLIM-33, 9 October 2026](#miniwind-payload-not-slim-33-9-october-2026)
- [CHIM-HARVEST-REMOVED-MAPS-33, 9 October 2026](#chim-harvest-removed-maps-33-9-october-2026)
- [BUILD-CACHE-CHIM-UNITS-33: the prerendered store, 9 October 2026](#build-cache-chim-units-33-the-prerendered-store-9-october-2026)
- [TRACKER-REGISTER-LINK-MERGE-33, 9 October 2026](#tracker-register-link-merge-33-9-october-2026)
- [BOOT-VOLUME-NOT-VALIDATED-33: diagnostic logs in memory during play, 9 October 2026](#boot-volume-not-validated-33-diagnostic-logs-in-memory-during-play-9-october-2026)
- [TEST-PROFILE-TIMELINE-SUM-33, 9 October 2026](#test-profile-timeline-sum-33-9-october-2026)
- [BOOT-VOLUME-NOT-VALIDATED-33 cause measured and repaired in source, 9 October 2026](#boot-volume-not-validated-33-cause-measured-and-repaired-in-source-9-october-2026)
- [BOOT-VOLUME-NOT-VALIDATED-33 registered, 9 October 2026](#boot-volume-not-validated-33-registered-9-october-2026)
- [HORIZON-FLORA-SPRITES-32 default accepted; HORIZON-HOLES-31 not re-checked, 8 October 2026](#horizon-flora-sprites-32-default-accepted-horizon-holes-31-not-re-checked-8-october-2026)
- [BUILD-EXCLUDE-STAGE-CLOSURE-33: quick test builds, 9 October 2026](#build-exclude-stage-closure-33-quick-test-builds-9-october-2026)
- [CHIM-ZONE-TMP-NOEXEC-33, 9 October 2026](#chim-zone-tmp-noexec-33-9-october-2026)
- [BUILD-MINIWIND-FINGERPRINT-ENGINE-33, 9 October 2026](#build-miniwind-fingerprint-engine-33-9-october-2026)
- [TEST-NATIVE-STALE-IMPORT-33: MiniWind exterior scope, 9 October 2026](#test-native-stale-import-33-miniwind-exterior-scope-9-october-2026)
- [CHIM-ACTOR-RING-33: NPC companion test, 9 October 2026](#chim-actor-ring-33-npc-companion-test-9-october-2026)
- [RELEASE-WS-BASELINE-VERSION-33: the whitespace baseline followed VERSION, 9 October 2026](#release-ws-baseline-version-33-the-whitespace-baseline-followed-version-9-october-2026)
- [BUILD-DOOR-REFERENCE-SERIAL-33, BUILD-ORDERED-WINDOW-33; stage repairs measured, 9 October 2026](#build-door-reference-serial-33-build-ordered-window-33-stage-repairs-measured-9-october-2026)
- [NPC-BAKED-WHOLE-DUPLICATION-33: modular NPCs designed and measured, 9 October 2026](#npc-baked-whole-duplication-33-modular-npcs-designed-and-measured-9-october-2026)
- [AUDIO-HOST-LOAD-33: crackle on a saturated host, 9 October 2026](#audio-host-load-33-crackle-on-a-saturated-host-9-october-2026)
- [CHIM Engine tracker and found-in-build records; CHIM-RECEIPT-COMMIT-33, 9 October 2026](#chim-engine-tracker-and-found-in-build-records-chim-receipt-commit-33-9-october-2026)
- [OPENING-BRIGHT-31, OPENING-JIUB-LANTERN-32 and NPC-LIGHT-COHERENCE-32: the opening scene's light, 9 October 2026](#opening-bright-31-opening-jiub-lantern-32-and-npc-light-coherence-32-the-opening-scenes-light-9-october-2026)
- [CHIM-TRACE-TAIL-33: a tail of expensive CHIM collision traces, 9 October 2026](#chim-trace-tail-33-a-tail-of-expensive-chim-collision-traces-9-october-2026)
- [BUILD-IDLE-STAGES-33, BUILD-STAGE-START-SHARE-33 and BUILD-NESTED-POOL-ALLOWANCE-33, 9 October 2026](#build-idle-stages-33-build-stage-start-share-33-and-build-nested-pool-allowance-33-9-october-2026)
- [BUILD-PROFILE-JOBS-START-ONLY-33: idle cores measured against the start allowance, 9 October 2026](#build-profile-jobs-start-only-33-idle-cores-measured-against-the-start-allowance-9-october-2026)
- [BUILD-PATH-IN-PAYLOAD-32 and BUILD-STAIR-FLAG-INERT-32, 8 October 2026](#build-path-in-payload-32-and-build-stair-flag-inert-32-8-october-2026)
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33 and the Vivec Arena in CHIM builds, 9 October 2026](#chim-image-optimizer-receipt-33-and-the-vivec-arena-in-chim-builds-9-october-2026)
- [CHIM-LEGACY-CHAIN-33: CHIM builds and the legacy exterior chain, 9 October 2026](#chim-legacy-chain-33-chim-builds-and-the-legacy-exterior-chain-9-october-2026)
- [BUILD-CACHE-OVERBROAD-33 and BUILD-CACHE-NO-CUTOFF-33: CHIM builds rerun the scene chain, 9 October 2026](#build-cache-overbroad-33-and-build-cache-no-cutoff-33-chim-builds-rerun-the-scene-chain-9-october-2026)
- [CHIM-HULL-STAIR-EDGE-33 and BUILD-REUSE-TMP-UNDECLARED-33: first MiniWind builds, 9 October 2026](#chim-hull-stair-edge-33-and-build-reuse-tmp-undeclared-33-first-miniwind-builds-9-october-2026)
- [GATE-SOURCE-RACE-33, 9 October 2026](#gate-source-race-33-9-october-2026)
- [CHIM-SEYDA-HUNK-GAP-33 and CHIM-ZONE-RESERVE-EARLY-33, 9 October 2026](#chim-seyda-hunk-gap-33-and-chim-zone-reserve-early-33-9-october-2026)
- [CHIM-CHUNK-LOAD-FAIL-33: Balmora chunks without room on the CHIM preview, 9 October 2026](#chim-chunk-load-fail-33-balmora-chunks-without-room-on-the-chim-preview-9-october-2026)
- [CHIM-FAR-TERRAIN-33: no distant ground on CHIM, 9 October 2026](#chim-far-terrain-33-no-distant-ground-on-chim-9-october-2026)
- [Last failing stair flights were gate artefacts, 9 October 2026](#last-failing-stair-flights-were-gate-artefacts-9-october-2026)
- [CHIM-SEYDA-MEMORY-33: Seyda Neen's ring, cause found, 8 October 2026](#chim-seyda-memory-33-seyda-neens-ring-cause-found-8-october-2026)
- [CHIM visibility rows: slow on irregular ground, rebuilt per worker count, 8 October 2026](#chim-visibility-rows-slow-on-irregular-ground-rebuilt-per-worker-count-8-october-2026)
- [CHIM heap gate: the zone default is too small for Seyda Neen, 8 October 2026](#chim-heap-gate-the-zone-default-is-too-small-for-seyda-neen-8-october-2026)
- [CHIM-TEXTURE-SPECKS-33: owner playtest, gate and opt-in effect, 9 October 2026](#chim-texture-specks-33-owner-playtest-gate-and-opt-in-effect-9-october-2026)
- [RELEASE-PATCH-SIZE-33, 8 October 2026](#release-patch-size-33-8-october-2026)
- [ENGINE-FPU-DATA-DECODE-33, 8 October 2026](#engine-fpu-data-decode-33-8-october-2026)
- [BUILD-ENV-FINGERPRINT-GLOBAL-33, merges for v0.0.33-dev1, 8 October 2026](#build-env-fingerprint-global-33-merges-for-v0033-dev1-8-october-2026)
- [BUILD-CACHE-CLOSURE-WIDE-33 and BUILD-CACHE-ABSOLUTE-PATHS-33: stage reuse, 9 October 2026](#build-cache-closure-wide-33-and-build-cache-absolute-paths-33-stage-reuse-9-october-2026)
- [DOCS-TOC-RENDER-FIGHT-33; v0.0.33-bug-fields merged, 8 October 2026](#docs-toc-render-fight-33-v0033-bug-fields-merged-8-october-2026)
- [TRACKER-REGISTER-SIZE-33: the bug register outgrew the release text limit, 8 October 2026](#tracker-register-size-33-the-bug-register-outgrew-the-release-text-limit-8-october-2026)
- [DOCS-DEAD-ANCHORS-32 and TEST-PROFILE-STAGE-WALL-32, 8 October 2026](#docs-dead-anchors-32-and-test-profile-stage-wall-32-8-october-2026)
- [Stair gate merged on v0.0.33-dev; BUILD-NAME-MOJIBAKE-32 closed as a duplicate, 8 October 2026](#stair-gate-merged-on-v0033-dev-build-name-mojibake-32-closed-as-a-duplicate-8-october-2026)
- [Seyda Neen on CHIM: first world, stair gate and findings, 8 October 2026](#seyda-neen-on-chim-first-world-stair-gate-and-findings-8-october-2026)
- [Stairs follow Morrowind's rules, and a gate walks them, 8 October 2026](#stairs-follow-morrowinds-rules-and-a-gate-walks-them-8-october-2026)
- [UI-MENU-LOGO-32, 8 October 2026](#ui-menu-logo-32-8-october-2026)
- [PHOTO-DEBUG-STRIP-33, 8 October 2026](#photo-debug-strip-33-8-october-2026)
- [QC-AW-FLAME-SPAWN-32 and CENSUS-LOAD-SLOW-32: repaired in source, A/B/C/D, 8 October 2026](#qc-aw-flame-spawn-32-and-census-load-slow-32-repaired-in-source-abcd-8-october-2026)
- [CENSUS-LOAD-SLOW-32 cause; REMOTE-CONSOLE-LOG-COST-32 and DEBUG-TP-SHIP-FREEZE-32, 8 October 2026](#census-load-slow-32-cause-remote-console-log-cost-32-and-debug-tp-ship-freeze-32-8-october-2026)
- [v0.0.32-dev3 owner play reports, 8 October 2026](#v0032-dev3-owner-play-reports-8-october-2026)
- [v0.0.32-dev3 smoke test findings, 8 October 2026](#v0032-dev3-smoke-test-findings-8-october-2026)
- [CHIM-ZONE-RING-THRASH-33 and CHIM-REBUILD-COST-33: emulator sweep, 8 October 2026](#chim-zone-ring-thrash-33-and-chim-rebuild-cost-33-emulator-sweep-8-october-2026)
- [CI-BOOTSTRAP-NUMPY-32, 8 October 2026](#ci-bootstrap-numpy-32-8-october-2026)
- [HEAP-SEYDA-OVERLAP-32: temporary pre-CHIM heap bypass for three Seyda Neen maps, 8 October 2026](#heap-seyda-overlap-32-temporary-pre-chim-heap-bypass-for-three-seyda-neen-maps-8-october-2026)
- [Morrowind collision census, 8 October 2026](#morrowind-collision-census-8-october-2026)
- [First FS-UAE session of Balmora under CHIM, 8 October 2026](#first-fs-uae-session-of-balmora-under-chim-8-october-2026)
- [Vivec Arena arrival and owner dev1 reports, 8 October 2026](#vivec-arena-arrival-and-owner-dev1-reports-8-october-2026)
- [TEST-PROFILE-SECTION-CPU-32, 8 October 2026](#test-profile-section-cpu-32-8-october-2026)
- [BUILD-EXTRA-TOWN-OPTIN-32: the Vivec Arena preview leaves the default build, 8 October 2026](#build-extra-town-optin-32-the-vivec-arena-preview-leaves-the-default-build-8-october-2026)
- [KEYS-AMIGA-EDIT-32: Del arrived as F11, FS-UAE Home/End as keypad ( and Help, 8 October 2026](#keys-amiga-edit-32-del-arrived-as-f11-fs-uae-homeend-as-keypad--and-help-8-october-2026)
- [BUILD-DRESSING-EXCLUDED-32: Census office lantern hook, silent converter drops, 8 October 2026](#build-dressing-excluded-32-census-office-lantern-hook-silent-converter-drops-8-october-2026)
- [AW-20260928-01: ship-to-deck transition sluggish again, 8 October 2026](#aw-20260928-01-ship-to-deck-transition-sluggish-again-8-october-2026)
- [CONSOLE-HISTORY-ARROWS-32: owner trace shows the arrows arriving, 8 October 2026](#console-history-arrows-32-owner-trace-shows-the-arrows-arriving-8-october-2026)
- [FLAME-RANGE-NEAREST-32: Census office hearth fire only up close, 8 October 2026](#flame-range-nearest-32-census-office-hearth-fire-only-up-close-8-october-2026)
- [CHIM parity and terrain hull fixes; test import path, 8 October 2026](#chim-parity-and-terrain-hull-fixes-test-import-path-8-october-2026)
- [Vivec dev1 owner evidence and CHIM terrain edges, 8 October 2026](#vivec-dev1-owner-evidence-and-chim-terrain-edges-8-october-2026)
- [CHIM harvest and payload parity findings, 8 October 2026](#chim-harvest-and-payload-parity-findings-8-october-2026)
- [BUILD-SEYDA-RECORDED-REWRITTEN-32: traced and repaired in source, 8 October 2026](#build-seyda-recorded-rewritten-32-traced-and-repaired-in-source-8-october-2026)
- [HORIZON-FLORA-SPRITES-32: cause measured, land-outline horizon default, 8 October 2026](#horizon-flora-sprites-32-cause-measured-land-outline-horizon-default-8-october-2026)
- [FOG-TOWN-HEAVY-32: fog settings identical to v0.0.31, 8 October 2026](#fog-town-heavy-32-fog-settings-identical-to-v0031-8-october-2026)
- [HORIZON-FLORA-SPRITES-32: owner decisions and planned improvements, 8 October 2026](#horizon-flora-sprites-32-owner-decisions-and-planned-improvements-8-october-2026)
- [CONSOLE-HISTORY-ARROWS-32: console arrows recall nothing on the owner's FS-UAE, 8 October 2026](#console-history-arrows-32-console-arrows-recall-nothing-on-the-owners-fs-uae-8-october-2026)
- [CONSOLE-HISTORY-EMPTY-32: Up past the oldest command sticks on an empty line, 8 October 2026](#console-history-empty-32-up-past-the-oldest-command-sticks-on-an-empty-line-8-october-2026)
- [HORIZON-FLORA-SPRITES-32: horizon silhouetting, not yet perfect, 8 October 2026](#horizon-flora-sprites-32-horizon-silhouetting-not-yet-perfect-8-october-2026)
- [BUILD-HEAP-RECEIPT-TUPLES-32: dev2 image step refused its final heap receipt, 8 October 2026](#build-heap-receipt-tuples-32-dev2-image-step-refused-its-final-heap-receipt-8-october-2026)
- [Vivec Arena residents, 8 October 2026](#vivec-arena-residents-8-october-2026)
- [GATE-SHARED-SOURCE-32: local gate tested the main checkout, 8 October 2026](#gate-shared-source-32-local-gate-tested-the-main-checkout-8-october-2026)
- [Image-parallel follow-ups merged, 8 October 2026](#image-parallel-follow-ups-merged-8-october-2026)
- [v0.0.32-dev1 delivery and smoke test findings, 8 October 2026](#v0032-dev1-delivery-and-smoke-test-findings-8-october-2026)
- [v0.0.32-dev1 playtest findings, 8 October 2026](#v0032-dev1-playtest-findings-8-october-2026)
- [ENTITY-TRACKER-HARVEST-32: register state corrected, 8 October 2026](#entity-tracker-harvest-32-register-state-corrected-8-october-2026)
- [Builder harvest step findings, 8 October 2026](#builder-harvest-step-findings-8-october-2026)
- [CHIM world-format follow-up findings, 8 October 2026](#chim-world-format-follow-up-findings-8-october-2026)
- [Image-parallel follow-up findings, 8 October 2026](#image-parallel-follow-up-findings-8-october-2026)
- [BUILD-HARVEST-NOT-BUILT-32: harvest built by default, 8 October 2026](#build-harvest-not-built-32-harvest-built-by-default-8-october-2026)
- [BUILD-IMAGE-SERIAL-32: cause and repair, 8 October 2026](#build-image-serial-32-cause-and-repair-8-october-2026)
- [dev1 image build findings, 8 October 2026](#dev1-image-build-findings-8-october-2026)
- [Parallel test runner findings, 8 October 2026](#parallel-test-runner-findings-8-october-2026)
- [Second CHIM engine slice, 8 October 2026](#second-chim-engine-slice-8-october-2026)
- [Build profiler findings, 8 October 2026](#build-profiler-findings-8-october-2026)
- [BUILD-XDFTOOL-ARGMAX-32, 8 October 2026](#build-xdftool-argmax-32-8-october-2026)
- [First CHIM engine slice, 8 October 2026](#first-chim-engine-slice-8-october-2026)
- [Harvest data audit and builder message, 8 October 2026](#harvest-data-audit-and-builder-message-8-october-2026)
- [First CHIM world-format build of Balmora, 8 October 2026](#first-chim-world-format-build-of-balmora-8-october-2026)
- [NET-UDP-INIT-CRASH-32, 8 October 2026](#net-udp-init-crash-32-8-october-2026)
- [Release coverage test; per-race hands built by default, 8 October 2026](#release-coverage-test-per-race-hands-built-by-default-8-october-2026)
- [Builder defaults audit: stages missing from the builder, 8 October 2026](#builder-defaults-audit-stages-missing-from-the-builder-8-october-2026)
- [BUILD-IMAGE-SERIAL-32, 8 October 2026](#build-image-serial-32-8-october-2026)
- [BUILD-FLORA-OPTIN-32 fixed in source, 8 October 2026](#build-flora-optin-32-fixed-in-source-8-october-2026)
- [BUILD-FLORA-OPTIN-32; world layout verified, 8 October 2026](#build-flora-optin-32-world-layout-verified-8-october-2026)
- [DEBUG-TP-TOWN-NAMES-32, 8 October 2026](#debug-tp-town-names-32-8-october-2026)
- [Renderer counters and benchmark findings, 8 October 2026](#renderer-counters-and-benchmark-findings-8-october-2026)
- [GOG/Steam loose-file A/B findings, 8 October 2026](#gogsteam-loose-file-ab-findings-8-october-2026)
- [BUILD-WORLD-LAYOUT-DRIFT-32; dev1 actor waiver tracked, 8 October 2026](#build-world-layout-drift-32-dev1-actor-waiver-tracked-8-october-2026)
- [Known-inputs check merged; BUILD-INPUTCHECK-SLOW-32, 8 October 2026](#known-inputs-check-merged-build-inputcheck-slow-32-8-october-2026)
- [Vivec cantons import and loader rework findings, 8 October 2026](#vivec-cantons-import-and-loader-rework-findings-8-october-2026)
- [Font A/B: both font paths show wrong characters, 8 October 2026](#font-ab-both-font-paths-show-wrong-characters-8-october-2026)
- [Builder breaks fixed; next stop in Seyda Neen culling, 8 October 2026](#builder-breaks-fixed-next-stop-in-seyda-neen-culling-8-october-2026)
- [BUILD-EDITION-DIFFERENCES-32: GOG and Steam builds differ, 8 October 2026](#build-edition-differences-32-gog-and-steam-builds-differ-8-october-2026)
- [BUILD-INPUTS-UNVERIFIED-32: user inputs not checked against known versions, 8 October 2026](#build-inputs-unverified-32-user-inputs-not-checked-against-known-versions-8-october-2026)
- [BUILD-NOT-FROM-SCRATCH-32: releases without a from-scratch build, 8 October 2026](#build-not-from-scratch-32-releases-without-a-from-scratch-build-8-october-2026)
- [First from-scratch build with the repository builder, 8 October 2026](#first-from-scratch-build-with-the-repository-builder-8-october-2026)
- [FPU support library findings, 8 October 2026](#fpu-support-library-findings-8-october-2026)
- [Asset census findings, 8 October 2026](#asset-census-findings-8-october-2026)
- [Face validator over the shipped v0.0.31 image, 8 October 2026](#face-validator-over-the-shipped-v0031-image-8-october-2026)
- [ENGINE-FPU-UNIMPL-31, NPC-TARGET-REDUNDANT-31, ENGINE-BUILD-REPRO-31, ENGINE-FPSP-MISSING-31, REMOTE-STATE-WIDTH-31: FPU fixes measured, 8 October 2026](#engine-fpu-unimpl-31-npc-target-redundant-31-engine-build-repro-31-engine-fpsp-missing-31-remote-state-width-31-fpu-fixes-measured-8-october-2026)
- [REMOTE-CONSOLE-APPEND-31: remote console log overwrites itself, 8 October 2026](#remote-console-append-31-remote-console-log-overwrites-itself-8-october-2026)
- [TEST-FPU-STRICT-JIT-31: strict FPU emulation needs the JIT off, 8 October 2026](#test-fpu-strict-jit-31-strict-fpu-emulation-needs-the-jit-off-8-october-2026)
- [Converter face findings from the texture snapping test, 8 October 2026](#converter-face-findings-from-the-texture-snapping-test-8-october-2026)
- [TOWN-FRAME-CEILING-32: high ground leaks town frames, 8 October 2026](#town-frame-ceiling-32-high-ground-leaks-town-frames-8-october-2026)
- [Independent review of the open-world plan, 8 October 2026](#independent-review-of-the-open-world-plan-8-october-2026)
- [World streamer measurement findings, 8 October 2026](#world-streamer-measurement-findings-8-october-2026)
- [ENGINE-SUBMODEL-LIMIT-32, TOOL-SIMPLIFY-MANIFOLD-32, SHELL-TEXTURE-VOTE-32: distant shell prototype, 8 October 2026](#engine-submodel-limit-32-tool-simplify-manifold-32-shell-texture-vote-32-distant-shell-prototype-8-october-2026)
- [Vivec limits repaired in source; ERICW-TEXINFO-SIGNED-31, EXTENTS-FPU-RULE-31, VIVEC-HEAP-31 found, 8 October 2026](#vivec-limits-repaired-in-source-ericw-texinfo-signed-31-extents-fpu-rule-31-vivec-heap-31-found-8-october-2026)
- [ESTIMATE-EVR-BELOW-CUR-31 and TOOLING-HEADLESS-BROWSER-31: map metrics layer, 8 October 2026](#estimate-evr-below-cur-31-and-tooling-headless-browser-31-map-metrics-layer-8-october-2026)
- [WORLD-REGION-DUPLICATION-31: exterior objects stored about ten times, 8 October 2026](#world-region-duplication-31-exterior-objects-stored-about-ten-times-8-october-2026)
- [Whole-world measurement findings, 8 October 2026](#whole-world-measurement-findings-8-october-2026)
- [MODEL-MARKSURF-SIGNED-31 and TOWN-VIS-OCCLUSION-31: visibility prototype, 8 October 2026](#model-marksurf-signed-31-and-town-vis-occlusion-31-visibility-prototype-8-october-2026)
- [ENGINE-FPU-UNIMPL-31, ENGINE-FPSP-MISSING-31, NPC-TARGET-REDUNDANT-31, CI-ERICW-SKIP-31, CI-SKIPS-UNGUARDED-31: FPU audit and gate skips, 8 October 2026](#engine-fpu-unimpl-31-engine-fpsp-missing-31-npc-target-redundant-31-ci-ericw-skip-31-ci-skips-unguarded-31-fpu-audit-and-gate-skips-8-october-2026)
- [GATE-NODE-MISSING-31 and TOOLKIT-TEST-POINTERLOCK-31: inspector tests, 8 October 2026](#gate-node-missing-31-and-toolkit-test-pointerlock-31-inspector-tests-8-october-2026)
- [ENGINE-BUILD-REPRO-31 and VIVEC-TEXINFO-31: from tonight's reports, 8 October 2026](#engine-build-repro-31-and-vivec-texinfo-31-from-tonights-reports-8-october-2026)
- [MESH-EXTENT-GRID-31 and LIGHTMAP-TAIL-31: Vivec dry run, 8 October 2026](#mesh-extent-grid-31-and-lightmap-tail-31-vivec-dry-run-8-october-2026)
- [BUILD-SEYDA-PRIVATE-STAGES-31: duplicate of BUILD-SEYDA-REGEN-30, 8 October 2026](#build-seyda-private-stages-31-duplicate-of-build-seyda-regen-30-8-october-2026)
- [BUILD-NIGHT-TABLES-31: night lighting tables only on hand-made disks, 8 October 2026](#build-night-tables-31-night-lighting-tables-only-on-hand-made-disks-8-october-2026)
- [BUILD-FINALIZE-SCENE-31: undefined name in image finalisation, 8 October 2026](#build-finalize-scene-31-undefined-name-in-image-finalisation-8-october-2026)
- [DBG-TOGGLE-WORDS-31: on/off words for settings, 8 October 2026](#dbg-toggle-words-31-onoff-words-for-settings-8-october-2026)
- [TOWN-VIS-OCCLUSION-31: buildings do not block visibility, 7 October 2026](#town-vis-occlusion-31-buildings-do-not-block-visibility-7-october-2026)
- [LAMPS-FLICKER-31 and SEYDA-LANTERNS-MISSING-31: dev5 night walk, 7 October 2026](#lamps-flicker-31-and-seyda-lanterns-missing-31-dev5-night-walk-7-october-2026)
- [BUILD-WINDOWS-DOCKER-SLOW-31: Docker disk steps on Windows, 7 October 2026](#build-windows-docker-slow-31-docker-disk-steps-on-windows-7-october-2026)
- [NIGHT-0400-DARK-31: sudden darkness near 04:00, 7 October 2026](#night-0400-dark-31-sudden-darkness-near-0400-7-october-2026)
- [GUARD-TORCH-BRIGHT-31 and LAMPS-RANGE-31: Balmora at night, 7 October 2026](#guard-torch-bright-31-and-lamps-range-31-balmora-at-night-7-october-2026)
- [LAMPS-RANGE-31: only the nearest lamps light up, 7 October 2026](#lamps-range-31-only-the-nearest-lamps-light-up-7-october-2026)
- [SEYDA-BLOCK-31 and PLACE-NAMES-INTERIOR-31: dev3 playtest, 7 October 2026](#seyda-block-31-and-place-names-interior-31-dev3-playtest-7-october-2026)
- [DLIGHT-WALLS-31: cause is the night remap, 7 October 2026](#dlight-walls-31-cause-is-the-night-remap-7-october-2026)
- [MUSIC-OPENING-CLIP-31: title clip during the opening load, 7 October 2026](#music-opening-clip-31-title-clip-during-the-opening-load-7-october-2026)
- [MUSIC-STARTUP-TRACK-31: random track under the startup logo, 7 October 2026](#music-startup-track-31-random-track-under-the-startup-logo-7-october-2026)
- [DLIGHT-WALLS-31: torches light the ground but not town walls, 7 October 2026](#dlight-walls-31-torches-light-the-ground-but-not-town-walls-7-october-2026)
- [OPENING-BRIGHT-31: ship hold brighter than the original, 7 October 2026](#opening-bright-31-ship-hold-brighter-than-the-original-7-october-2026)
- [HORIZON-HOLES-31: distant Balmora breaks up against the sky, 7 October 2026](#horizon-holes-31-distant-balmora-breaks-up-against-the-sky-7-october-2026)
- [HUD-NOTIFY-OVERLAP-31: console line over the title, 7 October 2026](#hud-notify-overlap-31-console-line-over-the-title-7-october-2026)
- [LIGHT-OFF-31: Off-by-default lights would bake as lit, 7 October 2026](#light-off-31-off-by-default-lights-would-bake-as-lit-7-october-2026)
- [LIGHT-FALLOFF-31 correction; LIGHTMAP-GRID-31, 7 October 2026](#light-falloff-31-correction-lightmap-grid-31-7-october-2026)
- [LIGHT-FALLOFF-31 and BALMORA-LAMPS-DIM-31: OpenMW reference, 7 October 2026](#light-falloff-31-and-balmora-lamps-dim-31-openmw-reference-7-october-2026)
- [SEYDA-WALL-SHAPE-31: likely a tree card drawn through a wall, 7 October 2026](#seyda-wall-shape-31-likely-a-tree-card-drawn-through-a-wall-7-october-2026)
- [BALMORA-LAMPS-DIM-31, NIGHT-RUST-31, EMISSIVE-UNSHIPPED-31: causes measured, 7 October 2026](#balmora-lamps-dim-31-night-rust-31-emissive-unshipped-31-causes-measured-7-october-2026)
- [LIGHT-NEGATIVE-31: negative lights bake as white, 7 October 2026](#light-negative-31-negative-lights-bake-as-white-7-october-2026)
- [BALMORA-LAMPS-DIM-31: Balmora lamps nearly black at night, 7 October 2026](#balmora-lamps-dim-31-balmora-lamps-nearly-black-at-night-7-october-2026)
- [SEYDA-WALL-SHAPE-31: shape in a Seyda Neen wall, 7 October 2026](#seyda-wall-shape-31-shape-in-a-seyda-neen-wall-7-october-2026)
- [LIGHT-FALLOFF-31: the opening lantern bakes no light, 7 October 2026](#light-falloff-31-the-opening-lantern-bakes-no-light-7-october-2026)
- [SEYDA-READ-SLOW-31: owner playtest of dev2, 7 October 2026](#seyda-read-slow-31-owner-playtest-of-dev2-7-october-2026)
- [AUDIO-03 and AUDIO-LOGO-31: music started under disk-heavy moments, 7 October 2026](#audio-03-and-audio-logo-31-music-started-under-disk-heavy-moments-7-october-2026)
- [TRACKER-MAP-BLANK-31: world progress map went blank on hover, 7 October 2026](#tracker-map-blank-31-world-progress-map-went-blank-on-hover-7-october-2026)
- [SEYDA-READ-SLOW-31: 16 KiB file buffer repairs and beats it, 7 October 2026](#seyda-read-slow-31-16-kib-file-buffer-repairs-and-beats-it-7-october-2026)
- [SEYDA-READ-SLOW-31: dev1 crossings read slower than the test image, 7 October 2026](#seyda-read-slow-31-dev1-crossings-read-slower-than-the-test-image-7-october-2026)
- [GATE-EMBERS-31: ember commit failed the dev1 gates, 7 October 2026](#gate-embers-31-ember-commit-failed-the-dev1-gates-7-october-2026)
- [SEYDA-LOAD-HANG-30: the hung read is the music stream, 7 October 2026](#seyda-load-hang-30-the-hung-read-is-the-music-stream-7-october-2026)
- [CI-HOSTDEPS-30: host CI job failed on the first v0.0.30 push, 7 October 2026](#ci-hostdeps-30-host-ci-job-failed-on-the-first-v0030-push-7-october-2026)
- [v0.0.30-rc1 owner playtest summary, 7 October 2026](#v0030-rc1-owner-playtest-summary-7-october-2026)
- [CENSUS-ENTITIES-30: owner-accepted in v0.0.30-rc1, 7 October 2026](#census-entities-30-owner-accepted-in-v0030-rc1-7-october-2026)
- [AUDIO-NEWGAME-30: rc1 playtest audio reports, 7 October 2026](#audio-newgame-30-rc1-playtest-audio-reports-7-october-2026)
- [CENSUS-ENTITIES-30: misplaced objects in the Census and Excise Office, 7 October 2026](#census-entities-30-misplaced-objects-in-the-census-and-excise-office-7-october-2026)
- [SEYDA-LOAD-HANG-30: rare freeze during a Seyda Neen region load, 7 October 2026](#seyda-load-hang-30-rare-freeze-during-a-seyda-neen-region-load-7-october-2026)
- [BUILD-SEYDA-REGEN-30: public build cannot regenerate Seyda Neen, 7 October 2026](#build-seyda-regen-30-public-build-cannot-regenerate-seyda-neen-7-october-2026)
- [INTRO-ROLES-30: crash on a region change, 7 October 2026](#intro-roles-30-crash-on-a-region-change-7-october-2026)
- [CONVERTER-ROOT-ROTATION-30: same cause in more maps, 7 October 2026](#converter-root-rotation-30-same-cause-in-more-maps-7-october-2026)
- [BALMORA-TEMPLE-GEOMETRY-29: cause found, 7 October 2026](#balmora-temple-geometry-29-cause-found-7-october-2026)

<!-- contents end -->

## TEST-ENV-LEAK-HULL-33, 9 October 2026

[TEST-ENV-LEAK-HULL-33](bugs/TEST-ENV-LEAK-HULL-33.md): the owner's sequential suite run failed the CHIM unit
fingerprint test because an earlier in-process test left the standing-hull switch set; the parallel gate never
shares a process between those tests. Tests now restore the environment; the release checks add a sequential run.

## CHIM-COURT-BARREL-USE-33, 9 October 2026

[CHIM-COURT-BARREL-USE-33](bugs/CHIM-COURT-BARREL-USE-33.md): on the v0.0.33 final image the courtyard barrel
with Fargoth's ring could not be used. The CHIM frame maps put every referenced func_wall into the chunks
with no edict, and the engine finds the barrel by its edict. The frame maps now keep a faceless marker for
every object listed in the engine's one list (aw_activated.h), and a gate checks it.

## CHIM-INTRO-TP-OTHER-TOWN-33, 9 October 2026

[CHIM-INTRO-TP-OTHER-TOWN-33](bugs/CHIM-INTRO-TP-OTHER-TOWN-33.md): the final image's smoke test teleported
from the prison ship to Balmora and landed in the intro docks' frame map (empty water): the docks' frame map
was chosen for any CHIM town during the intro stages. Now only for Seyda Neen.

## BUILD-REUSE-SCRATCH-UNDECLARED-33 fixed in v0.0.33, 9 October 2026

[BUILD-REUSE-SCRATCH-UNDECLARED-33](bugs/BUILD-REUSE-SCRATCH-UNDECLARED-33.md): measured on the release
builds: release candidate reruns reused 17, 18 and 25 of 34 stages before the repair; the v0.0.33 final
reused 30 of 34 with it (engine, harvest, chim and image ran, each for a stated reason).

## GATE-PRIVACY-SCAN-33, 9 October 2026

[GATE-PRIVACY-SCAN-33](bugs/GATE-PRIVACY-SCAN-33.md): the gate's source preflight does not scan file contents
for tool names and private paths; only the release kit does. The preflight will share the kit's scan.

## BUILD-SCHEDULER-LOWBUDGET-33: a small --jobs budget started no stage, 9 October 2026

[BUILD-SCHEDULER-LOWBUDGET-33](bugs/BUILD-SCHEDULER-LOWBUDGET-33.md): a MiniWind build with
`--jobs 3` stopped starting stages after its terrain stage. The scheduler reserved a worker for every
other ready branch before starting a pooled stage, so with more ready branches than the budget it
started none and spun on one core. Now, with nothing running, the first ready stage starts.

## CHIM-HARVEST-SPECIALS-33, 9 October 2026

[CHIM-HARVEST-SPECIALS-33](bugs/CHIM-HARVEST-SPECIALS-33.md): the rc1 image step stopped on the intro docks'
harvest catalogue: the docks run as their CHIM frame map, and the engine would never load the legacy-named
catalogue. It is left out for v0.0.33 (17 plants not pickable on the docks); a frame-map catalogue follows.

## CHIM-SEYDA-ACTOR-CONTACT-33, 9 October 2026

[CHIM-SEYDA-ACTOR-CONTACT-33](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md): the rc1 build stopped at the frame-map
parity check: nine Seyda Neen residents, baked on the recorded v0.0.31 terrain, stand up to 3.3 units off the
CHIM ground. The check now refits them with the legacy fitter's rules (9 of 12 refitted, Balmora unchanged).

## BUILD-ROUTED-FLORA-RESERVE-33, 9 October 2026

[BUILD-ROUTED-FLORA-RESERVE-33](bugs/BUILD-ROUTED-FLORA-RESERVE-33.md): with routed standing hulls the full
build stopped in world-flora: region vf0779's flora packing needed 33,533 clipnodes against its 32,767
reserve (32,614 with chains). v0.0.33 ships with chains as the default; routing stays selectable.

## NPC-IDLE-ONLY-ANIM-33, 9 October 2026

[NPC-IDLE-ONLY-ANIM-33](bugs/NPC-IDLE-ONLY-ANIM-33.md): NPCs play only their idle frames, so a moving NPC
glides; the owner noticed it on the companion test. Planned for the next release as the animation kit.

## ROUTED-HULL-NODE-ORDER-33 in the integration line, 9 October 2026

[ROUTED-HULL-NODE-ORDER-33](bugs/ROUTED-HULL-NODE-ORDER-33.md): the Arena Pit crashed the engine on load
("SV_RecursiveHullCheck: bad node number") because a routed hull's root sat above nodes it reaches. The same
routing writes the standing hulls of every legacy map model over 16 pieces since the routed hulls merged, so the
fix was taken into the integration line before the first full build that ships them.

## BUILD-CHIM-UNIT-HULL-KEY-33, 9 October 2026

[BUILD-CHIM-UNIT-HULL-KEY-33](bugs/BUILD-CHIM-UNIT-HULL-KEY-33.md): a `--model-hull chain` test build reused
all 692 CHIM variant units of the routed-hull build: the hull form and the routing source were not part of
the unit fingerprint. Both are now.

## CHIM-BALMORA-RING-OVER-33, 9 October 2026

[CHIM-BALMORA-RING-OVER-33](bugs/CHIM-BALMORA-RING-OVER-33.md): the first full v0.0.33 build stopped at the
CHIM heap gate on Balmora: the routed standing hulls of large CHIM models add 138,688 bytes to the south-west
ring, which had 2,528 bytes of headroom with chains. `--model-hull chain` passes meanwhile; repair in progress.

## BUILD-INTERIOR-INDEX-ROUTED-33, 9 October 2026

[BUILD-INTERIOR-INDEX-ROUTED-33](bugs/BUILD-INTERIOR-INDEX-ROUTED-33.md): the first full v0.0.33 build after
the routed standing hulls stopped in the interior stage: the prison ship's collision index expected a chain of
convex pieces. The index now keeps a routed standing hull and indexes the point hull only.

## MINIWIND-NO-WINUAE-PROFILE-33, 9 October 2026

[MINIWIND-NO-WINUAE-PROFILE-33](bugs/MINIWIND-NO-WINUAE-PROFILE-33.md): MiniWind playtest packages had an
FS-UAE profile only, no WinUAE profile and no launcher, unlike the v0.0.32 playtests. The package step will
write both profiles and the launcher for every build type.

## MESH-LOD-OPEN-SEAMS-33 and CHIM-STRIDER-RING-33 in v0.0.33, 9 October 2026

[MESH-LOD-OPEN-SEAMS-33](bugs/MESH-LOD-OPEN-SEAMS-33.md) and [CHIM-STRIDER-RING-33](bugs/CHIM-STRIDER-RING-33.md):
the closed-hull strider fix stays on its branch for v0.0.33 by owner decision (on CHIM it puts Balmora's active
ring 108,672 bytes over the zone); v0.0.33 ships the v0.0.32 strider profile and lists both as known issues.

## NPC-FOLLOW-FLOORS-33: NPC companion test in FS-UAE, 9 October 2026

NPC-FOLLOW-FLOORS-33: first FS-UAE routes of the NPC companion test on the MiniWind (CHIM Balmora).
Outdoors it followed round a building corner, up and down the river stairs, through the alley
between two houses, across the bridge and up the west stairway with no teleport (pings and one
flood fill where it stalled). In the South Wall Cornerclub it cannot find the stairs to another
floor within its 128-unit flood fill and is placed beside the player after 6 s: the known limit
of stages 1-2, registered; stage 3 is the repair.

## AMIGA-DISK-2GIB-LIMIT-33: partitions must also start below 2 GiB, 9 October 2026

[AMIGA-DISK-2GIB-LIMIT-33](bugs/AMIGA-DISK-2GIB-LIMIT-33.md): the full two-disk build asked for the volume
AW_WORLD3 because that partition started past 2 GiB, which Kickstart 3.1 does not mount. Recorded as an accepted
platform limit (partition size and start below 2 GiB, files well under 2 GiB, drive images below 4 GiB); the builder
orders partitions accordingly and the layout gate now checks start offsets too.

## LIGHT-ENTITIES-UNWIRED-33: Morrowind lights never become Quake light entities, 9 October 2026

[LIGHT-ENTITIES-UNWIRED-33](bugs/LIGHT-ENTITIES-UNWIRED-33.md): the owner saw the Jiub lantern without its
warm light; the cause is island-wide. `light_sources.entity()` is never called, 602 of 604 light compiler logs
report 0 lights, interiors use the own scalar bake and exterior meshes get no lighting. Umbrella cause of the
lamp, lantern and falloff bugs listed on its page. Open; repair not started.

## CHIM-FAR-TERRAIN-33 repaired in source; CHIM-FAR-OBJECTS-33 found, 9 October 2026

[CHIM-FAR-TERRAIN-33](bugs/CHIM-FAR-TERRAIN-33.md): a resident far terrain layer per frame (exact
LAND every 512 units over the frame plus one cell, `maps/<frame map>.far`, 13.2 KB of Hunk for
Balmora) is drawn past the fog plane in the fog colour up to the legacy overlap depth, with the
distant-LAND rasterizer; branch v0.0.33-chim-farterrain, not yet in a build. FS-UAE A/B against
v0.0.32 and CHIM Preview 1 at the owner's poses; slow preset 31 to 44 ms a frame.
[CHIM-FAR-OBJECTS-33](bugs/CHIM-FAR-OBJECTS-33.md): the same A/B shows that much of v0.0.32's
horizon at Balmora's east bank is houses past the CHIM ring, which CHIM does not draw.

## CHIM-ARENA-MEMORY-33: the Arena's canton bodies do not fit the CHIM zone, 9 October 2026

[CHIM-ARENA-MEMORY-33](bugs/CHIM-ARENA-MEMORY-33.md): the first Vivec Arena CHIM world validates and
passes the stair gate (341 flight steps), but the heap gate fails. The active ring peaks at
6,492,688 B against 6,242,304 B, and one canton body alone decodes to 2,514,432 B. The proposed fix
is to cut such structures by chunk into world geometry.

## CHIM-HULL-CHAIN-COST-33: canton bodies collide through one long chain, 9 October 2026

[CHIM-HULL-CHAIN-COST-33](bugs/CHIM-HULL-CHAIN-COST-33.md): a trace near the Vivec Arena canton
walks about 6,570 planes, because the canton body's standing hull is one chain of 21,497 clipnodes.
It made the CHIM Arena stair gate take over 20 minutes, and the engine walks the same chain. The fix
in progress compiles or routes the hulls of large models.

## COLLISION-HULL-CHAINS-33: long standing-hull chains island-wide, 9 October 2026

[COLLISION-HULL-CHAINS-33](bugs/COLLISION-HULL-CHAINS-33.md): the hull audit of the v0.0.33-dev1 full
build (2,673 maps) finds 183 brush models of 63 meshes whose standing hull is a chain 512 or more
clipnodes deep: the prison ship 31,659, the census office 23,127, the Vivec canton bodies up to
11,211. The legacy converter now routes large models' hulls (in source, not yet built).

## CHIM-SEYDA-HUNK-GAP-33: Seyda Neen's statics stream with their chunks (builder), 9 October 2026

[CHIM-SEYDA-HUNK-GAP-33](bugs/CHIM-SEYDA-HUNK-GAP-33.md): the frame map's sprite and model statics
are tagged to stream with their chunks; Seyda Neen's map then leaves 1,589,344 bytes for after the
zone instead of 2,580,400, so the zone is back to the full 6,864 KiB. The image step checks each frame
map's whole-map heap with the models in the ring: the active ring fits with 303,968 bytes of
headroom (one copy per ring, as the engine holds them). Engine side pending; both must ship together.

## CHIM-ZONE-RESERVE-EARLY-33: reloads of frame maps without a stated figure, 9 October 2026

[CHIM-ZONE-RESERVE-EARLY-33](bugs/CHIM-ZONE-RESERVE-EARLY-33.md): the MiniWind build mw2-033c (from
c4e14ab) ends 6.8 KB under the 2 MiB Hunk gap after a reload or `dbg tp` into CHIM Balmora (2,090,368
bytes): its frame map states no `"_chim_hunk_rest"`, so the engine keeps the full zone and says the gap.
Seyda Neen's tagged frame map (streamed statics) keeps the gap from its second load; the builder will
state the figure with a 16 KiB margin.

## HEAP-12MB-FAST-ROOM-33: the 12 MiB heap test, 9 October 2026

[HEAP-12MB-FAST-ROOM-33](bugs/HEAP-12MB-FAST-ROOM-33.md): the same route at 11 and 12 MiB of heap
(ship, Census, Seyda Neen on CHIM, Caius' house, Balmora, the Arena, the gallery, save and load).
12 MiB loads everything and keeps Seyda Neen's CHIM map above the 2 MiB Hunk gap (2,148,000 bytes),
but leaves 342,240 bytes of Fast RAM in one block (11 MiB: 1,390,824), so the guard torch's 1 MiB
probe can never pass. The default stays 11 MiB; `--heap-mb 12` warns.

## DEBUG-TP-CHIM-33: dbg tp on a pure-CHIM disk, 9 October 2026

[DEBUG-TP-CHIM-33](bugs/DEBUG-TP-CHIM-33.md): on a disk with only the CHIM frame maps of the towns,
`dbg tp X Y` into a CHIM town said the teleport was unavailable (the target check looked for the
town's legacy map) and the help offered towns the disk does not have. Fixed in source: the check uses
the scene map (the frame map on CHIM), the lists name only what the disk has, and `dbg tp X Y Z`
takes a height.

## BUILD-LAYOUT-GATE-AFTER-WRITE-33, 9 October 2026

[BUILD-LAYOUT-GATE-AFTER-WRITE-33](bugs/BUILD-LAYOUT-GATE-AFTER-WRITE-33.md): the disk-layout gate measured each
drive only after it was written, so an over-limit layout was refused after up to 4 GiB of images, and a
world map between 1 GiB and 1.5 GiB was copied into a partition first; the dry-run image was not
measured. The gate now also runs on the plan before any write and on the dry-run image, and
build.py --layout-selftest proves every refusal end to end with sparse dummies.

## BUILD-PRERENDERED-PRUNE-ORDER-33, 9 October 2026

[BUILD-PRERENDERED-PRUNE-ORDER-33](bugs/BUILD-PRERENDERED-PRUNE-ORDER-33.md): gate 677 failed a prerendered
store test: with two entries stored within one second, prune chose which one to keep by folder name
(the fingerprint), so the new fingerprint scope changed the result. Ties now go by the store's usage log.

## BUILD-IMAGE-NOT-INCREMENTAL-33: per-map pass cache, 9 October 2026

[BUILD-IMAGE-NOT-INCREMENTAL-33](bugs/BUILD-IMAGE-NOT-INCREMENTAL-33.md): development builds keep
the results of the image step's BSP optimizer, hidden-surface cull and stair-walk gate by input
map SHA-256, options and pass sources (`tools/pass_cache.py`); release candidates and finals run
every pass. On the 109 maps of the v0.0.33-dev1 MiniWind image a warm run takes 5.7 s for the
optimizer (388 s without) and 6.6 s for the cull (48 s), maps and receipts byte-identical.

## HUD-ENEMY-BAR-COLOUR-33, 9 October 2026

[HUD-ENEMY-BAR-COLOUR-33](bugs/HUD-ENEMY-BAR-COLOUR-33.md): in the first Vivec Arena emulator run the enemy's
health bar showed at the right place and time but orange, not yellow: the reserved UI palette has no yellow.

## NPC-WEAPON-MESH-33, COMBAT-NOT-SAVED-33, TOOL-ALIAS-FRAMES-33, COMBAT-PLAYER-KNOCKDOWN-33: combat, 9 October 2026

Found while building melee combat and the Vivec Arena minigame ([combat](COMBAT.md)):
[NPC-WEAPON-MESH-33](bugs/NPC-WEAPON-MESH-33.md) NPCs carry no visible weapons or shields although
the rules use them; [COMBAT-NOT-SAVED-33](bugs/COMBAT-NOT-SAVED-33.md) fights and deaths are not saved;
[TOOL-ALIAS-FRAMES-33](bugs/TOOL-ALIAS-FRAMES-33.md) the alias writer stops at 32 frames, so the Arena
fighters bake 31; [COMBAT-PLAYER-KNOCKDOWN-33](bugs/COMBAT-PLAYER-KNOCKDOWN-33.md) the player's
knockdown changes only the rules, not the view or movement.

## BUILD-HULL-ROUTE-BUDGET-33: routed hulls overflowed a legacy map's clipnodes, 9 October 2026

[BUILD-HULL-ROUTE-BUDGET-33](bugs/BUILD-HULL-ROUTE-BUDGET-33.md): with `--model-hull auto`, routed
standing hulls copied straddling pieces up to each model's own budget, but a legacy map's models share
one: Seyda Neen's scene map went from 57,181 clipnodes past 65,520. Legacy maps now route without
copies (57,637 clipnodes, worst chains 1.3 to 3.2 times shallower). Found by the in-map check before any
build.

## BUILD-CHIM-HULL-RING-33: CHIM model hulls grew Balmora's ring past the zone, 9 October 2026

[BUILD-CHIM-HULL-RING-33](bugs/BUILD-CHIM-HULL-RING-33.md): the pure-CHIM release build stopped at the
heap gate: routed and compiled hulls of Balmora's houses grew the south-west ring by 138,688 bytes, to
136,160 over the zone. CHIM now routes only models over 256 pieces, without copies; Balmora measures
6,239,776 bytes again.

## BUILD-REUSE-SCRATCH-UNDECLARED-33 and BUILD-SURVEY-NOT-REPRODUCIBLE-33, 9 October 2026

[BUILD-REUSE-SCRATCH-UNDECLARED-33](bugs/BUILD-REUSE-SCRATCH-UNDECLARED-33.md): the rc1c rerun reused 1 of
33 stages: the builder's scratch folder counted as an undeclared output of the first stages, and every later
stage followed them (about 1,427 s of conversion again). The folder is run-private now, and old records refused
only for it are reusable. [BUILD-SURVEY-NOT-REPRODUCIBLE-33](bugs/BUILD-SURVEY-NOT-REPRODUCIBLE-33.md): the
world survey writes its wall time into its report, so a rerun never matches (open, next release line).

## CHIM-GRAFT-REPACK-EMPTY-33: the world vanishes in Seyda Neen on CHIM, 9 October 2026

[CHIM-GRAFT-REPACK-EMPTY-33](bugs/CHIM-GRAFT-REPACK-EMPTY-33.md): in the owner's playtest of v0.0.33
final3 the ground and buildings of Seyda Neen vanished near the town square and the player fell under
the world ("frame world repacked (marks full): 0 chunks"). Not a hole in the data: the frame world's
repack let its block go when the zone had no room for a larger one and laid out 0 chunks. Repaired in
source: the block is kept and holds the nearest chunks that fit; regression test in the CHIM engine tests.

## CHIM-GRAFT-REPACK-EMPTY-33 safety net: the terrain floor, 9 October 2026

[CHIM-GRAFT-REPACK-EMPTY-33](bugs/CHIM-GRAFT-REPACK-EMPTY-33.md), second layer: with noclip off the
frame's resident far terrain is the lowest height. A walking or free-falling body below it, with nothing
of the world under it, is lifted onto the ground with one console line and the player is held there, so an
emptied frame world no longer means an endless fall. `chim_terrain_floor 0` keeps the old behaviour.

## BUILD-TMP-SCRATCH-33, 9 October 2026

[BUILD-TMP-SCRATCH-33](bugs/BUILD-TMP-SCRATCH-33.md): after CHIM-ZONE-TMP-NOEXEC-33 the owner asked whether /tmp is a bad place
for the builder at all. Audit of the tool sources: one executed use (already moved), four large ones (movie
frames, terrain survey, town context, pool item output) and a list of small ones. All executed or large uses
now go through tools/build_scratch.py (the run's scratch folder); a static test fails on any new use.

## TEST-COST-ORDER-LOAD-33, 9 October 2026

[TEST-COST-ORDER-LOAD-33](bugs/TEST-COST-ORDER-LOAD-33.md): gate 672 failed the scheduler cost-order test on a
fully loaded host; the merged head passes it 4 of 4 in isolation, so it is a load-dependent test, not a merge
interaction. The CHIM Engine tracker link in docs/BUGS.md lost in the batch merge is restored.

## TRACKER-CHIM-LINK-MERGE-33, 9 October 2026

[TRACKER-CHIM-LINK-MERGE-33](bugs/TRACKER-CHIM-LINK-MERGE-33.md): the full gate of the integration head
fc40213 failed the CHIM tracker test: merges had dropped the register's link to the CHIM Engine
tracker. The link is restored.

## BUILD-WORLD-PARTITION-MOUNT-33, 9 October 2026

[BUILD-WORLD-PARTITION-MOUNT-33](bugs/BUILD-WORLD-PARTITION-MOUNT-33.md): the full v0.0.33-dev1 image stopped at
"Please insert volume AW_WORLD3". The CHIM world partition DW3 started at 2,281,734,144 bytes of the
world disk; Kickstart 3.1 (FS-UAE 3.1.66) does not mount a partition that starts at or beyond 2 GiB
("Not a DOS disk"). Drives now keep every partition start below 2 GiB (largest partition last when
needed) and the image step refuses a written partition that starts later.

## MINIWIND-PAYLOAD-NOT-SLIM-33, 9 October 2026

[MINIWIND-PAYLOAD-NOT-SLIM-33](bugs/MINIWIND-PAYLOAD-NOT-SLIM-33.md): MiniWind #2 carries every movie and
voice because the gated exclude flags branch was not merged into its line before the build.

## CHIM-HARVEST-REMOVED-MAPS-33, 9 October 2026

[CHIM-HARVEST-REMOVED-MAPS-33](bugs/CHIM-HARVEST-REMOVED-MAPS-33.md): the second MiniWind image stopped at
the save fingerprint, which still required the region maps of Balmora's harvest catalogues after the pure
CHIM step had removed them. Catalogues of removed maps are accepted now.

## BUILD-CACHE-CHIM-UNITS-33: the prerendered store, 9 October 2026

[BUILD-CACHE-CHIM-UNITS-33](bugs/BUILD-CACHE-CHIM-UNITS-33.md): while the prerendered store was
built on the stage cache, the chim stage's fingerprint turned out to include the content of its
unit cache folder, which grows with every build, so the stage was never reused. The unit cache is
now a content-addressed cache option, like the NPC gallery and world terrain caches.

## TRACKER-REGISTER-LINK-MERGE-33, 9 October 2026

[TRACKER-REGISTER-LINK-MERGE-33](bugs/TRACKER-REGISTER-LINK-MERGE-33.md): merging integration head
1ddb8fe into v0.0.33-boot-validate, the tracker test found the bug register's link to the CHIM
Engine tracker missing (lost in an integration merge); restored on that branch.
[TEST-PROFILE-TIMELINE-SUM-33](bugs/TEST-PROFILE-TIMELINE-SUM-33.md) closed as a duplicate of
[TEST-PROFILE-TIMELINE-BOUND-33](bugs/TEST-PROFILE-TIMELINE-BOUND-33.md).

## BOOT-VOLUME-NOT-VALIDATED-33: diagnostic logs in memory during play, 9 October 2026

[BOOT-VOLUME-NOT-VALIDATED-33](bugs/BOOT-VOLUME-NOT-VALIDATED-33.md): owner decision, the
diagnostic logs (console copy, walk and stall profiles, heap audit, cell and BSP load profiles,
music events and profile, console history) stay in fixed memory buffers (41 KiB in all, oldest
lines drop) and are written at Exit game, after a crash report and with `dbg savelogs`;
`dbg logs live on` or a `--live-logs` image writes them as they happen, as before (benchmarks).
FS-UAE, slow cycle-exact setting: 0 writes in 1,355 s of play (previous engine 6 in 410 s, 3.7 %
of the time "not validated"; 15 % on the fast setting); after a hard kill the volume read
validated. Saves are still written when made.

## TEST-PROFILE-TIMELINE-SUM-33, 9 October 2026

[TEST-PROFILE-TIMELINE-SUM-33](bugs/TEST-PROFILE-TIMELINE-SUM-33.md): a full gate on a busy host
failed the build profile test's sampled-timeline check (2.48 s of timeline CPU against 2.01 s
measured by the stage); the previous commit's gate passed it. Cause not investigated.

## BOOT-VOLUME-NOT-VALIDATED-33 cause measured and repaired in source, 9 October 2026

[BOOT-VOLUME-NOT-VALIDATED-33](bugs/BOOT-VOLUME-NOT-VALIDATED-33.md): measured in FS-UAE. The game
writes to its boot volume from the first second (debug and music logs at start, diagnostic logs,
saves, settings at exit); each write leaves the volume marked not validated for about a second,
15 % of the time while standing in Seyda Neen. Stopping the emulator in such a second makes AmigaOS
validate the volume at the next boot: hidden by the boot countdown with the fast setting, about a
minute with a cycle-exact 68040 at multiplier 14, where the engine's first write (DEBUG.TXT) opened
the request; Retry after the check worked, Cancel stopped the game. Repaired in source on
v0.0.33-boot-validate: the engine waits for the validation before its first write
(`Set AmiWindValidateWait 0` keeps the old start) and a failed debug log no longer stops the game;
checked in FS-UAE with the slow setting, regression tests added.

## BOOT-VOLUME-NOT-VALIDATED-33 registered, 9 October 2026

[BOOT-VOLUME-NOT-VALIDATED-33](bugs/BOOT-VOLUME-NOT-VALIDATED-33.md): owner report from a private
CHIM preview playtest (the v0.0.32 release image with a CHIM development engine) on FS-UAE 3.1.66
with a slow cycle-exact 68040 setting: right after the boot check's "Loading AmiWind v0.0.32",
AmigaOS asked "Volume AMIWIND is not validated" (Retry/Cancel). Cause being measured.

## HORIZON-FLORA-SPRITES-32 default accepted; HORIZON-HOLES-31 not re-checked, 8 October 2026

[BUILD-DOOR-REFERENCE-SERIAL-33](bugs/BUILD-DOOR-REFERENCE-SERIAL-33.md): the door step read the
whole master once per destination cell, about 72 s on one core in interior, census, area and
balmora-interiors; now one pass. [BUILD-ORDERED-WINDOW-33](bugs/BUILD-ORDERED-WINDOW-33.md): the
ordered pool idled behind one slow item (world terrain at 13.9 of 24 cores); four results per
worker now, and a longest-first cost model from item history. Stage-only runs for
[BUILD-IDLE-STAGES-33](bugs/BUILD-IDLE-STAGES-33.md), all byte-identical: balmora 716 -> 268 s,
media 753 -> 258 s, balmora-interiors 904 -> 614 s, actor-contact 346 -> 194 s, bsp 125 -> 53 s
(4 CPUs, busy host).

## BUILD-EXCLUDE-STAGE-CLOSURE-33: quick test builds, 9 October 2026

[BUILD-EXCLUDE-STAGE-CLOSURE-33](bugs/BUILD-EXCLUDE-STAGE-CLOSURE-33.md): gate 650 caught the new
exclusion table in every conversion stage's fingerprint (the stage scheduler imported it) and a
native test that includes `aw_intro.c` without the new marker module. The scheduler, cache and
profiler now read the skipped stages from the build receipt; gate 651 is green.

## CHIM-ZONE-TMP-NOEXEC-33, 9 October 2026

[CHIM-ZONE-TMP-NOEXEC-33](bugs/CHIM-ZONE-TMP-NOEXEC-33.md): the second MiniWind build stopped in the CHIM
stage: the zone walk gate builds a host library in /tmp, which the build container mounts noexec. It is
now built under the CHIM output's work folder.

## BUILD-MINIWIND-FINGERPRINT-ENGINE-33, 9 October 2026

[BUILD-MINIWIND-FINGERPRINT-ENGINE-33](bugs/BUILD-MINIWIND-FINGERPRINT-ENGINE-33.md): gate 585 caught the MiniWind module importing the CHIM tools, which put the
engine sources into every conversion stage's fingerprint (no reuse after an engine edit). The image
step now passes the CHIM removal function in; a regression test guards the module's imports.

## TEST-NATIVE-STALE-IMPORT-33: MiniWind exterior scope, 9 October 2026

[TEST-NATIVE-STALE-IMPORT-33](bugs/TEST-NATIVE-STALE-IMPORT-33.md): while adding the MiniWind exterior scope, a native engine test run on its
own in the builder image failed to compile (no `chim_version.h`): it generated its version headers
with an older tools copy on the image's Python path. The full suite was not affected. The test now
loads this tree's `tools/project_version.py` from its file.

## CHIM-ACTOR-RING-33: NPC companion test, 9 October 2026



## RELEASE-WS-BASELINE-VERSION-33: the whitespace baseline followed VERSION, 9 October 2026



## BUILD-DOOR-REFERENCE-SERIAL-33, BUILD-ORDERED-WINDOW-33; stage repairs measured, 9 October 2026



## NPC-BAKED-WHOLE-DUPLICATION-33: modular NPCs designed and measured, 9 October 2026



## AUDIO-HOST-LOAD-33: crackle on a saturated host, 9 October 2026

[AUDIO-HOST-LOAD-33](bugs/AUDIO-HOST-LOAD-33.md): the owner heard music and sound crackle and snap
throughout CHIM Preview 1 played on a PC whose CPU was at 100 % with build jobs; the same build was
clean on a second, idle PC. Cause: host CPU starvation of the emulator's audio, not game data and not
the in-game loading crackle of [AUDIO-LOAD-29](BUGS.md#music-and-sound-audio). Audio is judged only on
an unloaded host; a controlled idle/loaded A/B on one PC is pending. Checked against the owner's
v0.0.32-dev3 Vivec reports: the floating resident is
[VIVEC-ARENA-FLOATING-NPC-32](bugs/VIVEC-ARENA-FLOATING-NPC-32.md), and the broken transition to the
open world and its flora, and Vivec not being visible from the open world, are
[TOWN-EDGE-UNBUILT-32](bugs/TOWN-EDGE-UNBUILT-32.md); no new entries for them.

## CHIM Engine tracker and found-in-build records; CHIM-RECEIPT-COMMIT-33, 9 October 2026

[NPC-BAKED-WHOLE-DUPLICATION-33](bugs/NPC-BAKED-WHOLE-DUPLICATION-33.md) registered at the owner's
request: the 2,675 humanoid records resolve to 3,500 appearances but only 1,726 distinct body parts
(942 meshes, each part used about 39 times); whole-appearance baking processes 12.3 million source
triangles against 0.40 million in the distinct parts, and the gallery stage takes 2,034 s (6.5 CPU
hours) cold. Design in [MODULAR_NPCS.md](MODULAR_NPCS.md): a parts library with a few quota levels
per part, recipes per appearance, the gallery built from parts (estimate: about 260 s with 4
levels), then one alias model composed per appearance at load time in the engine. Host prototype on
v0.0.33-modular-npc: parts baked once with their outfit quotas reproduce the whole bake (6 of 13
Balmora NPCs byte-identical, the rest within 8 faces); not shipped at the time of writing.

## OPENING-BRIGHT-31, OPENING-JIUB-LANTERN-32 and NPC-LIGHT-COHERENCE-32: the opening scene's light, 9 October 2026

Owner reports on CHIM Preview 1 (v0.0.32 content): the start end of the prison ship should be
about half as bright with a yellow lantern above Jiub, and "the NPC lighting isn't following any
coherence". [OPENING-BRIGHT-31](bugs/OPENING-BRIGHT-31.md): repaired in source with a per-cell
bake profile for the ship (original falloff, facing term, two box zones at the start end); start
views 0.50 of v0.0.32 on average and 0.94 to 1.04 of OpenMW at the same pose.
[OPENING-JIUB-LANTERN-32](bugs/OPENING-JIUB-LANTERN-32.md), new: baked light had no colour and the
lantern's glass is drawn opaque over its candle; baked faces lit mainly by warm lamps now take a
warm lightstyle (the warm colour table, chosen per surface) and the ship's lantern glass glows.
[NPC-LIGHT-COHERENCE-32](bugs/NPC-LIGHT-COHERENCE-32.md), new: characters took the light of the
floor below them; the interior converters now bake an actor light grid and the engine lights
characters by it (Jiub 2.13 times the wall, the original 2.44; Socucius Ergalla 0.65 of the wall,
was 0.35, the original 1.04). Exteriors unchanged. All three repaired in source on
v0.0.33-ship-light, not yet in a built image. [CENSUS-OFFICE-BRIGHT-32](bugs/CENSUS-OFFICE-BRIGHT-32.md), new,
measured on the way: the office walls are about twice as bright as the original's; no repair yet.

## CHIM-TRACE-TAIL-33: a tail of expensive CHIM collision traces, 9 October 2026

[CHIM-TRACE-TAIL-33](bugs/CHIM-TRACE-TAIL-33.md): counted offline during the NPC pathfinding
investigation on format 0.5 Balmora and Seyda Neen frames: most standing-hull traces are cheap, a
few visit thousands of clipnodes (Seyda Neen fan traces: median 171, p90 3,040, mean 2,003 visits).
Cause unknown; engine counter on the cycle-exact preset pending.

## BUILD-IDLE-STAGES-33, BUILD-STAGE-START-SHARE-33 and BUILD-NESTED-POOL-ALLOWANCE-33, 9 October 2026

[BUILD-IDLE-STAGES-33](bugs/BUILD-IDLE-STAGES-33.md): with the profile now comparing cores with
the workers held, the v0.0.32 from-scratch build shows eight scene-chain stages far below their
workers (balmora 2.84 of 12 cores for 510 s, actor-contact 1.39 of 12, bsp 0.98 of 8-12) while the
NPC gallery on the critical path waited for cores. Two scheduler causes:
[BUILD-STAGE-START-SHARE-33](bugs/BUILD-STAGE-START-SHARE-33.md), a pooled stage starting beside
others got `--jobs 1`, so its vis threads stayed at one (bsp: 87.9 s of vis on one thread), and
[BUILD-NESTED-POOL-ALLOWANCE-33](bugs/BUILD-NESTED-POOL-ALLOWANCE-33.md), pool workers inherited
the stage allowance, so each room worker opened its own pool (balmora-interiors at about 16 of 12
cores). Both fixed in source with tests; the per-stage repairs follow on the same branch.

## BUILD-PROFILE-JOBS-START-ONLY-33: idle cores measured against the start allowance, 9 October 2026

[BUILD-PROFILE-JOBS-START-ONLY-33](bugs/BUILD-PROFILE-JOBS-START-ONLY-33.md): the build profile
compared each stage's cores with the workers it started with, but the scheduler rebalances them
within a fraction of a second. In the v0.0.32 from-scratch build balmora started with 1 worker,
held 12 and used 2.84 cores for 510 s; actor-contact, interior, bsp and the Vivec Arena import
likewise; none was flagged as idle. Fixed in source on the build-progress branch: profile rows
record the workers held over time and every comparison uses them; regression tests with those
numbers.
The register now generates a [CHIM Engine tracker](bugs/CHIM_TRACKER.md): every CHIM bug by part,
open first, with the build it was found in and the latest journal changes. A bug is on it when its
`chim` field names its part; CHIM- IDs and the chim-streamer family are marked by `render` and must
carry it (test). Every CHIM bug and every bug found in a numbered build now also records that build:
playtest version, source, engine and world commits, CHIM version and world format
(`set ID --from-build build.json`). Backfilled from the build receipts: v0.0.32-dev1, -dev2, -dev3 and
v0.0.32 with their source commits; builds before v0.0.32-dev1 record no commit (unknown, with that
reason); [CHIM-TEXTURE-SPECKS-33](bugs/CHIM-TEXTURE-SPECKS-33.md) as seen in CHIM Preview 1 (engine
0d8bf4f, world format 0.4). New: [CHIM-RECEIPT-COMMIT-33](bugs/CHIM-RECEIPT-COMMIT-33.md): the CHIM
world receipts do not record the commit the world was built from, so the preview's world commit is
unknown.
Every new `VERSION` failed the release preflight with "trailing whitespace" and "blank line at
EOF" in untouched inherited engine files until a `docs/PATCH-v<VERSION>.json` was made by hand: the
check took its list of exempt historical files from the patch manifest of the version being worked
on. Fixed in source on v0.0.33-ws-baseline, not shipped at the time of writing: the list is
`docs/WHITESPACE-BASELINE.json`, written from the published v0.0.32 tag by
`tools/release.py --whitespace-baseline v0.0.32` (72 files under `engine/aga/` and `docs/aga/`);
only those paths can be exempt, edited files are checked in full, and four of our own files lost
their extra blank lines at the end. Regression tests in `tests/test_release.py`.
[Report](bugs/RELEASE-WS-BASELINE-VERSION-33.md).
[HORIZON-FLORA-SPRITES-32](bugs/HORIZON-FLORA-SPRITES-32.md): the owner, playing v0.0.32-dev3,
called the default horizon (`aw_skyline_fill 0`) excellent; the default method is accepted and the
entry stays open for the experimental skyline fill only.
[HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md): not re-checked on v0.0.32; needs the
across-the-river Balmora view on a v0.0.32 build.

## BUILD-PATH-IN-PAYLOAD-32 and BUILD-STAIR-FLAG-INERT-32, 8 October 2026

[BUILD-PATH-IN-PAYLOAD-32](bugs/BUILD-PATH-IN-PAYLOAD-32.md): the v0.0.32 release image payload
compared with dev3 differed in one file only, `id1/gfx/sky-palette-bank.json`, whose
`shared_sky_source` field holds the build work folder path. Fixed in source on v0.0.33-dev: the
marker names the source relative to the work folder, and the image step refuses payload text files
that contain the build folder path. [BUILD-STAIR-FLAG-INERT-32](bugs/BUILD-STAIR-FLAG-INERT-32.md):
found by the release payload and notes review: v0.0.32's `follow_original_stair_rules` option is
read by no converter; the stair work merged on v0.0.33-dev wires it, and a new test shows the
collision output changing with it.

## CHIM-IMAGE-OPTIMIZER-RECEIPT-33 and the Vivec Arena in CHIM builds, 9 October 2026

[CHIM-IMAGE-OPTIMIZER-RECEIPT-33](bugs/CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): a pure CHIM image would
stop at the final heap gate, because the frame maps and the removed legacy maps no longer match the
optimizer receipt; the receipt now follows the CHIM map set before the gates. Owner decision for
[CHIM-LEGACY-CHAIN-33](bugs/CHIM-LEGACY-CHAIN-33.md): a CHIM build leaves out extra towns that are
not on CHIM yet (the Vivec Arena: exterior maps, region and door tables, harvest catalogues),
recorded per file; the legacy open world stays as "not yet CHIM".

## CHIM-LEGACY-CHAIN-33: CHIM builds and the legacy exterior chain, 9 October 2026

[CHIM-LEGACY-CHAIN-33](bugs/CHIM-LEGACY-CHAIN-33.md): a CHIM build still runs every legacy exterior
stage (the Balmora region maps, the Vivec Arena, the open world), because the CHIM frame maps copy
their actors from the final legacy region maps and the image step needs the open-world overlay and
its town flora. Nothing wrong ships. Now every CHIM build records which legacy stages it still runs
and why, the image step fails if a legacy exterior map of a CHIM area is packed, and a CHIM build
with Seyda Neen takes the recorded v0.0.31 Seyda maps (--seyda-recorded).

## BUILD-CACHE-OVERBROAD-33 and BUILD-CACHE-NO-CUTOFF-33: CHIM builds rerun the scene chain, 9 October 2026

[BUILD-CACHE-OVERBROAD-33](bugs/BUILD-CACHE-OVERBROAD-33.md): owner report: after merges, the
AmiWind "MiniWind" Playtester Builds (v0.0.33-dev1, mw-033a and mw-033c) reran the scene chain although
the changes could not change its outputs; mw-033c reused 3 of 24 stages. Measured per stage and per
fingerprint part: the line still had the first fingerprint method; the narrower one still hashed whole
files, so the MiniWind build plan code in `tools/build_parallel.py` (every stage imports the module for
its worker pool) changed 20 stages, and `ROOT / 'config' / row['config']` counted the whole `config/`
folder. Repaired in development: fingerprint scope `units` (import-time code plus each reached
function), registry-named config files, a call trace in every profiled build; the earlier scopes stay
selectable. [BUILD-CACHE-NO-CUTOFF-33](bugs/BUILD-CACHE-NO-CUTOFF-33.md): a real change to an early
scene stage still reruns every stage after it, even when its outputs come out identical (open).

## CHIM-HULL-STAIR-EDGE-33 and BUILD-REUSE-TMP-UNDECLARED-33: first MiniWind builds, 9 October 2026

[CHIM-HULL-STAIR-EDGE-33](bugs/CHIM-HULL-STAIR-EDGE-33.md): the first AmiWind "MiniWind" Playtester
Build stopped at the CHIM stair gate on Balmora ref 32841, at a chunk edge: the qbsp-compiled
terrain hull was the default for regular ground too. It is the default for irregular ground only
now (from the CHIM builder branch). [BUILD-REUSE-TMP-UNDECLARED-33](bugs/BUILD-REUSE-TMP-UNDECLARED-33.md):
a stage that ran while a reused stage was copied counted the copy's temporary file as its own output
and became non-reusable; the recorder now ignores those temporaries.

## GATE-SOURCE-RACE-33, 9 October 2026

[GATE-SOURCE-RACE-33](bugs/GATE-SOURCE-RACE-33.md): a local gate copied the working tree after its
clean check while a merge was being resolved, and tested conflict markers under a clean commit's
name. The rerun on the untouched tree passed. Fix queued: stage from the committed head.

## CHIM-SEYDA-HUNK-GAP-33 and CHIM-ZONE-RESERVE-EARLY-33, 9 October 2026

[CHIM-SEYDA-HUNK-GAP-33](bugs/CHIM-SEYDA-HUNK-GAP-33.md): Seyda Neen's CHIM map ends its load with a
Hunk gap of 1,099,456 bytes at the default zone (6,864 KiB), under the engine's 2 MiB safety: its
frame map carries all 229 flora sprites and the actors at once (978,288 bytes, against 352,864 for a
legacy region map). The largest zone the rule allows there is 5,888 KiB; Balmora's is the default.
[CHIM-ZONE-RESERVE-EARLY-33](bugs/CHIM-ZONE-RESERVE-EARLY-33.md): `chim_reserve_kib` is checked when
the zone is taken, before the map's entities and per-map allocations load, so it cannot keep the gap.
Measured in FS-UAE on the v0.0.32 release images with the CHIM engine and B's Seyda Neen world.

## CHIM-CHUNK-LOAD-FAIL-33: Balmora chunks without room on the CHIM preview, 9 October 2026

[CHIM-CHUNK-LOAD-FAIL-33](bugs/CHIM-CHUNK-LOAD-FAIL-33.md): in the owner's playtest of the private CHIM
preview, Balmora chunks failed to load ("zone full or bad data"), never recovered, left areas without
buildings or ground, and the player fell through. Reproduced in FS-UAE at the owner's poses with the same
chunk numbers. Not bad data: the world reads back whole. The zone (6,864 KiB) held up to 6.1 MB locked;
1.2 MB were free but in pieces of at most 211 KB while the ring's house models decode to 258-291 KB.
Chunks stay locked out to the load radius (892 units), past the 636-unit ring the heap gate counts, and
a chunk's ground waits for every model it places. Related: CHIM-ZONE-BUDGET-33, CHIM-ZONE-RING-THRASH-33.
Repaired in source on v0.0.33-chim-chunkload: a loading chunk keeps its own parts locked (the first method
evicted them and loaded for ever), a chunk short of room releases farther chunks, a chunk whose model has no
room is activated without it (ground and collision stay), small blocks come from the zone's high end. Each
method is a cvar (0: the first method). The engine's own zone allocator over the owner's route (simulation):
holes under the player 860 to 0, model loads 1,010,584 to 997; in FS-UAE the nearest chunk without ground
stays 438 units away (69 before; collision margin 224). New builder gate: the zone walk
(`tools/chim/zone_sim.py`).

## CHIM-FAR-TERRAIN-33: no distant ground on CHIM, 9 October 2026

[CHIM-FAR-TERRAIN-33](bugs/CHIM-FAR-TERRAIN-33.md): an owner playtest of CHIM Preview 1 found that a
CHIM frame has no distant ground. Past the active ring the land is missing, valleys look empty and
Vivec is not visible from the world. This is a release blocker for v0.0.33: the CHIM distant view
must be at least as good as v0.0.32's HORSTATOR APPROVED horizon.

## Last failing stair flights were gate artefacts, 9 October 2026

[STAIRS-BALMORA-B01-32](bugs/STAIRS-BALMORA-B01-32.md),
[STAIRS-BALMORA-WESTSOUTH-32](bugs/STAIRS-BALMORA-WESTSOUTH-32.md),
[STAIRS-SEYDA-WAREHOUSE-32](bugs/STAIRS-SEYDA-WAREHOUSE-32.md) and
[STAIRS-ADDAMASARTUS-32](bugs/STAIRS-ADDAMASARTUS-32.md): fixed in source on branch
v0.0.33-stairs-2. Measured on the meshes and maps, none was a collision fault: B01's walk started
inside the authored collision ramp and settled from inside a low arch lintel (the column between
is free); the warehouse tower's start box touched the curved wall within the collision plate's
0.2 thickness; Western Guard Tower South's flight ends at a closed hinged door (AW-20260928-12);
the Addamasartus "step" is two tilted cave-floor triangles sharing an edge. The gate
(`tools/stair_walk.py`, shared by the legacy image step and CHIM) now reads a riser as a drop at
the shared edge, settles from the free part of the start column, and treats starts and walks that
meet visible geometry within the plate thickness as untestable (sideways retries first).
Rebuilt legacy maps with the rule: 5 gating failures -> 0; CHIM Balmora 1 -> 0; no passing
flight step lost. [STAIRS-SEYDA-LIGHTHOUSE-32](bugs/STAIRS-SEYDA-LIGHTHOUSE-32.md): exterior fixed
by the slanted-riser cut (c1f4d87), interior step untestable (the straight line meets the
lighthouse wall). Regression fixtures: `tests/test_stair_walk_cases.py`.

## CHIM-SEYDA-MEMORY-33: Seyda Neen's ring, cause found, 8 October 2026

[CHIM-SEYDA-MEMORY-33](bugs/CHIM-SEYDA-MEMORY-33.md): Seyda Neen's modelled CHIM ring (6,536,720
bytes) exceeded Balmora's because the irregular ground's standing hull was built as routed chains of
small prisms (107,506 clipnodes in the ring). Compiled by qbsp instead: 11,984 clipnodes, ring
5,683,920 bytes, within the engine's 6,096 KiB chunk room. Fixed in source, not shipped.

## CHIM visibility rows: slow on irregular ground, rebuilt per worker count, 8 October 2026

[CHIM-PVS-SLOW-33](bugs/CHIM-PVS-SLOW-33.md): Seyda Neen's visibility rows took 331 s (961 CPU s,
3 workers) and were rebuilt because the worker count had changed. Fixed in source: fixed block
count, 8-unit plane lookup for irregular ground.

## CHIM heap gate: the zone default is too small for Seyda Neen, 8 October 2026

[CHIM-ZONE-BUDGET-33](bugs/CHIM-ZONE-BUDGET-33.md): the strict CHIM heap gate (the engine's own
active-ring rule, every 64 units) finds Seyda Neen's ring at 6,536,720 bytes and Balmora's
south-west corner at 6,239,776, against 5,767,168 at the engine default `chim_zone_kib` 6,656 KiB.
Interim budget 7,680 KiB in the builder and the engine (owner decision pending); a world-stated
zone is proposed.

## CHIM-TEXTURE-SPECKS-33: owner playtest, gate and opt-in effect, 9 October 2026

[CHIM-TEXTURE-SPECKS-33](bugs/CHIM-TEXTURE-SPECKS-33.md): the owner's playtest of a CHIM preview
build showed bright orange and cream specks all over Balmora, glowing at dusk. That build's CHIM
world was made before the repair of 8 October: 858 texels in 86 of 176 textures still sat on the
image's seven sky-bank entries. FS-UAE A/B/C/D at six poses (legacy maps, the preview world, the
repaired world on the same image, the preview world without entities): only the preview world
specks; the repaired world matches legacy. The CHIM validator now refuses texels on the sky bank,
and the look is kept as the first opt-in CHIM texture effect, `autumn_glitter_leaves`
([CHIM texture effects](chim/TEXTURE_EFFECTS.md)).

## RELEASE-PATCH-SIZE-33, 8 October 2026

[RELEASE-PATCH-SIZE-33](bugs/RELEASE-PATCH-SIZE-33.md): the whitespace baseline for v0.0.33-dev1
(1,811 files of the published v0.0.32) passed the 256 KiB text limit of the release preflight. The
baselines get a named 1 MiB limit and the early-warning test. The `--accept-known-stair-findings`
builder option is classified as a private test waiver in the defaults test.

## ENGINE-FPU-DATA-DECODE-33, 8 October 2026

[ENGINE-FPU-DATA-DECODE-33](bugs/ENGINE-FPU-DATA-DECODE-33.md): after the CHIM engine merge the
engine stage stopped on three `fintrz` instructions reported in `AW_ModelVisible`. They were a
pointer table in `.text` decoded as instructions; the FPU check now ignores decoded opcodes inside
relocated longwords. The v0.0.33-dev1 whitespace baseline `docs/PATCH-v0.0.33-dev1.json` (published
v0.0.32) was added, as for earlier versions.

## BUILD-ENV-FINGERPRINT-GLOBAL-33, merges for v0.0.33-dev1, 8 October 2026

[BUILD-ENV-FINGERPRINT-GLOBAL-33](bugs/BUILD-ENV-FINGERPRINT-GLOBAL-33.md): the v0.0.33-dev1
build reused 0 of 34 stages from the v0.0.32 release run, because the stair rule setting is an
environment variable that goes into every stage's fingerprint, so stages that never read it
rebuild as well. The CHIM builder's tracker entries merged for v0.0.33-dev1 (SEYDA-REGIONS-PIN-33,
CHIM-HIDDEN-FACES-33, CHIM-STAIRGATE-SLOW-33, CHIM-ZONE-BUDGET-33) got their fact fields.
The image step's stair gate now takes the same private-test option as the CHIM stage
(`--accept-known-stair-findings ID`, -devN only, recorded in `stair-walk.json`); the five open
STAIRS-*-32 findings are listed in `config/known-stair-findings.json` with their placements.

## BUILD-CACHE-CLOSURE-WIDE-33 and BUILD-CACHE-ABSOLUTE-PATHS-33: stage reuse, 9 October 2026

Found while making `--reuse-from` keep what it should (the v0.0.33-dev1 pre-warm reused 0 of 34
stages). [BUILD-CACHE-CLOSURE-WIDE-33](bugs/BUILD-CACHE-CLOSURE-WIDE-33.md): fingerprints counted
every module any imported module could import, and whole top folders of data; the media stage
covered 157 modules and 569 data files. [BUILD-CACHE-ABSOLUTE-PATHS-33](bugs/BUILD-CACHE-ABSOLUTE-PATHS-33.md):
fingerprints held absolute paths, so reuse needed the checkout and workspace at the old run's
paths. Repaired in source on v0.0.33 development: fingerprints follow the code a stage can reach
and the environment variables it names, locations become tokens, and a read trace in every
profiled build marks a stage not reusable when it read a file its fingerprint left out. The stair
rule part of the same symptom is BUILD-ENV-FINGERPRINT-GLOBAL-33, registered on the v0.0.33-dev1
build line; this change repairs it too.
[BUILD-CACHE-TRACE-PYTHONPATH-33](bugs/BUILD-CACHE-TRACE-PYTHONPATH-33.md): gate 450 found that
the new read trace refused reuse of an already reused run when another checkout was on
`PYTHONPATH` (the builder's own modules counted as outside code); repaired before merge, with a
test in the gate's layout. No stale output was involved.

## DOCS-TOC-RENDER-FIGHT-33; v0.0.33-bug-fields merged, 8 October 2026

The bug fact fields are merged on v0.0.33-dev with the post-release branches; every bug from the
v0.0.30 series on carries its facts (the hand tables of the v0.0.32 release pages imported, six
bugs completed by hand). [DOCS-TOC-RENDER-FIGHT-33](bugs/DOCS-TOC-RENDER-FIGHT-33.md): after the
merge, the contents-list writer and the register renderer moved each other's blocks on eight bug
pages; fixed in source (the list goes after a generated block under the title), with cross-tool
tests.

## TRACKER-REGISTER-SIZE-33: the bug register outgrew the release text limit, 8 October 2026

With the bug facts on every entry, `docs/bugs/bugs.json` grew to 320,196 bytes and the release
preflight refused it (text files at most 262,144 bytes). Repaired in source on v0.0.33-bug-fields,
not shipped at the time of writing: `tools/release.py` names a 1 MiB limit for `docs/bugs/bugs.json`
and `docs/BUGS.md` only; a tracker test fails at 75 % of each tracker file's limit. Alternative noted:
one register file per version series. [Report](bugs/TRACKER-REGISTER-SIZE-33.md).

## DOCS-DEAD-ANCHORS-32 and TEST-PROFILE-STAGE-WALL-32, 8 October 2026

[DOCS-DEAD-ANCHORS-32](bugs/DOCS-DEAD-ANCHORS-32.md): checking the new contents-list anchors
against the existing links found seven links (five documents) pointing at headings renamed or
removed since at least v0.0.29. Fixed in source on v0.0.33-doc-toc (ef3c33c), not shipped at the
time of writing: the links point at the current sections and `tools/doc_toc.py check` now fails on
any same-repository `#anchor` link without a matching heading.
[TEST-PROFILE-STAGE-WALL-32](bugs/TEST-PROFILE-STAGE-WALL-32.md): gate 370 failed the build
profile stage test with the host at 100 % CPU ("2.06 not less than 1.936": wall time compared
with CPU time). Fixed in source on v0.0.33-doc-toc (1d7b743), not shipped at the time of writing:
the test compares the profiler with independent readings of the same stage; under load (2 CPUs,
8 busy loops) the old test failed 5 of 5, the new one passes 10 of 10 and still fails a sampler
that ignores child processes. Same family as TEST-PROFILE-SECTION-CPU-32 (timing tests on a busy
host).

## Stair gate merged on v0.0.33-dev; BUILD-NAME-MOJIBAKE-32 closed as a duplicate, 8 October 2026

[COLLISION-STAIR-SLOPE-32](bugs/COLLISION-STAIR-SLOPE-32.md): the stair rule, switch and stair
walkability gate are merged on v0.0.33-dev. A legacy image build from v0.0.33-dev stops at the gate
until the five flights [STAIRS-BALMORA-B01-32](bugs/STAIRS-BALMORA-B01-32.md),
[STAIRS-BALMORA-WESTSOUTH-32](bugs/STAIRS-BALMORA-WESTSOUTH-32.md),
[STAIRS-SEYDA-WAREHOUSE-32](bugs/STAIRS-SEYDA-WAREHOUSE-32.md),
[STAIRS-SEYDA-LIGHTHOUSE-32](bugs/STAIRS-SEYDA-LIGHTHOUSE-32.md) and
[STAIRS-ADDAMASARTUS-32](bugs/STAIRS-ADDAMASARTUS-32.md) are repaired.
[BUILD-NAME-MOJIBAKE-32](bugs/BUILD-NAME-MOJIBAKE-32.md) closed: duplicate of
[BUILD-MOJIBAKE-32](bugs/BUILD-MOJIBAKE-32.md), registered separately on two lines before they met.

## Seyda Neen on CHIM: first world, stair gate and findings, 8 October 2026

The CHIM builder regenerates Seyda Neen's exterior (format 0.5) and validates it, but the
stair gate fails: the rule does not clear the exterior lighthouse
([STAIRS-SEYDA-LIGHTHOUSE-32](bugs/STAIRS-SEYDA-LIGHTHOUSE-32.md): five flight steps; after the
step up the box lands on the next riser's sloped plate). New:
[SEYDA-REGIONS-PIN-33](bugs/SEYDA-REGIONS-PIN-33.md) (the recorded region table has 700-unit
overlaps, the layout writes 896; the table had one copy, now kept privately with a manifest),
[CHIM-HIDDEN-FACES-33](bugs/CHIM-HIDDEN-FACES-33.md) (CHIM draws placed-model faces under the
terrain that the recorded region maps cull; to be measured),
[CHIM-STAIRGATE-SLOW-33](bugs/CHIM-STAIRGATE-SLOW-33.md) (over 10 minutes on the Balmora and
Arena world).

## Stairs follow Morrowind's rules, and a gate walks them, 8 October 2026

[COLLISION-STAIR-SLOPE-32](bugs/COLLISION-STAIR-SLOPE-32.md): owner order, stairs follow the
original rules in the next build. Source on branch v0.0.32-stair-walk: a stair rule in the shared
collision layer (convex pieces that bury stair treads become the authored plates; plate meshes
with stairs get exact bevels), the `follow_original_stair_rules` switch (on by default) reaching
every converter, and an image-step gate that walks every flight of stairs of every map up and
down with the engine's step (8.5) and slope (0.69) rules. On the v0.0.32-dev2 maps the gate finds
158 failing flight steps (140 in the dev1 Arena, fixed by VIVEC-ARENA-ACTORS-32); five staircases
still fail with the rule: [STAIRS-BALMORA-B01-32](bugs/STAIRS-BALMORA-B01-32.md),
[STAIRS-BALMORA-WESTSOUTH-32](bugs/STAIRS-BALMORA-WESTSOUTH-32.md),
[STAIRS-SEYDA-WAREHOUSE-32](bugs/STAIRS-SEYDA-WAREHOUSE-32.md),
[STAIRS-SEYDA-LIGHTHOUSE-32](bugs/STAIRS-SEYDA-LIGHTHOUSE-32.md),
[STAIRS-ADDAMASARTUS-32](bugs/STAIRS-ADDAMASARTUS-32.md). Also new:
[COLLISION-SEYDA-PREVIEW-BYPASS-32](bugs/COLLISION-SEYDA-PREVIEW-BYPASS-32.md),
[BUILD-NAME-MOJIBAKE-32](bugs/BUILD-NAME-MOJIBAKE-32.md).

## UI-MENU-LOGO-32, 8 October 2026

[UI-MENU-LOGO-32](bugs/UI-MENU-LOGO-32.md): the menu logo showed a line above the name and
reddish-pink letters. The builder used the wordmark (rule above the name) and matched its gold to
the nearest colours of the whole game palette, which has no saturated gold: 424 of 1,377 letter
pixels in dev3 landed on the reserved status-bar slots, mean hue 26 degrees. Fixed in source: the
name-only logo on the palette's own gold ramp, never a reserved UI slot or sky bank entry, no rule
(an optional rule only below); `--menu-logo legacy` keeps the old method. Startup screen unchanged.

## PHOTO-DEBUG-STRIP-33, 8 October 2026

[PHOTO-DEBUG-STRIP-33](bugs/PHOTO-DEBUG-STRIP-33.md): found in the first in-game check of
photo mode: with Ctrl+H (`dbg hud`) the coordinate strip blacked out only from x=88, leaving
the bottom-left corner of the full-screen view beside it. Fixed in source on
v0.0.33-photomode, not shipped at the time of writing: in photo mode the strip spans the full
width and the input hint is not drawn. Native HUD test and an in-game frame.
[PHOTO-GALLERY-TEXT-33](bugs/PHOTO-GALLERY-TEXT-33.md): the second in-game check, in
`dbg torchtest`, showed the room's instruction lines over the photo mode view. Fixed in source
on v0.0.33-photomode, not shipped at the time of writing: gallery and test-room text is not
drawn in photo mode.

## QC-AW-FLAME-SPAWN-32 and CENSUS-LOAD-SLOW-32: repaired in source, A/B/C/D, 8 October 2026

[QC-AW-FLAME-SPAWN-32](bugs/QC-AW-FLAME-SPAWN-32.md): the game logic now declares
`aw_flame_size`, `aw_flame_shape` and the worldspawn `wad` key and spawns `aw_flame` by removing it,
as id's `info_null` does; the engine's static-flame table still reads the map text. New
`tests/test_entity_spawn_contract.py` checks every converter classname and key against the game
logic. [CENSUS-LOAD-SLOW-32](bugs/CENSUS-LOAD-SLOW-32.md): cause confirmed in one FS-UAE container
(busy host, relative numbers): dev3 Census 8.8-20.9 s with the remote console on, 0.13-0.16 s off;
with the repaired game logic 0.20-0.41 s on, 0.12-0.22 s off.

## CENSUS-LOAD-SLOW-32 cause; REMOTE-CONSOLE-LOG-COST-32 and DEBUG-TP-SHIP-FREEZE-32, 8 October 2026

[CENSUS-LOAD-SLOW-32](bugs/CENSUS-LOAD-SLOW-32.md): cause confirmed in one FS-UAE container (busy host,
relative numbers): dev3 Census 8.8-20.9 s with the remote console on, 0.13-0.16 s off; normal play is not
affected. New: [REMOTE-CONSOLE-LOG-COST-32](bugs/REMOTE-CONSOLE-LOG-COST-32.md) (each console line costs
about 7-18 ms with the remote console on; test sessions only) and
[DEBUG-TP-SHIP-FREEZE-32](bugs/DEBUG-TP-SHIP-FREEZE-32.md) (one freeze on `dbg tp balmora` 6 s after
`dbg tp prisonship`, not reproduced in two more attempts). The game logic repair for
[QC-AW-FLAME-SPAWN-32](bugs/QC-AW-FLAME-SPAWN-32.md) is in source on a later branch, not in v0.0.32.

## v0.0.32-dev3 owner play reports, 8 October 2026

[VIVEC-ARENA-WATER-FALL-32](bugs/VIVEC-ARENA-WATER-FALL-32.md): east of the Arena canton the sea
ends at the canton edge; sky is drawn below the horizon (LOCAL 1076 -150 65) and the player falls
out of the area through the water (LOCAL 1374 165 -212). Cause unknown.
[VIVEC-ARENA-FLOATING-NPC-32](bugs/VIVEC-ARENA-FLOATING-NPC-32.md): a resident by the Telvanni
canton stands at a walkway end with sky below his feet (seen from LOCAL 1185 -59 117); the actor
ground check passed, as it checks collision contact only. Cause unknown.
[WAIT-NOCLIP-MESSAGE-32](bugs/WAIT-NOCLIP-MESSAGE-32.md): with noclip on, T shows the combined
"after registration, on dry ground, when no one is speaking" refusal; the refusal follows the
original game (no waiting in the air), the message should name the reason that applied. Seen in
earlier builds too. All three: owner decision fix later; known in v0.0.32.
[VIVEC-ARENA-FRAME-EDGE-32](bugs/VIVEC-ARENA-FRAME-EDGE-32.md): owner pose LOCAL 1067 -819 159
(St. Olms side): a slab ends in darkness; the Arena preview is an isolated frame, not connected to
the world. [TOWN-EDGE-UNBUILT-32](bugs/TOWN-EDGE-UNBUILT-32.md): owner pose GLOBAL 42527 -94856
794 (Ascadian Isles, south of the Vivec frame): bare flat grey ground with a straight edge and no
flora after leaving the Vivec area; ship as is, CHIM M3/M4.

[VIVEC-CANTON-SKY-HOLE-32](bugs/VIVEC-CANTON-SKY-HOLE-32.md): in an owner screenshot the sky shows through a
canton wall seen from below, with misordered pieces where walls meet; pose not recorded; ship as is.

[VIVEC-DISTANT-BRIDGES-32](bugs/VIVEC-DISTANT-BRIDGES-32.md): in an owner screenshot from a canton top the
bridges between distant cantons are not drawn; pose not recorded; ship as is.

Stair walkability findings on the v0.0.32-dev2 maps, registered on a development branch whose gate
is not in v0.0.32, brought into the v0.0.32 register because they describe the shipped maps:
[COLLISION-STAIR-SLOPE-32](bugs/COLLISION-STAIR-SLOPE-32.md),
[STAIRS-BALMORA-B01-32](bugs/STAIRS-BALMORA-B01-32.md),
[STAIRS-BALMORA-WESTSOUTH-32](bugs/STAIRS-BALMORA-WESTSOUTH-32.md),
[STAIRS-SEYDA-WAREHOUSE-32](bugs/STAIRS-SEYDA-WAREHOUSE-32.md),
[STAIRS-SEYDA-LIGHTHOUSE-32](bugs/STAIRS-SEYDA-LIGHTHOUSE-32.md),
[STAIRS-ADDAMASARTUS-32](bugs/STAIRS-ADDAMASARTUS-32.md) and
[COLLISION-SEYDA-PREVIEW-BYPASS-32](bugs/COLLISION-SEYDA-PREVIEW-BYPASS-32.md). The `--name`
message mojibake found by the same work is [BUILD-MOJIBAKE-32](bugs/BUILD-MOJIBAKE-32.md).

## v0.0.32-dev3 smoke test findings, 8 October 2026

One FS-UAE session of the dev3 image (built from source 91a7eeb). New:
[QC-AW-FLAME-SPAWN-32](bugs/QC-AW-FLAME-SPAWN-32.md) (every `aw_flame` entity prints "not a field"
twice, "No spawn function" and an edict dump: the game logic has no `aw_flame` spawn function or
fields; 51 per Census office load, 8 per prison ship load),
[CENSUS-LOAD-SLOW-32](bugs/CENSUS-LOAD-SLOW-32.md) (Census office "Scene ready" 7,816 and
10,320 ms against 0.2-1.5 s elsewhere; load time follows the flame count, likely the console
output above written line by line to the session logs; A/B pending) and
[DEBUG-MAP-SAVE-VALIDATION-32](bugs/DEBUG-MAP-SAVE-VALIDATION-32.md) (after `map vf0291`,
`vf2386`, `vf2485` the autosave fails validation; two also report "Interior spawn blocked").
Evidence added to [AW-20260928-01](bugs/AW-20260928-01.md): prison 1,530 ms, ship to deck 309 and
364 ms, no slow transition in this session. "FPU support: none (CPU 68040)" without a
68040.library is the documented state ([FPU support library](FPU_SUPPORT_LIBRARY.md)).

## CHIM-ZONE-RING-THRASH-33 and CHIM-REBUILD-COST-33: emulator sweep, 8 October 2026

[CHIM-ZONE-RING-THRASH-33](bugs/CHIM-ZONE-RING-THRASH-33.md): fixed in source on
v0.0.33-chim-format-engine (41386bc), not shipped at the time of writing: a 6.5 MiB zone plus two
512 KiB frame-world slots reserved at map start. An 8-chunk walk and back read 1.9 MB instead of
41 MB, 338 evictions instead of 6,651, no failed rebuilds, and the long jump lands.
[CHIM-REBUILD-COST-33](bugs/CHIM-REBUILD-COST-33.md): one rebuild per crossing costs 0.7-3.5 ms
under JIT but 95-184 ms for 30-40 chunks in a cycle-exact run, a visible hitch on a 68040
(relative numbers); next: an incremental frame-world pool.

## CI-BOOTSTRAP-NUMPY-32, 8 October 2026

GitHub CI on main 5e97310 failed at the tool bootstrap: tools/build.py imported numpy through the
scenery reduction option helpers before the tools existed. numpy is now loaded on first use; a new
test runs the builder with every third-party module blocked.

## HEAP-SEYDA-OVERLAP-32: temporary pre-CHIM heap bypass for three Seyda Neen maps, 8 October 2026

The from-scratch build dev3-r2 stopped at the strict heap gate on the recorded maps sn019, sn026
and sn035 (modelled reserve allowance only, worst -238,180 bytes). Owner decision A: v0.0.32 ships
them through a temporary pre-CHIM bypass, `config/heap-bypass.json` (name and SHA-256, legacy
builder only), recorded in the heap receipts and `build.json`; a temporary bypass for the legacy
builder, removed when Seyda Neen moves to CHIM (M2). Everything else stays strict.
[Report](bugs/HEAP-SEYDA-OVERLAP-32.md).

## Morrowind collision census, 8 October 2026

Where Morrowind keeps its collision and how the converter uses it:
[COLLISION_MESHES.md](COLLISION_MESHES.md). 2,680 of the base game's 5,798 NIFs carry an authored
`RootCollisionNode`; the authored collision of every measured stair is a ramp of at most 45
degrees. New: [COLLISION-RCN-SCOPE-32](bugs/COLLISION-RCN-SCOPE-32.md) (the Seyda Neen exterior
and every non-`i/` model in converted rooms collide with their visual mesh, not the authored
collision) and [COLLISION-NC-FLAGS-32](bugs/COLLISION-NC-FLAGS-32.md) (NC, NCC, MRK and AvoidNode
flags are ignored, so banners, tapestries, rugs and similar props are solid).

## First FS-UAE session of Balmora under CHIM, 8 October 2026

On the five benchmark cameras CHIM draws far fewer world faces and clip nodes than the legacy maps
and roughly halves the frame time (JIT, busy host, relative), and doors work both ways
([CHIM-VIEW-FACES-33](bugs/CHIM-VIEW-FACES-33.md)). New:
[CHIM-TEXTURE-SPECKS-33](bugs/CHIM-TEXTURE-SPECKS-33.md) (bright single-texel specks in CHIM
textures), [CHIM-ZONE-RING-THRASH-33](bugs/CHIM-ZONE-RING-THRASH-33.md) (the ring does not fit
the 6 MiB zone; 64 failed frame-world rebuilds).

## Vivec Arena arrival and owner dev1 reports, 8 October 2026

[VIVEC-ARENA-TP-ARRIVAL-32](bugs/VIVEC-ARENA-TP-ARRIVAL-32.md): cause found and fixed in source
(branch v0.0.32-vivec-arrival). The Arena arrival starts inside the Waistworks entrance top; in
dev1 the canton's convex fill blocked every nearby spot, and Quake's stuck recovery then moved the
player to the stale `oldorigin` 0 0 0, the frame origin under the sea. Arrivals are now stored as
the engine search's standing spot on the converted collision (every town), the engine falls back
to the scene spawn point and never to water, `dbg unstuck` finds the nearest clear spot, and the
image step checks every town arrival on the final maps. The owner's other dev1 Arena reports
(floating outflow, missing exterior, stairs, stuck walkway, noclip refused, hanging pieces,
St. Delyn without walls) are the two causes of
[VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md), already fixed in source; no mirrored
placement is involved. New: [VIVEC-ARENA-FRAME-EDGE-32](bugs/VIVEC-ARENA-FRAME-EDGE-32.md)
(neighbouring canton bodies end at the frame edge, in view).

## TEST-PROFILE-SECTION-CPU-32, 8 October 2026

The full gate failed one build profile test on a loaded host: two 0.05 s section calls read
0.08 s because `os.times()` counts whole clock ticks. The test now allows for the tick
resolution. [Report](bugs/TEST-PROFILE-SECTION-CPU-32.md).

## BUILD-EXTRA-TOWN-OPTIN-32: the Vivec Arena preview leaves the default build, 8 October 2026

Found by the CHIM builder's payload measurement of v0.0.32-dev1: the Arena that v0.0.32 ships
was built only with `--extra-town vivec_arena`, and the payload check found 19 Arena files no
release feature explains. Fixed in source: towns marked `shipped_since` in `config/towns.json`
are built by default (`--no-extra-town` / `--only-core-towns` debugging opt-outs), a release
feature `extra-towns` follows the town table, and the v0.0.32 classes are recorded.
[Report](bugs/BUILD-EXTRA-TOWN-OPTIN-32.md).

## KEYS-AMIGA-EDIT-32: Del arrived as F11, FS-UAE Home/End as keypad ( and Help, 8 October 2026

Found while adding terminal editing to the console. The raw-key table read the Amiga Del key as
F11, so the documented "Delete clears a control" never worked; FS-UAE sends a PC keyboard's Home
and End as keypad `(` and Help, and Insert as the key left of Return (read as Enter). Fixed in
source: Del is Delete, and the FS-UAE presets send Home/End as unused keys 0x6A/0x6C that the game
reads as Home/End. Insert unchanged and documented. [Report](bugs/KEYS-AMIGA-EDIT-32.md).

## BUILD-DRESSING-EXCLUDED-32: Census office lantern hook, silent converter drops, 8 October 2026

The one entity v0.0.32-dev1's Census office lacks against v0.0.31 is a lantern hook (reference
321381). The mesh converter skips lantern hooks, ropes and similar dressing unless the caller retains
dressing, without listing them in the receipt; v0.0.31's census was not builder-made. The entity
tracker did not fail: the guided build passed no baseline and its gate tolerated small losses.
Prevention in source: every omission receipted; per-cell placement digests; the v0.0.31 release
baseline is compared by default. Owner decision A: the Seyda Neen interiors keep their dressing
(six pieces back: two lantern hooks, two ferns, two grass tufts), `--skip-dressing` keeps the
earlier rule, and `dressing-track.json` lists every placed piece per map with its heap estimate.
[Report](bugs/BUILD-DRESSING-EXCLUDED-32.md).

## AW-20260928-01: ship-to-deck transition sluggish again, 8 October 2026

Owner report on dev1/dev2 (FS-UAE 3.1.66, Ubuntu 24.04): "scene clearing from prison ship to the
deck; sometimes on FS-UAE seems absolutely sluggish". Same transition as the September hatch
freeze; cause unknown. Next: measure the "Scene ready" time and bytes read, cold and warm, on dev3.
[Report](bugs/AW-20260928-01.md).

## CONSOLE-HISTORY-ARROWS-32: owner trace shows the arrows arriving, 8 October 2026

The owner's `aw_input_trace 1` on dev1: Up and Down reach the game as raw 76 and 77 with qualifier
32768 (mouse grabbed). The same keys, order and qualifier in FS-UAE on dev1 recall history, and a
native replay passes, so neither the qualifier nor the emulator is the cause on his machine. Most
likely the empty-line state of CONSOLE-HISTORY-EMPTY-32 (fixed in source); to be checked on the
next build. A keyboard joystick on port 1 would swallow the arrows (no trace line); all shipped
presets set `joystick_port_1 = none`. [Report](bugs/CONSOLE-HISTORY-ARROWS-32.md).

## FLAME-RANGE-NEAREST-32: Census office hearth fire only up close, 8 October 2026

Owner report on dev1: the Census and Excise Office fireplace shows no fire until the player is right
next to it. The static flame budget (12 flames within 640 units) took the nearest flames in any
direction; 14 candles, 10 of them behind the camera, were nearer than the hearth. Same in v0.0.31
(identical flames and code). Repaired in the engine: flames on screen, ranked by drawn size over
distance; the earlier rule stays as `aw_static_flames_nearest 1`.
[Report](bugs/FLAME-RANGE-NEAREST-32.md).

## CHIM parity and terrain hull fixes; test import path, 8 October 2026

Fixed in source on the CHIM branch, not merged:
[CHIM-PAYLOAD-PARITY-33](bugs/CHIM-PAYLOAD-PARITY-33.md) (Balmora 1,473 statics, two-way frame-map
gate passes; two open requirements: frame origin and harvest representation) and
[CHIM-TERRAIN-HULL-BEVELS-33](bugs/CHIM-TERRAIN-HULL-BEVELS-33.md) (exact standing hull, tighter
seam check, format stays 0.4). [TEST-WORKER-SYSPATH-32](bugs/TEST-WORKER-SYSPATH-32.md): a second
case in the test process itself makes `test_actor_ground` fail to import after modules that put
`tools/` before `src/`.

## Vivec dev1 owner evidence and CHIM terrain edges, 8 October 2026

Owner evidence from real play of dev1: a Vivec canton sewer outflow floats without its canton
(the frame-by-origin bug, fixed in source by the footprint rule:
[VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md)), and `dbg tp vivec_arena` always lands at
the frame origin under the water, a v0.0.32 blocker
([VIVEC-ARENA-TP-ARRIVAL-32](bugs/VIVEC-ARENA-TP-ARRIVAL-32.md)). New:
[CHIM-TERRAIN-HULL-BEVELS-33](bugs/CHIM-TERRAIN-HULL-BEVELS-33.md) (a standing box rests up to 8
units above convex CHIM terrain edges). Feature in progress, not a bug: `dbg daynight off`/`on`
to freeze the time at midday (owner request).

## CHIM harvest and payload parity findings, 8 October 2026

The CHIM Balmora statics match the pre-image region maps, but the image step later removes 20
harvest mushroom statics and adds 5 town flora references that the CHIM world does not see; a
per-area parity gate is in progress. A town-wide CHIM harvest catalogue would break the name and
size limits, so CHIM keeps the per-region catalogues. Frame maps carry only worldspawn, the
`aw_npc` entities and one `info_player_start`. New:
[CHIM-PAYLOAD-PARITY-33](bugs/CHIM-PAYLOAD-PARITY-33.md),
[CHIM-HARVEST-NAMING-33](bugs/CHIM-HARVEST-NAMING-33.md). Updated:
[CHIM-FRAME-WORLD-BOUNDS-33](bugs/CHIM-FRAME-WORLD-BOUNDS-33.md).

## BUILD-SEYDA-RECORDED-REWRITTEN-32: traced and repaired in source, 8 October 2026

The dev1 rewrites of the recorded Seyda Neen maps were the actor ground bake (one placement,
reference 128961, re-fitted by 0.0067 units in 64 region maps) and the builder's fallback-alias copy
over `seyda.bsp`; the sky and hidden-surface passes left them unchanged. The exception is now the
builder option `--seyda-recorded` (`tools/recorded_stage.py`, pinned by
`config/seyda-recorded-v0.0.31.json`): later passes skip the recorded maps and a check after every
map pass stops the build on any difference. `seyda.bsp` ships as the sn029 alias, the one named
difference (owner option A: the complete town fails the release actor gate).
[Report](bugs/BUILD-SEYDA-RECORDED-REWRITTEN-32.md).

## HORIZON-FLORA-SPRITES-32: cause measured, land-outline horizon default, 8 October 2026

The Seyda Neen castle and wall are the skyline fill (`aw_skyline_fill`, added in v0.0.31-dev5,
shipped on in v0.0.31): sky below far fogged scenery takes the fog colour. The v0.0.31 engine draws
the same at both owner poses on the same data; `aw_skyline_fill 0` removes the columns. The game
config now selects 0, `aw_horizon_migrate` resets saved configs once, and the silhouetting stays
selectable: experimental and buggy (sprites need their shapes from the alpha channel), tested but
subpar results, kept for future improvement. [Report](bugs/HORIZON-FLORA-SPRITES-32.md).

## FOG-TOWN-HEAVY-32: fog settings identical to v0.0.31, 8 October 2026

`fog-locations.txt`, the game configs, palette, fog and sky lookups and the 540 town fog distance
equal v0.0.31; location fog is off by default. The Seyda Neen silhouettes are the skyline fill
(HORIZON-FLORA-SPRITES-32). The Arena canton is larger than the 540 fog band (HORIZON-HOLES-31); a
longer Arena distance is an owner decision. [Report](bugs/FOG-TOWN-HEAVY-32.md).

## HORIZON-FLORA-SPRITES-32: owner decisions and planned improvements, 8 October 2026

The v0.0.31 horizon system is the default again; the silhouetting stays as an alternative mode,
documented as "tested but subpar results", and is not removed (the owner sees potential in it).
Planned: the skyline fill must not let the topography show through, and sprites become
silhouettes of their actual form (alpha honoured) instead of solid blocks or columns.
[Report](bugs/HORIZON-FLORA-SPRITES-32.md).

## CONSOLE-HISTORY-ARROWS-32: console arrows recall nothing on the owner's FS-UAE, 8 October 2026

Owner report on dev1, FS-UAE on Ubuntu 24.04: Up and Down do nothing in the console; keypad 8 and
2 type digits (expected: the Amiga keypad has no cursor keys). Not reproduced: the dev1 image in
FS-UAE 3.1.66 on Linux with the shipped preset recalls history in the menu console, the ship and
Vivec Arena, and the dev2 smoke test recalls it too. The key path and the FS-UAE preset are
unchanged since v0.0.31. Next: `aw_input_trace 1` on the owner's machine shows whether the arrows
reach the game. [Report](bugs/CONSOLE-HISTORY-ARROWS-32.md).

## CONSOLE-HISTORY-EMPTY-32: Up past the oldest command sticks on an empty line, 8 October 2026

Found during CONSOLE-HISTORY-ARROWS-32, inherited from Quake's `Key_Console`: Up past the oldest
command jumped to an empty slot and stayed there until Down, and the history position survived
closing and reopening the console. Fixed in source: Up keeps the oldest command and each open or
close starts from the newest. Native raw-key test; fails on the old code; not yet packaged.
[Report](bugs/CONSOLE-HISTORY-EMPTY-32.md).

## HORIZON-FLORA-SPRITES-32: horizon silhouetting, not yet perfect, 8 October 2026

Owner report on dev1: the horizon is meant to follow the highest topography, and the sprite trees
break it (partly the owner's own call; not a v0.0.32 blocker). Two owner screenshots near Seyda
Neen show a canopy-like fog-coloured silhouette behind the town and a fog-coloured wall of spikes,
both gone up close. Working hypothesis: fully fogged flora sprites drawn beyond the solid-fog
distance. A selectable return of the previous behaviour is in preparation; no method is removed.
Linked from [FOG-TOWN-HEAVY-32](bugs/FOG-TOWN-HEAVY-32.md).
[Report](bugs/HORIZON-FLORA-SPRITES-32.md).

## BUILD-HEAP-RECEIPT-TUPLES-32: dev2 image step refused its final heap receipt, 8 October 2026

After about 20 minutes the dev2 image step stopped: the heap audit's harvest fingerprint entries
were tuples in memory and lists in the saved receipt (389 differences on the dev2 maps). Fixed in
source (2ca08b5) with a round-trip test. GATE-SHARED-SOURCE-32 updated: concurrent gates verified,
temporary space and engine build folder follow-ups fixed.
[Report](bugs/BUILD-HEAP-RECEIPT-TUPLES-32.md).

## Vivec Arena residents, 8 October 2026

[VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md): cause found and fixed in source (branch
v0.0.32-arena-actors). Three residents stood on neighbouring canton walkways the frame dropped
because their origin lies outside it; two stood on the Arena canton's lower walkway, buried under
convex collision. The frame now keeps objects whose footprint reaches in, and exterior
architecture keeps its authored collision surfaces when the convex proxy closes more than a step.
The actor gate passes without the waiver; Balmora maps and every non-Arena audit row are
unchanged. New: [COLLISION-CONVEX-LOSS-32](bugs/COLLISION-CONVEX-LOSS-32.md) (convex proxies lose
surfaces up to 107 units and close space elsewhere). Updated:
[CONVERT-COLLISION-FALLBACK-32](bugs/CONVERT-COLLISION-FALLBACK-32.md) (Vivec canton shells fall
back too), [VIVEC-ARENA-TP-ARRIVAL-32](bugs/VIVEC-ARENA-TP-ARRIVAL-32.md) (the arrival point
starts inside the standing hull of the Waistworks entrance top).

## GATE-SHARED-SOURCE-32: local gate tested the main checkout, 8 October 2026

The local integration gate staged the main checkout into one shared folder whatever branch it was
asked to gate, and concurrent gates collided there (one engine step failed with `FileExistsError`).
Fixed in the local gate runner: a repository selector, per-gate staged sources and temporary
folders, no reused gate numbers, and a report header naming the repository and commit. Branch
gates reported earlier that day from worktrees may have tested the main line; merges were gated
again on the merged main line. Follow-up: the per-gate temporary folders are never removed and
filled the build container's temporary space, so later gates failed with empty logs.
[Report](bugs/GATE-SHARED-SOURCE-32.md).

## Image-parallel follow-ups merged, 8 October 2026

Fixed in source on the v0.0.32 development line, not yet shipped (state stays open):
[BUILD-LIGHT-THREADS-32](bugs/BUILD-LIGHT-THREADS-32.md) (one light thread for every map through
one helper; maps lit with several threads before now differ from earlier builds, expected in
from-scratch comparisons), [BUILD-HAND-CATALOG-SERIAL-32](bugs/BUILD-HAND-CATALOG-SERIAL-32.md),
[ACTOR-AUDIT-ORDER-32](bugs/ACTOR-AUDIT-ORDER-32.md). Partly:
[BUILD-IMAGE-UNDERUSED-32](bugs/BUILD-IMAGE-UNDERUSED-32.md) (cull 186.5 s to 83.1 s, parallel
readback; guard torches still serial). The build profiler records host load per stage
([BENCH-SESSION-DRIFT-32](bugs/BENCH-SESSION-DRIFT-32.md)).

## v0.0.32-dev1 delivery and smoke test findings, 8 October 2026

The recorded Seyda Neen maps are rewritten by later image passes (high priority for v0.0.32 final),
the Arena and Balmora are heavily fogged, the world disk image is just over 2 GiB and the static
emulator templates lack the world disk. New:
[BUILD-SEYDA-RECORDED-REWRITTEN-32](bugs/BUILD-SEYDA-RECORDED-REWRITTEN-32.md),
[FOG-TOWN-HEAVY-32](bugs/FOG-TOWN-HEAVY-32.md),
[WORLD-HDF-OVER-2GIB-32](bugs/WORLD-HDF-OVER-2GIB-32.md),
[EMULATOR-TEMPLATES-WORLD-32](bugs/EMULATOR-TEMPLATES-WORLD-32.md). Updated:
[BUILD-SEYDA-REGEN-30](bugs/BUILD-SEYDA-REGEN-30.md) (report page written; the exception must be
honoured byte for byte), [WORLD-THIRD-PARTITION-32](bugs/WORLD-THIRD-PARTITION-32.md) (WinUAE DW2
untested), [HORIZON-HOLES-31](bugs/HORIZON-HOLES-31.md) (Arena),
[CONVERT-DEGENERATE-FACES-32](bugs/CONVERT-DEGENERATE-FACES-32.md) (non-convex faces in Balmora
collision unions). From the CHIM format 0.3 statistics:
[CHIM-VIEW-FACES-33](bugs/CHIM-VIEW-FACES-33.md) (heavy models) and
[CHIM-LEAF-SPAN-33](bugs/CHIM-LEAF-SPAN-33.md) (160 placements always sent).

## v0.0.32-dev1 playtest findings, 8 October 2026

The dev1 playtest payload lacks the hands and harvest of v0.0.31 (built from a snapshot before
those builder steps; no packaging coverage gate), the first Arena teleport of a session can fail
its arrival, and parallel jobs grew the container disk image on the system drive.
[PLAYTEST-PAYLOAD-COVERAGE-32](bugs/PLAYTEST-PAYLOAD-COVERAGE-32.md),
[VIVEC-ARENA-TP-ARRIVAL-32](bugs/VIVEC-ARENA-TP-ARRIVAL-32.md),
[BUILD-SCRATCH-DISK-GROWTH-32](bugs/BUILD-SCRATCH-DISK-GROWTH-32.md).

## ENTITY-TRACKER-HARVEST-32: register state corrected, 8 October 2026

Set back to open: it had been marked fixed in "v0.0.32-dev", a development line, not a shipped build.
The status keeps "fixed in source"; release preparation marks it fixed. `tools/bug_register.py` and
`tests/test_bug_tracker.py` now refuse a development line as `fixed_in` or `owner_accepted`.
[Report](bugs/ENTITY-TRACKER-HARVEST-32.md).

## Builder harvest step findings, 8 October 2026

Found while moving harvest into the builder (0331f76). New:
[HARVEST-SEYDA-HEAP-REFUSED-32](bugs/HARVEST-SEYDA-HEAP-REFUSED-32.md) (six Seyda Neen sub-cells lose
the harvest they had in v0.0.31),
[ENTITY-TRACKER-HARVEST-32](bugs/ENTITY-TRACKER-HARVEST-32.md) (fixed in source),
[HARVEST-EXTRA-TOWNS-32](bugs/HARVEST-EXTRA-TOWNS-32.md). Updated:
[BUILD-HARVEST-NOT-BUILT-32](bugs/BUILD-HARVEST-NOT-BUILT-32.md) (Balmora's baked mushrooms were
removed by hand in v0.0.29), [HARVEST-PILOT-SHIPPING-32](bugs/HARVEST-PILOT-SHIPPING-32.md) (8-model
cap per run), [HEAP-SEYDA-OVERLAP-32](bugs/HEAP-SEYDA-OVERLAP-32.md).

## CHIM world-format follow-up findings, 8 October 2026

FFS sweep, walk replay and per-placement visibility (branch v0.0.33-chim-format). The 36 ms random
seek was mostly the hard file's place on the PC; emulated disk time drifts between sessions and
cannot price bytes. New: [BENCH-HOST-STORAGE-32](bugs/BENCH-HOST-STORAGE-32.md),
[BENCH-SESSION-DRIFT-32](bugs/BENCH-SESSION-DRIFT-32.md),
[BENCH-DISK-BYTES-32](bugs/BENCH-DISK-BYTES-32.md),
[BUILD-HDF-BUFFERS-32](bugs/BUILD-HDF-BUFFERS-32.md),
[BENCH-FSUAE-PLAIN-HDF-32](bugs/BENCH-FSUAE-PLAIN-HDF-32.md),
[BENCH-AWBENCH-BUFFERS-32](bugs/BENCH-AWBENCH-BUFFERS-32.md) (fixed on the CHIM branch, not merged),
[BENCH-FSUAE-JIT-HANG-32](bugs/BENCH-FSUAE-JIT-HANG-32.md),
[CHIM-VALIDATOR-ORDER-33](bugs/CHIM-VALIDATOR-ORDER-33.md) (fixed on the CHIM branch, not merged).
Updated: [STREAM-FFS-SEEK-32](bugs/STREAM-FFS-SEEK-32.md),
[FFS-DIRECTORY-HASH-32](bugs/FFS-DIRECTORY-HASH-32.md) (first measurement),
[CHIM-PVS-HOLLOW-33](bugs/CHIM-PVS-HOLLOW-33.md) (per-placement lists),
[CHIM-READ-RUNS-33](bugs/CHIM-READ-RUNS-33.md), [SEYDA-READ-SLOW-31](bugs/SEYDA-READ-SLOW-31.md)
(timings on Windows-folder hard files).

## Image-parallel follow-up findings, 8 October 2026

Found while making the image step parallel. New:
[BUILD-LIGHT-THREADS-32](bugs/BUILD-LIGHT-THREADS-32.md),
[BUILD-HAND-CATALOG-SERIAL-32](bugs/BUILD-HAND-CATALOG-SERIAL-32.md),
[BUILD-IMAGE-UNDERUSED-32](bugs/BUILD-IMAGE-UNDERUSED-32.md),
[TEST-WORKER-SYSPATH-32](bugs/TEST-WORKER-SYSPATH-32.md),
[ACTOR-AUDIT-ORDER-32](bugs/ACTOR-AUDIT-ORDER-32.md).
Updated: [BUILD-SCHEDULER-JOBSHARE-32](bugs/BUILD-SCHEDULER-JOBSHARE-32.md) (map tool threads keep
their start share), [BUILD-PALETTE-RACE-32](bugs/BUILD-PALETTE-RACE-32.md) (expected flora
difference in from-scratch comparisons).

## BUILD-HARVEST-NOT-BUILT-32: harvest built by default, 8 October 2026

Owner decision: a default builder step for every map family, Seyda Neen regenerated too. The
`harvest` step converts the shared models and placements from the player's data; the image step
removes Balmora's baked mushrooms, writes the catalogues for the final maps, runs the geometry gate
and admits maps by the heap check. Owned dev1 maps: 381 of 388 admitted; world, Balmora and docks
catalogues byte-identical to v0.0.31. Not shipped.
[Report](bugs/BUILD-HARVEST-NOT-BUILT-32.md),
[HARVEST-SEYDA-STALE-32](bugs/HARVEST-SEYDA-STALE-32.md),
[HARVEST-PILOT-SHIPPING-32](bugs/HARVEST-PILOT-SHIPPING-32.md),
[HARVEST-GEOMETRY-GATE-32](bugs/HARVEST-GEOMETRY-GATE-32.md).

## BUILD-IMAGE-SERIAL-32: cause and repair, 8 October 2026

Cause: the image stage never received `--jobs`, so the scheduler ran it as a one-worker stage;
its per-map passes were serial or fixed at six workers. Repair (not shipped): `--jobs N` reaches
every image pass through the shared pool with byte-identical results, ericw light stays at one
thread per map (multi-threaded light output is not reproducible), and the early actor audit
approves the image in one pass. [Report](bugs/BUILD-IMAGE-SERIAL-32.md).

## dev1 image build findings, 8 October 2026

The dev1 image passed the xdftool step and then stopped on an undefined report in its last step (fixed).
[AUDIO-MISSING-SOURCES-32](bugs/AUDIO-MISSING-SOURCES-32.md),
[BUILD-FINALIZE-TORCHTEST-32](bugs/BUILD-FINALIZE-TORCHTEST-32.md),
[WORLD-THIRD-PARTITION-32](bugs/WORLD-THIRD-PARTITION-32.md).

## Parallel test runner findings, 8 October 2026

The suite now runs in parallel (same test IDs and results as serial). Found on the way: [BUILD-JOBS-RESOLVE-PER-STAGE-32](bugs/BUILD-JOBS-RESOLVE-PER-STAGE-32.md),
[TEST-NATIVE-TMPDIR-32](bugs/TEST-NATIVE-TMPDIR-32.md).

## Second CHIM engine slice, 8 October 2026

Chunk terrain is now grafted into the world tree (vis, lighting, water and traces through Quake's own
code); actors outside the ring are frozen; visible-entity drops are counted (also on v0.0.32-dev).
New: [CHIM-BORDER-COLLISION-33](bugs/CHIM-BORDER-COLLISION-33.md),
[CHIM-FRAME-WORLD-BOUNDS-33](bugs/CHIM-FRAME-WORLD-BOUNDS-33.md),
[CHIM-FROZEN-ACTORS-33](bugs/CHIM-FROZEN-ACTORS-33.md),
[CHIM-HULL2-33](bugs/CHIM-HULL2-33.md),
[CHIM-REBUILD-COST-33](bugs/CHIM-REBUILD-COST-33.md).

## Build profiler findings, 8 October 2026

The new build profiler found a possible palette race and a scheduler that keeps a stage at one worker.
[BUILD-PALETTE-RACE-32](bugs/BUILD-PALETTE-RACE-32.md),
[BUILD-SCHEDULER-JOBSHARE-32](bugs/BUILD-SCHEDULER-JOBSHARE-32.md).

## BUILD-XDFTOOL-ARGMAX-32, 8 October 2026

With trees and grass the boot payload has 15,747 files, and the single xdftool call exceeds the Linux
argument limit at the very end of the image step. [Report](bugs/BUILD-XDFTOOL-ARGMAX-32.md).

## First CHIM engine slice, 8 October 2026

Model zone, shared model library, placements through efrags and collision work in host tests. Open:
[CHIM-ACTORS-OUTSIDE-RING-33](bugs/CHIM-ACTORS-OUTSIDE-RING-33.md),
[CHIM-ANIM-TEXTURES-33](bugs/CHIM-ANIM-TEXTURES-33.md),
[CHIM-HEAP-CHECK-33](bugs/CHIM-HEAP-CHECK-33.md),
[CHIM-LIGHT-CONTENTS-33](bugs/CHIM-LIGHT-CONTENTS-33.md),
[CHIM-PACK-DIRS-33](bugs/CHIM-PACK-DIRS-33.md),
[CHIM-READ-BUDGET-33](bugs/CHIM-READ-BUDGET-33.md),
[CHIM-TERRAIN-GRAFT-33](bugs/CHIM-TERRAIN-GRAFT-33.md),
[RENDER-VISEDICTS-OVERFLOW-32](bugs/RENDER-VISEDICTS-OVERFLOW-32.md).

## Harvest data audit and builder message, 8 October 2026

The v0.0.31 harvest files were never rebuilt with their maps: stale Seyda catalogues, a pilot
catalogue still shipping, the geometry gate not re-run. Also a mojibake builder message.
[BUILD-MOJIBAKE-32](bugs/BUILD-MOJIBAKE-32.md),
[HARVEST-GEOMETRY-GATE-32](bugs/HARVEST-GEOMETRY-GATE-32.md),
[HARVEST-PILOT-SHIPPING-32](bugs/HARVEST-PILOT-SHIPPING-32.md),
[HARVEST-SEYDA-STALE-32](bugs/HARVEST-SEYDA-STALE-32.md).

## First CHIM world-format build of Balmora, 8 October 2026

Balmora in CHIM format 0.1: 17.4 MB instead of 162 MB, crossings read 277 KB instead of 4.4 MB, but
in many separate runs; visibility culls little; model faces still dominate. New: [CHIM-LEAF-SPAN-33](bugs/CHIM-LEAF-SPAN-33.md),
[CHIM-PVS-HOLLOW-33](bugs/CHIM-PVS-HOLLOW-33.md),
[CHIM-READ-RUNS-33](bugs/CHIM-READ-RUNS-33.md),
[CHIM-VIEW-FACES-33](bugs/CHIM-VIEW-FACES-33.md),
[CONVERT-COLLISION-FALLBACK-32](bugs/CONVERT-COLLISION-FALLBACK-32.md),
[GATE-SUITE-WRITABLE-32](bugs/GATE-SUITE-WRITABLE-32.md).

## NET-UDP-INIT-CRASH-32, 8 October 2026

The UDP start-up inherited from AmiQuake can end the game at boot when bsdsocket.library opens
(unchecked lookup, `Sys_Error`); untested so far. [Report](bugs/NET-UDP-INIT-CRASH-32.md).

## Release coverage test; per-race hands built by default, 8 October 2026

BUILD-HANDS-NOT-BUILT-32 fixed in source: a default `hand-catalog` builder stage, installed by the
image step after the sky palette bank; on owned data its command reproduces all 42 v0.0.31 files
byte for byte. [Report](bugs/BUILD-HANDS-NOT-BUILT-32.md). BUILD-STANDALONE-STAGES-32 closed:
neither tool's output is in v0.0.31. [Report](bugs/BUILD-STANDALONE-STAGES-32.md).
BUILD-HARVEST-NOT-BUILT-32: the harvest plan is traced and the builder step waits for an owner
decision. [Report](bugs/BUILD-HARVEST-NOT-BUILT-32.md). New `config/release-features.json`,
`tests/test_release_coverage.py` and `tools/payload_coverage.py`: every file class a release
ships has a feature and a default builder step.

## Builder defaults audit: stages missing from the builder, 8 October 2026

Trees and grass and the Balmora layout repair are now default. The audit found two shipped features
no builder step makes (per-race hands, mushroom harvest) and two standalone tools to check.
[BUILD-HANDS-NOT-BUILT-32](bugs/BUILD-HANDS-NOT-BUILT-32.md),
[BUILD-HARVEST-NOT-BUILT-32](bugs/BUILD-HARVEST-NOT-BUILT-32.md),
[BUILD-STANDALONE-STAGES-32](bugs/BUILD-STANDALONE-STAGES-32.md).

## BUILD-IMAGE-SERIAL-32, 8 October 2026

The image step uses one core of 24 for about 23 minutes per pass, and a private-test waiver needs two
passes. [Report](bugs/BUILD-IMAGE-SERIAL-32.md).

## BUILD-FLORA-OPTIN-32 fixed in source, 8 October 2026

World flora (trees and grass) is built by default; `--no-tree-sprites` is a debugging-only
opt-out and `--tree-sprites` a no-op alias. The Balmora layout repair no longer rides on the flora
option, and the image step names missing flora as the cause. Regression tests in
`tests/test_build_defaults.py`. [Report](bugs/BUILD-FLORA-OPTIN-32.md).

## BUILD-FLORA-OPTIN-32; world layout verified, 8 October 2026

The dev1 image stopped on a missing flora sprite: trees and grass need `--tree-sprites`, which the
from-scratch recipe left out. [Report](bugs/BUILD-FLORA-OPTIN-32.md). The rebuilt world region
directory is byte-identical to v0.0.31 ([BUILD-WORLD-LAYOUT-DRIFT-32](bugs/BUILD-WORLD-LAYOUT-DRIFT-32.md)).

## DEBUG-TP-TOWN-NAMES-32, 8 October 2026

`dbg tp vivec_arena` works, but the help line omits the new towns and short names such as
`vivec` are not accepted. [Report](bugs/DEBUG-TP-TOWN-NAMES-32.md).

## Renderer counters and benchmark findings, 8 October 2026

Renderer counters show brush models cost time through deep world-BSP walks, not fragments
(RENDER-BMODEL-FRAGMENTS-32). New: [BENCH-FSUAE-FREQ-32](bugs/BENCH-FSUAE-FREQ-32.md),
[BUILD-NO-OVERLAY-32](bugs/BUILD-NO-OVERLAY-32.md),
[ENGINE-ARGS-32](bugs/ENGINE-ARGS-32.md),
[RENDER-EDGECACHE-SEYDA-32](bugs/RENDER-EDGECACHE-SEYDA-32.md),
[RENDER-SURFCACHE-THRASH-32](bugs/RENDER-SURFCACHE-THRASH-32.md),
[STREAM-FFS-SEEK-32](bugs/STREAM-FFS-SEEK-32.md).

## GOG/Steam loose-file A/B findings, 8 October 2026

The original game data is the same in both editions; AmiWind's builder still makes edition-dependent
sky outputs and plugin sounds, and its asset readers ignore the expansion archives.
[ASSETS-ARCHIVE-ORDER-32](bugs/ASSETS-ARCHIVE-ORDER-32.md),
[BUILD-EDITION-SKY-32](bugs/BUILD-EDITION-SKY-32.md),
[BUILD-PLUGIN-SOUNDS-32](bugs/BUILD-PLUGIN-SOUNDS-32.md).

## BUILD-WORLD-LAYOUT-DRIFT-32; dev1 actor waiver tracked, 8 October 2026

The from-scratch dev1 build stops at world-terrain: the world survey takes its geometry
ceiling from the largest town region, which moved from 140,801 to 115,288 source triangles, so
the world would be laid out in 4,623 regions instead of the shipped 2,526.
[Report](bugs/BUILD-WORLD-LAYOUT-DRIFT-32.md). The owner-accepted private-test waiver for the five
Arena residents is now tracked on [VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md).

## Known-inputs check merged; BUILD-INPUTCHECK-SLOW-32, 8 October 2026

Every input is identified against a known-versions table with an inputs lock. The old
reference check spends over 12 minutes walking parent folders per file.
[Report](bugs/BUILD-INPUTCHECK-SLOW-32.md).

## Vivec cantons import and loader rework findings, 8 October 2026

Four cantons convert within all limits; the Temple, St. Delyn and St. Olms still exceed the
heap; the loader no longer stages lumps (smaller saving than estimated). New: NPC bake budget,
Arena handoff overlap, unreachable rooms, unbuilt neighbours, door bank limit (fixed), a
single loader stall, Seyda heap allowance, model slots, stale estimate coefficients.
[ESTIMATE-HEAP-STALE-32](bugs/ESTIMATE-HEAP-STALE-32.md),
[HEAP-SEYDA-OVERLAP-32](bugs/HEAP-SEYDA-OVERLAP-32.md),
[IMPORT-DOORBANK-LIMIT-32](bugs/IMPORT-DOORBANK-LIMIT-32.md),
[LOADER-STALL-32](bugs/LOADER-STALL-32.md),
[MODEL-SLOTS-256-32](bugs/MODEL-SLOTS-256-32.md),
[NPC-BAKE-VERTEX-32](bugs/NPC-BAKE-VERTEX-32.md),
[TOWN-EDGE-UNBUILT-32](bugs/TOWN-EDGE-UNBUILT-32.md),
[VIVEC-ARENA-HANDOFF-32](bugs/VIVEC-ARENA-HANDOFF-32.md),
[VIVEC-ROOMS-UNREACHABLE-32](bugs/VIVEC-ROOMS-UNREACHABLE-32.md).

## Font A/B: both font paths show wrong characters, 8 October 2026

The bitmap path keeps the .fnt glyph order while the engine indexes by game byte;
Magic Cards.ttf lacks many characters and draws ornaments for brackets.
[FONT-BITMAP-INDEX-32](bugs/FONT-BITMAP-INDEX-32.md),
[FONT-TTF-COVERAGE-32](bugs/FONT-TTF-COVERAGE-32.md).

## Builder breaks fixed; next stop in Seyda Neen culling, 8 October 2026

BUILD-SEYDA-HULL2-32 and BUILD-ACTOR-CONTACT-CALL-32 fixed in source; the from-scratch build
now stops in Seyda Neen terrain culling (covered by the recorded exception); shipped maps
carry unused hull 2 data. [BUILD-SEYDA-CULL-STABLE-32](bugs/BUILD-SEYDA-CULL-STABLE-32.md),
[MAP-UNUSED-HULL2-32](bugs/MAP-UNUSED-HULL2-32.md).

## BUILD-EDITION-DIFFERENCES-32: GOG and Steam builds differ, 8 October 2026

Same masters, different builds: Steam lacks the BookArt TrueType fonts, and
GOG loose files override archive copies in several steps.
[Report](bugs/BUILD-EDITION-DIFFERENCES-32.md).

## BUILD-INPUTS-UNVERIFIED-32: user inputs not checked against known versions, 8 October 2026

The builder records but never identifies the Morrowind files and Amiga
libraries it is given. [Report](bugs/BUILD-INPUTS-UNVERIFIED-32.md).

## BUILD-NOT-FROM-SCRATCH-32: releases without a from-scratch build, 8 October 2026

Images since v0.0.28 were older images with overlays; the builder's broken
stages never re-ran and CI builds only the asset-free dry run.
[Report](bugs/BUILD-NOT-FROM-SCRATCH-32.md).

## First from-scratch build with the repository builder, 8 October 2026

The public builder has not built the game from scratch since v0.0.28 (Seyda Neen
full-town hull 2 over the clipnode limit) and its actor stage fails since v0.0.27;
five Vivec Arena residents fail placement; the importer converts no interiors.
[BUILD-ACTOR-CONTACT-CALL-32](bugs/BUILD-ACTOR-CONTACT-CALL-32.md),
[BUILD-SEYDA-HULL2-32](bugs/BUILD-SEYDA-HULL2-32.md),
[IMPORT-TOWN-NO-INTERIORS-32](bugs/IMPORT-TOWN-NO-INTERIORS-32.md),
[PKG-STALE-RUNTIME-32](bugs/PKG-STALE-RUNTIME-32.md),
[VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md).

## FPU support library findings, 8 October 2026

A 68060 on Kickstart 3.1 without its library fails the boot check's FPU line;
boot lines wrap at 64 columns; dry-run text ignores user libraries.
[BOOT-68060-FPU-FAIL-32](bugs/BOOT-68060-FPU-FAIL-32.md),
[BOOT-CONSOLE-WIDTH-32](bugs/BOOT-CONSOLE-WIDTH-32.md),
[DRYRUN-LIBS-LABEL-32](bugs/DRYRUN-LIBS-LABEL-32.md).

## Asset census findings, 8 October 2026

Interior hulls outweigh interior geometry; open-world maps spend a fifth of
their bytes on visibility; terrain and some interior bakes are nearly
uniform; a flat mesh breaks collision building; tilt drives model variants.
[CONVERT-QHULL-FLAT-32](bugs/CONVERT-QHULL-FLAT-32.md),
[INTERIOR-BAKE-UNIFORM-32](bugs/INTERIOR-BAKE-UNIFORM-32.md),
[INTERIOR-HULLS-HEAVY-32](bugs/INTERIOR-HULLS-HEAVY-32.md),
[TERRAIN-LIGHT-UNIFORM-32](bugs/TERRAIN-LIGHT-UNIFORM-32.md),
[VF-VIS-LUMP-32](bugs/VF-VIS-LUMP-32.md).

## Face validator over the shipped v0.0.31 image, 8 October 2026

21.8 million faces in 2,724 maps checked. The v0.0.32 extent rule breaks the
lightmaps of all 58 old interiors (release blocker unless reconverted); 42
non-planar and 41 tilted faces; 6 wrongly wound; degenerate faces.
[CONVERT-DEGENERATE-FACES-32](bugs/CONVERT-DEGENERATE-FACES-32.md),
[CONVERT-FACE-WINDING-32](bugs/CONVERT-FACE-WINDING-32.md),
[EXTENTS-RULE-OLD-INTERIORS-32](bugs/EXTENTS-RULE-OLD-INTERIORS-32.md).

## ENGINE-FPU-UNIMPL-31, NPC-TARGET-REDUNDANT-31, ENGINE-BUILD-REPRO-31, ENGINE-FPSP-MISSING-31, REMOTE-STATE-WIDTH-31: FPU fixes measured, 8 October 2026

Per-frame counters (`dbg fpucount`) on the v0.0.31 image: 3,547 `cexp` calls per
frame at Balmora before, none after (brush rotation fast paths and cache, table
sine/cosine, NPC targeting once per frame, flame constants, no library
trigonometry linked). The engine build now fails if engine code reaches a
68040-unimplemented FPU instruction outside a justified allowlist. Two fresh
engine builds are byte-identical. In the emulator's strict FPU mode the engine
now runs past start-up but still stops at the first scene load (text-to-float
parsing). A formatting slip in the new state-file code was caught and fixed
before release. [ENGINE-FPU-UNIMPL-31](bugs/ENGINE-FPU-UNIMPL-31.md),
[NPC-TARGET-REDUNDANT-31](bugs/NPC-TARGET-REDUNDANT-31.md),
[ENGINE-BUILD-REPRO-31](bugs/ENGINE-BUILD-REPRO-31.md),
[ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md),
[REMOTE-STATE-WIDTH-31](bugs/REMOTE-STATE-WIDTH-31.md).

## REMOTE-CONSOLE-APPEND-31: remote console log overwrites itself, 8 October 2026

Every console message was written over the start of `AWCTL:console.log`; the
C library ignores `O_APPEND`. Fixed in source with a seek to the end.
[Report](bugs/REMOTE-CONSOLE-APPEND-31.md).

## TEST-FPU-STRICT-JIT-31: strict FPU emulation needs the JIT off, 8 October 2026

The emulator's "no unimplemented FPU instructions" option is ignored while the
JIT is on; a probe program shows the F-line traps only with the JIT off.
[Report](bugs/TEST-FPU-STRICT-JIT-31.md).

## Converter face findings from the texture snapping test, 8 October 2026

Merged faces take their plane from the first three vertices (29 degrees off in
two Khuul faces), can bend slightly, and texture coordinates are not range-checked.
[CONVERT-FACE-PLANE-32](bugs/CONVERT-FACE-PLANE-32.md),
[CONVERT-MERGE-NONPLANAR-32](bugs/CONVERT-MERGE-NONPLANAR-32.md),
[CONVERT-TEXCOORD-RANGE-32](bugs/CONVERT-TEXCOORD-RANGE-32.md).

## TOWN-FRAME-CEILING-32: high ground leaks town frames, 8 October 2026

Frames are sealed at 2,048 units; 320 regions have higher ground and leak.
ESTIMATE-EVR-BELOW-CUR-31 cause found and fixed in the public estimator.
[Report](bugs/TOWN-FRAME-CEILING-32.md).

## Independent review of the open-world plan, 8 October 2026

All performance figures were taken with the emulator at host speed; flat
directories are slow on real FFS; brush models may fragment down the terrain
BSP; the loader stages lumps before decoding. Notes added to
ENGINE-FPSP-MISSING-31 (denormals), INTERIOR-INLINE-LIMIT-31 (cause of the cap)
and CONVERT-VARIANTS-32 (scale). [BENCH-JIT-PROFILE-32](bugs/BENCH-JIT-PROFILE-32.md),
[FFS-DIRECTORY-HASH-32](bugs/FFS-DIRECTORY-HASH-32.md),
[LOADER-STAGING-PEAK-32](bugs/LOADER-STAGING-PEAK-32.md),
[RENDER-BMODEL-FRAGMENTS-32](bugs/RENDER-BMODEL-FRAGMENTS-32.md).

## World streamer measurement findings, 8 October 2026

Model variants per mesh, textures copied into every map, shared node subtrees,
placements stored differently per region, and a heap estimate that ignores
sharing inside a map. [BSP-SHARED-SUBTREES-32](bugs/BSP-SHARED-SUBTREES-32.md),
[CONVERT-VARIANTS-32](bugs/CONVERT-VARIANTS-32.md),
[HEAP-MODEL-SUM-32](bugs/HEAP-MODEL-SUM-32.md),
[MAP-TEXTURE-COPIES-32](bugs/MAP-TEXTURE-COPIES-32.md),
[REGION-PLACEMENT-FORMS-32](bugs/REGION-PLACEMENT-FORMS-32.md).

## ENGINE-SUBMODEL-LIMIT-32, TOOL-SIMPLIFY-MANIFOLD-32, SHELL-TEXTURE-VOTE-32: distant shell prototype, 8 October 2026

Map loading does not check the submodel count; mesh reduction can open closed
meshes; the shell texture vote picks door textures for walls.
[ENGINE-SUBMODEL-LIMIT-32](bugs/ENGINE-SUBMODEL-LIMIT-32.md),
[SHELL-TEXTURE-VOTE-32](bugs/SHELL-TEXTURE-VOTE-32.md),
[TOOL-SIMPLIFY-MANIFOLD-32](bugs/TOOL-SIMPLIFY-MANIFOLD-32.md).

## Vivec limits repaired in source; ERICW-TEXINFO-SIGNED-31, EXTENTS-FPU-RULE-31, VIVEC-HEAP-31 found, 8 October 2026

VIVEC-TEXINFO-31 and MODEL-MARKSURF-SIGNED-31: the engine reads face texinfo
indices, marksurface entries and leaf mark ranges unsigned, bounds-checked
before any pointer; the converter allows 65,535 mappings. MESH-EXTENT-GRID-31:
1/16-texel guard in the face split and a three-rule extent check.
LIGHTMAP-TAIL-31: caused by LIGHTMAP-GRID-31 (lightmaps sized from unstored
coordinates); the converter now sizes them from the stored values. Found on
the way: ericw vis crashes and light skips faces above texinfo 32,767
(ERICW-TEXINFO-SIGNED-31); surface extents followed a different rounding rule
on the 68040, the emulator, ericw light and the converter, now one double-
precision rule (EXTENTS-FPU-RULE-31). Rerun of the Vivec dry run: interiors
117 to 134 of 146 passing, exterior regions 160 to 174 of 192; the next limit
is the loader heap (VIVEC-HEAP-31). Source only, not shipped.
[MODEL-MARKSURF-SIGNED-31](bugs/MODEL-MARKSURF-SIGNED-31.md),
[VIVEC-TEXINFO-31](bugs/VIVEC-TEXINFO-31.md),
[MESH-EXTENT-GRID-31](bugs/MESH-EXTENT-GRID-31.md),
[LIGHTMAP-TAIL-31](bugs/LIGHTMAP-TAIL-31.md),
[LIGHTMAP-GRID-31](bugs/LIGHTMAP-GRID-31.md),
[ERICW-TEXINFO-SIGNED-31](bugs/ERICW-TEXINFO-SIGNED-31.md),
[EXTENTS-FPU-RULE-31](bugs/EXTENTS-FPU-RULE-31.md),
[VIVEC-HEAP-31](bugs/VIVEC-HEAP-31.md).

## ESTIMATE-EVR-BELOW-CUR-31 and TOOLING-HEADLESS-BROWSER-31: map metrics layer, 8 October 2026

The world estimate puts "everything" slightly below "current content" in 894
regions; no Docker image can render Toolkit screenshots.
[Report](bugs/ESTIMATE-EVR-BELOW-CUR-31.md), [report](bugs/TOOLING-HEADLESS-BROWSER-31.md).

## WORLD-REGION-DUPLICATION-31: exterior objects stored about ten times, 8 October 2026

Overlapping self-contained region maps store each exterior object about 9.8
times; most of the 4.8 GB of game files and the ~20 GB whole-island estimate
is repeated geometry. [Report](bugs/WORLD-REGION-DUPLICATION-31.md).

## Whole-world measurement findings, 8 October 2026

Estimating every map of the world with every object placed found silent
drops (night lamps in Vivec, static flames), the 220-object interior ceiling,
out-of-range interior coordinates, unsupported expansions and developer test
cells; MESH-EXTENT-GRID-31, LIGHTMAP-TAIL-31 and VIVEC-TEXINFO-31 reach beyond Vivec.
[LAMPS-CACHE-31](bugs/LAMPS-CACHE-31.md),
[INTERIOR-INLINE-LIMIT-31](bugs/INTERIOR-INLINE-LIMIT-31.md),
[FLAMES-CAP-31](bugs/FLAMES-CAP-31.md),
[INTERIOR-COORDS-31](bugs/INTERIOR-COORDS-31.md),
[BUILD-EXPANSIONS-31](bugs/BUILD-EXPANSIONS-31.md),
[IMPORT-TEST-CELLS-31](bugs/IMPORT-TEST-CELLS-31.md).

## MODEL-MARKSURF-SIGNED-31 and TOWN-VIS-OCCLUSION-31: visibility prototype, 8 October 2026

Occluders and building faces in the world model were measured not to help
open towns. The leaf face list loader reads face indices signed (latent bad
pointer above 32,767). [Report](bugs/MODEL-MARKSURF-SIGNED-31.md),
[report](bugs/TOWN-VIS-OCCLUSION-31.md).

## ENGINE-FPU-UNIMPL-31, ENGINE-FPSP-MISSING-31, NPC-TARGET-REDUNDANT-31, CI-ERICW-SKIP-31, CI-SKIPS-UNGUARDED-31: FPU audit and gate skips, 8 October 2026

The engine's sin+cos pairs become `cexp` calls that execute 68040-unimplemented
instructions every frame, the boot disk loads no FPU support library, and the
emulator hides both. NPC targeting runs several times per frame. Two CI test
gaps found while itemising skips. ENGINE-BUILD-REPRO-31: cause is the compile-time stamps.
[ENGINE-FPU-UNIMPL-31](bugs/ENGINE-FPU-UNIMPL-31.md),
[ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md),
[NPC-TARGET-REDUNDANT-31](bugs/NPC-TARGET-REDUNDANT-31.md),
[CI-ERICW-SKIP-31](bugs/CI-ERICW-SKIP-31.md),
[CI-SKIPS-UNGUARDED-31](bugs/CI-SKIPS-UNGUARDED-31.md).

## GATE-NODE-MISSING-31 and TOOLKIT-TEST-POINTERLOCK-31: inspector tests, 8 October 2026

The local gate never runs the inspector JavaScript tests (no Node.js in the
images); one of those tests left pointer lock set (fixed in source).
[Report](bugs/GATE-NODE-MISSING-31.md), [report](bugs/TOOLKIT-TEST-POINTERLOCK-31.md).

## ENGINE-BUILD-REPRO-31 and VIVEC-TEXINFO-31: from tonight's reports, 8 October 2026

Two engine builds from the same source gave different binaries; and 52 dense
Vivec exterior regions stop on the 32,767 texture-mapping limit (unsigned
texinfo planned). [Report](bugs/ENGINE-BUILD-REPRO-31.md),
[report](bugs/VIVEC-TEXINFO-31.md).

## MESH-EXTENT-GRID-31 and LIGHTMAP-TAIL-31: Vivec dry run, 8 October 2026

A sewer corridor face sitting exactly on the texture grid passes the converter's
extent check but exceeds 256 texels with the 68040's rounding, stopping 13 Vivec
maps; a 1/16-texel guard fixes it on a copy. Some interiors also write a last
lightmap past the end of the lighting lump.
[Report](bugs/MESH-EXTENT-GRID-31.md), [report](bugs/LIGHTMAP-TAIL-31.md).

## BUILD-SEYDA-PRIVATE-STAGES-31: duplicate of BUILD-SEYDA-REGEN-30, 8 October 2026

Recorded again while preparing v0.0.31 and closed as a duplicate of
BUILD-SEYDA-REGEN-30; its detail (the three private Seyda stages, the image path not run
end to end since v0.0.29-dev4) is now on that record.
[Report](bugs/BUILD-SEYDA-PRIVATE-STAGES-31.md).

## BUILD-NIGHT-TABLES-31: night lighting tables only on hand-made disks, 8 October 2026

The night lamp, glowing glass and location fog tables reached the playtest
disks by hand; the image builder never wrote them, so repository builds have
dark lamps and no glowing glass. Repaired in source: the image builder writes
and checks all three and records them in its receipt; the window table matches
the private dev5 table byte for byte on the same inputs.
[Report](bugs/BUILD-NIGHT-TABLES-31.md).

## BUILD-FINALIZE-SCENE-31: undefined name in image finalisation, 8 October 2026

Found reading `finalize_image`: since v0.0.29-dev4 the media step uses
`scene`, which only `image()` defines, so the image build would stop with a
`NameError` before media staging. Repaired in source (one line); a full image
build is pending. [Report](bugs/BUILD-FINALIZE-SCENE-31.md).

## DBG-TOGGLE-WORDS-31: on/off words for settings, 8 October 2026

`dbg fog on` turned the fog off: settings read "on" as 0. Toggle words now
become 1/0 for settings. [Report](bugs/DBG-TOGGLE-WORDS-31.md).

## TOWN-VIS-OCCLUSION-31: buildings do not block visibility, 7 October 2026

Measured from the dev5 maps: 94 % of Balmora's faces are in `func_wall`
building models, which Quake's `vis` ignores, so 84-89 % of a Balmora map is
potentially visible from an average spot (Seyda Neen 73 %). Occluder blocks
are planned. [Report](bugs/TOWN-VIS-OCCLUSION-31.md),
[performance page](performance/TOWN-VISIBILITY.md).

## LAMPS-FLICKER-31 and SEYDA-LANTERNS-MISSING-31: dev5 night walk, 7 October 2026

Owner, dev5: lamp light keeps switching on and off while turning or walking
(our dev5 front priority; repaired in source with lamp stickiness and fade-out),
and Seyda Neen walls are lit by lanterns that are not in its maps.
[Report](bugs/LAMPS-FLICKER-31.md), [report](bugs/SEYDA-LANTERNS-MISSING-31.md).

## BUILD-WINDOWS-DOCKER-SLOW-31: Docker disk steps on Windows, 7 October 2026

Measured 225 MB/s from a container into a Windows folder against about
1.9 GB/s for a native Windows copy; playtest builds move several 5.6 GB disk
images that way. Large copies move to the host and container scratch to a
Docker volume. [Report](bugs/BUILD-WINDOWS-DOCKER-SLOW-31.md).

## NIGHT-0400-DARK-31: sudden darkness near 04:00, 7 October 2026

Owner, dev4 in Balmora: the exterior turns much darker at about 04:00. Cause
unknown; a 03:30-04:30 time sweep is being measured.
[Report](bugs/NIGHT-0400-DARK-31.md).

## GUARD-TORCH-BRIGHT-31 and LAMPS-RANGE-31: Balmora at night, 7 October 2026

Owner, dev4: guard torches outshine the lamps, and lamps switch on and off like
motion detectors while walking. Guard torches now light half as far. Lamps ahead
of the view now win the few light slots, and newly chosen lamps fade in. The
repair is baking the lamps into the maps on a night lightstyle.
[Report](bugs/GUARD-TORCH-BRIGHT-31.md), [report](bugs/LAMPS-RANGE-31.md).

## LAMPS-RANGE-31: only the nearest lamps light up, 7 October 2026

Owner, dev4 in Balmora: distant lamps stay dark until approached. The night
lamps light only the nearest two. [Report](bugs/LAMPS-RANGE-31.md).

## SEYDA-BLOCK-31 and PLACE-NAMES-INTERIOR-31: dev3 playtest, 7 October 2026

Owner: an invisible obstacle on a Seyda Neen slope stops the walk toward an NPC;
interiors show no town or building name. The autosave message also covers the
title (HUD-NOTIFY-OVERLAP-31). [SEYDA-BLOCK-31](bugs/SEYDA-BLOCK-31.md),
[PLACE-NAMES-INTERIOR-31](bugs/PLACE-NAMES-INTERIOR-31.md).

## DLIGHT-WALLS-31: cause is the night remap, 7 October 2026

Walls do receive torch light (native run on the shipped map); the outdoor night
remap darkened it with everything else. Light-space night becomes the default in
dev4. [Report](bugs/DLIGHT-WALLS-31.md).

## MUSIC-OPENING-CLIP-31: title clip during the opening load, 7 October 2026

Owner, dev3: a clip of another track plays while the ship loads. The map load
resumes the paused title stream during the new opening hold. Repaired in source.
[Report](bugs/MUSIC-OPENING-CLIP-31.md).

## MUSIC-STARTUP-TRACK-31: random track under the startup logo, 7 October 2026

Owner, dev3 in WinUAE: a random soundtrack piece plays during the logo. My
AUDIO-LOGO-31 change removed the switch to the title that had hidden the random
start-up track. Repaired in source. [Report](bugs/MUSIC-STARTUP-TRACK-31.md).

## DLIGHT-WALLS-31: torches light the ground but not town walls, 7 October 2026

Owner report; the headlamp barely changes Balmora wall views (0.1-1.9 luma)
while it lights the ship. Investigating. [Report](bugs/DLIGHT-WALLS-31.md).

## OPENING-BRIGHT-31: ship hold brighter than the original, 7 October 2026

Owner: the opening is too bright. Measured against OpenMW at the same poses:
AmiWind 1.2 to 2.5 times brighter. [Report](bugs/OPENING-BRIGHT-31.md).

## HORIZON-HOLES-31: distant Balmora breaks up against the sky, 7 October 2026

Owner screenshots: far buildings are a fogged silhouette with holes. Far culling
drops parts of buildings; the distant fill draws only land. Needs work.
[Report](bugs/HORIZON-HOLES-31.md).

## HUD-NOTIFY-OVERLAP-31: console line over the title, 7 October 2026

Owner screenshot: the heap audit message printed over the debug title.
[Report](bugs/HUD-NOTIFY-OVERLAP-31.md).

## LIGHT-OFF-31: Off-by-default lights would bake as lit, 7 October 2026

Checking whether any original light follows a time of day (none does), found
the Off-by-default flag unread by the bake. No shipped map affected; repaired
in source with unit tests. [Report](bugs/LIGHT-OFF-31.md).

## LIGHT-FALLOFF-31 correction; LIGHTMAP-GRID-31, 7 October 2026

My measuring script read placed objects in model-local coordinates, so the
claim that the opening lantern bakes no light was wrong: the map is lit around
it. The falloff difference stands. Found instead: some baked lightmaps are one
sample row or column off the engine grid (double vs single precision).
[LIGHT-FALLOFF-31](bugs/LIGHT-FALLOFF-31.md), [LIGHTMAP-GRID-31](bugs/LIGHTMAP-GRID-31.md).

## LIGHT-FALLOFF-31 and BALMORA-LAMPS-DIM-31: OpenMW reference, 7 October 2026

OpenMW at the owner poses: the ship lantern in view is light_com_lantern_02_200_Boat
(the _64 one is on the deck above); the original hold is very dark (luma 11-16).
Balmora: the original street lantern glows and lights the wall below it. Owner:
Seyda Neen also has no lamp light at night; exteriors carry no lamp light at all.
[LIGHT-FALLOFF-31](bugs/LIGHT-FALLOFF-31.md), [BALMORA-LAMPS-DIM-31](bugs/BALMORA-LAMPS-DIM-31.md).

## SEYDA-WALL-SHAPE-31: likely a tree card drawn through a wall, 7 October 2026

Ray-cast of the reported pose: the dark shape matches the trunk base of a
camera-facing tree card standing 230 units behind the wall, depth-tested at
the tree's centre. Same in v0.0.30; in-game capture pending.
[Report](bugs/SEYDA-WALL-SHAPE-31.md).

## BALMORA-LAMPS-DIM-31, NIGHT-RUST-31, EMISSIVE-UNSHIPPED-31: causes measured, 7 October 2026

Balmora lamps: exterior lamps are never baked into light, the lamp glass is not
emissive in the shipped maps (only bmtemple has an emissive texture), and the
night remap darkens the finished frame including any light. The rust speckle is
the night remap rounding near-black colours to a rust palette entry.
[BALMORA-LAMPS-DIM-31](bugs/BALMORA-LAMPS-DIM-31.md), [NIGHT-RUST-31](bugs/NIGHT-RUST-31.md),
[EMISSIVE-UNSHIPPED-31](bugs/EMISSIVE-UNSHIPPED-31.md).

## LIGHT-NEGATIVE-31: negative lights bake as white, 7 October 2026

Identifying the Census office fireplace: the original darkens its left corner
with dark_128 (Negative flag); the bake ignores flags and adds it as white.
[Report](bugs/LIGHT-NEGATIVE-31.md).

## BALMORA-LAMPS-DIM-31: Balmora lamps nearly black at night, 7 October 2026

Owner, dev2 playtest at 22:21: a Balmora street lamp and its surroundings are
almost black. Cause unknown; investigating.
[Report](bugs/BALMORA-LAMPS-DIM-31.md).

## SEYDA-WALL-SHAPE-31: shape in a Seyda Neen wall, 7 October 2026

Owner, dev2 playtest: a dark shape pokes out of a stone wall near the shore at
global -10474 -73437 135; not seen before. Cause unknown; investigating.
[Report](bugs/SEYDA-WALL-SHAPE-31.md).

## LIGHT-FALLOFF-31: the opening lantern bakes no light, 7 October 2026

Owner, dev2 opening scene: the lantern hanging above the start gives no light.
Measured: it is the original `light_com_lantern_02_64` (radius 16 local units);
the nearest surface is 27 units away and the bake stops every light at its
radius, where the original falls off as radius/(3d). All samples near it are
the cell ambient (64). Open; OpenMW A/B in progress.
[Report](bugs/LIGHT-FALLOFF-31.md).

## SEYDA-READ-SLOW-31: owner playtest of dev2, 7 October 2026

Owner, playing v0.0.31-dev2: Seyda Neen is fast now. Owner-observed; acceptance
pending. [Report](bugs/SEYDA-READ-SLOW-31.md).

## AUDIO-03 and AUDIO-LOGO-31: music started under disk-heavy moments, 7 October 2026

Owner, WinUAE: the music still crackles right after the intro video, and also
while the startup logo plays. Both music starts coincided with heavy disk reads
(the ship map load; the streamed logo video). Repair in source: the ship scene
holds until loaded and settled, then the music starts; the title music starts
after the main menu appears. Not yet packaged or heard.
[AUDIO-03](bugs/AUDIO-03.md), [AUDIO-LOGO-31](bugs/AUDIO-LOGO-31.md).

## TRACKER-MAP-BLANK-31: world progress map went blank on hover, 7 October 2026

The owner saw the new map viewer draw and then go blank in Firefox: the hover
tooltip resized (and so cleared) the canvas on every mouse move. Fixed before
the viewer was committed; owner confirmed. [Report](bugs/TRACKER-MAP-BLANK-31.md).

## SEYDA-READ-SLOW-31: 16 KiB file buffer repairs and beats it, 7 October 2026

Narrowed to the build that added ember particles, but not to the embers
themselves: the slowdown sits in the C library's buffered reads. A 16 KiB
buffer when a game file is opened (default 1 KiB) halves map read time; dev1
Seyda crossings 0.70-0.91 s -> 0.39-0.48 s. In source; a 10-15 % gap stays
open. [Report](bugs/SEYDA-READ-SLOW-31.md),
[lessons](performance/LESSONS_LEARNED.md).

## SEYDA-READ-SLOW-31: dev1 crossings read slower than the test image, 7 October 2026

The dev1 boot check measured Seyda Neen crossings 0.10-0.21 s slower than the
earlier test image with the same maps, all of it in read time. Still faster
than v0.0.30. Cause unknown; engine and disk-layout A/B running.
[Report](bugs/SEYDA-READ-SLOW-31.md).

## GATE-EMBERS-31: ember commit failed the dev1 gates, 7 October 2026

The v0.0.31-dev1 gates found a blank line at the end of `d_iface.h` and three
native torch tests that no longer linked: the new ember calls had no test
stand-ins. Repaired in source before packaging.
[Report](bugs/GATE-EMBERS-31.md).

## SEYDA-LOAD-HANG-30: the hung read is the music stream, 7 October 2026

Disassembly of the matching unstripped build places the freeze's return
address directly after `fread` in the music stream reader (`refill`, called
from `CDAudio_Update`), not in the map loader. The earlier function name came
from a lookup that missed static functions and is withdrawn.
[Report](bugs/SEYDA-LOAD-HANG-30.md).

## CI-HOSTDEPS-30: host CI job failed on the first v0.0.30 push, 7 October 2026

The hosted `host-launcher-parity` job failed: flame extraction asked for the
NIF reader for a synthetic non-NIF test model, and that job installs only
numpy and Pillow. Not tagged or released. Repaired in source; the host tests
now also run in a reduced environment before every handoff.
[Report](bugs/CI-HOSTDEPS-30.md).

## v0.0.30-rc1 owner playtest summary, 7 October 2026

WinUAE playtest by the owner: Census office interiors work
(CENSUS-ENTITIES-30 accepted), mushroom picking on the road to Balmora works,
Balmora works and torches work. Open from the same playtest, all WinUAE music
crackles or pauses at transitions: AUDIO-NEWGAME-30, AUDIO-03,
AUDIO-ENTER-29, AUDIO-APPEARANCE-29, AUDIO-LOAD-29. Character attributes and
the papers reader (no disk loads) stay clean.

## CENSUS-ENTITIES-30: owner-accepted in v0.0.30-rc1, 7 October 2026

Owner WinUAE playtest of v0.0.30-rc1: the Census and Excise Office interiors
work. Same playtest: small music clicks on the pier at head selection and on
Choose/OK (AUDIO-APPEARANCE-29) and small crackles entering the Census office
(AUDIO-LOAD-29); both open.

## AUDIO-NEWGAME-30: rc1 playtest audio reports, 7 October 2026

v0.0.30-rc1 WinUAE playtest by the owner: music crackles when confirming New
Game (new, [report](bugs/AUDIO-NEWGAME-30.md)); crackles as the game fades in
after the intro (AUDIO-03); a split-second pause on Enter to follow the guard,
which worked in earlier versions (AUDIO-ENTER-29, regression); heavy crackling
from the ship's hull to the deck (AUDIO-LOAD-29). All open; tracked for after
v0.0.30.

## CENSUS-ENTITIES-30: misplaced objects in the Census and Excise Office, 7 October 2026

1. Symptom (v0.0.30-dev5 playtest): an upright rug on the upper floor whose
   lower half shows as a black hole in the ceiling below, and a tapestry
   inside a bookshelf. The fireplace and its flames are correct.
2. Cause: the dev5 lighting rebuild kept an older object list (v0.0.29) on
   top of geometry from the dev3 rebuild, which had added one object. Every
   later object pointed at its neighbour's model: 67 of 140.
3. Introduced in v0.0.30-dev5; dev4 was correct. Only the Census map; the
   rebuilt Temple's numbering matches.
4. Fix: the dev4 object list plus dev5's flames; all 140 objects point at the
   same models as in dev4, and the geometry is unchanged. The rebuild step now
   stops if any object's model number differs from the rebuilt geometry.
5. Shipped in v0.0.30-rc1. [Details](bugs/CENSUS-ENTITIES-30.md).

## SEYDA-LOAD-HANG-30: rare freeze during a Seyda Neen region load, 7 October 2026

1. Symptom: in about 5 of 70 automated FS-UAE runs of the Seyda Neen test
   route the game stopped during a region load; the screen froze and quit was
   ignored. Not yet reported in manual play.
2. Reproduction: scripted route seyda-east-y-300 under FS-UAE 3.1.66 with the
   console debugger; v0.0.30-dev4 and dev5 engines.
3. Evidence: every CPU sample was the idle loop. The game task waited on the
   DOS signal inside a read (`fread` -> dos.library `Read` -> exec `Wait`); its
   reply port was empty and the file-system handlers were idle.
4. Cause: open. A read request or its reply was lost below the engine (file
   system handler or emulator disk layer); not an engine loop.
5. Not tied to host disk load: 0 freezes in 12 runs with a 4 GB copy running.
6. Status: open, no fix. Next: name the calling engine function and check the
   emulator log at the moment of the freeze.
7. Shipped: present in v0.0.30 if it is a real game fault.

## BUILD-SEYDA-REGEN-30: public build cannot regenerate Seyda Neen, 7 October 2026

Reproduced 7 October 2026: running the partition on the original v0.0.29 inputs
stops with the message below. `build_aga.py image` calls the Seyda partition
without a canonical terrain source while `config/terrain-visual-cull.json`
enables culling by default, so the partition stops with "Enabled Seyda culling
requires --canonical-land-source". The shipped sub-cells were finished by
terrain steps outside the repository; v0.0.29 reused them unchanged. Next:
bring the missing steps into the public build.

## INTRO-ROLES-30: crash on a region change, 7 October 2026

`NUM_FOR_EDICT: bad pointer` on a Seyda Neen sub-cell load. The opening
sequence kept actor pointers across a map reload; one pointed past the new
entity list. Repaired by validating role pointers before use. Scripted route:
dev3 crashed 2/2, repaired engine 0/3. [Details](bugs/INTRO-ROLES-30.md).

## CONVERTER-ROOT-ROTATION-30: same cause in more maps, 7 October 2026

The root-rotation converter bug behind the Temple also turned Velothi kit walls
in Tharys Ancestral Tomb (see-through holes) and `in_nord_fireplace_01` in five
Seyda Neen interiors (fireplace facing away). All six maps are rebuilt; only
the root-rotated meshes changed. One Balmora exterior placement is pending.
[Details](bugs/CONVERTER-ROOT-ROTATION-30.md).

## BALMORA-TEMPLE-GEOMETRY-29: cause found, 7 October 2026

The Temple's missing and edge-on walls, see-through holes and floating objects
come from the scenery converter applying each mesh's NIF **root node rotation**.
Morrowind ignores that rotation (it keeps root translation and scale), and the
Velothi kit pieces carry a 90-degree root yaw, so they were turned a quarter
turn. Earlier audits compared geometry flattened by the same converter and
could not see it. Candidate repair: ignore the root rotation in
`model_geometry`; regression `tests/test_scenery_root_transform.py`. The
rebuilt Temple matches OpenMW at the reported views in FS-UAE; only the five
root-rotated models changed. Other converted maps with root-rotated meshes:
Tharys Ancestral Tomb and the fireplace interiors. Not shipped; first fixed
version pending. [Details](bugs/BALMORA-TEMPLE-GEOMETRY-29.md).

Entries before 7 October 2026 are in
[the v0.0.29 bug journal](journals/BUG_JOURNAL-v0.0.29.md).
