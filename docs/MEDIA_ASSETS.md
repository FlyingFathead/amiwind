# Project media

`resources/media/AmiWind_logo.png` is the AmiWind logo: the gold AmiWind name
under the line "An open-source RPG engine for the Commodore Amiga", on a
transparent background. It is the project's own logo, supplied by FlyingFathead
on 8 October 2026, and is stored exactly as supplied. The README shows it at a
reduced display width; the stored PNG is not resampled or replaced.

Dimensions: 2172 × 724 pixels, 8-bit RGBA.

SHA-256: `9863d887449616ac0ba9780a4a55a0e40af4d38eefe89a872d3256f4e080b261`.

These named project assets are included in the public source allowlist.
Converted Morrowind artwork, fonts, audio, movies and ROMs remain private build
inputs.

## Name-only logo and wordmark

`resources/media/AmiWind_logo_name_only.png` is the gold AmiWind name, framed
tightly around the letters. It heads the [AmiWind Toolkit](AMIWIND_TOOLKIT.md).

Dimensions: 1813 × 309 pixels.

SHA-256: `3b20caefa58d8bd1056a71acba1413de8525ab35ac29005729a0b35f27f6f346`.

`resources/media/AmiWind_wordmark.png` is the gold AmiWind name under the line.
The image builder uses it for the startup screen and the menu logo.

## In the game

The image builder makes a private startup stream from the wordmark: fade
in from black, brief hold, fade out, with the two lines "An open-source RPG
engine" and "for the Commodore Amiga" drawn below it. Esc goes to the main menu.
A separately scaled copy of the wordmark is composited into the upper
menu during image creation; no extra runtime overlay buffer is needed. The PNGs
in `resources/media/` remain the reusable masters.

## Use in media

The AmiWind logos in `resources/media/` are free to use in media about AmiWind:
articles, reviews, videos, streams and magazine coverage.
