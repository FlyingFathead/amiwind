# CONSOLE-COMMAND-SHADOWED-BY-CVAR-36: dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | aw_combat.c, aw_animkit.c: Cmd_AddCommand after a cvar of the same name; debug-commands.txt |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | medium: Every dbg combat and dbg animkit option did nothing in game; the host fixtures did not model Quake's refusal |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 2b48d60 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev2 (17 October 2026)._

## Status: 11 October 2026

Repaired in source on v0.0.36-blocking, not yet in a build. Found by the blocking fight smoke (COMBAT-BLOCKING-36).

## Symptom

In game, `aw_combat` (the handler behind `dbg combat`) only printed `"aw_combat" is "1"`: no status report, and
none of its options (seed, loadout, readout, dice, style, block, calm) ran. `dbg animkit` (handler `aw_animkit`) had
the same fault.

## Where

`engine/aga/src/aw_combat.c` and `aw_animkit.c` register a cvar and then a console command of the same name;
`config/debug-commands.txt` routes the debug words to those names.

## How it happened

Quake's `Cmd_AddCommand` refuses a command whose name is already a cvar ("already defined as a var"), and
`Cmd_ExecuteString` then hands the line to the cvar. Both files register the cvar first, so the command was
never added.

## Why it was not caught

The host fixtures stub `Cmd_AddCommand` without Quake's check, so every fixture test of these commands passed; no
in-game smoke ran a `dbg combat` option and read the answer.

## Reproduction

Always, in any build since the commands were added: console `dbg combat` or `aw_combat` prints the cvar.

## Repair

The handlers are now `aw_combat_cmd` and `aw_animkit_cmd` (the cvars `aw_combat` and `aw_animkit` keep their names
and meaning); the catalogue routes `dbg combat` and `dbg animkit` to them.

## Verification

`tests/test_console_command_names.py` sweeps every engine source: no `Cmd_AddCommand` name may be a cvar name.
Pending: the gate and the in-game `dbg combat` report in the blocking smoke.

## Prevention

The sweep test covers every command of the engine, now and future.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
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
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- SWEEP-GNISIS-LOAD-STALL-57 (no report page): Settlement sweep: the teleport to Gnisis shows no game-clock progress for 20 s (hang or a load over 20 s)
- [SWEEP-SLOW-ARRIVALS-57](SWEEP-SLOW-ARRIVALS-57.md): Settlement sweep: 13 of 82 places run above 50 ms a frame just after arrival at 32 MB Fast
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater
- TP-ARRIVAL-ABOVE-DOOR-57 (no report page): Settlement sweep: Bal Isra lands about 250 units above its door arrival (on top of the ruin?)
- TP-ARRIVAL-BELOW-DOOR-57 (no report page): Settlement sweep: Vivec, Temple and Uvirith s Grave land 160 to 290 units below their door arrivals
- TP-MENU-LABEL-CUT-63 (no report page): The dbg tp list box is narrower than the longest room names, so their (interior) mark can be cut off
- TP-PICKER-OPEN-FRAME-COST-57 (no report page): The dbg tp list box redraws the whole paused world every frame: 100 ms a frame open against 16 ms closed
- TP-PLACES-NO-DOOR-SEA-57 (no report page): Settlement list: Fields of Kummu arrives in the water (a place without a door used its cell middle)

Related bugs in other categories:

- [COMBAT-BLOCKING-36](COMBAT-BLOCKING-36.md): Requested: blocking in combat - NPCs block by their Block skill with a block animation, the player blocks with the right mouse button

<!-- END GENERATED CATEGORY -->
