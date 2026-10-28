# AmiWind v0.0.41-dev4: More Fixes

Development snapshot, 16 October 2026. Running on CHIM Engine v0.2.0. Previous snapshot:
[v0.0.41-dev3](RELEASE-v0.0.41-dev3.md).

This snapshot adds ring 4 of Vvardenfell to the CHIM world: 639 cells in all, with Seyda Neen, Balmora and the
whole city of Vivec. Vos, Sadrith Mora and one Azura's Coast cell beside it exceed the CHIM memory budget and stay
in the classic world for now.

## What changed since v0.0.41-dev3

- **Ring 4 on CHIM.** The cell list comes from the progress tracker's rings and keeps every cell already on CHIM
  (`tools/chim_cell_list.py`). Cells not ready yet stay in the classic world by name: those failing their audits or
  the CHIM memory budget, and the outer neighbours that keep them from being enclosed (`--open-pockets`), so that
  no classic cell is surrounded by CHIM cells.

## Known in this build

- [CHIM-VIVEC-FRAME-WIDE-41](../../bugs/CHIM-VIVEC-FRAME-WIDE-41.md): three residents at the edge of the Vivec frame may
  stand off the ground or out of reach; accepted for this private playtest only.
- [MESH-VIVEC-CAP-GAP-38](../../bugs/MESH-VIVEC-CAP-GAP-38.md): two banner-draped giant mushrooms at Vivec's entrance show
  open cap bands.
- [CHIM-STATICS-FALLBACK-41](../../bugs/CHIM-STATICS-FALLBACK-41.md): if a town frame's CHIM world cannot load, the map
  stops instead of running without its chunks.
- [BUILD-IDLE-STAGES-33](../../bugs/BUILD-IDLE-STAGES-33.md): early build stages still leave many cores idle.

See the [bug register](../../BUGS.md).
