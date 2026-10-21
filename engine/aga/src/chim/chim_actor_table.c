/* SPDX-License-Identifier: GPL-2.0-or-later
 * The CHIM actor table's decoders (chim_actor_table.h). */
#include <string.h>
#include "chim_format.h"
#include "chim_actor_table.h"

static int Finite (float f)
{
	return f == f && f > -1e30f && f < 1e30f;
}

int ChimActors_Header (const unsigned char *p, long file_bytes, chim_actor_head_t *h)
{
	unsigned long end;
	if (file_bytes < CHIM_ACTOR_HEADER_BYTES || memcmp (p, "ACT1", 4) || ChimFormat_U16 (p+4) != 0 ||
		(ChimFormat_U16 (p+6) != CHIM_ACTOR_VERSION && ChimFormat_U16 (p+6) != CHIM_ACTOR_VERSION_LISTS &&
		 ChimFormat_U16 (p+6) != CHIM_ACTOR_VERSION_SCALES) ||
		ChimFormat_U32 (p+8) != CHIM_ACTOR_HEADER_BYTES)
		return 0;
	h->version = ChimFormat_U16 (p+6);
	h->lists = 0;
	h->lists_at = ChimFormat_U32 (p+44);
	h->cells = ChimFormat_U32 (p+12);
	h->cells_at = ChimFormat_U32 (p+16);
	h->records = ChimFormat_U32 (p+20);
	h->records_at = ChimFormat_U32 (p+24);
	h->bases = ChimFormat_U32 (p+28);
	h->bases_at = ChimFormat_U32 (p+32);
	h->text_at = ChimFormat_U32 (p+36);
	h->bytes = ChimFormat_U32 (p+40);
	if ((long)h->bytes != file_bytes || h->cells > 65536 || h->records > 1048576 || h->bases > 65536)
		return 0;
	end = (unsigned long)h->cells_at + (unsigned long)h->cells * CHIM_ACTOR_CELL_BYTES;
	if (h->cells_at < CHIM_ACTOR_HEADER_BYTES || end > h->records_at)
		return 0;
	end = (unsigned long)h->records_at + (unsigned long)h->records * CHIM_ACTOR_RECORD_BYTES;
	if (end > h->bases_at)
		return 0;
	end = (unsigned long)h->bases_at + (unsigned long)h->bases * CHIM_ACTOR_BASE_BYTES;
	if (end > h->text_at || h->text_at > h->bytes)
		return 0;
	if (h->version == CHIM_ACTOR_VERSION)
		return h->lists_at == 0;
	/* versions 2 and 3: the list section after the text (and the scales after it, version 3) */
	if (h->lists_at < h->text_at || h->lists_at + 4 > h->bytes || (h->lists_at & 3))
		return 0;
	return 1;		/* the section's own count: the caller reads and checks it (ChimActors_ListsValid) */
}

void ChimActors_Cell (const unsigned char *p, chim_actor_cell_t *c)
{
	c->cx = ChimFormat_S16 (p);
	c->cy = ChimFormat_S16 (p+2);
	c->first = ChimFormat_U32 (p+4);
	c->count = ChimFormat_U32 (p+8);
}

int ChimActors_Record (const unsigned char *p, const chim_actor_head_t *h, chim_actor_record_t *r)
{
	int k;
	r->key = ChimFormat_U32 (p);
	r->base = ChimFormat_U16 (p+4);
	r->flags = ChimFormat_U16 (p+6);
	for (k=0 ; k<3 ; k++)
	{
		r->origin[k] = ChimFormat_F32 (p+8+4*k);
		if (!Finite (r->origin[k]) || r->origin[k] <= -8192 || r->origin[k] >= 8192)
			return 0;
	}
	r->yaw = ChimFormat_F32 (p+20);
	return Finite (r->yaw) && r->yaw >= -720 && r->yaw <= 720 && (unsigned)r->base < h->bases &&
		r->key <= 0xFFFFFFu && r->key != 0;
}

int ChimActors_Base (const unsigned char *p, const chim_actor_head_t *h, chim_actor_base_t *b)
{
	b->at = ChimFormat_U32 (p);
	b->bytes = (unsigned)ChimFormat_U16 (p+4);
	b->kind = ChimFormat_U16 (p+6);
	b->hash = ChimFormat_U32 (p+8);
	if (b->kind == CHIM_ACTOR_KIND_LEVELLED && h->version != CHIM_ACTOR_VERSION)
		return b->bytes == 0;		/* AT is the base's list */
	return (unsigned long)h->text_at + b->at + b->bytes <= (h->version != CHIM_ACTOR_VERSION ? h->lists_at : h->bytes) &&
		b->kind <= CHIM_ACTOR_KIND_CORPSE;
}

int ChimActors_ListsValid (const unsigned char *s, unsigned long bytes, unsigned bases)
{
	unsigned long n, k, first, count, entries_at, total = 0;
	if (bytes < 4)
		return 0;
	n = ChimFormat_U32 (s);
	if (n > 0x7FFF || 4 + n * CHIM_ACTOR_LIST_BYTES > bytes)
		return 0;
	entries_at = 4 + n * CHIM_ACTOR_LIST_BYTES;
	for (k=0 ; k<n ; k++)
	{
		const unsigned char *l = s + 4 + k * CHIM_ACTOR_LIST_BYTES;
		first = ChimFormat_U32 (l);
		count = ChimFormat_U16 (l+4);
		if (l[6] > 100 || first != total)
			return 0;
		total += count;
	}
	if (entries_at + total * CHIM_ACTOR_ENTRY_BYTES != bytes)
		return 0;
	for (k=0 ; k<total ; k++)
	{
		unsigned t = ChimFormat_U16 (s + entries_at + k * CHIM_ACTOR_ENTRY_BYTES + 2);
		if (t == CHIM_ACTOR_NOTHING)
			continue;
		if (t & CHIM_ACTOR_NESTED ? (t & 0x7FFF) >= n : t >= bases)
			return 0;
	}
	return 1;
}

