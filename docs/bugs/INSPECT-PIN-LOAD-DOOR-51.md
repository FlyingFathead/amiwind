# INSPECT-PIN-LOAD-DOOR-51: The inspect pin at an exterior load door names the building shell around it, not the door

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 25 October 2026, in v0.0.51 |
| Where | dbg hud inspect pin (collision pick) on load doors in CHIM region frames |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.51 (last seen) |
| Severity | low: A debug view only: the door is drawn and, since v0.0.53-dev2, usable; the pin made it look missing |
| Family | Debug commands and remote control (`debug-commands`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | 2026_10_25_v0.0.51_final_d74cc652 |
| From commit | source 3c0c6c8, engine 3c0c6c8, CHIM world 3c0c6c8 |
| CHIM engine version | CHIM 0.2.2, engine 3c0c6c8, world format 0.12 |
| Platform or emulator | FS-UAE, JIT, A1200 profile, 32 MB Fast RAM |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.53 (27 October 2026)._

## Status: 27 October 2026

Open. Reported by the maintainer with his v0.0.51 shots of 25 October 2026. A debug view only: since v0.0.53 the doors
in question are drawn, prompt and enter.

## Symptom

With the inspect pin on (`dbg hud inspect`), the crosshair on an exterior load door in a CHIM region frame pins the
building shell around the door by its collision pick, for example the Velothi tomb entrance at 8,14 and the Imperial
guard tower at 9,14, while the door itself is drawn right in front of the crosshair. It reads as if the door were not
there.

## Where

The inspect pin's collision pick (`dbg hud inspect`) on load doors in CHIM region frames.

## What has to be done

When the crosshair is on a load door, the pin names the door: its reference and the room it leads to.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- [DBG-ENTITY-INSPECT-39](DBG-ENTITY-INSPECT-39.md): Requested click-to-pin raw entity and reference inspection
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

- [CHIM-REGION-DOORS-NO-PROMPT-42](CHIM-REGION-DOORS-NO-PROMPT-42.md): Doors in CHIM region cells show no entrance at all (no prompt, not even Interior unavailable), e.g. every door in Khuul

<!-- END GENERATED CATEGORY -->
