# CHIM-ZONE-RING-THRASH-33: Balmora's chunk ring does not fit the default 6 MiB CHIM zone, so the cache thrashes

## Status: 8 October 2026

Open; tagged performance. Found in the first FS-UAE session of Balmora drawn by CHIM. CHIM engine.
Fixed in source on v0.0.33-chim-format-engine (41386bc), not shipped at the time of writing (see Repair
and Verification).

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

Fixed in source on v0.0.33-chim-format-engine (41386bc), not shipped at the time of writing: the
zone grows to 6.5 MiB and two 512 KiB frame-world slots are reserved at map start, so a rebuild
always has room for the new pool next to the old one. New defaults: `chim_zone_kib 6656`,
`chim_pool_kib 512` (capped at a twelfth of the zone), `chim_prefetch_room 1`. Native tests: the
slots, ring overrides, standing still reads nothing, a jump lands in a small zone.

## Verification

8 October 2026, one A/B/C/D sweep in FS-UAE (emulated A1200, 2 MiB Chip + 16 MiB Fast), an
8-chunk walk and back (emulator numbers are relative):

| | Read | Evictions | Failed rebuilds | Long jump |
| --- | --- | --- | --- | --- |
| Before (6 MiB zone) | 41 MB | 6,651 | rebuilds found no room | failed |
| After (6.5 MiB zone, two 512 KiB slots) | 1.9 MB | 338 | 0 | lands |

The rerun of the fixed build was identical. Hunk left after load: 2.86 MB before, 2.33 MB after
(a legacy region map leaves 3.55 MB). Pending: the full Balmora benchmark walk in a built image and
a hardware number.

## Prevention

The CHIM validator checks that the largest ring plus its models and the pool fit the configured
zone; the engine counters report evictions and failed rebuilds.
