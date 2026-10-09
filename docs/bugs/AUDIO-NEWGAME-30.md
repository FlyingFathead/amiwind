# AUDIO-NEWGAME-30: music crackle when choosing New Game

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.30-rc1 |
| Where | Main menu, New Game confirmation (WinUAE) |
| Reproduction | once |
| Duplicate of | no |
| Persists in | v0.0.30-rc1 (last seen) |
| Severity | low: One short music crackle at a menu step; not yet reproduced. |
| Family | Music and sound (`audio`) |
| Playtest version | v0.0.30-rc1 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Music and sound (`audio`). The mixer must stay fed through loads and scene changes; music starts after loads settle. See [families](README.md#families).

- [AUDIO-03](AUDIO-03.md): Audio glitch at the post-movie load into the Jiub opening scene (WinUAE)
- AUDIO-APPEARANCE-29 (no report page): Music pause entering character race selection
- AUDIO-CLOCK-29 (no report page): Long audio DMA gaps lose elapsed playback time
- AUDIO-EFFECTS-DEFAULT-29 (no report page): Effects volume should default to 75%
- AUDIO-ENTER-29 (no report page): Sub-second soundtrack cut on Enter to follow the guard
- [AUDIO-HOST-LOAD-33](AUDIO-HOST-LOAD-33.md): Music and sound crackle when the emulator shares a fully loaded host CPU
- AUDIO-LOAD-29 (no report page): OST crackles under heavy loading
- [AUDIO-LOGO-31](AUDIO-LOGO-31.md): Music crackles while the startup logo plays (WinUAE)
- AW-20260928-02 (no report page): Dock/menu freeze and looping audio
- AW-20260928-15 (no report page): Prison wave ambience masks dialogue
- AW-20260929-03 (no report page): Music cuts during loading
- AW-20260929-05 (no report page): Ship waves too quiet
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

<!-- END GENERATED CATEGORY -->
