/* SPDX-License-Identifier: GPL-2.0-or-later
 * The dialogue table (AWDL1, id1/dialogue.lut, tools/dialogue_lut.py; docs/DIALOGUE_DESIGN.md): every NPC record's
 * conversation topics with their answers in the original's order, the run-time conditions as the voice table's
 * 8-byte condition records (evaluated by aw_glut.c AW_GlutCond, the evaluator greetings and voice lines use), the
 * answers' result scripts and hyperlinks, and every quest's journal entries.
 * Only the index stays in memory for the session (the topic rows, the NPC row offsets and the fixture, about 25 KB on
 * Morrowind.esm); a conversation reads its NPC's row and candidates into a buffer the caller gives and frees it when
 * it ends. The NPC rows are the voice table's (the same order; the builder checks it), so an edict's row comes from
 * AW_GlutNpcOf.
 */
#ifndef AW_DIAL_H
#define AW_DIAL_H
#include "aw_mwvm.h"
#include "aw_actorstate.h"
#include "aw_glut.h"

#define AW_DIAL_VERSION 3   /* 3: the factions' rank requirements (the last section); older tables are refused */
#define AW_DIAL_HEADER 96
#define AW_DIAL_TOPIC_ROW 8        /* u32 name offset (topic strings), u8 name length, u8 kind, u16 0 */
#define AW_DIAL_ENTRY_ROW 20       /* u32 text, u32 first condition, u32 script, u32 first link, u16 links, u8 conditions, u8 flags */
#define AW_DIAL_LIST_ROW 8         /* u32 first item, u16 items, u16 0 */
#define AW_DIAL_QUEST_ROW 12       /* u32 quest id (topic strings), u32 first journal entry, u16 entries, u16 0 */
#define AW_DIAL_JOURNAL_ROW 8      /* u16 index, u8 flags, u8 0, u32 text */
#define AW_DIAL_ENTRY_LAST 1       /* no run-time condition: nothing after it can be said */
#define AW_DIAL_KIND_TOPIC 0
#define AW_DIAL_KIND_GREETING 2    /* Greeting 0..9: chosen when the conversation opens, never listed */
#define AW_DIAL_KIND_PERSUASION 3
#define AW_DIAL_NO_ROW 0xFFFFu     /* a topic with no script topic row (AW_DialTopicMap) */
#define AW_DIAL_MAX_TOPICS 512     /* one NPC's topics (Morrowind.esm: at most 258) */
#define AW_DIAL_MAX_MERGE 64       /* lists merged per topic and NPC */
#define AW_DIAL_NONE32 0xFFFFFFFFul
#define AW_DIAL_BUFFER 81920       /* one open conversation (tools/dialogue_lut.py BUFFER_BUDGET; Morrowind.esm: 53.6 KB at most) */

typedef struct {
    const unsigned char *data;     /* the resident part: header, topic rows, NPC row offsets, fixture */
    long size, file_size;
    long topics, npcs, functions;
    long row_bytes, listsets, listset_items, lists, list_items, entries, conds, globals, names, links, quests,
        journal, string_bytes, tstring_bytes, script_bytes, text_bytes;
    int info_refusal;              /* the topic "Info Refusal", -1 none */
    /* file offsets of the sections after the resident part */
    long at_conversation, conversation_bytes, at_rows, at_listsets, at_listset_items, at_lists, at_list_items,
        at_entries, at_conds, at_links, at_quests, at_journal, at_ranks, at_tstrings, at_scripts, at_texts,
         at_services, at_skill_attributes, at_ui_texts, at_rank_reqs;
    const unsigned char *topic, *npc_offset, *fixture, *known, *start;
    int starts;                    /* the topics a new character knows (the census captain's AddTopic) */
    const unsigned char *settings, *faction, *reaction;   /* the game settings, faction ids, faction reactions */
    int factions, reactions;
} aw_dial_t;

