# HORS-IN-PLAY-NO-NEW-GAME-RESET-67: dbg aw hors 0 started during play keeps the game before's script state: revealed map places, the explored map, the scripts' instances

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 17 November 2026, in v0.0.67-dev1 |
| Where | Debug command dbg aw hors 0 started in play (aw_scene.c hors_command) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.67-dev1 (last seen) |
| Severity | medium: the debug jump is used to restart play after a hang; the new game then carries places, map and script state of the old one, which makes test findings after it unreliable |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.67-dev1 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |
| Platform or emulator | FS-UAE 3.1.66, JIT, A1200 68040 preset, 32 MB Fast |

<!-- END GENERATED FACTS -->

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
- DBG-TP-SAME-MAP-54 (no report page): dbg tp X Y finds no map for a point on a MiniWind CHIM frame
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-GOD-LOCKED-DOORS-51](DEBUG-GOD-LOCKED-DOORS-51.md): Requested: in god mode a locked door opens, with a framed notice God mode used to enter a locked door
- [DEBUG-POSE-AFTER-RELOAD-52](DEBUG-POSE-AFTER-RELOAD-52.md): After a map reload a scripted check cannot return to the same view: aw_view does not take and dbg tp seyda lands on a different spot each time
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-MINIWIND-36](DEBUG-TP-MINIWIND-36.md): dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [DEBUG-VIEW-PITCH-DRIFT-54](DEBUG-VIEW-PITCH-DRIFT-54.md): aw_view alone lets the pitch drift, and the greeting camera takes the view during scripted sessions
- DEV2-REGION-LOAD-CRASH-57 (no report page): v0.0.57-dev1 dev2 image crashes with NUM_FOR_EDICT: bad pointer when a teleport loads another region (dev1 did not)
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [GAME-RECORDER-FIGHT-SEED-61](GAME-RECORDER-FIGHT-SEED-61.md): A recording made while an NPC fights the player does not replay the same: the fight takes a seed of its own on the replay's load
- [GAME-RECORDER-HOTKEY-DIALOGUE-61](GAME-RECORDER-HOTKEY-DIALOGUE-61.md): While a recording runs, Ctrl+R does not stop it when the dialogue window is open: the key goes into the dialogue search field
- [GAME-RECORDER-MISSING-61](GAME-RECORDER-MISSING-61.md): Requested: a gameplay recorder that records a play session and plays it back in another game instance
- [GODMODE-LOST-ON-MAP-CHANGE-64](GODMODE-LOST-ON-MAP-CHANGE-64.md): God mode switched on before a teleport, a door or a load is off again after the map change
- HORS-FROM-MENU-58 (no report page): dbg aw hors cannot be started from the main menu
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

- [HELD-WEAPON-WRONG-MODEL-62](HELD-WEAPON-WRONG-MODEL-62.md): An actor's held weapon is drawn with another actor's model after the opening is skipped
- [MAP-PLACES-SHOWN-UNVISITED-67](MAP-PLACES-SHOWN-UNVISITED-67.md): The map shows places the player has never visited (Pelagiad, the Moonmoth Legion fort)
- [NEWGAME-STATE-RESET-62](NEWGAME-STATE-RESET-62.md): A New Game started from the menu after playing leaves the fireplace of the Census and Excise Office unlit

<!-- END GENERATED CATEGORY -->
