# The saved game's budget: size, memory and time of a long game's save

_Last updated with AmiWind v0.0.66-dev2 (14 November 2026)._

A saved game is the game data plus every change made since the new game: taken, moved, dropped, disabled and locked
objects, container contents, the actors' state and changed records, script locals and global scripts, every global,
quest and topic, the dated journal, the explored map, markers, and the smaller blocks (see
[SAVEGAME_PLAN](../SAVEGAME_PLAN.md)). This page keeps the measured cost of such a save as the save grows, so every
change to the save is judged against a number, not a guess. Each line names the build, the test and the line it
compares against.

## The record

| | |
| --- | --- |
| Source | the v0.0.66 line (3673faee) |
| Test | `tests/aga_save_budget_test.c` driven by `tests/test_save_contract.py`: a synthetic 100-hour game, saved once, loaded whole, saved again |
| Where | host (the gate's Linux container, the native codec); the 68040 times are not measured yet |
| Game sized from | a late original save of one long playthrough: about 7,700 changed references (800 of them the player's drops), 242 touched containers, 3,000 changed actors, 2,800 script locals, every global (143), quest (632) and topic (about 2,400), 1,400 refilled places, and a journal of 2,489 entries (every entry the master holds) |
| Previous line | none: the first measurement of a whole long-game save |

## The numbers

| Part | Bytes | Share |
| --- | --- | --- |
| The fixed part (character, story, items, position) | 852 | 0.1 % |
| The world change list without the actor records | 397,902 | 40.4 % |
| The changed actor records (3,000 records of 182 bytes) | 546,012 | 55.5 % |
| The dated journal (2,489 entries of 16 bytes) | 39,832 | 4.0 % |
| **The file** | **984,606** | 100 % |

| Measure | Value |
| --- | --- |
| Memory held by the change list in play | about 913 KB (rows, places, extras, tables) |
| Memory held while saving | 1,459,388 bytes (the list plus the copy of the changed actor records, freed when the file is written) plus the one encode buffer of the file's size |
| Encode (host) | 45 ms |
| Decode (host) | 120 ms |
| Loaded game saved again, unchanged | the same bytes: nothing duplicated, nothing grown |

## Reading it

The file sits at the 1 MiB mark, which the save is meant to stay well under. More than half of it is the changed
actors' records written whole (every stat of every changed actor), where the rest of the list writes only what
differs from the game data. Writing an actor record as the fields that differ from its base row is the next saving
to measure; the base rows are in the game's own tables on disk, so nothing is lost by it. The journal and the fixed
part are small; the change list without the records is about 50 bytes per changed thing on average, with the
reference identities (8 bytes each, for loading a save made with other game data) a fifth of it.

The host times say nothing about the Amiga; the save and load of this file on the 68040 at 32 MB Fast RAM are the next
measurement, on the emulator and on the Raspberry Pi 4B, and the numbers will be added here against this line.
