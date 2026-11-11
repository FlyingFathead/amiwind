/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_tryalloc.c: the Amiga side of aw_tryalloc.h (SDK-MALLOC-TRAPS-52). The only file that calls the C library's
 * allocators: each request is checked against exec's largest free block first, because the toolchain's malloc
 * traps (TRAP #7) instead of returning NULL. */
#include <stdlib.h>
#include "aw_tryalloc.h"

#ifdef AW_TRYALLOC_CHECKED
#include <proto/exec.h>
#include <exec/memory.h>

unsigned long AW_TryAllocNeed (unsigned long size)
{
	return (size > AW_TRYALLOC_POOL ? size + 4 : AW_TRYALLOC_BLOCK) + AW_TRYALLOC_SPARE;
}

static int fits (unsigned long size)
{
	return (unsigned long)AvailMem (MEMF_LARGEST) >= AW_TryAllocNeed (size);
}

#undef free	/* this file frees with the C library's own */

/* The count by asking address (aw_tryalloc.h): linear probing on the block address, pc 0 = an empty slot. A removal shifts the
 * following entries back (no removed markers: with markers every free of a block not in the table scanned the whole
 * table once the markers filled it, and the first census engine stalled at the start). The table is kept at most
 * three quarters full, so a lookup of a block that is not noted (every small one) ends at the next empty slot. */
#define OWNED_SLOTS	2048
#define OWNED_MAX	(OWNED_SLOTS * 3 / 4)
static void *owned_block[OWNED_SLOTS];
static unsigned long owned_size[OWNED_SLOTS], owned_pc[OWNED_SLOTS], owned_dropped;
static int owned_count;
/* Off by default (the shipped engine): no block is noted and free() only tests this flag. aw_memcensus owners on
 * switches it on for a measuring session; off forgets the table. */
static int owned_on;

void AW_TryOwnersEnable (int on)
{
	if (!on)
	{
		int i;
		for (i=0 ; i<OWNED_SLOTS ; i++)
			owned_pc[i] = 0;
		owned_count = 0;
		owned_dropped = 0;
	}
	owned_on = on != 0;
}

int AW_TryOwnersOn (void) {return owned_on;}
static unsigned owned_slot (void *block) {return (unsigned)((((unsigned long)block >> 4) * 2654435761UL) >> 8) % OWNED_SLOTS;}

static void owned_forget (void *block)
{
	unsigned i, j, home;
	if (!owned_on || !block || !owned_count)
		return;
	for (i=owned_slot (block) ; owned_pc[i] ; i=(i+1)%OWNED_SLOTS)
		if (owned_block[i] == block)
			break;
	if (!owned_pc[i])
		return;
	owned_pc[i] = 0;
	owned_count--;
	/* backward shift: an entry after the hole whose home is not between the hole and it moves into the hole */
	for (j=(i+1)%OWNED_SLOTS ; owned_pc[j] ; j=(j+1)%OWNED_SLOTS)
	{
		home = owned_slot (owned_block[j]);
		if ((j > i && (home <= i || home > j)) || (j < i && home <= i && home > j))
		{
			owned_block[i] = owned_block[j];
			owned_size[i] = owned_size[j];
			owned_pc[i] = owned_pc[j];
			owned_pc[j] = 0;
			i = j;
		}
	}
}

static void owned_note (void *block, unsigned long size, unsigned long pc)
{
	unsigned i;
	if (!owned_on || !block || size < AW_TRYALLOC_OWNED)
		return;
	if (owned_count >= OWNED_MAX)
	{
		owned_dropped++;
		return;
	}
	for (i=owned_slot (block) ; owned_pc[i] ; i=(i+1)%OWNED_SLOTS)
		;
	owned_block[i] = block;
	owned_size[i] = size;
	owned_pc[i] = pc ? pc : 1;
	owned_count++;
}

void AW_TryFree (void *block)
{
	owned_forget (block);
	free (block);
}

int AW_TryOwners (unsigned long *pc, unsigned long *bytes, unsigned long *blocks, int max, unsigned long *total,
	unsigned long *dropped)
{
	int n = 0, j, k;
	unsigned i;
	*total = 0;
	*dropped = owned_dropped;
	for (i=0 ; i<OWNED_SLOTS ; i++)
	{
		if (!owned_pc[i])
			continue;
		*total += owned_size[i];
		for (j=0 ; j<n && pc[j] != owned_pc[i] ; j++)
			;
		if (j == n)
		{
			if (n == max)
			{
				/* the table is full: the entry goes to the smallest row when it is larger */
				for (k=0, j=0 ; k<n ; k++)
					if (bytes[k] < bytes[j])
						j = k;
				if (bytes[j] >= owned_size[i])
					continue;
				blocks[j] = 0;
				bytes[j] = 0;
			}
			else
			{
				n++;
				bytes[j] = blocks[j] = 0;
			}
			pc[j] = owned_pc[i];
		}
		bytes[j] += owned_size[i];
		blocks[j]++;
	}
	for (j=1 ; j<n ; j++)		/* largest first */
		for (k=j ; k>0 && bytes[k] > bytes[k-1] ; k--)
		{
			unsigned long t;
			t = pc[k]; pc[k] = pc[k-1]; pc[k-1] = t;
			t = bytes[k]; bytes[k] = bytes[k-1]; bytes[k-1] = t;
			t = blocks[k]; blocks[k] = blocks[k-1]; blocks[k-1] = t;
		}
	return n;
}

void *AW_TryMalloc (unsigned long size)
{
	void *p = fits (size) ? malloc (size) : NULL;
	owned_note (p, size, (unsigned long)__builtin_return_address (0));
	return p;
}

void *AW_TryCalloc (unsigned long count, unsigned long size)
{
	unsigned long total = count * size;
	void *p;
	if (size && total / size != count)
		return NULL;
	p = fits (total) ? calloc (count, size) : NULL;
	owned_note (p, total, (unsigned long)__builtin_return_address (0));
	return p;
}

void *AW_TryRealloc (void *old, unsigned long size)
{
	void *p = fits (size) ? realloc (old, size) : NULL;
	if (p)
	{
		owned_forget (old);
		owned_note (p, size, (unsigned long)__builtin_return_address (0));
	}
	return p;
}
#else
typedef int aw_tryalloc_host_unit;	/* elsewhere the header's macros are the C library's own */
#endif
