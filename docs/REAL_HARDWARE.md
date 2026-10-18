# Running AmiWind on real Amiga hardware

_Last updated with AmiWind v0.0.42-rc1 (17 October 2026)._

<!-- contents start -->
## Contents

- [Contents](#contents-1)
- [What the game needs](#what-the-game-needs)
- [Before you start: 68060 and Kickstart 3.1](#before-you-start-68060-and-kickstart-31)
- [First measure, then play](#first-measure-then-play)
- [More Fast RAM: the memory settings that exist today](#more-fast-ram-the-memory-settings-that-exist-today)
- [Disk buffers and RAM disks](#disk-buffers-and-ram-disks)
- [A cache test plan](#a-cache-test-plan)
- [Compatibility roadmap](#compatibility-roadmap)
- [Not yet: non-blocking disk reads](#not-yet-non-blocking-disk-reads)
- [PiStorm](#pistorm)
- [What to send back](#what-to-send-back)

<!-- contents end -->

AmiWind is developed in emulators (FS-UAE: A1200, AGA, 68040 with FPU, 2 MiB Chip and 16 MiB Fast RAM,
JIT). The first figure from a real Amiga came from a tester in October 2026: an earlier build on an A4000 with a
68060 at 100 MHz ran at about 0.2 frames per second, about 0.1 above the same tester's emulator runs. That is not
playable yet; making the frame cheaper is the main engine work now ([AmiWind on the 68060](68060.md)). More real
measurements, with the details listed under [what to send back](#what-to-send-back), are what turn emulator figures
into predictions for real machines. If you have one, this page lists what the game needs, what to run first, and
which settings use more memory. Measurements from real machines are very welcome: see
[how to report](#what-to-send-back).

## Contents

- [What the game needs](#what-the-game-needs)
- [Before you start: 68060 and Kickstart 3.1](#before-you-start-68060-and-kickstart-31)
- [First measure, then play](#first-measure-then-play)
- [More Fast RAM: the memory settings that exist today](#more-fast-ram-the-memory-settings-that-exist-today)
- [Disk buffers and RAM disks](#disk-buffers-and-ram-disks)
- [A cache test plan](#a-cache-test-plan)
- [Compatibility roadmap](#compatibility-roadmap)
- [Not yet: non-blocking disk reads](#not-yet-non-blocking-disk-reads)
- [What to send back](#what-to-send-back)

## What the game needs

- An AGA Amiga (A1200, A4000 or an AGA-compatible setup).
- A 68040 or 68060 **with an FPU** (EC and LC versions of the CPU have none).
- Kickstart 3.1 or later.
- At least 2 MiB Chip RAM and 16 MiB Fast RAM (the tested baseline).
- A disk or card for the game's drive images. Kickstart 3.1 limits: every partition under 2 GiB, and every
  partition must **start** within the first 2 GiB of its drive.
- The game itself is built from your own copy of Morrowind with the builder ([build setup](../README.md));
  no game data is distributed.

## Before you start: 68060 and Kickstart 3.1

On a 68060 with Kickstart 3.1, the game needs your own copy of `68060.library`, which it loads at boot (AmiWind
never ships it; see [FPU support library](FPU_SUPPORT_LIBRARY.md)). Without it the start-up check stops at the FPU
line: [BOOT-68060-FPU-FAIL-32](bugs/BOOT-68060-FPU-FAIL-32.md) (open).

From v0.0.42 the game disk has two engines and starts `AmiWind060` on a 68060 (the boot console says which). The
68040 engine makes a 68060 emulate 73,000 to 424,000 instructions per frame at the benchmark places (measured on
an emulated 68060; what that costs on a real one is estimated at up to about 40 % of a 5 s frame), the 68060 engine
about 3: [trapped instructions per frame](68060.md#trapped-instructions-per-frame). 68060 owners, please report
the build, `dbg fps`, the `dbg rcount` lines at the benchmark cameras, and whether `68060.library` and `SetPatch`
are installed; a file `S:AmiWind-68040` starts the 68040 engine instead, to compare both.

## First measure, then play

`awbench` measures the machine without any game data: CPU and FPU speed, Chip and Fast RAM throughput, disk
transfers and the CPU time left while the disk reads. Running it first gives useful numbers even if the game does
not start ([hardware benchmark](HARDWARE-BENCHMARK.md)).

In the game, `dbg rcount` (what each frame draws) and `dbg logs live on` (writes frame stalls, cell load times and
a walk profile to log files) give the numbers that matter most ([console commands](AMIWIND_CONSOLE_COMMANDS.md)).

## More Fast RAM: the memory settings that exist today

### Extra RAM is used automatically

At every start the game measures the free Fast RAM. What is free beyond a margin left to the system (2 MiB plus
an eighth of all Fast RAM) becomes CHIM's cache: shared models, textures and streamed pieces of the world stay in
memory, pieces you walk away from stay there too, and the world is fetched further ahead in the direction you
travel (two chunks ahead from 8 MiB of cache, three from 32 MiB). There is no upper limit other than the machine:
Fast RAM spread over several boards (accelerator RAM and a Zorro III card) is taken as several banks, largest
first, each under 2 GiB, so 2 GiB and more works too.

- **16 MiB of Fast RAM (the reference machine) takes nothing:** with the 11 MiB game heap only about 1 MiB is
  free, under the margin, so the game plays exactly as without this feature. The first cache bank needs at least
  8 MiB beyond the margin (about 30 MiB of Fast RAM or more).
- **The console says what happened on every start**, for example
  `Memory: 115 MiB Fast RAM free of 128 MiB; CHIM cache 97 MiB in 2 banks (automatic); look-ahead x3`
  or `Memory: 1 MiB Fast RAM free of 16 MiB; CHIM cache off (not enough extra Fast RAM, standard memory)`.
  The `chim` console command prints the same line.
- **A notice on the startup logo** says how much extra RAM was found and what it is used for. Pressing **M**
  while it shows starts this session without it (the standard memory). It never waits for a key; starts that
  skip the logo (the test options `aw_boot_console`, `aw_test_start`, a test drive's `test.cfg`) skip the notice.
- **Off for good:** Options > Extra RAM: Off (saved in `config.cfg` as `aw_autoram 0`; takes effect at the next
  start).
- **If the memory cannot be taken,** the console says so and the game plays on the standard memory.
- **The game heap stays at its built size** (11 MiB unless `-heapmb` or the builder's `--heap-mb` say otherwise):
  the extra goes to CHIM's cache, where the streaming memory runs full (Ebonheart, Khuul). A larger heap for
  Quake's own cache (actors and sounds) stays a manual setting until it is measured to help.

### The settings

These are in the engine now ([CHIM engine](chim/ENGINE.md), [memory guide](chim/build_guide/MEMORY.md)):

| Setting | What it does | Default |
| --- | --- | --- |
| `-chimcache KIB` (start argument) | Extra Fast RAM for CHIM's cache, by hand: shared models and textures stay in memory across map changes instead of being read again. Taken once at start; if the memory is not there, the console says so and the standard budget is used. Given, it replaces the automatic size (`-chimcache 0`: no cache bank at all). | automatic |
| `aw_autoram` (Options > Extra RAM, saved) | 1: free Fast RAM beyond the margin becomes CHIM's cache at the next start; 0: the standard memory always. | 1 |
| `-heapmb N` (start argument) | The game heap in MiB for this start (1 to 2047). | 11 (the built size) |
| `chim_prefetch` | How far ahead of the visible ring CHIM loads chunks (-1: the world's own value). | -1 |
| `chim_lookahead` | Loads ahead in the direction you walk (-1: the world's prefetch margin, two or three times that with an automatic cache of 8 or 32 MiB and more). | -1 |
| `chim_prefetch_room` | Prefetch only into free memory, so it never pushes out what is in use. | 1 |

The chunk and model cache evicts what was used longest ago (LRU), and loading has a per-frame budget.

On a machine with a lot of Fast RAM, for example an accelerator with 128 or 256 MiB, the cache is now sized by
itself; `-chimcache` and `-heapmb 32` remain for comparisons, and the interesting part is how the numbers compare
with Options > Extra RAM: Off.

## Disk buffers and RAM disks

- **Filesystem buffers.** `AddBuffers DW1:` shows the buffers of the volume holding the game (use your own volume
  name); `AddBuffers DW1: 100` adds 100 more (it adds, it does not set the total). They are small FFS buffers that
  mostly hold filesystem blocks such as the ones that locate data inside large files, not a large data cache.
  `awbench buffers DRIVE N` repeats the disk test with another buffer count ([hardware benchmark](HARDWARE-BENCHMARK.md)).
- **Block cache tools.** A third-party disk cache may help. It is not required, and it is best judged by
  comparing runs with and without it.
- **RAM disk.** `RAM:` can hold a few frequently used files, but the game data is gigabytes, the files must be copied
  in at every start, saves must stay on a real disk, and a RAM disk copy plus CHIM's own cache keeps the same data
  twice. CHIM's own cache (`-chimcache`) is the better first choice: it keeps what the engine actually uses, already
  decoded.

## A cache test plan

Suggested settings to compare (not measured recommendations; keep the heap at its default at first):

| Run | Start arguments |
| --- | --- |
| Baseline | Options > Extra RAM: Off (or M on the startup logo) |
| Automatic | none |
| Small | `-chimcache 8192` |
| Medium | `-chimcache 32768` |
| Large | `-chimcache 65536` |

Each run is a cold start followed by the same walk, twice, through Seyda Neen, Balmora and Vivec. The useful
notes are the load times, the worst stalls and the sound (whether the music skips). The console command `chim` prints the cache bank's use, loads,
evictions and file reads; `dbg rcount` adds the per-frame counts.

On accelerators whose Fast RAM comes in more than one region, the regions may differ in speed or in what a disk
controller can reach by DMA. If a large cache behaves oddly, how much memory the card has, and where, helps explain
it.


## Compatibility roadmap

Planned (project decisions, 16 October 2026; [roadmap](ROADMAP.md#near-future-one-game-for-the-68040-and-the-68060-16-october-2026)).
The baseline stays: the game is built and checked for an accelerated Amiga with the reference memory, and
everything below only adds to it.

The 68060 part has its own page, with what is known, the rules and the steps: [AmiWind on the 68060](68060.md).

- **One game for the 68040 and the 68060.** The engine reads the CPU and FPU type at start-up and picks its 68040 or
  its 68060-tuned version of each hot routine; the 68060 path avoids the instructions the 68060 emulates in
  software, and draws exactly the same picture.
- **The CPU support library, two ways.** Your own `68040.library` or `68060.library` (never shipped with AmiWind):
  put it in an `amiga-libs` folder next to your Morrowind `Data Files` folder before building, and the builder
  installs it on the game disk (`--amiga-libs DIR` chooses another folder); or drop it into the game disk's
  library folder after building. The boot script loads the one matching the CPU.
- **A clear message instead of a crash.** If the CPU needs a library that is not on the disk, the game says which
  file is missing and where to put it.
- **A boot notice when a 68060 is found without its library** (maintainer, 16 October 2026): a field set apart by
  dashed lines the width of the screen, saying that a 68060 was detected, that `68060.library` was not found, how
  to get the most out of the CPU, where to put the library on the game disk, and how to build the game with it
  (the `amiga-libs` folder next to `Data Files`). The notice waits a few seconds with a countdown and continues;
  pressing S stops the countdown so it can be read in full, and any key then continues.
- **Extra RAM as speed.** Since v0.0.42-rc1 the CHIM cache, the chunks kept after you leave them and the
  look-ahead grow with the free Fast RAM by themselves (above); still planned: a larger surface cache, visited
  interiors kept and read caching
  ([the cache plan](ROADMAP.md#the-cache-plan-extra-ram-spent-on-not-doing-work-twice-16-october-2026)).

## Not yet: non-blocking disk reads

Planned ([roadmap](ROADMAP.md), the cache plan above):

- Disk reads that never stop a frame. Some reads during play still wait for the disk
  ([ENGINE-SYNC-IO-MAIN-LOOP-36](bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md)); a real hard disk or card is slower than an
  emulator's host disk, so this matters more on real hardware.

## PiStorm

[PiStorm](https://pistorm.github.io/) is an open-source accelerator: a Raspberry Pi takes the place of the Amiga's
680x0 CPU, and Emu68, a bare-metal just-in-time translator, turns the 68k instruction stream into native ARM
(AArch64) code as it runs. The Amiga's own chipset stays in place, so the picture still comes from AGA, as
AmiWind expects. The hardware and software are published under open-source licences (BSD-like to MPLv2), and the
JIT's speed can be adjusted while the machine runs, from timing-friendly settings up to full speed. Project page
and documentation: [pistorm.github.io](https://pistorm.github.io/) (read 17 October 2026).

What it means for AmiWind, on paper (no AmiWind run on a PiStorm has been reported yet):

- **The CPU and FPU.** Emu68 presents itself as a 68040 with an FPU, the CPU the standard engine build targets
  ([FAQ](FAQ.md#can-todays-heavily-upgraded-amigas-realistically-run-amiwind)).
- **Memory.** A Pi gives the Amiga far more Fast RAM than the 16 MiB reference. AmiWind uses the extra Fast RAM by
  itself as the CHIM cache ([above](#extra-ram-is-used-automatically)), so a PiStorm machine keeps more of the
  world in memory and streams less from the disk.
- **Use full speed for playing.** The timing-friendly JIT settings exist for software that needs exact 68k
  timing; AmiWind does not, and benefits from the fastest setting.
- **The disk.** The game's drive images still need a disk or card the Amiga can boot from, with the Kickstart 3.1
  partition limits above.

- **The picture goes through the chipset.** The PiStorm project's own
  [performance page](https://pistorm.github.io/docs/benchmarks/) notes that drawing to an OCS/AGA bitplane screen is
  limited by the chipset and by the PiStorm's link to the Amiga, not by the CPU. AmiWind draws every frame into
  Chip RAM for the AGA screen, so on a PiStorm the CPU work (the 3D view) should shrink a great deal while the
  per-frame copy to Chip RAM stays roughly where the chipset puts it. Measurements will tell how the two share the
  frame.
- **Comparable numbers.** The same page treats synthetic benchmarks with caution and uses real programs instead,
  among them the DoomAttack timedemo (AGA and RTG modes, frames per second from the reported ticks). A report with
  both AmiWind's own `awbench` / timedemo and that DoomAttack figure places AmiWind beside other PiStorm results.

A first report from a PiStorm (which board, which Pi, the Emu68 version and its JIT settings, Fast RAM, the
`awbench` results and, if you have it, the DoomAttack figure) would turn this section into measurements. See
[what to send back](#what-to-send-back).

## What to send back

A useful report describes the machine (model, CPU and its revision, clock, FPU, Chip and Fast RAM, Kickstart, disk
or card) and includes the `awbench` results. From the game, it helps to have where you were, the `dbg rcount`
lines, the log files of `dbg logs live` and a screenshot. Reports go to the project's issue tracker on GitHub.
