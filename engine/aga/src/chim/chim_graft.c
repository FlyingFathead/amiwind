/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM frame world: the active chunks' terrain grafted into the map's world
 * model, so Quake's world machinery works on it unchanged.
 *
 * Quake addresses world data by index into the world model's own arrays:
 * R_RecursiveWorldNode draws worldmodel->surfaces + node->firstsurface (16
 * bits), faces walk surfedges, edges (16-bit vertex indices) and the world
 * edge cache by index, R_MarkLeaves and the PVS number leaves by position in
 * worldmodel->leafs, SV_FindTouchedLeafs stores those numbers in edicts, and
 * the hulls follow clipnode indices with plane indices. So the frame world
 * is one pool of those arrays: each chunk's decoded terrain subtree (its
 * template, decoded by model.c's section loaders and kept in the zone) is
 * copied in with its indices and pointers relocated, under a frame root and
 * an axial grid at chunk edges (split the chunk range in halves, longer axis
 * first; a range without a grafted chunk is one empty leaf).
 *
 * Two methods (chim_graft_mode, read at map start):
 * - 1, incremental (default): every array of the pool has free ranges; a
 *   chunk that joins the ring is copied into free ranges, one that leaves
 *   gives its ranges back. Nothing else moves: surfaces keep their surface
 *   cache blocks, efrags and edict leaf numbers stay valid; only the entities
 *   in the leaves that changed (the chunk's own and the grid's empty leaves)
 *   are linked again, as R_RemoveEfrags / R_AddEfrags and SV_LinkEdict do for
 *   a moving entity. The grid and the leaf PVS rows are rewritten (small).
 *   Chunks join within a per-frame budget (chim_graft_kib), nearest first;
 *   chunks within the collision margin never wait. A pool that cannot take a
 *   chunk is repacked: the whole ring copied again (counted and said).
 * - 0, full rebuild (the first method, kept selectable): the whole pool is
 *   copied again into the other of two slots on every change.
 *
 * Reused as they are: R_RecursiveWorldNode, R_MarkLeaves and Mod_LeafPVS
 * (each chunk's PVS row over the frame's chunks becomes a leaf row),
 * R_StoreEfrags, R_RemoveEfrags, R_AddEfrags, R_LightPoint (terrain
 * lightmaps), SV_PointContents and SV_RecursiveHullCheck (hull 0 from the
 * node tree as Mod_MakeHull0 builds it, hull 1 from the chunks' clipnodes),
 * SV_LinkEdict, the world edge cache. Texinfo, textures and lightmaps stay
 * in the chunk templates and are pointed at.
 */
#include "quakedef.h"
#include "r_local.h"
#include "d_local.h"
#include "chim_local.h"

void R_AddEfrags (entity_t *ent);
void R_RemoveEfrags (entity_t *ent);

/* The pool's index-addressed arrays; a chunk takes one range of each. */
enum { CA_NODE, CA_LEAF, CA_MARK, CA_SURF, CA_SURFEDGE, CA_EDGE, CA_VERT, CA_PLANE, CA_CLIP, CA_ARRAYS };
static const char *const array_name[CA_ARRAYS] =
	{"nodes", "leaves", "marks", "surfaces", "surfedges", "edges", "vertexes", "planes", "clipnodes"};
/* Quake's index widths: 16-bit firstsurface and edge vertexes, MAX_MAP_LEAFS
 * for vis rows, clipnode children (world.c AW_ClipChild's unsigned half). */
static const int array_limit[CA_ARRAYS] =
	{65520, MAX_MAP_LEAFS, 0x3fffffff, 65535, 0x3fffffff, 0x3fffffff, 65535, 0x3fffffff, 65520};

typedef struct
{
	int				entry;
	chim_model_t	*terrain;
	int				base[CA_ARRAYS], count[CA_ARRAYS];
	int				clip;			/* hull-1 root in the pool, or contents */
} chim_graft_t;

typedef struct
{
	int		base, count;
} chim_range_t;

typedef struct
{
	int			incremental;
	int			grafts, graft_cap, block;
	int			num[CA_ARRAYS];		/* elements in use from index 0 (incremental: the high water) */
	int			cap[CA_ARRAYS];		/* incremental: elements the block holds */
	int			grid[CA_ARRAYS];	/* incremental: grid elements in use (leaves: from 1) */
	int			grid_cap[CA_ARRAYS];	/* incremental: reserved at the front for the grid */
	int			vis_bytes, vis_cap;
	chim_graft_t	*graft;
	chim_range_t	*gaps;			/* incremental: free ranges per array, sorted */
	chim_range_t	*spare;			/* incremental: the same, saved while an update is planned */
	int			gap_count[CA_ARRAYS];
	int			gap_rows;			/* graft_cap + 2 */
	unsigned short	*sums;			/* incremental: planned cells summed, for the grid */
	byte		*plan;				/* incremental: per frame entry, grafted after this update */
	int			*adds;				/* incremental: entries planned to join, nearest first */
	mnode_t		*nodes;
	mleaf_t		*leafs;			/* leaf 0: the shared solid leaf */
	msurface_t	**marks;
	msurface_t	*surfs;
	int			*surfedges;
	medge_t		*edges;
	mvertex_t	*verts;
	mplane_t	*planes;
	dclipnode_t	*clips;			/* hull 1 (and 2) */
	dclipnode_t	*clips0;		/* hull 0, one per node */
	unsigned int	*edgecache;
	byte		*vis;
} chim_pool_t;

static model_t		*world;
static model_t		saved;
static int			incremental;	/* the method of this map */
static struct
{
	unsigned long	rebuilds, failures, failing, carried, detached, statics, edicts, lost, outgrown;
	unsigned long	adds, removes, repacks, copied, urgent, relinked, capped, trims, trim_said;
	double			seconds, worst;		/* update time since the last interval */
	int				interval;			/* updates since the last interval */
	int				i_adds, i_removes, i_repacks;
	long			i_bytes;			/* most bytes one update copied since the last interval */
	int				grafts, nodes, leafs, surfs, bytes;
	char			repack_reason[64];
} stats;

/* ---------------------------------------------------------------- sizes */

static int ElementBytes (int a)
{
	switch (a)
	{
	case CA_NODE:		return sizeof(mnode_t) + sizeof(dclipnode_t);	/* with its hull-0 clipnode */
	case CA_LEAF:		return sizeof(mleaf_t);
	case CA_MARK:		return sizeof(msurface_t *);
	case CA_SURF:		return sizeof(msurface_t);
	case CA_SURFEDGE:	return sizeof(int);
	case CA_EDGE:		return sizeof(medge_t) + sizeof(unsigned int);	/* with its edge cache word */
	case CA_VERT:		return sizeof(mvertex_t);
	case CA_PLANE:		return sizeof(mplane_t);
	default:			return sizeof(dclipnode_t);
	}
}

static void TemplateCounts (const chim_model_t *cm, int *n)
{
	const model_t *m = &cm->model;
	n[CA_NODE] = m->numnodes;
	n[CA_LEAF] = cm->leafs - 1;			/* its leaf 0 is the pool's leaf 0 */
	n[CA_MARK] = m->nummarksurfaces;
	n[CA_SURF] = m->numsurfaces;
	n[CA_SURFEDGE] = m->numsurfedges;
	n[CA_EDGE] = m->numedges;
	n[CA_VERT] = m->numvertexes;
	n[CA_PLANE] = m->numplanes;
	n[CA_CLIP] = m->numclipnodes;
}

static long CountBytes (const int *n)
{
	long bytes = 0;
	int a;
	for (a=0 ; a<CA_ARRAYS ; a++)
		bytes += (long)n[a] * ElementBytes (a);
	return bytes;
}

/* ---------------------------------------------------------------- counting and building */

/* Cursors while building; a dry run only counts. "copy" (the full rebuild)
 * copies each chunk where the grid reaches it; otherwise the grid points at
 * the chunks already in the pool and is written into its own ranges. */
typedef struct
{
	int		dry, copy;
	chim_pool_t	*p;
	int		n[CA_ARRAYS], grafts;
} chim_build_t;

static int Desired (int e)
{
	return chim_frame.entries[e].state == CHIM_STATE_ACTIVE && ChimModels_Terrain (e) != NULL;
}

/* The chunk at a cell the grid hangs in: full rebuild, every active chunk
 * with resident terrain; incremental, the chunks planned for this update. */
static int CellEntry (chim_build_t *b, int x, int y)
{
	int e = ChimChunks_CellEntry (x, y);
	if (e < 0)
		return -1;
	if (b->copy)
		return Desired (e) ? e : -1;
	return b->p->plan[e] ? e : -1;
}

static int RangeHasChunk (chim_build_t *b, int x0, int y0, int x1, int y1)
{
	int x, y, w;
	unsigned short *s;
	if (!b->copy)
	{
		/* Summed table: O(1) per range. */
		w = chim_frame.frame.nx + 1;
		s = b->p->sums;
		return s[y1*w + x1] - s[y0*w + x1] - s[y1*w + x0] + s[y0*w + x0] > 0;
	}
	for (y=y0 ; y<y1 ; y++)
		for (x=x0 ; x<x1 ; x++)
			if (CellEntry (b, x, y) >= 0)
				return 1;
	return 0;
}

static void Sums (chim_pool_t *p)
{
	int nx = chim_frame.frame.nx, ny = chim_frame.frame.ny, w = nx + 1, x, y, e;
	unsigned short *s = p->sums;
	for (x=0 ; x<w ; x++)
		s[x] = 0;
	for (y=0 ; y<ny ; y++)
	{
		unsigned short row = 0;
		s[(y+1)*w] = 0;
		for (x=0 ; x<nx ; x++)
		{
			e = ChimChunks_CellEntry (x, y);
			row = (unsigned short)(row + (e >= 0 && p->plan[e]));
			s[(y+1)*w + x+1] = (unsigned short)(s[y*w + x+1] + row);
		}
	}
}

static short ClampShort (float v)
{
	return (short)(v < -32768 ? -32768 : v > 32767 ? 32767 : v);
}

static mplane_t *AxialPlane (chim_build_t *b, int axis, float dist)
{
	mplane_t *pl;
	int k = b->n[CA_PLANE]++;
	if (b->dry)
		return NULL;
	pl = &b->p->planes[k];
	memset (pl, 0, sizeof(*pl));
	pl->normal[axis] = 1;
	pl->dist = dist;
	pl->type = (byte)axis;
	return pl;
}

static mleaf_t *VoidLeaf (chim_build_t *b, float x0, float y0, float x1, float y1)
{
	mleaf_t *l;
	int k = b->n[CA_LEAF]++;
	if (b->dry)
		return NULL;
	l = &b->p->leafs[k];
	memset (l, 0, sizeof(*l));
	l->contents = CONTENTS_EMPTY;
	l->minmaxs[0] = ClampShort (x0); l->minmaxs[1] = ClampShort (y0); l->minmaxs[2] = -4096;
	l->minmaxs[3] = ClampShort (x1); l->minmaxs[4] = ClampShort (y1); l->minmaxs[5] = 4095;
	return l;
}

static short ClipChild (int index)
{
	/* world.c AW_ClipChild: indices above 32767 use the unsigned half. */
	return (short)(unsigned short)index;
}

static int ClipIndex (short child)
{
	return child < -15 ? (unsigned short)child : child;
}

/* Copy one chunk's terrain template into the pool at the graft's ranges,
 * relocating every index and pointer; sets the graft's hull-1 root. */
static void CopyGraft (chim_pool_t *p, chim_graft_t *g)
{
	chim_model_t *cm = g->terrain;
	model_t *m = &cm->model;
	const int *b = g->base;
	int i, j, k, c;

	memcpy (p->planes + b[CA_PLANE], m->planes, m->numplanes*sizeof(mplane_t));
	memcpy (p->verts + b[CA_VERT], m->vertexes, m->numvertexes*sizeof(mvertex_t));
	for (i=0 ; i<m->numedges ; i++)
		for (j=0 ; j<2 ; j++)
			p->edges[b[CA_EDGE]+i].v[j] = (unsigned short)(m->edges[i].v[j] + b[CA_VERT]);
	for (i=0 ; i<m->numsurfedges ; i++)
	{
		k = m->surfedges[i];
		p->surfedges[b[CA_SURFEDGE]+i] = k < 0 ? k - b[CA_EDGE] : k + b[CA_EDGE];
	}
	for (i=0 ; i<m->numsurfaces ; i++)
	{
		msurface_t *s = &p->surfs[b[CA_SURF]+i];
		*s = m->surfaces[i];
		s->firstedge += b[CA_SURFEDGE];
		s->plane = p->planes + b[CA_PLANE] + (m->surfaces[i].plane - m->planes);
		s->cachehead = NULL;
	}
	for (i=0 ; i<m->nummarksurfaces ; i++)
		p->marks[b[CA_MARK]+i] = p->surfs + b[CA_SURF] + (m->marksurfaces[i] - m->surfaces);
	/* Leaf 0 of every chunk is the shared solid leaf 0 of the pool. */
	for (i=1 ; i<cm->leafs ; i++)
	{
		mleaf_t *l = &p->leafs[b[CA_LEAF]+i-1];
		*l = m->leafs[i];
		l->parent = l->parent ? p->nodes + b[CA_NODE] + (l->parent - m->nodes) : NULL;
		if (m->leafs[i].firstmarksurface)
			l->firstmarksurface = p->marks + b[CA_MARK] + (m->leafs[i].firstmarksurface - m->marksurfaces);
		l->compressed_vis = NULL;
		l->efrags = NULL;
		l->visframe = 0;
	}
	for (i=0 ; i<m->numnodes ; i++)
	{
		mnode_t *n = &p->nodes[b[CA_NODE]+i];
		*n = m->nodes[i];
		n->plane = p->planes + b[CA_PLANE] + (m->nodes[i].plane - m->planes);
		n->parent = m->nodes[i].parent ? p->nodes + b[CA_NODE] + (m->nodes[i].parent - m->nodes) : NULL;
		n->firstsurface = (unsigned short)(n->firstsurface + b[CA_SURF]);
		n->visframe = 0;
		for (j=0 ; j<2 ; j++)
		{
			mnode_t *child = m->nodes[i].children[j];
			if (child->contents < 0)
			{
				k = (int)((mleaf_t *)child - m->leafs);
				n->children[j] = (mnode_t *)(k ? &p->leafs[b[CA_LEAF]+k-1] : &p->leafs[0]);
			}
			else
				n->children[j] = p->nodes + b[CA_NODE] + (child - m->nodes);
		}
	}
	for (i=0 ; i<m->numclipnodes ; i++)
	{
		dclipnode_t *d = &p->clips[b[CA_CLIP]+i];
		d->planenum = m->clipnodes[i].planenum + b[CA_PLANE];
		for (j=0 ; j<2 ; j++)
		{
			c = ClipIndex (m->clipnodes[i].children[j]);
			d->children[j] = c >= 0 ? ClipChild (c + b[CA_CLIP]) : m->clipnodes[i].children[j];
		}
	}
	c = m->hulls[1].firstclipnode;
	g->clip = c >= 0 ? c + b[CA_CLIP] : c;
}

/* Hull 0 as Mod_MakeHull0 builds it, for nodes [first, first+count). */
static void Hull0 (chim_pool_t *p, int first, int count)
{
	int i, j;
	for (i=first ; i<first+count ; i++)
	{
		mnode_t *n = &p->nodes[i];
		p->clips0[i].planenum = (int)(n->plane - p->planes);
		for (j=0 ; j<2 ; j++)
			p->clips0[i].children[j] = n->children[j]->contents < 0 ? (short)n->children[j]->contents :
				ClipChild ((int)(n->children[j] - p->nodes));
	}
}

/* Full rebuild: copy one chunk where the grid reaches it. */
static mnode_t *Graft (chim_build_t *b, int entry, int *clip)
{
	chim_model_t *cm = ChimModels_Terrain (entry);
	chim_graft_t dry, *g = b->dry ? &dry : &b->p->graft[b->grafts];
	int n[CA_ARRAYS], a;

	TemplateCounts (cm, n);
	b->grafts++;
	for (a=0 ; a<CA_ARRAYS ; a++)
	{
		g->base[a] = b->n[a];
		g->count[a] = n[a];
		b->n[a] += n[a];
	}
	if (b->dry)
	{
		*clip = 0;
		return NULL;
	}
	g->entry = entry;
	g->terrain = cm;
	CopyGraft (b->p, g);
	*clip = g->clip;
	return b->p->nodes + g->base[CA_NODE];	/* node 0 is the template's root */
}

static void Bounds (mnode_t *n, mnode_t *a, mnode_t *b)
{
	int k;
	for (k=0 ; k<3 ; k++)
	{
		n->minmaxs[k] = a->minmaxs[k] < b->minmaxs[k] ? a->minmaxs[k] : b->minmaxs[k];
		n->minmaxs[k+3] = a->minmaxs[k+3] > b->minmaxs[k+3] ? a->minmaxs[k+3] : b->minmaxs[k+3];
	}
}

/* The grid over cells [x0,x1) x [y0,y1); *clip gets the hull-1 child. */
static mnode_t *Grid (chim_build_t *b, int x0, int y0, int x1, int y1, int *clip)
{
	float g = (float)chim_frame.frame.grain, lx = chim_frame.frame.low[0], ly = chim_frame.frame.low[1];
	int axis, mid, k, ck, front, back;
	mnode_t *n, *f, *bk;
	mplane_t *pl;

	if (!RangeHasChunk (b, x0, y0, x1, y1))
	{
		*clip = CONTENTS_EMPTY;
		return (mnode_t *)VoidLeaf (b, lx + x0*g, ly + y0*g, lx + x1*g, ly + y1*g);
	}
	if (x1 - x0 == 1 && y1 - y0 == 1)
	{
		chim_graft_t *gr;
		if (b->copy)
			return Graft (b, CellEntry (b, x0, y0), clip);
		*clip = 0;
		if (b->dry)
			return NULL;
		gr = &b->p->graft[chim_frame.entries[CellEntry (b, x0, y0)].graft];
		*clip = gr->clip;
		return b->p->nodes + gr->base[CA_NODE];
	}
	axis = x1 - x0 >= y1 - y0 ? 0 : 1;
	mid = axis ? (y0 + y1)/2 : (x0 + x1)/2;
	k = b->n[CA_NODE]++;
	ck = b->n[CA_CLIP]++;
	pl = AxialPlane (b, axis, (axis ? ly : lx) + mid*g);
	/* Front (children[0]) is the side the normal points to: the high half. */
	f = axis ? Grid (b, x0, mid, x1, y1, &front) : Grid (b, mid, y0, x1, y1, &front);
	bk = axis ? Grid (b, x0, y0, x1, mid, &back) : Grid (b, x0, y0, mid, y1, &back);
	*clip = ck;
	if (b->dry)
		return NULL;
	n = &b->p->nodes[k];
	memset (n, 0, sizeof(*n));
	n->plane = pl;
	n->children[0] = f;
	n->children[1] = bk;
	f->parent = n;
	bk->parent = n;
	Bounds (n, f, bk);
	b->p->clips[ck].planenum = (int)(pl - b->p->planes);
	b->p->clips[ck].children[0] = front >= 0 ? ClipChild (front) : (short)front;
	b->p->clips[ck].children[1] = back >= 0 ? ClipChild (back) : (short)back;
	return n;
}

/* Frame root (node 0, clip 0): west of the frame is one empty leaf, so the
 * world always starts with a node, as SV_PointContents expects. */
static void Build (chim_build_t *b)
{
	mnode_t *root = NULL, *east, *west;
	mplane_t *pl;
	int clip, a;

	for (a=0 ; a<CA_ARRAYS ; a++)
		b->n[a] = 0;
	b->n[CA_NODE] = 1; b->n[CA_CLIP] = 1; b->n[CA_LEAF] = 1; b->grafts = 0;
	b->n[CA_EDGE] = 1;			/* edge 0 is never drawn */
	pl = AxialPlane (b, 0, chim_frame.frame.low[0]);
	if (!b->dry)
	{
		root = &b->p->nodes[0];
		memset (root, 0, sizeof(*root));
		memset (&b->p->leafs[0], 0, sizeof(mleaf_t));
		b->p->leafs[0].contents = CONTENTS_SOLID;
		memset (&b->p->edges[0], 0, sizeof(medge_t));
	}
	east = Grid (b, 0, 0, chim_frame.frame.nx, chim_frame.frame.ny, &clip);
	west = (mnode_t *)VoidLeaf (b, -32768, -32768, chim_frame.frame.low[0], 32767);
	if (b->dry)
		return;
	root->plane = pl;
	root->children[0] = east;
	root->children[1] = west;
	east->parent = root;
	west->parent = root;
	Bounds (root, east, west);
	b->p->clips[0].planenum = (int)(pl - b->p->planes);
	b->p->clips[0].children[0] = clip >= 0 ? ClipChild (clip) : (short)clip;
	b->p->clips[0].children[1] = CONTENTS_EMPTY;
}

/* ---------------------------------------------------------------- visibility */

/* Quake's vis rows: one per chunk with a PVS row over the frame's chunks,
 * turned into leaf bits (every leaf of every visible grafted chunk, and the
 * empty leaves, which hold nothing to draw). Zero runs compressed as
 * Mod_DecompressVis reads them. Returns bytes written. */
static int ChunkRow (const chim_chunk_t *c, byte *bits)
{
	int nbytes = (chim_frame.count + 7) >> 3, out = 0, in = 0, n;
	while (out < nbytes)
	{
		if (in >= c->pvs_bytes)
			return 0;
		if (c->pvs[in])
		{
			bits[out++] = c->pvs[in++];
			continue;
		}
		if (in + 1 >= c->pvs_bytes || out + c->pvs[in+1] > nbytes)
			return 0;
		for (n=c->pvs[in+1] ; n ; n--)
			bits[out++] = 0;
		in += 2;
	}
	return in == c->pvs_bytes;
}

static int Compress (const byte *row, int bytes, byte *out)
{
	int i = 0, o = 0, n;
	while (i < bytes)
	{
		if (row[i])
		{
			out[o++] = row[i++];
			continue;
		}
		for (n=0 ; i < bytes && !row[i] && n < 255 ; i++)
			n++;
		out[o++] = 0;
		out[o++] = (byte)n;
	}
	return o;
}

/* The most bytes Compress writes for a row of this many bytes. */
static int RowBound (int bytes)
{
	return bytes + bytes/2 + 2;
}

/* Full rebuild: every leaf visible, less the leaves of grafted chunks this
 * one cannot see. */
static void Visibility (chim_pool_t *p)
{
	static byte chunks[CHIM_MAX_CHUNKS/8], row[MAX_MAP_LEAFS/8];
	int row_bytes = (p->num[CA_LEAF] - 1 + 7) >> 3, used = 0, i, j, k, l;
	chim_graft_t *g;

	for (i=0 ; i<p->grafts ; i++)
	{
		chim_chunk_t *c = chim_frame.entries[p->graft[i].entry].chunk.data;
		byte *start = p->vis + used;
		if (!c || !c->pvs_bytes || !ChunkRow (c, chunks))
			continue;		/* no row: Mod_DecompressVis makes all visible */
		/* Grid leaves hold no faces; their efrags stay visible. */
		memset (row, 0xff, row_bytes);
		for (j=0 ; j<p->grafts ; j++)
		{
			g = &p->graft[j];
			if (chunks[g->entry >> 3] & (1 << (g->entry & 7)))
				continue;
			for (k=0 ; k<g->count[CA_LEAF] ; k++)
			{
				l = g->base[CA_LEAF] + k - 1;		/* pool leaf n has vis bit n-1 */
				row[l >> 3] &= (byte)~(1 << (l & 7));
			}
		}
		used += Compress (row, row_bytes, start);
		for (k=0 ; k<p->graft[i].count[CA_LEAF] ; k++)
			p->leafs[p->graft[i].base[CA_LEAF] + k].compressed_vis = start;
	}
	p->vis_bytes = used;
}

static void SetBits (byte *row, int first, int count)
{
	int i;
	for (i=first ; i<first+count && (i & 7) ; i++)
		row[i >> 3] |= (byte)(1 << (i & 7));
	for ( ; i+8 <= first+count ; i+=8)
		row[i >> 3] = 0xff;
	for ( ; i<first+count ; i++)
		row[i >> 3] |= (byte)(1 << (i & 7));
}

/* Incremental: the grid's leaves and every leaf of each visible grafted
 * chunk; free ranges (holes) are not visible. The same rows as the full
 * rebuild for every leaf in use. Fits vis_cap by construction (Partition). */
static void VisRows (chim_pool_t *p)
{
	static byte chunks[CHIM_MAX_CHUNKS/8], row[MAX_MAP_LEAFS/8];
	int row_bytes = (p->num[CA_LEAF] - 1 + 7) >> 3, used = 0, i, j, k;
	chim_graft_t *g;

	for (i=0 ; i<p->grafts ; i++)
	{
		chim_chunk_t *c = chim_frame.entries[p->graft[i].entry].chunk.data;
		byte *start = NULL;
		if (c && c->pvs_bytes && ChunkRow (c, chunks))
		{
			memset (row, 0, row_bytes);
			SetBits (row, 0, p->grid[CA_LEAF]);
			for (j=0 ; j<p->grafts ; j++)
			{
				g = &p->graft[j];
				if (chunks[g->entry >> 3] & (1 << (g->entry & 7)))
					SetBits (row, g->base[CA_LEAF] - 1, g->count[CA_LEAF]);
			}
			if (used + RowBound (row_bytes) > p->vis_cap)
				Sys_Error ("CHIM: frame world vis rows over their reserve");
			start = p->vis + used;
			used += Compress (row, row_bytes, start);
		}
		for (k=0 ; k<p->graft[i].count[CA_LEAF] ; k++)
			p->leafs[p->graft[i].base[CA_LEAF] + k].compressed_vis = start;
	}
	p->vis_bytes = used;
}

/* ---------------------------------------------------------------- efrags and edicts */

/* Give an entity's efrags back to the free list without unlinking them from
 * their leaves: the leaves belong to a pool that is being replaced. */
int ChimGraft_ReleaseEfrags (entity_t *ent)
{
	efrag_t *ef, *next;
	int n = 0;
	for (ef=ent->efrag ; ef ; ef=next)
	{
		next = ef->entnext;
		ef->entnext = cl.free_efrags;
		cl.free_efrags = ef;
		aw_efrags_used--;
		n++;
	}
	ent->efrag = NULL;
	ent->topnode = NULL;
	return n;
}

#define CHIM_READD	(MAX_STATIC_ENTITIES+MAX_EDICTS)
static entity_t *readd[CHIM_READD];

/* Every entity linked into the old pool's leaves (static entities, and any
 * other efrag owner) is released and listed for linking again. */
static int ReleaseLeafEfrags (chim_pool_t *old, int *lost)
{
	int i, n = 0;
	efrag_t *ef;
	for (i=1 ; i<old->num[CA_LEAF] ; i++)
		for (ef=old->leafs[i].efrags ; ef ; ef=ef->leafnext)
		{
			entity_t *ent = ef->entity;
			if (!ent->efrag)
				continue;		/* released through an earlier leaf */
			if (n < CHIM_READD)
				readd[n++] = ent;
			else
				(*lost)++;
			ChimGraft_ReleaseEfrags (ent);
		}
	return n;
}

/* No free efrag may keep a pointer into a pool that is about to be freed:
 * R_ClearEfrags writes through every link's leaf. */
static void SweepFreeEfrags (void)
{
	efrag_t *ef;
	for (ef=cl.free_efrags ; ef ; ef=ef->entnext)
	{
		ef->leaf = NULL;
		ef->leafnext = NULL;
	}
}

static int RelinkEdicts (void)
{
	edict_t *ent;
	int i, n = 0;
	if (!sv.active || sv.worldmodel != world || !sv.edicts)
		return 0;
	for (i=1, ent=NEXT_EDICT(sv.edicts) ; i<sv.num_edicts ; i++, ent=NEXT_EDICT(ent))
		/* Linked before: in an area list, or (SOLID_NOT) with leaf numbers only. */
		if (!ent->free && (ent->area.prev || ent->num_leafs))
		{
			SV_LinkEdict (ent, false);
			n++;
		}
	return n;
}

/* What an incremental update changed, for linking again only what it must. */
#define CHIM_CHANGES	128
typedef struct
{
	int		readd, lost, all;
	int		old_grid;					/* grid leaves before the update */
	int		removed, leaves[CHIM_CHANGES][2];	/* leaf ranges given back */
	int		squares;
	float	square[CHIM_CHANGES][4];	/* chunk squares that joined or left */
} chim_changes_t;

static void NoteSquare (chim_changes_t *ch, int entry)
{
	chim_entry_t *e = &chim_frame.entries[entry];
	if (ch->squares >= CHIM_CHANGES)
	{
		ch->all = 1;
		return;
	}
	ch->square[ch->squares][0] = e->low[0];
	ch->square[ch->squares][1] = e->low[1];
	ch->square[ch->squares][2] = e->high[0];
	ch->square[ch->squares][3] = e->high[1];
	ch->squares++;
}

/* Take every entity out of a leaf that is about to change, the way a moving
 * entity leaves its leaves (R_RemoveEfrags: unlinked from every leaf it was
 * in). Placements are linked again by ChimChunks_Link; other owners (static
 * entities) are listed for R_AddEfrags. */
/* R_RemoveEfrags, and the links it frees forget their leaves (it pushes
 * them on the head of the free list): no free efrag points into the frame
 * world, whose leaves are reused. */
void ChimGraft_RemoveEfrags (entity_t *ent)
{
	efrag_t *ef;
	int n = 0;
	for (ef=ent->efrag ; ef ; ef=ef->entnext)
		n++;
	R_RemoveEfrags (ent);
	for (ef=cl.free_efrags ; ef && n ; ef=ef->entnext, n--)
	{
		ef->leaf = NULL;
		ef->leafnext = NULL;
	}
}

static void PullLeaf (mleaf_t *leaf, chim_changes_t *ch)
{
	efrag_t *ef;
	while ((ef = leaf->efrags) != NULL)
	{
		entity_t *ent = ef->entity;
		ChimGraft_RemoveEfrags (ent);
		stats.relinked++;
		if (ChimChunks_Forget (ent))
			continue;
		if (ch->readd < CHIM_READD)
			readd[ch->readd++] = ent;
		else
			ch->lost++;
	}
}

/* Only the edicts whose leaves changed: leaf numbers in a range given back
 * or in the old grid, or a box over a chunk square that joined or left. */
static int EdictChanged (const edict_t *ent, const chim_changes_t *ch)
{
	int i, j, l;
	if (ch->all)
		return 1;
	for (i=0 ; i<ent->num_leafs ; i++)
	{
		l = ent->leafnums[i] + 1;		/* leaf numbers skip leaf 0 */
		if (l <= ch->old_grid)
			return 1;
		for (j=0 ; j<ch->removed ; j++)
			if (l >= ch->leaves[j][0] && l < ch->leaves[j][1])
				return 1;
	}
	for (j=0 ; j<ch->squares ; j++)
		if (ent->v.absmin[0] <= ch->square[j][2] && ent->v.absmax[0] >= ch->square[j][0] &&
			ent->v.absmin[1] <= ch->square[j][3] && ent->v.absmax[1] >= ch->square[j][1])
			return 1;
	return 0;
}

static int RelinkChanged (const chim_changes_t *ch)
{
	edict_t *ent;
	int i, n = 0;
	if (!sv.active || sv.worldmodel != world || !sv.edicts)
		return 0;
	for (i=1, ent=NEXT_EDICT(sv.edicts) ; i<sv.num_edicts ; i++, ent=NEXT_EDICT(ent))
		if (!ent->free && (ent->area.prev || ent->num_leafs) && EdictChanged (ent, ch))
		{
			SV_LinkEdict (ent, false);
			n++;
		}
	return n;
}

/* ---------------------------------------------------------------- surface caches */

static void MoveCache (msurface_t *from, msurface_t *to)
{
	to->cachehead = from->cachehead;
	if (to->cachehead)
		to->cachehead->owner = &to->cachehead;
	from->cachehead = NULL;
}

static void DetachCache (msurface_t *s)
{
	surfcache_t *c;
	while ((c = s->cachehead) != NULL)
	{
		s->cachehead = c->surface_next;
		if (c->surface_next)
			c->surface_next->owner = &s->cachehead;
		c->owner = NULL;
		c->surface_next = NULL;
	}
}

/* ---------------------------------------------------------------- install */

static chim_user_t	pool_users[2];
static int			pool_current = -1;
/* Bytes of the slot's block when it was reserved at map start (it stays
 * allocated and locked until the map ends); 0: allocated per rebuild. */
static int			slot_bytes[2];
static int			reserve_bytes;		/* incremental: the block reserved at map start */
/* CHIM-GRAFT-REPACK-EMPTY-33: when the zone has no room for a block that
 * holds the whole ring, a repack keeps the nearest chunks that fit the
 * current block (squared distance up to ring_cap2) instead of dropping them
 * all; the rest wait until the zone has room for trim_want bytes again. */
static float		ring_cap2 = 1e30f;
static int			trim_want;

#define ALIGN8(n)	(((n)+7)&~7)

static void Install (chim_pool_t *p)
{
	world->nodes = p->nodes;
	world->numnodes = p->num[CA_NODE];
	world->leafs = p->leafs;
	world->numleafs = p->num[CA_LEAF] - 1;
	world->marksurfaces = p->marks;
	world->nummarksurfaces = p->num[CA_MARK];
	world->surfaces = p->surfs;
	world->numsurfaces = p->num[CA_SURF];
	world->firstmodelsurface = 0;
	world->nummodelsurfaces = p->num[CA_SURF];
	world->surfedges = p->surfedges;
	world->numsurfedges = p->num[CA_SURFEDGE];
	world->edges = p->edges;
	world->numedges = p->num[CA_EDGE];
	world->vertexes = p->verts;
	world->numvertexes = p->num[CA_VERT];
	world->planes = p->planes;
	world->numplanes = p->num[CA_PLANE];
	world->clipnodes = p->clips;
	world->numclipnodes = p->num[CA_CLIP];
	world->edgecache = p->edgecache;
	world->edgecache_count = p->num[CA_EDGE];
	world->visdata = p->vis;
	/* Faces carry their own lightmap pointers; R_LightPoint only needs to
	 * know that the world is lit. */
	world->lightdata = p->grafts && p->graft[0].terrain->model.lightdata ?
		p->graft[0].terrain->model.lightdata : saved.lightdata;
	world->hulls[0] = saved.hulls[0];
	world->hulls[0].clipnodes = p->clips0;
	world->hulls[0].planes = p->planes;
	world->hulls[0].firstclipnode = 0;
	world->hulls[0].lastclipnode = p->num[CA_NODE] - 1;
	world->hulls[1] = saved.hulls[1];
	world->hulls[1].clipnodes = p->clips;
	world->hulls[1].planes = p->planes;
	world->hulls[1].firstclipnode = 0;
	world->hulls[1].lastclipnode = p->num[CA_CLIP] - 1;
	/* The format stores one standing hull; the large hull uses it too. */
	world->hulls[2] = world->hulls[1];
	VectorCopy (saved.hulls[2].clip_mins, world->hulls[2].clip_mins);
	VectorCopy (saved.hulls[2].clip_maxs, world->hulls[2].clip_maxs);
}

static void Timed (double started, long bytes)
{
	double took = Sys_FloatTime () - started;
	stats.seconds += took;
	if (took > stats.worst)
		stats.worst = took;
	if (bytes > stats.i_bytes)
		stats.i_bytes = bytes;
	stats.interval++;
}

/* ---------------------------------------------------------------- full rebuild (method 0) */

int ChimGraft_Rebuild (void)
{
	chim_build_t b;
	chim_pool_t *p, *old = pool_current >= 0 ? pool_users[pool_current].data : NULL;
	int next = pool_current >= 0 ? !pool_current : 0;
	int size, at, row_bytes, i, k, n = 0, client, lost = 0;
	byte *base;
	double started = Sys_FloatTime (), took;

	if (!world)
		return 0;
	memset (&b, 0, sizeof(b));
	b.dry = 1;
	b.copy = 1;
	Build (&b);
	if (b.n[CA_SURF] > 65535 || b.n[CA_VERT] > 65535 || b.n[CA_LEAF] > MAX_MAP_LEAFS || b.n[CA_NODE] > 65520 ||
		b.n[CA_CLIP] > 65520)
	{
		if (!stats.failing++)
			Con_Printf ("CHIM: frame world over Quake's limits (%ld surfaces, %ld vertexes, %ld leaves)\n",
				(long)b.n[CA_SURF], (long)b.n[CA_VERT], (long)b.n[CA_LEAF]);
		stats.failures++;
		return 0;
	}
	row_bytes = (b.n[CA_LEAF] - 1 + 7) >> 3;
	size = ALIGN8 (sizeof(chim_pool_t)) + ALIGN8 (b.grafts*sizeof(chim_graft_t)) +
		ALIGN8 (b.n[CA_NODE]*sizeof(mnode_t)) + ALIGN8 (b.n[CA_LEAF]*sizeof(mleaf_t)) +
		ALIGN8 (b.n[CA_MARK]*sizeof(msurface_t *)) + ALIGN8 (b.n[CA_SURF]*sizeof(msurface_t)) +
		ALIGN8 (b.n[CA_SURFEDGE]*sizeof(int)) + ALIGN8 (b.n[CA_EDGE]*sizeof(medge_t)) +
		ALIGN8 (b.n[CA_VERT]*sizeof(mvertex_t)) + ALIGN8 (b.n[CA_PLANE]*sizeof(mplane_t)) +
		ALIGN8 (b.n[CA_CLIP]*sizeof(dclipnode_t)) + ALIGN8 (b.n[CA_NODE]*sizeof(dclipnode_t)) +
		ALIGN8 (b.n[CA_EDGE]*sizeof(unsigned int)) + ALIGN8 (b.grafts*(2*row_bytes+2));
	if (slot_bytes[next] >= size)
	{
		p = pool_users[next].data;
		memset (p, 0, size);
	}
	else
	{
		if (slot_bytes[next])
		{
			/* Outgrown: the slot goes back to per-rebuild allocation. */
			ChimZone_Unlock (pool_users[next].data);
			ChimZone_Free (&pool_users[next]);
			slot_bytes[next] = 0;
			stats.outgrown++;
		}
		p = ChimZone_Alloc (&pool_users[next], size, CHIM_KIND_WORLD, 0);
		if (p)
			ChimZone_Lock (p);
	}
	if (!p)
	{
		/* Said once per run of failures; the chunks wait ungrafted. */
		if (!stats.failing++)
			Con_Printf ("CHIM: no room for the frame world (%ld bytes); new chunks wait\n", (long)size);
		stats.failures++;
		return 0;
	}
	stats.failing = 0;
	base = (byte *)p;
	at = ALIGN8 (sizeof(chim_pool_t));
#define CARVE(field, count, type) (p->field = (type *)(base + at), at += ALIGN8 ((count)*sizeof(type)))
	CARVE (graft, b.grafts, chim_graft_t);
	CARVE (nodes, b.n[CA_NODE], mnode_t);
	CARVE (leafs, b.n[CA_LEAF], mleaf_t);
	CARVE (marks, b.n[CA_MARK], msurface_t *);
	CARVE (surfs, b.n[CA_SURF], msurface_t);
	CARVE (surfedges, b.n[CA_SURFEDGE], int);
	CARVE (edges, b.n[CA_EDGE], medge_t);
	CARVE (verts, b.n[CA_VERT], mvertex_t);
	CARVE (planes, b.n[CA_PLANE], mplane_t);
	CARVE (clips, b.n[CA_CLIP], dclipnode_t);
	CARVE (clips0, b.n[CA_NODE], dclipnode_t);
	CARVE (edgecache, b.n[CA_EDGE], unsigned int);
	CARVE (vis, b.grafts*(2*row_bytes+2), byte);
#undef CARVE
	p->grafts = b.grafts;
	p->block = size;
	for (i=0 ; i<CA_ARRAYS ; i++)
		p->num[i] = b.n[i];
	memset (&b, 0, sizeof(b));
	b.p = p;
	b.copy = 1;
	Build (&b);
	for (i=0 ; i<CA_ARRAYS ; i++)
		if (b.n[i] != p->num[i])
			Sys_Error ("CHIM: frame world count mismatch");
	if (b.grafts != p->grafts)
		Sys_Error ("CHIM: frame world count mismatch");
	Hull0 (p, 0, p->num[CA_NODE]);
	Visibility (p);
	for (i=0 ; i<p->grafts ; i++)
		ChimZone_Lock (p->graft[i].terrain);
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_frame.entries[i].grafted = 0;
		chim_frame.entries[i].graft = -1;
	}
	for (i=0 ; i<p->grafts ; i++)
	{
		chim_frame.entries[p->graft[i].entry].grafted = 1;
		chim_frame.entries[p->graft[i].entry].graft = i;
	}
	stats.copied += p->grafts;

	/* Surface caches move with their surfaces; the rest let go. */
	if (old)
	{
		for (i=0 ; i<p->grafts ; i++)
		{
			chim_graft_t *g = &p->graft[i], *o = NULL;
			/* Both lists are in grid order; a ring holds a few dozen chunks. */
			for (k=0 ; k<old->grafts && !o ; k++)
				if (old->graft[k].entry == g->entry && old->graft[k].terrain == g->terrain)
					o = &old->graft[k];
			if (!o)
				continue;
			for (k=0 ; k<g->terrain->model.numsurfaces ; k++)
				MoveCache (&old->surfs[o->base[CA_SURF]+k], &p->surfs[g->base[CA_SURF]+k]);
			stats.carried++;
		}
		for (i=0 ; i<old->num[CA_SURF] ; i++)
			if (old->surfs[i].cachehead)
			{
				DetachCache (&old->surfs[i]);
				stats.detached++;
			}
	}
	/* Client: release every efrag in the old leaves, install, link again. */
	client = cl.worldmodel == world;
	if (client && old)
	{
		ChimChunks_ReleaseEfrags ();
		n = ReleaseLeafEfrags (old, &lost);
	}
	if (old)
		SweepFreeEfrags ();
	Install (p);
	r_viewleaf = r_oldviewleaf = NULL;
	for (i=0 ; i<n ; i++)
		R_AddEfrags (readd[i]);
	stats.statics += n;
	stats.lost += lost;
	if (client)
		ChimChunks_Link ();
	stats.edicts += RelinkEdicts ();
	if (old)
	{
		for (i=0 ; i<old->grafts ; i++)
			ChimZone_Unlock (old->graft[i].terrain);
		if (!slot_bytes[pool_current])
		{
			ChimZone_Unlock (old);
			ChimZone_Free (&pool_users[pool_current]);
		}
	}
	pool_current = next;
	stats.rebuilds++;
	took = Sys_FloatTime () - started;
	if (chim_debug.value)
		Con_Printf ("CHIM: rebuild %ld chunks, %ld nodes, %ld leaves, %ld surfaces, %ld bytes, %ld us\n",
			(long)p->grafts, (long)p->num[CA_NODE], (long)p->num[CA_LEAF], (long)p->num[CA_SURF], (long)size,
			(long)(took*1e6));
	Timed (started, size);
	stats.grafts = p->grafts; stats.nodes = p->num[CA_NODE]; stats.leafs = p->num[CA_LEAF];
	stats.surfs = p->num[CA_SURF]; stats.bytes = size;
	return 1;
}

