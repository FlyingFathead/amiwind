# SEYDA-READ-SLOW-31: dev1 Seyda crossings read slower than the ov700 test image

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 7 October 2026, in v0.0.31-dev1 |
| Where | map loader file reads (Seyda Neen sub-cell crossings) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.31-dev2 |
| Severity | medium: Crossings 0.10-0.21 s slower than the test image; a measured load slowdown. |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | v0.0.31-dev1 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open; tagged performance. Narrowed to the engine build that added ember
particles; not caused by what the embers do. Found before v0.0.31-dev1 was
shared. dev1 is still faster than v0.0.30 on every measured crossing.

Note (8 October 2026): the crossing timings below were taken with the hard files in a Windows folder
shared into the container. Such timings include host I/O and are likely inflated
([BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md)); compare them only within their batch. New disk
timings are taken with the hard files on container-native storage.

## Symptom

On the FS-UAE crossing route `seyda-east-y-300` (3 runs each), the dev1 disks
take 0.10-0.21 s longer per Seyda Neen sub-cell crossing than the earlier test
image with the same maps (ov700 layout on the v0.0.30 disks):

| Map | v0.0.30 | ov700 test | dev1 |
| --- | --- | --- | --- |
| sn017 | 0.59 s | 0.46 s | 0.56 s |
| sn019 | 0.89 s | 0.57 s | 0.73 s |
| sn014 | 0.81 s | 0.45 s | 0.66 s |

The whole difference is time spent inside the map loader's `fread` calls: the
same bytes in the same number of calls, with the rest of the load unchanged
(0.14-0.17 s).

## Where

The engine, at the step that added ember particles (`r_part.c` particle type
and spawner, `d_iface.h`, `quakedef.h`, `aw_guard_torch.c`). The exact
mechanism is still being measured.

## How it happened

Measured so far (all on the same ov700 test disk unless noted; runs compared
only within one batch, because parallel emulators slow every run by up to
25 %):

1. Host load is not the cause: a dev1 rerun with nothing else running was as
   slow.
2. The disk layout is not the cause: every Seyda map is one contiguous block
   run on both disks, and the dev1 disk with the v0.0.30 engine is fast.
3. The engine is the cause: the ov700 test disk with only the dev1 engine is
   slow (sn019 read 0.42 s -> 0.61 s).
4. Every engine build between v0.0.30 and dev1, one batch: equal up to the
   build before the embers, slow from the ember build on (sn019 read 0.52 s ->
   0.62 s, all six maps).
5. Behaviour against layout, one batch (sn019 read): v0.0.30 engine 0.47 s;
   dev1 engine 0.61 s; dev1 rebuilt 0.61 s (identical binary apart from the
   build-time string); dev1 with ember spawning switched off 0.60 s; v0.0.30
   plus 24 bytes of unused data 0.47 s; v0.0.30 plus a small unused function
   0.47 s.

So the slowdown follows the ember build even when no ember code runs, and
small layout changes to v0.0.30 do not reproduce it. Leading hypothesis: the
build changes the alignment of a buffer the C library reads through (its
stdio buffer is 1 KiB), and the 68040 copies unaligned memory more slowly.
Diagnostic builds that log those addresses are being measured.

## Why it was not caught

The ov700 layout was measured on the v0.0.30 engine; the dev1 engine and disk
were first measured together in the dev1 boot check. The crossing benchmark
was not part of the engine gates.

## Reproduction

`bench.py <disk> <label> seyda-east-y-300 N` with the engine overlaid per run
(`BENCH_ENGINE`), comparing per-map `read_s` within one batch.

6. Fix candidates, one batch, each on both engines (sn019 read / whole
   crossing): C library default 1 KiB buffer 0.51 / 0.71 s (v0.0.30 engine)
   and 0.63 / 0.82 s (dev1 engine); unbuffered 0.37 / 0.58 s and 0.36 /
   0.57 s (the engines become equal, so the slowdown lives in the library's
   buffered path); 16 KiB buffer 0.23 / 0.44 s and 0.26 / 0.47 s; 64 KiB
   buffer 0.17 / 0.40 s and 0.21 / 0.47 s. Diagnostic builds showed the
   library buffer has the same alignment in both engines, so alignment is
   not the mechanism.

## Repair

In source (not shipped at the time of writing): loose game files opened by `COM_FOpenFile` get a
16 KiB stdio buffer (`setvbuf`) instead of the C library's 1 KiB default. Map
loading needs far fewer AmigaDOS calls; on the dev1 engine whole Seyda
crossings drop from 0.70-0.91 s to 0.39-0.48 s (v0.0.30 was 0.54-0.71 s).
64 KiB was not taken: no net gain on the whole crossing, and longer single
reads delay music streaming on real hardware. A 10-15 % gap between the
engines remains with buffering; its cause is still unknown and stays open
here (next experiment: large direct reads into the game's own memory).

## Verification

Same-batch FS-UAE measurements above (2 valid runs per variant, all six
Seyda maps). `tests/test_file_read_buffer.py` guards the buffer setup. The
packaged build and an owner playtest are pending.

## Prevention

The crossing benchmark against the previous engine for every engine change
that ships, compared within one batch. Lessons:
[performance lessons learned](../performance/LESSONS_LEARNED.md).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate
- [LOADER-STALL-32](LOADER-STALL-32.md): One unexplained stall while loading the Mages Guild with the new loader
- PERF-READAHEAD-29 (no report page): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

Related bugs in other categories:

- [AW-20260928-01](AW-20260928-01.md): Prison ship to deck transition is intermittently very slow or freezes (FS-UAE)
- [BENCH-HOST-STORAGE-32](BENCH-HOST-STORAGE-32.md): Emulator disk timings with the hard file in a Windows folder measure the PC, not FFS

<!-- END GENERATED CATEGORY -->
