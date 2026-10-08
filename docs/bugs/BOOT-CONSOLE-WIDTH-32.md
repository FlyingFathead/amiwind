# BOOT-CONSOLE-WIDTH-32: Boot check lines wrap on the 64-column boot console

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