/* ---------------------------------------------------------------- incremental pool (method 1) */

/* Free ranges of array a, sorted by base; first fit. */
static chim_range_t *Gaps (chim_pool_t *p, int a)
{
	return p->gaps + a*p->gap_rows;
}

static int GapAlloc (chim_pool_t *p, int a, int n, int *base)
{
	chim_range_t *g = Gaps (p, a);
	int i, k;
	if (n <= 0)
	{
		*base = 0;
		return 1;
	}
	for (i=0 ; i<p->gap_count[a] ; i++)
		if (g[i].count >= n)
		{
			*base = g[i].base;
			g[i].base += n;
			g[i].count -= n;
			if (!g[i].count)
			{
				for (k=i ; k<p->gap_count[a]-1 ; k++)
					g[k] = g[k+1];
				p->gap_count[a]--;
			}
			return 1;
		}
	return 0;
}

static void GapFree (chim_pool_t *p, int a, int base, int n)
{
	chim_range_t *g = Gaps (p, a);
	int i, k;
	if (n <= 0)
		return;
	for (i=0 ; i<p->gap_count[a] && g[i].base < base ; i++)
		;
	if (i > 0 && g[i-1].base + g[i-1].count == base)
	{
		g[i-1].count += n;
		if (i < p->gap_count[a] && base + n == g[i].base)
		{
			g[i-1].count += g[i].count;
			for (k=i ; k<p->gap_count[a]-1 ; k++)
				g[k] = g[k+1];
			p->gap_count[a]--;
		}
		return;
	}
	if (i < p->gap_count[a] && base + n == g[i].base)
	{
		g[i].base = base;
		g[i].count += n;
		return;
	}
	if (p->gap_count[a] >= p->gap_rows)
		Sys_Error ("CHIM: frame world free ranges full");
	for (k=p->gap_count[a] ; k>i ; k--)
		g[k] = g[k-1];
	g[i].base = base;
	g[i].count = n;
	p->gap_count[a]++;
}

