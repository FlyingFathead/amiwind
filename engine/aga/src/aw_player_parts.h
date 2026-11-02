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

#endif
