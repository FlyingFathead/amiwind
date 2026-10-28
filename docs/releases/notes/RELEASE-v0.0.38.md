# AmiWind v0.0.38 - Lava Is All You Need (And A Hint Of Tel Uvirith)

v0.0.38 restores exterior lava and expands the playable CHIM world, including
completed-stage Tel Uvirith in cell (10,1). It keeps the full game's normal
startup and supported towns and interiors. The public source release is
published; the refreshed private playtest image is still under validation.

## Lava and Tel Uvirith

Lava conversion preserves the original pool elevation and the surrounding
LAND detail. Both legacy BSP and CHIM conversion paths are supported. The
full-world conversion accounts for 349 original lava references in 27 exterior
cells. Scoped native runs observed lava shorelines and contact damage; matched
original comparisons, sound and wider traversal remain incomplete. See
[lava coverage](../../bugs/BUILD-LAVA-COVERAGE-38.md) and
[lava terrain budgets](../../bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md).

Tel Uvirith uses the selected completed stronghold stage, optimized geometry
and sprite details. The preceding full image passed sprite readback and native
arrival checks. Modeled active/load rings were 5,596,320 / 5,767,824 bytes
against a 6,242,304-byte budget. Those estimates do not establish smooth
traversal or complete collision coverage. Normal staircase traversal remains
open ([memory](../../bugs/CHIM-MOLAG-MEMORY-38.md),
[stairs](../../bugs/STAIRS-MOLAG-ACCESS-38.md)).

## Exterior CHIM coverage and compact images

The preceding full image has readback evidence for 360 whole regional CHIM
exterior cells. Six partially overlapping town cells are counted separately;
they do not increase that whole-cell count. These are packaged geometry counts,
not complete original-reference coverage, native checks of every cell, or
implemented actors and gameplay.

The refreshed builder preserves that CHIM selection. Its prebuild ownership
checklist excludes 135 redundant town-owned BSP map cores before terrain,
scenery and flora conversion. The same verified omissions now reach content
fingerprinting and world-disk packing. Required map dependencies and interiors
remain. Full-image assembly, readback and routing checks for this correction
are still pending; planned removal is not a measured final-image saving.

## Other changes

- Original nonsolid mesh markers, including fire ferns, are preserved. Empty
  point hulls get an explicit empty node. Scoped checks pass; other collision
  holds remain open.
- Quick-character audio scratch is counted in CHIM memory budgets, and debug
  recovery uses checked arrival placement.
- Third-person and vanity camera availability respects opening permissions.
- LAND fill has a saved control independent of fog. Noclip bob and roll default
  off, with saved controls; photo mode restores the previous bob setting.
- The Toolkit adds a map-name toggle, resizable map view and inspection copy.
- Opt-in terrain-aware render clipping and MiniWind inspection remain
  development tools; they do not establish full-world enablement or acceptance.

## Known in this build

- [SAVE-LAVA-DEATH-LOOP-38](../../bugs/SAVE-LAVA-DEATH-LOOP-38.md): a lava fall can leave an unsafe autosave; existing unsafe saves are not automatically repaired.
- [SAVE-TELEPORT-CHECKPOINT-38](../../bugs/SAVE-TELEPORT-CHECKPOINT-38.md): safe destination saving needs target-native verification.
- [UI-DEATH-DAMAGE-TINT-38](../../bugs/UI-DEATH-DAMAGE-TINT-38.md): lava damage tint can colour the death prompt.
- [PLAYER-TORCH-THIRDPERSON-38](../../bugs/PLAYER-TORCH-THIRDPERSON-38.md): the carried torch and pose can disappear while its light remains.
- [PLAYER-READY-THIRDPERSON-38](../../bugs/PLAYER-READY-THIRDPERSON-38.md): fists-up and weapon-draw animation are missing.
- [PLAYER-JUMP-THIRDPERSON-38](../../bugs/PLAYER-JUMP-THIRDPERSON-38.md): jump animation needs repair.
- [WATER-GAMEPLAY-PARITY-38](../../bugs/WATER-GAMEPLAY-PARITY-38.md): swimming and surface behavior need comparison with the original.
- [STAIRS-MOLAG-ACCESS-38](../../bugs/STAIRS-MOLAG-ACCESS-38.md): walkway and door stairs need normal-walking checks and repair.
- [CHIM-COAST-OBJECTS-MISSING-36](../../bugs/CHIM-COAST-OBJECTS-MISSING-36.md): original-reference and packaged coast coverage are incomplete.
- [CHIM-CELL-FEATURE-LIST-INCOMPLETE-38](../../bugs/CHIM-CELL-FEATURE-LIST-INCOMPLETE-38.md): converted geometry is separate from complete actors and gameplay.
- [COMBAT-AMBIENT-SPEECH-GATING-38](../../bugs/COMBAT-AMBIENT-SPEECH-GATING-38.md): ambient greetings and subtitles can interrupt combat.
- [ENGINE-SYNC-IO-MAIN-LOOP-36](../../bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): loading and streaming can stall play; measured performance work remains open.

## Next playtest and validation

Lava falls can leave unsafe autosaves, teleport checkpoints need verification,
and the damage tint can colour the death prompt. Candidate repairs are being
tested for v0.0.39-dev1, **Cell By Cell, Piece By Piece**; they are not v0.0.38
fixes. Third-person torch/readied/jump animations, swimming, combat speech,
stairs, coast-object coverage and loading/streaming performance also remain in
the [bug register](../../BUGS.md) and [roadmap](../../ROADMAP.md).

The prior image's native observations and HUD/crosshair-off lava captures are
preserved as evidence. They do not pass the refreshed image's remaining gates:
complete HDF readback, map exclusivity, town-boundary routing, exact-package
native smoke and verified delivery. The completed public release and its Linux
publishing kit remain separate from this pending private-image correction.

Full-game describes package scope. It does not mean every original feature or
exterior cell is complete.
