# COMBAT-AMBIENT-SPEECH-GATING-38: Ambient greetings and subtitles interrupt combat

<!-- BEGIN GENERATED FACTS: edit docs/bugs/bugs.json, then run tools/bug_register.py render -->

| Fact | Value |
| --- | --- |
| Reported by | owner |
| First noticed | 12 October 2026, in v0.0.38-dev2 |
| Where | Seyda Neen guard combat and nearby ambient speech |
| Reproduction | unknown |
| Duplicate of | no |
| Persists in | v0.0.38-dev2 (last seen) |
| Severity | medium: Unrelated greetings and subtitles interrupt a fight. |
| Family | Music and sound (`audio`) |
| Playtest version | v0.0.38-dev2 |
| From commit | source c2eaa5a, engine c2eaa5a, CHIM world c2eaa5a |
| CHIM engine version | CHIM unknown, engine c2eaa5a, world format unknown |
| Unknown because | CHIM version and format not yet transcribed into this report; exact dev2 receipt preserved. |
| Platform or emulator | unknown (Owner screenshot identifies dev2 but not the emulator.) |

<!-- END GENERATED FACTS -->

## Symptom

While fighting a guard in Seyda Neen, the owner still hears ordinary
greetings such as Yes, possibly from the opponent or nearby guards. The owner
requests combat-appropriate opponent speech while unrelated ambient voices and
speech text boxes are suppressed together. Exact actor attribution is unknown.

## Where

Seyda Neen combat, ambient speech and subtitles.

## How it happened

Source review, 13 October 2026: world.qc's aw_npc_idle, aw_greet and manual
aw_interact paths do not check AW_PlayerInCombat. AW_VoiceSay's idle path checks
distance and visibility but not combat. AW_CombatEngage stops the engaged
opponent's QuakeC idle think, but nearby residents continue polling. That is a
confirmed policy gap; the owner clip's exact speaker remains unknown.

Greetings use sound plus centerprint, while combat barks use the same entity
voice channel through a separate playback path. Generic centerprint does not
carry an actor or ambient-speech identity; its voiced label is inferred from
remaining speech time. Thus clearing every voice or text panel would also risk
unrelated combat, story or pickup feedback. Cancellation needs explicit ownership.

OpenMW 0.48 rejects greetings and idle lines for actors in combat. The owner's
requested suppression of unrelated nearby speech throughout the player's fight
is a wider AmiWind policy, not a claim that the original globally silences every
bystander. See the original [greeting and idle rules](https://raw.githubusercontent.com/OpenMW/openmw/openmw-0.48.0/apps/openmw/mwmechanics/actors.cpp).

## Why it was not caught

No verified multi-actor combat/ambient subtitle regression is attached.

## Reproduction

Repeat the owner scenario above in the delivered development build. Native reproduction remains pending.

## Repair

Introduce a coherent combat speech policy using the existing combat and
speech machinery. Verify original/OpenMW behavior before fixing policy details;
cover entering/leaving combat, opponent barks, other nearby actors and matching
subtitle suppression. Preserve ordinary speech after combat ends.

Reuse AW_PlayerInCombat for the encounter gate and the AmiQuake entity/channel
sound machinery. Track ambient audio and its own subtitle separately; reject
new ambient starts and cancel only owned ambient playback at combat entry,
while preserving opponent barks and other UI messages. Review queued server
sound/centerprint delivery as well as already playing channels. A prerequisite
[sound-stop indexing defect](AUDIO-STOP-CHANNEL-RANGE-39.md) was found in source;
its narrow candidate does not implement this full policy.

## Verification

Open, needs fixing. No repaired full package or native acceptance.

## Prevention

Add a regression that checks the delivered gameplay path and retains original-reference evidence.

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
- [AUDIO-STOP-CHANNEL-RANGE-39](AUDIO-STOP-CHANNEL-RANGE-39.md): Stopping an entity sound skips half the dynamic mixer slots
- [AW-20260928-02](AW-20260928-02.md): Dock/menu freeze and looping audio
- AW-20260928-15 (no report page): Prison wave ambience masks dialogue
- AW-20260929-03 (no report page): Music cuts during loading
- AW-20260929-05 (no report page): Ship waves too quiet
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

<!-- END GENERATED CATEGORY -->
