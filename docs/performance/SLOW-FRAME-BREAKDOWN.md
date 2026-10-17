# Where a slow frame goes (October 2026)

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

What a frame in Balmora costs on a slow accelerated Amiga, part by part, and what that means for the speed work.
These are emulator measurements: FS-UAE, cycle-exact 68040 with FPU at about 50 MHz (the slow accelerator preset of
[CHIM-SLOWCPU-FRAMETIME-33](../bugs/CHIM-SLOWCPU-FRAMETIME-33.md)), A1200 AGA, 2 MiB Chip and 16 MiB Fast RAM, the
v0.0.41 release image, at the five benchmark cameras of the [hardware benchmark](../HARDWARE-BENCHMARK.md). They
compare parts of the same frame with each other; they are not real-machine frame rates. The first real-machine figure
so far is about 0.2 frames per second on a 100 MHz 68060 with an earlier build ([real hardware](../REAL_HARDWARE.md)).

The counters used here are `dbg rcount 3` and `dbg rcount 4` ([renderer counters](RENDERER-COUNTERS.md)). With them
off, the engine draws exactly the same frames.

## The 3D view, with and without the placed models

| Camera | Normal view (ms) | Models off (ms) | Fog off (ms) | Both off (ms) |
| --- | ---: | ---: | ---: | ---: |
| 1 | 1,525 | 321 | 1,504 | 305 |
| 2 | 1,243 | 372 | 1,226 | 358 |
| 3 | 716 | 284 | 690 | 267 |
| 4 | 1,017 | 325 | 998 | 309 |
| 5 | 866 | 324 | 848 | 309 |

The placed models (houses, rocks, props: everything except the ground) are 60 to 79 % of the 3D view, including the
edge scanning their surfaces cause later in the frame. Turning the distance fog off saves little here, because the
day and night sky pass still runs; that pass needs its own timer.

## Inside the model cost

Each model is drawn as a Quake brush model: its tree is walked against the view, and its polygons are cut into
pieces (fragments) that go on to the edge list.

- Walking the trees costs about 13 microseconds per node and is half of the model cost or more (49 to 61 %).
- Emitting the fragments costs 60 to 84 microseconds per fragment and is the other 34 to 46 %; counting the edge
  scanning they cause afterwards, it is as large as the walk or larger.

## Where the faces come from

- 40 to 63 % of the faces sent come from models whose centre is past three quarters of the draw distance.
- 6 to 31 % come from models whose centre is beyond the fog plane, which are drawn almost entirely in fog colour.
- Medium and large models (radius 128 to 512 units) send 40 to 60 % of the faces; small clutter (under 32 units)
  only 1 to 13 %.
- Each placed model touches 12 to 33 world leaves on average. Quake has a cheap path for a model that sits in one
  leaf; only 0 to 6 models a frame take it.

## What it means for the speed work

1. **Fewer faces from far, medium and large models.** First skip only what is provably drawn entirely in fog colour
   (no visible change), then distance and size settings as options the player can choose. This cuts the walk, the
   fragments and the edge scanning together.
2. **A coarser drawing tree for the ground**, so most models sit in one leaf and take Quake's cheap path. This cuts
   the walk only, with no change to the picture or to collision.
3. Then the sky and fog pass and the rest of the frame, measured with their own timers first.

The AGA picture stays the default throughout: every change either draws the same image more cheaply or is an option.
See the [CHIM ideas page](../chim/IDEAS.md#the-slow-accelerator-reality) for the plan and
[AmiWind on the 68060](../68060.md) for the processor side.

## Small gains add up, and real machines set the scale

No single change is expected to make a frame ten times cheaper. The work above is a series of separate steps, and
their gains multiply: ten steps that each make the frame 10 % faster give about 2.6 times the speed, ten steps of
20 % about 6 times, ten steps of 30 % about 14 times. That is how the several-fold speed-up needed for a frame of
about a tenth of a second (10 frames per second) can be reached without one large rewrite. Each step is measured on
its own, at the same cameras, before the next one starts. A step that must not change the picture is checked for
pixel-identical frames against the previous build, and the renderer counters at the benchmark cameras show when a
later change gives a gain back.

All the figures on this page come from an emulator. They show how the parts of a frame compare with each other and
whether a change helped, but not how fast a real machine is. Emulator timing on a 68060 in particular is only an
approximation of the real processor. One run on a real machine per processor class (a 68040, a 68060) is enough to
set the scale for every emulator figure of that class. Reports from testers with real hardware are therefore the
calibration set: the build, the machine, the place in the game and two or three lines of `dbg fps` and
`dbg rcount` (see the [hardware benchmark](../HARDWARE-BENCHMARK.md) and [real hardware](../REAL_HARDWARE.md)
pages for what to send).

Why every instruction counts on a machine with one processor and one instruction stream, the four ways to make a
frame faster and the planned cycle model are explained on [one processor, one instruction stream](SINGLE-CORE-THROUGHPUT.md).

## Processor traps on the 68060

A 68060 runs the same instructions as a 68040 except a few, which it hands to its support library
(`68060.library`) to emulate in software. The engine built for the 68040 uses some of them in exactly the code
above: `R_RecursiveClipBPoly`, the model tree walk, turns two float comparisons per node into true or false values
(`fscc`), and `R_EmitEdge` does the same per edge. Counted on an emulated 68060 (FS-UAE, JIT off so these
instructions trap as on the chip), 17 October 2026, the v0.0.41 release disks, the same cameras:

| Camera | Traps per frame, 68040 build (measured) | 68060 build (measured) | At 100 MHz, 200 to 500 clocks a trap (estimated) |
| --- | ---: | ---: | --- |
| 1 | 424,064 | 3.6 | 0.85 to 2.1 s, 17 to 42 % of a 5 s frame |
| 2 | 282,443 | 3.2 | 0.56 to 1.4 s, 11 to 28 % |
| 3 | 186,895 | 3.5 | 0.37 to 0.93 s, 7 to 19 % |
| 4 | 238,433 | 2.5 | 0.48 to 1.2 s, 10 to 24 % |
| 5 | 206,378 | 1.5 | 0.41 to 1.0 s, 8 to 21 % |

Measured: the number of trapped instructions per frame (exact counts, the same in repeated runs within 1 %),
and where they are (67 to 76 % in the tree walk, 20 to 29 % in edge emission). Estimated: the clocks per trap
(an exception plus software emulation; not yet measured on a real 68060) and therefore the time; the 5 s frame
is the one real 68060 figure so far (about 0.2 frames per second at 100 MHz, an earlier build, other places).

The 68060 build of the same source (`AmiWind060`, from v0.0.42 on the game disk beside the 68040 build and
picked at boot on a 68060) has no `fscc` and no 64-bit multiply in engine code: its few traps per frame are the
C library's random numbers.

Why the share grows as the 3D work gets cheaper: there is one processor and one instruction stream, so the trap
time adds to everything else in the frame. The traps come one per tree node and per edge; cutting the models'
faces and nodes cuts them too, but the rest of the frame (sky, spans, the 2D screen) does not trap, so every
millisecond saved elsewhere makes the traps a larger part of what is left. On a 68060 removing them is a gain of
its own, independent of the other work. Details and method: [AmiWind on the 68060](../68060.md#trapped-instructions-per-frame).
