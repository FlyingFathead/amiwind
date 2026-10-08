# COLLISION-STAIR-SLOPE-32: Convex collision proxies make stairs unclimbable

| | |
| --- | --- |
| Reported by | owner reports and the stair walkability gate |
| First noticed | 8 October 2026 (Balmora stairs reported in v0.0.24) |
| Where | converted stairs and slopes; staircases listed on the page |
| Reproduction | always for the listed flights |
| Duplicate of | none (parent of the STAIRS-*-32 pages) |
| Persists in | v0.0.32 (rule and gate not in this release) |
| Severity | medium (blocked stairs) |

## Status: 8 October 2026

Open: rule, switch and gate in source on branch v0.0.32-stair-walk (not yet in a build). Five
staircases still fail the gate and are tracked separately (below). Owner order 8 October 2026:
stairs follow Morrowind's own rules in the next build, and a build fails on any unclimbable
flight of stairs.

In v0.0.32: the stair rule, the gate (`tools/stair_walk.py`) and the converter side of the `follow_original_stair_rules` setting are on a development branch and not in v0.0.32. v0.0.32 has the setting in the builder configuration (on by default) and the Vivec Arena stair repair from [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md).

## Symptom

Stairs that cannot be walked up although every step is lower than the step height: the Vivec
Arena bridges and canton stairs in dev1 (owner reports, fixed by
[VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md)), Balmora stairs in v0.0.24 (owner:
"some too steep angle"), and the staircases listed below.

## Where

Collision proxies of converted meshes (`tools/mesh_geometry.py`, used by every converter through
`collision_pieces`) and the movement rules (`STEPSIZE` 8.5, `AW_WALKABLE_Z` 0.69).

## How it happened

Morrowind collides against the authored triangles (the NIF `RootCollisionNode`, otherwise every
triangle; OpenMW 0.51 `components/nifbullet/bulletnifloader.cpp`), steps up 34 units (8.5 here)
and stands on slopes up to 46 degrees (`components/misc/constants.hpp` lines 43-44). AmiWind
collides against convex proxies. A proxy that takes in a wall, a railing arc or a block beside a
flight closes the treads, or turns them into a slope steeper than walkable; a thin surface plate
with approximate (axial) standing bevels grows into a turned stairwell.

History. v0.0.24 (30 September 2026) fixed the Balmora reports in two ways, both kept:
the walkable-floor limit moved from 0.7 to `AW_WALKABLE_Z` 0.69 (an authored ramp of
`ex_hlaalu_b_11` measured 45.76 degrees; [stair ramp walkability](../STAIR_RAMP_WALKABILITY.md)),
and a hand-made list of Hlaalu models (`town_regions.visual_profile`) keeps their authored
surfaces with exact bevels. VIVEC-ARENA-ACTORS-32 added the exterior architecture rule (closed
space deeper than a step gets plates). None of these covered every mesh, and nothing measured
stairs after conversion.

## Why it was not caught

No check walked the stairs of a converted map; the hand list came from owner reports.

## Reproduction

`python3 tools/stair_walk.py <image>/id1 --out stair-walk.json --jobs 8` on the v0.0.32-dev2 image:
158 failing flight steps (140 in the dev1 Vivec Arena maps, 1 Balmora, 6 Seyda Neen, 15 in
interiors).

## Repair

- Stair rule in the shared layer (`mesh_geometry.stair_treads`, `mitigate_stairs`, used by
  `collision_pieces` for every converter): a convex piece that buries a stair tread (too steep, or
  more than a step over it) becomes the authored surface plates with exact bevels (a walkable clip
  ramp through the nosings past a plate budget, or in the `ramps` measurement mode). Surface-plate
  meshes with stairs get exact bevels on all their plates. Risers above 8.5 are not stairs.
- Switch: `follow_original_stair_rules` (true by default; `--no-follow-original-stair-rules` for
  debugging), exported to every worker (`tools/mesh_geometry_env.py`).
- Gate: `tools/stair_walk.py` in the image step (`stair-walk.json`): every flight step of every map
  must be walkable up and down by the standing box with the engine's step and slope rules.
- Old methods kept: the 0.69 limit, Balmora's hand list and the architecture step rule.
- Design note: [STAIR_RULES.md](../STAIR_RULES.md).

## Verification

Owner's data, inside Docker, 8 October 2026:

| Map family | Flight steps (dev2 image) | Failing before | Failing with this branch |
|---|---|---|---|
| Vivec Arena | 181 | 140 (dev1 maps) | 0 (maps of the VIVEC-ARENA-ACTORS-32 fix) |
| Balmora | 300 | 1 | 1 ([STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md)) |
| Seyda Neen exterior | 9 | 6 | 6, recorded stage, reported not gated ([STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md)) |
| Interiors | 442 | 15 | 4 ([STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md), [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md), [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md), [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md)) |
| Open world (vf) | 0 flights | - | - |

- Where the rule changes collision: no Balmora (226), Vivec Arena (68), open-world (173) or
  convex interior (498) model. Seyda Neen exterior: `ex_common_lighthouse`,
  `ex_common_house_tall_02`, `ex_nord_win_02` (recorded stage in v0.0.32, so no shipped map
  changes until it is regenerated). Plate meshes with stairs (Seyda rooms, prison ship; Balmora
  rooms already exact): warehouse +12,191 clip nodes (+335 KB), lighthouse +3,799 (+104 KB),
  Addamasartus +10,009 (+279 KB), Eldafire +118, prison ship +14,935 (+414 KB). Every rebuilt map
  passes the modelled heap estimate (lowest clearance: Addamasartus 620,236 B, before 899,116 B;
  prison 1,334,300 B, before 1,748,092 B).
- Cost: collision proxies of all town and world models, rule on vs off: same CPU within 0.4 s; the
  13 Seyda rooms convert in 41.5 s instead of 22.4 s (8 workers); the gate takes 269 s for the
  497 maps of the dev2 image (8 workers). Engine-side hull visits per point test were not
  measured; only the maps above change.
- Tests: `tests/test_stair_rules_collision.py` (buried flight gets authored plates, clip ramp
  variant, walkable ramp unchanged, steps above 8.5 stay a wall, switch off, plate meshes with
  stairs, plumbing into build.py and the image step, no collision builder outside the shared
  function) and `tests/test_stair_walk.py` (synthetic BSP: open flight passes, filled flight
  fails with position and rise, `require` stops the image, recorded maps exempt, lone steps
  advisory, `check_polys` interface).
- Pending: a build with the switch on, an in-game check of the listed staircases.

## Prevention

The image-step gate on every build's final maps, on by default with the stair rules.
