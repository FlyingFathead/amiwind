# VIVEC-HEAP-31: dense Vivec maps exceed the loader heap budget once mappings and extents no longer stop them

## Status: 8 October 2026

Open. Measured in the Vivec dry run with the repaired converter; nothing
shipped.

## Symptom

With VIVEC-TEXINFO-31, MESH-EXTENT-GRID-31 and LIGHTMAP-TAIL-31 repaired, the
next limit in Vivec is the engine's loader heap (budget 11,534,336 bytes,
estimated by `tools/check_world_map_heap.py` after the map optimizer):

- 18 of the 192 exterior regions of the three Vivec frames are over, by
  89,460 to 3,202,244 bytes. All 18 are regions that stopped on texture
  mappings before: the Temple and Ministry area (cells 3,-13 / 3,-12 /
  4,-13 / 4,-12, 11 regions) and cells 6,-10 / 6,-9 / 7,-10 (7 regions, which
  are also over 220 inline models).
- 4 of the 146 interiors are over: St. Delyn Underworks +964 bytes, Telvanni
  Tower +141,380, Telvanni Plaza +144,452 (also 267 inline models), Hlaalu
  Underworks +769,028 (also 225 inline models).

## Where

Map size against the engine's heap: decoded faces, their staged copy during
loading, planes and texture mappings dominate (see the Vivec sections study:
faces and their staged copy are 53-55 % of the loader peak).

## How it happened

Vivec's canton and Temple meshes are dense, and the regions use Balmora's
layout (768-unit cores, 896 overlap, draw distance 540).

## Why it was not caught

Earlier limits stopped these maps first.

## Reproduction

Convert Vivec's frames centred on cells 3,-10 / 3,-13 / 6,-10 and its
interiors with the town and interior converters at Balmora's settings, run the
map optimizer and the heap check.

## Repair

Not done. Measured options from the earlier sweep and sections study: finer
region cores (384), a shorter draw distance (360, a visible change and owner
decision), interior sections at real doors, 32-pixel textures on props, and
sprite flora. Each needs a rerun of this measurement.

## Verification

Pending.

## Prevention

The builder's heap gate already rejects such maps; the planned limits check
reports every limit per map.
