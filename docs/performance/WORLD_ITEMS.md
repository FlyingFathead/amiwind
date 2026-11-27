# World items: what can be taken

_Last updated with AmiWind v0.0.69-dev5 (27 November 2026)._

Every item of Morrowind, Tribunal and Bloodmoon that the game places in a room or outdoors and that a player can take
or steal (weapons, armour, clothing, books and scrolls, potions, ingredients, misc items, gold, keys, apparatus,
lockpicks, probes, repair tools, and lights that can be carried), counted against what a build makes of it. The
builder counts it after every full build (`world-item-census.json` in the run folder); this page and
[WORLD_ITEMS.json](WORLD_ITEMS.json) keep the measurements, newest last, and a gate test reads the newest: an item that
stops being drawn, aimed at or taken, or a new reason for one, fails the gate. Items inside containers are counted with
the containers ([CONTAINERS.md](CONTAINERS.md)); the plants are the harvest's.

## The columns

For every such placed item, five answers read from the build's own files, by the rules the engine uses.

| Column | Means |
| --- | --- |
| In the build | The master that places it is one the build reads, and indoors its room is in the image. |
| Drawn | Indoors the room draws it (an entity of the room map carrying its reference, a placement of the CHIM room, or the placed item list); outdoors the placed item list draws it, an entity of a frame map carries it, or a piece of the CHIM world places it. |
| Aimable | It is drawn, and its item row is in the use table the engine reads for the place (a room alone, outdoors the 3 x 3 cells around the player, within the engine's rows). |
| Takeable | It is aimable, its row takes it (a book with words is read first), and every drawn copy goes with the take: an entity and a room placement by reference, the placed list's copy by the world change list, a piece of the CHIM world only through its hide row. |
| Owner kept | The row says taking it is theft exactly when the original does (the reference's owner, else its faction), and the area names that owner. |

What the count cannot see from the files: whether the view ray reaches an item that stands inside other geometry, and
a copy baked into a compiled room's other brushes (the opening rooms have their own strict check in the image step).

## Measurements

### v0.0.69-dev5 (27 November 2026)

Build `2026_11_26_v0.0.69-dev5_full-v0.0.69-dev5_6bbf562`, counted with tools/room_item_census.py world.

| Master | Side | Placed | In the build | Drawn | Aimable | Takeable | Owned | Owner kept |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Morrowind | interior | 37,478 | 37,478 | 37,478 | 37,478 | 37,478 | 29,374 | 29,374 |
| Morrowind | exterior | 497 | 497 | 489 | 489 | 134 | 151 | 151 |
| Tribunal | interior | 1,884 | 1,884 | 1,884 | 1,874 | 1,874 | 1,296 | 1,296 |
| Tribunal | exterior (the Mournhold districts) | 49 | 49 | 49 | 49 | 0 | 45 | 45 |
| Bloodmoon | interior | 2,598 | 2,598 | 2,598 | 2,598 | 2,598 | 2,088 | 2,088 |
| Bloodmoon | exterior | 76 | 76 | 76 | 76 | 16 | 6 | 6 |
| All | | 42,582 | 42,582 | 42,574 | 42,564 | 42,100 | 32,960 | 32,960 |

Why the rest could not be taken:

| Items | Cells | Reason | Register |
| ---: | ---: | --- | --- |
| 474 | 84 | Outdoors the placed item list and a piece of the CHIM world both draw the item at the same spot | [OUTDOOR-ITEM-CHIM-COPY-STAYS-69](../bugs/OUTDOOR-ITEM-CHIM-COPY-STAYS-69.md) |
| 464 | 80 | Of those, the piece has no hide row: taken, its CHIM copy stays where it lay | [OUTDOOR-ITEM-CHIM-COPY-STAYS-69](../bugs/OUTDOOR-ITEM-CHIM-COPY-STAYS-69.md) |
| 10 | 1 | The burned-out torches of the Temple Sewers West in Old Mournhold have no name, and the use table leaves out an item without one | [ITEM-NAMELESS-NOT-TAKEN-69](../bugs/ITEM-NAMELESS-NOT-TAKEN-69.md) |
| 8 | 2 | Seyda Neen's travel lanterns are drawn by nothing: the town's frame leaves its lights out | [SEYDA-LANTERNS-MISSING-31](../bugs/SEYDA-LANTERNS-MISSING-31.md) |

Indoors every item of the three masters is built, drawn and keeps its owner. Outdoors the lights and the items that
only the placed list draws (most of Seyda Neen's, among them the Iron Shardaxe in the rotting trunk by the lighthouse)
are taken whole.

## How to count

In the build's container (the game data folder and a finished full build's run folder):

    python3 tools/room_item_census.py world --data-files DATA --run RUN [--summary FILE] [--out FILE] [--md FILE]
        [--measurement docs/performance/WORLD_ITEMS.json] [--show REF,...] [--show-ids REGEX] [--check]

It prints one line per master and side, the gaps with the number of items and cells, and the verdict against the gaps
the register allows (`KNOWN_GAPS`); `--check` exits 1 when the verdict fails. The builder runs the same count after
every full build.
