# AmiWind v0.0.40: Rings 0, 1 and 2 of Vvardenfell in Full CHIM

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

## Latest owner/apron correction, 15 October 2026

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

## Combined-world gate update, 15 October 2026

All 369 frames in the combined candidate passed conversion, structural,
heap, zone-walk and stair validation on 15 October 2026. This establishes a
conversion result for that exact source, not native or packaged acceptance.
The initial comparison measured six of 547 original-cell boundary segments:
five agreed, while southern Seyda between (-2,-12) and (-2,-11) had 477
full-static support disagreements. Later scoped results are recorded below;
the remaining 541 segments are unmeasured.

The regional scenery apron first reduced the southern Seyda comparison from
477 to 69 support-status disagreements. Original reference 463188 had identical
63 rendered faces but 40 collision hit-presence disagreements in 588 rays:
the regional path retained the authored RootCollisionNode while the legacy
Seyda carrier omitted it. A CHIM-only supplement verifies the original NIF and
visual hashes, preserves carrier bytes and appends the original authored hulls.

The corrected Seyda frame now compiles with zero structural failures and passes
heap and zone-walk checks. Compared with the repaired regional frame, the same
boundary has zero full-static support-status disagreements across 2,816 samples
(5,632 queries); terrain and water controls also agree. Its complete stair gate
is unfinished: the parallel run exceeded its memory limit and was stopped by
out-of-memory termination. A passing boundary sample is not a complete stair,
combined-world, native or package pass.

The combined attempt then stopped at ownership validation before packing:
original kelp references, including 463098, were omitted from the Seyda frame.
These references are present in the original source carrier and absent from the
existing flora sprite receipt; a legacy dressing filter removed them. The next
source correction retains only the three known original kelp meshes 01/02/03,
binds additions to the original scenery index and leaves unrelated deferred
dressing unchanged. All 43 focused Seyda, town and ownership checks pass.
Compiled verification of this later correction, native checks and packaging
remain pending. The earlier source's running full suite does not certify it.
[Static seam](bugs/CHIM-FRAME-STATIC-SEAM-40.md) and
[boundary ownership](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md).


Release preparation, 15 October 2026. CHIM Engine remains v0.2.0.
This source checkpoint is not a shipped or accepted final release.
The Linux update starts from the published v0.0.39 main commit
`751e1efa6b28e7fc58453fc81c73100715b88195`.

## Release scope

The required scope is complete approved CHIM rings 0, 1 and 2, together with
current gameplay repairs. Original-cell town ownership, separate aprons,
original-reference accounting, preserved horizons and adjacent-cell visual and
collision seams are required. The remaining exterior world retains its existing
legacy representation, except for named CHIM towns. Door-entered interiors remain
independent. A gameplay-only package does not meet this release scope.

The plan covers 435 original cells in 369 frames. All five ring-0 cells,
171 ring-1 cells and 160 ring-2 cells belong to the plan. Planned coverage is not
packaged coverage. The current [cell tracker](chim/CELL_TRACKER.md) keeps the
converted, audited, native-checked and packaged states separate.

## Changes prepared since v0.0.39

- CHIM town boundaries follow original cells, with separate apron dependencies.
  Replaced exterior BSP terrain and scenery are excluded before compilation and
  from the payload. Required entity carriers and independent interiors remain.
- Original terrain detail and diagonal selection have been corrected in source.
  Adjacent source heights agree; compiled contact and native seams remain gates.
- Boundary dependency validation now preserves a single logical original owner
  across repeated frame dependencies. The combined world passes conversion and
  structural gates; static seam acceptance remains held.
- Gameplay changes address held attacks, blocking, original opening HUD timing,
  inventory layout and character previews, and rotating-limb animation offsets.
  Their complete native acceptance remains pending.
- The README includes original AmiWind dev1 photographs of two ring-2 shipwreck
  exteriors. Their build and free-camera scope are labelled. Original-game
  reference screenshots are excluded from public source.

## Known in this build

The [bug register](BUGS.md#fix-index) is the current status authority.
These open checks prevent final package acceptance:

- [CHIM-FRAME-STATIC-SEAM-40](bugs/CHIM-FRAME-STATIC-SEAM-40.md):
  the corrected sampled boundary now has zero full-static support-status
  disagreements. The full stair gate is unfinished, and the combined attempt
  failed ownership before packing because original kelp was omitted. The next
  kelp source correction passes 43 focused checks; its compiled, native and
  package verification remain pending.

- [CHIM-FRAME-DEPENDENCY-OWNERSHIP-40](bugs/CHIM-FRAME-DEPENDENCY-OWNERSHIP-40.md):
  complete combined-world readback, split-model and sprite equivalence, and
  native boundary checks remain pending after the source repair.
- [CHIM-SEYDA-ACTOR-CONTACT-33](bugs/CHIM-SEYDA-ACTOR-CONTACT-33.md):
  final ground contact for Nels Llendo and a dreamer remains unresolved.
- [PLAYER-PUNCH-THIRDPERSON-39](bugs/PLAYER-PUNCH-THIRDPERSON-39.md) and
  [PLAYER-READY-MOVEMENT-39](bugs/PLAYER-READY-MOVEMENT-39.md):
  physical punching, damage, ready movement and gait need final-build verification.
- [COMBAT-BLOCKING-36](bugs/COMBAT-BLOCKING-36.md): blocking in both views remains open.
- [WATER-GAMEPLAY-PARITY-38](bugs/WATER-GAMEPLAY-PARITY-38.md): swimming and
  water interactions require normal-speed playtesting.
- [UI-INVENTORY-LAYOUT-40](bugs/UI-INVENTORY-LAYOUT-40.md): the complete appearance,
  equipment and inventory presentation remains unfinished.
- [PUBLIC-REFERENCE-SCREENSHOT-40](bugs/PUBLIC-REFERENCE-SCREENSHOT-40.md):
  current source selection is corrected; publication of that correction is pending.

## Validation and delivery

The exact release source completed 4,208 tests with 4,202 passes,
three Windows-only skips and three tracked Census expected failures. Those
results do not certify the later static-seam source repair. Its full suite,
Amiga build and Linux update validation are separate gates.

The complete world, exact fresh package readback and native gameplay/seam
verification are required before shipment. No new packaged ring coverage or
final shipment is claimed by this preparation checkpoint.

The source update preserves the published history and applies the complete
v0.0.39-to-v0.0.40 change set, including explicit deletions. The self-contained
Linux handoff includes the entry script, helpers, full and incremental source
archives, manifests and checksums. Public source contains no game data or
proprietary assets. See [release workflow](RELEASE_WORKFLOW.md) and
[roadmap](ROADMAP.md).

Ring3 is future v0.0.41-dev1 work after this delivery. Its 149-cell feasibility
review does not expand this release's rings 0-2 claim; see
[the roadmap](ROADMAP.md#v0041-dev1-ring3-feasibility-after-v0040-delivery).
