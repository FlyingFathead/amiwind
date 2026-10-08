# LIGHTMAP-TAIL-31: the last face's lightmap points past the end of the lighting lump

## Status: 8 October 2026

Open. Cause found; repaired in source on the v0.0.32 Vivec fixes branch; not
shipped.

## Symptom

The map optimizer rejects some converted interiors with "Light sample range
outside lump": the room's last face needs more lightmap bytes than remain in
the lighting lump (St. Delyn Storage: offset 358,820 needs 84 bytes, 65 left).

## Where

The mesh converter's lightmap bake (`tools/prepare_mesh_bsp.py`,
`tools/interior_lighting.py` `bake_surface`), against the engine's
`CalcSurfaceExtents` (`engine/aga/src/model.c`). It is the visible end of
[LIGHTMAP-GRID-31](LIGHTMAP-GRID-31.md).

## How it happened

1. The bake sized each face's lightmap from the face's texture coordinates
   in double precision, before the vertices and texture axes were written to
   the map as single precision (and before shared vertices and mappings
   within 1e-5 were merged).
2. Imported texture coordinates often end exactly on a 16-texel line. After
   storage they sit a few millionths of a texel to either side. In St. Delyn
   Storage's last face the stored ends are -0.000023 and 192.00006 (bake: 0
   and 192), so the engine allocates 6 x 14 = 84 samples where the bake wrote
   5 x 13 = 65.
3. Every such face reads into the next face's samples; only the last face of
   the lump runs off its end, which the optimizer catches. In St. Delyn Storage
   3,379 of 29,874 converted faces had a shorter lightmap than the engine
   needs (engine rule; EXTENTS-FPU-RULE-31 describes why the rule itself also
   differed between FPUs).

## Why it was not caught

The bake's own comment noted a pending precision correction; only the last
face of a lump is range-checked, and the shipped interiors' last faces
happened to fit.

## Reproduction

Convert Vivec, St. Delyn Storage and run the map optimizer; or recompute each
face's engine grid from the stored values and compare it with the bytes up to
the next face's offset.

## Repair

The converter computes each face's lightmap grid after writing the face, from
the stored single-precision vertices and texture mapping, by the engine rule
(`tools/surface_grid.py`), and rebakes the face on that grid when it differs
from the bake's. It then rejects a face whose sample count differs from the
engine's.

## Verification

- `tests/test_surface_grid.py`: a lit face whose ends drift outward on storage
  is baked on the engine's 13 x 3 grid (the old bake wrote 11 x 3).
- Vivec dry run with the repaired converter (146 interiors, 192 exterior
  regions): all 7 rooms that failed this way (Dralor Manor, Hall of Wisdom,
  Hlaalu Prison Cells, St. Delyn Storage, Telvanni Vault, Mevel Fererus:
  Trader, Abbey of St. Delyn) pass the optimizer; every map as converted has
  0 faces whose engine-rule lightmap runs into the next face, and every
  optimized map passes the engine-rule light range check.
- Full Linux suite and warning-free engine build. In game: pending.

## Prevention

The converter checks every face's sample count against the engine grid; the
optimizer's oracle checks every face's range by the engine rule.
