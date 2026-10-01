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

## From Seyda Neen to Balmora: evening notes, 30 September 2026

Continued into 1 October, Helsinki. Owner's direction for the v0.0.24 follow-up;
implementation and measured acceptance remain recorded separately.

### A town is beginning to feel like a town

Getting from Seyda Neen to Balmora has been encouraging. The interiors, residents
and recent optimizations make the scope of the project easier to see. Balmora is
also a useful stress test: if its dense streets can be divided sensibly, smaller
settlements may prove more forgiving. The lessons should travel with us. Future
towns should inherit the conversion checks and subdivision tools, rather than
repeat the same discoveries one building at a time.

The short Loading pauses are still noticeable. They are tolerable for a working
build, but walking through a city ought to feel continuous. The next question is
how much of the coming scene can be prepared before the player reaches it. First
measure the reads, BSP setup and asset loading separately. Then try bounded work
between frames, keeping the 11 MiB heap and ordinary walking performance in view.
A larger buffer is worth testing; it is not automatically a better buffer if it
pushes useful models out of memory or adds stutter before the boundary.

Keep the current loader as `aw_cell_change_method 1`. Trial read-ahead as method
2, with explicit buffer and prediction settings, and preserve the old method for
comparison. Judge the experiment by the complete visible transition, steady frame
times and audio service, not just one faster disk read. The existing frozen-frame
Loading presentation remains useful whenever a real pause is unavoidable.

### Put the work on the world map

It would help to see the whole island laid out as terrain, with the original
Morrowind cell grid and our converted areas marked on it. Seyda Neen and Balmora
would become visible examples of what is finished, what is partial and what has
yet to be touched. A topographic overview could guide the next town or route
without implying that terrain alone makes a complete playable region.

Original cells are useful units for source inventory and progress tracking.
Runtime regions can still follow different boundaries where memory, geometry and
sightlines demand it. We should investigate both together before committing the
whole world to either one-cell-at-a-time loading or a single uniform subdivision.

