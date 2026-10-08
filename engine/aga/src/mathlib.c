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
// mathlib.c -- math primitives

#include <math.h>
#include "quakedef.h"

void Sys_Error (char *error, ...);

vec3_t vec3_origin = {0,0,0};
int nanmask = 255<<23;
int aw_fpucount[AW_FPU_COUNTERS];

/*-----------------------------------------------------------------*/

/*
AmiWind table sine/cosine (ENGINE-FPU-UNIMPL-31). The C library's sin/cos
(and the cexp the compiler makes of a sin+cos pair) execute FINTRZ/FMOVECR,
which the 68040 does not implement: each costs a trap into an FPU support
library, or a crash without one. Quake's own answer for per-frame trig is a
table (R_InitTurb's sintable, the 16-bit angle quantisation of ANGLE2SHORT);
here a quarter-wave table of SINTAB_STEPS+1 floats, filled on first use from
a Taylor series (multiplies and adds only), read with linear interpolation
plus the second-order term (sine's second derivative is minus itself, so the
chord error is frac*(1-frac)*h*h/2 times the value). Error below 1.5e-7
(float rounding); exact at multiples of 90 degrees, so 0 gives 0 and 1.
*/
#define SINTAB_STEPS	1024	// per 90 degrees; power of two
static float	sintab[SINTAB_STEPS+1];
static int		sintab_ready;

static void Q_SinTableInit (void)
{
	int		i, k;
	double	x, x2, term, sum;

	for (i=0 ; i<SINTAB_STEPS ; i++)
	{
		x = i * (M_PI/2) / SINTAB_STEPS;
		x2 = x*x;
		term = sum = x;
		for (k=2 ; k<24 ; k+=2)
		{
			term *= -x2 / (k*(k+1));
			sum += term;
		}
		sintab[i] = sum;
	}
	sintab[SINTAB_STEPS] = 1;
	sintab_ready = 1;
}

void Q_SinCosDeg (float degrees, float *s, float *c)
{
	double	t, frac, bend;
	float	a, b;
	int		i, j;

	AW_FPUCOUNT(AW_FPU_TABLE);
	if (degrees == 0)
	{
		*s = 0;
		*c = 1;
		return;
	}
	if (!sintab_ready)
		Q_SinTableInit ();
	if (degrees > 1.0e7 || degrees < -1.0e7)	// keep the index in range
		degrees -= 360 * floor (degrees / 360);
	t = degrees * (SINTAB_STEPS*4 / 360.0);
	i = (int)t;
	if (t < i)
		i--;
	frac = t - i;
	j = i & (SINTAB_STEPS-1);
	a = sintab[j] + frac * (sintab[j+1] - sintab[j]);	// sine within the quadrant
	b = sintab[SINTAB_STEPS-j] + frac * (sintab[SINTAB_STEPS-j-1] - sintab[SINTAB_STEPS-j]);
	bend = 1 + frac * (1 - frac) * ((M_PI/2/SINTAB_STEPS) * (M_PI/2/SINTAB_STEPS) / 2);
	a *= bend;
	b *= bend;
	switch ((i & (SINTAB_STEPS*4-1)) / SINTAB_STEPS)
	{
	case 0: *s = a; *c = b; break;
	case 1: *s = b; *c = -a; break;
	case 2: *s = -a; *c = -b; break;
	default: *s = -b; *c = a; break;
	}
}

void Q_SinCosRad (float radians, float *s, float *c)
{
	Q_SinCosDeg (radians * (float)(180 / M_PI), s, c);
}

float Q_SinRad (float radians)
{
	float	s, c;

	Q_SinCosDeg (radians * (float)(180 / M_PI), &s, &c);
	return s;
}

float Q_CosRad (float radians)
{
	float	s, c;

	Q_SinCosDeg (radians * (float)(180 / M_PI), &s, &c);
	return c;
}

/*
Arc tangent without the C library (whose atan loads its constants with
FMOVECR, unimplemented on the 68040): reduce to [0,1] by symmetry, then to
[0,tan(15 degrees)] with atan(t) = pi/6 + atan((t*sqrt(3)-1)/(t+sqrt(3))),
and sum the odd series to z^23 (error below 3e-16). Exact for zero and equal
magnitudes, so axis and diagonal directions give the same angles as before.
*/
static double Q_atan01 (double t)
{
	double	z, z2, term, sum;
	int		k, shifted;

	if (t == 1)
		return M_PI/4;
	shifted = t > 0.26794919243112270;
	z = shifted ? (t*1.7320508075688772 - 1) / (t + 1.7320508075688772) : t;
	z2 = z*z;
	term = sum = z;
	for (k=3 ; k<=23 ; k+=2)
	{
		term *= -z2;
		sum += term / k;
	}
	return shifted ? M_PI/6 + sum : sum;
}

