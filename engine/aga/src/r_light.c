/*
Copyright (C) 1996-1997 Id Software, Inc.

This program is free software; you can redistribute it and/or
modify it under the terms of the GNU General Public License
as published by the Free Software Foundation; either version 2
of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.

See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.

*/
// r_light.c

#include "quakedef.h"
#include "r_local.h"
#include "aw_sky.h"
int r_daylight=256,r_lamps=1;
unsigned char *r_warm_colormap; /* built by r_sky.c from aw_light_hue */
unsigned char r_dlight_cool[32];
/* A lightstyle's value with night dimming: lamps (AW_LAMP_STYLE and up) keep
 * their full value. */
int R_StyleLight(int style)
{
    int value=d_lightstylevalue[style];
    if(style>=AW_LAMP_STYLE)return r_lamps?value:0;
    return r_daylight<256?value*r_daylight>>8:value;
}
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
#include "aw_interior_light_policy.h"
extern int AW_TorchTestActive(void);
/* Independent saved controls, one active factor and one existing light buffer.
 * Compile-out builds retain only explanatory commands below. */
/* RC2 brightness measurement, 2026-10-06: Census, FS-UAE, 3 alternating
 * timerefresh pairs (128 rendered frames each), 1.0 versus 1.2 static light.
 * Median rotation: 1.175745s -> 1.189845s (+1.199%, +0.110ms/render).
 * This is a noisy renderer-only sample, not full gameplay or physical-Amiga
 * performance, and does not compare controls-enabled with controls-disabled.
 * Preserve cached surface-light work and independent NPC static-light scaling;
 * do not infer zero CPU/RAM cost at factor 1.0 or multiply torch light twice.
 * Method, raw samples and remaining checks: docs/INTERIOR_LIGHTING.md and
 * docs/bugs/INTERIOR-LIGHT-29.md. Measurements apply to the recorded RC2 build.
 */
static cvar_t aw_interiorluma={"aw_interiorluma","1.2",true};
static cvar_t aw_exteriorluma={"aw_exteriorluma","1.0",true};
static cvar_t *luma_controls[]={&aw_interiorluma,&aw_exteriorluma};
static float interior_luma_factor=1;
static char interior_luma_scene[64],luma_checked_text[2][64];
static int interior_luma_mode;
static float luma_checked_value[2],luma_settings[2]={1.2f,1};
static float R_LumaSetting(int outside)
{
    cvar_t *control=luma_controls[outside];char *end;double value;int invalid;
    if(strcmp(control->string,luma_checked_text[outside]) || control->value!=luma_checked_value[outside]){
        value=Q_strtod(control->string,&end);
        invalid=end==control->string || *end || !isfinite(value) || !isfinite(control->value);
        if(invalid)value=outside?1:1.2;
        if(value<0)value=0;
        if(value>4)value=4;
        luma_settings[outside]=(float)value;
        if(invalid || luma_settings[outside]!=control->value || strlen(control->string)>=64)
            Cvar_SetValue(control->name,luma_settings[outside]);
        strncpy(luma_checked_text[outside],control->string,63);luma_checked_text[outside][63]=0;
        luma_checked_value[outside]=control->value;
    }
    return luma_settings[outside];
}
float R_InteriorLumaFactor(void){return interior_luma_factor;}
void R_InteriorLumaUpdate(void)
{
    float effective;const char *scene=sv.active?sv.name:"";
    if(strcmp(scene,interior_luma_scene)){
        strncpy(interior_luma_scene,scene,63);interior_luma_scene[63]=0;
        interior_luma_mode=AW_GameplayInteriorLightPolicy(scene,AW_Interior())?1:
            (sv.active && R_SkyExterior() && strcmp(scene,"torchtest")?2:0);
    }
    effective=interior_luma_mode && !AW_TorchTestActive()?R_LumaSetting(interior_luma_mode-1):1;
    if(effective!=interior_luma_factor){interior_luma_factor=effective;D_FlushCaches();}
}
static int R_InteriorStaticLight(int value)
{
    float scaled;if(interior_luma_factor==1)return value;
    scaled=value*interior_luma_factor;
    return scaled>=255?255:scaled<=0?0:(int)scaled;
}
int R_BrightnessStep(int outside)
{
    int value=(int)(R_LumaSetting(outside!=0)*10+.5f);
    return value<10?10:value>15?15:value;
}
void R_BrightnessSetStep(int outside,int value)
{
    float setting;outside=outside!=0;
    if(value<10)value=10;
    if(value>15)value=15;
    setting=value*.1f;
    if(fabs(R_LumaSetting(outside)-setting)<.00001f)return;
    Cvar_SetValue(luma_controls[outside]->name,setting);R_InteriorLumaUpdate();
}
int R_InteriorBrightnessStep(void){return R_BrightnessStep(0);}
void R_InteriorBrightnessSetStep(int value){R_BrightnessSetStep(0,value);}
static void R_LumaCommand(int outside)
{
    char *end;double value;long configured,effective;const char *name=outside?"exterior":"interior";
    if(Cmd_Argc()>2){Con_Printf("Usage: dbg luma %s [0..4]\n",name);return;}
    if(Cmd_Argc()==2){
        value=Q_strtod(Cmd_Argv(1),&end);
        if(end==Cmd_Argv(1) || *end || !isfinite(value)){
            Con_Printf("%s luma requires a finite number (0..4).\n",name);return;
        }
        if(value<0)value=0;
        if(value>4)value=4;
        Cvar_SetValue(luma_controls[outside]->name,(float)value);
    }
    R_InteriorLumaUpdate();configured=(long)(R_LumaSetting(outside)*1000+.5f);
    effective=(long)(interior_luma_factor*1000+.5f);
    Con_Printf("%sluma %ld.%03ld; effective %ld.%03ld (%s). Static light multiplier; 1.0 is baseline.\n",
        name,configured/1000,configured%1000,effective/1000,effective%1000,
        interior_luma_mode && !AW_TorchTestActive()?(interior_luma_mode==1?"gameplay interior":"gameplay exterior"):"baseline/excluded");
}
static void R_InteriorLumaCommand(void){R_LumaCommand(0);}
static void R_ExteriorLumaCommand(void){R_LumaCommand(1);}
/* dbg luma: the current multipliers, then how to set them. The "set with" lines
 * are the catalogue's own (dbg help luma streams them from the disk file). */