/* The game settings of the disposition (tools/dialogue_lut.py SETTINGS, same order). */
enum {AW_DIAL_SET_RACE, AW_DIAL_SET_PERSONALITY_MULT, AW_DIAL_SET_PERSONALITY_BASE, AW_DIAL_SET_FACTION_RANK_MULT,
      AW_DIAL_SET_FACTION_RANK_BASE, AW_DIAL_SET_FACTION_MOD, AW_DIAL_SET_CRIME, AW_DIAL_SET_DISEASE,
      AW_DIAL_SET_WEAPON_DRAWN,
      AW_DIAL_SET_PERSONALITY_MOD, AW_DIAL_SET_LUCK_MOD, AW_DIAL_SET_REPUTATION_MOD, AW_DIAL_SET_LEVEL_MOD,
      AW_DIAL_SET_BRIBE10, AW_DIAL_SET_BRIBE100, AW_DIAL_SET_BRIBE1000, AW_DIAL_SET_PER_MIN_CHANCE,
      AW_DIAL_SET_PER_MIN_CHANGE, AW_DIAL_SET_PER_DIE_ROLL_MULT, AW_DIAL_SET_PER_TEMP_MULT, AW_DIAL_SET_FATIGUE_BASE,
      AW_DIAL_SET_FATIGUE_MULT, AW_DIAL_SET_TRAINING_MOD, AW_DIAL_SET_SPELL_VALUE_MULT, AW_DIAL_SET_REPAIR_MULT, AW_DIAL_SET_EFFECT_COST_MULT,
      AW_DIAL_SET_SPELLMAKING_VALUE_MULT, AW_DIAL_SET_ENCHANT_VALUE_MULT, AW_DIAL_SET_ENCHANT_CHANCE_MULT,
      AW_DIAL_SET_ENCHANT_CONSTANT_CHANCE_MULT, AW_DIAL_SET_ENCHANT_CONSTANT_DURATION_MULT, AW_DIAL_SET_ENCHANT_MULT,
      AW_DIAL_SET_SOUL_FOR_CONSTANT, AW_DIAL_SETTINGS};
/* Persuasion (the rule of OpenMW's MechanicsManager::getPersuasionDispositionChange, our own code). */
enum {AW_PERSUADE_ADMIRE, AW_PERSUADE_INTIMIDATE, AW_PERSUADE_TAUNT, AW_PERSUADE_BRIBE10, AW_PERSUADE_BRIBE100,
      AW_PERSUADE_BRIBE1000, AW_PERSUADE_KINDS};
typedef struct {
    float personality,luck,reputation,speechcraft,mercantile,level;
    float fatigue;                 /* current over maximum (1 when rested) */
} aw_dial_person_t;
typedef struct {
    int success,temp,perm;         /* the conversation's temporary change, the permanent one */
    int fight,flee;                /* the NPC's settings after it (Intimidate and Taunt change them) */
} aw_dial_persuasion_t;
#define AW_DIAL_FACTION_ID 32
#define AW_DIAL_RANKS 10           /* a faction's rank names on disk, AW_DIAL_FACTION_ID bytes each */
/* The file offset of faction FACTION's rank RANK name (0..9), -1 when the table has no such faction. */
long AW_DialRankAt(const aw_dial_t *d,const char *faction,int rank);
/* RankRequirement (FACTION-RANK-58; the rule of OpenMW's filter.cpp and hasFactionRankSkillRequirements /
 * hasFactionRankReputationRequirements, our own code): for the player at RANK (-1 not a member) of the speaker's
 * FACTION, the next rank's requirements read from disk (AW_DIAL_RANK_REQ bytes, nothing kept): +1 when the two
 * favoured attributes (base) and the best two favoured skills meet it, +2 when the faction reputation REPUTATION does;
 * 0 at the last rank, for an unknown faction or a failed read. ATTRIBUTES[8], SKILLS[27]: the player's. */
#define AW_DIAL_RANK_REQ 112       /* the prototype follows aw_dial_read_t below */
/* The rank defines (OpenMW's rule, our own code): %PCRank is the player's rank name in the speaker's faction (rank 0
 * when not a member), %NextPCRank the one after it (at most the tenth), "%" when the speaker has no faction; %Cell
 * the player's cell. Replaces them (any case) in SOURCE, the other defines kept for AW_GlutExpand. */
void AW_DialFillDefines(const char *source,char *out,int capacity,const char *pc_rank,const char *next_rank,
                        const char *cell);
/* What the disposition reads of the game (the engine fills it; the rule: OpenMW's
 * MechanicsManager::getDerivedDisposition, our own code). */
typedef struct {
    int base;                      /* the NPC's own disposition (its record, with the scripts' changes) */
    int same_race;                 /* the player is of the NPC's race */
    float personality;             /* the player's Personality */
    int bounty;                    /* the player's crime level */
    int diseased;                  /* the player has a common or a blight disease (fDispDiseaseMod) */
    int weapon_drawn;              /* the player holds a weapon drawn (fDispWeaponDrawn) */
    float charm;                   /* the magnitude of Charm on the NPC (added as it is) */
    const char *faction;           /* the NPC's faction id (folded), NULL none */
    /* the player's rank in a faction (-1 not a member) and whether expelled */
    int (*rank)(const char *faction,int *expelled);
} aw_dial_facts_t;
/* The NPC's disposition toward the player, clamped to 0..100 when CLAMP. */
int AW_DialDisposition(const aw_dial_t *d,const aw_dial_facts_t *f,int clamp);
/* The SCVR functions that compare the speaker with the player (the rule of OpenMW mwdialogue/filter.cpp, our own
 * code): SameSex, SameRace and ShouldAttack (isAggressive: the speaker's Fight rating toward the player with the
 * conversation's disposition reaches 100). RankRequirement: AW_DialRankRequirement. Numbers: mwad.dialogue FUNCTIONS. */
