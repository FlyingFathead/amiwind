/* SPDX-License-Identifier: GPL-2.0-or-later
 * The world change list (CELL-CHANGES-59, first slice: world objects): ONE sorted list for the whole world, every
 * exterior cell, every room and every CHIM frame, holding only what the player or a script changed on a placed
 * object, kept for the whole session and written into the saved game (AWS4 feature bit 32, aw_save_codec.c).
 * The game data is the base; a row holds only the fields that differ from it and absence means "as in the data"
 * (the rule of the original's saves and of OpenMW 0.51's cell store: a changed reference is written, an unchanged
 * one is not). Rows are set where the change happens (taking, a drop, a script's Disable or Lock), never by a
 * comparison at save time.
 *
 * KEY (u32): bits 0-23 the stable reference id the builder gives every placed reference (tools/ref_identity.py:
 * the content file's fixed index and the low 24 bits of its reference number; Morrowind.esm's own numbers are
 * their own ids, so every earlier save keeps its keys), bit 31 a builder-made object (as aw_save.h
 * AW_CHANGE_BUILDER), bit 30 a thing the player dropped (bits 0-23 its inventory serial, aw_state.h next_serial).
 * Bits 24-29 are always 0.
 *
 * The rows live in one array sorted by key that grows in steps (AW_TryRealloc): no fixed ceiling of 2,048 or
 * 1,024 entries; at most AW_LEDGER_ROWS (one row per changed thing; a late original game changes about 7,700
 * references) so its worst case can be declared for the resident registry. A second array orders the rows by
 * their place (cell, room or scene) so a map load reads only its own rows. Pure C: no engine headers, so the
 * native tests compile it as it is.
 */
#ifndef AW_LEDGER_H
#define AW_LEDGER_H
#include <stdint.h>

#define AW_LEDGER_PLAYER 0x40000000U    /* key bit 30: the player's drop */
#define AW_LEDGER_BUILDER 0x80000000U   /* key bit 31: a builder-made object */
#define AW_LEDGER_ID 0xFFFFFFU          /* key bits 0-23 */
#define AW_LEDGER_ROWS 32768            /* the most rows (16 x the old 2,048-entry list) */
#define AW_LEDGER_EXTRAS 4096           /* the most rows with a position (moved objects and drops) */

/* The fields a row carries (u8): TAKEN and DISABLED are separate (SAVE-TAKEN-DISABLED-ONE-FLAG-59): a script's
 * Enable never brings back what the player took. */
#define AW_LEDGER_TAKEN 0x01U       /* the player took it: gone from the world (OpenMW: count 0 on the reference) */
#define AW_LEDGER_DISABLED 0x02U    /* a script's Disable: hidden and not solid until Enable */
#define AW_LEDGER_LOCK 0x04U        /* a script set its lock: LOCK_LEVEL (0 unlocked .. 100), LAST the level it had */
#define AW_LEDGER_STOLEN 0x08U      /* taken from an owner (CRIME-59 reads it) */
#define AW_LEDGER_MOVED 0x10U       /* POSITION and YAW hold where it is now (game units, see AT) */
#define AW_LEDGER_DROPPED 0x20U     /* a player's drop: ITEM, COUNT, POSITION, YAW (only with key bit 30) */
#define AW_LEDGER_CONDITION 0x40U   /* CONDITION holds the dropped item's condition (0..1; without it: full) */
/* Slice 2 (doors, locks, the stolen mark): a hinged door stands open or turns open (the use's direction is recorded
 * when the door is used; OpenMW 0.51 keeps a door's state and turn on its reference, mwclass/door.cpp). Closed is the
 * game data's pose: no field. Never on a drop. Saved only in the list's second form (AWL2). */
#define AW_LEDGER_OPEN 0x80U
#define AW_LEDGER_FIELDS1 0x7FU     /* the fields of the first saved form (AWL1) */
#define AW_LEDGER_FIELDS 0xFFU

/* Where a row lies (a map load reads the rows of its own place):
 *   ANY   unknown (a script disabled a reference somewhere): read on every map
 *   CELL  an exterior cell: WHERE = cell x << 16 | (cell y & 0xffff); positions are the original's game units
 *   ROOM  a room: WHERE = its stable interior number (worldspawn _aw_cell_int); positions game units, room-local
 *   SCENE a map that is neither (an old save's drop): WHERE = its scene id (aw_maps.h); positions map units */
enum {AW_AT_ANY,AW_AT_CELL,AW_AT_ROOM,AW_AT_SCENE};

