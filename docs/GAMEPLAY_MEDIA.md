# Gameplay media — v0.0.23-dev2

Captured on 29 September 2026 from the actual compiled 68040 Amiga runtime in
FS-UAE 3.1.66, using the unchanged A1200/AGA/PAL/2 MiB Chip/16 MiB Z3/JIT profile.
The no-TTF converted input was used. The final checkpoint retains the captured
geometry and characters; later changes restored ship-wave gain and increased
surface/edge capacity after a different port viewpoint exposed overflow.

The four PNGs are 592 × 372 crops of the emulator display, including the game
HUD. No colour/brightness adjustment or generated content was applied. The port
and Fargoth views use the debug free camera. The Tradehouse view follows an actual
front-door activation. The prison view shows the name prompt after the movie.
The seven-second GIF is an actual in-engine port camera pan, captured at 10 fps
and reduced to 444 pixels wide / 8 fps with a 128-colour GIF palette. It has no
audio and is not a performance benchmark.

Only these exact paths are public media exceptions in `.gitignore` and
`tools/release.py`; other game images, audio, converted assets and ROMs stay out of
source archives. The release check verifies signatures and size limits (1 MiB
per screenshot, 4 MiB for the selected GIF).

## v0.0.23-dev3 captures — 29 September 2026

The README ship dialogue and corrected port hill are native FS-UAE captures from
dev3, cropped to the same 592×372 game area. Existing Tradehouse/Fargoth images
and the port pan retain their dev2 attribution. The before/after rock views in
WHAT_ARE_ROCKS.md use the same reported camera. None is generated or composited.
Only explicitly named promotional PNGs are exceptions to the global image ignore
and public source allowlist; private reference images remain excluded.
