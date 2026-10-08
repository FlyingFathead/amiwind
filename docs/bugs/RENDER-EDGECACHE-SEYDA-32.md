# RENDER-EDGECACHE-SEYDA-32: No edges are reused between frames in Seyda Neen views

## Status: 8 October 2026

Open. Found by the renderer counters work (branch v0.0.32-counters, not yet merged).

## Symptom

The edge cache reuses 0 edges per frame at the Seyda Neen cameras, against 190-350 in Balmora.

## Where

Engine edge setup (`r_edge.c`, `r_draw.c` cached edges).

## How it happened

Unknown: Quake caches world edges, not brush-model edges; Seyda Neen is mostly brush models.

## Why it was not caught

No per-frame edge counters before this work.

## Reproduction

`dbg rcount 1` at the Seyda Neen cameras.

## Repair

Not yet: confirm the cause; part of the streamer's world model decision.

## Verification

Pending.

## Prevention

Counters in the benchmark route.
