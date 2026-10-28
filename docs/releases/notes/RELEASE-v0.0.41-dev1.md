# AmiWind v0.0.41-dev1: Collisions And Boundaries

[CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md) — 15 October 2026, v0.0.41-dev1: full-build preparation rejected five explicitly selected ocean routing cells absent from the original CELL/LAND inventory, before legacy compilation. The source checklist now records additional ocean routing cells separately and allows their absence only before routing rows are appended. Final classification/stage verification still requires every row and CHIM routing flags; undeclared or unselected missing cells are rejected. All 98 targeted checks across five modules pass, including three new ocean checklist regressions. Exact production conversion, native ocean behavior, image/package and delivery checks remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](../../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: whole-world metadata binding failed because tutorial barrel reference 172851 lacked its original CELL, while the original audit records [-2,-9]. A narrow source correction restores only that missing field before capture, rejecting nonempty wrong cells and every other identity/transform mismatch. Fifty focused Seyda/ownership checks pass, including three new semantic regressions. The preceding 4,247-test full-suite pass remains historical; the repaired world is pending. The prepared Linux source kit is held and undelivered. Native, image/package and playtest acceptance remain pending; coverage states are unchanged.

[CHIM-FRAME-STATIC-SEAM-40](../../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1 image integration follow-up: added Seyda dependency numbers and model digests are checked against the world-index-bound source manifest before source-carrier static parity includes them. Frames without supplements retain prior behavior. The focused ownership/apron module now passes 33 checks, including five new semantic regressions and missing/rebound-model rejection. The issue remains OPEN; exact world rebuild, held-boundary/native and image/package checks remain pending.

[CHIM-FRAME-STATIC-SEAM-40](../../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: a source repair supplements only missing Seyda apron dependencies using the included original-cell owner's exact compiled mesh and textures, preserving original identity and unique ownership while translating frame-local origins. It targets rock reference 251397 and shell reference 461804; 32 focused ownership/apron checks pass. The rebuilt world and held boundary/native checks remain pending. Separately, independent normal interior/actor/UI conversion completed 2,451 files with unchanged source and inputs; it is not image, native or package acceptance. CHIM coverage states are unchanged. Earlier full-suite and world results remain bound to their preceding source; changed apron acceptance is pending.

[CHIM-FRAME-STATIC-SEAM-40](../../bugs/CHIM-FRAME-STATIC-SEAM-40.md) — 15 October 2026, v0.0.41-dev1: exact source validation completed 4,242 tests (4,236 passed, three Windows-only skips and three Census expected failures), with zero failures/errors; the matching engine compiled. The completed 369-frame world passed structural/source, modeled heap, host zone-walk and scoped stair gates. Of 547 boundary comparisons, 544 measured agreement and three remain held (237, 241, 242). Of 36 sampled models, 22 have matching face counts and unique face correspondence; 14 differ in collision-only versus visual representation and require payload/sprite/native review. These measurements do not establish visual severity or universal equivalence. Native captures, independent interior conversion, image assembly/readback and package acceptance remain pending; coverage states are unchanged. Stair evidence retains 15,348 advisory findings despite zero blocking failures.

15 October 2026 — The preceding v0.0.41 source snapshot completed 4,242 tests: 4,236 passed, zero failures/errors, three Windows-only skips and three exact Census expected failures; source was unchanged. This does not validate the subsequent v0.0.41-dev1 version alignment or establish image/native/package acceptance.

15 October 2026. Running on CHIM Engine v0.2.0, world format 0.7.

The active development candidate is **v0.0.41-dev1**. The planned final release
title is **v0.0.41: Collisions And Boundaries**. Preparation has begun; a
completed image, native acceptance, package and delivery are pending.

## Scope and evidence

This candidate continues the existing asset pool and source repairs. Earlier
immutable source snapshots remain identified as v0.0.41. Their automated tests,
conversion checks and compiled-engine evidence retain their exact input scope;
the version alignment is a new candidate and requires matching validation.
Historical release notes and captures are preserved.

Current work includes the placed-model arena reserve repair, named-town apron
ownership reconciliation and inventory palette format handling. The issue
register remains the current status authority:

- [CHIM-MODEL-ARENA-RESERVE-41](../../bugs/CHIM-MODEL-ARENA-RESERVE-41.md): placed-model allocation accounting; native runtime acceptance pending.
- [CHIM-FRAME-STATIC-SEAM-40](../../bugs/CHIM-FRAME-STATIC-SEAM-40.md): boundary selection and ownership repairs; the successor world and matched native boundary captures remain pending.
- [BUILD-INVENTORY-PALETTE-41](../../bugs/BUILD-INVENTORY-PALETTE-41.md): current inventory formats can pass the source palette conversion; completed production image and native appearance remain pending.

## Coverage and release gates

The final v0.0.41 CHIM plan retains 435 planned cells. Planned coverage is not
included, audited, native-checked or packaged coverage. Existing deferred
actors, held boundary findings and unimplemented gameplay remain explicit in
the [CHIM tracker](../../chim/PROGRESS_TRACKER.md). No coverage state is promoted by
this candidate naming change.

Version-specific FS-UAE and WinUAE presets accompany the source. Their presence
does not demonstrate emulator execution. Exact source checks, affected launcher
checks, completed image/readback, native verification, packaging, publication
and playtest acceptance must each have their own receipts. No new shipment or
delivery artifact is claimed. See the [bug register](../../BUGS.md), [changelog](../../CHANGELOG.md)
and [release workflow](../../RELEASE_WORKFLOW.md).

## Known in this build

Selected current blockers are listed here; the complete current status remains
in the [bug register](../../BUGS.md). Source and host checks do not establish native
or package acceptance.

World and collision:

- [CHIM-FRAME-STATIC-SEAM-40](../../bugs/CHIM-FRAME-STATIC-SEAM-40.md): opening-barrel source metadata and apron dependency repairs require an exact successor world; held boundaries, representation differences and native captures remain unresolved.
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): explicit ocean-routing checklist integration requires actual final routing and payload verification; planned cells and deferred features are not included coverage.
- [CHIM-MODEL-ARENA-RESERVE-41](../../bugs/CHIM-MODEL-ARENA-RESERVE-41.md): placed-model allocation accounting has scoped source/host evidence; matching native runtime and package verification remain pending.

Image assembly:

- [BUILD-INVENTORY-PALETTE-41](../../bugs/BUILD-INVENTORY-PALETTE-41.md): inventory format parsing is corrected in source; completed production image/readback and native icon appearance remain pending.
