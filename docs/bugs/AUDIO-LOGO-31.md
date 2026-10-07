# AUDIO-LOGO-31: music crackles while the startup logo plays (WinUAE)

## Status: 7 October 2026

Open. Owner report in WinUAE; cause found in source; repair in source, not yet
packaged or heard.

## Symptom

When the game starts and the AmiWind logo appears, the title music crackles.

## Where

Startup branding (`engine/aga/src/aw_movie.c`, the `intro/amiwind.awv` logo
video) and the main menu (`aw_menu.c`).

## How it happened

The title music was started at the same moment as the logo video. The logo is
a video streamed from disk frame by frame for its whole length, and the music is
streamed from disk too; both competed for the disk, the same mechanism as the
post-movie crackle ([AUDIO-03](AUDIO-03.md)).

## Why it was not caught

The automated FS-UAE runs do not listen for audio artifacts, and FS-UAE's disk
is far faster than WinUAE setups, so the competition is less audible there.

## Reproduction

WinUAE with a v0.0.31-dev2 or earlier package: start the game and listen while
the logo is shown.

## Repair

The logo no longer starts the title music. The main menu starts it half a second
after it appears (`AW_MusicTitleAfter`), when the logo has finished reading.
The logo itself is now silent.

## Verification

Pending: engine gates, then an owner check in WinUAE.

## Prevention

Music starts are kept away from disk-heavy moments (videos, map loads); see
[AUDIO-03](AUDIO-03.md) for the intro case.
