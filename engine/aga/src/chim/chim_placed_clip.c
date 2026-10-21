/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM placed collision. Used by world format 0.8 (EXPERIMENTAL: written only
 * by the builder's placement format 0.8; chim_chunks.c ClipModel takes it for
 * a placement whose model has a piece table). Worlds of 0.4-0.7 never reach
 * it and collide exactly as before.
 *
 * Today a CHIM model is stored once per mesh + scale + tilt: the builder
 * bakes scale and tilt into the geometry and expands each convex collision
 * piece by the standing player box (Minkowski sum with edge bevels,
 * prepare_mesh_bsp.standing_planes exact) into hull 1. Only yaw is left to
 * run time (chim_chunks.c ClipModel), and the trace is turned into the
 * model's frame, so the player box turns with the model.
 *
 * Here a placement carries the full rotation and a uniform scale, and the
 * mesh's collision is stored once, unexpanded: per convex piece its planes,
 * corners and edges (the edges as plane pairs, found offline). When a trace
 * first meets a placement, the piece is moved into the world (rotated
 * normals, scaled distances) and expanded there by the world-aligned box,
 * with every facet of the Minkowski sum:
 * - the piece's own planes, moved out by the box's support;
 * - the box's six faces at the piece's extremes (axial bevels);
 * - edge x box-axis planes that touch the piece (edge bevels): for an edge
 *   between planes a and b, the plane through it with normal e x axis is a
 *   facet when that normal lies between n_a and n_b (an O(1) test, no
 *   search over the corners).
 * The trace is then a point against convex pieces, as Quake 2's
 * CM_ClipBoxToBrush does it with a brush's bevels (the method, not the code).
 * OpenMW (apps/openmw/mwphysics/actor.cpp, object.cpp; rule, not code):
 * the default actor shape is a world-aligned box (actor collision shape type
 * 0) and an object's collision shape takes the reference's full rotation and
 * its uniform scale, which is what this computes.
 *
 * Union semantics follow SV_RecursiveHullCheck on the builder's piece chain
 * (outside any plane goes on to the next piece; on a plane counts as
 * outside): a hit is the first point where the segment goes from outside
 * every piece into one.
 */
#include "quakedef.h"
#include "chim_placed_clip.h"
#include "chim_format.h"

#define PLACED_DIST_EPSILON	(0.03125f)	/* world.c DIST_EPSILON */

chim_placed_stats_t chim_placed_stats;

void ChimPlaced_Matrix (float ax, float ay, float az, float m[3][3])
{
	/* prepare_scenery.reference_rotation: angles negated, R = Rx Ry Rz
	 * (the engine's table sine: libm's would reach FPU instructions the
	 * 68040 does not implement) */
	float cx, sx, cy, sy, cz, sz;
	float rx[3][3], ry[3][3], rz[3][3], t[3][3];
	int i, j, k;

	Q_SinCosRad (-ax, &sx, &cx);
	Q_SinCosRad (-ay, &sy, &cy);
	Q_SinCosRad (-az, &sz, &cz);

	memset (rx, 0, sizeof(rx)); memset (ry, 0, sizeof(ry)); memset (rz, 0, sizeof(rz));
	rx[0][0] = 1; rx[1][1] = cx; rx[1][2] = -sx; rx[2][1] = sx; rx[2][2] = cx;
	ry[1][1] = 1; ry[0][0] = cy; ry[0][2] = sy; ry[2][0] = -sy; ry[2][2] = cy;
	rz[2][2] = 1; rz[0][0] = cz; rz[0][1] = -sz; rz[1][0] = sz; rz[1][1] = cz;
	for (i=0 ; i<3 ; i++)
		for (j=0 ; j<3 ; j++)
			for (t[i][j]=0, k=0 ; k<3 ; k++)
				t[i][j] += rx[i][k]*ry[k][j];
	for (i=0 ; i<3 ; i++)
		for (j=0 ; j<3 ; j++)
			for (m[i][j]=0, k=0 ; k<3 ; k++)
				m[i][j] += t[i][k]*rz[k][j];
}

