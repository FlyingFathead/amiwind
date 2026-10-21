/* SPDX-License-Identifier: GPL-2.0-or-later
 * Generated terrain records (world format 0.11, EXPERIMENTAL; tools/chim/thgt.py writes them): the render part of a
 * chunk terrain's brush image generated from its heights and the facts the builder stored, the same bytes as the
 * TERR record it replaces, then loaded by the usual loaders. The rule is the builder's regular path
 * (chim.terrain.chunk_terrain), mirrored line for line from thgt.py generate(): axial splits on the tile grid, the
 * tile diagonal where a tile is two triangles, the ground plane node, the cut of a ground polygon whose texture span
 * passes 240 texels, the water plane node and water face where the tile lies under water and the ground cut where the
 * water line crosses it. The planes and the standing hull are stored (chim_terc.c payloads), so no floating-point
 * arithmetic beyond copies, sums of whole units, comparisons and the crossing point of an edge and a cut
 * (p + (q - p) * d / (d - e) in double, as the builder computes it) is done: floor and ceil are taken from the bits
 * (the 68040 has no FINT/FINTRZ), and on the 68k the FPU's rounding precision is set to double while generating and
 * restored after (ChimThgt_Generate).
 *
 * Record version 2 holds the converter's own triangles instead (the 32-unit samples of each tile and the triangles
 * as sample indices, as the builder gave them): the irregular path (region_subtree, split_line, split_keep,
 * clean_xy, ground_plane), computed in IEEE double in thgt.py's order, square roots included (FSQRT, which the
 * 68040 has).
 *
 * Two passes: the first counts every lump (the image layout), the second writes it. */
#include <math.h>
#include <stdlib.h>
#include <string.h>
#include "chim_format.h"
#include "chim_terc.h"
#include "chim_thgt.h"

#define BSP_HEADER		(4 + 15*8)
#define TEX_SPECIAL		1
#define CONTENTS_EMPTY	(-1)
#define CONTENTS_WATER	(-3)
#define MAX_TEXINFO		64
#define MAX_CALL_VERTS	32		/* thgt.py MAX_CALL_VERTS (edges: twice as many) */
#define MAX_POLY		16		/* corners of one polygon after splits and the water line (thgt.py MAX_POLY) */
#define MAX_PIECES		16		/* pieces of one ground polygon after the texture splits */

static const int file_order[15] = {3, 12, 13, 2, 8, 1, 6, 7, 11, 4, 10, 14, 5, 0, 9};
/* thgt.py PAIRS: (s, t) of each base axis pair */
static const float pair_axes[3][2][3] = {{{1, 0, 0}, {0, -1, 0}}, {{0, 1, 0}, {0, 0, -1}}, {{1, 0, 0}, {0, 0, -1}}};

typedef struct
{
	/* the record */
	int			version, nx, ny, nodes, light, light_samples, water_slot;
	float		x0, y0, x1, y1, floor_z, ceiling, water, step;
	long		croot;
	const unsigned char *heights, *tiles, *tris, *node_planes, *refs, *planes, *clip;
	long		refs_bytes, planes_bytes, clip_bytes;
	/* the image being written (NULL in the counting pass) and where each lump starts */
	unsigned char *img;
	long		at[15], len[15], room;
	/* counters (both passes) */
	long		verts, edges, surfedges, faces, texinfo, leaves, marks, node_count;
	int			tx_key[MAX_TEXINFO];
	int			bad;
	chim_thgt_stats_t *stats;
	struct { double pt[MAX_PIECES][MAX_POLY][3]; int n[MAX_PIECES], count; } pieces;	/* the texture split's pieces */
} gen_t;

static void PutLE32 (unsigned char *p, unsigned long v)
{
	p[0] = (unsigned char)v; p[1] = (unsigned char)(v >> 8); p[2] = (unsigned char)(v >> 16); p[3] = (unsigned char)(v >> 24);
}

static void PutLE16 (unsigned char *p, unsigned v)
{
	p[0] = (unsigned char)v; p[1] = (unsigned char)(v >> 8);
}

static void PutF32 (unsigned char *p, float f)
{
	unsigned long u;
	unsigned int w;
	memcpy (&w, &f, 4);
	u = w;
	PutLE32 (p, u);
}

/* floor of a float from its bits (exact; no FPU rounding instruction) */
static long FloorF (float f)
{
	unsigned int u;
	int e, sign;
	unsigned long m, ip, frac;
	long v;
	memcpy (&u, &f, 4);
	if (!(u & 0x7fffffffu))
		return 0;
	sign = (int)(u >> 31);
	e = (int)((u >> 23) & 255) - 127;
	m = (u & 0x7fffffu) | 0x800000u;
	if (e < 0)
		return sign ? -1 : 0;
	if (e >= 23)
	{
		v = (long)(m << (e - 23 > 7 ? 7 : e - 23));		/* |f| < 2^31: callers stay far below */
		return sign ? -v : v;
	}
	ip = m >> (23 - e);
	frac = m & ((1ul << (23 - e)) - 1);
	v = (long)ip;
	if (sign)
	{
		v = -v;
		if (frac)
			v--;
	}
	return v;
}

static long CeilF (float f)
{
	return -FloorF (-f);
}

static float Height (gen_t *g, int i, int j)
{
	return ChimFormat_F32 (g->heights + 4*(j*(g->nx + 1) + i));
}

static int TexinfoOf (gen_t *g, int pair, int slot, int flags)
{
	int key = (pair << 16) | (slot << 1) | flags, k;
	for (k=0 ; k<g->texinfo ; k++)
		if (g->tx_key[k] == key)
			return k;
	if (g->texinfo >= MAX_TEXINFO)
	{
		g->bad = 1;
		return 0;
	}
	g->tx_key[g->texinfo] = key;
	if (g->img)
	{
		unsigned char *q = g->img + g->at[6] + 40*g->texinfo;
		int c;
		for (c=0 ; c<3 ; c++)
		{
			PutF32 (q + 4*c, pair_axes[pair][0][c]);
			PutF32 (q + 16 + 4*c, pair_axes[pair][1][c]);
		}
		PutF32 (q + 12, 0);
		PutF32 (q + 28, 0);
		PutLE32 (q + 32, (unsigned long)slot);
		PutLE32 (q + 36, (unsigned long)flags);
	}
	return g->texinfo++;
}

typedef double point_t[3];

typedef struct
{
	const point_t	*pts;
	int			n, pair, slot, flags, side, light;
} surface_t;