unsigned ChimActors_RollSeed (unsigned key, unsigned seed)
{
	unsigned x = (unsigned)(((unsigned long)(key ^ seed) * 2654435761UL) & 0xFFFFFFFFUL);
	return x ? x : 0x9E3779B9u;
}

unsigned ChimActors_Rand (unsigned *state)
{
	unsigned long x = *state;
	x ^= (x << 13) & 0xFFFFFFFFUL;
	x ^= x >> 17;
	x ^= (x << 5) & 0xFFFFFFFFUL;
	*state = (unsigned)x;
	return (unsigned)x;
}

int ChimActors_LevelledPick (const unsigned char *s, unsigned index, int level, unsigned *state)
{
	int depth;
	for (depth=0 ; depth<CHIM_ACTOR_MAX_DEPTH ; depth++)
	{
		unsigned long n = ChimFormat_U32 (s), first, count, k, m = 0, pick;
		const unsigned char *l, *e;
		int top = -1, flags, chance;
		unsigned t = CHIM_ACTOR_NOTHING;
		if (index >= n)
			return CHIM_ACTOR_PICK_NONE;
		l = s + 4 + index * CHIM_ACTOR_LIST_BYTES;
		first = ChimFormat_U32 (l);
		count = ChimFormat_U16 (l+4);
		chance = l[6];
		flags = l[7];
		e = s + 4 + n * CHIM_ACTOR_LIST_BYTES + first * CHIM_ACTOR_ENTRY_BYTES;
		if ((int)(ChimActors_Rand (state) % 100) < chance)
			return CHIM_ACTOR_PICK_NONE;
		if (!(flags & CHIM_ACTOR_ALL_LEVELS))
			for (k=0 ; k<count ; k++)
			{
				int lv = ChimFormat_U16 (e + k*CHIM_ACTOR_ENTRY_BYTES);
				if (lv <= level && lv > top)
					top = lv;
			}
		for (k=0 ; k<count ; k++)
		{
			int lv = ChimFormat_U16 (e + k*CHIM_ACTOR_ENTRY_BYTES);
			if (lv <= level && ((flags & CHIM_ACTOR_ALL_LEVELS) || lv == top))
				m++;
		}
		if (!m)
			return CHIM_ACTOR_PICK_NONE;
		pick = ChimActors_Rand (state) % m;
		for (k=0 ; k<count ; k++)
		{
			int lv = ChimFormat_U16 (e + k*CHIM_ACTOR_ENTRY_BYTES);
			if (lv <= level && ((flags & CHIM_ACTOR_ALL_LEVELS) || lv == top) && !pick--)
			{
				t = ChimFormat_U16 (e + k*CHIM_ACTOR_ENTRY_BYTES + 2);
				break;
			}
		}
		if (t == CHIM_ACTOR_NOTHING)
			return CHIM_ACTOR_PICK_NONE;
		if (!(t & CHIM_ACTOR_NESTED))
			return (int)t;
		index = t & 0x7FFF;
	}
	return CHIM_ACTOR_PICK_NONE;
}

unsigned long ChimActors_ListBytes (const unsigned char *s, unsigned long avail)
{
	unsigned long n, k, total = 0, heads;
	if (avail < 4)
		return 0;
	n = ChimFormat_U32 (s);
	if (n > 0x7FFF)
		return 0;
	heads = 4 + n * CHIM_ACTOR_LIST_BYTES;
	if (heads > avail)
		return 0;
	for (k=0 ; k<n ; k++)
		total += ChimFormat_U16 (s + 4 + k * CHIM_ACTOR_LIST_BYTES + 4);
	if (heads + total * CHIM_ACTOR_ENTRY_BYTES > avail)
		return 0;
	return heads + total * CHIM_ACTOR_ENTRY_BYTES;
}

int ChimActors_ScalesValid (const unsigned char *s, unsigned long bytes, unsigned records)
{
	unsigned long n, k;
	unsigned prev = 0;
	if (bytes < 4)
		return 0;
	n = ChimFormat_U32 (s);
	if (n > records || 4 + n * CHIM_ACTOR_SCALE_BYTES != bytes)
		return 0;
	for (k=0 ; k<n ; k++)
	{
		unsigned index = ChimFormat_U32 (s + 4 + k * CHIM_ACTOR_SCALE_BYTES);
		float scale = ChimFormat_F32 (s + 4 + k * CHIM_ACTOR_SCALE_BYTES + 4);
		if (index >= records || (k && index <= prev) || !Finite (scale) || scale <= 0 || scale > 64)
			return 0;
		prev = index;
	}
	return 1;
}

float ChimActors_Scale (const unsigned char *s, unsigned index)
{
	long lo = 0, hi = (long)ChimFormat_U32 (s) - 1;
	while (lo <= hi)
	{
		long mid = (lo + hi) / 2;
		unsigned at = ChimFormat_U32 (s + 4 + mid * CHIM_ACTOR_SCALE_BYTES);
		if (at == index)
			return ChimFormat_F32 (s + 4 + mid * CHIM_ACTOR_SCALE_BYTES + 4);
		if (at < index)
			lo = mid + 1;
		else
			hi = mid - 1;
	}
	return 1.0f;
}
