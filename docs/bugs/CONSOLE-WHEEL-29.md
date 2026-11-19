# CONSOLE-WHEEL-29: FS-UAE console wheel starts working then reports unbound

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 5 October 2026, in v0.0.29-dev1 |
| Where | Debug console mouse wheel scrolling (FS-UAE, WinUAE) |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.29-dev1, v0.0.29-rc1 (last seen) |
| Severity | low: Wheel ticks print unbound-key notices and break scrolling. |
| Family | Console, keyboard and mouse input (`console-input`) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-05: reported in v0.0.29-dev1
- 2026-10-05: CONSOLE-WHEEL-29: FS-UAE wheel stops scrolling console (OPEN): Reported 5 October 2026 at 12:08:51 Europe/Helsinki in v0.0.29-dev1 on FS-UAE; screenshot at 12:08:55 shows repeated `MWHEELUP is unbound, hit F4 to set.` The maintainer ...
- 2026-10-06: Current RC1 regression checkpoint: Delivered playtest remains v0.0.29-rc1.
- 2026-10-06: Post-RC1 combined gate: The next candidate passes 1,046 Linux Docker checks, zero failures/errors, and four documented skips: three Windows-only checks and the JavaScript inspector check requiring Node.js.
- 2026-10-06: CONSOLE-WHEEL-29: scroll limits trigger unbound-message feedback: Recorded 2026-10-06T13:48:58+00:00; the maintainer report: v0.0.29-rc1 and earlier versions, WinUAE, F10 debug console.
- 2026-10-06: Current RC1 regression checkpoint: Consolidated RC1 reports, coordinates and scoped positive observations: RC1 playtest ledger (docs/history/feedback/RC1_PLAYTEST_LEDGER.md).

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
- [ENGINE-CBUF-OVERFLOW-35](ENGINE-CBUF-OVERFLOW-35.md): Command text larger than the command buffer or a line over 1023 characters overflowed
- [ENGINE-COM-TOKEN-UNBOUNDED-35](ENGINE-COM-TOKEN-UNBOUNDED-35.md): COM_Parse wrote tokens of any length into the 1 KiB com_token
- [ENGINE-LOADGAME-SYSERROR-35](ENGINE-LOADGAME-SYSERROR-35.md): A damaged Quake save stopped the program (Sys_Error) and its strings were read without a width
- [ENGINE-MAP-NAME-OVERFLOW-35](ENGINE-MAP-NAME-OVERFLOW-35.md): map, changelevel, connect and load copied a name of any length into fixed buffers
- [ENGINE-WRITE-OPEN-SYSERROR-35](ENGINE-WRITE-OPEN-SYSERROR-35.md): A write to a full or write-protected disk (screenshot) stopped the program
- [KEYS-AMIGA-EDIT-32](KEYS-AMIGA-EDIT-32.md): Amiga Del arrived as F11; FS-UAE sent Home/End as keypad ( and Help
- [MAP-VIEW-SWITCH-28](MAP-VIEW-SWITCH-28.md): Mouse cannot switch DEBUG / IN-GAME map views
- [UI-MAP-CLICK-DRAGS-SCREEN-36](UI-MAP-CLICK-DRAGS-SCREEN-36.md): A click on the game screen with the Amiga qualifier (held, or latched by a crashed program) drags the game screen down and reveals the AmigaDOS screen behind it
- [VIEW-PITCH-CENTER-29](VIEW-PITCH-CENTER-29.md): Legacy automatic pitch centering during free-look

<!-- END GENERATED CATEGORY -->
