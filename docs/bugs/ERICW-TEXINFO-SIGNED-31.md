# ERICW-TEXINFO-SIGNED-31: ericw vis crashes and ericw light skips faces above texinfo 32,767

## Status: 8 October 2026

Open. Found while checking the unsigned texinfo change (VIVEC-TEXINFO-31);
no shipped or converted map is affected today.

## Symptom

On a BSP29 map whose faces use texture mappings (texinfo) above index 32,767:

- `vis` (ericw-tools v0.18.1, the version the builder ships) stops with a
  segmentation fault after computing the visibility data.
- `light` (same release) finishes without error but leaves every face whose
  texinfo index is above 32,767 without a lightmap.

`qbsp` (same release) writes such maps correctly: indices 32,768 and up are
stored as unsigned 16-bit values and match the texinfo lump.

## Where

The ericw-tools v0.18.1 binaries in the builder image (`vis`, `light`); not
AmiWind source. Unaffected: `qbsp`, the engine (reads the field unsigned since
VIVEC-TEXINFO-31), and every AmiWind converter step, which runs `vis` and
`light` only on the terrain or room shell before the converted meshes (and
their texture mappings) are appended.

## How it happened

BSP29 stores the face texinfo index in 16 bits. ericw's tools read it as a
signed value, as stock Quake did, so an index above 32,767 becomes negative.
AmiWind now uses the full unsigned range.

## Why it was not caught

No map reached 32,768 texture mappings, and the converters never run `vis` or
`light` on maps with converted meshes.

## Reproduction

Synthetic, asset-free map: rows of small floating brushes, each face with its
own texture offsets, compiled with `qbsp`, then `vis -fast` and `light`
(probe script kept with the private measurement receipts). Results, same map
generator:

| Brush count | texinfo | Faces above 32,767 | qbsp | vis -fast | light |
| ---: | ---: | ---: | --- | --- | --- |
| 8,150 | 32,657 | 0 | ok | ok | ok (16,678 faces lit) |
| 8,250 | 33,057 | 289 | ok | segmentation fault | ok, but 0 of the 289 faces lit (859 of 1,768 lit just below the limit) |
| 9,000 | 36,061 | 3,293 | ok | segmentation fault | not run |

## Repair

None needed for the current pipeline. Any future step that runs `vis` or
`light` on a map with converted meshes (for example building faces moved into
the world model, TOWN-VIS-OCCLUSION-31) must keep that map below 32,768
texture mappings or use a fixed tool. Documented in the limits table of
[the release workflow](../RELEASE_WORKFLOW.md).

## Verification

Measured as above, in an offline throwaway container of the builder image.

## Prevention

The planned builder limits check should refuse to run `vis` or `light` on a
map with more than 32,767 texture mappings.
