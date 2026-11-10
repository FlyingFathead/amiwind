/* SPDX-License-Identifier: GPL-2.0-or-later
 * See-through ("fence") faces (d_fence.c, ROOM-DECAL-ALPHA-62). Kept out of
 * model.h, whose text the packed-edge allocation policy pins
 * (tools/edge_cache_heap.py): msurface_t flags bits above model.h's own.
 */
#ifndef D_FENCE_H
#define D_FENCE_H

/* its texture name starts with '{' and index 255 is its transparent texel;
 * r_bsp.c sets both bits the first time it meets the face */
#define SURF_DRAWFENCE		0x80
#define SURF_FENCEKNOWN		0x100
#define AW_FENCE_TEXTURE_PREFIX	'{'

/* msurface_t.flags is an unsigned short: fail the build if these do not fit */
typedef char aw_fence_flags_fit_u16[((SURF_DRAWFENCE|SURF_FENCEKNOWN)<=65535 &&
    !((SURF_DRAWFENCE|SURF_FENCEKNOWN) & (SURF_PLANEBACK|SURF_DRAWSKY|SURF_DRAWSPRITE|
      SURF_DRAWTURB|SURF_DRAWTILED|SURF_DRAWBACKGROUND)))?1:-1];

#endif
