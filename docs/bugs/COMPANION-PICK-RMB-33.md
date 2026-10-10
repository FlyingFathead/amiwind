# COMPANION-PICK-RMB-33: The right mouse button does not pick a companion: "MOUSE3 is unbound"

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | config/keymaps.cfg default binds; vid_amiga.c button mapping |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-rc1 (last seen) |
| Severity | low: Pick mode works with attack only; the right button the owner expects is unbound. |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.33-rc1 |
| From commit | source 7ae3ea7, engine 7ae3ea7, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 7ae3ea7, world format unknown |
| Unknown because | owner playtest report names no image commit or world format |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Repaired in source on v0.0.33-arena-combat, not yet in a build or gated. Found in the owner's playtest.

## Symptom

In pick mode (`dbg companion pick`), with the red crosshair on Dralsea Arethi in Balmora, the right
mouse button printed "MOUSE3 is unbound, hit F4 to set." and picked nothing.

## Where

`engine/aga/src/vid_amiga.c` (and `sys_amiga.c`) map the Amiga mouse buttons: left to `MOUSE1`,
middle to `MOUSE2`, right to `MOUSE3` (Quake on a PC calls the right button `MOUSE2`).
`config/keymaps.cfg` bound only `MOUSE1`; pick mode listens to the attack button only.

## How it happened

Pick mode was built around the attack button; the default keymap never bound the Amiga's right
button, which arrives as `MOUSE3`, not as the PC's `MOUSE2`.

## Why it was not caught

No test covered the default binds of the mouse buttons; the console line went unnoticed in an
earlier capture (docs/PLAYTEST_STATUS.md mentions the unbound `MOUSE3`).

## Reproduction

Always: `dbg companion pick`, aim at a resident, press the right mouse button.

## Repair

One coherent mouse map: left = attack (`MOUSE1`), right = a context action `+aw_alt` (`MOUSE3`,
default keymap and the saved-config migration when `MOUSE3` is unbound). `+aw_alt` picks the
companion under the crosshair in pick mode; in a fight it is kept for the held block, an AmiWind
extension that is not built yet (the original blocks automatically; COMBAT-SETUP-DICE-BLOCK-33);
otherwise it does nothing. Middle (`MOUSE2`) keeps its gallery and map uses. Documented in
docs/KEYMAPS.md.

## Verification

tests/test_combat.py `test_right_mouse_button_default_bind` (button mapping, default bind, migration,
command, pick hook) and the companion fixture (`AW_CompanionPickAim`: not handled outside pick mode,
handled in pick mode). Pending: the gate and an in-game check.

## Prevention

Every default control has a test over the shipped keymap; Amiga button names are documented next
to the bind.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
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
