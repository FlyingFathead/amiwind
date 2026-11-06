/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_STATE_H
#define AW_STATE_H
#include <stdint.h>
#define AW_STATE_VALUES 32
/* INVENTORY-ORIGINAL-LIMITS-61 (ENCUMBRANCE-INCOMPLETE-61, COLLECT-CAPACITY-REJECTED-60): the kinds of item carried
 * have no fixed limit, as in the original, where only the weight limits what the player carries. The item table is
 * its own table, apart from the 32 global and 32 quest rows: rows of AW_ITEM_BLOCK in blocks from the game heap
 * (AW_TryMalloc), added as the kinds come; a row keeps the item's count, its condition and charge (each with its mark)
 * and its weight (from the item's record, AW_ItemsWeigh), so the carried weight is a running total (AW_ItemsBurden),
 * never summed per frame. A new kind takes a row whose count fell to 0 first, then a new row.
 * OWNERSHIP: aw_state_t is copied by value in places; the copy shares the item table. Only the state that owns the
 * table changes items (AW_ItemsClone makes a copy of its own, AW_ItemsFree gives the rows back); a saved game decoded
 * into an aw_save_t owns its table until AW_SaveRelease or until it becomes the game's state.
 * AW_ITEM_KINDS_MAX bounds a decoded count only (the item catalogue's own bound, 65,536 records): never reached. */
#define AW_ITEM_BLOCK 32
#define AW_ITEM_KINDS_MAX 65536
#define AW_ITEM_CONDITION 1U   /* row flags: condition recorded (below the record's health) */
#define AW_ITEM_CHARGE 2U      /* charge recorded (below full) */
#define AW_ITEM_WEIGHED 4U     /* weight read from the item's record */
/* One kind of item, 24 bytes: its id is kept once in the table's name pool (NAME: offset, low 24 bits; FLAGS: top 8
 * bits), its HASH (AW_ItemHash of the folded id) is what a search compares first. The weight stays in the row so a
 * count going down needs no record read. */
typedef struct {
    uint32_t hash;int32_t value;
    float condition,charge,weight;
    uint32_t name;
} aw_item_row_t;
#define AW_ITEM_FLAGS(row) ((row)->name>>24)
#define AW_ITEM_SET_FLAG(row,f) ((row)->name|=(uint32_t)(f)<<24)
#define AW_ITEM_CLEAR_FLAG(row,f) ((row)->name&=~((uint32_t)(f)<<24))
typedef struct {
    int count,blocks;          /* rows in use (rows at 0 included); blocks allocated */
    aw_item_row_t **block;     /* the blocks (heap); NULL with no rows */
    char *names;               /* the name pool: every row's id, 0-terminated (heap) */
    uint32_t names_used,names_size;
    float burden;              /* sum of count x weight over the weighed rows */
} aw_items_t;
#define AW_ITEM_ROW(state,i) (&(state)->items.block[(i)/AW_ITEM_BLOCK][(i)%AW_ITEM_BLOCK])
#define AW_ITEM_ID(state,i) ((const char *)(state)->items.names+(AW_ITEM_ROW(state,i)->name&0xffffffU))
/* row I's condition or charge mark (AW_ITEM_CONDITION / AW_ITEM_CHARGE): Has (I may be -1), Mark (set with VALUE),
 * Unmark (cleared, value 0) */
#define AW_ITEM_HAS(state,i,f) ((i)>=0 && (AW_ITEM_FLAGS(AW_ITEM_ROW(state,i))&(f)))
#define AW_JOURNAL_ENTRIES 256
/* Dedicated placement facts, not quest/global slots. A catalogue digest binds
 * dense indices to full original identities; no respawn in the first stage. */
#define AW_HARVEST_SLOTS 4096
typedef struct {
    uint32_t slots;unsigned char catalogue[32];
    uint32_t facts[AW_HARVEST_SLOTS];
} aw_harvest_state_t;
/* Runtime equipment and placed drops retain original item identity. Slots use
 * original inventory semantics, independent of the ready-hand animation. */
#define AW_INVENTORY_SLOTS 19
#define AW_INVENTORY_DROPS 32
typedef struct {
    uint32_t serial;
    char id[64],scene[16];
    int32_t count;
    float position[3],yaw,condition;
    uint32_t condition_known;
} aw_dropped_item_t;
typedef struct {
    char equipped[AW_INVENTORY_SLOTS][64];
    uint32_t next_serial,initialized;
    aw_dropped_item_t dropped[AW_INVENTORY_DROPS];
} aw_inventory_state_t;
/* The selected magic item (the original magic menu's item selection; OpenMW
 * InventoryStore::mSelectedEnchantItem). The current enchantment charge of an owned item is in its item row
 * (AW_ITEM_CHARGE); no mark means full charge (OpenMW CellRef charge -1). */
