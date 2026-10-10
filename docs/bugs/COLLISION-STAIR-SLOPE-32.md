# COLLISION-STAIR-SLOPE-32: Convex collision proxies make stairs unclimbable

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 8 October 2026, in v0.0.24 |
| Where | converted stairs and slopes; staircases listed on the page |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.24, v0.0.32 (last seen) |
| Severity | medium: Blocked stairs. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.24 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 8 October 2026](#status-8-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 8 October 2026

Open: rule, switch and gate in source (not yet in a build). 9 October 2026: no staircase fails the
gate any more on the maps rebuilt with the rule (legacy) or on the CHIM Balmora and Seyda Neen
worlds; the last four were gate artefacts, fixed on branch v0.0.33-stairs-2 (see "Gate after the
last fixes" below). Was: five staircases still fail the gate and are tracked separately (below). Owner order 8 October 2026:
stairs follow Morrowind's own rules in the next build, and a build fails on any unclimbable
flight of stairs.

8 October 2026: the rule, the switch and the gate are merged on v0.0.33-dev. Until the five
STAIRS-*-32 flights are repaired, a legacy image build from v0.0.33-dev stops at the stair gate;
the source gate (tests, preflight, engine build) is not affected. Repairing those flights is the
next stair job.

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

### Gate after the last fixes (9 October 2026, branch v0.0.33-stairs-2)

The four flights still failing were gate artefacts, not collision faults (causes on their pages):
a cave floor read as a step ([STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md)), a start inside
an authored ramp under a low lintel ([STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md)), and
start boxes touching a wall or a closed door within the collision plates' 0.2 thickness
([STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md),
[STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md)); the gate rules are in
[STAIR_RULES.md](../STAIR_RULES.md). Previous gate vs this gate on the same maps (owner's data,
inside Docker, flight steps passed / failed / untestable):

| Maps | Previous gate | This gate | Gating failures |
|---|---|---|---|
| Legacy, rebuilt with the rule: 64 Balmora regions | 295 / 1 / 4 | 296 / 0 / 4 | 1 -> 0 |
| Legacy, rebuilt with the rule: 58 interiors (Seyda Neen rooms, prison ship, Census, Balmora rooms) | 419 / 6 / 15 | 420 / 0 / 18 | 4 -> 0 |
| v0.0.32 release maps (no rule): Vivec Arena | 197 / 0 / 0 | 197 / 0 / 0 | 0 -> 0 |
| v0.0.32 release maps (no rule): all 204 | | | 18 -> 13 (the rest: pre-rule warehouse 7 and lighthouse 1, recorded Seyda Neen lighthouse 5; the rebuilt maps clear them) |
| CHIM Balmora world | 294 / 1 / 4 | 295 / 0 / 4 | 1 -> 0 |
| CHIM Seyda Neen world (built with the slanted-riser cut) | 7 passed (1 covered, 1 advisory) | 7 passed | 0 -> 0 |

No flight step that passed before fails or becomes untestable. Rows that disappear are not steps
(two tilted cave-floor triangles in Addamasartus, a tilted dock plank at the intro docks): of all
step rows, 1,643 -> 1,565 on the rebuilt maps; ramp rows unchanged. Regression fixtures:
`tests/test_stair_walk_cases.py`.

## Prevention

The image-step gate on every build's final maps, on by default with the stair rules.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`). Convex collision proxies invent steep faces or bury authored surfaces; Morrowind collides with authored geometry (step up 34 units, slope up to 46 degrees). Rule: follow_original_stair_rules plus a walkability gate. See [families](README.md#families).

- [BUILD-HULL-ROUTE-BUDGET-33](BUILD-HULL-ROUTE-BUDGET-33.md): Routed standing hulls with copies overflow a legacy map's shared clipnode budget
- [BUILD-ROUTED-FLORA-RESERVE-33](BUILD-ROUTED-FLORA-RESERVE-33.md): Routed standing hulls push a legacy open-world map past the flora collision reserve: the full build stops in world-flora (vf0779)
- [BUILD-STAIR-FLAG-INERT-32](BUILD-STAIR-FLAG-INERT-32.md): The stair rule build option does nothing in v0.0.32
- [CHIM-HULL-STAIR-EDGE-33](CHIM-HULL-STAIR-EDGE-33.md): With the qbsp-compiled terrain hull on Balmora's regular ground, one flight of stairs fails at a chunk edge
- [COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md): Convex collision proxies lose and invent authored surfaces
- [COLLISION-HULL-CHAINS-33](COLLISION-HULL-CHAINS-33.md): 183 brush models across the island collide through standing-hull chains 512 to 31,659 clipnodes deep
- [COLLISION-NC-FLAGS-32](COLLISION-NC-FLAGS-32.md): Morrowind no-collision and editor-marker flags (NC, NCC, MRK, AvoidNode) are ignored by the mesh converters
- [COLLISION-RCN-SCOPE-32](COLLISION-RCN-SCOPE-32.md): Authored collision meshes (RootCollisionNode) are used by some converters only
- [COLLISION-SEYDA-PREVIEW-BYPASS-32](COLLISION-SEYDA-PREVIEW-BYPASS-32.md): The legacy Seyda Neen preview builds its own convex collision
- [COLLISION-TRACE-COST-33](COLLISION-TRACE-COST-33.md): Movement traces near large models walk long standing-hull chains: tens of ms per trace on a slow 68040 (emulator-relative)
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate
- [VIVEC-ARENA-TP-ARRIVAL-32](VIVEC-ARENA-TP-ARRIVAL-32.md): dbg tp vivec_arena leaves the player at the frame origin under the water
- [VIVEC-TEMPLE-STAIRS-33](VIVEC-TEMPLE-STAIRS-33.md): Palace steps and High Fane quarter flights fail the stair gate on the CHIM Vivec Temple frame

Related bugs in other categories:

- [CHIM-STAIRGATE-SLOW-33](CHIM-STAIRGATE-SLOW-33.md): The CHIM stair gate takes over 10 minutes on the Balmora and Vivec Arena world

<!-- END GENERATED CATEGORY -->
