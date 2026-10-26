# Running AmiWind on real Amiga hardware

_Last updated with AmiWind v0.0.52 (26 October 2026)._

<!-- contents start -->
## Contents

- [Contents](#contents-1)
- [Which machines AmiWind aims at](#which-machines-amiwind-aims-at)
- [What the game needs](#what-the-game-needs)
- [Why 32 MB of Fast RAM](#why-32-mb-of-fast-ram)
- [Before you start: 68060 and Kickstart 3.1](#before-you-start-68060-and-kickstart-31)
- [First measure, then play](#first-measure-then-play)
- [More Fast RAM: the memory settings that exist today](#more-fast-ram-the-memory-settings-that-exist-today)
  - [Extra RAM is used automatically](#extra-ram-is-used-automatically)
  - [The settings](#the-settings)
- [Disk buffers and RAM disks](#disk-buffers-and-ram-disks)
- [A cache test plan](#a-cache-test-plan)
- [Compatibility roadmap](#compatibility-roadmap)
- [Not yet: non-blocking disk reads](#not-yet-non-blocking-disk-reads)
- [PiStorm](#pistorm)
- [What to send back](#what-to-send-back)

<!-- contents end -->

AmiWind is developed in emulators (FS-UAE: A1200, AGA, 68040 with FPU, 2 MiB Chip and 32 MiB Fast RAM,
JIT; 16 MiB before 21 October 2026, 128 MiB until 23 October 2026). The first figure from a real Amiga came from a tester in October 2026: an earlier build on an A4000 with a
68060 at 100 MHz ran at about 0.2 frames per second, about 0.1 above the same tester's emulator runs. The second,
on 23 October 2026, came from another tester who built the game from the public repository (the build took a large
desktop PC and a night) and ran it on an **A3000 with a 68060 at 80 MHz through RTG**, with RTG changes the tester
made to their own build (the shipped build has not been run on RTG yet): the menus were quick and the music played,
and a short timedemo with settings the tester also changed gave about 0.6 to 0.7 frames per second; a clean retest is
planned. Neither is playable yet; making the frame cheaper is the main engine work now ([AmiWind on the 68060](68060.md)). An
RTG screen does not draw the 3D for the CPU: the drawing stays on the 68k either way. Handing it to a 3D graphics card
through Warp3D is a research item ([roadmap](ROADMAP.md#research-hardware-3d-through-warp3d-v0050-study-24-october-2026)). More real
measurements, with the details listed under [what to send back](#what-to-send-back), are what turn emulator figures
into predictions for real machines. If you have one, this page lists what the game needs, what to run first, and
which settings use more memory. Measurements from real machines are very welcome: see
[how to report](#what-to-send-back).

## Contents

- [Which machines AmiWind aims at](#which-machines-amiwind-aims-at)
- [What the game needs](#what-the-game-needs)
- [Why 32 MB of Fast RAM](#why-32-mb-of-fast-ram)
- [Before you start: 68060 and Kickstart 3.1](#before-you-start-68060-and-kickstart-31)
- [First measure, then play](#first-measure-then-play)
- [More Fast RAM: the memory settings that exist today](#more-fast-ram-the-memory-settings-that-exist-today)
- [Disk buffers and RAM disks](#disk-buffers-and-ram-disks)
- [A cache test plan](#a-cache-test-plan)
- [Compatibility roadmap](#compatibility-roadmap)
- [Not yet: non-blocking disk reads](#not-yet-non-blocking-disk-reads)
- [PiStorm](#pistorm)
- [What to send back](#what-to-send-back)

## Which machines AmiWind aims at

The 68k Amiga lives on in new accelerators and machines: FPGA cores (the Vampire's Apollo 68080), a Raspberry Pi
in the CPU socket running a 68k JIT ([PiStorm](#pistorm)), and complete new machines built around an emulator,
such as the THEA1200 (an A1200 replica running Amiberry). These are where AmiWind is meant to be played, and the
development emulators already run 68k code at that kind of speed. They also run on original Amigas fitted with a
modern accelerator, and most of them offer an RTG screen as the normal display.

A classic 68060 at 80 to 100 MHz is the floor: the check that the game starts, loads the world and stays within its
memory. It is not the goal for frame rate. The first figures from real machines are all from classic 68060 boards
(below), so a first figure from any of the modern machines is the most wanted report.

## What the game needs

- An AGA Amiga (A1200, A4000 or an AGA-compatible setup).
- A 68040 or 68060 **with an FPU** (EC and LC versions of the CPU have none).
- Kickstart 3.1 or later.
- 2 MiB Chip RAM and **32 MiB of Fast RAM, the safe minimum** for now, which should be enough for the entire
  game. More Fast RAM is used automatically ([below](#extra-ram-is-used-automatically)). 16 MiB still starts:
  the start-up check shows the Fast RAM row as `[!] WARN` and the note below, counts down ten seconds (ENTER
  starts at once) and goes on by itself, and the game loads more often ([why 32 MB](#why-32-mb-of-fast-ram)).
- A disk or card for the game's drive images. Kickstart 3.1 limits: every partition under 2 GiB, and every
  partition must **start** within the first 2 GiB of its drive.
- The game itself is built from your own copy of Morrowind with the builder ([build setup](../README.md));
  no game data is distributed.

## Why 32 MB of Fast RAM

Decided for the project on 23 October 2026, from measurements of 22 and 23 October 2026 with every outdoor NPC and
creature placed (781 actors in the 336 CHIM region frames):

- **Outdoors:** the 16 MB baseline leaves the game about 2.1 MB of model cache. 14 region frames need more than
  that; the worst, `rcp2_m7`, needs 2.0 MB more. Actor models per frame are 624 KB at the median and 4.13 MB at
  most. With more RAM (measured with a 24 MiB game heap, about 15.7 MB of cache) every frame fits.
- **Interiors** share CHIM's room store: the largest Balmora room set is 4.10 MB against a 7.03 MB room zone.
- **On 16 MB** the engine evicts models and loads them again: slower, not a crash.

With less than 32 MB the start-up check shows, for example,

    Fast RAM:             16 MB (32 MB needed)       [!] WARN

and under the checklist's closing line:

    -----------------------------------------------------
    NOTE: AmiWind has grown since v0.0.48: 32 MB of Fast RAM is now
    the minimum. Only 16 MB Fast RAM found, hence the game will
    start but may load more often.
    Press ENTER to continue anyway.
    Starting in 10 s...

The countdown never blocks the start: after ten seconds, or at once with ENTER, it reads `Starting now.` and the
game starts as usual. It repeats the note (without the countdown) on the console and on the startup logo. With
32 MB or more none of this is shown: the row reads `[x] OK` and the usual five-second countdown follows. Tracked as
[RAM-REQUIREMENT-32MB-48](bugs/RAM-REQUIREMENT-32MB-48.md).

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
not start ([hardware benchmark](HARDWARE-BENCHMARK.md)). It is not on the drive image yet: every build makes it, in
the build run's `engine/awbench` ([getting the program](HARDWARE-BENCHMARK.md#getting-the-program)); copy it to the
Amiga, for example to `RAM:`.

In the game, open the console with F10 or the backquote key. `dbg fps on` shows the frame rate on screen. For a
number another machine can be compared with, record a short walk once and play it back
([timedemo](HARDWARE-BENCHMARK.md#timedemo)):

1. `record bench balmora-chim`: the map starts again and everything from here is recorded; walk and look around
   for a moment.
2. `stop` ends the recording (`bench.dem` in the game's `id1` folder).
3. `timedemo bench` plays it back as fast as the machine can draw it, prints the frames per second and the
   renderer counters, and appends a line to `saves/timedemo-results.txt`.

Send that file with the settings you had on and where you recorded. A standard demo that every image ships, run by
one command, is planned for v0.0.49 ([roadmap](ROADMAP.md#one-standard-timedemo-for-real-amigas-v0049)). `dbg rcount`
(what each frame draws) and `dbg logs live on` (writes frame stalls, cell load times and a walk profile to log
files) give the numbers that matter most ([console commands](AMIWIND_CONSOLE_COMMANDS.md)).

## More Fast RAM: the memory settings that exist today

### Extra RAM is used automatically

At every start the game measures the free Fast RAM. What is free beyond a margin left to the system (2 MiB plus
an eighth of all Fast RAM) becomes CHIM's cache: shared models, textures and streamed pieces of the world stay in
memory, pieces you walk away from stay there too, and the world is fetched further ahead in the direction you
travel (two chunks ahead from 8 MiB of cache, three from 32 MiB). There is no upper limit other than the machine:
Fast RAM spread over several boards (accelerator RAM and a Zorro III card) is taken as several banks, largest
first, each under 2 GiB, so 2 GiB and more works too.

- **16 MiB of Fast RAM (the least that starts) takes nothing:** with the 11 MiB game heap only about 1 MiB is
  free, under the margin, so the game plays exactly as without this feature. The first cache bank needs at least
  4 MiB beyond the margin (32 MiB of Fast RAM gets a bank of about 7 MiB). Until v0.0.51 it needed 8 MiB, and a
  32 MiB machine whose free memory fell by 1 MiB got no bank at all.
- **The console says what happened on every start**, for example
  `Memory: 115 MiB Fast RAM free of 128 MiB; CHIM cache 97 MiB in 2 banks (automatic); look-ahead x3`
  or `Memory: 1 MiB Fast RAM free of 16 MiB; CHIM cache off (not enough extra Fast RAM, standard memory)`.
  The `chim` console command prints the same line.
- **A notice on the startup logo** says how much extra RAM was found and what it is used for. Pressing **M**
  while it shows starts this session without it (the standard memory). It never waits for a key; starts that
  skip the logo (the test options `aw_boot_console`, `aw_test_start`, a test drive's `test.cfg`) skip the notice.
- **Off for good:** Options > Video > Extra RAM: Off (saved in `config.cfg` as `aw_autoram 0`; takes effect at the next
  start).
- **If the memory cannot be taken,** the console says so and the game plays on the standard memory.
- **A big room takes more while you are in it** (from v0.0.52): an interior holds nothing but itself, so a room
  whose models do not fit its share and the cache (Akulakhan's Chamber, with the Heart and Akulakhan) takes a bank
  of the Fast RAM still free (its largest block less 2 MiB, in 64 KiB steps; on a 32 MiB machine about 3.4 MiB
  after a town, 4 MiB when the room is the first map) and then the rest of the game heap past its share, under the
  loading screen, and gives both back at the next map. Before it measures, the game gives back what it can make
  again on demand (the shared animation tables and posed frames of the skeletal actors), one console line each
  (`Fast RAM for a room's models: ... gave back ...`). The console then says `CHIM: room ...: 3456 KiB of the free
  Fast RAM taken for its models until the next map`; `chim` prints what is free now (`Memory now: ...`) and, for a
  room that grew, `room: loaded whole on try 3; it grew 2 times, ...`: each growth follows a request the full zone
  refused, so those requests are counted as failed although every model is in place. With Extra RAM off only the
  heap's rest is taken.
- **The game heap grows with the machine** (from v0.0.43, ENGINE-HEAP-FIXED-SIZE-43): the heap is sized at start,
  before CHIM's cache, from the largest free Fast RAM block less the same margin. It stays at the built size
  (11 MiB) unless that room holds the built size plus 8 MiB, then grows by a quarter of the room beyond it, to
  24 MiB at most; 128 MiB of Fast RAM gives a 24 MiB heap and an 82 MiB CHIM cache. Quake's own cache (actors and
  sounds) then keeps what it loaded across map changes, and the maps keep their 2 MiB safety gap. 16 MiB keeps
  exactly the built 11 MiB. `-heapmb N` sets the heap by hand (used as asked); Options > Video > Extra RAM: Off keeps the
  built size.
- **The way ahead is read before you get there** (from v0.0.43, CHIM-CROSSING-SYNC-LOAD-43). Outdoors every cell is
  its own map, so walking over a cell border is a map change. With extra RAM the engine reads the files of the
  cells you are likely to enter next into spare RAM, a slice per frame while nothing else is read, and the
  crossing takes them from there instead of the disk. Which cells: your cell is split into four quarters; the
  corner nearest to you names the 2x2 block of cells that meet there, and its three neighbours are read first, the
  one you are heading for first (the largest first when the RAM is short for all three); then your own cell, then
  the rest of the 3x3 ring. The block moves to another corner only when you are 1,024 units past the cell's middle,
  so walking along an edge or standing on a corner does not read and drop the same cells over and over. What was
  read ahead is dropped first when a real load needs memory, and on its own only for cells more than half a cell
  beyond the ring. The same RAM keeps the world's index and each map's placement counts, which every crossing read
  again before. The bytes are the same, so the game looks and collides the same; 16 MiB machines read everything
  from the disk exactly as before.

### The settings

These are in the engine now ([CHIM engine](chim/ENGINE.md), [memory guide](chim/build_guide/MEMORY.md)):

| Setting | What it does | Default |
| --- | --- | --- |
| `-chimcache KIB` (start argument) | Extra Fast RAM for CHIM's cache, by hand: shared models and textures stay in memory across map changes instead of being read again. Taken once at start; if the memory is not there, the console says so and the standard budget is used. Given, it replaces the automatic size (`-chimcache 0`: no cache bank at all). | automatic |
| `aw_autoram` (Options > Video > Extra RAM, saved) | 1: free Fast RAM beyond the margin becomes CHIM's cache at the next start; 0: the standard memory always. | 1 |
| `-heapmb N` (start argument) | The game heap in MiB for this start (1 to 2047), used as asked. | automatic: 11 (the built size), up to 24 with plenty of Fast RAM |
| `chim prefetch 0` / `1` (console, not saved) | 1: read the cells ahead into spare Fast RAM and keep the world index there (only with extra RAM); 0: every read from the disk, the first method. `chim prefetch` alone prints what it did. | 1 |
| `chim prefetch mib N` / `kib N` | The most it reads ahead, in MiB (also at most a quarter of CHIM's cache); how much it reads per frame, in KiB (one 32 KiB block at least), only in frames where nothing else is read. | 24 / 32 |
| `chim spikes MS` (console) | Prints one console line for every frame of MS milliseconds or more, naming what ran in it (map start, index, ring prime, reads, sounds); `chim spikes report` sums them; `chim zone` prints the engine's small memory zone. For measurements. | 0 (off) |
| `chim_prefetch` | How far ahead of the visible ring CHIM loads chunks (-1: the world's own value). | -1 |
| `chim_lookahead` | Loads ahead in the direction you walk (-1: the world's prefetch margin, two or three times that with an automatic cache of 8 or 32 MiB and more). | -1 |
| `chim_prefetch_room` | Prefetch only into free memory, so it never pushes out what is in use. | 1 |

The chunk and model cache evicts what was used longest ago (LRU), and loading has a per-frame budget.

On a machine with a lot of Fast RAM, for example an accelerator with 128 or 256 MiB, the cache is now sized by
itself; `-chimcache` and `-heapmb 32` remain for comparisons, and the interesting part is how the numbers compare
with Options > Video > Extra RAM: Off.

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
| Baseline | Options > Video > Extra RAM: Off (or M on the startup logo) |
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
- **Memory.** A Pi gives the Amiga far more Fast RAM than the 32 MiB reference. AmiWind uses the extra Fast RAM by
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
