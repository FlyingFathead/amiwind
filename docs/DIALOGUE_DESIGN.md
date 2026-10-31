# Dialogue: design (topics, conditions, choices, disposition, journal)

_Last updated with AmiWind v0.0.57 (31 October 2026)._

<!-- contents start -->
## Contents

- [The game's data, measured](#the-games-data-measured)
- [What OpenMW 0.51 does (the rules we follow; our own code)](#what-openmw-051-does-the-rules-we-follow-our-own-code)
- [Plan](#plan)
- [The two cheap fixes first](#the-two-cheap-fixes-first)
- [Order of work](#order-of-work)
- [Built so far](#built-so-far)

<!-- contents end -->

Status (DIALOGUE-57): steps 1 to 3 of the order of work below are built; result scripts, disposition and the
journal book reading the table follow. See "Built so far" at the end. What ran before: the greetings and the voice lines (the NPC voice
table, docs/NPC_VOICE_TABLE.md), the compiled game scripts with MessageBox and the journal calls
(docs/MWSCRIPT_BYTECODE.md), the earned journal book (docs/WORLD_MAP_AND_JOURNAL.md), the Talk prompt and its rule
(engine/aga/src/aw_talk.c). What does not run: topics, their conditions and result scripts, choices, disposition
changes, persuasion, and most journal entries. This note plans them so that the 32 MB Fast machine keeps only a small
index in memory.

## The game's data, measured

Morrowind.esm, read in a container (the same reader as tools/greeting_lut.py), 30 October 2026:

| Kind | Topics (DIAL) | Responses (INFO) | Response text | Conditions | Result script source |
| --- | --- | --- | --- | --- | --- |
| Topic | 1,698 | 13,082 | 2.37 MB | 15,801 | 426 KB |
| Greeting | 10 | 3,025 | 339 KB | 4,352 | 74 KB |
| Voice | 8 | 4,614 | 127 KB | 4,257 | 64 KB |
| Persuasion | 10 | 483 | 31 KB | 425 | 10 KB |
| Journal | 632 | 2,489 | 391 KB | - | - |
| **All** | **2,358** | **23,693** | **3.25 MB** | **24,835** | **573 KB** |

The longest response is 512 bytes. Speaker filters: 11,594 responses name one actor, 4,756 a race, 2,223 a class,
2,287 a faction, 2,436 a cell. The biggest topics: "latest rumors" with 266 responses, "Service Refusal" with 256.
Condition kinds (the SCVR type letter, OpenMW's selectwrapper.cpp order): journal 8,212, function 5,486, global
4,746, not-local 2,593, dead 1,258, item 1,048, not-id 427, local 358, not-class 237, not-race 189, not-cell 142,
not-faction 139.

None of this fits in memory as it is (3.8 MB of text and scripts against 32 MB in all), and almost none of it is
needed at once: one conversation reads one actor's topics.

## What OpenMW 0.51 does (the rules we follow; our own code)

Read in the amiwind-openmw:0.51.0 image, apps/openmw/mwdialogue/:

- **First match** (filter.cpp `Filter::search`, `list`): a topic's responses are tried in the data's order; the first
  that passes the actor tests, the player tests, every condition and the disposition test is the answer. When some
  response failed **only** on disposition, the answer comes from the topic "Info Refusal" instead.
- **Disposition** (`testDisposition`): the actor's derived disposition must be at least the response's. Creatures
  skip the test. Service refusals invert it.
- **Greeting** (dialoguemanagerimp.cpp `startDialogue`): the ten Greeting topics in order; the first that has a
  matching response (no Info Refusal fallback) opens the conversation; its result script runs; the topic names found
  in its text become known to the player (`addTopicsFromText`, keyword search over the text).
- **The topic list** (`updateActorKnownTopics`, `getAvailableTopics`): a topic shows when the player knows it AND
  this actor has an answer for it; sorted by name without case. A topic whose answer is already in the journal
  shows as exhausted (greyed), unless its answer leads to a topic the player does not know yet.
- **A topic chosen** (`executeTopic`): the answer's text (with %PCName style defines filled), its result script, the
  journal's topic page gets the response, the topics named in it become known.
- **Choices** (`questionAnswered`, `addChoice`): a result script's `Choice "text" n` lists buttons; the player's pick
  sets the Choice condition and the same topic is searched again.
- **Persuasion** (`persuade`): admire, intimidate, taunt, bribe 10/100/1000; the mechanics manager's formula
  (`getPersuasionDispositionChange`) gives success, a temporary and a permanent change; the answer is the topic
  "<Kind> Success/Fail".
- **Goodbye**: a result script's `Goodbye` ends it; the dialogue then shows only Goodbye.

## Plan

### 1. Build time: the dialogue table (tools/dialogue_lut.py, id1/dialogue.lut, AWDL1)

The same method as the voice table, which already compiles the greetings this way (tools/greeting_lut.py):

- **Static filters are decided at build time.** For each Topic response, the tests that read only the speaker's
  record (actor id, race, class, faction and rank, sex, NotId/NotRace/NotClass/NotFaction, cell when the speaker
  stands in one cell only) are evaluated for every NPC record. A response that can never be said by an NPC is not
  listed for it.
- **Per NPC record: its topic list.** The topics this NPC can ever answer, each with the ordered list of its
  candidate responses (shared between NPCs with the same list, as the voice table shares its lists). On disk; one
  row read when a conversation opens.
- **Run-time conditions** (globals, locals, journal, items, the dead, the player's stats and faction, disposition,
  Choice, Random) become the voice table's 8-byte condition records with its opcode table (the same functions,
  `SCVR_FUNCTIONS` in src/mwad/npc.py, `AW_GLUT_*` in engine/aga/src/aw_glut.h); new functions get new opcodes there,
  so greetings, voice lines and topics share one evaluator.
- **Result scripts** are compiled by the game-script compiler (tools/mwscript/) into the same bytecode as the
  object scripts, each as a small program with its own string table; on disk, loaded when the response is said.
- **Texts** stay on disk in one block, Latin-1, the defines (%PCName, %Name, ...) filled at run time.
- **Hyperlinks**: the topic names found in each response are listed at build time (a few topic numbers per
  response), so the engine never searches text for keywords.
- **Journal**: every quest's entries (2,489) with their index, the quest's name and the Finished/Restart flags; the
  book reads them by quest and index.

Expected sizes (to be measured by the tool, in its report): text 3.25 MB and compiled result scripts about 0.3 MB
on disk; the resident index about 30 KB: 2,358 topic names' offsets and lengths (8 bytes each, 19 KB), the known
topic set (2,358 bits, 295 bytes, saved), the per-NPC row offsets (4 bytes each for about 2,700 NPC records,
11 KB). Everything else is read per conversation and freed when it ends: one NPC row (a few hundred bytes), the
condition records and the texts of the responses that are tried (a topic's list, usually under 2 KB).

Measured in v0.0.57 (the tool's report on the real master): 26.6 KB resident with the factions and the disposition
settings in the table (the image step's budget is 32 KB), 17,613 table entries and 28,954 run-time conditions once
script locals are named by slot, 3.5 MB on disk; a conversation reads 34.5 to 53.6 KB and frees it at Goodbye.

### 2. Run time: one conversation

1. E on a talkable actor (aw_talk.c) opens the dialogue window and reads the NPC's row.
2. Greeting: the voice table's greeting (already the first match) is said and shown.
3. The topic list: the NPC's topics that the player knows, each checked with the first-match rule (the conditions
   of its candidates evaluated in order until one holds; disposition last, Info Refusal when only that failed).
   About 30 to 100 topics per NPC, each a few condition records: a few milliseconds on a 68040.
4. A topic chosen: its answer's text, its result script (the existing interpreter, with the host calls for Choice,
   Goodbye, AddTopic, ModDisposition, Journal, and the rest the scripts already use), the named topics marked known,
   the journal's topic entry.
5. Choice: buttons in the window, the pick sets the Choice value, the topic is searched again.
6. Persuasion: a sub-list in the window, OpenMW's formula with the game's GMSTs (fPersMod, fLuckMod, fRepMod,
   fLevelMod, fBribe*Mod, iPerMinChance, iPerMinChange), the answer from the Persuasion topics.
7. Goodbye or Escape closes it; the row and the read responses are freed.

Disposition: the NPC record's base, plus the derived terms OpenMW adds (same race, faction, personality,
reputation, crime), plus the conversation's temporary and permanent changes, which are saved per actor in the
actor state table (aw_actorstate.c).

### 3. The window

The console-font list box of the settlement list (engine/aga/src/aw_listbox.c, aw_listbox_rules.c): the topic list
with search as you type, Up/Down/Enter and the mouse, drawn over the game (the paused view kept, no redraw cost).
Beside or above it a text pane for the answer (the existing dialogue text wrapping, docs/DIALOGUE_AND_WAIT.md
"Dialogue display"), and a row of buttons for choices and persuasion. A greyed (exhausted) topic is drawn dimmer.
The box component gains: a second column (the text pane), an item colour per row, a button row. dbg weapon and
dbg gear use the same component.

### 4. Saves

The known topic set (295 bytes), the actors' disposition changes (in the actor records), the journal entries
earned (already saved), the topics' journal pages (a bit per response said that leads to the journal).

## The two cheap fixes first

- **TALK-PROMPT-NOT-TALKABLE-54**: already fixed in v0.0.55 by TALK-PROMPT-RULES (engine/aga/src/aw_talk.c: the
  prompt and E share one rule; dead, hostile, knocked down or without anything to say: no talk; tests/aga_talk_test.c).
  The register entry is closed with that.
- **NPC-GREETING-PICK-33**: the conversation greeting already takes the first match in the voice table
  (tools/greeting_lut.py, the engine's AW_Glut*). What is left is the build-time fixture `greeting_fixture` in
  src/mwad/npc.py, which picks one approach line per NPC for the older per-NPC fields (aw_voice / aw_line) with the
  highest disposition threshold at 50. Changing it to the first match changes those fields in every NPC placement,
  which re-keys the NPC and CHIM world stages (a whole-world rebuild for a fallback field the voice table overrides
  wherever it has a row). Proposal: change it together with the next change that rebuilds the world anyway, not
  alone.

## Order of work

1. tools/dialogue_lut.py with its report (the sizes above, measured) and tests on a synthetic master; the image step
   beside the voice table's.
2. The engine reader and the first-match search with the shared condition evaluator; a native test against the
   tool's own answers for a few NPCs (as tests/test_ambient_lut.py does).
3. The window on the list box; Talk: E opens it; greeting, topics, answers, Goodbye.
4. Result scripts and choices on the existing interpreter.
5. Disposition and persuasion; the journal entries of every quest.
6. A/B with headless OpenMW 0.51 for a few NPCs (the same topics, the same answers), and FS-UAE pictures at 32 MB
   Fast.

## Built so far

**1. The table** (`tools/dialogue_lut.py`, `id1/dialogue.lut`, AWDL1; the image step runs right after the voice
table's and checks that its NPC rows are the voice table's). Measured on Morrowind.esm, 30 October 2026:

| Part | Size | When it is in memory |
| --- | --- | --- |
| Topic rows (1,708 topics: 1,698 Topic, 10 Persuasion), NPC row offsets (2,673), fixture | 24.8 KB | the whole session |
| Globals (23) and names (1,243) the condition records name, with their strings | 25.0 KB | while a conversation is open |
| One conversation's buffer (that, the NPC's row, every candidate answer and its conditions) | 34.5 KB median, 53.6 KB at most (Eno Hlaalu, 747 answers) | while it is open (budget 80 KB) |
| Rows (1,835 distinct; 40 topics per NPC on average, 258 at most), lists, 14,901 entries, 22,482 conditions, 36,817 links, 632 quests with 2,489 journal entries, 263 KB of result scripts, 2.06 MB of texts | 3.5 MB | on disk, read as needed |

The table takes 16 s on 8 cores. The image step refuses a table past the budgets (32 KB resident, 40 KB of names,
80 KB per conversation). Topics are listed by name without case; a topic's answers keep the data's order, cut after
the first that has no run-time condition; Choice is a run-time condition here (the greeting fixes it to "no choice
open"). Result scripts are stored as their source for now (step 4 compiles them). Hyperlinks: the Topic names an answer's text
names, longest first, not inside a word, each once.

**2. The engine reader and first match** (`engine/aga/src/aw_dial.c`). A conversation reads the NPC's row and its
candidates into one buffer; the answer to a topic is the first candidate whose conditions all hold; when none holds
but one failed only on its disposition test, the answer comes from "Info Refusal". The condition records are tested by
the voice table's evaluator (`aw_glut.c AW_GlutCond`, now shared: greetings, voice lines and topics), which also reads
the open Choice. `tests/test_dialogue_lut.py` checks the engine against the tool's own answers (synthetic data; and on
Morrowind.esm, 11,135 answers of 32 NPCs matched).

**3. The window** (`engine/aga/src/aw_dialwin.c`). Talk (E) on an NPC with a dialogue row opens it with the
greeting (an NPC without one keeps the greeting as a subtitle); `dbg npcs talk [ID]` opens it with the nearest such
NPC, for checks. On the right: the topics the
player knows that this NPC answers (an answer or a refusal; OpenMW's getAvailableTopics), by name, with search as
you type, Up/Down, Enter and the mouse. On the left: the conversation, each chosen topic's name over its answer
(PgUp/PgDn or the wheel scroll it). The topics an answer names become known. Goodbye (the button, Escape or F10)
ends it. A new character knows the topics the census captain's answers add (their AddTopic calls, read from the
data: nine on Morrowind.esm). Not yet: result scripts and choices (step 4), disposition changes and persuasion
(step 5), saving the known topics, topics named in the greeting.

**Live state (v0.0.57 rc1).** The conditions read the game as it is, through the script host: journal indexes,
dead counts, the player's items, globals, the speaker's script locals (the table names each local by its slot in
the speaker's script, read by the script compiler's own declaration rule), the player's faction ranks and expelled
marks, and the character's level, sex, attributes and skills. Measured on Morrowind.esm before this: 9,775 of the
22,482 run-time conditions read a fixed start value and 1,814 could never pass. Still the start value: SameRace,
SameSex, RankRequirement and the rest of the player's state the engine does not keep yet.

**The disposition bar (v0.0.57 rc1).** Across the top of the window, blue, with its number: the NPC's disposition
toward the player as OpenMW works it out (MechanicsManager::getDerivedDisposition, our own code): the NPC's own
(its record, with the scripts' changes) plus the same-race bonus, the player's Personality, the faction term (its
reaction toward the player's factions, by rank) and the crime level, with the game's own settings (fDisp*) and
faction reactions, which the table now carries. OpenMW has no reputation term; disease, a drawn weapon and Charm
are not read yet. Every Disposition test of the conversation reads this value. Read only: persuasion comes later.

**Defines (v0.0.57 rc1).** %PCRank and %NextPCRank (the player's rank in the speaker's faction, rank 0 when not a
member, as OpenMW; "%" when the speaker has none; the rank names from the table) and %Cell (the player's place, as
the HUD names it), besides the speaker's and the player's defines filled before.
