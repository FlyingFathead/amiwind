# HUD-GLOBAL-NO-REGIONS-33: The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | debug HUD GLOBAL row (aw_hud.c) on a disk without world/regions.awr |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Debug only: the GLOBAL row (and with it the cell readout) was empty on MiniWind disks. |
| Family | Debug commands and remote control (`debug-commands`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Fixed in source on v0.0.34-hud-cell (112c562), not shipped at the time of writing. Found while
adding the original-cell readout to the debug HUD.

## Symptom

On a MiniWind disk (CHIM Balmora and its interiors, no open world), the debug HUD's first row read
`GLOBAL XYZ: unavailable (interior)` while the player stood in the Balmora exterior, so the new
`CELL x,y` readout and `dbg cell` had no position either. `chim_tp X Y` (original coordinates) worked
on the same disk.

## Where

`engine/aga/src/aw_hud.c` (the GLOBAL row). `AW_WorldToSource` (`aw_world.c`) takes a town's origin
from the world directory `world/regions.awr`; a MiniWind disk does not have it. The other users of
`AW_WorldToSource` (lamps, photo mode, remote state) are unchanged by the repair.

## How it happened

The GLOBAL row was written for the legacy world, where every exterior map (a region or a town slot)
is listed in the world directory. A CHIM frame map knows its own centre (`_chim_frame`, used by
`chim_tp`), but the HUD never asked it, and partial-area disks that leave the world directory out
came later.

## Why it was not caught

The HUD host test only used a map with a world-directory transform, and the FS-UAE runs that read
the GLOBAL row used full images with the world directory.

## Reproduction

Boot a MiniWind disk (no `world/regions.awr`), switch the debug HUD on (`dbg all on`) in the
Balmora exterior: the first row says "unavailable".

## Repair

- `Chim_Init` sets the hook `aw_chim_source` (owned by `aw_hud.c`): on the active CHIM frame,
  global = local x 4 + the frame centre (Z x 4), the inverse of `chim_tp`.
- The HUD's GLOBAL row, the cell readout and `dbg cell` use the world directory's transform first,
  then the CHIM frame's.
- Host tests: `tests/aga_hud_test.c` (no transform, then the frame hook: GLOBAL row and the cell on
  both sides of a cell edge), `tests/aga_chim_world_test.c` (the hook is unset before `Chim_Init`,
  refuses without a frame map and matches the frame centre on one). Gate 1031 green.

## Verification

FS-UAE, MiniWind evidence image with the v0.0.34-hud-cell engine: Balmora centre
`GLOBAL XYZ: -20480 -12289`, `CELL -3,-2`; either side of the -3/-2 cell edge `CELL -3,-2` and
`CELL -2,-2`; south of the -2/-3 edge `CELL -3,-3`. All match the original game's Balmora exterior
cells.

## Prevention

The HUD host test covers a map without a world-directory transform, with and without the CHIM
frame hook.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-CHIMTOWNS-33](DEBUG-TP-CHIMTOWNS-33.md): After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

<!-- END GENERATED CATEGORY -->