#define AW_DIAL_FN_SAME_SEX 44
#define AW_DIAL_FN_SAME_RACE 45
#define AW_DIAL_FN_SHOULD_ATTACK 71
typedef struct {
    int known;                     /* the speaker's record and the player's sheet were read */
    int player_female, speaker_female;
    const char *player_race, *speaker_race;   /* race record ids, NULL none */
    int fight_rating;              /* the speaker's Fight rating toward the player, -1 not known */
} aw_dial_pair_t;
/* 1 and *OUT for one of the three, 0 when FN is another function or the facts are not known. */
int AW_DialPairFunction(const aw_dial_pair_t *p,unsigned fn,long *out);
/* The scripts' faction reaction changes (ModFactionReaction: VALUE added; SetFactionReaction: SET), A toward B, kept
 * for the game (32 at most) and saved (AWFR); the disposition reads them. */
/* The journal's topic pages: the answers heard (entry, topic, speaker's name), each answer once, bounded (aw_dial.c);
 * Add: 1 kept, 2 kept and an old entry gave way (the caller logs it), 0 not kept; RemoveLast: ClearInfoActor. */
#define AW_DIAL_SPEAKER_NAME 32
void AW_DialHeardReset(void);
int AW_DialHeardCount(void);
int AW_DialHeardAt(int i,int *entry,int *topic,const char **speaker);
int AW_DialHeardAdd(int entry,int topic,const char *speaker);
int AW_DialHeardRemoveLast(int topic,const char *speaker);
int AW_DialHeardHas(int entry);
int AW_DialHeardExport(unsigned char *out,int capacity);
int AW_DialHeardImport(const unsigned char *p,int bytes);
void AW_DialReactionsReset(void);
int AW_DialReactionChange(const char *a,const char *b,int value,int set);
int AW_DialReactionsExport(unsigned char *out,int capacity);
int AW_DialReactionsImport(const unsigned char *p,int bytes);
/* One persuasion of KIND (AW_PERSUADE_*) with the NPC's derived DISPOSITION, ROLL 0..99 and its FIGHT and FLEE. */
void AW_DialPersuade(const aw_dial_t *d,int kind,const aw_dial_person_t *player,const aw_dial_person_t *npc,
                     int disposition,int roll,int fight,int flee,aw_dial_persuasion_t *out);
float AW_DialSetting(const aw_dial_t *d,int setting);

/* Reads BYTES at a file OFFSET into OUT: 1 done, 0 failed (the engine: the open file; the host test: memory). */
typedef int (*aw_dial_read_t)(void *user,long offset,void *out,long bytes);
/* A read-through block cache over a read function (DIALOGUE-CLOSE-FRAME-FREEZE-59): a conversation's open reads
 * thousands of small rows (list items, entries, conditions) that lie close together; each became a seek and a read of
 * the file. Through this, a read is served from AW_DIAL_CACHE_BLOCKS aligned blocks of AW_DIAL_CACHE_BLOCK bytes
 * (least recently used goes); a read of a block or more goes straight through. The bytes are the file's, unchanged.
 * Use AW_DialCacheRead as the read function with the cache as USER; SIZE = the file's length (the last block is
 * short). AW_DialCacheReset forgets the blocks (a new file). inner_reads counts the reads it passed on. */
#define AW_DIAL_CACHE_BLOCK (4L*1024L)
#define AW_DIAL_CACHE_BLOCKS 16
typedef struct {
    aw_dial_read_t read;void *user;long size;
    long at[AW_DIAL_CACHE_BLOCKS],length[AW_DIAL_CACHE_BLOCKS];unsigned long used[AW_DIAL_CACHE_BLOCKS],clock;
    unsigned long inner_reads,hits;
    unsigned char block[AW_DIAL_CACHE_BLOCKS][AW_DIAL_CACHE_BLOCK];
} aw_dial_cache_t;
void AW_DialCacheInit(aw_dial_cache_t *c,aw_dial_read_t read,void *user,long size);
void AW_DialCacheReset(aw_dial_cache_t *c);
int AW_DialCacheRead(void *cache,long offset,void *out,long bytes);
int AW_DialRankRequirement(const aw_dial_t *d,const char *faction,int rank,const short *attributes,const short *skills,
                           int reputation,aw_dial_read_t read,void *user);

