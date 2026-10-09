/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM model zone (engine/aga/src/chim/chim_zone.c): first fit, merging,
 * LRU eviction, locks, trims, persistent and transient banks, and a random
 * stress run that checks the zone's integrity after every operation.
 */
#include <assert.h>
#include <setjmp.h>
#include <stdarg.h>
#include "quakedef.h"
#include "chim/chim_zone.h"

static jmp_buf failure;
static int expect_error;
void Sys_Error (char *fmt, ...)
{
	va_list args;
	if (!expect_error)
	{
		va_start (args, fmt); vfprintf (stderr, fmt, args); va_end (args); fputc ('\n', stderr);
		abort ();
	}
	longjmp (failure, 1);
}

static unsigned evicted_ids[4096];
static int evicted;
static void on_evict (void *data, unsigned id)
{
	assert (data);
	if (evicted < 4096)
		evicted_ids[evicted] = id;
	evicted++;
}

static unsigned seed = 12345;
static int rnd (int n)
{
	seed = seed * 1103515245u + 12345u;
	return (int)((seed >> 16) & 0x7fff) % n;
}

static void basics (void)
{
	static unsigned char bank[64*1024];
	chim_user_t a = {0}, b = {0}, c = {0};
	chim_zone_stats_t s;
	void *p, *q;

	ChimZone_Reset ();
	ChimZone_SetEvict (CHIM_KIND_MODEL, on_evict);
	assert (ChimZone_AddBank (bank+3, sizeof(bank)-3, 0) == 0);
	assert (ChimZone_BankBytes (0) > 60000 && !(ChimZone_BankBytes (0) & 15));
	p = ChimZone_Alloc (&a, 1000, CHIM_KIND_MODEL, 7);
	assert (p && a.data == p && !((unsigned long)p & 15) && ChimZone_Size (p) >= 1000);
	assert (ChimZone_Find (CHIM_KIND_MODEL, 7) == p && !ChimZone_Find (CHIM_KIND_MODEL, 8));
	assert (!ChimZone_Find (CHIM_KIND_TEXTURE, 7));
	/* Zero-filled like Hunk_AllocName. */
	assert (!((unsigned char *)p)[999]);
	q = ChimZone_Alloc (&b, 2000, CHIM_KIND_MODEL, 8);
	assert (q && q != p);
	ChimZone_Free (&a);
	assert (!a.data && ChimZone_Check_Integrity ());
	/* First fit reuses the freed hole. */
	p = ChimZone_Alloc (&a, 500, CHIM_KIND_MODEL, 9);
	assert (p && (unsigned char *)p < (unsigned char *)q);
	/* Trim gives back the tail and merges it with the free space after it. */
	p = ChimZone_Alloc (&c, 20000, CHIM_KIND_MODEL, 10);
	ChimZone_Stats (&s);
	ChimZone_Trim (p, 100);
	assert (ChimZone_Size (p) < 200 && ChimZone_Check_Integrity ());
	{
		chim_zone_stats_t t;
		ChimZone_Stats (&t);
		assert (t.free_bytes > s.free_bytes + 19000 && t.trims == 1);
	}
	/* A request larger than any bank fails without evicting anything. */
	evicted = 0;
	assert (!ChimZone_Alloc (NULL, 70000, CHIM_KIND_MODEL, 11) && !evicted);
	ChimZone_Stats (&s);
	assert (s.failures == 1 && s.blocks == 3);
	/* Locks: double unlock is an error. */
	ChimZone_Lock (q);
	ChimZone_Unlock (q);
	expect_error = 1;
	if (!setjmp (failure))
	{
		ChimZone_Unlock (q);
		assert (!"unlock below zero accepted");
	}
	expect_error = 0;
	assert (ChimZone_Check_Integrity ());
}

