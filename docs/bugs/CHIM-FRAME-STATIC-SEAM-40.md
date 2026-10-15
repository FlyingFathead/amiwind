# CHIM-FRAME-STATIC-SEAM-40: Static collision differs across the Seyda boundary

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:adjacent-frame |
| First noticed | 15 October 2026, in v0.0.40-dev2 |
| Where | Whole-world Seyda original-reference binding: opening barrel 172851 missing CELL |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.40-dev2, v0.0.40, v0.0.41 (last seen) |
| Severity | critical: Required adjacent-cell collision acceptance fails within the actual crossing band. |
| Family | World storage and duplication (`world-storage`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format 0.7 |
| Unknown because | Opening-barrel missing-CELL repair has50focused Seyda/ownership passes. Whole-world rebuild/native/image pending; historical full-suite source is unchanged and separately bound. |
| Platform or emulator | not in game (Paired queries against exact compiled frame collision data.) |

<!-- END GENERATED FACTS -->

15 October 2026: active preparation now targets v0.0.41-dev1. The planned final release title is **v0.0.41: Collisions And Boundaries**. Earlier source snapshots, checks and findings retain their recorded version identities; they do not establish acceptance of this development candidate. Matching source validation, completed image assembly/readback, native checks, packaging and delivery remain separate gates. See [development preparation](../RELEASE-v0.0.41-dev1.md).

<!-- contents start -->
## Contents

- [Opening-barrel original-cell binding, 15 October 2026](#opening-barrel-original-cell-binding-15-october-2026)
- [Checked image parity for apron supplements, 15 October 2026](#checked-image-parity-for-apron-supplements-15-october-2026)
- [Missing Seyda apron dependencies: source repair, 15 October 2026](#missing-seyda-apron-dependencies-source-repair-15-october-2026)
- [Current conversion and held boundary evidence, 15 October 2026](#current-conversion-and-held-boundary-evidence-15-october-2026)
  - [Three boundary comparisons remain held](#three-boundary-comparisons-remain-held)
  - [Model measurements retain representation limits](#model-measurements-retain-representation-limits)
  - [Exact validation scope](#exact-validation-scope)
- [Named-apron owner dispositions, 15 October 2026](#named-apron-owner-dispositions-15-october-2026)
  - [Selected and deferred accounting](#selected-and-deferred-accounting)
- [Earlier coastal survey and retained-world evidence](#earlier-coastal-survey-and-retained-world-evidence)
- [Outer sea LAND survey follow-up, 15 October 2026](#outer-sea-land-survey-follow-up-15-october-2026)
- [Earlier apron repair and retained failed-world evidence](#earlier-apron-repair-and-retained-failed-world-evidence)
- [Vivec scenery selection repair, 15 October 2026](#vivec-scenery-selection-repair-15-october-2026)
  - [Selected and deferred accounting](#selected-and-deferred-accounting-1)
- [Earlier boundary and conversion evidence](#earlier-boundary-and-conversion-evidence)
- [Combined-world review checkpoint, 15 October 2026](#combined-world-review-checkpoint-15-october-2026)
- [Earlier scoped evidence](#earlier-scoped-evidence)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Proposed regional source repair, 15 October 2026](#proposed-regional-source-repair-15-october-2026)
- [Coastal apron source guard, 15 October 2026](#coastal-apron-source-guard-15-october-2026)
- [Sub-cell apron parity, 15 October 2026](#sub-cell-apron-parity-15-october-2026)
- [Authored collision retained, 15 October 2026](#authored-collision-retained-15-october-2026)
- [Compiled rock result and original kelp, 15 October 2026](#compiled-rock-result-and-original-kelp-15-october-2026)
- [Owner apron policy, 15 October 2026](#owner-apron-policy-15-october-2026)
- [Paired boundary validation, 15 October 2026](#paired-boundary-validation-15-october-2026)
- [Compiled apron selection, 15 October 2026](#compiled-apron-selection-15-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Opening-barrel original-cell binding, 15 October 2026

15 October 2026, v0.0.41-dev1: whole-world metadata binding failed because tutorial barrel reference 172851 lacked its original CELL, while the original audit records [-2,-9]. A narrow source correction restores only that missing field before capture, rejecting nonempty wrong cells and every other identity/transform mismatch. Fifty focused Seyda/ownership checks pass, including three new semantic regressions. The preceding 4,247-test full-suite pass remains historical; the repaired world is pending. The prepared Linux source kit is held and undelivered. Native, image/package and playtest acceptance remain pending; coverage states are unchanged.

The failed whole-world conversion is preserved: source and inputs were
unchanged, and the metadata guard refused tutorial barrel 172851 because the
older opening export stored an empty CELL rather than original [-2,-9]. All
other existing Seyda reference identities match; the target rock 251397 and
shell 461804 also match their original identities. This is a source metadata
binding failure, not evidence of changed native collision or geometry.

The opening_reference helper restores only a missing CELL from the exact
original audit before capture. It compares the complete original identity
and transform, rejects an already populated wrong cell, and refuses invalid
original audit cells. No other reference field is repaired or ignored. The
source correction reuses existing original-reference ownership validation;
AmiQuake runtime collision, geometry, tolerances and independent scene/engine
behavior are unchanged.

Fifty focused Seyda/ownership checks pass. Three new semantic regressions
cover missing-cell hydration, mismatch refusal and invalid original-cell
rejection. Exact source SHA-256:

- seyda.py: `d4248ed8898962188017ba051ebc49b9640d3324bfac434f8dd8890d18424d56`.
- test_chim_seyda.py: `6c8142ac78f29ba58e971a28432ab6c823d5794b2a20210a1371c54d34f1e613`.

The preceding full suite passed 4,247 tests with 4,241 passes, three Windows
skips and three Census expected failures, zero failures/errors and unchanged
source/pin. That result covers its original snapshot, not this correction.
The failed successor world and its receipts remain preserved. A new exact
world and affected gates are required before accepting the apron supplement.
The prepared Linux source kit is held for successor source and undelivered.

Previously held boundaries, representation differences and null/no-hit
residual cases remain unresolved. Native suspect captures await the assembled
runtime image. The independent 2,451-file scene conversion remains separately
scoped conversion-only evidence. No coverage, native, package, delivery or
playtest acceptance is promoted by this correction. Earlier running-world or
kit-progress statements below are historical.

## Checked image parity for apron supplements, 15 October 2026

15 October 2026, v0.0.41-dev1 image integration follow-up: added Seyda dependency numbers and model digests are checked against the world-index-bound source manifest before source-carrier static parity includes them. Frames without supplements retain prior behavior. The focused ownership/apron module now passes 33 checks, including five new semantic regressions and missing/rebound-model rejection. The issue remains OPEN; exact world rebuild, held-boundary/native and image/package checks remain pending.

The image integration verifies added original-reference numbers and compiled
model digests against the source manifest bound to the current world index.
Only those verified dependencies enter source-carrier static parity. Missing
or rebound models are rejected, while frames with no supplements preserve
the prior behavior. This extends the source apron repair; it does not change
existing geometry, representations, ownership or collision tolerances.

The current focused run passes 33 tests, including five new semantic
regressions. Initial 32-test evidence remains historical. The exact rebuilt
world, held boundary measurements, native captures and final image/readback
remain pending. Current source SHA-256:

- tools/chim/apron_policy.py: `cc4d185ca86d1492087336d692e4a7c406afecef63932b36cf0e9dc187354eec`.
- tools/chim/build.py: `b9fef940056525915fa48bee729a0be2c8192a69a9b92d987deb3d9dcdf35f26`.
- tools/chim_town.py: `1e9bf1319b967c3018460f3addff934100c5d063bab5916a6fe098203a73eb3a`.
- tests/test_chim_ownership.py: `10924642bfa3d07aa5e8be93e063c9404ea5d910462b529d40fdb93c53112178`.

## Missing Seyda apron dependencies: source repair, 15 October 2026

15 October 2026, v0.0.41-dev1: a source repair supplements only missing Seyda apron dependencies using the included original-cell owner's exact compiled mesh and textures, preserving original identity and unique ownership while translating frame-local origins. It targets rock reference 251397 and shell reference 461804; 32 focused ownership/apron checks pass. The rebuilt world and held boundary/native checks remain pending. Separately, independent normal interior/actor/UI conversion completed 2,451 files with unchanged source and inputs; it is not image, native or package acceptance. CHIM coverage states are unchanged.

The rock exists in the source index but falls outside the owned bounds used by
runtime selection. The shell exists in the original audit but is absent from
the scenery index. The supplement takes only missing apron dependencies from
an included original-cell owner's exact compiled mesh and textures. It shifts
the frame-local origin, preserves original reference identity and unique
ownership, and recomputes source metadata against the original audit. Invalid
ownership remains rejected. Existing geometry and representations, collision
tolerances and independent producer inputs are unchanged.

This reuses existing CHIM frame-local placed brush models and AmiQuake SV_Move
collision machinery; no runtime collision implementation is added. Four new
semantic regressions cover actual binary validation, differing frame-centre
translation, invalid-owner rejection and unaffected non-Seyda frames. All
32 focused ownership/apron checks pass. Current implementation/test SHA-256:

- apron_policy.py: `b42997f013ae64e96851e4c783ab58ae78fcdef7c0e96e9130736d6f193887a7`.
- build.py: `b9fef940056525915fa48bee729a0be2c8192a69a9b92d987deb3d9dcdf35f26`.
- test_chim_ownership.py: `58919c3e7a1999f8667d9ba37a9250bf0aa7ed756f8925595adbc7094c340a74`.

The complete world must be rebuilt before judging the targeted references or
held boundary pairs. Earlier full-suite, compiled-engine and world results
retain their exact source bindings and do not validate the changed apron code.
The three held boundary findings and 14 collision-only/visual representation
differences below remain unresolved; three null/no-hit residuals remain
unproven. No visual severity, missing visuals or universal equivalence is
inferred. Actual-game suspect captures await the assembled runtime image.

Separately completed independent conversion produced 2,451 files for normal
interiors, actors and UI using a metadata-only exterior carrier, with source
and inputs unchanged. It completed at 17:24:11 UTC; its receipt SHA-256 is
`b5b3a2b8f8436954915ca84aff473f72b73c5a52547f53bd714e0513816db8d2`.
This is conversion-only evidence. Current-world town actors, independent
Vivec rooms, actor contacts, image merge/exact payload checks, native gameplay
and package/readback/shipment remain pending. Earlier statements below that
this independent conversion was still running are historical.

The issue remains OPEN. The final 435-cell plan and all existing coverage
states remain unchanged; packaging, delivery and playtest acceptance require
their own matching evidence.

## Current conversion and held boundary evidence, 15 October 2026

15 October 2026, v0.0.41-dev1: exact source validation completed 4,242 tests (4,236 passed, three Windows-only skips and three Census expected failures), with zero failures/errors; the matching engine compiled. The completed 369-frame world passed structural/source, modeled heap, host zone-walk and scoped stair gates. Of 547 boundary comparisons, 544 measured agreement and three remain held (237, 241, 242). Of 36 sampled models, 22 have matching face counts and unique face correspondence; 14 differ in collision-only versus visual representation and require payload/sprite/native review. These measurements do not establish visual severity or universal equivalence. Native captures, independent interior conversion, image assembly/readback and package acceptance remain pending; coverage states are unchanged.

The 369-frame conversion is bound to unchanged original inputs and the exact
converter implementation. Structural/source validation reports no failures;
modeled heap and host allocator zone walks pass for all 369 frames. The scoped
stair gate passes with zero blocking failures across 94,480 tested cases while
retaining **15,348 advisory findings**. A scoped pass does not establish that
all candidate stairs are traversable in the native game.

### Three boundary comparisons remain held

| Pair | Measured finding | Remaining check |
| --- | --- | --- |
| 237 | Exact floating-point rendered-ground differences; support residual up to 0.00014953. | Matched native capture; no visual severity inferred. |
| 241 | Support delta up to 2.9548528. Original reference 461804 (kollop) exists in the Vivec owner catalogue but is absent from the Seyda source catalogue. | Source selection and matched native review. |
| 242 | Support delta up to 25.8135893 and four support-status disagreements. Original reference 251397 (rock) exists in the Vivec owner catalogue but is absent from the Seyda source catalogue. | Source selection and matched native review. |

The other 544 comparisons measured agreement under the existing audit. These
results do not prove every position, crossing or native scene equivalent.
Suspect-geometry captures remain pending because the new runtime image has not
yet been assembled. The report remains OPEN.

### Model measurements retain representation limits

Thirty-six original-reference model comparisons were sampled. Twenty-two have
matching face counts, unique one-to-one nearest-face correspondence and no
missing candidates; maximum sampled vertex residual is 0.0004662612, with no
sampled hit/no-hit disagreements. Three null/no-hit residual cases remain
unproven and are not recorded as zero error.

The other 14 references use collision_only hulls with zero render faces in
Seyda and visual model pieces in Vivec. This is a representation difference,
not proof of missing visuals or equivalent geometry. Sprite placement, final
payload representation and matched native appearance require review before
acceptance. Earlier model-piece provenance findings remain preserved; they
do not settle these assembled-payload questions.

### Exact validation scope

The preceding v0.0.41-dev1 source snapshot passed 4,242 tests: 4,236 passed,
three Windows-only skips and three exact Census expected failures, with no
failures/errors and unchanged source. Its manifest SHA-256 is
`f51cad7ffd30c6aa49d7bd35cb18794ed72299fd0253f56313c0647b67de047b`. The matching compiled engine is
1,071,728 bytes, SHA-256
`ac1b1b39a60ae5363289d40327466cff410995eceb43a7b06ba221417bb9c86c`. These results cover that source and compiled
artifact; they are not native execution, a finalized image or a package.

Boundary measurement receipt SHA-256:
`f4385124328e4518900ffcf9d863f36350cc02a8a72211004869f4e774e97dfa`.
Model measurement receipt SHA-256:
`a0a437cd263e6966c55c9e180fd45591789087bc78aed7d9284ead21b3c74c55`.
Structural/source receipt SHA-256:
`e53c5a85145baf9b3a0ae16b28420b5fb898a181909161204a708c89d1f5e06c`.

Independent normal interior, actor and UI conversion is still pending. The
435-cell final release plan and all existing converted, audited,
native-checked and packaged states are preserved. No new inclusion, native,
package, shipment or playtest acceptance is claimed by this record update.

## Named-apron owner dispositions, 15 October 2026

15 October 2026, v0.0.41 source candidate: the 941 world stopped at the unchanged ownership guard because ten explicitly deferred Seyda references reappeared through a named-town apron. The candidate applies the existing exact owner dispositions to named and regional neighbours alike. All ten original deferred IDs are verified and 38 focused checks pass. Fresh affected-world conversion and renewed boundary/memory checks remain pending; no coverage, native, package or owner acceptance is promoted.

The failed world941 reached the existing original-reference ownership guard.
All ten reported references match exact declared Seyda deferred originals:
251326, 251342, 251343, 251344, 251406, 251407, 208129, 208130, 208131, 208132.
They reappeared as dependencies through the neighbouring named Vivec apron.
The guard rejected this contradiction; it was not relaxed or bypassed.
Source and input hashes were unchanged in the preserved failed run.

The reconciliation path applied exact owner dispositions only to regional
neighbours and skipped named neighbours. The candidate now applies those SAME
existing rules to every neighbour, preserving original reference identity,
owner disposition and reason. It reuses the existing apron reconciliation
and ownership machinery; no renderer, collision hull, geometry algorithm,
reference transform or runtime memory-budget change is introduced.

### Selected and deferred accounting

The ten references remain explicitly deferred under their original owner's
existing declarations. A named-apron dependency must inherit that declaration
rather than silently reintroduce the reference. Original types, identities and
reasons remain attached to the records. Other selected/deferred references,
actors and unimplemented gameplay retain their earlier state. No new included
reference count is claimed before the fresh conversion and its guarded audit.
The 435 planned cells are unchanged; planning is not conversion or packaging.

The focused ownership receipt passes 38 checks with zero failures, errors or
skips and verifies the ten original IDs. It includes four named-neighbour
regressions for inherited owner policy. Its source hashes match the current
apron-policy and ownership-test files. Full fresh-world ownership, boundary,
memory/zone/stair and geometry checks remain required. Exact940 full-suite
acceptance remains bound to its immutable source, not this changed policy.
The two earlier failed worlds936 and941 remain preserved as distinct failures.

The fourteen previously questioned STAT references have model pieces on both
frame sides; actual model geometry equivalence remains under review. Neither
their earlier sprite-only lookup nor the named-apron fix proves a runtime
omission or its cause. Native suspect captures await a matching runtime image;
no current package, delivery artifact, shipment or owner acceptance is established.

## Earlier coastal survey and retained-world evidence

## Outer sea LAND survey follow-up, 15 October 2026

15 October 2026, v0.0.41 source candidate: the expanded Vivec survey stopped before conversion because two outer sea cells have no original LAND. All 36 owned cells have original LAND. The candidate selects the existing flat seabed policy for missing outer LAND; its source audit and 10 focused tests pass. The failed 936 world is preserved, and exact source 935 retains its reviewed full-suite pass. Fresh affected-world conversion and renewed boundary/memory checks remain pending; no native, package or owner acceptance is established.

The expanded radius-4 source survey found no original LAND for cells (7,-16)
and (8,-16). Both lie outside the unchanged 36-cell owned core. The complete
936 attempt is preserved as failed: after 365 regional preparations, the
source audit stopped before Vivec conversion, with source and inputs unchanged.
It does not establish a new completed world or boundary repair.

The candidate sets missing_land to flat, using the existing default-land
policy whose source heights are all -2048. No production Python changes are
introduced. The owned-cell rectangle, radius, 768-unit scenery apron, origin,
original owned LAND, terrain detail settings and budget remain unchanged.
This policy handles absent outer seabed records; it does not assert that
original LAND existed there or promote synthetic data to original coverage.

Original-data audit confirms that all 36 owned cells have LAND, identifies
exactly the two absent outer records, and verifies the existing flat default.
Ten focused town-grid checks pass with zero failures or errors; their bound
config/test hashes match the current candidate. This does not validate a
complete conversion. Exact source935 separately passed its reviewed full suite:
4,236 run, 4,230 passed, zero failures/errors, three Windows-only skips and
three tracked Census expected failures, with source and pin unchanged.
That predecessor suite does not cover the new missing-LAND setting.

Selected and deferred reference accounting remains bound to the predecessor
receipts until the fresh affected-world conversion reports exact selection,
exclusions and original reference types. Canonical 435 planned cells retain
coverage history; no converted, native or packaged state is promoted.
Nine boundary findings and actual model geometry equivalence remain under
review. The 14 previously questioned references are represented as model
pieces on both sides; their earlier sprite-only lookup is not proof of runtime
omission. No cause linking that lookup to the seabed policy is established.
Native suspect captures await a matching runtime image; no package or delivery
artifact exists for this candidate.

## Earlier apron repair and retained failed-world evidence

## Vivec scenery selection repair, 15 October 2026

15 October 2026, v0.0.41 source candidate: reference tracing finds one-sided placed scenery in eight of nine held boundary pairs (31 pair/reference entries, 30 unique original references). Vivec selection now requests a 768-unit scenery apron with source radius 4, retaining the same 36 owned cells, origin, terrain and detail budget. The regression fails against the prior configuration and 64 focused checks pass with unchanged source. Affected-world conversion, renewed seam/memory checks and native verification remain pending. Pair 237 retains a small numeric ground residual requiring review; no universal seam or package acceptance is established.

The earlier complete-world audit is preserved. Its eight model-bearing held
pairs contain 31 pair/reference entries representing 30 unique original
references, with placed scenery present on only one side. Pair 237 has no
held model samples in this trace: its maximum ground residual is
0.0006713867144654273. That measurement is retained for review, not silently
zeroed or promoted to acceptance.

Vivec used reference_margin 0 and source_radius 3, so its scenery selection
omitted the apron used by adjacent frames. The source candidate requests
reference_margin 768 and source_radius 4 using the existing original-reference
selection machinery. This reuses the existing compiled-footprint/apron path;
no new AmiQuake renderer, physics, hull or loader mechanism is introduced.
The 36 owned cells, origin, terrain settings, transforms and detail budget
remain unchanged. Neighbour scenery selection does not transfer cell ownership.

### Selected and deferred accounting

The failed world's exact selected/deferred reference records remain historical
evidence; source configuration is not proof that new references are included.
The 30 traced original references remain bound to their pair/frame/original
IDs. Affected conversion must report the resulting selected references and
explicit exclusions/deferred rows using their original types and reasons.
No new inclusion count is claimed before that conversion. Actors and deferred
or unimplemented gameplay retain their earlier states. Canonical 435 planned
cells are unchanged, with no converted, native or packaged coverage promotion.

The new regression fails once against the old configuration, then the focused
selection/ownership checks pass without skips and with source unchanged.
The focused receipt supplies candidate evidence. Complete affected-world
conversion, memory/zone/stair and renewed boundary checks remain pending.

The separate 14 sprite provenance gaps from model932 are still under
investigation. No cause connecting them to this apron setting is established,
and missing lookup rows are not evidence of missing runtime sprites. Native
suspect captures remain pending a matching runtime image. No package or delivery
artifact exists for this candidate.

## Earlier boundary and conversion evidence



15 October 2026 current checkpoint: 15 October 2026, v0.0.41: complete547-pair offline boundary audit has538agreements and9Vivec differences requiring review, with unchanged input hashes. Earlier paired Seyda success is scoped evidence only. No universal seam acceptance; native suspect captures await a runtime image. A separate scoped contact check now passes for 17 serialized actors; the nine boundary findings remain held. See [CHIM-MODEL-ARENA-RESERVE-41](CHIM-MODEL-ARENA-RESERVE-41.md#zone-actor-and-model-checkpoint-15-october-2026).

## Combined-world review checkpoint, 15 October 2026

15 October 2026, v0.0.41: complete547-pair offline boundary audit has538agreements and9Vivec differences requiring review, with unchanged input hashes. Earlier paired Seyda success is scoped evidence only. No universal seam acceptance; native suspect captures await a runtime image. Actor/contact verification remains pending.

All547pairs completed with input hashes unchanged; source is the immutable
allocation candidate used for the complete successor world. Nine held pairs
are237,239,241,242,243,263,275,300,301, all at Vivec boundaries.

| Pair | Held difference |
| --- | --- |
| 237 | 278 render-ground disagreements |
| 239 | 184 status disagreements; maximum height difference44.1498 |
| 241 | Maximum height difference2.95485 |
| 242 | 110 status disagreements; maximum height difference43.986 |
| 243 | 624 status disagreements; maximum height difference34.255 |
| 263 | 8 status disagreements; maximum height difference0.747 |
| 275 | 18 status disagreements; maximum height difference18.20 |
| 300 | 4 status disagreements; maximum height difference36.454 |
| 301 | 9 status disagreements; maximum height difference5.993 |

The existing height tolerance0.25 was not changed. These are offline audit
flags requiring review, not proof of a visible defect or a completed repair.
Suspect snapshots in the actual game are pending because no runtime image
of this complete world is available yet. Preserve each pair's source/frame
bindings and capture locations when native capture becomes possible.

The first actor/contact follow-up stopped before any actor check: its chosen
metadata-only candidate path contained no model payload. The corrected
binding verified17models and its carrier map hash, but the follow-up stopped
before contact measurement at a helper module-import failure. A bounded retry
with standard source-before-tools module ordering is pending. No actor/contact
success is established.

## Earlier scoped evidence

## Symptom

Paired compiled-world support queries disagree across the southern Seyda
boundary. Of 2,816 identical world-position samples, 477 return different
full-static support states. Among 2,339 pairs supported on both sides, the
largest height difference is 44.5188746683 game units. Differences occur on
the shared edge and inside the 64-unit map-handoff band.

Terrain height, water, terrain-only standing support, world point contents
and the common standing-hull probes agree. This is a separate static scenery
failure, not evidence that those terrain checks failed.

## Where

Frames `rcm2_m12` and `seyda`; original cells (-2,-12) and (-2,-11).
The shared original-space edge is Y=-90112, X=-16384 through -8192.
Original references 463188, 463190, 463191, 463192 and 463193 occur in the
scenery hits. CHIM Engine remains 0.2.0 and world format remains 0.7.

## How it happened

The cause is under investigation. Compiled source accounting has these five
references in Seyda, each originating in cell (-2,-11); the neighboring
regional frame has no static placements. At the same crossing coordinates,
its query hits terrain while the Seyda query hits scenery. The regional
settings currently request only the original cell and a terrain-only apron.
Missing neighboring scenery dependencies are the leading hypothesis.

## Why it was not caught

Structural validation, heap simulation, zone walking and the per-frame stair
gate pass. They do not establish that two independently generated frames give
the same static support at a shared world position. The expanded paired-frame
check detects this difference and stops with the evidence preserved.

## Reproduction

Use combined world source `1a551532d3f6643e2192b25e931ea887305a6827`.
Compare both frames at identical original XY coordinates on the edge and at
runtime offsets -64, -32, -5, -2, -0.25, 0, 0.25, 2, 5, 32 and 64.
At original XY (-10704,-89984), the regional frame supports the query at
approximately -192.2588 game units; Seyda reports it blocked at approximately
-147.6875 on reference 463193. Preserve each frame's transform and query hull.

## Repair

Pending. Retain one logical original-cell owner while preserving required
scenery copies and original transforms through the crossing apron. Do not
move actors, drop references, enlarge tolerances or mark unmeasured seams as
passing. A repaired successor must preserve the prior world as evidence.

AmiQuake mechanisms reviewed: `SV_CheckBottom` in `sv_move.c` checks ground
with midpoint/corner traces; CHIM's `chim_world.c` activates one frame and
prioritizes chunks inside its collision margin. These mechanisms require the
appropriate scenery to exist in the selected frame. No runtime change has
been made for this finding.

## Verification

The original combined conversion completes with source and inputs unchanged:
369 frames, source-aware structural validation, heap, zone walking and 39,854
stair/ramp tests pass (6,507 advisory). These gates retain their own scope.
Five adjacent boundary segments agree; this sixth segment fails and 541
remain unmeasured. All six measured segments agree for terrain and water.
The audit preserves exact index, validation, source and per-frame bindings.

An actual-game SUSPECT GEOMETRY snapshot is pending: a fresh combined-world
native image has not yet been assembled. The target above and implicated
reference IDs are retained for that capture and matched original-game view.
No visible native failure, repaired native traversal, packaged coverage,
shipment or acceptance is claimed.

## Prevention

Gate the complete combined world on paired static support and scenery
accounting across all selected neighboring frames, including empty regional
cells next to towns. Verify logical owners separately from required apron
copies. Preserve visual, collision, native and packaging checks separately.


## Proposed regional source repair, 15 October 2026

The regional source audit now includes adjacent cells. Whole-object scenery
selection retains the explicit apron through packing; an owned-cell rectangle
keeps source identity and logical ownership separate from dependency copies.
Core bounds, actor positions, runtime tolerances and CHIM version are unchanged.
All 73 focused regional, ownership, town and source-reuse checks pass. A fresh
compiled crossing comparison remains required; no native or package closure.


## Coastal apron source guard, 15 October 2026

The first compiled repair probe stopped before conversion because the expanded
source survey includes heightless ocean neighbors. The revised source permits
that recorded apron fallback but rejects missing LAND in an owned land cell;
explicit ocean cores retain their existing admission rule. All 74 focused
regional, ownership, town and source-reuse checks pass. Compiled comparison,
native verification and package acceptance remain pending.


## Sub-cell apron parity, 15 October 2026

The second probe found that sub-cell coverage still clipped the new scenery
apron at core bounds. Coverage now extends to the explicitly configured apron,
while sub-cell cores and logical ownership remain unchanged. The exact union
guard is retained and now exercised by a corner-apron regression. 75 focused
checks pass. Both preliminary failures are retained; compiled, native and
package acceptance remain pending.

## Authored collision retained, 15 October 2026

The compiled regional apron probe reduced support-state disagreements from
477 to69 and maximum supported-height difference from44.518874668 to8.258318516
game units. Terrain and water controls still agree. Reference463188 has the
same original NIF, transform and63render faces in both frames, but40of588
isolated collision rays disagree on whether they hit. The regional source
retains the original RootCollisionNode; the Seyda carrier omitted it and
therefore compiled collision from visible geometry.

The proposed CHIM repair supplements the existing carrier with its original
authored collision. It verifies both original NIF and visible-packet hashes,
preserves all original carrier bytes and index data, and appends only verified
collision packets to a separate archive. Existing mesh cache keys include the
collision hash. No runtime tolerance, model placement or rendering changes
are introduced. The existing converter and AmiQuake clipnode machinery remain
in use. Nineteen focused collision/Seyda checks pass, including immutable
carrier readback, exact supplement reuse and source-mismatch rejection.
Compiled pair comparison, matched native traversal, full suite and packaging
remain pending; the issue remains open.

## Compiled rock result and original kelp, 15 October 2026

The authored-hull repair produces zero support-state disagreements at all2,816
paired positions (5,632 queries) along the original failing boundary. Terrain,
water and common standing-hull controls also agree. The compiled Seyda frame
passes structural validation, heap sizing and zone walking. Its24-worker
stair check exceeded the8GiB container limit and is incomplete, not passed.

The combined owner gate also exposed original kelp omitted by Seyda's legacy
dressing filter. These references exist in the verified source carrier but
have no separate flora sprite representation. The proposed successor retains
only the three original kelp meshes, with their original placements, and binds
those entity-stage parity additions to the original scenery selection. Other
deferred dressing remains deferred.43focusedSeyda, town and ownership checks
pass. Combined-world validation, matched native checks, package and shipment
remain pending; source and compiled results do not establish acceptance.

## Owner apron policy, 15 October 2026

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

## Paired boundary validation, 15 October 2026

The latest v0.0.40 paired conversion passes structural, heap, zone-walk and
stair validation. The 3,836 tested steps and ramps pass; 610 advisory results
remain recorded. Across 2,816 paired positions, full-static support states agree
and the maximum supported-height difference is 0.000077 game units. Terrain,
water and common standing-hull controls agree. The complete 369-frame successor
is being built from the same converter source; its acceptance remains pending.
The exact source full suite is running. Native gameplay, other boundary segments,
fresh package readback and shipment remain separate unfinished gates.

The exact conversion source manifest is SHA-256
`88f5772209462c52b592f6748fc9a5e46ee4575a224c4e0e2991762d7e2e5d99`.
The earlier stair memory failure remains historical evidence; this new pair
completed the stair check with its own larger memory allowance. No runtime
collision tolerance was widened. The issue stays open pending the full gates.

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

Original rock 412217 has a source-box maximum Y of 111168.550388 and
a compiled maximum Y of 111100.673570. The apron starts at Y=111104
in original coordinates. Exact cached mesh and variant bytes established
this difference without another asset conversion. The existing AmiQuake
placement-box calculation is used; ownership validation is unchanged.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: World storage and duplication (`world-storage`). Every asset stored once and placed by reference (world streamer); map lumps carry only what the engine uses. See [families](README.md#families).

- [BSP-SHARED-SUBTREES-32](BSP-SHARED-SUBTREES-32.md): Converted maps share node subtrees between submodels; naive tree walks explode
- [CHIM-FRAME-DEPENDENCY-OWNERSHIP-40](CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md): Boundary scenery dependencies are treated as duplicate frame owners
- [CONVERT-VARIANTS-32](CONVERT-VARIANTS-32.md): Objects are converted once per mesh, scale and tilt: 4-7 times more models than meshes
- [INTERIOR-HULLS-HEAVY-32](INTERIOR-HULLS-HEAVY-32.md): Interior collision hulls are bigger than the interior geometry they belong to
- [MAP-TEXTURE-COPIES-32](MAP-TEXTURE-COPIES-32.md): Every map carries its own copy of every texture it uses
- [REGION-PLACEMENT-FORMS-32](REGION-PLACEMENT-FORMS-32.md): The same placement is stored in different forms from region to region
- [VF-VIS-LUMP-32](VF-VIS-LUMP-32.md): Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little
- [WORLD-REGION-DUPLICATION-31](WORLD-REGION-DUPLICATION-31.md): Every exterior object is stored about ten times (overlapping region maps)

Related bugs in other categories:

- [CHIM-LAVA-DUPLICATE-VERTEX-40](CHIM-LAVA-DUPLICATE-VERTEX-40.md): Float32 duplicate vertices falsely fail lava surface coverage
- [CHIM-MODEL-ARENA-RESERVE-41](CHIM-MODEL-ARENA-RESERVE-41.md): Placed CHIM models reserve renderer nodes that their point-hull loader never allocates

<!-- END GENERATED CATEGORY -->
