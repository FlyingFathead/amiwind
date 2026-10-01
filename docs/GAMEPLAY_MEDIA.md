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

## v0.0.23-dev4 captures — 29 September 2026

New README Darvame and Jiub screenshots are native TTF-playtest captures, cropped
only to the game display. The restored-tree capture records the reported camera
`-71 -429 38 / 262 / -7`. Existing Fargoth, Tradehouse and port GIF remain dev2.
The screenshot exceptions are exact filenames; all other generated/owned media
remain excluded. No generated imagery, brightness changes or compositing.

## v0.0.24-rc1 captures — 30 September 2026

The README and RC notes show native Balmora exterior and Mages Guild frames
captured from a writable copy of the matching production HDF. The production
binary hash is verified against the package. Diagnostic free-camera placement
is used for reproducible composition; images are not traversal proof.

PNG conversion preserves the native screenshot pixels, with no generated
content, compositing, colour or brightness adjustment. Dark interior lighting
is the current renderer's output. Only the two exact RC1 PNG paths are added
to the public media allowlist; raw captures and other game assets stay private.
The final stable release must keep verified screenshots near its release info
under the logo, at the top of Current state of the project.

## v0.0.24-rc2 captures — 1 October 2026

Three 320×200 PNGs preserve native screenshot pixels from the final RC2 production
executable in Linux FS-UAE, using the stated A1200/AGA/PAL 68040/FPU/JIT profile.
They show the Balmora bridge, the western street/guard and the eastern riverfront.
Diagnostic camera origins/yaw/pitch are `214,-480,115 / 125 / 5`,
`-495,-501,142 / 89 / -4`, and `232,282,80 / 223 / 4`. These are composition
positions, not proof of natural walking to those locations. No brightness, colour
or content alterations were made. The directory-backed capture run checks the
same binary and content later written to the HDF; the packaged-image boot check
is a separate receipt. Raw captures and diagnostic views stay private.

## RC3 captures — 1 October 2026

The RC3 release adds a close gallery view of Dagoth Ur and a Balmora street
view after the focused city-centre walking test. Both are native 320x200 FS-UAE
captures from the RC3 engine, without colour correction or compositing. Debug
camera placement is used; the gallery uses its documented steady daylight.
The mask view enables the byte-specific geometry allowance. These document
appearance and a tested view, not unrestricted gameplay acceptance.

## RC4 island map and journal

The RC4 map and journal images are native 320 by 200 UI captures shown at integer
2x scale. The images come from the final writable-copy HDF run; native pixels are
scaled by nearest-neighbour sampling without an emulator border. No colour
adjustment, compositing or invented map/journal artwork is applied. The player
is the debug Hors character in Balmora; the journal text is the actual opening
entry granted by the existing captain-duty state transaction. The map depicts
terrain coverage, not a claim that all shown land is already playable.

## v0.0.24 final release captures - 1 October 2026

Six new images come from a writable copy of the finished v0.0.24 HDF, running
its source-matched production executable. The final run completed 282 frames
with zero surface/edge overflow. Journal pixels before and after quickload
match exactly; the deliverable image was verified unchanged. Raw PCX files,
commands, native logs and the image receipt accompany the private package.

The public PNGs are 640 by 400 nearest-neighbour enlargements of native 320 by
200 frames, with no colour/brightness adjustment, generated imagery or
compositing. Hands and the crosshair are disabled through existing runtime
settings for the composition views. Camera placement is diagnostic, not evidence
of natural walking to each position. Gallery steady daylight and the exact-model
geometry opt-in are the existing documented settings, not screenshot-only code.

| Capture | Camera origin / yaw / pitch |
| --- | --- |
| Balmora bridge | `214,-480,85 / 125 / 6` |
| Balmora street | `-495,-501,142 / 75 / 0` |
| Balmora riverfront | `232,282,65 / 223 / 4` |
| Dagoth Ur mask, gallery record 122 | `0,26,13 / 270 / 0` |
| Island map and journal | Restored Hors character in Balmora |

| Streets and residents | Riverfront architecture |
| :---: | :---: |
| ![Balmora street](images/amiwind-v0.0.24-balmora-street.png) | ![Balmora riverfront](images/amiwind-v0.0.24-balmora-river.png) |

Every image has an exact `.gitignore` exception, a documentation-media allowlist
entry, and a source-package entry. The owner-run publishing helper also requires
all packaged public files to be tracked before committing. Other private
captures and converted assets remain excluded.
