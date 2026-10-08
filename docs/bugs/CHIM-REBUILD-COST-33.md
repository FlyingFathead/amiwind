# CHIM-REBUILD-COST-33: Each CHIM crossing rebuilds the whole frame world; the cost is not measured

## Status: 8 October 2026

Open. Found by the second CHIM engine slice (terrain in the world tree; branch v0.0.33-chim-engine).

## Symptom

Every crossing copies the whole ring into a new pool and relinks every static entity (up to 512) and edict
(up to 600); peak memory is old plus new pool (estimate about 350 KB for a Balmora ring). A rebuild that
cannot get memory evicts every unlocked cache block first, throwing away prefetched data.

## Where

`engine/aga/src/chim/chim_graft.c`; `Cache_Alloc` behaviour.

## How it happened

Simplest correct rebuild first.

## Why it was not caught

Host tests only so far; no emulator run on real data.

## Reproduction

Count and time rebuilds on a Balmora walk.

## Repair

Not yet: measure in FS-UAE; if it hitches, an incremental pool that touches only changed chunks,
and no eviction storm on failed rebuilds.

## Verification

8 October 2026, FS-UAE (emulator numbers are relative until a hardware number exists): one
frame-world rebuild per chunk crossing costs 0.7-3.5 ms under JIT, but 95-184 ms for 30-40 chunks
in a cycle-exact run (JIT off, CPU multiplier 7, busy host). On a 68040 that is a visible hitch at
every crossing. Suggested direction: an incremental frame-world pool that touches only the chunks
that changed. Pending: a hardware number.

## Prevention

Rebuild time and bytes in the CHIM counters.
