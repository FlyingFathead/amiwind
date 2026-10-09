# VIVEC-ARENA-TP-ARRIVAL-32: dbg tp vivec_arena leaves the player at the frame origin under the water

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | dbg tp vivec_arena arrival (aw_scene.c, va010) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | high: The teleport leaves the player at the frame origin under the water; a v0.0.32 blocker. |
| Family | Collision shapes and climbing (stairs, ramps, walkways) (`stairs-collision`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open, a v0.0.32 blocker (owner): fixed in source on branch v0.0.32-vivec-arrival, not yet in a build. Found in the v0.0.32-dev1
FS-UAE smoke test; confirmed by the owner in dev1 play ("`dbg tp vivec_arena` teleports straight
into the sea underneath the Vivec city": GLOBAL 36352 -87040 -466, LOCAL 0 0 -116).

## Symptom

`dbg tp vivec_arena` loaded `maps/va010.bsp`, printed "Interior spawn blocked" and "arrival blocked"
in the "Scene ready" line and left the player at local 0 0 (the frame origin), under the water in
the Arena ring. Later teleports in the smoke session printed "arrival checked": those were
world-map coordinate teleports, which take another path.

## Where

`engine/aga/src/aw_scene.c` (scene arrival placement), the Arena region directory written by
`tools/import_town.py`, and the converted collision of `va010`.

## How it happened

1. The Arena's arrival is the original exit point of the north Waistworks door (DODT of ref
   219153) plus the usual feet-to-origin lift: local (48, 431.25, 490.625). It lies 1.2 units
   inside the bounds of the Waistworks entrance top (`ex_vivec_ent_t_02`, ref 171688), so the
   standing hull starts in solid there. The engine searches nearby spots (eight 16-unit
   neighbours, then 8-unit steps down to 64). In dev1 every candidate was inside the Arena
   canton's convex collision fill (ref 466157, solid up to z 520 above the canton top:
   [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md)), so the search found nothing. The offline
   port of the search (`tools/arrival_spot.py`) gives the same result on the dev1 maps: no spot.
2. With the search failed, the player stayed where the spawn function put it (the map's
   `info_player_start`, the same blocked point). A fresh client edict has `oldorigin` 0 0 0, and
   Quake's stuck recovery (`SV_CheckStuck`, sv_phys.c) moves a player in solid back to
   `oldorigin`: the frame origin, over open water, and the player sank to the sea bed.

Not a first-teleport race: every town-name teleport to the Arena failed the same way.

## Why it was not caught

Nothing checked an arrival against the converted collision; the search ran only in the engine,
and its failure path was never tested. The smoke test did not read the arrival result line.

## Reproduction

`dbg tp vivec_arena` on the dev1 image (any session).
`python3 tools/arrival_spot.py <dev1 boot>/id1` reports the Arena arrival as having no standing
spot and Balmora's stored arrival as 23 units above its floor (resolved by the search at run time).

## Repair

- **Importer, every town (`tools/import_town.py`, `tools/arrival_spot.py`):** the stored arrival
  is the original pose resolved by the engine's own search on the converted collision of the
  region that owns it; the region's spawn entity moves with it. Same rule for Balmora and the
  Arena. No spot: the conversion stops. Arena: (48, 447.25, 465.075) on the canton top in front
  of the Waistworks door, facing it. Balmora: (-209.68, -1486.10, 288.125), the spot the engine
  already chose at run time.
- **Engine (`aw_scene.c`):** an arrival tries the requested point, then the scene's spawn point
  (the town default), then the highest clear floor at the requested XY; a world-map teleport tries
  the floor first. A spot needs a walkable floor, a clear standing hull and dry feet: never water.
  If everything fails the player stays at the spawn point, and `oldorigin` is set to the spawn
  point when every scene starts, so the stuck recovery can never use the frame origin.
- **`dbg unstuck` (`aw_unstuck`):** the same spot search from the player's position (then one
  storey up). It moves the player only to a clear, dry standing spot and leaves noclip; otherwise
  nothing moves. The noclip-off refusal ("Still inside solid") now names it.
- **Gate:** the image step checks every town directory on the final maps
  (`arrival-check.json`): each arrival is a standing spot (hull clear, walkable ground within the
  step height 8.5, dry feet) and each used return point resolves to one.

## Verification

Owner's data, inside Docker, 8 October 2026:

- `tools/arrival_spot.py` on the dev1 image: Seyda Neen arrival passes; Balmora's stored arrival
  is not itself a spot (ground 23 units below; resolved at run time to 288.125); Arena: no spot.
- Arena reconverted on this branch: stored arrival (48, 447.25, 465.075), spawn moved; only
  `va010.bsp`, its `vivec_arena.bsp` copy and the region directory change. Balmora reconverted:
  only its arrival region, its `balmora.bsp` copy and the region directory change (see the commit
  report for hashes).
- Tests: `tests/test_arrival_spot.py` (search, wall over the arrival, water, importer resolution
  and spawn move, the directory check on synthetic maps); `tests/aga_scene_test.c` (an arrival in
  solid falls back to the spawn point; nothing clear leaves the player at the spawn with
  `oldorigin` there, never 0 0 0; wet spots are refused; `dbg unstuck` moves only to a clear spot).
- Pending: FS-UAE `dbg tp vivec_arena` on the next build.

## Prevention

The image-step arrival gate on the final maps, the importer's fail-closed resolution, and the
native fallback test above.

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
- [COLLISION-STAIR-SLOPE-32](COLLISION-STAIR-SLOPE-32.md): Convex collision proxies make stairs unclimbable
- [SEYDA-BLOCK-31](SEYDA-BLOCK-31.md): Invisible obstacle blocks the path on a Seyda Neen slope
- [STAIRS-ADDAMASARTUS-32](STAIRS-ADDAMASARTUS-32.md): A low step in the Addamasartus cave is blocked
- [STAIRS-BALMORA-B01-32](STAIRS-BALMORA-B01-32.md): A Balmora Hlaalu house staircase cannot be approached from below
- [STAIRS-BALMORA-WESTSOUTH-32](STAIRS-BALMORA-WESTSOUTH-32.md): A Hlaalu hall staircase in a Balmora interior has no clear foot
- [STAIRS-SEYDA-LIGHTHOUSE-32](STAIRS-SEYDA-LIGHTHOUSE-32.md): Seyda Neen lighthouse stairs are blocked (outside and inside)
- [STAIRS-SEYDA-WAREHOUSE-32](STAIRS-SEYDA-WAREHOUSE-32.md): A spiral stair in the Seyda Neen warehouse tower is blocked
- TERRAIN-TRAP-29 (no report page): v0.0.29-dev1: Player reportedly stuck on rocks beside structures
- [VIVEC-ARENA-ACTORS-32](VIVEC-ARENA-ACTORS-32.md): Five Vivec Arena residents fail the actor placement gate

Related bugs in other categories:

- ARRIVAL-CEILING-28 (no report page): Coordinate arrivals start inside solid ceiling shell

<!-- END GENERATED CATEGORY -->
