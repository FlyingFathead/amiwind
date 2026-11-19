# What every being can have: the actor records

_Last updated with AmiWind v0.0.67-dev2 (18 November 2026)._

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
- [Is it all there: the audit](#is-it-all-there-the-audit)
  - [Ranged fighters](#ranged-fighters)
  - [Held weapons](#held-weapons)
  - [Combat styles](#combat-styles)
  - [The animations](#the-animations)
  - [Whole creature models and the surface check](#whole-creature-models-and-the-surface-check)
- [The build's actor spec check](#the-builds-actor-spec-check)
- [The expansions' actors](#the-expansions-actors)
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

## Is it all there: the audit

A world-wide table checks, field by field, every NPC and creature record of the three masters against what a build's
actor data holds: the actor table, the stats vocabulary every area's stats are cut from, the compiled Wander packages
and the script table. Each field of each record is **carried** (the build holds the record's value), **missing** (the
record has it, the build holds nothing), **different** (the build holds another value) or **absent** (the record has
no such value). Counts are given in records and in placed references, with the references of Morrowind.esm's cells
apart (the expansions' cells are not in the build yet).

- The tool: `tools/actor_record_audit.py --data-files DIR --build RUN --out DIR [--public FILE]
  [--fresh-actor-table]` (the last flag compares the actor table the current source would write, before any build).
- The counts: [actor-record-audit.json](actor-record-audit.json). The known gaps, each with its tracked ID:
  `config/actor-record-gaps.json`. The gate test `tests/test_actor_record_audit.py` fails on any gap that is not
  listed there, or that grew.

Headline, 13 November 2026 (the v0.0.65 release build's outputs, the actor table of v0.0.66): 3,041 people and 396
creature records, 4,798 placed references (3,906 in Morrowind.esm).

| Field | Missing or different (records) | Placed references (Morrowind.esm) | Tracked as |
| --- | ---: | ---: | --- |
| Level, attributes, skills, health, magicka, fatigue, behaviour ratings, disposition, reputation, rank, gold, race, class, faction, creature type, attacks, soul, flags, blood, spells, fixed inventory, script | 0 | 0 | all carried |
| Levelled inventory: chosen once at build time, not per actor | 1,276 | 1,820 | ACTOR-LEVELLED-INVENTORY-ONE-PICK-66 |
| Wander package (actors placed only in the expansions) | 520 | 6 | ACTOR-PACKAGES-NOT-HELD-66 |
| Ranged weapon: a bow or crossbow without its ammunition (7); a melee weapon rated higher at the opening (43) | 50 | 50 | ACTOR-RANGED-COMBAT-MISSING-66 |
| Follow, travel, escort packages | 158 | 123 | ACTOR-PACKAGES-NOT-HELD-66 |
| Creature scale (expansions only) | 42 | 0 | CREATURE-SCALE-NOT-HELD-66 |
| Armour worn | 23 | 44 | ACTOR-LEVELLED-INVENTORY-ONE-PICK-66 |
| Melee weapon equipped | 2 | 2 | ACTOR-LEVELLED-INVENTORY-ONE-PICK-66 |
| Script local count | 1 | 0 | NPC-CREATURE-COMBAT-STYLE-STATS-66 |

Fixed by the audit's first round (v0.0.66): a creature with the "weapon and shield" flag now equips the weapon and
armour its inventory gives and fights with the weapon's damage, as in the original (CREATURE-COMBAT-WEAPON-54). Before:
54 such records (164 placed references, among them every skeleton, lich, goblin and dremora with a weapon) struck with
their own claw attacks; after: 2, both a levelled pick. A creature without the flag keeps its items as loot only.

### Ranged fighters

The skeleton archers of Andrano Ancestral Tomb carry a long bow and nothing else to fight with, so they come at the
player with their fists. Two parts are missing, for every archer of the game (252 records):

1. The builder's equipment choice takes melee weapons only (weapon types 0 to 8); a bow, crossbow or thrown weapon is
   never the equipped weapon.
2. The engine has no shot: the player's own bow says so, and no actor can shoot.

The plan, as the original does it (OpenMW 0.51 aicombat.cpp, weapontype.cpp, projectilemanager.cpp, for the rules
only): an actor whose best weapon is ranged keeps its distance and shoots; the arrow or bolt is a projectile that flies
at a speed between the game settings fProjectileMinSpeed and fProjectileMaxSpeed by how far the bow was drawn, falls with gravity, and hits the first body
or wall on its path; the damage is the weapon's chop range plus the ammunition's, and one round of ammunition is used
per shot. Budget sheet for the first version (to be measured on the slow machine before it ships):

- RAM: one projectile pool of 16 entries (about 64 bytes each, 1 KiB), one shared arrow and bolt model each.
- CPU: one ray test against the world and the actors per projectile per frame (16 at most); a shot is an event, not a
  per-frame cost. The draw and release play the bow groups the animation tables already hold.
- DISK: no new file per area; the ammunition models are shared item models.
- DRAW: one small model per arrow in flight (about 20 triangles).

What v0.0.66 does (in the source, not yet checked in a running game):

- The builder (`tools/prepare_combat.py` `equipment(..., ranged=True)`, used by the actor table and the fight sheets)
  holds a bow, crossbow or thrown weapon when the inventory can shoot it (a bow with arrows, a crossbow with bolts) and
  it rates higher than the best melee weapon at the opening of a fight, by the original's weapon rating
  (weaponpriority.cpp: the mean chop plus the best round's, times the speed, and the ranged multiplier while the enemy
  is out of reach), or when it is the only weapon. The arrows stay in the inventory. Bows and crossbows are two-handed:
  no shield beside them. The arena fighters and the held models keep the melee choice. On the game data (the audit with
  this source's actor table, 13 November 2026): 202 of the 252 records hold their ranged weapon; 43 hold a melee weapon
  that rates higher at the opening; 7 carry a bow without arrows (the original rates such a bow 0).
- The fight layer (`engine/aga/src/aw_combat.c`, rules in `aw_combat_rules.c`): while the player is within the
  weapon's combat range (fProjectileMaxSpeed, 3,000 units) and in sight, the actor keeps its place and plays its attack
  group; at the release one round leaves its inventory (the live record, so a saved game keeps the count) and the
  shot flies at fProjectileMinSpeed to fProjectileMaxSpeed by the draw (an actor's draw in the original, 0.1 plus a roll),
  aimed above the target by the drop and falling with the original's projectile gravity. Each frame it moves once and
  traces once; it hits the first body or wall on its path. On the player it is the hit roll and damage of a blow, with
  the weapon's and the round's chop and the player's armour, never blocked. Out of rounds the actor fights hand to hand.
  `dbg combat` shows the shots fired, landed and missed and the pool.
- Not yet: switching between bow and melee weapon during a fight (the original rates both again at every action), the
  arrow model (the shot is drawn as a short shaft of four particles), shots at other actors, and the slow-machine
  measurement of the sheet above.

Budget as built: RAM 16 shots of about 40 bytes (640 bytes on the Amiga) and 12 bytes per fighter slot; CPU one trace per shot in flight
per frame (16 at most) and one sight trace per archer think (0.1 s); DISK none (the rounds are read from the actor
record already in memory); DRAW four particles per shot in flight.

### Held weapons

People and creatures draw the weapon and shield they fight with through the item models that follow the Weapon Bone
and Shield Bone of their skeleton (a `.tag` file beside the actor's model; `tools/npc_items.py`,
`engine/aga/src/aw_items.c`). The town residents had them; the models of the NPC library (the people of the rest of the
island, among them most guards) did not: in the v0.0.65 release build none of the 423 library models had a tag, so a
guard fought with a spear nobody saw (NPC-WEAPON-MESH-33, seen again in v0.0.65). From v0.0.66 the library writes the
same tag for every skeletal model whose person carries a weapon or shield, beside the bake, so no model is baked
again; the setting `AMIWIND_NPC_LIBRARY_ITEMS=0` turns it off. Measured on the game data (13 November 2026): 288 of
the 423 library models get a tag (28,680 bytes in all, about 100 bytes each), naming 69 item models of about 145 KB
each, shared with the residents' (the image already holds 111 item models, the guard's spear among them); the work is
about 1.3 seconds an appearance on one core and runs on all the stage's jobs. In play it adds one small item model
per armed person drawn. Not yet checked in a running game.

### Combat styles

Which weapon a person or creature takes into a fight, and so its style of combat (a melee weapon, a bow, a crossbow, a
thrown weapon, its fists, or a creature's own attacks), is chosen by the builder for its fight sheet and the actor
table (`tools/prepare_combat.py` `equipment`). From v0.0.66 the choice follows the original's weapon rating with the
fighter's own skills (OpenMW 0.51 weaponpriority.cpp rateWeapon, for the rules only): each weapon's damage term, a bow
or crossbow with its best round and no rating without one, is multiplied by the hit chance of the fighter with that
weapon (its skill, or a creature's Combat value, plus Agility / 5 and Luck / 10, times the fresh fatigue factor; the
enemy's side is not known before the fight and is left out), by the weapon's speed, and by fAIMeleeWeaponMult, or
fAIRangeMeleeWeaponMult for a ranged weapon, since every fight opens with the enemy out of reach. A weapon whose skill
is 0 is never taken. A creature's skill is its Combat, Magic or Stealth value by the skill's specialization, so a
creature with no Stealth leaves its dagger and bow and uses its own attacks; a creature without the "weapon and
shield" flag always does. Before, the melee weapon was the one with the highest maximum damage whatever the skill.

The table (`tools/combat_style_audit.py`, run in a container on the three masters; counts in
[combat-style-audit.json](combat-style-audit.json)) checks every record's choice against the rule written out on its
own. On the game data (13 November 2026), of 3,437 records: 1,839 fight with a melee weapon, 119 with a bow, 20 with a
crossbow, 54 with a thrown weapon, 1,062 with their fists and 343 creatures with their own attacks; 632 of them also
have spells to cast (weighed against the weapon in the fight itself). The choice of the v0.0.66 source before this
change differed for 35 records: 11 took another style (8 a thrown weapon and 2 a bow where their skills give a melee
weapon, 1 the other way round) and 24 another melee weapon. Now none differs. The skeleton archers hold their bows in
both.

### The animations

The same table also holds, per record, every kind of animation the original's files give its skeleton, against what
the build's model of that actor can play. The original side: a person's groups come from `xbase_anim.kf` (the beast
races from `xbase_animkna.kf`) plus its own file when its record names one; a creature's from its own `x<model>.kf`,
plus `xbase_anim.kf` when it walks on two legs (the text keys of each file, read without parsing the model). The
build side: the method each actor gets (a town or room resident, the NPC library, the opening's standing model with
the full kit it wears in a fight, the creature library's `kf` bake of six groups or its `skeletal` model on the
creature's whole table, an authored corpse with its one death pose) and the groups that method plays. The kinds:
idle, walk, run, attack (a creature's attack1 to attack3), the seven weapon attacks of a person (hand-to-hand,
one-handed, two-handed, two-wide, bow, crossbow, thrown), hit, knockdown, death, spell cast, block, sneak and swim.
A corpse counts only its death pose. Each row also names its method, and the opening's people are listed by name.

Headline (the v0.0.65 release build, Morrowind.esm references):

| Kind | Missing (references) | Why | After v0.0.66 (projected) |
| --- | ---: | --- | ---: |
| Knockdown | 791 | the creature library bakes six groups (168 creature records) | 16 |
| Spell cast | 129 | the same (38 creature records) | 16 |
| Weapon attacks, block, sneak, swim of two-legged creatures | 81 | the same (22 records: skeletons, dremora) | 4 |
| Idle, walk, run, hit, death | 6 to 7 | Fargoth and the opening's Imperial guard (no layout), Vivec, Dagoth Ur | 6 to 7 |

Every person of the towns, the rooms and the NPC library (about 2,550 records) carries every kind: they are skeletal
and play their table by state. The census office's people (Socucius Ergalla, Sellus Gravius, the hall guard) and the
prison ship's carry every kind through their full kit (fixed in v0.0.65, CENSUS-NPC-NO-ATTACK-ANIM-65). The gap was
the creatures (NPC-ATTACK-ANIMS-MISSING-65): from v0.0.66 the creature library bakes every creature with the
`skeletal` method, its whole table (the second and third attack, knockdown, spell cast and swim included, picked by
state as for the rooms' creatures and Dagoth Ur); a mesh the skeletal bake refuses keeps the six baked groups and is
named in the build log (in the game data: the storm atronach). `--creature-method kf` brings back the old bake.
Budget, measured by baking the 39 creature meshes alone on the game data (13 November 2026, about 5 minutes on 16
cores): 38 take the skeletal method; their models and tables are 10.1 MB on disk (2.97 MB of tables, 7.08 MB of
models) against 24.6 MB for the same meshes baked with `kf` (a standing and a mover model each), so the image is
about 14.5 MB smaller. In memory a placed creature holds one rest frame instead of two models of 16 and 38 frames; its
table (12 to 56 KB, or the shared humanoid table for the two-legged ones) is held once per kind. Posing a skeletal
model costs CPU per drawn frame, as every person already does; not yet measured in a running game. Fargoth's and the
guard's missing layout is FARGOTH-STANDING-NO-LAYOUT-66.

Since v0.0.67 the audit reads a creature's table as the engine plays it (ACTOR-AUDIT-APPENDED-TABLES-66). A creature on
the humanoid skeleton (the skeletons, goblins, dremora, liches and others) has a table appended to the shared humanoid
table: its own groups first, then the humanoid table's. The audit read every table as a plain one, so it counted those
creatures as playing nothing, or only their own few groups, while the game plays the whole humanoid set for them. On the
v0.0.66 release build, read correctly, about 160 records lack a kind instead of up to 560, nearly all of them expansion
actors that build does not place, and the gaps list says so.

### Whole creature models and the surface check

A creature whose gallery profile says `whole` (`config/gallery_model_quality.json`; today the cliff racer, whose thin
wing membranes and tail every reduction left full of holes, CREATURE-RACER-MESH-SPIKE-58) keeps every source triangle
on its source vertices, with the original textures in one skin atlas. Up to v0.0.65 that model came from the `kf`
bake. The `skeletal` method from v0.0.66 did not read the profile: the racer was baked to 474 of its 965 triangles,
every triangle on three vertices of its own with its own baked texture tile, 62 open edges (CREATURE-RACER-HOLES-67).
And its root bone is named `root bone`, not `Bip01`, so its own table kept the walk's and the run's travel, and the
box every pose is drawn in stretched to 8,069 units along its body: every drawn vertex was off by up to 15.8 units.

Since v0.0.67-dev3 such a creature takes the skeletal method's whole route (`tools/creature_whole.py`): its own table,
with its own root held in place in the walk and the run as OpenMW holds it, and its whole model on that table. The
cliff racer: 965 triangles on its 667 vertices, skin 512 by 288 with the original textures, every pose drawn within
1.75 units (0.4 % of its size), and all its table groups (the second and third attack, knockdown and its deaths). The
route has its own unit worker, so the other creatures' models keep theirs.

The library then compares every standing model, in the idle's first pose, with its source mesh posed the same way
(`tools/creature_surface.py`): triangles, the share of the source's surface within one unit of the model, and the
shapes whose surface the model lost (the `kf` bake's reduction check). A model whose profile keeps it whole and is not
stops the stage; the others are written to the library report. On the v0.0.67-dev2 library, for the record: the cliff
racer 83 % (474 triangles, two shapes lost), the frost giant 66 %, the netch bull and the kwama queen 69 %, the guar
with its pack 70 %, every other creature from 82 to 100 %.

The root travel is the same for every creature whose root bone is not named `Bip01`: their walk and run carry it, and
their boxes are coarser (the three worst after the racer: 2.8, 2.5 and 1.4 % of their size; the rest 0.2 to 1.1 %).
Holding every creature's own root re-bakes every creature model and room resident, so it comes as its own change after
v0.0.67-dev3 (CREATURE-TABLE-ROOT-TRAVEL-67).

## The build's actor spec check

Since v0.0.66 the image step stops a full build whose people and creatures fall short of the original or are out of
spec (`tools/actor_spec_check.py`, run right after the creature census, about 35 seconds on stored outputs; by hand:
`python3 tools/actor_spec_check.py RUN --data-files DIR`). It has two parts:

- Placement, per area kind: the NPC, creature and levelled creature references (deleted ones left out) of the cells
  of the selected masters, merged as the game merges them, counted for interiors, the region exteriors, the town
  exteriors and the water (swim-only creatures and lists that give only them), against what the build places: in the
  rooms, the references the image's maps carry, each under its own record's kind (a levelled point of an expansion
  room counts like one of the base game's); outdoors, the actor table under the town and region rules. A kind short by
  more than `config/actor_census_allowlist.json` allows fails; each allowed shortfall names its register entry.
  With the expansions selected, the places the build sets aside on purpose leave both sides and are listed by name
  with their register entry (the same file's `set_aside`): Mournhold's districts, which behave like an exterior and
  wait for the Mournhold exterior work (INTERIOR-NO-AMBI-66), the expansion rooms the room stage refused
  (EXPANSION-ROOMS-REFUSED-66), the cells the game data leaves empty, which the room stage lists as empty and makes no
  room of (no scenery to convert, at most an actor, and no door leads in; ROOM-EMPTY-CELL-66), and Solstheim's
  exterior cells, which no map holds yet (EXTERIOR-EXPANSION-ONLY-CELLS-66). Each list of rooms the room stage does not
  make is read as its own group, by the name the stage records it under. Only an expansion's references are set aside;
  a base game reference in such a place still counts as missing. With the base game alone nothing is set aside.
- Records: the audit above over the build's actor data; a field (level, attributes, skills, health, magicka,
  fatigue, behaviour values, flags, spells, inventory, the carried weapon and ranged weapon, packages, animations)
  with more missing or different records than `config/actor-record-gaps.json` lists fails.

On the v0.0.66-dev1 build it fails: the town maps place 0 of 4 creatures and 0 of 112 levelled creature points of
their cells (46 of them water lists), and the creature weapons and ranged weapons are not held (both fixed on the line
after that build; this tree's actor table passes the record part).

The first build with Tribunal and Bloodmoon selected (v0.0.66-dev2) stopped in it (BUILD-ACTOR-SPEC-EXPANSIONS-66):
the rooms' original counted the three masters' references while the placed levelled points were the base game's
alone (1,266 of 1,532: the 262 points the image places in the expansions' rooms were counted as missing), and the 50
NPCs and 13 creatures of the Tribunal places the room stage sets aside counted as missing too. Counted like for like
on the same build, every kind is within its tracked gap: in the rooms 2,738 of 2,740 NPCs, 888 of 891 creatures and
1,528 of 1,532 levelled points (the 2, 3 and 4 of the allowlist), with 50 NPCs and 13 creatures set aside; outdoors
everything planned is placed, and Solstheim's 82 NPCs, 120 creatures and 860 levelled points are set aside (before,
they counted as placed because the actor table holds them, though no map does). Its record part counted 52 actors
holding a melee weapon where their record also gives a ranged one, against 43 listed: the same two gaps (the opening
rating, ACTOR-RANGED-COMBAT-MISSING-66, and the one levelled pick, ACTOR-LEVELLED-INVENTORY-ONE-PICK-66) over nine
Bloodmoon actors the earlier count left out; the list now says 52.

The v0.0.66-dev3 build stopped in it once more (BUILD-ACTOR-SPEC-EMPTY-ROOMS-66): interior NPCs 2,738 of 2,741 placed,
3 missing against 2 allowed. Since that build the room stage lists the four cells the game data leaves empty under a
list of their own instead of among the refused rooms (Mournhold, Royal Palace, whose one Tribunal NPC stands in a cell
with no scenery and no door leading in, and three cells with no reference at all), and the check read only the two
older lists, so that NPC counted as missing. The check now reads the empty list as its own group; on the same build's
outputs it passes in about 20 seconds: in the rooms 2,738 of 2,740 NPCs, 893 of 896 creatures (the three Sotha Sil
rooms the dev2 build refused convert in this one, their 5 creatures placed) and 1,528 of 1,532 levelled points, with
50 NPCs and 8 creatures set aside.

Since v0.0.67 the outdoor rows count only what the engine can spawn (OUTDOOR-CREATURES-REGRESSION-66): a person or
creature whose base has a model in the build, a levelled point whose list can give such a creature at some level, with
the actor table and the creatures switched on by the image's own `default-game.cfg` (`chim actors table 1`; no
`chim actors creatures 0`). Before, every row of the table counted as placed, so a build whose creatures had lost their
models, or whose settings left the table off, would have passed while no creature appeared outdoors. On the v0.0.66
release build the count is the same as before (every outdoor creature and levelled point has a model; the table and
the creatures are on), and the check prints the settings it read.

The same models are checked early, in seconds, on the actor library stage's own output (`tools/actor_early_checks.py`,
the builder's early check `outdoor-creature-models`): when the stage is taken from an earlier run, before the first
stage; when the build makes it, the moment it has passed. Every creature the base game places outdoors and every
outdoor levelled list must give a creature with a model in the library, or the build stops before the world stages
and names the records (the v0.0.66 release library: 333 placed creatures and 5,082 levelled points, all with a model,
about 2 seconds).

## The expansions' actors

Since v0.0.67 the same check has a third part when Tribunal or Bloodmoon is selected (`tools/expansion_actor_check.py`;
with the base game alone it does not run and the report is as before). Each expansion is done in three stages, each a
milestone with a measured count, and `config/expansion-stages.json` says which stage each one is worked at:

1. the world: the expansion's rooms and exterior cells built and reachable;
2. the actors: every person and creature it places, in its own places and in Vvardenfell, placed and complete: a model
   the game plays, every stat its record has, its inventory and equipment, its combat style, every kind of animation
   the original gives it, and its own script attached with its variables;
3. the script logic: the global, start, quest and dialogue result scripts, the message boxes, the stats scripts set
   and the expansion's movies.

The report (`actor-spec-check.json`, key `expansion_actors`, with every placement in `expansion-actors.json` beside
it) gives per land (Mournhold, Solstheim and the actors inserted into Vvardenfell) the places built, the actors placed
and complete with the columns the others lack, and the scripts compiled, attached and running. At milestone 1 these
are counts; from milestone 2 on, every incomplete actor of that expansion stops the build with a line naming the actor,
its reference, its place and what it lacks, and the same check runs on the previous build's outputs before the first
stage. A world-wide gap with its own register entry (the levelled inventory picked once at build time,
ACTOR-LEVELLED-INVENTORY-ONE-PICK-66) is counted and named, never a stop.

On the v0.0.66 release build's outputs (both expansions at milestone 1, about 20 seconds for this part):

| Land | Actors placed | Complete | What the rest lack (placements) |
| --- | ---: | ---: | --- |
| Mournhold | 354 of 412 | 205 | script attached 172, placed 58 (the five districts and one empty room are set aside), model 41, animations 44, inventory 22 |
| Solstheim | 274 of 476 | 93 | script attached 359, placed 202 (exterior cells not built yet) |
| Inserted into Vvardenfell | 59 of 59 | 58 | inventory 1 |

The missing script bindings are fixed in v0.0.67 (EXPANSION-SCRIPTS-NOT-ATTACHED-66), so the next build counts them
attached.

## Sources and method

- The three master files, read in a container on 5 November 2026: every record of the types listed, the last record of an id
  winning. The survey scripts and their outputs are kept in the project's working notes.
- OpenMW 0.51 source (GPL-3.0): the record readers for people, creatures, races, classes, birthsigns and the behaviour data; the
  person's first-use code (derived values); the spell-derivation code; the resistance code; the save records. Read for the
  rules only; AmiWind's code is its own.
- [ACTOR_STATE.md](ACTOR_STATE.md), [ACTOR_STATS.md](ACTOR_STATS.md), [CHARACTER_CREATION.md](CHARACTER_CREATION.md), [COMBAT.md](COMBAT.md),
  [GAME_FEATURES.md](GAME_FEATURES.md) and [NPC_DEFAULTS.md](NPC_DEFAULTS.md) for what AmiWind holds today.
- The community reference on the original's mechanics (a local copy was consulted for the skills and specializations).
