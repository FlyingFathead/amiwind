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

#define CHIM_ZONE_BANKS	4

/* Block kinds; 0 is a free block. */
#define CHIM_KIND_INDEX		1	/* the current frame's chunk index */
#define CHIM_KIND_BUFFER	2	/* the loading buffer */
#define CHIM_KIND_MODEL		3	/* a shared model, id = model id */
#define CHIM_KIND_CHUNK		4	/* a chunk's placement catalogue, id = entry */
#define CHIM_KIND_TERRAIN	5	/* a chunk's terrain model, id = entry */
#define CHIM_KIND_TEXTURE	6	/* a shared texture, id = texture id */
#define CHIM_KIND_WORLD		7	/* the frame world pool (chim_graft.c) */
#define CHIM_KIND_STATIC	8	/* streamed statics: their list, and each sprite model (chim_statics.c) */
#define CHIM_KINDS			9

/* Like cache_user_t: data is cleared when the block is evicted or freed. */
typedef struct
{
	void	*data;
} chim_user_t;

typedef struct
{
	int		banks, blocks, locked, used_bytes, free_bytes, largest_free;
	int		kind_blocks[CHIM_KINDS], kind_bytes[CHIM_KINDS];
	long	locked_bytes, locked_peak;		/* bytes of locked blocks now, most since ChimZone_LockedPeak */
	unsigned long	allocations, evictions, failures, trims;
} chim_zone_stats_t;

void ChimZone_Reset (void);
int ChimZone_AddBank (void *base, int size, int persistent);
void ChimZone_DropBank (int bank);
void ChimZone_DropTransient (void);
int ChimZone_BankBytes (int bank);

void *ChimZone_Alloc (chim_user_t *user, int size, int kind, unsigned id);
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
long ChimZone_LockedPeak (int which, int reset);
int ChimZone_Check_Integrity (void);
unsigned long ChimZone_Failures (int *last_need);
int ChimZone_LargestUnlocked (void);
unsigned long ChimZone_Unsatisfiable (void);
void ChimZone_Map (void (*print)(const char *line));
void ChimZone_SetEnds (int small);

#endif
