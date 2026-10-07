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

The image build writes `entity-tracker.json` (counts, categories and cell
names only, no game data) for the final maps, prints the summary, and records
the report's hash in `build.json`. Given the previous build's report
(`--entity-baseline`), a category that drops to zero, or loses more than 5 %
of its placements (and at least 10), stops the build before any disk is made,
unless the loss is intended and explained with `--accept-entity-loss REASON`,
which is recorded.

Run it on its own:

```bash
python3 tools/entity_tracker.py report --master /path/to/Morrowind.esm \
    --maps build/boot/id1/maps --out entity-tracker.json \
    --previous previous/entity-tracker.json
python3 tools/entity_tracker.py compare old.json new.json
```
