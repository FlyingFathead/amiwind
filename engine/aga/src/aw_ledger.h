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
 * with neither is refused (it would have been written as AWL1 or AWL2). */
int AW_LedgerEncode(const aw_ledger_t *l,unsigned char *out,int capacity);
int AW_LedgerDecode(const unsigned char *data,int size,aw_ledger_t *into);

/* The engine's side (aw_mwhost.c, aw_inventory.c): the counts of the list (aw_placed ledger); a map position's place
 * for a row (the exterior cell and the original's game units outdoors, a numbered room and its room-local game units,
 * else the scene id and map units; 0 when none) and back (0 when the row's place is not on this map). */
void AW_MwscriptLedgerStatus(void);
int AW_PlacedWhere(const float *local,int *at,int32_t *where,float *game);
int AW_PlacedLocal(int at,int32_t where,const float *game,float *local);
#endif