/* Elements in use from index 0: the reserved front, every graft, the end. */
static void HighWater (chim_pool_t *p)
{
	int a, last;
	chim_range_t *g;
	for (a=0 ; a<CA_ARRAYS ; a++)
	{
		g = Gaps (p, a);
		last = p->gap_count[a] - 1;
		p->num[a] = last >= 0 && g[last].base + g[last].count == p->cap[a] ? g[last].base : p->cap[a];
	}
}

/* Where the chunks' part of each array starts: after the grid's reserve
 * (leaves: and after the solid leaf 0; edges: after edge 0). */
static int Front (int a)
{
	return a == CA_LEAF || a == CA_EDGE;
}

static int ChunkStart (const chim_pool_t *p, int a)
{
	return Front (a) + p->grid_cap[a];
}

/* A chunk can be active out to the load radius: the most chunk squares a
 * disc of that radius touches. */
static int RingChunks (void)
{
	float r = ChimChunks_LoadRadius ();
	int side = (int)(2*r / chim_frame.frame.grain) + 2;
	int n = side*side;
	return n > chim_frame.count ? chim_frame.count : n;
}

static int FixedBytes (int graft_cap)
{
	int cells = (chim_frame.frame.nx + 1) * (chim_frame.frame.ny + 1);
	return ALIGN8 (sizeof(chim_pool_t)) + ALIGN8 (graft_cap*sizeof(chim_graft_t)) +
		2*ALIGN8 (CA_ARRAYS*(graft_cap+2)*sizeof(chim_range_t)) + ALIGN8 (cells*sizeof(unsigned short)) +
		ALIGN8 (chim_frame.count) + ALIGN8 (graft_cap*sizeof(int)) + 8*(CA_ARRAYS + 4);
}

