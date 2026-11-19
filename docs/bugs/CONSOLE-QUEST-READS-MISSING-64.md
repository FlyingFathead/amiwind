# CONSOLE-QUEST-READS-MISSING-64: The console does not take the original journal and faction commands, so quest endings and expulsion cannot be read back

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 11 November 2026, in v0.0.64-dev4 |
| Where | the console command table and the dbg mwscript call list |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.64-dev4 (last seen) |
| Severity | medium: Quest and faction states can be set through the scripting call route, but not read back, so the in-game checks of quest endings and expulsion cannot be measured |
| Family | Console, keyboard and mouse input (`console-input`) |
| Playtest version | v0.0.64-dev4 |
| From commit | source unknown, engine unknown, CHIM world unknown |
| CHIM engine version | CHIM 0.2.2, engine unknown, world format 0.11 |
| Unknown because | the build receipt does not record source commit, engine commit, world commit |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Console, keyboard and mouse input (`console-input`). The console line editor, qualifier keys and the emulator key path. See [families](README.md#families).

- AW25-04 (no report page): M/N switched to the desktop, including while typing in the console
- [AW25-05](AW25-05.md): Console typed only uppercase letters and shifted digits
- CONSOLE-CAPS-29 (no report page): FS-UAE F10 Caps Lock appears stuck
- [CONSOLE-HISTORY-ARROWS-32](CONSOLE-HISTORY-ARROWS-32.md): Console Up/Down arrows recall nothing on the maintainer's FS-UAE (Ubuntu)
- [CONSOLE-HISTORY-EMPTY-32](CONSOLE-HISTORY-EMPTY-32.md): Console Up past the oldest command shows an empty line and stays there
- [CONSOLE-WHEEL-29](CONSOLE-WHEEL-29.md): FS-UAE console wheel starts working then reports unbound
- [ENGINE-CBUF-OVERFLOW-35](ENGINE-CBUF-OVERFLOW-35.md): Command text larger than the command buffer or a line over 1023 characters overflowed
- [ENGINE-COM-TOKEN-UNBOUNDED-35](ENGINE-COM-TOKEN-UNBOUNDED-35.md): COM_Parse wrote tokens of any length into the 1 KiB com_token
- [ENGINE-LOADGAME-SYSERROR-35](ENGINE-LOADGAME-SYSERROR-35.md): A damaged Quake save stopped the program (Sys_Error) and its strings were read without a width
- [ENGINE-MAP-NAME-OVERFLOW-35](ENGINE-MAP-NAME-OVERFLOW-35.md): map, changelevel, connect and load copied a name of any length into fixed buffers
- [ENGINE-WRITE-OPEN-SYSERROR-35](ENGINE-WRITE-OPEN-SYSERROR-35.md): A write to a full or write-protected disk (screenshot) stopped the program
- [KEYS-AMIGA-EDIT-32](KEYS-AMIGA-EDIT-32.md): Amiga Del arrived as F11; FS-UAE sent Home/End as keypad ( and Help
- [MAP-VIEW-SWITCH-28](MAP-VIEW-SWITCH-28.md): Mouse cannot switch DEBUG / IN-GAME map views
- [UI-MAP-CLICK-DRAGS-SCREEN-36](UI-MAP-CLICK-DRAGS-SCREEN-36.md): A click on the game screen with the Amiga qualifier (held, or latched by a crashed program) drags the game screen down and reveals the AmigaDOS screen behind it
- [VIEW-PITCH-CENTER-29](VIEW-PITCH-CENTER-29.md): Legacy automatic pitch centering during free-look

Related bugs in other categories:

- [FACTION-STATS-PAGE-64](FACTION-STATS-PAGE-64.md): The stats page shows no factions, ranks, reputation or bounty

<!-- END GENERATED CATEGORY -->
