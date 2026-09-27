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
// d_scan.c
//
// Portable C scan-level rasterization code, all pixel depths.

#include "quakedef.h"
#include "r_local.h"
#include "d_local.h"

#ifndef id68k
/*
=============
D_SetupFixedPointGradients

Convert floating-point gradients to 16.16 fixed-point for non-FPU assembly
Called after gradients are calculated, before D_DrawSpans
=============
*/
void D_SetupFixedPointGradients(void)
{
    // Convert all gradients to 16.16 format with rounding
    d_zistepu_fp = (int)(d_zistepu * 65536.0 + 0.5);
    d_zistepv_fp = (int)(d_zistepv * 65536.0 + 0.5);
    d_ziorigin_fp = (int)(d_ziorigin * 65536.0 + 0.5);

    d_sdivzstepu_fp = (int)(d_sdivzstepu * 65536.0 + 0.5);
    d_sdivzstepv_fp = (int)(d_sdivzstepv * 65536.0 + 0.5);
    d_tdivzstepu_fp = (int)(d_tdivzstepu * 65536.0 + 0.5);
    d_tdivzstepv_fp = (int)(d_tdivzstepv * 65536.0 + 0.5);
    d_sdivzorigin_fp = (int)(d_sdivzorigin * 65536.0 + 0.5);
    d_tdivzorigin_fp = (int)(d_tdivzorigin * 65536.0 + 0.5);
}
#endif

unsigned char	*r_turb_pbase, *r_turb_pdest;
fixed16_t		r_turb_s, r_turb_t, r_turb_sstep, r_turb_tstep;
int				*r_turb_turb;
int				r_turb_spancount;

void D_DrawTurbulent8Span (void);

#ifdef USE_FAST_RECIPROCAL
/*
=============
fast_reciprocal

Fast 1/x approximation using magic constant + Newton-Raphson iteration
Similar to Quake III's fast inverse square root, but for reciprocal
=============
*/
static inline float fast_reciprocal(float x)
{
	int i = *(int*)&x;
	i = 0x7EF127EA - i;  // Magic constant for 1/x approximation
	float y = *(float*)&i;
	y = y * (2.0f - x * y);  // One Newton-Raphson iteration for better precision
	return y;
}
#endif


#if !id68k
/*
=============
D_WarpScreen

// this performs a slight compression of the screen at the same time as
// the sine warp, to keep the edges from wrapping
=============
*/
void D_WarpScreen (void)
{
	int		w, h;
	int		u,v;
	byte	*dest;
	int		*turb;
	int		*col;
	byte	**row;
	byte	*rowptr[MAXHEIGHT+(AMP2*2)];
	int		column[MAXWIDTH+(AMP2*2)];
	float	wratio, hratio;

	w = r_refdef.vrect.width;
	h = r_refdef.vrect.height;

	wratio = w / (float)scr_vrect.width;
	hratio = h / (float)scr_vrect.height;

	for (v=0 ; v<scr_vrect.height+AMP2*2 ; v++)
	{
		rowptr[v] = d_viewbuffer + (r_refdef.vrect.y * screenwidth) +
				 (screenwidth * (int)((float)v * hratio * h / (h + AMP2 * 2)));
	}

	for (u=0 ; u<scr_vrect.width+AMP2*2 ; u++)
	{
		column[u] = r_refdef.vrect.x +
				(int)((float)u * wratio * w / (w + AMP2 * 2));
	}

	turb = r_turb_intsintable;
	dest = vid.buffer + scr_vrect.y * vid.rowbytes + scr_vrect.x;

	for (v=0 ; v<scr_vrect.height ; v++, dest += vid.rowbytes)
	{
		col = &column[turb[v]];
		row = &rowptr[v];

		for (u=0 ; u<scr_vrect.width ; u+=4)
		{
			dest[u+0] = row[turb[u+0]][col[u+0]];
			dest[u+1] = row[turb[u+1]][col[u+1]];
			dest[u+2] = row[turb[u+2]][col[u+2]];
			dest[u+3] = row[turb[u+3]][col[u+3]];
		}
	}
}

#endif

#if !id386 && !USE_ASM_SPANS

