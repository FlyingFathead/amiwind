# ENTITY-TRACKER-HARVEST-32: The entity tracker did not count plants placed by harvest catalogues

## Status: 8 October 2026

Open: fixed in source on the v0.0.32 development line (commit 0331f76); not shipped at the time of writing.
Found by the builder harvest step work (BUILD-HARVEST-NOT-BUILT-32).

## Symptom

The entity tracker counted only placements found in a map's BSP. Plants placed through a map's
harvest catalogue read as "not placed": v0.0.31's 7,336 world plants, and removing Balmora's baked
mushrooms (replaced by harvestable ones) would have looked like a loss against a baseline.

## Where

`tools/entity_tracker.py`.

## How it happened

Harvest catalogues were added to the payload after the tracker, and it never read them.

## Why it was not caught

Harvest data was made outside the builder, so the tracker's placed counts were never compared
before and after a harvest change.

## Reproduction

Run the entity tracker on a v0.0.31 image: harvest plants count as missing.

## Repair

`entity_tracker.harvest_refs` reads the references of each map's harvest catalogue; a map's placed
set is its BSP references plus its catalogue's.

## Verification

`tests/test_harvest_build.py` `test_entity_tracker_counts_catalogue_plants` (catalogue references
read; an empty catalogue gives none). A finished image's tracker report is pending.

## Prevention

That test; the tracker is run after the harvest install in the image step.
