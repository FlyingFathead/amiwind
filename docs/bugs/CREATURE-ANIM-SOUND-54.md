# CREATURE-ANIM-SOUND-54: A creature's sound generators from its animations are not played

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | developer |
| First noticed | 27 October 2026, in v0.0.54-dev1 |
| Where | creature actors: sound generators of the animation data |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.54-dev1 (last seen) |
| Severity | low: Creatures are silent. |
| Family | Music and sound (`audio`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source and engine be93bf6 |
| CHIM engine version | none: legacy engine |
| Platform or emulator | not in game (left over from source work) |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-27: reported in v0.0.54-dev1
- 2026-10-31 12:42 +0000: seen again in v0.0.57: PERSISTING in v0.0.57: AW_GlutCreatureSound (aw_glut.c) has no caller in normal play, so no creature ever moans, roars, screams, lands or steps with its sound generators; only the combat playground's sounds mode plays them.
- 2026-11-07: Register and work list synchronised: three entries fixed, the rest linked to open work: An audit of the register against the work list found entries that disagreed with it.

<!-- END GENERATED TIMELINE -->

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Music and sound (`audio`). The mixer must stay fed through loads and scene changes; music starts after loads settle. See [families](README.md#families).

- [AUDIO-03](AUDIO-03.md): Audio glitch at the post-movie load into the Jiub opening scene (WinUAE)
- [AUDIO-APPEARANCE-29](AUDIO-APPEARANCE-29.md): Music pause entering character race selection
- [AUDIO-CLOCK-29](AUDIO-CLOCK-29.md): Long audio DMA gaps lose elapsed playback time
- [AUDIO-DMA-CLOCK-DRIFT-35](AUDIO-DMA-CLOCK-DRIFT-35.md): The mixer estimates the audio DMA position from the EClock, not from the hardware, so the two can drift apart over a long session
- AUDIO-EFFECTS-DEFAULT-29 (no report page): Effects volume should default to 75%
- [AUDIO-ENTER-29](AUDIO-ENTER-29.md): Sub-second soundtrack cut on Enter to follow the guard
- [AUDIO-HOST-LOAD-33](AUDIO-HOST-LOAD-33.md): Music and sound crackle when the emulator shares a fully loaded CPU
- [AUDIO-LOAD-29](AUDIO-LOAD-29.md): OST crackles under heavy loading
- AUDIO-LOCAL-SOUND-CUTS-58 (no report page): One blow's combat sounds cut each other: every local sound replaces the player's other sounds, so only the last of swish, armour struck and Health Damage is heard
- [AUDIO-LOGO-31](AUDIO-LOGO-31.md): Music crackles while the startup logo plays (WinUAE)
- [AUDIO-MAGIC-STOPS-SPEECH-54](AUDIO-MAGIC-STOPS-SPEECH-54.md): A magic sound played as entity -1 stopped every NPC voice mid-line: AW_SpeechStop(-1) matched all speakers
- [AUDIO-NEWGAME-30](AUDIO-NEWGAME-30.md): Music crackles when confirming New Game (WinUAE)
- AUDIO-SFX-NAME-TABLE-FULL-58 (no report page): The mixer's sound name table (512 entries) is never emptied during a session: once 512 different sounds have played, every new voice line or effect stays silent
- [AUDIO-STOP-CHANNEL-RANGE-39](AUDIO-STOP-CHANNEL-RANGE-39.md): Stopping an entity sound skips half the dynamic mixer slots
- [AW-20260928-02](AW-20260928-02.md): Dock/menu freeze and looping audio
- [AW-20260928-15](AW-20260928-15.md): Prison wave ambience masks dialogue
- [AW-20260929-03](AW-20260929-03.md): Music cuts during loading
- [AW-20260929-05](AW-20260929-05.md): Ship waves too quiet
- [CHIM-ROOMS-WATER-SOUND-48](CHIM-ROOMS-WATER-SOUND-48.md): CHIM water rooms have no ambient water sound in their water: room maps got it from their visibility pass
- [COMBAT-AMBIENT-SPEECH-GATING-38](COMBAT-AMBIENT-SPEECH-GATING-38.md): Ambient greetings and subtitles interrupt combat
- [COMBAT-MUSIC-AIR-SWING-35](COMBAT-MUSIC-AIR-SWING-35.md): Swinging at the air starts the combat music; it should start only when the player attacks a valid combat target (an NPC or creature)
- [COMBAT-MUSIC-NEVER-ENDS-65](COMBAT-MUSIC-NEVER-ENDS-65.md): The battle music keeps playing after the player has left the fight behind
- [COMBAT-MUSIC-STUCK-64](COMBAT-MUSIC-STUCK-64.md): The battle music keeps playing after the fight has ended
- COMBAT-SOUNDS-RULE-OFF-58 (no report page): The original's combat sounds are switched off by default: normal play hears one sound per outcome, not OpenMW's set (swing swish, the armour piece struck, blocks, punches, criticals)
- [COMBAT-VOICES-SILENT-33](COMBAT-VOICES-SILENT-33.md): Player pain grunts and hostile NPC taunts are not heard in fights
- CREATURE-SOUNDS-CLIFFRACER-SILENT-58 (no report page): The combat playground stops after 30 s without input: the idle vanity camera's full view skips the playground, so the sounds mode goes silent
- [CUSTOM-OST-SLOT-53](CUSTOM-OST-SLOT-53.md): Requested: a custom OST slot: the user's own track built into the image and a player routine for it, apart from the playlist
- [DOOR-AUDIO-SECOND-COPY-48](DOOR-AUDIO-SECOND-COPY-48.md): The door audio stage converts its own copies of the 10 door sounds the media stage already converted (166,338 bytes stored twice)
- [ENGINE-MUSIC-NO-OFF-SWITCH-36](ENGINE-MUSIC-NO-OFF-SWITCH-36.md): The soundtrack has no off switch: music can only be disabled by deleting music/playlist.txt from the image
- [ENGINE-SOUND-NAME-SYSERROR-35](ENGINE-SOUND-NAME-SYSERROR-35.md): A sound name of 64 characters or more, or more than 512 sounds in a session, stopped the program
- [MUSIC-DEATH-SILENT-33](MUSIC-DEATH-SILENT-33.md): No death music when the player dies
- [MUSIC-DEATH-TRACK-RANDOM-60](MUSIC-DEATH-TRACK-RANDOM-60.md): The death music played in the wilderness while the player was alive
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- [MWSCRIPT-AUDIO-FIRST-48](MWSCRIPT-AUDIO-FIRST-48.md): The game's scripts start no sounds, lines or music cues: MWScript compiled by the builder, audio first
- [MWSCRIPT-ONESHOT-SLOTS-LEAK-54](MWSCRIPT-ONESHOT-SLOTS-LEAK-54.md): Script one-shot sounds never freed their slot: after 32 distinct one-shots in a map new script sounds were dropped
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- [NPC-VOICE-INTRUDER-THIEF-NO-EVENT-58](NPC-VOICE-INTRUDER-THIEF-NO-EVENT-58.md): NPCs never say their Intruder or Thief lines: the voice table holds them for 2,654 NPCs, but no engine event says them
- PLAYER-FOOTSTEPS-NONE-58 (no report page): The player has no footstep sounds: only NPCs play them, and there is no setting for the player's own
- [PUNCH-AUDIO-COVERAGE-29](PUNCH-AUDIO-COVERAGE-29.md): Original punch swing/hit sound coverage unverified
- [SOUND-MARKERS-SILENT-48](SOUND-MARKERS-SILENT-48.md): The original's sound markers are placed but silent: 2,163 in Morrowind (187 outdoors in 78 cells, 1,976 in 434 rooms), water under the Khuul pier, creaking under bridges and boats
- [TOMB-MUSIC-OVER-AMBIENT-60](TOMB-MUSIC-OVER-AMBIENT-60.md): Ancestral tombs play the exploration music over the tomb ambience
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

<!-- END GENERATED CATEGORY -->
