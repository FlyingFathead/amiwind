# Horstator's musings: keeping the world continuous

29 September 2026, evening, 22:53 Helsinki.
Current released baseline: v0.0.23-dev4. Working checkpoint: v0.0.23-dev5.
Owner's design direction, not a list of implemented streaming features.

## Why load the entire map at once?

The slow spots around Seyda Neen raise a bigger question than which window has
too many polygons. Why should the entire detailed map stay loaded when the player
can only see and interact with a neighborhood? Could we keep the exterior feeling
continuous by loading what is needed ahead of the player and offloading what has
fallen far enough behind?

A seamless map would be brilliant. Separate interiors are normal Morrowind; the
exterior should not become a succession of conspicuous loading screens. Prefer
continuous streaming based on position, with a special passage loader where
necessary. At worst, a brief "Loading..." overlay could acknowledge a short wait
without replacing the world with a full loading screen. This does not mean
promising that all storage reads will fit invisibly between frames.

## Original cells are source units, not mandatory town boundaries

A Morrowind exterior cell spans **8192 × 8192 original game units**. The current
terrain converter uses 128-unit sample spacing, giving 64 intervals across a
cell. At AmiWind's current quarter scale, that is **2048 × 2048 runtime units**.
These figures come from the existing terrain conversion in
[`prepare_quake.py`](../tools/prepare_quake.py); they are not a promise that one
cell's full scenery, textures, actors and collision fit our memory budget.

The original grid can index source records without dictating the runtime loading
region. A town may straddle multiple cells, while a mostly empty cell may be
cheap. If a strict cell swap would split an important place awkwardly, consider
**polygon-shaped town/point-of-interest regions**, with overlapping approach
areas and passage points chosen around geography. A town, port and its useful
sightlines should remain coherent even when the original grid cuts through them.

This is a fallback/design option, not a decision to carve every town into a
separate level. Measure whether finer streaming works before imposing boundaries.

## Layered LOD and residency

Prepare multiple representations on the host and make runtime selection cheap:

| Layer | Candidate contents | Residency idea |
| --- | --- | --- |
| Near | Detailed terrain, interactive actors, collision and close scenery | Keep ready around the player, including a movement safety margin |
| Middle | Reduced buildings and terrain, baked decorative detail | Prefetch on approach; replace with near detail before interaction |
| Far | Coarse terrain, silhouettes or other cheap substitutes | Retain enough horizon coverage for the view and fog distance |

Drawing less and storing less are separate goals. A hidden high-detail mesh is
still occupying memory until its allocation can actually be released. Keep
lightweight object identities and durable gameplay state when dropping visual
resources, so revisiting an area does not reset NPCs, containers or quests.

Use overlap and hysteresis: load before a boundary, unload farther behind it,
and avoid repeatedly swapping the same data when the player stands on an edge.
Shared textures or models need ownership/reference tracking before eviction.
A bounded work queue and measured memory/I/O budgets are more useful than a
periodic flush of everything. Keep music playback serviced during every stage.

## Flying changes the problem

The player might be walking through a narrow approach one moment and flying
above several regions the next. LOD selection therefore needs to consider
altitude, projected size, movement direction and speed, not only a ground-cell
index. A flight transition could keep a broad coarse layer available while
swapping detailed regions underneath it as needed.

Do not load all distant places at full detail merely because they become visible
from above. Equally, do not make the world disappear when the player crosses an
LOD boundary or turns around quickly. Host-baked layers, overlapping coverage,
prefetch margins and fog should work together. Check terrain seams, shoreline
continuity, landmark silhouettes and collision readiness separately.

## First experiment, not a full-world claim

### Evening addendum, 22:58 Helsinki

The ideal is that the player cannot tell a load or region switch happened at all,
even while moving through Seyda Neen. "WAD changes" in the discussion means
**BSP changes**. Investigate seamless BSP-region streaming, starting with the
original Morrowind CELL/LAND structure and the references that cross cell edges.
A normal whole-map BSP replacement is not automatically a seamless transition:
neighboring render data, collision and actor state must coexist during handover.
The brief "Loading..." overlay is a fallback when prefetch cannot keep up, not
the desired normal experience.

Keep yesterday's debug flymap proposal, **`dbg fly 1`**, as a planned inspection
tool. Verify its current implementation status before treating it as an available
command. It should let us inspect cell boundaries, streamed region overlap,
terrain seams and altitude-dependent LOD transitions, including fast flight and
turning back immediately after crossing a boundary.

Use the earlier terrain-observer/free-flight idea to cross two or three regions
repeatedly. Measure worst-frame time as well as average FPS, resident memory,
loading time, cache misses, audio underruns and boundary failures. Try walking,
fast flight, rapid turns and oscillating across an edge. Deliberately slow I/O to
find out when a passage overlay would be necessary.

The existing renderer owns a resident BSP with pointer-linked structures. True
partial unloading needs an explicit resource-lifetime design; it is not achieved
by freeing arbitrary parts of the current map allocation. Stable world IDs,
separate persistent state and independently loadable chunks must come first.

The dev5 dock variant is a smaller prebuilt scene, **not continuous streaming**.
Window flattening is a host-side visual simplification, **not an LOD streaming
system**. Keep these distinctions in the implementation and release notes.

Related entries: [28 September journal](HORSTATORS_JOURNAL_2026-09-28.md),
[mesh investigations](MESH_TIPS_AND_TRICKS.md), and
[29 September roadmap](PLAN-2026-09-29.md).
