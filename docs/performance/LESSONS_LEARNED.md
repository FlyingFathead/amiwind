# Performance lessons learned

Lessons from measuring AmiWind's loading on the emulated reference machine.
Newest first.

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