typedef struct {
    unsigned long entry;           /* the file's entry index (the same INFO as some NPCs see it) */
    unsigned long text, script, link;   /* offsets in the text and script blocks, first link; AW_DIAL_NONE32 none */
    unsigned short links;
    unsigned char conditions, flags;
    const unsigned char *cond;     /* its condition records, in the conversation buffer */
} aw_dial_answer_t;

typedef struct {
    const aw_dial_t *d;
    int npc, topics;
    struct {unsigned short topic, first, count;} topic[AW_DIAL_MAX_TOPICS];
    aw_dial_answer_t *answer;      /* every candidate of every topic, in the buffer */
    long answers;
    aw_glut_cond_t cond;           /* the evaluator's context: the table's globals and names, the speaker */
} aw_dial_conv_t;

/* Pure parts (host-tested, tests/aga_dial_test.c): */
/* Why a header is refused, for the console line ("" when it is not): not an AWDL file, or another format version
 * (VERSION_OUT the file's). */
const char *AW_DialRefusal(const unsigned char *h,long file_size,int *version_out);
/* The resident size an AWDL1 header asks for, or -1. */
long AW_DialResidentSize(const unsigned char *header,long file_size);
/* Index the resident part: 1 = usable (every section's size checked against the file's). */
int AW_DialOpen(aw_dial_t *d,const unsigned char *data,long size,long file_size);
/* The I-th topic a new character knows, -1 past them. */
int AW_DialStartTopic(const aw_dial_t *d,int i);
/* The known-topic set (one bit per topic, AW_DialKnownBytes bytes, the caller's): seed with the start topics;
 * mark a topic; test one. */
#define AW_DialKnownBytes(d) (((d)->topics+7)/8)
void AW_DialKnownStart(const aw_dial_t *d,unsigned char *known);
void AW_DialKnow(const aw_dial_t *d,unsigned char *known,int topic);
int AW_DialKnows(const aw_dial_t *d,const unsigned char *known,int topic);
/* The topic list of an open conversation (OpenMW getAvailableTopics: known AND this actor has an answer, a refusal
 * counting; Topic kind only), in the table's order (by name): the count, topic numbers into OUT (at most MAX). */
int AW_DialTopicList(const aw_dial_conv_t *c,const unsigned char *known,const aw_glut_state_t *s,int *out,int max);
/* The greeting when a conversation opens (the rule of OpenMW's DialogueManager::startDialogue, our own code): the
 * first Greeting-kind topic, in the table's order, with an answer this speaker passes now (the derived disposition,
 * no choice open), with no fallback to Info Refusal. The answer, -1 none; *TOPIC its topic. */
int AW_DialGreeting(const aw_dial_conv_t *c,const aw_glut_state_t *s,int *topic);
/* The known topics are kept by the scripts' topic rows (AddTopic; saved with the game as AWKT), matched to this
 * table's Topic-kind topics by name: the hash of a name (32-bit FNV-1a over its bytes, A-Z folded); MAP (one u16 per
 * table topic, the caller's) gets each Topic-kind topic's row among HASHES (ROWS, a row's name hash each) or
 * AW_DIAL_NO_ROW: the topics mapped, -1 when a name read fails. KnownSync: KNOWN follows the rows KNOWS reports for
 * every mapped topic, keeps its bits for the others, and holds the start topics. */
unsigned long AW_DialNameHash(const char *name,int length);
int AW_DialTopicMap(const aw_dial_t *d,aw_dial_read_t read,void *user,const unsigned long *hashes,int rows,
                    unsigned short *map);
void AW_DialKnownSync(const aw_dial_t *d,unsigned char *known,const unsigned short *map,int (*knows)(int row));
/* A topic's kind (AW_DIAL_KIND_*) and its name's place in the file (for the window's list), -1 for a bad topic. */
int AW_DialTopicKind(const aw_dial_t *d,int topic);
long AW_DialTopicName(const aw_dial_t *d,int topic,int *length);
/* Open a conversation with NPC row NPC: read its row, the globals and names, and every candidate of every topic it
 * has into BUFFER (BYTES); SPEAKER: the voice table's context of the same row (rank, disposition, home cell; this
 * table's globals and names replace the voice table's). 1 done, 0 when the buffer is short or a read fails. */
