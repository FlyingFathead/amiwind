/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_tryalloc.h: allocations that can say no (SKEL-16MB-TRAP-52, SDK-MALLOC-TRAPS-52).
 *
 * The toolchain's malloc never returns NULL: its allocator (libc malloc.o, MemMap::alloc) asks exec with
 * AllocMem(size + 4) for a request over 32,747 bytes, and for 32,760-byte pool blocks below that; when AllocMem
 * returns NULL it stores through it, and the compiler made that path a TRAP #7 (Software Failure #80000027). On the
 * Amiga these ask only when exec's largest free block holds what the allocator will ask for, plus a spare, and
 * return NULL otherwise, as the callers expect (aw_tryalloc.c). Elsewhere (host tests) they are the C library's own.
 * free() releases what they return. Every engine allocation goes through them (tests/test_engine_allocations.py). */
#ifndef AW_TRYALLOC_H
#define AW_TRYALLOC_H

#include <stdlib.h>

#define AW_TRYALLOC_POOL	32747UL		/* larger requests get their own AllocMem (malloc.o MemMap::alloc) */
#define AW_TRYALLOC_BLOCK	32760UL		/* a smaller one may need a new pool block of this size */
#define AW_TRYALLOC_SPARE	16384UL		/* left free for exec and the C library's own buffers */

/* The target only: host tests compile Amiga files with -DAMIGA and stub headers, and link none of aw_tryalloc.c */
#if defined(AMIGA) && defined(__m68k__)
#define AW_TRYALLOC_CHECKED 1
/* The largest free block a request of SIZE bytes needs. */
unsigned long AW_TryAllocNeed (unsigned long size);
void *AW_TryMalloc (unsigned long size);
/* calloc's count x size, refused when it overflows */
void *AW_TryCalloc (unsigned long count, unsigned long size);
/* NULL leaves the old block as it was (realloc's own rule): the caller keeps and frees it */
void *AW_TryRealloc (void *old, unsigned long size);
#else
#define AW_TryMalloc(size)	malloc (size)
#define AW_TryCalloc(count, size)	calloc (count, size)
#define AW_TryRealloc(old, size)	realloc (old, size)
#endif

#endif
