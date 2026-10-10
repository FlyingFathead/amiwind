# ENGINE-FATAL-PATH-SWEEP-35: Sweep of every engine fatal path that data or a player can reach

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | engine/aga/src (Sys_Error, Host_Error, PR_RunError, allocation failures, unbounded copies) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | medium: Tracks the reachable crash paths; the left items are listed with a reason |
| Family | Engine table limits (`engine-limits`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 6dcb10e |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

The record of the sweep. The paths that shipped data or a player can reach are fixed in source on
v0.0.35-crash-fixes-2 (not shipped at the time of writing), each under its own ID. The paths left are listed
below with the reason.

## Symptom

A review of the engine (v0.0.35 coherence audit) asked which fatal errors data or a player can reach. In this
engine `Sys_Error` stops the program; `Host_Error` ends the session and returns to the console; a QuakeC run
error (`PR_RunError`) is a Host_Error. A Host_Error still becomes a crash when it is entered again while the
first is handled, on a dedicated server, before the first host frame, or when the code it jumps out of held
resources that the next map load checks (CHIM-STATIC-PLACE-HOST-ERROR-35).

## Where

`engine/aga/src`: every `Sys_Error`, `Host_Error` and `PR_RunError` (391 lines), the Hunk, Cache and zone
allocation failures, and every `strcpy`, `strcat`, `sprintf` and `vsprintf` (363 calls: 27 reachable, 36
theoretical, 13 in compiled-out code, 287 bounded by construction).

## How it happened

Inherited from Quake, which trusted its own data and its console, and from AmiWind modules that assumed the
builder's output is always well formed.

## Why it was not caught

No test fed these paths bad or unusual input.

## Reproduction

Per row below.

## Repair

### Fixed (reachable by shipped data or a player)

| Where | Trigger | Was | Now | ID |
| --- | --- | --- | --- | --- |
| host_cmd.c map, changelevel, connect, restart; sv_main.c SV_SpawnServer | name of 55+ characters, many `map` words | buffer overflow | "Map name too long", refused before leaving the game | ENGINE-MAP-NAME-OVERFLOW-35 |
| host_cmd.c load | damaged save | Sys_Error, overflow | Host_Error "damaged save", widths on every read | ENGINE-LOADGAME-SYSERROR-35 |
| sys_amiga.c RunGameLoop | hours of play | float frame times | double | ENGINE-FRAME-TIME-FLOAT-35 |
| sv_main.c SV_SpawnServer | over 255 inline models | precache overflow | map unavailable | ENGINE-SUBMODEL-LIMIT-32 |
| snd_dma.c S_FindName | `play` with a 64+ character name; 512 sounds in a session | Sys_Error | no sound, one console line | ENGINE-SOUND-NAME-SYSERROR-35 |
| model.c Mod_ForName, Mod_TouchModel, Mod_LoadModel (Mod_FindName's callers) | model name empty or 64+ characters; missing model with crash | overflow of mod->name, Sys_Error | refused (Host_Error or no model) | ENGINE-MODEL-NAME-SYSERROR-35 |
| model.c Mod_LoadLeafs | map with over 8192 leaves | silent PVS overflow | clear stop naming the map; builder gate | ENGINE-LEAF-LIMIT-UNCHECKED-35 |
| sys_file_amiga.c Sys_FileOpenWrite | `screenshot` on a full or protected disk | Sys_Error | message, write refused | ENGINE-WRITE-OPEN-SYSERROR-35 |
| cmd.c Cbuf_InsertText, Cbuf_Execute | large `exec`, line over 1023 characters | Sys_Error, stack overflow | refused, line cut | ENGINE-CBUF-OVERFLOW-35 |
| common.c COM_Parse | token over 1023 characters | global overflow | cut, input consumed | ENGINE-COM-TOKEN-UNBOUNDED-35 |
| common.c COM_DefaultExtension and its callers | empty or long save, load and demo names | read before the buffer, overflow | bounded | ENGINE-ENTITY-TEXT-UNBOUNDED-35 |
| pr_edict.c ED_ParseEntity, ED_ParseGlobals, ED_LoadFromFile | damaged map entity text or save | Sys_Error, key and value overflows | Host_Error, bounded copies | ENGINE-ENTITY-TEXT-UNBOUNDED-35 |
| pr_edict.c PR_ValueString, PR_UglyValueString, PR_GlobalString; pr_cmds.c PF_VarString | long strings (saved, printed, traced) | overflow of 128/256-byte lines | bounded; saved strings written whole | ENGINE-ENTITY-TEXT-UNBOUNDED-35 |
| sv_main.c sign-on message | map "message" with a percent sign | text used as a format | data | ENGINE-ENTITY-TEXT-UNBOUNDED-35 |
| console.c, host.c, pr_exec.c, sys_amiga.c print buffers | print over 1023 characters | vsprintf overflow | vsnprintf | ENGINE-ENTITY-TEXT-UNBOUNDED-35 |
| cl_parse.c precache names, player names; model.c alias frame names | demo or server data; damaged .mdl | overflow | Host_Error, bounded | ENGINE-ENTITY-TEXT-UNBOUNDED-35 |
| pr_cmds.c PF_sound, PF_lightstyle | QuakeC arguments out of range | Sys_Error, write past sv.lightstyles | PR_RunError | ENGINE-QC-ARGS-SYSERROR-35 |
| chim/chim_statics.c Place | bad flora static at chunk activation | Host_Error with zone locks held, Sys_Error on the next map | static left out | CHIM-STATIC-PLACE-HOST-ERROR-35 |
| maps: edicts, model and sound precaches, statics, scenery catalogue, visible entities, leaves | a map over an engine table | stop at load | builder gate on every shipped map | BUILD-BUDGET-ENGINE-LIMITS-35 |

### Left, with the reason

| Where | Trigger | Severity | Why left |
| --- | --- | --- | --- |
| model.c brush decoders (about 75 Sys_Error sites) on a legacy world map | damaged or over-limit BSP | Sys_Error | CHIM arena loads already return a failed load (CHIM-BRUSH-BAD-DATA-35). A legacy world load has no clean way back after it has allocated in the Hunk. Shipped maps pass the builder's map gates (per-map limits, heap audit, BSP structure checks). Candidate: catch it as CHIM does, with the Hunk reset. |
| aw_render_ranges.c (14 sites) | malformed render-range metadata | Sys_Error on map entry | The data is written and checked by the builder (render pool inspection, hidden-surface cull tests). The native tests treat a conflicting range as fatal by design. Candidate: disable ranges for the map instead. |
| pr_edict.c ED_Alloc with `aw_ent_count_exceed_soft_fail 0` | over MAX_EDICTS | Sys_Error | The default (1) ends the session safely. 0 is the stock behaviour, kept as an explicit choice (DON'T DELETE ANY METHOD). Shipped maps are gated. |
| zone.c Z_Malloc | hundreds of `alias` commands fill the 48 KiB zone | Sys_Error | Needs deliberate console abuse; no shipped path comes close. |
| zone.c, common.c Hunk_Alloc, Cache_Alloc, COM_LoadFile | a map, model or sound that does not fit memory | Sys_Error | Guarded by the heap gates (check_world_map_heap.py, chim/heap.py, the alias, sprite and edge-cache heap tools); the CHIM zone already fails a chunk gracefully. |
| common.c, model.c short reads | disk or read error during a load | Sys_Error | Hardware or a damaged disk image. |
| common.c SZ_GetSpace on the sign-on | sign-on over MAX_MSGLEN | Sys_Error | Gated by the builder's sign-on estimate (sprite_heap.py). |
| cl_parse.c (bad server message, protocol, light style, stat), cl_tent.c | a hostile server (`connect`) or crafted demo | Sys_Error / Host_Error | AmiWind is single player; only hostile data reaches these. |
| draw.c, wad.c, host.c palette and colormap, aw_hand_sprites.c, PAK and volume manifest checks | a broken payload at start-up | Sys_Error with a clear message | Start-up checks of the shipped payload; the build and the payload preflight check the files. |
| host_cmd.c Host_Say, Host_Tell | a lone quote; `hostname` on a dedicated server | undefined behaviour, overflow | Dedicated-server only, or harmless. |
| zone.c, chim_zone.c, chim_graft.c, chim_chunks.c, renderer, physics, net, vid and snd hardware (about 150 sites) | internal invariants | Sys_Error | Not reachable from data or input; they mark programming errors. |

## Verification

`tests/test_engine_crash_paths.py` (native fixtures under AddressSanitizer for the name checks, COM_Parse,
COM_DefaultExtension and PF_VarString; source checks for the rest) and `tests/test_map_engine_limits.py`.

## Prevention

Data and console input are checked where they enter a fixed buffer or a fatal path. New fatal paths reachable by
data are registered with their own ID and listed here.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Engine table limits (`engine-limits`). Fixed engine tables (models, entities, faces, texinfo, flames, lamps, door rows) are checked by the builder before a map ships, never discovered in play. See [families](README.md#families).

- AW-20260928-16 (no report page): Two compiler-reported array bounds violations
- AW-20260929-02 (no report page): NPCs missing from expanded town render
- BALMORA-CAPACITY-005 (no report page): Bounded Balmora maps exceed the 600-entity limit
- [BUILD-BUDGET-ENGINE-LIMITS-35](BUILD-BUDGET-ENGINE-LIMITS-35.md): Town entity and model budgets were not tied to the engine's per-map tables
- EFRAG-01 (no report page): Static foliage leaf links exhausted ('Too many efrags!')
- [ENGINE-ENTITY-TEXT-UNBOUNDED-35](ENGINE-ENTITY-TEXT-UNBOUNDED-35.md): Entity and QuakeC text was copied into fixed buffers without a bound
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
- [INTERIOR-INLINE-LIMIT-31](INTERIOR-INLINE-LIMIT-31.md): Every interior object is its own inline model: 220 objects per interior at most
- [LAMPS-CACHE-31](LAMPS-CACHE-31.md): Night lamps beyond 96 per 3x3 cells are silently dropped (Vivec)
- [MODEL-MARKSURF-SIGNED-31](MODEL-MARKSURF-SIGNED-31.md): Face indices above 32,767 in leaf face lists become bad pointers
- [MODEL-SLOTS-256-32](MODEL-SLOTS-256-32.md): Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it
- [RENDER-VISEDICTS-OVERFLOW-32](RENDER-VISEDICTS-OVERFLOW-32.md): Entities beyond MAX_VISEDICTS (1,112) are dropped silently
- TOWN-FLORA-BUDGET-004 (no report page): World 4 MiB file budget wrongly applied to town flora maps
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

<!-- END GENERATED CATEGORY -->
