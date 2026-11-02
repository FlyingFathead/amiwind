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
#define AW_LEDGER_FIELDS 0x7FU

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
typedef struct aw_ledger_s {
    aw_ledger_row_t *row;
    int count,capacity;
    int *place;                   /* row indices by (at, where, key); valid while PLACED is set */
    int placed,place_capacity;
    int extras;                   /* rows with an extra block */
    unsigned long refused;        /* rows refused for memory or AW_LEDGER_ROWS (the change is not kept) */
} aw_ledger_t;

/* the session's list (the game being played) */
extern aw_ledger_t aw_ledger;

/* 1 (the default): the object state and the player's drops are kept here; 0: the old fixed tables (aw_mwhost.c
 * objects[1024], aw_state.h dropped[32] keyed by map name), kept selectable (aw_placed ledger on|off; from the next
 * new game or load, as the stores do not move between each other). */
extern int aw_ledger_on;
int AW_LedgerRows(const aw_ledger_t *l);
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
 * NULL: checked, not kept. 1 good, 0 refused. */
int AW_LedgerEncode(const aw_ledger_t *l,unsigned char *out,int capacity);
int AW_LedgerDecode(const unsigned char *data,int size,aw_ledger_t *into);

/* The engine's side (aw_mwhost.c, aw_inventory.c): the counts of the list (aw_placed ledger); a map position's place
 * for a row (the exterior cell and the original's game units outdoors, a numbered room and its room-local game units,
 * else the scene id and map units; 0 when none) and back (0 when the row's place is not on this map). */
void AW_MwscriptLedgerStatus(void);
int AW_PlacedWhere(const float *local,int *at,int32_t *where,float *game);
int AW_PlacedLocal(int at,int32_t where,const float *game,float *local);
#endif
