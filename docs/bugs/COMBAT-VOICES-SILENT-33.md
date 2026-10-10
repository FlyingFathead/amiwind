# COMBAT-VOICES-SILENT-33: Player pain grunts and hostile NPC taunts are not heard in fights

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 9 October 2026, in v0.0.33-rc1 |
| Where | engine/aga/src/aw_combat.c voice hook (no receiver); player hit voice |
| Reproduction | always |
| Duplicate of | no |
| Persists in | v0.0.33-rc1 (last seen) |
| Severity | medium: Fights are silent apart from impact sounds; the original voices hits, deaths and taunts. |
| Family | Music and sound (`audio`) |
| Playtest version | v0.0.33-rc1 |
| From commit | source 7ae3ea7, engine 7ae3ea7, CHIM world unknown |
| CHIM engine version | CHIM 0.1.0, engine 7ae3ea7, world format unknown |
| Unknown because | owner playtest report names no image commit or world format |
| Build note | owner playtest of a v0.0.33 build; the exact image commit is not in the report |

<!-- END GENERATED FACTS -->

## Status: 9 October 2026

Open (owner playtest). The NPC voice receiver (attack, hit, flee lines) exists on the animation kit line, not in v0.0.33; the player's own hit voice is not implemented anywhere.

## Symptom

In the playtest the player made no pain sounds when hit and hostile NPCs did not taunt.

## Where

engine/aga/src/aw_combat.c (aw_combat_voice hook has no receiver in the release line); player hit voice not implemented.

## How it happened

Sources (OpenMW 0.51): any actor that loses health from an attacker says a "hit" voice line with iVoiceHitOdds (mwclass/npc.cpp onHit; the player is an NPC there), and says "hit" again when its death animation starts (actors.cpp); a hostile says an "attack" line when it starts combat (mechanicsmanagerimp.cpp startCombat) and when attacking with iVoiceAttackOdds (aicombat.cpp). The lines come from the dialogue Voice topics for the actor's race and sex. AmiWind's combat layer only calls an optional hook, and the release line has no receiver; the player side was never wired.

## Why it was not caught

The voice receiver was split out to the animation kit job and was not in the release merge; no test checks that a fight produces voice.

## Reproduction

Always.

## Repair

Not yet. Merge the kit's receiver; add the player hit voice (race/sex Voice "Hit" lines, iVoiceHitOdds, not while already speaking); keep the original odds and the one-line-at-a-time rule.

## Verification

None yet: a fight fixture counts voice calls per event with the seeded rolls; an in-game clip with audio.

## Prevention

Combat and death behaviour follow the original rules with the source named (OpenMW source, game settings); every presentation change gets a fixture or an in-game clip.

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
- AW-20260928-02 (no report page): Dock/menu freeze and looping audio
- AW-20260928-15 (no report page): Prison wave ambience masks dialogue
- AW-20260929-03 (no report page): Music cuts during loading
- AW-20260929-05 (no report page): Ship waves too quiet
- [ENGINE-SOUND-NAME-SYSERROR-35](ENGINE-SOUND-NAME-SYSERROR-35.md): A sound name of 64 characters or more, or more than 512 sounds in a session, stopped the program
- [MUSIC-DEATH-SILENT-33](MUSIC-DEATH-SILENT-33.md): No death music when the player dies
- [MUSIC-OPENING-CLIP-31](MUSIC-OPENING-CLIP-31.md): A clip of another track plays while the opening scene loads
- [MUSIC-STARTUP-TRACK-31](MUSIC-STARTUP-TRACK-31.md): A random world track plays under the startup logo
- [NPC-GREETING-PICK-33](NPC-GREETING-PICK-33.md): Greetings take the highest disposition threshold at a fixed 50, OpenMW takes the first line that matches
- [NPC-VOICE-BARKS-33](NPC-VOICE-BARKS-33.md): NPCs never say their combat, hit, flee or idle voice lines
- PUNCH-AUDIO-COVERAGE-29 (no report page): Original punch swing/hit sound coverage unverified
- WIN-05 (no report page): Intermittent WinUAE background-music snapping

<!-- END GENERATED CATEGORY -->
