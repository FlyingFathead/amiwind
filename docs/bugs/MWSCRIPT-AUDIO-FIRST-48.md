# MWSCRIPT-AUDIO-FIRST-48: the game's scripts start no sounds, lines or music cues; MWScript compiled, audio first

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 23 October 2026, in v0.0.48-dev2 |
| Where | tools/mwscript, tools/prepare_mwscript.py, engine/aga/src/aw_mwvm.c and aw_mwhost.c |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.48-dev2 (last seen) |
| Severity | medium: the ambient loops, activator sounds, scripted NPC lines and music cues of the game's scripts are missing |
| Family | Music and sound (`audio`) |
| Playtest version | none: found in source (development branch, tests or gates), not in a playtest build |
| From commit | source 9b161ca, engine 9b161ca, CHIM world 9b161ca |
| CHIM engine version | CHIM 0.2.1, engine 9b161ca, world format 0.12 |
| Platform or emulator | not in game (found in source; the in-game check comes next) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.48-dev2 (23 October 2026)._

## Status: 23 October 2026

Open (feature). Implemented on the v0.0.48 MWScript branch: compiled by the builder in every build, run by the engine
only with `dbg mwscript on` (EXPERIMENTAL, off by default) until the in-game check in a MiniWind sandbox. Design and
measurements: [MWSCRIPT_BYTECODE.md](../MWSCRIPT_BYTECODE.md).

## What is missing

The maintainer, 23 October 2026: "all of the audio is already in the game so we should start utilizing it as per
MWscript". The converted sounds and voices are in the image, but nothing plays the ones the game's own scripts start:
ambient loops at sound markers (cave wind, water spouts, creaking boats, dripping), activator sounds, NPC lines spoken
by scripts, and music cues.

## What was done

- Every script of the three masters measured: 1,207 scripts, 251 distinct functions; 134 need only the interpreter,
  audio, journal and globals; 668 also need AI packages, inventory, combat, spells or positioning.
- `tools/mwscript/`: a compiler for MWScript as the game data uses it, quirks included; typed bytecode in one file,
  `id1/mwscript.awm` (156,838 bytes of code); every sound, voice and music name mapped to the media catalogue's
  converted file by index (81 of 82 sounds, 131 of 132 voice files; the rest have no source file).
- `engine/aga/src/aw_mwvm.c`, `aw_mwhost.c`: the interpreter and its game side; audio, journal, globals, timers,
  distance tests and the player's item counts run; other functions are logged once as "not yet".
- Builder stage `mwscript`, one unit reused from the pool when unchanged.

## Still to do

The in-game check (sounds, loops, ranges, frame time with and without), then the default; object state for the
not-yet functions most scripts use; the interpreter's values in saved games
([MWSCRIPT-STATE-NOT-SAVED-48](../BUGS.md)); scripted placements in rooms without an edict
([MWSCRIPT-INTERIOR-PLACEMENTS-48](../BUGS.md)).

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
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- MWSCRIPT-ONESHOT-SLOTS-LEAK-54 (no report page): Script one-shot sounds never freed their slot: after 32 distinct one-shots in a map new script sounds were dropped
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- SOUND-MARKERS-SILENT-48 (no report page): The original's sound markers are placed but silent: 2,163 in Morrowind (187 outdoors in 78 cells, 1,976 in 434 rooms), water under the Khuul pier, creaking under bridges and boats
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

Related bugs in other categories:

- AW-STATE-32-SLOTS-48 (no report page): The game state table holds 32 globals, 32 quests and 32 items; the game has 143 globals and 318 journal topics
- MWSCRIPT-DATA-UNKNOWN-NAMES-48 (no report page): Four Bloodmoon scripts read names declared nowhere in the game data and do not compile
- MWSCRIPT-INTERIOR-PLACEMENTS-48 (no report page): Scripted placements in rooms that have no edict are not attached: the engine has no room identity to match them (3,612 of 4,907 bindings are in rooms)
- MWSCRIPT-STATE-NOT-SAVED-48 (no report page): The compiled scripts' values (globals, object and script locals, journal indexes) are not in saved games

<!-- END GENERATED CATEGORY -->
