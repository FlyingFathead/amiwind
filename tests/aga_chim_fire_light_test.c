/* SPDX-License-Identifier: GPL-2.0-or-later */
/* The fires' light (CHIM-EXTERIOR-FLAMES-MISSING-48): a frame map's aw_flame rows with aw_flame_light, read by
 * chim_chunks.c, and the level a placement's drawn box gets from them. Prints one level per box for the Python
 * side (tests/test_chim_exterior_flames.py), which computes the same with tools/chim/placement_light.py. */
#include "quakedef.h"
#include "r_local.h"
#include "chim/chim_local.h"
#include <assert.h>

int main(void)
{
	static const char entities[] =
		"{\n\"classname\" \"worldspawn\"\n\"_chim_frame\" \"0 0\"\n}\n"
		"{\n\"classname\" \"aw_flame\"\n\"origin\" \"100.00 -20.50 8.00\"\n\"aw_flame_size\" \"8.00\"\n"
		"\"aw_flame_shape\" \"6.00 10.00 3.00\"\n\"aw_flame_light\" \"128.0 186.4\"\n}\n"
		"{\n\"classname\" \"aw_flame\"\n\"origin\" \"100.00 -20.50 8.00\"\n\"aw_flame_size\" \"0.80\"\n}\n"
		"{\n\"classname\" \"aw_flame\"\n\"origin\" \"-300.25 40.00 0.00\"\n\"aw_flame_size\" \"8.00\"\n"
		"\"aw_flame_light\" \"64.0 120.0\"\n}\n"
		"{\n\"classname\" \"info_player_start\"\n\"origin\" \"0 0 40\"\n\"aw_flame_light\" \"99.0 99.0\"\n}\n";
	static const float boxes[][6] = {
		{90, -30, 0, 110, -10, 16},       /* on the first fire */
		{150, -20, 0, 170, 0, 16},        /* 60 away: R/3 < d < R */
		{300, -20, 0, 320, 0, 16},        /* 210 away: between R and 2R */
		{400, -20, 0, 420, 0, 16},        /* past 2R: none */
		{-310, 30, -8, -290, 50, 8},      /* on the second fire */
		{-100, 0, 0, -80, 20, 16}};       /* between them */
	int i;
	ChimChunks_FireLights (entities);
	/* only aw_flame rows with a light count; the player start's key is ignored */
	assert (ChimChunks_FireCount () == 2);
	for (i=0 ; i<(int)(sizeof(boxes)/sizeof(boxes[0])) ; i++)
		printf ("level %d %d\n", i, ChimChunks_FireLevel (boxes[i], boxes[i] + 3));
	ChimChunks_FireLights (NULL);              /* a room or a map without fires: none */
	assert (ChimChunks_FireCount () == 0 && ChimChunks_FireLevel (boxes[0], boxes[0] + 3) == 0);
	puts ("fire light: rows read, levels printed, cleared");
	return 0;
}
