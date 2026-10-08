# BUILD-EDITION-SKY-32: Night sky and sky palette outputs depend on the Morrowind edition (loose .tga read before archive .dds)

## Status: 8 October 2026

Open. Found by the GOG/Steam loose-file A/B (measured on both installations, no repository change).

## Symptom

`build_night_sky.py` reads loose `.tga` before the archive `.dds`: GOG uses 22 loose star and moon
images, Steam the `Morrowind.bsa` copies. `gfx/aw_night_sky.lmp` differs in 1,956 of 27,664 bytes
and `gfx/night-sky.json` records the different hash. `prepare_shared_sky_assets.py` does the same
for clouds: the pixels are identical, but `gfx/sky-palette-bank.json` names and hashes a different
source file.

## Where

`tools/build_night_sky.py` (`owned_images`), `tools/prepare_shared_sky_assets.py` (`owned_clouds`).

## How it happened

The loose originals were preferred when only GOG data was used.

## Why it was not caught

Only one edition was ever built.

## Reproduction

Build the sky assets from a GOG and a Steam installation and compare `gfx/`.

## Repair

Not yet: read what the game reads (archive `.dds` first, in archive order), or record the
choice per edition; markers name the logical asset, not the edition's file.

## Verification

Pending.

## Prevention

Edition A/B of the builder outputs in the from-scratch check.
