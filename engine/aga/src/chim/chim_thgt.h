/* SPDX-License-Identifier: GPL-2.0-or-later
 * Generated terrain records (world format 0.11, EXPERIMENTAL; tools/chim/thgt.py writes them): the render part of a
 * chunk terrain generated from its heights, the same bytes as the TERR record it replaces (chim_thgt.c). */
#ifndef CHIM_THGT_H
#define CHIM_THGT_H

#define CHIM_THGT_HEAD_BYTES	72

/* What the generator did (dbg and tests: the work per chunk join, counted). */
typedef struct
{
	unsigned long	records, tiles, surfaces, splits, texture_splits, vertexes, faces, nodes, leaves;
} chim_thgt_stats_t;

/* 1 when DATA starts with the generated record's magic. */
int ChimThgt_Is (const unsigned char *data, long bytes);
/* Generate the brush image of the record SRC (BYTES) into DST (ROOM bytes; must not overlap SRC): 1 and the
 * image's size in *OUT, 0 on bad data or no room. STATS (may be NULL) counts the work. */
int ChimThgt_Generate (const unsigned char *src, long bytes, unsigned char *dst, long room, long *out,
	chim_thgt_stats_t *stats);

#endif
