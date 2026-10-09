# AUDIO-03: audio glitch at the post-movie load into the Jiub opening scene (WinUAE)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | unknown, in v0.0.29 |
| Where | Opening: post-movie load into the Jiub ship scene (WinUAE) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.29, v0.0.30-rc1, v0.0.31-dev2 (last seen) |
| Severity | medium: Audible crackle at one scene change; the game continues. |
| Family | Music and sound (`audio`) |

<!-- END GENERATED FACTS -->

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

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Music and sound (`audio`). The mixer must stay fed through loads and scene changes; music starts after loads settle. See [families](README.md#families).

- AUDIO-APPEARANCE-29 (no report page): Music pause entering character race selection
- AUDIO-CLOCK-29 (no report page): Long audio DMA gaps lose elapsed playback time
- AUDIO-EFFECTS-DEFAULT-29 (no report page): Effects volume should default to 75%
- AUDIO-ENTER-29 (no report page): Sub-second soundtrack cut on Enter to follow the guard
- [AUDIO-HOST-LOAD-33](AUDIO-HOST-LOAD-33.md): Music and sound crackle when the emulator shares a fully loaded host CPU
- AUDIO-LOAD-29 (no report page): OST crackles under heavy loading
- [AUDIO-LOGO-31](AUDIO-LOGO-31.md): Music crackles while the startup logo plays (WinUAE)
- [AUDIO-NEWGAME-30](AUDIO-NEWGAME-30.md): Music crackles when confirming New Game (WinUAE)
- AW-20260928-02 (no report page): Dock/menu freeze and looping audio
- AW-20260928-15 (no report page): Prison wave ambience masks dialogue
- AW-20260929-03 (no report page): Music cuts during loading
- AW-20260929-05 (no report page): Ship waves too quiet
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

<!-- END GENERATED CATEGORY -->
