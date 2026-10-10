# ENGINE-MAP-NAME-OVERFLOW-35: map, changelevel, connect and load copied a name of any length into fixed buffers

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | engine/aga/src/host_cmd.c map/changelevel/connect/load; sv_main.c SV_SpawnServer |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | medium: A long typed map name or a damaged save overwrote memory after 64-byte buffers |
| Family | Console, keyboard and mouse input (`console-input`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3b72d32 |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

## Status: 10 October 2026

Fixed in source on v0.0.35-crash-fixes-2, not shipped at the time of writing.

## Symptom

None seen in play. Typing `map` or `changelevel` with a name longer than about 54 characters, `map` with
many extra words, or `connect` with a long address wrote past 64-byte buffers (`name`, `level`,
`cls.mapstring`, `sv.name`, `sv.modelname`); so did `load` of a save whose map line was long.

## Where

`engine/aga/src/host_cmd.c` (`Host_Map_f`, `Host_Changelevel_f`, `Host_Restart_f`, `Host_Connect_f`,
`Host_Loadgame_f`, the compiled-out `Host_Changelevel2_f`) and `sv_main.c` (`SV_SpawnServer`).

## How it happened

Inherited from Quake: `strcpy` and `strcat` of console arguments into `MAX_QPATH` buffers, and
`sprintf (sv.modelname, "maps/%s.bsp", server)`.

## Why it was not caught

The console accepts any text and no test typed a long name.

## Reproduction

`map` followed by 70 letters at the console.

## Repair

`SV_MapNameFits` (sv_main.c) accepts a name only when `maps/<name>.bsp` fits `MAX_QPATH`
(`SV_MAPNAME_MAX`, 54 characters) and prints "Map name too long"; `SV_SpawnServer` calls it before anything
changes, so every caller is covered. `map` and `changelevel` check it before the running game is left, and
`map` joins its extra words with a bound (`Host_JoinArgs`; "map command too long"). The remaining copies use
`COM_FormatPath`. `connect` refuses a server name that does not fit.

## Verification

`tests/test_engine_crash_paths.py`: a native fixture (AddressSanitizer) runs `SV_MapNameFits` and
`Host_JoinArgs` from the engine source at and past the limits; source checks that no console copy is
unbounded and that the checks come before the disconnect.

## Prevention

Console arguments are checked where they enter a fixed buffer; the sweep of every unbounded copy is in
[ENGINE-FATAL-PATH-SWEEP-35](ENGINE-FATAL-PATH-SWEEP-35.md).

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
- [ENGINE-LOADGAME-SYSERROR-35](ENGINE-LOADGAME-SYSERROR-35.md): A damaged Quake save stopped the program (Sys_Error) and its strings were read without a width
- [ENGINE-WRITE-OPEN-SYSERROR-35](ENGINE-WRITE-OPEN-SYSERROR-35.md): A write to a full or write-protected disk (screenshot) stopped the program
- [KEYS-AMIGA-EDIT-32](KEYS-AMIGA-EDIT-32.md): Amiga Del arrived as F11; FS-UAE sent Home/End as keypad ( and Help
- MAP-VIEW-SWITCH-28 (no report page): Mouse cannot switch DEBUG / IN-GAME map views
- VIEW-PITCH-CENTER-29 (no report page): Legacy automatic pitch centering during free-look

<!-- END GENERATED CATEGORY -->
