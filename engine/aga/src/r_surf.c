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
// r_surf.c: surface-related refresh code

#include "quakedef.h"
#include "r_local.h"
#include "aw_torch.h"
#include "aw_sky.h"

drawsurf_t	r_drawsurf;

int				sourcesstep, blocksize, sourcetstep;
int				lightdelta, lightdeltastep;
int				blockdivshift;
unsigned		blockdivmask;
void			*prowdestbase;
unsigned char	*pbasesource;
int				surfrowbytes;	// used by ASM files
unsigned		*r_lightptr;
int				r_stepback;
int				r_lightwidth;
int				r_numhblocks, r_numvblocks;
unsigned char	*r_source, *r_sourcemax;

void R_DrawSurfaceBlock8_mip0 (void);
void R_DrawSurfaceBlock8_mip1 (void);
void R_DrawSurfaceBlock8_mip2 (void);
void R_DrawSurfaceBlock8_mip3 (void);

static void	(*surfmiptable[4])(void) = {
	R_DrawSurfaceBlock8_mip0,
	R_DrawSurfaceBlock8_mip1,
	R_DrawSurfaceBlock8_mip2,
	R_DrawSurfaceBlock8_mip3
};



unsigned		blocklights[18*18];

#if id68k
extern void R_AddDynamicLights (void);
#else
/*
===============
R_AddDynamicLights
===============
*/
void R_AddDynamicLights (void)
{
	msurface_t *surf;
	int			lnum;
	int			sd, td;
	float		dist, rad, minlight, gain;
	vec3_t		impact, local, lightorigin;
	int			s, t;
	int			i;
	int			smax, tmax;
	mtexinfo_t	*tex;
    float sn, tn, ss, tt, st, perpendicular;
    float s_world=1, t_world=1, t_skew=0, ds, dt;

	surf = r_drawsurf.surf;
	smax = (surf->extents[0]>>4)+1;
	tmax = (surf->extents[1]>>4)+1;
	tex = surf->texinfo;

    /* Imported UVs may be scaled or skewed. Radius and plane distance are
     * world units, so undo the in-plane UV basis before applying Quake's
     * cheap distance approximation. Compute this once per surface, not per
     * light sample. A singular mapping retains the legacy finite fallback. */
    sn=DotProduct(tex->vecs[0],surf->plane->normal);
    tn=DotProduct(tex->vecs[1],surf->plane->normal);
    ss=DotProduct(tex->vecs[0],tex->vecs[0])-sn*sn;
    tt=DotProduct(tex->vecs[1],tex->vecs[1])-tn*tn;
    st=DotProduct(tex->vecs[0],tex->vecs[1])-sn*tn;
    if(isfinite(ss) && isfinite(tt) && isfinite(st) && ss>0 && tt>0){
        perpendicular=tt-st*st/ss;
        if(perpendicular>tt*0.000001f){
            s_world=1.0f/sqrt(ss);t_world=1.0f/sqrt(perpendicular);t_skew=st/ss;
        }
    }

	for (lnum=0 ; lnum<MAX_DLIGHTS ; lnum++)
	{
		if ( !(surf->dlightbits & (1u<<lnum) ) )
			continue;		// not lit by this light

		rad = cl_dlights[lnum].radius;
        gain=AW_TorchLightGain(cl_dlights[lnum].key,rad,1)*256;
        if(gain<=0)continue;
        /* AmiWind, 2026-10-01: match brush-instance marking coordinates. */
        R_DlightOrigin(&cl_dlights[lnum],lightorigin);
		dist = DotProduct (lightorigin, surf->plane->normal) -
				surf->plane->dist;
		rad -= fabs(dist);
		minlight = cl_dlights[lnum].minlight;
		if (rad < minlight)
			continue;
		minlight = rad - minlight;

		for (i=0 ; i<3 ; i++)
		{
			impact[i] = lightorigin[i] -
					surf->plane->normal[i]*dist;
		}

		local[0] = DotProduct (impact, tex->vecs[0]) + tex->vecs[0][3];
		local[1] = DotProduct (impact, tex->vecs[1]) + tex->vecs[1][3];

		local[0] -= surf->texturemins[0];
		local[1] -= surf->texturemins[1];

		for (t = 0 ; t<tmax ; t++)
		{
			for (s=0 ; s<smax ; s++)
			{
                ds=local[0]-s*16;dt=fabs((local[1]-t*16-ds*t_skew)*t_world);
                ds=fabs(ds*s_world);
                /* Tiny valid bases and large offsets can produce non-finite
                 * or out-of-int-range distances. Reject before conversion;
                 * the normal torch range takes this same cheap early-out. */
                if(!(ds<minlight && dt<minlight) || ds>=2147483648.0f || dt>=2147483648.0f)
                    continue;
                sd=ds;td=dt;
				if (sd > td)
					dist = (float)sd + (td>>1);
				else
					dist = (float)td + (sd>>1);
				if (dist < minlight)
#ifdef QUAKE2
				{
					unsigned temp;
					temp = (rad - dist)*gain;
					i = t*smax + s;
					if (!cl_dlights[lnum].dark)
						blocklights[i] += temp;
					else
					{
						if (blocklights[i] > temp)
							blocklights[i] -= temp;
						else
							blocklights[i] = 0;
					}
				}
#else
					blocklights[t*smax + s] += (rad - dist)*gain;
#endif
			}
		}
	}
}

