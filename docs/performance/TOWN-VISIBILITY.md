# Town visibility: why buildings do not hide what is behind them

Measured 7 October 2026 on the v0.0.31-dev5 maps. Bug:
[TOWN-VIS-OCCLUSION-31](../bugs/TOWN-VIS-OCCLUSION-31.md).

## How Quake decides what to draw

Quake's map compiler splits a map into leaves, and its `vis` tool stores, for
every leaf, the list of leaves that can possibly be seen from it (the PVS,
potentially visible set). At run time the engine only considers geometry in
leaves on that list, then clips what is left to the view. Only solid
structural brushes of the world (`worldspawn`) form the walls of leaves.
Brush entities such as `func_wall` are drawn and collide, but they never block
visibility.

## What the converter does today

Morrowind buildings are triangle meshes. The converter turns each placed mesh
into its own `func_wall` brush model, so its look, collision and per-object
records stay intact. The world itself is only the terrain.

| Map | Faces in the world | Faces in `func_wall` models | `func_wall` models | Map visible from an average leaf |
| --- | ---: | ---: | ---: | ---: |
| balmora (bm019) | 2,215 | 36,031 | 590 | 87 % |
| bm020 | 2,415 | 35,520 | 638 | 89 % |
| bm028 | 2,539 | 35,245 | 654 | 88 % |
| bm029 | 2,406 | 22,420 | 417 | 84 % |
| seyda | 3,952 | 21,475 | 217 | 73 % |

![Faces in the world vs in func_wall models](../images/amiwind-perf-faces-world-vs-funcwall.svg)

Over 94 % of a Balmora map's faces are in building models that `vis` cannot
use, so from almost anywhere in town Quake treats almost the whole town as
visible. Everything in front of the player is transformed, clipped and sorted
every frame, including houses hidden behind the one being looked at; only what
is behind the player is skipped by the view test. Shortening the fog distance
helps (owner measurement in Balmora: fog distance 250 roughly doubles the
frame rate) because the far cut-off is then the only thing removing hidden
buildings.

## Not only towns: every converted map type

| Map type | Examples | Leaves | Faces in `func_wall` models | Map visible from an average leaf |
| --- | --- | ---: | ---: | ---: |
| Interiors | Mages Guild, Temple, Fighters Guild, Census, prison ship | 2 | 20,563-40,488 | 100 % |
| Town exteriors | Balmora maps | 812-955 | 22,420-36,031 | 84-89 % |
| Seyda Neen | town, docks, courtyard | 178-1,585 | 7,716-21,475 | 59-76 % |
| Open world with rocks and trees | sampled `vf` regions | 1,096-2,814 | 4,078-10,800 | 69-85 % |
| Open water | sampled `vf` regions | 200-304 | 0 | 36-39 % |

![Share of each map Quake treats as visible](../images/amiwind-perf-visibility-by-map.svg)

Interiors are the extreme case: the world of an interior map is one empty box
(two leaves) and every wall, floor and room is a `func_wall`, so the whole
interior is processed every frame wherever the player stands.

NPCs and creatures are affected too. They are alias models, which Quake draws
with a depth buffer rather than the edge sorting used for walls, so an NPC
hidden behind a house still costs its full drawing work. The engine only skips
an entity whose leaves are outside the visibility data, and today that data
sees through every building.

## And the visibility that exists is the rough kind

The town, interior and Census builds run `vis -threads 1 -fast`: the quick mode,
which skips the full portal flow and leaves looser visibility lists, on a single
core per map (maps are built side by side instead). With occluders in place the
shipping build should run full `vis`, using every core on the maps it rebuilds;
area test builds can keep `-fast` for speed, and the visibility report shows the
difference.

## First prototype result (8 October 2026): occluders alone are not enough

Rebuilding bm019 with 30 structural occluder blocks and full `vis` split the
map into more leaves (811 to 1,158), but 589 of its 590 building models stayed
potentially visible from every one of 213 test points. Two reasons, both in
Quake itself:

