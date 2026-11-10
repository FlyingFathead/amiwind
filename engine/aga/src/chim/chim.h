/* SPDX-License-Identifier: GPL-2.0-or-later
 * CHIM: AmiWind's world streamer, inside the one engine tree. Exteriors are a
 * resident world map plus chunks streamed around the player; every shared
 * model and texture is stored once and placed by reference.
 *
 * CHIM is active only for a map whose worldspawn names a CHIM frame
 * ("_chim_frame" "X Y") when chim/world.cwi exists. Otherwise none of this
 * runs: the hooks below stay NULL and the legacy engine is unchanged.
 */
#ifndef CHIM_H
#define CHIM_H

/* CHIM's own version (the CHIM_VERSION file, separate from AmiWind's
 * VERSION), from the generated header. */
#include "chim_version.h"

/* Hooks owned by the legacy files that call them; Chim_Init sets them. */
extern void (*aw_chim_map_begin)(const char *entities);	/* aw_scenery.c */
extern void (*aw_chim_map_end)(void);					/* aw_scenery.c */
extern void (*aw_chim_link)(void);						/* aw_scenery.c */
extern void (*aw_chim_clip)(vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *best); /* aw_scenery.c */
extern void (*aw_chim_player)(vec3_t origin);			/* aw_walk.c */
extern int (*aw_chim_frozen)(edict_t *ent);				/* aw_walk.c, called by sv_phys.c */
extern int (*aw_chim_floor)(const vec3_t origin, float *lowest, float *surface);	/* aw_walk.c: the terrain floor (chim_far.c) */
extern void (*aw_chim_spawn)(vec3_t origin);			/* aw_scene.c */
extern const char *(*aw_chim_town_map)(const char *town);	/* aw_region.c */
extern int (*aw_chim_entity)(char **data);				/* pr_edict.c: a streamed static taken (chim_statics.c) */
extern int (*aw_chim_source)(const float *local, float *world);	/* aw_hud.c: CHIM frame -> original coordinates */
/* aw_world.c: the shared conversion's second half (CHIM-FRAME-SOURCE-CONVERSION-59): the loaded frame map NAME's
 * map units <-> original coordinates, and whether a point lies inside its chunk grid; 0 for any other map */
extern int (*aw_world_chim_source)(const char *name, const float *local, float *world);
extern int (*aw_world_chim_local)(const char *name, const float *world, float *local);
extern int (*aw_world_chim_contains)(const char *name, const float *local);
/* aw_hinged_door.c: turn every copy of a hinged door placement to a yaw, and
 * clip against the copy that is drawn and solid (chim_chunks.c; defined in
 * chim_world.c, set by Chim_Init) */
extern int (*aw_chim_door_yaw)(unsigned pid, float yaw);
extern int (*aw_chim_door_clip)(unsigned pid, vec3_t start, vec3_t mins, vec3_t maxs, vec3_t end, trace_t *trace);
/* aw_hinged_door.c: move every copy of a scripted mover placement by d
 * (WORLD-BUTTONS-62; chim_room.c ChimMovers_Shift, set by Chim_Init) */
extern int (*aw_chim_place_shift)(unsigned pid, const float *d, int relink);
int ChimMovers_Shift (unsigned pid, const float *d, int relink);
/* ... and turn every copy by d (Quake angles; chim_room.c ChimMovers_Turn; NOW
 * gets the angles after it, may be NULL): the cranks, bar doors, Dwemer doors */
extern int (*aw_chim_place_turn)(unsigned pid, const float *d, float *now);
int ChimMovers_Turn (unsigned pid, const float *d, float *now);
/* ... and where its first loaded copy stands now (map units; 1 found) */
extern int (*aw_chim_place_origin)(unsigned pid, float *out);
int ChimMovers_Origin (unsigned pid, float *out);
#define CHIM_PLACE_TURNED	0x40000		/* run-time: a turned mover's box holds every pose */
/* The window's slot i (1 used: its frame and frame-local -> session offset;
 * 0 for every slot without a window) and a frame map's own frame: for the
 * flames of every frame (FIREPIT-FLAMES-62; aw_debug.c hands them to
 * aw_guard_torch.c) */
int Chim_WindowSlot (int i, int *cx, int *cy, float *offset);
int Chim_MapFrame (const char *entities, int *cx, int *cy);

void Chim_Init (void);
int Chim_Active (void);
extern int (*aw_chim_memory)(int op, char *first, char *second, int size);	/* aw_movie.c: extra Fast RAM (chim_world.c) */

#endif