typedef struct {
    char selected[64];
} aw_magic_state_t;
enum aw_value_kind { AW_GLOBAL, AW_JOURNAL, AW_ITEM };
enum aw_compare { AW_EQ, AW_NE, AW_GT, AW_GE, AW_LT, AW_LE };
typedef struct {char id[64];int32_t value;} aw_value_t;
typedef struct {int quest;int32_t stage,days,milliseconds;} aw_journal_entry_t;
typedef struct {
    /* the globals (AW_GLOBAL) and quest stages (AW_JOURNAL), 32 rows each; the items are in their own table */
    int count[2];aw_value_t values[2][AW_STATE_VALUES];
    aw_items_t items;
    int journal_count;aw_journal_entry_t journal[AW_JOURNAL_ENTRIES];
    aw_harvest_state_t harvest;
    aw_inventory_state_t inventory;
    aw_magic_state_t magic;
} aw_state_t;
extern aw_state_t aw_state;
/* CELL-CHANGES-59 slice 4 (AW-STATE-32-SLOTS-48): the named globals (the engine's "amiwind:..." facts) past the 32
 * AW_GLOBAL slots live in the world change list's named facts (aw_ledger.h), saved with it; aw_save.c sets these
 * (NULL, as in the native tests: a 33rd is refused as before). A fact already there stays there. */
extern int (*aw_state_fact_get)(const char *id,int32_t *out);
extern int (*aw_state_fact_set)(const char *id,int32_t value);
void AW_StateReset(void);
int32_t AW_StateGet(const aw_state_t *state,int kind,const char *id);
int AW_StateSet(aw_state_t *state,int kind,const char *id,int32_t value);
int AW_StateTest(const aw_state_t *state,int kind,const char *id,int comparison,int32_t value);
int AW_JournalAdd(aw_state_t *state,const char *id,int32_t index);
unsigned AW_JournalNotices(void);   /* sJournalEntry notices owed so far (a rising quest index each) */
int AW_ItemAdd(aw_state_t *state,const char *id,int32_t count);
/* The item table (INVENTORY-ORIGINAL-LIMITS-61). Count: rows in use; Index: the row of ID (any case), -1 none;
 * Reserve: room for N new kinds made now (rows at 0 count; blocks allocated), so the adds after it cannot fail for
 * room, 0 when memory says no (nothing changed); Append: a raw row at the end (the save decoder; 0 refused);
 * Free: the rows given back (the table empty); Clone: OUT a copy of IN with rows of its own (0 when memory says no:
 * OUT empty). */
int AW_ItemCount(const aw_state_t *state);
int AW_ItemIndex(const aw_state_t *state,const char *id);
int AW_ItemReserve(aw_state_t *state,int kinds);
int AW_ItemAppend(aw_state_t *state,const char *id,int32_t value);
void AW_ItemsFree(aw_state_t *state);
void AW_ItemMark(aw_state_t *state,int i,unsigned flag,float value);
void AW_ItemUnmark(aw_state_t *state,int i,unsigned flag);
int AW_ItemsClone(aw_items_t *out,const aw_items_t *in);
/* The carried weight (ENCUMBRANCE-INCOMPLETE-61): the running total of count x weight over the weighed rows,
 * changed by every count change (no per-frame sum). aw_item_weight (aw_inventory.c sets it: the item's record, read
 * from memory where it already is; NULL in the native tests: rows stay unweighed) gives a new row its weight;
 * AW_ItemsWeigh weighs every unweighed row and sums the total again exactly (the area load, after the carried
 * items' records were read; a loaded save). */
extern int (*aw_item_weight)(const char *id,float *weight);
/* a loaded save's item table taken over by the game (aw_save.c AW_SaveSpawn): its rows weighed at once (aw_inventory.c
 * sets it: one pass over the item file for many kinds; NULL in the native tests) */
extern void (*aw_save_items_loaded)(void);
float AW_ItemsBurden(const aw_state_t *state);
void AW_ItemsWeigh(aw_state_t *state);
/* why an AW_ItemAdd(state,id,count) would refuse: AW_ITEM_OK, AW_ITEM_FULL (no memory for a row for a new kind),
 * AW_ITEM_TOO_MANY (the count would pass INT32_MAX or below 0), AW_ITEM_BAD_ID. AW_ItemRefusalText: that reason in a
 * few plain words. AW_ItemRoom: 1 when a new kind can be taken now (a row at 0, a free row, or memory for a block). */
enum { AW_ITEM_OK, AW_ITEM_FULL, AW_ITEM_TOO_MANY, AW_ITEM_BAD_ID };
int AW_ItemRoom(const aw_state_t *state);
int AW_ItemRefusal(const aw_state_t *state,const char *id,int32_t count);
const char *AW_ItemRefusalText(const aw_state_t *state,int reason);
/* Enchantment recharge for unpaused or waited seconds (aw_inventory.c sets it). */
extern void (*aw_magic_frame)(float seconds);
int AW_CaptainDuties(void);
int AW_CourtyardRingAvailable(void);
int AW_CourtyardTakeRing(void);
#define AW_Papers() AW_StateGet(&aw_state,AW_ITEM,"chargen statssheet")
#define AW_Ring() AW_StateGet(&aw_state,AW_ITEM,"ring_keley")
#define AW_Package() AW_StateGet(&aw_state,AW_ITEM,"bk_a1_1_caiuspackage")
#endif
