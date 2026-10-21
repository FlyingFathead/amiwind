/* SPDX-License-Identifier: GPL-2.0-or-later
 * chim_format.c alone (GHOSTFENCE-NO-ANIMATION-46): a turbulent CHIM texture smaller than 64 x 64 is tiled to the
 * 64 x 64 that Turbulent8 reads, every mip level the source level repeated, so a face sees the same texel at every
 * texture coordinate (the small texture repeating with period w, h; the tiled one with period 64). */
#include <assert.h>
#include <stdio.h>
#include <string.h>
#include "chim_format.h"

int main(void)
{
	static unsigned char src[32*32/64*85], dst[CHIM_TURB_PIXELS];
	int i, j, x, y, s, t, sw, dw;
	const unsigned char *a, *b;
	assert (CHIM_TURB_PIXELS == 5440);
	/* Which textures are tiled: turbulent ('*'), smaller than 64, a divisor of 64. */
	assert (ChimFormat_TurbulentTile ("*scroll12", 32, 32));
	assert (ChimFormat_TurbulentTile ("*scroll12", 16, 32));
	assert (!ChimFormat_TurbulentTile ("*scroll12", 64, 64));
	assert (!ChimFormat_TurbulentTile ("*lava", 128, 128));
	assert (!ChimFormat_TurbulentTile ("*x", 48, 48));
	assert (!ChimFormat_TurbulentTile ("emit3_819", 32, 32));
	assert (!ChimFormat_TurbulentTile ("surface5", 32, 32));
	assert (!ChimFormat_TurbulentTile (NULL, 32, 32));
	for (i = 0; i < (int)sizeof(src); i++)
		src[i] = (unsigned char)(i * 7 + 3);
	memset (dst, 0xEE, sizeof(dst));
	ChimFormat_TileTurbulent (src, 32, 32, dst);
	a = src; b = dst;
	for (j = 0; j < 4; j++)
	{
		sw = 32 >> j; dw = 64 >> j;
		/* Any texture coordinate (s, t) wrapped at 64 (Turbulent8's mask) shows what the small texture shows at
		 * (s, t) wrapped at its own size. */
		for (t = 0; t < 200; t += 3)
			for (s = 0; s < 200; s += 5)
			{
				x = s % dw; y = t % dw;
				assert (b[y*dw + x] == a[(t % sw)*sw + s % sw]);
			}
		a += sw*sw; b += dw*dw;
	}
	assert (b == dst + CHIM_TURB_PIXELS);
	puts ("chim turbulent tile ok");
	return 0;
}