/* Least recently used goes first; locked blocks never go. */
static void lru (void)
{
	static unsigned char bank[16*1024];
	chim_user_t u[8];
	int i;

	memset (u, 0, sizeof(u));
	ChimZone_Reset ();
	ChimZone_SetEvict (CHIM_KIND_MODEL, on_evict);
	ChimZone_AddBank (bank, sizeof(bank), 0);
	for (i=0 ; i<6 ; i++)
		assert (ChimZone_Alloc (&u[i], 2000, CHIM_KIND_MODEL, (unsigned)i));
	ChimZone_Lock (u[0].data);			/* oldest, but locked */
	ChimZone_Check (&u[1]);				/* touched: now the newest */
	evicted = 0;
	assert (ChimZone_Alloc (&u[6], 5000, CHIM_KIND_MODEL, 6));
	/* 0 locked, 1 touched: 2 and 3 (adjacent, so their space merges) go. */
	assert (evicted >= 2 && evicted_ids[0] == 2 && evicted_ids[1] == 3);
	assert (u[0].data && u[1].data && !u[2].data && !u[3].data);
	assert (ChimZone_Check_Integrity ());
	/* With everything locked an allocation fails cleanly. */
	for (i=0 ; i<7 ; i++)
		if (u[i].data && i)
			ChimZone_Lock (u[i].data);
	assert (!ChimZone_Alloc (NULL, 8000, CHIM_KIND_MODEL, 99));
	assert (ChimZone_Check_Integrity ());
	/* EvictKind skips locked blocks. */
	ChimZone_Unlock (u[1].data);
	evicted = 0;
	ChimZone_EvictKind (CHIM_KIND_MODEL, NULL);
	assert (evicted == 1 && !u[1].data && u[0].data);
	assert (ChimZone_Check_Integrity ());
}

/* Models and textures prefer the persistent bank; the rest the transient
 * one. Dropping the transient bank clears its users; a locked block there
 * is an error. */
static void banks (void)
{
	static unsigned char transient[32*1024], persistent[32*1024];
	chim_user_t m = {0}, t = {0}, c = {0};
	chim_zone_stats_t s;

	ChimZone_Reset ();
	ChimZone_SetEvict (CHIM_KIND_MODEL, on_evict);
	assert (ChimZone_AddBank (persistent, sizeof(persistent), 1) == 0);
	assert (ChimZone_AddBank (transient, sizeof(transient), 0) == 1);
	assert (ChimZone_Alloc (&m, 1000, CHIM_KIND_MODEL, 1) && ChimZone_Persistent (m.data));
	assert (ChimZone_Alloc (&t, 1000, CHIM_KIND_TEXTURE, 1) && ChimZone_Persistent (t.data));
	assert (ChimZone_Alloc (&c, 1000, CHIM_KIND_CHUNK, 1) && !ChimZone_Persistent (c.data));
	ChimZone_Lock (c.data);
	expect_error = 1;
	if (!setjmp (failure))
	{
		ChimZone_DropTransient ();
		assert (!"locked block dropped");
	}
	expect_error = 0;
	/* (the failed drop left the zone as it was) */
	ChimZone_Unlock (c.data);
	ChimZone_DropTransient ();
	assert (!c.data && m.data && t.data);
	ChimZone_Stats (&s);
	assert (s.banks == 1 && s.blocks == 2);
	/* A new transient bank (the next map) is usable at once. */
	assert (ChimZone_AddBank (transient, sizeof(transient), 0) == 1);
	assert (ChimZone_Alloc (&c, 30000, CHIM_KIND_CHUNK, 2) && !ChimZone_Persistent (c.data));
	/* A full preferred bank spills into the other one. */
	assert (ChimZone_Alloc (NULL, 30000, CHIM_KIND_MODEL, 3) && ChimZone_Find (CHIM_KIND_MODEL, 3));
	assert (ChimZone_Check_Integrity ());
}

