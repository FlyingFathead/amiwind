# Cell-change continuity checklist - a growing list

A streaming boundary changes the resident map, not the player's ongoing game.
Seyda Neen and Balmora subdivisions are required to bound frame cost; preserving
continuity must not require loading the entire world at once.

## How this list grows

This is a living checklist, not a closed definition of gameplay state. Every
new system, stat, equipment mode, NPC behaviour or transient effect must add
its cell/sub-cell transition policy here and receive a regression or explicit
playtest case. Record what is preserved, rebased, expired or deliberately reset.
Do not mark a requirement complete merely because it is documented.

## Current evidence and remaining acceptance

| State | Current evidence | Remaining acceptance |
| --- | --- | --- |
| Held controls, Shift/Ctrl | Rc3 automatic loads no longer clear buttons; real scene harness checks no clear call | Held/released-during-load controls and focus-loss playtest |
| Noclip, position, view, velocity | Real transition harness passes both variants | Cross town/world and subdivision boundaries both directions |
| Health, hands raised, lit torch | Existing capture/restore verified by real transition harness | Raised/lowered hands and lit/unlit torch playtest |
| Magicka/fatigue values, level, inventory state | Harness retains character values and inventory state through spawn | Full character HUD/equipment review; no claim of all stat fields tested |
| Shared terrain and materials | Coverage and shared-world triangulation regressions pass; town compiled | Seyda Neen boundary playtest on the new image |
| Shared sky, night layers and time | Saved clock drives sky/moons; source fixtures cover map/interior isolation | Native exterior/interior and saved-state transitions; no stale sky or palette |
| Guard torch presentation | Original-class/inventory registry and saved clock determine bounded companion/light rendering | Native Imperial/Hlaalu cell crossings, on/off/auto, cache release/reload and lighting cost |
| Sky and night gallery cameras | Renderer-only override; source tests restore camera and cancel on map change/disconnect | Native daycycle/nightgallery tour, here and exit checks without player movement or saved-clock change |
| Coordinate arrival beneath ceiling shells | Four exact owned-hull failures reproduced and corrected by a bounded clear-start search | Native guard/Erene and pressure routes; distinguish a valid roof placement from ground contact |
| Weapons, active effects, pursuit/combat | Transition requirements recorded | Implement and test when the corresponding gameplay systems exist |

## Required continuity

- Preserve world position, view direction, movement mode and velocity through
  coordinate rebasing. Noclip must remain enabled when it was enabled before.
- Preserve physically held movement keys and Ctrl/Shift speed modifiers across
  automatic transitions. Releases during loading must be honoured; focus loss
  must clear input to avoid stuck keys. Teleports and menus require explicit
  policies rather than blindly replaying all buttons or one-shot actions.
- Preserve stable NPC identity, health, death state, position, dialogue and
  interaction state. When pursuit/combat is implemented, preserve its target,
  aggression, active pursuit and relevant timers across residency changes.
  An NPC must not stop chasing solely because a map boundary was crossed.
  This is a requirement, not a claim that NPC pursuit/combat is implemented.
- Preserve character identity and stats: current/max health, magicka, fatigue,
  attributes, skills, active effects and relevant timers. Never reset them to
  spawn defaults merely because a different BSP became resident.
- Preserve quest/journal progress, inventory and equipment. Track equipped
  items separately from drawn state: sheathed weapon, drawn weapon, raised bare
  hands, lowered hands, carried torch and whether its flame is lit. Preserve
  the applicable weapon/torch state, attack mode and unfinished draw/holster
  transitions according to an explicit policy; avoid restoring incompatible
  combinations. The current scene loader explicitly carries health, hand goal
  and torch goal; that alone does not verify all character-state categories.
  Define which transient animations and effects
  resume, expire or restart, and prevent duplicate events on re-entry.
- Keep shared ground heights, shoreline geometry and texture placement aligned
  throughout visible overlap, with sufficient ground beyond every handoff.

## Rc2 reports and rc3 correction status

The owner reported Ctrl/Shift flight-speed modifiers resetting while held
across cell/sub-cell changes during noclip. Rc2 cleared all held buttons when
scheduling a map load, including automatic region crossings. Rc3 retains
held buttons on automatic region crossings while retaining
clearing at doors, teleports and focus loss. The real transition harness passes
in both test variants, including noclip, health, magicka/fatigue, level, inventory,
hands and torch restoration.
Owner held-Shift/Ctrl and focus/release playtesting remains pending; for rc2 the
temporary workaround: release and press the modifier again after the load. Do not treat
retained noclip mode or velocity alone as proof of complete input continuity.

