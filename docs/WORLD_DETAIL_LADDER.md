# Further terrain development: world-detail and topology ladder

Recorded 3 October 2026. **Future TODO / roadmap direction — NOT implementation
work for now.** Continue the current Rocks and Mushrooms work and resolve its
memory/transition blockers first. This ladder is a content-planning guide, not
an authorization to start every pass or a replacement release schedule.

## Continue the current approach; subdivide dense areas as needed

Proceed with the current mapping/conversion approach, then introduce further
sub-cell division when entering high-polygon/high-cost areas such as settlements.
Use measured resident/loading memory, geometry/collision cost, frame times and
transition behavior to choose where and how. Mostly empty terrain need not have
the same residency density as a town. Original cells remain source indices;
runtime residency cores may be smaller or fitted polygons where worthwhile.

Mark over-headroom regions, profile their dominant allocations, and reduce or
subdivide the actual loaded payload. Retaining a complete parent tree/PVS can
negate a smaller boundary. Keep viewing/collision coverage separate from the
transition core; validate overlaps, both-direction crossings, corners, held input
and persistent actor/player state. Leave headroom throughout development rather
than postponing memory safety until later optimization. See
[memory allocation](MEMORY_ALLOCATION.md), [the heap watcher](HEAP_WATCHER.md),
[the current map profile](MAP_MEMORY_PROFILE.md) and
[cell-changing continuity](CELL_CHANGING.md).

## Deliberate content passes

1. **Rocks and mushrooms:** boulders, rock clusters, exposed stones and giant
   landscape mushrooms; natural objects that change recognizable silhouettes
   without being architecture. This is the current pass.
2. **Trees, roots and stumps:** swamp trees, exposed roots, dead trees/trunks,
   fallen logs and stumps. They establish landmarks and occlusion.
3. **Marsh vegetation:** reeds, grasses, ferns, low plants and cattail-like swamp
   clutter. Prefer cheap sprites/crossed planes where appropriate; account for
   unique textures/frame storage and placement state, not just polygon count.
4. **Shoreline topology:** beach/mud transitions, banks/embankments, submerged
   rocks, tiny islands, pools, marsh channels and proper land/water intersections.
   Give this unusually early attention around Seyda Neen: a swamp settlement
   loses much of its identity when banks and waterways look too flat and clean.
5. **Terrain formations:** ridges, raised shelves, cliffs/escarpments,
   depressions, gullies, steep rock faces and large natural formations that the
   heightmap alone does not represent.
6. **Paths and roads:** road surfaces, worn paths, edging, terrain steps, ramps,
   wooden crossings and causeways. Geography must communicate where a path goes.
7. **Natural entrances:** cave mouths, mine/grotto openings, hillside tomb
   entrances and transition geometry around them.
8. **Regional vegetation/geology sets:** extend the validated mechanism to
   Bitter Coast swamp scenery, Ascadian Isles greenery, West Gash rocks,
   Ashlands volcanic formations, Grazelands giant flora, Molag Amur lava/black
   rock and Red Mountain's landscape.

A possible content progression is rocks/mushrooms → trees/roots → reeds and
undergrowth → shorelines/marshes → cliffs/formations → roads/paths → entrances.
It is not a fixed assignment of version numbers: the planned **v0.0.28 — Trees
and Grass, Day and Night** title is now recorded in the roadmap. The title does
not imply that all graphics milestones are complete. Reconcile future scheduling
explicitly rather than silently changing the planned release contents.

## Keep micro-clutter and interactive objects separate

Barrels, crates, baskets, harvestable plants, loose logs, signposts, campfires
and similar objects are a separate world-object track. Some need inventory,
interaction or persistent state; containers are a system, not merely decoration.
A fallen trunk used as landscape topology and a movable/interactive loose log
can therefore require different treatment despite a similar appearance.

## Requirements for every future pass

Preserve original base-game placements and recognizable materials/textures.
Choose cheap representations deliberately and validate appearance, occlusion,
collision and memory costs. Natural additions make terrain seams more visible;
test Seyda Neen/Balmora boundaries and other affected cells as content grows.
Retain before/after allocation and performance evidence. A mitigation is a
bandage, not a verified fix; do not close defects by hiding them behind new detail.

Every detail pass and settlement subdivision follows the
[watcher / profiler / optimizer pipeline](HEAP_WATCHER.md#required-watcher--profiler--optimizer-pipeline).
Use the same evidence loop as content grows; do not substitute a successful
allocation or a lower polygon count for a measured memory/performance result.