int AW_DialConverse(aw_dial_conv_t *c,const aw_dial_t *d,int npc,const aw_glut_cond_t *speaker,
                    aw_dial_read_t read,void *user,unsigned char *buffer,long bytes);
/* The NPC's place of a topic, -1 when it has none. */
int AW_DialFind(const aw_dial_conv_t *c,int topic);
/* The answer to a topic (OpenMW Filter::search): its candidates in order, the first whose conditions all hold; when
 * none holds but one failed only on its disposition test, *refused = 1 (the answer then comes from Info Refusal).
 * The index into c->answer, or -1. */
int AW_DialPick(const aw_dial_conv_t *c,int topic,const aw_glut_state_t *s,int *refused);
/* The same for the topic "Service Refusal" (OpenMW checkServiceRefused): the disposition test inverted, the speaker
 * refuses only below an INFO's value (SERVICE-REFUSAL-UNCLOTHED-60); no Info Refusal. */
int AW_DialPickRefusal(const aw_dial_conv_t *c,int topic,const aw_glut_state_t *s);
/* The topic's answer with the refusal rule applied (Info Refusal's answer when only disposition failed), -1 none. */
int AW_DialAnswer(const aw_dial_conv_t *c,int topic,const aw_glut_state_t *s);
/* File offsets of an answer's text and result script, -1 when it has none. */
long AW_DialTextAt(const aw_dial_conv_t *c,int answer);
long AW_DialScriptAt(const aw_dial_conv_t *c,int answer);
/* An answer's links (topics its text names, each once in text order), read with READ; the count, at most MAX. */
int AW_DialLinks(const aw_dial_conv_t *c,int answer,aw_dial_read_t read,void *user,unsigned short *out,int max);
/* An answer's link spans in its shown text (the explicit @name# markers already stripped by the builder): offset and
 * length in characters, the topic; in text order; the count, at most MAX. */
#define AW_DIAL_LINK_ROW 6
typedef struct {unsigned short offset,length,topic;} aw_dial_span_t;
int AW_DialSpans(const aw_dial_conv_t *c,int answer,aw_dial_read_t read,void *user,aw_dial_span_t *out,int max);
int AW_DialEntrySpans(const aw_dial_t *d,const unsigned char *entry_row,aw_dial_read_t read,void *user,aw_dial_span_t *out,int max);
/* The services NPC ROW offers (OpenMW's ESM::NPC bits; tools/dialogue_lut.py services_of): one read, when a
 * conversation opens. 0 none. */
#define AW_DIAL_SERVICE_BARTER 0x037FFUL      /* AllItems: any of these, the Barter entry */
#define AW_DIAL_SERVICE_SPELLS 0x00800UL
#define AW_DIAL_SERVICE_TRAINING 0x04000UL
#define AW_DIAL_SERVICE_SPELLMAKING 0x08000UL
#define AW_DIAL_SERVICE_ENCHANTING 0x10000UL
#define AW_DIAL_SERVICE_REPAIR 0x20000UL
unsigned long AW_DialServices(const aw_dial_t *d,int row,aw_dial_read_t read,void *user);
#define AW_DIAL_SKILLS 27
/* The window's words, the game's own (GMST; tools/dialogue_lut.py UI_TEXTS, same order): AW_DIAL_TEXTS of
 * AW_DIAL_UI_TEXT bytes each, read into OUT (AW_DIAL_TEXTS x AW_DIAL_UI_TEXT) when a conversation opens. */
