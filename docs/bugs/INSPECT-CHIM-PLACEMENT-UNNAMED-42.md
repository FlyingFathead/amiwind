# INSPECT-CHIM-PLACEMENT-UNNAMED-42: Inspect pin on a placed mesh in a CHIM frame reports only worldspawn, no mesh or reference

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 17 October 2026, in v0.0.42-dev1 |
| Where | dbg hud pin on CHIM placements (Vivec city frame mushrooms) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.42-dev1 (last seen) |
| Severity | medium: The maintainer cannot name the mesh he points at; every CHIM placement collides as the world. |
| Family | Debug commands and remote control (`debug-commands`) |
| CHIM | Engine streaming and memory ([CHIM Engine tracker](CHIM_TRACKER.md)) |
| Playtest version | v0.0.42-dev1 |
| From commit | source 5e043ad, engine 5e043ad, CHIM world 5e043ad |
| CHIM engine version | CHIM 0.2.1, engine 5e043ad, world format 0.7 |
| Platform or emulator | FS-UAE (maintainer's play session) |

<!-- END GENERATED FACTS -->

## Symptom

Pinning one of Vivec's giant mushrooms with `dbg hud on` shows "class/name: worldspawn / unnamed, source id:
unavailable, source ref: unavailable, model: maps/vivec_city-chim.chim" (maintainer frames, v0.0.42-dev1,
17 October 2026: hits at vivec_city local -3973.3 3078.5 212.9, -4002.9 3117.9 198.3 and -2700.1 -325.5 214.3).
He cannot tell which mesh he is pointing at.

## Where

`engine/aga/src/aw_inspect.c` `pin_target`; the CHIM placements (`chim_chunks.c`).

## How it happened

A CHIM placement is not an edict: the frame's chunks hold placement records and collide through the
`aw_chim_clip` hook inside `SV_Move`, which reports every hit as the world. The pin only knew edicts and client
statics.

## Why it was not caught

The inspection HUD was written and tested on edicts (NPCs) and statics; no CHIM frame was in its test.

## Reproduction

Any CHIM area: `dbg hud on`, aim at a building, rock or plant and click.

## Repair

When the view ray hits the world, the pin asks the CHIM frame which linked placement the same ray hits
(`ChimChunks_Pick`: the same hull test as the collision, point ray). If that placement is at the same distance it
is the one hit: the pin names the placement id, the model's name from the CHIM index (`world.cwi` names), the
Morrowind reference number and its original cell (re-read from the placement record in the sector file) and the
placement's origin and yaw. A few small reads per click, none per frame; the runtime placement is unchanged.

For the maintainer's three hits the build's own scenery index already gives the answer: references 172013
(cell 2,-10) and 172126 (cell 2,-12), both `flora_emp_parasol_03` (MESH-VIVEC-CAP-GAP-38).

## Verification

`tests/aga_inspect_test.c` (a CHIM pick at the hit distance names the placement; at another distance it is the
terrain) and `tests/aga_chim_world_test.c` (a ray onto a yawed placement returns its pid, reference, model name
and the point-hull distance; a ray past it returns nothing). In game: pending a MiniWind pin.

## Prevention

Both tests above.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- [DBG-ENTITY-INSPECT-39](DBG-ENTITY-INSPECT-39.md): Requested click-to-pin raw entity and reference inspection
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-MINIWIND-36](DEBUG-TP-MINIWIND-36.md): dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- [INSPECT-NO-RIGHT-CLICK-EXIT-42](INSPECT-NO-RIGHT-CLICK-EXIT-42.md): Inspect mode cannot be left with the mouse: only the console command dbg hud off
- [INSPECT-OVER-VIEWPORT-42](INSPECT-OVER-VIEWPORT-42.md): Inspect mode (dbg hud) draws its hint and pinned panel on black boxes over the 3D view
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [MINIWIND-CITY-COORD-TP-36](MINIWIND-CITY-COORD-TP-36.md): dbg tp X Y Z does not work inside the whole-city Vivec MiniWind: Coordinate teleport unavailable (no map on this disk holds that point)
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

<!-- END GENERATED CATEGORY -->
