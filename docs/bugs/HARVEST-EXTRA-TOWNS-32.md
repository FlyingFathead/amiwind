# HARVEST-EXTRA-TOWNS-32: Opt-in towns get no harvestable mushrooms

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Harvest plan (tools/harvest_build.py), Vivec Arena maps |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | medium: Opt-in towns get no pickable mushrooms. |
| Family | Harvestable plants (`harvest`) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [CHIM-HARVEST-SPECIALS-33](CHIM-HARVEST-SPECIALS-33.md): The intro docks on CHIM have no harvestable plants: their catalogue is named after the legacy map, which a pure CHIM image leaves out
- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [BUILD-EXTRA-TOWN-OPTIN-32](BUILD-EXTRA-TOWN-OPTIN-32.md): A default build leaves out the Vivec Arena preview that v0.0.32 ships
- [BUILD-HARVEST-NOT-BUILT-32](BUILD-HARVEST-NOT-BUILT-32.md): Mushroom harvest data is not built by the builder

<!-- END GENERATED CATEGORY -->