/* The two 32-bit words of a double (high first), whatever the host's byte order. */
static void DoubleWords (double d, unsigned long *hi, unsigned long *lo)
{
	unsigned char b[8], ob[8];
	double one = 1.0;
	memcpy (b, &d, 8);
	memcpy (ob, &one, 8);
	if (ob[7] == 0x3f)		/* little-endian host */
	{
		*hi = (unsigned long)b[7] << 24 | (unsigned long)b[6] << 16 | (unsigned long)b[5] << 8 | b[4];
		*lo = (unsigned long)b[3] << 24 | (unsigned long)b[2] << 16 | (unsigned long)b[1] << 8 | b[0];
	}
	else
	{
		*hi = (unsigned long)b[0] << 24 | (unsigned long)b[1] << 16 | (unsigned long)b[2] << 8 | b[3];
		*lo = (unsigned long)b[4] << 24 | (unsigned long)b[5] << 16 | (unsigned long)b[6] << 8 | b[7];
	}
}

/* floor of a double from its bits (no FPU rounding instruction; |d| < 2^31) */
static long FloorD (double d)
{
	unsigned long hi, lo, ip, frac_hi, frac_lo;
	int e, sign, k;
	long v;
	DoubleWords (d, &hi, &lo);
	if (!(hi & 0x7fffffffu) && !lo)
		return 0;
	sign = (int)(hi >> 31);
	e = (int)((hi >> 20) & 0x7ff) - 1023;
	if (e < 0)
		return sign ? -1 : 0;
	if (e > 30)
		return 0;			/* out of range: callers stay far below */
	/* the mantissa 1.f (52 bits): the integer part is the leading 1 and the top e bits of f */
	ip = 1;
	frac_hi = hi & 0xfffffu;
	frac_lo = lo;
	for (k=0 ; k<e ; k++)
	{
		ip = (ip << 1) | ((frac_hi >> 19) & 1);
		frac_hi = ((frac_hi << 1) & 0xfffffu) | ((frac_lo >> 31) & 1);
		frac_lo = (frac_lo << 1) & 0xfffffffful;
	}
	v = (long)ip;
	if (sign)
	{
		v = -v;
		if (frac_hi || frac_lo)
			v--;
	}
	return v;
}

static long CeilD (double d)
{
	return -FloorD (-d);
}

/* round half to even of v (|v| < 2^31), from the bits: Python's round() of a float, without FINT */
static long RoundHE (double v)
{
	long k = FloorD (v);
	double f = v - (double)k;
	if (f > 0.5 || (f == 0.5 && (k & 1)))
		k++;
	return k;
}

/* p + (q - p) * d / (d - e) per component: the generator's one computed coordinate (IEEE double; the 68k FPU is set
 * to double precision while it runs, ChimThgt_Generate) */
static void Crossing (const double *p, const double *q, double d, double e, double *out)
{
	int k;
	for (k=0 ; k<3 ; k++)
		out[k] = p[k] + (q[k] - p[k]) * d / (d - e);
}

/* BrushLumps.faces: one vertex and edge map per call; the points (counter-clockwise) stored reversed. */
static long Emit (gen_t *g, const surface_t *s, int count, int plane)
{
	long vkey[MAX_CALL_VERTS][3];
	long vid[MAX_CALL_VERTS], first = g->faces, ea[MAX_CALL_VERTS*2], eb[MAX_CALL_VERTS*2], eid[MAX_CALL_VERTS*2];
	int nv = 0, ne = 0, k, j, m;
	for (k=0 ; k<count ; k++)
	{
		long vs[MAX_POLY], firstedge = g->surfedges;
		int tx = TexinfoOf (g, s[k].pair, s[k].slot, s[k].flags);
		if (s[k].n > MAX_POLY)
		{
			g->bad = 1;
			return first;
		}
		for (j=0 ; j<s[k].n ; j++)
		{
			const double *p = s[k].pts[s[k].n - 1 - j];
			long key[3];
			key[0] = RoundHE (p[0] * 1e5); key[1] = RoundHE (p[1] * 1e5); key[2] = RoundHE (p[2] * 1e5);
			for (m=0 ; m<nv ; m++)
				if (vkey[m][0] == key[0] && vkey[m][1] == key[1] && vkey[m][2] == key[2])
					break;
			if (m == nv)
			{
				if (nv >= MAX_CALL_VERTS)
				{
					g->bad = 1;
					return first;
				}
				vkey[nv][0] = key[0]; vkey[nv][1] = key[1]; vkey[nv][2] = key[2];
				vid[nv] = g->verts;
				if (g->img)
				{
					unsigned char *q = g->img + g->at[3] + 12*g->verts;
					PutF32 (q, (float)p[0]); PutF32 (q + 4, (float)p[1]); PutF32 (q + 8, (float)p[2]);
				}
				g->verts++;
				nv++;
			}
			vs[j] = vid[m];
		}
		for (j=0 ; j<s[k].n ; j++)
		{
			long a = vs[j], c = vs[(j + 1) % s[k].n], ed = 0;
			for (m=0 ; m<ne ; m++)
			{
				if (ea[m] == a && eb[m] == c)
				{
					ed = eid[m];
					break;
				}
				if (ea[m] == c && eb[m] == a)
				{
					ed = -eid[m];
					break;
				}
			}
			if (m == ne)
			{
				if (ne >= MAX_CALL_VERTS*2)
				{
					g->bad = 1;
					return first;
				}
				ea[ne] = a; eb[ne] = c; eid[ne] = g->edges; ne++;
				ed = g->edges;
				if (g->img)
				{
					unsigned char *q = g->img + g->at[12] + 4*g->edges;
					PutLE16 (q, (unsigned)a);
					PutLE16 (q + 2, (unsigned)c);
				}
				g->edges++;
			}
			if (g->img)
				PutLE32 (g->img + g->at[13] + 4*g->surfedges, (unsigned long)ed);
			g->surfedges++;
		}
		if (g->img)
		{
			unsigned char *q = g->img + g->at[7] + 20*g->faces;
			PutLE16 (q, (unsigned)plane);
			PutLE16 (q + 2, (unsigned)s[k].side);
			PutLE32 (q + 4, (unsigned long)firstedge);
			PutLE16 (q + 8, (unsigned)s[k].n);
			PutLE16 (q + 10, (unsigned)tx);
			q[12] = (unsigned char)(s[k].light ? 0 : 255);
			q[13] = q[14] = q[15] = 255;
			PutLE32 (q + 16, s[k].light ? 0ul : 0xfffffffful);
		}
		g->faces++;
	}
	return first;
}

