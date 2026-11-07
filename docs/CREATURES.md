# Creatures: every creature of the game and what the build makes of it

_Last updated with AmiWind v0.0.62-dev1 (7 November 2026)._

<!-- contents start -->
## Contents

- [What a creature is in the game data](#what-a-creature-is-in-the-game-data)
- [The creature census (v0.0.62)](#the-creature-census-v0062)
- [The census with the rooms' creatures (v0.0.62-dev1)](#the-census-with-the-rooms-creatures-v0062-dev1)
- [The census of v0.0.61](#the-census-of-v0061)
- [What is not built, and what it would take](#what-is-not-built-and-what-it-would-take)

<!-- contents end -->

## What a creature is in the game data

A creature is a record of its own in the masters (CREA): its model, its stats (a 96-byte record), its flags (walks,
flies, swims, two-legged), its behaviour values and its sounds. The world uses a creature record in four ways:

- placed: a reference in an exterior cell or in a room;
- levelled: named by a levelled creature list, which the game rolls at the player's level where the list is placed
  (most wild creatures come this way);
- scripted: placed by a script or a dialogue result (PlaceAtPC, PlaceAtMe, PlaceItem, PlaceItemCell);
- summoned: called up by a summoning effect; the game setting of the effect (sMagicScampID and the others) names the
  creature record.

The build makes one model per creature mesh, shared by every record that uses it (the creature library), and every
placed creature outdoors is spawned from the actor table, which also rolls the levelled lists. Rooms carry their
creatures and levelled creature points as entities the game spawns from the same table. What every record holds is listed in [ACTOR_RECORDS.md](ACTOR_RECORDS.md).

## The creature census (v0.0.62)

The image step counts every creature record of Morrowind, Tribunal and Bloodmoon on every build
(`tools/creature_census.py`, `config/creature-census.json`), with all their placements, the levelled lists that name
them, the scripts and dialogue results that place them and the summoning settings. Each record is either built (the
image places it: a map's actor row or a base of the actor table, with its model in the image) or not built for a
reason that the config names: an expansion master the image does not read, summoned only, placed in rooms only, or
not used by the game data at all. Each placement is checked too: an outdoor placement of a built creature is
spawned from the actor table; a room placement is built when the room's map holds it; every levelled creature point
of the base game's rooms must be in its room's map.

The build stops on anything the census cannot account for: a creature that is not built and that no group of the
config names (an outdoor creature the build should have made, a creature without a model, a mesh the bake refused, a
creature only a script places), a levelled creature point of a room that is not placed, a built creature without its sounds, or a master it reads that the config does
not name. A MiniWind, a build with content excluded and a build without the actor table are counted and reported,
never stopped. The census is written beside the image step's receipts (`creature-census.json`, private: it names
record ids and cells). For an audit of a finished build:

```sh
python3 tools/creature_census.py --data-files /input/DataFiles --run /vol/ws8/build/<run> --tables
```

It costs the build a few seconds (the three masters read once, the image's maps scanned for their actor rows in
parallel) and adds nothing to the image.

## The census with the rooms' creatures (v0.0.62-dev1)

All three masters against a full v0.0.62-dev1 image with the rooms' placed creatures, 7 November 2026: 228 creature
records built (100 in v0.0.61), 860 of 1,357 placements built (337), and 527 of the 904 room placements (4). Every
creature record the base game places is built; the build check passes.

| Creature records | Count | Placements | Status |
| --- | ---: | ---: | --- |
| Built by the image | 228 | 860 | built |
| Tribunal and Bloodmoon creatures | 136 | 494 | missing ([CREATURE-EXPANSION-62](bugs/CREATURE-EXPANSION-62.md)) |
| Summoned creatures | 16 | 0 | missing ([CREATURE-SUMMONED-62](bugs/CREATURE-SUMMONED-62.md)) |
| Creatures placed in rooms | 0 | 3 | missing ([INTERIOR-CREATURES-MISSING-41](bugs/INTERIOR-CREATURES-MISSING-41.md)) |
| Not used by the game data | 16 | 0 | skipped on purpose |
| All | 396 | 1,357 | |

The outdoor regions are as in v0.0.61 below; the rooms:

| Region | Placed creatures | Built | Not built | Levelled creature points | Placed by the image |
| --- | ---: | ---: | --- | ---: | ---: |
| Rooms (all interiors) | 904 | 527 | Creatures placed in rooms 3, Tribunal and Bloodmoon creatures 374 | 1,532 | 1,266 |
| All | 1,357 | 860 | 497 | 7,478 | 6,348 |

How a room places them: the actor table gives every creature a room places a list of one entry (after the levelled
lists, so those keep their order), the actor library makes its model, and the room map carries the reference as the
same entity a room's levelled creature has, so the game spawns it from the table with the outdoor creature's model,
stats, sounds and behaviour ([the actor table](chim/WORLD_FORMAT.md)). An authored-dead creature lies as its corpse.
A placed creature comes back after its death only when its record is flagged to respawn (the kwama queens are), as in
the original. Vivec, Dagoth Ur and the Heart of Lorkhan keep their own models from the room stage.
`--room-placed-creatures off` builds the rooms as before.

The three placements left are the Fighters Guild's rats in Drarayne Thelas' house and storage in Balmora: Balmora's
own rooms are converted with the town, and a change there rebuilds the town's frame, so they wait for that decision
(as the intro rooms' levelled creatures do).

What it costs, measured on that image at 32 MB Fast (68040 preset with JIT), 7 November 2026:

- Triangles: 523 more creatures in 217 rooms. Every creature model is reduced to under 600 triangles; the three
  meshes only rooms use (the kwama queen, the ash vampires and Yagrum Bagarn) are baked at 384 triangles (370, 379 and
  386), so each adds at most 1.8 % to the smallest room that holds it (Kagrenac's Library, 20,706 faces). With every
  room creature in view at once, the rooms that have them would draw 3.4 % more (median room 3.2 %).
- Frame: in Thelas Ancestral Tomb with an ancestor ghost close in view, 66.9 frames a second; the same pose with the
  room's creatures removed, 69.9 (about 0.7 ms a frame for the ghost).
- Memory: after arriving in Thelas Ancestral Tomb, the Sarimisun-Assa queen's lair, the lower Uncharted Caverns of
  Dubdilla (nine creatures of seven kinds) and the St. Delyn Underworks in Vivec (thirteen rats), 4.15 to 4.17 MB of
  the 13.6 MB heap stay free (4.1 MB in Samarys Ancestral Tomb before this change); the models go into the model cache
  and leave it when it needs the room.
- Disk: the actor table grows by about 29 KB (a list and a base per creature), of which about 3.6 KB stay resident;
  a room's creatures read their table text and their models while the room loads, behind the loading screen.

## The census of v0.0.61

All three masters against the v0.0.61 image, 7 November 2026: 396 creature records (Morrowind 260, Tribunal 63,
Bloodmoon 73), 1,357 placements and 7,478 levelled creature points.

| Creature records | Count | Placements | Status |
| --- | ---: | ---: | --- |
| Built by the image | 100 | 337 | built |
| Tribunal and Bloodmoon creatures | 136 | 491 | missing ([CREATURE-EXPANSION-62](bugs/CREATURE-EXPANSION-62.md)) |
| Summoned creatures | 16 | 0 | missing ([CREATURE-SUMMONED-62](bugs/CREATURE-SUMMONED-62.md)) |
| Creatures placed in rooms | 128 | 529 | missing ([INTERIOR-CREATURES-MISSING-41](bugs/INTERIOR-CREATURES-MISSING-41.md)) |
| Not used by the game data | 16 | 0 | skipped on purpose |
| All | 396 | 1,357 | |

The 529 room placements are those of the 128 records placed only in rooms and 331 room placements of creatures the
image builds for the outdoors (the rooms place only the creatures that `config/interior_creatures.json` lists).
The 16 unused records are named by no placement, used levelled list, script, dialogue result or summoning setting:
dead bodies with no placement, quest creatures the game never places and duplicates of placed ones.

Per region (outdoors) and for the rooms:

| Region | Placed creatures | Built | Not built | Levelled creature points | Placed by the image |
| --- | ---: | ---: | --- | ---: | ---: |
| Azura's Coast | 94 | 94 | none | 999 | 999 |
| Ashlands | 12 | 12 | none | 951 | 951 |
| West Gash | 61 | 61 | none | 760 | 760 |
| Sheogorad | 54 | 54 | none | 602 | 602 |
| Molag Mar | 24 | 24 | none | 510 | 510 |
| Bitter Coast | 36 | 36 | none | 497 | 497 |
| Ascadian Isles | 48 | 48 | none | 319 | 319 |
| Isinfier Plains | 19 | 0 | Tribunal and Bloodmoon creatures 19 | 344 | 0 |
| Hirstaang Forest | 11 | 0 | Tribunal and Bloodmoon creatures 11 | 237 | 0 |
| Red Mountain | 0 | 0 | none | 242 | 242 |
| Felsaad Coast | 59 | 0 | Tribunal and Bloodmoon creatures 59 | 149 | 0 |
| Grazelands | 4 | 4 | none | 202 | 202 |
| Moesring Mountains | 31 | 0 | Tribunal and Bloodmoon creatures 31 | 118 | 0 |
| Brodir Grove | 0 | 0 | none | 8 | 0 |
| Outdoors, no region | 0 | 0 | none | 6 | 0 |
| Thirsk | 0 | 0 | none | 2 | 0 |
| Rooms (all interiors) | 904 | 4 | Creatures placed in rooms 529, Tribunal and Bloodmoon creatures 371 | 1,532 | 1,266 |
| All | 1,357 | 337 | 1,020 | 7,478 | 6,348 |

Every outdoor creature of the base game is built, and so is every levelled creature point of its regions. Of the
base game's 1,270 levelled creature points in rooms, 1,266 are placed; the 4 of Addamasartus and Tharys Ancestral
Tomb are not ([ROOM-LEVELLED-INTRO-ROOMS-62](bugs/ROOM-LEVELLED-INTRO-ROOMS-62.md)). The Solstheim regions (Isinfier
Plains, Hirstaang Forest, Felsaad Coast, Moesring Mountains, Brodir Grove, Thirsk) and the expansions' rooms wait for
the expansion areas.

Of the built creatures, the six netch records stand on their idle when they would run: their model has no run group
in the original either.

## What is not built, and what it would take

- Summoned creatures: each of the 16 records uses a mesh the creature library already builds for the wild creature
  of the same kind, so no model is added; they need a base in the actor table and the spell effects that call them
  up.
- Creatures placed in rooms: built since v0.0.62-dev1 (above), except the three in Balmora's own rooms.
- Tribunal and Bloodmoon: with the expansion areas.
