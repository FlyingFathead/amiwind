# Prison-ship interior preview

_Last updated with AmiWind v0.0.66-dev1 (13 November 2026)._

The current checkpoint starts in a locally converted Imperial Prison Ship cell. This is
a walkable lighting/loading experiment, not the opening quest or character
creation. Jiub, guards, dialogue, confiscation, container contents and the Census
office are not implemented here. The three town NPC prototypes remain outside.

The host extracts cell references, AMBI lighting, placed LIGH records and linked
DOOR destinations from the user's master/archive. It reuses the existing NIF
export, material reduction, BSP, standing hull and shared palette stages. The
private report lists omitted references and reasons. Selected furnishings are
static decoration/collision, not functioning inventory containers.

Checkpoint-017 keeps the original curved lower hull, floors, ceiling, walls,
stairs and plank source surfaces/UVs, while reducing separate detail at the
existing ratio. Checkpoint-016's blanket reduction flattened the hull inward
through hammocks and furnishings. New total: 98 instances, 26,572 BSP faces,
14,566 nodes, 23,487 clipnodes, 3,538,308 bytes (+54,428 bytes). This is a visual
repair; the 1,205 authored shell collision prisms and player hull are unchanged.
The exterior BSP is byte-identical to checkpoint-016. Keep visual simplification
separate from collision and verify both after changing conversion rules.

Ambient and nine placed lamps produce offline scalar lightmaps. This gives a
dim impression without per-frame global illumination. Colored lighting, flame
flicker, shadows and exact original light matching are not implemented. Exterior
fog is disabled inside this sealed BSP; it is not a day/night system.

## Entering and leaving

While walking, approach and face the upper hatch and press E. The exterior hatch
returns to the interior. An activation radius, facing test and line-of-sight check
prevent remote use. Source arrival coordinates receive a bounded local floor
search because their standing head can initially intersect the hatch. Only one
scene is resident; old map data is released before loading the next. Music track
identity and played-frame position continue; some audio deadlines still miss.

For recovery use `dbg scene town`, `dbg scene ship` or `dbg recover`. `dbg reset
location 0` returns to the safe town point. For reproducible hatch tests while
noclip is enabled, current local player origins are near (18,27,49) inside and
(695,-487,97) outside; disable noclip before pressing E because E means up in
noclip. The native validation uses these placements to isolate activation; it
does not certify a complete unassisted stair route.

The loaded scene restores a bounded subset of player state (health and hand
draw goal). Inventory, quests, actor state, doors and persistent cell state are
future work. General scene IDs and save-safe transitions need a dedicated design.
See [conversion recipes](CONVERSION_RECIPES.md) and
[checkpoint validation](history/checkpoints/CHECKPOINT_017_VALIDATION.md).

`dbg scene change` opens the two-scene debug popup; Escape cancels to the console.

## The weight of the hold

The hold is one classic room map (`prison.bsp`): the ship's shell and 98 placed props, each a brush model. Measured on
the v0.0.65 release map (PRISON-SHIP-POLY-COLLISION-65): 26,628 drawn faces (the shell 7,997, the 14 hammocks 7,504, the
15 barrels 3,990), 29,182 clipnodes, of which the shell's are 28,873.

What the engine does with it (from the source): it tests each brush model's box against the view once and then sends
every face of a model in view through the back-face test and the edge clipper; there is no test per face. The map has
two leaves, so no visibility data helps. The shell's box is the whole room, so all its faces are tested at every
heading, although at most headings only a few hundred of them are on screen. A model of the engine's own test from four
fixed spots in the hold (the start, Jiub and the two guards' places, eight headings each) reproduces the renderer
counters measured in v0.0.57 (the heaviest heading: 69 models, 22,591 faces tested, 11,475 facing, against 69, 22,416
and 11,491 measured). Its worst view is the start looking down the hold: 23,386 faces tested, of which the shell 7,997,
the hammocks 7,504 and the barrels 3,458.

The collision: the shell has stairs, and a hollow mesh with stairs got exact standing bevels on every one of its 1,205
collision plates. A point test of the player's hull walks 837 tree steps on average in the walkable space (at most
2,183).

Three methods, each behind a builder switch, the old path selectable:

