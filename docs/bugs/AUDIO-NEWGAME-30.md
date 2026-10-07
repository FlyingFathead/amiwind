# AUDIO-NEWGAME-30: music crackle when choosing New Game

## Status: 7 October 2026

Open; reported, not yet reproduced. Present in v0.0.30-rc1 (WinUAE).

## Symptom

In WinUAE, choosing New Game and confirming with Choose makes the background
music crackle once.

## Where

Main menu, New Game confirmation, WinUAE. FS-UAE not yet checked.

## How it happened

Unknown. Likely the same family as the other load-time crackles
([AUDIO-LOAD-29](../BUGS.md), [AUDIO-03](../BUGS.md)): the music mixer is not
serviced often enough while the new game starts loading.

## Why it was not caught

Automated runs use FS-UAE and do not listen for audio artifacts at menu
transitions.

## Reproduction

WinUAE with the v0.0.30-rc1 package: main menu, New Game, Choose. Listen at
the moment of confirmation.

## Repair

None yet.

## Verification

None yet. Needs a WinUAE recording before and after a fix.

## Prevention

To be decided with the fix, for example an audio-continuity capture at menu
transitions.