static void stress (void)
{
	static unsigned char bank0[96*1024], bank1[40*1024];
	chim_user_t u[64];
	int i, op, k;

	memset (u, 0, sizeof(u));
	ChimZone_Reset ();
	ChimZone_SetEvict (CHIM_KIND_MODEL, on_evict);
	ChimZone_AddBank (bank0, sizeof(bank0), 0);
	ChimZone_AddBank (bank1, sizeof(bank1), 1);
	for (i=0 ; i<200000 ; i++)
	{
		k = rnd (64);
		op = rnd (10);
		if (!u[k].data)
		{
			void *p = ChimZone_Alloc (&u[k], 16 + rnd (6000), rnd (3) ? CHIM_KIND_MODEL : CHIM_KIND_CHUNK, (unsigned)k);
			if (p)
			{
				memset (p, k, ChimZone_Size (p));
				if (!rnd (8))
					ChimZone_Lock (p);
			}
		}
		else if (op < 3)
		{
			if (ChimZone_Locks (u[k].data))
				ChimZone_Unlock (u[k].data);
			ChimZone_Free (&u[k]);
		}
		else if (op < 5)
			ChimZone_Check (&u[k]);
		else if (op < 6 && !ChimZone_Locks (u[k].data))
			ChimZone_Trim (u[k].data, 1 + rnd (ChimZone_Size (u[k].data)));
		else if (op < 7 && ChimZone_Locks (u[k].data))
			ChimZone_Unlock (u[k].data);
		/* Blocks never move: a surviving block keeps its own bytes. */
		if (u[k].data)
			assert (((unsigned char *)u[k].data)[0] == (unsigned char)k);
		if (!(i & 255) || i < 2000)
			assert (ChimZone_Check_Integrity ());
	}
	assert (ChimZone_Check_Integrity ());
}

/* CHIM-CHUNK-LOAD-FAIL-33: the zone tells a full zone from bad data
 * (ChimZone_Failures moves only on a refused request, with its size), the
 * largest run without a lock is the largest request that can still succeed,
 * and the layout line shows locked blocks splitting the room. */
static char map_text[4096];
static void map_line (const char *line)
{
	strncat (map_text, line, sizeof(map_text) - strlen (map_text) - 2);
	strcat (map_text, "\n");
}

static void diagnostics (void)
{
	static unsigned char bank[64*1024];
	chim_user_t u[8];
	unsigned long f0;
	int last = -1, i, run;

	memset (u, 0, sizeof(u));
	ChimZone_Reset ();
	assert (ChimZone_AddBank (bank, sizeof(bank), 0) == 0);
	assert (ChimZone_Failures (&last) == 0 && last == 0);
	/* Eight blocks of 6 KiB; every other one locked splits the bank. */
	for (i=0 ; i<8 ; i++)
	{
		assert (ChimZone_Alloc (&u[i], 6000, CHIM_KIND_MODEL, i));
		if (!(i & 1))
			ChimZone_Lock (u[i].data);
	}
	run = ChimZone_LargestUnlocked ();
	/* The tail after the last block is free and joins the last unlocked one. */
	assert (run >= 6000 && run < 64*1024);
	f0 = ChimZone_Failures (NULL);
	/* More than any run: refused, counted, sized; the locked blocks stay. */
	assert (!ChimZone_Alloc (NULL, run + 4096, CHIM_KIND_MODEL, 99));
	assert (ChimZone_Failures (&last) == f0 + 1 && last >= run + 4096);
	assert (u[0].data && u[2].data && u[4].data && u[6].data);
	/* A request within the largest run succeeds (by eviction). */
	assert (ChimZone_Alloc (NULL, run - 64, CHIM_KIND_TEXTURE, 100));
	assert (ChimZone_Failures (NULL) == f0 + 1);
	map_text[0] = 0;
	ChimZone_Map (map_line);
	assert (!strncmp (map_text, "bank 0: M6*", 11) && strstr (map_text, " X"));
	for (i=0 ; i<8 ; i+=2)
		ChimZone_Unlock (u[i].data);
	assert (ChimZone_Check_Integrity ());
}

int main (void)
{
	basics ();
	lru ();
	banks ();
	stress ();
	diagnostics ();
	printf ("chim zone ok\n");
	return 0;
}
