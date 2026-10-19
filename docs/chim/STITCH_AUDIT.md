# CHIM/legacy border audit (the stitcher, step 1)

_Last updated with AmiWind v0.0.36 (11 October 2026)._

A CHIM area inside the legacy open world (a town table row with a world handoff, such as a CHIMport test
block) meets the legacy region maps at its handoff core. The engine changes maps there
(`aw_world.c` `AW_WorldDestination`): a player standing in a legacy region map enters the CHIM area as
soon as he is inside its core, and leaves it again 32 units past the core. Position, view and velocity
are carried; nothing is prefetched. The two maps must agree at that line, or the player sees a step,
drops or rises on arrival, or watches objects appear.

`tools/chim/stitch.py audit` measures that border from the files of one finished build run. It reads
only; it changes nothing and builds nothing. Fixes come later, each at the shared layer with its own
regression test; this audit is how they are judged (numbers before and after, not eyes).

    python3 tools/chim/stitch.py audit --run RUN [--area ID ...] [--out REPORT.json] [--no-arrival]

`RUN` is a build run folder holding at least `chim-world/` (the CHIM world and its far layers),
`chim-town-<id>/` for each area and the legacy region maps (`world-terrain/world-regions.json` and
`<stage>/vfNNNN/scene.bsp` of the most final stage present: world-flora, world-scenery, world-terrain).
The areas are the town table rows with a world handoff whose frame is in the run's CHIM world (all of
them by default: the audit is island-wide). The core, origin and draw distance come from the town
configs of the source tree that runs the audit, so run it from the commit the run was built from.

CHIM region frames ([CHIM_REGIONS.md](CHIM_REGIONS.md), one frame per exterior cell, a divided cell included)
are audited with `--regions all` or `--regions X,Y` (repeatable; with `--regions` and no `--area` only the
region frames run). Their rows come from the run's ownership table (`chim-world/chim-regions.json`): origin
the cell centre, core the cell, draw distance 540. An edge that meets another CHIM frame (a town or another
region frame) is listed under `frame_neighbours`, not measured as a legacy border. Each audited area prints a
`[i/n]` progress line.

A report holds game-derived positions and object lists: keep it with the build, not in the repo.

## What is measured

Coordinates are the engine's global units (Morrowind units x 0.25, one cell = 2048). Each core edge
(N = +y, E = +x, S = -y, W = -x) is sampled every 8 units along lines parallel to the edge, at outward
offsets from the edge (negative = inside the core). Samples sit at the middle of each 8-unit step, so
none lies on the 128-unit tile grid of either side.

- **Heights** at offsets -896, -512, -256, -128, -64, -32, 0, 32 and 64 (where both sides have ground:
  the CHIM frame ends where its ground ends: 96 units past the core with the inset, `terrain_margin` past it otherwise). Legacy: the highest upward ground face
  (textures `gN`) of the region map whose core holds the point, from the compiled map. CHIM: the
  highest upward face of the frame's chunk terrain at the point. Delta = CHIM - legacy.
- **Refinement (shoreline)**: the legacy converter inserts original 32-unit samples into tiles where
  the ground crosses the water level (`prepare_world_regions.terrain_triangles`); a CHIM frame built
  without them keeps the plain tile grid. A sample is *refined* when the legacy ground there differs
  from the plain grid through its tile's four corners (triangles 0-1-2, 0-2-3) by more than 0.01.
  `heights_unrefined` is the delta over the other samples; `chim_vs_legacy_grid` compares the CHIM
  ground with that plain legacy grid at every sample (0 means the CHIM terrain is the legacy grid).
- **Contents** one unit above the higher ground, on both maps (point hull): empty, water or solid.
  A sample is a mismatch when one side is solid or liquid and the other is not.
- **Arrival** at the handover lines, offset 0 (enter) and 32 (leave): the height where the standing
  hull (hull 1) rests, by bisection to 1/32 unit, on the legacy map and on the CHIM chunk holding the
  point. Delta = CHIM - legacy: what the player drops or rises when the map changes. A point where a
  side has no floor or no free space is counted as `not_measured`, never guessed. Only the terrain
  hulls are traced (placed objects are listed under objects). `arrival_unrefined` leaves out refined
  samples.
- **Far layer**: the frame's far terrain sidecar (`chim-world/far/<cx>_<cy>.far`) at its own sample
  points in the band outside the core (outward offset 0 to 896, along the edge to 896 past each end),
  against the legacy ground at the same point raised to the water level, as the far layer stores it.
  Object stamps are counted, not applied (the engine leaves them out by default).