static void Rotate (const float m[3][3], const float *v, float *out)
{
	out[0] = m[0][0]*v[0] + m[0][1]*v[1] + m[0][2]*v[2];
	out[1] = m[1][0]*v[0] + m[1][1]*v[1] + m[1][2]*v[2];
	out[2] = m[2][0]*v[0] + m[2][1]*v[1] + m[2][2]*v[2];
}

/* The box's reach along n: how far its plane moves out (support of -box). */
static float Reach (const float *n, const float mins[3], const float maxs[3])
{
	float r = 0;
	int k;
	for (k=0 ; k<3 ; k++)
		r -= n[k] * (n[k] >= 0 ? mins[k] : maxs[k]);
	return r;
}

static int AddPlane (chim_wshape_t *out, const float *n, float d, const float mins[3], const float maxs[3])
{
	float *p;
	if (out->numplanes >= out->capplanes)
		return 0;
	p = out->planes + 4*out->numplanes++;
	p[0] = n[0]; p[1] = n[1]; p[2] = n[2];
	p[3] = d + Reach (n, mins, maxs);
	return 1;
}

static void BeginShape (chim_wshape_t *out)
{
	int k;
	out->numpieces = out->numplanes = 0;
	for (k=0 ; k<3 ; k++)
	{
		out->mins[k] = 1e30f;
		out->maxs[k] = -1e30f;
	}
}

/* One piece into the world shape: its axial bevels, own planes and edge
 * bevels, moved out by the box. Returns 0 when it does not fit. */
static int PreparePiece (const chim_piece_t *p, const chim_xform_t *x, const float mins[3],
	const float maxs[3], chim_wshape_t *out)
{
	float wn[CHIM_PLACED_PIECE_PLANES][3], lo[3], hi[3], v[3], e[3], c[3], len, g, ca, cb, alpha, beta, d;
	int j, k, s, sign;
	unsigned long flops = 0;

	{
		chim_wpiece_t *wp;
		if (out->numpieces >= out->cappieces || p->numplanes > CHIM_PLACED_PIECE_PLANES)
			return 0;
		wp = &out->pieces[out->numpieces++];
		wp->first = out->numplanes;
		/* axial bevels first (the piece box: most traces leave on one of these) */
		for (k=0 ; k<3 ; k++)
		{
			lo[k] = 1e30f;
			hi[k] = -1e30f;
		}
		for (j=0 ; j<p->numverts ; j++)
		{
			Rotate (x->m, p->verts + 3*j, v);
			for (k=0 ; k<3 ; k++)
			{
				v[k] = x->origin[k] + x->scale*v[k];
				if (v[k] < lo[k])
					lo[k] = v[k];
				if (v[k] > hi[k])
					hi[k] = v[k];
			}
			flops += 15 + 6 + 6;
		}
		for (k=0 ; k<3 ; k++)
		{
			float n[3] = {0, 0, 0};
			n[k] = 1;
			if (!AddPlane (out, n, hi[k], mins, maxs))
				return 0;
			n[k] = -1;
			if (!AddPlane (out, n, -lo[k], mins, maxs))
				return 0;
			chim_placed_stats.bevels += 2;
			if (lo[k] + mins[k] < out->mins[k])
				out->mins[k] = lo[k] + mins[k];
			if (hi[k] + maxs[k] > out->maxs[k])
				out->maxs[k] = hi[k] + maxs[k];
		}
		/* own planes: n_w = M n, d_w = s d + n_w . origin */
		for (j=0 ; j<p->numplanes ; j++)
		{
			const float *pl = p->planes + 4*j;
			Rotate (x->m, pl, wn[j]);
			d = x->scale*pl[3] + DotProduct (wn[j], x->origin);
			if (!AddPlane (out, wn[j], d, mins, maxs))
				return 0;
			flops += 15 + 4 + 6;
		}
		/* edge bevels: e x axis, kept when it lies between the edge's two planes */
		for (j=0 ; j<p->numedges ; j++)
		{
			const short *ed = p->edges + 3*j;
			const float *na = wn[ed[0]], *nb = wn[ed[1]];
			float corner[3];
			e[0] = na[1]*nb[2] - na[2]*nb[1];
			e[1] = na[2]*nb[0] - na[0]*nb[2];
			e[2] = na[0]*nb[1] - na[1]*nb[0];
			Rotate (x->m, p->verts + 3*ed[2], corner);
			for (k=0 ; k<3 ; k++)
				corner[k] = x->origin[k] + x->scale*corner[k];
			g = DotProduct (na, nb);
			flops += 9 + 15 + 6 + 5;
			if (1 - g*g < 1e-8f)
				continue;
			for (k=0 ; k<3 ; k++)
			{
				/* c = e x unit axis k */
				c[0] = k == 0 ? 0 : k == 1 ? -e[2] : e[1];
				c[1] = k == 0 ? e[2] : k == 1 ? 0 : -e[0];
				c[2] = k == 0 ? -e[1] : k == 1 ? e[0] : 0;
				len = DotProduct (c, c);
				flops += 5;
				if (len < 1e-10f)
					continue;	/* edge along the axis: an axial or own plane already */
				len = 1/(float)sqrt (len);
				VectorScale (c, len, c);
				ca = DotProduct (c, na);
				cb = DotProduct (c, nb);
				flops += 3 + 1 + 3 + 10 + 6;
				if (ca > 0.99999f || cb > 0.99999f || ca < -0.99999f || cb < -0.99999f)
					continue;	/* the same plane as one of the edge's own */
				for (s=0 ; s<2 ; s++)
				{
					sign = s ? -1 : 1;
					/* c = alpha n_a + beta n_b: both >= 0 means a facet */
					alpha = sign*(ca - g*cb);
					beta = sign*(cb - g*ca);
					flops += 6;
					if (alpha < -1e-6f || beta < -1e-6f)
						continue;
					v[0] = sign*c[0]; v[1] = sign*c[1]; v[2] = sign*c[2];
					if (!AddPlane (out, v, DotProduct (v, corner), mins, maxs))
						return 0;
					chim_placed_stats.bevels++;
					flops += 5 + 6;
					break;
				}
			}
		}
		wp->count = out->numplanes - wp->first;
	}
	chim_placed_stats.prepare_flops += flops;
	return 1;
}

