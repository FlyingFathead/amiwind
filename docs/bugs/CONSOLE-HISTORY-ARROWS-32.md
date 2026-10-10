# CONSOLE-HISTORY-ARROWS-32: Console Up/Down arrows recall nothing on the owner's FS-UAE (Ubuntu)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 8 October 2026, in v0.0.32-dev1 |
| Where | Console Up/Down history on the owner's FS-UAE (Ubuntu) |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.32-dev1 (last seen) |
| Severity | low: Console history recall seems dead for one owner setup; not reproduced. |
| Family | Console, keyboard and mouse input (`console-input`) |
| Playtest version | v0.0.32-dev1 |
| From commit | source and engine 978475d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

<!-- contents start -->
## Contents

- [Status: 8 October 2026](#status-8-october-2026)
- [Symptom](#symptom)
- [Where](#where)
- [How it happened](#how-it-happened)
- [Why it was not caught](#why-it-was-not-caught)
- [Reproduction](#reproduction)
- [Repair](#repair)
- [Verification](#verification)
- [Prevention](#prevention)
- [Bugs in the same category](#bugs-in-the-same-category)

<!-- contents end -->

## Status: 8 October 2026

Open. Reported on v0.0.32-dev1. The arrows reach the game on the owner's
machine; the most likely cause is the engine defect
[CONSOLE-HISTORY-EMPTY-32](CONSOLE-HISTORY-EMPTY-32.md), fixed in source and
not yet in a build the owner has played.

## Symptom

Owner, v0.0.32-dev1, FS-UAE on Ubuntu 24.04 with a real keyboard: in the
console, the Up and Down arrows do nothing (no history recall, nothing else
visible). Keypad 8 and 2 type digits with Num Lock on or off. The owner
remembers the history working a few versions earlier, when playing in WinUAE.

## Where

Unknown. Candidates: the emulator or host input path (the arrows never reach
the Amiga as raw keys), or a console state not covered below.

Ruled out by reading and by test:

- The engine's key path is unchanged since v0.0.31: `keys.c`, `in_amiga.c`,
  `sys_amiga.c` and `vid_amiga.c` are identical between v0.0.31 and the dev1
  source; `console.c` differs only by the REMOTE-CONSOLE-APPEND-31 seek.
- The shipped FS-UAE preset and both launchers are identical between v0.0.31
  and dev1 apart from the version and image name; the preset sets
  `joystick_port_1 = none` (no keyboard joystick) and maps only Page Up and
  Page Down.
- The Amiga keypad has no cursor keys: raw `0x3E` and `0x1E` are the digits 8
  and 2 in every version, so keypad digits are expected.

## How it happened

Not proven. The owner's `aw_input_trace 1` on dev1 (FS-UAE, mouse grabbed)
shows the keys arriving: `Input raw 77 qualifier 32768` / `205` for Down and
`76` / `204` for Up, after the `196` release of the Return that enabled the
trace. Qualifier 32768 is `IEQUALIFIER_RELATIVEMOUSE`; the engine reads only
the Shift, Caps Lock, Ctrl and Alt bits, so it does not change the key.

With the code in dev1, one Up too many (more Ups than commands typed in this
session) leaves an empty line, and from then on every Up stays empty, also
after closing and reopening the console, until a command is entered
(CONSOLE-HISTORY-EMPTY-32). With a few commands and a quick double Up this
looks exactly like "the arrows do nothing".

A keyboard joystick gives the same complaint by another route: with
`joystick_port_1 = keyboard`, or the line missing (FS-UAE's `auto` then falls
back to keyboard emulation), FS-UAE uses the cursor keys and Right Ctrl/Right
Alt as the joystick and the game never sees them (no trace line). The owner's
trace rules this out for his machine.

## Why it was not caught

The console history had no test; the dev1 smoke route did not press the
arrows in the console.

## Reproduction

Tried on 8 October 2026 in FS-UAE 3.1.66 on Linux (Docker, Xvfb, keys sent
through the X server), JIT on, fresh writable copies of the delivered dev1
disks:

- With the exact preset the playtest launcher writes (template plus ROM and
  disks): main-menu console, `aw_input_trace 1`, `echo alpha`, Up, Up:
  `Input raw 76 qualifier 0` and `204` (release) are logged, and the line
  shows `aw_input_trace 1`, then `echo alpha`.
- In the ship after a new game and in Vivec Arena after `dbg tp vivec_arena`,
  half and full console: Up recalls the last and the previous command.
- The dev2 smoke test (same emulator) also recalled history with Up and Down.

Second round, same day:

- The owner's key order (Return, Down x4 with one repeated press, Up, Down)
  with qualifier 32768, made by clicking into the window and moving the mouse
  first: the trace matches the owner's line for line, and Up recalls the last
  command.
- Same disks with the FS-UAE preset changed, one change each: without the
  `joystick_port_1` line (log: `configuring joystick port 1 (auto)`, `could
  not auto-configure joystick,using keyboard emulation`) and with
  `joystick_port_1 = keyboard`: Up and Down produce no trace line and the
  line stays empty. The FS-UAE F12 menu then shows `[J] KEYBOARD` under
  Input options instead of `[X] NO HOST DEVICE`.
- A `Host.fs-uae` with `joystick_port_1 = keyboard` next to the shipped
  preset: the log marks it `(ignored)`; the preset's `none` wins.

Seen on the way: closing the console after a history walk
and reopening it continued the walk from where it stopped, and Up past the
oldest command showed an empty line that stayed empty; both are
[CONSOLE-HISTORY-EMPTY-32](CONSOLE-HISTORY-EMPTY-32.md).

## Repair

The engine repair is CONSOLE-HISTORY-EMPTY-32 (Up keeps the oldest command;
each opening of the console starts from the newest). Nothing else changed for
this report. Diagnostic already in the engine (see [KEYMAPS](../KEYMAPS.md)):
in the console, `aw_input_trace 1`, press Up and Down, then
`aw_input_trace 0`.

- `Input raw 76` (Up) and `Input raw 77` (Down) lines appear: the keys reach
  the game; report the qualifier numbers and what the edit line shows.
- No such line: the emulator or host takes the arrows before the Amiga sees
  them. Check the FS-UAE version, that the game was started with the AmiWind
  preset (`RUN-FS-UAE.sh` or the launcher), and that no FS-UAE host settings
  file or FS-UAE Launcher input setting puts a keyboard joystick (cursor keys)
  on a joystick port.

## Verification

Owner trace received (keys arrive). Pending: the owner checks Up and Down on
the next build that contains the CONSOLE-HISTORY-EMPTY-32 repair.

## Prevention

`tests/aga_console_history_test.c` drives Up and Down as native raw keys and
qualifiers through `Key_Event` into the console history, with the default
`+forward`/`+back` bindings on the arrows, and replays the owner's trace
with qualifier 32768. `tests/test_fsuae_keyboard_ports.py` keeps
`joystick_port_1 = none` in every shipped FS-UAE configuration.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Console, keyboard and mouse input (`console-input`). The console line editor, qualifier keys and the emulator key path. See [families](README.md#families).

- AW25-04 (no report page): M/N switched to the desktop, including while typing in the console
- AW25-05 (no report page): Console typed only uppercase letters and shifted digits
- CONSOLE-CAPS-29 (no report page): FS-UAE F10 Caps Lock appears stuck
- [CONSOLE-HISTORY-EMPTY-32](CONSOLE-HISTORY-EMPTY-32.md): Console Up past the oldest command shows an empty line and stays there
- CONSOLE-WHEEL-29 (no report page): FS-UAE console wheel starts working then reports unbound
- [ENGINE-CBUF-OVERFLOW-35](ENGINE-CBUF-OVERFLOW-35.md): Command text larger than the command buffer or a line over 1023 characters overflowed
- [ENGINE-COM-TOKEN-UNBOUNDED-35](ENGINE-COM-TOKEN-UNBOUNDED-35.md): COM_Parse wrote tokens of any length into the 1 KiB com_token
- [ENGINE-LOADGAME-SYSERROR-35](ENGINE-LOADGAME-SYSERROR-35.md): A damaged Quake save stopped the program (Sys_Error) and its strings were read without a width
- [ENGINE-MAP-NAME-OVERFLOW-35](ENGINE-MAP-NAME-OVERFLOW-35.md): map, changelevel, connect and load copied a name of any length into fixed buffers
- [ENGINE-WRITE-OPEN-SYSERROR-35](ENGINE-WRITE-OPEN-SYSERROR-35.md): A write to a full or write-protected disk (screenshot) stopped the program
- [KEYS-AMIGA-EDIT-32](KEYS-AMIGA-EDIT-32.md): Amiga Del arrived as F11; FS-UAE sent Home/End as keypad ( and Help
- MAP-VIEW-SWITCH-28 (no report page): Mouse cannot switch DEBUG / IN-GAME map views
- VIEW-PITCH-CENTER-29 (no report page): Legacy automatic pitch centering during free-look

<!-- END GENERATED CATEGORY -->
