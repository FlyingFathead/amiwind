# DEBUG-TP-CHIMTOWNS-33: After chim_towns 0, dbg tp from a CHIM town reloads that town on legacy maps at the current position

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | engine dbg tp and chim_towns (CHIM preview engine 0d8bf4f) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Test sessions only: the A/B switch lands at the wrong place; dbg tp seydaneen from Seyda once left coordinate teleport unavailable. |
| Family | Debug commands and remote control (`debug-commands`) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Seen in FS-UAE test sessions on the CHIM preview engine (0d8bf4f).

## Symptom

With the player in CHIM Balmora, `chim_towns 0` followed by `dbg tp -21800 -12300` or
`dbg tp seydaneen` loaded the legacy Balmora region map for the current position
(bm035 at -20500 -9500) instead of the destination. Once, `dbg tp seydaneen` issued in Seyda Neen
was followed by "Coordinate teleport unavailable; player state unchanged." for the next
`dbg tp X Y`.

## Where

`dbg tp` and the `chim_towns` switch.

## How it happened

Unknown; probably the town reload for the changed `chim_towns` value takes the place of the
teleport.

## Why it was not caught

The A/B switch was only used from another town.

## Reproduction

Stand in CHIM Balmora, `chim_towns 0`, `dbg tp seydaneen`.

## Repair

Pending. Test scripts switch `chim_towns` from another town.

## Verification

Pending.

## Prevention

A host test of `dbg tp` after a `chim_towns` change.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [COMPANION-PICK-RMB-33](COMPANION-PICK-RMB-33.md): The right mouse button does not pick a companion: "MOUSE3 is unbound"
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- [ENGINE-UNLINK-STUB-35](ENGINE-UNLINK-STUB-35.md): unlink was a stub that deleted nothing, so -condebug appended to the previous console log
- [HUD-GLOBAL-NO-REGIONS-33](HUD-GLOBAL-NO-REGIONS-33.md): The debug HUD said "GLOBAL XYZ: unavailable" on a CHIM town on a disk without the world directory (MiniWind)
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

Related bugs in other categories:

- [CHIM-SLOWCPU-FRAMETIME-33](CHIM-SLOWCPU-FRAMETIME-33.md): Balmora on CHIM runs at about 1 frame per second on a slow 68040 (cycle-exact emulation)

<!-- END GENERATED CATEGORY -->
