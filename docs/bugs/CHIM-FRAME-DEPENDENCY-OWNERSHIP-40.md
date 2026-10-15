# CHIM-FRAME-DEPENDENCY-OWNERSHIP-40: Boundary dependencies become duplicate frame owners

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | gate:chim-validate |
| First noticed | 15 October 2026, in v0.0.40-dev2 |
| Where | CHIM combined-world frame placement ownership validation |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.40-dev2 (last seen) |
| Severity | critical: Combined-world validation prevents the required full rings candidate from reaching native and package gates. |
| Family | World storage and duplication (`world-storage`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 3856b16, engine unknown, CHIM world 3856b16 |
| CHIM engine version | CHIM 0.2.0, engine unknown, world format 0.7 |
| Unknown because | Offline combined-world conversion and validation; no native engine exercised. |
| Platform or emulator | not in game (Validation of generated world bytes and original source catalogues.) |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Combined-world readback, 15 October 2026](#combined-world-readback-15-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Full source gate and release scope - 15 October 2026](#full-source-gate-and-release-scope---15-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Combined-world readback, 15 October 2026

The successor completes structural, heap, zone-walk and stair validation with
source and inputs unchanged. Six paired boundaries agree for terrain/water;
static scenery differs at the southern Seyda boundary. Model/sprite, final
actor contact, native and package acceptance remain pending.
[Static boundary finding](CHIM-FRAME-STATIC-SEAM-40.md).
Earlier failed or pending checkpoints below remain historical evidence.


## Symptom

The v0.0.40-dev2 combined world generates 369 frames, then validation rejects
six cross-frame ownership errors for placements owned by two frames. Source and input integrity
checks pass. The failed output cannot advance to seam, native or package
acceptance and remains preserved.

## Where

`tools/chim/build.py`, `tools/chim/seyda.py`, `tools/chim/world.py` and
`tools/chim/validate.py`, at original-cell Seyda and Vivec boundaries.
CHIM Engine remains 0.2.0 and world format remains 0.7.

## How it happened

Original-cell catalogues distinguish physical-origin owners from footprint
or assembly dependencies. Construction retains whole-object dependencies
needed at boundaries. The world writer assigns each placement a local owner
chunk; validation treats every repeated placement ID across frames as a
second global owner. The catalogue distinction is not carried through this
combined check.

All 36 repeated originals have identical original position, rotation, scale,
model identity and source cell in both catalogues, with exactly one logical
physical-cell owner. Six frame pairs are affected:

| Pair | Original references |
| --- | ---: |
| Seyda / cell (-1,-12) | 4 |
| Seyda / cell (0,-12) | 3 |
| Seyda / Vivec | 20 |
| Vivec / cell (3,-15) | 3 |
| Vivec / cell (4,-15) | 1 |
| Vivec / cell (7,-14) | 5 |

Binary readback finds 79 local placement records. Twenty-two matched piece
IDs use different model records between frames; reference 341399 is whole
in Seyda and split into eight pieces in Vivec. Different records alone do
not prove different geometry. Render/collision equivalence remains pending.
Matched-piece XY differences are at most 0.00048828125 original units.

A follow-up comparison finds identical decoded render geometry for 21 of
36 originals. Fourteen others are explicitly named collision-only foliage
models in Seyda and full meshes in Vivec. The Seyda conversion sends their
rendering through separate sprite entities; those exact companion bindings
and boundary behavior still need validation. The remaining object has 63
faces in both forms, whole versus eight pieces, without established union
or collision equivalence. None of these counts alone demonstrates a hole.

## Why it was not caught

Individual town checks do not contain both sides of a boundary. The combined
check detects the contract mismatch after conversion. Original-cell metadata
and per-frame checks had not exercised boundary dependencies together.

## Reproduction

Generate the four approved towns and 365 regional frames from source
`3856b16fa4c6dc8517da9cc25cfb58317d6fa405`, then run source-aware validation.
Compare the six pairs above using original reference identities, mapping
cut-piece IDs back to the original reference before comparing copies.

## Repair

Implemented in the current source candidate. Both preparation paths snapshot
original identity/transform before mounting and visual offsets, including
merged flora and the opening barrel. Core and apron coverage remain separate.
A source ownership check runs before pack assembly. Dependencies outside an
isolated selection remain valid; an included original owner must be present.

Each frame records the exact piece IDs, stored float poses, source cells,
story state and render/collision payload hashes. Validation checks those
against serialized records and the bound world index. Legacy or incomplete
metadata retains the strict cross-frame duplicate guard. Chunk owners, reach
copies and global placement-ID validation are unchanged. No scenery is
removed, renumbered or relocated by this repair.

Asset identity uses the original case-insensitive names and normalized path
separators. Render variants, collision-only flora and cut pieces retain their
existing representations. Logical ownership does not establish their visual
or collision equivalence; those checks remain separate release gates.

AmiQuake mechanism reviewed: the CHIM loader selects one frame at map start
and uses its existing chunks, model cache and efrags. A local chunk owner is
storage/streaming ownership, not proof of a second original reference owner.
No runtime mechanism or binary format was changed.

## Verification

The source repair passes 37 focused synthetic checks, including serialized
adjacent frames, missing included owners, conflicting source identities,
altered render/collision payloads, missing pieces, stale index bindings,
legacy metadata, source snapshots and existing town-grid controls. All 369
original source catalogues, including their separately sourced flora, satisfy
the source contract: 25,802 owner records and 141 dependencies. This review
does not alter or approve the previously failed world.

A new exact-source combined build and its binary readback are still pending.
The 14 collision-only flora companions and reference 341399's whole/eight-piece
geometry require explicit representation checks. Compiled seams, contact,
matched native views, full package readback and shipment remain pending.

Historical failure evidence:

Catalogue identity and single logical ownership pass for all 36 repeated
originals. Binary placement readback completes. Full validation still fails;
model equivalence, compiled seams, actor contact, matched OpenMW/FS-UAE views
and packaging remain pending. No visible defect or repaired native traversal
is established. If model comparison flags suspect geometry, its actual-game
snapshot with reference/build bindings remains required before a visual claim.

Earlier source and individual-cell evidence retain their scope. The earlier
incomplete conversion remains separate. No new converted, audited,
native-checked, packaged or shipped coverage is promoted from this output.

## Prevention

Add adjacent-cell source-to-binary regressions for overhanging scenery and
cut-piece variants. Reject duplicate logical owners, missing owners in
included cells, changed original transforms, unaccounted references and
altered dependency geometry. Keep structural, seam and native gates distinct.


## Full source gate and release scope - 15 October 2026

Source 1a551532 passes 4,207 tests: 4,201 passed, three Windows-only skips and
three tracked Census expected failures. Source and frozen input hashes are
unchanged. The runtime and its build dependencies match the previously passed
target build. This does not accept the failed combined world. The final release
plan contains 369 frames over 435 spatial original-cell cores, including all
ring-0, ring-1 and ring-2 cells. The conservative conversion digest records
419 cells because two historical town receipts lack a full owned-cell declaration;
planned spatial extent must not be counted as verified conversion coverage.
The repaired combined world, reference companions, native crossings and exact
package checks remain pending.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: World storage and duplication (`world-storage`). Every asset stored once and placed by reference (world streamer); map lumps carry only what the engine uses. See [families](README.md#families).

- [BSP-SHARED-SUBTREES-32](BSP-SHARED-SUBTREES-32.md): Converted maps share node subtrees between submodels; naive tree walks explode
- [CHIM-FRAME-STATIC-SEAM-40](CHIM-FRAME-STATIC-SEAM-40.md): Static scenery collision differs across the southern Seyda frame boundary
- [CONVERT-VARIANTS-32](CONVERT-VARIANTS-32.md): Objects are converted once per mesh, scale and tilt: 4-7 times more models than meshes
- [INTERIOR-HULLS-HEAVY-32](INTERIOR-HULLS-HEAVY-32.md): Interior collision hulls are bigger than the interior geometry they belong to
- [MAP-TEXTURE-COPIES-32](MAP-TEXTURE-COPIES-32.md): Every map carries its own copy of every texture it uses
- [REGION-PLACEMENT-FORMS-32](REGION-PLACEMENT-FORMS-32.md): The same placement is stored in different forms from region to region
- [VF-VIS-LUMP-32](VF-VIS-LUMP-32.md): Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little
- [WORLD-REGION-DUPLICATION-31](WORLD-REGION-DUPLICATION-31.md): Every exterior object is stored about ten times (overlapping region maps)

<!-- END GENERATED CATEGORY -->