#endif

/*
===============
R_BuildLightMap

Combine and scale multiple lightmaps into the 8.8 format in blocklights
===============
*/
/* Glowing materials (lantern glass, flames, lava, Bitter Coast mushrooms).
 * The scene converter names their textures "emitN..." with N = 1..9 for the
 * source emissive strength (9 = fully self-lit). With aw_emissive 1 (default)
 * such surfaces get at least that much light; 0 restores plain lightmaps.
 * Checked per lightmap build, not per pixel. */
cvar_t	aw_emissive = {"aw_emissive","1",true};
static int R_EmissiveLevel (msurface_t *surf)
{
	const char *n = surf->texinfo->texture->name;
	if (n[0]=='e' && n[1]=='m' && n[2]=='i' && n[3]=='t' && n[4]>='1' && n[4]<='9')
		return n[4]-'0';
	return 0;
}

void R_BuildLightMap (void)
{
	int			smax, tmax;
	int			t;
	int			i, size;
	byte		*lightmap;
	unsigned	scale;
	int			maps;
	msurface_t	*surf;
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
	float		static_factor;
#endif
	int			legacy_unlit;

	surf = r_drawsurf.surf;

	smax = (surf->extents[0]>>4)+1;
	tmax = (surf->extents[1]>>4)+1;
	size = smax*tmax;
	lightmap = surf->samples;
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
	static_factor = R_InteriorLumaFactor();
#endif
	legacy_unlit = !cl.worldmodel->lightdata && !R_SkyExterior();

	/* AmiWind exterior maps can have no lightmaps, or retain an unused lump.
	 * Both must use the same ambient/dynamic-light path at region boundaries.
	 * Keep the legacy fallback for maps without the validated exterior sky. */
	if (r_fullbright.value || (legacy_unlit
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
        && static_factor == 1
#endif
        ))
	{
		for (i=0 ; i<size ; i++)
			blocklights[i] = 0;
		return;
	}

// clear to ambient
	for (i=0 ; i<size ; i++)
		blocklights[i] = (legacy_unlit ? 255 : r_refdef.ambientlight)<<8;


// add all the lightmaps
	if (lightmap)
		for (maps = 0 ; maps < MAXLIGHTMAPS && surf->styles[maps] != 255 ;
			 maps++)
		{
			scale = r_drawsurf.lightadj[maps];	// 8.8 fraction
			for (i=0 ; i<size ; i++)
				blocklights[i] += lightmap[i] * scale;
			lightmap += size;	// skip to next lightmap
		}

// Scale only the static contribution; torch radii and strengths stay independent.
#if defined(AMIWIND_DEBUG_LUMA) && AMIWIND_DEBUG_LUMA
	if (static_factor != 1)
		for (i=0 ; i<size ; i++) {
			float value = blocklights[i]*static_factor;
			blocklights[i] = value >= 255*256 ? 255*256 : (unsigned)value;
		}
#endif

// self-lit materials: raise the static light to the material's level
	if (aw_emissive.value)
	{
		int level = R_EmissiveLevel (surf);
		if (level)
		{
			unsigned floor_light = (unsigned)(level*255*256/9);
			for (i=0 ; i<size ; i++)
				if (blocklights[i] < floor_light)
					blocklights[i] = floor_light;
		}
	}

// add all the dynamic lights
	if (surf->dlightframe == r_framecount)
		R_AddDynamicLights ();

// bound, invert, and shift
	for (i=0 ; i<size ; i++)
	{
		t = (255*256 - (int)blocklights[i]) >> (8 - VID_CBITS);

		if (t < (1 << 6))
			t = (1 << 6);

		blocklights[i] = t;
	}
}