double Q_atan2 (double y, double x)
{
	double	ax = fabs(x), ay = fabs(y), r;

	if (ay == 0)
		r = (x < 0) ? M_PI : 0;
	else if (ax == 0)
		r = M_PI/2;
	else
	{
		r = ay <= ax ? Q_atan01 (ay/ax) : M_PI/2 - Q_atan01 (ax/ay);
		if (x < 0)
			r = M_PI - r;
	}
	return y < 0 ? -r : r;
}

float Q_TanRad (float radians)
{
	float	s, c;

	Q_SinCosRad (radians, &s, &c);
	return s / c;
}

#define DEG2RAD( a ) ( a * M_PI ) / 180.0F

void ProjectPointOnPlane( vec3_t dst, const vec3_t p, const vec3_t normal )
{
	float d;
	vec3_t n;
	float inv_denom;

	inv_denom = 1.0F / DotProduct( normal, normal );

	d = DotProduct( normal, p ) * inv_denom;

	n[0] = normal[0] * inv_denom;
	n[1] = normal[1] * inv_denom;
	n[2] = normal[2] * inv_denom;

	dst[0] = p[0] - d * n[0];
	dst[1] = p[1] - d * n[1];
	dst[2] = p[2] - d * n[2];
}

/*
** assumes "src" is normalized
*/
void PerpendicularVector( vec3_t dst, const vec3_t src )
{
	int	pos;
	int i;
	float minelem = 1.0F;
	vec3_t tempvec;

	/*
	** find the smallest magnitude axially aligned vector
	*/
	for ( pos = 0, i = 0; i < 3; i++ )
	{
		if ( fabs( src[i] ) < minelem )
		{
			pos = i;
			minelem = fabs( src[i] );
		}
	}
	tempvec[0] = tempvec[1] = tempvec[2] = 0.0F;
	tempvec[pos] = 1.0F;

	/*
	** project the point onto the plane defined by src
	*/
	ProjectPointOnPlane( dst, tempvec, src );

	/*
	** normalize the result
	*/
	VectorNormalize( dst );
}

#ifdef _WIN32
#pragma optimize( "", off )
#endif


void RotatePointAroundVector( vec3_t dst, const vec3_t dir, const vec3_t point, float degrees )
{
	float	m[3][3];
	float	im[3][3];
	float	zrot[3][3];
	float	tmpmat[3][3];
	float	rot[3][3];
	int	i;
	vec3_t vr, vup, vf;

	vf[0] = dir[0];
	vf[1] = dir[1];
	vf[2] = dir[2];

	PerpendicularVector( vr, dir );
	CrossProduct( vr, vf, vup );

	m[0][0] = vr[0];
	m[1][0] = vr[1];
	m[2][0] = vr[2];

	m[0][1] = vup[0];
	m[1][1] = vup[1];
	m[2][1] = vup[2];

	m[0][2] = vf[0];
	m[1][2] = vf[1];
	m[2][2] = vf[2];

	memcpy( im, m, sizeof( im ) );

	im[0][1] = m[1][0];
	im[0][2] = m[2][0];
	im[1][0] = m[0][1];
	im[1][2] = m[2][1];
	im[2][0] = m[0][2];
	im[2][1] = m[1][2];

	memset( zrot, 0, sizeof( zrot ) );
	zrot[0][0] = zrot[1][1] = zrot[2][2] = 1.0F;

	{
		float	s, c;

		Q_SinCosDeg (degrees, &s, &c);
		zrot[0][0] = c;
		zrot[0][1] = s;
		zrot[1][0] = -s;
		zrot[1][1] = c;
	}

	R_ConcatRotations( m, zrot, tmpmat );
	R_ConcatRotations( tmpmat, im, rot );

	for ( i = 0; i < 3; i++ )
	{
		dst[i] = rot[i][0] * point[0] + rot[i][1] * point[1] + rot[i][2] * point[2];
	}
}

#ifdef _WIN32
#pragma optimize( "", on )
#endif

/*-----------------------------------------------------------------*/


float	anglemod(float a)
{
#if defined(__STORM__) || defined(__VBCC__) || defined(__GNUC__)
	// Use simple modulo for Amiga GCC - fixed-point version has precision issues
	if (a >= 0)
		a -= 360*(int)(a/360);
	else
		a += 360*( 1 + (int)(-a/360) );
#else
	a = (360.0/65536) * ((int)(a*(65536/360.0)) & 65535);
#endif
	return a;
}

