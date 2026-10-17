# One processor, one instruction stream

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

Why speed on a 68060 Amiga is a question of how many instructions a frame runs and how fast each one goes, and how
the speed work is organised around that. Measured figures for the frame are on
[where a slow frame goes](SLOW-FRAME-BREAKDOWN.md); the processor side is on [AmiWind on the 68060](../68060.md).

## Nothing hides the cost

A modern PC hides a lot of waste. Other processor cores take background work, a graphics processor does the 3D
drawing, and the processor itself reorders instructions and runs many of them at once while it waits for memory.
A 68060 Amiga has one processor running one stream of instructions, and the graphics chips do no 3D work. The 68060
has a short, in-order pipeline that can run two simple instructions together, and that is the only overlap there
is. Every instruction, every trap to a support library, every wait for memory and every cache miss is time taken
directly from the frame.

Roughly, the time of a frame is:

    frame time = instructions run x cycles per instruction + cycles spent waiting (stalls)

## Four ways to make a frame faster

1. **Run fewer instructions.** A better method beats faster code: not drawing what cannot be seen, drawing distant
   and small things with less detail, and taking cheaper paths that already exist in the engine. This comes first,
   because it removes work rather than speeding it up.
2. **Use cheaper instructions.** Some floating-point instructions that the 68040 runs are not built into the 68060
   and trap to a support library, which is far slower than the instruction itself. A build compiled for the 68060
   avoids them. Where the 68060's floating-point unit is slow, integer or fixed-point arithmetic can take its place.
3. **Run more instructions per cycle.** The 68060 can issue two integer instructions in the same cycle when they
   fit together (pair). A compiler that targets the 68060 arranges code for that; hand-written assembly is kept for
   the few hottest loops that measurement points to.
4. **Wait less.** The 68060 has an 8 KB instruction cache and an 8 KB data cache. Loops that fit in the instruction
   cache and data packed closely enough to stay in the data cache avoid slow trips to memory.

## Cost times count

A waste matters in proportion to how often it runs. A few extra cycles in code that runs once a frame are nothing;
the same cycles in code that runs hundreds of thousands of times a frame are a large share of it. An illustrative
example, not a measurement: 10 wasted cycles in a path that runs 100,000 times a frame are 1,000,000 cycles, which is
a tenth of the whole budget of a 10 frames-per-second frame on a 100 MHz 68060 (10,000,000 cycles). So the work
starts from measured counts (how many tree nodes, fragments and faces a frame handles, from the
[renderer counters](RENDERER-COUNTERS.md)) and only then looks at the cost of each.

## Predicting the frame before a real machine runs it

The emulators run 68060 code correctly but do not reproduce its timing: they do not model which instructions pair,
how the pipeline stalls or exactly how the caches behave. Timings from the emulator are therefore relative. The plan
is a cycle model that predicts a 68060 frame:

- how often each block of code runs in a frame, counted in the emulator;
- multiplied by the 68060's published instruction timings and pairing rules;
- plus the cost of traps to the support library;
- plus a model of the instruction and data caches.

The model is not built yet. Once it is, one run on a real machine per processor class (a 68040, a 68060) calibrates
it, and from then on it can estimate the effect of a change before anyone runs it on hardware. Reports from testers
with real machines (the build, the place, `dbg fps` and `dbg rcount` lines; see
[real hardware](../REAL_HARDWARE.md)) are that calibration.
