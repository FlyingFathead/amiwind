# HARVEST-EXTRA-TOWNS-32: Opt-in towns get no harvestable mushrooms

## Status: 8 October 2026

Open. Found by the builder harvest step work (BUILD-HARVEST-NOT-BUILT-32, commit 0331f76).

## Symptom

The harvest step covers the open world (`vf`), Seyda Neen (`sn`), Balmora (`bm`) and the intro
docks only. Towns added with `--extra-town` (Vivec Arena, `va*` maps) get no harvest catalogue, so
mushrooms there cannot be picked.

## Where

`tools/harvest_build.py` `plan_rows` (map sources: `world/regions.awr`, the Seyda Neen and Balmora
region tables, the intro docks bounds).

## How it happened

The plan reads the region tables of the map families v0.0.31 shipped; opt-in towns write their own
tables, which the plan does not read.

## Why it was not caught

Opt-in towns are new in v0.0.32 and no test builds harvest for one.

## Reproduction

Build with `--extra-town` and list `id1/harvest-va*.txt`: none.

## Repair

Not yet: read the region tables of every imported town in `plan_rows`. The v0.0.32 release notes
must mention that opt-in towns have no harvest.

## Verification

Pending.

## Prevention

A harvest plan test with an imported town.
