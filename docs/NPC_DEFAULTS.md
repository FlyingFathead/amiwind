# The default NPC: stats, behaviour, sounds and movement as data

_Last updated with AmiWind v0.0.54-dev1 (27 October 2026)._

<!-- contents start -->
## Contents

- [The general stats model](#the-general-stats-model)
- [Behaviour ratings and packages](#behaviour-ratings-and-packages)
- [What the scripts do to NPCs](#what-the-scripts-do-to-npcs)
- [What they carry and fight with](#what-they-carry-and-fight-with)
- [Loading and assigning, per character](#loading-and-assigning-per-character)
- [Changed state](#changed-state)
- [Sounds and voices](#sounds-and-voices)
- [Movement](#movement)
- [Every item of the game, checked](#every-item-of-the-game-checked)
- [Gaps](#gaps)
- [Credits](#credits)

<!-- contents end -->

What every humanoid NPC of Morrowind, Tribunal and Bloodmoon has, what the values usually are, and how AmiWind keeps
them as build-time tables the engine looks up instead of reading the game records. The maintainer asked for it on
27 October 2026 ("what are they up to by default", "the general stats", "how to load and assign per character and
have the changed states", "all the possible sounds", "the movements they make"). The record itself, its file
sections and its calls are in [ACTOR_STATE.md](ACTOR_STATE.md); this page is the model behind it and the measured
defaults. Everything was counted on the game data (3,041 NPC records, 27 October 2026); no character is listed.

Where the original game and OpenMW differ, OpenMW's rule is AmiWind's. The original's behaviour was checked against
the local copy of the UESP wiki, the rules against OpenMW 0.51's source; nothing of either is copied.

## The general stats model

Every NPC has the same fields. All of them are in its 96-byte ACTB row ([ACTOR_STATE.md](ACTOR_STATE.md#the-file)),
written once by the builder; the engine never reads an NPC record.

| Field | Range | Typical (median; 10 % to 90 %) | Rule |
| --- | --- | --- | --- |
| Level | 0 to 99 | 10 (3 to 23) | the record's |
| 8 attributes | 0 to 100 (records up to 255) | Strength 59, Speed 63, Luck 40; level 1 to 5: about 45 | autocalc from race, sex, class, level |
| 27 skills | 0 to 100 | Athletics 35, Block 25, Light Armor 23; the best skill 54 | autocalc from class majors, minors, specialization |
| Health | | 93 (46 to 199); level 1 to 5: 52 | (Strength + Endurance) / 2 + level step x (level - 1) |
| Magicka | | 100 (78 to 160) | Intelligence x fNPCbaseMagickaMult (2) |
| Fatigue | | 219 (164 to 310) | Strength + Willpower + Agility + Endurance |
| Hello, Fight, Flee, Alarm | 0 to 100 | 30, 30, 30, 0 | the record's (AIDT) |
| Disposition | 0 to 100 | 50 | the record's |
| Race, class, faction, rank, reputation, sex | | 10 races, 82 classes; 1,926 with no faction; 1,172 women | the record's |
| Inventory | entries into one shared item table | 6 entries | levelled lists resolved at the NPC's level |
| Spells | entries into one shared spell table | 2 (the race's powers) | the record's plus the race's |
| Gold | | 0 for 2,682 of 3,041 | the record's |

- **Autocalculated or fixed.** 1,939 NPCs (64 %) carry only a level and let the game compute the rest; 1,102 carry
  every value. The autocalculation is OpenMW's (rule from OpenMW file apps/openmw/mwclass/npc.cpp,
  autoCalculateAttributes and autoCalculateSkills): attributes grow with the level by the class's skills and stop
  at 100; health's level step is 3, plus 2 for a combat class or 1 for a stealth class, plus 1 when the class favours
  Endurance. The original describes the step without that last point; OpenMW's rule is ours.
- **What the levels mean.** 792 NPCs are level 1 to 5, 865 level 6 to 10, 1,050 level 11 to 20, 334 above.
  Health by level band (median): 52, 84, 125, 240.
- **Not yet.** Autocalculated NPCs' spells (rule from OpenMW file apps/openmw/mwmechanics/autocalcspell.cpp) are not
  made; only the record's and the race's spells are in the table.

## Behaviour ratings and packages

The four ratings and the AI packages decide what an NPC does when nobody scripts it.

| Rating | Usual values | What it does (rule) |
| --- | --- | --- |
| Hello | 30 for 2,576; 0 for 340 | greets the player within Hello x iGreetDistanceMultiplier (6) original units: 180 units for 30 (OpenMW mwmechanics/actors.cpp) |
| Fight | 30 for 1,805; 90 for 778; 100 for 57 | attacks on sight when Fight plus a distance bias (iFightDistanceBase 20, less with distance) plus a disposition bias ((50 - disposition) x fFightDispMult 0.2) reaches 100 (OpenMW mwmechanics/mechanicsmanagerimp.cpp isAggressive): a Fight-90 NPC attacks a nearby player, a Fight-30 one only when attacked |
| Flee | 30 for 2,427; 0 for 242 | 100 always flees; below that the flee wish grows as health falls (fAIFleeHealthMult 7; OpenMW mwmechanics/aicombataction.cpp) |
| Alarm | 0 for 1,943; 90 for 494; 100 for 477 | 100 reports every crime it sees; lower values scale the disposition and Fight changes a crime causes (OpenMW mwmechanics/mechanicsmanagerimp.cpp) |

Packages (the record's AI_W, AI_T, AI_F, AI_E, AI_A):

| | NPCs |
| --- | ---: |
| One wander package | 2,935 |
| No package (stands) | 31 |
| Two or more (travel or follow chains) | 75 |
| Wander entries / travel / follow / escort / activate | 2,934 / 149 / 83 / 0 / 0 |

- **Wander.** Distance median 126 original units (0 for 841 NPCs: they stand and idle in place; 512 at 90 %),
  duration 5 hours, every one repeats. The eight idle chances (Idle2 to Idle9) average 58, 20, 11, 9, 1, 1, 1 and 3:
  most NPCs mostly play the first idle. Rule (OpenMW mwmechanics/aiwander.cpp getRandomIdle): an idle is tried with
  probability fIdleChanceMultiplier (0.75); each of the eight rolls 0 to 100 and the highest roll under its own
  chance wins.
- **Services** (AIDT flags): 308 NPCs train, 211 sell ingredients, 208 potions, 143 weapons, 142 armour; the
  travel service NPCs carry 117 destinations.

## What the scripts do to NPCs

1,096 NPCs (36 %) name a script; 396 different scripts. Grouped by what each script does first (one group each):

| What the script does | Scripts |
| --- | ---: |
| Starts a fight or sets the Fight rating | 91 |
| Presence or schedule: enables, disables, moves, reads the hour | 79 |
| Reacts to a death (journal, quest) | 58 |
| Changes the AI package (wander, travel, follow, escort) | 54 |
| Greets or says a line | 43 |
| Other (dialogue state, items) | 61 |
| A marker for the dialogue only | 10 |

The functions they call most (scripts using it): GetJournalIndex 237, Journal 174, OnDeath 156, Disable 127,
GetDistance 106, Enable 86, ForceGreeting 81, StartCombat 72, GetDeadCount 58, AiWander 55, SetFight 49, Say 43,
StopCombat 29, SetHello 29, AiTravel 16, AddItem 16, AiFollow 12. The compiled forms and which of them run are in
[MWSCRIPT_BYTECODE.md](MWSCRIPT_BYTECODE.md#what-runs-today-what-is-not-yet).

## What they carry and fight with

The worn weapon is the best melee weapon the NPC carries and the armour the first piece of each slot, no shield with a
two-handed weapon (the combat sheets' rule, `tools/prepare_combat.py`).

| Weapon type | NPCs |
| --- | ---: |
| None (hand-to-hand, or only a bow or thrown weapons) | 1,139 |
| Short blade | 647 |
| Long blade, one-handed | 320 |
| Axe, one-handed | 249 |
| Axe, two-handed | 175 |
| Blunt, one-handed | 135 |
| Long blade, two-handed | 124 |
| Blunt, two-handed (staff) / (hammer) | 112 / 71 |
| Spear | 69 |

By class: warriors and guards carry long blades, barbarians and battlemages axes, miners two-handed axes, sorcerers,
spies and assassins short blades; commoners, slaves, nobles and acrobats mostly fight bare-handed. 1,508 NPCs wear
no armour (median 1 piece, 7 at 90 %); clothing median 3 pieces.

## Loading and assigning, per character

```
build time                                   run time (aw_actorstate.c, aw_mwhost.c)
NPC_ + RACE + CLAS + SKIL + LEVI + GMST      an actor spawns: its edict carries its record id and placed reference
  -> autocalc, levelled lists, equipment     first need (a script names it, a fight starts):
  -> ACTB row (96 B), AINV (6 B an entry),     binary search of ACTB by id (12 disk reads at most), once
     AITM / ASPT shared rows                   the row is copied into a live record (268 B) in a pool of 128
  -> id1/mwscript.awm, on disk               every later call: the live record, no disk read
```

- **Which row.** The actor's id, folded, binary-searched in ACTB; the row is cached per script instance. Placed
  actors are told apart by their placed reference, so two copies of one NPC have two live records.
- **What the engine computes and what it reads.** Everything above is read; the engine computes only the scripts'
  derived values (the modified attribute, the ratio of a dynamic stat) and the walk speed.
- **Cost on the Amiga.** About 607 KB on disk for all 3,437 actors; resident only the 128 live records, the dead
  counts and the script targets (about 43 KB, plus the 64 KB of saved-game buffers). No lookup per frame: a fight syncs its fighters' health into their
  records once a frame, scripts read the live record directly.

## Changed state

| Change | Where it is kept | Saved | Notes |
| --- | --- | --- | --- |
| Damage, health, magicka, fatigue | live record (and the fighter sheet while it fights) | yes | |
| Death | live record and the dead count of the id | yes | OnDeath reads it once |
| Attribute, skill, level, rating, disposition changes by scripts | live record | yes | |
| Items given or taken by scripts | up to 12 item changes per actor | yes | |
| Spells added or removed by scripts | up to 8 spell changes per actor | yes | |
| AI package changes (AiWander, AiTravel ...) | handed to the wander and combat code | no | |
| Position | the entity | no | |

A changed live record is never evicted; an unchanged one gives its place and is read again from its row. The changed
records are saved as one block of the save file (AWAS1, [ACTOR_STATE.md](ACTOR_STATE.md#saved-games)), keyed by the
placed reference, so they survive a cell change and a load. At 32 MB they stay resident (128 records, 34 KB); the
roadmap's disk offload of object state is not built.

What does not stick yet (see [Gaps](#gaps)): the record is written but a spawning actor does not read it back, so a
killed NPC or a lowered health returns as the record's default when the cell is entered again or a save is loaded;
and nobody but the scripts changes an NPC's items (no looting or pickpocketing yet).

## Sounds and voices

| Sound | How it is picked (rule) | Table | In the engine |
| --- | --- | --- | --- |
| Hello, Idle, Attack, Hit, Flee | the topic's lines in order, the first whose conditions pass, by the speaker's race and sex (OpenMW mwdialogue/filter.cpp); odds iVoiceAttackOdds 10 %, iVoiceHitOdds 30 %, fVoiceIdleOdds 10 | `id1/npc-voices.lut` ([NPC_VOICE_TABLE.md](NPC_VOICE_TABLE.md)) | yes (since v0.0.48) |
| Thief, Intruder | on a crime the NPC sees (OpenMW mwmechanics/mechanicsmanagerimp.cpp) | same table | no: no crimes yet |
| Conversation greeting (Greeting 0 to 9) | the first passing line of the ten topics in turn | same table | text; a few recorded |
| Footsteps | by boots weight class or barefoot, water, swimming (OpenMW mwclass/npc.cpp getSoundIdFromSndGen) | the model's layout file | yes ([ANIMATION.md](ANIMATION.md#footstep-sounds)) |
| Weapon swings, hits on armour, creature sounds | fixed records and sound generators (below) | `id1/npc-voices.lut`, decided (below) | the combat work of v0.0.54 |

The game has 6,392 voice lines: Hello 4,058, Idle 1,082, Attack 490, Hit 437, Flee 153, Thief 120, Intruder 51 and
one Alarm line no NPC can say; every race and sex has its own set (about 14 to 32 attack, 18 hit, 5 to 9 flee lines
each), plus 5,175 conversation greeting entries.

### How the game names its sounds

Three kinds of records name every sound an actor makes; nothing is chosen by file name alone.

- **Voices: dialogue of type Voice.** Eight topics (Hello, Idle, Attack, Hit, Flee, Thief, Intruder, Alarm). Each
  line is an INFO entry with filters: the speaker's id, race, class, faction and rank, sex, cell, the player's
  faction and rank, a minimum disposition, and up to six conditions on functions or variables (health, distance,
  journal, items, globals, Random100 ...). The first entry that passes is said (OpenMW mwdialogue/filter.cpp). The
  conversation greeting is the same search over the ten Greeting topics.
- **Creatures: sound generators** (SNDG records, 293 in the masters): a creature id and one of eight moments: left
  foot, right foot, swim left, swim right, moan, roar, scream, land. Counted: 75 moan, 75 roar, 73 scream, 26 and 24
  foot, 18 land, 1 and 1 swim. A creature uses its own id's generators, else those of the creature it was copied
  from, else those of another creature with the same model, else the 14 generic ones with no creature (rule from
  OpenMW mwclass/creature.cpp getSoundIdFromSndGen); 348 of the 396 creatures have their own or their original's.
  NPCs have no generators: their body sounds are fixed records.
- **Fixed sound records the engine names** (SOUN records by id, rule from OpenMW mwmechanics/combat.cpp and
  character.cpp, mwclass/npc.cpp): a swing (Weapon Swish), a blocked or armoured hit by the armour's or shield's
  weight class (Light, Medium or Heavy Armor Hit, the class from iShieldWeight and the other slot weights with
  fLightMaxMod and fMedMaxMod), a bare-handed hit (two variants), Health Damage, the bow and crossbow pull and shot,
  landing (DefaultLand, DefaultLandWater), the footsteps (bare, light, medium, heavy, water; swim left and right) and
  an item's draw and put-away sound by its type (44 records). The odds of the voice moments are game settings
  (iVoiceAttackOdds, iVoiceHitOdds, fVoiceIdleOdds).

### How AmiWind stores them

One rule: the builder resolves every name to a sound file of the media pool the image already ships
(`sound/pool/a<16 hex>.wav`) and the engine reads indexes, never names.

| Part | Where | Row |
| --- | --- | --- |
| Voices and greetings, per NPC record | `id1/npc-voices.lut` ([NPC_VOICE_TABLE.md](NPC_VOICE_TABLE.md)) | the record's candidate lists; run-time conditions as condition records |
| Footsteps and the voice lines of a model | its layout file `<model>.anm` ([ANIMATION.md](ANIMATION.md#the-layout-file)) | sound per event |
| Creature generators and the fixed combat sounds | decided (27 October 2026, 16:31 +0200 / 14:31 UTC): a new section of `id1/npc-voices.lut`, with the format version raised: eight pool indexes for each creature row of the actor table (16 bytes; the fallback is resolved by the builder), from all three masters, plus one fixed list of the engine's named sounds and one row per sound record (file, length, volume, hearing distances) for the scripts. It replaces the combat sheets' own sound generator list and the scripts' own sound copy, so there is one table | written by the builder since v0.0.54 ([NPC_VOICE_TABLE.md](NPC_VOICE_TABLE.md#the-sound-table-version-2-27-october-2026)); the combat work plays it and the scripts' Say and PlaySound move onto it |

## Movement

| Moment | Groups | How it is chosen (rule) | In the engine |
| --- | --- | --- | --- |
| Standing | idle, Idle2 to Idle9 | the wander package's idle chances (above; OpenMW mwmechanics/aiwander.cpp) | first idle only ([ACTOR-WANDER-AGGRO-52](bugs/ACTOR-WANDER-AGGRO-52.md)) |
| Moving | walk, run, swim (forward; back, left, right) | the package moves the NPC; speed: walk = fMinWalkSpeed 100 + Speed x (fMaxWalkSpeed 200 - 100) / 100, run = walk x (fBaseRunMultiplier 1.75 + Athletics / 100) (OpenMW mwclass/npc.cpp): about 163 and 342 original units a second for the typical NPC | walk and run by speed ([ANIMATION.md](ANIMATION.md#choosing-a-group)) |
| Fighting | the weapon type's stance and attacks, hand-to-hand, block | the worn weapon's type | see the animation coverage work |
| Hit, knocked down, dying | hit1 to hit5, knockdown, death1 to death5 | a random variant (OpenMW mwmechanics/character.cpp) | one variant each; the random ones not yet |
| Talking, own animations | the NPC's own animation file (dancers) | the record | see the animation coverage work |

The full list of groups and what plays each, measured, is the animation coverage work of v0.0.54
([ANIMATION.md](ANIMATION.md#not-done-yet) until it lands).

## Every item of the game, checked

`tools/item_coverage.py` checks every item record of the three masters against AmiWind's tables and an image; its
test is `tests/test_item_coverage.py`. Lights that cannot be carried (519) are scenery and left out. Measured on the
v0.0.53 release image, 27 October 2026:

| Type | Records | Shared item table | Carried by an NPC | Inventory catalogue | World model | Icon | Held model | Placed | Takeable |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Weapons | 616 | 403 | 368 | 485 | 0 | 1 | 368 | 291 | 1 |
| Armour | 408 | 334 | 314 | 280 | 0 | 1 | 48 of 65 shields | 227 | 1 |
| Clothing | 581 | 391 | 379 | 510 | 4 | 4 | | 224 | 3 |
| Misc | 585 | 216 | 207 | 536 | 1 | 1 | | 352 | 1 |
| Books | 635 | 222 | 197 | 574 | 3 | 3 | | 455 | 0 |
| Potions | 264 | 95 | 94 | 258 | 0 | 0 | | 233 | 0 |
| Ingredients | 126 | 99 | 97 | 95 | 0 | 0 | | 91 | 0 |
| Lockpicks, probes, repair | 18 | 15 | 14 | 0 | 0 | 0 | | 14 | 0 |
| Carried lights | 157 | 4 | 4 | 0 | 0 | 0 | | 144 | 0 |
| All | 3,390 | 1,779 | 1,674 | 2,738 | 8 | 10 | 416 | 2,031 | 6 |

So: every item an NPC carries or a script names is in the shared item table, and every carried weapon mesh that a
placed resident holds has its held model; but the game's items are not yet things the player can see, hold or take.

## Gaps

- **The record is not read back when an actor spawns** (a killed NPC comes back, a lowered health is restored on the
  next cell entry or load); combat starts from its own sheets, not the record. Next step of
  [ACTOR_STATE.md](ACTOR_STATE.md#next).
- **Ratings and packages are not executed**: Fight decides nothing on sight, wander distance and idle chances are
  unused ([ACTOR-WANDER-AGGRO-52](bugs/ACTOR-WANDER-AGGRO-52.md), v0.0.54's ambient and combat work).
- **Script package changes and positions are not saved**; script values are not saved
  ([MWSCRIPT-STATE-NOT-SAVED-48](bugs/MWSCRIPT-STATE-NOT-SAVED-48.md)).
- **More than 128 changed actors, 12 item or 8 spell changes on one actor**: further changes are dropped and counted.
- **Autocalculated NPCs' spells** are not made.
- **The voice table covers Morrowind's NPCs only** (2,673); the 368 Tribunal and Bloodmoon NPCs are silent.
- **The inventory catalogue** holds Morrowind's items only (no Tribunal or Bloodmoon items), and no lockpicks,
  probes, repair tools, apparatus or carried lights.
- **World models and icons** exist for the ten starting items only
  ([UI-ICONS-INVENTORY-42](bugs/UI-ICONS-INVENTORY-42.md)); placed items are not takeable
  ([INTERIOR-PLACED-ITEMS-47](bugs/INTERIOR-PLACED-ITEMS-47.md)); 17 of 65 shields and the carried weapons of
  actors not placed in the image have no held model.

## Credits

The rules were learned by reading OpenMW 0.51's source (GPL-3.0) and checked against the original game's
behaviour; AmiWind's builder and engine code are its own, nothing copied
([LICENSING_AND_CREDITS.md](LICENSING_AND_CREDITS.md)).
