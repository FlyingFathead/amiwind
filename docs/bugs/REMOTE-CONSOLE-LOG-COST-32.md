# REMOTE-CONSOLE-LOG-COST-32: With the remote console on, every console line costs about 7-18 ms in FS-UAE

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 8 October 2026, in v0.0.32-dev3 |
| Where | remote debugging console (aw_remote 1), engine/aga/src/console.c and aw_remote.c |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.62-dev1 |
| Severity | low: Test tooling. |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.32-dev3 |
| From commit | source and engine 91a7eeb |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.62-dev1 (7 November 2026)._

## Status: 8 October 2026

Open; cause known, not repaired. Tagged performance. Test sessions only: the remote console
(`aw_remote 1`) is off by default and not saved. Found while measuring
[CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md).

7 November 2026: repaired in v0.0.62-dev1 (see Repair).

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
one session on a loaded machine (same 1,170 calls: 8.8 to 21.7 s), so it depends on host load and
perhaps on the log size.

## Why it was not caught

The remote console is used for tests only, where it was assumed to be cheap; the load-time
measurements did not compare it with a run without it.

## Reproduction

FS-UAE, the v0.0.32-dev3 image (before the QC-AW-FLAME-SPAWN-32 repair): `aw_remote 1`,
`dbg tp census`, read "Scene ready"; then `aw_remote 0;dbg tp census` and read the line in the
console. Any command with long output (for example `edicts`) shows the same cost.

## Repair

7 November 2026 (v0.0.62-dev1): the second option. With the remote console on, `Con_Printf` hands
its text to `AW_RemoteLog` (`aw_remote.c`), which collects it in an 8 KiB buffer; the buffer is
appended to `console.log` in one open, seek, write and close at the remote poll (twice a second),
on the long-work heartbeat, when it is full, and at exit (a fatal exit writes it right after its
heap note, so the session tool still finds that note). A print larger than the buffer is appended
on its own. Quake's `-condebug` path stays as it is.

The cost mattered beyond load times: an `edict` listing is about 300 prints (each field name is
padded one space at a time), a frame of 3 to 7 seconds of folder traffic, and test sessions stopped
right after such frames (SESSION-STALL-AFTER-LONG-FRAME-62).

## Verification

Unit check (`tests/aga_remote_test.c`): 302 prints make no file call until the poll, which writes
them in order in one append; the heartbeat, a full buffer, a print larger than the buffer and the
exit flush each append in order. In game: the session check of SESSION-STALL-AFTER-LONG-FRAME-62.

## Prevention

