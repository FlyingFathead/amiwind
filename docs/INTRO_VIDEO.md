# Intro movie conversion and playback

## Startup branding decision: 6 October 2026

Keep AmiWind's own startup branding. Do not add a Bethesda/ZeniMax logo video
as a legal-protection measure. Preserve the original-game credits and independent
project notice in [licensing and credits](LICENSING_AND_CREDITS.md).
This decision is separate from compatibility with user-supplied in-game movies
and does not authorize redistribution of proprietary video or branding.

Cold boot plays a separate short AmiWind logo fade, then enters the main menu.
Esc skips that logo to the menu; it does not start a new game.

After confirmation, New Game first tries the privately converted prophecy movie, then starts the
ship adapter. Esc skips the movie and takes the same continuation path as normal
completion. Gameplay, the console and music hotkeys are suspended during playback.
The menu/world soundtrack pauses so it cannot overlap the movie's narration.
The chosen ship track starts only after the movie finishes or is skipped.

The source installation file is `Data Files/Video/mw_intro.bik`. The supplied
data-files archive initially contained an empty Video directory; the owner then
supplied the original videos separately. The New Game movie converts to 575
frames over 57.5 seconds (37,434,738 bytes at 320×200, including mono PCM). Missing or
invalid optional video is logged and falls through to the ship; it must never
make New Game unavailable. There is no replacement narration or guessed footage.

## Private conversion

Install the existing Pillow dependency and FFmpeg on the conversion computer.
The normal `prepare_intro.py` pass detects the original loose video, converts it
and places it in the private scene. To add it to an already converted scene:

```sh
python3 tools/prepare_video.py \
  --source '/path/to/Data Files/Video/mw_intro.bik' \
  --out /path/to/private/intro-video
cp /path/to/private/intro-video/mw_intro.awv /path/to/private/scene/id1/intro/
```

Build a new image from that scene. Keep both the source video and converted
movie out of public packages. `video-conversion.json` records source/output
SHA-256, dimensions, frame count, duration and audio format.

## Native format and budget

AWV1 is deliberately inexpensive to decode on the target: 320×200 indexed
frames at 10 fps, with a retained 160×100 low-bandwidth option, a fixed 256-colour movie palette, and signed
8-bit mono PCM at 11025 Hz. Source aspect ratio is fitted with black bars, without
cropping titles. The desktop converter samples the whole movie to choose its
palette, avoiding a palette made only from the opening black frame. The world
and UI palettes are restored afterward.

The 32-byte big-endian header contains magic, width, height, fps, sample rate,
frame count, sample count and twelve zero reserved bytes. It is followed by a
768-byte RGB palette, contiguous raw indexed frames and contiguous mono PCM.
Exact lengths, fixed dimensions and a 30-minute upper bound are checked before
playback. A short read during playback stops the movie and continues safely.

The player reserves one 64,000-byte picture, one 4,096-byte audio buffer and the
768-byte palette, plus small file/state overhead. Native-resolution throughput is
about 651 kB/s; the old 160×100 input needs about 171 kB/s. This is a first uncompressed
streaming format, not a claim that every physical hard drive meets the budget.
The audio sample clock selects pictures; late pictures are skipped rather than
slowing the narration. No Bink decoder, FFmpeg or general scripting runtime is
linked into the Amiga executable.

## Validation scope

Host tests cover conversion of an original synthetic picture/tone fixture,
truncated payload rejection, header bounds, the audio clock, mono mixing,
frame-buffer bounds, Esc and normal completion. A native FS-UAE test of that
fixture reached Jiub both after completion and after Esc. The final native
checkpoint also plays the supplied original prophecy and reaches Jiub after both
normal completion and Esc. Packed movie PCM exactly matches an independent
conversion of the source audio. Physical-hardware throughput and subjective audio
clarity remain owner playtests; emulator success does not certify those.

## Dev5 readable cards and logo

The startup wordmark is sampled directly at native 320×200 resolution, with the
small tagline drawn using the converted 16px Magic Cards font. This remains an
AGA low-resolution screen; no untested hires display-mode switch is claimed.

`prepare_video.py --low-res` retains the old movie conversion. Optional
`--captions /private/cards.json --font /private/gfx/magic16.awf` replaces selected
burned-in cards with readable native-pixel text on black. The JSON is a list of
objects with `start`, `end` (seconds) and `text`. Text is supplied privately from
the owner's movie, never embedded in public source. The dev5 private conversion
includes three replacement cards; timing boundaries are a readability adaptation,
not an exact reproduction of the original text fades. Narration is unchanged.
Exact gold ink shades are reserved in the movie palette.

The normal build converts at 320×200. To reproduce the private replacement cards,
run the optional caption conversion above and copy its AWV into the scene before
`build_aga.py image`. Missing videos still warn and continue to Jiub.

## v0.0.23-dev4 opening-only option

`./build.sh --intro-captions /private/cards.json ...` forwards the private card
file to image assembly. `build_aga.py image --intro-captions ...` also accepts it.
Only the first entry is used for a small `intro/opening.awt` sidecar; the AWV is
not rewritten. Use the existing JSON schema (`start`, `end` in seconds, `text`).
The image's converted 16 px Magic Cards font rasterizes that text on the host.
Use a separate private file for your language/edition's first quote. The private
playtest includes its exact input JSON for rebuilding; public source contains
no game quote or converted font data.

Archived `aw_intro_text_overlay 1` (default) displays the sidecar during its time
window; `0` plays the original burned-in text. If no sidecar is supplied, original
video plays. The older `prepare_video.py --captions` path remains available for
intentionally baked multi-card replacements.

Branding now runs 2 s fade in + 5 s hold + 1 s fade out. Space, Enter and Esc skip
it. Title music begins with branding and continues into the main menu. The movie
still uses its own unchanged PCM; starting New Game deliberately pauses the theme.

## Rc1 video-player aliases

`dbg playvid 15` plays the original Morrowind intro when included. IDs `1..17`
(also `01..17`) or an included catalogue name select other videos. The rc1
candidate also accepts `dbg vidplay`, `dbg playvideo` and `dbg videoplay`, all
routing to the same player and arguments. The current dev4 uses `dbg playvid`.
The aliases are listed under VIDEO in the disk-backed debug catalogue.