static void R_LumaStatusCommand(void)
{
    long indoor,outdoor,effective;
    R_InteriorLumaUpdate();
    indoor=(long)(R_LumaSetting(0)*1000+.5f);outdoor=(long)(R_LumaSetting(1)*1000+.5f);
    effective=(long)(interior_luma_factor*1000+.5f);
    Con_Printf("Current luma: indoor %ld.%03ld, outdoor %ld.%03ld (light multiplier; 1.000 = original).\n",
        indoor/1000,indoor%1000,outdoor/1000,outdoor%1000);
    Con_Printf("In effect here: %ld.%03ld (%s).\nSet with:\n",effective/1000,effective%1000,
        interior_luma_mode && !AW_TorchTestActive()?(interior_luma_mode==1?"indoor setting":"outdoor setting"):"original light, scene excluded");
    Cbuf_InsertText("dbg help luma\n");
}
void R_InteriorLumaInit(void)
{
    Cvar_RegisterVariable(&aw_interiorluma);Cvar_RegisterVariable(&aw_exteriorluma);
    Cmd_AddCommand("aw_interiorluma_set",R_InteriorLumaCommand);
    Cmd_AddCommand("aw_exteriorluma_set",R_ExteriorLumaCommand);
    Cmd_AddCommand("aw_luma_status",R_LumaStatusCommand);
}
#else
#define R_InteriorStaticLight(value) (value)
static void R_InteriorLumaUnavailable(void){Con_Printf("Can't adjust interior luma: built without luma controls.\n");}
static void R_ExteriorLumaUnavailable(void){Con_Printf("Can't adjust exterior luma: built without luma controls.\n");}
static void R_LumaStatusUnavailable(void){Con_Printf("Luma: original light (built without luma controls).\n");}
void R_InteriorLumaInit(void)
{
    Cmd_AddCommand("aw_interiorluma_set",R_InteriorLumaUnavailable);
    Cmd_AddCommand("aw_exteriorluma_set",R_ExteriorLumaUnavailable);
    Cmd_AddCommand("aw_luma_status",R_LumaStatusUnavailable);
}
#endif


int	r_dlightframecount;

/* AmiWind, 2026-10-01: the converted scenery uses translated/rotated brush
 * instances. Reuse the render transform for both light marking and sampling. */
