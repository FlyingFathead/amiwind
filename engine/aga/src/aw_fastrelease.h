/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_fastrelease.h: memory the session can make again, given back before a large block is sized from the free Fast
 * RAM (CHIM-ROOM-HEART-CHAMBER-LOAD-50, SKEL-ROOM-AFTER-TOWN-52).
 *
 * A releaser gives back what it holds and can rebuild on demand (the skeletal animation tables and posed frames:
 * aw_skel_release.c) and returns the bytes it freed. AW_FastReleaseAll runs every registered releaser, in the order
 * they registered, with one console line each (the bytes it says it gave back and exec's free Fast RAM before and
 * after, total and largest block), and returns the sum. It is called only where a large allocation is sized from
 * the free Fast RAM: the CHIM cache banks at start-up and -chimcache (chim_world.c Chim_MemoryStart, CacheBank) and a
 * room's growth (Chim_RoomGrow); never from a per-frame path. */
#ifndef AW_FASTRELEASE_H
#define AW_FASTRELEASE_H

#define AW_FAST_RELEASERS	8

typedef unsigned long (*aw_fast_release_t)(void);

/* NAME (kept, not copied) says what FN gives back. 1: registered (again: the same FN is kept once); 0: the table is
 * full. */
int AW_FastReleaseRegister (const char *name, aw_fast_release_t fn);
/* WHY names the caller on the console lines. Returns the bytes the releasers gave back. */
unsigned long AW_FastReleaseAll (const char *why);
int AW_FastReleasers (void);

#endif
