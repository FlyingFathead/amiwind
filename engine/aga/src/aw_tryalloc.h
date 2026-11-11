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
/* ROOM-LOAD-KEEPS-EXTERIOR-CACHE-64: the count by asking address. Every block of AW_TRYALLOC_OWNED bytes or more that these
 * allocate is noted with the address it was asked from; free() in a file that includes this header goes through
 * AW_TryFree, which forgets it (the C library's own blocks are never in the table, so they are freed as before).
 * aw_memcensus owners prints the live bytes by asking address (tools map it to a function by the link map). */
#define AW_TRYALLOC_OWNED	(4UL * 1024UL)	/* 4 KiB, a size in bytes (no coordinate) */
/* The count is off by default: nothing is noted and free() only tests a flag. ON 1 starts it (aw_memcensus owners
 * on, a measuring session), 0 stops it and forgets the table. */
void AW_TryOwnersEnable (int on);
int AW_TryOwnersOn (void);
void AW_TryFree (void *block);
/* The live owned blocks summed by asking address, largest first: up to MAX (pc, bytes, blocks); returns the count,
 * *total the live owned bytes, *dropped the blocks the full table could not note (counted, never lost). */
int AW_TryOwners (unsigned long *pc, unsigned long *bytes, unsigned long *blocks, int max, unsigned long *total,
	unsigned long *dropped);
#define free(block)	AW_TryFree (block)
#else
#define AW_TryMalloc(size)	malloc (size)
#define AW_TryCalloc(count, size)	calloc (count, size)
#define AW_TryRealloc(old, size)	realloc (old, size)
#endif

/* A growing allocation's worst case for the resident registry (tools/resident_registry.py, the growing group):
 * NAME, at most MAX entries of BYTES each. Generates nothing but a declaration. */
#define AW_RESIDENT_GROWS(name,max,bytes) extern int aw_resident_grows_declared

#endif