/*
===============
R_TextureAnimation

Returns the proper texture for a given time and base texture
===============
*/
texture_t *R_TextureAnimation (texture_t *base)
{
	int		reletive;
	int		count;

	if (currententity->frame)
	{
		if (base->alternate_anims)
			base = base->alternate_anims;
	}

	if (!base->anim_total)
		return base;

	reletive = (int)(cl.time*10) % base->anim_total;

	count = 0;
	while (base->anim_min > reletive || base->anim_max <= reletive)
	{
		base = base->anim_next;
		if (!base)
			Sys_Error ("R_TextureAnimation: broken cycle");
		if (++count > 100)
			Sys_Error ("R_TextureAnimation: infinite cycle");
	}

	return base;
}


/*
===============
R_DrawSurface
===============
*/
void R_DrawSurface (void)
{
	unsigned char	*basetptr;
	int				smax, tmax, twidth;
	int				u;
	int				soffset, basetoffset, texwidth;
	int				horzblockstep;
	unsigned char	*pcolumndest;
	void			(*pblockdrawer)(void);
	texture_t		*mt;

// calculate the lightings
	R_BuildLightMap ();

	surfrowbytes = r_drawsurf.rowbytes;

	mt = r_drawsurf.texture;

	r_source = (byte *)mt + mt->offsets[r_drawsurf.surfmip];

// the fractional light values should range from 0 to (VID_GRADES - 1) << 16
// from a source range of 0 - 255

	texwidth = mt->width >> r_drawsurf.surfmip;

	blocksize = 16 >> r_drawsurf.surfmip;
	blockdivshift = 4 - r_drawsurf.surfmip;
	blockdivmask = (1 << blockdivshift) - 1;

	r_lightwidth = (r_drawsurf.surf->extents[0]>>4)+1;

	r_numhblocks = r_drawsurf.surfwidth >> blockdivshift;
	r_numvblocks = r_drawsurf.surfheight >> blockdivshift;

//==============================

	if (r_pixbytes != 1)
		Sys_Error ("R_DrawSurface: only 8-bit surfaces are supported");
	pblockdrawer = surfmiptable[r_drawsurf.surfmip];
// TODO: only needs to be set when there is a display settings change
	horzblockstep = blocksize;

	smax = mt->width >> r_drawsurf.surfmip;
	twidth = texwidth;
	tmax = mt->height >> r_drawsurf.surfmip;
	sourcetstep = texwidth;
	r_stepback = tmax * twidth;

	r_sourcemax = r_source + (tmax * smax);

	soffset = r_drawsurf.surf->texturemins[0];
	basetoffset = r_drawsurf.surf->texturemins[1];

// << 16 components are to guarantee positive values for %
	soffset = ((soffset >> r_drawsurf.surfmip) + (smax << 16)) % smax;
	basetptr = &r_source[((((basetoffset >> r_drawsurf.surfmip)
		+ (tmax << 16)) % tmax) * twidth)];

	pcolumndest = r_drawsurf.surfdat;

	for (u=0 ; u<r_numhblocks; u++)
	{
		r_lightptr = blocklights + u;

		prowdestbase = pcolumndest;

		pbasesource = basetptr + soffset;

		(*pblockdrawer)();

		soffset = soffset + blocksize;
		if (soffset >= smax)
			soffset = 0;

		pcolumndest += horzblockstep;
	}
}


//=============================================================================

#if	!id386
#if !id68k

/*
================
R_DrawSurfaceBlock8_mip0
================
*/
/* Lightmap values are bounded to 0..255*64. Cast unsigned samples before
 * subtraction: otherwise a decreasing gradient wraps to a huge positive
 * step, then overflows during interpolation. Round negative steps down
 * explicitly, matching arithmetic right shift without shifting negatives. */