/* Vis rows cost each leaf a share of every row: at most graft_cap rows of
 * RowBound bytes over all leaves. */
static int VisReserve (int graft_cap, int leaves)
{
	return graft_cap * RowBound ((leaves + 7) >> 3);
}

/* A block that lays out this need with every array times factor. */
static int NeedBytes (const int *need, int graft_cap, int factor)
{
	int a, bytes = FixedBytes (graft_cap) + 64;
	for (a=0 ; a<CA_ARRAYS ; a++)
		bytes += ALIGN8 (need[a]*factor*ElementBytes (a)) + 8;
	/* Partition's factor estimate rounds; a twentieth more keeps it at 1. */
	bytes += ALIGN8 (VisReserve (graft_cap, need[CA_LEAF]*factor));
	return bytes + bytes/20;
}

/* Lay the arrays out in a block: every array gets its need times the same
 * factor (the room the block has over the need), within Quake's index
 * limits. Returns the factor, 0 when even the need does not fit. */
static float Partition (byte *base, int bytes, const int *need, const int *grid_need, int graft_cap, int commit)
{
	chim_pool_t *p = (chim_pool_t *)base;
	int fixed = FixedBytes (graft_cap), a, at, cap[CA_ARRAYS], grid_cap[CA_ARRAYS], chunk_need, tries;
	double content = 0, per_leaf = graft_cap * 3.0 / 16.0, f;
	long used = 0;

	for (a=0 ; a<CA_ARRAYS ; a++)
		content += (double)need[a] * (ElementBytes (a) + (a == CA_LEAF ? per_leaf : 0));
	content += graft_cap * 4.0 + 16*CA_ARRAYS;
	f = content > 0 ? (bytes - fixed) / content : 0;
	if (f > 64)
		f = 64;			/* an empty world: room for the ring stays in the block */
	/* The estimate above rounds; shrink the factor until the layout fits. */
	for (tries=0 ; tries<32 && f >= 1 ; tries++, f *= 0.97)
	{
		used = fixed;
		for (a=0 ; a<CA_ARRAYS ; a++)
		{
			cap[a] = (int)(need[a] * f);
			if (cap[a] < need[a])
				cap[a] = need[a];
			if (cap[a] > array_limit[a])
				cap[a] = array_limit[a];
			if (cap[a] < need[a])
				return 0;		/* over Quake's limits: no layout */
			/* The grid's reserve at the front; the chunks keep their need. */
			chunk_need = need[a] - grid_need[a] - Front (a);
			grid_cap[a] = grid_need[a] ? (int)(grid_need[a] * (f < 4 ? f : 4)) + 4 : 0;
			if (cap[a] - Front (a) - grid_cap[a] < chunk_need)
				grid_cap[a] = cap[a] - Front (a) - chunk_need;
			if (grid_cap[a] < grid_need[a])
				return 0;
			used += ALIGN8 (cap[a] * ElementBytes (a)) + 8;
		}
		used += ALIGN8 (VisReserve (graft_cap, cap[CA_LEAF]));
		if (used <= bytes)
			break;
	}
	if (f < 1 || used > bytes)
		return 0;
	if (!commit)
		return (float)f;
	memset (p, 0, sizeof(*p));
	p->incremental = 1;
	p->block = bytes;
	p->graft_cap = graft_cap;
	p->gap_rows = graft_cap + 2;
	at = ALIGN8 (sizeof(chim_pool_t));
#define CARVE(field, count, type) (p->field = (type *)(base + at), at += ALIGN8 ((count)*sizeof(type)))
	CARVE (graft, graft_cap, chim_graft_t);
	CARVE (gaps, CA_ARRAYS*p->gap_rows, chim_range_t);
	CARVE (spare, CA_ARRAYS*p->gap_rows, chim_range_t);
	CARVE (sums, (chim_frame.frame.nx + 1)*(chim_frame.frame.ny + 1), unsigned short);
	CARVE (plan, chim_frame.count, byte);
	CARVE (adds, graft_cap, int);
	CARVE (nodes, cap[CA_NODE], mnode_t);
	CARVE (clips0, cap[CA_NODE], dclipnode_t);
	CARVE (leafs, cap[CA_LEAF], mleaf_t);
	CARVE (marks, cap[CA_MARK], msurface_t *);
	CARVE (surfs, cap[CA_SURF], msurface_t);
	CARVE (surfedges, cap[CA_SURFEDGE], int);
	CARVE (edges, cap[CA_EDGE], medge_t);
	CARVE (edgecache, cap[CA_EDGE], unsigned int);
	CARVE (verts, cap[CA_VERT], mvertex_t);
	CARVE (planes, cap[CA_PLANE], mplane_t);
	CARVE (clips, cap[CA_CLIP], dclipnode_t);
#undef CARVE
	p->vis = base + at;
	p->vis_cap = VisReserve (graft_cap, cap[CA_LEAF]);
	if (at + p->vis_cap > bytes)
		Sys_Error ("CHIM: frame world layout over its block");
	for (a=0 ; a<CA_ARRAYS ; a++)
	{
		p->cap[a] = cap[a];
		p->grid_cap[a] = grid_cap[a];
		p->gap_count[a] = 0;
		GapFree (p, a, ChunkStart (p, a), cap[a] - ChunkStart (p, a));
	}
	/* Every leaf starts inert: solid, no parent, no faces. */
	memset (p->leafs, 0, cap[CA_LEAF]*sizeof(mleaf_t));
	for (a=0 ; a<cap[CA_LEAF] ; a++)
		p->leafs[a].contents = CONTENTS_SOLID;
	memset (p->surfs, 0, cap[CA_SURF]*sizeof(msurface_t));
	memset (p->edges, 0, sizeof(medge_t));
	return (float)f;
}

