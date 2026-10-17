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
/* Returns 1 when the slot holds the picture of key (loading it once). */
int AW_IconLoad(aw_icon_t *slot,const char *key);
/* Opaque blit of a loaded picture (clipped out entirely when off screen). */
void AW_IconDraw(const aw_icon_t *icon,int x,int y);
/* Statistics for the cost check (dbg/console aw_icons): table lookups and
 * picture reads since start, failed lookups; HUD box time per method
 * (0 placeholders, 1 original icons). */
typedef struct {unsigned lookups,reads,misses,draws,frames[2];double seconds[2];} aw_icon_stats_t;
extern aw_icon_stats_t aw_icon_stats;
/* Prints the statistics (console: aw_magic stats). */
void AW_IconStats(void);
/* Console aw_magic (selection, diagnostic charge, stats). */
void AW_MagicCommand(void);
#endif