void R_DlightOrigin(const dlight_t *light,vec3_t origin)
{
    VectorCopy(light->origin,origin);
    if(currententity && currententity!=&cl_entities[0]){
        VectorSubtract(origin,currententity->origin,origin);
        if(currententity->angles[0] || currententity->angles[1] || currententity->angles[2])
            R_EntityRotate(origin);
    }
}

/* AmiWind, 2026-10-02: converted brush models keep visible faces separately
 * from their collision nodes. A non-colliding model has a negative leaf root;
 * even a positive collision root can have no face references. Neither is a
 * render tree. Use this model's validated face range, never world surfaces. */
void R_MarkBrushLights(model_t *model)
{
    int first, count, i, k, axis;
    float distance, delta, radius;
    vec3_t origin;
    msurface_t *surface;
    dlight_t *light;

    if(!model || !model->surfaces)return;
    first=model->firstmodelsurface;count=model->nummodelsurfaces;
    if(first<0 || count<=0 || first>model->numsurfaces ||
       count>model->numsurfaces-first)return;
    for(k=0;k<MAX_DLIGHTS;k++){
        light=&cl_dlights[k];radius=light->radius;
        if(light->die<cl.time || radius<=0)continue;
        R_DlightOrigin(light,origin);
        /* Most visible models are outside the small carried light. Reject
         * their local bounding boxes before visiting any surface. */
        distance=0;
        for(axis=0;axis<3;axis++){
            delta=0;
            if(origin[axis]<model->mins[axis])delta=model->mins[axis]-origin[axis];
            else if(origin[axis]>model->maxs[axis])delta=origin[axis]-model->maxs[axis];
            distance+=delta*delta;
        }
        if(distance>radius*radius)continue;
        surface=model->surfaces+first;
        for(i=0;i<count;i++,surface++){
            if((surface->flags&SURF_DRAWTILED) || !surface->plane)continue;
            distance=DotProduct(origin,surface->plane->normal)-surface->plane->dist;
            if(distance>radius || distance< -radius)continue;
            if(surface->dlightframe!=r_dlightframecount){
                surface->dlightbits=0;
                surface->dlightframe=r_dlightframecount;
            }
            surface->dlightbits|=1u<<k;
        }
    }
}


/*
==================
R_AnimateLight
==================
*/
void R_AnimateLight (void)
{
	int			i,j,k;

//
// light animations
// 'm' is normal light, 'a' is no light, 'z' is double bright
	i = (int)(cl.time*10);
	for (j=0 ; j<MAX_LIGHTSTYLES ; j++)
	{
		if (!cl_lightstyle[j].length)
		{
			d_lightstylevalue[j] = 256;
			continue;
		}
		k = i % cl_lightstyle[j].length;
		k = cl_lightstyle[j].map[k] - 'a';
		k = k*22;
		d_lightstylevalue[j] = k;
	}
}


/*
=============================================================================

DYNAMIC LIGHTS

=============================================================================
*/

/*
=============
R_MarkLights
=============
*/
void R_MarkLights (dlight_t *light, int bit, mnode_t *node)
{
	mplane_t	*splitplane;
	float		dist;
	msurface_t	*surf;
	int			i;

	if (node->contents < 0)
		return;

	splitplane = node->plane;
	dist = DotProduct (light->origin, splitplane->normal) - splitplane->dist;

	if (dist > light->radius)
	{
		R_MarkLights (light, bit, node->children[0]);
		return;
	}
	if (dist < -light->radius)
	{
		R_MarkLights (light, bit, node->children[1]);
		return;
	}

// mark the polygons
	surf = cl.worldmodel->surfaces + node->firstsurface;
	for (i=0 ; i<node->numsurfaces ; i++, surf++)
	{
		if (surf->dlightframe != r_dlightframecount)
		{
			surf->dlightbits = 0;
			surf->dlightframe = r_dlightframecount;
		}
		surf->dlightbits |= bit;
	}

	R_MarkLights (light, bit, node->children[0]);
	R_MarkLights (light, bit, node->children[1]);
}


/*
=============
R_PushDlights
=============
*/
void R_PushDlights (void)
{
	int		i;
	dlight_t	*l;

	r_dlightframecount = r_framecount + 1;	// because the count hasn't
											//  advanced yet for this frame
	l = cl_dlights;

	for (i=0 ; i<MAX_DLIGHTS ; i++, l++)
	{
		if (l->die < cl.time || !l->radius)
			continue;
		R_MarkLights ( l, 1u<<i, cl.worldmodel->nodes );
	}
}


/*
=============================================================================

LIGHT SAMPLING

=============================================================================
*/

