# DEBUG-TP-MINIWIND-36: dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.57-dev1 at 2026-10-30 07:07 +0200: Balmora exterior MiniWind 2a3284a: every dbg tp X Y unavailable, also beside the player; the new settlement list (dbg tp, TP-PICKER-57) therefore takes you nowhere on a MiniWind; full dev1 image works
- Reported with v0.0.62-dev1 at 2026-11-07 06:16 +0200: Seyda Neen CHIM MiniWind b3bf27ea: dbg tp X Y refused (no map on this disk holds that point); scripted checks moved with noclip + aw_view

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 11 October 2026, in v0.0.36-dev4 |
| Where | aw_scene.c teleport_command, aw_world.c AW_WorldMapTarget (world/regions.awr) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev4 (last seen) |
| Severity | low: test sessions only: evidence poses in MiniWind sandboxes need noclip and aw_view instead |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | MiniWind v0.0.36-dev4 |
| From commit | source 1b5e0aa, engine 1b5e0aa, CHIM world 1b5e0aa |
| CHIM engine version | CHIM 0.1.0, engine 1b5e0aa, world format 0.7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.62-dev1 (7 November 2026)._

## Status: 7 November 2026

Open until a numbered build carries the fix. Seen again in the Seyda Neen MiniWind of v0.0.62-dev1. A fix is on its
way into v0.0.62 (see Repair); it counts as fixed once `dbg tp X Y` is seen landing inside a MiniWind of a numbered
build.

## Status: 11 October 2026

Open. Found while taking evidence frames in a Balmora MiniWind sandbox; worked around with `noclip` and
`aw_view` (local coordinates).

## Symptom

In a MiniWind build of the Balmora exterior on CHIM, `dbg tp -24400 -11196` (original Morrowind global
coordinates inside Balmora's frame) prints "Coordinate teleport unavailable (no map on this disk holds that
point); player state unchanged." The player stays where he is. `noclip` followed by `aw_view` with the frame's
local coordinates does move the camera there.

## Where

`engine/aga/src/aw_scene.c` `teleport_command` -> `AW_MapTeleportAt` -> `engine/aga/src/aw_world.c`
`AW_WorldMapTarget` -> `load_directory`.

## How it happened

`AW_WorldMapTarget` first reads `world/regions.awr`, the open-world region table, and returns "no map" when
that file is missing, before it looks at the towns. The town rows it needs (each town's origin and core) are
read from the same file. A MiniWind image holds one town and no open world, so it ships no `regions.awr`, and
every coordinate teleport fails, even to a point inside the town the sandbox holds. The named teleports
(`dbg tp balmora`) take another path.

## Why it was not caught

Coordinate teleports were tested on full images, which always ship the region table. The MiniWind tests
start at the preset's spot and never teleport by coordinates.

## Reproduction

Always, in any MiniWind image: `dbg tp <x> <y>` with a point inside the sandbox's town.

## Repair

v0.0.62: on a disk without the open-world region table, `dbg tp X Y [Z]` (and `dbg tp marker`) resolves a point
inside the map that is loaded, through the same conversion the debug HUD uses for its global coordinates (the
loaded CHIM frame), and loads the player there as any coordinate teleport does (`aw_world.c`
`AW_WorldLoadedTarget`, `aw_scene.c` `teleport_command`). A disk with the table answers as before; scripts
(Position) keep the table's answer alone. A refused coordinate teleport now also prints which maps the disk holds
and, on a MiniWind, where the player stands in original coordinates. Test: `tests/aga_world_regions_test.c` with
no region table (inside the loaded map, outside it, another map, a name too long for a map).

## Verification

To do: `dbg tp` inside the sandbox's town in a MiniWind of a numbered build lands there; a full build is unchanged.

## Prevention

To do: the MiniWind test method uses coordinate teleports for its evidence poses, so a regression shows at once.

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
- DBG-TP-DOORLIST-NO-ARRIVAL-LINE-63 (no report page): dbg tp into a room reached through a door list prints no arrival line
- DBG-TP-NO-FLOOR-FALLBACK-63 (no report page): dbg tp to a spot with no floor under it falls back to the frame centre
- DBG-TP-SAME-MAP-54 (no report page): dbg tp X Y finds no map for a point on a MiniWind CHIM frame
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- DEBUG-GOD-LOCKED-DOORS-51 (no report page): Requested: in god mode a locked door opens, with a framed notice God mode used to enter a locked door
- DEBUG-POSE-AFTER-RELOAD-52 (no report page): After a map reload a scripted check cannot return to the same view: aw_view does not take and dbg tp seyda lands on a different spot each time
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- DEBUG-VIEW-PITCH-DRIFT-54 (no report page): aw_view alone lets the pitch drift, and the greeting camera takes the view during scripted sessions
- DEV2-REGION-LOAD-CRASH-57 (no report page): v0.0.57-dev1 dev2 image crashes with NUM_FOR_EDICT: bad pointer when a teleport loads another region (dev1 did not)
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- GAME-RECORDER-FIGHT-SEED-61 (no report page): A recording made while an NPC fights the player does not replay the same: the fight takes a seed of its own on the replay's load
- GAME-RECORDER-HOTKEY-DIALOGUE-61 (no report page): While a recording runs, Ctrl+R does not stop it when the dialogue window is open: the key goes into the dialogue search field
- [GAME-RECORDER-MISSING-61](GAME-RECORDER-MISSING-61.md): Requested: a gameplay recorder that records a play session and plays it back in another game instance
- GODMODE-LOST-ON-MAP-CHANGE-64 (no report page): God mode switched on before a teleport, a door or a load is off again after the map change
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

<!-- END GENERATED CATEGORY -->
