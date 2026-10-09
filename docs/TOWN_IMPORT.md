# Town import

Balmora was the first town converted into bounded exterior sub-cells. The same
converter now imports any town from a config file: `tools/import_town.py
--town <id>`. `tools/prepare_balmora.py` remains as a thin wrapper with the old
command line and byte-identical Balmora outputs. The first new town is Vivec's
Arena canton (`config/vivec_arena.json`).

<!-- contents start -->
## Contents

- [How Quake does it](#how-quake-does-it)
- [Town config](#town-config)
- [Town interiors and doors](#town-interiors-and-doors)
- [Arrival](#arrival)
- [Collision of exterior architecture](#collision-of-exterior-architecture)
- [Adding a town](#adding-a-town)
- [Vivec, Arena](#vivec-arena)
- [Vivec](#vivec)
- [vis options](#vis-options)

<!-- contents end -->

## How Quake does it

Nothing here is a new engine mechanism. A town frame is an ordinary Quake map:
terrain brushes in `worldspawn`, every placed mesh a `func_wall`, an
`info_player_start`, compiled by qbsp, vis and light. Quake sends coordinates
as 1/8-unit shorts (`MSG_WriteCoord` in `common.c`), so one map spans at most
+-4096 units: 4 original cells at the 0.25 scale. A town therefore uses one
frame of at most that size, split into sub-cell BSPs that share the frame's
coordinates, and the runtime swaps the resident world model as the player
crosses a core (`aw_region.c`), the way `map` loads a level.

The engine knows towns only through a table, like the other converted
`id1` and `world` tables: `engine/aga/src/aw_town_table.h`, generated from
`config/towns.json` and the town configs by `tools/town_table.py`. No town
name is compiled into the region, world, fog, scenery or scene code.

## Town config

A converted town is one JSON file in `config/`. The frame and sub-cell
settings are Balmora's schema; the `town` block names what the converter used
to hard-wire for Balmora.

| Field | Meaning |
| --- | --- |
| `source_cell`, `source_radius` | Audited square of original cells (every cell needs LAND) |
| `centre`, `scale` | Original point of the frame's local origin; scale 0.25 |
| `bounds` | Frame in local units, a whole number of cores per axis, inside +-4096 |
| `reference_margin` | Optional frame filter (for frames not equal to the audited cells): keep residents and markers whose origin is inside the bounds plus this margin, and every visible placement whose whole-object bounds reach into them (measured in a scratch export of the audited cells) |
| `core_size`, `overlap`, `hysteresis`, `draw_distance` | Sub-cell layout; the overlap must cover `sqrt(2) * draw + hysteresis + 32` |
| `terrain_step`, `terrain_material_repairs` | Terrain quads and checked tile repairs |
| `entity_budget`, `model_budget`, `collision_margin` | Per-region limits (Balmora: 1000, 220 inline models, 224) |
| `region_core_overrides` | Measured core splits, by region name |
| `town.id` | Registry id (`config/towns.json`) |
| `town.title` | Display name (save list, messages) |
| `town.map` | Runtime map name (`sv.name`), also the arrival alias `maps/<map>.bsp` |
| `town.map_prefix` | Two letters; region maps are `<prefix>000` upwards (`bm`, `va`; never `vf`) |
| `town.region_cap` | Native region directory capacity, at most 64 (`AW_REGION_MAX`) |
| `town.message` | `worldspawn` message of every region map |
| `town.region_file` | Native directory (AWBR1), e.g. `balmora-regions.txt` |
| `town.door_file` | Door bank (AWD3); must be `scene-doors-<map>.txt` |
| `town.visual_group` | Group key in the scenery index |
| `town.arrival` | `{"travel_npc": id}`: that NPC's travel destination inside this frame; or `{"source_position": [x, y, z], "source_rotation_z": radians}`: an explicit original pose, converted like a travel destination |
| `town.return` | `{"travel_npc": id, "config": file}`: return travel into another area; or `null` (the directory then records `0 0 0 0`) |
| `handoff_core` | Optional: the frame-local rectangle this town owns in the world handoff. Default: `bounds` inset by 96. Must stay `draw_distance + 32` inside the bounds, so the frame edge is never in view from a point the player can stand in |
| `interiors` | Optional: `[{"cell": original interior cell, "exclude": reason}]`, the rooms reached through the town's load doors. Append only: a room's position gives its map name `<prefix>i000` upwards and its save ID. `exclude` keeps the slot and leaves the room unconverted; its doors show it as unavailable |

`config/towns.json` lists the runtime towns in stable save order (append,
never reorder) with the engine-only facts:

| Field | Meaning |
| --- | --- |
| `id`, `config` | Town id and its config file |
| `town` | Inline town block for towns not converted by `import_town.py` (Seyda Neen) |
| `world_slot` | 0/1: Seyda's and Balmora's handoff rows in `world/regions.awr`; -1: the handoff frame comes from the town config (`bounds` inset by 96) and is used once `maps/<map>.bsp` is installed |
| `flags` | `seyda_scenes`, `legacy_payload`, `own_doors`, `scenery_catalogue`, `teleport_arrival`, `ground_place` (see `aw_town.h`) |
| `travel` | `{"npc": display name, "target": map, "use_return_point": bool}` or `null` |
| `shipped_since` | Optional `vX.Y.Z`, towns after Seyda and Balmora only: the release that first ships the town. Every default build imports it (`vivec_arena`: `v0.0.32`); the release feature `extra-towns` in `config/release-features.json` takes its files from this row. Not allowed on a blocked town |
| `withdrawn` | Optional reason, on a town with `shipped_since`: the town is left out of default builds (and the release feature) until the field is removed; `--extra-town` builds it again. `vivec_arena`: withdrawn from v0.0.33 (CHIM-ARENA-MEMORY-33) |
| `blocked` | Optional reason: the town is configured but fails a limit. It keeps its table row and save IDs; `build.sh --extra-town` does not offer it and `import_town.py` converts it only with `--dry-run` |

Towns after Seyda and Balmora get save IDs from `AW_TOWN_MAP_BASE` (16384) in
table order, clear of the open-world and interior ranges. Town interiors get
save IDs from `AW_TOWN_INTERIOR_BASE` (20480): towns in table order, each town's
rooms in list order. `tools/town_table.py` writes their map names, titles
(the original cell names) and owning town into the same header.

## Town interiors and doors

How Quake does it: a room is a level of its own and a load door is a level
change with a spawn point, exactly as for Balmora's interiors; the engine
needs only the rooms' save IDs. `tools/import_town.py` converts every listed,
not excluded room with the shared interior converter
(`prepare_area.build_room`, Balmora's interior policy: every selected
placement kept, exact standing bevels on hollow shells; a room reached only
from other rooms takes its spawn from the original interior entrances),
places its residents, and writes the door banks (`tools/town_interiors.py`):

- the town's exterior bank links each load door into a converted room with
  the door's original arrival;
- each room gets `doors-<room>.txt`: doors into other listed rooms (any town),
  and exits to the town frame whose handoff core holds the original exit
  point, in table order (the engine's own world-handoff rule);
- a door into a room that is not listed, excluded or failed keeps target `-`:
  the engine shows "Interior unavailable" and never loads it.

A room also fails when its coordinates reach the +-4096 network range
(INTERIOR-COORDS-31) or it needs more than 220 inline models
(INTERIOR-INLINE-LIMIT-31); the build stops, so a failing room must be listed
with `exclude` and its reason.

`--dry-run` converts every region and room, records each limit failure in
`<out>/dry-run.json` instead of stopping, and publishes nothing. Use it to
measure a new town before writing its exclusions.

## Arrival

A town's arrival (`town.arrival` or its travel NPC) is an original pose: a
door or travel exit point, lifted from feet to origin. The importer stores the
engine's own standing spot for it: the arrival search of `aw_scene.c`
(`tools/arrival_spot.py`: the point, its eight 16-unit neighbours, then 8-unit
steps down to 64; walkable floor, clear standing hull, dry feet) on the
converted collision of the region that owns it, and moves that region's spawn
entity there. A pose without a spot stops the conversion. The image step
checks every town directory on the final maps (`arrival-check.json`). In
play, a failed arrival falls back to the scene spawn point, never the frame
origin (VIVEC-ARENA-TP-ARRIVAL-32).

## Collision of exterior architecture

Placed meshes collide as a union of convex hulls unless their profile asks for
surfaces. Balmora's hand-made list (`town_regions.visual_profile`) and the
interiors use the authored surfaces (thin plates with exact standing bevels).
Every other exterior architecture mesh (`meshes/x/`) of a converted town is
measured: when its convex proxy closes more space than the engine's step
height (8.5, `STEPSIZE`), it uses the authored surfaces too
(`mesh_geometry.collision_pieces`). Deeper invented solid would be a wall or
ledge the original does not have, and would bury residents standing on the
real floor. The region report records the decision per mesh (`collision`).
No Balmora mesh reaches the limit; the Vivec cantons and bridges do.

## Adding a town

1. Find the town's centre from the original placements (its central static)
   and snap it to the 512-unit terrain material grid. Choose bounds that keep
   dense neighbours with known texinfo or heap failures outside the frame.
2. Write `config/<town>.json` (copy `vivec_arena.json`) and append a row to
   `config/towns.json`.
3. Run `python3 tools/town_table.py --write`. `build_aga.py engine` and the test
   suite fail while the header is stale.
4. Convert: `tools/import_town.py --town <id> --data-files ... --scene ...
   --out ... --qbsp ... --vis ... --light ...` (inside Docker), or add
   `--extra-town <id>` to `build.sh`, which runs the same step after Balmora's
   interiors.
6. When a release ships the town, set `"shipped_since": "vX.Y.Z"` on its row:
   from then on every default build imports it, and record the release's payload
   classes (`tools/payload_coverage.py classes`) in the same change.
5. Check every region with `tools/check_world_map_heap.py` and the region
   reports in the work directory, then A/B the arrival view against OpenMW.

## Vivec, Arena

`config/vivec_arena.json`: the canton's centre piece stands at original
(36544, -86912); the frame centre (36352, -87040) is that point on the terrain
material grid. Bounds +-1536 give 16 regions of Balmora's 768 core; overlap
896, draw distance 540, 220 inline models. The frame keeps the Temple/Ministry
regions that overflowed texinfo in the measurement run outside, and its edge
stays beyond fog range from every point of the canton. The neighbouring canton
centre pieces have their origins outside the frame, but their walkways reach
into it and carry residents, so they are kept by footprint and clipped to the
regions like everything else (VIVEC-ARENA-ACTORS-32). Arrival is the original exit point of the north Arena
Waistworks door, the side facing the Foreign Quarter bridge, turned towards
the entrance. There is no travel NPC and no return travel.

First owned-data conversion (8 October 2026, 8 jobs, 92 s): 16 regions, 392
placements kept (none lost across regions), at most 306 placements and 97
inline models per region; every region passes the modelled heap estimate
(6,519,492-8,288,004 B after hidden-surface cull and optimizer; budget
11,534,336 B); 26
door-bank rows; 7 residents (3 NPC records, classified as standing in
`config/actor_grounding.json`). An average leaf still sees 33-85 % of its
region's leaves (TOWN-VIS-OCCLUSION-31).

Shipped in v0.0.32 as an outside-only preview (`shipped_since`). Withdrawn from
v0.0.33 by owner decision (`withdrawn`: the canton bodies do not fit the CHIM
zone, CHIM-ARENA-MEMORY-33): a default build no longer imports it, and
`--extra-town vivec_arena` still builds it (BUILD-EXTRA-TOWN-OPTIN-32).

Not yet done for a playable Arena: a target playtest (arrival, region
crossings, heap on the Amiga); the Arena
interiors (doors already carry the original destination records); residents
beyond the generic idle/greeting import; the open world's handoff into the
frame is untested on target.

## Vivec

Vivec does not fit one frame: its placements span about 7,200 by 8,200 local
units, more than the +-4096 coordinate range, and one region directory holds
64 regions. Each canton is therefore its own town, appended to
`config/towns.json` after the Arena and opt-in with `--extra-town`:

| Town | Config | Prefix | Handoff core (original cells) | Regions | Rooms |
| --- | --- | --- | --- | ---: | ---: |
| `vivec_foreign` | `vivec_foreign.json` | `vq` | 3,-10 and 4,-10 | 35 | 20 |
| `vivec_hlaalu` | `vivec_hlaalu.json` | `vh` | 2,-11 and the south part of 2,-10 | 30 | 18 |
| `vivec_redoran` | `vivec_redoran.json` | `vr` | 3,-11 | 25 | 16 |
| `vivec_telvanni` | `vivec_telvanni.json` | `vt` | 5,-11 and the south part of 5,-10 | 30 | 18 |
| `vivec_temple` | `vivec_temple.json` | `vp` | the Temple, High Fane, Palace and Ministry of Truth (3..4, -13..-14) | 36 | 22 |
| `vivec_delyn` | `vivec_delyn.json` | `vd` | 3,-12 | 25 | 22 |
| `vivec_olms` | `vivec_olms.json` | `vo` | 4,-12 | 25 | 27 |

Why one town per canton: the save order and the engine table are per town
(append only), each frame stays inside the coordinate range and the region
cap, and a canton that fails a limit can be left out without touching the
others. The cantons own neighbouring rectangles of the original cell grid
(`handoff_core`); each frame adds at least draw distance + 32 around its core
in whole 768 cores, so the player walks from one canton frame into the next
(the engine's town-to-town handoff, first frame in table order wins where
cores overlap) before a frame edge comes into view. Bridges between cantons
are inside the frames; the open world's `vf` maps carry no Vivec statics, so
water outside every converted canton core belongs to the world. Arrival is
the original exit point of one canton door (`town.arrival.reason`).

Rooms: every interior reached through a canton's load doors, directly or
through other rooms, belongs to the canton of its first entrance (towns in
table order, then the lowest door reference); 143 rooms in all, including the
Ministry of Truth cells and the Daedric shrines reached from the Underworks.
The Arena's nine rooms are not listed yet: `vivec_arena.json` is unchanged.

First owned-data dry run (8 October 2026, 8 jobs, `--dry-run` per town, then
hidden-surface cull, the map optimizer and the heap estimate per map):

| Town | Regions pass | Region heap (B) | Rooms pass |
| --- | ---: | --- | ---: |
| Foreign Quarter | 35 / 35 | 6,682,548 - 11,083,364 | 18 / 20 |
| Hlaalu | 30 / 30 | 6,815,860 - 10,042,820 | 16 / 18 |
| Redoran | 25 / 25 | 6,702,404 - 9,053,588 | 14 / 16 |
| Telvanni | 30 / 30 | 7,066,404 - 10,247,620 | 15 / 18 |
| Temple | 28 / 36 | 6,362,836 - 14,703,988 | 21 / 22 |
| St. Delyn | 20 / 25 | 6,446,916 - 13,576,276 | 20 / 22 |
| St. Olms | 19 / 25 | 7,153,764 - 14,068,580 | 25 / 27 |

Budget 11,534,336 B; no map exceeded 220 inline models, the texture-mapping,
face, clipnode or extent limits outside the rooms listed below.

- Rooms listed with `exclude` (14): twelve need more than 220 inline models
  (INTERIOR-INLINE-LIMIT-31; sections at real doors, see
  [INTERIOR_SECTIONS.md](INTERIOR_SECTIONS.md)), three are over the heap
  (VIVEC-HEAP-31), one reaches 4,156 units (INTERIOR-COORDS-31). The reasons
  are in the configs. Rooms whose only way in is an excluded room (most
  shops off the Waistworks) still convert and pass; they become reachable
  when their hub does.
- `resident_exclusions`: two Telvanni residents whose models exceed the
  shared NPC baker's vertex budget at every step down to 192.
- Towns marked `blocked` in `config/towns.json` (Temple, St. Delyn,
  St. Olms): 19 exterior regions around the Temple plaza and between the
  southern cantons exceed the heap by 20,132 to 3,169,652 B
  (VIVEC-HEAP-31). The region tools cannot help within the 64-region cap at
  draw distance 540: `region_core_overrides` only reshape the grid, and the
  coverage around a smaller core is still core + 2 x 896. They stay in the
  table (stable save IDs); `build.sh` does not offer them and
  `import_town.py` converts them only with `--dry-run`.

Not yet done for playable cantons: an image build and a target playtest
(arrivals, canton-to-canton crossings, door banks on the Amiga), OpenMW A/B of
the arrival views, residents beyond the generic idle/greeting import.

## vis options

Every converter takes `--vis-mode {fast,full}` (default fast, the historical
`-fast` pass) and runs vis with threads from `--jobs`: a map compiled alone
gets all jobs, maps compiled side by side share them. light runs with one
thread per map (its multi-threaded output order is not reproducible). The builder accepts
`--vis {fast,full}` and passes a non-default mode to every map converter and
`build_aga.py image`. Full vis changes almost nothing in towns, even with the
tested occluders (measured); see
[performance/TOWN-VISIBILITY.md](performance/TOWN-VISIBILITY.md).
