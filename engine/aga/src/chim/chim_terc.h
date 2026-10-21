/* SPDX-License-Identifier: GPL-2.0-or-later
 * Compact terrain records (world format 0.10, EXPERIMENTAL; tools/chim/terc.py
 * writes them): a lossless repack of a chunk terrain's BSP29 brush image that
 * expands back into the very same bytes before the usual loaders read them.
 * Layout and methods: tools/chim/terc.py and docs/chim/WORLD_FORMAT.md. */
#ifndef CHIM_TERC_H
#define CHIM_TERC_H

#define CHIM_TERC_HEAD_BYTES	16
#define CHIM_TERC_ENTRY_BYTES	8

/* 1 when DATA starts with the compact record's magic. */
int ChimTerc_Is (const unsigned char *data, long bytes);
/* Expand the compact record SRC (BYTES) into DST (ROOM bytes; must not
 * overlap SRC): 1 and the image's size in *OUT, 0 on bad data or no room. */
int ChimTerc_Expand (const unsigned char *src, long bytes, unsigned char *dst, long room, long *out);
/* One lump of a compact record: METHOD's payload P (N bytes) expanded at DST + AT (ROOM bytes in DST); its
 * length in *LEN. DST NULL: the length only. 0 on bad data or no room. */
int ChimTerc_Lump (int method, const unsigned char *p, long n, unsigned char *dst, long at, long room, long *len);

#endif
