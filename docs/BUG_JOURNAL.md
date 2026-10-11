# Bug journal

Entries for v0.0.35 (from 10 October 2026). Older entries are frozen: [8 October 2026 to the v0.0.34 release](journals/BUG_JOURNAL-v0.0.34.md), [7 October 2026](journals/BUG_JOURNAL-v0.0.31.md) and [v0.0.29 and earlier](journals/BUG_JOURNAL-v0.0.29.md). The current status of every bug is in the [register](BUGS.md).

<!-- contents start -->
## Contents

- [Stair fixes verified, AW-LEASE-NO-GROW-36, 11 October 2026](#stair-fixes-verified-aw-lease-no-grow-36-11-october-2026)
- [CHIM-FRAME-EDGE-EFRAG-CRASH-36 fixed, 11 October 2026](#chim-frame-edge-efrag-crash-36-fixed-11-october-2026)
- [AW-LEASE-MEMORY-DEADLOCK-36 fixed, 11 October 2026](#aw-lease-memory-deadlock-36-fixed-11-october-2026)
- [TRACKER-REGISTER-SIZE-36, 11 October 2026](#tracker-register-size-36-11-october-2026)
- [SMOKE-PASSES-WITHOUT-MAP-36, 11 October 2026](#smoke-passes-without-map-36-11-october-2026)
- [CHIM-FRAME-EDGE-EFRAG-CRASH-36 (persisting) and ENGINE-CRASH-EXIT-KEYBOARD-36, 11 October 2026](#chim-frame-edge-efrag-crash-36-persisting-and-engine-crash-exit-keyboard-36-11-october-2026)
- [TEST-PROFILE-OVERHEAD-SAMPLES-36, 11 October 2026](#test-profile-overhead-samples-36-11-october-2026)
- [WORLDMAP-LAVA-MISMATCH-36, AW-LEASE-MEMORY-DEADLOCK-36 and BUILD-END-USER-LAUNCHERS-36, 11 October 2026](#worldmap-lava-mismatch-36-aw-lease-memory-deadlock-36-and-build-end-user-launchers-36-11-october-2026)
- [CHIM-FRAME-EDGE-EFRAG-CRASH-36 (persisting) and ENGINE-CRASH-EXIT-KEYBOARD-36, 11 October 2026](#chim-frame-edge-efrag-crash-36-persisting-and-engine-crash-exit-keyboard-36-11-october-2026-1)
- [TEST-PARALLEL-SHARE-TIMING-36, 11 October 2026](#test-parallel-share-timing-36-11-october-2026)
- [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36, COMBAT-BLOCKING-36 and the platform field, 11 October 2026](#camera-thirdperson-combat-npc-hidden-36-combat-blocking-36-and-the-platform-field-11-october-2026)
- [BUILD-IMAGE-HASH-UNDERUSED-36 and BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36 fixed, 11 October 2026](#build-image-hash-underused-36-and-build-image-heap-audit-underused-36-fixed-11-october-2026)
- [BUILD-CHIM-STAIR-WALK-UNCACHED-36 fixed, 11 October 2026](#build-chim-stair-walk-uncached-36-fixed-11-october-2026)
- [AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36 and BUILD-PROFILER-NO-WASTE-ALARM-36 fixed, 11 October 2026](#aw-concurrent-builds-oversubscribe-36-and-build-profiler-no-waste-alarm-36-fixed-11-october-2026)
- [BUILD-STAGE-INTERRUPT-ABSORBED-36 and BUILD-EXECUTABLES-LIST-UNGATED-36 fixed, 11 October 2026](#build-stage-interrupt-absorbed-36-and-build-executables-list-ungated-36-fixed-11-october-2026)
- [BUILD-IMAGE-STAIR-WALK-SERIAL-36, BUILD-IMAGE-FRAME-MAP-HEAP-SERIAL-36, BUILD-IMAGE-HASH-UNDERUSED-36 and BUILD-IMAGE-HEAP-AUDIT-UNDERUSED-36: the perf guard, 11 October 2026](#build-image-stair-walk-serial-36-build-image-frame-map-heap-serial-36-build-image-hash-underused-36-and-build-image-heap-audit-underused-36-the-perf-guard-11-october-2026)
- [CHIM-HEAP-INT-MATMUL-36, 11 October 2026](#chim-heap-int-matmul-36-11-october-2026)
- [CHIM-REGION-DIVIDED-CELLS-36 (persisting) and AW-RUN-NAME-LONG-REASON-36, 11 October 2026](#chim-region-divided-cells-36-persisting-and-aw-run-name-long-reason-36-11-october-2026)
- [BUILD-PASS-KEY-RULE-NO-CARRYOVER-36, BUILD-STAIR-KEY-BOOKKEEPING-36, BUILD-STAGE-INTERRUPT-ABSORBED-36 and BUILD-EXECUTABLES-LIST-UNGATED-36, 11 October 2026](#build-pass-key-rule-no-carryover-36-build-stair-key-bookkeeping-36-build-stage-interrupt-absorbed-36-and-build-executables-list-ungated-36-11-october-2026)
- [Register rotation, 11 October 2026](#register-rotation-11-october-2026)
- [CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36 and BUILD-POOL-READONLY-SCENE-WRITE-35 (persisting), 11 October 2026](#chim-native-image-no-shared-sky-36-and-build-pool-readonly-scene-write-35-persisting-11-october-2026)
- [BUILD-LEGACY-TOWN-MAPS-SHIPPED-36 and BUILD-CHIM-FRAME-SWAP-LATE-36: Seyda Neen CHIM-native, 11 October 2026](#build-legacy-town-maps-shipped-36-and-build-chim-frame-swap-late-36-seyda-neen-chim-native-11-october-2026)
- [BUILD-PASS-KEY-OVERBROAD-36, 11 October 2026](#build-pass-key-overbroad-36-11-october-2026)
- [AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36, 11 October 2026](#aw-concurrent-builds-oversubscribe-36-11-october-2026)
- [LAVA-NOT-IMPLEMENTED-33 closed; TRACKER-FIXED-LEFT-OPEN-36, 11 October 2026](#lava-not-implemented-33-closed-tracker-fixed-left-open-36-11-october-2026)
- [CHIM-BALMORA-RING-GROWTH-36, 11 October 2026](#chim-balmora-ring-growth-36-11-october-2026)
- [CHIM-ARENA-HUNK-GAP-36 and EMU-JIT-FAULT-ADDRESS-36; version 0.0.36-dev4, 11 October 2026](#chim-arena-hunk-gap-36-and-emu-jit-fault-address-36-version-0036-dev4-11-october-2026)
- [PLAYTEST-SHIPPED-WITHOUT-SMOKE-36, 11 October 2026](#playtest-shipped-without-smoke-36-11-october-2026)
- [BUILD-MINIWIND-BALMORA-ASSUMED-36, 11 October 2026](#build-miniwind-balmora-assumed-36-11-october-2026)
- [ENGINE-FPCR-DANCE-36, ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36 and ENGINE-CEILF-PER-EDGE-36, 10 October 2026](#engine-fpcr-dance-36-engine-dead-fixedpoint-gradients-36-and-engine-ceilf-per-edge-36-10-october-2026)
- [ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36 and ENGINE-O2-STRNCPY-WARNINGS-36: engine profiles, 10 October 2026](#engine-upstream-spans8-sprite-loop-36-and-engine-o2-strncpy-warnings-36-engine-profiles-10-october-2026)
- [BUILD-RUN-FOLDER-PRECREATED-36, 11 October 2026](#build-run-folder-precreated-36-11-october-2026)
- [ENGINE-MUSIC-NO-OFF-SWITCH-36 and ENGINE-STRICT-WARNINGS-36, 11 October 2026](#engine-music-no-off-switch-36-and-engine-strict-warnings-36-11-october-2026)
- [CHIM-DEV3-MAPLOAD-CRASH-36 cause and CHIM-WORLD-INDEX-FILE-LIMIT-36, 11 October 2026](#chim-dev3-mapload-crash-36-cause-and-chim-world-index-file-limit-36-11-october-2026)
- [CHIM-DEV3-MAPLOAD-CRASH-36, 11 October 2026](#chim-dev3-mapload-crash-36-11-october-2026)
- [CHIM-EMPTY-POINT-HULL-36, 11 October 2026](#chim-empty-point-hull-36-11-october-2026)
- [BUILD-ACTOR-GATE-CHIM-FRAMES-36, AW-RESULT-RECIPE-SAVED-36 and VIVEC-ARENA-ACTORS-32 on CHIM, 11 October 2026](#build-actor-gate-chim-frames-36-aw-result-recipe-saved-36-and-vivec-arena-actors-32-on-chim-11-october-2026)
- [BUILD-REUSE-CUTOFF-MODE-36 and BUILD-SEYDA-BOUNDED-RUN-PATHS-36 (second case), 11 October 2026](#build-reuse-cutoff-mode-36-and-build-seyda-bounded-run-paths-36-second-case-11-october-2026)
- [BUILD-CHIM-STAGE-SERIAL-TAIL-36 and CHIM-STAIR-GATE-WORLD-RELOAD-36 repaired in source, 11 October 2026](#build-chim-stage-serial-tail-36-and-chim-stair-gate-world-reload-36-repaired-in-source-11-october-2026)
- [CACHE-NO-PROVENANCE-36, 11 October 2026](#cache-no-provenance-36-11-october-2026)
- [COLLISION-TRACE-LIMIT-ROUTED-ROOM-36, 11 October 2026](#collision-trace-limit-routed-room-36-11-october-2026)
- [BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36, 11 October 2026](#build-chim-sandbox-no-shared-sky-36-11-october-2026)
- [BUILD-MINIWIND-ARENA-PIT-REFUSED-36, 11 October 2026](#build-miniwind-arena-pit-refused-36-11-october-2026)
- [BUILD-MINIWIND-DIRECT-START-TOWN-36, 11 October 2026](#build-miniwind-direct-start-town-36-11-october-2026)
- [TEST-PARALLEL-ORDER-FLAKY-36, 11 October 2026](#test-parallel-order-flaky-36-11-october-2026)
- [Pipeline entries, correction, the eight build rules and the persisting set, 11 October 2026](#pipeline-entries-correction-the-eight-build-rules-and-the-persisting-set-11-october-2026)
- [IMAGE-ONE-HDF-TARGET-36, BUILD-CHIM-FRAME-SWAP-LATE-36, BUILD-IMAGE-AUDIO-SERIAL-36 and BUILD-PIPELINE-UNDERUTILIZATION-36, 11 October 2026](#image-one-hdf-target-36-build-chim-frame-swap-late-36-build-image-audio-serial-36-and-build-pipeline-underutilization-36-11-october-2026)
- [BUILD-OPTIMIZER-CACHE-KEY-BROAD-36, 11 October 2026](#build-optimizer-cache-key-broad-36-11-october-2026)
- [TOOLKIT-MONITOR-BLIND-PHASES-36, 11 October 2026](#toolkit-monitor-blind-phases-36-11-october-2026)
- [BUILD-IMAGE-CHIM-MAPS-SERIAL-36, 11 October 2026](#build-image-chim-maps-serial-36-11-october-2026)
- [BUILD-LEGACY-TOWN-MAPS-SHIPPED-36, 11 October 2026](#build-legacy-town-maps-shipped-36-11-october-2026)
- [BUILD-SILENT-PHASES-36, 11 October 2026](#build-silent-phases-36-11-october-2026)
- [CHIM-FRAME-COORD-RANGE-33: wide coordinate spike in source, 10 October 2026](#chim-frame-coord-range-33-wide-coordinate-spike-in-source-10-october-2026)
- [CHIM-PREDICT-VIVEC-LOW-36 and CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36; CHIM-FRAME-COORD-RANGE-33 measured, 10 October 2026](#chim-predict-vivec-low-36-and-chim-detail-budget-seam-unaudited-36-chim-frame-coord-range-33-measured-10-october-2026)
- [BUILD-UNDERUSE-GATE-36, 11 October 2026](#build-underuse-gate-36-11-october-2026)
- [BUILD-PROFILE-SECTIONS-MISSING-36, BUILD-CHIM-STATS-SERIAL-TAIL-36 and CHIM-STAIR-GATE-WORLD-RELOAD-36, 11 October 2026](#build-profile-sections-missing-36-build-chim-stats-serial-tail-36-and-chim-stair-gate-world-reload-36-11-october-2026)
- [DOCS-VIVEC-FRAME-PLAN-36, 10 October 2026](#docs-vivec-frame-plan-36-10-october-2026)
- [BUILD-CHIM-STAIR-WALK-UNCACHED-36: only stair walks checked by a passed master build are reused, 10 October 2026](#build-chim-stair-walk-uncached-36-only-stair-walks-checked-by-a-passed-master-build-are-reused-10-october-2026)
- [CHIM-COMPILED-HULL-SHORT-36: model hull patch on by default; A/B/C/D of the town rings, 10 October 2026](#chim-compiled-hull-short-36-model-hull-patch-on-by-default-abcd-of-the-town-rings-10-october-2026)
- [ENGINE-UPSTREAM-ASM-UNUSED-36, 10 October 2026](#engine-upstream-asm-unused-36-10-october-2026)
- [ENGINE-RESIDENT-REGISTRY-GROWTH-36, 10 October 2026](#engine-resident-registry-growth-36-10-october-2026)
- [OPS-GATE-UNLISTED-TESTS-36 and BUILD-REUSE-AUDIT-WITHOUT-REASON-36, 10 October 2026](#ops-gate-unlisted-tests-36-and-build-reuse-audit-without-reason-36-10-october-2026)
- [BUILD-CHIM-STAGE-IDLE-START-36 repaired in source, 10 October 2026](#build-chim-stage-idle-start-36-repaired-in-source-10-october-2026)
- [CHIM-TOWN-HEAP-ROUTED-HULL-36; BUILD-CHIM-HEAP-GATE-LATE-36 and BUILD-CHIM-STAIR-WALK-UNCACHED-36 repaired in source, 10 October 2026](#chim-town-heap-routed-hull-36-build-chim-heap-gate-late-36-and-build-chim-stair-walk-uncached-36-repaired-in-source-10-october-2026)
- [BUILD-CHIM-HEAP-GATE-LATE-36 and BUILD-CHIM-STAIR-WALK-UNCACHED-36, 10 October 2026](#build-chim-heap-gate-late-36-and-build-chim-stair-walk-uncached-36-10-october-2026)
- [CHIM-COMPILED-HULL-SHORT-36: compiled model hulls, island-wide sweep, 10 October 2026](#chim-compiled-hull-short-36-compiled-model-hulls-island-wide-sweep-10-october-2026)
- [WAIT-FEET-IN-WATER-36, 10 October 2026](#wait-feet-in-water-36-10-october-2026)
- [WAIT-DURING-COMBAT-36, 10 October 2026](#wait-during-combat-36-10-october-2026)
- [PLAYER-DEATH-LIMBO-35 and COMBAT-PLAYER-DEATH-FALL-33 repaired in source, 10 October 2026](#player-death-limbo-35-and-combat-player-death-fall-33-repaired-in-source-10-october-2026)
- [BUILD-PROGRESS-ETA-BASIS-36, 10 October 2026](#build-progress-eta-basis-36-10-october-2026)
- [BUILD-CHIM-STAGE-IDLE-START-36, 10 October 2026](#build-chim-stage-idle-start-36-10-october-2026)
- [CHIM-COMPILED-HULL-SHORT-36 and BUILD-CHIM-VALIDATE-LATE-36, 10 October 2026](#chim-compiled-hull-short-36-and-build-chim-validate-late-36-10-october-2026)
- [BUILD-REUSE-REDUCED-RECORD-36, 10 October 2026](#build-reuse-reduced-record-36-10-october-2026)
- [PHYSICS-GRAVITY-SCALE-36, 10 October 2026](#physics-gravity-scale-36-10-october-2026)
- [BUILD-HARVEST-NATIVE-TOWN-ORDER-36, 10 October 2026](#build-harvest-native-town-order-36-10-october-2026)
- [HANG-IDLE-DUSK-35: cause found, 10 October 2026](#hang-idle-dusk-35-cause-found-10-october-2026)
- [BUILD-LEGACY-CHAIN-DEFAULT-36, 10 October 2026](#build-legacy-chain-default-36-10-october-2026)
- [HANG-IDLE-DUSK-35 game side repaired in source, ENGINE-SYNC-IO-MAIN-LOOP-36, 10 October 2026](#hang-idle-dusk-35-game-side-repaired-in-source-engine-sync-io-main-loop-36-10-october-2026)
- [BUILD-ENGINE-SOURCE-KEY-BROAD-36, 10 October 2026](#build-engine-source-key-broad-36-10-october-2026)
- [TEST-GODMODE-UNLISTED-36, 10 October 2026](#test-godmode-unlisted-36-10-october-2026)
- [BUILD-IMAGE-NATIVE-BALMORA-CACHE-36, 10 October 2026](#build-image-native-balmora-cache-36-10-october-2026)
- [CHIM-REGION-DIVIDED-CELLS-36, 10 October 2026](#chim-region-divided-cells-36-10-october-2026)
- [CHIM-REGION-MARGIN-STORAGE-36: terrain references and the compiled terrain hull, 10 October 2026](#chim-region-margin-storage-36-terrain-references-and-the-compiled-terrain-hull-10-october-2026)
- [HANG-IDLE-DUSK-35, 10 October 2026](#hang-idle-dusk-35-10-october-2026)
- [NPC-WANDER-NOT-EXECUTED-35, 10 October 2026](#npc-wander-not-executed-35-10-october-2026)
- [ANIMKIT-COVERAGE-35, 10 October 2026](#animkit-coverage-35-10-october-2026)
- [PLAYER-DEATH-LIMBO-35, 10 October 2026](#player-death-limbo-35-10-october-2026)
- [COMBAT-MUSIC-AIR-SWING-35, 10 October 2026](#combat-music-air-swing-35-10-october-2026)
- [BUILD-REUSE-CASCADE-36: five causes found and repaired in source, 10 October 2026](#build-reuse-cascade-36-five-causes-found-and-repaired-in-source-10-october-2026)
- [LAUNCHER-GL-CONTEXT-FALLBACK-36, 10 October 2026](#launcher-gl-context-fallback-36-10-october-2026)
- [BUILD-REUSE-CASCADE-36, 10 October 2026](#build-reuse-cascade-36-10-october-2026)
- [CHIM-REGION-MARGIN-STORAGE-36, 10 October 2026](#chim-region-margin-storage-36-10-october-2026)
- [CHIM-STITCH-SHORELINE-36 and CHIM-FAR-BAND-GAP-36 repaired in source, 10 October 2026](#chim-stitch-shoreline-36-and-chim-far-band-gap-36-repaired-in-source-10-october-2026)
- [CHIM-NATIVE-HARVEST-MISSING-36, 10 October 2026](#chim-native-harvest-missing-36-10-october-2026)
- [CHIMPORT-POOL-CROSS-MOUNT-36, 10 October 2026](#chimport-pool-cross-mount-36-10-october-2026)
- [BUILD-IMAGE-CHIM-NATIVE-TOWN-36, 10 October 2026](#build-image-chim-native-town-36-10-october-2026)
- [BUILD-REUSE-PLAN-ENV-36, 10 October 2026](#build-reuse-plan-env-36-10-october-2026)
- [CHIM-STITCH-SHORELINE-36, CHIM-FAR-BAND-GAP-36 and CHIM-HANDOFF-POPIN-36, 10 October 2026](#chim-stitch-shoreline-36-chim-far-band-gap-36-and-chim-handoff-popin-36-10-october-2026)
- [COLLISION-ROUTE-NO-SPLIT-36, 10 October 2026](#collision-route-no-split-36-10-october-2026)
- [CHIMPORT-DOOR-MARKER-AUDIT-36, 10 October 2026](#chimport-door-marker-audit-36-10-october-2026)
- [CHIMPORT-RETRY-AUDIT-FAILED-36, 10 October 2026](#chimport-retry-audit-failed-36-10-october-2026)
- [CHIM-ACTOR-GROUNDING-POLICY-36 fixed, 10 October 2026](#chim-actor-grounding-policy-36-fixed-10-october-2026)
- [TRACKER-SEA-CELL-SET-36, 10 October 2026](#tracker-sea-cell-set-36-10-october-2026)
- [CHIM-ACTOR-GROUNDING-POLICY-36, 10 October 2026](#chim-actor-grounding-policy-36-10-october-2026)
- [CHIM-SLOWCPU-FRAMETIME-33: Balmora on CHIM at about 1 frame per second on a slow 68040, 9 October 2026](#chim-slowcpu-frametime-33-balmora-on-chim-at-about-1-frame-per-second-on-a-slow-68040-9-october-2026)
- [CI-NEW-BUILDER-RULES-35, 10 October 2026](#ci-new-builder-rules-35-10-october-2026)
- [ANIMKIT-TORCH-STANDING-35, 10 October 2026](#animkit-torch-standing-35-10-october-2026)
- [TEST-WORKER-SYSPATH-32, 10 October 2026](#test-worker-syspath-32-10-october-2026)
- [ANIMKIT-ACTOR-ABI-SITES-35, 10 October 2026](#animkit-actor-abi-sites-35-10-october-2026)
- [ANIMKIT-ITEM-TAG-FRAMES-35, 10 October 2026](#animkit-item-tag-frames-35-10-october-2026)
- [BUILD-CELL-PROGRESS-KEY-BUGS-35, 10 October 2026](#build-cell-progress-key-bugs-35-10-october-2026)
- [BUILD-POOL-ARG-UNFINGERPRINTED-35, 10 October 2026](#build-pool-arg-unfingerprinted-35-10-october-2026)
- [ANIMKIT-IMAGE-FORMATS-35, 10 October 2026](#animkit-image-formats-35-10-october-2026)
- [BUILD-SEYDA-REPORT-HOST-PATHS-35, 10 October 2026](#build-seyda-report-host-paths-35-10-october-2026)
- [BUILD-CHIM-KEY-UNDERDECLARED-35, 10 October 2026](#build-chim-key-underdeclared-35-10-october-2026)
- [BUILD-POOL-APPLY-READ-MISS-35, 10 October 2026](#build-pool-apply-read-miss-35-10-october-2026)
- [BUILD-SCENE-DIAGNOSTIC-COPY-35, 10 October 2026](#build-scene-diagnostic-copy-35-10-october-2026)
- [BUILD-POOL-READONLY-SCENE-WRITE-35, 10 October 2026](#build-pool-readonly-scene-write-35-10-october-2026)
- [BUILD-RESUME-OUTPUTS-DIFFER-35, 10 October 2026](#build-resume-outputs-differ-35-10-october-2026)
- [BUILD-RESUME-HAZARD-STATIC-35, 10 October 2026](#build-resume-hazard-static-35-10-october-2026)
- [BUILD-GALLERY-JSON-KEY-ORDER-35, 10 October 2026](#build-gallery-json-key-order-35-10-october-2026)
- [ANIMKIT-GROUND-CHECK-LAYOUT-35, 10 October 2026](#animkit-ground-check-layout-35-10-october-2026)
- [NPC-NO-RUN-ANIM-35, 10 October 2026](#npc-no-run-anim-35-10-october-2026)
- [BUILD-SEYDA-CONVERTED-NOT-STAGED-35, 10 October 2026](#build-seyda-converted-not-staged-35-10-october-2026)
- [BUILD-IMAGE-STALE-PYTHONPATH-35, 10 October 2026](#build-image-stale-pythonpath-35-10-october-2026)
- [BUILD-REUSE-KEYS-TOO-BROAD-35, 10 October 2026](#build-reuse-keys-too-broad-35-10-october-2026)
- [Engine crash paths and engine table limits (BUILD-BUDGET-ENGINE-LIMITS-35 and fifteen more), 10 October 2026](#engine-crash-paths-and-engine-table-limits-build-budget-engine-limits-35-and-fifteen-more-10-october-2026)
- [CHIMPORT-NO-SHARED-POOL-35, 10 October 2026](#chimport-no-shared-pool-35-10-october-2026)
- [Engine review fixes (ENGINE-PAK-HEADER-TRUST-35 and thirteen more), 10 October 2026](#engine-review-fixes-engine-pak-header-trust-35-and-thirteen-more-10-october-2026)
- [MWAD data-reader review fixes, 10 October 2026](#mwad-data-reader-review-fixes-10-october-2026)
- [CHIM streaming crash paths from a source review, 10 October 2026](#chim-streaming-crash-paths-from-a-source-review-10-october-2026)
- [BUILD-FLORA-FALLBACK-RETRY-35, 10 October 2026](#build-flora-fallback-retry-35-10-october-2026)
- [BUILD-CACHE-OWNER-FAILS-STAGE-34 and the published-release check, 10 October 2026](#build-cache-owner-fails-stage-34-and-the-published-release-check-10-october-2026)
- [BUILD-SURVEY-KEY-CONFIG-35, 10 October 2026](#build-survey-key-config-35-10-october-2026)
- [BUILD-SCHEDULER-TABLE-KEY-35, 10 October 2026](#build-scheduler-table-key-35-10-october-2026)
- [CI-SUITE-TWICE-33, 10 October 2026](#ci-suite-twice-33-10-october-2026)
- [HARVEST-BITTERCOAST-29 and HARVEST-PLANTS-IN-COLLISION-33, 10 October 2026](#harvest-bittercoast-29-and-harvest-plants-in-collision-33-10-october-2026)
- [MESH-LOD-OPEN-SEAMS-33 and CHIM-STRIDER-RING-33 for v0.0.34, 10 October 2026](#mesh-lod-open-seams-33-and-chim-strider-ring-33-for-v0034-10-october-2026)
- [BUILD-SEYDA-REGEN-30 fixed in source: no recorded Seyda Neen input, 10 October 2026](#build-seyda-regen-30-fixed-in-source-no-recorded-seyda-neen-input-10-october-2026)
- [TOOLKIT-MAP-SCALING-36, 11 October 2026](#toolkit-map-scaling-36-11-october-2026)
- [TRACKER-OCEAN-COUNTED-DONE-36, 11 October 2026](#tracker-ocean-counted-done-36-11-october-2026)

<!-- contents end -->

## Stair fixes verified, AW-LEASE-NO-GROW-36, 11 October 2026

VIVEC-TEMPLE-STAIRS-33, STAIRS-EBONHEART-CHIM-36, STAIRS-VIVEC-ROOMS-JOINT-36 and BUILD-IMAGE-STAIR-WALK-SERIAL-36 are fixed
in v0.0.36. The whole-city Vivec MiniWind built from the integration line accepted no stair findings and had no blocking
failures, and every flight step of its 130 rooms passed. Its image stair walk covered 132 maps in 252.6 s on 16 workers;
before, it took 15 min 55 s on 1.8 cores. BUILD-STAIR-KEY-BOOKKEEPING-36 stays open until a rebuild shows the walks
reused. AW-LEASE-NO-GROW-36 (owner): a gate that starts or ends now shrinks or grows the running builds; their worker
pools still keep the size they started with.

## CHIM-FRAME-EDGE-EFRAG-CRASH-36 fixed, 11 October 2026

CHIM-FRAME-EDGE-EFRAG-CRASH-36 is fixed in v0.0.36. It was reported four times, by the owner in normal play among them.
The root cause was in CL_RelinkEntities: it pointed its loop cursor at the third-person body, so every entity after it
was read and written from the wrong memory. The body now has its own pointer, and labelled safety nets guard the efrag
links. In integration gate 2203 the smoke had Seyda Neen and Balmora in play, and the safety net was never used.

## AW-LEASE-MEMORY-DEADLOCK-36 fixed, 11 October 2026

AW-LEASE-MEMORY-DEADLOCK-36 is fixed in v0.0.36-dev5. The master builder's default memory lease now fits beside a running
gate. A request for more memory than the host leases at all is refused at once instead of waiting in the queue, and a
waiting request reads the config again each time it checks.

## TRACKER-REGISTER-SIZE-36, 11 October 2026

TRACKER-REGISTER-SIZE-36: bugs.json passed 75 % of its 1 MiB release text limit (789,008 bytes). The rotation rule
frees under 3 KB, so the warning for bugs.json is 85 % for now (the hard limit is unchanged); a second archive for
fixed bugs of v0.0.34 and v0.0.35 follows right after the v0.0.36 release, and the warning returns to 75 %.

## SMOKE-PASSES-WITHOUT-MAP-36, 11 October 2026

SMOKE-PASSES-WITHOUT-MAP-36: the engine boot smoke passed while its first map ran under the title menu: the smoke loaded
Seyda Neen during the startup logo, the logo's end opened the menu over it, and the smoke only checked the server's map
name. In 109 of 142 gate smokes since 10 October only the second load (Balmora) was shown in play. The smoke now proves
every map in play (screen, signon, world leaves) and a map started during the logo stays in play.

## CHIM-FRAME-EDGE-EFRAG-CRASH-36 (persisting) and ENGINE-CRASH-EXIT-KEYBOARD-36, 11 October 2026

CHIM-FRAME-EDGE-EFRAG-CRASH-36 is PERSISTING: after the README screenshot session, the owner hit "R_StoreEfrags: Bad
entity type 270440" in normal play of the v0.0.36-dev5 playtest (FS-UAE JIT, Seyda Neen, backing away from a hostile
NPC). The value is the long at Amiga address 0x44, which is where model_t.type is read when the model is NULL: a leaf
link points to an entity whose model was cleared after it was linked. ENGINE-CRASH-EXIT-KEYBOARD-36: after that crash
the AmigaDOS shell typed "amiwind" as "AIWDID" (shift/caps latched, M and N eaten), consistent with the engine's
input.device handler left in the chain on the crash route.

Root cause, confirmed the same day by a same-scene comparison: the third-person view's player body overwrote the entity
loop pointer in CL_RelinkEntities, so the rest of that frame's entities were walked in foreign memory and damaged leaf
links. Without the fix the Seyda Neen third-person scene froze (2 of 2 runs) and the Balmora idle camera damaged a link
(2 of 2); with it, all runs were clean.

## TEST-PROFILE-OVERHEAD-SAMPLES-36, 11 October 2026

TEST-PROFILE-OVERHEAD-SAMPLES-36: integration gate 2037 failed the profiler overhead test while a full build ran beside
it. The sampler took 6 samples in its fixed 2 s; the test needs more than 20. It now samples until it has enough, for at
most 15 s. This is the same kind of fault as TEST-PARALLEL-SHARE-TIMING-36. Fixed in v0.0.36-dev5.

## WORLDMAP-LAVA-MISMATCH-36, AW-LEASE-MEMORY-DEADLOCK-36 and BUILD-END-USER-LAUNCHERS-36, 11 October 2026

WORLDMAP-LAVA-MISMATCH-36 (owner, dev5 on FS-UAE): in Molag Amar the map shows a lava band under the player, but the
game shows grass. AW-LEASE-MEMORY-DEADLOCK-36: the new memory leases kept 44 GiB builds waiting for as long as any gate
ran. The stopgap is smaller leases in the config and the waiting requests restarted; the repair in the master builder is
pending. BUILD-END-USER-LAUNCHERS-36 (owner request): the builder's simple mode should write a Python launcher, an
FS-UAE config and a WinUAE config for each build.
## CHIM-FRAME-EDGE-EFRAG-CRASH-36 (persisting) and ENGINE-CRASH-EXIT-KEYBOARD-36, 11 October 2026

CHIM-FRAME-EDGE-EFRAG-CRASH-36 is PERSISTING: after the README screenshot session, the owner hit "R_StoreEfrags: Bad
entity type 270440" in normal play of the v0.0.36-dev5 playtest (FS-UAE JIT, Seyda Neen, backing away from a hostile
NPC). The value is the long at Amiga address 0x44, which is where model_t.type is read when the model is NULL: a leaf
link points to an entity whose model was cleared after it was linked. ENGINE-CRASH-EXIT-KEYBOARD-36: after that crash
the AmigaDOS shell typed "amiwind" as "AIWDID" (shift/caps latched, M and N eaten), consistent with the engine's
input.device handler left in the chain on the crash route.

## TEST-PARALLEL-SHARE-TIMING-36, 11 October 2026

TEST-PARALLEL-SHARE-TIMING-36: integration gate 2032 failed the fair-share scheduler test while two full builds ran
beside it. The test watched for the freed worker budget during a fixed 4 s, and the busy host outlasted it. The watcher
now waits until it sees the budget, for at most 20 s. Fixed in v0.0.36-dev5.

## CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36, COMBAT-BLOCKING-36 and the platform field, 11 October 2026

From the owner's dev5 playtest on FS-UAE with JIT. [CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36](bugs/CAMERA-THIRDPERSON-COMBAT-NPC-HIDDEN-36.md):
during a fight, switching to third person (Tab) hides the NPC you are fighting; it comes back in first person. The
cause is not known yet. [COMBAT-BLOCKING-36](bugs/COMBAT-BLOCKING-36.md) is a request: blocking in combat. NPCs should block by
their Block skill with a block animation, and the player should block with the right mouse button, so the companion pick
moves to another key.
Both are targeted at v0.0.37.

CHIM-FRAME-EDGE-EFRAG-CRASH-36 is PERSISTING. The owner hit the same efrag crash in normal play of the dev5 build in
Seyda Neen, after it was first seen in a noclip view past the Vivec frame edge. It blocks rc1.

Bug entries now carry a `platform` field, the platform or emulator a bug was seen on. The owner's game-side reports
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

## BUILD-CHIM-STAIR-WALK-UNCACHED-36 fixed, 11 October 2026

BUILD-CHIM-STAIR-WALK-UNCACHED-36 is fixed in v0.0.36-dev5 (3d2499e). The CHIM stair gate now keys each frame by the SHA-256
of exactly what the walk reads, so a texture table or model numbering change no longer re-walks every frame, and its walk
units run on every core. On the coast2 frames the walk took 798 s on 3.6 cores; now a cold run takes 187.5 s and a warm run
7.6 s with no frame walked. The rows are byte-identical. The perf guard job and the stairs-rc1 job had both registered
BUILD-IMAGE-STAIR-WALK-SERIAL-36; the two entries are now one, with both reports on its page.

## AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36 and BUILD-PROFILER-NO-WASTE-ALARM-36 fixed, 11 October 2026

AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36 is fixed in v0.0.36-dev5. The master builder now leases cores and memory for the
whole machine. A build that does not fit waits in a queue, release builds go first, and the leases of finished jobs
expire. BUILD-PROFILER-NO-WASTE-ALARM-36 is fixed too. The perf guard fails a build when a parallel section turns serial,
loses its core share, or gets slower for the same work.

## BUILD-STAGE-INTERRUPT-ABSORBED-36 and BUILD-EXECUTABLES-LIST-UNGATED-36 fixed, 11 October 2026

BUILD-STAGE-INTERRUPT-ABSORBED-36 and BUILD-EXECUTABLES-LIST-UNGATED-36 are fixed in v0.0.36-dev5 (9ec4893). The stage
wrapper now passes Ctrl-C on and the build stops. Committed executables are checked against the release list before a
gate runs. Integration gate 2025 passed (3,821 tests, boot smoke).
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

## CHIM-HEAP-INT-MATMUL-36, 11 October 2026

CHIM-HEAP-INT-MATMUL-36: the CHIM heap scan multiplied its 0/1 chunk, model and texture tables as int32, which numpy
runs in its own plain loop. On the whole-city Vivec world the setup (1,764 chunk images) took 0.4 s and the scan
52.3 s. The tables are float32 now (exact for these counts) and the scan slices smaller: heap gate 58.2 s -> 5.5 s,
frame-map heap check 72.1 s -> 7.3 s, reports byte-identical (SHA-256).

## CHIM-REGION-DIVIDED-CELLS-36 (persisting) and AW-RUN-NAME-LONG-REASON-36, 11 October 2026

[CHIM-REGION-DIVIDED-CELLS-36](bugs/CHIM-REGION-DIVIDED-CELLS-36.md) PERSISTING (v0.0.36-dev2, -dev3, -dev4 all
stopped at the same 270 CHIM cells): the preflight counted the tracker's map list, which also names every map whose
apron holds an object of the cell; 473 of 621 finished land cells are one map and only 148 are truly 2 x 2 or 4 x 4.
Repaired in source on v0.0.36-chimport-x: a divided cell is one CHIM frame whose first map's directory row owns the
whole cell (the other rows are aliases; no engine change); 661 cells now pass the preflight.
[AW-RUN-NAME-LONG-REASON-36](bugs/AW-RUN-NAME-LONG-REASON-36.md): `aw gate` with a long reason was refused after
leasing its gate number (the run name is the request id, at most 128 characters); the reason part is now shortened.
[CHIMPORT-RETRY-LAVA-STALE-SOURCE-36](bugs/CHIMPORT-RETRY-LAVA-STALE-SOURCE-36.md): the island hull-policy rerun stopped 25
inland lava cells on a source stage older than the lava conversion (open).
## BUILD-PASS-KEY-RULE-NO-CARRYOVER-36, BUILD-STAIR-KEY-BOOKKEEPING-36, BUILD-STAGE-INTERRUPT-ABSORBED-36 and BUILD-EXECUTABLES-LIST-UNGATED-36, 11 October 2026

[BUILD-PASS-KEY-RULE-NO-CARRYOVER-36](bugs/BUILD-PASS-KEY-RULE-NO-CARRYOVER-36.md): dev4 recomputed 2,372 optimizer
maps and the exterior sky maps although code and outputs were identical to dev3: two key rule changes carried no
entries written by older trees. The pool is healed (stable form-2 keys); the previous-rule lookup carried the cull
and head passes. [BUILD-STAIR-KEY-BOOKKEEPING-36](bugs/BUILD-STAIR-KEY-BOOKKEEPING-36.md): stair walk keys count
the progress lines and the record bookkeeping; open.
[BUILD-STAGE-INTERRUPT-ABSORBED-36](bugs/BUILD-STAGE-INTERRUPT-ABSORBED-36.md): the stage wrapper absorbed Ctrl-C;
it now ends by the interrupt. [BUILD-EXECUTABLES-LIST-UNGATED-36](bugs/BUILD-EXECUTABLES-LIST-UNGATED-36.md):
committed file modes are checked against EXECUTABLES before a gate.

## Register rotation, 11 October 2026

`docs/bugs/bugs.json` reached its release size limit (786,357 of 786,432 bytes). Fixed or closed bugs first found in v0.0.33 or earlier, and not persisting, now rotate into a frozen archive of the same schema, `docs/bugs/archive/bugs-v0.0.29-v0.0.33.json` (52 bugs). The tools, the register, the CHIM tracker and the tests read both files; IDs stay unique across them and report pages stay where they are. No limit was raised.
## CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36 and BUILD-POOL-READONLY-SCENE-WRITE-35 (persisting), 11 October 2026

[CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36](bugs/CHIM-NATIVE-IMAGE-NO-SHARED-SKY-36.md): an image whose exteriors are only
CHIM frame maps (every MiniWind of a CHIM-native town) had no shared sky; the exterior sky pass installed it only with
legacy exteriors. Repaired in source on v0.0.36-seyda-chim. [BUILD-POOL-READONLY-SCENE-WRITE-35](bugs/BUILD-POOL-READONLY-SCENE-WRITE-35.md)
PERSISTING: the scene stages that edit their inherited tree in place (area first) failed on read-only pool links of a
reused earlier stage; they now unshare those links first (`mwad.paths.unshare_tree`). Both found by the Seyda Neen
MiniWind runs.

## BUILD-LEGACY-TOWN-MAPS-SHIPPED-36 and BUILD-CHIM-FRAME-SWAP-LATE-36: Seyda Neen CHIM-native, 11 October 2026

PERSISTING, repaired in source on v0.0.36-seyda-chim: [BUILD-LEGACY-TOWN-MAPS-SHIPPED-36](bugs/BUILD-LEGACY-TOWN-MAPS-SHIPPED-36.md)
and [BUILD-CHIM-FRAME-SWAP-LATE-36](bugs/BUILD-CHIM-FRAME-SWAP-LATE-36.md). Seyda Neen is CHIM-native: the new
chim-town-seyda stage takes its frame and opening-scene entities from the scene stage's complete town by the legacy
chain's own cut and flora rules, so no Seyda Neen region map is cut in the actor-contact stage or the image step (65
maps, compiled twice before). Parity with the v0.0.36-dev3 frame maps: 243, 56 and 14 entities identical. The world
manifest no longer accepts a town chain as "kept because"; a legacy chain of a CHIM area needs a retired flag.

## BUILD-PASS-KEY-OVERBROAD-36, 11 October 2026

[BUILD-PASS-KEY-OVERBROAD-36](bugs/BUILD-PASS-KEY-OVERBROAD-36.md): Vivec stage A try3 recomputed all 275 character head
previews although every input was already in the shared cache. The pass key had changed twice without a change any
preview runs: try2 by an edit to the cache's own key code (`tools/pass_cache.py`), try3 by a new function in
`tools/build_parallel.py` (pass caches still counted every function's default values as import-time code). Repaired in
source on v0.0.36-build-timeline: pass and unit keys use the stage keys' import-time form and leave the cache module
out; a miss is looked up once under the older key form (SHA-256 verified) and recorded under the new key.
## AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36, 11 October 2026

[AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36](bugs/AW-CONCURRENT-BUILDS-OVERSUBSCRIBE-36.md): two full builds and several gates at once ran
the machine out of memory in a gate step (gate 1936, "cp: Cannot allocate memory") and halved every build's core use. Repair
planned: machine-wide core and memory leases with priority in the master builder.

## LAVA-NOT-IMPLEMENTED-33 closed; TRACKER-FIXED-LEFT-OPEN-36, 11 October 2026

[LAVA-NOT-IMPLEMENTED-33](bugs/LAVA-NOT-IMPLEMENTED-33.md) is fixed since v0.0.35 (liquid lava with damage, tint and sound);
its entry had stayed open ([TRACKER-FIXED-LEFT-OPEN-36](bugs/TRACKER-FIXED-LEFT-OPEN-36.md)). CHIM cells with lava pools get
the same liquid when CHIMport reaches them.

## CHIM-BALMORA-RING-GROWTH-36, 11 October 2026

[CHIM-BALMORA-RING-GROWTH-36](bugs/CHIM-BALMORA-RING-GROWTH-36.md): with the converter mesh method Balmora no longer fits the
CHIM zone (10,928 B over at one ring); the mesh method table (planar merge), now the default, passes with 68,192 B to spare.
The change since v0.0.36-dev3 that grew the ring is to be measured.

## CHIM-ARENA-HUNK-GAP-36 and EMU-JIT-FAULT-ADDRESS-36; version 0.0.36-dev4, 11 October 2026

The Vivec stage A MiniWind passed its boot smoke (Arena loaded, 10 s in the scene). Two findings from it:
[CHIM-ARENA-HUNK-GAP-36](bugs/CHIM-ARENA-HUNK-GAP-36.md) (hunk gap under 2 MiB at the Arena, a memory review before stage B) and
[EMU-JIT-FAULT-ADDRESS-36](bugs/EMU-JIT-FAULT-ADDRESS-36.md) (two JIT fault-address lines, to check). The line moves to 0.0.36-dev4
for the next playtest (both dev3 crash fixes in).

## PLAYTEST-SHIPPED-WITHOUT-SMOKE-36, 11 October 2026

[PLAYTEST-SHIPPED-WITHOUT-SMOKE-36](bugs/PLAYTEST-SHIPPED-WITHOUT-SMOKE-36.md): our own process failure. The v0.0.36-dev3 private playtest package
went out with an engine that dies on every map load: no gate or ship step booted the engine, the ship step's "not
smoke-tested" note did not stop the publish, and about a dozen branches had been merged in one round. Repaired: a
boot-smoke rule for every package and engine gate, the automated FS-UAE engine smoke as a gate step, and small merge
rounds.
## BUILD-MINIWIND-BALMORA-ASSUMED-36, 11 October 2026

[BUILD-MINIWIND-BALMORA-ASSUMED-36](bugs/BUILD-MINIWIND-BALMORA-ASSUMED-36.md): Vivec stage A try 3 passed the actor gate
(CHIM-EMPTY-POINT-HULL-36 fixed the blocked resident) and failed the content fingerprint on the missing Balmora region
table. Fixed in source: only a full image or a Balmora MiniWind binds it.

## ENGINE-FPCR-DANCE-36, ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36 and ENGINE-CEILF-PER-EDGE-36, 10 October 2026

An independent read-only review of the engine's hot paths, three C-side costs, each registered on its own because
each is a separate change to measure and check pixel by pixel:
[ENGINE-FPCR-DANCE-36](bugs/ENGINE-FPCR-DANCE-36.md): every float-to-int conversion saves, changes and restores
the FPU control register (901 sites in the default engine);
[ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36](bugs/ENGINE-DEAD-FIXEDPOINT-GRADIENTS-36.md): fixed-point gradients that only
the 68020 assembly reads are computed for every surface;
[ENGINE-CEILF-PER-EDGE-36](bugs/ENGINE-CEILF-PER-EDGE-36.md): two library `ceil` calls per emitted edge.
Open: an engine C speed pass, per-section timers first.

## ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36 and ENGINE-O2-STRNCPY-WARNINGS-36: engine profiles, 10 October 2026

The engine can now be built with upstream AmiQuake's 68k assembly (`--engine-profile upstream`) and a selective
`-O2` (`--engine-opt o2`), both experimental; the default `c` engine is byte-identical to the one before;
[ENGINE_PROFILES.md](ENGINE_PROFILES.md), ENGINE-UPSTREAM-ASM-UNUSED-36). Two findings on the way:
[ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36](bugs/ENGINE-UPSTREAM-SPANS8-SPRITE-LOOP-36.md): upstream's assembly
`D_DrawSpans8` has the shape of the sprite span loop and never runs at the default `d_subdiv16 1`; it stays out of the
upstream profile. [ENGINE-O2-STRNCPY-WARNINGS-36](bugs/ENGINE-O2-STRNCPY-WARNINGS-36.md): the first `-O2` build
printed four `-Wstringop-truncation` warnings; the copies now use `Q_strcpy_bounded` (same bytes).
## BUILD-RUN-FOLDER-PRECREATED-36, 11 October 2026

[BUILD-RUN-FOLDER-PRECREATED-36](bugs/BUILD-RUN-FOLDER-PRECREATED-36.md): on the published head 8ad8810 every CHIM build
stopped in seconds with "File exists": the world map manifest was written into the run folder before the run made it.
Fixed in source: the run writes it when it makes its folder.

## ENGINE-MUSIC-NO-OFF-SWITCH-36 and ENGINE-STRICT-WARNINGS-36, 11 October 2026

[ENGINE-MUSIC-NO-OFF-SWITCH-36](bugs/ENGINE-MUSIC-NO-OFF-SWITCH-36.md): while isolating CHIM-DEV3-MAPLOAD-CRASH-36 the
soundtrack could only be turned off by deleting music/playlist.txt; there is no cvar, option or builder flag. Planned:
a music on/off cvar and builder option with a test. [ENGINE-STRICT-WARNINGS-36](bugs/ENGINE-STRICT-WARNINGS-36.md): a
diagnostic engine build with -Wextra, -Wmaybe-uninitialized, -Wshadow and -Wunused shows 482 warnings that the gate's
-Wall -Wno-unused hides (view.c 35, chim_world.c 18, ...). Planned: fix them all, then raise the gate flags.

## CHIM-DEV3-MAPLOAD-CRASH-36 cause and CHIM-WORLD-INDEX-FILE-LIMIT-36, 11 October 2026

[CHIM-DEV3-MAPLOAD-CRASH-36](bugs/CHIM-DEV3-MAPLOAD-CRASH-36.md): cause found by an A/B sweep and a build bisect
(c8bf614 dies, its parent loads): the asynchronous music reader used the pointer from AllocDosObject(DOS_STDPKT) as a
StandardPacket, though it is the DosPacket part, so every music read corrupted memory. Fixed in aw_aread.c, keeping the
HANG-IDLE-DUSK-35 behaviour. [CHIM-WORLD-INDEX-FILE-LIMIT-36](bugs/CHIM-WORLD-INDEX-FILE-LIMIT-36.md): with that fixed,
every CHIM map of dev3 was refused: the engine read at most 4096 world files and the coast world has 7,236. One limit
(65535, the 16-bit file field) in the engine and the writer. The dev3 image loads Seyda Neen and Balmora with both fixes.

## CHIM-DEV3-MAPLOAD-CRASH-36, 11 October 2026

[CHIM-DEV3-MAPLOAD-CRASH-36](bugs/CHIM-DEV3-MAPLOAD-CRASH-36.md): the v0.0.36-dev3 playtest image, run in FS-UAE 3.1.66 with
its own engine and the shipped JIT preset, makes the emulator exit about 2 s after any map load (JIT faults at 0xabababab,
then an illegal access in the emulator); on the cycle-exact preset the game stops advancing. Found by a scripted bench run
after the playtest was published without a smoke test. Investigating: engine or data, then an engine bisect.
## CHIM-EMPTY-POINT-HULL-36, 11 October 2026

[CHIM-EMPTY-POINT-HULL-36](bugs/CHIM-EMPTY-POINT-HULL-36.md): the cause of the blocked Arena resident 241599. A CHIM
model without collision (a render-only tile of a cut model) had no point-hull node and a leaf root the engine reads as
solid contents; the engine also refuses an empty node lump on load. Fixed in source; CHIM validation now fails such a model.

## BUILD-ACTOR-GATE-CHIM-FRAMES-36, AW-RESULT-RECIPE-SAVED-36 and VIVEC-ARENA-ACTORS-32 on CHIM, 11 October 2026

The first Vivec stage A MiniWind failed in the image step: the actor gate read only BSP map actors
([BUILD-ACTOR-GATE-CHIM-FRAMES-36](bugs/BUILD-ACTOR-GATE-CHIM-FRAMES-36.md)); it now judges the CHIM town stage's frame
fit results too, and on that run reports Ordinator 241599 blocked on the frame collision
([VIVEC-ARENA-ACTORS-32](bugs/VIVEC-ARENA-ACTORS-32.md), persisting on CHIM). The master builder lost that run's result
document ([AW-RESULT-RECIPE-SAVED-36](bugs/AW-RESULT-RECIPE-SAVED-36.md)). Both fixed in source.
## BUILD-REUSE-CUTOFF-MODE-36 and BUILD-SEYDA-BOUNDED-RUN-PATHS-36 (second case), 11 October 2026

[BUILD-REUSE-CUTOFF-MODE-36](bugs/BUILD-REUSE-CUTOFF-MODE-36.md): in the v0.0.36-dev3 compiled-hull build the bsp stage
ran again and wrote byte-identical outputs, yet ten later stages were refused as "outputs differ": the reuse source had
itself reused bsp by hard link, read-only (0o444), and early cutoff compared modes with their write bits. Repaired in
source on v0.0.36-build-timeline: modes are compared without the write bits.
[BUILD-SEYDA-BOUNDED-RUN-PATHS-36](bugs/BUILD-SEYDA-BOUNDED-RUN-PATHS-36.md): second case found the same way: the
actor-contact stage's seyda-regions.json still named its intro-scene inputs by absolute run-folder path; now relative
to the run folder (the shipped table is unchanged).
## BUILD-CHIM-STAGE-SERIAL-TAIL-36 and CHIM-STAIR-GATE-WORLD-RELOAD-36 repaired in source, 11 October 2026

[BUILD-CHIM-STAGE-SERIAL-TAIL-36](bugs/BUILD-CHIM-STAGE-SERIAL-TAIL-36.md): after the parallel world build the chim
stage validated, heap-gated and zone-walked its 273 frames on one core (about 10 minutes of dev3). Now on the
shared worker pool, every unit reused by SHA-256: validation 8 min -> 160 s (28 s with nothing changed), heap gate
and zone walk 1 min each -> 36 s and 32 s. [CHIM-STAIR-GATE-WORLD-RELOAD-36](bugs/CHIM-STAIR-GATE-WORLD-RELOAD-36.md):
stair workers read one frame's files instead of the whole world: 44 min -> 169 s on the dev3 world, same report.
Both repaired on v0.0.36-chim-speed (not shipped).
## CACHE-NO-PROVENANCE-36, 11 October 2026

Every build cache was keyed by SHA-256 and the storage pool is content-addressed, but no entry said when, by which
run or from which version and commit it was made, and image pass entries had no output hash when a map was left
unchanged. tools/cache_provenance.py now records that for every cache writer in one format, without changing any
key or payload; older entries get backfilled records with each estimated or inferred field labelled.
[Report](bugs/CACHE-NO-PROVENANCE-36.md).

## COLLISION-TRACE-LIMIT-ROUTED-ROOM-36, 11 October 2026

[COLLISION-TRACE-LIMIT-ROUTED-ROOM-36](bugs/COLLISION-TRACE-LIMIT-ROUTED-ROOM-36.md): the tool collision tracer stops on the
Arena Pit's routed hull (visit limit) at its door arrival, which stopped the Arena Pit MiniWind in its image start check.
The check now records the spot as not traced (warning) instead of failing; the tracer is to be measured.

## BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36, 11 October 2026

[BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36](bugs/BUILD-CHIM-SANDBOX-NO-SHARED-SKY-36.md): an area build of a CHIM town with no
exterior Quake map shipped no shared sky, although its CHIM frame names it (the Vivec stage A image had none); the first
Arena Pit MiniWind stopped on it. Fixed in source: the prepared sky is installed for the frames and rooms that name it.

## BUILD-MINIWIND-ARENA-PIT-REFUSED-36, 11 October 2026

[BUILD-MINIWIND-ARENA-PIT-REFUSED-36](bugs/BUILD-MINIWIND-ARENA-PIT-REFUSED-36.md): the Vivec Arena Pit preset was refused
as "not converted" (IMPORT-TOWN-NO-INTERIORS-32) although the Pit (vai000) shipped in v0.0.35. The start resolver now
reads the town table's rooms and finds it. The real gap behind it: a CHIM-native Arena build runs no stage that makes the
town's listed rooms (the Vivec stage A try4 run has no vai000), so the start is refused before any stage naming that
missing stage. Open until a CHIM-native room stage exists. Then, the same day: the stage `chim-rooms-<town>` (tools/chim_rooms.py)
converts a CHIM-native town's listed rooms with the legacy chain's room converter (per-room hashed units, routed hulls)
and links the door banks both ways; a regression against v0.0.35, persisting ARENA-PIT-NO-INTERIOR-33. Fixed in
source; the real MiniWind build of vivec-arena-pit is the verification.

## BUILD-MINIWIND-DIRECT-START-TOWN-36, 11 October 2026

[BUILD-MINIWIND-DIRECT-START-TOWN-36](bugs/BUILD-MINIWIND-DIRECT-START-TOWN-36.md): the first Vivec stage A MiniWind request was
refused by the build check because the direct start of a MiniWind build was checked against Balmora only. Fixed in source:
the start is checked against the MiniWind build's own town; regression test in tests/test_direct_start.py.
## TEST-PARALLEL-ORDER-FLAKY-36, 11 October 2026

[TEST-PARALLEL-ORDER-FLAKY-36](bugs/TEST-PARALLEL-ORDER-FLAKY-36.md): a timing-sensitive parallel-build test failed in two gates and passed in three, all on unrelated branches. Open: make it deterministic and rerun it 50 times in CI.
Then the general rule (owner order the same day): every partial-area build starts inside what it holds. The start is
derived from the content (an explicit start inside a town picks that town; no start means the town's arrival point), a
start outside is refused before any stage naming what the build holds, and the image step checks the start map and
spot on the final payload before packing.

## Pipeline entries, correction, the eight build rules and the persisting set, 11 October 2026

Persisting, unresolved: the build-speed and dead-weight problems of the pipeline were found from 8 October 2026 on (image step
on one core, needless rebuilds, silent phases, legacy maps of CHIM areas), several were marked fixed, and all of them are still
present in v0.0.36-dev3. They are one set, indexed on the page of
[BUILD-PIPELINE-UNDERUTILIZATION-36](bugs/BUILD-PIPELINE-UNDERUTILIZATION-36.md) as eight build rules with every earlier entry.
Earlier entries marked fixed now say "persisting": [BUILD-REUSE-SCRATCH-UNDECLARED-33](bugs/BUILD-REUSE-SCRATCH-UNDECLARED-33.md),
[BUILD-IMAGE-CHIM-NATIVE-TOWN-36](bugs/BUILD-IMAGE-CHIM-NATIVE-TOWN-36.md) and
[BUILD-LEGACY-CHAIN-DEFAULT-36](bugs/BUILD-LEGACY-CHAIN-DEFAULT-36.md). Their history is not rewritten.

Correction, checked on the finished dev3 run: dev3 ships no legacy Seyda map. The image step builds 65 of them plus the 270
maps of CHIM region cells and removes them before packing (435,379,983 bytes removed), so the waste is build time (the Seyda
chain about 62 seconds, about 12.6 % of the 5 min 22 s optimizer), not payload. The 42 `bm*` maps in the image are Balmora
interiors and stay. The earlier "42 Balmora files, 69,038,532 bytes" and "302 MB shipped" figures were wrong and are withdrawn;
[BUILD-LEGACY-TOWN-MAPS-SHIPPED-36](bugs/BUILD-LEGACY-TOWN-MAPS-SHIPPED-36.md) and
[BUILD-CHIM-FRAME-SWAP-LATE-36](bugs/BUILD-CHIM-FRAME-SWAP-LATE-36.md) now say so. Removing them does not shrink the image, so the
one-HDF gap has to come from elsewhere ([IMAGE-ONE-HDF-TARGET-36](bugs/IMAGE-ONE-HDF-TARGET-36.md)).

New entries, all open: [BUILD-OPTIMIZER-CACHE-KEY-BROAD-36](bugs/BUILD-OPTIMIZER-CACHE-KEY-BROAD-36.md) (13 of 2,658 maps reused),
[BUILD-STATS-SERIAL-36](bugs/BUILD-STATS-SERIAL-36.md), [BUILD-PROFILER-NO-WASTE-ALARM-36](bugs/BUILD-PROFILER-NO-WASTE-ALARM-36.md)
and [BUILD-PARTITION-GROWTH-UNGATED-36](bugs/BUILD-PARTITION-GROWTH-UNGATED-36.md) (the disk-layout gate checks only the four Amiga
limits, not the image size or the partition count).

## IMAGE-ONE-HDF-TARGET-36, BUILD-CHIM-FRAME-SWAP-LATE-36, BUILD-IMAGE-AUDIO-SERIAL-36 and BUILD-PIPELINE-UNDERUTILIZATION-36, 11 October 2026

Four new entries from the v0.0.36-dev3 build, all open.
[IMAGE-ONE-HDF-TARGET-36](bugs/IMAGE-ONE-HDF-TARGET-36.md): the game ships as two image files (4,026,564,608 and
1,610,645,504 bytes) with three world partitions (DH0 + DW0 on disk 1, DW1 + DW2 on disk 2), the same layout as v0.0.35-dev1,
whose second disk was 1,879,080,960 bytes. Every partition is under 2 GiB and starts below 2 GiB, but the target is one HDF.
Path: dead weight out, store-once CHIM for the open world, a payload breakdown by kind in the image summary.
[BUILD-CHIM-FRAME-SWAP-LATE-36](bugs/BUILD-CHIM-FRAME-SWAP-LATE-36.md): 270 legacy open-world maps of CHIM cells
were built and processed, then removed at the end; a world map manifest
before the first stage fixes it. See the correction below for the legacy town maps.
[BUILD-IMAGE-AUDIO-SERIAL-36](bugs/BUILD-IMAGE-AUDIO-SERIAL-36.md): the audio payload (6,447 voices, 717 effects, 18 music,
17 videos) goes in serially on about 1.8 of 24 cores; hashed pool plus parallel units planned.
[BUILD-PIPELINE-UNDERUTILIZATION-36](bugs/BUILD-PIPELINE-UNDERUTILIZATION-36.md): the umbrella that links them with
BUILD-SILENT-PHASES-36 and BUILD-IMAGE-CHIM-MAPS-SERIAL-36 and adds a profiler check that fails a benchmark build on idle sections.
## BUILD-OPTIMIZER-CACHE-KEY-BROAD-36, 11 October 2026

[BUILD-OPTIMIZER-CACHE-KEY-BROAD-36](bugs/BUILD-OPTIMIZER-CACHE-KEY-BROAD-36.md): regression - the image step's optimizer pass
cache reused 13 of 2,658 maps because its key covers the whole image tool. Open.

## TOOLKIT-MONITOR-BLIND-PHASES-36, 11 October 2026

[TOOLKIT-MONITOR-BLIND-PHASES-36](bugs/TOOLKIT-MONITOR-BLIND-PHASES-36.md): the Monitor shows nothing during silent build phases.
Open: Activity panel from the live trace, phases and a live stage timeline.

## BUILD-IMAGE-CHIM-MAPS-SERIAL-36, 11 October 2026

[BUILD-IMAGE-CHIM-MAPS-SERIAL-36](bugs/BUILD-IMAGE-CHIM-MAPS-SERIAL-36.md): the image step writes the 270 CHIM region-cell maps one
by one on half a core, silently. Open: parallel, cached by SHA-256, with progress.
Cause: each map read and checked the whole CHIM world again (about 5 s). Repaired in source: the world is read
once, the maps are made on the shared worker pool and kept in the image pass cache by SHA-256; timed phases.

## BUILD-LEGACY-TOWN-MAPS-SHIPPED-36, 11 October 2026

[BUILD-LEGACY-TOWN-MAPS-SHIPPED-36](bugs/BUILD-LEGACY-TOWN-MAPS-SHIPPED-36.md): the CHIM-native towns still ship their legacy region
maps (about 300 MB). New builder rule: legacy maps of CHIM areas leave the build unless the engine still loads them.

## BUILD-SILENT-PHASES-36, 11 October 2026

[BUILD-SILENT-PHASES-36](bugs/BUILD-SILENT-PHASES-36.md): builder phases print no start/end timing or progress, and the CHIM
stats step runs silent on one core after the stair gate. Fix in progress: section timer, progress lines, heartbeat, visible by default.
## CHIM-FRAME-COORD-RANGE-33: wide coordinate spike in source, 10 October 2026

[CHIM-FRAME-COORD-RANGE-33](bugs/CHIM-FRAME-COORD-RANGE-33.md): owner decision, widen the coordinates
first and then build one Vivec city frame. The engine switch `AW_EXP_WIDECOORD` (off by default) sends
positions as 24 bits of 1/256 units (+/-32,768 units, protocol 1015) and raises the frame and arrival
bounds (`AW_COORD_BOUND`); every 4000 / 4096 in the engine and the builder's frame checks is classified in
`config/coord-range-audit.json`, and a test keeps the list complete. The default build is unchanged; the
wide engine compiles with no warnings. Not yet measured: sign-on size, bytes and time per frame.

## CHIM-PREDICT-VIVEC-LOW-36 and CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36; CHIM-FRAME-COORD-RANGE-33 measured, 10 October 2026

Found by the Vivec on CHIM preflight (milestone M3, phase 1: read-only, no build).
[CHIM-PREDICT-VIVEC-LOW-36](bugs/CHIM-PREDICT-VIVEC-LOW-36.md): the CHIM memory predictor, fitted on Balmora and
Seyda Neen, predicts every Vivec district frame 28-54 % below the heap gate of the frames built on 9 October;
Vivec meshes decode to 124-218 bytes per source triangle against the fitted 88.6. Vivec memory is decided by built
heap gates until it is refitted.
[CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36](bugs/CHIM-DETAIL-BUDGET-SEAM-UNAUDITED-36.md): the seam-tear audit measures
the town, group, open-world and interior reductions but not the CHIM detail budgets, so 'vivec-deep' (the statues
at 900 of 5,451 and 4,009 triangles) is not checked for opened seams before it becomes the Vivec default.
[CHIM-FRAME-COORD-RANGE-33](bugs/CHIM-FRAME-COORD-RANGE-33.md): of the two-frame option the north frame is 96 units
over the +/-4,000 bound on each side; three frames fit.
[RENDER-SURFACE-OVERFLOW-SILENT-36](bugs/RENDER-SURFACE-OVERFLOW-SILENT-36.md): faces past r_maxsurfs
(12,288) or edges past r_maxedges (24,576) are dropped with no warning; the Vivec Temple frame sends up to 37,112
placement faces per view position. To measure at the Vivec poses. Also checked against the source, no bug:
clipnode children above 32,767 are read as the unsigned half (65,520 per model, builder and engine agree); the
zone statements are corrected (CHIM-ZONE-BUDGET-33 status: 6,864 KiB less 2 x 384 KiB).
## BUILD-UNDERUSE-GATE-36, 11 October 2026

[BUILD-UNDERUSE-GATE-36](bugs/BUILD-UNDERUSE-GATE-36.md): a sweep of the v0.0.36-dev3 compiled-hull run found the chim
stage's validation (518 s), zone walk (77 s) and statistics (464 s) on about one core of 24, none of them flagged by the
profiler, which only looked at whole stages. Repaired in source on v0.0.36-build-timeline: any stage or phase over 30 s on
under half of its stage's workers is listed in the build summary, the optimizer's fix items and the live progress.

## BUILD-PROFILE-SECTIONS-MISSING-36, BUILD-CHIM-STATS-SERIAL-TAIL-36 and CHIM-STAIR-GATE-WORLD-RELOAD-36, 11 October 2026

[BUILD-PROFILE-SECTIONS-MISSING-36](bugs/BUILD-PROFILE-SECTIONS-MISSING-36.md): the chim stage of the v0.0.36-dev3
compiled-hull build printed "CHIM stair gate: passed" with no time and then nothing for about 8 minutes; the stair gate's
43 min 51 s were reconstructed from the run's file times and the stair-walk cache entries. Repaired in source on
v0.0.36-build-timeline: a phase timer with start and end lines (time, cores), the phases in the profile and the Build
Timeline, a heartbeat from the builder for any stage silent for 30 s, and `--log-level`.
[BUILD-CHIM-STATS-SERIAL-TAIL-36](bugs/BUILD-CHIM-STATS-SERIAL-TAIL-36.md): those 8 silent minutes were the CHIM statistics
validating the whole world a second time on one core; chim_build now validates once and hands the world to the statistics.
[CHIM-STAIR-GATE-WORLD-RELOAD-36](bugs/CHIM-STAIR-GATE-WORLD-RELOAD-36.md): the stair gate's workers read the whole world
again on every frame change (14.5 s per read on this world); open, for the stair-walk rework.

## DOCS-VIVEC-FRAME-PLAN-36, 10 October 2026

[DOCS-VIVEC-FRAME-PLAN-36](bugs/DOCS-VIVEC-FRAME-PLAN-36.md): four CHIM documents disagree on how Vivec goes onto CHIM
(one frame, eight district frames, the coordinate range, the no-overlap rule). Open: one plan after the owner decides.
## BUILD-CHIM-STAIR-WALK-UNCACHED-36: only stair walks checked by a passed master build are reused, 10 October 2026

[BUILD-CHIM-STAIR-WALK-UNCACHED-36](bugs/BUILD-CHIM-STAIR-WALK-UNCACHED-36.md): a stored stair walk is now a record with
its provenance (version, commit, run, master builder request, host time) and its own SHA-256. It is reused only after
the run that wrote it passed every gate as a build of the master builder, which marks it as checked; results of
failed, dry or local runs stay candidates and are walked again. Legacy maps and CHIM frames share the mechanism; the
log names each as walked or reused from which run.

## CHIM-COMPILED-HULL-SHORT-36: model hull patch on by default; A/B/C/D of the town rings, 10 October 2026

[CHIM-COMPILED-HULL-SHORT-36](bugs/CHIM-COMPILED-HULL-SHORT-36.md): the town frames built with the v0.0.36-dev3 inputs at four
commits: Balmora / Seyda Neen 6,230,992 / 5,679,168 (642c1ea defaults), 6,065,216 / 5,679,248 (5184581, compiled terrain
hull), 6,352,304 / 6,531,968 (5184581, routed terrain hull: [CHIM-TOWN-HEAP-ROUTED-HULL-36](bugs/CHIM-TOWN-HEAP-ROUTED-HULL-36.md),
all of it terrain collision), 6,065,216 / 5,679,248 (checked compiled hull). With the model hull patch Balmora needs 6,093,376
of 6,242,304, so the patch is now on by default; `off` keeps the previous method.

## ENGINE-UPSTREAM-ASM-UNUSED-36, 10 October 2026

[ENGINE-UPSTREAM-ASM-UNUSED-36](bugs/ENGINE-UPSTREAM-ASM-UNUSED-36.md): the engine builds without upstream AmiQuake's 68k
assembly (`USE_ASM_SPANS=0`, no `.s` files) since v0.0.16. Open: measure before deciding.

## ENGINE-RESIDENT-REGISTRY-GROWTH-36, 10 October 2026

[ENGINE-RESIDENT-REGISTRY-GROWTH-36](bugs/ENGINE-RESIDENT-REGISTRY-GROWTH-36.md): console commands, console
variables and large static name tables stay in memory for the whole session, and nothing kept them from growing
(the 98 AmiWind commands alone are about 3 KiB of hunk). A ratchet test now compares them with a committed
budget: 266 commands (8,512 bytes of hunk), 321 variables (7,704 bytes of structures and 10,496 bytes of zone),
no name table of 1 KiB or more. Growth fails the test with the new names; new debug commands belong in the
on-disk `dbg` catalogue.

## OPS-GATE-UNLISTED-TESTS-36 and BUILD-REUSE-AUDIT-WITHOUT-REASON-36, 10 October 2026

[OPS-GATE-UNLISTED-TESTS-36](bugs/OPS-GATE-UNLISTED-TESTS-36.md): the gate stages only the files of the public
file list, so a test missing from it never ran (TEST-GODMODE-UNLISTED-36) and nothing compared the checkout's
test files with the list. A gate request now is refused, naming the files, when a test file is unlisted; a suite
test checks the repository the same way. No test file was missing.
[BUILD-REUSE-AUDIT-WITHOUT-REASON-36](bugs/BUILD-REUSE-AUDIT-WITHOUT-REASON-36.md): the reuse audit and preflight
called the BUILD-REUSE-REDUCED-RECORD-36 reason ("reused it without ... which this build runs again") UNEXPECTED;
it now follows the stages that replaced the file and is EXPECTED unless one of them was rebuilt unexpectedly.

## BUILD-CHIM-STAGE-IDLE-START-36 repaired in source, 10 October 2026

[BUILD-CHIM-STAGE-IDLE-START-36](bugs/BUILD-CHIM-STAGE-IDLE-START-36.md): the CHIM world prepared its areas one after
another, and a region frame's own steps are serial; region frames are now prepared side by side, one per worker. 24
region cells: 302 seconds before, 87 after, the same CHIM world by SHA-256.

## CHIM-TOWN-HEAP-ROUTED-HULL-36; BUILD-CHIM-HEAP-GATE-LATE-36 and BUILD-CHIM-STAIR-WALK-UNCACHED-36 repaired in source, 10 October 2026

[CHIM-TOWN-HEAP-ROUTED-HULL-36](bugs/CHIM-TOWN-HEAP-ROUTED-HULL-36.md): the dev3 run's rings over the zone come from
`--chim-terrain-hull routed` replacing the towns' compiled hulls: built alone, Seyda Neen needs 6,528,832 bytes with it,
5,679,248 with the checked compiled hull (Balmora 6,065,216) and with the default (Balmora 6,230,992).
[BUILD-CHIM-HEAP-GATE-LATE-36](bugs/BUILD-CHIM-HEAP-GATE-LATE-36.md) and
[BUILD-CHIM-STAIR-WALK-UNCACHED-36](bugs/BUILD-CHIM-STAIR-WALK-UNCACHED-36.md) repaired in source: the heap gate and
the zone walk run before the stair walk; CHIM frames use the legacy maps' stair-walk pass cache keyed by the SHA-256 of
what a frame's walk reads, a seeded sample is walked again on every build, and every frame prints one line.

## BUILD-CHIM-HEAP-GATE-LATE-36 and BUILD-CHIM-STAIR-WALK-UNCACHED-36, 10 October 2026

[BUILD-CHIM-HEAP-GATE-LATE-36](bugs/BUILD-CHIM-HEAP-GATE-LATE-36.md): the v0.0.36-dev3 run with 270 CHIM region cells and the
routed terrain hull failed its chim stage after 1 h 48 min: the heap gate, which takes seconds, ran after a 69-minute stair
walk and found Balmora's and Seyda Neen's rings over the zone (6,348,016 and 6,523,568 of 6,242,304 bytes).
[BUILD-CHIM-STAIR-WALK-UNCACHED-36](bugs/BUILD-CHIM-STAIR-WALK-UNCACHED-36.md): that walk redoes every frame on every
build; the v0.0.33 pass cache of the legacy maps (BUILD-STAIR-WALK-SLOW-33) was never hooked into the CHIM frames.

## CHIM-COMPILED-HULL-SHORT-36: compiled model hulls, island-wide sweep, 10 October 2026

[CHIM-COMPILED-HULL-SHORT-36](bugs/CHIM-COMPILED-HULL-SHORT-36.md): every compiled standing hull of Balmora, Seyda Neen and
the Bitter Coast test area rebuilt with the exactness check: 1,108 terrain hulls exact; 11 of 42 model hulls (Hlaalu
houses and two Dwemer ruins) lose pieces under walkable tops, by up to 139 units. One check for every caller
(collision_bsp.standing_check); lost pieces patched with the exact pieces (patch_holes). Terrain is patched or falls
back to the routed hull. Models are checked and recorded; patching them (--chim-model-hull-patch on) needs 12,400 bytes
more than Balmora's ring has, so it is off by default.

## WAIT-FEET-IN-WATER-36, 10 October 2026

WAIT-FEET-IN-WATER-36: a study of the original's wait and rest rules found that the wait selector (T) opens with the
feet in water; the original refuses it. Open, part of the wait and rest work.

## WAIT-DURING-COMBAT-36, 10 October 2026

[WAIT-DURING-COMBAT-36](bugs/WAIT-DURING-COMBAT-36.md): the wait key worked in the middle of a fight (owner report).
Repaired in source: one "are we in a fight?" check (`AW_PlayerInCombat`, the battle music's own condition) now
also refuses waiting, with the game's own text. The original's wider test (any aggressive actor nearby) comes with
the wait and rest work.

## PLAYER-DEATH-LIMBO-35 and COMBAT-PLAYER-DEATH-FALL-33 repaired in source, 10 October 2026

[PLAYER-DEATH-LIMBO-35](bugs/PLAYER-DEATH-LIMBO-35.md): a dead player can no longer talk, activate, attack, wait or
move; after the death animation the original question appears (load the most recent save / main menu, straight to
the main menu with no save), plus the AmiWind Retry fight after a lost fight (`--death-retry`, default on).
[COMBAT-PLAYER-DEATH-FALL-33](bugs/COMBAT-PLAYER-DEATH-FALL-33.md): death switches to the third-person death camera
and the player's new body plays its death animation, as the original (OpenMW playRandomDeath -> useDeathCamera).
The death track now also plays for a death outside a fight ([MUSIC-DEATH-SILENT-33](bugs/MUSIC-DEATH-SILENT-33.md)
stays open). In-game check pending. See [THIRD_PERSON.md](THIRD_PERSON.md).
Owner rule the same day: dead, no names, hints, prompts, crosshair, enemy bar or voice lines either; one predicate
(`AW_PlayerDead`) asked by every such path.
## BUILD-PROGRESS-ETA-BASIS-36, 10 October 2026

[BUILD-PROGRESS-ETA-BASIS-36](bugs/BUILD-PROGRESS-ETA-BASIS-36.md): the live progress of the v0.0.36-dev3 coast build
expected its chim stage at about 154 s, from earlier three-area runs, while the stage built 273 frames and ran 1 h 48 min;
the progress showed 27 % and about 22 minutes left. Repaired in source on v0.0.36-build-timeline: the history is scaled by
the stage's frames, earlier runs of unknown size do not count ("no comparable history", ETA marked as a lower bound), and
the basis is in the progress record, the status line and the Build Timeline.

## BUILD-CHIM-STAGE-IDLE-START-36, 10 October 2026

[BUILD-CHIM-STAGE-IDLE-START-36](bugs/BUILD-CHIM-STAGE-IDLE-START-36.md): the first Build Timeline of the v0.0.36-dev3
coast builds shows the chim stage on 1-4 cores for its first 35-45 minutes while it held 12-24 workers, in both runs that
reached it (resume2 and routed-hull). Cause unknown; the stage records no timed sections.

## CHIM-COMPILED-HULL-SHORT-36 and BUILD-CHIM-VALIDATE-LATE-36, 10 October 2026

[CHIM-COMPILED-HULL-SHORT-36](bugs/CHIM-COMPILED-HULL-SHORT-36.md): the first full build with CHIM region cells, the compiled
terrain hull and terrain references (v0.0.36-dev3) failed CHIM validation on four chunks of region cells 13,-15, 13,-14,
14,-15 and 16,-11. The compiled standing hull lies up to 3 units below the exact expanded ground there; the routed hull
from the same pieces passes. Reproduced on those four cells alone; the build was rerun with the routed hull.
[BUILD-CHIM-VALIDATE-LATE-36](bugs/BUILD-CHIM-VALIDATE-LATE-36.md): that failure surfaced only after the 2,687-second chim
stage, and its lines named no frame.

## BUILD-REUSE-REDUCED-RECORD-36, 10 October 2026

[BUILD-REUSE-REDUCED-RECORD-36](bugs/BUILD-REUSE-REDUCED-RECORD-36.md): the dev3 build reused intro from the dev2 run's short record (158 of 177 files) while census ran again and found its palette missing; the reuse plan now checks the full record and reruns the stage when the stages that replaced its files run again.

## PHYSICS-GRAVITY-SCALE-36, 10 October 2026

[PHYSICS-GRAVITY-SCALE-36](bugs/PHYSICS-GRAVITY-SCALE-36.md): gravity is Quake's 800 in a world scaled 0.25, about 5.7 times the original's; to be measured against OpenMW before tuning.

## BUILD-HARVEST-NATIVE-TOWN-ORDER-36, 10 October 2026

[BUILD-HARVEST-NATIVE-TOWN-ORDER-36](bugs/BUILD-HARVEST-NATIVE-TOWN-ORDER-36.md): the second v0.0.36-dev2 image run stopped on Balmora's harvest catalogues, checked before the CHIM-native town's frame map was written; the check now knows the CHIM-native towns staged in the image.

## HANG-IDLE-DUSK-35: cause found, 10 October 2026

[HANG-IDLE-DUSK-35](bugs/HANG-IDLE-DUSK-35.md): the idle freeze is a music stream read that never returns while the main loop waits for it, the same call chain as [SEYDA-LOAD-HANG-30](bugs/SEYDA-LOAD-HANG-30.md) (v0.0.30). Linked with the suspected and possible freezes of the same kind; repair (non-blocking music read) in progress.
## BUILD-LEGACY-CHAIN-DEFAULT-36, 10 October 2026

[BUILD-LEGACY-CHAIN-DEFAULT-36](bugs/BUILD-LEGACY-CHAIN-DEFAULT-36.md): v0.0.36-dev1 playtest images were built with
`--legacy-area balmora`, preparing Balmora's CHIM frame through the legacy region-map chain with only a warning,
and `--chim-native-towns` was still off by default. Repaired: CHIM-native areas are the default
(`--chim-native-towns on`); `--legacy-area` and `--chim-native-towns off` are retired since CHIM v0.1.0, stop a
developer-mode build before any stage unless named with `--override`, and every use is recorded in the
receipts and the build summary.
## HANG-IDLE-DUSK-35 game side repaired in source, ENGINE-SYNC-IO-MAIN-LOOP-36, 10 October 2026

[HANG-IDLE-DUSK-35](bugs/HANG-IDLE-DUSK-35.md): the music stream reads through asynchronous DOS packets
(`aw_aread.c`); a read that is late or never answered is logged once, the music goes silent and the game goes on;
the stream resumes on a late reply or is abandoned after 6 s for the next track. Soak verification open.
[ENGINE-SYNC-IO-MAIN-LOOP-36](bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): the sweep that followed lists the other
synchronous file calls during play (CHIM streaming, sound and voice loads, model reloads, autosave, lamps).
## BUILD-ENGINE-SOURCE-KEY-BROAD-36, 10 October 2026

[BUILD-ENGINE-SOURCE-KEY-BROAD-36](bugs/BUILD-ENGINE-SOURCE-KEY-BROAD-36.md): the reuse preflight of an engine-only
change planned the chim and world-flora stages for rebuild, with unrelated engine files listed as their changed
sources; probable cause: the engine source folder named by the limit readers is hashed whole. Open.
## TEST-GODMODE-UNLISTED-36, 10 October 2026

[TEST-GODMODE-UNLISTED-36](bugs/TEST-GODMODE-UNLISTED-36.md): the dbg godmode test was missing from the public file
list, so the gate never ran it, and its check of the C escape failed; both repaired.

## BUILD-IMAGE-NATIVE-BALMORA-CACHE-36, 10 October 2026

[BUILD-IMAGE-NATIVE-BALMORA-CACHE-36](bugs/BUILD-IMAGE-NATIVE-BALMORA-CACHE-36.md): the v0.0.36-dev2 image step asked for the legacy Balmora cache
although Balmora was CHIM-native; the input check now follows the CHIM-native town list.

## CHIM-REGION-DIVIDED-CELLS-36, 10 October 2026

[CHIM-REGION-DIVIDED-CELLS-36](bugs/CHIM-REGION-DIVIDED-CELLS-36.md): the --chim-regions preflight accepts 271 of 724 converted cells;
the 454 refused are divided cells (the legacy builder split them over 2-9 maps; a region frame replaces one map).
## CHIM-REGION-MARGIN-STORAGE-36: terrain references and the compiled terrain hull, 10 October 2026

[CHIM-REGION-MARGIN-STORAGE-36](bugs/CHIM-REGION-MARGIN-STORAGE-36.md): repair in source behind two experimental build
options, both off: `--chim-terrain-hull compiled` (the chunks' standing hull compiled by qbsp) and `--chim-terrain-refs on`
(world format 0.7: chunk terrain stored once per content, placed at an offset; the engine moves its copy when it grafts
the chunk). Scratch worlds of 7 and 6 region cells: 9.0 and 10.0 MB with copies, 1.9 and 2.6 MB with both options, 0.91
and 0.93 times the open-world maps they replace; every CHIM gate passed.

## HANG-IDLE-DUSK-35, 10 October 2026

[HANG-IDLE-DUSK-35](bugs/HANG-IDLE-DUSK-35.md): owner playtest of v0.0.35: idle outdoors on legacy terrain for a few
minutes, around sundown, the game froze with the music looping. Seen several times on FS-UAE. Leads: night lighting
at dusk, audio DMA drift, the old dock/menu freeze. Next: a headless idle soak run across dusk.

## NPC-WANDER-NOT-EXECUTED-35, 10 October 2026

[NPC-WANDER-NOT-EXECUTED-35](bugs/NPC-WANDER-NOT-EXECUTED-35.md): owner playtest of v0.0.35: residents stand still; the original's
Wander packages are decoded but not executed. Planned from the path grids and the OpenMW behaviour.

## ANIMKIT-COVERAGE-35, 10 October 2026

[ANIMKIT-COVERAGE-35](bugs/ANIMKIT-COVERAGE-35.md): owner playtest of v0.0.35: Fargoth has no walk animation and hops
at the player instead of punching. Repair planned island-wide: walk, run, swim and attack for every NPC that can
move or fight, plus a builder audit that fails on a missing group.

## PLAYER-DEATH-LIMBO-35, 10 October 2026

[PLAYER-DEATH-LIMBO-35](bugs/PLAYER-DEATH-LIMBO-35.md): after the player dies there is no way out (owner playtest of v0.0.35).

## COMBAT-MUSIC-AIR-SWING-35, 10 October 2026

[COMBAT-MUSIC-AIR-SWING-35](bugs/COMBAT-MUSIC-AIR-SWING-35.md): swinging at the air starts the combat music (owner playtest of v0.0.35).
## BUILD-REUSE-CASCADE-36: five causes found and repaired in source, 10 October 2026

[BUILD-KEY-FUNCTION-DEFAULTS-TOP-36](bugs/BUILD-KEY-FUNCTION-DEFAULTS-TOP-36.md): adding an unused function to a
shared module changed every importing stage's key; stage keys now count only default values that run code on
import. [BUILD-REUSE-RECORD-RETIRED-36](bugs/BUILD-REUSE-RECORD-RETIRED-36.md): the early cutoff lost the record of
a stage reused from a retired run and counted identical outputs as changed; runs now keep those records.
[BUILD-SEYDA-BOUNDED-RUN-PATHS-36](bugs/BUILD-SEYDA-BOUNDED-RUN-PATHS-36.md): actor-contact wrote its run folder
path into 67 region records. [BUILD-FLORA-RECEIPT-SECONDS-36](bugs/BUILD-FLORA-RECEIPT-SECONDS-36.md): the world
flora receipt held the wall time. [BUILD-DIAGNOSTIC-INPUT-REFUSED-36](bugs/BUILD-DIAGNOSTIC-INPUT-REFUSED-36.md):
cell-progress reads chim-stats.json and was never reusable; such a read is now a hashed input.

## LAUNCHER-GL-CONTEXT-FALLBACK-36, 10 October 2026

[LAUNCHER-GL-CONTEXT-FALLBACK-36](bugs/LAUNCHER-GL-CONTEXT-FALLBACK-36.md): on a host whose OpenGL cannot create a context,
FS-UAE stops with a raw X error after the launcher's preflight passed. Workaround: software OpenGL
(`LIBGL_ALWAYS_SOFTWARE=1`); planned: the launcher explains it and offers that fallback.

## BUILD-REUSE-CASCADE-36, 10 October 2026

[BUILD-REUSE-CASCADE-36](bugs/BUILD-REUSE-CASCADE-36.md): after a fix to the CHIM-native town code, a rebuild reused 13 of
36 stages instead of the planned 28: the interior stage reran with different outputs and 5 rebuilds were
unexpected. Hold-level; under investigation.

## CHIM-REGION-MARGIN-STORAGE-36, 10 October 2026

[CHIM-REGION-MARGIN-STORAGE-36](bugs/CHIM-REGION-MARGIN-STORAGE-36.md): a CHIM region frame (one cell, `--chim-regions`)
carries a terrain-only margin of 896 units on every side, so it stores about 3.5 times its cell's terrain: three
neighbouring cells took 3.46 MB of CHIM frames for 0.68 MB of legacy maps; the 172 cells of the sea ring would add
about 120 MB to the image.
## CHIM-STITCH-SHORELINE-36 and CHIM-FAR-BAND-GAP-36 repaired in source, 10 October 2026

[CHIM-STITCH-SHORELINE-36](bugs/CHIM-STITCH-SHORELINE-36.md): town frames now take the legacy shoreline
triangulation (`--chim-terrain-shoreline`, default on; only chunks holding a shoreline tile change).
[CHIM-FAR-BAND-GAP-36](bugs/CHIM-FAR-BAND-GAP-36.md): bcoast_x7y2 owns its cell box with a 768-unit terrain-only
margin, and the town table refuses a handoff core under draw distance + 32 from the frame edge (the Arena selects
the inset by name). Border audit on the rebuilt area: height steps 0.0 and far band gap 0 on every edge, arrival
within 0.031 units.
## CHIM-NATIVE-HARVEST-MISSING-36, 10 October 2026

[CHIM-NATIVE-HARVEST-MISSING-36](bugs/CHIM-NATIVE-HARVEST-MISSING-36.md): extra CHIM-native areas (first: the Bitter Coast test
area) get no harvest catalogue; harvest is planned for Seyda Neen and Balmora only.
## CHIMPORT-POOL-CROSS-MOUNT-36, 10 October 2026

[CHIMPORT-POOL-CROSS-MOUNT-36](bugs/CHIMPORT-POOL-CROSS-MOUNT-36.md): the island CHIMport run reached its run folder
and the shared storage pool through two mounts of the same volume. Hard links between two mounts fail, so the pool
copied every unit it already held instead of linking it (0 of 2,000 sampled unit files linked). Fix: one mount;
a link probe at the start of pooled runs is proposed.

## BUILD-IMAGE-CHIM-NATIVE-TOWN-36, 10 October 2026

[BUILD-IMAGE-CHIM-NATIVE-TOWN-36](bugs/BUILD-IMAGE-CHIM-NATIVE-TOWN-36.md): a full build with the Bitter Coast
test area as a CHIM-native town failed at the end of its image step: the town's CHIM frame map still read its
activated objects from legacy region maps (maps/bc000.bsp) that a CHIM-native town never has. Repaired: no
legacy region map is read for a CHIM-native town, and the payload preflight refuses a CHIM-native area that the
legacy chain also claims, naming each file and its two sources.

## BUILD-REUSE-PLAN-ENV-36, 10 October 2026

[BUILD-REUSE-PLAN-ENV-36](bugs/BUILD-REUSE-PLAN-ENV-36.md): the standalone `build.py --reuse-plan` reported "environment" rebuilds
that the real build did not have (it runs without the build's options); the build's own preflight showed 18 of 26
stages reused, every rebuild explained. Workaround: read the build's preflight line.

## CHIM-STITCH-SHORELINE-36, CHIM-FAR-BAND-GAP-36 and CHIM-HANDOFF-POPIN-36, 10 October 2026

The new border audit (`tools/chim/stitch.py audit`) measured where the Bitter Coast test area meets the legacy
world. [CHIM-STITCH-SHORELINE-36](bugs/CHIM-STITCH-SHORELINE-36.md): the area's ground lacks the legacy shoreline
refinement, so in shore tiles the two maps differ by up to 28.25 units (arrival steps up to 24); elsewhere they
are identical. [CHIM-FAR-BAND-GAP-36](bugs/CHIM-FAR-BAND-GAP-36.md): the frame edge is 96 units past the handoff
core and the far layer starts at the fog plane, leaving up to 476 units with no ground.
[CHIM-HANDOFF-POPIN-36](bugs/CHIM-HANDOFF-POPIN-36.md): 1,078 of the area's 1,838 placements (Gnaar Mok, a
Dwemer ruin, marsh plants) are not drawn from the legacy side.
## COLLISION-ROUTE-NO-SPLIT-36, 10 October 2026

[COLLISION-ROUTE-NO-SPLIT-36](bugs/COLLISION-ROUTE-NO-SPLIT-36.md): with the shared hull rule in, 5 Bitter Coast
cells stay hull-pending only because of kelp and kreshweed: the router accepts them but finds no cut, so their
standing hull is still one chain 277-305 clipnodes deep. Open.

## CHIMPORT-DOOR-MARKER-AUDIT-36, 10 October 2026

[CHIMPORT-DOOR-MARKER-AUDIT-36](bugs/CHIMPORT-DOOR-MARKER-AUDIT-36.md): the door audit counted the prison marker
(a DOOR record with a marker model) as a missing door, so 6 island cells, Seyda Neen among them, failed it. The
audit now leaves marker doors out and reports them apart.

## CHIMPORT-RETRY-AUDIT-FAILED-36, 10 October 2026

[CHIMPORT-RETRY-AUDIT-FAILED-36](bugs/CHIMPORT-RETRY-AUDIT-FAILED-36.md): a Bitter Coast region rerun with
`--retry-failed` selected none of its 13 unfinished cells: cells that converted but failed an audit (hull chains,
memory fit, doors) are "done" for the runner, and the retry looked only at that. It now also reruns every cell
whose last result is failed, hull policy pending or not converted.

## CHIM-ACTOR-GROUNDING-POLICY-36 fixed, 10 October 2026

[CHIM-ACTOR-GROUNDING-POLICY-36](bugs/CHIM-ACTOR-GROUNDING-POLICY-36.md): every NPC placed in an exterior cell is
now classified by measurement against the land or the static it stands on (tools/actor_grounding_census.py): 559
of 566 placements measure as ground, 432 ground NPCs and 5 placed-dead exceptions were added to the policy, and 7
candidates outside the shipped and test areas wait for a sourced decision. The build preflight refuses an
unclassified resident of a CHIM area in about 2 seconds, before any stage.

## TRACKER-SEA-CELL-SET-36, 10 October 2026

[TRACKER-SEA-CELL-SET-36](bugs/TRACKER-SEA-CELL-SET-36.md): 37 coastal land cells (seabed terrain and sea, nothing
placed) were missing from the tracker's island view: their island set came only from the metrics layer, which has
no row for them. The set now comes from the masters' LAND records. They were converted all along (empty sea).

## CHIM-ACTOR-GROUNDING-POLICY-36, 10 October 2026

[CHIM-ACTOR-GROUNDING-POLICY-36](bugs/CHIM-ACTOR-GROUNDING-POLICY-36.md): the first build with a CHIMport test
area (a 3 x 3 Bitter Coast block with Gnaar Mok) stopped at its chim-town stage: 9 of the area's 10 residents are
not in the NPC grounding policy, which lists only the shipped towns' NPCs. The check ran 40 minutes into the build.
Planned repair: classify every exterior NPC by measurement, and check the policy in the build preflight.

## CHIM-SLOWCPU-FRAMETIME-33: Balmora on CHIM at about 1 frame per second on a slow 68040, 9 October 2026
[CHIM-SLOWCPU-FRAMETIME-33](bugs/CHIM-SLOWCPU-FRAMETIME-33.md): owner play report of the private CHIM
preview (engine 0d8bf4f, world format 0.4, v0.0.32 disks) on the slow accelerator preset: unplayable.
Same-session A/B/A at the five Balmora cameras (FS-UAE cycle-exact 68040 at 49.7 MHz, relative):
CHIM 1.06-1.61 s per frame, legacy 2.03-4.13 s, so not a CHIM regression; slow-hardware work is
deferred to after v0.0.33. The brush-model clip walk is 65-72 percent of the CHIM view. New:
[RENDER-FOG-PASS-COST-33](bugs/RENDER-FOG-PASS-COST-33.md) (fog and day-night sky pass 150-210 ms),
[SERVER-FRAME-ARRIVAL-33](bugs/SERVER-FRAME-ARRIVAL-33.md) (226 ms server frame at the arrival
camera), [DEBUG-TP-CHIMTOWNS-33](bugs/DEBUG-TP-CHIMTOWNS-33.md) (dbg tp after chim_towns 0).

## CI-NEW-BUILDER-RULES-35, 10 October 2026

[CI-NEW-BUILDER-RULES-35](bugs/CI-NEW-BUILDER-RULES-35.md): the pushed v0.0.35 commit failed hosted CI on two new
builder rules: the previous-release check refused the one-commit checkout, and the run-name rule refused the
Docker check's run name. Fixed: a checkout without history leaves the check to the release gate; the Docker check
passes `--any-run-name`. Regression tests for both.
Second repair: CI's own engine step (`--dry-run --name ci`) hit the same naming rule; the rule now refuses only
developer-mode image builds and warns everywhere else (also public users following the docs).

## ANIMKIT-TORCH-STANDING-35, 10 October 2026

[ANIMKIT-TORCH-STANDING-35](bugs/ANIMKIT-TORCH-STANDING-35.md): with the animation kit, guards hold their torch only
while standing; the walk and run models have no torch attachment. Known in v0.0.35.

## TEST-WORKER-SYSPATH-32, 10 October 2026

[TEST-WORKER-SYSPATH-32](bugs/TEST-WORKER-SYSPATH-32.md): fixed. The release suite record (one interpreter) failed
twice on the actor ground bake test: a spawned pool worker inherited a path with `tools/` before `src/`, imported
`tools/mwad.py` as `mwad` and died unpickling its task. Pool workers now put `src/` first when they start; a
regression test covers it. Builds were not affected (their path already lists `src/` first).

## ANIMKIT-ACTOR-ABI-SITES-35, 10 October 2026

[ANIMKIT-ACTOR-ABI-SITES-35](bugs/ANIMKIT-ACTOR-ABI-SITES-35.md): the third image step in a row stopped on a tool
that assumed the previous 8 or 21 actor frames, this time the guard torch companions. A sweep of every site
that reads actor frames found two more that would have stopped later builds (the CHIM frame map actor contact
and two 32-frame ceilings). One helper now answers every site from the model's declared layout, kit guards get
an idle-group torch companion, and the payload preflight checks actor layouts first.

## ANIMKIT-ITEM-TAG-FRAMES-35, 10 October 2026

[ANIMKIT-ITEM-TAG-FRAMES-35](bugs/ANIMKIT-ITEM-TAG-FRAMES-35.md): the new preflight check found that kit
residents' weapon and shield tag tables had one row per kit sample instead of per model frame, and the model they
fight in had none: armed residents fought without drawing their items. The tags now follow each model's frames
and the engine reads the fighting model's tag.

## BUILD-CELL-PROGRESS-KEY-BUGS-35, 10 October 2026

[BUILD-CELL-PROGRESS-KEY-BUGS-35](bugs/BUILD-CELL-PROGRESS-KEY-BUGS-35.md): a self-naming label made the
cell-progress key cover all of docs/, so each bug registration stopped builds. Fixed in the key scan; an advisory
stage never stops a build.

## BUILD-POOL-ARG-UNFINGERPRINTED-35, 10 October 2026

[BUILD-POOL-ARG-UNFINGERPRINTED-35](bugs/BUILD-POOL-ARG-UNFINGERPRINTED-35.md): balmora was never reusable once
the shared storage pool passed 512 MiB: its `--npc-model-pool` folder was hashed as a stage input. The pool now
counts as its token for every stage (it is content-addressed); the read trace refuses any pool read that is not a
keyed lookup, and the resident bake's pool key covers all the code it runs.

## ANIMKIT-IMAGE-FORMATS-35, 10 October 2026

[ANIMKIT-IMAGE-FORMATS-35](bugs/ANIMKIT-IMAGE-FORMATS-35.md): the image step's palette overlay did not know the
animation kit's layout and item tag files and stopped late. Both formats are declared, and the payload
preflight now checks every staged file's format first.

## BUILD-SEYDA-REPORT-HOST-PATHS-35, 10 October 2026

[BUILD-SEYDA-REPORT-HOST-PATHS-35](bugs/BUILD-SEYDA-REPORT-HOST-PATHS-35.md): with the Seyda Neen preflight
repaired, the next default build stopped at the host-paths check: the converted `id1/seyda-regions.json`
named its inputs by absolute build path. The shipped file now names them relative to the image folder (same
schema and hashes as the recorded file); the full report stays in the build folder.

## BUILD-CHIM-KEY-UNDERDECLARED-35, 10 October 2026

[BUILD-CHIM-KEY-UNDERDECLARED-35](bugs/BUILD-CHIM-KEY-UNDERDECLARED-35.md): the CHIM stage ran the cell progress
tracker (8 files, 2 light_sources functions) as a subprocess whose name was written in two parts, so its
fingerprint left them out although the tracker writes a stage output; the read trace refused the reuse. The tracker
now runs as its own stage, cell-progress, with its own key; the fingerprint scan follows names built from literal
parts; build_audit reports uncovered reads of every stage.

## BUILD-POOL-APPLY-READ-MISS-35, 10 October 2026

[BUILD-POOL-APPLY-READ-MISS-35](bugs/BUILD-POOL-APPLY-READ-MISS-35.md): in a pool-mode build every reused stage
read tools/storage_pool.py through the reuse step and was then refused as the next build's reuse source. The reuse
step's own modules are no longer counted as inputs of a reused stage.

## BUILD-SCENE-DIAGNOSTIC-COPY-35, 10 October 2026

[BUILD-SCENE-DIAGNOSTIC-COPY-35](bugs/BUILD-SCENE-DIAGNOSTIC-COPY-35.md): npcs, hands, interior and intro were
never reusable: copying the previous scene, logs included, counted as reading another stage's diagnostics. A byte
copy of a diagnostic into a diagnostic is no longer a read; any other read still is.

## BUILD-POOL-READONLY-SCENE-WRITE-35, 10 October 2026

[BUILD-POOL-READONLY-SCENE-WRITE-35](bugs/BUILD-POOL-READONLY-SCENE-WRITE-35.md): a pool-mode resume failed in 17
s: npcs could not rewrite its own copy of seyda.bsp, because copytree copied the pool's read-only mode. Every
folder copy now goes through mwad.paths.copy_tree, which makes the new copy writable and never touches the pooled
file.

## BUILD-RESUME-OUTPUTS-DIFFER-35, 10 October 2026

[BUILD-RESUME-OUTPUTS-DIFFER-35](bugs/BUILD-RESUME-OUTPUTS-DIFFER-35.md): every v0.0.35 resume refused the stages
after a rerun scene-chain stage as 'outputs differ' without comparing a byte: the comparison gave up on any
non-reusable record. Records refused only for what they read are now compared; the reruns were identical apart from
logs.

## BUILD-RESUME-HAZARD-STATIC-35, 10 October 2026

[BUILD-RESUME-HAZARD-STATIC-35](bugs/BUILD-RESUME-HAZARD-STATIC-35.md): a resume stopped in area on 8 files census
had left out, although census had run again and written them. The rebuild hazard is now kept per stage and checked
against what really ran.

## BUILD-GALLERY-JSON-KEY-ORDER-35, 10 October 2026

[BUILD-GALLERY-JSON-KEY-ORDER-35](bugs/BUILD-GALLERY-JSON-KEY-ORDER-35.md): 3,460 NPC gallery files differed
between two builds only in JSON key order (cached results sorted, fresh ones not). Every gallery JSON writer now
sorts its keys.

## ANIMKIT-GROUND-CHECK-LAYOUT-35, 10 October 2026

[ANIMKIT-GROUND-CHECK-LAYOUT-35](bugs/ANIMKIT-GROUND-CHECK-LAYOUT-35.md): with the animation kit as the default,
the actor ground check refused resident models with more than their 8 idle frames and stopped the image step.
It now reads the model's kit layout and checks the idle poses.

## NPC-NO-RUN-ANIM-35, 10 October 2026

[NPC-NO-RUN-ANIM-35](bugs/NPC-NO-RUN-ANIM-35.md): in v0.0.34 companions and hostile NPCs walked but never ran:
release residents carried only idle frames. The animation kit is now the default (`--anim-kit on`), with
`dbg animkit` to inspect it and `--anim-kit off` for the previous frames.

## BUILD-SEYDA-CONVERTED-NOT-STAGED-35, 10 October 2026

[BUILD-SEYDA-CONVERTED-NOT-STAGED-35](bugs/BUILD-SEYDA-CONVERTED-NOT-STAGED-35.md): the first full v0.0.35
development build stopped at the image step's payload preflight after all its stages: the early preflight
required the Seyda Neen region table and special maps, which the same step converts later. The early
preflight now checks the files the image step writes itself before its frame maps as planned (the
conversion's plan, or the pinned recorded set); the later preflight checks them written. Verified read only
on the failed run's own staged files; the failed run is resumed with `--reuse-from`.

## BUILD-IMAGE-STALE-PYTHONPATH-35, 10 October 2026

[BUILD-IMAGE-STALE-PYTHONPATH-35](bugs/BUILD-IMAGE-STALE-PYTHONPATH-35.md): builder container images keep an
old builder copy on `PYTHONPATH`; a run of a newer mounted source without its own `PYTHONPATH` could import
old code silently, and one read the wrong version from it. Every build now runs an import guard (builder
code only from the source tree being built; other builder trees dropped from `PYTHONPATH` before any
stage), `tools/build.py --check-entry` is the read-only entry check for workers, and
`tools/build.py --developer-mode` checks the working version, the integration head, the storage pool, the
run name and the reuse plan before any stage.

## BUILD-REUSE-KEYS-TOO-BROAD-35, 10 October 2026

[BUILD-REUSE-KEYS-TOO-BROAD-35](bugs/BUILD-REUSE-KEYS-TOO-BROAD-35.md): the first v0.0.35 development build
reused 0 of 35 stages from the v0.0.34 build, and 0 of 3,551 gallery models. Every stage's own key had
really changed (sources in 35 stages, game inputs in 28, settings in 21), so nothing could be reused
safely, but the build only said so in its state file. A reuse preflight now lists, before any stage runs,
every rebuild with its reason and the changed files that touch it. It stops the build when a rebuild is
not explained (`--accept-rebuild` overrides), and `tools/build.py --reuse-plan OLD_RUN` runs it alone. The
gallery model key now covers the code its converter reaches, which also adds modules the old file list
left out. Build run names now carry date, version, purpose and commit.

## Engine crash paths and engine table limits (BUILD-BUDGET-ENGINE-LIMITS-35 and fifteen more), 10 October 2026

- [BUILD-BUDGET-ENGINE-LIMITS-35](bugs/BUILD-BUDGET-ENGINE-LIMITS-35.md): registered; fixed in source on
  v0.0.35-crash-fixes-2. Every map the image ships is counted the way the engine loads it (edicts, model and
  sound precaches, statics, scenery catalogue, visible entities, leaves) in the payload preflight and the image
  step; town budgets may only tighten the engine. Worst shipped map: 25 model slots left (vf1258).
- [ENGINE-MAP-NAME-OVERFLOW-35](bugs/ENGINE-MAP-NAME-OVERFLOW-35.md),
  [ENGINE-FRAME-TIME-FLOAT-35](bugs/ENGINE-FRAME-TIME-FLOAT-35.md),
  [ENGINE-LOADGAME-SYSERROR-35](bugs/ENGINE-LOADGAME-SYSERROR-35.md): registered; fixed in source.
- [ENGINE-SUBMODEL-LIMIT-32](bugs/ENGINE-SUBMODEL-LIMIT-32.md): fixed in source (map unavailable instead of a
  precache overflow).
- [ENGINE-FATAL-PATH-SWEEP-35](bugs/ENGINE-FATAL-PATH-SWEEP-35.md): the sweep of every fatal path data or a
  player can reach, with the table of what was fixed and what was left and why. Fixed in source from it:
  [ENGINE-SOUND-NAME-SYSERROR-35](bugs/ENGINE-SOUND-NAME-SYSERROR-35.md),
  [ENGINE-MODEL-NAME-SYSERROR-35](bugs/ENGINE-MODEL-NAME-SYSERROR-35.md),
  [ENGINE-WRITE-OPEN-SYSERROR-35](bugs/ENGINE-WRITE-OPEN-SYSERROR-35.md),
  [ENGINE-CBUF-OVERFLOW-35](bugs/ENGINE-CBUF-OVERFLOW-35.md),
  [ENGINE-COM-TOKEN-UNBOUNDED-35](bugs/ENGINE-COM-TOKEN-UNBOUNDED-35.md),
  [ENGINE-ENTITY-TEXT-UNBOUNDED-35](bugs/ENGINE-ENTITY-TEXT-UNBOUNDED-35.md),
  [ENGINE-LEAF-LIMIT-UNCHECKED-35](bugs/ENGINE-LEAF-LIMIT-UNCHECKED-35.md),
  [ENGINE-QC-ARGS-SYSERROR-35](bugs/ENGINE-QC-ARGS-SYSERROR-35.md) and
  [CHIM-STATIC-PLACE-HOST-ERROR-35](bugs/CHIM-STATIC-PLACE-HOST-ERROR-35.md).

## CHIMPORT-NO-SHARED-POOL-35, 10 October 2026

[CHIMPORT-NO-SHARED-POOL-35](bugs/CHIMPORT-NO-SHARED-POOL-35.md): the CHIMporter kept its own unit store in
each run folder beside the builder's shared hashed storage pool, so a second run folder or workspace converted
and stored everything again. `tools/chimport.py` now takes the builder's `--storage-pool`, `--reuse-mode` and
the new `--storage-pool-dir` (also for `tools/build.py`; build config key `storage_pool_dir`, environment
`AMIWIND_STORAGE_POOL`): units and whole cells are stored once and linked, and every run reports stored vs
linked bytes. Default off. Also new: `--region NAME` and a lock that refuses a second `run` on one folder.

## Engine review fixes (ENGINE-PAK-HEADER-TRUST-35 and thirteen more), 10 October 2026

A source review of the engine found fifteen problems; fourteen are fixed in source on the v0.0.35 line, each
with a regression check. High: [ENGINE-PAK-HEADER-TRUST-35](bugs/ENGINE-PAK-HEADER-TRUST-35.md) (the pak loader
trusted its header and directory) and [ENGINE-STACK-UNCHECKED-35](bugs/ENGINE-STACK-UNCHECKED-35.md) (no
check of the start-up stack). Medium: [ENGINE-C2P-ROWSTRIDE-35](bugs/ENGINE-C2P-ROWSTRIDE-35.md),
[ENGINE-VID-UPDATE-FIRST-RECT-35](bugs/ENGINE-VID-UPDATE-FIRST-RECT-35.md),
[ENGINE-VA-UNBOUNDED-35](bugs/ENGINE-VA-UNBOUNDED-35.md),
[ENGINE-FILEBASE-UNBOUNDED-35](bugs/ENGINE-FILEBASE-UNBOUNDED-35.md),
[ENGINE-UDP-ADDRESS-OVERFLOW-35](bugs/ENGINE-UDP-ADDRESS-OVERFLOW-35.md). Low:
[ENGINE-FLOATTIME-DIV64-35](bugs/ENGINE-FLOATTIME-DIV64-35.md), [ENGINE-ANGLEMOD-RANGE-35](bugs/ENGINE-ANGLEMOD-RANGE-35.md),
[ENGINE-HARVEST-MESSAGE-BOUND-35](bugs/ENGINE-HARVEST-MESSAGE-BOUND-35.md),
[ENGINE-SCENE-NAME-BOUND-35](bugs/ENGINE-SCENE-NAME-BOUND-35.md), [ENGINE-FOPEN-TEXT-MODE-35](bugs/ENGINE-FOPEN-TEXT-MODE-35.md),
[ENGINE-UNLINK-STUB-35](bugs/ENGINE-UNLINK-STUB-35.md) and [ENGINE-GAMMA-POW-35](bugs/ENGINE-GAMMA-POW-35.md) (the
gamma table no longer links pow, so the FPU gate lost its last pow exception). Open:
[AUDIO-DMA-CLOCK-DRIFT-35](bugs/AUDIO-DMA-CLOCK-DRIFT-35.md), the mixer's estimated audio position; to be
measured before any change.

## MWAD data-reader review fixes, 10 October 2026

- [MWAD-STRING-DECODE-35](bugs/MWAD-STRING-DECODE-35.md): registered and fixed in source on v0.0.35-mwad-fixes.
- [MWAD-TEXT-WRITER-LF-35](bugs/MWAD-TEXT-WRITER-LF-35.md): registered and fixed in source on v0.0.35-mwad-fixes.
- [MWAD-DELETED-RECORD-35](bugs/MWAD-DELETED-RECORD-35.md): registered and fixed in source on v0.0.35-mwad-fixes.
- [MWAD-WALK-ORDER-35](bugs/MWAD-WALK-ORDER-35.md): registered and fixed in source on v0.0.35-mwad-fixes.
- [MWAD-READER-CHECKS-35](bugs/MWAD-READER-CHECKS-35.md): registered and fixed in source on v0.0.35-mwad-fixes.

## CHIM streaming crash paths from a source review, 10 October 2026

A review of the CHIM engine found paths where bad data or a full pool ended the map. Each is now a failed load, a wait or a counted fallback, with a native test: [CHIM-PACK-LRU-STREAM-35](bugs/CHIM-PACK-LRU-STREAM-35.md), [CHIM-BRUSH-BAD-DATA-35](bugs/CHIM-BRUSH-BAD-DATA-35.md), [CHIM-EFRAG-UNCAPPED-35](bugs/CHIM-EFRAG-UNCAPPED-35.md), [CHIM-GRAFT-FAIL-NO-FLOOR-35](bugs/CHIM-GRAFT-FAIL-NO-FLOOR-35.md), [CHIM-ZONE-UNSATISFIABLE-EVICT-35](bugs/CHIM-ZONE-UNSATISFIABLE-EVICT-35.md), [CHIM-MIPTEX-OFFSET-UNCHECKED-35](bugs/CHIM-MIPTEX-OFFSET-UNCHECKED-35.md), [CHIM-ALIAS-STATIC-HUNK-35](bugs/CHIM-ALIAS-STATIC-HUNK-35.md), [CHIM-VIEW-LEAF-NO-PVS-35](bugs/CHIM-VIEW-LEAF-NO-PVS-35.md).

## BUILD-FLORA-FALLBACK-RETRY-35, 10 October 2026

## BUILD-CACHE-OWNER-FAILS-STAGE-34 and the published-release check, 10 October 2026

[BUILD-CACHE-OWNER-FAILS-STAGE-34](bugs/BUILD-CACHE-OWNER-FAILS-STAGE-34.md): unit cache entries owned by another
user stopped the v0.0.34 release build four minutes in. A refused cache read or write no longer fails a stage, and
a build preflight checks cache ownership, free space and the game data before any stage. The previous-release
check ([RELEASE-PREVIOUS-FIXES-MISSING-33](bugs/RELEASE-PREVIOUS-FIXES-MISSING-33.md)) now requires the
published release commit and prints the merge that fixes a missing one.

## BUILD-SURVEY-KEY-CONFIG-35, 10 October 2026

[BUILD-SURVEY-KEY-CONFIG-35](bugs/BUILD-SURVEY-KEY-CONFIG-35.md): the world survey re-ran on the v0.0.34
build because its key held every configuration file: a path built from a loop name over a written-out list
counted as the whole folder. Loop names with written-out string values now name their files (world survey 56
-> 6 data files; world terrain, world UI and CHIM narrowed the same way).

## BUILD-SCHEDULER-TABLE-KEY-35, 10 October 2026

## CI-SUITE-TWICE-33, 10 October 2026

[CI-SUITE-TWICE-33](bugs/CI-SUITE-TWICE-33.md): hosted CI ran the full test suite twice per
revision (source checks job and the Docker builder job). The Docker check now runs a short set of builder
test modules; `--full-suite` keeps the previous method.

## HARVEST-BITTERCOAST-29 and HARVEST-PLANTS-IN-COLLISION-33, 10 October 2026

[HARVEST-BITTERCOAST-29](bugs/HARVEST-BITTERCOAST-29.md): seen again in v0.0.33 at the same Bitter Coast
cluster. Cause: the pick ray stops on a tree's convex root collision that also contains two of the three
mushrooms. The engine now keeps a plant as the target when the solid that stopped the ray contains the
plant's own centre; a new island-wide pick audit (51 of 934 plants unpickable before, 0 after) gates the
image. The enclosing solids are tracked as
[HARVEST-PLANTS-IN-COLLISION-33](bugs/HARVEST-PLANTS-IN-COLLISION-33.md).

## MESH-LOD-OPEN-SEAMS-33 and CHIM-STRIDER-RING-33 for v0.0.34, 10 October 2026

[MESH-LOD-OPEN-SEAMS-33](bugs/MESH-LOD-OPEN-SEAMS-33.md): the owner saw the strider's open hull again in
v0.0.33; it shipped as a known issue (the repair was held), not a regression. v0.0.34 takes the repair
and its seam audit, with the strider boundary-locked at 0.45, which fits CHIM Balmora's ring
([CHIM-STRIDER-RING-33](bugs/CHIM-STRIDER-RING-33.md)). The audit now measures the profile the town and
CHIM converters compose, not the group profile alone.

## BUILD-SEYDA-REGEN-30 fixed in source: no recorded Seyda Neen input, 10 October 2026

[BUILD-SEYDA-REGEN-30](bugs/BUILD-SEYDA-REGEN-30.md): the builder no longer needs the recorded v0.0.31 Seyda
Neen maps. `--seyda-recorded DIR` is optional; without it a CHIM build converts the Seyda Neen region maps from
your data, without the terrain visual cull, and checks the CHIM frame maps against them. The cull cannot complete
from scratch ([BUILD-SEYDA-CULL-STABLE-32](bugs/BUILD-SEYDA-CULL-STABLE-32.md), reproduced again and measured;
open for the legacy builder) and is not needed for maps that never ship. The actor-contact stage passes from data
(65 Seyda Neen maps, 759 s at 12 workers); a full from-scratch image build is pending.

## TOOLKIT-MAP-SCALING-36, 11 October 2026

[TOOLKIT-MAP-SCALING-36](bugs/TOOLKIT-MAP-SCALING-36.md): the tracker map was a small box with inner scrollbars and far-apart
controls. Fixed and verified in the browser (11 October 2026): the map fills its stage, fits the island, pans by drag and zooms around the cursor.

## TRACKER-OCEAN-COUNTED-DONE-36, 11 October 2026

[TRACKER-OCEAN-COUNTED-DONE-36](bugs/TRACKER-OCEAN-COUNTED-DONE-36.md): the tracker counted the open-ocean cells as done although the
engine does not place the ocean chunk yet. Fixed and verified in the browser (11 October 2026): they are silver, on their own line and totals row, and no longer done.
