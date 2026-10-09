# Hardware benchmark for owners of accelerated Amigas

Every frame rate and loading time measured so far comes from an emulator, mostly
with its JIT compiler at unlimited speed on a fast PC disk. Those figures are only
good for comparing builds with each other, not for predicting what a real 68040 or
68060 with an IDE or CompactFlash drive does
([BENCH-JIT-PROFILE-32](bugs/BENCH-JIT-PROFILE-32.md)). One set of numbers from real
hardware calibrates all of them. `awbench` is a small program that measures what
matters for AmiWind: disk reads in the request sizes the game uses, how much CPU
time the disk transfer leaves for everything else, and plain CPU, FPU and memory
speed. It reads no game data and needs nothing from Morrowind.

<!-- contents start -->
## Contents

- [What it does](#what-it-does)
- [Getting the program](#getting-the-program)
- [Running it](#running-it)
- [Reading the results](#reading-the-results)
- [Frame time in the game](#frame-time-in-the-game)
- [Emulator numbers are not hardware numbers](#emulator-numbers-are-not-hardware-numbers)

<!-- contents end -->

The developers have not run it on real hardware; your results are the first.

## What it does

| Command | What it measures |
| --- | --- |
| `awbench cpu` | integer multiply and add loops, an FPU multiply/add loop (only when an FPU is present), Fast RAM copy, Chip RAM writes (the display path) |
| `awbench disk FILE` | creates `FILE` (8 MB of generated data) if it does not exist, then reads the whole file four times: in 16 KiB and in 64 KiB requests, sequentially and at pseudo-random positions |
| `awbench all FILE` | both |
| `awbench seek FILE [N]` | how reads that skip around a large file cost on this drive: 16 KiB requests straight through, skipping 4 KiB to 1 MiB forward between requests, reading through 4-64 KiB gaps instead, and at random positions (N requests per pattern, default 256); for the world streamer's pack layout |
| `awbench replay LIST` | reads the file ranges a list names, crossing by crossing, and times each crossing: the developers use it to replay the world streamer's reads of a walk through a town |
| `awbench buffers DRIVE N` | sets the drive's buffers to N (AmigaDOS `AddBuffers`), to repeat `disk` or `seek` with other buffer counts in one session |

Every run starts with a setup block (processor and FPU, memory, Kickstart and
Workbench versions, the resident FPU support library, and for `disk`/`all` the drive's
file system, device driver, unit, buffers and MaxTransfer), so results from different
machines can be compared; you add the card name, clock and drive model by hand.

For every read pass it prints the transfer rate and `cpu_free_pct`: the share of CPU
time other programs still got while the file was read. A counting task at the lowest
priority runs whenever nothing else needs the CPU; its counting rate during the read,
compared with its rate while `awbench` sleeps, gives that share. An IDE port in PIO mode
copies every byte with the CPU, so this is often low, and it decides whether the game
can load the next area in the background while you walk.

`awbench` writes only the one file you name and deletes nothing. Delete the file
yourself afterwards.

## Getting the program

The repository's builder builds `awbench` with every engine build: after
`./build.sh engine` (or `tools/build_aga.py engine --sdk ... --out OUT`) it is
`OUT/awbench`, and its checksum is in `OUT/engine-build.json`
(`hardware_benchmark_sha256`). With the Amiga cross compiler installed you can also
run `make bench` in `engine/aga` (the program is `engine/aga/build/awbench`). It needs
a 68020 or better and Kickstart 2.0 or later; the source is
`engine/aga/bench/awbench.c`.

## Running it

1. Copy `awbench` to the Amiga, for example to `RAM:` or to the drive AmiWind is on.
2. Boot without extra programs running (no Workbench activity, no network stack if
   you can avoid it). Load your usual `SetPatch` and CPU support library
   (68040.library or 68060.library) as you normally do.
3. Open a Shell and run, using the drive that holds AmiWind's world data (often the
   IDE or CompactFlash drive):

   ```
   awbench >RAM:awbench.txt all DH1:awbench.dat
   awbench >RAM:awbench-2.txt disk DH1:awbench.dat
   Delete DH1:awbench.dat
   ```

   The second run reads the file again without creating it, which shows whether the
   drive or its file system caches anything. AmigaDOS needs the `>` redirection right
   after the program name. The CPU loops take a few seconds on a 68040; the disk passes
   read 32 MB in all.
4. Open `RAM:awbench.txt` in a text editor. Its first block, from
   `AWBENCH-REPORT begin` to `AWBENCH-REPORT end`, describes your setup; replace the
   four `tester ... <fill in ...>` lines with what the program cannot find out itself:
   the accelerator card's name, the CPU clock, the drive (internal IDE hard disk,
   CompactFlash card and adapter, or something else, with the model) and, if you know
   them, the file system and the buffers you set. Then send both files.

If the drive name is wrong, `awbench` says so and stops instead of asking you to
insert a volume (it never opens a requester).

## Reading the results

The setup block (one example, from the emulator):

```
AWBENCH-REPORT begin (copy from here to AWBENCH-REPORT end)
system cpu=68040 fpu=040 attn=804f
system chip_kb=2043 fast_kb=16383 chip_free_kb=2022 fast_free_kb=16132
system exec=40.10 kickstart_softver=68 dos=40.3 workbench=none
system fpu_support=none resident
system eclock_hz=709379
disk drive=DW1: volume=AW_WORLD1 disktype=DOS\1 block_bytes=512 blocks=3145726 used=2643136
disk dosdevice=DW1: exec_device=uaehf.device unit=1 buffers=30 maxtransfer=0xffffff mask=0x7ffffffe dostype=DOS\1 bufmemtype=0x0
tester card=<fill in: accelerator name, e.g. Blizzard 1240, Apollo 1260, PiStorm>
tester clock_mhz=<fill in: CPU clock>
tester medium=<fill in: internal IDE hard disk / CF card and adapter / other; card or disk model>
tester filesystem=<fill in if known: FFS, PFS3, SFS and version; AddBuffers you use>
AWBENCH-REPORT end
```

- `system cpu/fpu/attn`: the processor and FPU as the system reports them (exec
  `AttnFlags`; a 68060 is only reported as such once 68060.library has run, and then
  `pcr`, `id`, `rev` and `fpu_disabled` come from its processor configuration register;
  a Vampire's 68080 is shown as 68080).
- `chip_kb`/`fast_kb`: all Chip and other (Fast) memory in the memory list; `_free_kb`:
  free at the start.
- `exec`/`kickstart_softver`/`dos`/`workbench`: Kickstart (exec 40 is 3.1, 45 is 3.9,
  46 is 3.1.4, 47 is 3.2) and the Workbench version (`version.library`, `none` if not
  loaded).
- `fpu_support`: which of 68040.library, 68060.library or 68080.library is resident.
- `disk drive=...`: the volume holding FILE, its file system type (`DOS\1` is FFS,
  `DOS\3` FFS international, `PFS\3` PFS3, `SFS\0` SFS) and size in blocks;
  `disk dosdevice=...`: the device driver and unit (for example `scsi.device`, the
  A1200's internal IDE), the buffers, MaxTransfer and Mask of the partition.

Each result is one line starting with `AWBENCH`, with `key=value` fields:

- `cpu test=intmul|intadd|fpu`: loop count, microseconds and millions of loops per
  second.
- `mem test=fastcopy|chipwrite`: MB/s (1 MB = 1,048,576 bytes).
- `disk test=create`: write rate while creating the file (includes generating the data).
- `disk test=read request=16384|65536 pattern=seq|seek`: MB/s and `cpu_free_pct`.
- `idle counts_per_s`: the counting task's rate while idle (the 100 % reference).
- `seek pattern=skip|through|random gap=... file_bytes=...`: microseconds per 16 KiB
  request (`us_per_request`), useful MB/s, the time to open the file and `cpu_free_pct`.
  `skip` seeks forward by `gap` between requests, `through` reads the gap instead,
  `random` seeks to random positions.

### Why the seek mode exists

The Amiga's Fast File System keeps a file's list of blocks in a chain of extension
blocks, one per 36 KiB of a file with 512-byte blocks. A seek forward follows the
chain from the current position; a seek backward starts again at the file's first
block. So a seek costs about one chain step per 36 KiB travelled, and a seek to a
random place in a large file is slow, while a short forward skip costs no more than
reading on ([STREAM-FFS-SEEK-32](bugs/STREAM-FFS-SEEK-32.md)). The world streamer's
packs are laid out and read with that in mind; `awbench seek` on a real drive tells it
what the steps cost there. Use a large file to see the effect, for example one made
by copying a big file onto the drive, or let `awbench` create its 8 MB file.

Measured in FS-UAE (cycle-approximate 68040, an FFS partition made by the builder,
8 October 2026; relative numbers, not hardware):

| File | plain 16 KiB request | skip 4-64 KiB | skip 256 KiB | skip 1 MiB | random position |
| --- | ---: | ---: | ---: | ---: | ---: |
| 8 MB | 0.72 ms | 0.59-0.90 ms | 3.0 ms | 11.3 ms | 22.8 ms |
| 128 MB | 1.40 ms | 1.17-1.25 ms | 6.8 ms | 8.0 ms | 264 ms |

`tools/chim/readcost.py` turns such reports into a read cost model for the world
streamer's validator (`--read-cost`). Those patterns use 16 KiB requests, so they
overstate long reads; the validator's default model is fitted to `awbench replay`
runs of the streamer's actual reads instead (`readcost.py REPLAY --replay-estimates`).

- `replay crossing=... runs=... files=... bytes=... us=...`: one crossing of a replay
  list (lines `X n` start crossing n, lines `R path offset bytes` are read runs; each
  file is opened at its first run, a run further on seeks forward from the current
  position, any other from the start); `replay total us=...`.
- `buffers drive=... before=... want=... result=... after=...`: the buffer count
  before and after `awbench buffers`.

## Frame time in the game

The game itself reports what its renderer does once a second with the console
command `dbg rcount 1` (`dbg rcount 0` turns it off): frames and frames per second
(`fps10` is tenths), brush model, face, fragment, edge and span counts, surface cache
work, and the time split in microseconds; the last field before `pk` is the average
frame time and `pk` the slowest frame. The developers' emulator measurements use ten
fixed cameras (the `dbg tp` coordinates are original Morrowind positions; the game
places you on the ground there):

| Camera | Console commands |
| --- | --- |
| Balmora 1 | `dbg tp -20088 -14638`, then `aw_aim 113 -3` |
| Balmora 2 | `dbg tp -20970 -16963`, then `aw_aim 45 0` |
| Balmora 3 | `dbg tp -21800 -12300`, then `aw_aim 90 0` |
| Balmora 4 | `dbg tp -19000 -11000`, then `aw_aim 225 0` |
| Balmora 5 | `dbg tp -20500 -9500`, then `aw_aim 270 0` |
| Seyda Neen 1 | `dbg tp -11264 -71680`, then `aw_aim 90 0` |
| Seyda Neen 2 | `dbg tp -11548 -71200`, then `aw_aim 180 0` |
| Seyda Neen 3 | `dbg tp -10474 -73437`, then `aw_aim 45 0` |
| Seyda Neen 4 | `dbg tp -10920 -75120`, then `aw_aim 0 0` |
| Seyda Neen 5 | `dbg tp -12200 -72500`, then `aw_aim 60 0` |

Before measuring: `dbg daynightcycle off`, `dbg set time 1200`, `dbg headlamp off`.
Wait until the scene has loaded and the view has settled, close the console, wait ten
seconds and note two or three `rcount` lines (they also scroll by at the top of the
screen). `timerefresh` in the console renders 128 frames while turning on the spot and
prints the time; it is a rougher number because the view changes.

On a 68040 without its support library the game can stop with an FPU exception
([ENGINE-FPSP-MISSING-31](bugs/ENGINE-FPSP-MISSING-31.md)); load 68040.library (via
`SetPatch` or your accelerator's tools) before starting AmiWind and mention it in your
report.

## Emulator numbers are not hardware numbers

`awbench` also runs in FS-UAE, which is how it was tested. Emulated disk figures mean
nothing for real drives (the emulator's hard disk is a virtual device backed by the PC's
file cache), and CPU figures depend on the emulator profile: see "Benchmark profile" in
[FS-UAE-PLAYTESTING.md](FS-UAE-PLAYTESTING.md#benchmark-profile).

Even between emulator runs, disk figures depend on where the PC keeps the hard file:
the emulated machine waits for every block the PC reads. One sweep (8 October 2026,
cycle-approximate 68040, `awbench seek` with 32 requests per pattern, 8 MB file;
milliseconds per 16 KiB request):

| Hard file | straight | skip 64 KiB | skip 1 MiB | random |
| --- | ---: | ---: | ---: | ---: |
| A: 384 MiB partition, empty, file written by the builder, 50 buffers | 0.45 | 0.89 | 5.3 | 19.7 |
| B: as A, 87 % full | 0.48 | 1.38 | 9.6 | 18.9 |
| C0: as A, file written by the Amiga | 0.49 | 0.95 | 5.2 | 18.0 |
| C: 85 % full, free space in scattered 32 KiB holes, file written by the Amiga | 0.63 | 1.42 | 6.0 | 18.5 |
| R: A inside an RDB disk (30 buffers, MaxTransfer 0xffffff) | 0.47 | 1.36 | 6.0 | 19.6 |
| D: 1.5 GiB RDB partition, empty | 0.43 | 0.94 | 5.1 | 18.4 |
| A with 30 / 100 buffers | 0.44 / 0.41 | 0.92 / 1.27 | 5.0 / 9.2 | 19.6 / 18.1 |
| A again (drift control) | 0.45 | 0.91 | 8.6 | 21.8 |
| F: 64 MiB partition on the PC's Linux side (a Docker volume) | 0.41-0.88 | 0.90-0.92 | 6.3-8.1 | 18.3-21.2 |
| F: the same file in a Windows folder shared into the container | 2.9-3.7 | 4.6-5.2 | 14.8-15.5 | 33.2-35.3 |
| A real world disk of a test build (1.5 GiB, 85 % full, file written by the Amiga), Windows folder | 3.1-3.9 | 6.3-8.2 | 29-48 | 122-146 |

Fill, fragmentation, buffer count, RDB and partition size stay within the drift of
the control run; the hard file's place on the PC changes everything (with the JIT
profile, a straight 16 KiB request took 0.07 ms from the Docker volume and 1.09 ms
from the Windows folder). Emulator disk timings are only comparable when every hard
file sits on the same kind of storage, and a seek benchmark of a Windows-side hard
file mostly measures the PC.
