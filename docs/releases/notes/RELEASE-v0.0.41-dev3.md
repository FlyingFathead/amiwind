# AmiWind v0.0.41-dev3: More Fixes

Development snapshot, 16 October 2026. Running on CHIM Engine v0.2.0. Previous snapshot:
[v0.0.41-dev2](RELEASE-v0.0.41-dev2.md).

This snapshot adds ring 3 of Vvardenfell to the CHIM world: 513 cells in all, with Seyda Neen, Balmora and the
whole city of Vivec. Seven ring 3 cells stay in the classic world for now: three fail their audits, three Bitter
Coast cells near Hla Oad exceed the CHIM memory budget, and one is left out so that no classic cell is enclosed.

## What changed since v0.0.41-dev1

- **Ring 3 on CHIM.** The cell list comes from the progress tracker's rings and keeps every cell already on CHIM
  (`tools/chim_cell_list.py`): rings 1 to 3, the ring-0 sea cells and the inland lava cells converted earlier.
- **Lava regions within the storage budget.** Two more lava terrain regions are split, and the scenery stage now
  names every over-budget region in one pass ([BUILD-LAVA-TERRAIN-BUDGET-38](../../bugs/BUILD-LAVA-TERRAIN-BUDGET-38.md)).
- **Seyda Neen's giant mushrooms.** The cell-aligned Seyda Neen frame keeps its giant mushrooms, with closed seams.
- **Streamed statics.** The builder checks a town frame's streamed statics against the engine's streamed list, as
  the engine stores them ([CHIM-STATICS-FALLBACK-41](../../bugs/CHIM-STATICS-FALLBACK-41.md)).
- **The Guard marker** is back at the lower right; `dbg landfill on/off` switches the distant land layer.

## Known in this build

- [CHIM-VIVEC-FRAME-WIDE-41](../../bugs/CHIM-VIVEC-FRAME-WIDE-41.md): three residents at the edge of the Vivec frame may
  stand off the ground or out of reach; accepted for this private playtest only.
- [MESH-VIVEC-CAP-GAP-38](../../bugs/MESH-VIVEC-CAP-GAP-38.md): two banner-draped giant mushrooms at Vivec's entrance show
  open cap bands.
- [CHIM-STATICS-FALLBACK-41](../../bugs/CHIM-STATICS-FALLBACK-41.md): if a town frame's CHIM world cannot load, the map
  stops instead of running without its chunks.
- [BUILD-IDLE-STAGES-33](../../bugs/BUILD-IDLE-STAGES-33.md): early build stages still leave many cores idle.

See the [bug register](../../BUGS.md).
