/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM model zone (chim_zone.h). Allocation follows Quake's Z_TagMalloc
 * (zone.c): blocks tile each bank with no gaps and free neighbours are merged.
 * The policy follows Cache_Alloc / Cache_Check (zone.c): an LRU list of used
 * blocks, the least recently used unlocked block is evicted until a request
 * fits, and the owner's chim_user_t is cleared like a cache_user_t. Unlike the
 * Cache, nothing ever moves, so brush models keep their internal pointers.
 */
#include "quakedef.h"
#include "chim_zone.h"

typedef struct chim_block_s
{
	int		size;			/* including the header; a multiple of 16 */
	unsigned char	kind, bank;
	short	locks;
	unsigned	id;
	chim_user_t	*user;
	struct chim_block_s	*prev, *next;		/* address order within the bank */
	struct chim_block_s	*lru_prev, *lru_next;	/* used blocks only */
} chim_block_t;

#define CHIM_HEADER	((int)((sizeof(chim_block_t)+15)&~15))
#define CHIM_MIN_SPLIT	(CHIM_HEADER+16)
#define CHIM_DATA(b)	((void *)((byte *)(b)+CHIM_HEADER))

typedef struct
{
	chim_block_t	*first;
	int		size, persistent;
} chim_bank_t;

static chim_bank_t	banks[CHIM_ZONE_BANKS];
static int			numbanks;
static chim_block_t	lru;		/* sentinel: lru.lru_next is the most recent */
static void			(*evict_callbacks[CHIM_KINDS])(void *data, unsigned id);
static unsigned long	allocations, evictions, failures, trims;
static int			last_failed_need;	/* the last failed request, header included */
static int			small_high;		/* ChimZone_SetEnds: blocks below this size come from the high end */

static chim_block_t *Block (const void *data)
{
	chim_block_t *b;
	if (!data)
		Sys_Error ("CHIM zone: NULL block");
	b = (chim_block_t *)((byte *)data - CHIM_HEADER);
	if (!b->kind || b->bank >= numbanks)
		Sys_Error ("CHIM zone: not an allocated block");
	return b;
}

static void UnlinkLRU (chim_block_t *b)
{
	b->lru_prev->lru_next = b->lru_next;
	b->lru_next->lru_prev = b->lru_prev;
	b->lru_prev = b->lru_next = NULL;
}

static void MakeLRU (chim_block_t *b)
{
	b->lru_next = lru.lru_next;
	b->lru_prev = &lru;
	lru.lru_next->lru_prev = b;
	lru.lru_next = b;
}

/* Bytes of locked blocks (in use: the active ring's models, terrain and
 * catalogues, the frame-world pool, the loading buffer, the index): what a
 * map cannot do without, as against the cache of unlocked blocks. Peaks
 * since the last rcount line (0) and since the map started (1). */
static long	locked_bytes, locked_peak[2];

static void LockedBytes (long delta)
{
	int k;
	locked_bytes += delta;
	for (k=0 ; k<2 ; k++)
		if (locked_bytes > locked_peak[k])
			locked_peak[k] = locked_bytes;
}

long ChimZone_LockedPeak (int which, int reset)
{
	long peak = locked_peak[which];
	if (reset)
		locked_peak[which] = locked_bytes;
	return peak;
}

void ChimZone_Reset (void)
{
	memset (banks, 0, sizeof(banks));
	locked_bytes = locked_peak[0] = locked_peak[1] = 0;
	numbanks = 0;
	lru.lru_next = lru.lru_prev = &lru;
	allocations = evictions = failures = trims = 0;
	last_failed_need = 0;
}

int ChimZone_AddBank (void *base, int size, int persistent)
{
	chim_block_t *b;
	byte *start;
	int i;

	if (!lru.lru_next)
		ChimZone_Reset ();
	if (!base)
		return -1;
	start = (byte *)(((unsigned long)base + 15) & ~15UL);
	size -= (int)(start - (byte *)base);
	size &= ~15;
	if (size < CHIM_MIN_SPLIT)
		return -1;
	for (i=0 ; i<numbanks ; i++)
		if (!banks[i].first)
			break;
	if (i == CHIM_ZONE_BANKS)
		return -1;
	b = (chim_block_t *)start;
	memset (b, 0, sizeof(*b));
	b->size = size;
	b->bank = (unsigned char)i;
	banks[i].first = b;
	banks[i].size = size;
	banks[i].persistent = persistent != 0;
	if (i == numbanks)
		numbanks++;
	return i;
}