/*
=============
D_DrawTurbulent8Span
=============
*/
void D_DrawTurbulent8Span (void)
{
	int		sturb, tturb;

	do
	{
		sturb = ((r_turb_s + r_turb_turb[(r_turb_t>>16)&(CYCLE-1)])>>16)&63;
		tturb = ((r_turb_t + r_turb_turb[(r_turb_s>>16)&(CYCLE-1)])>>16)&63;
		*r_turb_pdest++ = *(r_turb_pbase + (tturb<<6) + sturb);
		r_turb_s += r_turb_sstep;
		r_turb_t += r_turb_tstep;
	} while (--r_turb_spancount > 0);
}

#endif	// !id386 && !USE_ASM_SPANS


#if !id68k
/*
=============
Turbulent8
=============
*/
void Turbulent8 (espan_t *pspan)
{
	int				count;
	fixed16_t		snext, tnext;
	float			sdivz, tdivz, zi, z, du, dv, spancountminus1;
	float			sdivz16stepu, tdivz16stepu, zi16stepu;
	
	r_turb_turb = r_turb_sintable;

	r_turb_sstep = 0;	// keep compiler happy
	r_turb_tstep = 0;	// ditto

	r_turb_pbase = (unsigned char *)cacheblock;

	sdivz16stepu = d_sdivzstepu * 32;
	tdivz16stepu = d_tdivzstepu * 32;
	zi16stepu = d_zistepu * 32;

	do
	{
		r_turb_pdest = (unsigned char *)((byte *)d_viewbuffer +
				(screenwidth * pspan->v) + pspan->u);

		count = pspan->count;

	// calculate the initial s/z, t/z, 1/z, s, and t and clamp
		du = (float)pspan->u;
		dv = (float)pspan->v;

		sdivz = d_sdivzorigin + dv*d_sdivzstepv + du*d_sdivzstepu;
		tdivz = d_tdivzorigin + dv*d_tdivzstepv + du*d_tdivzstepu;
		zi = d_ziorigin + dv*d_zistepv + du*d_zistepu;
	#ifdef USE_FAST_RECIPROCAL
	z = (float)0x10000 * fast_reciprocal(zi);	// prescale to 16.16 fixed-point
#else
	z = (float)0x10000 / zi;	// prescale to 16.16 fixed-point
#endif

		r_turb_s = (int)(sdivz * z) + sadjust;
		if (r_turb_s > bbextents)
			r_turb_s = bbextents;
		else if (r_turb_s < 0)
			r_turb_s = 0;

		r_turb_t = (int)(tdivz * z) + tadjust;
		if (r_turb_t > bbextentt)
			r_turb_t = bbextentt;
		else if (r_turb_t < 0)
			r_turb_t = 0;

		do
		{
		// calculate s and t at the far end of the span
			if (count >= 32)
				r_turb_spancount = 32;
			else
				r_turb_spancount = count;

			count -= r_turb_spancount;

			if (count)
			{
			// calculate s/z, t/z, zi->fixed s and t at far end of span,
			// calculate s and t steps across span by shifting
				sdivz += sdivz16stepu;
				tdivz += tdivz16stepu;
				zi += zi16stepu;
			#ifdef USE_FAST_RECIPROCAL
	z = (float)0x10000 * fast_reciprocal(zi);	// prescale to 16.16 fixed-point
#else
	z = (float)0x10000 / zi;	// prescale to 16.16 fixed-point
#endif

				snext = (int)(sdivz * z) + sadjust;
				if (snext > bbextents)
					snext = bbextents;
				else if (snext < 32)
					snext = 32;	// prevent round-off error on <0 steps from
								//  from causing overstepping & running off the
								//  edge of the texture

				tnext = (int)(tdivz * z) + tadjust;
				if (tnext > bbextentt)
					tnext = bbextentt;
				else if (tnext < 32)
					tnext = 32;	// guard against round-off error on <0 steps

				r_turb_sstep = (snext - r_turb_s) >> 5;
				r_turb_tstep = (tnext - r_turb_t) >> 5;
			}
			else
			{
			// calculate s/z, t/z, zi->fixed s and t at last pixel in span (so
			// can't step off polygon), clamp, calculate s and t steps across
			// span by division, biasing steps low so we don't run off the
			// texture
				spancountminus1 = (float)(r_turb_spancount - 1);
				sdivz += d_sdivzstepu * spancountminus1;
				tdivz += d_tdivzstepu * spancountminus1;
				zi += d_zistepu * spancountminus1;
			#ifdef USE_FAST_RECIPROCAL
	z = (float)0x10000 * fast_reciprocal(zi);	// prescale to 16.16 fixed-point
#else
	z = (float)0x10000 / zi;	// prescale to 16.16 fixed-point
#endif
				snext = (int)(sdivz * z) + sadjust;
				if (snext > bbextents)
					snext = bbextents;
				else if (snext < 32)
					snext = 32;	// prevent round-off error on <0 steps from
								//  from causing overstepping & running off the
								//  edge of the texture

				tnext = (int)(tdivz * z) + tadjust;
				if (tnext > bbextentt)
					tnext = bbextentt;
				else if (tnext < 32)
					tnext = 32;	// guard against round-off error on <0 steps

				if (r_turb_spancount > 1)
				{
					r_turb_sstep = (snext - r_turb_s) / (r_turb_spancount - 1);
					r_turb_tstep = (tnext - r_turb_t) / (r_turb_spancount - 1);
				}
			}

			r_turb_s = r_turb_s & ((CYCLE<<16)-1);
			r_turb_t = r_turb_t & ((CYCLE<<16)-1);

			D_DrawTurbulent8Span ();

			r_turb_s = snext;
			r_turb_t = tnext;

		} while (count > 0);

	} while ((pspan = pspan->pnext) != NULL);
}

