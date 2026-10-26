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

void *AW_TryMalloc (unsigned long size)
{
	return fits (size) ? malloc (size) : NULL;
}

void *AW_TryCalloc (unsigned long count, unsigned long size)
{
	unsigned long total = count * size;
	if (size && total / size != count)
		return NULL;
	return fits (total) ? calloc (count, size) : NULL;
}

void *AW_TryRealloc (void *old, unsigned long size)
{
	return fits (size) ? realloc (old, size) : NULL;
}
#else
typedef int aw_tryalloc_host_unit;	/* elsewhere the header's macros are the C library's own */
#endif
