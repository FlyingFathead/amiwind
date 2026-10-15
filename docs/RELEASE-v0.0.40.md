# AmiWind v0.0.40: Rings 0, 1 and 2 of Vvardenfell in Full CHIM

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
  across repeated frame dependencies. The repaired combined world is being checked.
- Gameplay changes address held attacks, blocking, original opening HUD timing,
  inventory layout and character previews, and rotating-limb animation offsets.
  Their complete native acceptance remains pending.
- The README includes original AmiWind dev1 photographs of two ring-2 shipwreck
  exteriors. Their build and free-camera scope are labelled. Original-game
  reference screenshots are excluded from public source.

## Known in this build

The [bug register](BUGS.md#fix-index) is the current status authority.
These open checks prevent final package acceptance:

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

The preceding ownership source completed 4,207 tests with 4,201 passes,
three Windows-only skips and three tracked Census expected failures. Those
results do not certify this new final-version source tree. Its full suite,
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
