/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_C2P_H
#define AW_C2P_H
/* Chunky-to-planar conversion (aw_c2p.c), called by vid_amiga.c: one
 * prototype for the definition and the caller (ENGINE-STRICT-WARNINGS-36).
 * Needs <exec/types.h>. */
struct BitMap;
void *aw_c2p_reloc(struct BitMap *bm);
void aw_c2p_deinit(void *c2p);
void aw_c2p(void *c2p, struct BitMap *bm, UBYTE *src, ULONG width, ULONG rows);
#endif
