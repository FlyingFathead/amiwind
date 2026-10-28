# MUSIC-STARTUP-TRACK-31: a random world track plays under the startup logo

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 7 October 2026, in v0.0.31-dev3 |
| Where | Engine music start-up (aw_music.c, CDAudio_Init) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.31-dev3 (last seen) |
| Severity | low: A random track plays under the startup logo. |
| Family | Music and sound (`audio`) |
| Playtest version | v0.0.31-dev3 |
| From commit | source and engine unknown |
| CHIM engine version | none: legacy engine |
| Unknown because | the build receipt records no source commit (builds before v0.0.32-dev1 were assembled from earlier images, not by the repository builder) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Status: 7 October 2026

Regression in v0.0.31-dev3, found by the maintainer in WinUAE the evening it was
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
as the maintainer spotted: start-up opened and pre-read a random track (16 reads),
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
mixer is silent; the title then starts with the title track. Maintainer listening
check pending.

## Prevention

Listen to the start-up after any change to music start points; the native test
covers the silence before the menu.

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
- [AUDIO-LOAD-29](AUDIO-LOAD-29.md): OST crackles under heavy loading
- [AUDIO-LOGO-31](AUDIO-LOGO-31.md): Music crackles while the startup logo plays (WinUAE)
- AUDIO-MAGIC-STOPS-SPEECH-54 (no report page): A magic sound played as entity -1 stopped every NPC voice mid-line: AW_SpeechStop(-1) matched all speakers
- [AUDIO-NEWGAME-30](AUDIO-NEWGAME-30.md): Music crackles when confirming New Game (WinUAE)
- [AUDIO-STOP-CHANNEL-RANGE-39](AUDIO-STOP-CHANNEL-RANGE-39.md): Stopping an entity sound skips half the dynamic mixer slots
- [AW-20260928-02](AW-20260928-02.md): Dock/menu freeze and looping audio
- AW-20260928-15 (no report page): Prison wave ambience masks dialogue
- AW-20260929-03 (no report page): Music cuts during loading
- AW-20260929-05 (no report page): Ship waves too quiet
- CHIM-ROOMS-WATER-SOUND-48 (no report page): CHIM water rooms have no ambient water sound in their water: room maps got it from their visibility pass
- [COMBAT-AMBIENT-SPEECH-GATING-38](COMBAT-AMBIENT-SPEECH-GATING-38.md): Ambient greetings and subtitles interrupt combat
- [COMBAT-MUSIC-AIR-SWING-35](COMBAT-MUSIC-AIR-SWING-35.md): Swinging at the air starts the combat music; it should start only when the player attacks a valid combat target (an NPC or creature)
- [COMBAT-VOICES-SILENT-33](COMBAT-VOICES-SILENT-33.md): Player pain grunts and hostile NPC taunts are not heard in fights
- CREATURE-ANIM-SOUND-54 (no report page): A creature's sound generators from its animations are not played
- CUSTOM-OST-SLOT-53 (no report page): Requested: a custom OST slot: the user's own track built into the image and a player routine for it, apart from the playlist
- DOOR-AUDIO-SECOND-COPY-48 (no report page): The door audio stage converts its own copies of the 10 door sounds the media stage already converted (166,338 bytes stored twice)
- [ENGINE-MUSIC-NO-OFF-SWITCH-36](ENGINE-MUSIC-NO-OFF-SWITCH-36.md): The soundtrack has no off switch: music can only be disabled by deleting music/playlist.txt from the image
- [ENGINE-SOUND-NAME-SYSERROR-35](ENGINE-SOUND-NAME-SYSERROR-35.md): A sound name of 64 characters or more, or more than 512 sounds in a session, stopped the program
- [MUSIC-DEATH-SILENT-33](MUSIC-DEATH-SILENT-33.md): No death music when the player dies
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MWSCRIPT-AUDIO-FIRST-48](MWSCRIPT-AUDIO-FIRST-48.md): The game's scripts start no sounds, lines or music cues: MWScript compiled by the builder, audio first
- MWSCRIPT-ONESHOT-SLOTS-LEAK-54 (no report page): Script one-shot sounds never freed their slot: after 32 distinct one-shots in a map new script sounds were dropped
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- SOUND-MARKERS-SILENT-48 (no report page): The original's sound markers are placed but silent: 2,163 in Morrowind (187 outdoors in 78 cells, 1,976 in 434 rooms), water under the Khuul pier, creaking under bridges and boats
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

<!-- END GENERATED CATEGORY -->
