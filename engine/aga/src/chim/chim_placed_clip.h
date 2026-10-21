/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM placed collision: one stored collision shape per mesh, placed with any
 * rotation and a uniform scale, traced with a world-aligned player box.
 * World format 0.8 (EXPERIMENTAL, written only by the builder's placement
 * format 0.8) uses it for every placement of a model with a piece table;
 * 0.4-0.7 worlds never call it. See chim_placed_clip.c for the method.
 */
#ifndef CHIM_PLACED_CLIP_H
#define CHIM_PLACED_CLIP_H

/* One convex piece in the mesh's own frame (unscaled, untilted).
 * planes: 4 floats each, n and d, a point x is inside when n.x < d for all.
 * verts: 3 floats each, the piece's corners.
 * edges: 3 shorts each: the two planes that meet at the edge and one of
 * its corners (computed offline by the builder, never at run time). */
typedef struct
{
	int				numplanes, numverts, numedges;
	const float		*planes;
	const float		*verts;
	const short		*edges;
} chim_piece_t;

typedef struct
{
	int					numpieces;
	const chim_piece_t	*pieces;
} chim_shape_t;

/* world = origin + scale * m * local (m orthonormal, rows are world axes) */
typedef struct
{
	float	m[3][3];
	float	scale;
	float	origin[3];
} chim_xform_t;

/* A shape placed in the world: per piece a run of world planes, for one box
 * size (the planes are already moved out by the box, Minkowski sum with all
 * bevels, so a trace is a point against convex pieces). */
typedef struct
{
	int		first, count;
} chim_wpiece_t;

typedef struct
{
	int				numpieces, numplanes, capplanes, cappieces;
	chim_wpiece_t	*pieces;
	float			*planes;		/* 4 floats each: world n, d (box included) */
	float			mins[3], maxs[3];	/* the expanded shape's box */
} chim_wshape_t;

typedef struct
{
	unsigned long	prepares, prepare_flops;	/* placements made world shapes, and their float ops */
	unsigned long	traces, planes_tested;		/* traces and plane tests (2 dot products each) */
	unsigned long	bevels;						/* bevel planes added (axial + edge) */
	unsigned long	table_traces, pieces_met;	/* 0.8: traces against piece tables, pieces they expanded */
	unsigned long	table_full;					/* 0.8: traces that did not fit the scratch (fallback) */
} chim_placed_stats_t;

extern chim_placed_stats_t chim_placed_stats;

/* TES3 angles (radians, as stored in the game's references) to the matrix the
 * builder uses (prepare_scenery.reference_rotation: Z, then Y, then X). */
void ChimPlaced_Matrix (float ax, float ay, float az, float m[3][3]);

/* Quake entity angles (pitch, yaw, roll, degrees) to model -> world: the
 * transpose of the renderer's own rotation (r_bsp.c R_BuildBmodelRotation,
 * the same arithmetic), so a placement collides where it is drawn. */
void ChimPlaced_AnglesMatrix (const float angles[3], float m[3][3]);

/* The world shape of a placement for a box of size mins..maxs (point: zeros).
 * Returns 0 when the buffers are too small (nothing usable then). */
int ChimPlaced_Prepare (const chim_shape_t *shape, const chim_xform_t *x, const float mins[3],
	const float maxs[3], chim_wshape_t *out);

/* SV_ClipMoveToEntity for a prepared placement: the box is the one the shape
 * was prepared for. Same results form as world.c (fraction, endpos, plane,
 * startsolid, allsolid) including the DIST_EPSILON pull-back. */
void ChimPlaced_Trace (const chim_wshape_t *w, const float start[3], const float end[3], trace_t *trace);

/* Format 0.8 piece table (a placed model's lump 4; tools/chim/placed.py
 * piece_table): big-endian on disk, turned into native order in place once,
 * when the model is loaded. Returns 1 when every piece can be expanded (the
 * table is then usable by ChimPlaced_TraceTable), 0 for a table that is
 * malformed, or has a piece with more than CHIM_PLACED_PIECE_PLANES planes
 * (the caller then keeps the model's stored hull). Calling it again on a
 * converted table only checks it. */
#define CHIM_PLACED_PIECE_PLANES	128	/* v0.0.46 world: largest piece 101 planes */
#define CHIM_PLACED_SCRATCH_PLANES	2048	/* world planes one trace may expand */
#define CHIM_PLACED_SCRATCH_PIECES	64		/* pieces one trace may meet */
int ChimPlaced_TableLoad (unsigned char *table, long bytes);
int ChimPlaced_TablePieces (const unsigned char *table);

/* A trace against a placed model's piece table at m, origin (scale 1): only
 * the pieces whose expanded box the swept box meets are expanded (by mins,
 * maxs) and traced. Returns 0 when they do not fit the scratch (the caller
 * then traces the stored hull), else 1 with the trace filled. */
int ChimPlaced_TraceTable (const unsigned char *table, const float m[3][3], const float origin[3],
	const float start[3], const float mins[3], const float maxs[3], const float end[3], trace_t *trace);

#endif
