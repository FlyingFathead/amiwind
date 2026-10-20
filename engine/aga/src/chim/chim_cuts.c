/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM whole-structure cuts: the frame map's cut groups (CHIM-BRIDGE-POP-PIECES-44).
 *
 * A long structure is built from many placements: Vivec's walkways and canton
 * tiles, Balmora's walls and bridges, the Ghostfence, a hillside of rocks.
 * Each placement passing the distance tests on its own sphere (aw_fog.c) drops
 * the small middle pieces first and leaves a bridge without its middle. The
 * CHIM builder finds those structures in the frame's own data
 * (tools/chim/cuts.py: same mesh family, touching drawn boxes) and writes them
 * as a sidecar of the frame map, maps/<frame map>.cut, like the far terrain
 * (chim_far.c): a box per structure and the placement ids of its members. At
 * map start the box table and the sorted member ids go into the low Hunk
 * (given back with the map); when a chunk becomes active, each placement of
 * a structure gets its structure's box (entity_t aw_cut_box), and aw_fog.c
 * (aw_cull + 16, dbg cut groups) tests that box instead of the placement's own sphere, so
 * the structure is drawn, fogged and left out as one piece.
 *
 * No sidecar, a damaged one or one built for another frame: every placement
 * keeps its own sphere (the method before), said with chim_debug 1.
 *
 * File (big-endian, tools/chim/cuts.py):
 *    0 'CHCT', u16 version 1, u16 header bytes 24, i16 cx, i16 cy,
 *   12 u32 structures, u32 members, u32 CRC-32 (zlib) of the body;
 *   24 i16[6] per structure (frame-local mins, maxs), then per member by
 *      placement id ascending: u32 placement id, u16 structure, u16 0.
 */
#include "quakedef.h"
#include "chim_local.h"

#define CUTS_HEADER	24
#define CUTS_BOX	12
#define CUTS_MEMBER	8

static float			*boxes;		/* 6 per structure */
static unsigned			*pids;		/* members, ascending */
static unsigned short	*which;		/* each member's structure */
static long				structures, members;
static char				why[64];

/* CRC-32 (zlib polynomial), continuing from crc (0 to start). */
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

/* The 24-byte header: 1 with the counts and CRC when it is a version 1 file
 * for frame (cx, cy) whose size is `file_bytes`. */
int ChimCuts_Header (const unsigned char *p, long file_bytes, int cx, int cy, long *n, long *m, unsigned *crc)
{
	if (file_bytes < CUTS_HEADER || memcmp (p, "CHCT", 4) || ChimFormat_U16 (p+4) != 1 ||
		ChimFormat_U16 (p+6) != CUTS_HEADER || ChimFormat_S16 (p+8) != cx || ChimFormat_S16 (p+10) != cy)
		return 0;
	*n = (long)ChimFormat_U32 (p+12);
	*m = (long)ChimFormat_U32 (p+16);
	*crc = ChimFormat_U32 (p+20);
	if (*n < 0 || *n > 65535 || *m < 0 || *m > 1L<<20 ||
		file_bytes != CUTS_HEADER + *n*CUTS_BOX + *m*CUTS_MEMBER)
		return 0;
	return 1;
}

/* The body (n boxes, m members) into the tables: 1 when its CRC matches,
 * the members ascend and every structure exists. */
int ChimCuts_Body (const unsigned char *body, long n, long m, unsigned crc,
	float *box_out, unsigned *pid_out, unsigned short *which_out)
{
	long i;
	int j;
	if (Crc32 (0, body, n*CUTS_BOX + m*CUTS_MEMBER) != crc)
		return 0;
	for (i=0 ; i<n ; i++)
		for (j=0 ; j<6 ; j++)
			box_out[6*i+j] = (float)ChimFormat_S16 (body + i*CUTS_BOX + 2*j);
	for (i=0 ; i<m ; i++)
	{
		const unsigned char *p = body + n*CUTS_BOX + i*CUTS_MEMBER;
		pid_out[i] = ChimFormat_U32 (p);
		which_out[i] = (unsigned short)ChimFormat_U16 (p+4);
		if (which_out[i] >= n || (i && pid_out[i] <= pid_out[i-1]))
			return 0;
	}
	return 1;
}

