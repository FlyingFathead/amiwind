# BOOT-CONSOLE-WIDTH-32: Boot check lines wrap on the 64-column boot console

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 8 October 2026, in v0.0.32-dev |
| Where | Boot check text (engine/aga/boot/bootcheck.asm) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.32-dev (last seen) |
| Severity | low: Cosmetic: boot lines and countdown wrap on a 64-column console. |
| Family | Boot and engine start-up (`boot-startup`) |

<!-- END GENERATED FACTS -->

## Status: 8 October 2026

Open. Found by the FPU support library work (FS-UAE, Kickstart 3.1, JIT off). Cosmetic.

## Symptom

The Chip and Fast RAM lines wrap, and the countdown "Continuing in N seconds..." wraps so each
update lands on a new line instead of overwriting the last.

## Where

`engine/aga/boot/bootcheck.asm` (line texts).

## How it happened

Lines written for a wider console.

## Why it was not caught

Checked in a wider emulator window.

## Reproduction

Boot and read the checklist.

## Repair

Fixed in source (v0.0.32-dev): every checklist line shortened to fit 63 columns (the RAM
lines now read "Chip RAM: 2048K, free 1724, max 1701 [x] OK"; the countdown reads
"SPACE or ENTER = start now.   Starting in 5 s..." and overwrites itself on one row).

## Verification

`tests/test_boot_console_width.py` checks every boot line at its widest values (6-digit
KiB counts, 27-character names) against 63 columns, and that the countdown fits one row.
Not yet seen in the emulator.

## Prevention

A column-width check in the boot-check tests.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Boot and engine start-up (`boot-startup`). The boot check and engine start-up report problems clearly and never stop the game silently. See [families](README.md#families).

- [BOOT-68060-FPU-FAIL-32](BOOT-68060-FPU-FAIL-32.md): On a 68060 with Kickstart 3.1 and no 68060.library the boot check fails the FPU line and stops
- [BOOT-VOLUME-NOT-VALIDATED-33](BOOT-VOLUME-NOT-VALIDATED-33.md): At boot AmigaOS asks Volume AMIWIND is not validated (Retry/Cancel) while the game starts
- CFG-01 (no report page): Semicolons in default-config comments ran as console commands
- CONFIG-COMMENT-29 (no report page): Semicolons split default-config comments into commands
- CRASH-REPORT-02 (no report page): Fatal engine exit returned to AmigaDOS without a visible reason
- [ENGINE-ARGS-32](ENGINE-ARGS-32.md): The C start-up passes no arguments from the boot shell
- [ENGINE-STACK-UNCHECKED-35](ENGINE-STACK-UNCHECKED-35.md): The engine never checked the stack it was started with; the pak directory alone needs 128 KiB
- [MINIWIND-NO-WINUAE-PROFILE-33](MINIWIND-NO-WINUAE-PROFILE-33.md): MiniWind playtest packages ship only an FS-UAE profile: no WinUAE profile and no launcher
- [NET-UDP-INIT-CRASH-32](NET-UDP-INIT-CRASH-32.md): UDP network start-up can stop the game at boot when bsdsocket.library is present

<!-- END GENERATED CATEGORY -->
