# AUDIO-LOAD-29: OST crackles under heavy loading

<!-- BEGIN GENERATED PERSISTING: edit the reports list in docs/bugs/bugs.json (bug_register.py report), then run tools/bug_register.py render -->

## PERSISTING: reported 2 times; something has to be done

- Reported with v0.0.51-dev1 at 2026-10-25 01:16 +0300: v0.0.51-dev1 image, FS-UAE 32 MB, same five loads: longest gaps 44-121 ms after the first load (319 ms), 0 late in every load; the first load printed 'music ran dry 1 times'. WinUAE listen pending
- Reported with v0.0.51-dev2 at 2026-10-25 03:53 +0200: dev2, FS-UAE 32 MB: first load of a session 310 ms, music ran dry 3 times (311 ms, 2 on the chamber run; dev1 319 ms, 1); later loads 39-129 ms, 0 late

<!-- END GENERATED PERSISTING -->

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | maintainer |
| First noticed | 6 October 2026, in v0.0.29-rc1 |
| Where | Music mixer during heavy loads (ship hull to deck, entering Census office) |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.29-rc1, v0.0.29-rc2, v0.0.30-rc1 (last seen) |
| Severity | high: The music never crackling through loads is the project s golden standard (the maintainer, 24 October 2026); the opening is the first thing every player hears |
| Family | Music and sound (`audio`) |

<!-- END GENERATED FACTS -->

_Last updated with AmiWind v0.0.51 (25 October 2026)._

## Status: 25 October 2026

Open. Fixed in part on v0.0.51: the CHIM world's large reads (rooms, frames, models) now go in slices with the
music fed between them, as the other loads already did, and every load prints one "Loading audio" line. The
maintainer's listen on WinUAE through the opening (ship hull to deck, the census office) decides; it is pending.

## Symptom

The background music crackles while the game loads a place, most of all through the opening: from the ship's hull
to its deck and into the census office (the maintainer, from v0.0.29-rc1 on). The music never crackling through a
load is the project's golden standard.

## Measured

Every load prints `Loading audio: N mixer updates, longest gap X ms (mixes Y ms ahead), K late (...), music ran dry
D times`: the longest time the music went without being fed, whether any sound came late, and how often the mixer
had nothing left to play.

FS-UAE, 32 MB of Fast RAM, the same five loads (the default smoke's two maps and the scripted five-load run):

| Build | First load of the session | Later loads | Late |
| --- | --- | --- | --- |
| v0.0.50 engine (no slices), v0.0.50 image | Seyda Neen 216 ms | ship 39, census 55, Akulakhan's Chamber 218, Balmora 205 ms | 0 |
| v0.0.51 engine (slices), the same image | Seyda Neen 221 ms | ship 37, census 52, Akulakhan's Chamber 204, Balmora 46 ms | 0 |
| v0.0.51-dev1 | 319 ms, ran dry once (the intro movie, see below) | 44-121 ms | 0 |
| v0.0.51-dev2 | 310 ms, ran dry 3 times (the intro movie, see below) | 39-129 ms | 0 |
| v0.0.51 meter leaving the movie out, the dev2 image | 58 ms outside a 4,893 ms intro movie, ran dry 3 times | 43, 52, 115 (Akulakhan's Chamber), 49 ms | 0 |

**The first load's long "gap" was the intro movie.** The first load of a session is New Game: after the map loads,
the intro movie plays inside the same load. It pauses the music and the mixer plays the movie's own sound, but the
meter went on timing the paused music, so every first load showed 219-319 ms and the music "running dry". The line
now names the load step at both ends of the longest gap, prints the ticks inside a gap over 150 ms, and leaves the
movie's time out (the line says how much). Measured that way, no load starves the music for longer than 115 ms in
FS-UAE. Whether the movie's own sound crackles is a separate question for the listen. The 3 "ran dry" counts of the
first load outside the movie are not explained yet (most likely the music restarting after the movie).

## Where

The music mixer (engine/aga/src/snd_dma.c) during blocking loads: map loads, model and room reads
(chim/chim_world.c Chim_PackReadRaw, read in slices since v0.0.51), and the first load after the game starts.

## Next

The WinUAE listen through the opening (the intro movie's own sound included); the first load's dry counts after
the movie.

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
- CUSTOM-OST-SLOT-53 (no report page): Requested: a custom OST slot: the user's own track built into the image and a player routine for it, apart from the playlist
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

Related bugs in other categories:

- [SEYDA-LOAD-HANG-30](SEYDA-LOAD-HANG-30.md): Rare freeze during a Seyda Neen region load

<!-- END GENERATED CATEGORY -->