A related future convenience is a translation from the current local XYZ display
to original world coordinates and a clearly defined world-map coordinate view.
Establish the transforms first, including interior limitations and negative cell
boundaries. The proposed small upper-right display and `dbg global coords` switch
belong in [the roadmap](ROADMAP.md#future-world-coordinate-hud-investigate-first-not-v0024-work),
not in this release's implementation queue.

### Meet the entire cast on a plain floor

The character model gallery should make conversion inspectable. A quiet, evenly
lit plane is enough: one actor at a time, at the correct scale, with a footprint
square beneath it and room to walk around. Start with the largest creatures and
work down to the smallest. Include humanoids, enemies and animals, with equipped
and base-body views where the source separates clothing from the body.

Enter through `dbg aw charplane`, with `dbg modelgallery` and `dbg npcgallery` as
aliases. Keep next/previous controls and lookup instructions on screen. Names,
original IDs and stable conversion numbers should all lead to the right entry;
searching for Dagoth Ur should not require guessing punctuation. The catalogue
can be large on disk. Only the selected model needs to occupy the inspection
scene. Failed conversions must remain visible in the inventory so nothing is
quietly omitted from the claim of complete coverage.

### Residents should arrive on the ground when they are meant to

The Balmora floaters point to a workflow problem as well as individual bad
placements. A converted town should not depend on someone walking every street
to discover residents suspended above the paving. The main check belongs in the
build: establish the intended initial state, resolve support against the complete
owning scene, then independently measure the rendered model against the final
collision geometry. An unresolved placement should stop packaging.

There is a subtle trap in the overlapping sub-cells. A distant copy can retain a
visible platform while omitting its collision hull. Settling its occupant against
that reduced scene can move them to the terrain underneath. Compute a canonical
placement where the support is complete, and carry it unchanged into the overlap
copies. Initial loading and save/sub-cell restoration must preserve that result.

The rule is intended support at initialization. Tarhiel must still fall from the
sky; cliff racers must still fly; Vivec must retain his levitating pose. Neither
race nor faction is enough to decide. Record explicit states and exceptions, and
flag unknown cases. The expensive geometric checks belong on the build machine,
leaving the Amiga with prepared placements and small, occasional diagnostics.
[The placement workflow](NPC_GROUND_CONTACT.md) defines the current guarantee and
its limits, including the difference between initial idle contact and later
animation or scripted movement.

### Finish the small things that break the illusion

Before final v0.0.24, work through the premature birthsign display, disappearing
NPC names and Talk hints, reported floating residents, the blank hill patch and
both sticky walking locations. Keep every reported camera and duplicate view in
[the feedback record](FEEDBACK-v0.0.24-rc1.md), and distinguish a reproduced fix
from a plausible explanation. The dancers question is settled: the remembered
trio belongs to Desele's in Suran, not Balmora's South Wall Cornerclub.

Take a few more honest native screenshots of Balmora along the way. Once the
fixes and checks are complete, the owner's intended release is **v0.0.24 —
Welcome to Balmora**, rather than another RC1 label. Record the remaining limits
plainly; a release milestone should make the project's progress easy to see.

### A browser and a safe return from the gallery

Add `dbg gallery` as the short entry command. Tab (with B as an alias) opens a
small browser of friendly names; case-insensitive keywords should find a
character without requiring exact punctuation. Keep its original ID and stable
conversion number visible when names overlap. This catalogue belongs on disk,
with only one page loaded while the debug browser is open.

Put the selected name below the viewport at the bottom right, with a Talk hint
when a converted greeting is available. F1 should explain only the gallery's
controls: next and previous, Shift+B for the base body, browsing, lookup and
return. Ctrl+X and `dbg gallery exit` should restore the game captured on entry.
That also makes this a useful future bench for testing one NPC's dialogue trees
against a known state, without carrying test changes back into the adventure.
Full topic and result-script support remains separate work. Scrolling will be
needed for longer topic lists and text panels.

The immediate build is RC2 for another owner test where necessary; final
**v0.0.24 — Welcome to Balmora** remains the goal after the outstanding checks.

### An inspection checkpoint before the final release — 1 October 2026

The gallery should turn repeated model inspection into a durable conversion
record. Source identities remain stable, shared appearances point to the same
asset, and an approval follows that asset only while its checksum remains the
same. Larger models should receive specific allowances when justified; one
troublesome outfit must not raise every actor's budget. An automatic setting
means using those recorded allowances within the renderer's tested ceiling.

RC2 gives us a useful checkpoint for more playtesting while the remaining model,
foot-contact and walking cases are investigated. Keep those cases visible, retain
the original renderer, and promote the final release only with clear evidence.

### The late shift: leave nobody out — 1 October 2026

After RC2 went up, the last request before bed was simple: every character model
must make it into the gallery. A searchable list is useful, but an unavailable
entry cannot show whether a robe, face or creature has survived conversion.
The gallery earns its place when it lets us inspect the whole cast and keep a
reliable record of what we have seen.

There is something fitting about spending the last stretch before "Welcome to
Balmora" making sure its residents can stand on their own feet. The streets
already feel like a place. The remaining work is in the details that keep
breaking that feeling: a floating resident, an invisible step, an outfit that
costs a few more triangles than expected. Those deserve investigation while
the original report is still easy to reproduce.

Keep the difficult models intact where possible, give justified exceptions
their own measured limits, and record the results without pretending that a
successful conversion is a visual approval. The final release should leave us
with both a more convincing Balmora and a process we can trust in the next town.
The project title now states the ambition plainly: **AmiWind - Bringing TES III:
Morrowind to Commodore Amiga**.

### After Balmora: joining the island — 1 October 2026

The next leap should be geographical: a terrain-and-texture map of Vvardenfell,
cell by cell, with our two existing towns finding their place in it. Use
Morrowind's own cells first. Smaller regions are a tool for places that need
them, not a requirement to chop up every quiet stretch of countryside. A bridge
in Vivec might make a natural crossing, but the source layout and measurements
should decide that.

Seyda Neen and Balmora have also taught us how to approach the next dwelling:
keep its complete geometry, connect its doors, retain its residents and check
the result against the packaged collision. Those lessons should become reusable
steps, with exceptions brought into view rather than worked around invisibly.
Once the terrain connects, a full-screen map on M and a proper character-and-
equipment inventory on I will have a much larger world to serve.

One final visual lesson arrived with the pale faces: the blight is an amusing
excuse for grey blotches, but it is not a rendering fix. The palette and its
lighting tables have to agree. Dagoth Ur deserves his gold mask, and the Nords
and Bretons deserve their actual skin colours.


### The ashen faces, and three familiar keys — 1 October, late night

The pale faces had been wearing a little too much Vvardenfell ash. This time the
Blight was innocent: new warm palette entries were still passing through old
lighting and fog tables, which remembered them as sky grey. Repairing those
columns restores their colour without spending more polygons or adding runtime
work. There is still room to improve small faces and texture seams, but that is
a separate problem from turning healthy Nords grey.

The next interface milestones have familiar homes: M for the world map, I for
inventory and equipment, and J for the quest journal. After v0.0.24, the island
terrain and its polygon-density survey should guide expansion cell by cell,
using smaller regions only where measured density requires them. Seyda Neen and
Balmora have given us the beginnings of a repeatable conversion workflow; the
next task is to make that knowledge travel with every new settlement.

## 1 October: give the island a common map

Balmora's stairs are behaving much better in the owner's latest roaming, and
the obvious floating residents have stopped spoiling the streets. That is a
welcome change in the feel of the place. The precise outstanding contact and
wedge reports still belong in the investigation ledger; a pleasant walk and a
complete placement audit answer different questions.

The next leap is to see how these two towns belong to the island around them.
The first survey now joins all 1,292 terrain grids, with Seyda Neen and Balmora
fitted to the same source coordinates. The height edges agree. The geometry
survey also gives us something better than guessing where the next city will
need smaller regions: a map of actual placed meshes and their overlap costs.
Start with Morrowind's cells, split where the evidence asks for it, and carry
the lessons about doors, dwellings and grounded residents into each new area.

There is now a beginning for the player's own record of that journey as well:
a two-page journal, opened with J, showing entries earned during play. It is
small by design. The island overview and the journal's words stay on disk until
they are needed. A map of the whole island is a useful first step; walking its
length, with the right textures and no broken crossings, is the next proof.

## 1 October 2026 - Welcome to Balmora (and Vvardenfell!)

The island has become a measurable whole. Seyda Neen and Balmora gave us the
workflow; the terrain and polygon-density survey now gives us a way to decide
where to apply it next. Start with Morrowind's own cells, divide only where the
measured workload demands it, and preserve the sense of an open world.

This is a major milestone in mapping Vvardenfell, not the completion of every
place on it. Solstheim and Tribunal are outside the present base-game scope.
The map and two-page journal now belong to the Amiga runtime, while the next
terrain conversions can build on a common coordinate system. Character creation
and the complete model gallery give the project faces as well as geography;
Dagoth Ur has earned a place on the main page, gold mask and all.

The owner chose to close v0.0.24 as a milestone release after RC playtesting.
Known placement findings remain written down and the strict audit remains
failed. A release number records the work we are shipping; it does not erase
the work still ahead.