enum {AW_DIAL_TEXT_PERSUASION,AW_DIAL_TEXT_ADMIRE,AW_DIAL_TEXT_INTIMIDATE,AW_DIAL_TEXT_TAUNT,AW_DIAL_TEXT_BRIBE10,
      AW_DIAL_TEXT_BRIBE100,AW_DIAL_TEXT_BRIBE1000,AW_DIAL_TEXT_BACK,AW_DIAL_TEXT_BARTER,AW_DIAL_TEXT_SPELLS,
      AW_DIAL_TEXT_TRAVEL,AW_DIAL_TEXT_SPELLMAKING,AW_DIAL_TEXT_ENCHANTING,AW_DIAL_TEXT_TRAINING,AW_DIAL_TEXT_REPAIR,
      AW_DIAL_TEXT_GOODBYE,AW_DIAL_TEXT_GP,AW_DIAL_TEXT_TRAINING_WORDS,AW_DIAL_TEXT_TRAINING_ATTRIBUTE,
      AW_DIAL_TEXT_BUY,AW_DIAL_TEXT_SELL,AW_DIAL_TEXT_MAGNITUDE,AW_DIAL_TEXT_DURATION,AW_DIAL_TEXT_AREA,
      AW_DIAL_TEXT_RANGE,AW_DIAL_TEXT_RANGE_SELF,AW_DIAL_TEXT_RANGE_TOUCH,AW_DIAL_TEXT_RANGE_TARGET,
      AW_DIAL_TEXT_NEED_EFFECT,AW_DIAL_TEXT_NEED_NAME,AW_DIAL_TEXT_ZERO_COST,AW_DIAL_TEXT_NO_GOLD_SPELL,AW_DIAL_TEXT_NAME,
      AW_DIAL_TEXT_EFFECTS,AW_DIAL_TEXT_CREATE,AW_DIAL_TEXT_FEET,AW_DIAL_TEXT_SECONDS,AW_DIAL_TEXT_POINTS,
      AW_DIAL_TEXT_POINT_COST,AW_DIAL_TEXT_NEED_ENCH_EFFECT,AW_DIAL_TEXT_NEED_SOUL,AW_DIAL_TEXT_NEED_ITEM,
      AW_DIAL_TEXT_TOO_MUCH,AW_DIAL_TEXT_CAST_ONCE,AW_DIAL_TEXT_CAST_STRIKES,AW_DIAL_TEXT_CAST_USED,
      AW_DIAL_TEXT_CAST_CONSTANT,AW_DIAL_TEXT_CAST_COST,AW_DIAL_TEXT_ENCHANT_DONE,AW_DIAL_TEXT_ITEM,AW_DIAL_TEXT_SOUL,
      AW_DIAL_TEXT_CHANCE,AW_DIAL_TEXT_JOURNAL_ENTRY,AW_DIAL_TEXT_SKILL0,AW_DIAL_TEXTS=AW_DIAL_TEXT_SKILL0+27};
#define AW_DIAL_UI_TEXT 48
int AW_DialUiTexts(const aw_dial_t *d,aw_dial_read_t read,void *user,char *out);
/* the attribute skill SKILL is governed by (0..7, the SKIL record), -1 unknown */
int AW_DialSkillAttribute(const aw_dial_t *d,int skill,aw_dial_read_t read,void *user);
/* OpenMW getBarterOffer: the price asked (BUYING) or given for BASE; DISPOSITION the derived one */
int AW_DialBarterOffer(const aw_dial_t *d,int base,int buying,const aw_dial_person_t *player,const aw_dial_person_t *npc,
                       int disposition);
/* the NPC's three best skills of SKILLS[COUNT] into OUT (ties: the earlier skill); the count */
int AW_DialTrainingPicks(const float *skills,int count,int *out);
/* OpenMW SpellBuyingWindow: max(1, cost x fSpellValueMult), then the offer */
int AW_DialSpellPrice(const aw_dial_t *d,int cost,const aw_dial_person_t *player,const aw_dial_person_t *npc,int disposition);
/* OpenMW MerchantRepair: the price of mending a thing of VALUE from DURABILITY to MAX (both whole points) */
int AW_DialRepairPrice(const aw_dial_t *d,int value,int max,int durability,const aw_dial_person_t *player,
                       const aw_dial_person_t *npc,int disposition);
/* Spellmaking (OpenMW SpellCreationDialog::notifyEffectsChanged, spellutil calcEffectCost with the player-spell
 * method): one effect of a made spell, its magic effect's base cost and flags (MGEF), and the made spell's magicka
 * cost and price */
typedef struct {float base_cost;int flags,magnitude_min,magnitude_max,duration,area,range;} aw_dial_effect_t;
#define AW_DIAL_MGEF_NO_DURATION 0x4
#define AW_DIAL_MGEF_NO_MAGNITUDE 0x8
#define AW_DIAL_MGEF_APPLIED_ONCE 0x1000
#define AW_DIAL_RANGE_TARGET 2
float AW_DialEffectCostPlayer(const aw_dial_t *d,const aw_dial_effect_t *e);
int AW_DialSpellmakingCost(const aw_dial_t *d,const aw_dial_effect_t *e,int count);
int AW_DialSpellmakingPrice(const aw_dial_t *d,const aw_dial_effect_t *e,int count,const aw_dial_person_t *player,
                            const aw_dial_person_t *npc,int disposition);
/* Enchanting (OpenMW mwmechanics/enchanting.cpp): the effects' accumulated costs (CONSTANT: a constant effect,
 * its duration fEnchantmentConstantDurationMult), the points, the cast cost by the caster's Enchant skill, the price at
 * an enchanter, the enchanter's chance and an item's capacity */
