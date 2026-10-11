# DEBUG-TP-MINIWIND-36: dbg tp X Y does nothing in a MiniWind build: the coordinate teleport needs the open-world region table, which a MiniWind image leaves out

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

To do: resolve the towns without the open-world table (the town rows from the town table the image already
ships), and read `regions.awr` only for the open-world part; or write a town-only `regions.awr` into MiniWind
images. A test that a MiniWind image resolves a coordinate inside its town.

## Verification

To do: `dbg tp` inside the sandbox's town in a MiniWind build lands there; a full build is unchanged.

## Prevention

To do: the MiniWind test method uses coordinate teleports for its evidence poses, so a regression shows at once.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [CONSOLE-COMMAND-SHADOWED-BY-CVAR-36](CONSOLE-COMMAND-SHADOWED-BY-CVAR-36.md): dbg combat and dbg animkit options never ran: their console commands share a name with a cvar, so Quake refused the command and the cvar answered
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [MINIWIND-CITY-COORD-TP-36](MINIWIND-CITY-COORD-TP-36.md): dbg tp X Y Z does not work inside the whole-city Vivec MiniWind: Coordinate teleport unavailable (no map on this disk holds that point)
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

<!-- END GENERATED CATEGORY -->