/* Copy one planned chunk into its ranges. */
static void Join (chim_pool_t *p, int entry, chim_changes_t *ch)
{
	chim_graft_t *g = &p->graft[p->grafts];
	int a, i;
	g->entry = entry;
	g->terrain = ChimModels_Terrain (entry);
	TemplateCounts (g->terrain, g->count);
	for (a=0 ; a<CA_ARRAYS ; a++)
		if (!GapAlloc (p, a, g->count[a], &g->base[a]))
			Sys_Error ("CHIM: frame world range for %s lost", array_name[a]);
	CopyGraft (p, g);
	Hull0 (p, g->base[CA_NODE], g->count[CA_NODE]);
	for (i=0 ; i<g->count[CA_EDGE] ; i++)
		p->edgecache[g->base[CA_EDGE]+i] = 0;
	ChimZone_Lock (g->terrain);
	chim_frame.entries[entry].grafted = 1;
	chim_frame.entries[entry].graft = p->grafts;
	p->grafts++;
	stats.adds++;
	stats.i_adds++;
	stats.copied++;
	if (ch)
		NoteSquare (ch, entry);
}

/* Give one chunk's ranges back; everything in its leaves is linked again. */
static void Leave (chim_pool_t *p, int k, chim_changes_t *ch)
{
	chim_graft_t *g = &p->graft[k];
	int a, i, client = cl.worldmodel == world;
	for (i=0 ; i<g->count[CA_LEAF] ; i++)
	{
		mleaf_t *l = &p->leafs[g->base[CA_LEAF]+i];
		if (client)
			PullLeaf (l, ch);
		memset (l, 0, sizeof(*l));
		l->contents = CONTENTS_SOLID;
	}
	for (i=0 ; i<g->count[CA_SURF] ; i++)
	{
		msurface_t *s = &p->surfs[g->base[CA_SURF]+i];
		if (s->cachehead)
		{
			DetachCache (s);
			stats.detached++;
		}
		/* A free surface points at nothing (its template may be evicted):
		 * code that walks every world surface skips it (no plane, no
		 * texinfo). */
		memset (s, 0, sizeof(*s));
	}
	if (ch->removed < CHIM_CHANGES)
	{
		ch->leaves[ch->removed][0] = g->base[CA_LEAF];
		ch->leaves[ch->removed][1] = g->base[CA_LEAF] + g->count[CA_LEAF];
		ch->removed++;
	}
	else
		ch->all = 1;
	NoteSquare (ch, g->entry);
	for (a=0 ; a<CA_ARRAYS ; a++)
		GapFree (p, a, g->base[a], g->count[a]);
	ChimZone_Unlock (g->terrain);
	chim_frame.entries[g->entry].grafted = 0;
	chim_frame.entries[g->entry].graft = -1;
	p->grafts--;
	if (k != p->grafts)
	{
		p->graft[k] = p->graft[p->grafts];
		chim_frame.entries[p->graft[k].entry].graft = k;
	}
	stats.removes++;
	stats.i_removes++;
}