typedef struct {
    float position[3],yaw;
    float condition;              /* with AW_LEDGER_CONDITION */
    int32_t count;                /* a drop's stack */
    char item[64];                /* a drop's record id */
} aw_ledger_extra_t;
typedef struct {
    uint32_t key;
    uint8_t fields,at;
    uint8_t lock,last_lock;       /* with AW_LEDGER_LOCK: the level, and the level it had last (Lock without a number) */
    int32_t where;
    aw_ledger_extra_t *extra;     /* with MOVED or DROPPED, else NULL */
} aw_ledger_row_t;
/* The stolen items (slice 2; the rule of OpenMW 0.51 mwmechanics/mechanicsmanagerimp.cpp itemTaken and its saved
 * stolen-items map, our own code): taking an owned thing adds COUNT to the pair (item record id, owner), the owner being
 * the reference's owner, else its owning faction (FACTION 1). Kept by item id, not on the world reference, so the mark
 * goes wherever the item goes: dropped, picked up again, carried across maps and saves. Gold is never marked. The crime
 * system (CRIME-59) reads it; returning or confiscating takes COUNT off and a pair at 0 goes. Ids are folded to lower
 * case (the game's ids are case-blind). */
#define AW_LEDGER_STOLEN_MAX 1024     /* pairs at most (one per kind of item and owner, not per thing) */
#define AW_LEDGER_STOLEN_BYTES 72     /* one pair */
#define AW_LEDGER_STOLEN_ID 32        /* the longest id (the game's record ids) */
typedef struct {
    char item[AW_LEDGER_STOLEN_ID+1],owner[AW_LEDGER_STOLEN_ID+1];
    uint8_t faction;              /* 1: OWNER is a faction */
    int32_t count;                /* 1 .. AW_LEDGER_STOLEN_COUNT */
} aw_ledger_stolen_t;
#define AW_LEDGER_STOLEN_COUNT 1000000
/* Slice 3, container deltas (the rule of OpenMW 0.51 mwclass/container.cpp and mwworld/containerstore.cpp, and of
 * the original's per-reference changes; our own code): what the player or a script took from or put into a placed
 * container is kept per container reference as the difference against its game-data contents, one entry per
 * (container key, item id) with a signed count; absence means "as in the data". A container never touched has no
 * entry. Respawning containers and levelled lists are not resolved yet (slice 7): a levelled entry stays as the
 * data has it. Ids folded to lower case. */
#define AW_LEDGER_CONTENTS_MAX 8192   /* entries at most (one per container and kind of item changed) */
#define AW_LEDGER_CONTENT_BYTES 44    /* one entry */
typedef struct {
    uint32_t key;                 /* the container's reference (key rules above; never bit 30) */
    char item[AW_LEDGER_STOLEN_ID+1];
    int32_t count;                /* taken out < 0 < put in; never 0; |count| <= AW_LEDGER_STOLEN_COUNT */
} aw_ledger_content_t;
/* NPC faction ranks changed by a script's RaiseRank / LowerRank (OpenMW 0.51 statsextensions.cpp OpRaiseRank,
 * OpLowerRank: the NPC's rank in its own (primary) faction, kept on the NPC; never the player's): one entry per NPC
 * reference, the rank now. */
#define AW_LEDGER_RANKS_MAX 2048
#define AW_LEDGER_RANK_BYTES 8
#define AW_LEDGER_RANK_TOP 255        /* OpenMW sets no top; the saved byte does */
typedef struct {uint32_t key;int16_t rank;} aw_ledger_rank_t;
/* Slice 4, what scripts and dialogue change (MWSCRIPT-STATE-NOT-SAVED-48, AW-STATE-32-SLOTS-48; the rules of OpenMW
 * 0.51 mwworld/globals.cpp, mwdialogue/journalimp.cpp, mwdialogue/dialoguemanagerimp.cpp and mwmechanics npcstats,
 * our own code): four tables of (key, value), each sorted by key, holding only what differs from the game data's
 * start (absence = as in the data):
 *   GLOBALS       the scripts' globals: key = the name hash of the global's record id, value = its 32 bits
 *   QUESTS        the journal: key = the name hash of the quest's id, value = its stage (never 0)
 *   TOPICS        the topics the player knows: key = the name hash of the topic, value 1
 *   DISPOSITIONS  an NPC's disposition changed by a script or a conversation: key = the NPC reference (key rules
 *                 above, never bit 30), value = the disposition (-32768 .. 32767)
 * Name hash: FNV-1a over the id folded to lower case (the dialogue table's AW_DialNameHash; 0 becomes 1), so a
 * rebuilt game in another order keeps every value; a key no record has is dropped on load. The engine's own named
 * facts (aw_state.h AW_GLOBAL past its 32 slots: "amiwind:..." ids) are a fifth table of (id, value). */