The owner also reported Seyda Neen's landscape changing sharply at its town
boundary. The old ground ended only 64 units beyond the eastern exit against
540 units of draw distance. A surrounding-ground apron and shared world terrain
sampling are being rebuilt and require a separate owner boundary playtest.

The owner accepted the rc2 giant-mushroom cap correction. That acceptance does
not cover these transition defects. See [bug journal](BUG_JOURNAL.md).

## Visible overlap and terrain handoff policy

Measure how much neighbouring sub-cells duplicate with
[sub-cell redundancy](SUBCELL_REDUNDANCY.md) before and after changing cores or
overlap. Crossing load times, what a crossing reads and the cache and loader
changes are measured in [Seyda Neen performance](SEYDA_NEEN_PERFORMANCE.md).

A core chooses which BSP owns the player. Coverage is the larger area that BSP
can render and collide with. Hysteresis keeps ownership from bouncing back and
forth near a boundary. These are different bounds: extending a core alone does
not create ground, and declaring overlap does not prove that geometry exists.

- Coverage records must enclose their cores and match the generated resident
  payload. Check the runtime directory format before packaging. Empty or clipped
  boundary strips must not be presented as verified visible landscape.
- At every reachable exit, retain real ground through the whole view range,
  including diagonal views, hysteresis and transition margin. Check the actual
  terrain footprint, not the sea backdrop or sky enclosure. Derive and test the
  required margin when draw distance or loading policy changes.
- Shared LAND must use the same source coordinates, world scale, height samples,
  coarse grid alignment, triangle/winding policy and shoreline refinements on
  both sides. Local origins may differ; rebasing must preserve global position.
- Ground materials, texture sources, UV placement, palette and lighting/fog
  policy must agree in shared coverage. Do not call a height-only comparison a
  complete visual-continuity test.
- Preserve complete intersecting rocks, mushroom parts, buildings and relevant
  collision through the overlap. Select by transformed bounds, not just an
  object's centre. Distinguish remaining scenery differences from ground gaps.
- Keep bounded residency and the town's FPS subdivisions. An overlap fix must
  stay within face, vertex, clipnode, memory and loading budgets; joining every
  cell into one resident map defeats the subdivision policy.

### Seyda Neen: town-to-world and internal town subdivisions

The rc2 owner screenshots near the eastern town exit show a missing landscape
followed by a sudden hillside after a few steps. The town remained resident to
local X=1600 while its ground stopped at X=1664: only 64 units ahead against a
540-unit draw distance. A sea/sky backdrop could not supply the missing LAND.

The candidate correction adds a 768-unit real-ground apron, uses the streamed
world sampler/triangulation/material choice outside the detailed port approach,
and extends subdivision coverage without moving town ownership cores. An older
candidate also raised a per-cell sky enclosure to follow measured surrounding
hill height; that part is superseded by the owner requirement to remove local
sky-enclosure render geometry and use a separate shared/background sky path.
The detailed Silt Strider approach retains fine ground samples. Outer coverage
records must still enclose all subdivision cores, including the legacy outer
edge strips.

Test town-to-world and world-to-town crossings at the reported eastern exit,
then other exits and diagonal views. Test internal town subdivisions and the
north bridge separately: an internal region change and leaving the town are
separate transitions. Confirm rocks, ground materials, collision, player height
and performance together. The corrected rc3 owner playtest remains pending.

### Balmora: FPS subdivisions and surrounding-world boundary

Balmora's configured profile uses a 768-unit core target, 896-unit overlap,
96-unit hysteresis and 540-unit draw distance. Keep its measured subdivisions
and detailed town payload. Audit each core edge and outer town handoff against
actual generated LAND and collision coverage, including bridges and riverbanks.
Do not assume configured overlap survives clamping at the town's outer bounds.

Use the same world-transform and material agreement checks as Seyda Neen, while
respecting Balmora's authored terrain-material repairs and its own geometry.
Recheck doors, NPC placement and character state across its internal regions.
The Seyda Neen correction is not evidence that Balmora's outer handoff has
passed the same audit or playtest; track that acceptance separately.

## Regression and playtest checklist

Cross the same boundary in both directions while holding movement and each
speed modifier, then release during loading and after loading. Repeat with
focus loss, noclip and ordinary walking. Verify world position and camera
orientation, and that no held key becomes stuck. Compare the landscape from
both sides without moving the view. Repeat while wounded or fatigued, with raised/lowered hands, an equipped but
sheathed weapon, a drawn weapon when supported, and a lit/unlit torch. Check
that stats, equipment and draw state survive each transition. Check persistent
NPC state after leaving
and returning; add pursuit/combat cases when those systems exist.

## Heap clearance: rc3 Seyda Neen incident

