/* SPDX-License-Identifier: GPL-2.0-or-later
 * Renderer counters (dbg rcount / aw_rcount 1; aw_rcount.c). Plain integer
 * increments in the renderer, like Quake's own c_faceclip / r_polycount /
 * c_surf; the timing split runs only while the cvar is on.
 */
#ifndef AW_RCOUNT_H
#define AW_RCOUNT_H

enum {
    RC_BM_PASSES,       /* brush model passes considered (entities + render-range views) */
    RC_BM_VISIBLE,      /* passed the AmiWind distance/fog test */
    RC_BM_INVIEW,       /* not fully clipped by the view frustum (bounding box) */
    RC_BM_CLIPPED,      /* box spans world nodes: faces clipped down the world BSP */
    RC_BM_ONELEAF,      /* box in one world leaf: faces straight to the edge list */
    RC_BF_TESTED,       /* brush model faces given the backface test */
    RC_BF_FRONT,        /* ... facing the camera */
    RC_CLIP_FACES,      /* front faces on the clipped path (R_RecursiveClipBPoly) */
    RC_FRAGMENTS,       /* fragments emitted by it (R_RenderBmodelFace calls) */
    RC_CLIP_NODES,      /* world BSP nodes visited clipping them (R_RecursiveClipBPoly calls) */
    RC_LEAF_FACES,      /* front faces on the one-leaf path (R_DrawSubmodelPolygons) */
    RC_WORLD_FACES,     /* world faces sent to R_RenderFace */
    RC_EDGES_NEW,       /* edges emitted (R_EmitEdge) */
    RC_EDGES_CACHED,    /* edges reused from the edge cache (R_EmitCachedEdge) */
    RC_EDGES_USED,      /* edge records used this frame */
    RC_SURFS,           /* span surfaces used this frame */
    RC_SPANS,           /* spans generated (R_ScanEdges) */
    RC_SC_ALLOC,        /* surface cache allocations (D_SCAlloc) */
    RC_SC_ALLOC_BYTES,  /* ... bytes */
    RC_SC_BUILD,        /* surface cache blocks drawn (D_CacheSurface misses) */
    RC_SC_BUILD_BYTES,  /* ... texels drawn */
    RC_ENTITIES,        /* entities in cl_visedicts this frame (R_StoreEfrags, edicts) */
    RC_SPRITES,         /* sprite entities drawn (R_DrawSprite) */
    RC_COUNTERS
};
enum { RT_WORLD, RT_BMODELS, RT_SCAN, RT_DRAW, RT_ALIAS, RT_VIEW, RT_TIMERS };

#ifdef AMIGA
extern long aw_rcount[RC_COUNTERS];
extern int aw_rcount_timing;            /* timers run (aw_rcount on) */
extern double aw_rtime[RT_TIMERS];      /* seconds this frame */
double AW_RCountClock(void);
#define AW_RC(i) (aw_rcount[i]++)
#define AW_RC_ADD(i, n) (aw_rcount[i] += (n))
#define AW_RT_BEGIN(t0) ((t0) = aw_rcount_timing ? AW_RCountClock() : 0)
#define AW_RT_END(slot, t0) do { if (aw_rcount_timing) aw_rtime[slot] += AW_RCountClock() - (t0); } while (0)
#else   /* host tests of renderer files: no counter storage linked */
#define AW_RC(i) ((void)0)
#define AW_RC_ADD(i, n) ((void)0)
#define AW_RT_BEGIN(t0) ((t0) = 0)
#define AW_RT_END(slot, t0) ((void)(t0))
#define AW_RCountLine() ""
#define AW_RCountInit() ((void)0)
#define AW_RCountFrame() ((void)0)
#endif

#ifdef AMIGA
void AW_RCountInit(void);
void AW_RCountFrame(void);
const char *AW_RCountLine(void);        /* last once-a-second line, "" if none */
#endif
/* CHIM appends its own fields (chim/chim_world.c sets it with its data). */
extern int (*aw_chim_rcount)(char *out, int size, long frames);

#endif