/*
==================
BOPS_Error

Split out like this for ASM to call.
==================
*/
void BOPS_Error (void)
{
	Sys_Error ("BoxOnPlaneSide:  Bad signbits");
}


#if	!id386

/*
==================
BoxOnPlaneSide

Returns 1, 2, or 1 + 2
==================
*/
int BoxOnPlaneSide (vec3_t emins, vec3_t emaxs, mplane_t *p)
{
	float	dist1, dist2;
	int		sides;

#if 0	// this is done by the BOX_ON_PLANE_SIDE macro before calling this
		// function
// fast axial cases
	if (p->type < 3)
	{
		if (p->dist <= emins[p->type])
			return 1;
		if (p->dist >= emaxs[p->type])
			return 2;
		return 3;
	}
#endif

// general case
	switch (p->signbits)
	{
	case 0:
dist1 = p->normal[0]*emaxs[0] + p->normal[1]*emaxs[1] + p->normal[2]*emaxs[2];
dist2 = p->normal[0]*emins[0] + p->normal[1]*emins[1] + p->normal[2]*emins[2];
		break;
	case 1:
dist1 = p->normal[0]*emins[0] + p->normal[1]*emaxs[1] + p->normal[2]*emaxs[2];
dist2 = p->normal[0]*emaxs[0] + p->normal[1]*emins[1] + p->normal[2]*emins[2];
		break;
	case 2:
dist1 = p->normal[0]*emaxs[0] + p->normal[1]*emins[1] + p->normal[2]*emaxs[2];
dist2 = p->normal[0]*emins[0] + p->normal[1]*emaxs[1] + p->normal[2]*emins[2];
		break;
	case 3:
dist1 = p->normal[0]*emins[0] + p->normal[1]*emins[1] + p->normal[2]*emaxs[2];
dist2 = p->normal[0]*emaxs[0] + p->normal[1]*emaxs[1] + p->normal[2]*emins[2];
		break;
	case 4:
dist1 = p->normal[0]*emaxs[0] + p->normal[1]*emaxs[1] + p->normal[2]*emins[2];
dist2 = p->normal[0]*emins[0] + p->normal[1]*emins[1] + p->normal[2]*emaxs[2];
		break;
	case 5:
dist1 = p->normal[0]*emins[0] + p->normal[1]*emaxs[1] + p->normal[2]*emins[2];
dist2 = p->normal[0]*emaxs[0] + p->normal[1]*emins[1] + p->normal[2]*emaxs[2];
		break;
	case 6:
dist1 = p->normal[0]*emaxs[0] + p->normal[1]*emins[1] + p->normal[2]*emins[2];
dist2 = p->normal[0]*emins[0] + p->normal[1]*emaxs[1] + p->normal[2]*emaxs[2];
		break;
	case 7:
dist1 = p->normal[0]*emins[0] + p->normal[1]*emins[1] + p->normal[2]*emins[2];
dist2 = p->normal[0]*emaxs[0] + p->normal[1]*emaxs[1] + p->normal[2]*emaxs[2];
		break;
	default:
		dist1 = dist2 = 0;		// shut up compiler
		BOPS_Error ();
		break;
	}

#if 0
	int		i;
	vec3_t	corners[2];

	for (i=0 ; i<3 ; i++)
	{
		if (plane->normal[i] < 0)
		{
			corners[0][i] = emins[i];
			corners[1][i] = emaxs[i];
		}
		else
		{
			corners[1][i] = emins[i];
			corners[0][i] = emaxs[i];
		}
	}
	dist = DotProduct (plane->normal, corners[0]) - plane->dist;
	dist2 = DotProduct (plane->normal, corners[1]) - plane->dist;
	sides = 0;
	if (dist1 >= 0)
		sides = 1;
	if (dist2 < 0)
		sides |= 2;

#endif

	sides = 0;
	if (dist1 >= p->dist)
		sides = 1;
	if (dist2 < p->dist)
		sides |= 2;

#ifdef PARANOID
if (sides == 0)
	Sys_Error ("BoxOnPlaneSide: sides==0");
#endif

	return sides;
}

#endif


void AngleVectors (vec3_t angles, vec3_t forward, vec3_t right, vec3_t up)
{
	float		sr, sp, sy, cr, cp, cy;

	AW_FPUCOUNT(AW_FPU_ANGLEVECTORS);
	Q_SinCosDeg (angles[YAW], &sy, &cy);
	Q_SinCosDeg (angles[PITCH], &sp, &cp);
	Q_SinCosDeg (angles[ROLL], &sr, &cr);

	forward[0] = cp*cy;
	forward[1] = cp*sy;
	forward[2] = -sp;
	right[0] = -sr*sp*cy + cr*sy;
	right[1] = -sr*sp*sy - cr*cy;
	right[2] = -sr*cp;
	up[0] = cr*sp*cy + sr*sy;
	up[1] = cr*sp*sy - sr*cy;
	up[2] = cr*cp;
}

