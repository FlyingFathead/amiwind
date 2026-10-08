# EMULATOR-TEMPLATES-WORLD-32: The static emulator templates list only the boot disk, not the world disk

## Status: 8 October 2026

Open. Present in v0.0.31 and v0.0.32-dev1. Found in the v0.0.32-dev1 delivery checks.

## Symptom

The static templates in `resources/emulators/` do not include the world disk: the `.fs-uae` file
names only the boot hard disk image, and the WinUAE `.uae` file names no hard disk and asks the
player to select the boot image. A player who starts from a template
instead of a launcher gets no world partitions. The launchers add the world disk correctly.

## Where

`resources/emulators/AmiWind-<version>-FS-UAE.fs-uae`, `AmiWind-<version>-WinUAE.uae` and their
generator (`tools/emulator_configs.py`).

## How it happened

The templates were written for the single-disk layout and not updated when the world moved to its
own drive.

## Why it was not caught

Smoke tests use the launchers, never the templates.

## Reproduction

Read the dev1 templates: the FS-UAE one has one hard drive entry (the boot image), the WinUAE one
none.

## Repair

Not yet: generate the templates from the same drive list the launchers use (boot and world disks,
every partition), or remove them in favour of the launchers.

## Verification

Pending: boot from each template in FS-UAE and WinUAE and check every partition is mounted.

## Prevention

A test that the templates and the launchers list the same drives.