enum {AW_LEDGER_GLOBALS,AW_LEDGER_QUESTS,AW_LEDGER_TOPICS,AW_LEDGER_DISPOSITIONS,AW_LEDGER_TABLES};
#define AW_LEDGER_VALUES_MAX 8192     /* entries per table at most (the game: 143 globals, 632 quests, ~2,400 topics) */
#define AW_LEDGER_VALUE_BYTES 8       /* one entry */
#define AW_LEDGER_VALUES_ALL 32768    /* the four tables together at most (4 x AW_LEDGER_VALUES_MAX) */
#define AW_LEDGER_FACTS_MAX 1024      /* the engine's named facts past aw_state's 32 */
#define AW_LEDGER_FACT_BYTES 68
#define AW_LEDGER_FACT_ID 63
typedef struct {uint32_t key;int32_t value;} aw_ledger_value_t;
typedef struct {char id[AW_LEDGER_FACT_ID+1];int32_t value;} aw_ledger_fact_t;
/* Slice 5, the scripts' own state (MWSCRIPT-STATE-NOT-SAVED-48; the rules of OpenMW 0.51 mwworld/livecellref.cpp,
 * mwscript/locals.cpp and mwscript/globalscripts.cpp: a reference's local script state is part of its saved state, a
 * global script is saved with its running state and its locals; our own code):
 *   LOCALS   one entry per local value that differs from its start (0, as OpenMW's Locals::configure sets it): an
 *            object's (GLOBAL 0, KEY its reference, key rules above, never bit 30) or a global script's (GLOBAL 1, KEY
 *            the script's name hash); SCRIPT the name hash of the script the values belong to, HINT its row in the
 *            compiled scripts when saved (a load takes the values only when that row still has the name: a rebuilt
 *            file in another order drops them, counted), SLOT the local's number, VALUE its 32 bits (a float's bits)
 *   SCRIPTS  a global script whose running state differs from a new game's (a start script stopped, any other one
 *            started): its name hash, hint and RUNNING (1/0)
 * Both sorted, LOCALS by (global, key, slot), SCRIPTS by name hash. */
#define AW_LEDGER_LOCALS_MAX 8192     /* the interpreter keeps at most 4,096 attached and 4,096 parked values */
#define AW_LEDGER_LOCAL_BYTES 16
#define AW_LEDGER_SCRIPTS_MAX 2048
#define AW_LEDGER_SCRIPT_BYTES 8
typedef struct {uint32_t key,script;uint16_t hint;uint8_t slot,global;int32_t value;} aw_ledger_local_t;
typedef struct {uint32_t script;uint16_t hint;uint8_t running,unused;} aw_ledger_script_t;
/* Slice 6, the actors (ACTOR-STATE-POOL-LIMITS-54; the rules of OpenMW 0.51 mwworld/livecellref.cpp, esm3/npcstate and
 * creaturestats: a changed actor reference is saved with its death, its place and its stats, an unchanged one is not;
 * our own code). Two parts, both by the actor's reference and only for actors that differ from the game data:
 *   ACTORS   one row per actor reference the window or a room let go changed (aw_actors.c, which keeps no list of its
 *            own any more: the 2,048-entry list is gone): DEAD (killed; the body stays where it fell, a body a script
 *            removed is the reference's DISABLED row above), MOVED (ORIGIN and ANGLES where it was left, HEALTH its
 *            health then, HOURS the game time, ROOM the room's stable number or 0 outdoors), FIGHT (hostile to the
 *            player), FOLLOW (the companion), PICK (a levelled reference's roll). Key: the reference (bits 0-23, bits
 *            24-31 clear: builder-made actors stay in the save's own entries).
 *   RECORDS  the changed actor records (aw_actorstate.c: stats, health, fatigue and magicka, behaviour ratings, disposition,
 *            inventory and spell changes, hostility by script), in their own form "AWAR" (aw_actorstate.h
 *            AW_ActorStateExportRecords), one record per reference, written at a save and read back after a load;
 *            the list keeps the bytes, the actor module checks them.
 * Slice 7 adds DIED (the game hours of the death, for the respawn below). */
#define AW_LEDGER_ACTORS_MAX 8192     /* actor rows at most (the game places 2,673 NPCs; its actor table has 3,437 bases) */
#define AW_LEDGER_ACTOR_BYTES 52
#define AW_LEDGER_RECORDS_MAX 2097152 /* the actor records' bytes at most (8,192 records of 182 bytes and their changes);
                                       * held only from a save's start to its write and from a load to its spawn */