int VectorCompare (vec3_t v1, vec3_t v2)
{
	int		i;

	for (i=0 ; i<3 ; i++)
		if (v1[i] != v2[i])
			return 0;

	return 1;
}

void VectorMA (vec3_t veca, float scale, vec3_t vecb, vec3_t vecc)
{
	vecc[0] = veca[0] + scale*vecb[0];
	vecc[1] = veca[1] + scale*vecb[1];
	vecc[2] = veca[2] + scale*vecb[2];
}


vec_t _DotProduct (vec3_t v1, vec3_t v2)
{
	return v1[0]*v2[0] + v1[1]*v2[1] + v1[2]*v2[2];
}

void _VectorSubtract (vec3_t veca, vec3_t vecb, vec3_t out)
{
	out[0] = veca[0]-vecb[0];
	out[1] = veca[1]-vecb[1];
	out[2] = veca[2]-vecb[2];
}

void _VectorAdd (vec3_t veca, vec3_t vecb, vec3_t out)
{
	out[0] = veca[0]+vecb[0];
	out[1] = veca[1]+vecb[1];
	out[2] = veca[2]+vecb[2];
}

void _VectorCopy (vec3_t in, vec3_t out)
{
	out[0] = in[0];
	out[1] = in[1];
	out[2] = in[2];
}

void CrossProduct (vec3_t v1, vec3_t v2, vec3_t cross)
{
	cross[0] = v1[1]*v2[2] - v1[2]*v2[1];
	cross[1] = v1[2]*v2[0] - v1[0]*v2[2];
	cross[2] = v1[0]*v2[1] - v1[1]*v2[0];
}

double sqrt(double x);

#if !idppc

/*
==================
InvSqrt

Fast inverse square root using the famous Quake III algorithm
Returns 1/sqrt(x)

Benchmarked on real 68040 hardware:
- 2.3x faster than hardware fssqrt instruction
- ~0.2% error (acceptable for game physics and rendering)
==================
*/
static float InvSqrt(float x)
{
	float xhalf = 0.5f * x;
	int i = *(int*)&x;            // store floating-point bits in integer
	i = 0x5f3759df - (i >> 1);    // initial guess for Newton's method
	x = *(float*)&i;              // convert new bits into float
	x = x*(1.5f - xhalf*x*x);     // One round of Newton's method
	return x;
}

vec_t Length(vec3_t v)
{
	int		i;
	float	length_squared;

	length_squared = 0;
	for (i=0 ; i< 3 ; i++)
		length_squared += v[i]*v[i];

	// Use fast inverse sqrt: sqrt(x) = x * (1/sqrt(x))
	return length_squared * InvSqrt(length_squared);
}

float VectorNormalize (vec3_t v)
{
	float	length_squared;
	float	ilength;

	length_squared = v[0]*v[0] + v[1]*v[1] + v[2]*v[2];

	if (length_squared > 0)
	{
		// Use fast inverse sqrt directly (this is what we need!)
		ilength = InvSqrt(length_squared);
		v[0] *= ilength;
		v[1] *= ilength;
		v[2] *= ilength;

		// Return length: sqrt(x) = x * (1/sqrt(x))
		return length_squared * ilength;
	}

	return 0;
}

#endif

void VectorInverse (vec3_t v)
{
	v[0] = -v[0];
	v[1] = -v[1];
	v[2] = -v[2];
}

void VectorScale (vec3_t in, vec_t scale, vec3_t out)
{
	out[0] = in[0]*scale;
	out[1] = in[1]*scale;
	out[2] = in[2]*scale;
}


int Q_log2(int val)
{
	int answer=0;
	while (val>>=1)
		answer++;
	return answer;
}


