/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM prefetch into spare Fast RAM (engine/aga/src/chim/chim_prefetch.c) with
 * the real zone (chim_zone.c) and a synthetic file table of 5 x 5 cells, each
 * a frame directory and two sectors of known bytes:
 * - baseline: no bank that survives a map change (the 16 MiB machine): off,
 *   nothing allocated, nothing read, every read goes to the disk;
 * - the 2x2 block at the player's quadrant, the neighbour the player heads
 *   for first, then the current cell, then the rest of the 3x3 ring;
 * - hysteresis: the block moves only a margin past the midline; a corner and
 *   an edge walk do not swap it back and forth;
 * - reads served from RAM are byte-identical; a read with a block missing
 *   goes to the disk;
 * - a real allocation evicts read-ahead bytes before anything else;
 * - the budget holds; frames well past the ring are dropped to make room;
 * - turned off ("chim prefetch 0"): reads go to the disk again.
 */
#include <assert.h>
#include <stdarg.h>
#include "quakedef.h"
#include "chim/chim_local.h"

chim_world_t	chim_world;
chim_frame_state_t	chim_frame;

void Sys_Error (char *fmt, ...)
{
	va_list args;
	va_start (args, fmt); vfprintf (stderr, fmt, args); va_end (args); fputc ('\n', stderr);
	abort ();
}
void Con_Printf (char *fmt, ...)
{
	va_list args;
	va_start (args, fmt); vprintf (fmt, args); va_end (args);
}
void Cvar_RegisterVariable (cvar_t *v)
{
	v->value = (float)atof (v->string);
}
static double clock_now = 1;
double Sys_FloatTime (void)
{
	return clock_now;
}
int ChimModels_Busy (void)
{
	return 0;
}

#define GRID	5		/* cells -2..2 in x and y */
#define FILES	(GRID*GRID*3)
#define SECTOR	(40*1024)
#define FRAME	(6*1024)
static chim_file_row_t	rows[FILES];
static chim_pack_t		packs[FILES];
static unsigned long	disk_reads, disk_bytes;
static int				last_read_row = -1;

static unsigned char Byte (int row, long at)
{
	return (unsigned char)(row*31 + at*7 + (at >> 9));
}

chim_pack_t *Chim_File (int row)
{
	if (row < 0 || row >= FILES)
		return NULL;
	packs[row].file = (FILE *)1;	/* never used as a FILE here */
	packs[row].row = row;
	packs[row].bytes = rows[row].bytes;
	return &packs[row];
}

int Chim_PackReadRaw (chim_pack_t *pack, long offset, void *out, long bytes)
{
	long i;
	if (offset < 0 || bytes < 0 || offset + bytes > pack->bytes)
		return 0;
	for (i=0 ; i<bytes ; i++)
		((unsigned char *)out)[i] = Byte (pack->row, offset + i);
	disk_reads++;
	disk_bytes += (unsigned long)bytes;
	last_read_row = pack->row;
	return 1;
}

/* What Chim_PackRead does (chim_world.c): RAM first, then the disk. */
static int PackRead (int row, long offset, void *out, long bytes, int *from_ram)
{
	*from_ram = ChimPrefetch_Read (row, offset, out, bytes);
	return *from_ram || Chim_PackReadRaw (Chim_File (row), offset, out, bytes);
}

static void World (void)
{
	int i = 0, x, y, s;
	memset (rows, 0, sizeof(rows));
	for (y=-2 ; y<=2 ; y++)
		for (x=-2 ; x<=2 ; x++)
		{
			strcpy (rows[i].kind, "FRAM");
			rows[i].cx = (short)x;
			rows[i].cy = (short)y;
			rows[i].bytes = FRAME;
			i++;
			for (s=0 ; s<2 ; s++, i++)
			{
				strcpy (rows[i].kind, "SECT");
				rows[i].cx = (short)x;
				rows[i].cy = (short)y;
				rows[i].sector = (unsigned short)s;
				rows[i].bytes = SECTOR;
			}
		}
	assert (i == FILES);
	memset (&chim_world, 0, sizeof(chim_world));
	chim_world.file = rows;
	chim_world.files = FILES;
	memset (&chim_frame, 0, sizeof(chim_frame));
	chim_frame.count = 1;
	chim_frame.frame.centre[0] = chim_frame.frame.centre[1] = 0;
}

static int RowCell (int row, int *cx, int *cy)
{
	*cx = rows[row].cx;
	*cy = rows[row].cy;
	return 1;
}

/* A frame-local origin for an original-units position. */
static void At (float x, float y, vec3_t o)
{
	o[0] = x / 4;
	o[1] = y / 4;
	o[2] = 0;
}

static void Walk (float x0, float y0, float x1, float y1, int steps, int spare)
{
	vec3_t o;
	int i;
	for (i=0 ; i<=steps ; i++)
	{
		clock_now += .3;
		At (steps ? x0 + (x1 - x0)*i/steps : x1, steps ? y0 + (y1 - y0)*i/steps : y1, o);
		ChimPrefetch_Step (o, spare);
	}
}