#define AW_LEDGER_ACTOR_DEAD 1U
#define AW_LEDGER_ACTOR_MOVED 2U
#define AW_LEDGER_ACTOR_FIGHT 4U
#define AW_LEDGER_ACTOR_FOLLOW 8U
#define AW_LEDGER_ACTOR_PICK 16U
#define AW_LEDGER_ACTOR_FIELDS 31U
#define AW_LEDGER_ACTOR_DIED 32U      /* slice 7, the seventh form only: f32 the game hours of the death */
typedef struct {
    uint32_t key;
    uint8_t dead,moved,fight,follow;   /* 0/1 each */
    uint16_t pick,unused;              /* 0 not rolled, 1 nothing, 2 + the actor table base it gave */
    float origin[3],angles[3],health,hours;
    int32_t room;                      /* a room's stable number (origin room-local), 0 outdoors (origin island) */
    float died;                        /* slice 7: game hours when it was first kept dead (0 unknown: HOURS then) */
} aw_ledger_actor_t;
/* Slice 7, respawn (the rules of OpenMW 0.51 mwworld/cellstore.cpp CellStore::respawn, mwclass/container.cpp,
 * creature.cpp, npc.cpp and creaturelevlist.cpp respawn; the times are the game data's GMSTs; our own code):
 *   - a container whose record is flagged Respawn gets its game-data contents back (its deltas go) when its place (an
 *     exterior cell or a room) is loaded more than 24 x 30 x iMonthsToRespawn game hours after the place's last
 *     refill (the first time: after the game's start); the place's time is then set to now, refill or not (STAMPS);
 *   - a dead actor comes back as the game data has it (its row and its record go) at its cell's next load when it is
 *     a levelled creature list's (always) or its record is flagged Respawn, min(fCorpseRespawnDelay,
 *     fCorpseClearDelay) game hours after its death; any other dead actor stays dead.
 * Morrowind.esm: iMonthsToRespawn 4, fCorpseRespawnDelay 72, fCorpseClearDelay 72 (read by the builder, AWI1). */
typedef struct {int months;float respawn_delay,clear_delay;} aw_ledger_respawn_t;
#define AW_LEDGER_RESPAWN_DEFAULT {4,72.0f,72.0f}
#define AW_LEDGER_STAMPS_MAX 8192     /* places with a refill time at most (the game: 1,420 exterior cells, 1,000 rooms) */
#define AW_LEDGER_STAMP_BYTES 12
typedef struct {int32_t where;uint8_t at,unused[3];float hours;} aw_ledger_stamp_t;
/* Slice 7, content-change migration (the rule of OpenMW 0.51 mwworld/cellstore.cpp readReferenceCollection and
 * mwstate/statemanagerimp.cpp: a saved state is applied to the reference with the same reference number AND the same
 * record id; otherwise it is dropped with a warning; the content files are matched by name): every reference the list
 * names keeps, from the save on, the name hash of its record id (IDENTS, AW_LedgerNameHash of the reference's NAME,
 * from the build's reference identity table, focus.awf AWI1), and the list keeps the content files the game was made
 * with (FILES: the fixed index of tools/ref_identity.py, the name and the file's digest). A save of other game data or
 * another build's tables is migrated at its load (AW_LedgerMigrate): a change whose reference this game no longer has,
 * whose content file is gone, or whose reference now names another record is dropped and counted, never applied. */
#define AW_LEDGER_IDENTS_MAX 65536    /* references with a record hash at most (every keyed part of the list) */
#define AW_LEDGER_IDENT_BYTES 8
#define AW_LEDGER_FILES_MAX 8
#define AW_LEDGER_FILE_NAME 31
typedef struct {uint32_t key,record;} aw_ledger_ident_t;
typedef struct {uint8_t index,unused[3];uint32_t references;uint8_t digest[8];char name[AW_LEDGER_FILE_NAME+1];} aw_ledger_file_t;
/* What a migration dropped, by part (AW_LedgerMigrate); FILES the content files of the save this game lacks. */
typedef struct {
    unsigned long objects,containers,ranks,dispositions,locals,actors,picks,drops,stolen,files;
} aw_ledger_dropped_t;
typedef struct aw_ledger_s {
    aw_ledger_row_t *row;
    int count,capacity;
    int *place;                   /* row indices by (at, where, key); valid while PLACED is set */
    int placed,place_capacity;
    int extras;                   /* rows with an extra block */
    unsigned long refused;        /* rows refused for memory or AW_LEDGER_ROWS (the change is not kept) */
    aw_ledger_stolen_t *stolen;   /* sorted by (item, owner, faction) */
    int stolen_count,stolen_capacity;
    aw_ledger_content_t *content; /* sorted by (key, item) */
    int content_count,content_capacity;
    aw_ledger_rank_t *rank;       /* sorted by key */
    int rank_count,rank_capacity;
    aw_ledger_value_t *value[AW_LEDGER_TABLES];   /* slice 4, each sorted by key */
    int value_count[AW_LEDGER_TABLES],value_capacity[AW_LEDGER_TABLES];
    aw_ledger_fact_t *fact;       /* sorted by id */
    int fact_count,fact_capacity;
    aw_ledger_local_t *local;     /* slice 5, sorted by (global, key, slot) */
    int local_count,local_capacity;
    aw_ledger_script_t *script;   /* slice 5, sorted by name hash */
    int script_count,script_capacity;
    aw_ledger_actor_t *actor;     /* slice 6, sorted by key */
    int actor_count,actor_capacity;
    unsigned char *records;       /* slice 6, the "AWAR" bytes (NULL: none) */
    int records_bytes;
    aw_ledger_stamp_t *stamp;     /* slice 7, sorted by (at, where) */
    int stamp_count,stamp_capacity;
    aw_ledger_ident_t *ident;     /* slice 7, sorted by key */
    int ident_count,ident_capacity;
    aw_ledger_file_t file[AW_LEDGER_FILES_MAX];   /* slice 7, the content files (by index) */
    int file_count;
} aw_ledger_t;