int ChimZone_BankBytes (int bank)
{
	return bank >= 0 && bank < numbanks && banks[bank].first ? banks[bank].size : 0;
}

/* Merge b with a free successor; b must be free. */
static void MergeNext (chim_block_t *b)
{
	chim_block_t *n = b->next;
	if (n && !n->kind)
	{
		b->size += n->size;
		b->next = n->next;
		if (n->next)
			n->next->prev = b;
	}
}

static void Release (chim_block_t *b)
{
	chim_block_t *p;
	if (b->user)
		b->user->data = NULL;
	UnlinkLRU (b);
	b->kind = 0; b->locks = 0; b->id = 0; b->user = NULL;
	MergeNext (b);
	p = b->prev;
	if (p && !p->kind)
		MergeNext (p);
}

static void Evict (chim_block_t *b)
{
	if (b->locks)
		Sys_Error ("CHIM zone: evicting a locked block");
	if (evict_callbacks[b->kind])
		evict_callbacks[b->kind] (CHIM_DATA(b), b->id);
	evictions++;
	Release (b);
}

/* Small blocks from the bank's high end (ChimZone_SetEnds): the highest
 * free block that holds need, cut from its top. */
static chim_block_t *TryHigh (int bank, int need)
{
	chim_block_t *b, *best = NULL, *top;
	for (b=banks[bank].first ; b ; b=b->next)
		if (!b->kind && b->size >= need)
			best = b;
	if (!best || best->size - need < CHIM_MIN_SPLIT)
		return best;
	top = (chim_block_t *)((byte *)best + best->size - need);
	memset (top, 0, sizeof(*top));
	top->size = need;
	top->bank = best->bank;
	top->prev = best;
	top->next = best->next;
	if (best->next)
		best->next->prev = top;
	best->next = top;
	best->size -= need;
	return top;
}

/* Quake's Hunk keeps a low and a high end so that data of different
 * lifetimes do not interleave. With ends set, blocks smaller than small
 * bytes (textures, chunk catalogues and terrain, small models) are taken
 * from the high end of a bank and larger ones first fit from the low end,
 * so small locked blocks do not split the room large models need
 * (CHIM-CHUNK-LOAD-FAIL-33). 0: first fit for every block (the first
 * method). */
void ChimZone_SetEnds (int small)
{
	small_high = small > 0 ? small : 0;
}

/* First fit: in the preferred banks first, then in the others. */
static chim_block_t *TryAlloc (int need, int persistent)
{
	int pass, i;
	chim_block_t *b, *rest;

	for (pass=0 ; pass<2 ; pass++)
		for (i=0 ; i<numbanks ; i++)
		{
			if (!banks[i].first || (banks[i].persistent == persistent) != !pass)
				continue;
			if (need < small_high)
			{
				if ((b = TryHigh (i, need)) != NULL)
					return b;
				continue;
			}
			for (b=banks[i].first ; b ; b=b->next)
			{
				if (b->kind || b->size < need)
					continue;
				if (b->size - need >= CHIM_MIN_SPLIT)
				{
					rest = (chim_block_t *)((byte *)b + need);
					memset (rest, 0, sizeof(*rest));
					rest->size = b->size - need;
					rest->bank = b->bank;
					rest->prev = b;
					rest->next = b->next;
					if (b->next)
						b->next->prev = rest;
					b->next = rest;
					b->size = need;
				}
				return b;
			}
		}
	return NULL;
}

void *ChimZone_Alloc (chim_user_t *user, int size, int kind, unsigned id)
{
	chim_block_t *b;
	int need, i, largest = 0, persistent;

	if (kind <= 0 || kind >= CHIM_KINDS || size < 0 || size > 0x7fffffff - 2*CHIM_HEADER)
		Sys_Error ("CHIM zone: bad allocation");
	if (user && user->data)
		Sys_Error ("CHIM zone: already allocated");
	need = CHIM_HEADER + ((size + 15) & ~15);
	for (i=0 ; i<numbanks ; i++)
		if (banks[i].first && banks[i].size > largest)
			largest = banks[i].size;
	/* Shared models and textures prefer memory that survives a map change. */
	persistent = kind == CHIM_KIND_MODEL || kind == CHIM_KIND_TEXTURE;
	while (need <= largest)
	{
		b = TryAlloc (need, persistent);
		if (b)
		{
			b->kind = (unsigned char)kind;
			b->id = id;
			b->locks = 0;
			b->user = user;
			MakeLRU (b);
			memset (CHIM_DATA(b), 0, b->size - CHIM_HEADER);
			if (user)
				user->data = CHIM_DATA(b);
			allocations++;
			return CHIM_DATA(b);
		}
		/* Evict the least recently used unlocked block and retry. */
		for (b=lru.lru_prev ; b != &lru && b->locks ; b=b->lru_prev)
			;
		if (b == &lru)
			break;
		Evict (b);
	}
	failures++;
	last_failed_need = need;
	return NULL;
}

