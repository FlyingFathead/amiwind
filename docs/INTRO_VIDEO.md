# Intro movie conversion and playback

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
