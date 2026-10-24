/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM prefetch into spare Fast RAM (CHIM-CROSSING-SYNC-LOAD-43).
 *
 * In the open world every exterior cell is its own CHIM frame map, so walking
 * over a cell border is a map change: the frame's directory and the chunks
 * around the arrival are read again, in many small reads (CHIM-READ-RUNS-33).
 * With extra Fast RAM (the zone's banks that survive a map change, chim_zone.h)
 * this module reads the files of the frames the player is likely to enter
 * next, a slice per frame while nothing else reads, into that RAM, and serves
 * later reads of the same bytes from it (Chim_PackRead). The bytes are the
 * same, so what is drawn and collided is the same; only the disk time moves
 * out of the crossing.
 *
 * Which frames (the maintainer's rule, 18 October 2026): the current cell is
 * split into four quadrants; the quadrant the player stands in names the
 * nearest corner, and the 2x2 block of cells meeting there (the current cell
 * and three neighbours) is read first, the neighbour the player heads for
 * first. The block moves to another corner only when the player is a margin
 * past the cell's midline (hysteresis: walking along an edge or standing on a
 * corner does not swap the block back and forth). With room to spare the
 * whole 3x3 ring around the player follows. Read-ahead bytes are dropped only
 * for frames more than half a cell beyond that ring, or first of everything
 * when a real load needs the memory (chim_zone.c Victim).
 *
 * Like Quake's Cache_* (zone.c): the blocks are an LRU cache that any real
 * allocation may evict; nothing waits for them. Off ("chim prefetch 0") or
 * without banks that survive a map change (the 16 MiB baseline), nothing here
 * runs and every read goes to the disk as before.
 *
 * The same spare RAM also keeps what every map of the world reads the same:
 * the decoded world index (chim_world.c ReadIndex) and each frame's placement
 * count (chim_chunks.c ChimChunks_Begin), so a crossing no longer reads and
 * decodes them again.
 */
#include "quakedef.h"
#include "chim_local.h"
#include "aw_spike.h"

/* The settings: "chim prefetch ..." (chim_world.c Status), not saved and no
 * registered cvars (tests/resident_registry_budget.json). */
static int	prefetch_on = 1;			/* 0: off, the first method */
static int	prefetch_mib = 24;			/* most bytes read ahead (also at most a quarter of the banks) */
static int	prefetch_kib = 32;			/* bytes read ahead per frame (one block at least) */
static int	prefetch_ring = 1;			/* 1: after the 2x2 block, the rest of the 3x3 ring */
static int	prefetch_margin = 1024;		/* units past the midline before the block moves */
#define FRAME_BYTES_MAX	(4L*1048576L)	/* frames larger than this are not read ahead */

#define CELL_UNITS		8192.0f		/* a Morrowind exterior cell, original units */
#define BLOCK_SHIFT		15
#define BLOCK_BYTES		(1L << BLOCK_SHIFT)	/* 32 KiB */
#define BLOCKS_PER_FILE	2048		/* files to 64 MiB; blocks past it are never cached */
#define SLOTS			(1 << 12)	/* hash table (a power of two) */
#define WANT			9			/* the 3x3 ring */
#define FRAME_FILES		48			/* files of one frame read ahead (its directory and sectors) */

typedef struct
{
	unsigned	id;			/* row * BLOCKS_PER_FILE + block, +1 (0: empty slot) */
	void		*data;
} slot_t;

typedef struct
{
	int		cx, cy;			/* the cell (= the region frame) */
	int		files, row[FRAME_FILES];
	int		file, block;	/* read cursor */
	int		done, skipped;	/* every block cached, or not read ahead (no frame, too large) */
	long	bytes;
} want_t;

static chim_user_t	table_user, owned_user;
static slot_t		*table;
static unsigned		*owned;			/* per file row: the frame's placement count, ~0 unknown */
static int			owned_rows;
static long			held;			/* bytes of blocks in the zone (headers excluded) */
static int			blocks;
static want_t		want[WANT];
static int			wants, side[2], have_side, cell[2] = {0x7fff, 0x7fff};
static float		last_pos[2], heading[2], plan_heading[2];
static double		last_time;
static unsigned long	hits, hit_bytes, misses, partial, dropped, evicted, read_blocks, read_bytes, slices, held_back;
/* Frames without a slice, by reason: the ring read this frame, a model load
 * was under way, no file handle was free, no room in the banks. */
static unsigned long	wait_ring, wait_model, wait_file, wait_room;
static unsigned long	passes;		/* passes over the file table (FillAll): one per new block, none while standing */
static double		slice_time, slice_worst;

/* ------------------------------------------------------------ the table */

static unsigned Hash (unsigned id)
{
	return (id * 2654435761u) >> 20 & (SLOTS - 1);
}

static slot_t *Find (unsigned id)
{
	unsigned i, n;
	if (!table)
		return NULL;
	for (i=Hash (id), n=0 ; table[i].id && n<SLOTS ; i=(i+1)&(SLOTS-1), n++)
		if (table[i].id == id)
			return &table[i];
	return NULL;
}

/* Linear probing, deletion by moving later entries of the run back. */
static void Remove (slot_t *s)
{
	unsigned i = (unsigned)(s - table), j = i, k;
	table[i].id = 0;
	table[i].data = NULL;
	for (;;)
	{
		j = (j + 1) & (SLOTS - 1);
		if (!table[j].id)
			return;
		k = Hash (table[j].id);
		if ((i <= j) ? (i < k && k <= j) : (i < k || k <= j))
			continue;
		table[i] = table[j];
		table[j].id = 0;
		table[j].data = NULL;
		i = j;
	}
}

static int Insert (unsigned id, void *data)
{
	unsigned i, n;
	for (i=Hash (id), n=0 ; n<SLOTS ; i=(i+1)&(SLOTS-1), n++)
		if (!table[i].id)
		{
			table[i].id = id;
			table[i].data = data;
			return 1;
		}
	return 0;
}

/* The zone threw a block out for a real load (chim_zone.c Victim). */
static void Evicted (void *data, unsigned id)
{
	slot_t *s = Find (id);
	if (s && s->data == data)
	{
		Remove (s);
		held -= ChimZone_Size (data);
		blocks--;
		evicted++;
	}
}

static void Drop (slot_t *s)
{
	void *data = s->data;
	held -= ChimZone_Size (data);
	blocks--;
	dropped++;
	Remove (s);
	ChimZone_FreeData (data);
}

/* ------------------------------------------------------------ state */

static long Budget (void)
{
	long b = (long)prefetch_mib * 1048576L, quarter = (long)ChimZone_PersistentBytes () / 4;
	return b < quarter ? b : quarter;
}

int ChimPrefetch_Active (void)
{
	return prefetch_on && ChimZone_PersistentBytes () > 0;
}

/* The table and the placement counts, taken once from the banks that
 * survive map changes (locked: never evicted). */
static int Ready (void)
{
	int i;
	if (!ChimPrefetch_Active ())
		return 0;
	if (!table)
	{
		if (!ChimZone_AllocPersistent (&table_user, SLOTS*sizeof(slot_t), CHIM_KIND_INDEX, 0x7f00))
			return 0;
		ChimZone_Lock (table_user.data);
		table = table_user.data;
		ChimZone_SetEvict (CHIM_KIND_PREFETCH, Evicted);
	}
	if (!owned && chim_world.files > 0)
	{
		if (ChimZone_AllocPersistent (&owned_user, chim_world.files*sizeof(unsigned), CHIM_KIND_INDEX, 0x7f01))
		{
			ChimZone_Lock (owned_user.data);
			owned = owned_user.data;
			owned_rows = chim_world.files;
			for (i=0 ; i<owned_rows ; i++)
				owned[i] = ~0u;
		}
	}
	return 1;
}

/* A frame's placement count by its file row (chim_chunks.c): 1 when known. */
int ChimPrefetch_Owned (int row, unsigned *count)
{
	if (!Ready () || !owned || row < 0 || row >= owned_rows || owned_rows != chim_world.files || owned[row] == ~0u)
		return 0;
	*count = owned[row];
	return 1;
}

void ChimPrefetch_SetOwned (int row, unsigned count)
{
	if (Ready () && owned && row >= 0 && row < owned_rows && owned_rows == chim_world.files && count != ~0u)
		owned[row] = count;
}

/* ------------------------------------------------------------ reads */

/* A read the cache holds whole: copied, 1. Anything missing: 0, the caller
 * reads the disk as before. */
int ChimPrefetch_Read (int row, long offset, void *out, long bytes)
{
	long b, first, last, at, n;
	slot_t *s[8];
	int i, count;
	if (!table || !blocks || row < 0 || bytes <= 0 || !prefetch_on)
		return 0;
	first = offset >> BLOCK_SHIFT;
	last = (offset + bytes - 1) >> BLOCK_SHIFT;
	if (last >= BLOCKS_PER_FILE || last - first >= 8)
		return 0;
	for (count=0, b=first ; b<=last ; b++, count++)
		if (!(s[count] = Find ((unsigned)row*BLOCKS_PER_FILE + (unsigned)b + 1)))
		{
			misses++;
			partial += count > 0;
			return 0;
		}
	for (i=0, b=first ; b<=last ; b++, i++)
	{
		at = b == first ? offset - (b << BLOCK_SHIFT) : 0;
		n = BLOCK_BYTES - at;
		if (n > bytes)
			n = bytes;
		if (at + n > ChimZone_Size (s[i]->data))
			return 0;		/* the file ends inside the block: never asked past it (Chim_PackRead checks) */
		memcpy (out, (byte *)s[i]->data + at, (size_t)n);
		out = (byte *)out + n;
		bytes -= n;
		ChimZone_Touch (s[i]->data);
	}
	hits++;
	hit_bytes += (unsigned long)(last - first + 1);
	return 1;
}

/* ------------------------------------------------------------ the frames ahead */

/* The files of each wanted cell's frame, from one pass over the file table:
 * its directory (FRAM) first, then its sectors in table order. */
static void FillAll (want_t *w, int n)
{
	int i, k;
	passes++;
	for (k=0 ; k<n ; k++)
	{
		int cx = w[k].cx, cy = w[k].cy;
		memset (&w[k], 0, sizeof(w[k]));
		w[k].cx = cx;
		w[k].cy = cy;
		w[k].files = 1;		/* row[0]: the directory, found below */
		w[k].row[0] = -1;
	}
	for (i=0 ; i<chim_world.files ; i++)
	{
		const chim_file_row_t *f = &chim_world.file[i];
		for (k=0 ; k<n ; k++)
		{
			if (f->cx != w[k].cx || f->cy != w[k].cy)
				continue;
			if (!strcmp (f->kind, "FRAM") && w[k].row[0] < 0)
				w[k].row[0] = i;
			else if (!strcmp (f->kind, "SECT") && w[k].files < FRAME_FILES)
				w[k].row[w[k].files++] = i;
			else
				continue;
			w[k].bytes += f->bytes;
			break;
		}
	}
	for (k=0 ; k<n ; k++)
		if (w[k].row[0] < 0 || w[k].bytes > FRAME_BYTES_MAX)
			w[k].skipped = 1;
}

/* Cell position of a frame-local point (original units: local x 4 + the
 * frame's centre, as chim_tp and the debug HUD). */
static void CellOf (const vec3_t origin, float *pos)
{
	pos[0] = origin[0]*4 + chim_frame.frame.centre[0];
	pos[1] = origin[1]*4 + chim_frame.frame.centre[1];
}

/* How far along the heading the ray from pos enters cell x, y (slab test;
 * within 4 cells), -1: it does not. */
static float RayEntry (const float *pos, int x, int y)
{
	float lo[2], hi[2], t0 = 0, t1 = 4*CELL_UNITS, a, b, s;
	int k;
	lo[0] = x*CELL_UNITS; hi[0] = lo[0] + CELL_UNITS;
	lo[1] = y*CELL_UNITS; hi[1] = lo[1] + CELL_UNITS;
	if (heading[0] == 0 && heading[1] == 0)
		return -1;
	for (k=0 ; k<2 ; k++)
	{
		if (fabs (heading[k]) < 1e-6f)
		{
			if (pos[k] < lo[k] || pos[k] > hi[k])
				return -1;
			continue;
		}
		a = (lo[k] - pos[k]) / heading[k];
		b = (hi[k] - pos[k]) / heading[k];
		if (a > b)
		{
			s = a; a = b; b = s;
		}
		if (a > t0)
			t0 = a;
		if (b < t1)
			t1 = b;
		if (t0 > t1)
			return -1;
	}
	return t0;
}

/* The wanted frames, in order: the 2x2 block's three neighbours (heading
 * first), the current cell, then the other five of the 3x3 ring. */
static void Plan (const float *pos)
{
	int c[2], k, n = 0, i, j, s[2], order[8], m;
	float f[2], margin = prefetch_margin / CELL_UNITS, score[8], d[2];
	int nx[8], ny[8];
	want_t next[WANT];
	for (k=0 ; k<2 ; k++)
	{
		c[k] = (int)floor (pos[k] / CELL_UNITS);
		f[k] = pos[k] / CELL_UNITS - c[k];
	}
	for (k=0 ; k<2 ; k++)
	{
		s[k] = f[k] < .5f ? -1 : 1;
		/* Hysteresis: within the margin of the midline the block stays. */
		if (have_side && c[0] == cell[0] && c[1] == cell[1] && f[k] > .5f - margin && f[k] < .5f + margin)
			s[k] = side[k];
	}
	/* The same block and much the same heading: the plan stands. A turn of
	 * more than 30 degrees orders the same cells again. */
	if (have_side && c[0] == cell[0] && c[1] == cell[1] && s[0] == side[0] && s[1] == side[1] &&
		((!heading[0] && !heading[1]) || heading[0]*plan_heading[0] + heading[1]*plan_heading[1] > .866f))
		return;		/* no heading yet (standing since the map started) also keeps it */
	plan_heading[0] = heading[0];
	plan_heading[1] = heading[1];
	cell[0] = c[0];
	cell[1] = c[1];
	side[0] = s[0];
	side[1] = s[1];
	have_side = 1;
	/* The three neighbours of the block, by heading (the cell walked
	 * towards first), then the other five of the ring by heading. */
	nx[0] = c[0] + s[0]; ny[0] = c[1];
	nx[1] = c[0];        ny[1] = c[1] + s[1];
	nx[2] = c[0] + s[0]; ny[2] = c[1] + s[1];
	for (m=3, i=-1 ; i<=1 ; i++)
		for (j=-1 ; j<=1 ; j++)
		{
			int x = c[0] + i, y = c[1] + j, inblock = (x == c[0] || x == c[0] + s[0]) && (y == c[1] || y == c[1] + s[1]);
			if (!inblock)
			{
				nx[m] = x;
				ny[m] = y;
				m++;
			}
		}
	/* Order: when the heading's ray enters the cell (the one walked into
	 * first leads); cells the ray misses follow by their distance. Score:
	 * smaller first, in units. */
	for (i=0 ; i<8 ; i++)
	{
		score[i] = RayEntry (pos, nx[i], ny[i]);
		if (score[i] < 0)
		{
			d[0] = pos[0] < nx[i]*CELL_UNITS ? nx[i]*CELL_UNITS - pos[0] : pos[0] > (nx[i] + 1)*CELL_UNITS ? pos[0] - (nx[i] + 1)*CELL_UNITS : 0;
			d[1] = pos[1] < ny[i]*CELL_UNITS ? ny[i]*CELL_UNITS - pos[1] : pos[1] > (ny[i] + 1)*CELL_UNITS ? pos[1] - (ny[i] + 1)*CELL_UNITS : 0;
			score[i] = 4*CELL_UNITS + (float)sqrt (d[0]*d[0] + d[1]*d[1]);
		}
		order[i] = i;
	}
	for (i=0 ; i<8 ; i++)		/* within each group, the first entered first */
		for (j=i+1 ; j<8 ; j++)
			if ((i < 3) == (j < 3) && score[order[j]] < score[order[i]])
			{
				k = order[i];
				order[i] = order[j];
				order[j] = k;
			}
	for (i=0 ; i<3 ; i++, n++)
	{
		next[n].cx = nx[order[i]];
		next[n].cy = ny[order[i]];
	}
	next[n].cx = c[0];
	next[n++].cy = c[1];
	if (prefetch_ring)
		for (i=3 ; i<8 ; i++, n++)
		{
			next[n].cx = nx[order[i]];
			next[n].cy = ny[order[i]];
		}
	/* Only the order changed (the same cells): keep what each has, no pass
	 * over the file table. */
	for (i=0 ; i<n ; i++)
	{
		for (j=0 ; j<wants ; j++)
			if (want[j].cx == next[i].cx && want[j].cy == next[i].cy)
				break;
		if (j == wants)
			break;
	}
	if (i < n)
		FillAll (next, n);
	/* What was already read for a frame still wanted carries over (its
	 * files and read cursor). */
	for (i=0 ; i<n ; i++)
		for (j=0 ; j<wants ; j++)
			if (want[j].cx == next[i].cx && want[j].cy == next[i].cy)
			{
				next[i] = want[j];
				break;
			}
	/* RAM short for the whole block (the maintainer, 18 October 2026: the
	 * heavy cells stall most): its neighbours by size, the largest first. */
	if (next[0].bytes + next[1].bytes + next[2].bytes > Budget ())
		for (i=0 ; i<3 ; i++)
			for (j=i+1 ; j<3 ; j++)
				if (next[j].bytes > next[i].bytes)
				{
					want_t w = next[i];
					next[i] = next[j];
					next[j] = w;
				}
	memcpy (want, next, n*sizeof(want_t));
	wants = n;
}

/* Blocks of frames beyond the ring by more than half a cell go first when
 * the budget is full; 1 when room was made. */
static int MakeRoom (const float *pos)
{
	int i, freed = 0;
	float cx, cy, dx, dy;
	for (i=0 ; i<SLOTS ; i++)
	{
		int row;
		if (!table[i].id)
			continue;
		row = (int)((table[i].id - 1) / BLOCKS_PER_FILE);
		if (row >= chim_world.files)
			continue;
		cx = (chim_world.file[row].cx + .5f)*CELL_UNITS;
		cy = (chim_world.file[row].cy + .5f)*CELL_UNITS;
		dx = (float)fabs (cx - pos[0]) / CELL_UNITS;
		dy = (float)fabs (cy - pos[1]) / CELL_UNITS;
		if (dx > 2.0f || dy > 2.0f)		/* past the ring's cells (1.5) by half a cell */
		{
			Drop (&table[i]);
			freed = 1;
			i--;		/* Remove moved a later entry into this slot */
		}
	}
	return freed;
}

/* One slice: the next missing blocks of the first wanted frame that is not
 * complete, up to prefetch_kib KiB. */
static void Slice (const float *pos)
{
	long limit = (long)prefetch_kib * 1024, got = 0, size, at, n, budget = Budget ();
	double started = Sys_FloatTime ();
	int i;
	chim_pack_t *pack;
	void *data;
	for (i=0 ; i<wants && got < (limit > BLOCK_BYTES ? limit : BLOCK_BYTES) ; i++)
	{
		want_t *w = &want[i];
		while (!w->done && !w->skipped && got < (limit > BLOCK_BYTES ? limit : BLOCK_BYTES))
		{
			int row;
			unsigned id;
			if (w->file >= w->files)
			{
				w->done = 1;
				break;
			}
			row = w->row[w->file];
			size = (long)chim_world.file[row].bytes;
			at = (long)w->block << BLOCK_SHIFT;
			if (at >= size || w->block >= BLOCKS_PER_FILE)
			{
				w->file++;
				w->block = 0;
				continue;
			}
			id = (unsigned)row*BLOCKS_PER_FILE + (unsigned)w->block + 1;
			if (Find (id))
			{
				w->block++;
				continue;
			}
			n = size - at < BLOCK_BYTES ? size - at : BLOCK_BYTES;
			if (held + n > budget && !MakeRoom (pos))
			{
				held_back++;
				goto out;		/* full of wanted bytes: nothing more now */
			}
			if (blocks >= SLOTS/2)
			{
				held_back++;
				goto out;
			}
			if (!(pack = Chim_File (row)))
			{
				wait_file++;
				goto out;
			}
			if (!(data = ChimZone_AllocPersistent (NULL, (int)n, CHIM_KIND_PREFETCH, id)))
			{
				wait_room++;
				goto out;
			}
			if (!Chim_PackReadRaw (pack, at, data, n))
			{
				ChimZone_FreeData (data);
				w->skipped = 1;
				break;
			}
			if (!Insert (id, data))
			{
				ChimZone_FreeData (data);
				goto out;
			}
			held += ChimZone_Size (data);
			blocks++;
			read_blocks++;
			read_bytes += (unsigned long)n;
			chim_world.prefetch_bytes += (unsigned long)n;
			got += n;
			w->block++;
		}
	}
out:
	if (got)
	{
		double t = Sys_FloatTime () - started;
		slices++;
		slice_time += t;
		if (t > slice_worst)
			slice_worst = t;
		AW_SpikeAdd (AW_SP_PREFETCH, t, got);
	}
}

/* Once a frame on a CHIM map, after the ring's own work (chim_world.c Tick):
 * spare = the ring read nothing this frame and no load is under way. */
void ChimPrefetch_Step (const vec3_t origin, int spare)
{
	float pos[2], dx, dy, len;
	double now;
	if (!Ready () || !chim_frame.count || !chim_world.files)
		return;
	CellOf (origin, pos);
	if (!(fabs (pos[0]) < 1e7f && fabs (pos[1]) < 1e7f))
		return;		/* not a place (a NaN origin is never planned for) */
	now = Sys_FloatTime ();
	/* Heading: the way the player moved over the last quarter second (kept
	 * while standing). */
	if (now - last_time >= .25 || now < last_time)
	{
		dx = pos[0] - last_pos[0];
		dy = pos[1] - last_pos[1];
		len = (float)sqrt (dx*dx + dy*dy);
		if (last_time > 0 && len > 16 && len < CELL_UNITS)
		{
			heading[0] = dx / len;
			heading[1] = dy / len;
		}
		last_pos[0] = pos[0];
		last_pos[1] = pos[1];
		last_time = now;
	}
	Plan (pos);
	if (!spare)
		wait_ring++;
	else if (ChimModels_Busy ())
		wait_model++;
	else
		Slice (pos);
}

/* Another store (chim_world.c Chim_StoreSelect): its file rows mean other
 * files, so every block and placement count goes. */
void ChimPrefetch_StoreChanged (void)
{
	int i;
	for (i=0 ; table && i<SLOTS ; i++)
		while (table[i].id)
			Drop (&table[i]);
	if (owned)
	{
		ChimZone_Unlock (owned_user.data);
		ChimZone_Free (&owned_user);
		owned = NULL;
		owned_rows = 0;
	}
	wants = have_side = 0;
}

/* A new map: the plan starts again from the arrival (the blocks stay). */
void ChimPrefetch_MapBegin (void)
{
	have_side = 0;
	wants = 0;
	last_time = 0;
	heading[0] = heading[1] = 0;	/* known again a quarter second after the arrival */
}

/* "chim prefetch [0/1 / kib N / mib N / ring 0/1 / margin N]" (chim_world.c
 * Status): no argument prints the report. argv[0] is "prefetch". */
void ChimPrefetch_Command (int argc, char **argv)
{
	int v = argc >= 2 ? atoi (argv[argc-1]) : 0;
	if (argc == 2 && (!strcmp (argv[1], "0") || !strcmp (argv[1], "1")))
		prefetch_on = v;
	else if (argc == 3 && !strcmp (argv[1], "kib") && v >= 1 && v <= 1024)
		prefetch_kib = v;
	else if (argc == 3 && !strcmp (argv[1], "mib") && v >= 0 && v <= 2047)
		prefetch_mib = v;
	else if (argc == 3 && !strcmp (argv[1], "ring") && (v == 0 || v == 1))
		prefetch_ring = v;
	else if (argc == 3 && !strcmp (argv[1], "margin") && v >= 0 && 2*v <= (int)CELL_UNITS)
		prefetch_margin = v;
	else if (argc != 1)
		Con_Printf ("chim prefetch [0/1 / kib 1..1024 / mib 0..2047 / ring 0/1 / margin 0 to half a cell]\n");
	have_side = 0;		/* plan again with the new values */
	ChimPrefetch_Report ();
}

void ChimPrefetch_SetOn (int on)
{
	prefetch_on = on != 0;
}

/* The plan for tests and the report: the i-th wanted cell and its state
 * (0 reading, 1 read, 2 not read ahead); 0 past the end. */
int ChimPrefetch_Wanted (int i, int *cx, int *cy, int *state)
{
	if (i < 0 || i >= wants)
		return 0;
	*cx = want[i].cx;
	*cy = want[i].cy;
	*state = want[i].skipped ? 2 : want[i].done ? 1 : 0;
	return 1;
}

unsigned long ChimPrefetch_Passes (void)
{
	return passes;
}

long ChimPrefetch_Held (int *count)
{
	*count = blocks;
	return held;
}

void ChimPrefetch_Report (void)
{
	int i;
	Con_Printf ("prefetch (chim prefetch %ld, kib %ld, mib %ld, ring %ld, margin %ld): %s; %ld blocks, %ld KiB held of %ld KiB; read ahead %lu KiB in %lu slices (%ld ms, worst %ld ms)\n",
		(long)prefetch_on, (long)prefetch_kib, (long)prefetch_mib, (long)prefetch_ring, (long)prefetch_margin,
		!ChimPrefetch_Active () ? "off (no extra Fast RAM, or turned off)" : "on",
		(long)blocks, held/1024, Budget ()/1024, read_bytes/1024, slices, (long)(slice_time*1000 + .5), (long)(slice_worst*1000 + .5));
	Con_Printf ("prefetch: %lu reads served from RAM (%lu blocks), %lu not (%lu in part); %lu blocks dropped beyond the ring, %lu evicted for real loads, %lu slices held back\n",
		hits, hit_bytes, misses, partial, dropped, evicted, held_back);
	Con_Printf ("prefetch: frames without a slice: %lu the ring read, %lu a model load under way, %lu no file handle free, %lu no room; %lu plans\n",
		wait_ring, wait_model, wait_file, wait_room, passes);
	for (i=0 ; i<wants ; i++)
		Con_Printf ("  ahead %ld: cell %ld %ld, %ld files %ld KiB, %s\n", (long)i, (long)want[i].cx, (long)want[i].cy,
			(long)want[i].files, want[i].bytes/1024, want[i].skipped ? "not read ahead" : want[i].done ? "read" :
			"reading");
}

void ChimPrefetch_Init (void)
{
	table = NULL;
	owned = NULL;
	table_user.data = owned_user.data = NULL;
	owned_rows = blocks = wants = have_side = 0;
	held = 0;
}
