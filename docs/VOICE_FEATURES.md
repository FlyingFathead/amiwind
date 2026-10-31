# Voices and sounds

_Last updated with AmiWind v0.0.58-dev1 (31 October 2026)._

<!-- Generated whole by tools/voice_features.py render from docs/voice-features.json; do not edit by hand. -->

Every voice moment and character sound the original game plays, row by row: what the build maps, whether it has been heard in a build, and the proof. The reference for when a sound plays is OpenMW 0.51 as written down in docs/COMBAT.md, docs/ANIMATION.md and docs/NPC_VOICE_TABLE.md, and the builder's fallback test (tests/test_greeting_lut.py); the OpenMW source itself is not available on the build machine, so no row cites it line by line. Tribunal and Bloodmoon voices are out of scope until the expansions' NPCs are in the built world (NPC-VOICE-TABLE-ADDONS-54).

**23 rows:** 8 mapped, 9 in-source, 1 silent, 2 not-built, 2 silent-by-design, 1 out-of-scope.

## Measured on the game data

The v0.0.57 release image's voice table, read back: 2,673 NPCs (2,675 from v0.0.58 with the two Orcs), every one with a voiced line (hit and attack 2,673, hello 2,648, idle, intruder, thief and flee 2,654); 396 creatures, every one with a sound (1,321 moments of their own, 1,760 by the shared fallback); 599 of the 601 sound records mapped; one named voice file the game data does not have (vo/d/f/Hit_DF007.mp3).

## States

- `heard`: heard in a build, with its proof
- `mapped`: mapped and wired in the engine; not yet heard in a build
- `in-source`: new in source on this line; not yet in a build
- `silent`: the original plays it; nothing plays it here yet
- `not-built`: the system that plays it is not built yet
- `silent-by-design`: silent in the original too, with the reason
- `out-of-scope`: not in this release, with the reason

## NPC voices

| Moment | State | Mapped | Proof | Bugs |
| --- | --- | --- | --- | --- |
| Hello: the greeting said as the player comes near | `in-source` | the voice table's first match for every NPC, town residents too (world.qc aw_greet, aw_glut.c AW_GlutSay); no gap across all actors since v0.0.58 | native test tests/aga_glut_test.c (glue: the hello said with its voice, quiet when the build lacks the file); tests/test_greeting_lut.py EngineSource; not yet heard in a build | [NPC-GREETING-PICK-33](bugs/NPC-GREETING-PICK-33.md) |
| Conversation greeting (Greeting 0 to 9) | `mapped` | voice table greeting lists; the dialogue window opens with it | tests/test_greeting_lut.py conversation greeting lists; the v0.0.57 release table read back: all 26 Dreamers open with their own Sixth House greeting | [NPC-DREAMER-GREETING-DEFAULT-42](bugs/NPC-DREAMER-GREETING-DEFAULT-42.md) |
| Idle lines | `mapped` | world.qc aw_npc_idle calls the idle bark (OpenMW Actors::playIdleDialogue odds, sight and range in aw_anim.c) | not yet heard in a build | [NPC-VOICE-BARKS-33](bugs/NPC-VOICE-BARKS-33.md) |
| Attack: the fight starts (always) and a new swing (10 %) | `mapped` | aw_combat.c voice hook to aw_anim.c combat_voice | native glue test plays an attack bark; not yet heard in a build | [NPC-VOICE-BARKS-33](bugs/NPC-VOICE-BARKS-33.md), [COMBAT-VOICES-SILENT-33](bugs/COMBAT-VOICES-SILENT-33.md) |
| Hit: health lost (30 %) and death (always) | `mapped` | aw_combat.c voice hook (AW_VOICE_HIT, AW_VOICE_DEATH) | not yet heard in a build | [NPC-VOICE-BARKS-33](bugs/NPC-VOICE-BARKS-33.md), [COMBAT-VOICES-SILENT-33](bugs/COMBAT-VOICES-SILENT-33.md) |
| Flee | `mapped` | aw_combat.c voice hook (AW_VOICE_FLEE) when a fighter turns to flee | not yet heard in a build | [NPC-VOICE-BARKS-33](bugs/NPC-VOICE-BARKS-33.md) |
| Intruder and Thief lines | `silent` | in the voice table for 2,654 NPCs; no engine event says them | found by reading the engine's voice calls | NPC-VOICE-INTRUDER-THIEF-NO-EVENT-58 |
| Alarm | `silent-by-design` | the data's one Alarm line has no NPC that can say it | voice table read back: 0 NPCs with an Alarm line | - |
| The two Orcs with accented record ids (atúlg gro-largúm, yatúr gro-shak) | `in-source` | in the voice and the dialogue table since v0.0.58 (Windows-1252 ids) | tests/test_greeting_lut.py and the native lookup in tests/aga_glut_test.c; not yet heard in a build | [NPC-VOICE-NONASCII-IDS-48](bugs/NPC-VOICE-NONASCII-IDS-48.md) |
| A voice the game data itself lacks (vo/d/f/Hit_DF007.mp3) | `silent-by-design` | named in tools/greeting_lut.py MISSING_IN_GAME_DATA with its reason | GOG and Steam loose files run Hit_DF006 then Hit_DF008; none of the three archives has it | [AUDIO-MISSING-SOURCES-32](bugs/AUDIO-MISSING-SOURCES-32.md) |

