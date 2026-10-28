# INTERIOR-EXCLUDE-STALE-41: Two Vivec rooms stayed left out on heap numbers from an older build

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 16 October 2026, in v0.0.41 |
| Where | Vivec district configs (interiors exclude reasons) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.42 |
| Severity | medium: Telvanni Tower and St. Delyn Underworks fit every limit with the v0.0.41 converter but their doors showed them unavailable |
| Family | Engine table limits (`engine-limits`) |
| Playtest version | 2026_10_16_v0.0.41_release_ce7ace6 |
| From commit | source and engine ce7ace6 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Status: 16 October 2026

Fixed on the v0.0.42 line (the rooms are listed again; measured below). Present in v0.0.41.

## Symptom

Vivec, Telvanni Tower and Vivec, St. Delyn Underworks were left out of the whole-city Vivec build with
"heap ... over the 11,534,336 B budget after the optimizer" (141,380 and 964 bytes over), so their doors said
the interior was unavailable. Converted with the v0.0.41 converter and measured against the v0.0.41 release
image's own heap profiles, both fit: Telvanni Tower 213 inline models and 589,004 bytes of heap to spare,
St. Delyn Underworks 205 models and 302,268 bytes to spare.

## Where

The `exclude` reasons of the Vivec district configs (`config/vivec_*.json`, key `interiors`). Every other
excluded room was measured again the same way; the inline model counts matched the recorded ones exactly.

## How it happened

The reasons were written from a measurement of an earlier build. Later converter and heap estimate changes
lowered the two rooms' peaks, but an excluded room is never converted, so nothing measured it again.

## Why it was not caught

No check converts an excluded room to see whether its recorded reason still holds.

## Reproduction

Convert the room with the room converter (`prepare_area.build_room`), run the world map optimizer and the heap
estimate (`tools/check_world_map_heap.py`) with the image's recorded harvest and guard torch profiles; the
estimate for an included room of the same image (vdi000: 3,856,940 bytes to spare) matches the image's
own `world-map-heap.json` exactly.

## Repair

The two rooms are listed without an exclusion. The remaining exclusions carry the numbers measured on
16 October 2026 with the same method.

## Verification

Measured per room on the v0.0.41 release build's inputs; a Vivec interiors sandbox build boots them.

## Prevention

Every exclusion reason names the measured numbers and the date's method; a room's exclusion is measured again
whenever the converter changes (v0.0.42 plan 2.1).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Engine table limits (`engine-limits`). Fixed engine tables (models, entities, faces, texinfo, flames, lamps, door rows) are checked by the builder before a map ships, never discovered in play. See [families](README.md#families).

- ALIAS-BUDGET-32MB-48 (no report page): The alias model budget is still the 16 MB era's 512 KiB: two NPCs fall back to standing-only animations
- AW-20260928-16 (no report page): Two compiler-reported array bounds violations
- AW-20260929-02 (no report page): NPCs missing from expanded town render
- AW-CLIP-NOT-A-FIELD-54 (no report page): Every CHIM room and frame map load prints 'aw_clip' is not a field once per clip wall
- BALMORA-CAPACITY-005 (no report page): Bounded Balmora maps exceed the 600-entity limit
- [BUILD-BUDGET-ENGINE-LIMITS-35](BUILD-BUDGET-ENGINE-LIMITS-35.md): Town entity and model budgets were not tied to the engine's per-map tables
- BUILD-LEGACY-ENGINE-PATHS-48 (no report page): The engine's legacy town region streaming was not marked or fenced as legacy
- [CHIM-ROOM-CLIPNODE-BUDGET-48](CHIM-ROOM-CLIPNODE-BUDGET-48.md): Akulakhan's Chamber cannot be made as a CHIM room: a model's collision exceeds the clipnode budget
- EFRAG-01 (no report page): Static foliage leaf links exhausted ('Too many efrags!')
- [ENGINE-ENTITY-TEXT-UNBOUNDED-35](ENGINE-ENTITY-TEXT-UNBOUNDED-35.md): Entity and QuakeC text was copied into fixed buffers without a bound
- [ENGINE-FATAL-PATH-SWEEP-35](ENGINE-FATAL-PATH-SWEEP-35.md): Sweep of every engine fatal path that data or a player can reach
- [ENGINE-FILEBASE-UNBOUNDED-35](ENGINE-FILEBASE-UNBOUNDED-35.md): COM_FileBase copied a name of any length into a 32-byte buffer and walked before the start of a name without a slash
- [ENGINE-LEAF-LIMIT-UNCHECKED-35](ENGINE-LEAF-LIMIT-UNCHECKED-35.md): A map with more leaves than MAX_MAP_LEAFS overflowed the PVS buffers silently
- [ENGINE-MODEL-NAME-SYSERROR-35](ENGINE-MODEL-NAME-SYSERROR-35.md): Model names of any length went into 64-byte model slots, and a missing model file stopped the program
- [ENGINE-RESIDENT-REGISTRY-GROWTH-36](ENGINE-RESIDENT-REGISTRY-GROWTH-36.md): Console commands, console variables and static name tables stay resident for the whole session, and nothing stopped them from growing
- [ENGINE-SUBMODEL-LIMIT-32](ENGINE-SUBMODEL-LIMIT-32.md): Map loading does not check the submodel count against MAX_MODELS
- [ENGINE-UDP-ADDRESS-OVERFLOW-35](ENGINE-UDP-ADDRESS-OVERFLOW-35.md): A typed network connect address longer than 254 characters overflowed a stack buffer
- [ENGINE-VA-UNBOUNDED-35](ENGINE-VA-UNBOUNDED-35.md): va() formatted into its 1 KiB buffer without a bound
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
- [MODEL-MARKSURF-SIGNED-31](MODEL-MARKSURF-SIGNED-31.md): Face indices above 32,767 in leaf face lists become bad pointers
- [MODEL-SLOTS-256-32](MODEL-SLOTS-256-32.md): Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it
- [RENDER-SURFACE-OVERFLOW-SILENT-36](RENDER-SURFACE-OVERFLOW-SILENT-36.md): Faces past r_maxsurfs (12,288) or edges past r_maxedges (24,576) are dropped without a warning: Vivec views send up to 37,112 placement faces
- [RENDER-VISEDICTS-OVERFLOW-32](RENDER-VISEDICTS-OVERFLOW-32.md): Entities beyond MAX_VISEDICTS (1,112) are dropped silently
- TOWN-FLORA-BUDGET-004 (no report page): World 4 MiB file budget wrongly applied to town flora maps
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

Related bugs in other categories:

- [VIVEC-ROOM-PRECACHE-LIMIT-42](VIVEC-ROOM-PRECACHE-LIMIT-42.md): Telvanni Tower was listed again although its map needs 257 model precaches; the engine holds 256

<!-- END GENERATED CATEGORY -->
