# MODEL-MARKSURF-SIGNED-31: face indices above 32,767 in leaf face lists become bad pointers

## Status: 8 October 2026

Open. Found by the building visibility prototype; latent (no shipped map has
more than 32,767 faces yet; bm019 has 31,022). Repaired in source on the
v0.0.32 Vivec fixes branch (8 October 2026); not shipped.

## Symptom

A map whose leaf face list references a face above index 32,767 would make the
engine read a negative index and form a pointer before the face array. The
later edge-cache pass (`AW_InitEdgeCache`) rejects a negative mark, so the
load would stop with "Invalid mark edge cache range" rather than run on;
leaf mark ranges (`firstmarksurface`) above 32,767 had no check at all.

## Where

`engine/aga/src/model.c`: `Mod_LoadMarksurfaces` (each entry) and
`Mod_LoadLeafs` (`firstmarksurface`, `nummarksurfaces`). Audited and correct
already: face plane indices and edge vertex indices (unsigned), node face
ranges (unsigned, range-checked in `AW_ValidateDiskNodes`), node children
(signed by design: negative means a leaf), clipnode children (AmiWind's
unsigned decoder). The tools read marksurfaces and leaf/node face fields
unsigned already (`'<H'`, `'<ii6h2H4B'`, `'<i2h6h2H'`).

## How it happened

The loader reads each entry as a signed 16-bit value and only checks the upper
bound, as the original Quake loader did; the leaf loader reads the leaf's
first mark and count signed and checks neither.

## Why it was not caught

No map came close to the limit until the Vivec and world-face measurements.

## Reproduction

Load a map with more than 32,768 faces whose leaves reference high face numbers.

## Repair

With [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): marksurface entries and leaf
mark ranges are read unsigned and checked against the face and mark counts
before any pointer is formed; node face ranges are read explicitly
unsigned.

## Verification

Native fixture `tests/aga_marksurface_index_test.c` (run by
`test_aga_native_source`): entries 0, 32,767, 32,768, 40,000 and 65,535
resolve to the right faces; an entry one past the face count stops the load
before the pointer is set, at counts 32,767, 32,768, 40,000 and 65,535; leaf
ranges starting at 32,767, 32,768 and 39,999 load; ranges one mark past the
list stop the load. The fixture fails on the previous loader. Full Linux
suite and warning-free engine build passed. Target hardware: pending.

## Prevention

Loader tests with indices above 32,767; the planned builder limits check.
