# TERRAIN-LIGHT-UNIFORM-32: Open-world terrain lightmaps are nearly uniform

## Status: 8 October 2026

Open. Found by the asset census (tools/asset_census.py). Needs a headlamp-off visual check.

## Symptom

About 130,000 lightmap samples are compiled per open-world map but only about 5 KB is stored
after sharing, which means almost no light variation: possibly no sun or shadow in the bake.

## Where

Open-world terrain light compile.

## How it happened

Unknown.

## Why it was not caught

Lightmaps were not inspected per sample.

## Reproduction

Read the vf maps' lighting lumps and sample variation.

Confirmed by the CHIM Balmora build (8 October 2026): the terrain bake has no light sources, so every
terrain sample stores 12.

## Repair

Not yet: inspect in game (headlamp off) and in the bake settings.

## Verification

Pending.

## Prevention

Lightmap variation report per map.