| Method | Switch (default) | Faces drawn (before / added / total) | Collision |
| --- | --- | --- | --- |
| Shell bevels: exact on the 320 walkable plates (floors, treads, ledges), approximate on the walls, the rooms' rule | `--chim-hollow-bevels` (the hold's own 1; 0 = exact on every plate) | unchanged | clipnodes 29,182 to 18,054 (the shell 28,873 to 17,745), planes 44,795 to 33,812, deepest path through the shell 6,371 to 3,964, a point test 837 to 649 steps on average |
| Small closed parts as boxes: the hammocks' ten rings and small knots (at most 2.5 units, about 5 to 12 cm) drawn as their boxes in their own material | `--room-small-parts box` (off = as authored) | 26,628 / -2,030 / 24,598 (a hammock 536 / -145 / 391) | unchanged |
| Draw tiles: the shell's faces in 16 tiles of at most 512 faces, each with its own box; the faces themselves unchanged | `--room-draw-tiles 512` (0 = one model) | unchanged | unchanged (the tiles carry no collision) |

All three together, from the same four spots: faces tested per view 14,128 to 10,749 on average, 23,386 to 21,356 in
the worst view; faces facing the camera 7,285 to 5,488 on average. The map file is 3,783,692 to 3,369,576 bytes before
the later stages. The light headings gain most (the parts of the shell behind the view are no longer tested); the worst
view, which looks at most of the room, gains from the hammocks and not from the tiles.

Measured with the other values, for the record: bevels approximate on every plate (2) give 14,251 clipnodes, a point
test 516 steps; boxing the hammocks' two end knots too (4.75 units, a limit of 10) gives a hammock of 283 faces and
23,086 in all (19,844 tested in the worst view). Not the default: the walkable plates keep their exact bevels, and the
end knots are large enough to be seen as boxes.

Checks: the standing-box sweep of the bevel rule (`tools/hollow_bevel_sweep.py`) pushes no point through a wall with
either value (early stops 1.67 % of the far points with 1, 1.94 % with 2, limit 2 %); a connectivity check on the
collision data (standing cells on a 4-unit grid, steps of at most 18 units) reaches the upper deck from the start with
every value: 4,609 cells with 1 and 4,596 with 2 against 4,693 (the cells that differ lie along the side walls, where
the approximate bevels stop the player a few units earlier); with every switch at its old value the room is byte-identical to the
earlier output; a box is closed and spans its part exactly, so no open edge appears. Not measured yet: the frame time
on the Raspberry Pi 4B at the fixed spots (hold, deck, pier) and the look of the boxed rings in game.

The deck and the Seyda Neen pier, what is in view (the v0.0.65 release world; the boxes of the placements in the
three by three cells around against the view from the deck arrival and from the middle of the nearest dock pieces,
eight headings each, within the world's draw distance of 540 units): the kelp and the rocks that dominate the cell's
count are hardly in view (the rocks at most 640 faces). The ship itself (ex_de_ship, 3,690 faces, one model) is in
view at every heading from the deck and at most from the pier, the silt strider (3,219 faces, one placement) at two
headings from each spot, and the town's houses with 4,700 to 6,200 faces towards the town. The heaviest views: 16,378
faces from the deck, 16,494 from the pier.

Draw tiles for the ship and the silt strider, `--chim-draw-tiles on` (off by default): the two models are stored as the
large-model cut's tiles (every face and convex collision piece whole in the tile holding its centre) at a 128-unit
grain, whatever their width, so the per-model frustum test leaves out their parts behind the view. It changes those
models' stored units, so it waits for a planned rebuild of the world. Measured offline on the v0.0.65 world with the
same rule, from the same two spots (faces tested per view in all):

| Spot | Whole models (mean / heaviest view) | Tiles at 128 (mean / heaviest view) | Tiles at 256, the frame grain |
| --- | ---: | ---: | ---: |
| Deck | 8,042 / 16,378 | 6,399 / 12,927 | 7,896 / 15,996 |
| Pier | 8,658 / 16,494 | 7,166 / 11,805 | 7,547 / 12,804 |

The frame's own grain gives the 166 by 610 unit ship only three tiles, hence the smaller grain. The two models
then take 5.8 passes a view on average from the deck and 3.8 from the pier (1.2 and 1.0 whole; at most 10).

The other room maps: the census office's interior pieces have the hollow profile too, but none of its 193 placements
has exact standing bevels (the map has 3,145 clipnodes for 26,787 drawn faces) and none of its models is room-sized
(the largest kit piece spans less than half of the room on two axes), so neither method applies there. The two debug
scenes have no placed models, and every CHIM room already takes the rooms' rule (no room type defaults to exact
bevels). The hold was the only case.
