# BENCH-HOST-STORAGE-32: Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS

## Status: 8 October 2026

Open (benchmark method). Found by the CHIM world-format follow-up (FFS sweep, branch
v0.0.33-chim-format, commit 66d316b; table in `docs/HARDWARE-BENCHMARK.md` on that branch).

## Symptom

The same 64 MiB hard file, same FS-UAE profile (cycle-approximate 68040), `awbench seek`, random
16 KiB requests in an 8 MB file: 18.3-21.2 ms per request with the hard file on the PC's Linux side
(a Docker volume), 33.2-35.3 ms with the same file in a Windows folder shared into the container. A
real world disk of a test build read from a Windows folder took 122-146 ms per random request.
Straight 16 KiB requests: 0.41-0.88 ms against 2.9-3.7 ms (JIT profile: 0.07 ms against 1.09 ms).

## Where

Every FS-UAE disk or crossing timing taken with the hard files in a Windows folder shared into the
container. Known to include:

- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): the first measurement (36 ms per random 16 KiB read),
  from the renderer counters work;
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): the crossing benches (`read_s` per map);
- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): the 36 ms per seek it quotes as its starting point.

Relative results inside one batch on the same storage keep their direction, but absolute
milliseconds and the share of time spent reading are likely inflated by host I/O.

## How it happened

The emulated machine waits for every block the PC reads. A Windows folder shared into a Linux
container is far slower per request than container-native storage (the same effect as
[BUILD-WINDOWS-DOCKER-SLOW-31](BUILD-WINDOWS-DOCKER-SLOW-31.md) for builds), and FS-UAE passes that
latency on to the emulated FFS.

## Why it was not caught

No benchmark had compared the same hard file on two kinds of host storage; the hard file's place on
the PC was not part of the benchmark record.

## Reproduction

Copy one hard file to a Docker volume and to a shared Windows folder; run `awbench seek` on both in
the same FS-UAE profile and compare the random-position column.

## Repair

Not yet: rule for every emulator disk timing: the hard files sit on container-native storage (a
Docker volume or the container's own file system), never in a shared Windows folder. Earlier
timings are relative only; the ones that matter are to be repeated on container-native storage.

## Verification

Pending: repeat the Seyda crossing bench and the seek bench with the hard files on a Docker volume.

## Prevention

Every disk benchmark report records where the hard files sit on the PC; benchmark scripts refuse a
hard file in a shared Windows folder for disk timings.