/* The structure box of placement `pid` in sorted tables, or NULL. */
const float *ChimCuts_Find (const float *box_table, const unsigned *pid_table, const unsigned short *which_table,
	long m, unsigned pid)
{
	long lo = 0, hi = m - 1, mid;
	while (lo <= hi)
	{
		mid = (lo + hi) >> 1;
		if (pid_table[mid] == pid)
			return box_table + 6*which_table[mid];
		if (pid_table[mid] < pid)
			lo = mid + 1;
		else
			hi = mid - 1;
	}
	return NULL;
}

const float *ChimCuts_Box (unsigned pid)
{
	return members ? ChimCuts_Find (boxes, pids, which, members, pid) : NULL;
}

void ChimCuts_End (void)
{
	/* The tables live in the map's Hunk, which the map change frees. */
	boxes = NULL;
	pids = NULL;
	which = NULL;
	structures = members = 0;
}

static void Said (const char *text)
{
	strncpy (why, text, sizeof(why)-1);
	why[sizeof(why)-1] = 0;
	if (chim_debug.value)
		Con_Printf ("CHIM cut groups: %s\n", why);
}

/* Map start (chim_world.c, after the far terrain): maps/<map>.cut for the
 * frame in chim_frame. */
void ChimCuts_Begin (const char *map_name, long hunk_spare)
{
	FILE *f = NULL;
	unsigned char head[CUTS_HEADER];
	unsigned char *body;
	char path[MAX_QPATH+8], *dot;
	long n, m, body_bytes, keep;
	unsigned crc;
	int length, mark;

	ChimCuts_End ();
	if (!map_name || strlen (map_name) >= MAX_QPATH)
	{
		Said ("no frame map name");
		return;
	}
	strcpy (path, map_name);
	dot = strrchr (path, '.');
	if (!dot || strchr (dot, '/'))
		dot = path + strlen (path);
	strcpy (dot, ".cut");
	length = COM_FOpenFile (path, &f);
	if (!f)
	{
		Said ("none beside the frame map (each placement on its own)");
		return;
	}
	if (fread (head, 1, CUTS_HEADER, f) != CUTS_HEADER ||
		!ChimCuts_Header (head, length, chim_frame.frame.cx, chim_frame.frame.cy, &n, &m, &crc))
	{
		fclose (f);
		Said ("invalid file or another frame's (refused)");
		return;
	}
	body_bytes = n*CUTS_BOX + m*CUTS_MEMBER;
	keep = 24*n + 4*m + ((2*m + 3) & ~3L);
	if (hunk_spare < keep + body_bytes + 64)
	{
		fclose (f);
		Said ("no room in the Hunk above chim_reserve_kib");
		return;
	}
	boxes = Hunk_AllocName ((int)(24*n + 4), "chimcutbox");
	pids = Hunk_AllocName ((int)(4*m + 4), "chimcutpid");
	which = Hunk_AllocName ((int)(2*m + 4), "chimcutwhich");
	/* The body is read above them and given back once converted (the Hunk is
	 * a stack; nothing else allocates in between). */
	mark = Hunk_LowMark ();
	body = Hunk_AllocName ((int)body_bytes + 4, "chimcutbody");
	if ((long)fread (body, 1, body_bytes, f) != body_bytes || !ChimCuts_Body (body, n, m, crc, boxes, pids, which))
	{
		fclose (f);
		Hunk_FreeToLowMark (mark);
		ChimCuts_End ();	/* the tables' blocks go back with the map */
		Said ("damaged (refused)");
		return;
	}
	fclose (f);
	Hunk_FreeToLowMark (mark);
	structures = n;
	members = m;
	why[0] = 0;
	if (chim_debug.value)
		Con_Printf ("CHIM cut groups %s: %ld structures, %ld placements\n", path, structures, members);
}

/* chim_status line: what the frame map's cut groups hold. */
void ChimCuts_Report (void)
{
	if (members)
		Con_Printf ("cut groups: %ld structures, %ld placements (used with dbg cut groups on)\n", structures, members);
	else
		Con_Printf ("cut groups: none (%s)\n", why[0] ? why : "not a CHIM frame map");
}
