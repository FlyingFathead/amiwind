/* SPDX-License-Identifier: GPL-2.0-or-later
 * d_fence.c: see-through ("fence") faces of the world, rooms and brush models
 * (ROOM-DECAL-ALPHA-62, CHIM-MODEL-FENCE-FACES-64).
 *
 * A face whose texture name starts with '{' (the converter names every texture
 * with see-through texels so; palette index 255 is its transparent texel) is
 * kept out of the edge list: r_bsp.c hands it to R_FenceAdd instead, which
 * appends it to a small per-frame list. After R_ScanEdges has drawn the opaque
 * world (z written), D_DrawFences draws each listed face on its own: rotated for
 * its entity as D_DrawSurfaces does for submodels, its lit tile from the surface
 * cache (r_surf.c passes index 255 through unshaded for these faces), clipped
 * against the view planes and the near plane in model space, one span per row
 * (the sprite rasteriser's pattern), then per texel: 255 = skip, else z read,
 * compare, z write and colour write. Models and sprites drawn after it z-test
 * against it. No sorting: nothing blends, and a transparent texel writes no z.
 *
 * aw_fence 0 (the default until a measured A/B decides) keeps every face on the
 * edge list as before: the old path stays selectable. Counters on the rcount
 * line ("fn"): faces drawn this way, texels visited, texels written.
 */
#include "quakedef.h"
#include "r_local.h"
#include "d_local.h"
#include "aw_rcount.h"
#include "d_fence.h"

cvar_t	aw_fence = {"aw_fence", "0"};

extern int	r_fence_cache_on;	/* r_surf.c: the fence block drawer for SURF_DRAWFENCE tiles */
extern vec3_t	transformed_modelorg;	/* d_edge.c */

#define AW_FENCE_FACES	384		/* faces per frame; more are drawn solid on the edge list */
#define AW_FENCE_VERTS	72		/* polygon vertices after clipping (5 planes) */

typedef struct
{
	msurface_t	*surf;
	entity_t	*ent;
} fenceface_t;

static fenceface_t	fence_faces[AW_FENCE_FACES];
static int		fence_count;
static int		fence_cache_state = -1;
static int		fence_miplevel;

typedef struct
{
	float	u, v;
} fencept_t;

static fencept_t	fence_pts[AW_FENCE_VERTS + 1];
static int		fence_nump, fence_minindex, fence_maxindex;
static sspan_t		fence_spans[MAXHEIGHT + 1];

extern int (*r_fence_add) (msurface_t *surf, entity_t *ent);	/* r_bsp.c */
extern void (*r_fence_begin) (void), (*r_fence_draw) (void);	/* r_main.c */

/* d_init.c D_Init: the switch and the hooks (r_bsp.c and r_main.c hold only
 * pointers, so their host tests link without this file) */
void D_FenceInit (void)
{
	Cvar_RegisterVariable (&aw_fence);
	r_fence_add = R_FenceAdd;
	r_fence_begin = D_FenceBeginFrame;
	r_fence_draw = D_DrawFences;
}

/* The surface cache holds a fence tile drawn one way or the other: flush it when
 * the switch changes, so aw_fence 0 shows exactly the old solid tiles. */
static void FenceCacheState (void)
{
	int	on = aw_fence.value != 0;

	if (on != fence_cache_state)
	{
		if (fence_cache_state != -1)
			D_FlushCaches ();
		fence_cache_state = on;
		r_fence_cache_on = on;
	}
}

void D_FenceBeginFrame (void)
{
	fence_count = 0;
	FenceCacheState ();
}

/* r_bsp.c: 1 = the face is listed (keep it off the edge list), 0 = draw it solid. */
int R_FenceAdd (msurface_t *surf, entity_t *ent)
{
	if (!r_fence_cache_on || fence_count >= AW_FENCE_FACES)
		return 0;
	fence_faces[fence_count].surf = surf;
	fence_faces[fence_count].ent = ent;
	fence_count++;
	return 1;
}

