/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM model zone: non-moving memory for shared models and chunk data.
 *
 * Quake's Cache_* keeps loaded data across map changes with an LRU list, but
 * moves blocks (Cache_Move) when the Hunk grows, and brush models are full of
 * internal pointers. This zone keeps Cache_*'s interface and LRU policy on
 * Quake's Z_* allocation scheme instead: first fit, never moved, free
 * neighbours merged. Memory comes in banks (a block of the Hunk for the
 * current map, optional extra Fast RAM that survives map changes). Locked
 * blocks (in use by an active chunk, or being loaded) are never evicted.
 */
#ifndef CHIM_ZONE_H
#define CHIM_ZONE_H

/* The bank for the current map, the manual -chimcache bank, and the banks of
 * extra Fast RAM taken automatically at start-up (chim_world.c): one per
 * memory region, each under 2 GiB, so any amount of Fast RAM fits. */
#define CHIM_ZONE_BANKS	16

/* Block kinds; 0 is a free block. */
#define CHIM_KIND_INDEX		1	/* the current frame's chunk index */
#define CHIM_KIND_BUFFER	2	/* the loading buffer */
#define CHIM_KIND_MODEL		3	/* a shared model, id = model id */
#define CHIM_KIND_CHUNK		4	/* a chunk's placement catalogue, id = entry */
#define CHIM_KIND_TERRAIN	5	/* a chunk's terrain model, id = entry */
#define CHIM_KIND_TEXTURE	6	/* a shared texture, id = texture id */
#define CHIM_KIND_WORLD		7	/* the frame world pool (chim_graft.c) */
#define CHIM_KIND_STATIC	8	/* streamed statics: their list, and each sprite model (chim_statics.c) */
#define CHIM_KIND_PREFETCH	9	/* raw file bytes read ahead into spare Fast RAM (chim_prefetch.c) */
#define CHIM_KINDS			10

/* Like cache_user_t: data is cleared when the block is evicted or freed. */
typedef struct
{
	void	*data;
} chim_user_t;

typedef struct
{
	int		banks, blocks, locked, largest_free;
	/* Sums over all banks: unsigned long, banks together may pass 2 GiB. */
	unsigned long	used_bytes, free_bytes;
	int		kind_blocks[CHIM_KINDS];
	unsigned long	kind_bytes[CHIM_KINDS];
	long	locked_bytes, locked_peak;		/* bytes of locked blocks now, most since ChimZone_LockedPeak */
	unsigned long	allocations, evictions, failures, trims;
} chim_zone_stats_t;

void ChimZone_Reset (void);
int ChimZone_AddBank (void *base, int size, int persistent);
void ChimZone_DropBank (int bank);
void ChimZone_DropTransient (void);
int ChimZone_BankBytes (int bank);
int ChimZone_BankUsed (int bank);
int ChimZone_HasFree (int bytes);

/* Automatic extra memory (chim_world.c, at start-up; docs/REAL_HARDWARE.md).
 * The margin left to the system: 2 MiB plus an eighth of all Fast RAM. The
 * budget: the free Fast RAM beyond that margin. Each step takes one bank from
 * the largest free block (the first leaves 2 MiB of its block), whole MiB,
 * under 2 GiB, at least CHIM_AUTO_FIRST for the first bank and
 * CHIM_AUTO_NEXT for the others; 0 ends. A 16 MiB Fast RAM machine with the
 * 11 MiB heap never reaches a first bank: it plays as without the feature.
 * The first bank's least was 8 MiB until v0.0.51: the v0.0.50 build left 13
 * MiB free on 32 MiB, a 7 MiB budget, so 32 MiB got no bank at all and
 * Akulakhan's Chamber (10.1 MiB of models) did not load (CHIM-AUTO-BANK-
 * CLIFF-51). The look-ahead keeps its 8 MiB step (ChimZone_AutoLookahead). */
