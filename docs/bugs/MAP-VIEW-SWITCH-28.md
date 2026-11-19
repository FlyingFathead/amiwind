# MAP-VIEW-SWITCH-28: Mouse cannot switch DEBUG / IN-GAME map views

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | unknown |
| First noticed | unknown |
| Where | DEBUG / IN-GAME map view overlay, mouse switching |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | unknown |
| Severity | low: Mouse cannot switch map views; keyboard unaffected. |
| Family | Console, keyboard and mouse input (`console-input`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-05: MAP-VIEW-SWITCH-28: mouse cannot switch map views (OPEN) (part 1 of 3): 5 October v0.0.29-dev1 input-path candidate: the native event loop overwrote earlier relative mouse deltas and deferred their delivery until `IN_Move`, while mouse ...
- 2026-10-05: MAP-VIEW-SWITCH-28: mouse cannot switch map views (OPEN) (part 2 of 3): A controlled emulator input trace requested a six-pixel upward host movement but delivered two guest deltas of (+122,+122).
- 2026-10-05: MAP-VIEW-SWITCH-28: mouse cannot switch map views (OPEN) (part 3 of 3): Reproduction to verify: open the map and click DEBUG, then IN-GAME; record pointer position and whether the active view/highlight changes.

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Console, keyboard and mouse input (`console-input`). The console line editor, qualifier keys and the emulator key path. See [families](README.md#families).

- AW25-04 (no report page): M/N switched to the desktop, including while typing in the console
- [AW25-05](AW25-05.md): Console typed only uppercase letters and shifted digits
- CONSOLE-CAPS-29 (no report page): FS-UAE F10 Caps Lock appears stuck
- [CONSOLE-HISTORY-ARROWS-32](CONSOLE-HISTORY-ARROWS-32.md): Console Up/Down arrows recall nothing on the maintainer's FS-UAE (Ubuntu)
- [CONSOLE-HISTORY-EMPTY-32](CONSOLE-HISTORY-EMPTY-32.md): Console Up past the oldest command shows an empty line and stays there
- [CONSOLE-QUEST-READS-MISSING-64](CONSOLE-QUEST-READS-MISSING-64.md): The console does not take the original journal and faction commands, so quest endings and expulsion cannot be read back
- [CONSOLE-WHEEL-29](CONSOLE-WHEEL-29.md): FS-UAE console wheel starts working then reports unbound
- [ENGINE-CBUF-OVERFLOW-35](ENGINE-CBUF-OVERFLOW-35.md): Command text larger than the command buffer or a line over 1023 characters overflowed
- [ENGINE-COM-TOKEN-UNBOUNDED-35](ENGINE-COM-TOKEN-UNBOUNDED-35.md): COM_Parse wrote tokens of any length into the 1 KiB com_token
- [ENGINE-LOADGAME-SYSERROR-35](ENGINE-LOADGAME-SYSERROR-35.md): A damaged Quake save stopped the program (Sys_Error) and its strings were read without a width
- [ENGINE-MAP-NAME-OVERFLOW-35](ENGINE-MAP-NAME-OVERFLOW-35.md): map, changelevel, connect and load copied a name of any length into fixed buffers
- [ENGINE-WRITE-OPEN-SYSERROR-35](ENGINE-WRITE-OPEN-SYSERROR-35.md): A write to a full or write-protected disk (screenshot) stopped the program
- [KEYS-AMIGA-EDIT-32](KEYS-AMIGA-EDIT-32.md): Amiga Del arrived as F11; FS-UAE sent Home/End as keypad ( and Help
- [UI-MAP-CLICK-DRAGS-SCREEN-36](UI-MAP-CLICK-DRAGS-SCREEN-36.md): A click on the game screen with the Amiga qualifier (held, or latched by a crashed program) drags the game screen down and reveals the AmigaDOS screen behind it
- [VIEW-PITCH-CENTER-29](VIEW-PITCH-CENTER-29.md): Legacy automatic pitch centering during free-look

<!-- END GENERATED CATEGORY -->
