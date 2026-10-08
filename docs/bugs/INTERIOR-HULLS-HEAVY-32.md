# INTERIOR-HULLS-HEAVY-32: Interior collision hulls are bigger than the interior geometry they belong to

## Status: 8 October 2026

Open. Found by the asset census (tools/asset_census.py).

## Symptom

Interior architecture pieces carry about 1.6 times their drawn bytes in collision (hollow shells
with exact bevels). Interior hulls are the largest single kind of world data in the streamer
estimate: about 479 MB with the recommended policy, 512 MB with today's rules.

## Where

`tools/mesh_geometry.py` collision parts for interior meshes.

## How it happened

Exact hollow-shell collision per piece.

## Why it was not caught

Collision bytes were never compared with drawn bytes.

## Reproduction

Run the census disk breakdown.

## Repair

Not yet: simpler collision for interior pieces (merged or convex parts within a tolerance),
measured against getting stuck.

## Verification

Pending.

## Prevention

The census reports hull bytes per class.
