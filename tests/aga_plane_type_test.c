/* SPDX-License-Identifier: GPL-2.0-or-later
 * aw_planetype.h alone (CHIM-PLANE-TYPE-ALL-SLANTED-46): a stored type-3 plane with an exact +X/+Y/+Z normal gets its
 * axis; every other plane keeps its stored type; the axial point distance p[type] - dist equals the dot-product
 * distance of the slanted path exactly, over many points. */
#include <assert.h>
#include <stdio.h>
#include "aw_planetype.h"

static float dot_dist (const float *n, const float *p, float d)
{
	return n[0]*p[0] + n[1]*p[1] + n[2]*p[2] - d;
}

int main(void)
{
	static const float x[3] = {1, 0, 0}, y[3] = {0, 1, 0}, z[3] = {0, 0, 1};
	static const float negx[3] = {-1, 0, 0}, slant[3] = {0.6f, 0.8f, 0}, almost[3] = {0.99999994f, 0, 0};
	static const float negzero[3] = {1, -0.0f, -0.0f};
	const float *axes[3];
	int a, i;
	axes[0] = x; axes[1] = y; axes[2] = z;
	assert (AW_PlaneType (x, 3) == 0);
	assert (AW_PlaneType (y, 3) == 1);
	assert (AW_PlaneType (z, 3) == 2);
	assert (AW_PlaneType (negzero, 3) == 0);
	assert (AW_PlaneType (negx, 3) == 3);      /* Quake's axial types assume a positive normal */
	assert (AW_PlaneType (slant, 3) == 3);
	assert (AW_PlaneType (almost, 3) == 3);    /* not exactly axial: keep the dot product */
	assert (AW_PlaneType (slant, 1) == 1);     /* a stored axial type is kept as stored */
	assert (AW_PlaneType (x, 4) == 0);         /* any non-axial stored type */
	for (a = 0; a < 3; a++)
		for (i = 0; i < 20000; i++)
		{
			float p[3], d = (float)((unsigned long)i * 37UL % 9001UL) * 0.37f - 1600.0f;
			p[0] = (float)((unsigned long)i * 7919UL % 65536UL) * 0.125f - 4096.0f;
			p[1] = (float)((unsigned long)i * 104729UL % 65536UL) * 0.0625f - 2048.0f;
			p[2] = (float)((unsigned long)i * 1299709UL % 32768UL) * 0.25f - 4096.0f;
			assert (p[AW_PlaneType (axes[a], 3)] - d == dot_dist (axes[a], p, d));
		}
	puts ("plane type ok");
	return 0;
}