/* the session's list (the game being played) */
extern aw_ledger_t aw_ledger;

/* 1 (the default): the object state and the player's drops are kept here; 0: the old fixed tables (aw_mwhost.c
 * objects[1024], aw_state.h dropped[32] keyed by map name), kept selectable (aw_placed ledger on|off; from the next
 * new game or load, as the stores do not move between each other). */
extern int aw_ledger_on;
/* What the list holds to be saved: its rows and its stolen pairs (0: nothing, no save section). */
int AW_LedgerRows(const aw_ledger_t *l);
/* Stolen pairs: COUNT (negative: returned or confiscated) added to (ITEM, OWNER, FACTION); the pair's count after it,
 * 0 when it went or nothing was kept (gold, an empty or too long id, memory, AW_LEDGER_STOLEN_MAX: refused counted). */
int AW_LedgerStolenAdd(aw_ledger_t *l,const char *item,const char *owner,int faction,int count);
/* The count of ITEM stolen from OWNER (FACTION as above); OWNER NULL: from anyone. */
int AW_LedgerStolenCount(const aw_ledger_t *l,const char *item,const char *owner,int faction);
/* Container deltas: DELTA added to (KEY, ITEM); the entry's count after it (0: it went, or nothing was kept: a bad key
 * or id, memory, AW_LEDGER_CONTENTS_MAX, refused counted). Delta of KEY's ITEM (0 none). The entries of KEY: their
 * count, *FIRST the index of the first in l->content. */
int AW_LedgerContentAdd(aw_ledger_t *l,uint32_t key,const char *item,int delta);
int AW_LedgerContentDelta(const aw_ledger_t *l,uint32_t key,const char *item);
int AW_LedgerContentOf(const aw_ledger_t *l,uint32_t key,int *first);
/* NPC ranks: the rank kept for KEY (-1 none); set it (0..AW_LEDGER_RANK_TOP; 0 when not kept). */
int AW_LedgerRank(const aw_ledger_t *l,uint32_t key);
int AW_LedgerRankSet(aw_ledger_t *l,uint32_t key,int rank);
/* Slice 4: the name hash of an id (never 0); TABLE's value of KEY into *OUT (1 kept, 0 none); set it (1 kept; 0 a bad
 * table, key or value, memory or AW_LEDGER_VALUES_MAX, refused counted); drop it; empty TABLE. QUESTS never keeps 0
 * (setting 0 drops it: the data's start). The named facts the same way by id (folded to lower case). */
uint32_t AW_LedgerNameHash(const char *id);
int AW_LedgerValue(const aw_ledger_t *l,int table,uint32_t key,int32_t *out);
int AW_LedgerValueSet(aw_ledger_t *l,int table,uint32_t key,int32_t value);
void AW_LedgerValueDrop(aw_ledger_t *l,int table,uint32_t key);
void AW_LedgerValueClear(aw_ledger_t *l,int table);
int AW_LedgerFact(const aw_ledger_t *l,const char *id,int32_t *out);
int AW_LedgerFactSet(aw_ledger_t *l,const char *id,int32_t value);
/* Slice 5: a local value set (VALUE 0 drops it: the start; 1 kept or dropped, 0 a bad key, script or slot, memory or
 * AW_LEDGER_LOCALS_MAX, refused counted); one read (1 kept, *OUT its value); a global script's running state set
 * (1 kept, 0 refused counted); emptied. GLOBAL 1: KEY must be SCRIPT. */