/* A leaf: contents, bounds as stored shorts, the marksurfaces of faces [first, first + n), then MORE. */
static int Leaf (gen_t *g, int contents, const long box[6], long first, long n, const long *more, long nmore)
{
	long k;
	if (g->img)
	{
		unsigned char *q = g->img + g->at[10] + 28*g->leaves;
		int c;
		PutLE32 (q, (unsigned long)(long)contents);
		PutLE32 (q + 4, 0xfffffffful);
		for (c=0 ; c<6 ; c++)
			PutLE16 (q + 8 + 2*c, (unsigned)box[c]);
		PutLE16 (q + 20, (unsigned)g->marks);
		PutLE16 (q + 22, (unsigned)(n + nmore));
		q[24] = q[25] = q[26] = q[27] = 0;
		for (k=0 ; k<n ; k++)
			PutLE16 (g->img + g->at[11] + 2*(g->marks + k), (unsigned)(first + k));
		for (k=0 ; k<nmore ; k++)
			PutLE16 (g->img + g->at[11] + 2*(g->marks + n + k), (unsigned)more[k]);
	}
	g->marks += n + nmore;
	return -1 - (int)(g->leaves++);
}

static void Node (gen_t *g, long index, int front, int back, const long box[6], long firstface, long numfaces)
{
	unsigned char *q;
	int c;
	if (!g->img)
		return;
	if (index >= g->nodes)
	{
		g->bad = 1;
		return;
	}
	q = g->img + g->at[5] + 24*index;
	PutLE32 (q, (unsigned long)ChimFormat_U16 (g->node_planes + 2*index));
	PutLE16 (q + 4, (unsigned)front);
	PutLE16 (q + 6, (unsigned)back);
	for (c=0 ; c<6 ; c++)
		PutLE16 (q + 8 + 2*c, (unsigned)box[c]);
	PutLE16 (q + 20, (unsigned)firstface);
	PutLE16 (q + 22, (unsigned)numfaces);
}

static int PlaneOf (gen_t *g, long index)
{
	if (index >= g->nodes)
	{
		g->bad = 1;
		return 0;
	}
	return ChimFormat_U16 (g->node_planes + 2*index);
}

/* mesh_geometry.split_surface: a face whose texture span passes 240 texels (1/16 guard, 16-texel grid) is cut 224
 * texels from its low line, the back part first; the texture axes are whole units, so the spans are exact. */
static void Split (gen_t *g, const point_t *poly, int n, int pair)
{
	double uv[MAX_POLY][2], mn, mx, cut, dist[MAX_POLY];
	point_t front[MAX_POLY], back[MAX_POLY];
	int a, i, j, k, nf, nb;
	long lo, hi;
	for (i=0 ; i<n ; i++)
		for (a=0 ; a<2 ; a++)
		{
			double v = 0;
			for (k=0 ; k<3 ; k++)
				v += poly[i][k] * pair_axes[pair][a][k];
			uv[i][a] = v;
		}
	for (a=0 ; a<2 ; a++)
	{
		mn = mx = uv[0][a];
		for (i=1 ; i<n ; i++)
		{
			if (uv[i][a] < mn) mn = uv[i][a];
			if (uv[i][a] > mx) mx = uv[i][a];
		}
		lo = FloorD ((mn - 0.0625) / 16) * 16;
		hi = CeilD ((mx + 0.0625) / 16) * 16;
		if (hi - lo <= 240)
			continue;
		cut = (double)(lo + 224);
		for (i=0 ; i<n ; i++)
			dist[i] = uv[i][a] - cut;
		nf = nb = 0;
		for (i=0 ; i<n ; i++)
		{
			double d, e;
			j = (i + 1) % n;
			d = dist[i];
			e = dist[j];
			if (nf >= MAX_POLY - 1 || nb >= MAX_POLY - 1)
			{
				g->bad = 1;
				return;
			}
			if (d <= 1e-6)
				memcpy (back[nb++], poly[i], sizeof(point_t));
			if (d >= -1e-6)
				memcpy (front[nf++], poly[i], sizeof(point_t));
			if ((d > 1e-6 && e < -1e-6) || (d < -1e-6 && e > 1e-6))
			{
				Crossing (poly[i], poly[j], d, e, front[nf]);
				memcpy (back[nb], front[nf], sizeof(point_t));
				nf++;
				nb++;
			}
		}
		if (nb < 3 || nf < 3)
		{
			g->bad = 1;
			return;
		}
		Split (g, (const point_t *)back, nb, pair);
		Split (g, (const point_t *)front, nf, pair);
		return;
	}
	if (g->pieces.count >= MAX_PIECES)
	{
		g->bad = 1;
		return;
	}
	memcpy (g->pieces.pt[g->pieces.count], poly, sizeof(point_t)*(size_t)n);
	g->pieces.n[g->pieces.count++] = n;
}

/* ---- record version 2, the converter's own triangles: chim.terrain.chunk_terrain's irregular path (irregular_tile,
 * region_subtree, surface_subtree), mirrored from thgt.py generate(): every value in IEEE double in the same order
 * (sums left to right, lengths as the square root of the sum of squares). */

#define MAX_ITEMS		64		/* ground pieces of one region */
#define ARENA_POINTS	6144	/* corners of the pieces alive along one region path (thgt.py ARENA) */

static point_t arena[ARENA_POINTS];

typedef struct
{
	long	at;			/* first corner in the arena */
	int		n;
} item_t;

static float Sample (gen_t *g, int gx, int gy)
{
	return ChimFormat_F32 (g->heights + 4*((long)gy*(4*g->nx + 1) + gx));
}

static double AreaXY (const point_t *p, int n)
{
	double s = 0;
	int k;
	for (k=0 ; k<n ; k++)
		s += p[k][0] * p[(k + 1) % n][1] - p[k][1] * p[(k + 1) % n][0];
	return 0.5 * s;
}

static void Cross (const double *a, const double *b, double *n)
{
	n[0] = a[1] * b[2] - a[2] * b[1];
	n[1] = a[2] * b[0] - a[0] * b[2];
	n[2] = a[0] * b[1] - a[1] * b[0];
}

static double Length (const double *n)
{
	return sqrt (n[0] * n[0] + n[1] * n[1] + n[2] * n[2]);
}

static double Abs (double v)
{
	return v < 0 ? -v : v;
}

/* chim.terrain.ground_plane: the largest fan cross product, unit, upward; d at the first corner */
static void GroundPlane (const point_t *p, int n, double *nrm, double *d)
{
	double best[3] = {0, 0, 0}, bl = 0, a[3], b[3], c[3], l;
	int i, k, have = 0;
	for (i=1 ; i<n-1 ; i++)
	{
		for (k=0 ; k<3 ; k++)
		{
			a[k] = p[i][k] - p[0][k];
			b[k] = p[i+1][k] - p[0][k];
		}
		Cross (a, b, c);
		l = Length (c);
		if (!have || l > bl)
		{
			best[0] = c[0]; best[1] = c[1]; best[2] = c[2];
			bl = l;
			have = 1;
		}
	}
	nrm[0] = best[0] / bl; nrm[1] = best[1] / bl; nrm[2] = best[2] / bl;
	if (nrm[2] < 0)
	{
		nrm[0] = -nrm[0]; nrm[1] = -nrm[1]; nrm[2] = -nrm[2];
	}
	*d = nrm[0] * p[0][0] + nrm[1] * p[0][1] + nrm[2] * p[0][2];
}

