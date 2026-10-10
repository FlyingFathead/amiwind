# ERICW-TEXINFO-SIGNED-31: ericw vis crashes and ericw light skips faces above texinfo 32,767

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | ericw-tools vis and light (external tools) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31 (last seen) |
| Severity | low: vis crashes and light skips faces above texinfo 32767; no current map is affected. |
| Family | Engine table limits (`engine-limits`) |
| Playtest version | v0.0.31 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Engine table limits (`engine-limits`). Fixed engine tables (models, entities, faces, texinfo, flames, lamps, door rows) are checked by the builder before a map ships, never discovered in play. See [families](README.md#families).

- AW-20260928-16 (no report page): Two compiler-reported array bounds violations
- AW-20260929-02 (no report page): NPCs missing from expanded town render
- BALMORA-CAPACITY-005 (no report page): Bounded Balmora maps exceed the 600-entity limit
- [BUILD-BUDGET-ENGINE-LIMITS-35](BUILD-BUDGET-ENGINE-LIMITS-35.md): Town entity and model budgets were not tied to the engine's per-map tables
- EFRAG-01 (no report page): Static foliage leaf links exhausted ('Too many efrags!')
- [ENGINE-ENTITY-TEXT-UNBOUNDED-35](ENGINE-ENTITY-TEXT-UNBOUNDED-35.md): Entity and QuakeC text was copied into fixed buffers without a bound
- [ENGINE-FATAL-PATH-SWEEP-35](ENGINE-FATAL-PATH-SWEEP-35.md): Sweep of every engine fatal path that data or a player can reach
- [ENGINE-FILEBASE-UNBOUNDED-35](ENGINE-FILEBASE-UNBOUNDED-35.md): COM_FileBase copied a name of any length into a 32-byte buffer and walked before the start of a name without a slash
- [ENGINE-LEAF-LIMIT-UNCHECKED-35](ENGINE-LEAF-LIMIT-UNCHECKED-35.md): A map with more leaves than MAX_MAP_LEAFS overflowed the PVS buffers silently
- [ENGINE-MODEL-NAME-SYSERROR-35](ENGINE-MODEL-NAME-SYSERROR-35.md): Model names of any length went into 64-byte model slots, and a missing model file stopped the program
- [ENGINE-SUBMODEL-LIMIT-32](ENGINE-SUBMODEL-LIMIT-32.md): Map loading does not check the submodel count against MAX_MODELS
- [ENGINE-UDP-ADDRESS-OVERFLOW-35](ENGINE-UDP-ADDRESS-OVERFLOW-35.md): A typed network connect address longer than 254 characters overflowed a stack buffer
- [ENGINE-VA-UNBOUNDED-35](ENGINE-VA-UNBOUNDED-35.md): va() formatted into its 1 KiB buffer without a bound
- ENTITY-DIAGNOSTIC-009 (no report page): Entity-exhaustion warning reports the high-water count as live slots
- [ENTITY-EXHAUSTION-007](ENTITY-EXHAUSTION-007.md): Entity slot exhaustion terminated the game with Sys_Error
- [FLAMES-CAP-31](FLAMES-CAP-31.md): Static flames above 128 per map are silently dropped
- FLORA-ENTITY-001 (no report page): Dense vegetation exceeds the per-map entity reserve
- FLORA-RESERVE-002 (no report page): Two world flora maps exceed storage and clipnode reserves
- GEO-04 (no report page): Canonical-terrain world rebuild fails VIS (too many portals)
- [IMPORT-DOORBANK-LIMIT-32](IMPORT-DOORBANK-LIMIT-32.md): Town importer did not check the engine's 128-row door bank limit
- [INTERIOR-COORDS-31](INTERIOR-COORDS-31.md): Some interiors place objects beyond the +/-4096 coordinate range
- [INTERIOR-INLINE-LIMIT-31](INTERIOR-INLINE-LIMIT-31.md): Every interior object is its own inline model: 220 objects per interior at most
- [LAMPS-CACHE-31](LAMPS-CACHE-31.md): Night lamps beyond 96 per 3x3 cells are silently dropped (Vivec)
- [MODEL-MARKSURF-SIGNED-31](MODEL-MARKSURF-SIGNED-31.md): Face indices above 32,767 in leaf face lists become bad pointers
- [MODEL-SLOTS-256-32](MODEL-SLOTS-256-32.md): Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it
- [RENDER-VISEDICTS-OVERFLOW-32](RENDER-VISEDICTS-OVERFLOW-32.md): Entities beyond MAX_VISEDICTS (1,112) are dropped silently
- TOWN-FLORA-BUDGET-004 (no report page): World 4 MiB file budget wrongly applied to town flora maps
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

<!-- END GENERATED CATEGORY -->
