# AUDIO-HOST-LOAD-33: Music and sound crackle when the emulator shares a fully loaded host CPU

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-dev |
| Where | Emulator audio output on a host PC whose CPU is saturated by other work |
| Reproduction | sometimes |
| Duplicate of | no |
| Persists in | v0.0.33-dev (last seen) |
| Severity | low: Test environment only: the game is clean on an unloaded PC; misleads audio playtests. |
| Family | Music and sound (`audio`) |
| Playtest version | CHIM Preview 1 |
| From commit | source 0f467e4, engine 0d8bf4f, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 0d8bf4f, world format 0.4 |
| Unknown because | the CHIM world receipt records no commit (CHIM-RECEIPT-COMMIT-33) |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open. Seen in CHIM Preview 1 on a PC running heavy builds; not seen on a second PC. The cause is the
host, not the game; a controlled A/B on one PC (idle against loaded) is still to be run before it is
closed.

## Symptom

The owner played CHIM Preview 1 (the v0.0.32 game with Balmora on CHIM, engine 0d8bf4f, world format
0.4) shortly after midnight on 9 October 2026 on the same PC that was running heavy build and test
jobs, with the host CPU at 100 %. Music and sound crackled and snapped throughout play, not only during
loads. The same build played on the owner's second PC, which ran nothing else, had clean audio.

## Where

The emulator's audio output on the host. The emulated Amiga, the game's mixer (snd_dma.c, snd_mix.c)
and the music data are the same on both PCs; only the host load differs. Not specific to CHIM: the
emulator needs host CPU time for every frame of audio whatever the game runs.

## How it happened

An Amiga emulator produces audio in real time: each emulated frame it must hand the host sound system
the next block of samples. With every host CPU thread busy with build containers, the emulator thread
is not scheduled in time, the host audio buffer runs dry, and the gaps are heard as crackle and snaps.
With JIT and unlimited CPU speed (the playtest profile, see
[BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md)) the emulator itself asks for a whole host core, so it
is the first to suffer when the host is saturated.

This differs from [AUDIO-LOAD-29](AUDIO-LOAD-29.md) and [WIN-05](../journals/BUG_JOURNAL-v0.0.29.md#win-05-intermittent-winuae-background-music-snapping---investigation-open):
those crackles happen inside the emulated machine (the game's mixer starves during blocking disk
loads) and are heard on an idle host; this one is continuous and disappears on an idle host.

## Why it was not caught

Playtests had so far run on a host with spare CPU, or with the builds paused. The project's CPU budget
for build jobs leaves only two host threads for the desktop and emulator, and critical builds may take
every thread while the owner plays elsewhere; nothing warned that the play PC was saturated.

## Reproduction

On one PC: play the same build idle, then with build containers holding every CPU thread at 100 %.
Not yet run as a controlled pair; the evidence so far is the owner's two PCs.

## Repair

None in the game. Play on a PC that is not running builds, or throttle the builds (lower their CPU
limits) while playing on the build PC.

## Verification

Pending: the controlled idle/loaded A/B on one PC, judged by ear, with host CPU load recorded.

## Prevention

Audio playtest reports note the host load. Audio judgements (this family) are made only on an
unloaded host, like emulator timings ([BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md)). When playing
on the build PC, build jobs are limited so that free threads remain for the desktop and emulator.

<!-- BEGIN GENERATED CATEGORY: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

## Bugs in the same category

Family: Music and sound (`audio`). The mixer must stay fed through loads and scene changes; music starts after loads settle. See [families](README.md#families).

- [AUDIO-03](AUDIO-03.md): Audio glitch at the post-movie load into the Jiub opening scene (WinUAE)
- AUDIO-APPEARANCE-29 (no report page): Music pause entering character race selection
- AUDIO-CLOCK-29 (no report page): Long audio DMA gaps lose elapsed playback time
- [AUDIO-DMA-CLOCK-DRIFT-35](AUDIO-DMA-CLOCK-DRIFT-35.md): The mixer estimates the audio DMA position from the EClock, not from the hardware, so the two can drift apart over a long session
- AUDIO-EFFECTS-DEFAULT-29 (no report page): Effects volume should default to 75%
- AUDIO-ENTER-29 (no report page): Sub-second soundtrack cut on Enter to follow the guard
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
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

Related bugs in other categories:

- [BENCH-JIT-PROFILE-32](BENCH-JIT-PROFILE-32.md): Every frame-rate and load-time figure was measured with the emulator at host speed

<!-- END GENERATED CATEGORY -->
