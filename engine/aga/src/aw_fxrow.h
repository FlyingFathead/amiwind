/* SPDX-License-Identifier: GPL-2.0-or-later
 * The active-effect icons (HUD-ACTIVE-EFFECTS-ROW-64; docs/HUD_ACTIVE_EFFECTS.md): the small icon of every magic effect
 * active on the player, in a row under the view that wraps into at most three rows, the last place "+N" for the ones
 * that do not fit; the same icons on the Stats window, and V there opens a box that scrolls: every active effect with
 * its icon, name, description, magnitude, sources and time left.
 *
 * Rules from OpenMW 0.51 (apps/openmw/mwgui/spellicons.cpp updateWidgets, written independently): one icon per effect
 * ID however many sources feed it (a std::map keyed by the effect ID, so the icons stand in effect-number order); its
 * details keep every source with its argument, magnitude and own time left; a permanent source shows no countdown.
 * The pictures are the effect records' own small icons (MGEF ITEX), converted by the build (tools/prepare_icons.py,
 * gfx/effects.awe); nothing of the game is in the repository.
 *
 * The rules here are pure (aw_fxrow_rules.c, host-tested: tests/aga_fxrow_test.c); aw_fxrow.c is the engine glue. */
#ifndef AW_FXROW_H
#define AW_FXROW_H

#define AW_FX_ROWS_MAX 3      /* the HUD grid's rows at most (the maintainer's decision, 11 November 2026) */
#define AW_FX_HUD_ICON 12     /* the HUD's icon: the original 16 x 16 at about 3/4 (our HUD is 24/42 of the original's) */
#define AW_FX_HUD_STEP 13     /* icon and a one-pixel gap */
#define AW_FX_LIST_ICON 16    /* the list box's icon: the original's own size */
#define AW_FX_HUD_MAX 48      /* HUD places at most (the resident picture cache holds this many) */
#define AW_FX_ENTRIES 96      /* effect entries collected: the pool's 32 on the player and the always-active spells' */
#define AW_FX_EFFECTS 143     /* the game's magic effect numbers 0..142 (aw_effects.h AW_EFFECT_COUNT) */

/* Where an entry comes from (OpenMW's source kinds: a cast spell, a potion or used item, a worn item's constant
 * effect, the spells of the actor's list that act always). */
enum {AW_FX_FROM_SPELL,AW_FX_FROM_ITEM,AW_FX_FROM_WORN,AW_FX_FROM_ABILITY,AW_FX_FROM_BLIGHT,AW_FX_FROM_DISEASE,
      AW_FX_FROM_CURSE,AW_FX_FROM_POWER,AW_FX_FROMS};
/* One active effect on the player: EFFECT 0..142, ARG its attribute or skill (-1 none), SOURCE the spell row or slot
 * (-1 unknown), FROM AW_FX_FROM_*, LEFT the seconds left (< 0: permanent, no countdown). */
typedef struct {short effect,arg;int source;unsigned char from;float magnitude,left;} aw_fx_entry_t;
/* One icon: the effect, its entries [FIRST, FIRST+COUNT) of the sorted list, the soonest end of its timed entries
 * (LEFT, < 0 when all are permanent), PERMANENT 1 when one of them is. */
typedef struct {short effect,first,count;float left;unsigned char permanent;} aw_fx_group_t;
/* The HUD grid: PER_ROW icons a row, ROWS rows used, SHOWN icons drawn, MORE hidden behind "+N" (0 none), PLACES
 * the places used (SHOWN, plus one for "+N"). */
typedef struct {int per_row,rows,shown,more,places;} aw_fx_layout_t;

/* Sorts E (N entries) by effect number, keeping the order of entries of the same effect (stable); N. */
int AW_FxSort(aw_fx_entry_t *e,int n);
/* The icons of a sorted list, at most MAX; their count. */
int AW_FxGroups(const aw_fx_entry_t *e,int n,aw_fx_group_t *g,int max);
/* The grid for GROUPS icons in an area WIDTH x HEIGHT pixels, icons of ICON pixels every STEP, at most MAX_ROWS rows and
 * MAX_PLACES places: everything when it fits, else the last place is "+N". 0 when not even one place fits. */
int AW_FxLayout(int groups,int width,int height,int icon,int step,int max_rows,int max_places,aw_fx_layout_t *out);
/* The top left of place I of L: row 0 at the bottom (Y_BOTTOM is its top), rows going up, each from X0 left to right. */
void AW_FxPlace(const aw_fx_layout_t *l,int i,int x0,int y_bottom,int step,int *x,int *y);
/* "+N" for N hidden icons. */
void AW_FxMoreText(int n,char *out,int size);
/* The time left as the list shows it: "permanent" (LEFT < 0), "12 s", "3 min 5 s", "2 h 4 min". */
void AW_FxTimeText(float left,char *out,int size);
const char *AW_FxFromName(int from);
/* A text of BYTES bytes (no terminator needed; line breaks and tabs count as spaces) in lines of at most WIDTH
 * characters (< AW_FX_LINE), broken between words (a word longer than a line is cut), at most MAX lines; their count. */
#define AW_FX_LINE 80
int AW_FxWrap(const char *text,int bytes,int width,char out[][AW_FX_LINE],int max);
/* FROM of a spell of the ASPT TYPE (0 spell, 1 ability, 2 blight, 3 disease, 4 curse, 5 power). */
int AW_FxFromSpellType(int type);

/* gfx/effects.awe (tools/prepare_icons.py write_effects): b'AWE1', u16 count, u8 small size, u8 large size, then count
 * rows of 16 bytes (u32 small picture, u32 large picture, u32 description: offsets from the file's start, 0 none;
 * u16 description bytes, u16 0), then the pictures (palette indices, size x size, no header) and the descriptions
 * (cp1252, no terminator); little-endian. */
#define AW_FX_FILE "gfx/effects.awe"
#define AW_FX_ROW_BYTES 16
typedef struct {unsigned long small,large,desc;unsigned short desc_bytes;} aw_fx_dir_t;
/* Reads the header and the directory of a file of BYTES bytes from DATA (at least the header and the rows); the rows
 * into DIR (MAX of them, the rest dropped), the sizes into SMALL and LARGE. The count, or -1 for a bad file (a
 * row pointing past the end, sizes that are not AW_FX_HUD_ICON and AW_FX_LIST_ICON). */
int AW_FxDirectory(const unsigned char *data,unsigned long head_bytes,unsigned long file_bytes,aw_fx_dir_t *dir,int max);

/* ---- engine glue (aw_fxrow.c) ---- */
void AW_FxRowInit(void);
/* The small (AW_FX_HUD_ICON) pictures of N (at most 32) EFFECTS into OUT in one open of the effect file; OK[i] 1 for
 * each read; how many were read (the character windows' spell lists, aw_spelllist.c). */
int AW_FxSmallIcons(const short *effects,int n,unsigned char (*out)[AW_FX_HUD_ICON*AW_FX_HUD_ICON],unsigned char *ok);
#endif
