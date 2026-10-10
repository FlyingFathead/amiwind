# AUDIO-LOGO-31: music crackles while the startup logo plays (WinUAE)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.31-dev2 |
| Where | Startup logo video and title music (aw_movie.c, aw_menu.c) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev2 (last seen) |
| Severity | medium: Title music crackles under the startup logo on WinUAE. |
| Family | Music and sound (`audio`) |
| Playtest version | v0.0.31-dev2 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Music and sound (`audio`). The mixer must stay fed through loads and scene changes; music starts after loads settle. See [families](README.md#families).

- [AUDIO-03](AUDIO-03.md): Audio glitch at the post-movie load into the Jiub opening scene (WinUAE)
- AUDIO-APPEARANCE-29 (no report page): Music pause entering character race selection
- AUDIO-CLOCK-29 (no report page): Long audio DMA gaps lose elapsed playback time
- [AUDIO-DMA-CLOCK-DRIFT-35](AUDIO-DMA-CLOCK-DRIFT-35.md): The mixer estimates the audio DMA position from the EClock, not from the hardware, so the two can drift apart over a long session
- AUDIO-EFFECTS-DEFAULT-29 (no report page): Effects volume should default to 75%
- AUDIO-ENTER-29 (no report page): Sub-second soundtrack cut on Enter to follow the guard
- [AUDIO-HOST-LOAD-33](AUDIO-HOST-LOAD-33.md): Music and sound crackle when the emulator shares a fully loaded host CPU
- AUDIO-LOAD-29 (no report page): OST crackles under heavy loading
- [AUDIO-NEWGAME-30](AUDIO-NEWGAME-30.md): Music crackles when confirming New Game (WinUAE)
- AW-20260928-02 (no report page): Dock/menu freeze and looping audio
- AW-20260928-15 (no report page): Prison wave ambience masks dialogue
- AW-20260929-03 (no report page): Music cuts during loading
- AW-20260929-05 (no report page): Ship waves too quiet
- [COMBAT-VOICES-SILENT-33](COMBAT-VOICES-SILENT-33.md): Player pain grunts and hostile NPC taunts are not heard in fights
- [ENGINE-SOUND-NAME-SYSERROR-35](ENGINE-SOUND-NAME-SYSERROR-35.md): A sound name of 64 characters or more, or more than 512 sounds in a session, stopped the program
- [MUSIC-DEATH-SILENT-33](MUSIC-DEATH-SILENT-33.md): No death music when the player dies
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

<!-- END GENERATED CATEGORY -->
