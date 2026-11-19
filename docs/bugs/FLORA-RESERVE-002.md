# FLORA-RESERVE-002: Two world flora maps exceed storage and clipnode reserves

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | unknown |
| Where | world flora maps vf0698 and vf0791 |
| Reproduction | always |
| Duplicate of | no |
| Persists in | unknown |
| Severity | medium: Two candidate maps exceed storage and clipnode reserves; a split passes. |
| Family | Engine table limits (`engine-limits`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-03: FLORA-RESERVE-002: two full-world rc1 flora candidates exceed reserves (part 1 of 2): Observed/version/reproduction: 3 October 2026, unreleased v0.0.28-rc1.
- 2026-10-03: FLORA-RESERVE-002: two full-world rc1 flora candidates exceed reserves (part 2 of 2): Correction candidate: retain the other 2,524 map IDs and subdivide each failed cell into four cores of 1,024 units, each with the same 896-unit apron.

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Engine table limits (`engine-limits`). Fixed engine tables (models, entities, faces, texinfo, flames, lamps, door rows) are checked by the builder before a map ships, never discovered in play. See [families](README.md#families).

- ALIAS-BUDGET-32MB-48 (no report page): The alias model budget is still the 16 MB era's 512 KiB: two NPCs fall back to standing-only animations
- [AW-20260928-16](AW-20260928-16.md): Two compiler-reported array bounds violations
- [AW-20260929-02](AW-20260929-02.md): NPCs missing from expanded town render
- [AW-CLIP-NOT-A-FIELD-54](AW-CLIP-NOT-A-FIELD-54.md): Every CHIM room and frame map load prints 'aw_clip' is not a field once per clip wall
- [BALMORA-CAPACITY-005](BALMORA-CAPACITY-005.md): Bounded Balmora maps exceed the 600-entity limit
- [BUILD-BUDGET-ENGINE-LIMITS-35](BUILD-BUDGET-ENGINE-LIMITS-35.md): Town entity and model budgets were not tied to the engine's per-map tables
- [BUILD-LEGACY-ENGINE-PATHS-48](BUILD-LEGACY-ENGINE-PATHS-48.md): The engine's legacy town region streaming was not marked or fenced as legacy
- [CHIM-ROOM-CLIPNODE-BUDGET-48](CHIM-ROOM-CLIPNODE-BUDGET-48.md): Akulakhan's Chamber cannot be made as a CHIM room: a model's collision exceeds the clipnode budget
- [CRASH-ANCESTRAL-TOMB-AUDIO-LOOP-65](CRASH-ANCESTRAL-TOMB-AUDIO-LOOP-65.md): The game froze in an ancestral tomb (the one with a chandelier), with the sound stuck in a loop
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
- [ENTITY-DIAGNOSTIC-009](ENTITY-DIAGNOSTIC-009.md): Entity-exhaustion warning reports the high-water count as live slots
- [ENTITY-EXHAUSTION-007](ENTITY-EXHAUSTION-007.md): Entity slot exhaustion terminated the game with Sys_Error
- [ERICW-TEXINFO-SIGNED-31](ERICW-TEXINFO-SIGNED-31.md): ericw vis crashes and ericw light leaves faces unlit above texinfo 32,767
- [FLAMES-CAP-31](FLAMES-CAP-31.md): Static flames above 128 per map are silently dropped
- [FLORA-ENTITY-001](FLORA-ENTITY-001.md): Dense vegetation exceeds the per-map entity reserve
- GEO-04 (no report page): Canonical-terrain world rebuild fails VIS (too many portals)
- [IMPORT-DOORBANK-LIMIT-32](IMPORT-DOORBANK-LIMIT-32.md): Town importer did not check the engine's 128-row door bank limit
- [INTERIOR-COORDS-31](INTERIOR-COORDS-31.md): Some interiors place objects beyond the +/-4096 coordinate range
- [INTERIOR-EXCLUDE-STALE-41](INTERIOR-EXCLUDE-STALE-41.md): Two Vivec rooms stayed left out on heap numbers from an older build
- [INTERIOR-INLINE-LIMIT-31](INTERIOR-INLINE-LIMIT-31.md): Every interior object is its own inline model: 220 objects per interior at most
- [LAMPS-CACHE-31](LAMPS-CACHE-31.md): Night lamps beyond 96 per 3x3 cells are silently dropped (Vivec)
- [MAP-EXPLORED-ROOMS-CAP-66](MAP-EXPLORED-ROOMS-CAP-66.md): The explored map remembers at most 256 rooms: a room visited after the 256th never clears, so its local map stays dark with its doors hidden; the local map also searched every room name 256 times a frame
- [MAP-EXPLORED-SAVE-BLOCK-66](MAP-EXPLORED-SAVE-BLOCK-66.md): A well explored map can refuse the whole save: the explored land is written into the save's fixed 32 KB actor block with the dead counts, topics, spell effects and the other parts, and when its rows do not fit the save is refused
- [MODEL-MARKSURF-SIGNED-31](MODEL-MARKSURF-SIGNED-31.md): Face indices above 32,767 in leaf face lists become bad pointers
- [MODEL-SLOTS-256-32](MODEL-SLOTS-256-32.md): Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it
- [MWVM-INSTANCES-256-66](MWVM-INSTANCES-256-66.md): At most 256 scripted objects run per loaded map: a map with more leaves the rest without their scripts
- [MWVM-PARKING-STORE-SMALL-66](MWVM-PARKING-STORE-SMALL-66.md): The store that keeps script values of unloaded maps holds 2,304 objects and 8,192 values: with the expansions the game has about 3,278 scripted objects with about 11,000 values
- [MWVM-PLACE-COPIES-FOUR-66](MWVM-PLACE-COPIES-FOUR-66.md): The script engine plans 4 live copies per scripted Place row in one map, and a fifth copy is refused
- [NET-VIVEC-ENTITY-PACKET-OVERFLOW-66](NET-VIVEC-ENTITY-PACKET-OVERFLOW-66.md): In Vivec the server's entity update overflows the client datagram every frame: packet overflow printed 1,938 times during one 45-second stay
- [RENDER-SURFACE-OVERFLOW-SILENT-36](RENDER-SURFACE-OVERFLOW-SILENT-36.md): Faces past r_maxsurfs (12,288) or edges past r_maxedges (24,576) are dropped without a warning: Vivec views send up to 37,112 placement faces
- [RENDER-VISEDICTS-OVERFLOW-32](RENDER-VISEDICTS-OVERFLOW-32.md): Entities beyond MAX_VISEDICTS (1,112) are dropped silently
- [SAVE-ACTOR-ROWS-256-66](SAVE-ACTOR-ROWS-256-66.md): The save keeps at most 256 saved actor rows: at the 256th row the capture stops and the rest of that place's NPCs (their greetings, place and health) are left out of the save without a word; only NPCs were looked at
- TOWN-FLORA-BUDGET-004 (no report page): World 4 MiB file budget wrongly applied to town flora maps
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

<!-- END GENERATED CATEGORY -->