int AW_LedgerLocalSet(aw_ledger_t *l,int global,uint32_t key,uint32_t script,int hint,int slot,int32_t value);
int AW_LedgerLocal(const aw_ledger_t *l,int global,uint32_t key,int slot,int32_t *out);
int AW_LedgerScriptSet(aw_ledger_t *l,uint32_t script,int hint,int running);
void AW_LedgerLocalsClear(aw_ledger_t *l);
/* Slice 6: the actor row of KEY (MAKE 1: made, all fields 0, when it is not there); NULL when none, KEY breaks the key
 * rule, or the list cannot grow (refused counted). The pointer holds until the next made row. A row whose fields are
 * all 0 is not saved. The records: set (a copy of BYTES; 0 bytes: none; 1 kept, 0 too large or no memory, refused
 * counted). Emptied (both parts). */
aw_ledger_actor_t *AW_LedgerActor(aw_ledger_t *l,uint32_t key,int make);
int AW_LedgerRecordsSet(aw_ledger_t *l,const unsigned char *bytes,int count);
void AW_LedgerActorsClear(aw_ledger_t *l);
/* Slice 7, respawn. Actor A comes back now (1: due; the caller resets it, AW_LedgerActorReset): dead, RESPAWNS (its
 * record is flagged Respawn) or a levelled reference's (PICK set), and its death (DIED, else HOURS) at least
 * min(respawn delay, clear delay) game hours before NOW. Reset: every field but the key back to 0 (as in the data). */
int AW_LedgerActorRespawns(const aw_ledger_actor_t *a,int respawns,float now,const aw_ledger_respawn_t *r);
void AW_LedgerActorReset(aw_ledger_actor_t *a);
/* A place (AT, WHERE as the rows' places) is loaded at game hours NOW: 1 when its respawning containers refill (more
 * than 24 x 30 x MONTHS hours after its last refill, the first one after the game's start; the place's time is set to
 * NOW), else 0. Its last refill time (0: none) for the status. */
int AW_LedgerRespawnPlace(aw_ledger_t *l,int at,int32_t where,float now,int months);
float AW_LedgerPlaceStamp(const aw_ledger_t *l,int at,int32_t where);
/* Every container delta of KEY goes (a refill); how many. */
int AW_LedgerContentDrop(aw_ledger_t *l,uint32_t key);
/* Slice 7, identity. The record hash kept for KEY (1, *RECORD), 0 none; set (1; 0 a bad key, memory or the ceiling).
 * Refresh: the idents become exactly the keys the list names now (rows of placed references, container deltas, ranks,
 * dispositions, object locals, actor rows), each with its hash kept or, when new, from LOOKUP (1 found; 0 the build
 * does not name it: no ident). The content files: set from the build's table (copied). */
int AW_LedgerIdent(const aw_ledger_t *l,uint32_t key,uint32_t *record);
int AW_LedgerIdentSet(aw_ledger_t *l,uint32_t key,uint32_t record);
typedef int (*aw_ledger_lookup_t)(void *context,uint32_t key,uint32_t *record);
int AW_LedgerIdentRefresh(aw_ledger_t *l,aw_ledger_lookup_t lookup,void *context);
void AW_LedgerFilesSet(aw_ledger_t *l,const aw_ledger_file_t *files,int count);
/* Slice 7, migration of a save of other game data: every keyed change of L is checked: its content file (KEY >> 20,
 * tools/ref_identity.py) must be one of NOW's FILES (by name), LOOKUP must find the key in this game, and when the save
 * kept the key's record hash it must be the same; ITEM_OK (NULL: all good) checks a drop's or a container delta's item
 * id. What fails is dropped and counted in OUT; the levelled picks (base rows of another build's actor table) all go.
 * The idents of what stays are set to this game's hashes and FILES to NOW's. Returns the changes dropped in all. */
unsigned long AW_LedgerMigrate(aw_ledger_t *l,const aw_ledger_file_t *now,int now_count,aw_ledger_lookup_t lookup,
                               void *context,int (*item_ok)(void *context,const char *id),aw_ledger_dropped_t *out);
/* The row of KEY, or -1. */
int AW_LedgerFind(const aw_ledger_t *l,uint32_t key);
/* The row of KEY, made (no fields) when it is not there; NULL when the list cannot grow. The pointer holds until
 * the next Put or Tidy. */