/* Height of the surface the last successful RecursiveLightPoint hit. */
static float lightpoint_hit_z;

int RecursiveLightPoint (mnode_t *node, vec3_t start, vec3_t end)
{
	int			r;
	float		front, back, frac;
	int			side;
	mplane_t	*plane;
	vec3_t		mid;
	msurface_t	*surf;
	int			s, t, ds, dt;
	int			i;
	mtexinfo_t	*tex;
	byte		*lightmap;
	unsigned	scale;
	int			maps;

	if (node->contents < 0)
		return -1;		// didn't hit anything

// calculate mid point

// FIXME: optimize for axial
	plane = node->plane;
	front = DotProduct (start, plane->normal) - plane->dist;
	back = DotProduct (end, plane->normal) - plane->dist;
	side = front < 0;

	if ( (back < 0) == side)
		return RecursiveLightPoint (node->children[side], start, end);

	frac = front / (front-back);
	mid[0] = start[0] + (end[0] - start[0])*frac;
	mid[1] = start[1] + (end[1] - start[1])*frac;
	mid[2] = start[2] + (end[2] - start[2])*frac;

// go down front side
	r = RecursiveLightPoint (node->children[side], start, mid);
	if (r >= 0)
		return r;		// hit something

	if ( (back < 0) == side )
		return -1;		// didn't hit anuthing

// check for impact on this node

	surf = cl.worldmodel->surfaces + node->firstsurface;
	for (i=0 ; i<node->numsurfaces ; i++, surf++)
	{
		if (surf->flags & SURF_DRAWTILED)
			continue;	// no lightmaps

		tex = surf->texinfo;

		s = DotProduct (mid, tex->vecs[0]) + tex->vecs[0][3];
		t = DotProduct (mid, tex->vecs[1]) + tex->vecs[1][3];;

		if (s < surf->texturemins[0] ||
		t < surf->texturemins[1])
			continue;

		ds = s - surf->texturemins[0];
		dt = t - surf->texturemins[1];

		if ( ds > surf->extents[0] || dt > surf->extents[1] )
			continue;

		lightpoint_hit_z = mid[2];
		if (!surf->samples)
			return 0;

		ds >>= 4;
		dt >>= 4;

		lightmap = surf->samples;
		r = 0;
		if (lightmap)
		{

			lightmap += dt * ((surf->extents[0]>>4)+1) + ds;

			for (maps = 0 ; maps < MAXLIGHTMAPS && surf->styles[maps] != 255 ;
					maps++)
			{
				scale = R_StyleLight(surf->styles[maps]);
				r += *lightmap * scale;
				lightmap += ((surf->extents[0]>>4)+1) *
						((surf->extents[1]>>4)+1);
			}

			r >>= 8;
		}

		return r;
	}

// go down back side
	return RecursiveLightPoint (node->children[!side], mid, end);
}

cvar_t	aw_actor_brush_light = {"aw_actor_brush_light","1",true};

/* Light value of a surface's lightmap at a point on its plane, or -1 if the
 * point lies outside the surface's texture extents. */
static int R_SurfaceLightAt (msurface_t *surf, vec3_t at)
{
	mtexinfo_t	*tex = surf->texinfo;
	int		s, t, ds, dt, maps, r = 0;
	unsigned	scale;
	byte		*lightmap;

	s = DotProduct (at, tex->vecs[0]) + tex->vecs[0][3];
	t = DotProduct (at, tex->vecs[1]) + tex->vecs[1][3];
	if (s < surf->texturemins[0] || t < surf->texturemins[1])
		return -1;
	ds = s - surf->texturemins[0];
	dt = t - surf->texturemins[1];
	if (ds > surf->extents[0] || dt > surf->extents[1])
		return -1;
	if (!surf->samples)
		return 0;
	ds >>= 4;
	dt >>= 4;
	lightmap = surf->samples + dt * ((surf->extents[0]>>4)+1) + ds;
	for (maps = 0 ; maps < MAXLIGHTMAPS && surf->styles[maps] != 255 ; maps++)
	{
		scale = R_StyleLight(surf->styles[maps]);
		r += *lightmap * scale;
		lightmap += ((surf->extents[0]>>4)+1) * ((surf->extents[1]>>4)+1);
	}
	return r >> 8;
}

/* Highest upward-facing inline-model surface below p within 2048 units, if
 * higher than the world floor already found (best_z). Results are cached per
 * position: actors are re-sampled only after they move. */
