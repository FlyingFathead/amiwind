# INTERIOR-INLINE-LIMIT-31: Every interior object is its own inline model: 220 objects per interior at most

## Status: 8 October 2026

Open. Found by the whole-world measurement (every object placed, estimated per map, checked on 30 converted maps).

## Symptom

Interiors bake light per object, so each placed object becomes its own brush model. The
converter stops above 220 inline models. It is the most-failed limit in the world: 402
maps with every object placed (264 with today's content); grottos have 490-750 objects.
Omalen Ancestral Tomb and Ald-ruhn Guild of Mages failed this way in validation.

## Where

The interior converter (`prepare_area`, per-object light baking).

## How it happened

Per-object models were chosen for per-object lighting; exteriors share models instead.

## Why it was not caught

The shipped interiors have fewer objects.

## Reproduction

Convert any grotto, e.g. Vassamsi Grotto.

Review note (8 October 2026): the 220 cap comes from the model table (`MAX_MOD_KNOWN`, the
edge-cache model limit of 256; one model per brush model), not from Quake's file format.
Placing interior objects as catalogue placements (as `aw_scenery.c` already does outdoors)
needs no model per piece and removes the cap.

## Repair

Not yet. Options, to be measured on a tomb and a grotto:

- Share geometry: many tombs and caves are built from the same few kit pieces,
  repeated almost unchanged. Quake stores lightmaps per face, so two placements
  can share one model only where their lighting matches; elsewhere the faces
  must stay separate.
- Bake static pieces into the room itself: walls, floors and fixed clutter
  become world faces of the interior, lit once by the light compiler, leaving
  inline models for doors, containers and other things that move or are used.
  This also gives `vis` real walls between rooms
  ([TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md)).
- Split the room into sections where neither is enough.

## Verification

Pending.

## Prevention

The builder reports inline models per map with warn/fail limits.
