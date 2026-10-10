# MUSIC-OPENING-CLIP-31: a clip of another track plays while the opening scene loads

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 7 October 2026, in v0.0.31-dev3 |
| Where | opening scene load, music resume (engine music code) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev3 (last seen) |
| Severity | low: A short clip of the title track plays during the load. |
| Family | Music and sound (`audio`) |
| Playtest version | v0.0.31-dev3 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

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
- [AUDIO-LOGO-31](AUDIO-LOGO-31.md): Music crackles while the startup logo plays (WinUAE)
- [AUDIO-NEWGAME-30](AUDIO-NEWGAME-30.md): Music crackles when confirming New Game (WinUAE)
- AW-20260928-02 (no report page): Dock/menu freeze and looping audio
- AW-20260928-15 (no report page): Prison wave ambience masks dialogue
- AW-20260929-03 (no report page): Music cuts during loading
- AW-20260929-05 (no report page): Ship waves too quiet
- [COMBAT-VOICES-SILENT-33](COMBAT-VOICES-SILENT-33.md): Player pain grunts and hostile NPC taunts are not heard in fights
- [ENGINE-SOUND-NAME-SYSERROR-35](ENGINE-SOUND-NAME-SYSERROR-35.md): A sound name of 64 characters or more, or more than 512 sounds in a session, stopped the program
- [MUSIC-DEATH-SILENT-33](MUSIC-DEATH-SILENT-33.md): No death music when the player dies
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

<!-- END GENERATED CATEGORY -->