/* One clip of the winding IN (n points) against PLANE into OUT; the back side goes. */
static int FenceClip (float (*in)[3], int n, float (*out)[3], clipplane_t *plane)
{
	int	i, count = 0;
	float	dists[AW_FENCE_VERTS + 1], frac;
	float	*a, *b;

	for (i=0 ; i<n ; i++)
		dists[i] = DotProduct (in[i], plane->normal) - plane->dist;
	dists[n] = dists[0];
	for (i=0 ; i<n ; i++)
	{
		a = in[i];
		b = in[i+1 < n ? i+1 : 0];
		if (dists[i] >= 0)
		{
			if (count >= AW_FENCE_VERTS)
				return 0;
			VectorCopy (a, out[count]);
			count++;
		}
		if (dists[i] == 0 || dists[i+1] == 0 || (dists[i] > 0) == (dists[i+1] > 0))
			continue;
		if (count >= AW_FENCE_VERTS)
			return 0;
		frac = dists[i] / (dists[i] - dists[i+1]);
		out[count][0] = a[0] + frac*(b[0] - a[0]);
		out[count][1] = a[1] + frac*(b[1] - a[1]);
		out[count][2] = a[2] + frac*(b[2] - a[2]);
		count++;
	}
	return count;
}

/* D_CalcGradients (d_edge.c) with this pass's own mip level. */
static void FenceGradients (msurface_t *pface, int mip)
{
	float	mipscale, t;
	vec3_t	p_temp1, p_saxis, p_taxis;

	mipscale = 1.0 / (float)(1 << mip);
	TransformVector (pface->texinfo->vecs[0], p_saxis);
	TransformVector (pface->texinfo->vecs[1], p_taxis);

	t = xscaleinv * mipscale;
	d_sdivzstepu = p_saxis[0] * t;
	d_tdivzstepu = p_taxis[0] * t;
	t = yscaleinv * mipscale;
	d_sdivzstepv = -p_saxis[1] * t;
	d_tdivzstepv = -p_taxis[1] * t;
	d_sdivzorigin = p_saxis[2] * mipscale - xcenter * d_sdivzstepu - ycenter * d_sdivzstepv;
	d_tdivzorigin = p_taxis[2] * mipscale - xcenter * d_tdivzstepu - ycenter * d_tdivzstepv;

	VectorScale (transformed_modelorg, mipscale, p_temp1);
	t = 0x10000*mipscale;
	sadjust = ((fixed16_t)(DotProduct (p_temp1, p_saxis) * 0x10000 + 0.5)) -
			((pface->texturemins[0] << 16) >> mip) + pface->texinfo->vecs[0][3]*t;
	tadjust = ((fixed16_t)(DotProduct (p_temp1, p_taxis) * 0x10000 + 0.5)) -
			((pface->texturemins[1] << 16) >> mip) + pface->texinfo->vecs[1][3]*t;
	bbextents = ((pface->extents[0] << 16) >> mip) - 1;
	bbextentt = ((pface->extents[1] << 16) >> mip) - 1;
}

/* The left edges (D_SpriteScanLeftEdge's walk over fence_pts). */
static void FenceScanLeftEdge (void)
{
	int		i, v, itop, ibottom, lmaxindex;
	fencept_t	*pvert, *pnext;
	sspan_t		*pspan = fence_spans;
	float		du, dv, vtop, vbottom, slope;
	fixed16_t	u, u_step;

	i = fence_minindex;
	if (i == 0)
		i = fence_nump;
	lmaxindex = fence_maxindex;
	if (lmaxindex == 0)
		lmaxindex = fence_nump;
	vtop = ceil (fence_pts[i].v);
	do
	{
		pvert = &fence_pts[i];
		pnext = pvert - 1;
		vbottom = ceil (pnext->v);
		if (vtop < vbottom)
		{
			du = pnext->u - pvert->u;
			dv = pnext->v - pvert->v;
			slope = du / dv;
			u_step = (int)(slope * 0x10000);
			u = (int)((pvert->u + (slope * (vtop - pvert->v))) * 0x10000) + (0x10000 - 1);
			itop = (int)vtop;
			ibottom = (int)vbottom;
			for (v=itop ; v<ibottom ; v++)
			{
				pspan->u = u >> 16;
				pspan->v = v;
				u += u_step;
				pspan++;
			}
		}
		vtop = vbottom;
		i--;
		if (i == 0)
			i = fence_nump;
	} while (i != lmaxindex);
}