int AW_DialEnchantCosts(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,float *out);
float AW_DialEnchantPoints(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,int precise);
int AW_DialEnchantCastCost(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,float enchant_skill);
int AW_DialEnchantPrice(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,
                        const aw_dial_person_t *player,const aw_dial_person_t *npc,int disposition);
int AW_DialEnchantChance(const aw_dial_t *d,const aw_dial_effect_t *e,int count,int constant,float enchant_skill,
                         float intelligence,float luck,float fatigue);
int AW_DialEnchantCapacity(const aw_dial_t *d,float item_points);
/* OpenMW Enchanting::nextCastStyle (ENDT types 0 cast once, 1 when strikes, 2 when used, 3 constant): the style after
 * STYLE for an ITEM kind, a constant effect only with a soul of at least iSoulAmountForConstantEffect */
enum {AW_DIAL_ENCHANT_WORN,AW_DIAL_ENCHANT_WEAPON,AW_DIAL_ENCHANT_BOOK};
int AW_DialNextCastStyle(int item,int style,int soul,const aw_dial_t *d);
int AW_DialTrainingPrice(const aw_dial_t *d,int skill,const aw_dial_person_t *player,const aw_dial_person_t *npc,
                         int disposition);
/* Spans through the define filling (which changes lengths): AW_DialMarkSpans puts AW_DIAL_LINK_OPEN/CLOSE around each
 * span of TEXT (spans in text order, not overlapping); after the filling AW_DialTakeSpans takes the marks out again
 * and gives each span its new offset and length, the topics in the same order. Both return the output's length. */
#define AW_DIAL_LINK_OPEN '\002'
#define AW_DIAL_LINK_CLOSE '\003'
int AW_DialMarkSpans(const char *text,const aw_dial_span_t *spans,int n,char *out,int capacity);
int AW_DialTakeSpans(const char *marked,const aw_dial_span_t *topics,int n,char *out,int capacity,aw_dial_span_t *spans,
                     int *found);
/* The next line of *TEXT wrapped at COLS characters (at the last space that fits, else cut; a line end ends a line):
 * 1 and the line in OUT (CAPACITY > COLS), *TEXT moved past it; 0 at the end. */
int AW_DialWrapNext(const char **text,int cols,char *out,int capacity);

/* The dialogue window (aw_dialwin.c, engine only): opened by Talk (pr_cmds.c PF_aw_converse) with the greeting
 * already chosen; 1 when it opened (the NPC has a dialogue row; otherwise the greeting stays a subtitle). */
struct edict_s;
void AW_DialWindowInit(void);
int AW_DialWindowOpen(struct edict_s *e,const char *greeting,int talked);
void AW_DialWindowReadCache(int on);   /* dbg npcs talkcache on|off: the conversation's block cache (default on) */
/* dbg npcs talk [ID]: Talk with the nearest NPC that can be talked to (or record ID), the player turned to it. */
void AW_DialWindowTalk(const char *id);
/* aw_mwhost.c: a speaker's disposition facts from the actor record, the character and the player's standing */
void AW_MwscriptDispositionFacts(const char *record,unsigned long reference,int base,const char *faction,
                                 aw_dial_facts_t *f);
int AW_MwscriptPersons(const char *record,unsigned long reference,aw_dial_person_t *player,aw_dial_person_t *npc,
                       int *fight,int *flee);
void AW_MwscriptSetSpeaker(const char *record,unsigned long reference,int disposition,int fight,int flee);
int AW_MwscriptPlayerGold(int delta);
/* training: the speaker's 27 skills, the player's skill (raised by one when RAISE) and attribute (aw_mwhost.c) */
int AW_MwscriptNpcSkills(const char *record,unsigned long reference,float *out);
int AW_MwscriptPlayerSkill(int skill,int raise);
int AW_MwscriptPlayerAttribute(int attribute);
/* the speaker's spells for sale (plain spells the player lacks, by name) with names and costs; buying adds one */
int AW_MwscriptSpellsForSale(const char *record,unsigned long reference,int *out,int max,char (*names)[48],int *costs);
int AW_MwscriptBuySpell(int spell);
/* Barter (the plain pages; OpenMW's full window is its own tracker row): a ware of the merchant's stock or the
 * player's inventory, its name, value, inventory category, whether enchanted and how many */
