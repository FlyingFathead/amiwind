/* SPDX-License-Identifier: GPL-2.0-or-later
 * The player's body assembled from parts by equipment slot (docs/THIRD_PERSON.md "The assembled body";
 * PLAYER-GEAR-VISUAL-59). The builder (tools/prepare_player_parts.py) writes one skeletal model per part mesh in the
 * shared model table (progs/parts/<12 hex>.mdl, unit scale, on the shared humanoid table) and the recipe table
 * view/parts.txt (AWPP1). AW_PartsAssemble reads the recipe's text and gives the parts of one character: the race's
 * skin per slot, the chosen head and hair, and over them the worn clothing and armour by the original's priority
 * (tools/../src/mwad/npc.py outfit: armour 3, robe 24, skirt 8, other clothing 2; a higher rank takes a slot, equal
 * ranks the first id; a part '-' covers its slot with nothing, as a helmet hides the hair). Pure: no engine state. */
#ifndef AW_PLAYER_PARTS_H
#define AW_PLAYER_PARTS_H

#define AW_PARTS_SLOTS 27        /* mwad.npc PART_NAMES */
#define AW_PARTS_MAX 24          /* parts drawn at most (27 slots less the shield and weapon bones and the tail) */
#define AW_PARTS_ITEMS 16        /* worn items read at most */
#define AW_PARTS_PATH 32         /* "progs/parts/<12 hex>.mdl" is 28 */

typedef struct {
    int count;                               /* parts to draw */
    int slot[AW_PARTS_MAX];
    char model[AW_PARTS_MAX][AW_PARTS_PATH]; /* game paths */
    char table[AW_PARTS_PATH];               /* the shared table the parts name */
    char anm[48];                            /* the player's groups on its frames */
    int weapon_bone, shield_bone;            /* the item bones' table indices (-1 none) */
    float weight, height;                    /* the race and sex's own scale (x y by weight, z by height) */
    int beast;                               /* 1 = the beast table (no shoes or boots drawn there either) */
} aw_parts_body_t;

/* The parts of RACE (its id; the recipe writes a space as '|'), FEMALE, the chosen HEAD and HAIR (BODY ids; NULL or "" = the race's
 * first) wearing the ITEMS (their ids, any order, NULL entries skipped) from the recipe TEXT (SIZE bytes, need not be
 * NUL-terminated). 1 = OUT holds a body; 0 = no such race and sex in the recipe or a malformed recipe. */
int AW_PartsAssemble(const char *text, long size, const char *race, int female, const char *head, const char *hair,
                     const char *const *items, int nitems, aw_parts_body_t *out);
/* The inventory picture's pose on the shared table (INVENTORY-PREVIEW-BAKED-BODY-59): the group names for the right
 * hand's weapon TYPE (-1 or anything outside 0..8: unarmed; 0..8 the original's melee types), the first the
 * original's own group, the second its one- or two-handed fallback (NULL when none); the picture starts the group
 * and advances no time (OpenMW 0.51 mwrender/characterpreview.cpp InventoryPreview::update, the same rule
 * tools/player_inventory_pose.py bakes). *SHOW_LEFT 0 for a two-handed weapon (no shield shown). Returns 1 or 2. */
int AW_PartsInventoryGroups(int type, const char *out[2], int *show_left);

/* A resident's own recipe (NPC-PARTS-RUNTIME-59, docs/MODULAR_NPCS.md "Stage: residents from parts"): the builder
 * (tools/npc_recipes.py) writes view/npc_parts.txt (AWNP1), one line per resident drawn from parts:
 *   N <npc id> <race> <0|1> <head body id|-> <hair body id|-> <worn item id> ...
 * ids with a space written '|', as in the body recipe. AW_PartsNpcFind reads the line of ID (case-insensitive) into
 * OUT; the words stay as written ('|' for a space), which AW_PartsAssemble reads as the same ids. Pure. */
#define AW_PARTS_ID 64
typedef struct {
    char race[AW_PARTS_ID], head[AW_PARTS_ID], hair[AW_PARTS_ID];   /* head/hair "" = the race's first */
    int female, count;
    char items[AW_PARTS_ITEMS][AW_PARTS_ID];
} aw_parts_npc_t;
/* 1 = OUT holds ID's recipe; 0 = no line for ID, or TEXT is not AWNP1, or the line is malformed. */
int AW_PartsNpcFind(const char *text, long size, const char *id, aw_parts_npc_t *out);

