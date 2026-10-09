# DEBUG-TP-SHIP-FREEZE-32: The game froze once on `dbg tp balmora` issued 6 s after `dbg tp prisonship`

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | dbg tp balmora 6 s after dbg tp prisonship, remote console on |
| Reproduction | once |
| Duplicate of | no |
| Persists in | unknown |
| Severity | medium: Freeze; debug path only. |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

<!-- END GENERATED CATEGORY -->
