# Performance lessons learned

Lessons from measuring AmiWind's loading on the emulated reference machine.
Newest first.

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
counts alone would have called that a success. Details:
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