/* chim.terrain.split_keep: the part of a polygon on one side (keep 1 front, -1 back) of a vertical plane */
static int SplitKeep (gen_t *g, const point_t *p, int n, const double *nrm, double d, double keep, point_t *out)
{
	int i, k, m = 0;
	for (i=0 ; i<n ; i++)
	{
		const double *a = p[i], *q = p[(i + 1) % n];
		double dp = keep * (nrm[0] * a[0] + nrm[1] * a[1] - d), dq = keep * (nrm[0] * q[0] + nrm[1] * q[1] - d);
		if (dp >= -1e-9)
		{
			if (m >= MAX_POLY)
			{
				g->bad = 1;
				return 0;
			}
			memcpy (out[m++], a, sizeof(point_t));
		}
		if ((dp > 1e-9 && dq < -1e-9) || (dp < -1e-9 && dq > 1e-9))
		{
			double t = dp / (dp - dq);
			if (m >= MAX_POLY)
			{
				g->bad = 1;
				return 0;
			}
			for (k=0 ; k<3 ; k++)
				out[m][k] = a[k] + (q[k] - a[k]) * t;
			m++;
		}
	}
	return m;
}

/* chim.terrain.clean_xy: no repeated or collinear corners (in plan) */
static int CleanXY (point_t *p, int n)
{
	int i, m = 0, changed;
	const double eps = 1e-7;
	for (i=0 ; i<n ; i++)
		if (!m || Abs (p[i][0] - p[m-1][0]) > eps || Abs (p[i][1] - p[m-1][1]) > eps)
		{
			if (m != i)
				memcpy (p[m], p[i], sizeof(point_t));
			m++;
		}
	if (m > 1 && Abs (p[0][0] - p[m-1][0]) <= eps && Abs (p[0][1] - p[m-1][1]) <= eps)
		m--;
	changed = 1;
	while (changed && m > 3)
	{
		changed = 0;
		for (i=0 ; i<m ; i++)
		{
			const double *a = p[(i + m - 1) % m], *b = p[i], *c = p[(i + 1) % m];
			if (Abs ((b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])) <= eps)
			{
				memmove (p[i], p[i+1], sizeof(point_t) * (size_t)(m - 1 - i));
				m--;
				changed = 1;
				break;
			}
		}
	}
	return m;
}

/* chim.terrain.split_line: through a piece's edge that cuts the region, the fewest pieces cut, then the most even */
static int SplitLine (gen_t *g, const point_t *region, int rn, const item_t *items, int ni, double *nrm, double *d)
{
	long best_cuts = 0, best_even = 0, cuts, front, back;
	int found = 0, it, i, k, j;
	for (it=0 ; it<ni ; it++)
	{
		const point_t *p = arena + items[it].at;
		int n = items[it].n;
		for (i=0 ; i<n ; i++)
		{
			const double *a = p[i], *b = p[(i + 1) % n];
			double ex = b[0] - a[0], ey = b[1] - a[1], l = sqrt (ex * ex + ey * ey), c[2], cd, mn, mx;
			if (l < 1e-6)
				continue;
			c[0] = ey / l; c[1] = -ex / l;
			if (c[0] < -1e-12 || (Abs (c[0]) <= 1e-12 && c[1] < 0))
			{
				c[0] = -c[0]; c[1] = -c[1];
			}
			cd = c[0] * a[0] + c[1] * a[1];
			mn = mx = c[0] * region[0][0] + c[1] * region[0][1] - cd;
			for (k=1 ; k<rn ; k++)
			{
				double s = c[0] * region[k][0] + c[1] * region[k][1] - cd;
				if (s < mn) mn = s;
				if (s > mx) mx = s;
			}
			if (mx <= 1e-6 || mn >= -1e-6)
				continue;
			cuts = front = back = 0;
			for (j=0 ; j<ni ; j++)
			{
				const point_t *q = arena + items[j].at;
				double qmn, qmx;
				qmn = qmx = c[0] * q[0][0] + c[1] * q[0][1] - cd;
				for (k=1 ; k<items[j].n ; k++)
				{
					double s = c[0] * q[k][0] + c[1] * q[k][1] - cd;
					if (s < qmn) qmn = s;
					if (s > qmx) qmx = s;
				}
				if (qmx > 1e-6 && qmn < -1e-6)
					cuts++;
				else if (qmx > 1e-6)
					front++;
				else
					back++;
			}
			if (!found || cuts < best_cuts || (cuts == best_cuts && labs (front - back) < best_even))
			{
				best_cuts = cuts;
				best_even = labs (front - back);
				nrm[0] = c[0]; nrm[1] = c[1];
				*d = cd;
				found = 1;
			}
		}
	}
	if (!found)
		g->bad = 1;
	return found;
}

/* clip_below (+ dedupe_points for the irregular path): the polygon at or under the water line, its crossings */
static int ClipBelow (gen_t *g, const point_t *p, int n, point_t *out)
{
	int j, m = 0;
	for (j=0 ; j<n ; j++)
	{
		double dp = p[j][2] - g->water, dq = p[(j + 1) % n][2] - g->water;
		if (dp <= 0)
		{
			if (m >= MAX_POLY)
			{
				g->bad = 1;
				return 0;
			}
			memcpy (out[m++], p[j], sizeof(point_t));
		}
		if ((dp < 0 && 0 < dq) || (dq < 0 && 0 < dp))
		{
			if (m >= MAX_POLY)
			{
				g->bad = 1;
				return 0;
			}
			Crossing (p[j], p[(j + 1) % n], dp, dq, out[m++]);
		}
	}
	return m >= 3 ? m : 0;
}

static double MaxDiff (const double *a, const double *b)
{
	double m = Abs (a[0] - b[0]), v;
	v = Abs (a[1] - b[1]); if (v > m) m = v;
	v = Abs (a[2] - b[2]); if (v > m) m = v;
	return m;
}

static int Dedupe (point_t *p, int n)
{
	int i, m = 0;
	for (i=0 ; i<n ; i++)
		if (!m || MaxDiff (p[i], p[m-1]) > 1e-6)
		{
			if (m != i)
				memcpy (p[m], p[i], sizeof(point_t));
			m++;
		}
	if (m > 1 && MaxDiff (p[0], p[m-1]) <= 1e-6)
		m--;
	return m >= 3 ? m : 0;
}

static void BoxOf (double x0, double y0, double z0, double x1, double y1, float ceiling, long box[6])
{
	box[0] = FloorD (x0); box[1] = FloorD (y0); box[2] = FloorD (z0);
	box[3] = CeilD (x1); box[4] = CeilD (y1); box[5] = CeilF (ceiling);
}

