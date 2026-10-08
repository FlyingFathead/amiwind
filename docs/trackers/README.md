# Trackers

Progress trackers for converting Morrowind's world to AmiWind. They answer
"what exists, what is done, what is missing" before content is built at scale.
None of them contains Morrowind game data: they hold cell coordinates, record
IDs, counts and AmiWind's own status. Anyone with their own Morrowind
installation can regenerate the detailed views locally.

| Tracker | Status | What it shows |
| --- | --- | --- |
| [World progress](WORLD_PROGRESS.md) | First version in the image build | Every exterior cell with switchable overlays: converted, needs work, memory warnings, entity coverage, points of interest; whole-world limit estimate |
| [Entities](ENTITIES.md) | First version in the image build | Per entity category (rocks, plants, giant mushrooms, NPCs, creatures, containers, doors, fires...): original placements vs placed in AmiWind, with reasons for anything missing |
| [Points of interest](POI.md) | Checklist done; `dbg poi` planned | Every named place, from cellars to cities, and which are converted |

Bugs are tracked separately in the [bug register](../BUGS.md).
