# DEBUG-TP-CHIM-33: dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | dbg tp coordinate targets and help (aw_world.c, aw_scene.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Debug only: dbg tp X Y into a CHIM town failed on a pure-CHIM disk; the help offered towns the disk lacks. |
| Family | Debug commands and remote control (`debug-commands`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.33-chim-engine; not in a build yet. Found by an audit of every `dbg tp`
form against a pure-CHIM disk (the towns' legacy exterior maps gone, only `maps/<town>-chim.bsp`
and the region tables).

## Symptom

- `dbg tp X Y` (original Morrowind coordinates) inside Balmora or Seyda Neen said "Coordinate
  teleport unavailable" on a pure-CHIM disk, although the town runs there on its CHIM frame map.
- Walking from the open world into a CHIM town could not hand over to the town for the same reason.
- `dbg tp` with no valid name printed every teleport town of the town table (`prisonship`, all
  Vivec cantons), whether or not the disk had its map.
- There was no way to give a height: `dbg tp X Y` always landed on the highest surface (a roof
  instead of the street under a bridge or an upper floor).

## Where

`engine/aga/src/aw_world.c` (`AW_WorldMapTarget`, `AW_WorldDestination`), `aw_scene.c`
(`scene_help`, `teleport_command`), `aw_console.c` (the `dbg tp` argument rule).

## How it happened

The coordinate targets checked that `maps/<target>.bsp` exists. For a town that is the legacy alias
map, which a pure-CHIM disk does not have; every other scene check had already moved to
`AW_SceneMapSize` (the scene's own map, else the town's CHIM frame map). The help line was built
from the town table alone (DEBUG-TP-TOWN-NAMES-32), before towns could be missing from a disk.

## Why it was not caught

The pure-CHIM disk host test covered named arrivals, saves and the scene checks, not coordinate
targets or the help line; FS-UAE runs used images that still held the legacy maps.

## Reproduction

On a disk with only `maps/balmora-chim.bsp` for Balmora: `dbg tp -15000 -12000` (inside Balmora).

## Repair

- Coordinate targets (and the open-world hand-over into a town) check the destination with
  `AW_SceneMapSize`, so a CHIM town resolves to its frame map; the arrival then loads the chunk ring
  before the ground search, as every CHIM arrival does.
- `dbg tp X Y Z`: the player lands on the first walkable floor at or below Z (a solid start steps
  down up to 128 units), then the usual highest-floor search and the scene spawn as fallbacks.
- The help and error lines (`Unknown destination: ...`, `Destination not on this disk: ...`) list
  only the named destinations this disk has.

## Verification

Host tests on the pure-CHIM disk fixture (`tests/test_chim_pure_disk_native.py`): coordinates in
Balmora and Seyda Neen resolve to the towns on both disks, the open world's region map only on the
legacy disk, the height maps to the town's local Z, the destination list differs by disk. FS-UAE
check on a pure-CHIM image pending.

## Prevention

The same host test fails if a coordinate target checks a map file directly again or the list offers
a town without its map.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

<!-- END GENERATED CATEGORY -->