/* Failed requests so far, and the size (header included) of the last:
 * the caller tells a full zone from bad data by the count moving. */
unsigned long ChimZone_Failures (int *last_need)
{
	if (last_need)
		*last_need = last_failed_need;
	return failures;
}

/* The largest run of adjacent unlocked blocks (free or evictable): the
 * largest request that can succeed without unlocking anything. */
int ChimZone_LargestUnlocked (void)
{
	chim_block_t *b;
	int i, run, best = 0;
	for (i=0 ; i<numbanks ; i++)
		for (run=0, b=banks[i].first ; b ; b=b->next)
		{
			run = b->locks ? 0 : run + b->size;
			if (run > best)
				best = run;
		}
	return best > CHIM_HEADER ? best - CHIM_HEADER : 0;
}

/* The bank's layout for the console (the first failed request of a map,
 * all of them with chim_debug): one entry per block in address order, kind
 * letter (. free, I index, B buffer, M model, C chunk, T terrain, X
 * texture, W frame world), size in KiB, '*' when locked. */
void ChimZone_Map (void (*print)(const char *line))
{
	static const char letters[] = ".IBMCTXWS";
	char line[96];
	chim_block_t *b;
	int i, n;
	for (i=0 ; i<numbanks ; i++)
	{
		if (!banks[i].first)
			continue;
		n = sprintf (line, "bank %d:", i);
		for (b=banks[i].first ; b ; b=b->next)
		{
			if (n > 80)
			{
				print (line);
				n = sprintf (line, "  ");
			}
			n += sprintf (line + n, " %c%d%s", letters[b->kind < CHIM_KINDS ? b->kind : 0], (b->size + 1023) / 1024,
				b->locks ? "*" : "");
		}
		print (line);
	}
}

void *ChimZone_Check (chim_user_t *user)
{
	if (!user || !user->data)
		return NULL;
	ChimZone_Touch (user->data);
	return user->data;
}

void ChimZone_Touch (void *data)
{
	chim_block_t *b = Block (data);
	UnlinkLRU (b);
	MakeLRU (b);
}

void ChimZone_Free (chim_user_t *user)
{
	if (!user || !user->data)
		Sys_Error ("CHIM zone: free of an unallocated user");
	ChimZone_FreeData (user->data);
}

/* Freeing on purpose: no eviction callback. Locks are the caller's. */
void ChimZone_FreeData (void *data)
{
	chim_block_t *b = Block (data);
	if (b->locks)
		LockedBytes (-b->size);
	Release (b);
}

void ChimZone_Trim (void *data, int size)
{
	chim_block_t *b = Block (data), *rest;
	int need = CHIM_HEADER + ((size + 15) & ~15);

	if (size < 0 || need > b->size)
		Sys_Error ("CHIM zone: bad trim");
	if (b->size - need < CHIM_MIN_SPLIT)
		return;
	rest = (chim_block_t *)((byte *)b + need);
	memset (rest, 0, sizeof(*rest));
	rest->size = b->size - need;
	rest->bank = b->bank;
	rest->prev = b;
	rest->next = b->next;
	if (b->next)
		b->next->prev = rest;
	b->next = rest;
	if (b->locks)
		LockedBytes (need - b->size);
	b->size = need;
	MergeNext (rest);
	trims++;
}

void ChimZone_Lock (void *data)
{
	chim_block_t *b = Block (data);
	if (b->locks == 32767)
		Sys_Error ("CHIM zone: lock overflow");
	if (!b->locks++)
		LockedBytes (b->size);
}

void ChimZone_Unlock (void *data)
{
	chim_block_t *b = Block (data);
	if (b->locks <= 0)
		Sys_Error ("CHIM zone: unlock of an unlocked block");
	if (!--b->locks)
		LockedBytes (-b->size);
}

int ChimZone_Locks (const void *data)
{
	return Block (data)->locks;
}

int ChimZone_Size (const void *data)
{
	return Block (data)->size - CHIM_HEADER;
}

