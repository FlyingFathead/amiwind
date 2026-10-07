# TOWN-VIS-OCCLUSION-31: town buildings do not block Quake visibility

## Status: 7 October 2026

Open. Measured; repair planned in the converter.

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
