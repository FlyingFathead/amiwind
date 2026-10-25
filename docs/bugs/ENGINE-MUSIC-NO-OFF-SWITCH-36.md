# ENGINE-MUSIC-NO-OFF-SWITCH-36: The soundtrack has no off switch: music can only be disabled by deleting music/playlist.txt from the image

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | test |
| First noticed | 11 October 2026, in v0.0.36-dev3 |
| Where | engine/aga/src/aw_music.c CDAudio_Init; no cvar, option or builder flag |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.36-dev3 (last seen) |
| Severity | medium: a shipped feature that cannot be switched off; it blocked switch-off isolation of a crash |
| Family | Music and sound (`audio`) |
| Playtest version | v0.0.36-dev3 |
| From commit | source 3b5e7a9, engine 3b5e7a9, CHIM world 3b5e7a9 |
| CHIM engine version | CHIM 0.1.0, engine 3b5e7a9, world format 0.7 |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.39 (14 October 2026)._

## Status: 11 October 2026

Partly repaired in source on v0.0.36-dev3-crash: `dbg music on|off` (console variable `aw_music`). The audio settings menu switch and the builder option follow in a later version.

## Symptom

There is no way to turn the soundtrack off: no console variable, no Options entry, no builder option. The only way
is to remove `music/playlist.txt` from the boot disk, so that `CDAudio_Init` finds no playlist.

## Where

`engine/aga/src/aw_music.c`, `CDAudio_Init` (music is available whenever the playlist parses);
`bgmvolume` only scales the output, the stream is still read.

## How it happened

The soundtrack player grew from a fixed CD-audio replacement; it was always on, and nothing asked for a switch until a
fault had to be isolated feature by feature.

## Why it was not caught

The rule that every feature stays selectable (DON'T DELETE ANY METHOD, shipped features default on with an opt-out)
was not checked for the soundtrack; no test lists the features without an off switch.

## Reproduction

Start any build and look for a music cvar or option: none. While isolating
[CHIM-DEV3-MAPLOAD-CRASH-36](CHIM-DEV3-MAPLOAD-CRASH-36.md) the "music off" variant had to be made by deleting
`music/playlist.txt` from a play copy of the boot disk (with it gone, the faulty engines loaded maps fine).

## Repair

Done (v0.0.36 line): `dbg music on|off` (also `true`/`false`, `1`/`0`; no argument shows the switch and the
stream status) through the existing `aw_music_status` handler, and the console variable `aw_music` (default on, not
saved). Off closes the stream; a read still outstanding is abandoned into its own packet and buffer and closed when its
reply comes; no stream is opened and no read sent until on again. Tests: the "switch" case of the music player test
(a read held outstanding while the music goes off), `tests/test_music_switch.py` and the console translation test.

Planned (a later version, not v0.0.36): background music on/off in the in-game audio settings menu, next to the
volume controls, saved with the player's settings; the same switch as a console variable (and a `dbg` line) and a
builder option that sets its default in the game config. Off means no stream is opened and no read is sent. A test
checks exactly that. Listed in the [roadmap](../ROADMAP.md).

## Verification

Open.

## Prevention

Open: a test over the engine's feature list that every shipped feature has an off switch.

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
- DOOR-AUDIO-SECOND-COPY-48 (no report page): The door audio stage converts its own copies of the 10 door sounds the media stage already converted (166,338 bytes stored twice)
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

Related bugs in other categories:

- [CHIM-DEV3-MAPLOAD-CRASH-36](CHIM-DEV3-MAPLOAD-CRASH-36.md): v0.0.36-dev3 image: the emulator exits about 2 s after a map load (JIT preset); the game stops advancing on the cycle-exact preset
- [DOCS-ROADMAP-IMPLEMENTATION-39](DOCS-ROADMAP-IMPLEMENTATION-39.md): Roadmap retains obsolete implementation and coverage claims

<!-- END GENERATED CATEGORY -->
