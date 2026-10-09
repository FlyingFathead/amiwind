# CHIM-HARVEST-SPECIALS-33: no harvestable plants on the intro docks on CHIM

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | build |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | image step save fingerprint (build_aga.py) and aw_harvest_runtime.c naming |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-rc1 (last seen) |
| Severity | medium: 17 harvestable plants on the intro docks are not pickable in v0.0.33; the rc1 image step stopped on it first |
| Family | Harvestable plants (`harvest`) |
| CHIM | Builder ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.33-rc1 image-reuse build (rc1b-27058ec) |
| From commit | source 27058ec, engine 27058ec, CHIM world 27058ec |
| CHIM engine version | CHIM 0.1.0, engine 27058ec, world format 0.5 |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Mitigated for v0.0.33; the repair is planned for the next release. Known issue of v0.0.33.

## Symptom

The v0.0.33-rc1 image step stopped with "Harvest catalogue has no matching map: harvest-intro_docks.txt".

## Where

The image step's save fingerprint (`tools/build_aga.py`) checks that every harvest catalogue belongs to a
map. The engine (`aw_harvest_runtime.c`) loads `harvest-<loaded map>.txt`.

## How it happened

With Seyda Neen on CHIM the intro docks run as their CHIM frame map `intro_docks-chim.bsp`; the legacy map
`intro_docks.bsp` is no longer built. Its catalogue (17 plants) is still made under the legacy name.
CHIM-HARVEST-REMOVED-MAPS-33 covered the region maps of CHIM towns (the engine follows their regions), not
special maps such as the docks.

## Why it was not caught

No full build had Seyda Neen and its special maps on CHIM before the release candidate.

## Reproduction

A full build with Seyda Neen on CHIM (the v0.0.33 default).

## Repair

For v0.0.33 the image step leaves the special map's legacy catalogue out of the image and the save
fingerprint and lists it, because the engine would never load it on the CHIM frame map. Next release: a
catalogue for the frame map itself (name and coordinates checked against the frame map).

## Verification

`tests/test_harvest_alias_fingerprint.py` covers it (a special on CHIM: left out; a CHIM town's region
catalogue: kept; no frame map: kept).

## Prevention

Full builds of every CHIM area before release candidates.

The image step now starts with a payload preflight that runs this harvest catalogue check (and the
other read-only payload checks) on the map set the image will ship, so such an error stops the build in
seconds, before the image step writes anything ([BUILD_PROFILE.md](../BUILD_PROFILE.md#payload-preflight)).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Harvestable plants (`harvest`). Harvest catalogues are built by the builder for the shipped maps and counted by the entity tracker. See [families](README.md#families).

- [ENTITY-TRACKER-HARVEST-32](ENTITY-TRACKER-HARVEST-32.md): The entity tracker did not count plants placed by harvest catalogues
- [HARVEST-BITTERCOAST-29](HARVEST-BITTERCOAST-29.md): Only one of three nearby Bitter Coast mushrooms reportedly usable
- [HARVEST-EXTRA-TOWNS-32](HARVEST-EXTRA-TOWNS-32.md): Opt-in towns get no harvestable mushrooms
- [HARVEST-GEOMETRY-GATE-32](HARVEST-GEOMETRY-GATE-32.md): The harvest geometry gate was never re-run on the shipped Seyda Neen maps
- [HARVEST-PILOT-SHIPPING-32](HARVEST-PILOT-SHIPPING-32.md): 24 Seyda Neen maps still ship the six-plant pilot harvest catalogue
- [HARVEST-PLANTS-IN-COLLISION-33](HARVEST-PLANTS-IN-COLLISION-33.md): 51 placed harvest plants have their centre inside converted collision (terrain or a tree's convex root piece)
- [HARVEST-SEYDA-STALE-32](HARVEST-SEYDA-STALE-32.md): v0.0.31 ships Seyda Neen harvest catalogues made for older map versions
- HARVEST-WORLD-29 (no report page): Original mushroom placement, picking and persistent state worldwide

Related bugs in other categories:

- [CHIM-HARVEST-REMOVED-MAPS-33](CHIM-HARVEST-REMOVED-MAPS-33.md): A pure CHIM image stops at the save fingerprint: harvest catalogues of the removed town region maps have no matching map

<!-- END GENERATED CATEGORY -->
