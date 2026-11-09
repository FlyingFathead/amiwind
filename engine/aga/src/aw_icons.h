/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_ICONS_H
#define AW_ICONS_H
/* One icon lookup table for the UI (tools/prepare_icons.py): gfx/icons.awl maps a
 * key ("item:<id>", "skill:26", "hud:box", "hud:bar", "hud:track:weapon|magic",
 * "mgef:<index>") to its converted picture (at most 32x32), gfx/icon/<sha16>.awi.
 * A caller owns its slots; a slot reloads only when its key changes, never per
 * frame. */
#define AW_ICON_MAX 32
typedef struct {
    char key[64];
    int ok,w,h;
    unsigned char pixels[AW_ICON_MAX*AW_ICON_MAX];
} aw_icon_t;
/* A wide UI strip (the title bar's head block): at most 320 x 16. */
#define AW_STRIP_W 320
#define AW_STRIP_H 16
typedef struct {
    char key[64];
    int ok,w,h;
    unsigned char pixels[AW_STRIP_W*AW_STRIP_H];
} aw_strip_t;
int AW_StripLoad(aw_strip_t *slot,const char *key);
/* Returns 1 when the slot holds the picture of key (loading it once). */
int AW_IconLoad(aw_icon_t *slot,const char *key);
/* Opaque blit of a loaded picture (clipped out entirely when off screen). */
void AW_IconDraw(const aw_icon_t *icon,int x,int y);
/* ITEM-ICONS-MISSING-62: the slot fit of every item picture (inventory, container, barter windows): the scale and the
 * top left of a W x H picture in a SLOT_W x SLOT_H slot (0 when it does not fit), and the slot filled with COLOUR
 * with the picture centred on it. "big:<id>" is an item's 32 x 32 picture (every item with an icon, black behind it),
 * "inv:<id>" its 16 x 16 inventory picture, which a slot of 34 shows at 2x. */
int AW_IconFit(int w,int h,int slot_w,int slot_h,int *ox,int *oy);
void AW_IconDrawFit(const aw_icon_t *icon,int x,int y,int slot_w,int slot_h,int colour);
/* An item's picture slot: tries "big:<id>", then "inv:<id>" (what the inventory window shows); 1 when loaded. */
int AW_IconLoadItem(aw_icon_t *slot,const char *id);
/* Statistics for the cost check (dbg/console aw_icons): table lookups and
 * picture reads since start, failed lookups; HUD box time per method
 * (0 placeholders, 1 original icons). */
/* area: item pictures answered by the loaded area tables (AREA-TABLES-59) */
typedef struct {unsigned lookups,reads,misses,draws,frames[2];double seconds[2];unsigned area;} aw_icon_stats_t;
extern aw_icon_stats_t aw_icon_stats;
/* Prints the statistics (console: aw_magic stats). */
void AW_IconStats(void);
/* Console aw_magic (selection, diagnostic charge, stats). */
void AW_MagicCommand(void);
#endif
