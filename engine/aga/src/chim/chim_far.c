/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM far terrain: the frame's distant land, resident for the whole map.
 *
 * The frame world (chim_graft.c) holds only the active chunk ring: the view
 * distance plus the hysteresis. A legacy region map held its neighbours'
 * ground at least 892 units beyond the player (core plus 896 units of
 * overlap), so at the fog plane there was land, drawn fully fogged: the
 * horizon method of record (aw_skyline_fill 0, the land outline). On a CHIM
 * map, beyond the ring and past the frame's edge, the ground was absent and
 * the view ended in sky (CHIM-FAR-TERRAIN-33).
 *
 * Quake has no terrain level of detail; the nearest mechanism is AmiWind's own
 * distant-LAND pass (aw_horizon.c, aw_terrain_horizon), which rasterizes the
 * world model's LAND faces beyond the fog plane in the fog colour, depth
 * tested against the z-buffer the span renderer wrote. The far layer reuses
 * that rasterizer (AW_HorizonGrid) on its own data: a coarse heightfield over
 * the frame and a margin beyond it, the sidecar maps/<frame map>.far (written
 * by the CHIM builder, tools/chim/far.py; docs/chim/WORLD_FORMAT.md "Far
 * terrain"), read once at map start into the low Hunk (like efrag pages and
 * Quake's static data for the map) and given back with the Hunk at the next
 * map change. It is drawn after the fog pass (aw_fog.c), beyond the fog plane
 * only, so it never covers a resident chunk nearer than the fog plane and,
 * beyond it, both are the same full fog colour: nothing has to be hidden
 * where a chunk is resident.
 *
 * chim_far 0 draws no far land (the first CHIM method, kept for A/B tests);
 * chim_far_reach limits the forward depth it reaches (default 896, the legacy
 * region overlap; 0: the whole layer); chim_far_objects 1 (read at map start;
 * experimental, off) raises the file's object stamps, the drawn box tops of
 * large placements, into the heights; chim_far_cull 0 tests every block
 * (equivalence checks).
 *
 * The layer is also the TERRAIN FLOOR (CHIM-GRAFT-REPACK-EMPTY-33, second
 * layer): it is the one copy of the frame's ground that is never streamed, so
 * it stays when the frame world loses its chunks. ChimFar_Floor gives the
 * lowest height a walking body may reach at a point and the ground to lift it
 * onto (aw_walk.c AW_TerrainFloor, from SV_Physics_Client's walk move and
 * SV_Physics_Step's free fall; noclip and flight never ask). The surface is
 * the chunk terrain's own tile triangles through the same samples; the lowest
 * height is the quad's lowest corner less FLOOR_MARGIN (irregular ground,
 * standing hull lattice and rounding stay above it), or, where a corner lies
 * at the water level (the layer keeps the water surface there, not the bed),
 * the lowest terrain point of the chunk (the frame's chunk table, resident)
 * less FLOOR_MARGIN. chim_terrain_floor 0 turns it off (the previous
 * behaviour, kept for A/B); applied object stamps (chim_far_objects 1) turn
 * it off, as the heights then hold object tops.
 */
#include "quakedef.h"
#include "chim_local.h"
#include "../aw_horizon.h"

cvar_t	chim_far = {"chim_far", "1"};
cvar_t	chim_far_reach = {"chim_far_reach", "896"};
cvar_t	chim_far_objects = {"chim_far_objects", "0"};
static cvar_t	chim_far_cull = {"chim_far_cull", "1"};
cvar_t	chim_terrain_floor = {"chim_terrain_floor", "1"};

#define FLOOR_MARGIN	64		/* local units the lowest height keeps below the layer's ground */
#define FLOOR_WATER		0		/* the layer's water level (tools/chim/far.py WATER_LEVEL) */

extern void (*aw_chim_far_draw)(byte colour, int distance);	/* aw_fog.c */
extern int (*aw_chim_floor)(const vec3_t origin, float *lowest, float *surface);	/* aw_walk.c */

static aw_horizon_grid_t	layer;
static short	*memory;			/* heights then block bounds, in the low Hunk */
static int		loaded, bytes, stamped;
static char		path[MAX_QPATH+8];
static char		why[64];
static chim_far_header_t	head;
static long		counts[9];
static double	last_time, worst_time;
static unsigned long	draws;
static int		frame_lowest, frame_lowest_known;	/* the frame's lowest chunk terrain point */

/* CRC-32 (zlib polynomial), as the builder writes it; continues from crc
 * (0 to start), as zlib's crc32 () does. */
static unsigned Crc32 (unsigned crc, const unsigned char *p, long n)
{
	unsigned c = crc ^ 0xFFFFFFFFu;
	int k;
	while (n-- > 0)
	{
		c ^= *p++;
		for (k=0 ; k<8 ; k++)
			c = (c >> 1) ^ (0xEDB88320u & (0u - (c & 1u)));
	}
	return c ^ 0xFFFFFFFFu;
}

/* The 40-byte header; 1 when it is a far terrain file of this version whose
 * size is `file_bytes` (the whole file). */
int ChimFar_Parse (const unsigned char *p, long file_bytes, chim_far_header_t *h)
{
	if (file_bytes < CHIM_FAR_HEADER_BYTES || memcmp (p, "CHFL", 4))
		return 0;
	h->version = ChimFormat_U16 (p+4);
	h->header = ChimFormat_U16 (p+6);
	h->cx = ChimFormat_S16 (p+8);
	h->cy = ChimFormat_S16 (p+10);
	h->origin[0] = ChimFormat_F32 (p+12);
	h->origin[1] = ChimFormat_F32 (p+16);
	h->step = ChimFormat_F32 (p+20);
	h->scale = ChimFormat_F32 (p+24);
	h->nx = ChimFormat_U16 (p+28);
	h->ny = ChimFormat_U16 (p+30);
	h->block = ChimFormat_U16 (p+32);
	h->stamps = ChimFormat_U16 (p+34);
	h->crc = ChimFormat_U32 (p+36);
	if (h->version < 1 || h->version > CHIM_FAR_VERSION || h->header != CHIM_FAR_HEADER_BYTES ||
		(h->version == 1 && h->stamps))
		return 0;
	if (h->nx < 2 || h->ny < 2 || h->nx > 1025 || h->ny > 1025 || h->block < 1 || h->block > AW_HORIZON_GRID_MAX_BLOCK)
		return 0;
	if (!(h->step > 0 && h->step <= 65536) || !(h->scale > 0 && h->scale <= 1) ||
		!isfinite (h->origin[0]) || !isfinite (h->origin[1]) ||
		fabs (h->origin[0]) > 4000000 || fabs (h->origin[1]) > 4000000)
		return 0;
	return file_bytes == CHIM_FAR_HEADER_BYTES + ChimFar_BodyBytes (h);
}

/* Bytes after the header: the heights, then (version 2) the stamps' u32 sample
 * indices and i16 heights, padded to a multiple of 4. */
long ChimFar_BodyBytes (const chim_far_header_t *h)
{
	long grid = 2L*h->nx*h->ny, stamps = 6L*h->stamps;
	return grid + stamps + (stamps ? (4 - (grid + stamps) % 4) % 4 : 0);
}

/* Object stamps (version 2): raise each listed sample to its height, the
 * drawn box tops of large placed objects; indices ascending and in range.
 * Returns how many were applied, or -1 when the list is malformed. */
int ChimFar_Stamps (short *heights, int nx, int ny, const unsigned char *list, int count)
{
	int k, z;
	long index, last = -1;
	for (k=0 ; k<count ; k++)
	{
		index = (long)ChimFormat_U32 (list + 4*k);
		if (index <= last || index >= (long)nx*ny)
			return -1;
		last = index;
	}
	for (k=0 ; k<count ; k++)
	{
		index = (long)ChimFormat_U32 (list + 4*k);
		z = ChimFormat_S16 (list + 4*count + 2*k);
		if (z > heights[index])
			heights[index] = (short)z;
	}
	return count;
}

/* Blocks across and along for a grid (as AW_HorizonGrid walks them). */
static int Blocks (int n, int block)
{
	return (n - 2) / block + 1;
}

/* Lowest and highest height of every block, rows by y (AW_HorizonGrid's bounds). */
void ChimFar_Bounds (const short *heights, int nx, int ny, int block, short *bounds)
{
	int bx = Blocks (nx, block), by = Blocks (ny, block), bi, bj, i, j, i1, j1, z, lo, hi;
	for (bj=0 ; bj<by ; bj++)
		for (bi=0 ; bi<bx ; bi++)
		{
			i1 = bi*block + block;
			if (i1 > nx-1)
				i1 = nx-1;
			j1 = bj*block + block;
			if (j1 > ny-1)
				j1 = ny-1;
			lo = 32767;
			hi = -32768;
			for (j=bj*block ; j<=j1 ; j++)
				for (i=bi*block ; i<=i1 ; i++)
				{
					z = heights[j*nx+i];
					if (z < lo)
						lo = z;
					if (z > hi)
						hi = z;
				}
			bounds[2*(bj*bx+bi)] = (short)lo;
			bounds[2*(bj*bx+bi)+1] = (short)hi;
		}
}

static void Said (const char *text)
{
	strncpy (why, text, sizeof(why)-1);
	why[sizeof(why)-1] = 0;
	if (chim_debug.value)
		Con_Printf ("CHIM far terrain: %s\n", why);
}

/* Map start (chim_world.c MapBegin, after the frame world): the frame map's
 * sidecar, maps/<map>.far, for the frame in chim_frame. */
void ChimFar_Begin (const char *map_name, long hunk_spare)
{
	FILE *f = NULL;
	unsigned char raw[CHIM_FAR_HEADER_BYTES];
	unsigned char *body;
	int length, n, i, bx, by, keep, mark, applied = 0;
	long body_bytes, grid_bytes, stamp_bytes;
	unsigned char *list;
	unsigned crc;
	char *dot;

	ChimFar_End ();
	memset (counts, 0, sizeof(counts));
	worst_time = last_time = 0;
	draws = 0;
	/* The terrain floor's fallback under water: the frame's lowest chunk
	 * terrain point, from the chunk table (resident for the map). */
	for (i=0 ; i<chim_frame.count ; i++)
		if (!frame_lowest_known || chim_frame.entries[i].disk.zmin < frame_lowest)
		{
			frame_lowest = chim_frame.entries[i].disk.zmin;
			frame_lowest_known = 1;
		}
	if (!map_name || strlen (map_name) >= MAX_QPATH)
	{
		Said ("no frame map name");
		return;
	}
	strcpy (path, map_name);
	dot = strrchr (path, '.');
	if (!dot || strchr (dot, '/'))
		dot = path + strlen (path);
	strcpy (dot, ".far");
	length = COM_FOpenFile (path, &f);
	if (!f)
	{
		Said ("none beside the frame map");
		return;
	}
	if (length < CHIM_FAR_HEADER_BYTES || fread (raw, 1, CHIM_FAR_HEADER_BYTES, f) != CHIM_FAR_HEADER_BYTES ||
		!ChimFar_Parse (raw, length, &head))
	{
		fclose (f);
		Said ("invalid file (refused)");
		return;
	}
	if (head.cx != chim_frame.frame.cx || head.cy != chim_frame.frame.cy)
	{
		fclose (f);
		Said ("built for another frame (refused)");
		return;
	}
	n = head.nx * head.ny;
	bx = Blocks (head.nx, head.block);
	by = Blocks (head.ny, head.block);
	body_bytes = ChimFar_BodyBytes (&head);
	grid_bytes = 2L*n;
	stamp_bytes = body_bytes - grid_bytes;
	/* Kept: the heights and the block bounds. The stamps are read above them
	 * and the Hunk is given back to its mark once they are applied (Quake's
	 * Hunk is a stack; nothing else allocates in between). */
	keep = (int)((grid_bytes + 3) & ~3L) + 4*bx*by;
	if (hunk_spare < keep + stamp_bytes + 32)
	{
		fclose (f);
		Said ("no room in the Hunk above chim_reserve_kib");
		return;
	}
	memory = Hunk_AllocName (keep, "chimfar");
	body = (unsigned char *)memory;
	mark = Hunk_LowMark ();
	list = stamp_bytes ? (unsigned char *)Hunk_AllocName ((int)stamp_bytes, "chimfarstamps") : NULL;
	if ((long)fread (body, 1, grid_bytes, f) != grid_bytes ||
		(list && (long)fread (list, 1, stamp_bytes, f) != stamp_bytes))
		crc = ~head.crc;
	else
		crc = Crc32 (Crc32 (0, body, grid_bytes), list, stamp_bytes);
	fclose (f);
	if (crc != head.crc)
	{
		Hunk_FreeToLowMark (mark);
		memory = NULL;		/* the heights' block goes back with the map */
		Said ("height data damaged (refused)");
		return;
	}
	for (i=0 ; i<n ; i++)		/* big-endian on disk: native shorts in place */
		memory[i] = (short)ChimFormat_S16 (body + 2*i);
	/* Large objects (chim_far_objects 1, read at map start): their stamps,
	 * raised into the grid before the block bounds. */
	if (list && chim_far_objects.value > 0)
		applied = ChimFar_Stamps (memory, head.nx, head.ny, list, head.stamps);
	Hunk_FreeToLowMark (mark);
	if (applied < 0)
	{
		memory = NULL;
		Said ("stamps malformed (refused)");
		return;
	}
	stamped = applied;
	layer.bounds = (short *)(body + ((grid_bytes + 3) & ~3L));
	ChimFar_Bounds (memory, head.nx, head.ny, head.block, (short *)layer.bounds);
	layer.heights = memory;
	layer.nx = head.nx;
	layer.ny = head.ny;
	layer.block = head.block;
	/* local = (world - frame origin) x scale, as every CHIM position */
	layer.x0 = (head.origin[0] - chim_frame.frame.centre[0]) * head.scale;
	layer.y0 = (head.origin[1] - chim_frame.frame.centre[1]) * head.scale;
	layer.step = head.step * head.scale;
	layer.reach = 0;
	bytes = keep;
	loaded = 1;
	why[0] = 0;
	if (chim_debug.value)
		Con_Printf ("CHIM far terrain %s: %ld x %ld samples, step %ld, %ld bytes\n", path,
			(long)head.nx, (long)head.ny, (long)layer.step, (long)bytes);
}

void ChimFar_End (void)
{
	/* The heights live in the map's Hunk, which the map change frees. */
	memset (&layer, 0, sizeof(layer));
	memory = NULL;
	loaded = bytes = 0;
	frame_lowest_known = 0;
}

/* The terrain floor at a frame-local point: 1 with the lowest height a
 * walking body may reach there and the ground surface to lift it onto, 0 where
 * there is none (no layer, outside it, chim_terrain_floor 0, stamps applied,
 * water without a chunk record). One lookup: four samples, no FPU traps. */
static int Floor (const vec3_t origin, float *lowest, float *surface)
{
	const short *h;
	float fx, fy, h00, h10, h01, h11, low;
	int i, j, e;

	if (!loaded || stamped || chim_terrain_floor.value <= 0 || !Chim_Active () || !(layer.step > 0))
		return 0;
	fx = (origin[0] - layer.x0) / layer.step;
	fy = (origin[1] - layer.y0) / layer.step;
	if (!(fx >= 0 && fy >= 0 && fx < layer.nx - 1 && fy < layer.ny - 1))
		return 0;
	i = (int)fx;		/* not negative: truncation is the floor */
	j = (int)fy;
	fx -= i;
	fy -= j;
	h = layer.heights + j*layer.nx + i;
	h00 = h[0];
	h10 = h[1];
	h01 = h[layer.nx];
	h11 = h[layer.nx+1];
	/* The chunk terrain's two tile triangles: diagonal from sample (i, j) to
	 * (i+1, j+1) (tools/chim/terrain.py tile_polygons). */
	if (fx >= fy)
		*surface = h00 + fx*(h10 - h00) + fy*(h11 - h10);
	else
		*surface = h00 + fy*(h01 - h00) + fx*(h11 - h01);
	low = h00;
	if (h10 < low)
		low = h10;
	if (h01 < low)
		low = h01;
	if (h11 < low)
		low = h11;
	if (low <= FLOOR_WATER)
	{
		/* Water: the bed is not in the layer. The lowest terrain point of the
		 * chunk under the point, else of the frame. */
		e = -1;
		if (chim_frame.frame.grain > 0 && origin[0] >= chim_frame.frame.low[0] && origin[1] >= chim_frame.frame.low[1])
			e = ChimChunks_CellEntry ((int)((origin[0] - chim_frame.frame.low[0]) / chim_frame.frame.grain),
				(int)((origin[1] - chim_frame.frame.low[1]) / chim_frame.frame.grain));
		if (e >= 0 && e < chim_frame.count)
			low = chim_frame.entries[e].disk.zmin;
		else if (frame_lowest_known)
			low = frame_lowest;
		else
			return 0;
	}
	*lowest = low - FLOOR_MARGIN;
	return 1;
}

/* The floor through the hook's own function (the chim command, the tests). */
int ChimFar_Floor (const vec3_t origin, float *lowest, float *surface)
{
	return Floor (origin, lowest, surface);
}

/* aw_fog.c, after the fog pass: the layer beyond the fog plane. */
static void Draw (byte colour, int distance)
{
	double t;
	if (!loaded || !Chim_Active () || chim_far.value <= 0)
		return;
	layer.reach = chim_far_reach.value > 0 ? chim_far_reach.value : 0;
	t = Sys_FloatTime ();
	AW_HorizonGrid (&layer, colour, distance, chim_far_cull.value != 0);
	last_time = Sys_FloatTime () - t;
	if (last_time > worst_time)
		worst_time = last_time;
	AW_HorizonGridCounts (counts);
	draws++;
}

int ChimFar_Loaded (void)
{
	return loaded;
}

/* The resident layer (NULL when none): for the chim command and the tests. */
const aw_horizon_grid_t *ChimFar_Layer (void)
{
	return loaded ? &layer : NULL;
}

/* For dbg rcount: " far drawn/blocks tris px us" (last frame; us the worst since the last line). */
int ChimFar_RCount (char *out, int size)
{
	long worst = (long)(worst_time*1e6 + .5);
	worst_time = 0;
	if (!loaded || chim_far.value <= 0)
		return snprintf (out, size, " far off") > 0;
	return snprintf (out, size, " far %ld/%ld tr %ld px %ld fus %ld", counts[4], counts[0], counts[5]-counts[6],
		counts[8], worst) > 0;
}

void ChimFar_Report (void)
{
	if (!loaded)
	{
		Con_Printf ("far terrain (chim_far %ld): %s\n", (long)chim_far.value, why[0] ? why : "not loaded");
		return;
	}
	Con_Printf ("far terrain (chim_far %ld, reach %ld): %s, %ld x %ld samples every %ld units, %ld bytes of Hunk\n",
		(long)chim_far.value, (long)chim_far_reach.value, path, (long)head.nx, (long)head.ny, (long)layer.step,
		(long)bytes);
	Con_Printf ("far terrain objects (chim_far_objects %ld, read at map start): %ld of %ld stamps applied\n",
		(long)chim_far_objects.value, (long)stamped, (long)head.stamps);
	Con_Printf ("terrain floor (chim_terrain_floor %ld): %s, %ld units below the layer's ground\n",
		(long)chim_terrain_floor.value, chim_terrain_floor.value <= 0 ? "off" : stamped ? "off (object stamps applied)" : "on",
		(long)FLOOR_MARGIN);
	Con_Printf ("far terrain last frame: blocks %ld drawn of %ld (near %ld, far %ld, side %ld), triangles %ld (%ld facing away), polygons %ld, pixels %ld, %ld us\n",
		counts[4], counts[0], counts[1], counts[2], counts[3], counts[5], counts[6], counts[7], counts[8],
		(long)(last_time*1e6 + .5));
}

void ChimFar_Init (void)
{
	Cvar_RegisterVariable (&chim_far);
	Cvar_RegisterVariable (&chim_far_reach);
	Cvar_RegisterVariable (&chim_far_objects);
	Cvar_RegisterVariable (&chim_far_cull);
	Cvar_RegisterVariable (&chim_terrain_floor);
}

void ChimFar_Hook (void)
{
	aw_chim_far_draw = Draw;
	aw_chim_floor = Floor;
}
