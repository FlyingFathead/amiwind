# AmiWind v0.0.39-dev1 - Cell By Cell, Piece By Piece

This source update continues from v0.0.38, preserving its CHIM selection,
lava work and completed-stage Tel Uvirith. It contains the first save-safety,
death-menu and exterior-build corrections for the next playtest. These are
candidate fixes: a complete dev1 image and targeted gameplay acceptance are
still pending.

## Changes

- The README CHIM map now uses the dated public reference. Audit milestones,
  native checks and package inclusion are shown separately; old release plans
  and stale lava counts are removed from the current guide.

- Autosaves wait for a settled, grounded and safe arrival after teleporting.
  Falling, lava, slime, loading, menus and combat defer the save and retain the
  previous checkpoint. Existing unsafe save files are not rewritten.
- The death-choice menu requests an untinted palette and retains the existing
  frozen background. The real character/save death prompt still needs a
  targeted native check; a diagnostic map-start death only reached the title
  menu and does not count as that acceptance.
- Before conversion, the builder inventories exterior cells and assigns BSP,
  regional CHIM or town ownership. The current selection skips 135 redundant
  town-owned BSP cores before terrain, scenery and flora conversion. Partial
  cores and required dependencies stay; interiors keep their own format.
- Final payload cleanup removes matching catalogues with retired maps. The
  save fingerprint now honours those explicit retirements while still failing
  on undeclared missing maps. Never-compiled exterior maps carry their
  verified ownership from the prebuild checklist into the final fingerprint;
  their CHIM owners remain bound to the save namespace. The world-disk packer
  receives that same validated omission list and rejects undeclared missing maps.
- Both emulator presets are included for dev1. The source is based on the
  published v0.0.38 commit, with the subsequent fixes retained.

## Known in this build

- [SAVE-TELEPORT-CHECKPOINT-38](../../bugs/SAVE-TELEPORT-CHECKPOINT-38.md): settled arrival saving is a candidate; target-native save/reload remains pending.
- [SAVE-LAVA-DEATH-LOOP-38](../../bugs/SAVE-LAVA-DEATH-LOOP-38.md): unsafe existing saves are not repaired automatically; native lava/fall coverage remains pending.
- [UI-DEATH-DAMAGE-TINT-38](../../bugs/UI-DEATH-DAMAGE-TINT-38.md): the actual death-choice prompt still needs visual acceptance.
- [BUILD-WORLD-FINGERPRINT-RETIRED-38](../../bugs/BUILD-WORLD-FINGERPRINT-RETIRED-38.md): the full image exposed a missing pruning/fingerprint integration case; corrected image verification remains pending.
- [BUILD-WORLD-PACK-RETIRED-38](../../bugs/BUILD-WORLD-PACK-RETIRED-38.md): the omission handoff into world-disk packing is corrected in source; affected tests and full-image readback remain pending.
- [BUILD-SHADOWED-WORLD-MAPS-38](../../bugs/BUILD-SHADOWED-WORLD-MAPS-38.md): the exterior plan is source-tested; final compact-image routing still needs verification.
- [PLAYER-TORCH-THIRDPERSON-38](../../bugs/PLAYER-TORCH-THIRDPERSON-38.md): carried torch and holding-pose repair remains open.
- [PLAYER-READY-THIRDPERSON-38](../../bugs/PLAYER-READY-THIRDPERSON-38.md): fists-up and weapon-draw animation remain open.
- [PLAYER-JUMP-THIRDPERSON-38](../../bugs/PLAYER-JUMP-THIRDPERSON-38.md): jump-animation repair remains open.
- [CHIM-COAST-OBJECTS-MISSING-36](../../bugs/CHIM-COAST-OBJECTS-MISSING-36.md): coast-object coverage and collision holds remain open.
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): converted geometry is separate from actors, original reference coverage and implemented gameplay.
- [ENGINE-SYNC-IO-MAIN-LOOP-36](../../bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): heavy loading, streaming and measured performance work continues.

The roadmap also retains water and swimming behavior, stairs and docks, combat
and speech, UI/help, the progress map and all exterior cells in rings 0, 1 and
2. This first update does not mark that backlog complete. Current statuses and
all reports remain in the [bug register](../../BUGS.md) and [roadmap](../../ROADMAP.md).