- **Far band gap**: the far layer is drawn beyond the fog plane only, and the frame's chunks end at the
  frame edge. From the handover lines the depth with no ground at all is the fog distance (the row's
  draw distance) less the distance to the frame edge: `gap_at_enter` (standing on the core edge) and
  `gap_at_leave` (standing 32 units past it, the last point still on the CHIM map).
- **Objects** whose drawn box meets the band (along the edge, offset -896 to +896), per side: legacy
  region map entities with a source reference (`aw_ref`; each reference once, although overlapping
  region maps repeat it) and CHIM placements owned by the frame, matched by source reference:
  `both`, `legacy_only`, `chim_only` (each with its offsets from the edge and its cell), `moved`
  (both, origins more than 2 units apart), `cut_by_handover_line` (the box spans offset 0) and
  `cut_by_frame_edge` (a CHIM box reaching past the frame edge).
- **Area census** (`objects` of the area): CHIM placements inside the core that no legacy region map
  draws (no entity with the same reference): they are not seen from the legacy side and appear at the
  handover. Counted by model class with their tallest drawn box (`chim_only_by_class`).

Two CHIM areas whose cores touch: samples outside a core that lie in another audited area's core are
skipped and the neighbour is named (`frame_neighbours`).

## Limits and status

The limits are written into every report (`limits`). Per border cell (a Morrowind cell the edge runs
through, inside the core):

| Measure | warn | fail |
| --- | --- | --- |
| height delta, max over the cell | > 1.0 | > 4.5 (the actor refit rule) |
| arrival delta, max per way | > 1.0 | > 4.5 |
| contents mismatches | any | - |
| far layer step | reported | not judged yet |

An edge's status is the worst of its cells and its far band gap (`warn` while the gap is above 0). An
area's status is the worst of its edges; the report's, the worst of its areas.

## Report format aw-stitch-report-1

JSON, one object:

- `format`: `aw-stitch-report-1`; `generated` (host time); `run` (folder name and the status/commit
  fields the run records); `source_version` (the auditing tree's VERSION); `limits`; `sampling`
  (`step`, `band`, `height_offsets`, `arrival_offsets`, `tile`, `water_level`, `legacy_stages`);
  `world_checks` (structure problems found while reading the CHIM world, normally empty); `status`.
- `areas`: one object per area: `id`, `cell`, `origin`, `core`, `frame_extent`, `draw_distance`,
  `status`, `far_sha256`, `legacy_maps` (name -> `sha256`, `stage`: every region map read),
  `objects` (the area census: `chim_inside_core`, `drawn_by_legacy`, `chim_only`,
  `chim_only_by_class`), `worst_samples` (the 25 largest height deltas: `abs`, `edge`, `offset`, `x`,
  `y`, `legacy`, `chim`, `shoreline`) and `edges` (N, E, S, W).
- An edge: `line`, `along`, `samples_along`, `offsets`, `heights`, `heights_unrefined`,
  `chim_vs_legacy_grid` (each `{n, max, mean}` of absolute deltas), `shoreline_samples`, `missing`
  (samples without ground per side), `frame_neighbours`, `arrival` (`enter`, `leave`: `{n, max, mean,
  not_measured}`), `arrival_unrefined`, `contents_mismatch`, `far` (`{n, max, mean, stamps,
  step_local}` or `not measured`), `far_band_gap` (`frame_edge_beyond_core`, `fog_distance`,
  `gap_at_enter`, `gap_at_leave`, `status`), `objects` (above), `cells` and `status`.
- A cell: `cell`, `heights`, `heights_unrefined`, `chim_vs_legacy_grid`, `shoreline_samples`,
  `contents_samples`, `contents_mismatch`, `arrival`, `arrival_unrefined`, `far_step`, `status`,
  `reasons`.

## What comes next

The audit is step 1 of the stitcher plan. Steps 2 and 3 are in: a frame inside the legacy world owns
its cell box and carries a terrain-only margin (`terrain_margin`, at least draw distance + 32; the town
table refuses a handoff core closer to the frame edge unless it selects `"handoff_core": "inset"`), and
town frames take the legacy shoreline triangulation (`--chim-terrain-shoreline`, default on); on
bcoast_x7y2 the audit then reads height steps 0, arrival within 0.031 units and far band gap 0 on every
edge. Next: the terrain light bytes, prefetch across the handover, then walks across every edge in the emulator
(headlamp pairs) and the original game at the same poses. Once its limits are agreed, the audit runs
in every build with CHIM areas inside the legacy world and its report joins the build receipt.