Proposed: load-time and frame-time measurements record whether the remote console was on; a
benchmark of a long console command with the remote console on and off.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- CONSOLE-TP-ROOM-NAME-63 (no report page): The console teleport to a room map name stays in the current town instead of entering the room
- DBG-CONTAINER-AIM-NO-SPOT-59 (no report page): aw_placed container aim finds no standing spot the room collision accepts in Arrille's Tradehouse
- DBG-DOOR-GO-AIM-CHIM-59 (no report page): aw_hinged_door go does not bring the door under the crosshair in a CHIM room
- [DBG-ENTITY-INSPECT-39](DBG-ENTITY-INSPECT-39.md): Requested click-to-pin raw entity and reference inspection
- DBG-PLACED-LOOK-VIEW-NOT-TURNED-61 (no report page): The test commands aw_placed look and aw_view set the view angles but the view does not turn
- DBG-QUOTED-ID-REFUSED-62 (no report page): A debug command with a quoted record ID holding a space is refused as an unknown debug command (dbg npcs talk "agronian guy")
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DBG-TP-SAME-MAP-54 (no report page): dbg tp X Y finds no map for a point on a MiniWind CHIM frame
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- DEBUG-GOD-LOCKED-DOORS-51 (no report page): Requested: in god mode a locked door opens, with a framed notice God mode used to enter a locked door
- DEBUG-POSE-AFTER-RELOAD-52 (no report page): After a map reload a scripted check cannot return to the same view: aw_view does not take and dbg tp seyda lands on a different spot each time
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-MINIWIND-36](DEBUG-TP-MINIWIND-36.md): dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- DEBUG-VIEW-PITCH-DRIFT-54 (no report page): aw_view alone lets the pitch drift, and the greeting camera takes the view during scripted sessions
- DEV2-REGION-LOAD-CRASH-57 (no report page): v0.0.57-dev1 dev2 image crashes with NUM_FOR_EDICT: bad pointer when a teleport loads another region (dev1 did not)
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- GAME-RECORDER-FIGHT-SEED-61 (no report page): A recording made while an NPC fights the player does not replay the same: the fight takes a seed of its own on the replay's load
- GAME-RECORDER-HOTKEY-DIALOGUE-61 (no report page): While a recording runs, Ctrl+R does not stop it when the dialogue window is open: the key goes into the dialogue search field
- [GAME-RECORDER-MISSING-61](GAME-RECORDER-MISSING-61.md): Requested: a gameplay recorder that records a play session and plays it back in another game instance
- HORS-FROM-MENU-58 (no report page): dbg aw hors cannot be started from the main menu
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- [INSPECT-CHIM-PLACEMENT-UNNAMED-42](INSPECT-CHIM-PLACEMENT-UNNAMED-42.md): Inspect pin on a placed mesh in a CHIM frame reports only worldspawn, no mesh or reference
- [INSPECT-NO-RIGHT-CLICK-EXIT-42](INSPECT-NO-RIGHT-CLICK-EXIT-42.md): Inspect mode cannot be left with the mouse: only the console command dbg hud off
- [INSPECT-OVER-VIEWPORT-42](INSPECT-OVER-VIEWPORT-42.md): Inspect mode (dbg hud) draws its hint and pinned panel on black boxes over the 3D view
- [INSPECT-PIN-LOAD-DOOR-51](INSPECT-PIN-LOAD-DOOR-51.md): The inspect pin at an exterior load door names the building shell around it, not the door: the drawn door looks absent
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [MINIWIND-CITY-COORD-TP-36](MINIWIND-CITY-COORD-TP-36.md): dbg tp X Y Z does not work inside the whole-city Vivec MiniWind: Coordinate teleport unavailable (no map on this disk holds that point)
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- SWEEP-GNISIS-LOAD-STALL-57 (no report page): Settlement sweep: the teleport to Gnisis shows no game-clock progress for 20 s (hang or a load over 20 s)
- [SWEEP-SLOW-ARRIVALS-57](SWEEP-SLOW-ARRIVALS-57.md): Settlement sweep: 13 of 82 places run above 50 ms a frame just after arrival at 32 MB Fast
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater
- TP-ARRIVAL-ABOVE-DOOR-57 (no report page): Settlement sweep: Bal Isra lands about 250 units above its door arrival (on top of the ruin?)
- TP-ARRIVAL-BELOW-DOOR-57 (no report page): Settlement sweep: Vivec, Temple and Uvirith s Grave land 160 to 290 units below their door arrivals
- TP-PICKER-OPEN-FRAME-COST-57 (no report page): The dbg tp list box redraws the whole paused world every frame: 100 ms a frame open against 16 ms closed
- TP-PLACES-NO-DOOR-SEA-57 (no report page): Settlement list: Fields of Kummu arrives in the water (a place without a door used its cell middle)

Related bugs in other categories:

- [CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md): The Census and Excise Office takes 8-10 s to load in FS-UAE; other scenes 0.2-1.5 s
- [SESSION-STALL-AFTER-LONG-FRAME-62](SESSION-STALL-AFTER-LONG-FRAME-62.md): The game stops with its clock frozen right after a frame of several seconds spent on console output or file reads, in three of ten scripted Seyda Neen sessions

<!-- END GENERATED CATEGORY -->