/* surface_subtree of the irregular path: the ground plane node over one region's polygon, water and air above */
static long IrrSurface (gen_t *g, const point_t *poly, int n, const double *xy, int slot, long box[6])
{
	long me = g->node_count++, first, numfaces, front;
	double a[3], b[3], nrm[3], l, best = -1.0, zlo = poly[0][2], water = g->water, comp[6];
	point_t low[MAX_POLY], rev[MAX_POLY];
	surface_t s[MAX_PIECES];
	long leafbox[6];
	int k, pair = -1, pi, low_n, j;
	for (k=0 ; k<3 ; k++)
	{
		a[k] = poly[1][k] - poly[0][k];
		b[k] = poly[2][k] - poly[0][k];
	}
	Cross (a, b, nrm);
	l = Length (nrm);
	nrm[0] = nrm[0] / l; nrm[1] = nrm[1] / l; nrm[2] = nrm[2] / l;
	comp[0] = nrm[2]; comp[1] = -nrm[2]; comp[2] = nrm[0]; comp[3] = -nrm[0]; comp[4] = nrm[1]; comp[5] = -nrm[1];
	for (k=0 ; k<6 ; k++)
		if (comp[k] > best)
		{
			best = comp[k];
			pair = k / 2;
		}
	if (pair < 0)
	{
		g->bad = 1;
		return me;
	}
	for (j=1 ; j<n ; j++)
		if (poly[j][2] < zlo)
			zlo = poly[j][2];
	BoxOf (xy[0], xy[1], (zlo < water ? zlo : water) - 1, xy[2], xy[3], g->ceiling, box);
	pi = PlaneOf (g, me);
	g->pieces.count = 0;
	Split (g, poly, n, pair);
	if (g->bad)
		return me;
	for (j=0 ; j<g->pieces.count ; j++)
	{
		s[j].pts = (const point_t *)g->pieces.pt[j]; s[j].n = g->pieces.n[j]; s[j].pair = pair; s[j].slot = slot;
		s[j].flags = 0; s[j].side = 0; s[j].light = 1;
	}
	numfaces = g->pieces.count;
	first = Emit (g, s, g->pieces.count, pi);
	low_n = ClipBelow (g, poly, n, low);
	if (g->bad)
		return me;
	if (low_n)
		low_n = Dedupe (low, low_n);
	if (low_n && zlo < water)
	{
		for (j=0 ; j<low_n ; j++)
			low[j][2] = water;
	}
	else
		low_n = 0;
	if (low_n && Abs (AreaXY ((const point_t *)low, low_n)) > 1e-9)
	{
		long wbox[6], water_faces[2], wn, k2;
		surface_t w[2];
		int wpi;
		if (g->water_slot == 0xff)
		{
			g->bad = 1;
			return me;
		}
		for (j=0 ; j<low_n ; j++)
			memcpy (rev[j], low[low_n - 1 - j], sizeof(point_t));
		wn = g->node_count++;
		BoxOf (xy[0], xy[1], zlo - 1, xy[2], xy[3], g->ceiling, wbox);
		wpi = PlaneOf (g, wn);
		w[0].pts = (const point_t *)low; w[0].n = low_n; w[0].pair = 0; w[0].slot = g->water_slot;
		w[0].flags = TEX_SPECIAL; w[0].side = 0; w[0].light = 0;
		w[1] = w[0];
		w[1].pts = (const point_t *)rev; w[1].side = 1;
		water_faces[0] = Emit (g, w, 2, wpi);
		water_faces[1] = water_faces[0] + 1;
		BoxOf (xy[0], xy[1], water, xy[2], xy[3], g->ceiling, leafbox);
		k2 = Leaf (g, CONTENTS_EMPTY, leafbox, first, numfaces, water_faces, 2);
		BoxOf (xy[0], xy[1], zlo, xy[2], xy[3], g->ceiling, leafbox);
		leafbox[5] = CeilD (water);
		front = Leaf (g, CONTENTS_WATER, leafbox, first, numfaces, water_faces, 2);
		Node (g, wn, (int)k2, (int)front, wbox, water_faces[0], 2);
		Node (g, me, (int)wn, -1, box, first, numfaces);
	}
	else
	{
		BoxOf (xy[0], xy[1], zlo, xy[2], xy[3], g->ceiling, leafbox);
		front = Leaf (g, CONTENTS_EMPTY, leafbox, first, numfaces, NULL, 0);
		Node (g, me, (int)front, -1, box, first, numfaces);
	}
	g->stats->surfaces++;
	g->stats->texture_splits += (unsigned long)(numfaces - 1);
	return me;
}

