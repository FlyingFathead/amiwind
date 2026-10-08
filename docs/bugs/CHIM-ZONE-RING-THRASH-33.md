# CHIM-ZONE-RING-THRASH-33: Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes

## Status: 8 October 2026

Open; tagged performance. Found in the first FS-UAE session of Balmora drawn by CHIM. CHIM engine.

## Symptom

With the default 6 MiB zone, Balmora's ring of up to 41 chunks does not fit. One FS-UAE session
showed:

- 15,259 cache evictions;
- 61 MB read in 30,215 reads and 3,593 file opens;
- 64 failed frame-world rebuilds ("no room for the frame world", largest free block 358 KB), with
  chunks left waiting ungrafted.

## Where

CHIM engine zone (cache) sizing, ring size and the frame-world rebuild
([CHIM-REBUILD-COST-33](CHIM-REBUILD-COST-33.md): a rebuild needs the old and the new pool at
once); heap accounting of the zone ([CHIM-HEAP-CHECK-33](CHIM-HEAP-CHECK-33.md)).

## How it happened

The zone holds models, chunks and the frame-world pool together; a full Balmora ring plus its
models is larger than 6 MiB, so loading one chunk evicts another that the ring still needs, and
the rebuild cannot find a contiguous block for the pool.

## Why it was not caught

Host tests used small rings; this was the first emulator run with Balmora's full ring.

## Reproduction

FS-UAE, Balmora under CHIM with the default zone: walk the town and read the CHIM cache counters
(evictions, reads, opens, failed rebuilds).

## Repair

Not yet; options under measurement: allocate the frame-world pool before the models, a smaller
ring, or a larger zone within the memory budget.

## Verification

Pending: no failed rebuilds and a bounded eviction count on the benchmark walk.

## Prevention

The CHIM validator checks that the largest ring plus its models and the pool fit the configured
zone; the engine counters report evictions and failed rebuilds.
