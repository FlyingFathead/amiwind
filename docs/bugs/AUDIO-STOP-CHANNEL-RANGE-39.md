# AUDIO-STOP-CHANNEL-RANGE-39: Stopping an entity sound skips half the dynamic mixer slots

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | audit |
| First noticed | 13 October 2026, in v0.0.39-dev1 |
| Where | AmiQuake entity sound cancellation in snd_dma.c |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.39-dev1 (last seen) |
| Severity | medium: Upper dynamic slots can keep playing after cancellation while speech pose timing has stopped. |
| Family | Music and sound (`audio`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine cb06544 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (Source audit; prepared synthetic PCM fixture has not executed and native occurrence is not isolated.) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Symptom

An entity sound assigned to dynamic mixer slots 8 through 11 can continue after
S_StopSound is called for its entity and channel. Speech-pose timing is cleared
first, so the model can stop speaking while its audio continues. This is a
source finding; a maintainer-visible occurrence has not been isolated.

## Where

AmiQuake sound channel selection and stopping in engine/aga/src/snd_dma.c.
Found while tracing cancellation for ambient speech during combat.

## How it happened

SND_PickChannel allocates eight dynamic channels starting after NUM_AMBIENTS,
which is four. S_StopSound instead scanned indices zero through seven. It
included ambient slots and missed the upper four dynamic slots. The channel
layout comment in sound.h described the same incorrect ordering.

## Why it was not caught

The existing real-mixer fixture exercised whole-scene cancellation and speech
tails, but did not stop an individual entity sound in every dynamic slot.

## Reproduction

Place an entity voice in each dynamic slot, especially indices 8 through 11,
then stop that exact entity/channel. Inspect channel activity and mixed PCM.
The old loop cannot visit the upper slots. A synthetic PCM fixture is prepared;
its execution and native audio reproduction remain pending.

## Repair

Use the same dynamic interval as SND_PickChannel. Preserve exact entity/channel
matching and AW_SpeechStop. Do not touch ambient or static channels, music or
the separately preserved scene voice tail. Correct the channel-layout comment.
This reuses the existing AmiQuake mixer; no new allocation or per-frame pass.

## Verification

Pending. The existing real-mixer fixture now includes all eight dynamic slots,
wrong-channel calls, other entities, ambient/static isolation, speech timing
and PCM silence after stopping the last slot. No test, target compile or native
audio pass has been recorded for this change. This does not itself fix greeting
policy or subtitle ownership in COMBAT-AMBIENT-SPEECH-GATING-38.

## Prevention

Exercise allocator and stopper boundaries together using the actual mixer.
Keep unrelated channels and music as controls, and require an exact-build
native combat-speech clip before claiming the broader speech issue repaired.

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
- [AW-20260928-02](AW-20260928-02.md): Dock/menu freeze and looping audio
- AW-20260928-15 (no report page): Prison wave ambience masks dialogue
- AW-20260929-03 (no report page): Music cuts during loading
- AW-20260929-05 (no report page): Ship waves too quiet
- CHIM-ROOMS-WATER-SOUND-48 (no report page): CHIM water rooms have no ambient water sound in their water: room maps got it from their visibility pass
- [COMBAT-AMBIENT-SPEECH-GATING-38](COMBAT-AMBIENT-SPEECH-GATING-38.md): Ambient greetings and subtitles interrupt combat
- [COMBAT-MUSIC-AIR-SWING-35](COMBAT-MUSIC-AIR-SWING-35.md): Swinging at the air starts the combat music; it should start only when the player attacks a valid combat target (an NPC or creature)
- [COMBAT-VOICES-SILENT-33](COMBAT-VOICES-SILENT-33.md): Player pain grunts and hostile NPC taunts are not heard in fights
- DOOR-AUDIO-SECOND-COPY-48 (no report page): The door audio stage converts its own copies of the 10 door sounds the media stage already converted (166,338 bytes stored twice)
- [ENGINE-MUSIC-NO-OFF-SWITCH-36](ENGINE-MUSIC-NO-OFF-SWITCH-36.md): The soundtrack has no off switch: music can only be disabled by deleting music/playlist.txt from the image
- [ENGINE-SOUND-NAME-SYSERROR-35](ENGINE-SOUND-NAME-SYSERROR-35.md): A sound name of 64 characters or more, or more than 512 sounds in a session, stopped the program
- [MUSIC-DEATH-SILENT-33](MUSIC-DEATH-SILENT-33.md): No death music when the player dies
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- [MWSCRIPT-AUDIO-FIRST-48](MWSCRIPT-AUDIO-FIRST-48.md): The game's scripts start no sounds, lines or music cues: MWScript compiled by the builder, audio first
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- SOUND-MARKERS-SILENT-48 (no report page): The original's sound markers are placed but silent: 2,163 in Morrowind (187 outdoors in 78 cells, 1,976 in 434 rooms), water under the Khuul pier, creaking under bridges and boats
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

<!-- END GENERATED CATEGORY -->
