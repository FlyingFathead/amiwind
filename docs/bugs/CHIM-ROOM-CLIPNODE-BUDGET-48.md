# CHIM-ROOM-CLIPNODE-BUDGET-48: Akulakhan's Chamber cannot be made as a CHIM room

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | tools/chim/models.py collider: in_akulacave00, 162,975 standing clipnodes |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.48-dev2 |
| Severity | high: the main quest's last room is not in a default build (left out, its doors inert) |
| Family | Engine table limits (`engine-limits`) |
| CHIM | Stairs and collision on CHIM worlds ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source dd23cc8, engine dd23cc8, CHIM world dd23cc8 |
| CHIM engine version | CHIM 0.2.1, engine dd23cc8, world format 0.12 |
| Platform or emulator | not in game (the CHIM interiors stage leaves the room out) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

<!-- contents start -->
## Contents

- [Status: 23 October 2026](#status-23-october-2026)
- [Symptom](#symptom)
- [Why it matters](#why-it-matters)
- [Cause](#cause)
- [Fix](#fix)
- [Regression tests](#regression-tests)
- [Open](#open)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 23 October 2026

Fixed in the builder (branch v0.0.48-akulakhan). The room is made as a CHIM room; its doors are live again. Not yet
checked in the game.

## Symptom

The CHIM interiors stage over every batch room: `Akulakhan's Chamber` (map `rifa4ef181ed`, batch 19) fails with
`ValueError: Clipnode budget exceeded` from one model's standing collision (`chim/models.py` `collider`), after the
routed-hull attempt also exceeded the budget. Before CHIM-ROOM-FAIL-STAGE-48 this one room failed the whole stage.

## Why it matters

It is the main quest's last room (the heart of Lorkhan). The big-rooms measurement already named its cave shell: one
model of about 7.6 MiB loaded, two thirds of it collision.

## Cause

The model is the cave shell `meshes/i/in_akulacave00.nif`. Its authored collision (`RootCollisionNode`) is the whole
cave, 6,532 triangles, and its profile keeps it as hollow authored plates with exact standing bevels (the cave shell
rule): 6,281 convex plates. One brush image addresses its clipnodes with 16-bit numbers, so a model holds at most
65,520. Measured on the room's own scenery export:

| standing hull of in_akulacave00 | clipnodes | one image holds |
| --- | ---: | ---: |
| chain of the plates, exact bevels (the profile) | 162,975 | 65,520 |
| chain of the plates, approximate bevels | 69,713 | 65,520 |
| routed hull (no copies: the chain plus one per cut) | over the chain | 65,520 |
| qbsp union of the pieces | compile fails, as for the other cave shells | |

No other model in the room comes near the limit. The next largest is `ex_dwrv_enter00`, at 2,205 clipnodes.

## Fix

The hard-room method's steps, in order ([INTERIOR_SECTIONS.md](../INTERIOR_SECTIONS.md#on-chim-rooms-v0048)):

1. **Lighter collision alone does not fit.** Approximate bevels are still 69,713 clipnodes and would change the
   collision. The compiled union fails to compile.
2. **The mesh optimizer** reduces only what is drawn, never the collision, so it cannot help here.
3. **A cut, at the model.** The over-budget part is one model, the whole cave, so the room's references cannot be
   divided at a corridor to fix it. The model itself is cut instead, as the large-model cut does for wide exterior
   models. The model is cut into tiles of its own frame, and every collision plate and every face goes whole to one
   tile. The tiles together are exactly the model, so neither what is drawn nor what is solid changes. Each tile is
   its own image with its own 16-bit numbers. Two parts could not be enough: 162,975 clipnodes need at least three.

How the builder does it (`tools/chim/budget_tiles.py`, `tools/chim/build.py` `frame_input`):

- A model variant run that stops on a budget error (clipnodes, point nodes, vertices, texture mappings) runs its
  units one by one. Every model that fits keeps its unit, its result and its cache key. The model over the budget
  is named and stored as tiles at the frame's grain, halved until every tile fits (at most 127 tiles).
- It applies to any frame or room with a model over the budget, not to one room. No other model changes, and no
  existing unit is keyed anew: the code keys of every unit kind were compared before and after, and all are the same.
- A CHIM room maps a tile's placement number back to its source placement (its light level, the room map check).
- The hatch from Dagoth Ur's Facility Cavern stays the room's load door, with the same target and arrival. The
  room-batches stage and its door banks are unchanged.

**Measured** (23 October 2026, the stage commands on batch 19 with no image, 8 cores; the MiniWind Balmora inputs
of 22 October, read only):

- chim-room-batches, batch 19: 35 rooms converted in 74.1 s on 5.2 of 8 cores.
- chim-interiors over batch 19: 35 rooms, none failed. Akulakhan's Chamber has 365 placements and 135 models. The
  cave shell became 78 tiles at grain 256. 71.1 s on 1.3 cores; a second run took 50.9 s and wrote a byte-identical
  store.
- Installed (a scratch install, then removed): all 35 room maps installed, none removed, so the room's doors are
  live. The room's need is 10,599,248 bytes (models 10,396,496, textures 181,680, record 21,044).
- **32 MB:** it fits. A room has 15,384,576 bytes at the 32 MB minimum, so 4.8 MB are left. No model is now a
  single 7.6 MiB block.
- **16 MB:** it does not fit. The 16 MB zone alone is 7,012,352 bytes, so on 16 MB, or with Extra RAM off, this
  room is one of those that show the 16 MB refusal screen.

## Regression tests

`tests/test_budget_tiles.py`: a synthetic cave of 8,192 authored plates with exact bevels.

- The whole model is refused for budget. Its tiles each fit, hold every piece exactly once, and moved back by their
  centres are the model's own pieces.
- The grain halves until every tile fits, and the tile count is bounded.
- A variant run names the unit over the budget and keeps every other unit's result; any other error stops it as
  before.

## Open

- To check in the game: the room loads at 32 MB and its doors work (the hatch both ways). The walls hold, the lava
  floors burn and the heart platform stands, with the headlamp off and on.
- The model's whole-image attempt is not cached, so every run tries it again before the cached tiles are used. Its
  room then runs on about one core: the batch-19 rerun took 50.9 s on 1.4 of 8 cores. In a full stage, other rooms
  run beside it. ([CHIM-ROOM-OVER-BUDGET-RETRY-48](../BUGS.md))

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Engine table limits (`engine-limits`). Fixed engine tables (models, entities, faces, texinfo, flames, lamps, door rows) are checked by the builder before a map ships, never discovered in play. See [families](README.md#families).

- ALIAS-BUDGET-32MB-48 (no report page): The alias model budget is still the 16 MB era's 512 KiB: two NPCs fall back to standing-only animations
- AW-20260928-16 (no report page): Two compiler-reported array bounds violations
- AW-20260929-02 (no report page): NPCs missing from expanded town render
- BALMORA-CAPACITY-005 (no report page): Bounded Balmora maps exceed the 600-entity limit
- [BUILD-BUDGET-ENGINE-LIMITS-35](BUILD-BUDGET-ENGINE-LIMITS-35.md): Town entity and model budgets were not tied to the engine's per-map tables
- BUILD-LEGACY-ENGINE-PATHS-48 (no report page): The engine's legacy town region streaming was not marked or fenced as legacy
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
- [INTERIOR-EXCLUDE-STALE-41](INTERIOR-EXCLUDE-STALE-41.md): Two Vivec rooms stayed left out on heap numbers from an older build
- [INTERIOR-INLINE-LIMIT-31](INTERIOR-INLINE-LIMIT-31.md): Every interior object is its own inline model: 220 objects per interior at most
- [LAMPS-CACHE-31](LAMPS-CACHE-31.md): Night lamps beyond 96 per 3x3 cells are silently dropped (Vivec)
- [MODEL-MARKSURF-SIGNED-31](MODEL-MARKSURF-SIGNED-31.md): Face indices above 32,767 in leaf face lists become bad pointers
- [MODEL-SLOTS-256-32](MODEL-SLOTS-256-32.md): Some Vivec interiors exceed the engine's 256 model slots; the heap check does not catch it
- [RENDER-SURFACE-OVERFLOW-SILENT-36](RENDER-SURFACE-OVERFLOW-SILENT-36.md): Faces past r_maxsurfs (12,288) or edges past r_maxedges (24,576) are dropped without a warning: Vivec views send up to 37,112 placement faces
- [RENDER-VISEDICTS-OVERFLOW-32](RENDER-VISEDICTS-OVERFLOW-32.md): Entities beyond MAX_VISEDICTS (1,112) are dropped silently
- TOWN-FLORA-BUDGET-004 (no report page): World 4 MiB file budget wrongly applied to town flora maps
- [VIVEC-TEXINFO-31](VIVEC-TEXINFO-31.md): Dense Vivec canton regions exceed the 32,767 texture-mapping limit

Related bugs in other categories:

- [CHIM-ROOM-HEART-CHAMBER-LOAD-50](CHIM-ROOM-HEART-CHAMBER-LOAD-50.md): Entering Akulakhan s Chamber (the Heart Chamber) ends the game: a model of its room store does not load, and the engine stops with Host_Error instead of refusing at the door
- [CHIM-ROOM-OVER-BUDGET-RETRY-48](CHIM-ROOM-OVER-BUDGET-RETRY-48.md): A model over the image budget is tried whole again on every run before its cached tiles are used: its room runs on one core

<!-- END GENERATED CATEGORY -->