/*
================
R_ConcatRotations
================
*/
void R_ConcatRotations (float in1[3][3], float in2[3][3], float out[3][3])
{
	out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] +
				in1[0][2] * in2[2][0];
	out[0][1] = in1[0][0] * in2[0][1] + in1[0][1] * in2[1][1] +
				in1[0][2] * in2[2][1];
	out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] +
				in1[0][2] * in2[2][2];
	out[1][0] = in1[1][0] * in2[0][0] + in1[1][1] * in2[1][0] +
				in1[1][2] * in2[2][0];
	out[1][1] = in1[1][0] * in2[0][1] + in1[1][1] * in2[1][1] +
				in1[1][2] * in2[2][1];
	out[1][2] = in1[1][0] * in2[0][2] + in1[1][1] * in2[1][2] +
				in1[1][2] * in2[2][2];
	out[2][0] = in1[2][0] * in2[0][0] + in1[2][1] * in2[1][0] +
				in1[2][2] * in2[2][0];
	out[2][1] = in1[2][0] * in2[0][1] + in1[2][1] * in2[1][1] +
				in1[2][2] * in2[2][1];
	out[2][2] = in1[2][0] * in2[0][2] + in1[2][1] * in2[1][2] +
				in1[2][2] * in2[2][2];
}


/*
================
R_ConcatTransforms
================
*/
void R_ConcatTransforms (float in1[3][4], float in2[3][4], float out[3][4])
{
	out[0][0] = in1[0][0] * in2[0][0] + in1[0][1] * in2[1][0] +
				in1[0][2] * in2[2][0];
	out[0][1] = in1[0][0] * in2[0][1] + in1[0][1] * in2[1][1] +
				in1[0][2] * in2[2][1];
	out[0][2] = in1[0][0] * in2[0][2] + in1[0][1] * in2[1][2] +
				in1[0][2] * in2[2][2];
	out[0][3] = in1[0][0] * in2[0][3] + in1[0][1] * in2[1][3] +
				in1[0][2] * in2[2][3] + in1[0][3];
	out[1][0] = in1[1][0] * in2[0][0] + in1[1][1] * in2[1][0] +
				in1[1][2] * in2[2][0];
	out[1][1] = in1[1][0] * in2[0][1] + in1[1][1] * in2[1][1] +
				in1[1][2] * in2[2][1];
	out[1][2] = in1[1][0] * in2[0][2] + in1[1][1] * in2[1][2] +
				in1[1][2] * in2[2][2];
	out[1][3] = in1[1][0] * in2[0][3] + in1[1][1] * in2[1][3] +
				in1[1][2] * in2[2][3] + in1[1][3];
	out[2][0] = in1[2][0] * in2[0][0] + in1[2][1] * in2[1][0] +
				in1[2][2] * in2[2][0];
	out[2][1] = in1[2][0] * in2[0][1] + in1[2][1] * in2[1][1] +
				in1[2][2] * in2[2][1];
	out[2][2] = in1[2][0] * in2[0][2] + in1[2][1] * in2[1][2] +
				in1[2][2] * in2[2][2];
	out[2][3] = in1[2][0] * in2[0][3] + in1[2][1] * in2[1][3] +
				in1[2][2] * in2[2][3] + in1[2][3];
}


/*
===================
FloorDivMod

Returns mathematically correct (floor-based) quotient and remainder for
numer and denom, both of which should contain no fractional part. The
quotient must fit in 32 bits.
====================
*/

void FloorDivMod (double numer, double denom, int *quotient,
		int *rem)
{
	int		q, r;
	double	x;

#ifndef PARANOID
	if (denom <= 0.0)
		Sys_Error ("FloorDivMod: bad denominator %d\n", denom);

//	if ((floor(numer) != numer) || (floor(denom) != denom))
//		Sys_Error ("FloorDivMod: non-integer numer or denom %f %f\n",
//				numer, denom);
#endif

	if (numer >= 0.0)
	{

		x = floor(numer / denom);
		q = (int)x;
		r = (int)floor(numer - (x * denom));
	}
	else
	{
	//
	// perform operations with positive values, and fix mod to make floor-based
	//
		x = floor(-numer / denom);
		q = -(int)x;
		r = (int)floor(-numer - (x * denom));
		if (r != 0)
		{
			q--;
			r = (int)denom - r;
		}
	}

	*quotient = q;
	*rem = r;
}


/*
===================
GreatestCommonDivisor
====================
*/
int GreatestCommonDivisor (int i1, int i2)
{
	if (i1 > i2)
	{
		if (i2 == 0)
			return (i1);
		return GreatestCommonDivisor (i2, i1 % i2);
	}
	else
	{
		if (i1 == 0)
			return (i2);
		return GreatestCommonDivisor (i1, i2 % i1);
	}
}


#if	!id386

// TODO: move to nonintel.c

/*
===================
Invert24To16

Inverts an 8.24 value to a 16.16 value
====================
*/

fixed16_t Invert24To16(fixed16_t val)
{
	if (val < 256)
		return (0xFFFFFFFF);

	return (fixed16_t)
			(((double)0x10000 * (double)0x1000000 / (double)val) + 0.5);
}

#endif
