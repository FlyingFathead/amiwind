# Entity tracker

**Status: first version in the image build (v0.0.31 development).**

Keeps track of which kinds of things are placed in AmiWind, so nothing is left
behind unnoticed as more of the world is converted.

## How it counts

- **Original:** every placed reference in your own `Morrowind.esm`, one per
  placement, with its category and cell. Each reference has a number that is
  unique in the master file (measured: 316,116 placements, no repeats).
- **AmiWind:** the reference numbers carried by the entities of every shipped
  map (`aw_ref`: scenery, doors, flora, harvest plants, NPCs, corpses). A
  placement counts as placed when any map carries its number, so a placement
  that sits in several overlapping maps is counted once.
- **Categories:** rocks, giant mushrooms, trees, plants, harvest plants (the
  pickable flora containers), other statics, doors, containers, lights,
  activators, NPCs, creatures and items. Rocks, giant mushrooms, trees and
  plants are decided by the same rules the converters use.

## Why something is missing

Every original placement that is not placed gets exactly one reason:

| Reason | Meaning |
| --- | --- |
| `cell_not_converted` | No shipped map places anything from its cell yet. |
| `outside_world_scope` | Only the open-world maps (`vf*`) reach its cell, and they carry nothing of its category (they hold the land, rocks, giant mushrooms, trees and flora). |
| `deliberately_skipped` | An interior converter rule leaves it out; the rule's own reason is counted (small items and actors deferred, fine dressing such as ropes, hooks and baskets, editor markers, unsupported activators). |
| `category_not_implemented` | Nothing of its category is placed anywhere yet (creatures, for now). |
| `not_placed` | Its cell and category are converted and no rule explains it: the "forgot those" list. |

## In the build

The image build writes `entity-tracker.json` for the final maps, prints the
summary, and records the report's hash in `build.json`. The report has counts
per category and per cell, and per cell and category a SHA-256 of the sorted
placed reference numbers (`placed_digests`); the build's own copy also lists
the numbers (`placed_refs`), so it can name what is missing. The build report
stays beside the image and is never shipped.

Against a baseline (`--entity-baseline`), the image step stops before any disk
is made when a category drops to zero or loses more than 5 % of its placements
(and at least 10), and, with the same master, when any cell and category has
fewer placements than the baseline, or the same number of other placements: one
missing lantern hook is enough (BUILD-DRESSING-EXCLUDED-32). An intended loss
passes with `--accept-entity-loss REASON`, which is recorded.

`tools/build.py` compares with the last release by default:
`config/entity-baseline.json`, made from the release's maps with
`entity_tracker.py baseline` (counts and digests only, no reference numbers).
`--no-entity-baseline` turns the comparison off for debugging only. Each
release replaces the baseline with its own.

The image step also writes `dressing-track.json` (private, beside the image):
every interior placement of dressing (lantern hooks, ropes, ferns and similar,
`prepare_mesh_bsp.DRESSING_EXCLUDED`) per map, with each map's modelled heap
estimate. The Seyda Neen interiors keep their dressing by default;
`--skip-dressing` restores the earlier rule (BUILD-DRESSING-EXCLUDED-32).

Run it on its own:

```bash
python3 tools/entity_tracker.py report --master /path/to/Morrowind.esm \
    --maps build/boot/id1/maps --out entity-tracker.json \
    --previous previous/entity-tracker.json
python3 tools/entity_tracker.py compare old.json new.json
python3 tools/entity_tracker.py baseline release-entity-tracker.json     --release v0.0.31 --out config/entity-baseline.json
```