typedef struct {char id[40],name[48];int value,category,enchanted,count,row;} aw_dial_ware_t;
int AW_MwscriptStock(const char *record,unsigned long reference,aw_dial_ware_t *out,int max);
int AW_MwscriptPlayerWares(aw_dial_ware_t *out,int max);
/* one item changes hands at PRICE gold: BUY from the merchant, else sold to it; 1 done */
int AW_MwscriptTrade(const char *record,unsigned long reference,const aw_dial_ware_t *w,int buy,int price);
/* the player's weapons and armour below full health (their health and current points); mending one to full */
int AW_MwscriptRepairables(aw_dial_ware_t *out,int *maximum,int *durability,int max);
int AW_MwscriptMend(const char *id);
/* the effects the player may make spells with (aw_actorstate.h aw_spell_effect_t) */
int AW_MwscriptKnownEffects(aw_spell_effect_t *out,int max);
/* Dialogue result scripts (aw_mwhost.c): the answer's result TEXT (LENGTH bytes) run on the speaker; the window's
 * Choice and Goodbye arrive through aw_dial_result_choice while it runs. 1 ran, 0 none compiled for it, -1 it did not
 * compile (said in the log) */
int AW_MwscriptRunResult(const char *record,unsigned long reference,const char *text,int length);
extern void (*aw_dial_result_choice)(const char **texts,int ntexts,const aw_mwcell_t *numbers,int count);
extern void (*aw_dial_result_clear)(void);       /* ClearInfoActor while a result runs */
/* the journal's topic pages read the table (aw_dialwin.c): a topic's name, a heard entry's text; 1 read */
int AW_DialWindowTopicName(int topic,char *out,int capacity);
int AW_DialWindowEntryText(int entry,char *out,int capacity);
/* the journal book's way to them (aw_worldui.c defines these; AW_DialWindowInit sets them) */
extern int (*aw_journal_heard_count)(void);
extern int (*aw_journal_heard_at)(int i,int *entry,int *topic,const char **speaker);
extern int (*aw_journal_topic_name)(int topic,char *out,int capacity);
extern int (*aw_journal_entry_text)(int entry,char *out,int capacity);
extern void (*aw_journal_updated)(void);   /* aw_mwhost.c defines it: a quest's journal index rose */
extern int (*aw_journal_entry_marked)(int entry,char *out,int capacity,unsigned short *topics,int max);
/* Enchanting: the player's enchantable things (points, kind AW_DIAL_ENCHANT_*); making MADE with filled gem GEM */
int AW_MwscriptEnchantables(aw_dial_ware_t *out,int *points,int *kind,int max);
int AW_MwscriptEnchant(const aw_made_item_t *made,int gem);
float AW_MwscriptSpeakerStat(const char *record,unsigned long reference,int stat);
/* the speaker attacks when its Fight rating with this disposition reaches 100 (OpenMW isAggressive; aw_combat.c
 * AW_CombatAggro); 1 a fight started, 0 not, -1 no combat layer */
struct edict_s;
int AW_MwscriptSpeakerAggro(struct edict_s *e,int disposition);
/* The derived disposition of an NPC toward the player for the world's aggro on sight (DIALOGUE-FIGHT-DISPOSITION-57),
 * without reading the NPC's conversation each engage tick: what is the NPC's own (its record's disposition, same race,
 * its faction) is looked up once into CACHE when the NPC's slot is made; each call then only takes the NPC's current disposition (the record's,
 * with the changes persuasion and scripts made, kept on its actor record) and the player's side. 50 without the
 * dialogue table. */
typedef struct {signed char ready;signed char same_race;short base;int actor_row;char faction[32];} aw_dial_npc_cache_t;
void AW_DialNpcPrepare(struct edict_s *e,aw_dial_npc_cache_t *cache);   /* when the NPC's slot is made; reads */
int AW_DialNpcDisposition(struct edict_s *e,const aw_dial_npc_cache_t *cache);  /* the engage tick; reads nothing */
/* the player's side and the NPC's current disposition into F (aw_mwhost.c); the race and faction are the caller's */
void AW_MwscriptDispositionNow(int actor_row,unsigned long reference,int base,aw_dial_facts_t *f);
/* the NPC's row in the actor file (a binary search on disk: once, with the cache), -1 none */
int AW_MwscriptActorRow(const char *record);
int AW_DialWindowActive(void);
/* the compiled scripts' file string reads that went to disk (aw_mwhost.c read_string; cached names do not count) */
unsigned long AW_MwscriptStringReads(void);
/* RankRequirement from the loaded table (AW_DialRankRequirement; 0 without the table) */
int AW_DialWindowRankRequirement(const char *faction,int rank,const short *attributes,const short *skills,int reputation);
#endif
