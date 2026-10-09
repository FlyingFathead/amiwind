# MODEL-MARKSURF-SIGNED-31: face indices above 32,767 in leaf face lists become bad pointers

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Engine map loader (marksurfaces and leaf mark ranges) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Latent bad pointer above 32,767 faces; no shipped map reaches it yet. |
| Family | Engine table limits (`engine-limits`) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Engine table limits (`engine-limits`). Fixed engine tables (models, entities, faces, texinfo, flames, lamps, door rows) are checked by the builder before a map ships, never discovered in play. See [families](README.md#families).

- AW-20260928-16 (no report page): Two compiler-reported array bounds violations
- AW-20260929-02 (no report page): NPCs missing from expanded town render
- BALMORA-CAPACITY-005 (no report page): Bounded Balmora maps exceed the 600-entity limit
- EFRAG-01 (no report page): Static foliage leaf links exhausted ('Too many efrags!')
- [ENGINE-SUBMODEL-LIMIT-32](ENGINE-SUBMODEL-LIMIT-32.md): Map loading does not check the submodel count against MAX_MODELS
- ENTITY-DIAGNOSTIC-009 (no report page): Entity-exhaustion warning reports the high-water count as live slots
- [ENTITY-EXHAUSTION-007](ENTITY-EXHAUSTION-007.md): Entity slot exhaustion terminated the game with Sys_Error
- [ERICW-TEXINFO-SIGNED-31](ERICW-TEXINFO-SIGNED-31.md): ericw vis crashes and ericw light leaves faces unlit above texinfo 32,767
- [FLAMES-CAP-31](FLAMES-CAP-31.md): Static flames above 128 per map are silently dropped
- FLORA-ENTITY-001 (no report page): Dense vegetation exceeds the per-map entity reserve
- FLORA-RESERVE-002 (no report page): Two world flora maps exceed storage and clipnode reserves
- GEO-04 (no report page): Canonical-terrain world rebuild fails VIS (too many portals)
- [IMPORT-DOORBANK-LIMIT-32](IMPORT-DOORBANK-LIMIT-32.md): Town importer did not check the engine's 128-row door bank limit
- [INTERIOR-COORDS-31](INTERIOR-COORDS-31.md): Some interiors place objects beyond the +/-4096 coordinate range
- [INTERIOR-INLINE-LIMIT-31](INTERIOR-INLINE-LIMIT-31.md): Every interior object is its own inline model: 220 objects per interior at most
- [LAMPS-CACHE-31](LAMPS-CACHE-31.md): Night lamps beyond 96 per 3x3 cells are silently dropped (Vivec)
- [MODEL-SLOTS-256-32](MODEL-SLOTS-256-32.md): Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it
- [RENDER-VISEDICTS-OVERFLOW-32](RENDER-VISEDICTS-OVERFLOW-32.md): Entities beyond MAX_VISEDICTS (1,112) are dropped silently
- TOWN-FLORA-BUDGET-004 (no report page): World 4 MiB file budget wrongly applied to town flora maps
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

<!-- END GENERATED CATEGORY -->