aw_ledger_row_t *AW_LedgerPut(aw_ledger_t *l,uint32_t key);
/* The row's extra block (zeroed when new); NULL when no memory or AW_LEDGER_EXTRAS. */
aw_ledger_extra_t *AW_LedgerExtra(aw_ledger_t *l,aw_ledger_row_t *row);
/* A row's place; the place order is made again at its next use. */
void AW_LedgerSetPlace(aw_ledger_t *l,aw_ledger_row_t *row,int at,int32_t where);
/* KEY's row goes when it has no field left (an Enable of what only a script had disabled, a drop picked up). */
void AW_LedgerTidy(aw_ledger_t *l,uint32_t key);
void AW_LedgerClear(aw_ledger_t *l);
/* TO becomes FROM (TO's rows freed first); FROM is left empty. */
void AW_LedgerMove(aw_ledger_t *to,aw_ledger_t *from);
/* The rows at a place: their count, *FIRST the first position in the place order (AW_LedgerPlaceRow). */
int AW_LedgerPlace(aw_ledger_t *l,int at,int32_t where,int *first);
aw_ledger_row_t *AW_LedgerPlaceRow(aw_ledger_t *l,int position);
/* The first row whose key is at least KEY (the drops: AW_LEDGER_PLAYER .. AW_LEDGER_BUILDER-1); l->count when none. */
int AW_LedgerFrom(const aw_ledger_t *l,uint32_t key);
/* Bytes held now (rows, place order, extra blocks). */
unsigned long AW_LedgerResident(const aw_ledger_t *l);

/* The saved form (AWS4 feature 32): "AWL1", u32 rows, then each row: u32 key, u8 fields, u8 at, u8 lock,
 * u8 last lock, i32 where; with MOVED or DROPPED f32 x, y, z, yaw; with DROPPED i32 count, u8 length and the
 * item id; with CONDITION f32 condition. Little-endian. Encode returns the bytes written (OUT NULL: the bytes it
 * needs), 0 when a row breaks the rules below. Decode checks every field (keys strictly ascending, bits 24-29
 * clear, known fields only, a lock level within 0..100, a place of its kind, finite positions, a drop only under
 * key bit 30 and key bit 30 only for a drop) and fills INTO (emptied first) only when all of it is good; INTO
 * NULL: checked, not kept. 1 good, 0 refused.
 * The second form (slice 2), written only when the list has an OPEN row or a stolen pair (so a list without them
 * stays readable by the first reader): "AWL2", u32 rows (0 allowed), the rows as above with OPEN known (never on a
 * drop), then u32 pairs and each pair: u8 length and the item id, u8 length and the owner id, u8 faction (0 or 1),
 * u32 count (1 .. AW_LEDGER_STOLEN_COUNT); pairs strictly ascending, ids printable and folded, never gold. The
 * reader takes both forms; an "AWL1" list with OPEN is refused as before.
 * The third form (slice 3), written only when the list has a container delta or an NPC rank: "AWL3", the second
 * form's rows and pairs (either may be 0), then u32 deltas and each: u32 key, u8 length and the folded item id, i32
 * count (non-zero, at most AW_LEDGER_STOLEN_COUNT either way), strictly ascending by (key, id); then u32 ranks and
 * each: u32 key, u8 rank, strictly ascending; keys of both follow the key rules and never carry bit 30. An "AWL3"
 * with neither is refused (it would have been written as AWL1 or AWL2).
 * The fourth form (slice 4), written only when a slice 4 table or a named fact has an entry: "AWL4", the third
 * form's parts (any may be 0), then for GLOBALS, QUESTS, TOPICS and DISPOSITIONS in turn: u32 entries and each: u32
 * key, then i32 value (not for TOPICS), strictly ascending by key; then u32 facts and each: u8 length and the folded
 * id, i32 value, strictly ascending by id. An "AWL4" with none of them is refused.
 * The fifth form (slice 5), written only when a script local or a global script's running state is kept: "AWL5", the
 * fourth form's parts (any may be 0), then u32 scripts and each: u32 name hash, u16 hint, u8 running (0 or 1),
 * strictly ascending by hash; then u32 locals and each: u8 global (0 or 1), u32 key, u32 script name hash, u16 hint,
 * u8 slot, i32 value (never 0), strictly ascending by (global, key, slot); an object's key follows the key rules and
 * never carries bit 30, a global script's key is its script hash. An "AWL5" with neither is refused.
 * The sixth form (slice 6), written only when an actor row with a field or actor records are kept: "AWL6", the fifth
 * form's parts (any may be 0), then u32 actor rows and each: u32 key (bits 24-31 clear, strictly ascending), u8
 * fields (AW_LEDGER_ACTOR_*, never 0), with PICK u16 pick (1 .. 0x8001), with MOVED f32 x, y, z, yaw, health, hours
 * and i32 room (0 or 1 .. 0xFFFFFF); then u32 record bytes and the bytes ("AWAR" first when there are any). An
 * "AWL6" with neither is refused.
 * The seventh form (slice 7), written only when a content file, an ident, a place's refill time or an actor's death
 * time is kept: "AWL7", the sixth form's parts (any may be 0; actor rows may carry DIED: f32 hours after the room), then
 * u8 files and each: u8 index (0 .. 31, strictly ascending), u8 length and the name (printable), u32 references, 8
 * digest bytes; then u32 idents and each: u32 key (the key rules, never bits 30-31), u32 record hash (never 0),
 * strictly ascending; then u32 stamps and each: u8 at (CELL or ROOM), i32 where, f32 hours, strictly ascending by
 * (at, where). An "AWL7" with none of the four is refused. */