/* region_subtree: split the region on the pieces' edges until one ground plane is left */
static long Region (gen_t *g, const point_t *region, int rn, const item_t *items, int ni, int slot, long *top,
	long box[6])
{
	double xy[4], n0[3], d0, nrm[3], d, zlo;
	int k, i, uniform = 1;
	long me;
	if (g->bad || ni < 1)
	{
		g->bad = 1;
		return 0;
	}
	xy[0] = xy[2] = region[0][0];
	xy[1] = xy[3] = region[0][1];
	for (k=1 ; k<rn ; k++)
	{
		if (region[k][0] < xy[0]) xy[0] = region[k][0];
		if (region[k][1] < xy[1]) xy[1] = region[k][1];
		if (region[k][0] > xy[2]) xy[2] = region[k][0];
		if (region[k][1] > xy[3]) xy[3] = region[k][1];
	}
	GroundPlane (arena + items[0].at, items[0].n, n0, &d0);
	for (i=1 ; i<ni && uniform ; i++)
	{
		double nn[3], dd;
		GroundPlane (arena + items[i].at, items[i].n, nn, &dd);
		if (!(Abs (nn[0] - n0[0]) < 1e-6 && Abs (nn[1] - n0[1]) < 1e-6 && Abs (nn[2] - n0[2]) < 1e-6 &&
			Abs (dd - d0) < 1e-3))
			uniform = 0;
	}
	if (uniform)
	{
		point_t face[MAX_POLY];
		for (k=0 ; k<rn ; k++)
		{
			long kx = RoundHE (region[k][0] * 1e6), ky = RoundHE (region[k][1] * 1e6);
			int found = 0;
			/* the last piece corner with this plan position (a dict: the last one written wins) */
			for (i=ni-1 ; i>=0 && !found ; i--)
			{
				const point_t *p = arena + items[i].at;
				int j;
				for (j=items[i].n-1 ; j>=0 ; j--)
					if (RoundHE (p[j][0] * 1e6) == kx && RoundHE (p[j][1] * 1e6) == ky)
					{
						face[k][2] = p[j][2];
						found = 1;
						break;
					}
			}
			face[k][0] = region[k][0];
			face[k][1] = region[k][1];
			if (!found)
				face[k][2] = (d0 - n0[0] * region[k][0] - n0[1] * region[k][1]) / n0[2];
		}
		return IrrSurface (g, (const point_t *)face, rn, xy, slot, box);
	}
	if (!SplitLine (g, region, rn, items, ni, nrm, &d))
		return 0;
	zlo = arena[items[0].at][2];
	for (i=0 ; i<ni ; i++)
		for (k=0 ; k<items[i].n ; k++)
			if (arena[items[i].at + k][2] < zlo)
				zlo = arena[items[i].at + k][2];
	me = g->node_count++;
	g->stats->splits++;
	{
		long child[2], cb[2][6], base = *top;
		double keep;
		int side;
		for (side=0 ; side<2 ; side++)
		{
			point_t part[MAX_POLY], plan[MAX_POLY];
			item_t kept[MAX_ITEMS];
			int pn, nk = 0;
			keep = side ? -1.0 : 1.0;
			for (k=0 ; k<rn ; k++)
			{
				plan[k][0] = region[k][0]; plan[k][1] = region[k][1]; plan[k][2] = 0.0;
			}
			pn = SplitKeep (g, (const point_t *)plan, rn, nrm, d, keep, part);
			pn = CleanXY (part, pn);
			for (i=0 ; i<ni && !g->bad ; i++)
			{
				point_t piece[MAX_POLY];
				int m = SplitKeep (g, (const point_t *)(arena + items[i].at), items[i].n, nrm, d, keep, piece);
				if (m >= 3 && Abs (AreaXY ((const point_t *)piece, m)) > 1e-6)
				{
					if (nk >= MAX_ITEMS || *top + m > ARENA_POINTS)
					{
						g->bad = 1;
						break;
					}
					memcpy (arena[*top], piece, sizeof(point_t) * (size_t)m);
					kept[nk].at = *top;
					kept[nk].n = m;
					*top += m;
					nk++;
				}
			}
			if (g->bad || !nk || pn < 3)
			{
				g->bad = 1;
				return me;
			}
			child[side] = Region (g, (const point_t *)part, pn, kept, nk, slot, top, cb[side]);
			*top = base;
			if (g->bad)
				return me;
		}
		BoxOf (xy[0], xy[1], (zlo < g->water ? zlo : g->water) - 1, xy[2], xy[3], g->ceiling, box);
		Node (g, me, (int)child[0], (int)child[1], box, 0, 0);
		(void)PlaneOf (g, me);
	}
	return me;
}

static long IrrTile (gen_t *g, int i, int j, long box[6])
{
	long t = (long)j*g->nx + i, at = 0, top, k;
	int slot = g->tiles[2*t], count = g->tiles[2*t + 1], c, v;
	double x = (double)g->x0 + (double)i*g->step, y = (double)g->y0 + (double)j*g->step;
	item_t items[MAX_ITEMS];
	point_t region[4];
	for (k=0 ; k<t ; k++)
		at += g->tiles[2*k + 1];
	g->stats->tiles++;
	if (count < 1 || count > MAX_ITEMS || 3L*count > ARENA_POINTS)
	{
		g->bad = 1;
		return 0;
	}
	for (c=0 ; c<count ; c++)
	{
		point_t *p = arena + 3L*c;
		for (v=0 ; v<3 ; v++)
		{
			int id = g->tris[3*(at + c) + v], u = id % 5, w = id / 5;
			if (id > 24)
			{
				g->bad = 1;
				return 0;
			}
			p[v][0] = x + 32.0 * u;
			p[v][1] = y + 32.0 * w;
			p[v][2] = Sample (g, 4*i + u, 4*j + w);
		}
		if (AreaXY ((const point_t *)p, 3) < 0)
		{
			point_t tmp;
			memcpy (tmp, p[0], sizeof(point_t));
			memcpy (p[0], p[2], sizeof(point_t));
			memcpy (p[2], tmp, sizeof(point_t));
		}
		items[c].at = 3L*c;
		items[c].n = 3;
	}
	top = 3L*count;
	region[0][0] = x; region[0][1] = y;
	region[1][0] = x + g->step; region[1][1] = y;
	region[2][0] = x + g->step; region[2][1] = y + g->step;
	region[3][0] = x; region[3][1] = y + g->step;
	for (c=0 ; c<4 ; c++)
		region[c][2] = 0;
	return Region (g, (const point_t *)region, 4, items, count, slot, &top, box);
}

/* surface_subtree: returns the node index; BOX gets the node's bounds */
static long Surface (gen_t *g, const point_t *poly, int n, double x, double y, int pair, int slot, int under, long box[6])
{
	long me = g->node_count++, k, first, wn, numfaces;
	double zlo = poly[0][2], water = g->water;
	point_t flat[MAX_POLY], rev[MAX_POLY];
	int pi, front, wpi, j, low_n = 0;
	surface_t s[MAX_PIECES];
	long leafbox[6];
	for (j=1 ; j<n ; j++)
		if (poly[j][2] < zlo)
			zlo = poly[j][2];
	box[0] = FloorD (x); box[1] = FloorD (y); box[2] = FloorD (zlo < water ? zlo : water) - 1;
	box[3] = CeilD (x + g->step); box[4] = CeilD (y + g->step); box[5] = CeilF (g->ceiling);
	pi = PlaneOf (g, me);
	g->pieces.count = 0;
	Split (g, poly, n, pair);
	if (g->bad)
		return me;
	for (j=0 ; j<g->pieces.count ; j++)
	{
		s[j].pts = (const point_t *)g->pieces.pt[j]; s[j].n = g->pieces.n[j]; s[j].pair = pair; s[j].slot = slot;
		s[j].flags = 0; s[j].side = 0; s[j].light = 1;
	}
	numfaces = g->pieces.count;
	first = Emit (g, s, g->pieces.count, pi);
	if (under)
	{
		long wbox[6], water_faces[2];
		surface_t w[2];
		if (!(zlo < water))
		{
			g->bad = 1;
			return me;
		}
		/* clip_below: the corners at or under the water line and the crossings, at the water level */
		low_n = ClipBelow (g, poly, n, flat);
		if (low_n < 3)
		{
			g->bad = 1;
			return me;
		}
		for (j=0 ; j<low_n ; j++)
			flat[j][2] = water;
		for (j=0 ; j<low_n ; j++)
			memcpy (rev[j], flat[low_n - 1 - j], sizeof(point_t));
		wn = g->node_count++;
		wbox[0] = box[0]; wbox[1] = box[1]; wbox[2] = FloorD (zlo - 1); wbox[3] = box[3]; wbox[4] = box[4];
		wbox[5] = box[5];
		wpi = PlaneOf (g, wn);
		w[0].pts = (const point_t *)flat; w[0].n = low_n; w[0].pair = 0; w[0].slot = g->water_slot;
		w[0].flags = TEX_SPECIAL; w[0].side = 0; w[0].light = 0;
		w[1] = w[0];
		w[1].pts = (const point_t *)rev; w[1].side = 1;
		water_faces[0] = Emit (g, w, 2, wpi);
		water_faces[1] = water_faces[0] + 1;
		leafbox[0] = box[0]; leafbox[1] = box[1]; leafbox[2] = FloorD (water); leafbox[3] = box[3]; leafbox[4] = box[4];
		leafbox[5] = box[5];
		k = Leaf (g, CONTENTS_EMPTY, leafbox, first, numfaces, water_faces, 2);
		leafbox[2] = FloorD (zlo); leafbox[5] = CeilD (water);
		front = Leaf (g, CONTENTS_WATER, leafbox, first, numfaces, water_faces, 2);
		Node (g, wn, (int)k, front, wbox, water_faces[0], 2);
		Node (g, me, (int)wn, -1, box, first, numfaces);
	}
	else
	{
		leafbox[0] = box[0]; leafbox[1] = box[1]; leafbox[2] = FloorD (zlo); leafbox[3] = box[3]; leafbox[4] = box[4];
		leafbox[5] = box[5];
		front = Leaf (g, CONTENTS_EMPTY, leafbox, first, numfaces, NULL, 0);
		Node (g, me, front, -1, box, first, numfaces);
	}
	g->stats->surfaces++;
	g->stats->texture_splits += (unsigned long)(numfaces - 1);
	return me;
}

