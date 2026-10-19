# AUDIO-DMA-CLOCK-DRIFT-35: The mixer estimates the audio DMA position from the EClock, not from the hardware, so the two can drift apart over a long session

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | review |
| First noticed | 10 October 2026, in v0.0.34 |
| Where | engine/aga/src/snd_amiga.c SNDDMA_GetSamples |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.34 (last seen) |
| Severity | medium: Drift between the estimate and Paula can cause periodic crackle; not measured yet |
| Family | Music and sound (`audio`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine 3240e3d |
| CHIM engine version | none: legacy engine |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.39 (14 October 2026)._

## Status: 10 October 2026

Open: registered from the engine review, not changed yet.

## Symptom

Over a long session the mixer's idea of where the audio hardware is playing can drift from where Paula really is; a drift would show as periodic crackle.

## Where

`engine/aga/src/snd_amiga.c SNDDMA_GetSamples`.

## How it happened

The audio device gives no play position, so SNDDMA_GetSamples estimates it from the EClock and the Paula period set at start-up.

## Why it was not caught

The engine came from the original sources, where these paths assumed well-formed input; no test fed them bad or unusual values.

## Reproduction

Found by reading the source (v0.0.35 engine review).

## Repair

Not changed yet. Re-anchoring needs the audio channels restarted together with the mixer's painted time, which is not a small, safe change. Next step: measure the drift per hour in a long session first.

## Verification

Not verified; open.

## Prevention

Measure before changing the audio clock.

## Related freezes

10 October 2026: the soak run of [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md) (full analysis and repair: a music stream read that never returns while the main loop waits for it) did not confirm this drift as the cause of that freeze; the freeze is a blocked music read. This issue stays open on its own.

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
- [AUDIO-NEWGAME-30](AUDIO-NEWGAME-30.md): Music crackles when confirming New Game (WinUAE)
- [AUDIO-STOP-CHANNEL-RANGE-39](AUDIO-STOP-CHANNEL-RANGE-39.md): Stopping an entity sound skips half the dynamic mixer slots
- [AW-20260928-02](AW-20260928-02.md): Dock/menu freeze and looping audio
- AW-20260928-15 (no report page): Prison wave ambience masks dialogue
- AW-20260929-03 (no report page): Music cuts during loading
- AW-20260929-05 (no report page): Ship waves too quiet
- [COMBAT-AMBIENT-SPEECH-GATING-38](COMBAT-AMBIENT-SPEECH-GATING-38.md): Ambient greetings and subtitles interrupt combat
- [COMBAT-MUSIC-AIR-SWING-35](COMBAT-MUSIC-AIR-SWING-35.md): Swinging at the air starts the combat music; it should start only when the player attacks a valid combat target (an NPC or creature)
- [COMBAT-VOICES-SILENT-33](COMBAT-VOICES-SILENT-33.md): Player pain grunts and hostile NPC taunts are not heard in fights
- [ENGINE-MUSIC-NO-OFF-SWITCH-36](ENGINE-MUSIC-NO-OFF-SWITCH-36.md): The soundtrack has no off switch: music can only be disabled by deleting music/playlist.txt from the image
- [ENGINE-SOUND-NAME-SYSERROR-35](ENGINE-SOUND-NAME-SYSERROR-35.md): A sound name of 64 characters or more, or more than 512 sounds in a session, stopped the program
- [MUSIC-DEATH-SILENT-33](MUSIC-DEATH-SILENT-33.md): No death music when the player dies
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

Related bugs in other categories:

- [HANG-IDLE-DUSK-35](HANG-IDLE-DUSK-35.md): The game freezes with the music looping after the player is left idle for a few minutes outdoors, seen around sundown

<!-- END GENERATED CATEGORY -->