#endif

#if	!id386
#if	!idppc
#if !USE_ASM_SPANS


/*
=============
D_DrawSpans8
=============
*/
void D_DrawSpans8 (espan_t *pspan)
{
	int				count, spancount, copy_of_cachewidth;
	unsigned char	*pbase, *pdest;
	fixed16_t		s, t, snext, tnext, sstep, tstep;
	float			sdivz, tdivz, zi, z, du, dv, spancountminus1;
	float			sdivz8stepu, tdivz8stepu, zi8stepu;

	sstep = 0;	// keep compiler happy
	tstep = 0;	// ditto

	pbase = (unsigned char *)cacheblock;

	sdivz8stepu = d_sdivzstepu * 8;
	tdivz8stepu = d_tdivzstepu * 8;
	zi8stepu = d_zistepu * 8;

	do
	{
		pdest = (unsigned char *)((byte *)d_viewbuffer +
				(screenwidth * pspan->v) + pspan->u);

		count = pspan->count;

	// calculate the initial s/z, t/z, 1/z, s, and t and clamp
		du = (float)pspan->u;
		dv = (float)pspan->v;

		sdivz = d_sdivzorigin + dv*d_sdivzstepv + du*d_sdivzstepu;
		tdivz = d_tdivzorigin + dv*d_tdivzstepv + du*d_tdivzstepu;
		zi = d_ziorigin + dv*d_zistepv + du*d_zistepu;
	#ifdef USE_FAST_RECIPROCAL
	z = (float)0x10000 * fast_reciprocal(zi);	// prescale to 16.16 fixed-point
#else
	z = (float)0x10000 / zi;	// prescale to 16.16 fixed-point
#endif

		s = (int)(sdivz * z) + sadjust;
		if (s > bbextents)
			s = bbextents;
		else if (s < 0)
			s = 0;

		t = (int)(tdivz * z) + tadjust;
		if (t > bbextentt)
			t = bbextentt;
		else if (t < 0)
			t = 0;

		if (count > 8)
			zi += zi8stepu;
		else {
			spancountminus1 = (float)(count - 1);
			zi += d_zistepu * spancountminus1;
		}
		z = (float)0x10000 / zi; // prescale to 16.16 fixed-point

		do
		{
		// calculate s and t at the far end of the span
			if (count >= 8)
				spancount = 8;
			else
				spancount = count;

			count -= spancount;

			if (count)
			{
			// calculate s/z, t/z, zi->fixed s and t at far end of span,
			// calculate s and t steps across span by shifting
				sdivz += sdivz8stepu;
				tdivz += tdivz8stepu;
				snext = (int)(sdivz * z) + sadjust;
				tnext = (int)(tdivz * z) + tadjust;
				if (count > 8)
					zi += zi8stepu;
				else {
					spancountminus1 = (float)(count - 1);
					zi += d_zistepu * spancountminus1;
				}
				z = (float)0x10000 / zi; // prescale to 16.16 fixed-point
				if (snext > bbextents)
					snext = bbextents;
				else if (snext < 8)
					snext = 8; // prevent round-off error on <0 steps from
						   //  from causing overstepping & running off the
						   //  edge of the texture

				if (tnext > bbextentt)
					tnext = bbextentt;
				else if (tnext < 8)
					tnext = 8; // guard against round-off error on <0 steps

				sstep = (snext - s) >> 3;
				tstep = (tnext - t) >> 3;
			}
			else
			{
			// calculate s/z, t/z, zi->fixed s and t at last pixel in span (so
			// can't step off polygon), clamp, calculate s and t steps across
			// span by division, biasing steps low so we don't run off the
			// texture
				sdivz += d_sdivzstepu * spancountminus1;
				tdivz += d_tdivzstepu * spancountminus1;

				snext = (int)(sdivz * z) + sadjust;
				tnext = (int)(tdivz * z) + tadjust;

				if (snext > bbextents)
					snext = bbextents;
				else if (snext < 8)
					snext = 8; // prevent round-off error on <0 steps from
						   //  from causing overstepping & running off the
						   //  edge of the texture
				if (tnext > bbextentt)

					tnext = bbextentt;
				else if (tnext < 8)
					tnext = 8; // guard against round-off error on <0 steps

				if (spancount > 1)
				{
					sstep = (snext - s) / (spancount - 1);
					tstep = (tnext - t) / (spancount - 1);
				}
			}

			copy_of_cachewidth = cachewidth;
#if 1
			do
			{
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
			} while (--spancount > 0);
#else
			switch (((unsigned long)pdest) & 3) {
			case 1:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				if (--spancount == 0)
					goto done;
			case 2:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				if (--spancount == 0)
					goto done;
			case 3:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				if (--spancount == 0)
					goto done;
			case 0:
				break;
			}
			while (spancount >= 4)
			{
				register unsigned long pixel;

				pixel = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				pixel = (pixel << 8) + *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				pixel = (pixel << 8) + *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				pixel = (pixel << 8) + *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				*(unsigned long *)pdest = pixel;
				pdest += 4;
				spancount -= 4;
			}
			switch (spancount) {
			case 3:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
			case 2:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
			case 1:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
			case 0:
				break;
			}
done:
#endif
			s = snext;
			t = tnext;

		} while (count > 0);

	} while ((pspan = pspan->pnext) != NULL);
}

