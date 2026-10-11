/* SPDX-License-Identifier: GPL-2.0-or-later
 * The one map path resolver. Every place that turns a map name into a file
 * name asks AW_MapPath: maps/<name>.chim when this image has a CHIM world
 * (chim/world.cwi) and that file exists, else maps/<name>.bsp.
 *
 * A .chim file is a CHIM frame map: a BSP29 file (Quake's model loader
 * dispatches on the header, not the extension) that holds the map's entities,
 * collision-only boxes and an empty world; its geometry lives in the CHIM
 * world (chim/). Without that world it is not a playable map, so the engine
 * refuses it loudly instead of loading a void (AW_MapRefused).
 */
#ifndef AW_MAPPATH_H
#define AW_MAPPATH_H

#define AW_MAP_PATH_SIZE	64		/* MAX_QPATH: "maps/" + name + ".chim" fits */
#define AW_MAP_EXT_LEGACY	".bsp"
#define AW_MAP_EXT_CHIM		".chim"

/* Set by Chim_Init when chim/world.cwi exists. While it is 0 (legacy data)
 * the resolver never asks for a .chim file: legacy paths are unchanged. */
extern int aw_chim_world;

/* path (size bytes) = the file for map name; returns path. */
char *AW_MapPath (const char *name, char *path, int size);
/* 1 when path is maps/<name>.bsp or maps/<name>.chim. */
int AW_MapPathIs (const char *path, const char *name);
/* 1 when path names a .chim file. */
int AW_MapPathChim (const char *path);
/* A loaded map that cannot run here: a CHIM frame map (worldspawn
 * "_chim_frame") without a CHIM world, or a .chim file that is no frame map.
 * Returns 1 and the reason in why. */
int AW_MapRefused (const char *path, const char *entities, char *why, int size);
/* After a failed load: 1 (reason in why) when maps/<name>.chim exists but
 * this image has no CHIM world to run it. */
int AW_MapChimOrphan (const char *name, char *why, int size);

#endif
