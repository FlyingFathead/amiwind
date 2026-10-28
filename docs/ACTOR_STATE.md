# The actor record

_Last updated with AmiWind v0.0.54-dev1 (27 October 2026)._

<!-- contents start -->
## Contents

- [Where the numbers come from](#where-the-numbers-come-from)
- [The file](#the-file)
- [In memory](#in-memory)
- [The calls](#the-calls)
- [The scripts' actor functions](#the-scripts-actor-functions)
- [Saved games](#saved-games)
- [Next](#next)
- [Credits](#credits)

<!-- contents end -->

Every NPC and creature of the three masters (Morrowind, Tribunal and Bloodmoon) has one compact record that the
engine owns from load: level, attributes, skills, health, magicka and fatigue, the behaviour ratings, disposition,
inventory and spells. Combat, behaviour and the compiled game scripts ([MWSCRIPT_BYTECODE.md](MWSCRIPT_BYTECODE.md)) all
read and change the same record, as OpenMW's script extensions do; play's changes are saved with the game. The
maintainer asked for it on 25 October 2026 ("the mwscript hook for each character's baselevel abilities, weapons,
stats, inventory"), with the starting stats of every character and of the player. What the values usually are, how
they are assigned and changed, the NPCs' sounds and movements and the item coverage are in
[NPC_DEFAULTS.md](NPC_DEFAULTS.md).

Status: **in progress** (v0.0.54). The table is built in every build; the record, its calls and the compiled
scripts' actor functions are in the engine ([MWSCRIPT_BYTECODE.md](MWSCRIPT_BYTECODE.md), experimental with the
scripts, `dbg mwscript on`); the changed records are kept in saved games. Not checked in game yet.

## Where the numbers come from

The builder reads every NPC_ and CREA record of the masters (the last master's record of an id wins, as in the game)
and writes one row per actor:

- NPCs with their own stats (a 52-byte NPDT) keep them as the record holds them.
- NPCs with autocalculated stats (the 12-byte NPDT, 1,939 of 3,041) get them by the original autocalculation:
  attributes from race, sex, class and level, skills from race, class and specialization, health from Strength,
  Endurance, the class and the level; fatigue is Strength + Willpower + Agility + Endurance and magicka Intelligence
  times the game setting fNPCbaseMagickaMult. Rule from OpenMW (mwclass/npc.cpp autoCalculateAttributes and
  autoCalculateSkills, mwmechanics/creaturestats.cpp); the same code makes the combat sheets
  (`tools/prepare_combat.py`).
- Creatures keep their record's values; their 27 skills are the record's combat, magic and stealth values, each by
  the skill's specialization (rule from OpenMW mwclass/creature.cpp).
- Inventory: every carried entry, a levelled list resolved as the combat sheets do it (the highest entry at or below
  the actor's level), each entry an index into one shared item table (weapons with their damage, reach, speed,
  weight and condition, armour with its rating, clothing, other items), never a copy. The worn weapon and armour are
  the combat sheets' choice (the best melee weapon, the first armour piece of each slot, no shield with a two-handed
  weapon). The scripts' gold coins (gold_005, gold_010, gold_025, gold_100) are one item, as in OpenMW, and the
  record's gold counts as it.
- Spells: the record's own, plus the race's powers and abilities for NPCs (as OpenMW adds them).
- The behaviour ratings Hello, Fight, Flee and Alarm (AIDT). The behaviour packages (wander, travel, follow, escort, activate)
  and the path grids are another table of their own, not part of this record.

The player's record is the character sheet the character creation makes (race, sex, class and birthsign:
`aw_character.c`); its starting stats follow the same rules, and the record calls read and write that sheet, so
there is one copy of the player's stats.

## The file

The table is written into `id1/mwscript.awm` by the `mwscript` builder stage (one unit keyed by the masters and the
compiler's source, which now includes `tools/mwscript/actors.py` and `tools/prepare_combat.py`), as six sections
after the script sections. Big-endian; the layout is in `tools/mwscript/actors.py`.

| Section | Row | Holds | Stays |
| --- | ---: | --- | --- |
| OACT | 2 | the actor each script object names (the scripts' targets) | in memory with the scripts |
| ACTB | 96 | one actor: id, kind, flags, level, attributes, skills, behaviour ratings, disposition, reputation, rank, health, magicka, fatigue, race, class, faction, gold, its inventory and spell lists, its weapon, creature type, attacks, soul | on disk |
| AINV | 6 | an inventory entry: item, count, flags (worn, from a levelled list, restocks) | on disk |
| AITM | 28 | a shared item: id, kind, type, condition, armour rating, damage, flags, weight, speed, reach | on disk |
| ASPT | 4 | a shared spell: id, type | on disk |
| ASPL | 2 | a spell entry | on disk |

Measured on the game data (27 October 2026): 3,437 actors (3,041 NPCs, 396 creatures), 20,596 inventory entries,
1,691 items, 629 spells, 14,276 spell entries; with the items, spells and objects the scripts name (v0.0.54's
script functions), 1,797 items (AITM 50,316 bytes), 660 spells (ASPT 2,640) and an OACT of 1,302 bytes.

| | Bytes |
| --- | ---: |
| ACTB | 329,952 |
| AINV | 123,576 |
| AITM | 47,348 |
| ASPT / ASPL | 2,516 / 28,552 |
| OACT (resident) | 976 |
| Names added to STRS | 74,000 (about) |
| All, on disk | 606,920 |

For comparison, `combat/actors.txt` (the combat sheets, kept: nothing of it is removed) is about 480 KB of text for
the NPCs of Morrowind.esm only, without inventory, spells or creatures.

## In memory

The rows stay on disk. An actor's row is read when the actor is first needed (a script names it, a fight starts); its
live record then holds what play changes. Resident while the game runs:

| | Bytes |
| --- | ---: |
| The live records (a pool of 128, 268 bytes each, measured on the host build) and the player's | 34,572 |
| The dead counts (2 bytes an actor) | 6,874 |
| OACT | 1,302 |
| The saved-game buffers (one for a save, one for a loaded save; `aw_save.c`) | 65,536 |

A live record that differs from its row is kept; an unchanged one may give its place to another and is read again
from its row when needed. Finding an actor by id is a binary search on disk (12 reads at most).

## The calls

`engine/aga/src/aw_actorstate.h`. Pure C, no engine headers; the host gives one read function for the file.

```c
int AW_ActorStateOpen(const unsigned char *head,uint32_t head_bytes,const aw_actorstate_io_t *io);
int AW_ActorFind(const char *id);                      /* the actor's row, by its id */
int AW_ActorOfObject(int object,const uint16_t *oact,int count);
int AW_ActorBase(int row,aw_actor_base_t *out);        /* the row as the builder wrote it */
int AW_ActorItem(int item,aw_item_t *out);             /* a shared item */
aw_actor_t *AW_ActorGet(uint32_t reference,int row,int create);   /* the live record of a placed actor */
aw_actor_t *AW_ActorPlayer(void);
float AW_ActorStat(const aw_actor_t *a,int stat);
void AW_ActorSetStat(aw_actor_t *a,int stat,float value);
void AW_ActorModStat(aw_actor_t *a,int stat,float value);
void AW_ActorModCurrent(aw_actor_t *a,int dynamic,float value);
float AW_ActorRatio(const aw_actor_t *a,int dynamic);
int AW_ActorOnDeath(aw_actor_t *a);
void AW_ActorKill(aw_actor_t *a);
int AW_ActorDeadCount(int row);
int AW_ActorItemCount(const aw_actor_t *a,int item);
int AW_ActorAddItem(aw_actor_t *a,int item,int count);
int AW_ActorRemoveItem(aw_actor_t *a,int item,int count);
int AW_ActorEquipped(const aw_actor_t *a,int entry);
int AW_ActorHasSpell(const aw_actor_t *a,int spell);
int AW_ActorAddSpell(aw_actor_t *a,int spell);
int AW_ActorRemoveSpell(aw_actor_t *a,int spell);
int AW_ActorStateExport(unsigned char *out,int capacity);
int AW_ActorStateImport(const unsigned char *data,int bytes);
```

Stats: `AWA_ATTRIBUTE + 0..7` (Strength to Luck), `AWA_SKILL + 0..26` (Block to Hand-to-hand), `AWA_HEALTH`,
`AWA_MAGICKA`, `AWA_FATIGUE`, `AWA_LEVEL`, `AWA_HELLO`, `AWA_FIGHT`, `AWA_FLEE`, `AWA_ALARM`, `AWA_DISPOSITION`,
`AWA_DEAD`. The rules, OpenMW's (apps/openmw/mwscript/statsextensions.cpp, aiextensions.cpp,
containerextensions.cpp; apps/openmw/mwmechanics/stat.cpp), written independently:

- Get of an attribute or skill is the modified value (base plus fortify minus damage, never below 0); of health,
  magicka or fatigue the current value (magicka never below 0).
- Set of an attribute or skill sets the base and clears its modifier and damage; of a dynamic stat sets the base and
  the current value to it. Creatures have no skills of their own to set or change.
- Mod of an attribute or skill: the modified value goes up by the amount but not past 100 unless it is fortified,
  the base stays within 0 to 100 (OpenMW's modStat). Mod of a dynamic stat changes the base (not below 0, except
  fatigue) and the current value by the amount.
- ModCurrent of a dynamic stat changes the current value only, never above the base; fatigue may go below 0 (a
  knockdown). Health at 0 or below kills the actor.
- The ratio is current over base (1 when the base is 0).
- OnDeath reads 1 once after the actor died. The dead count of an actor id counts every death of it.
- Item counts are the row's entries plus play's changes; AddItem and RemoveItem with a negative count read it as
  the unsigned 16-bit number it is, and 0 does nothing; RemoveItem takes at most what the actor has. A worn item
  that was removed is no longer worn.
- AddSpell and RemoveSpell change the actor's own list; a spell added and removed again leaves no change behind.

Not yet: a script's explicit call on an actor placed more than once changing the record of every copy (OpenMW
does that for RemoveItem and the behaviour ratings), the derived disposition (Get reads the base), autocalculated NPCs'
spells by the original spell autocalculation, the abilities' effects on the stats (Fortify Maximum Magicka and the
like come with the magic work).

## The scripts' actor functions

The compiled scripts reach the record through five opcodes (ACTOR, ITEM, SPELL, COMBAT, DEADCOUNT; the table is in
[MWSCRIPT_BYTECODE.md](MWSCRIPT_BYTECODE.md)): every attribute, skill and dynamic stat call, the level, the
behaviour ratings, disposition, OnDeath, GetDeadCount, the items and spells of any actor, StartCombat and
StopCombat. Item and spell ids and the actor of GetDeadCount are resolved by the builder to rows of the shared
tables, so the engine reads no names while scripts run. The engine side (`aw_mwhost.c`):

- The target is the script's own actor (its edict's record id, found once), another object placed once (its
  reference and the OACT row), or the player (the character sheet, read before the call and written back after;
  the player's items are the game state the engine already keeps).
- While an NPC fights, its fighter sheet (`aw_combat.c`) holds its health, magicka and fatigue; the scripts' calls
  read and write both, and once a frame during a fight its health and its death reach the record (the dead count,
  OnDeath) and wake the scripts that read actors. Combat reading the record itself is the combat work's next step.
- StartCombat starts the one fight the combat layer has, with the player, unless either is dead (OpenMW);
  StopCombat ends that actor's fight through the combat layer's per-actor end, and AIWander hands its arguments,
  read as OpenMW reads them, to the ambient tables' wander; both are hooks those parts of the engine fill
  (`aw_mwscript_combat_end`, `aw_mwscript_wander` in `quakedef.h`), and until they do the call is logged and does
  nothing. `AW_MwscriptSpeedAttribute` gives the ambient walk an actor's Speed from its record.
- The original's endgame scripts change `dagoth_ur_1` from afar after he is gone; those calls are ignored, as OpenMW
  does.
- `aw_mwscript_status` prints the record's counters (calls, records made, changed, dropped, disk reads, fights
  started and stopped, wanders).

## Saved games

The changed live records and the dead counts are saved as one block (AWAS1: the record's fixed 182 bytes plus 4
bytes per inventory or spell change; 4 bytes a dead count), kept by each actor's reference, in the save file as its
feature 16 (at most 32,768 bytes; a save over that is refused with a message and the earlier saves kept). A record
not changed by play is not saved; the player's stats are saved with the character. A save without changed actors
is the same bytes as before; an older engine refuses a save that has the block.

## Next

1. The in-game check in a MiniWind sandbox: a script's SetFight and StartCombat, OnDeath after a fight, a save and a
   load with a changed actor.
2. Combat reading its fighters from the record (one copy of the dynamic stats).
3. An explicit call on an id placed more than once, the derived disposition, autocalculated NPCs' spells.

## Credits

The rules of the stats, the autocalculation and the scripts' calls were learned by reading OpenMW 0.51's source
(GPL-3.0); AmiWind's builder and engine code are its own, nothing copied
([LICENSING_AND_CREDITS.md](LICENSING_AND_CREDITS.md)).