#endif
#endif
#endif


#if	!id386
#if	!idppc
#if !id68k


/*
=============
D_DrawSpans16
=============
*/
void D_DrawSpans16 (espan_t *pspan)
{
	int				count, spancount, copy_of_cachewidth;
	unsigned char	*pbase, *pdest;
	fixed16_t		s, t, snext, tnext, sstep, tstep;
	float			sdivz, tdivz, zi, z, du, dv, spancountminus1;
	float			sdivz16stepu, tdivz16stepu, zi16stepu;

	sstep = 0;	// keep compiler happy
	tstep = 0;	// ditto

	pbase = (unsigned char *)cacheblock;

	sdivz16stepu = d_sdivzstepu * 16;
	tdivz16stepu = d_tdivzstepu * 16;
	zi16stepu = d_zistepu * 16;

	do
	{
		pdest = (unsigned char *)((byte *)d_viewbuffer +
				(screenwidth * pspan->v) + pspan->u);

		count = pspan->count;

	// calculate the initial s/z, t/z, 1/z, s, and t and clamp
		du = (float)pspan->u;
		dv = (float)pspan->v;

		sdivz = d_sdivzorigin + dv*d_sdivzstepv + du*d_sdivzstepu;
		tdivz = d_tdivzorigin + dv*d_tdivzstepv + du*d_tdivzstepu;
		zi = d_ziorigin + dv*d_zistepv + du*d_zistepu;
	#ifdef USE_FAST_RECIPROCAL
	z = (float)0x10000 * fast_reciprocal(zi);	// prescale to 16.16 fixed-point
#else
	z = (float)0x10000 / zi;	// prescale to 16.16 fixed-point
#endif

		s = (int)(sdivz * z) + sadjust;
		if (s > bbextents)
			s = bbextents;
		else if (s < 0)
			s = 0;

		t = (int)(tdivz * z) + tadjust;
		if (t > bbextentt)
			t = bbextentt;
		else if (t < 0)
			t = 0;

		if (count > 16)
			zi += zi16stepu;
		else {
			spancountminus1 = (float)(count - 1);
			zi += d_zistepu * spancountminus1;
		}
		z = (float)0x10000 / zi; // prescale to 16.16 fixed-point

		do
		{
		// calculate s and t at the far end of the span
			if (count >= 16)
				spancount = 16;
			else
				spancount = count;

			count -= spancount;

			if (count)
			{
			// calculate s/z, t/z, zi->fixed s and t at far end of span,
			// calculate s and t steps across span by shifting
				sdivz += sdivz16stepu;
				tdivz += tdivz16stepu;
				snext = (int)(sdivz * z) + sadjust;
				tnext = (int)(tdivz * z) + tadjust;
				if (count > 16)
					zi += zi16stepu;
				else {
					spancountminus1 = (float)(count - 1);
					zi += d_zistepu * spancountminus1;
				}
				z = (float)0x10000 / zi; // prescale to 16.16 fixed-point
				if (snext > bbextents)
					snext = bbextents;
				else if (snext < 16)
					snext = 8; // prevent round-off error on <0 steps from
						   //  from causing overstepping & running off the
						   //  edge of the texture

				if (tnext > bbextentt)
					tnext = bbextentt;
				else if (tnext < 16)
					tnext = 8; // guard against round-off error on <0 steps

				sstep = (snext - s) >> 4;
				tstep = (tnext - t) >> 4;
			}
			else
			{
			// calculate s/z, t/z, zi->fixed s and t at last pixel in span (so
			// can't step off polygon), clamp, calculate s and t steps across
			// span by division, biasing steps low so we don't run off the
			// texture
				sdivz += d_sdivzstepu * spancountminus1;
				tdivz += d_tdivzstepu * spancountminus1;

				snext = (int)(sdivz * z) + sadjust;
				tnext = (int)(tdivz * z) + tadjust;

				if (snext > bbextents)
					snext = bbextents;
				else if (snext < 16)
					snext = 8; // prevent round-off error on <0 steps from
						   //  from causing overstepping & running off the
						   //  edge of the texture
				if (tnext > bbextentt)

					tnext = bbextentt;
				else if (tnext < 16)
					tnext = 8; // guard against round-off error on <0 steps

				if (spancount > 1)
				{
					sstep = (snext - s) / (spancount - 1);
					tstep = (tnext - t) / (spancount - 1);
				}
			}

			copy_of_cachewidth = cachewidth;
#if 1
			do
			{
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
			} while (--spancount > 0);
#else
			switch (((unsigned long)pdest) & 3) {
			case 1:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				if (--spancount == 0)
					goto done;
			case 2:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				if (--spancount == 0)
					goto done;
			case 3:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				if (--spancount == 0)
					goto done;
			case 0:
				break;
			}
			while (spancount >= 4)
			{
				register unsigned long pixel;

				pixel = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				pixel = (pixel << 8) + *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				pixel = (pixel << 8) + *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				pixel = (pixel << 8) + *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
				*(unsigned long *)pdest = pixel;
				pdest += 4;
				spancount -= 4;
			}
			switch (spancount) {
			case 3:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
			case 2:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
			case 1:
				*pdest++ = *(pbase + (s >> 16) + (t >> 16) * copy_of_cachewidth);
				s += sstep;
				t += tstep;
			case 0:
				break;
			}
done:
#endif
			s = snext;
			t = tnext;

		} while (count > 0);

	} while ((pspan = pspan->pnext) != NULL);
}

