# ENGINE-LOADGAME-SYSERROR-35: A damaged Quake save stopped the program (Sys_Error) and its strings were read without a width

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | engine/aga/src/host_cmd.c Host_Loadgame_f |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | low: Console load of a damaged .sav crashed the game or overran a buffer |
| Family | Console, keyboard and mouse input (`console-input`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3b72d32 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on v0.0.35-crash-fixes-2, not shipped at the time of writing.

## Symptom

None seen in play: AmiWind's own saves use their own format and menu. The console's Quake `load` command read
a `.sav` with `fscanf ("%s")` into a 64-byte map name and a 32 KiB line, stopped the program with `Sys_Error` on
an entity block that did not fit or did not start with a brace, and wrote edicts past `MAX_EDICTS` for a save
with too many.

## Where

`engine/aga/src/host_cmd.c` `Host_Loadgame_f`.

## How it happened

Inherited from Quake.

## Why it was not caught

No test loads a damaged save through the console.

## Reproduction

`load` of a hand-edited save with a long map line or a stray token.

## Repair

Every `%s` read has a width (`%63s` for the map name, `%32767s` for the lines); the map name goes through
`SV_MapNameFits`; a damaged entity block or too many entities close the file and end the session with a
Host_Error ("damaged save") instead of stopping the program.

## Verification

`tests/test_engine_crash_paths.py` (source checks: widths, no Sys_Error in the load path, the entity bound).

## Prevention

Save data is checked where it is read; the sweep is in [ENGINE-FATAL-PATH-SWEEP-35](ENGINE-FATAL-PATH-SWEEP-35.md).

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
- [ENGINE-COM-TOKEN-UNBOUNDED-35](ENGINE-COM-TOKEN-UNBOUNDED-35.md): COM_Parse wrote tokens of any length into the 1 KiB com_token
- [ENGINE-MAP-NAME-OVERFLOW-35](ENGINE-MAP-NAME-OVERFLOW-35.md): map, changelevel, connect and load copied a name of any length into fixed buffers
- [ENGINE-WRITE-OPEN-SYSERROR-35](ENGINE-WRITE-OPEN-SYSERROR-35.md): A write to a full or write-protected disk (screenshot) stopped the program
- [KEYS-AMIGA-EDIT-32](KEYS-AMIGA-EDIT-32.md): Amiga Del arrived as F11; FS-UAE sent Home/End as keypad ( and Help
- MAP-VIEW-SWITCH-28 (no report page): Mouse cannot switch DEBUG / IN-GAME map views
- VIEW-PITCH-CENTER-29 (no report page): Legacy automatic pitch centering during free-look

<!-- END GENERATED CATEGORY -->