int ChimPlaced_Prepare (const chim_shape_t *shape, const chim_xform_t *x, const float mins[3],
	const float maxs[3], chim_wshape_t *out)
{
	int i;
	BeginShape (out);
	for (i=0 ; i<shape->numpieces ; i++)
		if (!PreparePiece (&shape->pieces[i], x, mins, maxs, out))
			return 0;
	chim_placed_stats.prepares++;
	return 1;
}

typedef struct
{
	float	enter, exit;	/* inside the piece for enter < t <= exit */
	int		inside_start, plane;
} placed_span_t;

/* The span of the segment inside one piece; 0 when it misses the piece. */
static int PieceSpan (const chim_wshape_t *w, int i, const float *p1, const float *p2, placed_span_t *span)
{
	const chim_wpiece_t *wp = &w->pieces[i];
	float enter = -1, exit = 2, d1, d2, f;
	int j, startout = 0, plane = -1;

	for (j=0 ; j<wp->count ; j++)
	{
		const float *pl = w->planes + 4*(wp->first + j);
		d1 = DotProduct (pl, p1) - pl[3];
		d2 = DotProduct (pl, p2) - pl[3];
		chim_placed_stats.planes_tested++;
		if (d1 >= 0)
			startout = 1;
		if (d1 >= 0 && d2 >= 0)
			return 0;		/* wholly in front of one plane */
		if (d1 < 0 && d2 < 0)
			continue;
		f = d1/(d1 - d2);
		if (d1 > d2)
		{
			if (f > enter)
			{
				enter = f;
				plane = wp->first + j;
			}
		}
		else if (f < exit)
			exit = f;
	}
	if (!startout)
		enter = -1;
	else if (enter >= exit)
		return 0;
	span->enter = enter;
	span->exit = exit;
	span->inside_start = !startout;
	span->plane = plane;
	return 1;
}

