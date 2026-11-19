# MUSIC-DEATH-SILENT-33: No death music when the player dies

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | engine/aga/src/aw_music.c AW_MusicDeath, aw_combat.c caller |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.33-rc1 (last seen) |
| Severity | low: The death track never played in the playtest; the cause is not known yet. |
| Family | Music and sound (`audio`) |
| Playtest version | v0.0.33-rc1 |
| From commit | source 7ae3ea7, engine 7ae3ea7, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 7ae3ea7, world format unknown |
| Unknown because | maintainer playtest report names no image commit or world format |
| Build note | maintainer playtest of a v0.0.33 build; the exact image commit is not in the report |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-09: reported in v0.0.33-rc1
- 2026-10-09: ARENA-PIT-NO-INTERIOR-33, COMBAT-SETUP-DICE-BLOCK-33, COMBAT-VOICES-SILENT-33, MUSIC-DEATH-SILENT-33, COMBAT-PLAYER-DEATH-FALL-33: The maintainer playtest findings for a later release: ARENA-PIT-NO-INTERIOR-33 the Vivec Arena minigame ...
- 2026-10-10: PLAYER-DEATH-LIMBO-35 and COMBAT-PLAYER-DEATH-FALL-33 repaired in source: PLAYER-DEATH-LIMBO-35: a dead player can no longer talk, activate, attack, wait or move; after the death animation the original question appears (load the most ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.42-dev1 (17 October 2026)._

## Status: 9 October 2026

Open (maintainer playtest), cause unknown. The code plays the death track once when the player dies in a fight; suspects: the track missing from the build's music catalogue, music held at that moment, or a death outside a fight (the call sits in the combat layer only).

## Symptom

The player died and no death jingle played.

## Where

engine/aga/src/aw_music.c AW_MusicDeath (track "mw_death" from the music catalogue), engine/aga/src/aw_combat.c caller.

## How it happened

Unknown. The original plays the special death track when the player dies (OpenMW music.lua playerDied). AW_MusicDeath looks up "mw_death" and returns silently when the catalogue lacks it or music is held; it is only called from the combat layer, so a death by other damage never asks for it.

## Why it was not caught

The death path has a unit test for the call, not for the track being in the image or for deaths outside fights.

## Reproduction

Not known yet.

## Repair

Not yet: move the call to the shared player-death point (every cause), report a missing track once on the console, add the track to the image check.

## Verification

None yet.

## Prevention

Combat and death behaviour follow the original rules with the source named (OpenMW source, game settings); every presentation change gets a fixture or an in-game clip.

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
- [CREATURE-ANIM-SOUND-54](CREATURE-ANIM-SOUND-54.md): A creature's sound generators from its animations are not played
- CREATURE-SOUNDS-CLIFFRACER-SILENT-58 (no report page): The combat playground stops after 30 s without input: the idle vanity camera's full view skips the playground, so the sounds mode goes silent
- [CUSTOM-OST-SLOT-53](CUSTOM-OST-SLOT-53.md): Requested: a custom OST slot: the user's own track built into the image and a player routine for it, apart from the playlist
- [DOOR-AUDIO-SECOND-COPY-48](DOOR-AUDIO-SECOND-COPY-48.md): The door audio stage converts its own copies of the 10 door sounds the media stage already converted (166,338 bytes stored twice)
- [ENGINE-MUSIC-NO-OFF-SWITCH-36](ENGINE-MUSIC-NO-OFF-SWITCH-36.md): The soundtrack has no off switch: music can only be disabled by deleting music/playlist.txt from the image
- [ENGINE-SOUND-NAME-SYSERROR-35](ENGINE-SOUND-NAME-SYSERROR-35.md): A sound name of 64 characters or more, or more than 512 sounds in a session, stopped the program
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

Related bugs in other categories:

- [PLAYER-DEATH-LIMBO-35](PLAYER-DEATH-LIMBO-35.md): After the player dies there is no way out: the game stays in a limbo with no reload or retry

<!-- END GENERATED CATEGORY -->
