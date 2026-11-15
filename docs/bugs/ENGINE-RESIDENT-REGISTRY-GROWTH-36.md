# ENGINE-RESIDENT-REGISTRY-GROWTH-36: Console commands, console variables and static name tables stay resident for the whole session, and nothing stopped them from growing

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 10 October 2026, in v0.0.36-dev3 |
| Where | engine/aga/src: Cmd_AddCommand (low hunk) and Cvar_RegisterVariable (zone) registrations |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.40-dev1 (last seen) |
| Severity | medium: Every registration costs memory for the whole session; unchecked growth eats heap a slow Amiga needs for the world |
| Family | Engine table limits (`engine-limits`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine fe2de50 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (found by reading the engine's resident memory tables, not while playing) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Status: 10 October 2026](#status-10-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Race-command registration recurrence, 14 October 2026](#race-command-registration-recurrence-14-october-2026)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 10 October 2026

Guarded in source: a ratchet test fails when any resident registry grows above its committed budget. The
registries themselves are unchanged; moving debug commands into the on-disk `dbg` catalogue is a memory-saving
candidate ([MEMORY_ALLOCATION.md](../MEMORY_ALLOCATION.md#memory-saving-candidates-for-the-next-round-10-october-2026)).

## Symptom

The 98 AmiWind console commands alone cost about 3 KiB of hunk for the whole session, and each new feature
tended to add a few more. Nothing measured the total or noticed it growing.

## Where

`engine/aga/src`: every `Cmd_AddCommand` puts a 12-byte `cmd_function_t` on the low hunk, rounded up to 16
bytes plus the 16-byte hunk header (32 bytes); every `Cvar_RegisterVariable` keeps its 24-byte `cvar_t` and a
zone copy of its value string (length + 1, the 24-byte block header and the 4-byte trash marker, rounded up to
8 bytes). Large static tables of names are in the binary for the whole session too.

## How it happened

Registering a command or a variable is the Quake way to add a console feature, and it is one line of code. The
cost is small per entry and was never added up.

## Why it was not caught

Memory checks measure maps, models and the world streamer; the engine's own registries are set up before any
map loads and had no budget.

## Reproduction

`python tools/resident_registry.py` on the v0.0.36 line: 266 console commands (8,512 bytes of hunk) and 321
console variables (7,704 bytes of structures and 10,496 bytes of zone), no static name table of 1 KiB or more.

## Repair

`tools/resident_registry.py` reads the engine sources the Makefile compiles (comments and `#if 0` blocks left
out, included `.inc` files and string macros resolved) and counts the registrations and their bytes.
`tests/test_resident_registry.py` compares them with `tests/resident_registry_budget.json`: above the budget it
fails and names the new entries, with the advice to route debug commands through the on-disk `dbg` catalogue
(`aw_console.c`, AWDC1) or to raise the budget in the same commit with the maintainer-approved, dated reason
(`--raise-budget`); below the budget it asks for the budget to be lowered (`--lower-budget`). The test also
checks that the engine structures still have the sizes the counts assume.

## Verification

The test passes on today's engine with the budget set to today's numbers; synthetic engines show that a new
command fails with its name, comments and disabled code are not counted, and lowering needs no reason.

## Prevention

The ratchet runs in every gate: the registries can only shrink unless the maintainer approves growth.

## Race-command registration recurrence, 14 October 2026

The complete v0.0.40-dev1 candidate gate rejects the new aw_set_playerrace
Cmd_AddCommand entry: 270 commands exceed the unchanged 269-command budget;
8,640 bytes exceed the unchanged 8,608-byte command hunk budget. The extra
registration costs 32 bytes for the session through AmiQuake's existing command
allocation path.

The complete gate runs 4,079 checks: 4,072 pass, one fails, no errors, three
Windows skips and three tracked expected failures. The failed assertion is
test_resident_registry.Budget.test_the_engine_fits_its_resident_registry_budget.
Functional race-command checks did not measure the resident registry; the full
ratchet correctly caught the growth before adoption.

This reopens the existing issue. Its earlier v0.0.36 fixed guard is historical
evidence, not acceptance of the new registration. The failed candidate and its
exact receipts remain preserved. The source correction now reuses the existing
on-demand AWDC1 dbg dispatcher, routing to aw_quickchar_set playerrace instead
of adding a resident command. The
269/8,608-byte budget is unchanged; source code and handler cost are not claimed
to be zero merely because a registration is removed.

Twenty focused checks pass, including the actual executable character and
console paths, generated command/help coverage and the unchanged resident
budget. The exact new target/full gate, native command behavior, packaging and
complete acceptance remain pending. The canonical recurrence remains open. This change does not affect CHIM coverage.

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
- CRASH-ANCESTRAL-TOMB-AUDIO-LOOP-65 (no report page): The game froze in an ancestral tomb (the one with a chandelier), with the sound stuck in a loop
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
- [ERICW-TEXINFO-SIGNED-31](ERICW-TEXINFO-SIGNED-31.md): ericw vis crashes and ericw light leaves faces unlit above texinfo 32,767
- [FLAMES-CAP-31](FLAMES-CAP-31.md): Static flames above 128 per map are silently dropped
- FLORA-ENTITY-001 (no report page): Dense vegetation exceeds the per-map entity reserve
- FLORA-RESERVE-002 (no report page): Two world flora maps exceed storage and clipnode reserves
- GEO-04 (no report page): Canonical-terrain world rebuild fails VIS (too many portals)
- [IMPORT-DOORBANK-LIMIT-32](IMPORT-DOORBANK-LIMIT-32.md): Town importer did not check the engine's 128-row door bank limit
- [INTERIOR-COORDS-31](INTERIOR-COORDS-31.md): Some interiors place objects beyond the +/-4096 coordinate range
- [INTERIOR-EXCLUDE-STALE-41](INTERIOR-EXCLUDE-STALE-41.md): Two Vivec rooms stayed left out on heap numbers from an older build
- [INTERIOR-INLINE-LIMIT-31](INTERIOR-INLINE-LIMIT-31.md): Every interior object is its own inline model: 220 objects per interior at most
- [LAMPS-CACHE-31](LAMPS-CACHE-31.md): Night lamps beyond 96 per 3x3 cells are silently dropped (Vivec)
- MAP-EXPLORED-ROOMS-CAP-66 (no report page): The explored map remembers at most 256 rooms: a room visited after the 256th never clears, so its local map stays dark with its doors hidden; the local map also searched every room name 256 times a frame
- MAP-EXPLORED-SAVE-BLOCK-66 (no report page): A well explored map can refuse the whole save: the explored land is written into the save's fixed 32 KB actor block with the dead counts, topics, spell effects and the other parts, and when its rows do not fit the save is refused
- [MODEL-MARKSURF-SIGNED-31](MODEL-MARKSURF-SIGNED-31.md): Face indices above 32,767 in leaf face lists become bad pointers
- [MODEL-SLOTS-256-32](MODEL-SLOTS-256-32.md): Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it
- MWVM-INSTANCES-256-66 (no report page): At most 256 scripted objects run per loaded map: a map with more leaves the rest without their scripts
- MWVM-PARKING-STORE-SMALL-66 (no report page): The store that keeps script values of unloaded maps holds 2,304 objects and 8,192 values: with the expansions the game has about 3,278 scripted objects with about 11,000 values
- [RENDER-SURFACE-OVERFLOW-SILENT-36](RENDER-SURFACE-OVERFLOW-SILENT-36.md): Faces past r_maxsurfs (12,288) or edges past r_maxedges (24,576) are dropped without a warning: Vivec views send up to 37,112 placement faces
- [RENDER-VISEDICTS-OVERFLOW-32](RENDER-VISEDICTS-OVERFLOW-32.md): Entities beyond MAX_VISEDICTS (1,112) are dropped silently
- SAVE-ACTOR-ROWS-256-66 (no report page): The save keeps at most 256 saved actor rows: at the 256th row the capture stops and the rest of that place's NPCs (their greetings, place and health) are left out of the save without a word; only NPCs were looked at
- TOWN-FLORA-BUDGET-004 (no report page): World 4 MiB file budget wrongly applied to town flora maps
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

<!-- END GENERATED CATEGORY -->