/* The right edges, clamped to the view rectangle (D_SpriteScanRightEdge). */
static void FenceScanRightEdge (void)
{
	int		i, v, itop, ibottom;
	fencept_t	*pvert, *pnext;
	sspan_t		*pspan = fence_spans;
	float		du, dv, vtop, vbottom, slope, uvert, unext, vvert, vnext;
	fixed16_t	u, u_step;

	i = fence_minindex;
	vvert = fence_pts[i].v;
	if (vvert < r_refdef.fvrecty_adj)
		vvert = r_refdef.fvrecty_adj;
	if (vvert > r_refdef.fvrectbottom_adj)
		vvert = r_refdef.fvrectbottom_adj;
	vtop = ceil (vvert);
	do
	{
		pvert = &fence_pts[i];
		pnext = pvert + 1;
		vnext = pnext->v;
		if (vnext < r_refdef.fvrecty_adj)
			vnext = r_refdef.fvrecty_adj;
		if (vnext > r_refdef.fvrectbottom_adj)
			vnext = r_refdef.fvrectbottom_adj;
		vbottom = ceil (vnext);
		if (vtop < vbottom)
		{
			uvert = pvert->u;
			if (uvert < r_refdef.fvrectx_adj)
				uvert = r_refdef.fvrectx_adj;
			if (uvert > r_refdef.fvrectright_adj)
				uvert = r_refdef.fvrectright_adj;
			unext = pnext->u;
			if (unext < r_refdef.fvrectx_adj)
				unext = r_refdef.fvrectx_adj;
			if (unext > r_refdef.fvrectright_adj)
				unext = r_refdef.fvrectright_adj;
			du = unext - uvert;
			dv = vnext - vvert;
			slope = du / dv;
			u_step = (int)(slope * 0x10000);
			u = (int)((uvert + (slope * (vtop - vvert))) * 0x10000) + (0x10000 - 1);
			itop = (int)vtop;
			ibottom = (int)vbottom;
			for (v=itop ; v<ibottom ; v++)
			{
				pspan->count = (u >> 16) - pspan->u;
				u += u_step;
				pspan++;
			}
		}
		vtop = vbottom;
		vvert = vnext;
		i++;
		if (i == fence_nump)
			i = 0;
	} while (i != fence_maxindex);
	pspan->count = DS_SPAN_LIST_END;
}

/* D_SpriteDrawSpans without the flora base push and the night shade (the tile is
 * lit already): texel 255 is skipped, every other texel z-tested and written. */