/* Slice 7, the build's reference identity table: focus.awf's last section (tools/prepare_focus.py), little-endian:
 *   "AWI1" u8 files, each {u8 index, u8 length, the name, u32 references, 8 digest bytes (SHA-256's first)},
 *   u32 iMonthsToRespawn, f32 fCorpseRespawnDelay, f32 fCorpseClearDelay (the master's GMSTs),
 *   u32 rows, u32 step, u32 blocks (= ceil(rows / step)), blocks x u32 the first key of each block,
 *   rows x {u32 key | flags << 24, u32 record hash}   ascending key: every live placed reference of the content files
 *          by its stable id (tools/ref_identity.py), flags AW_REFS_RESPAWN (its record is flagged Respawn: a container,
 *          a creature or an NPC) and AW_REFS_LEVELLED (a levelled creature list), the record hash AW_LedgerNameHash
 *          of the reference's record id.
 * Only the block index is resident (about 5 KB for Morrowind.esm's 316,116 references) and one block of rows
 * (STEP x 8 bytes) read when a key is looked up. READ: the bytes at AT (0 ok). */
#define AW_REFS_RESPAWN 0x01000000U
#define AW_REFS_LEVELLED 0x02000000U
#define AW_REFS_STEP_MAX 1024
#define AW_REFS_BLOCK_BYTES 8192      /* AW_REFS_STEP_MAX rows of 8 bytes */
#define AW_REFS_BLOCKS_MAX 16384
#define AW_REFS_ROWS_MAX 4194304
typedef struct {
    int (*read)(void *context,long at,void *out,long bytes);
    void *context;
    long rows_at;
    uint32_t rows,step,blocks,*first;
    aw_ledger_file_t file[AW_LEDGER_FILES_MAX];
    int file_count;
    aw_ledger_respawn_t respawn;
    unsigned char *block;           /* STEP x 8 bytes: block CACHED (-1 none) */
    long cached;
    unsigned long lookups,reads;
} aw_refs_t;
/* Read the table's head at AT (END the file's end); 1 ready, 0 not a table this engine reads (nothing held). */
int AW_RefsOpen(aw_refs_t *r,int (*read)(void *context,long at,void *out,long bytes),void *context,long at,long end);
/* KEY's record hash and flags (AW_REFS_*): 1 found, 0 not a reference of this game. */
int AW_RefsFind(aw_refs_t *r,uint32_t key,uint32_t *record,uint32_t *flags);
void AW_RefsClose(aw_refs_t *r);
int AW_LedgerEncode(const aw_ledger_t *l,unsigned char *out,int capacity);
int AW_LedgerDecode(const unsigned char *data,int size,aw_ledger_t *into);

/* Slice 7, what respawn and migration did this session (aw_mwscript_status, aw_placed ledger): containers refilled,
 * place loads that refilled, actors come back; the last migrated load's drops (RECORDS: actor records and dead
 * counts of another build's actor table, dropped). */
typedef struct {
    unsigned long containers,places,actors,records,migrated_all;
    int migrations;
    aw_ledger_dropped_t migrated;
} aw_ledger_events_t;
extern aw_ledger_events_t aw_ledger_events;
/* The engine's side: the game hours now (the clock's saved globals, aw_clock.c; 0 before it runs), the build's
 * reference identity table (aw_inventory.c: focus.awf's AWI1 section, opened on first use; NULL without one). */
float AW_LedgerGameHours(void);
aw_refs_t *AW_PlacedRefs(void);
/* The engine's side (aw_mwhost.c, aw_inventory.c): the counts of the list (aw_placed ledger); a map position's place
 * for a row (the exterior cell and the original's game units outdoors, a numbered room and its room-local game units,
 * else the scene id and map units; 0 when none) and back (0 when the row's place is not on this map). */
void AW_MwscriptLedgerStatus(void);
int AW_PlacedWhere(const float *local,int *at,int32_t *where,float *game);
int AW_PlacedLocal(int at,int32_t where,const float *game,float *local);
#endif
