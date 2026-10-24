# Performance lessons learned

_Last updated with AmiWind v0.0.48-dev2 (22 October 2026)._

<!-- contents start -->
## Contents

- [Equal meshes that were not equal (22 October 2026)](#equal-meshes-that-were-not-equal-22-october-2026)
- [Rooms one after another (22 October 2026)](#rooms-one-after-another-22-october-2026)
- [A walkway fix that weighed on every rock (20 October 2026)](#a-walkway-fix-that-weighed-on-every-rock-20-october-2026)
- [The ruin that was mostly collision (16 October 2026)](#the-ruin-that-was-mostly-collision-16-october-2026)
- [What a town frame is spent on (8 October 2026)](#what-a-town-frame-is-spent-on-8-october-2026)
- [The walls Quake never saw (7 October 2026)](#the-walls-quake-never-saw-7-october-2026)
- [The file reader we never measured (7 October 2026)](#the-file-reader-we-never-measured-7-october-2026)

<!-- contents end -->

Lessons from measuring AmiWind's loading on the emulated reference machine.
Newest first.

## Equal meshes that were not equal (22 October 2026)

Cutting today's interiors into a shared store saved nothing: 16,950 placements gave 7,313 distinct models, 244 MB plus
48 MB of light, from 303 MB of rooms. The cause was in how the rooms are made. A tilted placement has its rotation
baked into its own model, and a lit placement has its faces split on its own light grid. So two copies of the same mesh
differ by up to 0.27 units and in texture mapping, and no two can be stored as one.

What we learned:

- Baking a placement's tilt and light into its model makes equal meshes differ. Sharing needs one model per mesh, with
  the turn applied at run time and the light kept as a small value per placement.
- Measure what makes copies differ before building a store on the idea that they are equal. One measuring pass
  (`tools/interior_store.py measure`) showed the cause.
- With one model per mesh the same 56 rooms came to 20.7 MB of store plus 0.59 MB of room maps, against 79.3 MB.
  Speed and memory inside the rooms are not measured yet.

## Rooms one after another (22 October 2026)

The builder stage that converts interiors handled the rooms one after another, and ran only a few meshes of each room
in parallel. Most cores sat idle. Running the rooms side by side, one room per worker, largest first, cut the 56 rooms
from about 5 minutes to 19 seconds on 20 workers (about 18 cores busy).

What we learned:

- Never serialize independent units. A room does not depend on another room, so rooms are the unit of work, not the
  few meshes inside one room.
- Give the largest units out first, so the last worker is not left with the biggest room.
- A stage that uses under half its cores for over a minute is a bug to register and fix, not a number to list.

## A walkway fix that weighed on every rock (20 October 2026)

The player sank to the knees on the Vivec dock walkways, because the convex collision pieces lost the surface they
were cut from. The repair (CHIM-VIVEC-DOCK-WALKWAY-43) went into the shared converter, as it should, and covered
the 484 mesh types with the same loss. But it gave every piece the hull of all its points: walls, undersides and
every rock corner, not only the surface the player stands on. Island-wide that added about 55 MB of stored planes
and nodes and 11 MB of collision; 1,196 of 1,351 frames grew, and six went over the memory zone. The first full
build to carry it failed at its heap gate after 2 h 38 min (CHIM-HULL-SURFACE-HEAP-46).

What we learned:

- A fix in the shared converter must be measured where it costs, not only where it helps. The walkway fix was
  checked at the walkway; its memory estimate counted one kind of collision node and promised +110 KB.
- A heap check on the tightest frames takes minutes. `tools/chim_heaviest_frames.py` now lists them for a quick
  `chim_build` check before a converter change merges; run on the previous world, it names exactly the six frames
  that failed.
- Only what the player stands on needs to be exact. Pieces now keep their walkable surface and give the sides the
  cheaper hull: the added planes fall by about two thirds, and the walkway still holds the player.
- One visible trade was made to fit the last frame, by the maintainer's decision: collision-free kelp and grass
  copies are rounded to 0.1 of scale (at most 5 % of their drawn size) so copies share one model (`--scale-snap`,
  on by default, can be switched off). It is checked in the v0.0.46-dev1 playtest.
- The deeper answer is not to guess at collision and then measure it, but to build it from what the game already
  says (see the roadmap, "Collision from what the game already knows").

## The ruin that was mostly collision (16 October 2026)

Five Bitter Coast cells near Hla Oad did not fit the CHIM memory budget (7.1-7.3 MB against 6.24 MB).
The heap report put the blame on drawn geometry, and the mesh optimizer looked like the fix. It was
not: Ashurnibibi's ruin meshes carried about 31,000 collision planes for 1,750 drawn faces, because
their compact compiled collision had failed and the raw chain of convex pieces was kept. The compiler
refused the pieces over sliver faces from near-identical planes; merging coplanar facets before
writing them fixed it, and all five cells fit with 120-360 KB to spare
([CHIM-COLLISION-UNION-FALLBACK-41](../bugs/CHIM-COLLISION-UNION-FALLBACK-41.md)).

1. **Read the model's own bytes before choosing a fix.** A memory category in a report is a summary;
   the lump sizes of the heaviest models (planes, clipnodes, nodes, faces) say what to change.
2. **A fallback is a finding.** The build listed the meshes whose collision fell back, but not as a
   problem and without the reason; 24 meshes across the island carried it.
3. **Keep the error's head.** The stored message was the last 200 characters of the compiler's
   output, which were warnings; the error line was earlier.
4. **Measure blanket methods.** The mesh optimizer on every mesh made these frames 1.5 MB larger.

## What a town frame is spent on (8 October 2026)

The engine now counts its own work per frame (`dbg rcount`: brush models in
view, faces clipped, fragments, world-BSP nodes visited, surface and edge cache
use, and the time of each render stage). Ten fixed cameras in Balmora and
Seyda Neen, measured in FS-UAE, gave the same counts on every repeat:

| | Balmora (5 cameras) | Seyda Neen (5 cameras) |
| --- | --- | --- |
| Fragments per clipped brush-model face | 1.38-1.59 | 1.03-1.05 |
| World-BSP nodes visited per clipped face | 27-52 | 3-5 |
| Node visits per frame | 79,907-233,867 | 16,713-33,555 |
| Share of render time in brush models | 67-82 % | 39-59 % |
| Surface cache blocks built per frame, camera still | 0 | up to 914 (812 KB) |
| Edges reused from the previous frame | 190-350 | 0 |

What we learned:

1. **The cost was the walk, not the pieces.** We expected brush models to cost
   time by being cut into many fragments
   ([RENDER-BMODEL-FRAGMENTS-32](../bugs/RENDER-BMODEL-FRAGMENTS-32.md)). They
   are barely cut. What costs is finding where each face goes: in Balmora every
   clipped face walks 27-52 nodes down a deep world BSP, transforming each
   node's plane again every time. The fast one-leaf path is almost unused there
   (0-8 models in view).
2. **A still camera should not rebuild anything.** Seyda Neen views rebuild
   hundreds of surface cache blocks every frame because the cache is smaller
   than what they show
   ([RENDER-SURFCACHE-THRASH-32](../bugs/RENDER-SURFCACHE-THRASH-32.md)), and
   reuse no edges at all
   ([RENDER-EDGECACHE-SEYDA-32](../bugs/RENDER-EDGECACHE-SEYDA-32.md)).
3. **Count first, then time.** The counts are identical across runs and
   emulator settings; times are not. Counts are the main currency for
   comparing builds; times only compare within one batch.
4. **Emulator times are relative.** All earlier frame rates used FS-UAE with
   the JIT, which runs far faster than any real 68040
   ([BENCH-JIT-PROFILE-32](../bugs/BENCH-JIT-PROFILE-32.md)). A
   cycle-approximate 68040 at 24.8 MHz takes 148-188 times longer per frame
   (2.7-8.1 s at these cameras). That profile is a relative reference too, not
   a hardware number; one measurement on a real accelerated A1200 is still
   needed. FS-UAE ignores `uae_cpu_frequency` in this mode; only
   `uae_cpu_multiplier` sets the clock
   ([BENCH-FSUAE-FREQ-32](../bugs/BENCH-FSUAE-FREQ-32.md)).
5. **Remove the traps, then prove it.** With the C library's number parsing and
   formatting replaced by the engine's own, the instructions a 68040 has to
   emulate in software fell from 40 to 16 in the engine, and a strict-FPU run
   (no JIT, unimplemented instructions trap) rendered all ten cameras with no
   trap ([ENGINE-FPU-UNIMPL-31](../bugs/ENGINE-FPU-UNIMPL-31.md)). Saves,
   menus, combat and the intro are not yet covered.

## The walls Quake never saw (7 October 2026)

For months the frame rate in towns and interiors was treated as the limit of
the hardware. It was not measured where it mattered: every converted building,
room and rock was a `func_wall` model, which Quake's `vis` ignores, so the
visibility data saw straight through all of them. Interiors were one empty box,
100 % visible; Balmora 84-89 %. Shortening the fog distance roughly doubled the
frame rate in Balmora because it was the only thing removing hidden buildings.
Lesson: before calling anything a hardware limit, read the map's visibility
data and count what the engine is asked to draw. And count it the way the
engine does: the first occluder prototype split the map nicely, yet 589 of 590
building models stayed visible, because Quake keeps or drops an entity whole
and treats one linked to more than 16 leaves as visible everywhere. Leaf
counts alone would have called that a success. The full prototype then
showed that even fitted occluders and building faces in the world model barely
change what is sent in an open town: measure the engine's own decision before
building the fix. Details:
[Town visibility](TOWN-VISIBILITY.md); rule in
[DEVELOPMENT.md](../DEVELOPMENT.md).

## The file reader we never measured (7 October 2026)

Chasing a small slowdown in the v0.0.31-dev1 boot check
([SEYDA-READ-SLOW-31](../bugs/SEYDA-READ-SLOW-31.md)) turned up a much larger,
older cost: every loose game file was read through the C library's default
1 KiB stdio buffer, so loading a 4.8 MB Seyda Neen map took over 4,700
separate AmigaDOS reads. One line, a 16 KiB buffer when the file is opened,
cut map read time by more than half on every Seyda Neen sub-cell, and whole
crossings from 0.70-0.91 s to 0.39-0.48 s (FS-UAE, 68040, same disk, same
batch).

| Seyda crossing (dev1 engine) | 1 KiB buffer | unbuffered | 16 KiB buffer | 64 KiB buffer |
| --- | --- | --- | --- | --- |
| sn019 disk read | 0.63 s | 0.36 s | 0.26 s | 0.21 s |
| sn019 whole crossing | 0.82 s | 0.57 s | 0.47 s | 0.47 s |

64 KiB read faster still but made the rest of the load slower, so the whole
crossing gained nothing, and larger single reads hold up music streaming
longer on real hardware. 16 KiB shipped.

What we learned:

1. **Profile the real path before guessing.** The slowdown we were hunting
   was 0.1-0.2 s; the cost hiding next to it was 0.3 s and had been there
   since long before. Neither shows up until the actual read calls are timed.
2. **Compare many variants in one batch, with controls.** Running several
   emulators at once slows every run by up to a quarter, so numbers only
   compare within one batch. Every batch reruns the known-good build as its
   control, and tests every candidate at once (A/B/C/D, not a chain of A/Bs).
3. **Bisect over kept builds.** Every gate build was kept, so one batch over
   all of them showed exactly which change the slowdown arrived with.
4. **Disprove hypotheses with one targeted run each.** Host load, disk layout
   and buffer alignment were all plausible; a quiet rerun, a block-layout
   check and logged buffer addresses ruled each out. Call it a hypothesis
   until a measurement confirms it.
5. **Measure fixes, not just causes.** Testing the candidate read paths on
   both the fast and the slow engine found the fix, and also showed where the
   slowdown lives (it disappears without buffering), before its root cause
   was known.

Still open: with a buffer, the newer engine reads 10-15 % slower than the
older one for reasons not yet found; large direct reads into the game's own
memory are the next experiment. Target: 0.1-0.2 s per crossing everywhere.