/* The grid over the planned chunks, written into its reserve. */
static void WriteGrid (chim_pool_t *p)
{
	chim_build_t b;
	memset (&b, 0, sizeof(b));
	b.p = p;
	Build (&b);
	p->grid[CA_NODE] = b.n[CA_NODE];
	p->grid[CA_LEAF] = b.n[CA_LEAF] - 1;
	p->grid[CA_PLANE] = b.n[CA_PLANE];
	p->grid[CA_CLIP] = b.n[CA_CLIP];
	Hull0 (p, 0, p->grid[CA_NODE]);
}

static void GridNeed (chim_pool_t *p, int *n)
{
	chim_build_t b;
	int a;
	memset (&b, 0, sizeof(b));
	b.p = p;
	b.dry = 1;
	Build (&b);
	for (a=0 ; a<CA_ARRAYS ; a++)
		n[a] = 0;
	n[CA_NODE] = b.n[CA_NODE];
	n[CA_LEAF] = b.n[CA_LEAF] - 1;
	n[CA_PLANE] = b.n[CA_PLANE];
	n[CA_CLIP] = b.n[CA_CLIP];
}

static void Finish (chim_pool_t *p)
{
	HighWater (p);
	VisRows (p);
	Install (p);
	r_viewleaf = r_oldviewleaf = NULL;
	stats.grafts = p->grafts; stats.nodes = p->num[CA_NODE]; stats.leafs = p->num[CA_LEAF];
	stats.surfs = p->num[CA_SURF];
	stats.bytes = (int)CountBytes (p->num) + p->vis_bytes;
}

/* The need of the desired chunks within squared distance cap2 (all of them
 * with 1e30): their templates plus the grid over them and the arrays' fronts;
 * the plan is left in probe->plan. Returns how many chunks it holds. */
static int PlanNeed (chim_pool_t *probe, float cap2, int *need, int *grid_need)
{
	int i, a, n[CA_ARRAYS], desired = 0;
	chim_build_t b;
	for (a=0 ; a<CA_ARRAYS ; a++)
		need[a] = grid_need[a] = 0;
	for (i=0 ; i<chim_frame.count ; i++)
	{
		probe->plan[i] = (byte)(Desired (i) && chim_frame.entries[i].distance <= cap2);
		if (!probe->plan[i])
			continue;
		desired++;
		TemplateCounts (ChimModels_Terrain (i), n);
		for (a=0 ; a<CA_ARRAYS ; a++)
			need[a] += n[a];
	}
	Sums (probe);
	memset (&b, 0, sizeof(b));
	b.p = probe;
	b.dry = 1;
	Build (&b);
	grid_need[CA_NODE] = b.n[CA_NODE];
	grid_need[CA_LEAF] = b.n[CA_LEAF] - 1;
	grid_need[CA_PLANE] = b.n[CA_PLANE];
	grid_need[CA_CLIP] = b.n[CA_CLIP];
	for (a=0 ; a<CA_ARRAYS ; a++)
		need[a] += grid_need[a] + Front (a);
	return desired;
}

/* CHIM-GRAFT-REPACK-EMPTY-33: the largest ring of nearest chunks (a squared
 * distance cap, found by bisection) whose layout fits a block of these
 * bytes. Leaves its need in need/grid_need and the cap in ring_cap2;
 * returns its chunk count, 0 when not even the nearest chunk fits (the plan
 * and the need are then the whole ring's again). */
static int TrimRing (chim_pool_t *probe, int bytes, int graft_cap, int *need, int *grid_need)
{
	float lo = -1, hi = 0, mid;
	int i, k, a, n, over;
	for (i=0 ; i<chim_frame.count ; i++)
		if (Desired (i) && chim_frame.entries[i].distance > hi)
			hi = chim_frame.entries[i].distance;
	for (k=0 ; k<24 && hi - lo > 1 ; k++)
	{
		mid = lo < 0 ? 0 : (lo + hi) * 0.5f;
		n = PlanNeed (probe, mid, need, grid_need);
		for (over=0, a=0 ; a<CA_ARRAYS ; a++)
			if (need[a] > array_limit[a])
				over = 1;
		/* a quarter of headroom, so the next chunk to join finds free ranges */
		if (n && !over && Partition ((byte *)probe, bytes, need, grid_need, graft_cap, 0) >= 1.25f)
			lo = mid;
		else if (lo < 0)
			break;		/* not even the chunks under the player fit */
		else
			hi = mid;
	}
	if (lo < 0)
	{
		PlanNeed (probe, 1e30f, need, grid_need);
		return 0;
	}
	ring_cap2 = lo;
	return PlanNeed (probe, lo, need, grid_need);
}

/* The whole ring copied again into a block laid out for it: the current
 * block when it has room to spare, else a new one (the reserve, or twice
 * the need). Used at map start, at the first prime, and when the pool
 * cannot take a joining chunk (said, counted). */
static int Repack (const char *reason)
{
	chim_pool_t *old = pool_current >= 0 ? pool_users[pool_current].data : NULL, *p;
	int need[CA_ARRAYS], grid_need[CA_ARRAYS], desired = 0, i, a, graft_cap, want, next, nr = 0;
	int lost = 0, client = cl.worldmodel == world, in_place, shrink = 0, let_go = 0, empty = 0, exact, old_block;
	int trimmed = 0, ring = 0, over = 0;
	float f_old;
	static chim_pool_t probe;
	double started = Sys_FloatTime ();
	chim_user_t scratch;

	/* The need: the grid over every desired chunk, and their templates. The
	 * plan is worked out in the current pool's own plan (laid out again
	 * below), or in a scratch block when there is no pool yet. */
	memset (&probe, 0, sizeof(probe));
	scratch.data = NULL;
	if (old)
	{
		probe.plan = old->plan;
		probe.sums = old->sums;
	}
	else
	{
		if (!ChimZone_Alloc (&scratch, ALIGN8 (chim_frame.count) + (chim_frame.frame.nx+1)*(chim_frame.frame.ny+1)*2,
			CHIM_KIND_WORLD, 0))
		{
			if (!stats.failing++)
				Con_Printf ("CHIM: no room to plan the frame world; new chunks wait\n");
			stats.failures++;
			return 0;
		}
		probe.plan = scratch.data;
		probe.sums = (unsigned short *)((byte *)scratch.data + ALIGN8 (chim_frame.count));
	}
	ring_cap2 = 1e30f;
	desired = PlanNeed (&probe, ring_cap2, need, grid_need);
	if (scratch.data)
		ChimZone_Free (&scratch);
	for (a=0 ; a<CA_ARRAYS ; a++)
		if (need[a] > array_limit[a] && !over)
		{
			over = 1;
			if (!stats.failing++)
				Con_Printf ("CHIM: frame world over Quake's limits (%ld %s, at most %ld)\n", (long)need[a],
					array_name[a], (long)array_limit[a]);
		}
	if (over && !(old && chim_graft_trim.value))
	{
		stats.failures++;
		return 0;
	}
	graft_cap = RingChunks ();
	if (graft_cap < desired + desired/4 + 4)
		graft_cap = desired + desired/4 + 4;
	if (graft_cap > chim_frame.count)
		graft_cap = chim_frame.count;
	/* Where the ring goes:
	 * - in place, when the block holds half again the need (and, unless it
	 *   is the reserve, not eight times: an outsized block goes back to the
	 *   zone);
	 * - else a new block of twice the need (at least the reserve) while the
	 *   old one still holds the world; a smaller one goes where the old one
	 *   was (freed first), so the zone stays in one piece;
	 * - in a zone without room for both, the old block is let go first and
	 *   the need alone is tried, then the old block's size again: then
	 *   nothing joins and the chunks wait (said once). */
	f_old = old ? Partition ((byte *)&probe, old->block, need, grid_need, graft_cap, 0) : 0;
	in_place = old && f_old >= 1.5f && (old->block == reserve_bytes || f_old <= 8);
	want = NeedBytes (need, graft_cap, 2);
	exact = NeedBytes (need, graft_cap, 1);
	if (want < reserve_bytes)
		want = reserve_bytes;
	if (over)
	{
		/* CHIM-GRAFT-REPACK-EMPTY-33: a ring over Quake's limits keeps the
		 * nearest chunks within them in the old block (more room does not
		 * help: the trim lifts when nothing waits). */
		if ((trimmed = TrimRing (&probe, old->block, graft_cap, need, grid_need)) <= 0)
		{
			stats.failures++;
			return 0;
		}
		ring = desired;
		trim_want = 0x7fffffff;
		in_place = 1;
		stats.trims++;
	}
	next = pool_current >= 0 ? pool_current : 0;
	p = NULL;
	if (!in_place)
	{
		next = old ? !pool_current : 0;
		shrink = old && want <= old->block;
		if (!shrink && !(p = ChimZone_Alloc (&pool_users[next], want, CHIM_KIND_WORLD, 0)))
		{
			if (old && f_old >= 1)
			{
				in_place = 1;		/* tight: no room for a larger block */
				next = pool_current;
				stats.capped++;
			}
			else if (old && chim_graft_trim.value &&
				(trimmed = TrimRing (&probe, old->block, graft_cap, need, grid_need)) > 0)
			{
				/* CHIM-GRAFT-REPACK-EMPTY-33: the ring does not fit the
				 * block and the zone has no room for a larger one. The old
				 * block is kept (never let go before a new one is secured)
				 * and holds the nearest chunks that fit; the rest wait. */
				ring = desired;
				trim_want = want;
				in_place = 1;
				next = pool_current;
				stats.capped++;
				stats.trims++;
			}
			else if (old && chim_graft_trim.value)
			{
				/* Not even the nearest chunk fits the old block: it stays as
				 * it is (never let go for an empty world); retried later. */
				if (!stats.failing++)
					Con_Printf ("CHIM: no room for the frame world (%ld bytes); the ring stays, new chunks wait\n",
						(long)want);
				stats.failures++;
				return 0;
			}
			else if (old)
				let_go = 1;		/* the first method (chim_graft_trim 0): the old block goes first */
			else
			{
				if (!stats.failing++)
					Con_Printf ("CHIM: no room for the frame world (%ld bytes); new chunks wait\n", (long)want);
				stats.failures++;
				return 0;
			}
		}
	}
	/* Release everything that points into the old pool. */
	old_block = old ? old->block : 0;
	if (old)
	{
		if (client)
		{
			ChimChunks_ReleaseEfrags ();
			nr = ReleaseLeafEfrags (old, &lost);
		}
		for (i=0 ; i<old->num[CA_SURF] ; i++)
			if (old->surfs[i].cachehead)
			{
				DetachCache (&old->surfs[i]);
				stats.detached++;
			}
		SweepFreeEfrags ();
		for (i=0 ; i<old->grafts ; i++)
			ChimZone_Unlock (old->graft[i].terrain);
		if (!in_place)
		{
			ChimZone_Unlock (old);
			ChimZone_Free (&pool_users[pool_current]);
			if (reserve_bytes)
				stats.outgrown++;
			reserve_bytes = 0;		/* the reserve was this block */
		}
	}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_frame.entries[i].grafted = 0;
		chim_frame.entries[i].graft = -1;
	}
	if (shrink || let_go)
	{
		/* First fit finds the room the old block left. */
		p = ChimZone_Alloc (&pool_users[next], shrink ? want : exact, CHIM_KIND_WORLD, 0);
		if (!p)
		{
			p = ChimZone_Alloc (&pool_users[next], old_block, CHIM_KIND_WORLD, 0);
			empty = 1;
		}
		if (!p)
			Sys_Error ("CHIM: frame world lost its block");
	}
	if (p && !in_place)
		ChimZone_Lock (p);
	p = pool_users[next].data;
	if (empty)
	{
		/* Only the grid: the chunks wait for room. */
		for (a=0 ; a<CA_ARRAYS ; a++)
			need[a] = grid_need[a] = 0;
		need[CA_NODE] = grid_need[CA_NODE] = 1;
		need[CA_LEAF] = 3; grid_need[CA_LEAF] = 2;
		need[CA_PLANE] = grid_need[CA_PLANE] = 1;
		need[CA_CLIP] = grid_need[CA_CLIP] = 1;
		need[CA_EDGE] = 1;
		if (!stats.failing++)
			Con_Printf ("CHIM: no room for the frame world (%ld bytes); new chunks wait\n", (long)exact);
		stats.failures++;
	}
	else
		stats.failing = 0;
	if (Partition ((byte *)p, ChimZone_Size (p), need, grid_need, graft_cap, 1) < 1)
		Sys_Error ("CHIM: frame world block lost its layout");
	pool_current = next;
	memset (p->plan, 0, chim_frame.count);
	for (i=0 ; i<chim_frame.count && !empty ; i++)
		if (Desired (i) && chim_frame.entries[i].distance <= ring_cap2)
			p->plan[i] = 1;
	for (i=0 ; i<chim_frame.count ; i++)
		if (p->plan[i])
			Join (p, i, NULL);
	Sums (p);
	WriteGrid (p);
	Finish (p);
	for (i=0 ; i<nr ; i++)
		R_AddEfrags (readd[i]);
	stats.statics += nr;
	stats.lost += lost;
	if (client)
		ChimChunks_Link ();
	stats.edicts += RelinkEdicts ();
	stats.rebuilds++;
	stats.repacks++;
	stats.i_repacks++;
	strncpy (stats.repack_reason, reason, sizeof(stats.repack_reason)-1);
	if (chim_debug.value || (stats.repacks > 1 && desired))
		Con_Printf ("CHIM: frame world repacked (%s): %ld chunks, %ld KiB block\n", reason, (long)p->grafts,
			(long)(p->block/1024));
	if (trimmed && (chim_debug.value || !stats.trim_said++))
		Con_Printf ("CHIM: frame world holds the nearest %ld of %ld chunks (no room for %ld KiB); the rest wait\n",
			(long)trimmed, (long)ring, (long)(trim_want/1024));
	if (!trimmed)
		stats.trim_said = 0;
	Timed (started, CountBytes (p->num));
	/* A trimmed ring has chunks waiting (2): the frame world stays dirty, so
	 * Update lays the whole ring out again once the zone has room. */
	return empty ? 0 : trimmed ? 2 : 1;
}

