# STREAM-FFS-SEEK-32: Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

## Status: 8 October 2026

Open. Found by the renderer counters work (branch v0.0.32-counters, not yet merged).

8 October 2026, FFS sweep (CHIM world-format follow-up, branch v0.0.33-chim-format, 66d316b): the
36 ms per random 16 KiB read was mostly a host-storage artefact. The hard file sat in a Windows folder
shared into the container ([BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md)). The same 64 MiB image
took 18.3-21.2 ms per random request on a Docker volume against 33.2-35.3 ms from the Windows folder;
a real test world disk from the Windows folder took 122-146 ms. FFS fill (87 % full), fragmentation
(free space in 32 KiB holes), buffers (30 / 50 / 100), RDB and a 1.5 GiB partition all stayed within
about 18-22 ms, the drift of the control rerun. The seek cost itself (extension-block walk, below)
remains and is still open.

## Symptom

On an FFS world disk (30 buffers), 16 KiB reads at random offsets in an 8 MB file ran at
0.44 MB/s (36 ms per seek, 11.6 % CPU left for other tasks), against 17 MB/s sequential, in the
emulator. Relevant to large pack files for the streamer.

## Where

AmigaOS FFS file access pattern; future streamer pack layout.

## How it happened

FFS walks file extension blocks to seek; cost grows with file size.

## Why it was not caught

First seek benchmark.

## Reproduction

`awbench disk DW1:awbench.dat`.

Second measurement (8 October 2026, CHIM format work): FFS seek cost grows with distance and file
offset because FFS walks the file's extension-block chain (about one step per 36 KiB travelled;
backward seeks walk from the start of the file). Forward skips up to 64 KiB cost no more than reading
on. Random 16 KiB reads: 22.8 ms in an 8 MB file, 264 ms in a 128 MB file (cycle-approximate 68040);
with the JIT, 5.4 ms (8 MB file, 50 buffers, builder-written file, 384 MiB partition) against the
first measurement's 36 ms (30 buffers, Amiga-created file, nearly full 1.5 GB partition). Partition
fill, fragmentation and buffer count probably matter (FS-UAE gives a partition HDF without RDB 50
buffers, not 30); an A/B is pending. Layout rule: small files, read in ascending order.

## Repair

Not yet: streamer packs written in spatial order, read mostly sequentially; measure buffers and
smaller packs; real hardware number needed.

## Verification

Pending: a hardware seek measurement; emulator seek timings only with the hard file on
container-native storage, compared within one session with a drift-control rerun
([BENCH-SESSION-DRIFT-32](BENCH-SESSION-DRIFT-32.md)).

## Prevention

Disk benchmark in the streamer design gate; disk timings only with hard files on container-native
storage.
