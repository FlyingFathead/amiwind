# SEYDA-LOAD-HANG-30: rare freeze while loading in Seyda Neen

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 7 October 2026, in v0.0.30-dev4 |
| Where | Seyda Neen region load, music stream read (aw_music refill) |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.30-dev4, v0.0.30-dev5 (last seen) |
| Severity | critical: The game froze during a region load in about 5 of 70 automated runs. |
| Family | Loading and disk reads (`disk-loading`) |
| Playtest version | v0.0.30-dev4 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 7 October 2026

Open. Seen only in automated FS-UAE runs; not reported in manual play.

## Symptom

In about 5 of 70 automated runs of the Seyda Neen crossing route, the game
stopped during a region load: the picture froze and the quit command was
ignored. The emulator itself kept running.

## Where

FS-UAE 3.1.66 (A1200, AGA, 68040), v0.0.30-dev4 and dev5 engines, during
Seyda Neen sub-cell loads. WinUAE and real hardware are not yet checked.

## What the debugger shows

Captured with the FS-UAE console debugger at the moment of the freeze:

- Every CPU sample is the AmigaOS idle loop: nothing is spinning.
- The game task waits for the DOS signal inside a file read. Its reply port
  is empty, and the file-system handlers are idle.
- Call chain, verified by disassembly of the matching unstripped build: exec
  `Wait` <- dos.library `Read` <- C library `read` <- `fread` <- `refill`
  (the music stream reader in `aw_music.c`, return address directly after its
  `fread` call) <- `CDAudio_Update` <- `Host_Frame` <- `main`.

So the read that never completes is a **soundtrack stream read**, issued while
a region is loading, not the map load itself. An earlier reading of the same
capture named a different function; that came from a symbol lookup that
missed static functions and is withdrawn.

## How it happened

Unknown. The read request or its reply is lost below the engine (file-system
handler or emulator disk layer), or the music stream's file handle is in a
state the handler does not answer. 12 runs with heavy host disk load produced
no freeze, so host disk contention alone is not the trigger.

## Why it was not caught

Single runs rarely show it; it needs many repeated automated runs.

## Reproduction

The scripted route `seyda-east-y-300` under FS-UAE with the console debugger
enabled, repeated until a run freezes (about 1 in 14).

## Repair

None yet. Next steps: a breakpoint or watch on the music refill read to record
the file position and size of the read that hangs; check whether the music
file and the map are on the same partition at that moment; test whether
pausing music streaming during region loads prevents the freeze.

## Related

The WinUAE music crackles at transitions (AUDIO-LOAD-29 and related) come from
the same streaming path being starved during loads.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Loading and disk reads (`disk-loading`). Load time follows bytes read and seeks on FFS; measured with read counters, not wall time alone. See [families](README.md#families).

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [CHIM-READ-RUNS-33](CHIM-READ-RUNS-33.md): CHIM crossings read little but in many separate runs, so FFS seeks dominate
- [LOADER-STALL-32](LOADER-STALL-32.md): One unexplained stall while loading the Mages Guild with the new loader
- PERF-READAHEAD-29 (no report page): Outdoor cell/sub-cell crossing pauses and lost read-ahead
- [SEYDA-READ-SLOW-31](SEYDA-READ-SLOW-31.md): dev1 Seyda crossings read slower than the ov700 test image
- [STREAM-FFS-SEEK-32](STREAM-FFS-SEEK-32.md): Random 16 KiB reads on FFS run at 0.44 MB/s and take most of the CPU

Related bugs in other categories:

- AUDIO-LOAD-29 (no report page): OST crackles under heavy loading

<!-- END GENERATED CATEGORY -->