## NPC and creature sounds

| Moment | State | Mapped | Proof | Bugs |
| --- | --- | --- | --- | --- |
| NPC footsteps by boots, water and swimming | `mapped` | the layout's left and right keys and their files (aw_anim.c, aw_npc_footsteps) | docs/ANIMATION.md Footstep sounds | - |
| Creature footsteps and swimming | `in-source` | the creature layouts' soundgen keys, played from the voice table's creature row | tests/test_creature_tables.py SoundEventTests, tests/aga_glut_test.c; not yet heard in a build | CREATURE-ANIM-SOUND-54 |
| Creature moan, roar, scream and land | `in-source` | the same keys in idle, attack, hit and jump groups, in walks, fights and forced groups | tests/test_creature_tables.py, tests/aga_glut_test.c (the rat's moan); not yet heard in a build | CREATURE-ANIM-SOUND-54 |
| A creature without its own sound generator borrows (its original's, then one sharing its model, then the generic) | `mapped` | builder rule in tools/greeting_lut.py sound_table (docs/COMBAT.md Sounds) | tests/test_greeting_lut.py test_fallback_rule; 1,760 fallback moments in v0.0.57 | - |

## Combat sounds

| Moment | State | Mapped | Proof | Bugs |
| --- | --- | --- | --- | --- |
| Swing swish, the armour piece struck, blocks, Health Damage, critical | `in-source` | aw_combat.c AW_CombatSwingSounds, OpenMW's set; off by default until the in-game check (dbg combat sounds) | tests/test_combat.py; one blow's sounds no longer cut each other | COMBAT-SOUNDS-RULE-OFF-58, AUDIO-LOCAL-SOUND-CUTS-58 |
| Punches (Hand To Hand Hit 1 and 2) | `in-source` | with the combat set | not yet heard in a build | PUNCH-AUDIO-COVERAGE-29 |
| Knockdown and death from the animation's own sound keys | `not-built` | Body Fall Medium played by the combat layer when the knockdown or the death starts, not at the animation's key; the NPC layouts carry only the step keys, and adding the others re-keys every NPC model stage, so it waits for the next NPC stage change | docs/COMBAT.md Sounds | - |
| Bow, crossbow and thrown: draw, shoot, projectile hit | `not-built` | no ranged combat yet | - | - |
| Spell cast and hit by school | `mapped` | aw_magic.c effect sounds per phase; a sound of no entity no longer ends the NPCs' voices | tests/aga_sfx_names_test.c (no voice ended by a -1 sound); not yet checked against every school in a build | AUDIO-MAGIC-STOPS-SPEECH-54 |

## Player

| Moment | State | Mapped | Proof | Bugs |
| --- | --- | --- | --- | --- |
| The player's pain grunts and death line; the enemies' taunts | `in-source` | the player's Hit line by his race and sex (id1/npc-voice-player.txt, tools/greeting_lut.py player_voices) when hurt (30 %) and when killed; the enemies' Attack lines on the fight start and new swings. An approximation: the original filters the Hit infos with the player himself as speaker (race and sex, and also his class, faction, rank and the infos' other conditions); the voice table bakes each NPC's filter into its audience at build time and carries no race or sex condition, so AmiWind borrows the lines of the faction-less NPC of that race and sex with the commonest Hit set. It differs where a Hit info is limited to a class, a faction the player joins, or a condition on the speaker that the borrowed NPC passes and the player would not (or the reverse) | tests/test_greeting_lut.py, tests/aga_glut_test.c (a Breton man speaks a Breton man's lines); not yet heard in a build | [COMBAT-VOICES-SILENT-33](bugs/COMBAT-VOICES-SILENT-33.md) |
| The player's own footsteps | `in-source` | aw_glut.c by boots and water; off by default: dbg footsteps, Options > Audio, saved | tests/aga_glut_test.c step slots; not yet heard in a build | PLAYER-FOOTSTEPS-NONE-58 |

## Mixer

| Moment | State | Mapped | Proof | Bugs |
| --- | --- | --- | --- | --- |
| More than 512 different sounds in one session | `in-source` | snd_dma.c S_FindName reuses a slot nothing holds (decided for the project, 31 October 2026: option (a), no bigger table). The measurement is the console line 'Sound table full (512 names, none free)', printed only when no slot can be freed; the voices-only catalogue (option (c)) is the next step only if a long Pi session ever shows that line | tests/aga_sfx_names_test.c (2,513 names) | AUDIO-SFX-NAME-TABLE-FULL-58 |

## Out of scope

| Moment | State | Mapped | Proof | Bugs |
| --- | --- | --- | --- | --- |
| Tribunal and Bloodmoon voices | `out-of-scope` | until the expansions' NPCs are in the built world | - | NPC-VOICE-TABLE-ADDONS-54 |
