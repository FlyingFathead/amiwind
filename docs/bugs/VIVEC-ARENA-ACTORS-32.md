# VIVEC-ARENA-ACTORS-32: Five Vivec Arena residents fail the actor placement gate

## Status: 8 October 2026

Open: fixed in source on branch v0.0.32-arena-actors (not yet in a build that shipped). With the
fix the actor placement gate passes for the Arena without the private-test waiver. Found by the
first from-scratch build with the repository builder (v0.0.32-dev1 attempt). Present in the
private v0.0.32-dev1 test only (the Arena was not in any release).

## Symptom

Ordinators 241614 (region va004, unsupported), 241599 (va005, blocked), 241603 (va011, blocked),
259446 (va015, unsupported) and Aron Andaren 259450 (va007, unsupported) start outside support
tolerance; 2 of 7 residents are grounded.

## Private-test waiver (tracked)

Owner decision, 8 October 2026: these five residents, and only these, are accepted for the
private v0.0.32-dev1 test so Vivec can be looked at. It is not a fix and not accepted for any
release.

- Mechanism: the builder's `--allow-known-actor-ground-findings` with the reviewed audit. Any
  other failing resident, or a changed audit, stops the build.
- The image is then named `-private-test` and `actor-ground-acceptance.json` records
  `production_gate_passed: false` and the approved audit's SHA-256.
- Builds that used it are listed below with that hash.
- A release candidate or final must pass the gate without the waiver.

| Build | Approved audit SHA-256 | Failing references |
|---|---|---|

Owner evidence from real play of the dev1 test (8 October 2026), the visible effect of cause 1
below: at global position 39859 -86712 706 (local 876 81 176) a canton sewer outflow hangs in the
air with no canton body around it, and at night the exterior looks empty. The owner reported it as
"the exterior isn't rendering at all". The frame-by-origin rule kept the small piece (its origin
inside the frame) and dropped its parent canton body (origin outside). Fixed in source by the
footprint rule (merged into the v0.0.32 development line, 9a2992b); an in-game check at that pose
is pending.

## Owner reports in dev1 play (8 October 2026)

The same two causes explain the owner's dev1 reports in the Arena frame. Each pose was compared
offline on the dev1-source maps and the fixed maps (a textured render of every BSP model, no
fog, plus standing-hull checks and a stepped walk with the engine's step height):

| Owner report (local pose) | dev1 maps | Fixed maps |
|---|---|---|
| Sewer outflow hanging in the air, no canton (876 81 176, E100) | Telvanni canton body (ref 466153) missing; outflow and banners float | Canton body present around the outflow |
| Exterior missing at night, same spot (E086) | Same: nothing but the outflow east of the Arena | Canton body present |
| Stairs cannot be climbed (600 -580 173, S181) | Standing hull inside the Arena canton fill (466157); walk blocked after 38 units by an overhang of the fill | Hull clear; walk climbs 49 units up the stairs (`ex_vivec_b_wb_01`, still convex: its fill is 5.6, under a step) |
| Stuck on the covered walkway by a guard (-87 -540 168, W258) | Standing hull inside the fill; no ground reachable | Hull clear; 200-unit walk along the walkway |
| Noclip off refused, "colliding" (-407 -561 201, SE129) | Standing hull inside the fill; no spot within the engine search | Hull clear: noclip off succeeds; the floor is 40 units below |
| Pieces hanging in the sky, slab seen from behind (-344 -756 192, S187, looking up) | Fragments of the south canton (466160) and bridge pieces without their body | Canton body present |
| St. Delyn: arches and outflow without walls (-1211 -962 87, E101) | South-west canton body (117156) missing | Present |

No mirrored transform is involved: no shape of the 68 Arena or 226 Balmora models has a negative
determinant in its node chain, Morrowind placement scales are positive, and tilted placements
keep their winding (`prepare_mesh_bsp._prepare_placement` orders faces by the source normal).
Proof sheets are kept with the private evidence. The neighbouring canton bodies now end at the
frame edge: [VIVEC-ARENA-FRAME-EDGE-32](VIVEC-ARENA-FRAME-EDGE-32.md).

## Where

`tools/import_town.py` (which placements belong to a town frame) and the collision proxies of
converted meshes (`tools/mesh_geometry.py`, chosen per mesh by `tools/town_regions.py`
`visual_profile`). Checked by `tools/check_actor_ground.py`. Seyda Neen, Balmora, the interiors
and the open world are unaffected (measured below).

## How it happened

Two independent causes. In every case the original game has a walkway under the resident: the
source mesh has one flat surface 5 to 66 original units below the authored position, and the
game drops the resident onto it.

1. **The frame kept residents by origin, and the floor they stand on by origin too.** The Arena
   frame keeps placements whose origin lies within +-1536 local units of the frame centre.
   Residents are points, so that is right for them; a Vivec canton is about 1,780 local units
   wide, and the Redoran (ref 466164, origin x -1808) and Telvanni (ref 466153, origin x 1776)
   cantons have their origins outside the frame while their walkways reach into it. Their
   residents were kept and their floors were not: 241614 (Redoran canton top, original z 1812),
   259446 (Telvanni canton top) and 259450 (Telvanni lower walkway) stood over nothing
   ("unsupported"), and would float over open water in view of the Arena canton. The sub-cell
   code already measured overlap from whole-object bounds; the frame filter did not.
2. **Convex collision buried the walkways.** Exterior architecture is collided as a union of
   convex hulls (`collision_parts`). On a canton the hull of a few large triangles closes the
   space above the lower walkway: at 241599 the column is solid from the walkway (local z 144)
   to above z 231, at 241603 a false ramp rises 9 to 28 units over it ("blocked": the feet start
   inside solid). The canton mesh (`ex_vivec_c_04`, 1,287 collision triangles) leaves 126 of 238
   hulls outside the 2-unit tolerance, the deepest closed space 34.7 units; groups of four or
   fewer triangles are never split further, whatever their error. The same proxy also loses
   surfaces (the 14-direction support samples), so with cause 1 fixed alone the Redoran canton
   top under 241614 was still missing and 259450 was buried by the Telvanni canton
   ([COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md)).

A/B/C/D on the owner's data (Arena import plus the actor stage on the dev1 actor-contact maps;
A reproduces dev1's maps and audit byte for byte):

| Variant | Frame by footprint | Architecture surfaces | Failing residents |
|---|---|---|---|
| A (dev1 source) | no | no | 241614, 241599, 241603, 259446, 259450 |
| C | yes | no | 241614, 241599, 241603, 259450 |
| D | no | yes | 241614, 259446, 259450 |
| B (fix) | yes | yes | none |

## Why it was not caught

The Arena is the first converted town whose frame is not its audited cells (Balmora's frame is
its 3x3 cells, so it has no frame filter) and the first with towers and walkways larger than a
region. The actor gate measures the converted collision, not the source surface, so a resident
standing on a convex fill above the real floor passes (Ordinator 259454 on the bridge
`ex_vivec_b_gap_t_01` was grounded 8.6 units above the authored bridge surface in dev1).

## Reproduction

Build with `--extra-town vivec_arena` on the dev1 source: the actor stage fails on the five
references above.

## Repair

Generic, for every converted town; no reference or model is named in the code.

- Frame selection by footprint (`import_town.py`): when a town has a frame filter, every visible
  placement of the audited cells is measured once in a scratch export, and a placement belongs to
  the frame when its origin is inside it (residents and markers are points) or its whole-object
  bounds reach into it. Region visuals and collision stay clipped to region coverage, as before.
  For the Arena: 420 placements instead of 392 (the Redoran, Telvanni and three other canton
  bodies, bridge pieces and their dressing), 29 door-bank rows instead of 26.
- Architecture keeps its authored collision surfaces when the convex proxy closes more than a
  step: exterior architecture (`meshes/x/`) not already on the hand-made surface list gets
  `surface_collision_beyond` = the engine's step height (8.5, `STEPSIZE` in `sv_move.c` and
  `sv_phys.c`); `mesh_geometry.collision_pieces`, now the one implementation used by the
  converter and the size estimates, then uses the same thin surface plates and exact standing
  bevels as the Balmora list when the deepest closed space of the convex proxy is deeper than
  that. Quake's own rule: anything up to a step the player walks up; deeper invented solid is a
  wall or ledge the original does not have. Arena models switched (closed depth): `ex_vivec_c_04`
  34.69, `ex_vivec_b_t_01` 28.18, `ex_vivec_c_02` 25.92, `ex_vivec_bt_01` 13.26,
  `ex_vivec_lp_01` 10.69, `ex_vivec_b_wb_gap_01` 10.41, `ex_vivec_b_gap_t_01` 10.12,
  `ex_vivec_b_gap_b_01` 10.06, `ex_vivec_b_tb_01` 9.13. No Balmora model reaches the limit
  (deepest convex architecture: `ex_hlaalu_striderport_01`, 5.71).