- An entity linked to more than 16 leaves (`MAX_ENT_LEAFS`) is treated as
  visible everywhere; 362 of the 590 building models cross that line.
- A brush entity is kept or skipped as a whole, never per face.

## Second prototype result (8 October 2026): the tested occluders give negligible benefit

The full prototype rebuilt bm019, bm020 and bm028 with the shipped pipeline
(byte-identical to the shipped maps without occluders) and added 30-39 skip
occluder blocks per map, fitted inside the Hlaalu houses so that no block
touches a drawn surface or leaks through a window.

- What the server sends barely moves. From 213 street points, 589 of bm019's
  590 building models are still sent with occluders and full `vis`; bm028
  goes from 653 to 650 of 654, bm020 from 637 to 635 of 638.
- The cost is real: the visibility lump doubles or triples, about 180-290 KB
  more modelled heap per map, and full `vis` runs 8-13 times longer.
- The occlusion exists geometrically. Tracing lines of sight from 48 street
  points, 497 building placements are visible over bare terrain, 299 with the
  fitted blocks and 151 with whole-building blocks. Quake's leaf-to-leaf
  visibility loses it: the open street leaves are huge (median
  727 x 962 x 114 units), and a visibility row means "seen from anywhere in
  this leaf". Even with 128-unit leaves, 87 % of leaves stay visible from the
  street.
- Hint brushes (ericw-tools `hint`, which add splits and portals for `vis`)
  were tried too: 128- and 256-unit vertical hints with the occluders moved
  bm019 from 589 to 586-588 models sent.
- The 16-leaf entity limit (`MAX_ENT_LEAFS`) is not the binding limit with
  today's leaves: lifting it changes the count by 0-8 models.
- Building faces in the world model: measured instead of built. Placing the
  153 largest buildings' 33,999 faces in every leaf they touch would cut face
  work by at most about 5 % and break the marksurface (65,535) and texture
  mapping (32,767) limits. Quake also draws world faces only through the BSP
  node that owns them, so faces cannot simply be appended to the world model;
  qbsp would have to compile them.

Conclusion: the tested occluders and hints give negligible benefit with the
current town partitioning, so they are not shipped. Further town occlusion
work is deferred until there is evidence for a better partitioning or culling
approach; the line-of-sight numbers show occlusion exists, but they are not a
frame-rate prediction. Positions inside one leaf share its potentially
visible set, which must cover every point of that leaf, so a large open-street
leaf keeps buildings that are hidden from a particular corner. Meanwhile the
town frame rate is sought from drawing less at a distance (fog distance,
simpler distant shapes) and cheaper per-model work. Interiors, rooms behind
thick walls, still need the occluder test below.

## What the sent models cost (8 October 2026)

Renderer counters measured what happens to the building models that visibility
does not remove. In Balmora they take 67-82 % of render time, and not because
they are cut into many pieces (1.38-1.59 fragments per face): each clipped face
walks 27-52 nodes of the world BSP to find where it belongs, up to 233,867 node
visits in one frame. So cheaper placement of the models that are sent matters
as much as sending fewer
([RENDER-BMODEL-FRAGMENTS-32](../bugs/RENDER-BMODEL-FRAGMENTS-32.md);
[What a town frame is spent on](LESSONS_LEARNED.md)).

## Interiors: still to test

Occluder slabs inside the thick wall and floor meshes between rooms, so `vis`
splits an interior into rooms, measured the same way.

## Method

The visible share is read straight from each map's visibility lump: for every
leaf with visibility data, the number of leaves in its decompressed visibility
row divided by all leaves, averaged over the leaves. Faces per model come from
the model lump; `func_wall` counts from the entity lump.

The story behind it: [Horstator's musings, 7 October 2026](../HORSTATORS_MUSINGS_2026-10-07.md).
