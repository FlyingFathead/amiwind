# VIVEC-TEXINFO-31: dense Vivec canton regions exceed the 32,767 texture-mapping limit

## Status: 8 October 2026

Open. Repaired in source on the v0.0.32 Vivec fixes branch (8 October 2026);
not shipped.

## Symptom

Converting Vivec's exterior, 52 regions (mostly the Temple, St. Delyn, St. Olms
and the Foreign Quarter) stop with "Texture mapping budget exceeded".

## Where

`tools/prepare_mesh_bsp.py` (the texture mapping budget check) and the BSP29
face record, whose texinfo field is 16 bits wide.

## How it happened

Each face stores its texture mapping as a signed 16-bit index, so a map can
use 32,767 mappings. Vivec's canton meshes have thousands of triangles with
their own mappings; the converter already shares identical ones. The engine
reads the field signed and without a bounds check
(`engine/aga/src/model.c`, `Mod_LoadFaces`).

## Why it was not caught

No earlier converted area reached the limit.

## Reproduction

Convert Vivec's exterior frames with the town converter at Balmora's settings.

## Repair

- Engine: `Mod_LoadFaces` reads the face texinfo index unsigned, as face plane
  indices already were, and stops the load with "Face texinfo index outside
  texinfo lump" before forming a pointer when it is out of range. No memory
  cost. The Quake mechanism is unchanged: the same 16-bit BSP29 field, read
  with the full range.
- Converter: `tools/prepare_mesh_bsp.py` allows 65,536 mappings (indices up
  to 65,535). Every BSP face reader and writer in `tools/` (struct formats
  `'<HhihH4Bi'`, the shared `FORMATS` tables, the numpy face dtype in
  `analyze_subcell_redundancy.py`, `replace_bsp_world.py`'s combined limit) and
  the map inspector read the field unsigned.
- `qbsp` (ericw-tools v0.18.1) writes indices above 32,767 correctly (measured
  up to 36,060 on a synthetic map); `vis` and `light` of that release do not
  handle them ([ERICW-TEXINFO-SIGNED-31](ERICW-TEXINFO-SIGNED-31.md)). The
  converters run those two only before meshes are appended, so no map is
  affected.

## Verification

- Native fixture `tests/aga_face_texinfo_test.c`: indices 0, 32,767, 32,768,
  40,000 and 65,535 resolve to the right mapping; an index one past the lump
  stops the load before the surface gets a mapping, at counts 32,767, 32,768,
  40,000 and 65,535. Fails on the previous loader.
- `tests/test_surface_grid.py`: the tool readers accept 32,767, 32,768 and
  65,535 and reject an index one past the lump with a texinfo error.
- Vivec dry run with the repaired converter: all 32 exterior regions of the
  three Vivec frames that stopped on this limit now convert; the densest uses
  51,583 mappings (f02045, 79 % of the new limit). 18 of them then exceed the
  loader heap budget ([VIVEC-HEAP-31](VIVEC-HEAP-31.md)); none fails on
  mappings.
- Full Linux suite and warning-free engine build. In game: pending.

## Prevention

The converter reports texture mappings per map (`texinfo` in its result); the
planned builder limits check should report them per map too.
