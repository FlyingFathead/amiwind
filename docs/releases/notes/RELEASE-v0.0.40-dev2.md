# AmiWind v0.0.40-dev2 inspection candidate

## Combined-world gate update, 15 October 2026

All 369 frames complete conversion and structural, heap, zone-walk and stair
validation. Five adjacent boundary segments agree; the southern Seyda segment
fails full-static support and 541 segments remain unmeasured. Repair and
native capture are pending. No new native, packaged or shipped coverage is
promoted. [Static seam](../../bugs/CHIM-FRAME-STATIC-SEAM-40.md) and
[boundary ownership](../../bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).
Earlier preparation checkpoints below retain their original scope.


Final release title: **v0.0.40: Rings 0, 1 and 2 of Vvardenfell in Full CHIM**.
This development candidate is still undergoing the required release checks.
The remaining exterior world retains its existing legacy representation, except
for named CHIM towns. Door-entered interiors remain independent.

Current source checkpoint, 15 October 2026: boundary ownership repair passes
37 focused checks and the source contract for all 369 frames. Combined-world
readback, split-model/sprite dependencies, seams, native gameplay and full
package gates remain pending. Converted, audited, native-checked and packaged
coverage retain their previous receipts.
[Ownership repair](../../bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).


Running on CHIM Engine v0.2.0. Candidate preparation: 15 October 2026.

## Changes since dev1

- Player model fitting now searches the existing mesh options for full action
  sampling before accepting reduced frames. Geometry, anatomy and memory limits
  remain unchanged. Production and native checks are pending.
  [Body fitting](../../bugs/BUILD-PLAYER-BODY-BUDGET-FALLBACK-39.md).

- Simplified actor vertices now carry their offsets with a rotating limb.
  The prior transfer preserved translation but could deform rotating poses.
  Nine focused regressions and 115 shared converter checks pass. Rebuilt
  original assets and gameplay verification are still pending.
  [Animation transfer](../../bugs/NPC-ANIMATION-OFFSET-40.md).
- Inventory panels separate the title, six item rows, details, status and
  controls. The scrollbar uses bounded shared UI behavior. Dedicated character
  companions provide ten inventory poses instead of a combat-ready preview.
  Twenty companions and one Nord equipment sequence were checked in an earlier
  diagnostic build. The new candidate requires its own checks.
  [Inventory layout](../../bugs/UI-INVENTORY-LAYOUT-40.md).
- Opening HUD activation follows the original sequence: character review reveals
  status bars, reading the papers reveals the weapon slot, taking them enables
  fighting, and taking the ring reveals the magic slot.
  [Opening HUD](../../bugs/HUD-STATS-29.md).

## Remaining playtest gates

This is an unreleased inspection candidate. Third-person ready movement,
physical punching and damage, blocking in both views, swimming, gait and leg
shape remain open. Inspect the exact packaged build with normal collision and
warp disabled. Serialized asset checks do not establish animation quality.

The inventory still has unfinished original artwork, full item coverage and
appearance/equipment support. Dropping into unsupported CHIM terrain remains
explicitly refused. Original game assets, private workflows and captures are
excluded from matching public source.

## Required CHIM coverage - 15 October 2026

Dev2 requires complete approved rings 0, 1 and 2 and original-cell town
ownership, with separate aprons. A gameplay-only release does not meet this
scope. Independent interiors and required nonduplicate dependencies remain.

Vivec has offline conversion evidence for 36 core and 28 apron cells. Expanded
Seyda has 16 core and 20 apron cells; 3,724 stair walks report zero blocking
failures and 532 advisory findings. The 29 zone chunk loads without room remain
explicit. Four Seyda and two Vivec ring-2 overlaps are converted offline.
The five additional ocean frames also pass scoped offline checks; four original
leveled-creature spawns remain deferred. These counts do not establish playable
coverage or complete package inclusion.

The corrected source-only Seyda carrier completes, including resident models,
voices, animations and original references. Integration matches all 1,390
scenery placements, but Nels Llendo and one dreamer fail final ground contact.
Original LAND comparison finds coarse terrain distortion at both sites.
The source now restores two original-detail tiles and uses OpenMW 0.48
diamond diagonals for full-detail terrain. Source coordinate/edge checks pass,
but compiled contact and native seams are pending. Nels has a feasible source
height interval; the dreamer remains unresolved across the existing search range.
No actor omission, widened contact tolerance or native acceptance is claimed.

Historical package coverage remains 171 ring-1 cells and 154 of 160 ring-2
whole cells. Combined-world routing, actor contact, native visual/collision
seams and exact package readback remain necessary before promoting coverage.
CHIM-owned terrain/scenery BSP compilation and duplicate package payload are
excluded; small empty-world entity/frame carriers and independent interior
BSPs remain required where selected.

See [cell coverage](../../chim/CELL_TRACKER.md),
[actor contact](../../bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md),
[terrain diagonals](../../bugs/CHIM-TERRAIN-DIAGONAL-40.md),
[stairs](../../bugs/CHIM-SEYDA-EXPANDED-STAIRS-40.md),
[core/apron accounting](../../bugs/CHIM-TRACKER-APRON-40.md),
[the bug register](../../BUGS.md#fix-index) and [roadmap](../../ROADMAP.md).

## Validation and delivery

The terrain source completes 4,191 tests: 4,185 passes, three Windows-only
skips and three tracked Census expected failures, with no unexpected failures
or errors. Exact unchanged runtime/build inputs verify Amiga engine reuse.
Original LAND ray/contact diagonal differences are documented; compiled-world
contact, native seams and packaging remain pending.
The current-source player conversion and independent readback verify 243 files,
100 models and all 20 appearances across normal/torch/swim/inventory companions.
Argonian male sampling retains 122 frames. These asset bytes match the preceding
checked set; native gameplay and visual acceptance remain separate.

Documentation, generated trackers, allowlist and normal public-source export
are checked together. Any later code change requires its affected gates.
The combined world, fresh packaged-build native checks, complete playtest and
matching source delivery remain pending. Dev2 has not shipped. Earlier failed
runs and the existing v0.0.39/dev1 deliveries remain preserved.

## Combined-world status, 15 October 2026

A subsequent complete world fails six ownership checks. All 36 repeated
original references have one logical owner; binary dependency equivalence
and repaired validation remain pending.
[Boundary ownership](../../bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).
No new native, packaged or shipped ring coverage is established.
The full gameplay and CHIM rings 0, 1 and 2 scope remains required.
