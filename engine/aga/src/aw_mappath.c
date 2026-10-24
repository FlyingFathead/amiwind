/* SPDX-License-Identifier: GPL-2.0-or-later
 * The one map path resolver (aw_mappath.h): maps/<name>.chim (a CHIM frame
 * map) when the image has a CHIM world and that file exists, else
 * maps/<name>.bsp. Region frames keep their cell names (vf1637.chim beside
 * vf1638.bsp), so the region directory, handover, saves and the HUD keep
 * working by name.
 */
#include "quakedef.h"
#include "aw_mappath.h"

int aw_chim_world;

/* The answer for the last few names (the region and section look-ahead ask
 * every frame); files do not change while the engine runs. */
#define MAP_ASKED	8
static char asked_name[MAP_ASKED][AW_MAP_PATH_SIZE];
static char asked_chim[MAP_ASKED];
static int asked_stamp[MAP_ASKED], asked_clock;

/* Bounded formatting: 0 (and an empty string) when the result does not fit. */
static int Fmt (char *out, int size, const char *name, const char *ext)
{
	int n = Q_snprintf (out, (size_t)size, "maps/%s%s", name, ext);
	if (n < 0 || n >= size)
	{
		out[0] = 0;
		return 0;
	}
	return 1;
}

static int Exists (const char *path)
{
	FILE *f = NULL;
	char name[AW_MAP_PATH_SIZE];
	if (strlen (path) >= sizeof(name))
		return 0;
	strcpy (name, path);
	COM_FOpenFile (name, &f);
	if (!f)
		return 0;
	fclose (f);
	return 1;
}

static int HasChim (const char *name)
{
	char path[AW_MAP_PATH_SIZE];
	int i, slot = 0;
	for (i=0 ; i<MAP_ASKED ; i++)
		if (asked_stamp[i] && !strcmp (asked_name[i], name))
		{
			asked_stamp[i] = ++asked_clock;
			return asked_chim[i];
		}
	for (i=1 ; i<MAP_ASKED ; i++)
		if (asked_stamp[i] < asked_stamp[slot])
			slot = i;
	strcpy (asked_name[slot], name);
	asked_chim[slot] = Fmt (path, sizeof(path), name, AW_MAP_EXT_CHIM) && Exists (path);
	asked_stamp[slot] = ++asked_clock;
	return asked_chim[slot];
}

char *AW_MapPath (const char *name, char *path, int size)
{
	if (!path || size < 1)
		return path;
	path[0] = 0;
	if (!name || !*name || strlen (name) >= AW_MAP_PATH_SIZE - 10)
		return path;
	if (aw_chim_world && HasChim (name))
		Fmt (path, size, name, AW_MAP_EXT_CHIM);
	else
		Fmt (path, size, name, AW_MAP_EXT_LEGACY);
	return path;
}

static int EndsWith (const char *text, const char *end)
{
	size_t a = strlen (text), b = strlen (end);
	return a >= b && !strcmp (text + a - b, end);
}

int AW_MapPathChim (const char *path)
{
	return path && EndsWith (path, AW_MAP_EXT_CHIM);
}

int AW_MapPathIs (const char *path, const char *name)
{
	size_t n;
	if (!path || !name || strncmp (path, "maps/", 5))
		return 0;
	path += 5;
	n = strlen (name);
	if (strncmp (path, name, n))
		return 0;
	return !strcmp (path + n, AW_MAP_EXT_LEGACY) || !strcmp (path + n, AW_MAP_EXT_CHIM);
}

/* KEY ("\"_chim_frame\"", "\"_chim_room\"") in the worldspawn (the first entity) of the map's entities. */
static int WorldKey (const char *entities, const char *quoted)
{
	const char *end, *key;
	if (!entities || *entities != '{' || !(end = strchr (entities, '}')))
		return 0;
	key = strstr (entities, quoted);
	return key && key < end;
}

static int FrameKey (const char *entities)
{
	return WorldKey (entities, "\"_chim_frame\"");
}

int AW_MapRefused (const char *path, const char *entities, char *why, int size)
{
	int frame = FrameKey (entities);
	if (why && size > 0)
		why[0] = 0;
	if (frame && !aw_chim_world)
	{
		if (why && size > 0)
			Q_snprintf (why, size, "%s is a CHIM frame map: its world is in chim/world.cwi, which this image does not have", path ? path : "map");
		return 1;
	}
	/* a CHIM room map (tools/chim/interior.py: "_chim_room", its models on the interior store) is a .chim file too
	   (IMAGE-ROOM-MAPS-ENGINE-REFUSED-48) */
	if (!frame && AW_MapPathChim (path) && !WorldKey (entities, "\"_chim_room\""))
	{
		if (why && size > 0)
			Q_snprintf (why, size, "%s is a .chim file without a CHIM frame (\"_chim_frame\") or room (\"_chim_room\")", path);
		return 1;
	}
	return 0;
}

int AW_MapChimOrphan (const char *name, char *why, int size)
{
	char path[AW_MAP_PATH_SIZE];
	if (why && size > 0)
		why[0] = 0;
	if (aw_chim_world || !name || !*name || !Fmt (path, sizeof(path), name, AW_MAP_EXT_CHIM) || !Exists (path))
		return 0;
	if (why && size > 0)
		Q_snprintf (why, size, "%s is a CHIM frame map and this image has no CHIM world (chim/world.cwi)", path);
	return 1;
}
