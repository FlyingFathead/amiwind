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

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-08: reported in v0.0.32-dev3
- 2026-10-08: CENSUS-LOAD-SLOW-32 cause; REMOTE-CONSOLE-LOG-COST-32 and DEBUG-TP-SHIP-FREEZE-32: CENSUS-LOAD-SLOW-32: cause confirmed in one FS-UAE container (loaded machine, relative numbers): dev3 Census 8.8-20.9 s with the remote console on ...
- 2026-11-17: v0.0.67-dev1: Cause attributed on 17 November 2026 (v0.0.67-dev1 line, the load fallbacks job): the same mechanism as CHIM-SEYDA-BALMORA-LOAD-HANG-43, captured on 16 November 2026.

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.67-dev1 (17 November 2026)._

<!-- contents start -->
## Contents

- [Timeline](#timeline)
- [Status: 17 November 2026](#status-17-november-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Related freezes](#related-freezes)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 17 November 2026

Open; cause attributed (below, "How it happened"): the emulator's lost disk-done announcement of
[CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md), a test-session mechanism a player's game does not
have. Seen once, in an FS-UAE test session of the v0.0.32-dev3 image (remote console on) while measuring
[CENSUS-LOAD-SLOW-32](CENSUS-LOAD-SLOW-32.md), not reproduced in two more attempts.

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

Attributed on 17 November 2026 to the mechanism of [CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md),
captured in a test session on 16 November 2026. With the remote console on, every console line and every write of the
remote state file is a request to the remote-console folder, a host folder that the emulator serves as a drive from a
host thread. FS-UAE 3.1.66 announces a finished request by setting a bit in a shared interrupt word that its emulator
thread rewrites without atomic operations, so now and then the announcement is lost: the request is done, its reply is
never sent, and the game sleeps on it for ever.

The freeze of 8 October shows every sign of that: the remote console was on (the same traffic the later captures needed),
the game stopped right after it had taken `dbg tp balmora` from the command file (the state file counted the command and
was not rewritten again), the emulator ran on at full speed, no key or console line reached the game, and the load itself
never began (no heap line of a new load). It was not captured in a debugger, so the cause is attributed by these signs,
not measured. A player's game has no such drive. In v0.0.32 the music stream was also read in the main loop
([HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md)), a second way the same lost reply could stop the game; it reads
asynchronously since v0.0.36.

The game side cannot catch a reply that never comes (the main loop itself waits for it). What the game does catch since
v0.0.67: a load whose frames run but whose arrival never comes ends after a time limit and goes back, with an OK box
saying "The load did not finish." ([LOAD_ERRORS.md](../LOAD_ERRORS.md)).

## Why it was not caught

Debug teleports right after `dbg tp prisonship` were not part of any test sequence; the dev3 smoke
test waited about 20 s after it.

## Reproduction

Not reproduced: the same sequence (Census, Census, ship, 6 s, Balmora) on the dev3 image and once
with the QC-AW-FLAME-SPAWN-32 game logic loaded normally. Nine further Balmora, Census and ship
jumps per session with 6-30 s gaps did not freeze.

## Repair

For the test sessions, the way out of [CHIM-SEYDA-BALMORA-LOAD-HANG-43](CHIM-SEYDA-BALMORA-LOAD-HANG-43.md): the
emulator's deterministic mode, which completes host-folder requests on the emulator thread. In the game: the load time
limit and the failed-load box (v0.0.67, [LOAD_ERRORS.md](../LOAD_ERRORS.md)) for loads that stop while frames still run.

## Verification

Pending.

## Prevention

Pending the cause.

## Related freezes

10 October 2026: suspected to be the same mechanism as [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md) (full analysis and repair: a music stream read that never returns while the main loop waits for it) and [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): there the freeze needed an emulator pause followed by heavy remote console traffic, and this freeze happened with the remote console on. Not captured in a debugger, so not confirmed.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- [AW-20260928-14](AW-20260928-14.md): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- [CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66](CONSOLE-EQUIP-SKIPS-ONPCEQUIP-66.md): The original's console Equip on the player wears the item without its script's OnPCEquip: Wraithguard equipped with player->equip leaves wraithguardEquipped at 0
- [CONSOLE-GETPOS-SCRATCH-ORIGIN-66](CONSOLE-GETPOS-SCRATCH-ORIGIN-66.md): The console's GetPos on an actor answers a point near 0 instead of where the actor stands (dagoth_ur_2->getpos y read -0.43 while he stood at y 3700)
- [CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66](CONSOLE-SHOWVARS-SCRATCH-INSTANCE-66.md): The console's ShowVars on a reference prints the console's own empty instance, not the reference's script (heart_akulakhan->sv: script 0, 0 locals)
- [CONSOLE-TP-ROOM-NAME-63](CONSOLE-TP-ROOM-NAME-63.md): The console teleport to a room map name stays in the current town instead of entering the room
- [DBG-CONTAINER-AIM-NO-SPOT-59](DBG-CONTAINER-AIM-NO-SPOT-59.md): aw_placed container aim finds no standing spot the room collision accepts in Arrille's Tradehouse
- [DBG-CONTAINER-AIM-OUT-OF-REACH-67](DBG-CONTAINER-AIM-OUT-OF-REACH-67.md): aw_placed container aim stands the player 40 units from the container, past the reach for a container on the floor, and aims above a small one
- [DBG-DBATTACK-ASLEEP-COUNT-67](DBG-DBATTACK-ASLEEP-COUNT-67.md): dbg dbattack reports no sleeping frame and a dead assassin when the attack wakes the player in the rest's first frame
- [DBG-DOOR-GO-AIM-CHIM-59](DBG-DOOR-GO-AIM-CHIM-59.md): aw_hinged_door go does not bring the door under the crosshair in a CHIM room
- [DBG-ENTITY-INSPECT-39](DBG-ENTITY-INSPECT-39.md): Requested click-to-pin raw entity and reference inspection
- [DBG-PLACED-LOOK-VIEW-NOT-TURNED-61](DBG-PLACED-LOOK-VIEW-NOT-TURNED-61.md): The test commands aw_placed look and aw_view set the view angles but the view does not turn
- [DBG-QUOTED-ID-REFUSED-62](DBG-QUOTED-ID-REFUSED-62.md): A debug command with a quoted record ID holding a space is refused as an unknown debug command (dbg npcs talk "agronian guy")
- [DBG-SPAWN-CELL-ZERO-67](DBG-SPAWN-CELL-ZERO-67.md): An actor placed by the debug spawn command is booked in cell 0,0 instead of the player's cell: the focus names it under the crosshair, but nothing is drawn there
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- [DBG-TP-BEINGS-66](DBG-TP-BEINGS-66.md): Requested: the dbg tp list chooses All, Exteriors, Interiors or Beings and reaches any person or creature by name
- [DBG-TP-DOORLIST-NO-ARRIVAL-LINE-63](DBG-TP-DOORLIST-NO-ARRIVAL-LINE-63.md): dbg tp into a room reached through a door list prints no arrival line
- [DBG-TP-DURING-LOAD-66](DBG-TP-DURING-LOAD-66.md): A dbg tp typed while a load is still running is lost: a town name does nothing, a place says no map holds the point, a room prints its name and stays
- [DBG-TP-NO-FLOOR-FALLBACK-63](DBG-TP-NO-FLOOR-FALLBACK-63.md): dbg tp to a spot with no floor under it falls back to the frame centre
- [DBG-TP-ROOM-NAME-COMMA-67](DBG-TP-ROOM-NAME-COMMA-67.md): dbg tp with a room name as the place list shows it, a comma in it, is refused as an unknown debug command
- DBG-TP-SAME-MAP-54 (no report page): dbg tp X Y finds no map for a point on a MiniWind CHIM frame
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-GOD-LOCKED-DOORS-51](DEBUG-GOD-LOCKED-DOORS-51.md): Requested: in god mode a locked door opens, with a framed notice God mode used to enter a locked door
- [DEBUG-POSE-AFTER-RELOAD-52](DEBUG-POSE-AFTER-RELOAD-52.md): After a map reload a scripted check cannot return to the same view: aw_view does not take and dbg tp seyda lands on a different spot each time
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-MINIWIND-36](DEBUG-TP-MINIWIND-36.md): dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [DEBUG-VIEW-PITCH-DRIFT-54](DEBUG-VIEW-PITCH-DRIFT-54.md): aw_view alone lets the pitch drift, and the greeting camera takes the view during scripted sessions
- DEV2-REGION-LOAD-CRASH-57 (no report page): v0.0.57-dev1 dev2 image crashes with NUM_FOR_EDICT: bad pointer when a teleport loads another region (dev1 did not)
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [GAME-RECORDER-FIGHT-SEED-61](GAME-RECORDER-FIGHT-SEED-61.md): A recording made while an NPC fights the player does not replay the same: the fight takes a seed of its own on the replay's load
- [GAME-RECORDER-HOTKEY-DIALOGUE-61](GAME-RECORDER-HOTKEY-DIALOGUE-61.md): While a recording runs, Ctrl+R does not stop it when the dialogue window is open: the key goes into the dialogue search field
- [GAME-RECORDER-MISSING-61](GAME-RECORDER-MISSING-61.md): Requested: a gameplay recorder that records a play session and plays it back in another game instance
- [GODMODE-LOST-ON-MAP-CHANGE-64](GODMODE-LOST-ON-MAP-CHANGE-64.md): God mode switched on before a teleport, a door or a load is off again after the map change
- HORS-FROM-MENU-58 (no report page): dbg aw hors cannot be started from the main menu
- [HORS-IN-PLAY-NO-NEW-GAME-RESET-67](HORS-IN-PLAY-NO-NEW-GAME-RESET-67.md): dbg aw hors 0 started during play keeps the game before's script state: revealed map places, the explored map, the scripts' instances
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- [INSPECT-ACTOR-HEALTH-ZERO-67](INSPECT-ACTOR-HEALTH-ZERO-67.md): The inspect line shows health 0.0 for every living actor: it printed the engine's own health field, which holds the player's health only
- [INSPECT-CHIM-PLACEMENT-UNNAMED-42](INSPECT-CHIM-PLACEMENT-UNNAMED-42.md): Inspect pin on a placed mesh in a CHIM frame reports only worldspawn, no mesh or reference
- [INSPECT-NO-RIGHT-CLICK-EXIT-42](INSPECT-NO-RIGHT-CLICK-EXIT-42.md): Inspect mode cannot be left with the mouse: only the console command dbg hud off
- [INSPECT-OVER-VIEWPORT-42](INSPECT-OVER-VIEWPORT-42.md): Inspect mode (dbg hud) draws its hint and pinned panel on black boxes over the 3D view
- [INSPECT-PIN-LOAD-DOOR-51](INSPECT-PIN-LOAD-DOOR-51.md): The inspect pin at an exterior load door names the building shell around it, not the door: the drawn door looks absent
- [MAP-TELEPORT-28](MAP-TELEPORT-28.md): F10 map teleport intermittently fails
- [MINIWIND-CITY-COORD-TP-36](MINIWIND-CITY-COORD-TP-36.md): dbg tp X Y Z does not work inside the whole-city Vivec MiniWind: Coordinate teleport unavailable (no map on this disk holds that point)
- [MWSCRIPT-MOVE-WAITS-FOR-CONSOLE-67](MWSCRIPT-MOVE-WAITS-FOR-CONSOLE-67.md): A script that moves the player to another place runs only after the console is closed
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- [SWEEP-GNISIS-LOAD-STALL-57](SWEEP-GNISIS-LOAD-STALL-57.md): Settlement sweep: the teleport to Gnisis shows no game-clock progress for 20 s (hang or a load over 20 s)
- [SWEEP-SLOW-ARRIVALS-57](SWEEP-SLOW-ARRIVALS-57.md): Settlement sweep: 13 of 82 places run above 50 ms a frame just after arrival at 32 MB Fast
- [TELEPORT-XY-006](TELEPORT-XY-006.md): No dbg tp X Y; map teleport could land underwater
- TP-ARRIVAL-ABOVE-DOOR-57 (no report page): Settlement sweep: Bal Isra lands about 250 units above its door arrival (on top of the ruin?)
- TP-ARRIVAL-BELOW-DOOR-57 (no report page): Settlement sweep: Vivec, Temple and Uvirith s Grave land 160 to 290 units below their door arrivals
- [TP-MENU-LABEL-CUT-63](TP-MENU-LABEL-CUT-63.md): The dbg tp list box is narrower than the longest room names, so their (interior) mark can be cut off
- TP-PICKER-OPEN-FRAME-COST-57 (no report page): The dbg tp list box redraws the whole paused world every frame: 100 ms a frame open against 16 ms closed
- TP-PLACES-NO-DOOR-SEA-57 (no report page): Settlement list: Fields of Kummu arrives in the water (a place without a door used its cell middle)

Related bugs in other categories:

- [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md): The game freezes with the music looping after the player is left idle for a few minutes outdoors, seen around sundown
- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load

<!-- END GENERATED CATEGORY -->
