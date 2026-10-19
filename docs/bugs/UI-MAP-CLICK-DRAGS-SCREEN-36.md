# UI-MAP-CLICK-DRAGS-SCREEN-36: A click on the game screen with the Amiga qualifier drags the game screen down and reveals the AmigaDOS screen behind it

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.36-dev5 at 2026-10-11 14:31 +0300: maintainer: clicking in the map (M) drags AmigaDOS into view
- Reported with v0.0.36-dev5 at 2026-10-11 14:33 +0300: maintainer: right+left click combos reach the AmigaDOS screen behind the game

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 11 October 2026, in v0.0.36-dev5 |
| Where | Engine: the game screen (vid_amiga.c) and the input handler (sys_amiga.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | fixed in v0.0.36 |
| Severity | high: The game screen slides away mid-play and the AmigaDOS screen behind it takes clicks |
| Family | Console, keyboard and mouse input (`console-input`) |
| Playtest version | v0.0.36-dev5 |
| From commit | source 6c29a23, engine 6c29a23, CHIM world 6c29a23 |
| CHIM engine version | CHIM 0.1.0, engine 6c29a23, world format 0.7 |
| Build note | run 2026_10_11_v0.0.36-dev5_full-coast-arena-seyda-dev5_6c29a23 |
| Platform or emulator | FS-UAE, JIT (maintainer, dev5 playtest) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Status: 11 October 2026

Fixed on the v0.0.36 line (branch v0.0.36-thirdperson). The maintainer reported it twice from the v0.0.36-dev5 playtest
on FS-UAE: clicking and dragging in the world map pulled the AmigaDOS window into view, and right+left click
combinations reached the AmigaDOS screen behind the game.

## Symptom

During play, a click or a drag (in the world map, or right and left buttons together) moved the whole game screen
down. The AmigaDOS screen with the startup window showed above it, and clicks there went to AmigaDOS instead of the
game.

## Where

Engine: the game screen opened in `vid_amiga.c` and the input handler in `sys_amiga.c` that runs before Intuition.

## How it happened

The game opened its screen with the system default, a draggable screen; the line that turns dragging off was
commented out in the AmiQuake source it came from. Intuition drags a screen when the left mouse button is pressed
with the Amiga key held, anywhere on that screen. The Amiga qualifier did not have to be held on purpose: a program
that crashed with an Amiga key down leaves the qualifier latched (see ENGINE-CRASH-EXIT-KEYBOARD-36 on the same
line), so after an earlier crash every left click became a screen drag. The game's input handler already removed
the Amiga qualifier from the M and N keys (screen to front and back), but not from mouse events.

## Why it was not caught

Scripted runs never pressed a mouse button with a qualifier, and the screen position was not part of any check.

## Reproduction

Always, with the Amiga qualifier present during a click: on the dev5 engine and image in FS-UAE, holding left
Amiga and dragging with the left button moves the game screen down by the drag distance and shows the AmigaDOS
window above it (the scripted run's `map-amiga-drag` frame).

## Repair

The game screen opens non-draggable (`SA_Draggable FALSE`), so no button, qualifier or Intuition setting can
move it. The input handler also removes the Amiga qualifier from every mouse event while the game screen is in
front and its window is active, before Intuition sees it; the game still receives every button and movement. Other
screens, and every key, keep their qualifiers; the handler is removed on exit as before.

## Verification

Same image (the dev5 build) and the same scripted session in FS-UAE with JIT (`tools/engine_smoke.py --script`
with `xdo` mouse steps: plain drags, right+left combinations, left Amiga held during a drag, a tap of left Amiga
followed by a plain drag):

| Engine | Left Amiga + drag | Plain drag, right+left combinations |
| --- | --- | --- |
| dev5 (6c29a23) | game screen moved down, AmigaDOS window shown | screen stays |
| fixed | screen stays at the top | screen stays |

Both runs passed the boot smoke.

## Prevention

`tests/test_third_person.py` checks that the screen opens non-draggable and that the handler strips the Amiga
qualifier from mouse events before the key guard runs. `tools/engine_smoke.py` scripts now take `xdo` steps for
mouse and held-key input, so the drag sequence can be repeated on any build.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Console, keyboard and mouse input (`console-input`). The console line editor, qualifier keys and the emulator key path. See [families](README.md#families).

- AW25-04 (no report page): M/N switched to the desktop, including while typing in the console
- AW25-05 (no report page): Console typed only uppercase letters and shifted digits
- CONSOLE-CAPS-29 (no report page): FS-UAE F10 Caps Lock appears stuck
- [CONSOLE-HISTORY-ARROWS-32](CONSOLE-HISTORY-ARROWS-32.md): Console Up/Down arrows recall nothing on the maintainer's FS-UAE (Ubuntu)
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
