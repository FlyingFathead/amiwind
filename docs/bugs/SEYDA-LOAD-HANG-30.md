# SEYDA-LOAD-HANG-30: rare freeze while loading in Seyda Neen

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