/* The residents' recipes per place (BUILD-NPC-RECIPES-PER-CELL-59; tools/npc_recipes.py has the byte layout): one
 * small binary table per exterior cell (view/npc_parts/c<x>_<y>.awnb, grid numbers) and per room
 * (view/npc_parts/<map>.awnb), AWNB: one fixed record per resident placed there, sorted by its id hash (race and sex in
 * a byte, head, hair and worn items as 16-bit indices into the table's own few names). The engine holds only the
 * tables of the places loaded now (a cell's when the streamer's window joins it, a room's when the room is entered;
 * each goes with its place), read with one read each and searched by hash, no text parsed. Big-endian. The set below
 * never allocates or frees (the caller owns the bytes). Pure. */
#define AW_NPC_TABLES 40         /* places held at once (the window's frames plus the home frame, or one room) */
#define AW_NPC_RECORD (10 + 2 * AW_PARTS_ITEMS)  /* npc_recipes.RECORD */
typedef struct {
    struct {char key[AW_PARTS_ID]; unsigned char *data; long bytes;} t[AW_NPC_TABLES];
    int count;
    long bytes;                  /* held now */
} aw_npc_tables_t;
/* KEY of the exterior cell CX CY into OUT ("c<x>_<y>"); a room's key is its map name. */
void AW_NpcTableCellKey(int cx, int cy, char *out, int size);
/* FNV-1a 32 of ID as a recipe word (ASCII lower case, a space as '|'): npc_recipes.id_hash. */
unsigned long AW_NpcIdHash(const char *id);
/* The exterior cells' tables are in one pack, view/npc_parts/cells.awnp (AWNP: u16 cells, u16 0, then per cell sorted
 * by x then y: i16 x, i16 y, u32 offset, u32 size; then the tables). The pack's index is read once and held: the bytes
 * of the whole index from its first 8 bytes HEAD (-1 not a pack), and where cell CX CY's table is (1, or 0 none). */
long AW_NpcPackIndexBytes(const unsigned char *head);
int AW_NpcPackFind(const unsigned char *index, long size, int cx, int cy, unsigned long *at, unsigned long *bytes);
/* The resident directory, view/npc_parts/dir.awnd (AWND: u16 places, u16 0, u32 residents; per resident sorted by
 * hash u32 id hash, u16 place; a u16 offset per place name; the names): which place's table holds a resident, for a
 * lookup outside the places loaded now (one table narrow-loaded, never all). Count: residents, 0 not a directory.
 * Find: 1 and KEY (SIZE bytes) = the place of ID. CellOfKey: 1 and *CX *CY when KEY is "c<x>_<y>". */
int AW_NpcDirCount(const unsigned char *data, long size);
int AW_NpcDirFind(const unsigned char *data, long size, const char *id, char *key, int keysize);
int AW_NpcCellOfKey(const char *key, int *cx, int *cy);
/* Residents in table DATA (SIZE bytes), -1 when it is not a whole AWNB table. */
int AW_NpcTableCount(const unsigned char *data, long size);
/* ID's recipe from one table into OUT (the table's words, as the text form had them): 1 found. */
int AW_NpcTableFind(const unsigned char *data, long size, const char *id, aw_parts_npc_t *out);
/* 1 when KEY is held. */
int AW_NpcTablesHas(const aw_npc_tables_t *t, const char *key);
/* DATA (BYTES) held under KEY: 1 added; 0 KEY already held or DATA not a table, -1 the set is full (the caller keeps
 * DATA then and frees it). */
int AW_NpcTablesAdd(aw_npc_tables_t *t, const char *key, unsigned char *data, long bytes);
/* KEY let go: its bytes for the caller to free (NULL when not held); *BYTES their size. */
unsigned char *AW_NpcTablesDrop(aw_npc_tables_t *t, const char *key, long *bytes);
/* The last held table let go (NULL when none): for clearing the set. */
unsigned char *AW_NpcTablesPop(aw_npc_tables_t *t, long *bytes);
/* ID's recipe from the tables held now (the first that has it): 1 = OUT holds it. */
int AW_NpcTablesFind(const aw_npc_tables_t *t, const char *id, aw_parts_npc_t *out);

#endif
