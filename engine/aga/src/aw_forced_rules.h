/* SPDX-License-Identifier: GPL-2.0-or-later
 * The saved block of a script's ForceSneak and screen fade (v0.0.62, MWSCRIPT-GAP-FUNCTIONS-62; aw_mwhost.c):
 * "AWFS" u8 1, u8 the player forced, u8 count, count x u32 NPC reference, f32 the fade level the screen goes to
 * (0 none .. 1 black), big-endian; 11 + 4 x count bytes. Pure C (native tests: tests/test_mwscript.py). */
#ifndef AW_FORCED_RULES_H
#define AW_FORCED_RULES_H
#include <stdint.h>

/* The block's bytes into OUT, or -1 when CAPACITY is too small. */
int AW_ForcedPack(unsigned char *out,int capacity,int player,const uint32_t *refs,int count,float fade);
/* The block at P (of BYTES available) read: its bytes, or -1 when it is not one, cut, holds more than MAX references
 * or a fade outside 0..1. */
int AW_ForcedUnpack(const unsigned char *p,int bytes,int *player,uint32_t *refs,int max,int *count,float *fade);
#endif
