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

_Last updated with AmiWind v0.0.42-dev2 (17 October 2026)._

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

## Related freezes

10 October 2026: suspected to be the same mechanism as [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md) (full analysis and repair: a music stream read that never returns while the main loop waits for it) and [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): there the freeze needed an emulator pause followed by heavy remote console traffic, and this freeze happened with the remote console on. Not captured in a debugger, so not confirmed.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- [DBG-ENTITY-INSPECT-39](DBG-ENTITY-INSPECT-39.md): Requested click-to-pin raw entity and reference inspection
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- DEBUG-GOD-LOCKED-DOORS-51 (no report page): Requested: in god mode a locked door opens, with a framed notice God mode used to enter a locked door
- DEBUG-POSE-AFTER-RELOAD-52 (no report page): After a map reload a scripted check cannot return to the same view: aw_view does not take and dbg tp seyda lands on a different spot each time
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-MINIWIND-36](DEBUG-TP-MINIWIND-36.md): dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- [INSPECT-CHIM-PLACEMENT-UNNAMED-42](INSPECT-CHIM-PLACEMENT-UNNAMED-42.md): Inspect pin on a placed mesh in a CHIM frame reports only worldspawn, no mesh or reference
- [INSPECT-NO-RIGHT-CLICK-EXIT-42](INSPECT-NO-RIGHT-CLICK-EXIT-42.md): Inspect mode cannot be left with the mouse: only the console command dbg hud off
- [INSPECT-OVER-VIEWPORT-42](INSPECT-OVER-VIEWPORT-42.md): Inspect mode (dbg hud) draws its hint and pinned panel on black boxes over the 3D view
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [MINIWIND-CITY-COORD-TP-36](MINIWIND-CITY-COORD-TP-36.md): dbg tp X Y Z does not work inside the whole-city Vivec MiniWind: Coordinate teleport unavailable (no map on this disk holds that point)
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

Related bugs in other categories:

- [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md): The game freezes with the music looping after the player is left idle for a few minutes outdoors, seen around sundown
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load

<!-- END GENERATED CATEGORY -->
