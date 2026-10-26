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
    RC_ALIAS_TRIS,      /* alias model triangles sent to the alias renderer (R_AliasDrawModel) */
    RC_LOD_NEAR,        /* NPCs drawn with their near level, level 0 (aw_npc_lod.c) */
    RC_LOD_COARSE,      /* NPCs drawn with a coarse level, 2 or 3 */
    RC_LOD_SLOTS,       /* NPC level models resident (per frame) */
    RC_FAR_FOG_ON,      /* 100 for each frame the fog-exact far test applies (aw_cull 2+, aw_fog.c) */
    RC_FAR_FOG_DEPTH,   /* its view depth from which geometry may be left out, while on */
    RC_FAR_FOG_WHY,     /* while off: why (aw_fog.c fog_exact_begin) */
    RC_FAR_FOG_MODELS,  /* brush model passes the fog-exact far test left out */
    RC_FAR_FOG_FACES,   /* front faces it left out */
    RC_FAR_SIZE,        /* passes the size-scaled cut-off left out (aw_cull 3, 4, 6) */
    RC_FAR_DETAIL,      /* front faces the far detail step left out (aw_cull 5, 6) */
    RC_COUNTERS
};
/* RT_SKY: the background sky spans (D_DrawBackground, inside RT_DRAW); RT_FOG: the fog
 * and day/night sky pixel pass (AW_FogDraw, inside RT_VIEW). RT_SKELPOSE / RT_SKELVERTS: a skeletal actor's
 * posing, the bones from the table (AW_SkelPose) and the vertices (AW_SkelPoseVerts), inside RT_ALIAS
 * (SKEL-RUNTIME-COST-52); the line's "kp" field, with the poses made and drawn from the pose cache. */
enum { RT_WORLD, RT_BMODELS, RT_SCAN, RT_DRAW, RT_ALIAS, RT_VIEW, RT_SKY, RT_FOG, RT_SKELPOSE, RT_SKELVERTS, RT_TIMERS };

#ifdef AMIGA
extern long aw_rcount[RC_COUNTERS];
extern int aw_rcount_timing;            /* timers run (aw_rcount on) */
extern double aw_rtime[RT_TIMERS];      /* seconds this frame */
double AW_RCountClock(void);
#define AW_RC(i) (aw_rcount[i]++)
#define AW_RC_ADD(i, n) (aw_rcount[i] += (n))
#define AW_RC_GET(i) (aw_rcount[i])
#define AW_RT_BEGIN(t0) ((t0) = aw_rcount_timing ? AW_RCountClock() : 0)
#define AW_RT_END(slot, t0) do { if (aw_rcount_timing) aw_rtime[slot] += AW_RCountClock() - (t0); } while (0)
#else   /* host tests of renderer files: no counter storage linked */
#define AW_RC(i) ((void)0)
#define AW_RC_ADD(i, n) ((void)0)
#define AW_RC_GET(i) 0L
#define AW_RT_BEGIN(t0) ((t0) = 0)
#define AW_RT_END(slot, t0) ((void)(t0))
#define AW_RCountLine() ""
#define AW_RCountInit() ((void)0)
#define AW_RCountFrame() ((void)0)
#endif

/* dbg rcount 3/4 (aw_rcount.c "rprof" line): the brush-model slot split into the
 * BSP clip walk and the fragment emit (EClock ticks, corrected for the cost
 * of reading the clock), front faces and sent faces per distance band x model
 * size class, and leaves touched per in-view placement. Everything runs only
 * while aw_rcount is 3 or 4 (one integer test per site otherwise). */
enum { RP_PASS, RP_CLIP, RP_EMIT, RP_ONELEAF, RP_TIMERS };
#define RP_BANDS 5      /* 0-25/25-50/50-75/75-100 % of the draw distance, beyond */
#define RP_SIZES 4      /* model radius <32, 32-128, 128-512, >=512 units */
#ifdef AMIGA
extern int aw_rprof_on;
extern unsigned long aw_rprof_ticks[RP_TIMERS];
extern long aw_rprof_pairs[RP_TIMERS];
unsigned long AW_RProfTicks(void);
void AW_RProfModel(const float *origin, float radius, long front, long sent, int leaves, int visible_leaves);
const char *AW_RProfLine(void);         /* last once-a-second line, "" if none */
#define AW_RP_BEGIN(t0) ((t0) = aw_rprof_on ? AW_RProfTicks() : 0)
#define AW_RP_END(slot, t0) do { if (aw_rprof_on) { aw_rprof_ticks[slot] += AW_RProfTicks() - (t0); aw_rprof_pairs[slot]++; } } while (0)
#else
#define aw_rprof_on 0
#define AW_RP_BEGIN(t0) ((t0) = 0)
#define AW_RP_END(slot, t0) ((void)(t0))
#define AW_RProfModel(o, r, f, s, l, v) ((void)0)
#define AW_RProfLine() ""
#endif

#ifdef AMIGA
void AW_RCountInit(void);
void AW_RCountFrame(void);
const char *AW_RCountLine(void);        /* last once-a-second line, "" if none */
#endif
/* CHIM appends its own fields (chim/chim_world.c sets it with its data). */
extern int (*aw_chim_rcount)(char *out, int size, long frames);

#endif