static void FenceDrawSpans (sspan_t *pspan)
{
	int		count, spancount, slowdepth, depthvalue;
	double		pixelzi, endzi;
	unsigned int	izistep, izi;
	byte		*pbase = cacheblock, *pdest, btemp;
	short		*pz;
	fixed16_t	s, t, snext, tnext, sstep = 0, tstep = 0;
	float		sdivz, tdivz, zi, z, du, dv, spancountminus1;
	float		sdivz8stepu = d_sdivzstepu * 8, tdivz8stepu = d_tdivzstepu * 8, zi8stepu = d_zistepu * 8;
	long		visited = 0, written = 0;

	izistep = fabs (d_zistepu) < 1 ? (unsigned int)(int)(d_zistepu*2147483648.0) : 0;
	do
	{
		pdest = (byte *)d_viewbuffer + (screenwidth * pspan->v) + pspan->u;
		pz = d_pzbuffer + (d_zwidth * pspan->v) + pspan->u;
		count = pspan->count;
		if (count <= 0)
			goto NextSpan;
		visited += count;

		du = (float)pspan->u;
		dv = (float)pspan->v;
		sdivz = d_sdivzorigin + dv*d_sdivzstepv + du*d_sdivzstepu;
		tdivz = d_tdivzorigin + dv*d_tdivzstepv + du*d_tdivzstepu;
		zi = d_ziorigin + dv*d_zistepv + du*d_zistepu;
		z = (float)0x10000 / zi;
		pixelzi = zi;
		endzi = pixelzi + (count-1)*(double)d_zistepu;
		slowdepth = !(pixelzi >= 0 && pixelzi <= 32767.0/32768 && endzi >= 0 && endzi <= 32767.0/32768);
		izi = slowdepth ? 0 : (unsigned int)(pixelzi*2147483648.0);

		s = (int)(sdivz * z) + sadjust;
		if (s > bbextents) s = bbextents; else if (s < 0) s = 0;
		t = (int)(tdivz * z) + tadjust;
		if (t > bbextentt) t = bbextentt; else if (t < 0) t = 0;

		do
		{
			spancount = count >= 8 ? 8 : count;
			count -= spancount;
			if (count)
			{
				sdivz += sdivz8stepu;
				tdivz += tdivz8stepu;
				zi += zi8stepu;
				z = (float)0x10000 / zi;
				snext = (int)(sdivz * z) + sadjust;
				if (snext > bbextents) snext = bbextents; else if (snext < 8) snext = 8;
				tnext = (int)(tdivz * z) + tadjust;
				if (tnext > bbextentt) tnext = bbextentt; else if (tnext < 8) tnext = 8;
				sstep = (snext - s) >> 3;
				tstep = (tnext - t) >> 3;
			}
			else
			{
				spancountminus1 = (float)(spancount - 1);
				sdivz += d_sdivzstepu * spancountminus1;
				tdivz += d_tdivzstepu * spancountminus1;
				zi += d_zistepu * spancountminus1;
				z = (float)0x10000 / zi;
				snext = (int)(sdivz * z) + sadjust;
				if (snext > bbextents) snext = bbextents; else if (snext < 8) snext = 8;
				tnext = (int)(tdivz * z) + tadjust;
				if (tnext > bbextentt) tnext = bbextentt; else if (tnext < 8) tnext = 8;
				if (spancount > 1)
				{
					sstep = (snext - s) / (spancount - 1);
					tstep = (tnext - t) / (spancount - 1);
				}
			}
			do
			{
				btemp = *(pbase + (s >> 16) + (t >> 16) * cachewidth);
				if (btemp != 255)
				{
					depthvalue = slowdepth ? (!(pixelzi > 0) ? 0 : pixelzi >= 32767.0/32768 ? 32767 :
						(int)(pixelzi*32768)) : (int)(izi >> 16);
					if (*pz <= depthvalue)
					{
						*pz = depthvalue;
						*pdest = btemp;
						written++;
					}
				}
				izi += izistep;
				if (slowdepth)
					pixelzi += d_zistepu;
				pdest++;
				pz++;
				s += sstep;
				t += tstep;
			} while (--spancount > 0);
			s = snext;
			t = tnext;
		} while (count > 0);
NextSpan:
		pspan++;
	} while (pspan->count != DS_SPAN_LIST_END);
	AW_RC_ADD(RC_FENCE_VISITED, visited);
	AW_RC_ADD(RC_FENCE_WRITTEN, written);
}