void ChimPlaced_Trace (const chim_wshape_t *w, const float start[3], const float end[3], trace_t *trace)
{
	placed_span_t spans[64];
	int i, j, n = 0, best = -1;
	float f, delta[3], speed;

	memset (trace, 0, sizeof(*trace));
	trace->fraction = 1;
	for (i=0 ; i<3 ; i++)
		trace->endpos[i] = end[i];
	chim_placed_stats.traces++;
	for (i=0 ; i<w->numpieces && n<64 ; i++)
		if (PieceSpan (w, i, start, end, &spans[n]))
		{
			if (spans[n].inside_start)
			{
				trace->startsolid = true;
				if (spans[n].exit > 1)
					trace->allsolid = true;
			}
			n++;
		}
	/* all solid: from the start, the spans inside the pieces join up past
	 * the end (an exit at exactly 1 ends on a plane: outside, as the chain) */
	if (trace->startsolid && !trace->allsolid)
	{
		float reach = 0;
		int grew = 1;
		for (i=0 ; i<n ; i++)
			if (spans[i].inside_start && spans[i].exit > reach)
				reach = spans[i].exit;
		while (grew && reach <= 1)
			for (grew=0, i=0 ; i<n ; i++)
				if (!spans[i].inside_start && spans[i].enter < reach && spans[i].exit > reach)
				{
					reach = spans[i].exit;
					grew = 1;
				}
		if (reach > 1)
			trace->allsolid = true;
	}
	if (trace->allsolid)
	{
		trace->fraction = 0;
		for (i=0 ; i<3 ; i++)
			trace->endpos[i] = start[i];
		return;
	}
	/* the first entry from outside every piece */
	for (i=0 ; i<n ; i++)
	{
		if (spans[i].inside_start || spans[i].plane < 0)
			continue;
		f = spans[i].enter < 0 ? 0 : spans[i].enter;
		if (best >= 0 && f >= trace->fraction)
			continue;
		for (j=0 ; j<n ; j++)
			if (j != i && (spans[j].inside_start || spans[j].enter < f) && f <= spans[j].exit)
				break;
		if (j != n)
			continue;
		best = i;
		trace->fraction = f;
	}
	if (best < 0)
		return;
	{
		const float *pl = w->planes + 4*spans[best].plane;
		VectorCopy (pl, trace->plane.normal);
		trace->plane.dist = pl[3];
	}
	for (i=0 ; i<3 ; i++)
		delta[i] = end[i] - start[i];
	/* world.c SV_ClipMoveToEntity / chim_chunks.c ClipModel: the contact
	 * margin once, on the complete sweep */
	speed = DotProduct (delta, trace->plane.normal);
	if (speed < 0)
		speed = -speed;
	if (speed > 0)
	{
		trace->fraction -= PLACED_DIST_EPSILON/speed;
		if (trace->fraction < 0)
			trace->fraction = 0;
	}
	for (i=0 ; i<3 ; i++)
		trace->endpos[i] = start[i] + trace->fraction*delta[i];
}

/* ---------------------------------------------------------------- format 0.8 */

void ChimPlaced_AnglesMatrix (const float angles[3], float m[3][3])
{
	/* r_bsp.c R_BuildBmodelRotation step by step (world -> model), then
	 * transposed: the renderer and the collision turn a placement alike */
	float s, c, t1[3][3], t2[3][3], t3[3][3], e[3][3];
	int i, j;

	Q_SinCosDeg (angles[YAW], &s, &c);
	t1[0][0] = c; t1[0][1] = s; t1[0][2] = 0;
	t1[1][0] = -s; t1[1][1] = c; t1[1][2] = 0;
	t1[2][0] = 0; t1[2][1] = 0; t1[2][2] = 1;
	if (!angles[PITCH] && !angles[ROLL])
		memcpy (e, t1, sizeof(e));
	else
	{
		Q_SinCosDeg (angles[PITCH], &s, &c);
		t2[0][0] = c; t2[0][1] = 0; t2[0][2] = -s;
		t2[1][0] = 0; t2[1][1] = 1; t2[1][2] = 0;
		t2[2][0] = s; t2[2][1] = 0; t2[2][2] = c;
		R_ConcatRotations (t2, t1, t3);
		Q_SinCosDeg (angles[ROLL], &s, &c);
		t1[0][0] = 1; t1[0][1] = 0; t1[0][2] = 0;
		t1[1][0] = 0; t1[1][1] = c; t1[1][2] = s;
		t1[2][0] = 0; t1[2][1] = -s; t1[2][2] = c;
		R_ConcatRotations (t1, t3, e);
	}
	for (i=0 ; i<3 ; i++)
		for (j=0 ; j<3 ; j++)
			m[i][j] = e[j][i];
}

