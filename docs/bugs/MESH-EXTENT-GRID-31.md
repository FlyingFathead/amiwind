# MESH-EXTENT-GRID-31: grid-exact mesh faces exceed the 256-texel surface limit on the 68040

## Status: 8 October 2026

Open. Repaired in source on the v0.0.32 Vivec fixes branch (8 October 2026);
not shipped.

## Symptom

Thirteen converted Vivec interiors (every Underworks and Puzzle Canal levels 1-5)
stop the engine while loading with a bad surface extents error; the map
optimizer rejects them.

## Where

`tools/mesh_geometry.py` `split_surface` (converter) and the 256-texel surface
check in `engine/aga/src/model.c` (`CalcSurfaceExtents`).

## How it happened

Quake's software renderer limits every surface to 256 texels across. The
converter splits large faces to stay under it, but its check rounds to the
16-texel grid. One polygon of `meshes/i/in_sewer_bcorr3_00.nif` spans exactly
240 texels with both ends on grid lines (240 <= 240 passes). Placing the mesh
and storing it as 32-bit floats moves the ends by about 0.003 texel; the
68040's wider intermediate precision then rounds each end outward by one
16-texel block, giving 272 > 256. A plain 32-bit check gives 256, which is why
the converter's own check passed.

## Why it was not caught

The converter checks extents with host floating point, not the target's
rounding; no earlier map had a face sitting exactly on the grid at the limit.

## Reproduction

Convert any Vivec Underworks interior with the current converter and load it
on the target, or run the map optimizer on it.

## Repair

- `tools/mesh_geometry.py` `split_surface` widens each span by 1/16 texel
  (`surface_grid.GRID_GUARD`) before rounding to the grid, so a span ending
  exactly on grid lines at the limit is split; a kept piece stays within 240
  texels whatever the rounding.
- The mesh converter checks every converted face's extents from the stored
  single-precision values under three rules: the engine's (double precision
  after every step, [EXTENTS-FPU-RULE-31](EXTENTS-FPU-RULE-31.md)), single
  precision after every step (GCC's `fsmul`/`fsadd`), and 68040 extended
  intermediates kept unrounded; any extent above 256 stops the conversion
  with the face named (`tools/surface_grid.py` `check_lumps`).
- Correction to the cause above: the compiled engine rounds every step to
  single precision on a real 68040 (256 for this face); the 272-texel stop
  matches the wider arithmetic of the emulator. The engine now uses one
  rule on every FPU.

## Verification

- `tests/test_surface_grid.py`: a synthetic 240-texel span with grid-exact
  ends that grows to 272 texels once stored; the old check keeps it whole,
  the guarded split cuts it into pieces of at most 240 texels under all three
  rules, and the converter check rejects the unsplit face.
- Vivec dry run with the repaired converter: all 13 maps that failed this way
  (Arena, Foreign Quarter, Hall, Hlaalu, Redoran, St. Delyn, St. Olms and
  Telvanni Underworks, Puzzle Canal levels 1-5) pass the map optimizer; the
  largest extent in all 338 converted maps is 240 texels. The other sewer maps
  outside Vivec (Falasmaryon, Hlormaren, Kogoruhn, Molag Mar) were not rerun.
- Full Linux suite and warning-free engine build. In game: pending.

## Prevention

The converter's three-rule extent check on every converted face.
