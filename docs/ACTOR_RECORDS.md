# What every being can have: the actor records

_Last updated with AmiWind v0.0.61-dev3 (2026-11-06)._

<!-- contents start -->
## Contents

- [How to read this page](#how-to-read-this-page)
- [Who has what](#who-has-what)
- [The NPC with stored stats (52-byte stats record, NPDT)](#the-npc-with-stored-stats-52-byte-stats-record-npdt)
- [The auto-calculated NPC (12-byte stats record, NPDT)](#the-auto-calculated-npc-12-byte-stats-record-npdt)
- [What every NPC record also holds](#what-every-npc-record-also-holds)
- [The creature (96-byte stats record, NPDT)](#the-creature-96-byte-stats-record-npdt)
- [The player](#the-player)
- [The race (RACE)](#the-race-race)
- [The class (CLAS)](#the-class-clas)
- [The birthsign (BSGN)](#the-birthsign-bsgn)
- [The behaviour data (AIDT)](#the-behaviour-data-aidt)
- [The flags and blood types](#the-flags-and-blood-types)
- [The spell lists (NPCS)](#the-spell-lists-npcs)
- [Derived values](#derived-values)
  - [An auto-calculated NPC](#an-auto-calculated-npc)
  - [The player at the start](#the-player-at-the-start)
  - [A creature's skills](#a-creatures-skills)
  - [Resistances and weaknesses](#resistances-and-weaknesses)
  - [What a missing value reads as](#what-a-missing-value-reads-as)
- [Part two: everything a being holds while the game runs](#part-two-everything-a-being-holds-while-the-game-runs)
- [Sources and method](#sources-and-method)

<!-- contents end -->

A full index of the values a being can hold: the player, the people (NPCs) and the creatures, and the records they are
made from (race, class, birthsign). Part one lists every field of every record type, with its type, the range found in
the game data, what reads it and how AmiWind holds it. Part two lists the derived values, the formulas that turn a
short record into a full set of stats. Part three lists everything a being holds while the game runs, as OpenMW 0.51
keeps and saves it, and what AmiWind has of it today. Not every being has every value: a creature has no skills of its
own, an auto-calculated person has almost no stored stats, and the player has no record of stats at all until the
character is made. Nothing here is invented: a value is listed only where a record, the original's rules or OpenMW 0.51
has it. Every other calculation of the game (hit chances, prices, speeds, spell chances and the rest) is on
[GAME_FORMULAS.md](GAME_FORMULAS.md).

## How to read this page

- **Ranges** are the lowest and highest value found in the three master files (Morrowind, Tribunal and Bloodmoon read
  together; where an id appears twice the last file wins, and a deleted record removes the earlier one). They were counted
  from the game data in a container on 5 November 2026. A range says what the data uses, not what the format could hold.
- **Counts** are numbers of records after that merge: 3,041 people (NPCs), 396 creatures, 10 races, 83 classes,
  13 birthsigns, 27 skills and 27 factions.
- **Used by** gives the original game's use (its documented rules, from the community reference on the original's
  mechanics) and what OpenMW 0.51 does with it. OpenMW's source was read for the rules only; nothing of its code is used
  (see [LICENSING_AND_CREDITS.md](LICENSING_AND_CREDITS.md)).
- **In AmiWind** says where the value lives today. The record table the builder writes is described in
  [ACTOR_STATE.md](ACTOR_STATE.md) (one 96-byte row per being, called the actor table here); the player's sheet is the
  character sheet of the character creation ([CHARACTER_CREATION.md](CHARACTER_CREATION.md)). "Not yet" means the value is
  not held anywhere in the game today. A single stat block per being that every game system reads is in progress
  (tracker item ACTOR-STATS-ALL-61; how each being's stats are stored per area and read is in
  [ACTOR_STATS.md](ACTOR_STATS.md)); this page describes the state before it.
- The 8 attributes, in the original's order: Strength, Intelligence, Willpower, Agility, Speed, Endurance, Personality,
  Luck. The 27 skills, in the original's order: Block, Armorer, Medium Armor, Heavy Armor, Blunt Weapon, Long Blade, Axe,
  Spear, Athletics, Enchant, Destruction, Alteration, Illusion, Conjuration, Mysticism, Restoration, Alchemy,
  Unarmored, Security, Sneak, Acrobatics, Light Armor, Short Blade, Marksman, Mercantile, Speechcraft, Hand-to-hand.
- The 3 specializations: Combat (Block, Armorer, Medium Armor, Heavy Armor, Blunt Weapon, Long Blade, Axe, Spear,
  Athletics), Magic (Enchant, Destruction, Alteration, Illusion, Conjuration, Mysticism, Restoration, Alchemy,
  Unarmored) and Stealth (Security, Sneak, Acrobatics, Light Armor, Short Blade, Marksman, Mercantile, Speechcraft,
  Hand-to-hand): nine skills each, as the 27 skill records in the data show.

## Who has what

| Value | Player | NPC with stored stats | NPC auto-calculated | Creature |
| --- | :---: | :---: | :---: | :---: |
| Level | yes (set by play) | yes | yes | yes |
| 8 attributes | yes | stored | derived from race, class, level | stored (larger numbers) |
| 27 skills | yes | stored | derived from race, class, level | no: 3 values stand in (combat, magic, stealth) |
| Health, magicka, fatigue | derived, then raised by play | stored | derived | stored |
| Disposition, reputation, faction rank | reputation and ranks by play | stored | stored (level, disposition, reputation, rank) | no |
| Gold | the inventory | stored | stored | stored |
| The behaviour data (hello, fight, flee, alarm, services) | no | yes | yes | yes |
| Race, class, faction, sex | chosen at creation | yes | yes | no |
| Birthsign | yes | no | no | no |
| Spell list (known spells, abilities, powers) | yes | yes | yes, plus the spells derived from skills | yes |
| Inventory | yes | yes | yes | yes |
| Soul value, 6 attack ranges, creature type | no | no | no | yes |
| Scale | no | no | no | optional |

## The NPC with stored stats (52-byte stats record, NPDT)

The people with a full stats record: 1,102 of 3,041. The record is exactly 52 bytes (the format has two sizes, 52 and 12;
see the next section).

| Name | Record field | Type | Range seen | Used by (original and OpenMW 0.51) | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Level | first value of NPDT | signed 16-bit whole number | 1 to 99 | Both: scales the number of levelled items and creatures it carries, the chance to hit, disposition and reputation rules; OpenMW stores it as the actor's level | Actor table row, 16 bits |
| Attributes (8) | NPDT, 8 bytes | one unsigned byte each | 0 to 255 | Both: every skill check, hit chance, carry weight, speed, fatigue; OpenMW sets them as the attribute bases | Actor table row (16 bits each); live record keeps the base and a modifier |
| Skills (27) | NPDT, 27 bytes | one unsigned byte each | 0 to 250 | Both: the weapon, armour and magic skill of every roll; OpenMW sets them as the skill bases | Actor table row, one byte each; live record keeps the base and a modifier |
| Health | NPDT | unsigned 16-bit | 0 to 65,535 | Both: the base health; OpenMW takes it as stored | Actor table row, 16 bits; live record keeps base and current as decimals |
| Magicka | NPDT | unsigned 16-bit | 0 to 2,000 | Both: the base magicka; OpenMW takes it as stored until Intelligence changes, then recalculates | Same as health |
| Fatigue | NPDT | unsigned 16-bit | 0 to 999 | Both: the base fatigue; OpenMW takes it as stored until Strength, Willpower, Agility or Endurance changes, then recalculates as their sum | Same as health |
| Disposition | NPDT | unsigned byte | 0 to 100 | Both: the person's own starting attitude to the player, before personality, reputation and other modifiers | Actor table row, one byte; the live record keeps it as the base |
| Reputation | NPDT | unsigned byte | 0 to 25 | Both: a measure of fame used by dialogue conditions. OpenMW replaces it for every person who belongs to a faction (see "Derived values") | Actor table row, one byte |
| Rank | NPDT | signed byte | 0 to 9 | Both: the rank in the person's faction; only meaningful when a faction is set (1,115 of the 3,041 people have one); OpenMW reads it as no rank when the faction is empty | Actor table row, one byte; read with the faction name |
| Gold | NPDT | signed 32-bit | 0 to 10,000 | Both: the coins a merchant starts with and what a person carries | Actor table row, 32 bits |
| Padding | 2 unused bytes | | | Nothing | Not held |

## The auto-calculated NPC (12-byte stats record, NPDT)

The other 1,939 people carry only 12 bytes. Their attributes, skills, health, magicka and fatigue are not stored; the game
works them out from the race, the class and the level when the person is first needed (the section "Derived values").
OpenMW decides by the size of the record (12 bytes), and in the data this agrees with the "auto-calculate" flag, which
the same 1,939 people have.

| Name | Record field | Type | Range seen | Used by (original and OpenMW 0.51) | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Level | first value of NPDT | signed 16-bit | 0 to 60 | Both: the level the derived values are calculated for; a level of 0 is allowed (OpenMW treats the level-1 step as 0 and goes on) | Actor table row, 16 bits |
| Disposition | NPDT | unsigned byte | 0 to 80 | Both: starting attitude | Actor table row |
| Reputation | NPDT | unsigned byte | 0 to 20 | Both: fame; replaced by the faction rule for faction members | Actor table row |
| Rank | NPDT | unsigned byte | 0 to 9 | Both: rank in the faction | Actor table row |
| Gold | NPDT | signed 32-bit | 0 to 10,000 | Both: coins carried | Actor table row, 32 bits |
| Padding | 3 unused bytes | | | Nothing | Not held |

## What every NPC record also holds

Both kinds of person share these subrecords.

| Name | Record field | Type | Range seen | Used by (original and OpenMW 0.51) | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Id | NAME | text, up to 32 characters | 3,041 ids | Both: how scripts, dialogue and the world name the person | Folded to a short string index in the actor table |
| Name | FNAM | text | one per person | Both: the name shown | The dialogue and name tables |
| Model | MODL | text | most people share the base model; the shape comes from race, head and hair | Both: the body model; OpenMW picks the beast skeleton when the race is a beast race | The builder's body and animation tables |
| Race | RNAM | race id | 10 distinct | Both: attributes, skill bonuses, powers, body shape, voice | Actor table row (string index) |
| Class | CNAM | class id | 82 distinct | Both: favoured attributes, major and minor skills, specialization (for derived values), dialogue | Actor table row (string index) |
| Faction | ANAM | faction id | 25 distinct, 1,115 people | Both: membership and rank; dialogue conditions; OpenMW derives reputation | Actor table row (string index) |
| Head | BNAM | body part id | one per person | Both: the head mesh | The builder's head tables |
| Hair | KNAM | body part id | one per person | Both: the hair mesh | The builder's hair tables |
| Script | SCRI | script id | some people | Both: the script that runs with the person | The compiled script table (see [MWSCRIPT_BYTECODE.md](MWSCRIPT_BYTECODE.md)) |
| Flags | FLAG | 32-bit | see "The flags and blood types" | Both | Actor table row flags |
| Carried items | NPCO, one per entry | count and item id | 0 to 35 entries | Both: the inventory; a negative count means the item is restocked | Actor table: inventory entries into a shared item table |
| Spells | NPCS, one per entry | spell id, 32 characters | 0 to 137 entries (509 people have any) | Both: the spells, abilities and powers the person knows | Actor table: spell entries |
| Behaviour data | AIDT | 12 bytes | all but one person | See "The behaviour data" | Actor table: the four ratings; services in the dialogue table |
| Travel destinations | DODT with DNAM | position and cell | 0 to 4 per person | Both: the destinations a transport service offers (silt strider, boat, guild guide) | The dialogue and travel tables |
| Wander package | AI_W | distance, duration, time of day, 8 idle chances, repeat | 2,934 | Both: roam near the home position for a time | The ambient NPC path tables |
| Travel package | AI_T | position, repeat | 149 | Both: walk to a place | The ambient NPC path tables |
| Follow package | AI_F | position, duration, target id, cell, repeat | 83 | Both: follow a being | Not yet as a record; scripts' AIFollow only |
| Escort package | AI_E | same as follow | 0 in people | Both: lead a being to a place | Not yet |
| Activate package | AI_A | target id, repeat | 0 | Both: walk to an object and activate it | Not yet |
| Package condition | CNDT | text | not counted | Both: a condition for the package before it | Not yet |

## The creature (96-byte stats record, NPDT)

All 396 creatures have a 96-byte stats record made of 24 whole numbers of 32 bits each. Creatures use whole numbers
where people use bytes, so their attributes and health run much higher.

| Name | Record field | Type | Range seen | Used by (original and OpenMW 0.51) | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Creature type | NPDT value 1 | signed 32-bit | 0 to 3: creature (219), daedra (59), undead (53), humanoid (65) | Both: which spells and effects work on it (Turn Undead, Command Creature, Command Humanoid, and the like); OpenMW stores the type | Actor table row, one byte |
| Level | NPDT value 2 | signed 32-bit | 1 to 100 | Both: as for people | Actor table row, 16 bits |
| Attributes (8) | NPDT values 3 to 10 | signed 32-bit each | 0 to 255 | Both: as for people | Actor table row, 16 bits each |
| Health | NPDT value 11 | signed 32-bit | 0 to 10,000 | Both: the base health | Actor table row, 16 bits |
| Magicka | NPDT value 12 | signed 32-bit | 0 to 10,000 | Both: the base magicka | Actor table row |
| Fatigue | NPDT value 13 | signed 32-bit | 50 to 5,000 | Both: the base fatigue | Actor table row |
| Soul value | NPDT value 14 | signed 32-bit | 0 to 1,500 | Both: the size of the soul a soul gem needs to trap this creature | Actor table row, 16 bits |
| Combat | NPDT value 15 | signed 32-bit | 0 to 200 | Both: stands in for every combat skill (see "Derived values") | Actor table: copied into the 27 skills by each skill's specialization |
| Magic | NPDT value 16 | signed 32-bit | 0 to 200 | Both: stands in for every magic skill | Same |
| Stealth | NPDT value 17 | signed 32-bit | 0 to 200 | Both: stands in for every stealth skill | Same |
| Attacks (6) | NPDT values 18 to 23 | signed 32-bit | 0 to 400 | Both: the damage range of the chop, slash and thrust attacks, each a lowest and a highest value | Actor table: six 16-bit values |
| Gold | NPDT value 24 | signed 32-bit | 0 to 10,000 | Both: coins carried | Actor table, 32 bits |

Other creature subrecords:

| Name | Record field | Type | Range seen | Used by | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Id, name, model, script | NAME, FNAM, MODL, SCRI | text | 396 | Both | As for people |
| Base creature | CNAM | creature id | rare | OpenMW stores the creature this one is a modification of | Not held |
| Scale | XSCL | 32-bit decimal | 0.8 to 2.0 (42 creatures; the rest 1.0) | Both: the size of the model | Not yet (models are built at their record size only where the builder bakes them) |
| Flags | FLAG | 32-bit | see "The flags and blood types" | Both | Actor table flags |
| Carried items | NPCO | count and id | 0 to 11 entries | Both | Actor table |
| Spells | NPCS | spell id | 0 to 10 entries (289 creatures have any) | Both: abilities and spells; this is where creature resistances and weaknesses come from | Actor table spell entries |
| Behaviour data | AIDT | 12 bytes | all | See "The behaviour data" | Actor table |
| Packages | AI_W, AI_T, AI_F, AI_E | as for people | 337, 26, 17, 1 | Both | Ambient path tables |

## The player

The player has no record of stats. The character creation makes a person from three choices (race, class and
birthsign), a sex and a name, and the starting stats follow the rules in "Derived values". In the original and OpenMW
the player is stored like an NPC plus the extra values listed here; in AmiWind it is the character sheet.

| Name | Where it comes from | Type | Range | Used by | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Name | chosen | text | up to 31 characters | Both: the name shown | Character sheet |
| Race, sex | chosen | race id, flag | 10 races, 2 sexes | Both: attributes, skill bonuses, powers, body | Character sheet |
| Class | chosen, or a custom class | class id | 83 in the data, or one made by the player | Both: favoured attributes, major and minor skills, specialization | Character sheet (one extra slot for a custom class) |
| Birthsign | chosen | birthsign id | 13 | Both: its powers, abilities and spells | Character sheet |
| Level | starts at 1 | whole number | 1 to 99 or more | Both | Character sheet |
| Attributes (8) base | race and class | whole number | 0 to 100 for a raise; fortified values go higher | Both | Character sheet: base, modifier and damage kept apart |
| Skills (27) base | race, class and specialization, then use | whole number | 0 to 100 | Both | Character sheet: base only |
| Health, magicka, fatigue | derived (see below), current and maximum | decimal | | Both | Character sheet: current and maximum |
| Skill progress (27) | training by use | decimal 0 to 1 of the next point | | Both: a skill rises when its progress is full | Character sheet |
| Level progress | skill raises of major and minor skills | whole number | 0 up to the level-up total | Both: the level-up when it reaches the total (game setting iLevelupTotal, 10) | Character sheet |
| Raises per attribute (8) | skill raises since the last level | whole number | 0 to 10 counted | Both: sets the attribute multiplier at the next level (game settings iLevelUp01Mult to iLevelUp10Mult) | Character sheet |
| Raises per specialization (3) | same | whole number | | Both: the specialization bonus at level-up | Character sheet |
| Bounty, reputation, faction ranks | play | whole numbers | reputation 0 to 255 | Both | The player's standing block, saved with the game |
| Head and hair | chosen | body part id | | Both | Character sheet |

## The race (RACE)

Ten races, all playable; two of them (Argonian and Khajiit) are beast races.

| Name | Record field | Type | Range seen | Used by (original and OpenMW 0.51) | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Id, name, description | NAME, FNAM, DESC | text | 10 | Both: the race page of the character creation | Character catalogue |
| Skill bonuses | first 7 pairs of RADT: a skill number and an amount | two signed 32-bit values each | skill -1 to 26 (-1 means the slot is unused), amount 0 to 15; all 70 slots used across the 10 races | Both: added to the skill's start value for a player of the race and for auto-calculated people | Character catalogue |
| Attribute values | next 16 values of RADT: for each attribute a male and a female value | signed 32-bit | 25 to 50 | Both: the base attribute for the chosen sex | Character catalogue (16 bytes per race) |
| Male height, female height | RADT, decimals | 32-bit decimal | 0.9 to 1.1 male, 0.95 to 1.1 female | Both: scales the body model | Not yet |
| Male weight, female weight | RADT, decimals | 32-bit decimal | 0.95 to 1.35 male, 0.9 to 1.1 female | Both: scales the body width | Not yet |
| Flags | last value of RADT | 32-bit | playable (1): 10 races; beast race (2): 2 races | Both: playable shows the race in the creation; beast cannot wear shoes or helmets and uses the beast skeleton | Character catalogue (playable); body tables (beast) |
| Powers and abilities | NPCS, one per entry | spell id | 2 to 6 per race | Both: the race's abilities (permanent resistances, fortified skills) and its power (once a day); OpenMW adds them to the spell list of every person and to the player's | Added to the actor's spell list; the player's magicka bonuses are kept as modifiers |

The whole record is 140 bytes (7 pairs of 8 bytes, 16 attribute values, 4 decimals, the flags).

## The class (CLAS)

83 classes; 21 are playable.

| Name | Record field | Type | Range seen | Used by (original and OpenMW 0.51) | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Id, name, description | NAME, FNAM, DESC | text | 83 | Both | Character catalogue |
| Favoured attributes (2) | first two values of CLDT | signed 32-bit | 0 to 7 (an attribute number) | Both: +10 to the base of each attribute; the skill-use multipliers; the health step for Endurance | Character catalogue (2 bytes) |
| Specialization | CLDT | signed 32-bit | 0 combat (28 classes), 1 magic (28), 2 stealth (27) | Both: +5 to every skill of that specialization; faster skill use; the health step for combat and stealth | Character catalogue |
| Minor and major skills (5 pairs) | CLDT, ten values | signed 32-bit | 0 to 26 (a skill number); each pair holds a minor then a major skill | Both: +10 for a minor and +25 for a major skill; each counts fully towards level-up | Character catalogue (10 bytes) |
| Playable | CLDT | signed 32-bit flag | 1 for 21 classes | Both: shown in the creation list | Character catalogue |
| Services | CLDT | 32-bit flags | 0 to 131,587 | The original: the services of a trainer of this class. OpenMW 0.51 does not read it for actors; a person's own services are read | Not held |

The whole record is 60 bytes.

## The birthsign (BSGN)

13 birthsigns.

| Name | Record field | Type | Range seen | Used by (original and OpenMW 0.51) | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Id, name, description | NAME, FNAM, DESC | text | 13 | Both | Character catalogue |
| Picture | TNAM | texture name | 13 | Both: the picture shown in the creation | Character catalogue |
| Powers, abilities and spells | NPCS, one per entry | spell id | 1 to 3 per sign | Both: added to the player's spell list at the start | The sheet's list of the sign's spells and its magicka bonus (a tenth per point of fortified maximum magicka) |

## The behaviour data (AIDT)

Every person but one and every creature has the 12-byte behaviour data record. It is the behaviour ratings plus the services.

| Name | Record field | Type | Range seen | Used by (original and OpenMW 0.51) | In AmiWind |
| --- | --- | --- | --- | --- | --- |
| Hello | first value of AIDT | unsigned 16-bit | people 0 to 300, creatures 0 to 100 | Both: how far away the being notices the player and greets; a rating of 0 never greets. OpenMW's note says the format could hold 0 to 65,535 | Actor table, one byte (a larger value is cut to 255) |
| Fight | AIDT | unsigned byte | 0 to 100 | Both: a chance of 0 to 100 that it attacks; a value of 100 or more always fights; 0 never. Combined with the player's disposition, level and the like to choose | Actor table, one byte |
| Flee | AIDT | unsigned byte | 0 to 100 | Both: the health level at which it runs | Actor table, one byte |
| Alarm | AIDT | unsigned byte | 0 to 100 | Both: how likely it is to react to a crime it witnesses | Actor table, one byte |
| Padding | 3 bytes | | | Nothing | Not held |
| Services | AIDT, 32-bit flags | bit set | bits 0 to 17 | Both: which buttons a talk offers and what kinds of item a merchant buys | The dialogue table's services section |

The service bits, with the number of people that have each: sells or buys weapons (143), armour (142), clothing (105),
books (127), ingredients (211), lockpicks (61), probes (56), lights (67), apparatus (49), repair items (123),
miscellaneous items (98); sells spells (96); buys magic items (101); buys potions (208); trains (308); makes spells (43);
enchants (24); repairs (60). Creatures: 21 have the bits for ingredients, lockpicks, repair items, magic items, potions
and repair.

## The flags and blood types

The flag value (FLAG) packs the flag bits in the lowest byte and the blood type from bit 10 up.

| Bit | In people | Count | In creatures | Count | Used by | In AmiWind |
| --- | --- | ---: | --- | ---: | --- | --- |
| 0 | Female | 1,172 | Can walk upright (bipedal) | 42 | Both: sex of the body and voice; for creatures, the stance and use of a weapon | Female and bipedal flags in the actor table |
| 1 | Essential | 51 | Respawns | 46 | Essential: its death shows a warning to the player; respawn: the being returns when its cell resets | Essential and respawn flags |
| 2 | Respawns | 82 | Has a weapon and shield | 58 | Creature only: holds a weapon and shield that can be taken | Not held (the inventory carries them) |
| 3 | Base | 3,041 | Base | 396 | Set on every being of the master files, no effect | Not held |
| 4 | Auto-calculate | 1,939 | Swims | 22 | People: stats derived; creatures: moves in water | Auto-calculate flag; swims flag |
| 5 | | | Flies | 14 | Creatures: moves in the air | Flies flag |
| 6 | | | Walks | 316 | Creatures: moves on the ground | Walks flag |
| 7 | | | Essential | 5 | Creatures: as for people | Essential flag |

The blood type is a number from 0 to 2: 0 the usual red blood, 1 the white of skeletons, 2 the sparks of metal. In the
data 3,040 people have type 0 and one has type 1; creatures have type 0 (325), type 1 (43) and type 2 (28). The original
chooses the blood splash a hit shows; OpenMW 0.51 stores the value and only its scripting interface reads it. AmiWind
does not hold it yet.

## The spell lists (NPCS)

A spell list is a run of NPCS subrecords, each a spell id (32 characters). The same subrecord is used by four record
types.

| Holder | Range per record | Counts | What it lists | In AmiWind |
| --- | --- | --- | --- | --- |
| Person | 0 to 137 | 509 people have any | spells, abilities, powers and diseases the person starts with | Actor table spell entries |
| Creature | 0 to 10 | 289 creatures have any | abilities (resistances, weaknesses, immunities), spells and attacks that cast | Actor table spell entries |
| Race | 2 to 6 | all 10 races | the race's abilities and its power | Added to each person and to the player |
| Birthsign | 1 to 3 | all 13 signs | the sign's powers, abilities and spells | The player's sheet |

A spell record has its own type (a spell, an ability, a blight, a disease, a curse or a power); the actor table keeps the
type of each spell beside its id. The list does not contain the spells a person gets by autocalculation; those are
derived (next part).

## Derived values

These formulas are OpenMW 0.51's (apps/openmw/mwclass/npc.cpp, mwmechanics/autocalcspell.cpp, creaturestats.cpp,
npcstats.cpp, spellresistance.cpp), which follow the original; AmiWind's builder and engine run its own code written
from the rules. The game settings named in each step are the data's values (Morrowind, Tribunal and Bloodmoon agree).
All rounding is half to even, as in OpenMW.

### An auto-calculated NPC

The values start from the 12-byte record (level, disposition, reputation, rank, gold) and the race, class and sex.

**Attributes.** Each attribute starts at the race's value for the person's sex. Each of the class's two favoured
attributes then gets 10 more. Then, for every attribute, every skill that is governed by it adds to a running total:
1.0 if the skill is a major skill of the class, 0.5 if it is a minor skill, and 0.2 for any other skill. The attribute
grows by that total times (level minus 1), rounded, and is capped at 100. A level-1 person therefore has the race value
plus the class bonus.

**Skills.** Every skill starts at 0. Each minor skill of the class gets 10 and each major skill gets 25. Then every skill
gets 5, the race's bonus for it (if it has one) and 5 more if it belongs to the class's specialization. On top of that comes
(level minus 1) times a rate: the rate is 1.0 if the skill is a major or minor skill of the class (otherwise 0.1), plus
0.5 if it belongs to the class's specialization. The result is rounded and capped at 100. A level of 0 is treated as a
level where the (level minus 1) part is 0.

**Health.** Half of Strength plus Endurance (rounded down, using the attributes from the step above), plus (level minus
1) times a number: 3, plus 2 for a combat class, plus 1 for a stealth class, plus 1 more if Endurance is one of the
class's favoured attributes (so 3 for a magic class, up to 6 for a combat class that favours Endurance).

**Magicka.** Intelligence times the game setting fNPCbaseMagickaMult (2.0 in the data). OpenMW adds one tenth of the
magnitude of any Fortify Maximum Magicka effect to that multiplier; at the start there is none. The same rule applies to
every person after Intelligence changes.

**Fatigue.** Strength plus Willpower plus Agility plus Endurance, the modified values. OpenMW recomputes it whenever one
of the four changes, keeping the current-to-base ratio.

**Reputation.** For a person who belongs to a faction, OpenMW ignores the stored value and uses the game setting
iAutoRepFacMod (2) times (rank plus 1), plus iAutoRepLevMod (0 in the data) times (level minus 1). This applies to people
with stored stats as well. A person with no faction keeps the stored reputation.

**Spells.** An auto-calculated person gets the spells from the game's list of autocalculated spells, in the order the
files list them, by these steps. A spell is considered only if it is a normal spell (not an ability, power or disease)
and has the "auto-calculate" mark. It is skipped when the person's base magicka (Intelligence times fNPCbaseMagickaMult)
is less than the game setting iAutoSpellTimesCanCast (3) times the spell's cost; when it is one of the race's powers;
when it has an effect on a skill or attribute and that skill or attribute is below iAutoSpellAttSkillMin (70); or when the
chance is too low. The chance uses the spell's weakest school: for each effect the game works out its cost term (the
average magnitude times the base cost of the effect times its duration, plus the area, times fEffectCostMult 0.5, and
times 1.5 for a spell cast on a target), and the school with the lowest value of two times the skill minus that term is
the weakest school. The chance is two times the skill of that school, minus the spell's cost, plus 0.2 times Willpower
and 0.1 times Luck; it must reach fAutoSpellChance (80), and a spell that always succeeds counts as 100. Each school has
a limit of spells: iAutoSpellAlterationMax 5, Conjuration 2, Destruction 5, Illusion 5, Mysticism 5 and Restoration 5.
When a school is full, a new spell is kept only if it costs more than the cheapest one already kept, and it replaces that
one. On top of these, every person gets the race's powers and abilities and then the spells of the record's own list. A
person whose spells were already set (a loaded save) does not get the derived spells again.

### The player at the start

The player's starting stats are not derived from a level: they start from race, class and the two choices.

- Attributes: the race's value for the sex, plus 10 for each favoured attribute of the class.
- Skills: 5, plus the race's bonus, plus 10 for a minor and 25 for a major skill, plus 5 for each skill of the class's
  specialization.
- Health: half of Strength plus Endurance, rounded down. Magicka: Intelligence times fPCbaseMagickaMult (1.0).
  Fatigue: Strength plus Willpower plus Agility plus Endurance.
- At each level-up: health rises by Endurance times fLevelUpHealthEndMult (0.1), also added to the current health; the
  level goes up by one when the level progress reaches iLevelupTotal (10); the three attributes the player raised get the
  multiplier for the number of skill raises that fed them (iLevelUp01Mult to iLevelUp10Mult: 2, 2, 2, 2, 3, 3, 3, 4, 4, 5).

**The player's starting spells.** Three sources are added to the spell list:

1. The race's powers and abilities (all of its NPCS entries).
2. The birthsign's powers, abilities and spells.
3. Spells derived from the skills. A normal spell with the "PC start" mark is considered in file order. It is skipped if it
   is one of the race's powers, if the player's base magicka (Intelligence times fPCbaseMagickaMult) is lower than its cost,
   if the chance is below fAutoPCSpellChance (50) (the chance uses the same formula as above), or if one of its effects
   on a skill or attribute needs a value under iAutoSpellAttSkillMin (70). At most iAutoPCSpellMax (100) are kept; past the
   limit a new spell replaces the cheapest one only if it costs more.

AmiWind has the first two today; the third (starting spells from skills) and the derived spells of auto-calculated people
are not yet built (see [ACTOR_STATE.md](ACTOR_STATE.md) "Not yet").

### A creature's skills

A creature has no skill list. When a rule asks for a skill, OpenMW answers with the creature's combat value if the skill's
specialization is Combat, the magic value if it is Magic, and the stealth value if it is Stealth. All nine skills of a
specialization therefore read the same number. A creature's attributes, health, magicka and fatigue are read as stored.
AmiWind fills the 27 skill bytes of the creature's row this way when the builder runs.

### Resistances and weaknesses

A being does not store a resistance. Each resistance or weakness is the total magnitude of the matching effects it
currently has from its abilities, spells, equipment and active spells: Resist Fire and Fire Shield count towards fire,
Weakness to Fire counts against it (Resist Frost with Frost Shield, Resist Shock with Lightning Shield, and so on for
common disease, blight, normal weapons, magicka, paralysis and poison). If there are none, the value is 0. The resistance is
a percentage, so a total of 100 is immunity and a negative total (a weakness) makes the damage larger. For an effect
with no resisting effect of its own (many buffs), the resistance is 0. When a spell lands, the game also rolls a chance
based on Willpower plus a tenth of Luck, scaled by the fatigue term, against the spell's ease of casting; an effect that
has no magnitude is either resisted whole or not at all. AmiWind applies only the Resist and Weakness to Normal Weapons
totals so far (the combat code reads them, v0.0.61); the other resistances are not applied yet: the actor table keeps
the spell list and the active effects are in place, so the totals can be computed as the magic work continues.

### What a missing value reads as

| Missing | Reads as |
| --- | --- |
| A resistance or weakness with no source | 0 |
| A creature's skill | The creature's combat, magic or stealth value by the skill's specialization |
| The behaviour data of a person | Hello 30, fight 30, flee 30, alarm 0, no services (OpenMW). AmiWind's table writes 0 for all four |
| The behaviour data of a creature | Hello 0, fight 90, flee 20, alarm 0 (OpenMW). AmiWind's table writes 0 for all four |
| A creature's scale | 1.0 |
| A person's faction | No faction; rank reads as -1 |
| Spell list, carried items, travel destinations, packages | Empty (a being with no package stands where it is placed) |
| A race skill bonus slot with skill -1 | Nothing (it matches no skill) |
| A class attribute below 0 | Skipped |
| The stats or the flags of a record | The record is refused as damaged |

## Part two: everything a being holds while the game runs

This is OpenMW 0.51's live state: the creature statistics shared by every being, the extra person statistics (used by the
player and NPCs), the actor save records, and the object state around them (components/esm3/creaturestats.hpp,
npcstats.hpp, statstate.hpp, creaturestate.hpp, npcstate.hpp, player.hpp, aisequence.hpp, activespells.hpp, spellstate.hpp,
inventorystate.hpp, locals.hpp, objectstate.hpp). P is the player, N a person, C a creature. "Saved" says whether the
OpenMW save file keeps the value.

| Variable | Type | Who | Saved | In AmiWind today |
| --- | --- | :---: | :---: | --- |
| Attributes (8): base, modifier, damage | decimals | P N C | yes | Base and one modifier (fortify minus damage) per actor, in the live record; the player's sheet keeps modifier and damage apart. Saved |
| Skills (27): base, modifier, damage | decimals | P N | yes | As attributes. Creatures: no skills |
| Skill progress (27) | decimal | P | yes | Player's sheet. Saved |
| Dynamic stats (health, magicka, fatigue): base, modifier, current | decimals | P N C | yes | Base and current per actor; the modifier (fortify maximum) not yet. Saved with the actor |
| Level | whole number | P N C | yes | Per actor. Saved |
| Level progress | whole number | P | yes | Player's sheet. Saved |
| Skill raises per attribute (8) and per specialization (3) | whole numbers | P | yes | Player's sheet. Saved |
| Base disposition | whole number | N | yes | Per actor (base only). Saved with the actor |
| Disposition changes during a conversation (persuasion, bribes) | | N | yes (folded into the base) | Kept for the conversation by the dialogue layer; not on the record |
| Crime disposition modifier | whole number | N | yes | Not yet |
| Reputation | whole number | P N | yes | Player: the standing block, saved. People: the table's value, not changed |
| Bounty (crime level), current crime id, paid crime id | whole numbers | P | yes | Bounty in the standing block, saved. A theft seen by a witness is reported and raises it (v0.0.61-dev3); the other crimes: not yet |
| Faction ranks, expelled marks and faction reputation | per faction | P N | yes | Player: the standing block, saved. People: the table's faction and rank only |
| Werewolf state, werewolf kills, the saved attribute and skill values to restore | flag, number, lists | P N | yes | Not yet |
| Used items (ids of what has been eaten or drunk, for learning ingredient effects) | list of ids | P | yes | Not yet |
| Dead, died this frame, murdered | flags | P N C | yes | Dead and "died" flags on the live record, and a dead count per id, saved. Murdered: not yet |
| Death animation chosen, death animation finished, time of death | number, flag, time | P N C | yes | Not yet |
| Knocked down (and its one-frame flags), hit recovery, blocking | flags | P N C | yes | In the fight sheet while a fight runs (knocked down or out, staggered, not ready to block); not saved |
| Talked to the player | flag | N C | yes | Not on the actor record |
| Alarmed, attacked | flags | N C | yes | Aware and attacking flags in the fight sheet; not saved |
| Drawn state (nothing, weapon, spell) | number | P N C | yes | The player's equipped weapon is shown in the hands; no separate state is kept or saved |
| Movement flags, fall height | | P N C | yes | The player's movement layer only |
| Last object that hit it, last object that tried to hit it | ids | P N C | yes | Not yet |
| Spell list: known spells, the selected spell, powers used and when, permanent effects | lists | P N C | yes | Known spells: the table's list plus play's changes, saved. The rest: not yet |
| Active spells (each with source, caster, item, flags and per-effect magnitude, duration and time left) | list | P N C | yes | A pool of 64 entries (32 of them for the player) for any of the 143 effects applied to an actor by reference, with the time left, saved in a block of their own; the effects of non-player actors run while they are loaded (v0.0.61). Sources, casters and the effects of actors that are not loaded: not yet |
| Magic effects total (base and modifier per effect, the source of resistances and Fortify values) | map | P N C | yes | Not yet (resistances and weaknesses wait for it; see [GAME_FORMULAS.md](GAME_FORMULAS.md)) |
| Corprus spells (worsenings and the next worsening time) | list | P N C | yes | Not yet |
| Summoned creatures and the summon graveyard | maps | P N C | yes | Not yet |
| The package sequence: wander, travel, escort, follow, activate, combat and pursue with their live state and remaining time | list | N C | yes | Ambient wander and travel tables, and the one fight the combat layer has; no live sequence per being; not saved |
| Behaviour settings: hello, fight, flee, alarm (base and modifier) | whole numbers | N C | yes | Base only, per actor. Saved |
| Trade time (when a merchant restocks) and gold pool | time, number | N C | yes | Gold per actor; sold items kept per merchant and saved; the restock timer: not yet |
| Inventory: items, counts, condition, charge; equipment slots; selected enchanted item; permanent magic effect values | lists | P N C | yes | The table's entries plus play's changes, saved; worn marks per entry; the player's items keep condition and charge in saved games (v0.0.61); condition and charge of other beings' items: an NPC weapon's charge is kept for the session only. The player's items are the engine's own table |
| Local script variables (short, long, float) | name and value per object | any scripted object | yes | Held by the script host; saved since v0.0.59 |
| Position, enabled state, count and the reference's own values (owner, lock, charge) | | any object | yes | The world change list, partly |
| Animation state | | any object | yes | Not saved |
| Talk and greeting timers | | N C | no (runtime) | Kept by the voice and dialogue layers, not on the actor record |
| Sneak detection timer and roll | | N C | no | Not yet |
| Friendly-hit count | whole number | N C | no | Not yet |
| Attack type, attacking or casting now | text, flag | P N C | no | The fight sheet's attacking flag |
| Birthsign | id | P | yes | Character sheet. Saved |
| Mark and Recall position | position, cell | P | yes | Not yet |
| Previous items (for bound item spells) | map of ids | P | yes | Not yet |
| Last known exterior position, current cell | position, id | P | yes | The save's own position block |

## Sources and method

- The three master files, read in a container on 5 November 2026: every record of the types listed, the last record of an id
  winning. The survey scripts and their outputs are kept in the project's working notes.
- OpenMW 0.51 source (GPL-3.0): the record readers for people, creatures, races, classes, birthsigns and the behaviour data; the
  person's first-use code (derived values); the spell-derivation code; the resistance code; the save records. Read for the
  rules only; AmiWind's code is its own.
- [ACTOR_STATE.md](ACTOR_STATE.md), [ACTOR_STATS.md](ACTOR_STATS.md), [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [COMBAT.md](COMBAT.md),
  [GAME_FEATURES.md](GAME_FEATURES.md) and [NPC_DEFAULTS.md](NPC_DEFAULTS.md) for what AmiWind holds today.
- The community reference on the original's mechanics (a local copy was consulted for the skills and specializations).
