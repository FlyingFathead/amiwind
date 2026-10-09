# REMOTE-STATE-WIDTH-31: Remote state file printed "51.*ld" for fractional fields

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | remote state file formatter (engine remote pipe) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: Debug state file printed garbled numbers; never released. |
| Family | Debug commands and remote control (`debug-commands`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Fixed in source on the FPU fixes branch before any build left it; never released.

## Symptom

In an emulator benchmark with the FPU-fixes engine, `AWCTL:state.txt` showed
`frame_ms 51.*ld` (and the same for `realtime` and `angles`) instead of numbers.

## Where

`engine/aga/src/aw_remote.c`, the fixed-point formatter added to keep float
formatting out of the state file ([ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md)).

## How it happened

The formatter used a `*` field width (`%0*ld`). The Amiga C library does not
support `*` widths and printed the text literally.

## Why it was not caught

The host test of the remote pipe runs with the Linux C library, which supports
`*` widths; only the Amiga build shows the fault.

## Reproduction

Run the remote pipe (`aw_remote 1`) with the affected build and read
`state.txt`.

## Repair

Explicit `%01ld`/`%02ld` formats instead of a `*` width.

## Verification

8 October 2026: rebuilt engine in a remote session wrote `frame_ms 16.2` and
`angles -2.8 112.5`; the gate suite includes the new format test.

## Prevention

`tests/test_check_fpu_unimplemented.py` fails on any `*` field width in an engine
printf format string.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- [DBG-TOGGLE-WORDS-31](DBG-TOGGLE-WORDS-31.md): dbg on/off words turned settings off
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

Related bugs in other categories:

- [ENGINE-FPU-UNIMPL-31](ENGINE-FPU-UNIMPL-31.md): Every-frame math traps on a real 68040 (sin+cos become cexp)

<!-- END GENERATED CATEGORY -->