#define CHIM_AUTO_MIB		1048576UL
#define CHIM_AUTO_FLOOR		(2UL*CHIM_AUTO_MIB)
#define CHIM_AUTO_KEEP		(2UL*CHIM_AUTO_MIB)
#define CHIM_AUTO_FIRST		(4UL*CHIM_AUTO_MIB)
#define CHIM_AUTO_NEXT		(4UL*CHIM_AUTO_MIB)
#define CHIM_AUTO_BANK_MAX	(2047UL*CHIM_AUTO_MIB)
unsigned long ChimZone_AutoMargin (unsigned long total);
unsigned long ChimZone_AutoBudget (unsigned long free_bytes, unsigned long total);
unsigned long ChimZone_AutoStep (unsigned long largest, unsigned long *budget, int first);
int ChimZone_AutoLookahead (unsigned long auto_bytes);

/* A CHIM room map holds nothing but its room (ROOM-AKULAKHAN-HEAP-52): when
 * its models and textures do not fit the map's zone and the cache banks, the
 * room takes, under the loading plaque, one more bank of the Fast RAM still
 * free (the largest block less CHIM_ROOM_KEEP, in CHIM_ROOM_GRAIN steps, at
 * least CHIM_ROOM_LEAST), then the rest of the Hunk the whole-map rule leaves
 * (chim_world.c Chim_RoomGrow); both go back at the next map. Rooms that fit
 * take neither. 0: no step. The grain was a whole MiB until v0.0.52, which
 * left up to 1023 KiB of the block unused: after Balmora at 32 MB Akulakhan's
 * Chamber took 3 MiB of a block just short of 6 MiB and had 420 KiB to spare
 * (CHIM-ROOM-HEART-CHAMBER-LOAD-50). */
#define CHIM_ROOM_KEEP		(2UL*CHIM_AUTO_MIB)
#define CHIM_ROOM_LEAST		(1UL*CHIM_AUTO_MIB)
#define CHIM_ROOM_GRAIN		65536
#define CHIM_ROOM_HUNK_LEAST	65536
/* What a room taking the Hunk's rest leaves for what its map loads after the
 * zone (its entities, the client's per-map allocations) when the map states
 * less: the measured 1,589,344 bytes (tools/engine_limits.py MEASURED_HUNK),
 * in KiB, rounded up. */
#define CHIM_ROOM_REST_KIB	1553
unsigned long ChimZone_RoomStep (unsigned long largest);

void *ChimZone_Alloc (chim_user_t *user, int size, int kind, unsigned id);
/* Only from banks that survive a map change (none: NULL, nothing evicted
 * elsewhere); for the prefetch and what it keeps across maps. */
void *ChimZone_AllocPersistent (chim_user_t *user, int size, int kind, unsigned id);
int ChimZone_PersistentBytes (void);
void *ChimZone_Check (chim_user_t *user);
void ChimZone_Free (chim_user_t *user);
void ChimZone_FreeData (void *data);
void ChimZone_Trim (void *data, int size);
void ChimZone_Lock (void *data);
void ChimZone_Unlock (void *data);
int ChimZone_Locks (const void *data);
int ChimZone_Size (const void *data);
void *ChimZone_Find (int kind, unsigned id);
void ChimZone_Touch (void *data);
int ChimZone_Persistent (const void *data);
void ChimZone_EvictKind (int kind, int (*keep)(void *data, unsigned id));
void ChimZone_SetEvict (int kind, void (*evicted)(void *data, unsigned id));
void ChimZone_ForEach (int kind, void (*visit)(void *data, unsigned id));
void ChimZone_Stats (chim_zone_stats_t *stats);
/* The failed request BACK steps before the last (0: the last): its kind, id and size; 0 when there is none. The
 * chim command names them (CHIM-ROOM-HEART-CHAMBER-LOAD-50). */
#define CHIM_ZONE_FAILED	8
int ChimZone_Failed (int back, int *kind, unsigned *id, int *size);
long ChimZone_LockedPeak (int which, int reset);
int ChimZone_Check_Integrity (void);
unsigned long ChimZone_Failures (int *last_need);
int ChimZone_LargestUnlocked (void);
int ChimZone_FitsWithout (int need, void **unlock, int n);
unsigned long ChimZone_Unsatisfiable (void);
void ChimZone_Map (void (*print)(const char *line));
void ChimZone_SetEnds (int small);

#endif