The rc3 real-ground apron fixed missing terrain at the town/world edge but
enlarged the central subdivision visibility table from 473407 to 2767103 bytes.
The loader held a temporary input table and allocated a second resident copy
inside the 11-MiB heap. A Hors restart from Jiub name entry exhausted the heap
loading sn012. Held-input/state preservation does not add BSP data and is not
the cause indicated by this failure. See CRASH-01 in [the bug journal](BUG_JOURNAL.md).

Byte-only sections now load into their final allocation. The host regression
and Amiga compile pass; total clearance and target playtesting remain separate
gates. Build checks must account for expanded target-ABI structures, each
loading-stage temporary allocation and reserved non-BSP headroom, before image
assembly. Report the failing map, stage, peak, reserve and budget. Changing
overlap requires measured clearance and both-direction seam playtesting; keep
FPS cores and visible coverage requirements distinct.

### Imperative: LEAVE HEADROOM

**Always leave headroom.** Do not accept a region because its allocations only
just fit. Reserve non-BSP engine/gameplay storage separately from an additional
positive safety margin for loading uncertainty and future state. A zero-margin
configuration is not release validation. Report the heap budget, target-ABI
resident bytes, worst temporary peak, non-BSP reserve, required safety headroom
and remaining clearance. The tool must fail before image assembly when either
the peak or reserved headroom cannot fit. Document the assumptions and refresh
the accounting whenever allocator structures, caches or gameplay systems change.

The default budget is the actual engine reservation (currently 11534336 bytes),
not the emulator total Fast RAM. The runtime, compiled ABI and checker must
agree; increasing RAM or lowering a reserve must never silently turn a failed
reference-target build into a pass. A passing estimate still needs a target
playtest; a failing estimate must not be overridden by a successful lucky load.

See [Memory allocation and heap clearance](MEMORY_ALLOCATION.md) for the
allocation model, rc3 incident, mandatory reserves, build audit and transition
reports. Keep both guides synchronized when changing residency or the loader.

## Complete lifecycle watcher and over-budget regions

See [the heap watcher](HEAP_WATCHER.md) for build-stage estimates and event-driven
runtime profiling across unload, BSP load, actor/player restoration and first
presentation, including cache, zone and external Fast/Chip memory. See
[the map memory profile](MAP_MEMORY_PROFILE.md) for the 28 over-headroom regions,
shortfalls and dominant allocations. Mark failures explicitly and prioritize
reduction/subdivision, preserving complete coverage and state continuity. A
smaller core that still retains an oversized parent tree/PVS is not a fix.
Every replacement must pass the same headroom gate and target crossing tests.


## Boundary placement is a measured choice, not an FPS guarantee

Owner clarification, 3 October 2026: the suggested off-centre cut near sn017 is illustrative, not a required coordinate. Candidates may move boundaries or use nonuniform subdivision where actual payload measurements support it. Record the layout and map identity: sn017 in the original 25-region directory is not the same region as sn017 in the adaptive 64-region proposal.

Evaluate both sides of every changed boundary. Preserve the coverage apron, collision continuity and gameplay state; avoid merely transferring a failure to the neighbour. Density heatmap bins guide investigation but do not predict resident visibility, collision or loader allocation costs.

Acceptance has two independent axes: (1) loading-cycle peak and useful growth headroom under unchanged reserves, and (2) measured gameplay frame time plus crossing stalls and frequency. Subdivision can reduce payload but increase reloads, repeated shared-data preparation or clipping work. It must not be advertised as a performance improvement without matched target tests. Include requested and effective view distance, fixed position/view and settings; measure steady gameplay and both-direction crossings separately. The Balmora longer-view observation remains a hypothesis to test, not proof of its cause.

## Automatic region-crossing presentation delay

The archived aw_region_loading_delay setting controls a presentation delay for
automatic region crossings only. The default is two seconds; zero shows the
loading screen immediately. Startup and explicit travel remain immediate.
Begin the delay at a safe loading-screen checkpoint after blocking reads; never
interrupt or time out a blocking read to satisfy the delay. This changes screen
presentation timing, not loader throughput, map residency or frame performance.
Nine source checks pass and the rc5 candidate was packaged/read back; target
crossing timing and owner playtesting remain pending.

## Large interiors: subdivision at natural boundaries

Development decision, 6 October 2026. This is the chosen optimization approach
for oversized interiors; the new section routing and streaming are not yet
implemented. Existing interiors that fit the target budget can remain one map.

An original interior may contain enough geometry, texture mappings, collision
data and models to exceed the Amiga map allowance. Subdivide such interiors at
doorways, corridors, cave bends and other natural occlusion boundaries. Choose
sections around the original room layout rather than imposing a small uniform
grid that creates frequent interruptions while walking.

