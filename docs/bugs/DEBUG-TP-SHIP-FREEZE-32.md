# DEBUG-TP-SHIP-FREEZE-32: The game froze once on `dbg tp balmora` issued 6 s after `dbg tp prisonship`

| | |
| --- | --- |
| Reported by | A/B/C/D session (FS-UAE) |
| First noticed | 8 October 2026, v0.0.32-dev3 image |
| Where | dbg tp balmora 6 s after dbg tp prisonship, remote console on |
| Reproduction | once (not reproduced in two more attempts) |
| Duplicate of | none known |
| Persists in | unknown (not reproduced) |
| Severity | medium (freeze; debug path only) |

## Status: 8 October 2026

Open; cause unknown, seen once, not reproduced in two more attempts. Found in an FS-UAE test
session of the v0.0.32-dev3 image (remote console on) while measuring
[CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md).

## Symptom

After `dbg tp census`, then `dbg tp prisonship` (Scene ready: prison, 1,331 ms; the ship intro
restarts with "WASD: move. E: activate. Enter to follow the guard."), a remote `dbg tp balmora`
6 s later was taken from the command file (the state file counted it), and then the game stopped:
the picture stayed on the intro message, the remote state file was no longer rewritten, typed
console commands and Enter had no effect, and nothing more was written to the console log (no
"Heap ... after-unload" line of a new load). The emulator kept running at full speed.

## Where

Unknown. Candidates: the scene jump (`aw_scene.c`, `scene_command` / `load_scene`) while the ship
intro's first-person sequence is starting, or the remote console log on the emulator's host-folder
volume (each console line opens and closes a host file,
[REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md)).

## How it happened

Unknown.

## Why it was not caught

Debug teleports right after `dbg tp prisonship` were not part of any test sequence; the dev3 smoke
test waited about 20 s after it.

## Reproduction

Not reproduced: the same sequence (Census, Census, ship, 6 s, Balmora) on the dev3 image and once
with the QC-AW-FLAME-SPAWN-32 game logic loaded normally. Nine further Balmora, Census and ship
jumps per session with 6-30 s gaps did not freeze.

## Repair

Not yet; first a reproduction with the emulator debugger available to see where the guest is.

## Verification

Pending.

## Prevention

Pending the cause.