static void FenceDrawFace (fenceface_t *f)
{
	static float	clip[2][AW_FENCE_VERTS + 1][3];
	msurface_t	*s = f->surf;
	model_t		*m = f->ent->model;
	clipplane_t	nearplane;
	vec3_t		local, tv, p_normal;
	float		distinv, zi, nearzi = 0, ymin = 999999.9f, ymax = -999999.9f;
	int		i, n, cur = 0, lindex;
	surfcache_t	*pcache;

	if (s->numedges < 3 || s->numedges > AW_FENCE_VERTS - 8)
		return;
	for (i=0 ; i<s->numedges ; i++)
	{
		lindex = m->surfedges[s->firstedge + i];
		VectorCopy (m->vertexes[lindex > 0 ? m->edges[lindex].v[0] : m->edges[-lindex].v[1]].position, clip[0][i]);
	}
	n = s->numedges;
	/* the four view planes and the near plane, in model space (R_TransformFrustum) */
	VectorCopy (vpn, nearplane.normal);
	nearplane.dist = DotProduct (modelorg, vpn) + NEAR_CLIP;
	for (i=0 ; i<5 && n >= 3 ; i++)
	{
		n = FenceClip (clip[cur], n, clip[!cur], i < 4 ? &view_clipplanes[i] : &nearplane);
		cur = !cur;
	}
	if (n < 3)
		return;

	for (i=0 ; i<n ; i++)
	{
		VectorSubtract (clip[cur][i], modelorg, local);
		TransformVector (local, tv);
		if (tv[2] < NEAR_CLIP)
			tv[2] = NEAR_CLIP;
		zi = 1.0f / tv[2];
		if (zi > nearzi)
			nearzi = zi;
		fence_pts[i].u = xcenter + xscale * zi * tv[0];
		fence_pts[i].v = ycenter - yscale * zi * tv[1];
		if (fence_pts[i].v < ymin)
		{
			ymin = fence_pts[i].v;
			fence_minindex = i;
		}
		if (fence_pts[i].v > ymax)
		{
			ymax = fence_pts[i].v;
			fence_maxindex = i;
		}
	}
	if (ceil (ymin) >= ceil (ymax))
		return;
	fence_nump = n;
	fence_pts[n] = fence_pts[0];

	/* the plane's 1/z gradients (R_RenderFace) */
	TransformVector (s->plane->normal, p_normal);
	distinv = 1.0f / (s->plane->dist - DotProduct (modelorg, s->plane->normal));
	d_zistepu = p_normal[0] * xscaleinv * distinv;
	d_zistepv = -p_normal[1] * yscaleinv * distinv;
	d_ziorigin = p_normal[2] * distinv - xcenter * d_zistepu - ycenter * d_zistepv;

	fence_miplevel = D_MipLevelForScale (nearzi * scale_for_mip * s->texinfo->mipadjust);
	r_drawsurf.light = currententity ? currententity->aw_light : 0;
	r_drawsurf.tint = currententity ? currententity->aw_tint : 0;
	pcache = D_CacheSurface (s, fence_miplevel);
	cacheblock = (pixel_t *)pcache->data;
	cachewidth = pcache->width;
	FenceGradients (s, fence_miplevel);
	D_SetupFixedPointGradients ();

	FenceScanLeftEdge ();
	FenceScanRightEdge ();
	FenceDrawSpans (fence_spans);
	AW_RC(RC_FENCE_FACES);
}

/* r_main.c, after R_EdgeDrawing (the opaque world and its z) and before the
 * entities: every listed face, then the world drawing state back. */
void D_DrawFences (void)
{
	int	i;
	vec3_t	local;
	double	t0;

	if (!fence_count)
		return;
	AW_RT_BEGIN(t0);
	/* start from the world's drawing state, whatever the last brush model left */
	VectorCopy (base_vpn, vpn);
	VectorCopy (base_vup, vup);
	VectorCopy (base_vright, vright);
	VectorCopy (base_modelorg, modelorg);
	R_TransformFrustum ();
	for (i=0 ; i<fence_count ; i++)
	{
		fenceface_t	*f = &fence_faces[i];

		currententity = f->ent;
		if (f->ent != &cl_entities[0])
		{
			VectorSubtract (r_origin, f->ent->origin, local);
			TransformVector (local, transformed_modelorg);
			R_RotateBmodel ();
		}
		else
			TransformVector (modelorg, transformed_modelorg);
		FenceDrawFace (f);
		if (f->ent != &cl_entities[0])
		{
			VectorCopy (base_vpn, vpn);
			VectorCopy (base_vup, vup);
			VectorCopy (base_vright, vright);
			VectorCopy (base_modelorg, modelorg);
			R_TransformFrustum ();
		}
	}
	fence_count = 0;
	currententity = &cl_entities[0];
	AW_RT_END(RT_FENCE, t0);
}