Before choosing a split, inspect the final converted geometry with the
[polygon inspector and heatmap](POLYCOUNT_INSPECTOR.md), alongside the
[memory profile](MAP_MEMORY_PROFILE.md). Remove redundant geometry/plane/texture
mapping data where correctness can be preserved. Polygon density alone does not
predict memory use: collision structures, textures, model caches, loader peaks
and overlapping coverage also contribute. Evaluate the complete resource cost
of both sections, including their shared boundary area and existing reserves.

Keep a single logical original interior identity across all physical sections.
Original object references, quests, NPC state, inventory, and picked or empty
mushroom facts must remain persistent when moving between sections or loading a
save. Adding section IDs must preserve existing saved map identities. Doors must
retain their original destinations and arrival positions.

Internal handoffs must preserve view angles, held equipment and active voices;
the soundtrack continues. Check collision and visibility in both directions,
including backtracking. Read-ahead may prepare the likely next section, but an
optimization is accepted only after measuring memory use and the visible pause
on the target engine. A section that fits on its own can still fail during its
loading peak or exhibit an unacceptable handoff.

Explicit loading screens on entering or leaving a building are acceptable.
The current transition performance priority is continuous outdoor movement:
pauses and jolts at exterior cell/sub-cell boundaries. Interior subdivision should
avoid introducing similarly frequent interruptions within a room or corridor.

### Preferred subdivision points

Doorways are the first choice for section boundaries in mines and other large
interiors. Where there is no doorway, use a narrow passage, corridor turn or
cave bend that limits visibility between sections. Include sufficient overlap
for views through the opening and continuous collision; a doorway alone is not
proof that the boundary is invisible or that the loading peak fits the budget.

### Pursuit across section and cell boundaries

The three boundary rules and actor eligibility distinctions are summarized in the [NPC cell-traversal guide](NPC_CELL_TRAVERSAL.md). They remain design requirements, not implemented gameplay AI.

NPC pursuit must survive internal section and adjoining exterior cell changes.
This is a design requirement, not a claim of implemented cross-cell combat AI.
A streaming boundary must not reset aggression or make an active pursuer vanish.
Track each actor by stable original reference identity, independent of the map's
entity slot. Transfer health, equipment, combat target, aggression, position,
movement intent and relevant combat timers without restarting the encounter.

Associate each connection with traversable entry/exit points. Pursuers must reach
and cross that connection by a valid route, then continue from the corresponding
arrival point. Do not teleport them directly beside the player. Original teleport/loading doors are a different boundary type: by default,
hostile NPCs must not follow the player out of a cave, tomb or other interior
through its original exit. Preserve the original Morrowind behaviour. This must
not prevent pursuit through artificial subdivisions of that same logical
interior, or across adjoining walkable exterior cells. Friendly followers and
explicit scripted transitions require their own rules; blocking hostile passage
does not by itself clear the NPC's saved hostility or reset health. Ordinary
non-teleport doors still need lock and actor-capability checks.

Reference: OpenMW's [hostile-follower compatibility issue](https://gitlab.com/OpenMW/openmw/-/issues/5101)
documents Morrowind leaving hostile followers behind at teleport doors, and the
[teleport-door pathfinding discussion](https://gitlab.com/OpenMW/openmw/-/issues/4893)
identifies that general navigation capability as outside the original game's
feature set. These are reference findings; AmiWind pursuit still requires
implementation and target testing.

Maintain exactly one authoritative actor state during handoff; overlapping map
sections must not create duplicate NPCs or duplicate attacks and drops. If the
source section is unloaded, retain a bounded pursuit record and advance permitted
travel until the actor can be instantiated at the destination entry. Detailed
pathing through unloaded terrain remains an implementation decision; never assume
a straight line is traversable. Save/load and returning across a boundary must
retain the same actor state.

Acceptance checks must cover pursuit in both directions, immediate backtracking,
multiple pursuers, death during handoff, blocked connections, and save/load during
pursuit. Include actor state and any overlap in the section's memory budget.


### Dense ramps: subdivide first, then measure

Evaluate the naturally divided mine sections before reducing ramp or other mesh
polygon counts. Subdivision reduces resident geometry, but a dense object can
still be expensive to render while visible. The inspector heatmap measures
placed vertex concentration; its see-through wireframe also superimposes
geometry at different depths. Neither alone establishes a frame-time bottleneck.

Measure each section's complete memory cost, boundary overlap and loading peak,
then profile representative visible views in the target engine. If those results
still exceed the budget or frame-time target, simplify the specific costly meshes
and repeat the measurements. Preserve walkable slopes, silhouette, collision,
material boundaries and closed seams; do not indiscriminately decimate the mine.
