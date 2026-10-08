# CHIM-PVS-HOLLOW-33: Chunk visibility culls almost nothing in Balmora: houses have hollow collision shells

## Status: 8 October 2026

Open. Found by the first CHIM world-format build of Balmora (branch v0.0.33-chim-format, format 0.1).

## Symptom

99.7 % of the chunk ring is potentially visible on average; 30 of 8,836 chunk pairs are blocked. Most
houses' collision volumes are hollow shells that do not block sight lines.

## Where

CHIM chunk PVS (`tools/chim/visibility.py`); building collision.

## How it happened

Visibility is computed from collision volumes, and town buildings are hollow.

## Why it was not caught

First measurement.

## Reproduction

The CHIM validator's visibility report for Balmora.

Building occluders (8 October 2026): 51 hollow-shell buildings now act as occluders from their closed
render meshes (+7 % solid cells); the ring's visible share is unchanged (99.7 % mean, 82.6 % lowest).
Chunk-level rows cannot cull in a town: 90 % of Balmora chunks hold content more than 128 units above
their lowest ground, which shows over the houses between. Next: per-placement visible lists using
the same occluders.

Per-placement visible lists (world format 0.3, 8 October 2026, branch v0.0.33-chim-format, fe8d594):
a performance limit rather than a defect, and still open. Of 51,224 placement tests in the Balmora
ring (placements in a chunk's ring but not next to it), 5,875 (11.5 %) are blocked. Per view, median
placements drop from 95 to 86 and faces of placed models from 13,535 to 12,170; on the benchmark
cameras the lists cut 2-15 % of the placements and 1-10 % of the faces. A street-level town view
still sees most of the ring because:

- the lists use a raised eye (97 units) as well as the standing eye, so jumps and stairs do not pop
  placements in, and the raised eye sees over the houses;
- the box sample points include roof tops that show over the next roof;
- occluders are eroded 24 units inside the walls.

Open items:

- Standing eye only would give 14.4 % fewer placements and 12.9 % fewer faces per view than the
  chunk rows (83 / 11,476 median per view), but risks placements popping in on jumps and stairs.
  Open decision: measure popping in the engine (renderer counters on the fixed cameras) first.
- Smaller occluder erosion is untested: the erosion experiment was invalid (the patched default
  argument never took effect), so its result is discarded and the experiment is to be repeated.

This matches the town findings of [TOWN-VISIBILITY.md](../performance/TOWN-VISIBILITY.md) and
[TOWN-VIS-OCCLUSION-31](TOWN-VIS-OCCLUSION-31.md): in towns the bigger lever is distance detail.

## Repair

Not yet: use the buildings' closed render meshes (or simple fitted boxes) as occluders for the
visibility rows; compare with running Quake's vis on the stitched frame.

## Verification

Pending.

## Prevention

Visible share per chunk in the validator report.
