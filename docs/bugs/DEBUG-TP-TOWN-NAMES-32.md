# DEBUG-TP-TOWN-NAMES-32: dbg tp help omits new towns and has no short town names

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | dbg tp help text and town name lookup (aw_scene.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | low: Help omits new towns and short names such as vivec are not accepted; debug-only. |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on v0.0.32-dev; not in the dev1 playtest build; not shipped at the time of writing. Found while
checking the v0.0.32-dev1 teleport presets.

## Symptom

`dbg tp vivec_arena` works (the town table marks the Arena as a teleport arrival, and the
`dbg tp` menu lists every installed map), but the help line still says only
"balmora/seydaneen/prisonship/<map name>", and `dbg tp vivec` says "Destination not found".

## Where

`engine/aga/src/aw_scene.c` (`scene_command` help text and name lookup).

## How it happened

Help text and names were written before the data-driven town table.

## Why it was not caught

No test compares the help text with the town table.

## Reproduction

In dev1: `dbg tp vivec`, then `dbg tp` with a wrong argument to see the help line.

## Repair

`scene_help()` builds the help line from the town table (every town marked for teleport
arrival); `dbg tp vivec` and `dbg tp arena` map to `vivec_arena` while the Arena is the only
Vivec town. README and the console command page say how to visit the Arena preview.

## Verification

`tests/test_debug_tp_names.py`; full gate 116 green (1,421 tests, engine with 0 warnings).
In-game check with the next engine build.

## Prevention

A test that every teleport town appears in the help text.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

<!-- END GENERATED CATEGORY -->
