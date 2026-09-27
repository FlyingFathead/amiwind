# Seyda Neen vicinity: first complete area

Owner-selected scope, 27 September 2026:
[UESP map centered near -11394, -71667](https://gamemap.uesp.net/mw/?x=-11394&y=-71667&zoom=7).
The supplied map screenshot is retained privately; it is not bundled as public
artwork. Use the map as a coverage checklist, with the owned master as source.

The next major milestone is a connected, working starting area. Complete the
exteriors first, then load interiors separately on entry. Keep development in
this vicinity until movement, interaction and persistent local state work
together; additional towns are not the next coverage target.

## Agreed footprint and delivery order

| Part of the area | Exterior acceptance target |
| --- | --- |
| Town center, tradehouse, shacks, Census office and warehouse | Complete visible structures, doors, stairs and continuous walking routes; retain the repaired town-square route. |
| Port and arrival assembly | Connected piers, supports and gangplank; ship, hatch and cabin agree with the selected opening state. No orphan parts. |
| Lighthouse peninsula, nearby islets and shoreline | Source terrain and water meet consistently; distinguish converted coverage from the temporary flat sea. |
| Opposing shore, bridge connections and mainland approach | Reachable routes in both directions without falling through seams or meeting an invisible export boundary. |
| Silt strider stop | Include its shore, approach and landing in the footprint now. Add the recognizable strider as a later creature/landmark conversion task; travel service is separate gameplay work. |
| Bridge-side residential area described by the owner as Fargoth's house | Verify the house/cell/door identity from the owned data before assigning a name or destination. Include the connected residential route. |
| Town containers and nearby actors | Inventory placed references now; add visible containers and suitable collision, then their interaction/state milestone. The current three actors are only a subset. |

1. Audit selected cells, transformed object bounds and connected assemblies.
   Report missing terrain, unsupported record types and skipped assets.
2. Complete the connected exteriors in small checkpoints. Fix the positional
   shack-wall report, ship omissions and coverage seams; retain debugging flight,
   coordinates and safe recall throughout.
3. Pass fixed walking/camera routes and resource measurements before calling the
   exterior area complete. Gate later expansion on this evidence.
4. Build the prison-ship interior for the opening, then the Census and Excise
   office as the first town interior. Load each separately and test linked
   entry/exit repeatedly. See the [ship journal](journals/SEYDA_NEEN.md).
5. Build the local gameplay slice here: containers and player inventory, NPC
   activation/dialogue, relevant opening state and eventual save/load. Supporting
   host lookups can be prepared earlier; this is not a demand to implement every
   game system before the first interior.

The silt strider's visual presence does not require implementing fast travel
at the same time. Its source record, animation, bounds, sound and allocation
need an audit; do not assume the existing humanoid bake supports it unchanged.
Container work is tracked in [CONTAINERS.md](CONTAINERS.md).

## Exterior acceptance routes and budgets

Record exact source/local coordinates, camera direction, runtime version and
emulator settings for each route: town square to port, port to lighthouse,
town to the opposing shore and strider approach, and the residential/shack loop.
Walk both ways; test stairs, narrow crossings, idle slopes and rapid turns.
Door panels and walls must survive the reported viewpoints without drawing
through nearer geometry. Require zero renderer-capacity overflows on these
routes and explicit coverage reporting for intentionally unfinished boundaries.

Compare the same geometry and routes under each fog preset. Record frame-time
distribution and worst stalls, edge/surface peaks, Chip/Fast/heap/cache use,
asset reloads, disk reads and audio deadline misses. Preserve the earlier
measurements; increasing coverage must not silently change the hardware target.
The current accelerated reference remains distinct from a stock-CPU A1200 goal.

Generate placed-reference, shared-asset, material, collision, door-destination,
actor and container lookups on the host. Keep only the working set and compact
mutable state resident. Profile before selecting chunk size, prefetch distance
or compression; more HDD capacity does not eliminate rendering or I/O costs.

## Cells and runtime chunks

TES3 exterior cells are 8192 by 8192 source units. Cell coordinates use floor
of world coordinate / 8192, including negative positions. The linked center
lies in cell (-2,-9). At the current quarter scale, a full source cell spans
2048 local units. Interior CELL records are separate spaces reached via linked
DOOR destinations, not extra floors of the exterior cell.

The current terrain slice spans +/-768 local units around source
(-11264,-71680); static-reference origins are filtered at +/-736. These cutoffs
are smaller than the requested vicinity and can omit a structure crossing the
border. Inventory a 3x3 source-cell neighborhood around (-2,-9), then select the
requested footprint by transformed bounds and connected structure groups.
This is an audit region, not a promise to load nine full cells into Amiga RAM.

Runtime streaming chunks can be smaller than source cells. Keep stable source
reference IDs, explicit coverage bounds, shared asset IDs, actor/door state and
separate memory budgets. No fixed chunk size is accepted until profiling.
Draw distance controls visibility, not which source cells exist in the export.

Reference: [OpenMW camera/cell size documentation](https://openmw.readthedocs.io/en/stable/reference/modding/settings/camera.html).

## Missing prison ship: conversion and game state

The owned base master identifies the prison ship hull as an ACTI record, while
its hatch/cabin doors are DOOR records. The checkpoint-014 scenery pass selected STAT
and DOOR only. The hull origin also lies just beyond the +/-736 object cutoff;
its local X is approximately 743. The hatch could therefore appear without its
ship. This is an incomplete conversion, not evidence that the runtime executed
Morrowind's departure logic. No such opening quest logic is implemented yet.

The original character-generation class NPC script disables the boat and
associated guards/doors/objects during its initial state. Preserve that authored
state transition when implementing the opening; do not invent a visible sailing
animation or infer the transition merely from entering any interior.

Checkpoint-015 groups the hull, hatch, cabin door and gangplank by stable IDs
and admits this specific visible ACTI hull. Opening-actor/state grouping remains
future work; unrelated objects still use the old selection cutoff.
Do not blindly render editor collision markers. Audit transformed bounds and
record skipped types/assets. Keep the arrival presentation and post-registration
presentation as separate test states with verified entity allocations.

## Sea and waterline

The expanded flat sea is a temporary Z=0 reference/backdrop, not this whole map.
`amiwind_debug_sealevel on/off` controls its visibility independently of text
HUD overlays. Water physics do not change. A future topographic diagnostic
should show actual LAND elevations, water datum and missing coverage separately.
Replace the placeholder as neighboring terrain/coastline is converted.

## Silt Strider omission audit

Owner suspects the missing edge area is the Silt Strider landing. Source audit
finds the strider as ACTI `a_siltstrider` and its operator in the named town cell.
The current ordinary scenery pass admits STAT/DOOR plus the explicit ship ACTI,
so the strider itself is omitted. This is a confirmed selection omission, but
not yet a confirmed cause for the separate malformed terrain screenshot.
Audit landing/terrain/bounds and retain the hypothesis in SEYDA_NEEN_NEXT_STEPS.md.