static void Plan (char *out)
{
	int i, cx, cy, st;
	out[0] = 0;
	for (i=0 ; ChimPrefetch_Wanted (i, &cx, &cy, &st) ; i++)
		sprintf (out + strlen (out), "%s%d,%d", i ? " " : "", cx, cy);
}

/* The plan's 2x2 block as a set: its three neighbours and the current cell,
 * sorted (the order follows the heading and may change freely; the rest of
 * the ring follows the current cell). */
static int Cmp (const void *a, const void *b)
{
	return strcmp ((const char *)a, (const char *)b);
}
static void Set (char *out)
{
	char cell[16][16];
	int i, n, cx, cy, st;
	for (n=0 ; n<16 && ChimPrefetch_Wanted (n, &cx, &cy, &st) ; n++)
		sprintf (cell[n], "%d,%d", cx, cy);
	if (n > 4)
		n = 4;
	qsort (cell, n, 16, Cmp);
	out[0] = 0;
	for (i=0 ; i<n ; i++)
		sprintf (out + strlen (out), "%s ", cell[i]);
}


int main (void)
{
	static unsigned char transient[2*1024*1024], keep[4*1024*1024];
	unsigned char buf[70000], want[70000];
	char plan[256], plan2[256];
	int i, ram, blocks, cx, cy, swaps;
	long held, at;
	chim_user_t big = {0}, model = {0};

	setvbuf (stdout, NULL, _IONBF, 0);

	/* 1. The 16 MiB baseline: only the map's bank. Nothing runs. */
	ChimZone_Reset ();
	ChimPrefetch_Init ();
	World ();
	assert (ChimZone_AddBank (transient, sizeof(transient), 0) == 0);
	assert (!ChimPrefetch_Active ());
	Walk (8192*.8f, 8192*.8f, 8192*.9f, 8192*.9f, 20, 1);
	assert (disk_reads == 0 && !ChimPrefetch_Held (&blocks) && !blocks);
	assert (!ChimPrefetch_Wanted (0, &cx, &cy, &i));
	assert (PackRead (5, 100, buf, 1000, &ram) && !ram && disk_reads == 1);
	printf ("baseline ok\n");

	/* 2. Extra RAM: the 2x2 block at the NE corner of cell 0,0, heading
	 * north-east-north: 0,1 first, then 1,1 and 1,0, the cell itself, the ring. */
	ChimZone_Reset ();
	ChimPrefetch_Init ();
	World ();
	disk_reads = 0;
	assert (ChimZone_AddBank (transient, sizeof(transient), 0) == 0);
	assert (ChimZone_AddBank (keep, sizeof(keep), 1) == 1);
	assert (ChimPrefetch_Active ());
	assert (ChimZone_AllocPersistent (&model, 1000, CHIM_KIND_MODEL, 77));
	Walk (8192*.70f, 8192*.60f, 8192*.75f, 8192*.85f, 4, 0);
	Plan (plan);
	printf ("plan after the walk: %s\n", plan);
	/* heading north: 0,1 is entered first; the block's other two next (by
	 * distance: the ray misses both), then the cell itself */
	assert (!strncmp (plan, "0,1 1,0 1,1 0,0 ", 16) || !strncmp (plan, "0,1 1,1 1,0 0,0 ", 16));
	assert (strlen (plan) > 30);	/* the rest of the 3x3 ring */
	assert (disk_reads == 0);		/* not spare: nothing read */
	/* The first slice reads the first wanted cell's directory. */
	Walk (8192*.75f, 8192*.85f, 8192*.75f, 8192*.86f, 0, 1);
	assert (disk_reads >= 1 && RowCell (last_read_row, &cx, &cy) && cx == 0 && cy == 1);
	printf ("plan %s ok\n", plan);

	/* 3. Byte-identical reads from RAM; a missing block goes to the disk. */
	for (i=0 ; i<40 ; i++)
		Walk (8192*.75f, 8192*.86f, 8192*.75f, 8192*.86f, 0, 1);
	{
		int row = -1;
		for (i=0 ; i<FILES ; i++)
			if (rows[i].cx == 0 && rows[i].cy == 1 && !strcmp (rows[i].kind, "SECT"))
				row = i;
		for (at=0 ; at + 5000 <= SECTOR ; at += 4999)
		{
			unsigned long before = disk_reads;
			long k;
			assert (PackRead (row, at, buf, 5000, &ram));
			assert (ram && disk_reads == before);
			for (k=0 ; k<5000 ; k++)
				want[k] = Byte (row, at + k);
			assert (!memcmp (buf, want, 5000));
		}
	}
	/* A cell far outside the plan is on the disk only. */
	assert (PackRead (0, 0, buf, 100, &ram) && !ram);
	printf ("reads ok\n");

	/* 4. Hysteresis: back to just under the midline (inside the margin): the
	 * block stays; well past it: the block moves west/south. */
	Set (plan);
	Walk (8192*.75f, 8192*.86f, 8192*.45f, 8192*.45f, 6, 0);
	Set (plan2);
	assert (!strcmp (plan, plan2));
	Walk (8192*.45f, 8192*.45f, 8192*.30f, 8192*.30f, 6, 0);
	Set (plan2);
	/* the south-west block: its three neighbours lead the plan */
	assert (strcmp (plan, plan2));
	{
		char head[64];
		int k, sp = 0;
		for (k=0 ; plan2[k] && sp < 3 ; k++)
			sp += plan2[k] == ' ';
		memcpy (head, plan2, k);
		head[k] = 0;
		assert (strstr (head, "-1,0 ") && strstr (head, "0,-1 ") && strstr (head, "-1,-1 "));
	}
	/* A corner and an edge walk do not swap the block back and forth: around
	 * the corner of cells 0,0 / 1,0 / 0,1 / 1,1 within the margin. */
	Walk (8192*.30f, 8192*.30f, 8192*.95f, 8192*.95f, 10, 0);
	Set (plan);
	for (swaps=0, i=0 ; i<200 ; i++)
	{
		float a = (float)i * .7f, r = 8192*.06f;
		Walk (8192*.95f + r*(float)cos (a), 8192*.95f + r*(float)sin (a), 8192*.95f + r*(float)cos (a + .7f),
			8192*.95f + r*(float)sin (a + .7f), 1, 0);
		Set (plan2);
		swaps += strcmp (plan, plan2) != 0;
		strcpy (plan, plan2);
	}
	printf ("corner: %d plan changes in 200 steps on a corner\n", swaps);
	assert (swaps <= 8);
	for (swaps=0, i=0 ; i<100 ; i++)
	{
		Walk (8192*.10f + 80*i, 8192*.98f, 8192*.10f + 80*(i + 1), 8192*.98f, 1, 0);
		Set (plan2);
		swaps += strcmp (plan, plan2) != 0;
		strcpy (plan, plan2);
	}
	printf ("edge: %d plan changes walking 8000 units along an edge\n", swaps);
	assert (swaps <= 3);
	printf ("hysteresis ok\n");

	/* 5. A real load evicts read-ahead bytes first: an older model (taken
	 * before the read-ahead blocks, so below them in the bank) stays. */
	for (i=0 ; i<200 ; i++)
		Walk (8192*.95f, 8192*.95f, 8192*.95f, 8192*.95f, 0, 1);
	held = ChimPrefetch_Held (&blocks);
	assert (held > 0 && blocks > 0);
	{
		chim_zone_stats_t s;
		ChimZone_Stats (&s);
		/* the two banks' free bytes are not one run: ask for the persistent
		 * bank's free tail plus most of the read-ahead bytes */
		assert (ChimZone_Alloc (&big, (int)((long)s.free_bytes - (long)ChimZone_BankBytes (0) + held - blocks*64L - 8192),
			CHIM_KIND_MODEL, 78));
	}
	assert (model.data);		/* the older model was not thrown out */
	assert (ChimPrefetch_Held (&i) < held);
	ChimZone_Free (&big);
	printf ("evict first ok\n");

	/* 6. The budget holds (a quarter of the bank); far frames are dropped to
	 * make room for the new ones. */
	for (i=0 ; i<400 ; i++)
		Walk (8192*.95f, 8192*.95f, 8192*.95f, 8192*.95f, 0, 1);
	held = ChimPrefetch_Held (&blocks);
	assert (held <= (long)sizeof(keep)/4 + 32*1024);
	Walk (8192*.95f, 8192*.95f, -8192*1.5f, -8192*1.5f, 30, 0);
	for (i=0 ; i<400 ; i++)
		Walk (-8192*1.5f, -8192*1.5f, -8192*1.5f, -8192*1.5f, 0, 1);
	assert (ChimPrefetch_Held (&blocks) <= (long)sizeof(keep)/4 + 32*1024);
	printf ("budget ok: %ld bytes in %d blocks\n", ChimPrefetch_Held (&blocks), blocks);
	assert (ChimZone_Check_Integrity ());

	/* 6b. Standing still (no heading since the map started, then a fixed
	 * heading): no pass over the file table after the first plan. */
	{
		unsigned long before;
		ChimPrefetch_MapBegin ();
		Walk (8192*.30f, 8192*.30f, 8192*.30f, 8192*.30f, 0, 1);
		before = ChimPrefetch_Passes ();
		for (i=0 ; i<100 ; i++)
			Walk (8192*.30f, 8192*.30f, 8192*.30f, 8192*.30f, 0, 1);
		assert (ChimPrefetch_Passes () == before);
		/* a turn re-orders the same cells without a pass */
		Walk (8192*.30f, 8192*.30f, 8192*.36f, 8192*.30f, 3, 0);
		Walk (8192*.36f, 8192*.30f, 8192*.36f, 8192*.36f, 3, 0);
		assert (ChimPrefetch_Passes () == before);
		printf ("standing ok: %lu passes\n", before);
	}

	/* 7. Turned off: every read goes to the disk again. */
	ChimPrefetch_SetOn (0);
	assert (!ChimPrefetch_Active ());
	{
		unsigned long before = disk_reads;
		assert (PackRead (FILES - 1, 0, buf, 100, &ram) && !ram && disk_reads == before + 1);
	}
	ChimPrefetch_Report ();
	printf ("chim prefetch ok\n");
	return 0;
}
