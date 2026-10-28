# AmiWind v0.0.38-dev2 - Piece By Piece, Cell By Cell

Full playable development build using the current full-game recipe and valid cached assets. MiniWind remains a diagnostic tool and is not the scope of this playtest. Existing world and gameplay limitations remain; this is not a claim that every original cell or feature is complete.

## Candidate changes

- Restores full-game packaging scope: the existing world, supported towns and interiors, normal startup and NPC gallery, instead of the single-cell lava diagnostic.
- Includes the current CHIM recovery and startup audio memory-reserve changes.
- Reuses verified content through the hashed asset pool; changed stages must be rebuilt and validated.

## Known in this build

- [CHIM-FERN-NCO-SOLID-38](../../bugs/CHIM-FERN-NCO-SOLID-38.md): fire ferns marked nonsolid in the original can obstruct walking in mesh conversion. Repair pending.
- [CHIM-HULL-CHAIN-COST-33](../../bugs/CHIM-HULL-CHAIN-COST-33.md): six cell holds are not cleared by offline hull compilation alone.
- [CHIM-COAST-OBJECTS-MISSING-36](../../bugs/CHIM-COAST-OBJECTS-MISSING-36.md): coast object coverage remains incomplete.
- [CHIM-WINDOW-MOUNT-CROSS-CELL-33](../../bugs/CHIM-WINDOW-MOUNT-CROSS-CELL-33.md): four conversions need cross-cell window support.
- [ENGINE-SYNC-IO-MAIN-LOOP-36](../../bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md): nonblocking streaming and measured performance work remain on the roadmap.

Native validation and packaging receipts determine delivery status. The previous diagnostic build does not establish acceptance of this full-game package.
