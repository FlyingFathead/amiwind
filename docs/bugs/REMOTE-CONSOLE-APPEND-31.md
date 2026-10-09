# REMOTE-CONSOLE-APPEND-31: Remote console log keeps only the last message

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.31 |
| Where | Remote console log (console.c, Con_DebugLog) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev5, v0.0.31 (last seen) |
| Severity | low: Debug log keeps only the last message. |
| Family | Debug commands and remote control (`debug-commands`) |
| Playtest version | v0.0.31 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open; fix in source (not yet in a released build).

## Symptom

With `aw_remote 1`, `AWCTL:console.log` should collect every console line
(Quake's `-condebug` log). In a v0.0.31 benchmark session it held three short
fragments after a long run: each new message was written over the start of
the file, so earlier lines (for example the first of two `timerefresh`
results) were lost.

## Where

`engine/aga/src/console.c` `Con_DebugLog` (also used by `-condebug`'s
`qconsole.log`). Present since the remote console pipe was added in
v0.0.31-dev5.

## How it happened

The log is opened with `open(..., O_WRONLY | O_CREAT | O_APPEND)` for every
message. The Amiga C library opens the file at position 0 and does not apply
`O_APPEND`, so every write started at offset 0.

## Why it was not caught

The remote pipe was checked by reading `state.txt` (rewritten in place by
design) and single command results; no test wrote two console lines and read
both back.

## Reproduction

Start a session with `aw_remote 1`, run `timerefresh` twice, read
`AWCTL:console.log`: one result line remains, followed by fragments of
longer earlier lines.

## Repair

Seek to the end of the file after opening it, before writing; skip the write
when the open fails.

## Verification

8 October 2026, FPU-fixes engine on the v0.0.31 image: a 40-second remote
session kept all 40 once-a-second `fpucount` lines plus both `timerefresh`
results in order (the v0.0.31 engine kept one).

## Prevention

Benchmark scripts compare the number of commands sent with the result lines
read back.

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
- [REMOTE-CONSOLE-LOG-COST-32](REMOTE-CONSOLE-LOG-COST-32.md): With the remote console on, every console line costs about 7-18 ms in FS-UAE
- [REMOTE-STATE-WIDTH-31](REMOTE-STATE-WIDTH-31.md): Remote state file printed 51.*ld for fractional fields
- TELEPORT-XY-006 (no report page): No dbg tp X Y; map teleport could land underwater

<!-- END GENERATED CATEGORY -->
