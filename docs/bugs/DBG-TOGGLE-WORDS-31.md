# DBG-TOGGLE-WORDS-31: dbg on/off words turned settings off

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.31-dev6 |
| Where | Console dbg routes onto settings (aw_console.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.31 |
| Severity | low: dbg on turned settings off; debug console only. |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.31-dev6 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found while checking `dbg fog`; repaired in source, not yet packaged.

## Symptom

`dbg help` says toggle values may be on/off, true/false or 1/0, but for `dbg`
names that map straight onto a setting (`dbg fog`, `dbg skyline fill`,
`dbg fog location`, `dbg warm light` and others) `on` switched the setting off.

## Where

`engine/aga/src/aw_console.c`, `route_format`: the catalogue route passed the
word through unchanged, and Quake reads a setting's value as a number, so
"on" became 0.

## How it happened

Commands with their own argument parsing (`guardtorch`, `headlamp`) accept the
words; settings never did, and the help text promised it for all.

## Why it was not caught

The console tests checked command routes, not routes onto settings with words.

## Reproduction

Any build up to v0.0.31-dev6: `dbg fog on` turns the fog off.

## Repair

A route onto a setting turns on/true/yes into 1 and off/false/no into 0 for a
single argument; commands keep their own words. Native test cases cover both.

## Verification

Native console test; owner check pending.

## Prevention

The help's promise is now covered by a test for settings and commands.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Debug commands and remote control (`debug-commands`). dbg commands, teleports, debug map loads and the remote console. See [families](README.md#families).

- AW-20260928-14 (no report page): Master debug toggle omits coordinates
- DEBUG-ALIASES-29 (no report page): Discoverable video-player aliases and disk-backed help
- [DEBUG-TP-CHIM-33](DEBUG-TP-CHIM-33.md): dbg tp to original coordinates fails in a CHIM town on a pure-CHIM disk, and its help offers towns the disk does not have
- [DEBUG-TP-SHIP-FREEZE-32](DEBUG-TP-SHIP-FREEZE-32.md): The game froze once on dbg tp balmora issued 6 s after dbg tp prisonship
- [DEBUG-TP-TOWN-NAMES-32](DEBUG-TP-TOWN-NAMES-32.md): dbg tp help omits new towns and has no short town names
- MAP-TELEPORT-28 (no report page): F10 map teleport intermittently fails
- [REMOTE-CONSOLE-APPEND-31](REMOTE-CONSOLE-APPEND-31.md): Remote console log keeps only the last message
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

<!-- END GENERATED CATEGORY -->