/* One update of the incremental pool: chunks that left give their ranges
 * back; chunks that joined are copied in, nearest first, within the frame's
 * budget (phase 1: chim_graft_kib, phase 0: only those within the collision
 * margin, phase 2: all). Returns 1 when the pool holds exactly the active
 * chunks, 2 when chunks still wait for the budget, 0 when there was no room. */
static int Update (int phase)
{
	chim_pool_t *p = pool_current >= 0 ? pool_users[pool_current].data : NULL;
	static chim_changes_t ch;
	int a, i, j, k, adds = 0, removes = 0, more = 0, client = cl.worldmodel == world, n[CA_ARRAYS], base;
	int trim_waiting = 0;
	int grid_need[CA_ARRAYS];
	long budget = phase == 2 ? 0 : (long)(chim_graft_kib.value * 1024), spent = 0, bytes;
	float urgent2 = chim_frame.settings.collision_margin * chim_frame.settings.collision_margin;
	double started = Sys_FloatTime ();

	if (!p)
		return Repack ("no frame world");
	if (ring_cap2 < 1e30f)
	{
		/* A trimmed ring (CHIM-GRAFT-REPACK-EMPTY-33) is laid out whole
		 * again once the zone has room for the block it needed. */
		chim_zone_stats_t zs;
		ChimZone_Stats (&zs);
		if (zs.largest_free - zs.largest_free/9 >= trim_want)
			return Repack ("room again");
	}
	/* Plan: which grafts stay, which chunks join (nearest first). */
	memset (p->plan, 0, chim_frame.count);
	for (k=0 ; k<p->grafts ; k++)
	{
		chim_graft_t *g = &p->graft[k];
		if (Desired (g->entry) && ChimModels_Terrain (g->entry) == g->terrain)
			p->plan[g->entry] = 1;
		else
			removes++;
	}
	for (i=0 ; i<chim_frame.count ; i++)
	{
		chim_entry_t *e = &chim_frame.entries[i];
		if (e->graft >= 0 || !Desired (i))
			continue;
		if (e->distance > ring_cap2)
		{
			trim_waiting = 1;	/* beyond the trimmed ring: waits for room */
			continue;
		}
		if (adds >= p->graft_cap)
			return Repack ("graft table full");
		for (k=adds ; k>0 && chim_frame.entries[p->adds[k-1]].distance > e->distance ; k--)
			p->adds[k] = p->adds[k-1];
		p->adds[k] = i;
		adds++;
	}
	if (!trim_waiting)
		ring_cap2 = 1e30f;		/* every desired chunk is within reach again */
	if (!removes && !adds)
		return trim_waiting ? 2 : 1;
	/* Within the budget (always at least one chunk; never a chunk within
	 * the collision margin left waiting). Phase 0 only takes urgent ones. */
	for (j=0 ; j<adds ; j++)
	{
		chim_entry_t *e = &chim_frame.entries[p->adds[j]];
		int urgent = e->distance <= urgent2;
		TemplateCounts (ChimModels_Terrain (p->adds[j]), n);
		bytes = CountBytes (n);
		if (!urgent && (phase == 0 || (budget > 0 && j > 0 && spent + bytes > budget)))
			break;
		if (urgent && budget > 0 && j > 0 && spent + bytes > budget)
			stats.urgent++;
		spent += bytes;
	}
	more = j < adds || trim_waiting;
	adds = j;
	if (!removes && !adds)
		return more ? 2 : 1;
	/* Without a reserve the block was sized for an earlier ring: when most
	 * of it left (a long jump), the block goes back to the zone for one
	 * sized for what stays, so the new ring finds room to load. */
	if (removes && !reserve_bytes)
	{
		long keep = spent;
		for (k=0 ; k<p->grafts ; k++)
			if (p->plan[p->graft[k].entry])
				keep += CountBytes (p->graft[k].count);
		if (p->block > FixedBytes (p->graft_cap) + 8*keep)
			return Repack ("pool outsized");
	}
	/* Check the plan fits before anything changes: the graft table, every
	 * array's free ranges (first fit on a copy), the grid's reserve. */
	if (p->grafts - removes + adds > p->graft_cap)
		return Repack ("graft table full");
	{
		int saved_count[CA_ARRAYS], ok = 1;
		for (a=0 ; a<CA_ARRAYS ; a++)
		{
			memcpy (p->spare + a*p->gap_rows, Gaps (p, a), p->gap_count[a]*sizeof(chim_range_t));
			saved_count[a] = p->gap_count[a];
		}
		for (k=0 ; k<p->grafts ; k++)
			if (!p->plan[p->graft[k].entry])
				for (a=0 ; a<CA_ARRAYS ; a++)
					GapFree (p, a, p->graft[k].base[a], p->graft[k].count[a]);
		for (j=0 ; j<adds && ok ; j++)
		{
			TemplateCounts (ChimModels_Terrain (p->adds[j]), n);
			for (a=0 ; a<CA_ARRAYS && ok ; a++)
				if (!GapAlloc (p, a, n[a], &base))
				{
					ok = 0;
					strcpy (stats.repack_reason, array_name[a]);
				}
		}
		for (a=0 ; a<CA_ARRAYS ; a++)
		{
			memcpy (Gaps (p, a), p->spare + a*p->gap_rows, saved_count[a]*sizeof(chim_range_t));
			p->gap_count[a] = saved_count[a];
		}
		if (!ok)
		{
			char reason[64];
			sprintf (reason, "%.40s full", stats.repack_reason);
			return Repack (reason);
		}
	}
	for (j=0 ; j<adds ; j++)
		p->plan[p->adds[j]] = 1;
	Sums (p);
	GridNeed (p, grid_need);
	for (a=0 ; a<CA_ARRAYS ; a++)
		if (grid_need[a] > p->grid_cap[a])
			return Repack ("grid reserve full");

	/* Commit. Entities in the old grid's empty leaves and in the leaves of
	 * chunks that leave are linked again; nothing else moves. */
	memset (&ch, 0, sizeof(ch));
	ch.old_grid = p->grid[CA_LEAF];
	for (i=1 ; i<=p->grid[CA_LEAF] ; i++)
	{
		if (client)
			PullLeaf (&p->leafs[i], &ch);
		memset (&p->leafs[i], 0, sizeof(mleaf_t));
		p->leafs[i].contents = CONTENTS_SOLID;
	}
	for (k=p->grafts-1 ; k>=0 ; k--)
		if (!p->plan[p->graft[k].entry])
			Leave (p, k, &ch);
	for (j=0 ; j<adds ; j++)
		Join (p, p->adds[j], &ch);
	WriteGrid (p);
	Finish (p);
	for (i=0 ; i<ch.readd ; i++)
		R_AddEfrags (readd[i]);
	stats.statics += ch.readd;
	stats.lost += ch.lost;
	if (client)
		ChimChunks_Link ();
	stats.edicts += RelinkChanged (&ch);
	stats.rebuilds++;
	if (chim_debug.value)
		Con_Printf ("CHIM: update %ld: +%ld -%ld chunks (%ld waiting), %ld bytes copied, %ld us\n", (long)phase, (long)adds,
			(long)removes, (long)(more ? 1 : 0), spent, (long)((Sys_FloatTime () - started)*1e6));
	Timed (started, spent);
	return more ? 2 : 1;
}

