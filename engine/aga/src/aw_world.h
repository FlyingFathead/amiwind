/* SPDX-License-Identifier: GPL-2.0-or-later */
#ifndef AW_WORLD_H
#define AW_WORLD_H
int AW_WorldDestination(const char *,const float *,char *,float *);
int AW_WorldToSource(const char *,const float *,float *);
int AW_SourceToWorld(const char *,const float *,float *);
int AW_WorldMapTarget(const float *,char *,float *);
int AW_MapTeleport(const float *);
int AW_MapTeleportAt(const float *,int);
qboolean AW_MapPlaceBelow(edict_t *,const float *);
qboolean AW_MapPlace(edict_t *,const float *);
int AW_WorldContains(const char *,const float *);
const char *AW_RegionNameAt(const float *source_coordinates);
#endif
