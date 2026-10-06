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
        value=strtod(control->string,&end);
        invalid=end==control->string || *end || !isfinite(value) || !isfinite(control->value);
        if(invalid)value=outside?1:1.2;
        if(value<0)value=0;if(value>4)value=4;
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
    if(value<10)value=10;if(value>15)value=15;
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
        value=strtod(Cmd_Argv(1),&end);
        if(end==Cmd_Argv(1) || *end || !isfinite(value)){
            Con_Printf("%s luma requires a finite number (0..4).\n",name);return;
        }
        if(value<0)value=0;if(value>4)value=4;
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
void R_InteriorLumaInit(void)
{
    Cvar_RegisterVariable(&aw_interiorluma);Cvar_RegisterVariable(&aw_exteriorluma);
    Cmd_AddCommand("aw_interiorluma_set",R_InteriorLumaCommand);
    Cmd_AddCommand("aw_exteriorluma_set",R_ExteriorLumaCommand);
}
#else
#define R_InteriorStaticLight(value) (value)
static void R_InteriorLumaUnavailable(void){Con_Printf("Can't adjust interior luma: built without luma controls.\n");}
static void R_ExteriorLumaUnavailable(void){Con_Printf("Can't adjust exterior luma: built without luma controls.\n");}
void R_InteriorLumaInit(void)
{
    Cmd_AddCommand("aw_interiorluma_set",R_InteriorLumaUnavailable);
    Cmd_AddCommand("aw_exteriorluma_set",R_ExteriorLumaUnavailable);
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
				scale = d_lightstylevalue[surf->styles[maps]];
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

int R_LightPoint (vec3_t p)
{
	vec3_t		end;
	int			r;

	if (!cl.worldmodel->lightdata)
		/* Match no-sample exterior surfaces instead of lighting actors fully
		 * merely because this region omitted an unused lighting lump. */
		return R_InteriorStaticLight(R_SkyExterior() ? r_refdef.ambientlight : 255);

	end[0] = p[0];
	end[1] = p[1];
	end[2] = p[2] - 2048;

	r = RecursiveLightPoint (cl.worldmodel->nodes, p, end);

	if (r == -1)
		r = 0;

	if (r < r_refdef.ambientlight)
		r = r_refdef.ambientlight;

	return R_InteriorStaticLight(r);
}