static long Tile (gen_t *g, int i, int j, long box[6])
{
	unsigned char slot = g->tiles[2*(j*g->nx + i)], facts = g->tiles[2*(j*g->nx + i) + 1];
	double x = (double)g->x0 + (double)i*g->step, y = (double)g->y0 + (double)j*g->step, zlo;
	point_t c[4], t0[3], t1[3];
	int under = (facts & 2) != 0, k;
	long me, front, back, b[6];
	c[0][0] = x; c[0][1] = y; c[0][2] = Height (g, i, j);
	c[1][0] = x + g->step; c[1][1] = y; c[1][2] = Height (g, i + 1, j);
	c[2][0] = x + g->step; c[2][1] = y + g->step; c[2][2] = Height (g, i + 1, j + 1);
	c[3][0] = x; c[3][1] = y + g->step; c[3][2] = Height (g, i, j + 1);
	g->stats->tiles++;
	if (facts & 1)
		return Surface (g, (const point_t *)c, 4, x, y, (facts >> 2) & 3, slot, under, box);
	zlo = c[0][2];
	for (k=1 ; k<4 ; k++)
		if (c[k][2] < zlo)
			zlo = c[k][2];
	me = g->node_count++;
	memcpy (t0[0], c[0], sizeof(point_t)); memcpy (t0[1], c[1], sizeof(point_t)); memcpy (t0[2], c[2], sizeof(point_t));
	memcpy (t1[0], c[0], sizeof(point_t)); memcpy (t1[1], c[2], sizeof(point_t)); memcpy (t1[2], c[3], sizeof(point_t));
	front = Surface (g, (const point_t *)t0, 3, x, y, (facts >> 2) & 3, slot, under, b);
	back = Surface (g, (const point_t *)t1, 3, x, y, (facts >> 4) & 3, slot, under, b);
	box[0] = FloorD (x); box[1] = FloorD (y); box[2] = FloorD (zlo < g->water ? zlo : g->water) - 1;
	box[3] = CeilD (x + g->step); box[4] = CeilD (y + g->step); box[5] = CeilF (g->ceiling);
	Node (g, me, (int)front, (int)back, box, 0, 0);
	(void)PlaneOf (g, me);
	return me;
}

static long Grid (gen_t *g, int i0, int j0, int i1, int j1, long box[6])
{
	long me, front, back, a[6], b[6];
	int mid, k;
	if (i1 - i0 == 1 && j1 - j0 == 1)
		return g->version == 2 ? IrrTile (g, i0, j0, box) : Tile (g, i0, j0, box);
	me = g->node_count++;
	g->stats->splits++;
	if (i1 - i0 >= j1 - j0)
	{
		mid = (i0 + i1) / 2;
		front = Grid (g, mid, j0, i1, j1, a);
		back = Grid (g, i0, j0, mid, j1, b);
	}
	else
	{
		mid = (j0 + j1) / 2;
		front = Grid (g, i0, mid, i1, j1, a);
		back = Grid (g, i0, j0, i1, mid, b);
	}
	for (k=0 ; k<3 ; k++)
	{
		box[k] = a[k] < b[k] ? a[k] : b[k];
		box[k+3] = a[k+3] > b[k+3] ? a[k+3] : b[k+3];
	}
	Node (g, me, (int)front, (int)back, box, 0, 0);
	(void)PlaneOf (g, me);
	return me;
}

static void Model (gen_t *g)
{
	unsigned char *q = g->img + g->at[14];
	PutF32 (q, g->x0); PutF32 (q + 4, g->y0); PutF32 (q + 8, g->floor_z);
	PutF32 (q + 12, g->x1); PutF32 (q + 16, g->y1); PutF32 (q + 20, g->ceiling);
	PutF32 (q + 24, 0); PutF32 (q + 28, 0); PutF32 (q + 32, 0);
	PutLE32 (q + 36, 0);
	PutLE32 (q + 40, (unsigned long)g->croot);
	PutLE32 (q + 44, (unsigned long)g->croot);
	PutLE32 (q + 48, (unsigned long)g->croot);
	PutLE32 (q + 52, 0);
	PutLE32 (q + 56, 0);
	PutLE32 (q + 60, (unsigned long)g->faces);
}

static int Run (gen_t *g)
{
	long box[6];
	g->verts = 0; g->edges = 1; g->surfedges = 0; g->faces = 0; g->texinfo = 0; g->leaves = 1; g->marks = 0;
	g->node_count = 0; g->bad = 0;
	if (g->img)
	{
		memcpy (g->img + g->at[10], "\xfe\xff\xff\xff\xff\xff\xff\xff", 8);	/* solid leaf 0: contents -2, visofs -1 */
		memset (g->img + g->at[10] + 8, 0, 20);
		PutLE32 (g->img + g->at[12], 0);										/* edge 0, never used */
	}
	Grid (g, 0, 0, g->nx, g->ny, box);
	return !g->bad && g->node_count == g->nodes;
}

int ChimThgt_Is (const unsigned char *data, long bytes)
{
	return bytes >= CHIM_THGT_HEAD_BYTES && !memcmp (data, "THG1", 4);
}