#define ACTOR_LIGHT_CACHE 16
static int R_ActorBrushLight (vec3_t p, int r, float best_z)
{
	static struct {vec3_t p; int r; float floor; model_t *world;} cache[ACTOR_LIGHT_CACHE];
	static int next;
	int		i, j, k, sample;
	entity_t	*e;
	model_t		*m;
	msurface_t	*surf;
	vec3_t	local, d, at;
	float	yaw, c, s, z, dist, world_floor = best_z;

	for (i=0 ; i<ACTOR_LIGHT_CACHE ; i++)
		if (cache[i].world == cl.worldmodel && cache[i].floor == best_z &&
			fabs(cache[i].p[0]-p[0]) < 1 && fabs(cache[i].p[1]-p[1]) < 1 && fabs(cache[i].p[2]-p[2]) < 1)
			return cache[i].r;
	for (i=1 ; i<cl.num_entities ; i++)
	{
		e = &cl_entities[i];
		m = e->model;
		if (!m || m->type != mod_brush || m == cl.worldmodel || m->name[0] != '*')
			continue;
		if (e->msgtime != cl.mtime[0])
			continue;	// not present this frame
		VectorSubtract (p, e->origin, d);
		if (d[0]*d[0] + d[1]*d[1] > m->radius*m->radius)
			continue;
		if (e->origin[2] + m->mins[2] > p[2] || e->origin[2] + m->maxs[2] <= best_z)
			continue;	// entirely above the point, or below the floor found
		yaw = -e->angles[YAW] * (float)(M_PI/180);
		c = (float)Q_CosRad(yaw);
		s = (float)Q_SinRad(yaw);
		local[0] = c*d[0] - s*d[1];
		local[1] = s*d[0] + c*d[1];
		local[2] = d[2];
		surf = &m->surfaces[m->firstmodelsurface];
		for (j=0 ; j<m->nummodelsurfaces ; j++, surf++)
		{
			float nz = surf->plane->normal[2];
			if (surf->flags & (SURF_DRAWTILED|SURF_DRAWSKY))
				continue;
			if (surf->flags & SURF_PLANEBACK)
				nz = -nz;
			if (nz < 0.7f)
				continue;	// not a floor
			dist = surf->plane->dist;
			/* point on the plane straight below: n.x*x + n.y*y + n.z*z = dist */
			z = (dist - surf->plane->normal[0]*local[0] - surf->plane->normal[1]*local[1]) / surf->plane->normal[2];
			if (z > local[2] + 1 || z < local[2] - 2048 || z + e->origin[2] <= best_z)
				continue;
			for (k=0 ; k<2 ; k++)
				at[k] = local[k];
			at[2] = z;
			sample = R_SurfaceLightAt (surf, at);
			if (sample < 0)
				continue;
			best_z = z + e->origin[2];
			r = sample;
		}
	}
	VectorCopy (p, cache[next].p);
	cache[next].r = r;
	cache[next].floor = world_floor;
	cache[next].world = cl.worldmodel;
	next = (next + 1) % ACTOR_LIGHT_CACHE;
	return r;
}

int R_LightPoint (vec3_t p)
{
	vec3_t		end;
	int			r;

	if (!cl.worldmodel->lightdata)
		/* Match no-sample exterior surfaces instead of lighting actors fully
		 * merely because this region omitted an unused lighting lump. */
		return R_InteriorStaticLight(R_SkyExterior() ? r_refdef.ambientlight*r_daylight>>8 : 255);

	end[0] = p[0];
	end[1] = p[1];
	end[2] = p[2] - 2048;

	r = RecursiveLightPoint (cl.worldmodel->nodes, p, end);

	/* Interiors are built from brush objects (func_wall); the world BSP is
	 * mostly the sealing box, so an actor's floor is usually an object. Also
	 * look for the highest upward-facing object surface below the point and
	 * use its lightmap. Inline models keep surfaces but no render nodes here,
	 * so their surfaces are tested directly. aw_actor_brush_light 0 restores
	 * the world-only trace. */
	if (aw_actor_brush_light.value)
		r = R_ActorBrushLight (p, r, r >= 0 ? lightpoint_hit_z : -1e30f);

	if (r == -1)
		r = 0;

	if (r < r_refdef.ambientlight*r_daylight>>8)
		r = r_refdef.ambientlight*r_daylight>>8;

	return R_InteriorStaticLight(r);
}
