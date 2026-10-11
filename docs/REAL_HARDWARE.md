# Running AmiWind on real Amiga hardware

AmiWind has so far been tested in emulators (FS-UAE: A1200, AGA, 68040 with FPU, 2 MiB Chip and 16 MiB Fast RAM,
JIT). No run on a real Amiga has been measured yet. If you have one, this page lists what the game needs, what to
run first, and which settings use more memory. Measurements from real machines are very welcome: see
[how to report](#what-to-send-back).

## Contents

- [What the game needs](#what-the-game-needs)
- [Before you start: 68060 and Kickstart 3.1](#before-you-start-68060-and-kickstart-31)
- [First measure, then play](#first-measure-then-play)
- [More Fast RAM: the memory settings that exist today](#more-fast-ram-the-memory-settings-that-exist-today)
- [Disk buffers and RAM disks](#disk-buffers-and-ram-disks)
- [A cache test plan](#a-cache-test-plan)
- [Not yet: automatic sizing and non-blocking disk reads](#not-yet-automatic-sizing-and-non-blocking-disk-reads)
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

On a 68060 with Kickstart 3.1, install your own `68060.library` and let the game load it at boot:
[FPU support library](FPU_SUPPORT_LIBRARY.md) (your own copy; it is never shipped). Without it the start-up check
stops at the FPU line: [BOOT-68060-FPU-FAIL-32](bugs/BOOT-68060-FPU-FAIL-32.md) (open).

## First measure, then play

`awbench` measures the machine without any game data: CPU and FPU speed, Chip and Fast RAM throughput, disk
transfers and the CPU time left while the disk reads. Run it first, so there are numbers even if the game does not
start: [hardware benchmark](HARDWARE-BENCHMARK.md).

In the game, `dbg rcount` (what each frame draws) and `dbg logs live on` (writes frame stalls, cell load times and
a walk profile to log files) give the numbers that matter most ([console commands](AMIWIND_CONSOLE_COMMANDS.md)).

## More Fast RAM: the memory settings that exist today

These are in the engine now ([CHIM engine](chim/ENGINE.md), [memory guide](chim/build_guide/MEMORY.md)):

| Setting | What it does | Default |
| --- | --- | --- |
| `-chimcache KIB` (start argument) | Extra Fast RAM for CHIM's cache: shared models and textures stay in memory across map changes instead of being read again. Taken once at start; if the memory is not there, the console says so and the standard budget is used. | off |
| `-heapmb N` (start argument) | The game heap in MiB for this start (1 to 2047). | 11 (the built size) |
| `chim_prefetch` | How far ahead of the visible ring CHIM loads chunks (-1: the world's own value). | -1 |
| `chim_lookahead` | Loads ahead in the direction you walk (-1: the world's prefetch margin). | -1 |
| `chim_prefetch_room` | Prefetch only into free memory, so it never pushes out what is in use. | 1 |

The chunk and model cache evicts what was used longest ago (LRU), and loading has a per-frame budget.

On a machine with a lot of Fast RAM, for example an accelerator with 128 or 256 MiB, start with a larger cache and
heap, such as `-chimcache 32768 -heapmb 32`, and compare the numbers with the defaults.

## Disk buffers and RAM disks

- **Filesystem buffers.** `AddBuffers DW1:` shows the buffers of the volume holding the game (use your own volume
  name); `AddBuffers DW1: 100` adds 100 more (it adds, it does not set the total). They are small FFS buffers that
  mostly hold filesystem blocks such as the ones that locate data inside large files, not a large data cache.
  `awbench buffers DRIVE N` repeats the disk test with another buffer count ([hardware benchmark](HARDWARE-BENCHMARK.md)).
- **Block cache tools.** A third-party disk cache may help, but try it as a comparison with and without, not as a
  requirement.
- **RAM disk.** `RAM:` can hold a few frequently used files, but the game data is gigabytes, the files must be copied
  in at every start, saves must stay on a real disk, and a RAM disk copy plus CHIM's own cache keeps the same data
  twice. CHIM's own cache (`-chimcache`) is the better first choice: it keeps what the engine actually uses, already
  decoded.

## A cache test plan

Suggested settings to compare (not measured recommendations; keep the heap at its default at first):

| Run | Start arguments |
| --- | --- |
| Baseline | none |
| Small | `-chimcache 8192` |
| Medium | `-chimcache 32768` |
| Large | `-chimcache 65536` |

For each: a cold start, then the same walk twice through Seyda Neen, Balmora and Vivec. Note the load times, the
worst stalls, and the sound (does the music skip). The console command `chim` prints the cache bank's use, loads,
evictions and file reads; `dbg rcount` adds the per-frame counts.

On accelerators whose Fast RAM comes in more than one region, the regions may differ in speed or in what a disk
controller can reach by DMA; if a large cache behaves oddly, note how much memory the card has and where.


## Not yet: automatic sizing and non-blocking disk reads

Planned for v0.0.38 ([roadmap](ROADMAP.md)):

- The cache and heap sized automatically from the free Fast RAM at start, so a big-memory machine uses it without
  start arguments.
- Disk reads that never stop a frame. Some reads during play still wait for the disk
  ([ENGINE-SYNC-IO-MAIN-LOOP-36](bugs/ENGINE-SYNC-IO-MAIN-LOOP-36.md)); a real hard disk or card is slower than an
  emulator's host disk, so this matters more on real hardware.

## What to send back

The machine (model, CPU and its revision, clock, FPU, Chip and Fast RAM, Kickstart, disk or card), the `awbench`
results, and from the game: where you were, the `dbg rcount` lines, the log files of `dbg logs live`, and a
screenshot. Report through
the project's issue tracker on GitHub.