#endif
#endif
#endif


#if	!id386
#if	!idppc
#if !id68k

/*
=============
D_DrawZSpans
=============
*/
void D_DrawZSpans (espan_t *pspan)
{
	int				count, doublecount, izistep;
	int				izi;
	short			*pdest;
	unsigned		ltemp;
	double			zi;
	float			du, dv;

// FIXME: check for clamping/range problems
// we count on FP exceptions being turned off to avoid range problems
	izistep = (int)(d_zistepu * 0x8000 * 0x10000);

	do
	{
		pdest = d_pzbuffer + (d_zwidth * pspan->v) + pspan->u;

		count = pspan->count;

	// calculate the initial 1/z
		du = (float)pspan->u;
		dv = (float)pspan->v;

		zi = d_ziorigin + dv*d_zistepv + du*d_zistepu;
	// we count on FP exceptions being turned off to avoid range problems
		izi = (int)(zi * 0x8000 * 0x10000);

		if ((long)pdest & 0x02)
		{
			*pdest++ = (short)(izi >> 16);
			izi += izistep;
			count--;
		}

		if ((doublecount = count >> 1) > 0)
		{
			do
			{
                *pdest++ = (short)(izi >> 16);
                izi += izistep;
                *pdest++ = (short)(izi >> 16);
                izi += izistep;
			} while (--doublecount > 0);
		}

		if (count & 1)
			*pdest = (short)(izi >> 16);

	} while ((pspan = pspan->pnext) != NULL);
}

#endif
#endif
#endif