/* The frame world follows the active set: phase 0 after chunks left the
 * ring (gives their terrain back), 1 at the end of a tick (within the
 * budget), 2 when priming (everything). */
int ChimGraft_Update (int phase)
{
	if (!world)
		return 0;
	if (!incremental)
		return ChimGraft_Rebuild ();
	return Update (phase);
}

int ChimGraft_Incremental (void)
{
	return world && incremental;
}

/* ---------------------------------------------------------------- map */

int ChimGraft_Begin (model_t *w)
{
	int k, reserve = (int)chim_pool_kib.value * 1024, requested;
	chim_zone_stats_t zs;
	ChimZone_Stats (&zs);
	world = w;
	saved = *w;
	pool_current = -1;
	reserve_bytes = 0;
	ring_cap2 = 1e30f;
	trim_want = 0;
	memset (&stats, 0, sizeof(stats));
	incremental = chim_graft_mode.value != 0;
	if (incremental)
		reserve *= 2;		/* the same memory as the two slots of the full rebuild */
	requested = reserve;
	/* At most a twelfth of the zone per slot (a sixth for the one pool): a
	 * small zone keeps its room for models. Said when it applies. */
	if (reserve > (zs.used_bytes + zs.free_bytes) / (incremental ? 6 : 12))
		reserve = (zs.used_bytes + zs.free_bytes) / (incremental ? 6 : 12);
	if (reserve < requested)
	{
		stats.capped++;
		Con_Printf ("CHIM: frame world %s %ld KiB of %ld KiB asked (chim_pool_kib), the most a %s of the %ld KiB zone allows\n",
			incremental ? "pool" : "slots", (long)(reserve/1024), (long)(requested/1024), incremental ? "sixth" : "twelfth",
			(long)((zs.used_bytes + zs.free_bytes)/1024));
	}
	/* Reserved first, before any model or chunk is loaded, so the frame
	 * world never waits for contiguous room in a full zone. */
	for (k=0 ; k<2 ; k++)
	{
		slot_bytes[k] = 0;
		if (reserve > 0 && (!incremental || !k) && ChimZone_Alloc (&pool_users[k], reserve, CHIM_KIND_WORLD, 0))
		{
			ChimZone_Lock (pool_users[k].data);
			slot_bytes[k] = reserve;
		}
	}
	if (incremental)
	{
		if (slot_bytes[0])
		{
			/* The reserve is the pool: laid out for the empty world now and
			 * again (in place) when the ring first arrives. */
			reserve_bytes = slot_bytes[0];
			slot_bytes[0] = 0;
			pool_current = 0;
			{
				int need[CA_ARRAYS], grid_need[CA_ARRAYS], a;
				for (a=0 ; a<CA_ARRAYS ; a++)
					need[a] = grid_need[a] = 0;
				need[CA_NODE] = grid_need[CA_NODE] = 1;
				need[CA_LEAF] = 3; grid_need[CA_LEAF] = 2;
				need[CA_PLANE] = grid_need[CA_PLANE] = 1;
				need[CA_CLIP] = grid_need[CA_CLIP] = 1;
				need[CA_EDGE] = 1;
				if (Partition ((byte *)pool_users[0].data, reserve_bytes, need, grid_need, RingChunks (), 1) < 1)
				{
					ChimZone_Unlock (pool_users[0].data);
					ChimZone_Free (&pool_users[0]);
					pool_current = -1;
					reserve_bytes = 0;
				}
			}
		}
		if (pool_current >= 0)
		{
			chim_pool_t *p = pool_users[0].data;
			memset (p->plan, 0, chim_frame.count);
			Sums (p);
			WriteGrid (p);
			Finish (p);
			return 1;
		}
		if (Repack ("no reserve"))
			return 1;
	}
	else if (ChimGraft_Rebuild ())
		return 1;
	for (k=0 ; k<2 ; k++)
		if (pool_users[k].data)
		{
			ChimZone_Unlock (pool_users[k].data);
			ChimZone_Free (&pool_users[k]);
		}
	slot_bytes[0] = slot_bytes[1] = 0;
	reserve_bytes = 0;
	pool_current = -1;
	*world = saved;
	world = NULL;
	return 0;
}

/* Host_ClearMemory has already cleared the efrag pool (R_ClearEfrags runs
 * before AW_SceneryClear), so only the free list and caches are left. */
void ChimGraft_End (void)
{
	chim_pool_t *p;
	int i;
	if (!world)
		return;
	*world = saved;
	if (pool_current >= 0 && (p = pool_users[pool_current].data) != NULL)
	{
		for (i=0 ; i<p->num[CA_SURF] ; i++)
			DetachCache (&p->surfs[i]);
		SweepFreeEfrags ();
		for (i=0 ; i<p->grafts ; i++)
			ChimZone_Unlock (p->graft[i].terrain);
	}
	for (i=0 ; i<2 ; i++)
		if (pool_users[i].data)
		{
			ChimZone_Unlock (pool_users[i].data);
			ChimZone_Free (&pool_users[i]);
		}
	slot_bytes[0] = slot_bytes[1] = 0;
	reserve_bytes = 0;
	pool_current = -1;
	r_viewleaf = r_oldviewleaf = NULL;
	world = NULL;
}

/* Which graft holds a pool leaf: its frame entry and its leaf in the
 * chunk's own template (1..), or entry -1 for the grid's leaves (local:
 * the leaf's number among them) and leaf 0. For tests and reports. */
int ChimGraft_LeafOwner (int leaf, int *entry, int *local)
{
	chim_pool_t *p = pool_current >= 0 ? pool_users[pool_current].data : NULL;
	int k;
	*entry = -1;
	*local = leaf;
	if (!p || leaf <= 0)
		return 0;
	for (k=0 ; k<p->grafts ; k++)
		if (leaf >= p->graft[k].base[CA_LEAF] && leaf < p->graft[k].base[CA_LEAF] + p->graft[k].count[CA_LEAF])
		{
			*entry = p->graft[k].entry;
			*local = leaf - p->graft[k].base[CA_LEAF] + 1;
			return 1;
		}
	return 1;
}

void ChimGraft_Report (void)
{
	chim_pool_t *p = pool_current >= 0 ? pool_users[pool_current].data : NULL;
	int a;
	Con_Printf ("frame world (%s): %ld chunks grafted, %ld nodes, %ld leaves, %ld surfaces, %ld KiB; %lu updates, %lu failed\n",
		incremental ? "incremental, chim_graft_mode 1" : "full rebuild, chim_graft_mode 0", (long)stats.grafts,
		(long)stats.nodes, (long)stats.leafs, (long)stats.surfs, (long)(stats.bytes/1024), stats.rebuilds, stats.failures);
	if (incremental)
	{
		Con_Printf ("frame world pool: %ld KiB block (%s), %lu chunks joined, %lu left, %lu repacked (last: %s), %lu outgrown\n",
			(long)(p ? p->block/1024 : 0), reserve_bytes ? "reserved at map start" : "allocated when outgrown",
			stats.adds, stats.removes, stats.repacks, stats.repack_reason[0] ? stats.repack_reason : "none", stats.outgrown);
		Con_Printf ("budget: chim_graft_kib %ld bytes per frame + one chunk (0: none); %lu joined past it within the collision margin\n",
			(long)(chim_graft_kib.value * 1024), stats.urgent);
		if (p)
			for (a=0 ; a<CA_ARRAYS ; a++)
				Con_Printf ("  %-9s %6ld of %6ld (grid %ld of %ld)\n", array_name[a], (long)p->num[a], (long)p->cap[a],
					(long)p->grid[a], (long)p->grid_cap[a]);
	}
	else
		Con_Printf ("frame world slots: %ld and %ld KiB reserved at map start, %lu outgrown\n",
			(long)(slot_bytes[0]/1024), (long)(slot_bytes[1]/1024), stats.outgrown);
	Con_Printf ("updates: %lu chunks copied, %lu surface caches moved, %lu detached, %lu efrag owners and %lu edicts relinked, %lu not relinked\n",
		stats.copied, stats.carried, stats.detached, stats.statics + stats.relinked, stats.edicts, stats.lost);
}

/* Updates since the last call, their total and longest time (us). */
void ChimGraft_Interval (int *rebuilds, long *total_us, long *worst_us, int *pool_bytes)
{
	*rebuilds = stats.interval;
	*total_us = (long)(stats.seconds * 1e6 + .5);
	*worst_us = (long)(stats.worst * 1e6 + .5);
	*pool_bytes = stats.bytes;
	stats.interval = 0;
	stats.seconds = stats.worst = 0;
}

/* Chunks joined, left and repacks since the last call, and the most bytes
 * one update copied; with the urgent joins so far. */
void ChimGraft_Work (int *adds, int *removes, int *repacks, long *worst_bytes, unsigned long *urgent)
{
	*adds = stats.i_adds;
	*removes = stats.i_removes;
	*repacks = stats.i_repacks;
	*worst_bytes = stats.i_bytes;
	*urgent = stats.urgent;
	stats.i_adds = stats.i_removes = stats.i_repacks = 0;
	stats.i_bytes = 0;
}

void ChimGraft_Totals (unsigned long *adds, unsigned long *removes, unsigned long *repacks, unsigned long *copied,
	unsigned long *relinked, unsigned long *urgent)
{
	*adds = stats.adds;
	*removes = stats.removes;
	*repacks = stats.repacks;
	*copied = stats.copied;
	*relinked = stats.relinked + stats.statics + stats.edicts;
	*urgent = stats.urgent;
}

/* The frame-world slots reserved at map start (bytes, 0: per rebuild), how
 * often a slot was outgrown, and the rebuilds that found no room. The
 * incremental pool reports its block as slot 0. */
/* CHIM-GRAFT-REPACK-EMPTY-33: repacks that kept only the nearest chunks,
 * and whether the ring is trimmed now. */
void ChimGraft_Trims (unsigned long *trims, int *trimmed)
{
	*trims = stats.trims;
	*trimmed = ring_cap2 < 1e30f;
}

void ChimGraft_Slots (int *slot0, int *slot1, unsigned long *outgrown, unsigned long *failures)
{
	*slot0 = incremental ? reserve_bytes : slot_bytes[0];
	*slot1 = incremental ? 0 : slot_bytes[1];
	*outgrown = stats.outgrown;
	*failures = stats.failures;
}

void ChimGraft_Stats (int *rebuilds, int *grafts, int *leafs, int *surfs, int *bytes)
{
	*rebuilds = (int)stats.rebuilds;
	*grafts = stats.grafts;
	*leafs = stats.leafs;
	*surfs = stats.surfs;
	*bytes = stats.bytes;
}
