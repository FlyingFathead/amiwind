# HORIZON-HOLES-31: distant buildings break up against the sky

## Status: 7 October 2026

Open. Needs work; cause understood in outline, not yet measured.

## Symptom

Looking across the river at Balmora at sunset, the far buildings are a flat
fog-brown silhouette with the sky showing through holes and jagged gaps
(owner screenshots at 17:59, 18:19 and 18:24, local about (284..319,
116..260, 62), facing east).

## Where

Far culling (`aw_cull`, forward far plane in `aw_fog.c`) and the distant land
fill (`aw_horizon.c`, `AW_HorizonDraw`).

## How it happened

Geometry beyond the draw distance is culled per node and surface, so a large
building near the limit loses some pieces and keeps others; the kept pieces
are fully fogged. The distant fill that closes the view behind the fog plane
draws only land polygons (flat fog colour), not buildings, so the gaps show
sky.

v0.0.32-dev1 (8 October 2026): the Vivec Arena shows the same break-up close up (upper parts
patchy, sky and fog showing through) and turns into a flat fog silhouette from about 1,500 units;
the heavier fog is recorded separately as [FOG-TOWN-HEAVY-32](FOG-TOWN-HEAVY-32.md).

## Why it was not caught

Distance views of towns against a bright sky were not part of the checks; the
land fill was designed and tested for terrain only.

## Reproduction

v0.0.31-dev2: from the west bank opposite Balmora (global about -19300 -11800),
`dbg set time 1800`, look east across the river.

## Repair

Not done. Proposed: extend the distant fill with each placed object's
simplified collision hull (real geometry, a few dozen flat polygons per
building) drawn in the fog colour beyond the fog plane, and cull objects whole
rather than piece by piece near the limit. Cost to be measured with an FS-UAE
frame-time sweep before enabling.

## Verification

Pending: the same views without holes, and the frame-time cost.

## Prevention

Distance views of every town against a bright sky in the capture set.
