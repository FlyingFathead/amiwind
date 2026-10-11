/* SPDX-License-Identifier: GPL-2.0-or-later
 * The one map path resolver (aw_mappath.c): maps/<name>.chim (a CHIM frame
 * map) only when the image has a CHIM world and the file exists, else
 * maps/<name>.bsp; a frame map without its CHIM world, or a .chim file that
 * is no frame map, is refused with a reason instead of loading a void. No
 * original game data. */
#include <assert.h>
#include "quakedef.h"
#include "aw_mappath.h"

static const char *present[8];
static int opens;

int COM_FOpenFile (char *name, FILE **file)
{
	int i;
	opens++;
	*file = NULL;
	for (i=0 ; present[i] ; i++)
		if (!strcmp (name, present[i]))
		{
			*file = tmpfile ();
			return 124;
		}
	return -1;
}

int main (void)
{
	char path[AW_MAP_PATH_SIZE], why[160];
	static const char frame[] = "{\n\"classname\" \"worldspawn\"\n\"_chim_frame\" \"-7 2\"\n}\n{\n\"classname\" \"info_player_start\"\n}\n";
	static const char plain[] = "{\n\"classname\" \"worldspawn\"\n}\n{\n\"_chim_frame\" \"1 1\"\n}\n";

	present[0] = "maps/vf1637.chim";
	present[1] = "maps/vf1637.bsp";
	present[2] = "maps/balmora-chim.chim";

	/* legacy data (no chim/world.cwi): never a .chim, no file asked */
	aw_chim_world = 0;
	opens = 0;
	assert (!strcmp (AW_MapPath ("vf1637", path, sizeof(path)), "maps/vf1637.bsp"));
	assert (!strcmp (AW_MapPath ("vf1638", path, sizeof(path)), "maps/vf1638.bsp"));
	assert (opens == 0);

	/* a CHIM image: the frame map when it is there, the legacy map beside it */
	aw_chim_world = 1;
	assert (!strcmp (AW_MapPath ("vf1637", path, sizeof(path)), "maps/vf1637.chim"));
	assert (!strcmp (AW_MapPath ("vf1638", path, sizeof(path)), "maps/vf1638.bsp"));
	assert (!strcmp (AW_MapPath ("balmora-chim", path, sizeof(path)), "maps/balmora-chim.chim"));
	opens = 0;
	assert (!strcmp (AW_MapPath ("vf1637", path, sizeof(path)), "maps/vf1637.chim"));
	assert (opens == 0);					/* asked again: answered from the kept names */
	/* bounded: a name that does not fit gives an empty path, never a cut one */
	assert (AW_MapPath ("vf1637", path, 12)[0] == 0);
	assert (AW_MapPath ("0123456789012345678901234567890123456789012345678901234567", path, sizeof(path))[0] == 0);

	assert (AW_MapPathIs ("maps/intro_docks.bsp", "intro_docks"));
	assert (AW_MapPathIs ("maps/intro_docks-chim.chim", "intro_docks-chim"));
	assert (!AW_MapPathIs ("maps/intro_docks-chim.chim", "intro_docks"));
	assert (!AW_MapPathIs ("maps/sn045.far", "sn045"));
	assert (AW_MapPathChim ("maps/x.chim") && !AW_MapPathChim ("maps/x.bsp"));

	/* refusals */
	aw_chim_world = 0;
	assert (AW_MapRefused ("maps/vf1637.bsp", frame, why, sizeof(why)));
	assert (strstr (why, "CHIM frame map") && strstr (why, "chim/world.cwi"));
	assert (!AW_MapRefused ("maps/vf1638.bsp", plain, why, sizeof(why)) && !why[0]);	/* the key outside the worldspawn */
	assert (AW_MapRefused ("maps/vf1639.chim", plain, why, sizeof(why)));
	assert (strstr (why, "without a CHIM frame"));
	assert (AW_MapChimOrphan ("vf1637", why, sizeof(why)) && strstr (why, "maps/vf1637.chim"));
	assert (!AW_MapChimOrphan ("vf1638", why, sizeof(why)));
	aw_chim_world = 1;
	assert (!AW_MapRefused ("maps/vf1637.chim", frame, why, sizeof(why)));
	assert (!AW_MapRefused ("maps/vf1637.bsp", frame, why, sizeof(why)));	/* --chim-frame-ext bsp */
	assert (AW_MapRefused ("maps/vf1639.chim", plain, why, sizeof(why)));
	assert (!AW_MapChimOrphan ("vf1637", why, sizeof(why)));
	printf ("map path resolver ok\n");
	return 0;
}
