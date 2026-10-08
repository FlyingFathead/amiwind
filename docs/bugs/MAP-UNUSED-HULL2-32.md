# MAP-UNUSED-HULL2-32: Shipped maps carry about 1.1 MB of collision data for a hull the engine never uses

## Status: 8 October 2026

Open. Found by the builder fixes (hull analysis).

## Symptom

113 of 114 intro-scene maps carry clipnodes reachable only from hull 2 (the submodels' stock
hulls): 139,425 clipnodes, about 1.1 MB, loaded into the heap and never traced. The engine
uses hulls 0 and 1 only (world.c SV_HullForEntity; every QuakeC and engine trace box fits hull 1).

## Where

Map compiles (qbsp writes all hulls) and the map optimizer.

## How it happened

Stock Quake compiles all hulls.

## Why it was not caught

No one checked which hulls the engine uses.

## Reproduction

Count hull 2 clipnodes in the shipped maps.

## Repair

Not yet: drop hull 2 (and 3) data in the map optimizer for every map through one shared step;
measure the heap saved. The CHIM format stores only the hulls the engine uses.

## Verification

Pending.

## Prevention

`check_engine_hulls` reports unused hull bytes.
