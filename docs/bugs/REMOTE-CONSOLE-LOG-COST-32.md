# REMOTE-CONSOLE-LOG-COST-32: With the remote console on, every console line costs about 7-18 ms in FS-UAE

| | |
| --- | --- |
| Reported by | A/B/C/D session (FS-UAE) |
| First noticed | 8 October 2026, v0.0.32-dev3 image |
| Where | remote debugging console (aw_remote 1), engine/aga/src/console.c and aw_remote.c |
| Reproduction | always with the remote console on |
| Duplicate of | none (cause of CENSUS-LOAD-SLOW-32) |
| Persists in | v0.0.32 (test sessions only) |
| Severity | low (test tooling) |

## Status: 8 October 2026

Open; cause known, not repaired. Tagged performance. Test sessions only: the remote console
(`aw_remote 1`) is off by default and not saved. Found while measuring
[CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md).

## Symptom

In FS-UAE with the remote console on, anything that prints many console lines slows the game
down: the dev3 Census office load with about 1,170 console calls took 5.5-21.7 s against
0.13-0.16 s with the remote console off. Load times read in test sessions include this cost.

## Where

`engine/aga/src/console.c` (`Con_Printf`, `Con_DebugLog`) and `engine/aga/src/aw_remote.c`
(`AW_RemoteConsoleLog`): with `aw_remote 1`, every `Con_Printf` call goes to `Con_DebugLog`, which
opens `AWCTL:console.log` (a host folder the emulator mounts), seeks to the end, writes and closes
it.

## How it happened

The remote console reuses Quake's `-condebug` method, which opens and closes the log for every
console call. On a real hard disk that is a few file-system calls; on the emulator's host-folder
volume each open and close crosses into the host. The cost per call varied between 7 and 18 ms in
one session on a busy host (same 1,170 calls: 8.8 to 21.7 s), so it depends on host load and
perhaps on the log size.

## Why it was not caught

The remote console is used for tests only, where it was assumed to be cheap; the load-time
measurements did not compare it with a run without it.

## Reproduction

FS-UAE, the v0.0.32-dev3 image (before the QC-AW-FLAME-SPAWN-32 repair): `aw_remote 1`,
`dbg tp census`, read "Scene ready"; then `aw_remote 0;dbg tp census` and read the line in the
console. Any command with long output (for example `edicts`) shows the same cost.

## Repair

Not yet. Options: keep the log file open while the remote console is on and close it on
`aw_remote 0`, map change or quit; or buffer console output and append it once per remote poll
(twice a second). Quake's `-condebug` path stays as it is.

## Verification

Pending: the same load with the remote console on and off within a few percent of each other.

## Prevention

Proposed: load-time and frame-time measurements record whether the remote console was on; a
benchmark of a long console command with the remote console on and off.
