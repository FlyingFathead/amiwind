# Every being's stats

_Last updated with AmiWind v0.0.61-dev3 (2026-11-06)._

Every NPC and creature in the game, and the player, carries the stats its original record gives it, even where no
game system reads them yet. They are kept in one place and read through one set of calls, and each kind of being
holds exactly what its record type holds and nothing more. Status: **in progress** (v0.0.61). In: the builder side,
the engine's decoder, the live actor records made from it when an area loads (so the scripts' stat functions read
them), and combat's fighter sheets taking their stats from it. Next, one at a time: the stat window, the dialogue
facts, levelling and rest, and the live block split by kind.

## What each record type holds

| Record | Holds |
| --- | --- |
| NPC with its own stats (the long NPC data) | level, 8 attributes, 27 skills, health, magicka, fatigue, disposition, reputation, faction rank, gold |
| NPC with auto-calculated stats (the short NPC data) | level, disposition, reputation, faction rank, gold; the attributes, skills, health, magicka and fatigue are worked out from its race, class and level |
| Creature | type, level, 8 attributes, health, magicka, fatigue, soul, combat, magic and stealth values, 6 attack values (chop, slash and thrust, minimum and maximum), gold |
| Every actor | its flags and blood type, its behaviour values (hello, fight, flee, alarm and the services it offers), its spells and abilities; NPCs also race, class and faction |

Measured on the game data (the three masters): 1,102 NPCs with their own stats, 1,939 auto-calculated NPCs and 396
creatures.

Known gaps in v0.0.61-dev3: the fallback for actors far from the player and the widened greeting value are still to
come (`ACTOR-STATS-FAR-FALLBACK-61`, `ACTOR-HELLO-CLAMPED-61`).

Resistances and weaknesses are not stats in the original. They come from the being's abilities and spells: a race's
abilities (a Nord's resistance to frost), or a creature's own spell list (the ghosts' resistance to normal weapons).
Each being's entry therefore carries its ability and spell rows, and the magic code sums their effects.

## Where the stats live

There is no separate stats file. The stats travel in the per-area tables the engine already reads when a room or an
exterior cell loads (`id1/areas.awa`; the actor record itself is in [ACTOR_STATE.md](ACTOR_STATE.md)). Each area's
record gains a stats section holding one entry for every actor placed there. The section loads with the same single
read as the rest of the area and is freed with it.

- **The entry.** A kind byte (stored-stat NPC, auto-calculated NPC, creature), a small present mask, then only the
  fields that kind holds, each in the width its values need. Auto-calculated NPCs store only level, disposition,
  reputation, rank, race and class; the rest is derived when the actor is made. Fields such as gold, services,
  faction and spells are written only when the record has them.
- **Nothing repeated.** The race rows (attribute bases, skill bonuses, racial powers), the class rows (favoured
  attributes, specialization, major and minor skills) and the skill table (each skill's governing attribute and
  specialization) are kept once, in one small shared stats record of the same pack (about 4.7 KB), read once with
  the pack's index and kept. An area's entries name those rows by number.
- **Levelled creatures.** A levelled creature list can give any of several creatures. Outdoors the same lists cover
  many cells, so the creatures they can give are kept once, in the shared record. A room keeps the creatures of its
  own lists in its own section, so entering a room is still one read.
- **The direct lookup.** Every placed actor already has a row in its area's record. The builder writes that actor's
  entry offset into the row, so a spawning actor jumps straight to its entry. A sorted table of id hashes answers
  actors that are not placed in the area: someone a script or a conversation names, or a levelled pick.

How it loads. Entering a room reads the room's area record (its rows, containers, items and the stats of all its
characters) in one read, in the same loading step as the room's map; NPCs do not move between a room and the outside,
so nothing streams within a room. In that same step every character of the room gets its live record from its entry,
before the room is shown; nothing is made later on first use. Outdoors the 3 x 3 window of cells around the player
loads as before, one read per cell, and the live records of the new cells' actors are made a few per frame (four),
so crossing into a cell never makes them all in one frame; an actor that is needed sooner gets its record at once.
`dbg mwscript stats` shows a being's stats and the last load's numbers.

Sizes on the game data, measured before and after sharing: with every area holding its own copies, the sections were
1.31 MB (16,433 creature entries for 228 different creatures, 1,640 copies of 10 race rows, 2,305 copies of 76 class
rows). Kept once instead: 306 KB over 1,377 areas plus the 4.7 KB shared record. Per area the median is 131 bytes and
the largest 1,690 bytes (a tomb with 25 creatures); the largest exterior cell holds 576 bytes. The sections need no
file open of their own: at 2 MB/s the largest room reads under 1 ms more, and a typical outdoor load of nine cells
about 0.6 ms more.

Measured in game (6 November 2026; AmiWind v0.0.61-dev1 MiniWind of Seyda Neen, commit 90eb3646, FS-UAE with the JIT
68040 preset at 32 MB Fast; area stats on, the default): entering Arrille's Tradehouse made all 7 of its characters'
live records in the loading step in 1.1 ms; outdoors the worst frame of the staggered making (4 actors a frame) took
1.0 ms. The first outdoor load's step took 124 ms, nearly all of it opening the actor table once, which the scripts
otherwise open on their first actor call. The readouts of `dbg mwscript stats` for nine beings (Fargoth, Eldafire and
Tandram Andalen auto-calculated; Processus Vitellius, an Imperial guard, Arrille, Elone and Hrisskar Flat-Foot with
their own stats; a mudcrab) matched their records stat for stat, and their live records matched their blocks; the
player's sheet was unchanged.

## How the values read

The calls follow the original game's rules as OpenMW 0.51 implements them (read for the rules, never copied):

- A stat the being's record stores reads as stored.
- An auto-calculated NPC's attributes, skills, health, magicka and fatigue are derived from race, class and level,
  as the original's auto-calculation does.
- A creature asked for any skill answers with its combat, magic or stealth value, chosen by that skill's
  specialization.
- An actor without behaviour values reads the record defaults (an NPC's hello, fight and flee 30).
- Anything else a record type lacks reads 0. The faction rank of an actor without a faction reads -1.
- A separate call tells whether the being's kind stores a stat at all.

Checked on the game data: every NPC and creature of the three masters (3,437) read through the engine's decoder
matches its record, and every auto-calculated NPC matches the builder's own auto-calculation.

## The live block per kind

Only actors in the loaded areas carry a live block. The others are rebuilt from their area's entry plus the saved
change list when their area loads. The live block holds what play changes, as OpenMW keeps it per actor: base,
modifier and damage of every attribute (and of every skill for NPCs and the player), health, magicka and fatigue
(base, modifier, current), the behaviour values, disposition and reputation, the death, knockdown, attack, block and
drawn states, timers, and links to the active effects, the behaviour packages, the script's local variables and the
item and
spell changes. Creatures keep no skills of their own, so their block has no skill part. Rare data (a merchant's gold
pool, crime and bounty, changed faction ranks, summons, the player's level progress) lives in a small side record
made only when used and saved through the change list.

## Credits

The record layouts and the reading rules were learned by reading OpenMW 0.51's source (GPL-3.0); AmiWind's builder
and engine code are its own, nothing copied ([LICENSING_AND_CREDITS.md](LICENSING_AND_CREDITS.md)).