static int R_LightStep(int end, int start, int shift)
{
    int delta = end - start;
    if (delta >= 0)
        return delta >> shift;
    return -((-delta + (1 << shift) - 1) >> shift);
}

void R_DrawSurfaceBlock8_mip0 (void)
{
	int	v;
	int	psourcestep, prowdeststep;
	unsigned char	*psource, *prowdest, *colormap;

	colormap = (unsigned char *)vid.colormap;
	psourcestep = sourcetstep;
	prowdeststep = surfrowbytes;
	psource = pbasesource;
	prowdest = prowdestbase;

	for (v=0 ; v<r_numvblocks ; v++)
	{
		int i, lightleft, lightright, lightleftstep, lightrightstep;

	// FIXME: use delta rather than both right and left, like ASM?
		lightleft = r_lightptr[0];
		lightright = r_lightptr[1];
		r_lightptr += r_lightwidth;
		lightleftstep = R_LightStep((int)r_lightptr[0], lightleft, 4);
		lightrightstep = R_LightStep((int)r_lightptr[1], lightright, 4);

		for (i=0 ; i<16 ; i++)
		{
			int b, lightstep, light;

			lightstep = R_LightStep(lightleft, lightright, 4);

			light = lightright;

			for (b=15; b>=0; b--)
			{
				prowdest[b] = colormap[(light & 0xFF00) + psource[b]];
				light += lightstep;
			}

			psource += psourcestep;
			lightright += lightrightstep;
			lightleft += lightleftstep;
			prowdest += prowdeststep;
		}

		if (psource >= r_sourcemax)
			psource -= r_stepback;
	}
}


/*
================
R_DrawSurfaceBlock8_mip1
================
*/
void R_DrawSurfaceBlock8_mip1 (void)
{
	int	v;
	int	psourcestep, prowdeststep;
	unsigned char	*psource, *prowdest, *colormap;

	colormap = (unsigned char *)vid.colormap;
	psourcestep = sourcetstep;
	prowdeststep = surfrowbytes;
	psource = pbasesource;
	prowdest = prowdestbase;

	for (v=0 ; v<r_numvblocks ; v++)
	{
		int i, lightleft, lightright, lightleftstep, lightrightstep;

	// FIXME: use delta rather than both right and left, like ASM?
		lightleft = r_lightptr[0];
		lightright = r_lightptr[1];
		r_lightptr += r_lightwidth;
		lightleftstep = R_LightStep((int)r_lightptr[0], lightleft, 3);
		lightrightstep = R_LightStep((int)r_lightptr[1], lightright, 3);

		for (i=0 ; i<8 ; i++)
		{
			int b, lightstep, light;

			lightstep = R_LightStep(lightleft, lightright, 3);

			light = lightright;

			for (b=7; b>=0; b--)
			{
				prowdest[b] = colormap[(light & 0xFF00) + psource[b]];
				light += lightstep;
			}

			psource += psourcestep;
			lightright += lightrightstep;
			lightleft += lightleftstep;
			prowdest += prowdeststep;
		}

		if (psource >= r_sourcemax)
			psource -= r_stepback;
	}
}


/*
================
R_DrawSurfaceBlock8_mip2
================
*/
void R_DrawSurfaceBlock8_mip2 (void)
{
	int	v;
	int	psourcestep, prowdeststep;
	unsigned char	*psource, *prowdest, *colormap;

	colormap = (unsigned char *)vid.colormap;
	psourcestep = sourcetstep;
	prowdeststep = surfrowbytes;
	psource = pbasesource;
	prowdest = prowdestbase;

	for (v=0 ; v<r_numvblocks ; v++)
	{
		int i, lightleft, lightright, lightleftstep, lightrightstep;

	// FIXME: use delta rather than both right and left, like ASM?
		lightleft = r_lightptr[0];
		lightright = r_lightptr[1];
		r_lightptr += r_lightwidth;
		lightleftstep = R_LightStep((int)r_lightptr[0], lightleft, 2);
		lightrightstep = R_LightStep((int)r_lightptr[1], lightright, 2);

		for (i=0 ; i<4 ; i++)
		{
			int b, lightstep, light;

			lightstep = R_LightStep(lightleft, lightright, 2);

			light = lightright;

			for (b=3; b>=0; b--)
			{
				prowdest[b] = colormap[(light & 0xFF00) + psource[b]];
				light += lightstep;
			}

			psource += psourcestep;
			lightright += lightrightstep;
			lightleft += lightleftstep;
			prowdest += prowdeststep;
		}

		if (psource >= r_sourcemax)
			psource -= r_stepback;
	}
}