/* The table in memory after ChimPlaced_TableLoad (native order):
 * head: "PCSn" (n: converted), pieces, bytes, 0; per piece 36 bytes:
 * planes, corners, edges, 0 (u16 each), box mins and maxs (6 floats), data
 * offset (u32); the data as on disk (floats, then u16 edges). */
#define TABLE_HEAD	16
#define TABLE_ENTRY	36

static unsigned TableU32 (const unsigned char *p)
{
	unsigned v;
	memcpy (&v, p, 4);
	return v;
}

static unsigned TableU16 (const unsigned char *p)
{
	unsigned short v;
	memcpy (&v, p, 2);
	return v;
}

static void Native32 (unsigned char *p)
{
	unsigned v = ChimFormat_U32 (p);
	memcpy (p, &v, 4);
}

static void Native16 (unsigned char *p)
{
	unsigned short v = (unsigned short)ChimFormat_U16 (p);
	memcpy (p, &v, 2);
}

/* No libm: inf - inf and NaN - NaN are NaN, which never equals 0. */
static int TableFinite (float f)
{
	float zero = f - f;
	return zero == 0.0f && f > -1e7f && f < 1e7f;
}

int ChimPlaced_TablePieces (const unsigned char *table)
{
	return table && !memcmp (table, "PCSn", 4) ? (int)TableU32 (table+4) : 0;
}

int ChimPlaced_TableLoad (unsigned char *table, long bytes)
{
	unsigned n, k, j, total;
	if (!table || bytes < TABLE_HEAD)
		return 0;
	if (!memcmp (table, "PCS1", 4))
	{
		/* on disk: the sizes checked first, then every field turned around */
		n = ChimFormat_U32 (table+4);
		total = ChimFormat_U32 (table+8);
		if (total > (unsigned long)bytes || n > 65535 || TABLE_HEAD + (unsigned long)n*TABLE_ENTRY > total)
			return 0;
		for (k=0 ; k<n ; k++)
		{
			unsigned char *e = table + TABLE_HEAD + k*TABLE_ENTRY;
			unsigned long np = ChimFormat_U16 (e), nc = ChimFormat_U16 (e+2), ne = ChimFormat_U16 (e+4);
			unsigned long at = ChimFormat_U32 (e+32);
			if ((at & 3) || at < TABLE_HEAD + (unsigned long)n*TABLE_ENTRY || at > total ||
				16*np + 12*nc + 6*ne > total - at)
				return 0;
		}
		for (k=0 ; k<n ; k++)
		{
			unsigned char *e = table + TABLE_HEAD + k*TABLE_ENTRY;
			unsigned np = ChimFormat_U16 (e), nc = ChimFormat_U16 (e+2), ne = ChimFormat_U16 (e+4);
			unsigned at = ChimFormat_U32 (e+32);
			for (j=0 ; j<4 ; j++)
				Native16 (e + 2*j);
			for (j=0 ; j<7 ; j++)
				Native32 (e + 8 + 4*j);
			for (j=0 ; j<4*np + 3*nc ; j++)
				Native32 (table + at + 4*j);
			for (j=0 ; j<3*ne ; j++)
				Native16 (table + at + 16*np + 12*nc + 2*j);
		}
		for (j=1 ; j<4 ; j++)
			Native32 (table + 4*j);
		memcpy (table, "PCSn", 4);
	}
	if (memcmp (table, "PCSn", 4))
		return 0;
	n = TableU32 (table+4);
	total = TableU32 (table+8);
	if (total > (unsigned long)bytes || TABLE_HEAD + (unsigned long)n*TABLE_ENTRY > total)
		return 0;
	for (k=0 ; k<n ; k++)
	{
		const unsigned char *e = table + TABLE_HEAD + k*TABLE_ENTRY;
		unsigned np = TableU16 (e), nc = TableU16 (e+2), ne = TableU16 (e+4), at = TableU32 (e+32);
		const float *f = (const float *)(table + at);
		const unsigned char *ed = table + at + 16*np + 12*nc;
		float box[6];
		memcpy (box, e+8, sizeof(box));
		if (np < 4 || nc < 4 || np > CHIM_PLACED_PIECE_PLANES)
			return 0;
		for (j=0 ; j<6 ; j++)
			if (!TableFinite (box[j]) || (j < 3 && box[j] > box[j+3]))
				return 0;
		for (j=0 ; j<4*np + 3*nc ; j++)
			if (!TableFinite (f[j]))
				return 0;
		for (j=0 ; j<ne ; j++)
			if (TableU16 (ed+6*j) >= np || TableU16 (ed+6*j+2) >= np || TableU16 (ed+6*j+4) >= nc)
				return 0;
	}
	return 1;
}

