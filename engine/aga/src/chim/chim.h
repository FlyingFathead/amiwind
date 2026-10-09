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

void Chim_Init (void);
int Chim_Active (void);

#endif
