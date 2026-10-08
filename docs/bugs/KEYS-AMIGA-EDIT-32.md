# KEYS-AMIGA-EDIT-32: Amiga Del arrived as F11; FS-UAE sent Home/End as keypad ( and Help

## Status: 8 October 2026

Open: fixed in source on the console-terminal branch, not yet packaged. Present
in every earlier version. The FS-UAE Insert key (below) is not changed.

## Symptom

Found while adding terminal line editing to the console:

- The Amiga Del key (raw 0x46) reached the game as F11. The controls menu,
  which documents "Delete or Backspace clears the action's keys", and anything
  else that waits for Delete never saw it.
- In FS-UAE 3.1.66 (Linux, AmiWind preset, `aw_input_trace 1`), a PC keyboard's
  Home arrives as raw 90 (0x5A, keypad `(`, qualifier 256) and End as raw 95
  (0x5F, Help, read as Pause: "PAUSE is unbound"). The Home/End actions of the
  world map, gallery, fog and audio sliders and the console therefore never
  received them in FS-UAE.
- Insert arrives as raw 43 (0x2B, the key left of Return), which the game reads
  as Enter: pressing Insert in the console runs the line.

## Where

`engine/aga/src/keys.c` (`Key_AmigaRaw`) and the FS-UAE presets
(`resources/emulators/AmiWind-v<version>-FS-UAE.fs-uae`,
`tools/AmiWind-FS-UAE-launcher.py`). WinUAE's mapping of PC Home/End/Insert
has not been measured.

## How it happened

The raw-key table put K_F11 at 0x46 (there is no F11 on an Amiga keyboard and
nothing is bound to it). Home/End were read only from raw 0x70/0x71, the codes
of PC-style Amiga keyboards; FS-UAE has no action that sends those codes and
maps the PC keys to keypad `(` and Help.

## Why it was not caught

No test or emulator run pressed Del, Home or End.

## Reproduction

FS-UAE, AmiWind dev1 preset, console, `aw_input_trace 1`, then Home, End,
Delete, Insert: raw 90/218, 95/223, 70/198, 43/171.

## Repair

- `Key_AmigaRaw`: 0x46 is K_DEL.
- FS-UAE presets: `keyboard_key_home = action_key_6a` and
  `keyboard_key_end = action_key_6c` (FS-UAE's unused-key actions, as
  already done for Page Up/Down with 0x68/0x69); `Key_AmigaRaw` reads
  0x6A/0x6C as Home/End. Raw 0x70/0x71 still work.
- Insert: not changed (0x2B as Enter is kept); documented in KEYMAPS.

## Verification

Native: `tests/aga_console_history_test.c` checks the table entries and
drives Del, Home and End through `Key_Event`; `tests/test_fsuae_keyboard_ports.py`
checks the preset lines. FS-UAE with the rebuilt engine: see the journal.

## Prevention

The two tests above.
