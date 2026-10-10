# CHIM frames in the open world (design)

Status: design, 9 October 2026. Nothing here is built yet.

Live conversion status of every cell: [CHIM cell tracker](CELL_TRACKER.md); the island-wide
conversion tool that fills it (CHIMport) comes with the next release.

## Goal

Exterior cells converted by the CHIMport runner ([CHIMport](CHIMPORT.md): island results and
[hull policy pending](CHIMPORT.md#hull-policy-pending)) become playable next to the legacy open world in the
next release: the player walks from a legacy region into a CHIM frame and back, and every gate that a
CHIM town passes applies to these frames. The legacy open world stays as it is and selectable; nothing
is deleted. This is a step towards the M4 grid (WORLD_FORMAT.md, "Planned: all of Vivec (M3) and the
open world (M4)"), which later replaces the hand-over at frame edges with crossing without a map load.

## What exists

- CHIMport writes one CHIM world per cell (`world.cwi` per cell) with per-cell gates: format, stair walk,
  hull depth, seams, sky-bank texels and heap rings. Of its first 166 cells, 69 passed, 86 are empty
  (water) and 11 failed with "measure-empty-world".
- The image step takes one CHIM world, and the engine runs CHIM only for towns of the town table: a
  town's `maps/<town>-chim.bsp` replaces its region maps (`chim_world.c` TownFile / TownMap).
- The engine's open-world hand-over (`aw_world.c` AW_WorldDestination) already treats town-table frames
  as destinations. A point inside a table frame's core box goes to that frame (with its `-chim` map when
  it exists); any other point goes to the legacy region `vfNNNN` whose core holds it. Balmora's CHIM
  frame already hands over this way at its open edges.

## Design

### 1. One world from many cells (multi-cell world build)

- Frames are 3 x 3 cells on the M4 grid: centres at cells (3i, 3j + 1), so Balmora's frame is one of
  the tiles. A frame is built when CHIMport converted its cells; a frame whose cells are partly
  unconverted is not built (no half frames).
- `tools/chim_build.py --frame CX CY` (repeatable) builds grid frames from the per-cell sources the
  CHIMport runner already uses: canonical LAND ground, the world scenery export by cell, world flora.
  All frames go into one world (format 0.5 holds many frames; frames do not overlap, which the
  writer's frame-box check already refuses).
- The shared unit cache keeps every model and texture stored once across all frames, as CHIMport's
  `units/` already does.
- Placements belong to the frame that holds their origin. A placement that reaches into a neighbouring
  frame is drawn only from its own frame until format 0.6 ("Reach across frames"); the edge check (4)
  reports every such placement.

### 2. Open-world frame maps

- `chim.frame_map` gets an open-world entry: the frame's legacy maps are the world regions `vfNNNN`
  whose core boxes meet the frame (from `world/regions.awr`), instead of a town's region table.
- From those maps it copies the frame's point entities inside the frame's bounds (actors, flora sprites,
  lights, sounds), with the same accounting, parity and actor-ground checks as a town frame map. The
  statics parity compares the CHIM frame's placements with the legacy statics inside the frame.
- Each frame map states `_chim_frame`, `_chim_hunk_rest` and, from the streaming setting, the streamed
  statics. Its name is `f<i>_<j>-chim.bsp` on the grid (short names, under the 30-character limit).

### 3. Frame selection and hand-over to the legacy world

- Each built frame becomes a row of the town table (`config/towns.json`, generated into the engine by
  `tools/town_table.py`) of a new light kind, `frame`: name, origin (the frame centre x 0.25), core box
  (the frame's bounds), the world hand-over flag, and nothing town-specific (no doors, sky or fog tables
  of its own: it uses the open world's).
- The engine needs no new mechanism: AW_WorldDestination already prefers a table frame's core over the
  legacy regions, and TownMap picks the frame's `-chim` map. Walking out of a frame's core hands over to
  the legacy region holding the point, as Balmora's open edges do today.
- Engine work: check the fixed tables sized by AW_TOWN_COUNT (about 25 more rows for 174 cells), the
  `dbg tp` names, saves (a save inside a frame names the frame), and the world map click (frames first).
- A frame row exists only when its frame map is in the image; a build without CHIM frames keeps today's
  open world.

### 4. Edge checks

At every frame edge that meets the legacy world, in the image step:

- Ground: the frame's chunk terrain and the neighbouring legacy region's terrain come from the same
  canonical LAND triangles. The check samples both along the edge (every 8 units, the standing box's
  footprint) and refuses a step in height or a gap.
- Hand-over arrival: for samples along the edge, the arrival on each side must be a standing spot
  (the engine's arrival search on each side's collision), both ways.
- Placements cut by the frame edge (point 1): listed, with their bounds; until format 0.6 they are drawn
  from their own frame only, so a building straddling an edge is half missing in the other frame. The
  check refuses a frame whose edge cuts a placement's walkable surface.
- Doors in the frame: each door's link still resolves (the door bank names the frame).
- The far layer: when the player stands in a frame, the distant ground beyond its edges comes from the
  far-terrain layer (CHIM-FAR-TERRAIN-33); when in a legacy region, the CHIM frame is distant ground like
  any other. Both must show the same horizon (HORSTATOR APPROVED, sprites keep their outlines); A/B at
  fixed poses on both sides of an edge.

## Visibility (the vis story)

- Inside a frame: as every CHIM frame, placements are linked to the leaves their boxes touch, each chunk
  has its visibility row and placement list, and the renderer counters (entities sent, faces drawn and
  clipped, BSP nodes per face) are checked before and after.
- Across a hand-over edge only one side is loaded at a time, so the frame never draws the legacy
  region's statics or the other way round; what lies beyond the edge is far layer and fog, as at any
  region edge today. No placement is drawn twice.
- Large models in the frames use the large-model cut (`cut_models_over`) when they are wider than two
  chunks, so they stay under MAX_ENT_LEAFS and are culled per piece.

## Memory

Every frame passes the CHIM heap gate (the active ring at every position, the load ring and the largest
block reported) and the frame-map heap gate (the whole-map zone with the frame map's own Hunk rest).
CHIMport's per-cell heap figures (least headroom about 5.8 MB in a passed coastal cell) are per cell; a
frame holds nine cells, so the frame gate is the authority. Dense frames are flagged by the predictor and
the world-metrics heatmap before they are built.

## Disk

All frames share one world's PAKs, sharded under 1 GiB, names under 30 characters, at most 72 entries
per directory, every partition below 2 GiB and starting below 2 GiB, images below 4 GiB (the disk-layout
gate). CHIMport's 69 passed cells are 68.9 MB as separate worlds; one world stores shared models and
textures once.

## Gates and tests

- Builder: a frame list builds one world; frames do not overlap; a frame with unconverted cells is
  refused; the frame map's open-world entry copies exactly the frame's point entities (fixture of two
  legacy regions meeting inside a frame).
- Image step: the four edge checks above, with a report per edge; the frame-map heap gate per frame.
- Engine: a host test that AW_WorldDestination picks the frame inside its core and the legacy region
  outside it, both ways; `dbg tp` to a frame by name.
- A MiniWind sandbox of one CHIMport frame and its legacy neighbours (a preset row): walk across each
  edge, save and load inside the frame, compare with OpenMW at the same poses.

## Order of work

1. Multi-cell world build for grid frames from CHIMport's per-cell sources; one frame first (a fully
   converted coastal frame).
2. The open-world frame-map entry and the frame row kind in the town table.
3. Edge checks and the MiniWind sandbox; A/B against the legacy region and OpenMW.
4. All frames with every cell converted; frames with missing cells wait for CHIMport.

## Decisions (owner, 9 October 2026)

- Frames whose missing cells are only water (CHIMport's "empty" cells) ship. A frame missing any
  cell that holds land or placements waits for CHIMport.
- A frame whose edge cuts a placement is refused until format 0.6 (reach across frames). There is no
  known-finding route for it.
- Vivec keeps its eight district frames until M4 frames span edges; two city frames are the possible
  next step (CHIM-FRAME-COORD-RANGE-33).
