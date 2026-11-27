# AUDIO-03: audio glitch at the post-movie load into the Jiub opening scene (WinUAE)

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | unknown, in v0.0.29 |
| Where | Opening: post-movie load into the Jiub ship scene (WinUAE) |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.29, v0.0.30-rc1, v0.0.31-dev2 (last seen) |
| Severity | medium: Audible crackle at one scene change; the game continues. |
| Family | Music and sound (`audio`) |
| Waiting on | Lacks dependency: the maintainer's WinUAE listening check (the fix c93ffae is in since v0.0.31) |
| Deferred by the maintainer | 2026-10-29: to v0.0.57, the maintainer (desktop chat 2026-10-29, on the six expired v0.0.56 deferrals): approved, the six bugs are deferred to v0.0.57. |

<!-- END GENERATED FACTS -->

<!-- BEGIN GENERATED TIMELINE: edit docs/bugs/bugs.json (bug_register.py step, note, report), then run tools/bug_register.py render -->

## Timeline

Dated events, oldest first, from the entry's own data (first noticed, reports, history, closure steps, returns, the fix, a deferral):

- 2026-10-03: AUDIO-03: WinUAE video-to-Jiub loading spike: The maintainer reports repeatable audio glitches during the heaviest scene-loading spike immediately after the intro movie, when entering the Jiub opening scene.
- 2026-10-07: AUDIO-03 and AUDIO-LOGO-31: music started under disk-heavy moments: The maintainer, WinUAE: the music still crackles right after the intro video, and also while the startup logo plays.
- 2026-10-07: v0.0.30-rc1: v0.0.30-rc1 the maintainer playtest summary: WinUAE playtest by the maintainer: Census office interiors work (CENSUS-ENTITIES-30 accepted), mushroom picking on the road to Balmora works, Balmora works and torches work.
- 2026-10-07: AUDIO-NEWGAME-30: rc1 playtest audio reports: v0.0.30-rc1 WinUAE playtest by the maintainer: music crackles when confirming New Game (new, report (AUDIO-NEWGAME-30)); crackles as the game fades in after the intro (AUDIO-03); a split-second ...
- 2026-10-29: deferred by the maintainer: to v0.0.57, the maintainer (desktop chat 2026-10-29, on the six expired v0.0.56 deferrals): approved, the six bugs are deferred to v0.0.57.
- 2026-10-31: seen again in v0.0.57-dev5: Supporting reading only (FS-UAE, not the WinUAE judgement): v0.0.57-dev5 full image, 32 MB Fast, audio on, aw_new_game: the load from the intro movie into the prison ship read longest mixer gap 63 ms with the mix 1486 ms ahead, 0 late ...

<!-- END GENERATED TIMELINE -->

_Last updated with AmiWind v0.0.66-dev12 (16 November 2026)._

## Status: 7 October 2026

Open. Reported in v0.29-era builds, still present in v0.0.30-rc1 and
v0.0.31-dev2 (maintainer, WinUAE). Cause found in source; repair in source, not yet
packaged or heard. Earlier history: the entry's dated history in the timeline below.

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

As proposed by the maintainer: hold the opening scene briefly and start the music
only after the loads. `AW_IntroBegin` no longer starts the music; it marks it
pending. Once the client is fully signed on to the ship map, the intro waits a
short settle period (4 frames and 0.25 s; shortened from 8 frames and 0.75 s once the hold also flushes the previous stream, MUSIC-OPENING-CLIP-31), then starts the opening track. Until
then the intro script holds: the scene is on screen, but nobody speaks before
the music runs.

## Verification

Pending: engine gates, then a maintainer check in WinUAE.

## Prevention

Music starts are kept away from disk-heavy moments; see also
[AUDIO-LOGO-31](AUDIO-LOGO-31.md) (startup logo).

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Music and sound (`audio`). The mixer must stay fed through loads and scene changes; music starts after loads settle. See [families](README.md#families).

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
- [MUSIC-DEATH-SILENT-33](MUSIC-DEATH-SILENT-33.md): No death music when the player dies
- [MUSIC-DEATH-TRACK-RANDOM-60](MUSIC-DEATH-TRACK-RANDOM-60.md): The death music played in the wilderness while the player was alive
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- [MWSCRIPT-AUDIO-FIRST-48](MWSCRIPT-AUDIO-FIRST-48.md): The game's scripts start no sounds, lines or music cues: MWScript compiled by the builder, audio first
- [MWSCRIPT-ONESHOT-SLOTS-LEAK-54](MWSCRIPT-ONESHOT-SLOTS-LEAK-54.md): Script one-shot sounds never freed their slot: after 32 distinct one-shots in a map new script sounds were dropped
- [MWSCRIPT-SOUND-OWN-SCRIPT-ONLY-68](MWSCRIPT-SOUND-OWN-SCRIPT-ONLY-68.md): GetSoundPlaying and StopSound see only sounds the same script started, a loop on another object moves to the script's own object, and the pitch argument of the VP sound calls is not used
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- [NPC-VOICE-INTRUDER-THIEF-NO-EVENT-58](NPC-VOICE-INTRUDER-THIEF-NO-EVENT-58.md): NPCs never say their Intruder or Thief lines: the voice table holds them for 2,654 NPCs, but no engine event says them
- [NPC-VOICE-ON-EFFECTS-VOLUME-69](NPC-VOICE-ON-EFFECTS-VOLUME-69.md): NPC voice lines from the voice table and script Say play at the effects volume, not the dialogue volume
- PLAYER-FOOTSTEPS-NONE-58 (no report page): The player has no footstep sounds: only NPCs play them, and there is no setting for the player's own
- [PUNCH-AUDIO-COVERAGE-29](PUNCH-AUDIO-COVERAGE-29.md): Original punch swing/hit sound coverage unverified
- [SOUND-MARKERS-SILENT-48](SOUND-MARKERS-SILENT-48.md): The original's sound markers are placed but silent: 2,163 in Morrowind (187 outdoors in 78 cells, 1,976 in 434 rooms), water under the Khuul pier, creaking under bridges and boats
- [TOMB-MUSIC-OVER-AMBIENT-60](TOMB-MUSIC-OVER-AMBIENT-60.md): Ancestral tombs play the exploration music over the tomb ambience
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

<!-- END GENERATED CATEGORY -->
