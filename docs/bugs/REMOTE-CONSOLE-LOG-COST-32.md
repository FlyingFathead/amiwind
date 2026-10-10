# REMOTE-CONSOLE-LOG-COST-32: With the remote console on, every console line costs about 7-18 ms in FS-UAE

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | remote debugging console (aw_remote 1), engine/aga/src/console.c and aw_remote.c |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev3, v0.0.32 (last seen) |
| Severity | low: Test tooling. |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

Related bugs in other categories:

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s

<!-- END GENERATED CATEGORY -->