## Verification

Branch v0.0.32-arena-actors, owner's data, inside Docker, 8 October 2026:

- Actor audit (all packaged towns): passed, 165 grounded, 3 explicit exceptions, 0 errors. All
  7 Arena residents keep their authored X/Y and stand on the source surface (+0.45: plate top plus
  the usual 0.25 lift): z 144.45 on the lower walkways, 448.45 on the canton tops, 512.45 on the
  bridge. Every Seyda Neen, intro, Balmora and interior row is byte-identical to dev1's audit;
  only the 17 Arena map hashes change.
- Balmora regions rebuilt with the fix: every map byte-identical to dev1.
- Arena map heap estimate (raw region maps): all 16 pass; minimum clearance 2,950,876 B (dev1
  source: 3,336,028 B); largest region 2,807,208 B; at most 324 placements, 103 inline models and
  29,265 clipnodes per region (Balmora regions reach 53,119); 22 shell unions fall back to exact
  standing-box pieces after a qbsp non-convex face, the same fallback Balmora takes 10 times.
- Regression tests: `tests/test_mesh_geometry.py` (a walkway under a roof is buried by the convex
  proxy and kept by the surface rule; a closed space within a step keeps the convex proxy
  unchanged; the step height matches the engine) and `tests/test_town_import.py`
  `ArenaFootprint` (footprint selection, resume, architecture profile). All fail on the dev1
  source.
- Pending: a from-scratch build of the release candidate and an in-game look at the Arena,
  including the owner's pose above (no floating sewer outflow, canton bodies present).

## Prevention

The gate stays. A waived image cannot pass as a release:

- The image is named `-private-test`.
- Its `actor-ground-acceptance.json` says `production_gate_passed: false`.
- The builder refuses the waiver options (`--allow-known-actor-ground-findings`,
  `--map-budget-policy warning`) and any `-private-test` image unless VERSION is a `-devN`
  build: a release candidate or final image must pass every gate (`tools/project_version.py`
  `require_private_test_version`, checked by `tools/build.py` and the `image` step).

The frame rule and the collision rule are generic and covered by the regression tests above;
the remaining convex-proxy errors outside exterior architecture are tracked on
[COLLISION-CONVEX-LOSS-32](COLLISION-CONVEX-LOSS-32.md).
