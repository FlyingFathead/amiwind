# CONSOLE-HISTORY-EMPTY-32: Console Up past the oldest command shows an empty line and stays there

## Status: 8 October 2026

Open: fixed in source on the console-history branch, not yet packaged. Present
in every AmiWind version (inherited from Quake's `Key_Console`). Found while
investigating [CONSOLE-HISTORY-ARROWS-32](CONSOLE-HISTORY-ARROWS-32.md).

## Symptom

In the console, after a few commands:

- Pressing Up more times than there are commands shows an empty line, and
  every further Up keeps it empty; only Down brings the history back. It looks
  as if Up does nothing.
- Closing the console after walking the history and opening it again, the
  next Up continues from where the walk stopped instead of the newest command
  (seen in FS-UAE on dev1: reopened, Up showed the third-newest command).

## Where

`engine/aga/src/keys.c` (`Key_Console`, `K_UPARROW`) and
`engine/aga/src/console.c` (`Con_ToggleConsole_f`). Typing, Enter, Down, Tab
completion and Shift+Up/Down scrollback are unaffected.

## How it happened

The history is a ring of 32 lines. Up searched backwards for a non-empty line;
when it came back round to the edit line it jumped to slot `edit_line+1`, the
oldest slot of a full ring. Until all 32 slots have been used that slot is
empty, so the edit line became empty; the next Up searched from there, came
round again and landed on the same empty slot. The search position
(`history_line`) was reset only by Enter, so it survived closing and reopening
the console.

## Why it was not caught

The console history had no test.

## Reproduction

Native: `tests/aga_console_history_test.c` with the old `keys.c` fails with
`edit line ']', expected ']echo one'` at the fourth Up after three commands;
`tests/aga_console_cycle_test.c` with the old `console.c` fails because the
search position is not reset when the console opens.

## Repair

- Up searches from a copy of the position and, when there is no older
  command, keeps the oldest one on the line (nothing is lost; a full ring
  behaves as before).
- Opening or closing the console (`Con_ToggleConsole_f`, also reached by the
  F10 cycle) sets the search position to the newest command.

## Verification

Both native tests pass with the repair and fail without it. Not yet built into
an image or played.

## Prevention

`tests/aga_console_history_test.c` (native raw keys `0x4C`/`0x4D` with
qualifiers through `Key_Event`: recall order, Up past the oldest, Down back to
the empty line, Shift scrollback, re-running a recalled line, keypad digits)
and the open/close reset in `tests/aga_console_cycle_test.c`.
