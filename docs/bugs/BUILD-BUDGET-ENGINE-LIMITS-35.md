# BUILD-BUDGET-ENGINE-LIMITS-35: Town entity and model budgets were not tied to the engine's per-map tables

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | config town budgets; tools/import_town.py; engine MAX_EDICTS, MAX_MODELS, scenery catalogue |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | high: A map over an engine table stops the game at load (no free edicts, precache overflow, scenery catalogue) |
| Family | Engine table limits (`engine-limits`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3b72d32 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on v0.0.35-crash-fixes-2, not shipped at the time of writing. Every map the image ships is
checked against the engine's per-map tables; no shipped map of v0.0.32 or v0.0.34 is over one (measured below).

## Symptom

None seen in play. The town configs (`config/balmora.json`, `config/vivec_*.json`) set `"entity_budget": 1000`
and `"model_budget": 220`, while the engine holds `MAX_EDICTS` 600 edicts and `MAX_MODELS` 256 model precaches
per map. A map over one of the engine's tables stops at load: `ED_Alloc: no free edicts` (or the session ends
with the soft-fail cvar), a precache overflow, "Too many static entities", or the scenery catalogue's error.

## Where

`config/*.json` budgets; `tools/import_town.py` (the only check, per region, against the config numbers);
the engine: `quakedef.h` (`MAX_EDICTS`, `MAX_MODELS`, `MAX_SOUNDS`), `client.h` (`MAX_STATIC_ENTITIES`,
`MAX_VISEDICTS`), `aw_scenery.c` (the scenery catalogue), `sv_main.c` and `pr_cmds.c` (precaches).

## How it happened

The budgets were chosen per town before the engine limits had one source (`tools/engine_limits.py`), and the
region check compared them with themselves. The engine's own use of edicts and precaches (the world, the
client, the player and hand models the QuakeC precaches, the arena opponent and test companion) was not
counted anywhere.

What the engine really does (read from the source): on a scenery town's region maps (`AW_TOWN_SCENERY`:
Balmora's `bm000`-`bm063` and the Vivec districts) every `func_wall` goes into the scenery catalogue, not into
an edict (`AW_SceneryCapture`), except the ones a harvest catalogue binds; the catalogue holds 1000 placements
(now `AW_SCENERY_MAX_PLACEMENTS`) and is linked into `cl_visedicts` after the edicts in one go (a Host_Error
above `MAX_VISEDICTS` 1112). So the 1000 of the town configs is the catalogue's limit, not an edict count; on
any other map a `func_wall` is an edict. Static entities (`aw_static`, `aw_flora`) and removed entities
(`aw_flame`, `aw_lava`, entities without a spawn function) free their edict at once.

## Why it was not caught

No gate read a finished map the way the engine spawns it; the per-town budget was the only check.

## Reproduction

A town config with a budget above the engine's room, or a map whose entities, inline models plus precached
models, sounds or statics pass the engine's tables.

## Repair

- `tools/map_engine_limits.py` counts each finished map as the engine loads it: edicts at the load peak (world,
  one client, every entity whose QuakeC spawn function keeps its edict, one reused slot for freed ones, the ten
  edicts engine code adds at run time: test companion, arena opponent, weapon and shield of up to four hostiles), model precaches (slot 0, the world, its inline models, the worldspawn
  precaches, every `precache_model(self.model)`, each actor model's carried items from its `.tag`, one run-time
  slot), sound precaches (with each actor model's `.anm` animation sounds), sound precaches, static entities, the
  scenery catalogue, the visible-entity table at the scenery link and the leaves. The spawn functions and fixed precaches
  are read from `engine/aga/qc/world.qc`, the scenery towns from the engine's town table, the limits from the
  engine headers: nothing is copied.
- The payload preflight runs it on the staged maps before the image step writes anything; the image step runs
  it again on the final map set (after the CHIM frame maps, before the stair and heap gates) and writes
  `engine-map-limits.json`.
- A config budget may only tighten the engine: the build preflight refuses a town config whose entity budget
  passes the scenery catalogue (scenery towns) or `MAX_EDICTS` less the fixed edicts (other towns), or whose
  model budget passes `MAX_MODELS` less the fixed precaches.
- The engine's literal 1000 became `AW_SCENERY_MAX_PLACEMENTS` (`aw_town.h`), read by the builder.

CHIMport cell settings (`tools/chimport.py`) keep `"entity_budget": 1000` (owner decision, 10 October 2026):
their region maps are not scenery towns, but they only feed the CHIM builder and never ship as maps; the final
gate covers every map that does.

The gate also counts leaves against `MAX_MAP_LEAFS` ([ENGINE-LEAF-LIMIT-UNCHECKED-35](ENGINE-LEAF-LIMIT-UNCHECKED-35.md)).

## Verification

`tests/test_map_engine_limits.py`: the limits are the engine's defines; every engine `ED_Alloc` call outside the
map load, QuakeC spawn and the NPC gallery is counted; spawn rules come from the QuakeC; synthetic maps at and
one over each table; every `config/*.json` passes; the gates run in the preflight and the image step.

Measured on the shipped builds (read only), worst map per table:

| Table (limit) | v0.0.34 image (629 maps) | v0.0.34 all staged maps (2185) | v0.0.32 image (486 maps) |
| --- | --- | --- | --- |
| Edicts at load (600) | vf0141 372 | vf1025 400 | vf0141 372 |
| Model precaches (256) | vf0453 203 | vf1258 231 | bm020 224 |
| Sound precaches (256) | balmora-chim 16 | bm063 16 | bm063 16 |
| Static entities (512) | seyda-chim 229 | vf1907 202 | vf0229 110 |
| Scenery catalogue (1000) | none (Balmora on CHIM) | bm028 654 | bm028 654 |
| Visible entities at the scenery link (1112) | none | bm028 685 | bm028 685 |
| Leaves (8192) | vf0256 3145 | vf2251 4175 | vf0256 3145 |

The closest is the model table: 25 slots left on vf1258 (the staged world map set of v0.0.34).

## Prevention

One count of what the engine loads, read from the engine and the QuakeC, run on every map before it ships; a
test over every config.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Engine table limits (`engine-limits`). Fixed engine tables (models, entities, faces, texinfo, flames, lamps, door rows) are checked by the builder before a map ships, never discovered in play. See [families](README.md#families).

- AW-20260928-16 (no report page): Two compiler-reported array bounds violations
- AW-20260929-02 (no report page): NPCs missing from expanded town render
- BALMORA-CAPACITY-005 (no report page): Bounded Balmora maps exceed the 600-entity limit
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
- [INTERIOR-INLINE-LIMIT-31](INTERIOR-INLINE-LIMIT-31.md): Every interior object is its own inline model: 220 objects per interior at most
- [LAMPS-CACHE-31](LAMPS-CACHE-31.md): Night lamps beyond 96 per 3x3 cells are silently dropped (Vivec)
- [MODEL-MARKSURF-SIGNED-31](MODEL-MARKSURF-SIGNED-31.md): Face indices above 32,767 in leaf face lists become bad pointers
- [MODEL-SLOTS-256-32](MODEL-SLOTS-256-32.md): Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it
- [RENDER-VISEDICTS-OVERFLOW-32](RENDER-VISEDICTS-OVERFLOW-32.md): Entities beyond MAX_VISEDICTS (1,112) are dropped silently
- TOWN-FLORA-BUDGET-004 (no report page): World 4 MiB file budget wrongly applied to town flora maps
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

<!-- END GENERATED CATEGORY -->
