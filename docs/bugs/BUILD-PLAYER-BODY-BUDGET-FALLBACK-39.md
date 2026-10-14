# BUILD-PLAYER-BODY-BUDGET-FALLBACK-39: Player body fitting stops before trying smaller meshes

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): RC2 all-body run fails Breton female:480 exceeds alias budget;384/320/256 trip leg guard. Two controls plus Argonian male/female and Breton male read back; remaining set incomplete.
- Reported with v0.0.39-rc2 at 2026-10-13 (time not recorded): RC2 body checks pass 20/20: 16 prior pairs reused, four female models newly baked below 512 KiB. Tail excluded from leg guard; 33 checks pass. Native/package acceptance pending.

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 13 October 2026, in v0.0.39-dev1 |
| Where | Player-body converter mesh and animation byte-budget selection |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.39-dev1 (last seen) |
| Severity | medium: A recoverable model-budget overflow can abort conversion instead of using an existing smaller mesh budget. |
| Family | Builder breaks and reproducibility (`builder-from-scratch`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine ec8c27d |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (Offline converter review and actual body-bake/readback checks; native acceptance remains pending.) |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [PERSISTING: reported 2 times; something has to be done](#persisting-reported-2-times-something-has-to-be-done)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Exact RC1 evidence, 13 October 2026](#exact-rc1-evidence-13-october-2026)
- [Earlier RC2 all-appearance bake failure, 13 October 2026](#earlier-rc2-all-appearance-bake-failure-13-october-2026)
- [Corrected RC2 all-body binary result, 13 October 2026](#corrected-rc2-all-body-binary-result-13-october-2026)
- [Post-pin RC2 package observation, 14 October 2026](#post-pin-rc2-package-observation-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Symptom

Source inspection found two failures in the player-body budget loop. A model
whose minimum animation frames exceed 512 KiB at the first mesh budget aborts
conversion before the smaller mesh budgets are tried. A later vertex-budget
failure can also discard a valid model already fitted at an earlier budget.
At initial source review no failing race or sex had been demonstrated in an actual body bake. Subsequent candidate failures and the corrected all-body result are recorded below.

## Where

`tools/prepare_player_view.py`, player-body conversion, and `tools/npc_anim.py`,
alias byte-budget fitting. This affects offline model preparation.

## How it happened

The loop catches one geometry-budget exception but calls the animation fitter
outside that handler. Its byte-budget exception escapes the loop. The vertex
handler also raises on the last attempt even when an earlier candidate fits.

## Why it was not caught

Existing player-view checks covered settings, appearance selection and builder
wiring. They did not follow a failed fit into the next geometry budget, or
check that a later failure preserves an earlier valid result.

## Reproduction

Use synthetic geometry where the largest mesh exceeds the alias byte limit
even at minimum frame counts, while a smaller mesh fits. The old loop stops
at the first byte-budget error. Separately, retain a valid reduced-frame fit
and make every later geometry attempt exceed its vertex budget: the old loop
raises on the last attempt instead of returning the retained fit.

## Repair

The source correction retries the existing mesh budgets after typed geometry
or animation-budget failures. It preserves the last valid fit, and fails with
the appearance and attempted budgets when none fit. Unrelated conversion
errors still abort immediately. The byte limit is unchanged.

The AmiQuake alias loader in `engine/aga/src/model.c` keeps its existing
`Mod_LoadAliasModel` staging and `Cache_Alloc` path. This repair changes the
offline selection only; no additional runtime buffer or heap is introduced.

## Verification

The initial correction has five boundary regressions covering minimum-frame byte overflow followed by a successful
smaller mesh, geometry overflow, retention of a valid reduced-frame result,
all-budget failure, and an unrelated malformed-input error after a valid fit.
Synthetic geometry uses the real byte fitter at controlled test limits.

The corrected candidate now has the focused and all-body binary evidence below. Native inspection of changed geometry/frame counts, complete image/package checks and owner acceptance remain required; source and bake checks alone do not establish visual repair.

## Prevention

Exercise the real byte fitter across failed and successful geometry attempts.
Keep the first full-frame fit, otherwise the last valid reduced-frame fit.
Retain tests for all-budget failure and unrelated conversion errors so retry
never hides bad input or permits an oversized model.

## Exact RC1 evidence, 13 October 2026

The exact RC1 package was independently extracted and read back. All 20 body
models and layouts passed their actual-format checks; 1,751 existing non-body
model/animation assets remained byte-identical. A Nord male session exercised
third-person ready/lower, movement, jump and camera changes. This is one
appearance and scene; matched original-game views, all-appearance motion,
loaded memory and performance acceptance remain separate.

## Earlier RC2 all-appearance bake failure, 13 October 2026

The earlier isolated all-body run at source 4b968c2 failed on Breton female. The 480 attempt could not fit the alias budget while retaining full normal/ready gait and action layers (1380 vertices, 460 triangles); the 384, 320 and 256 retries were refused by the visible leg-section guard. Preserve those refusals: weakening the budgets or silently dropping promised gait is not a successful result. Nord/Khajiit male controls were reused and Argonian male/female plus Breton male were newly baked/read back before the failure; other appearances were not established for that snapshot.

This candidate failure is separate from the historical RC1 package readback of20 bodies. The two-body source-candidate success does not establish all-appearance completion. Further bounded diagnosis and corrected bakes are required, followed by exact target/native/package and owner checks. No fix or acceptance promotion is claimed.

## Corrected RC2 all-body binary result, 13 October 2026

The corrected isolated candidate now passes actual-format model/layout checks for all 20 race/sex body pairs under the unchanged 512 KiB limit. Sixteen exact prior pairs were reused with provenance checks; High Elf, Nord, Orc and Redguard female models were newly baked/read back at 523,464, 522,164, 520,864 and 520,864 bytes respectively, with 104 frames each. Full normal/ready walk 8/run 6 and authored punch declarations are retained. These are body-file checks, not a complete RC2 image or package.

The anatomical leg-section guard now uses labelled leg parts 17–22 in both compared meshes, excluding Khajiit tail part 26 from the width test. Its 75% threshold and the actual model/alias budgets remain unchanged. Thirty-three focused automated checks pass against the exact corrected source snapshot, including the tail/narrow-leg regression. The earlier 83 affected body/animation checks remain separate evidence, not a rerun of the latest full suite.

Read-only section audits still identify possible knee/calf gaps in five fallback bodies. Part extrema extend up to 0.415 units beyond authored bounds; knee/calf 2D section Hausdorff distance increases from about 0.45–0.58 to 1.17–1.83 units. Plain 384 simplification causes most of that increase; contour adjustment adds 0–0.13 units. These are geometry metrics, not proof of a visible hole or an accepted repair. Native silhouette/seam inspection, matched v0.0.38 gait and RC1 ready controls, original-game comparison, memory/performance, exact package and owner acceptance remain pending. The earlier failure and historical RC1 twenty-body readback remain evidence for their own snapshots. The latest bake completion replaces the earlier incomplete-set limit without closing this issue.

## Post-pin RC2 package observation, 14 October 2026

Full RC2 disk readback and independent package extraction verify all 20 declared base bodies and140 torch/held/swim companion files within the unchanged 512 KiB model cap. Exact played readback preserves186 engine/metadata/body files. Binary coverage does not certify all 20 visual appearances, native memory, leg seams or owner acceptance.

These observations were recorded after source pin b6d759052f908f134ad2eaee1abb85c3aba7ca2d. This documentation continuation does not rewrite the sealed source archive, Linux update kit or inspection package. Owner acceptance and final v0.0.39 clearance remain pending.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Builder breaks and reproducibility (`builder-from-scratch`). The repository builder builds the whole game from the owner's data with no private step, byte for byte the same each time. See [families](README.md#families).

- [ACTOR-AUDIT-ORDER-32](ACTOR-AUDIT-ORDER-32.md): The actor audit lists Canonical owner omits errors in set order
- AW25-08 (no report page): Area build aborted on exterior window assets reused indoors
- AW25-09 (no report page): Image stage rejected the world/journal receipt after terrain
- [BUILD-ACTOR-CONTACT-CALL-32](BUILD-ACTOR-CONTACT-CALL-32.md): Builder actor-contact stage calls convert() with the wrong arguments since v0.0.27
- [BUILD-ACTOR-CONTACT-REGRESSION-38](BUILD-ACTOR-CONTACT-REGRESSION-38.md): Full dev3 rebuild rejects116 previously grounded actors
- [BUILD-DIAGNOSTIC-PALETTE-38](BUILD-DIAGNOSTIC-PALETTE-38.md): Lava diagnostic mixes conversion and runtime palettes
- [BUILD-FINALIZE-SCENE-31](BUILD-FINALIZE-SCENE-31.md): Image finalisation stops on an undefined name before media staging
- [BUILD-FINALIZE-TORCHTEST-32](BUILD-FINALIZE-TORCHTEST-32.md): The image step fails at its very end: finalize_image uses an undefined torch test report
- [BUILD-FLORA-BSP-BYTES-38](BUILD-FLORA-BSP-BYTES-38.md): Exterior flora BSPs exceed the storage budget during the full build
- [BUILD-HEAP-RECEIPT-TUPLES-32](BUILD-HEAP-RECEIPT-TUPLES-32.md): The image step refuses its own final heap receipt (tuples against lists)
- [BUILD-LAVA-TERRAIN-BUDGET-38](BUILD-LAVA-TERRAIN-BUDGET-38.md): Detailed lava terrain exceeds region storage budget
- [BUILD-LIGHT-THREADS-32](BUILD-LIGHT-THREADS-32.md): ericw light is not byte-reproducible with more than one thread
- [BUILD-NO-OVERLAY-32](BUILD-NO-OVERLAY-32.md): The builder has no engine-overlay command; dev measurements used a private script
- [BUILD-NOT-FROM-SCRATCH-32](BUILD-NOT-FROM-SCRATCH-32.md): Five releases shipped without the public builder being able to build them from scratch
- [BUILD-PALETTE-RACE-32](BUILD-PALETTE-RACE-32.md): Census and world flora assets can run together on the same palette file
- [BUILD-PATH-IN-PAYLOAD-32](BUILD-PATH-IN-PAYLOAD-32.md): A shipped sky file contains the folder the build ran in
- BUILD-QCC-PATH-008 (no report page): Image assembly was given the QCC source directory as its compiler
- [BUILD-SEYDA-HULL2-32](BUILD-SEYDA-HULL2-32.md): From-scratch builds stop at the Seyda Neen full-town map (hull 2 clipnodes over the limit) since v0.0.28
- [BUILD-SEYDA-REPORT-HOST-PATHS-35](BUILD-SEYDA-REPORT-HOST-PATHS-35.md): The converted Seyda Neen region table report (seyda-regions.json) shipped absolute build paths
- [BUILD-TMP-SCRATCH-33](BUILD-TMP-SCRATCH-33.md): Builder stages build, load or store files in the system temp directory
- [BUILD-WORLD-LAYOUT-DRIFT-32](BUILD-WORLD-LAYOUT-DRIFT-32.md): The world region layout depends on the town maps, so a from-scratch build lays out a different world
- [BUILD-XDFTOOL-ARGMAX-32](BUILD-XDFTOOL-ARGMAX-32.md): The image step fails at the end: xdftool argument list too long
- [CHIM-IMAGE-OPTIMIZER-RECEIPT-33](CHIM-IMAGE-OPTIMIZER-RECEIPT-33.md): A pure CHIM image stops at the final heap gate: frame maps and removed legacy maps differ from the optimizer receipt
- [ENGINE-BUILD-REPRO-31](ENGINE-BUILD-REPRO-31.md): Engine builds from identical source give different binaries
- [RELEASE-PREVIOUS-FIXES-MISSING-33](RELEASE-PREVIOUS-FIXES-MISSING-33.md): The next release line did not contain the previous release's last fixes, and no gate checked it
- TREES-BUILD-001 (no report page): First v0.0.28-rc1 test run lacked presets and optional inputs
- WIN-01 (no report page): Native Windows Python geometry-worker queue failure
- WIN-03 (no report page): Windows image-packing command exceeds process limit
- WIN-04 (no report page): Gallery allowance receipt mismatched after Windows CRLF staging

<!-- END GENERATED CATEGORY -->
