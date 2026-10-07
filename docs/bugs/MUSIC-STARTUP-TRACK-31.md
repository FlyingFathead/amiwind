# MUSIC-STARTUP-TRACK-31: a random world track plays under the startup logo

## Status: 7 October 2026

Regression in v0.0.31-dev3, found by the owner in WinUAE the evening it was
published. Cause read in source; repaired in source, not yet packaged.

## Symptom

At startup, during the AmiWind logo and its fade, a random soundtrack piece
plays instead of silence followed by the title music (Nerevar Rising).

## Where

`engine/aga/src/aw_music.c`, `CDAudio_Init`.

## How it happened

Music start-up always opened a random exploration track and started playing
it. Before dev3 the logo immediately switched to the title track, so the
random one was never heard. The [AUDIO-LOGO-31](AUDIO-LOGO-31.md) repair made
the logo silent and moved the title start to the main menu; nothing replaced
the switch, so the random track played under the logo until the menu started
the title.

This also explains the original start-up crackle ([AUDIO-LOGO-31](AUDIO-LOGO-31.md)),
as the owner spotted: start-up opened and pre-read a random track (16 reads),
then the logo threw it away and opened the title (16 more) while the logo video
streamed from the same disk. dev3 is silent under the logo and does not crackle;
with this repair only one track (the title) is opened, once, at the menu.

## Why it was not caught

The music tests check the title and world playlists separately; none checks
what plays between start-up and the main menu. The change was not listened to
before packaging.

## Reproduction

v0.0.31-dev3 in WinUAE: start the game and listen during the logo.

## Repair

With a title track in the playlist, start-up opens nothing and stays paused; the
main menu starts the title half a second after it appears. Playlists without a
title track keep the world shuffle at start-up.

## Verification

Native music test: after start-up with a title track nothing is open and the
mixer is silent; the title then starts with the title track. Owner listening
check pending.

## Prevention

Listen to the start-up after any change to music start points; the native test
covers the silence before the menu.
