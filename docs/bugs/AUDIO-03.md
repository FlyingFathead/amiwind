# AUDIO-03: audio glitch at the post-movie load into the Jiub opening scene (WinUAE)

## Status: 7 October 2026

Open. Reported in v0.29-era builds, still present in v0.0.30-rc1 and
v0.0.31-dev2 (owner, WinUAE). Cause found in source; repair in source, not yet
packaged or heard. Earlier history: [journal](../journals/BUG_JOURNAL-v0.0.29.md#audio-03-winuae-video-to-jiub-loading-spike).

## Symptom

Right after the intro video ends, as the prison-ship scene with Jiub fades in,
the music crackles.

## Where

`engine/aga/src/aw_intro.c`, `AW_IntroBegin`.

## How it happened

`AW_IntroBegin` started the opening music track and then queued `map prison`.
The music therefore began exactly when the heaviest load of the opening started,
and its disk refills competed with the map read.

## Why it was not caught

The automated FS-UAE runs do not listen for audio artifacts, and FS-UAE's disk
is far faster than WinUAE setups.

## Reproduction

WinUAE: New Game, let the intro video play to the end (or skip it), and listen
as the ship scene appears.

## Repair

As proposed by the owner: hold the opening scene briefly and start the music
only after the loads. `AW_IntroBegin` no longer starts the music; it marks it
pending. Once the client is fully signed on to the ship map, the intro waits a
short settle period (4 frames and 0.25 s; shortened from 8 frames and 0.75 s once the hold also flushes the previous stream, MUSIC-OPENING-CLIP-31), then starts the opening track. Until
then the intro script holds: the scene is on screen, but nobody speaks before
the music runs.

## Verification

Pending: engine gates, then an owner check in WinUAE.

## Prevention

Music starts are kept away from disk-heavy moments; see also
[AUDIO-LOGO-31](AUDIO-LOGO-31.md) (startup logo).
