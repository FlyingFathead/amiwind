# MUSIC-OPENING-CLIP-31: a clip of another track plays while the opening scene loads

## Status: 7 October 2026

Found by the owner in v0.0.31-dev3 (WinUAE). Cause read in source; repaired in
source, not yet packaged.

## Symptom

After the intro video, while the prison ship loads and the opening scene holds,
a short clip of another piece (the title music) plays before the opening track.

## Where

`engine/aga/src/aw_music.c` (`CDAudio_Play`, `CDAudio_Resume`) and the opening
hold in `engine/aga/src/aw_intro.c`.

## How it happened

The intro video pauses the music, leaving the title track's read-ahead blocks
in the buffer. When the ship map loads, the server sends Quake's CD-track
message (`svc_cdtrack`), which AmiWind's music treats as "resume". Before dev3
the opening track started immediately and replaced the buffer; since the
[AUDIO-03](AUDIO-03.md) repair the opening track waits for the scene to
settle, so the resumed title blocks played until it started.

## Why it was not caught

The music tests cover each start point alone, not the resume that a map load
sends in between; the change was not listened to before packaging.

## Reproduction

v0.0.31-dev3: New Game, let the intro video end, listen while the ship loads.

## Repair

The opening hold stops the music and flushes its buffer; resume requests are
ignored until the opening track (or the title) starts and ends the hold.

## Verification

Native music test: the hold is silent and flushed, a CD resume does not
restart it, the opening track ends it. Owner listening check pending.

## Prevention

Music start points and the engine's own resume paths are tested together.
