# TOWN-VIS-OCCLUSION-31: town buildings do not block Quake visibility

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 7 October 2026, in v0.0.31-dev5 |
| Where | Town and interior maps: func_wall models ignored by vis |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev5 (last seen) |
| Severity | medium: Most of a town stays potentially visible; low frame rates in Balmora and Seyda Neen. |
| Family | Rendering cost and visibility (`render-performance`) |
| Playtest version | v0.0.31-dev5 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. The planned repair (occluders, building faces in the world model) was
prototyped and measured not to help open towns; see
[Town visibility](../performance/TOWN-VISIBILITY.md). Interiors still to test.

## Symptom

Low frame rates in Balmora and Seyda Neen, worst with a long fog distance;
shortening the fog distance to 250 roughly doubles the frame rate (owner).

## Where

The scene converter (each placed mesh becomes a `func_wall` brush model) and
the visibility data `vis` computes from the world brushes.

## How it happened

Quake's `vis` only uses structural world brushes as walls. All building meshes
are `func_wall` models, so the world of a town map is just its terrain and
almost every leaf can see almost every other: 84-89 % of a Balmora map from an
average leaf, 73 % in Seyda Neen. See
[Town visibility](../performance/TOWN-VISIBILITY.md).

Every converted map type is affected: interiors are one empty two-leaf box
(100 % visible: Mages Guild 40,488 faces, all processed every frame), Seyda
Neen 59-76 %, the open world with rock and tree `func_wall` models 69-85 %.
NPCs and creatures behind buildings are drawn too: alias models use the depth
buffer, so a hidden NPC costs its full drawing work, and only the visibility
data could skip it.

The town, interior and Census builds also run `vis -threads 1 -fast`
(`tools/prepare_balmora.py`, `prepare_area.py`, `prepare_census.py`): the rough
mode, on one core per map, so even the terrain's visibility is only coarse.

## Why it was not caught

Performance work measured load times and frame rates, not how much of a map
the visibility data lets the engine skip.

## Reproduction

Any Balmora street with a long fog distance: frame rate near 10 looking along
the street; read the visibility lump of bm019 as described in the performance
page.

## Repair

Planned: invisible `skip`-textured structural occluder blocks inside each
building footprint, then `vis` again; buildings stay brush models. Interiors:
occluder slabs inside the walls and floors between rooms. Open world: occluders
in large rocks only.

First prototype (bm019, 30 occluders, full `vis`): 589 of 590 building models
still potentially visible everywhere; 362 exceed Quake's 16-leaf link limit and
are always visible, and entities are culled whole. Next: building faces in the
world model (culled per leaf) plus occluders.

## Verification

Pending: visible share and frame rate at the same views, before and after.

## Prevention

A visibility gate per town map: the average visible share must stay below a
set limit.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Rendering cost and visibility (`render-performance`). Read the visibility data and renderer counters before any performance claim. See [families](README.md#families).

- AW-20260928-07 (no report page): Slow opening exterior / excessive residency
- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)
- [CHIM-TRACE-TAIL-33](CHIM-TRACE-TAIL-33.md): A few CHIM collision traces visit thousands of clipnodes
- [ENGINE-C2P-ROWSTRIDE-35](ENGINE-C2P-ROWSTRIDE-35.md): The display conversion ignored the bitmap row stride: a screen whose rows are padded for the fetch mode rendered skewed
- [ENGINE-FLOATTIME-DIV64-35](ENGINE-FLOATTIME-DIV64-35.md): Sys_FloatTime made two 64-bit library divisions per call to build seconds and microseconds
- [ENGINE-VID-UPDATE-FIRST-RECT-35](ENGINE-VID-UPDATE-FIRST-RECT-35.md): VID_Update converted only the first rectangle of the update list
- MODAL-WORLD-29 (no report page): Head/race and journal backgrounds consume world work
- [NPC-TARGET-REDUNDANT-31](NPC-TARGET-REDUNDANT-31.md): NPC targeting runs 2-4 times per frame and checks every NPC
- [RENDER-BMODEL-FRAGMENTS-32](RENDER-BMODEL-FRAGMENTS-32.md): Brush models spanning many terrain leaves are clipped face by face down the terrain BSP
- [RENDER-EDGECACHE-SEYDA-32](RENDER-EDGECACHE-SEYDA-32.md): No edges are reused between frames in Seyda Neen views
- [RENDER-SURFCACHE-THRASH-32](RENDER-SURFCACHE-THRASH-32.md): Seyda Neen views rebuild the surface cache every frame at a fixed camera

Related bugs in other categories:

- [CHIM-PVS-HOLLOW-33](CHIM-PVS-HOLLOW-33.md): Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells
- [INTERIOR-HULL-CHAIN-33](INTERIOR-HULL-CHAIN-33.md): The Arena Pit's main structure collides through one chain of 36,545 clipnodes; every trace in the room walks it
- [VF-VIS-LUMP-32](VF-VIS-LUMP-32.md): Open-world terrain maps spend about a fifth of their bytes on visibility data that culls little

<!-- END GENERATED CATEGORY -->
