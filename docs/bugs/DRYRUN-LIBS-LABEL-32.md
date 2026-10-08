# DRYRUN-LIBS-LABEL-32: A dry-run image built with --amiga-libs still says it contains no game assets or ROMs only

## Status: 8 October 2026

Open. Found by the FPU support library work (FS-UAE, Kickstart 3.1, JIT off).

## Symptom

With `--amiga-libs`, the dry-run image contains the user's own FPU support library, but its
receipt and on-screen text still describe it as containing no game assets or ROMs.

## Where

`tools/build_dry_run.py` receipt and boot text.

## How it happened

The text predates the option.

## Why it was not caught

New option.

## Reproduction

Build a dry run with --amiga-libs.

## Repair

State in the receipt and text that user-supplied system libraries are included.

## Verification

Pending.

## Prevention

Test on the receipt text with the option.