void *ChimZone_Find (int kind, unsigned id)
{
	chim_block_t *b;
	for (b=lru.lru_next ; b && b != &lru ; b=b->lru_next)
		if (b->kind == kind && b->id == id)
			return CHIM_DATA(b);
	return NULL;
}

int ChimZone_Persistent (const void *data)
{
	return banks[Block (data)->bank].persistent;
}

/* Evict every unlocked block of a kind that keep() does not keep. */
void ChimZone_EvictKind (int kind, int (*keep)(void *data, unsigned id))
{
	chim_block_t *b, *next;
	for (b=lru.lru_next ; b && b != &lru ; b=next)
	{
		next = b->lru_next;
		if (b->kind != kind || b->locks || (keep && keep (CHIM_DATA(b), b->id)))
			continue;
		Evict (b);
		next = lru.lru_next;	/* the callback may have freed others */
	}
}

void ChimZone_ForEach (int kind, void (*visit)(void *data, unsigned id))
{
	chim_block_t *b;
	for (b=lru.lru_next ; b && b != &lru ; b=b->lru_next)
		if (b->kind == kind)
			visit (CHIM_DATA(b), b->id);
}

void ChimZone_SetEvict (int kind, void (*evicted)(void *data, unsigned id))
{
	if (kind > 0 && kind < CHIM_KINDS)
		evict_callbacks[kind] = evicted;
}

/* Every block in the bank goes; a locked block there is a caller bug. */
void ChimZone_DropBank (int bank)
{
	chim_block_t *b, *next;
	if (bank < 0 || bank >= numbanks || !banks[bank].first)
		return;
	for (b=banks[bank].first ; b ; b=b->next)
		if (b->kind && b->locks)
			Sys_Error ("CHIM zone: dropping a bank with a locked block");
	for (b=banks[bank].first ; b ; b=next)
	{
		next = b->next;
		if (b->kind)
		{
			if (b->user)
				b->user->data = NULL;
			if (evict_callbacks[b->kind])
				evict_callbacks[b->kind] (CHIM_DATA(b), b->id);
			UnlinkLRU (b);
		}
	}
	memset (&banks[bank], 0, sizeof(banks[bank]));
	while (numbanks && !banks[numbanks-1].first)
		numbanks--;
}

void ChimZone_DropTransient (void)
{
	int i;
	for (i=0 ; i<numbanks ; i++)
		if (banks[i].first && !banks[i].persistent)
			ChimZone_DropBank (i);
}

void ChimZone_Stats (chim_zone_stats_t *s)
{
	chim_block_t *b;
	int i, data;

	memset (s, 0, sizeof(*s));
	for (i=0 ; i<numbanks ; i++)
	{
		if (!banks[i].first)
			continue;
		s->banks++;
		for (b=banks[i].first ; b ; b=b->next)
		{
			data = b->size - CHIM_HEADER;
			if (!b->kind)
			{
				s->free_bytes += b->size;
				if (data > s->largest_free)
					s->largest_free = data;
				continue;
			}
			s->blocks++;
			s->used_bytes += b->size;
			if (b->locks)
				s->locked++;
			s->kind_blocks[b->kind]++;
			s->kind_bytes[b->kind] += b->size;
		}
	}
	s->locked_bytes = locked_bytes;
	s->locked_peak = locked_peak[1];
	s->allocations = allocations; s->evictions = evictions;
	s->failures = failures; s->trims = trims;
}

/* Banks tiled exactly, no adjacent free blocks, LRU = the used blocks. */
int ChimZone_Check_Integrity (void)
{
	chim_block_t *b;
	int i, used = 0, listed = 0, total;

	for (i=0 ; i<numbanks ; i++)
	{
		if (!banks[i].first)
			continue;
		total = 0;
		for (b=banks[i].first ; b ; b=b->next)
		{
			if (b->size < CHIM_HEADER || (b->size & 15) || b->bank != i)
				return 0;
			if (b->next && ((byte *)b + b->size != (byte *)b->next || b->next->prev != b))
				return 0;
			if (!b->kind && b->next && !b->next->kind)
				return 0;
			if (b->kind)
			{
				used++;
				if (!b->lru_next || !b->lru_prev || (b->user && b->user->data != CHIM_DATA(b)))
					return 0;
			}
			total += b->size;
		}
		if (total != banks[i].size)
			return 0;
	}
	for (b=lru.lru_next ; b != &lru ; b=b->lru_next)
	{
		if (!b->kind || b->lru_next->lru_prev != b)
			return 0;
		listed++;
	}
	return listed == used;
}
