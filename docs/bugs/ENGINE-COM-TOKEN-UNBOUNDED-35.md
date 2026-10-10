# ENGINE-COM-TOKEN-UNBOUNDED-35: COM_Parse wrote tokens of any length into the 1 KiB com_token

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | engine/aga/src/common.c COM_Parse |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | medium: A token over 1023 characters (map entity text, config, save) overwrote memory after com_token |
| Family | Console, keyboard and mouse input (`console-input`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 6dcb10e |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on v0.0.35-crash-fixes-2, not shipped at the time of writing.

## Symptom

None seen in play. `COM_Parse` copied quoted strings and words into the global `com_token[1024]` with no length check.

## Where

`engine/aga/src/common.c COM_Parse`.

## How it happened

Inherited from Quake.

## Why it was not caught

Found by the fatal-path sweep of the engine (see [ENGINE-FATAL-PATH-SWEEP-35](ENGINE-FATAL-PATH-SWEEP-35.md)); no test fed this path bad or unusual input.

## Reproduction

A config, save or entity value of more than 1023 characters.

## Repair

Tokens are cut at the buffer; the input is still consumed to its end, so the next token starts where it did. The render-range metadata keeps its own reader.

## Verification

`tests/test_engine_crash_paths.py`: native fixture: a 3,000-character word and quoted string come back as 1,023 characters.

## Prevention

Every fatal path that data or a player can reach is in the sweep table, fixed or left with a reason.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Console, keyboard and mouse input (`console-input`). The console line editor, qualifier keys and the emulator key path. See [families](README.md#families).

- AW25-04 (no report page): M/N switched to the desktop, including while typing in the console
- AW25-05 (no report page): Console typed only uppercase letters and shifted digits
- CONSOLE-CAPS-29 (no report page): FS-UAE F10 Caps Lock appears stuck
- [CONSOLE-HISTORY-ARROWS-32](CONSOLE-HISTORY-ARROWS-32.md): Console Up/Down arrows recall nothing on the owner's FS-UAE (Ubuntu)
- [CONSOLE-HISTORY-EMPTY-32](CONSOLE-HISTORY-EMPTY-32.md): Console Up past the oldest command shows an empty line and stays there
- CONSOLE-WHEEL-29 (no report page): FS-UAE console wheel starts working then reports unbound
- [ENGINE-CBUF-OVERFLOW-35](ENGINE-CBUF-OVERFLOW-35.md): Command text larger than the command buffer or a line over 1023 characters overflowed
- [ENGINE-LOADGAME-SYSERROR-35](ENGINE-LOADGAME-SYSERROR-35.md): A damaged Quake save stopped the program (Sys_Error) and its strings were read without a width
- [ENGINE-MAP-NAME-OVERFLOW-35](ENGINE-MAP-NAME-OVERFLOW-35.md): map, changelevel, connect and load copied a name of any length into fixed buffers
- [ENGINE-WRITE-OPEN-SYSERROR-35](ENGINE-WRITE-OPEN-SYSERROR-35.md): A write to a full or write-protected disk (screenshot) stopped the program
- [KEYS-AMIGA-EDIT-32](KEYS-AMIGA-EDIT-32.md): Amiga Del arrived as F11; FS-UAE sent Home/End as keypad ( and Help
- MAP-VIEW-SWITCH-28 (no report page): Mouse cannot switch DEBUG / IN-GAME map views
- VIEW-PITCH-CENTER-29 (no report page): Legacy automatic pitch centering during free-look

<!-- END GENERATED CATEGORY -->