static int Generate (const unsigned char *src, long bytes, unsigned char *dst, long room, long *out,
	chim_thgt_stats_t *stats)
{
	static gen_t g;
	chim_thgt_stats_t dummy;
	long image, render, at, body, n_pl, n_clip, n_refs, count;
	int slot;
	memset (&g, 0, sizeof(g));
	memset (&dummy, 0, sizeof(dummy));
	g.stats = stats ? stats : &dummy;
	if (!ChimThgt_Is (src, bytes))
		return 0;
	g.version = ChimFormat_U16 (src+12);
	if (g.version != 1 && g.version != 2)
		return 0;
	image = (long)ChimFormat_U32 (src+4);
	render = (long)ChimFormat_U32 (src+8);
	g.nx = ChimFormat_U16 (src+14);
	g.ny = ChimFormat_U16 (src+16);
	g.nodes = ChimFormat_U16 (src+18);
	g.x0 = ChimFormat_F32 (src+20); g.y0 = ChimFormat_F32 (src+24);
	g.x1 = ChimFormat_F32 (src+28); g.y1 = ChimFormat_F32 (src+32);
	g.floor_z = ChimFormat_F32 (src+36); g.ceiling = ChimFormat_F32 (src+40);
	g.water = ChimFormat_F32 (src+44); g.step = ChimFormat_F32 (src+48);
	g.light_samples = ChimFormat_U16 (src+52);
	g.light = src[54];
	g.water_slot = src[55];
	n_pl = (long)ChimFormat_U32 (src+56);
	n_clip = (long)ChimFormat_U32 (src+60);
	n_refs = (long)ChimFormat_U32 (src+64);
	g.croot = (long)ChimFormat_U32 (src+68);
	if (g.nx < 1 || g.ny < 1 || g.nx > 64 || g.ny > 64 || image > room || image < BSP_HEADER || render > image)
		return 0;
	at = CHIM_THGT_HEAD_BYTES;
	g.heights = src + at;
	if (g.version == 1)
		at += 4L*(g.nx + 1)*(g.ny + 1);
	else
		at += 4L*(4*g.nx + 1)*(4*g.ny + 1);
	g.tiles = src + at;
	at += (2L*g.nx*g.ny + 3) & ~3L;
	if (g.version == 2)
	{
		long t, tris = 0;
		if (at + 2L*g.nx*g.ny > bytes)
			return 0;
		for (t=0 ; t<(long)g.nx*g.ny ; t++)
			tris += g.tiles[2*t + 1];
		g.tris = src + at;
		at += (3L*tris + 3) & ~3L;
	}
	g.node_planes = src + at;
	at += (2L*g.nodes + 3) & ~3L;
	g.refs = src + at;
	at += n_refs;
	g.planes = src + at;
	at += n_pl;
	g.clip = src + at;
	at += n_clip;
	if (at > bytes || n_refs < 4 || n_pl < 4 || n_clip < 4)
		return 0;
	count = (long)(g.refs[0] | (g.refs[1] << 8) | (g.refs[2] << 16) | ((unsigned long)g.refs[3] << 24));
	if (count < 0 || 4 + 4*count > n_refs)
		return 0;
	g.refs_bytes = 4 + 4*count;
	/* pass 1: the size of every lump */
	g.room = room;
	if (!Run (&g))
		return 0;
	g.len[3] = 12*g.verts; g.len[12] = 4*g.edges; g.len[13] = 4*g.surfedges; g.len[2] = g.refs_bytes;
	g.len[8] = g.light_samples; g.len[6] = 40*g.texinfo; g.len[7] = 20*g.faces; g.len[11] = 2*g.marks;
	g.len[4] = 0; g.len[10] = 28*g.leaves; g.len[14] = 64; g.len[5] = 24*g.nodes; g.len[0] = 0;
	if (!ChimTerc_Lump (g.planes[0], g.planes + 4, n_pl - 4, NULL, 0, 0x7fffffffL, &g.len[1]) ||
		!ChimTerc_Lump (g.clip[0], g.clip + 4, n_clip - 4, NULL, 0, 0x7fffffffL, &g.len[9]))
		return 0;
	/* the layout: chim.format.brush_image's (each lump on a 4-byte boundary, the render part before the hull) */
	body = BSP_HEADER;
	for (slot=0 ; slot<15 ; slot++)
	{
		int k = file_order[slot];
		if (k == 9 && body != render)
			return 0;
		body = (body + 3) & ~3L;
		g.at[k] = body;
		body += g.len[k];
	}
	body = (body + 3) & ~3L;
	if (body != image || body > room)
		return 0;
	/* pass 2: write */
	memset (dst, 0, (size_t)image);
	PutLE32 (dst, 29);
	for (slot=0 ; slot<15 ; slot++)
	{
		PutLE32 (dst + 4 + 8*slot, (unsigned long)g.at[slot]);
		PutLE32 (dst + 8 + 8*slot, (unsigned long)g.len[slot]);
	}
	g.img = dst;
	if (!Run (&g))
		return 0;
	memcpy (dst + g.at[2], g.refs, (size_t)g.refs_bytes);
	memset (dst + g.at[8], g.light, (size_t)g.light_samples);
	if (!ChimTerc_Lump (g.planes[0], g.planes + 4, n_pl - 4, dst, g.at[1], room, &count) || count != g.len[1] ||
		!ChimTerc_Lump (g.clip[0], g.clip + 4, n_clip - 4, dst, g.at[9], room, &count) || count != g.len[9])
		return 0;
	Model (&g);
	g.stats->records++;
	g.stats->vertexes += g.verts;
	g.stats->faces += g.faces;
	g.stats->nodes += g.nodes;
	g.stats->leaves += g.leaves;
	*out = image;
	return 1;
}

/* The generation with the 68k FPU rounding every operation to double precision (FPCR rounding precision bits), so
 * the crossings come out as in IEEE double arithmetic (the builder's); restored after. Other hosts: as they are. */
int ChimThgt_Generate (const unsigned char *src, long bytes, unsigned char *dst, long room, long *out,
	chim_thgt_stats_t *stats)
{
	int ok;
#if defined(__mc68000__) || defined(__m68k__)
	unsigned long fpcr, dbl;
	__asm__ volatile ("fmove.l %%fpcr,%0" : "=d" (fpcr));
	dbl = (fpcr & ~0xc0ul) | 0x80ul;
	__asm__ volatile ("fmove.l %0,%%fpcr" : : "d" (dbl));
#endif
	ok = Generate (src, bytes, dst, room, out, stats);
#if defined(__mc68000__) || defined(__m68k__)
	__asm__ volatile ("fmove.l %0,%%fpcr" : : "d" (fpcr));
#endif
	return ok;
}
