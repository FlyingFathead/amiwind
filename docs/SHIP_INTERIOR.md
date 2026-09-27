# Prison-ship interior preview

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
[checkpoint validation](CHECKPOINT_017_VALIDATION.md).

`dbg scene change` opens the two-scene debug popup; Escape cancels to the console.