static float			scratch_planes[4*CHIM_PLACED_SCRATCH_PLANES];
static chim_wpiece_t	scratch_pieces[CHIM_PLACED_SCRATCH_PIECES];

int ChimPlaced_TraceTable (const unsigned char *table, const float m[3][3], const float origin[3],
	const float start[3], const float mins[3], const float maxs[3], const float end[3], trace_t *trace)
{
	chim_wshape_t w;
	chim_xform_t x;
	float lo[3], hi[3];
	unsigned n, k;
	int i, j;

	memset (&w, 0, sizeof(w));
	w.planes = scratch_planes;
	w.capplanes = CHIM_PLACED_SCRATCH_PLANES;
	w.pieces = scratch_pieces;
	w.cappieces = CHIM_PLACED_SCRATCH_PIECES;
	BeginShape (&w);
	memcpy (x.m, m, sizeof(x.m));
	x.scale = 1;
	VectorCopy (origin, x.origin);
	/* the swept box: where a piece must reach to be met */
	for (i=0 ; i<3 ; i++)
	{
		lo[i] = (start[i] < end[i] ? start[i] : end[i]) + mins[i] - 1;
		hi[i] = (start[i] > end[i] ? start[i] : end[i]) + maxs[i] + 1;
	}
	n = (unsigned)ChimPlaced_TablePieces (table);
	chim_placed_stats.table_traces++;
	for (k=0 ; k<n ; k++)
	{
		const unsigned char *e = table + TABLE_HEAD + k*TABLE_ENTRY;
		chim_piece_t piece;
		float box[6], centre, reach;
		unsigned at;
		memcpy (box, e+8, sizeof(box));
		/* the piece's box turned into the world: centre, and |m| times the half sizes */
		for (i=0 ; i<3 ; i++)
		{
			centre = origin[i];
			reach = 0;
			for (j=0 ; j<3 ; j++)
			{
				float h = (box[j+3] - box[j])*0.5f, mm = m[i][j];
				centre += mm*(box[j+3] + box[j])*0.5f;
				reach += (mm < 0 ? -mm : mm)*h;
			}
			if (centre + reach < lo[i] || centre - reach > hi[i])
				break;
		}
		if (i != 3)
			continue;
		at = TableU32 (e+32);
		piece.numplanes = (int)TableU16 (e);
		piece.numverts = (int)TableU16 (e+2);
		piece.numedges = (int)TableU16 (e+4);
		piece.planes = (const float *)(table + at);
		piece.verts = piece.planes + 4*piece.numplanes;
		piece.edges = (const short *)(piece.verts + 3*piece.numverts);
		if (!PreparePiece (&piece, &x, mins, maxs, &w))
		{
			chim_placed_stats.table_full++;
			return 0;
		}
		chim_placed_stats.pieces_met++;
	}
	ChimPlaced_Trace (&w, start, end, trace);
	return 1;
}