/*
================
R_DrawSurfaceBlock8_mip3
================
*/
void R_DrawSurfaceBlock8_mip3 (void)
{
	int	v;
	int	psourcestep, prowdeststep;
	unsigned char	*psource, *prowdest, *colormap;

	colormap = (unsigned char *)vid.colormap;
	psourcestep = sourcetstep;
	prowdeststep = surfrowbytes;
	psource = pbasesource;
	prowdest = prowdestbase;

	for (v=0 ; v<r_numvblocks ; v++)
	{
		int i, lightleft, lightright, lightleftstep, lightrightstep;

	// FIXME: use delta rather than both right and left, like ASM?
		lightleft = r_lightptr[0];
		lightright = r_lightptr[1];
		r_lightptr += r_lightwidth;
		lightleftstep = R_LightStep((int)r_lightptr[0], lightleft, 1);
		lightrightstep = R_LightStep((int)r_lightptr[1], lightright, 1);

		for (i=0 ; i<2 ; i++)
		{
			int b, lightstep, light;

			lightstep = R_LightStep(lightleft, lightright, 1);

			light = lightright;

			for (b=1; b>=0; b--)
			{
				prowdest[b] = colormap[(light & 0xFF00) + psource[b]];
				light += lightstep;
			}

			psource += psourcestep;
			lightright += lightrightstep;
			lightleft += lightleftstep;
			prowdest += prowdeststep;
		}

		if (psource >= r_sourcemax)
			psource -= r_stepback;
	}
}


/* The 16-bit surface drawer (stock Quake, marked "FIXME: make this work")
 * read uninitialised light values and was unreachable: r_pixbytes is
 * always 1 here. Removed; see R_DrawSurface. */

#endif
#endif


//============================================================================

/*
================
R_GenTurbTile
================
*/
void R_GenTurbTile (pixel_t *pbasetex, void *pdest)
{
	int		*turb;
	int		i, j, s, t;
	byte	*pd;

	turb = r_turb_sintable;
	pd = (byte *)pdest;

	for (i=0 ; i<TILE_SIZE ; i++)
	{
		for (j=0 ; j<TILE_SIZE ; j++)
		{
			s = (((j << 16) + turb[i & (CYCLE-1)]) >> 16) & 63;
			t = (((i << 16) + turb[j & (CYCLE-1)]) >> 16) & 63;
			*pd++ = *(pbasetex + (t<<6) + s);
		}
	}
}


/*
================
R_GenTurbTile16
================
*/
void R_GenTurbTile16 (pixel_t *pbasetex, void *pdest)
{
	int				*turb;
	int				i, j, s, t;
	unsigned short	*pd;

	turb = r_turb_sintable;
	pd = (unsigned short *)pdest;

	for (i=0 ; i<TILE_SIZE ; i++)
	{
		for (j=0 ; j<TILE_SIZE ; j++)
		{
			s = (((j << 16) + turb[i & (CYCLE-1)]) >> 16) & 63;
			t = (((i << 16) + turb[j & (CYCLE-1)]) >> 16) & 63;
			*pd++ = d_8to16table[*(pbasetex + (t<<6) + s)];
		}
	}
}


/*
================
R_GenTile
================
*/
void R_GenTile (msurface_t *psurf, void *pdest)
{
	if (psurf->flags & SURF_DRAWTURB)
	{
		if (r_pixbytes == 1)
		{
			R_GenTurbTile ((pixel_t *)
				((byte *)psurf->texinfo->texture + psurf->texinfo->texture->offsets[0]), pdest);
		}
		else
		{
			R_GenTurbTile16 ((pixel_t *)
				((byte *)psurf->texinfo->texture + psurf->texinfo->texture->offsets[0]), pdest);
		}
	}
	else if (psurf->flags & SURF_DRAWSKY)
	{
		if (r_pixbytes == 1)
		{
			R_GenSkyTile (pdest);
		}
		else
		{
			R_GenSkyTile16 (pdest);
		}
	}
	else
	{
		Sys_Error ("Unknown tile type");
	}
}
